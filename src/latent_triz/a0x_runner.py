"""Fail-closed orchestration seam for one A0X leg/model pair.

The module deliberately has no model-library, subprocess, network, or target
path dependency.  Task 11 supplies exact, hash-bound dossiers before a later
material wrapper can provide the remaining injected stages.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from latent_triz.validator import validate

from .a0x_contract import (
    A0XContractError,
    Leg,
    PairBinding,
    assert_authorization_chain,
    assert_leg_freeze_binding,
    compute_dense_bound,
    sha256_file,
    strict_json_object,
)
from .a0x_execution import AttemptState, seal_terminal_attempt, validate_authorization_chain
from .a0x_freeze import (
    A0XFreezeError,
    verify_a0_selection_manifest,
    verify_frozen_legs,
    verify_protected_tree_metadata_only,
)
from .a0x_preflight import A0XPreflightError, _validate_admission, _validate_resource, load_registry, verify_card_sources


class A0XRunnerError(RuntimeError):
    """Raised when an A0X pair cannot stay one-shot and fail-closed."""


@dataclass(frozen=True)
class A0XRunnerDependencies:
    """Fixed, injected stages for one synthetic A0/R1 pair lifecycle.

    The bundle deliberately supplies capabilities instead of paths or runtime
    libraries. Production construction is unavailable here: Task 12 must wire
    a separately authorized boundary. Synthetic tests inject only temporary
    objects and can use the Task-9 builder/verifier unchanged.
    """

    static_preflight: Callable[[Mapping[str, Any]], Any]
    tokenizer_factory: Callable[[], Any]
    model_factory: Callable[[Any], Any]
    activation: Callable[[Any], Any]
    activation_sealer: Callable[[Any], Any]
    target_capability_factory: Callable[[Any], Any]
    analysis: Callable[[Any], Any]
    package_builder: Callable[[Any], Path]
    package_verifier: Callable[[Path], None]
    protected_tree_postflight: Callable[[Path], None]
    failure_sealer: Callable[[str, BaseException, PairBinding, Mapping[str, Any]], Mapping[str, Any]]
    release_model: Callable[[Any], None]


class CcpExecutor(Protocol):
    """The only CCP surface accepted by the synthetic contract checker."""

    def sha256(self, path: str) -> str: ...

    def execute(self, argv: tuple[str, ...]) -> tuple[int, bytes]: ...

    def guard_exec(self, argv_commitment: str, child: Callable[[], Mapping[str, Any]]) -> tuple[int, bytes, Mapping[str, Any] | None]: ...

    def review_dry_run(self, trace: Mapping[str, Any]) -> bool: ...


_SCHEMA_PREFIX = "a0x-"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_PAIR_DOSSIERS = {
    ("a0", "smollm2_360m"): "experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json",
    ("a0", "qwen3_0_6b_base"): "experiments/a0x-six-model/approval-dossiers/a0/qwen3_0_6b_base.json",
    ("a0", "gpt2"): "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json",
    ("a0", "smollm2_135m"): "experiments/a0x-six-model/approval-dossiers/a0/smollm2_135m.json",
    ("a0", "gpt_neo_125m"): "experiments/a0x-six-model/approval-dossiers/a0/gpt_neo_125m.json",
    ("a0", "qwen2_5_0_5b"): "experiments/a0x-six-model/approval-dossiers/a0/qwen2_5_0_5b.json",
    ("r1", "smollm2_360m"): "experiments/a0x-six-model/approval-dossiers/r1/smollm2_360m.json",
    ("r1", "qwen3_0_6b_base"): "experiments/a0x-six-model/approval-dossiers/r1/qwen3_0_6b_base.json",
    ("r1", "gpt2"): "experiments/a0x-six-model/approval-dossiers/r1/gpt2.json",
    ("r1", "smollm2_135m"): "experiments/a0x-six-model/approval-dossiers/r1/smollm2_135m.json",
    ("r1", "gpt_neo_125m"): "experiments/a0x-six-model/approval-dossiers/r1/gpt_neo_125m.json",
    ("r1", "qwen2_5_0_5b"): "experiments/a0x-six-model/approval-dossiers/r1/qwen2_5_0_5b.json",
}
_MATERIAL_TARGET_SLUG = {
    "smollm2_360m": "smollm2-360m",
    "qwen3_0_6b_base": "qwen3-0-6b-base",
    "gpt2": "gpt2",
    "smollm2_135m": "smollm2-135m",
    "gpt_neo_125m": "gpt-neo-125m",
    "qwen2_5_0_5b": "qwen2-5-0-5b",
}
_MATERIAL_DOSSIERS = {
    (leg, _MATERIAL_TARGET_SLUG[model_key]): dossier
    for (leg, model_key), dossier in _PAIR_DOSSIERS.items()
}
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_GUARD_EXEC_ACTIVE: ContextVar[bool] = ContextVar("a0x_guard_exec_active", default=False)
_PREFLIGHT_LABELS = (
    "admission status --json", "resource status --json", "plan --json",
    "doctor --json", "dry-run --json",
)
_MATRIX_RUNTIMES = {
    "python311": {
        "kind": "docker_compatible",
        "image": "ghcr.io/marcoporcellato/latent-triz-verify@sha256:25de19baba5938c80de18c930342ccdcdf3c6759051196c3c713bd3e434d2f0e",
        "cpu_count": 1,
        "memory_mib": 1024,
        "pids_limit": 256,
        "network": False,
    },
    "python312": {
        "kind": "docker_compatible",
        "image": "ghcr.io/marcoporcellato/latent-triz-verify@sha256:e984457d591121c52517027f49bb55371f68075caace763b8859db136e434dd0",
        "cpu_count": 1,
        "memory_mib": 1024,
        "pids_limit": 256,
        "network": False,
    },
}
_MATRIX_CHECK_ARGV = {
    "repository-check-py311": ["python", "scripts/repository_check.py"],
    "schema-cross-validate-py311": ["python", "scripts/schema_cross_validate.py"],
    "repository-check-py312": ["python", "scripts/repository_check.py"],
    "schema-cross-validate-py312": ["python", "scripts/schema_cross_validate.py"],
}


def _ccp_argvs(contract: Mapping[str, Any], *, generation: int | None = None) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return the complete frozen CCP argv vectors, never symbolic labels.

    One Matrix V2 configuration owns ``plan``, ``doctor``, ``dry-run`` and
    ``run``. Cache and repository are explicit because CCP resolves them at
    the command boundary rather than from an opaque process default.
    """
    ccp = contract.get("ccp")
    if not isinstance(ccp, Mapping):
        raise A0XRunnerError("material contract CCP identity is invalid")
    matrix = ccp.get("matrix_config_binding")
    location = ccp.get("location_binding")
    if not isinstance(matrix, Mapping) or not isinstance(location, Mapping):
        raise A0XRunnerError("material contract CCP argv bindings are invalid")
    matrix_path = matrix.get("path")
    repository, cache_dir = location.get("repository"), location.get("cache_dir")
    if not all(isinstance(item, str) and item for item in (matrix_path, repository, cache_dir)):
        raise A0XRunnerError("material contract CCP argv paths are invalid")
    rows: list[tuple[str, tuple[str, ...]]] = [
        (_PREFLIGHT_LABELS[0], ("admission", "status", "--json")),
        (_PREFLIGHT_LABELS[1], ("resource", "status", "--json")),
        (_PREFLIGHT_LABELS[2], ("plan", "--config", matrix_path, "--json")),
        (_PREFLIGHT_LABELS[3], ("doctor", "--config", matrix_path, "--json")),
        (_PREFLIGHT_LABELS[4], ("dry-run", "--config", matrix_path, "--repository", repository, "--cache-dir", cache_dir, "--json")),
    ]
    if generation is not None:
        if not _is_integer(generation) or generation <= 0:
            raise A0XRunnerError("CCP generation is invalid")
        rows.append(("run --generation <authorized-u64> --json", ("run", "--config", matrix_path, "--repository", repository, "--cache-dir", cache_dir, "--generation", str(generation), "--json")))
    return tuple(rows)


def planned_material_dossiers() -> dict[tuple[str, str], str]:
    """Return the fixed human-facing Make-target dossier mapping."""
    return dict(_MATERIAL_DOSSIERS)


def frozen_pair_dossiers() -> dict[tuple[str, str], str]:
    """Return the canonical internal leg/model-key dossier mapping."""
    return dict(_PAIR_DOSSIERS)


def verify_a0x_dossier_inventory(root: str | Path) -> None:
    """Require exactly the twelve declared dossier files and no other entry."""

    repository = Path(root).resolve()
    dossier_root = repository / "experiments/a0x-six-model/approval-dossiers"
    expected_files = {repository / relative for relative in _PAIR_DOSSIERS.values()}
    expected_directories = {dossier_root, dossier_root / "a0", dossier_root / "r1"}
    if not dossier_root.is_dir() or dossier_root.is_symlink():
        raise A0XRunnerError("A0X dossier inventory root is unavailable")
    actual_files: set[Path] = set()
    for entry in dossier_root.rglob("*"):
        if entry.is_symlink():
            raise A0XRunnerError("A0X dossier inventory rejects symlinks")
        if entry.is_dir():
            if entry not in expected_directories:
                raise A0XRunnerError("A0X dossier inventory contains an unexpected directory")
            continue
        if not entry.is_file():
            raise A0XRunnerError("A0X dossier inventory contains a non-regular entry")
        actual_files.add(entry)
    if actual_files != expected_files:
        raise A0XRunnerError("A0X dossier inventory differs from the frozen twelve-file set")


def reserve_attempt_claim(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Durably consume one attempt before any material-boundary operation.

    ``O_EXCL`` and ``O_NOFOLLOW`` make concurrent, dangling-link and replay
    claims fail closed.  The record is intentionally never removed here.
    """
    _validate_claim_payload(payload)
    claim = Path(path)
    if claim.is_absolute() and claim.parent == Path("/"):
        raise A0XRunnerError("attempt claim path is unsafe")
    if os.path.lexists(claim):
        raise A0XRunnerError("attempt claim already exists")
    _reject_symlinked_parent(claim)
    claim.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(claim, flags, 0o600)
    except FileExistsError as error:
        raise A0XRunnerError("attempt claim already exists") from error
    except OSError as error:
        raise A0XRunnerError("attempt claim could not be reserved") from error
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(claim.parent)
    except OSError as error:
        raise A0XRunnerError("attempt claim could not be durably sealed") from error
    return claim


def _run_ccp_preflight(
    *, contract: Mapping[str, Any], material_contract_raw: bytes, executor: CcpExecutor,
    source_head: str,
) -> dict[str, Any]:
    """Run exactly the five reviewed read-only commands through an injected fake."""
    try:
        raw_contract = strict_json_object(material_contract_raw)
    except A0XContractError as error:
        raise A0XRunnerError("material contract raw bytes are invalid") from error
    if dict(contract) != raw_contract:
        raise A0XRunnerError("material contract object differs from raw bytes")
    _validate_material_contract(raw_contract)
    ccp = contract.get("ccp") if isinstance(contract, Mapping) else None
    if not isinstance(ccp, Mapping) or not _REVISION.fullmatch(source_head):
        raise A0XRunnerError("material contract or source HEAD is invalid")
    expected = _ccp_argvs(contract)
    expected_contract_argv = [list(argv) for _label, argv in _ccp_argvs(contract)]
    expected_contract_argv.append(["run", "--config", ccp["matrix_config_binding"]["path"], "--repository", ccp["location_binding"]["repository"], "--cache-dir", ccp["location_binding"]["cache_dir"], "--generation", "<authorized-u64>", "--json"])
    expected_contract_argv.append(["guard", "exec"])
    if ccp.get("commands") != expected_contract_argv or ccp.get("hash_before_command") is not True:
        raise A0XRunnerError("material CCP command order is invalid")
    trace: list[dict[str, Any]] = []
    validated_inputs: dict[str, dict[str, Any]] = {}
    for command, argv in expected:
        observed_hash = executor.sha256(ccp["path"])
        if observed_hash != ccp.get("sha256"):
            raise A0XRunnerError("CCP executable hash drift")
        exit_code, raw = executor.execute(argv)
        if not isinstance(exit_code, int) or exit_code != 0 or not isinstance(raw, bytes):
            raise A0XRunnerError("CCP command failed or returned malformed output")
        try:
            parsed = strict_json_object(raw)
        except A0XContractError as error:
            raise A0XRunnerError("CCP output is not strict JSON") from error
        _validate_ccp_response(command, parsed, ccp)
        if command in {"admission status --json", "resource status --json"}:
            validated_inputs[command] = dict(parsed)
        trace.append({"command": command, "argv": list(argv), "executable_sha256": observed_hash, "exit_code": exit_code, "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw), "state": _privacy_minimized_state(command, parsed)})
    return {
        "source_head": source_head,
        "commands": trace,
        "resource": validated_inputs["resource status --json"],
        "admission": validated_inputs["admission status --json"],
        "run_count": 0,
    }


def _run_once(contract: Mapping[str, Any], executor: CcpExecutor, argv_commitment: str, callback: Callable[[], Mapping[str, Any]]) -> tuple[dict[str, Any], Mapping[str, Any] | None]:
    """Execute the one lifecycle callback inside the injected CCP run guard."""
    ccp = contract["ccp"]
    observed_hash = executor.sha256(ccp["path"])
    if observed_hash != ccp["sha256"]:
        raise A0XRunnerError("CCP executable hash drift")
    if not isinstance(argv_commitment, str) or not _SHA256.fullmatch(argv_commitment):
        raise A0XRunnerError("CCP guard argv commitment is invalid")
    def guarded_child() -> Mapping[str, Any]:
        token = _GUARD_EXEC_ACTIVE.set(True)
        try:
            return callback()
        finally:
            _GUARD_EXEC_ACTIVE.reset(token)

    exit_code, raw, child = executor.guard_exec(argv_commitment, guarded_child)
    if not isinstance(exit_code, int) or isinstance(exit_code, bool) or not isinstance(raw, bytes):
        raise A0XRunnerError("CCP guard exec returned a malformed terminal result")
    if exit_code != 0:
        classification = _classify_guard_exit(exit_code)
        return ({"command": "guard exec", "executable_sha256": observed_hash, "exit_code": exit_code,
                 "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw),
                 "state": {"argv_commitment": argv_commitment, "guard_exit_classification": classification,
                           "child_exit": None, "child_exit_classification": classification,
                           "lifecycle_status": "not_completed", "terminal_links": []}}, None)
    if not isinstance(child, Mapping):
        raise A0XRunnerError("CCP guard exec completed without a child result")
    # ``guard exec`` tees the child program's output and intentionally does
    # not have a CCP JSON envelope.  The exit status is the only CCP result;
    # raw child output is retained only as a privacy-minimized hash/length.
    terminal_link = child.get("package_path")
    lifecycle_status = child.get("status")
    terminal_links = [terminal_link] if isinstance(terminal_link, str) and terminal_link else []
    if lifecycle_status not in {"completed", "positive", "null", "non_interpretable", "incompatible", "failed"} or len(terminal_links) != 1:
        raise A0XRunnerError("CCP guarded child did not return one sealed terminal package link")
    return ({"command": "guard exec", "executable_sha256": observed_hash, "exit_code": exit_code,
            "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw),
            "state": {
                "argv_commitment": argv_commitment,
                "guard_exit_classification": "completed",
                "child_exit": 0,
                "child_exit_classification": "completed",
                "lifecycle_status": lifecycle_status,
                "terminal_links": terminal_links,
            }}, child)


def _classify_guard_exit(exit_code: int) -> str:
    """Classify the documented synchronous ``guard exec`` terminal codes."""
    if exit_code == 124:
        return "timeout"
    if exit_code == 130:
        return "cancelled"
    if exit_code == 70:
        return "cleanup_or_internal"
    if 1 <= exit_code <= 255:
        return "child_failed"
    return "invalid_exit"


def _validate_ccp_response(command: str, parsed: Mapping[str, Any], ccp: Mapping[str, Any]) -> None:
    try:
        if command == "admission status --json":
            _validate_admission(parsed)
        elif command == "resource status --json":
            _validate_resource(parsed)
        elif command == "plan --json":
            plan_binding = ccp["matrix_plan_binding"]
            if set(parsed) != {"plan_digest", "plan"} or parsed.get("plan_digest") != plan_binding["outer_digest"]:
                raise A0XRunnerError("CCP plan digest does not match the frozen configuration")
            plan = parsed.get("plan")
            if not isinstance(plan, Mapping) or set(plan) != {"schema_version", "project", "receipt", "environment", "caches", "runtimes"}:
                raise A0XRunnerError("CCP plan shape is malformed")
            if plan.get("schema_version") != "2.0" or plan.get("project") != "MarcoPorcellato/Latent-TRIZ":
                raise A0XRunnerError("CCP Matrix plan identity is invalid")
            _validate_matrix_plan_v2(plan, ccp)
            runtimes = plan.get("runtimes")
            expected_digests = {"python311": plan_binding["python311_digest"], "python312": plan_binding["python312_digest"]}
            if not isinstance(runtimes, list) or len(runtimes) != 2:
                raise A0XRunnerError("CCP Matrix plan runtime projection is invalid")
            observed_digests = {
                item.get("id"): item.get("configuration_digest")
                for item in runtimes if isinstance(item, Mapping)
                and set(item) == {"id", "configuration_digest", "runtime", "checks"}
                and isinstance(item.get("runtime"), Mapping) and isinstance(item.get("checks"), list)
            }
            if observed_digests != expected_digests:
                raise A0XRunnerError("CCP Matrix plan runtime digests drifted")
        elif command == "doctor --json":
            _validate_matrix_doctor(parsed, ccp)
        elif command == "dry-run --json":
            _validate_matrix_dry_run(parsed, ccp)
        else:
            raise A0XRunnerError("CCP command is not allowed")
    except (A0XPreflightError, KeyError, TypeError) as error:
        raise A0XRunnerError("CCP response is invalid for its command") from error


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_keys(value: Any, expected: set[str], context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise A0XRunnerError(f"CCP {context} shape is malformed")
    return value


def _require_sha256_id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:") or not _SHA256.fullmatch(value.removeprefix("sha256:")):
        raise A0XRunnerError(f"CCP {context} digest is malformed")
    return value


def _canonical_ccp_receipt_id(receipt: Mapping[str, Any]) -> str:
    """Match CCP canonical JSON for the strict, integer-only receipt envelope."""
    try:
        raw = json.dumps(dict(receipt), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XRunnerError("CCP receipt cannot be canonically encoded") from error
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _validate_matrix_plan_v2(plan: Mapping[str, Any], ccp: Mapping[str, Any]) -> None:
    """Validate a full MatrixPlanEnvelopeV2 projection; reject synthetic stubs."""
    _require_keys(plan, {"schema_version", "project", "receipt", "environment", "caches", "runtimes"}, "Matrix plan")
    if plan["schema_version"] != "2.0" or plan["project"] != "MarcoPorcellato/Latent-TRIZ":
        raise A0XRunnerError("CCP Matrix plan identity is invalid")
    receipt = _require_keys(plan["receipt"], {"output", "freshness_seconds"}, "Matrix plan receipt")
    if receipt["output"] != ".ccp/receipt.json" or not _is_integer(receipt["freshness_seconds"]) or receipt["freshness_seconds"] <= 0:
        raise A0XRunnerError("CCP Matrix plan receipt is invalid")
    environment = _require_keys(plan["environment"], {"inherit", "fixed", "runtime_internal", "remote_secret_only"}, "Matrix plan environment")
    if any(not isinstance(environment[name], list) for name in environment):
        raise A0XRunnerError("CCP Matrix plan environment is invalid")
    caches = plan["caches"]
    if not isinstance(caches, list) or any(not isinstance(item, Mapping) or set(item) != {"id", "mount_path"} for item in caches):
        raise A0XRunnerError("CCP Matrix plan caches are invalid")
    expected_digests = {"python311": ccp["matrix_plan_binding"]["python311_digest"], "python312": ccp["matrix_plan_binding"]["python312_digest"]}
    expected_checks = {"python311": {"repository-check-py311", "schema-cross-validate-py311"}, "python312": {"repository-check-py312", "schema-cross-validate-py312"}}
    runtimes = plan["runtimes"]
    if not isinstance(runtimes, list) or len(runtimes) != 2:
        raise A0XRunnerError("CCP Matrix plan runtime projection is invalid")
    observed: dict[str, str] = {}
    for item in runtimes:
        runtime = _require_keys(item, {"id", "configuration_digest", "runtime", "checks"}, "Matrix runtime plan")
        runtime_id = runtime["id"]
        if not isinstance(runtime_id, str) or runtime_id not in expected_digests or runtime_id in observed or runtime["configuration_digest"] != expected_digests[runtime_id]:
            raise A0XRunnerError("CCP Matrix plan runtime digests drifted")
        shape = runtime["runtime"]
        if not isinstance(shape, Mapping) or dict(shape) != _MATRIX_RUNTIMES[runtime_id]:
            raise A0XRunnerError("CCP Matrix runtime plan is malformed")
        checks = runtime["checks"]
        if not isinstance(checks, list) or len(checks) != 2:
            raise A0XRunnerError("CCP Matrix runtime checks are invalid")
        identifiers: set[str] = set()
        for check in checks:
            required_fields = {"id", "required", "argv", "working_directory", "timeout_seconds", "depends_on", "artifacts"}
            optional_fields = required_fields | {"artifact_contracts"}
            if not isinstance(check, Mapping) or set(check) not in (required_fields, optional_fields) or check.get("required") is not True or not isinstance(check.get("id"), str) or not isinstance(check.get("argv"), list) or not check["argv"] or not isinstance(check.get("working_directory"), str) or not _is_integer(check.get("timeout_seconds")) or check["timeout_seconds"] <= 0 or not isinstance(check.get("depends_on"), list) or not isinstance(check.get("artifacts"), list):
                raise A0XRunnerError("CCP Matrix check plan is malformed")
            if check["id"] not in expected_checks[runtime_id] or check["argv"] != _MATRIX_CHECK_ARGV[check["id"]] or check["working_directory"] != "." or check["timeout_seconds"] != 300 or check["depends_on"] != [] or check["artifacts"] != [] or check.get("artifact_contracts", []) != []:
                raise A0XRunnerError("CCP Matrix check binding drifted")
            identifiers.add(check["id"])
        if identifiers != expected_checks[runtime_id]:
            raise A0XRunnerError("CCP Matrix check bindings drifted")
        observed[runtime_id] = runtime["configuration_digest"]
    if observed != expected_digests:
        raise A0XRunnerError("CCP Matrix plan runtime digests drifted")


def _validate_v1_doctor(value: Mapping[str, Any]) -> None:
    """Validate the producer's complete ``RuntimeProbe`` JSON projection."""
    required = {
        "runtime", "flavor", "server_version", "operating_system", "os_type",
        "containment", "graceful_stop",
    }
    optional = {"memory_limit_supported", "swap_limit_supported"}
    if not required.issubset(value) or set(value) - required - optional:
        raise A0XRunnerError("CCP doctor shape is malformed")
    if value["runtime"] != "docker_compatible" or value["flavor"] not in {"docker_compatible", "orb_stack"}:
        raise A0XRunnerError("CCP doctor runtime identity is invalid")
    if not isinstance(value["server_version"], str) or not value["server_version"]:
        raise A0XRunnerError("CCP doctor server version is invalid")
    operating_system = value["operating_system"]
    if operating_system is not None and (not isinstance(operating_system, str) or not operating_system):
        raise A0XRunnerError("CCP doctor operating system is invalid")
    if value["os_type"] != "linux":
        raise A0XRunnerError("CCP doctor OS type is invalid")
    if value["containment"] != "process_group" or value["graceful_stop"] != "process_group_signal":
        raise A0XRunnerError("CCP doctor process-control capability is invalid")
    if any(not isinstance(value[name], bool) for name in optional if name in value):
        raise A0XRunnerError("CCP doctor resource capability flag is invalid")


def _validate_matrix_rows(
    value: Mapping[str, Any], ccp: Mapping[str, Any], *, payload_key: str, context: str,
) -> list[Mapping[str, Any]]:
    _require_keys(value, {"schema_version", "plan_digest", "runtimes"}, context)
    binding = ccp["matrix_plan_binding"]
    if value["schema_version"] != "2.0" or value["plan_digest"] != binding["outer_digest"]:
        raise A0XRunnerError(f"CCP {context} does not match the frozen Matrix plan")
    runtimes = value["runtimes"]
    if not isinstance(runtimes, list) or len(runtimes) != 2:
        raise A0XRunnerError(f"CCP {context} runtime projection is invalid")
    expected_ids = ("python311", "python312")
    for runtime_id, row in zip(expected_ids, runtimes, strict=True):
        runtime = _require_keys(row, {"runtime_id", "configuration_digest", payload_key}, f"{context} runtime")
        if runtime["runtime_id"] != runtime_id or runtime["configuration_digest"] != binding[f"{runtime_id}_digest"]:
            raise A0XRunnerError(f"CCP {context} runtime binding drifted")
    return runtimes


def _validate_matrix_doctor(value: Mapping[str, Any], ccp: Mapping[str, Any]) -> None:
    """Validate CCP's Matrix V2 doctor envelope and every inner probe."""
    for runtime in _validate_matrix_rows(value, ccp, payload_key="probe", context="Matrix doctor"):
        _validate_v1_doctor(runtime["probe"])


def _validate_matrix_dry_run(value: Mapping[str, Any], ccp: Mapping[str, Any]) -> None:
    """Validate CCP's Matrix V2 dry-run envelope without executing checks."""
    expected_checks = {
        "python311": {"repository-check-py311", "schema-cross-validate-py311"},
        "python312": {"repository-check-py312", "schema-cross-validate-py312"},
    }
    binding = ccp["matrix_plan_binding"]
    for runtime in _validate_matrix_rows(value, ccp, payload_key="dry_run", context="Matrix dry-run"):
        runtime_id = runtime["runtime_id"]
        _validate_v1_dry_run(
            runtime["dry_run"],
            runtime_id=runtime_id,
            expected_digest=binding[f"{runtime_id}_digest"],
            expected_check_ids=expected_checks[runtime_id],
        )


def _validate_v1_dry_run(
    value: Mapping[str, Any], *, runtime_id: str, expected_digest: str, expected_check_ids: set[str],
) -> None:
    """Validate one inner V1 ``DryRunPlan`` from the Matrix envelope."""
    _require_keys(
        value,
        {"schema_version", "plan_digest", "runtime", "program", "checks", "workspace", "workspace_mount_policy", "executed"},
        "V1 dry-run",
    )
    if (
        value["schema_version"] != "1.0"
        or value["plan_digest"] != expected_digest
        or value["runtime"] != "docker_compatible"
        or value["program"] != "docker"
        or value["workspace_mount_policy"] != "explicit_bindings"
        or value["executed"] is not False
    ):
        raise A0XRunnerError("CCP dry-run does not match the frozen plan")

    workspace = value["workspace"]
    required_workspace = {"schema_version", "repository", "run_root", "mounts"}
    if not isinstance(workspace, Mapping) or not required_workspace.issubset(workspace) or set(workspace) - required_workspace - {"source_snapshot_digest"}:
        raise A0XRunnerError("CCP dry-run workspace shape is malformed")
    repository = workspace["repository"]
    run_root = workspace["run_root"]
    if workspace["schema_version"] != "1.0" or not isinstance(repository, str) or not Path(repository).is_absolute() or not isinstance(run_root, str) or not Path(run_root).is_absolute():
        raise A0XRunnerError("CCP dry-run workspace identity is invalid")
    if "source_snapshot_digest" in workspace:
        _require_sha256_id(workspace["source_snapshot_digest"], "V1 workspace snapshot")
    mounts = workspace["mounts"]
    if not isinstance(mounts, list) or len(mounts) != 1:
        raise A0XRunnerError("CCP dry-run workspace mounts are invalid")
    mount = _require_keys(mounts[0], {"source", "target", "access", "purpose"}, "V1 repository mount")
    if mount != {"source": repository, "target": "/workspace", "access": "read_only", "purpose": "repository"}:
        raise A0XRunnerError("CCP dry-run repository mount is invalid")

    checks = value["checks"]
    if not isinstance(checks, list) or len(checks) != len(expected_check_ids):
        raise A0XRunnerError("CCP dry-run check set is invalid")
    observed_ids: set[str] = set()
    expected_mount = f"type=bind,src={repository},dst=/workspace,readonly"
    runtime = _MATRIX_RUNTIMES[runtime_id]
    for item in checks:
        check = _require_keys(item, {"id", "program", "argv", "depends_on"}, "V1 dry-run check")
        argv = check["argv"]
        check_id = check["id"]
        expected_argv = [
            "run", "--rm", "--init", "--read-only", "--network", "none",
            "--cpus", str(runtime["cpu_count"]),
            "--memory", f"{runtime['memory_mib']}m",
            "--pids-limit", str(runtime["pids_limit"]),
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--env", "TMPDIR=/tmp",
            "--mount", expected_mount,
            "--workdir", "/workspace",
            runtime["image"],
            *_MATRIX_CHECK_ARGV.get(check_id, []),
        ]
        if (
            check_id not in expected_check_ids
            or check_id in observed_ids
            or check["program"] != "docker"
            or check["depends_on"] != []
            or argv != expected_argv
        ):
            raise A0XRunnerError("CCP dry-run check binding is invalid")
        observed_ids.add(check_id)
    if observed_ids != expected_check_ids:
        raise A0XRunnerError("CCP dry-run check set is invalid")


def validate_matrix_qualification_receipt(raw: bytes, *, contract: Mapping[str, Any], source_head: str, generation: int) -> dict[str, Any]:
    """Validate one canonical MatrixReceiptEnvelopeV2 for a specific CCP generation."""
    if not _REVISION.fullmatch(source_head) or not _is_integer(generation) or generation <= 0:
        raise A0XRunnerError("qualification source HEAD or generation is invalid")
    try:
        envelope = strict_json_object(raw)
    except A0XContractError as error:
        raise A0XRunnerError("Matrix qualification receipt is not strict JSON") from error
    _require_keys(envelope, {"receipt_id", "receipt"}, "Matrix receipt envelope")
    receipt_id = _require_sha256_id(envelope["receipt_id"], "Matrix receipt")
    receipt = _require_keys(envelope["receipt"], {"schema_version", "producer", "repository", "run", "configuration_digest", "runtime_receipts", "overall_status", "incomplete_reason", "redaction_policy_version"}, "Matrix receipt")
    if _canonical_ccp_receipt_id(receipt) != receipt_id:
        raise A0XRunnerError("CCP Matrix receipt ID does not match canonical receipt bytes")
    ccp = contract.get("ccp")
    if not isinstance(ccp, Mapping):
        raise A0XRunnerError("material contract CCP identity is invalid")
    if receipt["schema_version"] != "2.0" or receipt["overall_status"] != "PASS" or receipt["incomplete_reason"] is not None or not isinstance(receipt["redaction_policy_version"], str) or not receipt["redaction_policy_version"]:
        raise A0XRunnerError("CCP Matrix qualification status is invalid")
    producer = _require_keys(receipt["producer"], {"name", "version"}, "Matrix receipt producer")
    if producer != {"name": "commit-ci-preflight", "version": ccp["version"].removeprefix("commit-ci-preflight ")}:
        raise A0XRunnerError("CCP Matrix receipt producer drifted")
    repository = _require_keys(receipt["repository"], {"repository", "commit_sha", "dirty"}, "Matrix receipt repository")
    if repository != {"repository": contract["repository"], "commit_sha": source_head, "dirty": False}:
        raise A0XRunnerError("CCP Matrix receipt source identity drifted")
    run = _require_keys(receipt["run"], {"run_id", "generation", "started_at_utc", "finished_at_utc"}, "Matrix receipt run")
    if not isinstance(run["run_id"], str) or not run["run_id"] or run["generation"] != generation or not _is_integer(run["generation"]) or not isinstance(run["started_at_utc"], str) or not isinstance(run["finished_at_utc"], str) or run["finished_at_utc"] < run["started_at_utc"]:
        raise A0XRunnerError("CCP Matrix receipt run evidence drifted")
    binding = ccp["matrix_plan_binding"]
    if receipt["configuration_digest"] != binding["outer_digest"]:
        raise A0XRunnerError("CCP Matrix receipt outer digest drifted")
    runtime_receipts = receipt["runtime_receipts"]
    if not isinstance(runtime_receipts, list) or len(runtime_receipts) != 2:
        raise A0XRunnerError("CCP Matrix receipt runtime set is invalid")
    expected_runtime_digests = {"python311": binding["python311_digest"], "python312": binding["python312_digest"]}
    expected_check_ids = {"python311": {"repository-check-py311", "schema-cross-validate-py311"}, "python312": {"repository-check-py312", "schema-cross-validate-py312"}}
    observed_runtime_ids: set[str] = set()
    observed_check_ids: set[str] = set()
    for group in runtime_receipts:
        group = _require_keys(group, {"runtime_id", "receipt"}, "Matrix runtime receipt")
        runtime_id = group["runtime_id"]
        if not isinstance(runtime_id, str) or runtime_id not in expected_runtime_digests or runtime_id in observed_runtime_ids:
            raise A0XRunnerError("CCP Matrix receipt runtime IDs drifted")
        _validate_runtime_receipt_v1(group["receipt"], runtime_id=runtime_id, expected_configuration_digest=expected_runtime_digests[runtime_id], producer=producer, repository=repository, generation=generation, expected_checks=expected_check_ids[runtime_id])
        observed_runtime_ids.add(runtime_id)
        observed_check_ids.update(check["id"] for check in group["receipt"]["receipt"]["checks"])
    if observed_runtime_ids != set(expected_runtime_digests) or len(observed_check_ids) != 4:
        raise A0XRunnerError("CCP Matrix receipt checks are incomplete")
    return envelope


def _validate_runtime_receipt_v1(value: Any, *, runtime_id: str, expected_configuration_digest: str, producer: Mapping[str, Any], repository: Mapping[str, Any], generation: int, expected_checks: set[str]) -> None:
    envelope = _require_keys(value, {"receipt_id", "receipt"}, "runtime receipt envelope")
    receipt = _require_keys(envelope["receipt"], {"schema_version", "producer", "repository", "run", "platform", "configuration_digest", "checks", "overall_status", "incomplete_reason", "redaction_policy_version"}, "runtime receipt")
    if _require_sha256_id(envelope["receipt_id"], "runtime receipt") != _canonical_ccp_receipt_id(receipt):
        raise A0XRunnerError("CCP runtime receipt ID does not match canonical receipt bytes")
    if receipt["schema_version"] != "1.0" or receipt["producer"] != producer or receipt["repository"] != repository or receipt["configuration_digest"] != expected_configuration_digest or receipt["overall_status"] != "PASS" or receipt["incomplete_reason"] is not None or receipt["redaction_policy_version"] != "1.0":
        raise A0XRunnerError("CCP runtime receipt evidence drifted")
    run = _require_keys(receipt["run"], {"run_id", "generation", "started_at_utc", "finished_at_utc"}, "runtime receipt run")
    if (
        not isinstance(run["run_id"], str) or not run["run_id"]
        or run["generation"] != generation or not _is_integer(run["generation"])
        or not isinstance(run["started_at_utc"], str) or not run["started_at_utc"]
        or not isinstance(run["finished_at_utc"], str) or not run["finished_at_utc"]
        or run["finished_at_utc"] < run["started_at_utc"]
    ):
        raise A0XRunnerError("CCP runtime receipt generation drifted")
    platform = _require_keys(receipt["platform"], {"host_os", "host_arch", "runtime_kind", "runtime_version", "image_reference", "image_digest"}, "runtime receipt platform")
    expected_image = _MATRIX_RUNTIMES[runtime_id]["image"]
    expected_image_digest = expected_image.rsplit("@", 1)[1]
    if any(not isinstance(platform[name], str) or not platform[name] for name in platform) or platform["runtime_kind"] != "docker_compatible" or platform["image_reference"] != expected_image or platform["image_digest"] != expected_image_digest:
        raise A0XRunnerError("CCP runtime receipt platform is invalid")
    _require_sha256_id(platform["image_digest"], "runtime image")
    checks = receipt["checks"]
    if not isinstance(checks, list) or len(checks) != 2:
        raise A0XRunnerError("CCP runtime receipt checks are invalid")
    observed = set()
    expected_fields = {"id", "required", "argv", "working_directory", "status", "exit_code", "duration_ms", "timed_out", "cancelled", "output_digest", "incomplete_reason"}
    for check in checks:
        check = _require_keys(check, expected_fields, "runtime check")
        if not isinstance(check["id"], str) or check["id"] not in expected_checks or check["id"] in observed or check["required"] is not True or check["argv"] != _MATRIX_CHECK_ARGV[check["id"]] or check["working_directory"] != "." or check["status"] != "PASS" or check["exit_code"] != 0 or not _is_integer(check["duration_ms"]) or check["duration_ms"] < 0 or check["timed_out"] is not False or check["cancelled"] is not False or check["incomplete_reason"] is not None:
            raise A0XRunnerError("CCP runtime check evidence is invalid")
        _require_sha256_id(check["output_digest"], "runtime check output")
        observed.add(check["id"])
    if observed != expected_checks:
        raise A0XRunnerError("CCP runtime check bindings drifted")


def _privacy_minimized_state(command: str, parsed: Mapping[str, Any]) -> dict[str, Any]:
    if command == "admission status --json":
        return {"active": parsed["active"], "queue_count": parsed["queue_count"]}
    if command == "resource status --json":
        return {"decision": parsed["decision"], "policy_version": parsed["policy_version"]}
    if command in {"plan --json", "dry-run --json"}:
        return {"plan_digest": parsed["plan_digest"]}
    return {"accepted": True}


def _reject_symlinked_parent(path: Path) -> None:
    """Reject a user-controlled existing symlink before creating descendants.

    Walk upward only until the nearest existing regular directory.  That avoids
    treating macOS's system-level ``/var`` indirection as an attempt-path
    alias, while still rejecting a dangling descendant beneath a symlink.
    """
    current = path.parent
    while current != current.parent:
        if os.path.lexists(current):
            if current.is_symlink():
                raise A0XRunnerError("attempt claim parent contains a symlink")
            return
        current = current.parent


def _fsync_directory(path: Path) -> None:
    """Persist a newly created claim directory entry before any later stage."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise A0XRunnerError("attempt claim parent directory could not be durably sealed") from error


def _validate_material_contract(contract: Mapping[str, Any]) -> None:
    expected_ccp = {
        "path": "/Users/marco1/.cargo/bin/commit-ci-preflight",
        "source_commit": "3fccc197e5055a2759ee7afe51b91133938ec904",
        "qualified_source_tree": "9e478c1489a9926772e8ab8bea21bd57470494b6",
        "sha256": "b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c",
        "version": "commit-ci-preflight 0.1.0",
    }
    if contract.get("repository") != "MarcoPorcellato/Latent-TRIZ" or contract.get("max_run_count") != 1:
        raise A0XRunnerError("material contract identity is invalid")
    bindings = {"matrix_config_binding": {"path": ".commit-ci-preflight.toml", "raw_sha256": "3dc320e11a22cd0774a64b4a3773fd7568e389b1092b165da17b073685832a9b"}, "matrix_policy_binding": {"path": ".commit-ci-policy-v2.toml", "raw_sha256": "4f68f75523b1a5131f81db668a3e017f62cf180f9cf1c2422d2b2e94b471d0ca"}, "location_binding": {"repository": ".", "cache_dir": "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1"}, "matrix_plan_binding": {"outer_digest": "sha256:25b35b942a6ff9b6237ebed7cefbdbc96b968bbe8954a38b606942f36b8df4b2", "python311_digest": "sha256:b3d8beef1542566d9d925bfee77d2244995dc74adcd879128ef65e82ed1d354b", "python312_digest": "sha256:d446c4ca0602c09eee61c796ad2972f58ab0eebe84a39f928fd90aac5bfb535c"}}
    expected_commands = [list(argv) for _label, argv in _ccp_argvs({"ccp": {**expected_ccp, **bindings}})]
    expected_commands.append(["run", "--config", ".commit-ci-preflight.toml", "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--generation", "<authorized-u64>", "--json"])
    expected_commands.append(["guard", "exec"])
    if contract.get("ccp") != {**expected_ccp, "commands": expected_commands, "hash_before_command": True, **bindings}:
        raise A0XRunnerError("material contract CCP identity is invalid")
    if contract.get("offline") != {"network": False, "generation": False, "local_cpu_float32": True}:
        raise A0XRunnerError("material contract offline prohibitions are invalid")
    if contract.get("stop_boundaries") != ["before_model_load", "after_first_terminal_outcome", "after_one_sealed_target_read"]:
        raise A0XRunnerError("material contract stop-boundary vocabulary is invalid")


def validate_qualification_authorization(
    authorization: Mapping[str, Any], *, material_contract_raw: bytes, source_head: str, contract: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Validate the separate one-shot Matrix qualification authorization.

    Qualification owns the positive CCP generation.  A later scientific-pair
    authorization is deliberately a different document and cannot smuggle one
    into ``guard exec``.
    """
    try:
        from .a0x_contract import QUALIFICATION_AUTHORIZATION_PROFILE, canonical_commitment
        canonical_commitment(authorization, QUALIFICATION_AUTHORIZATION_PROFILE)
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XRunnerError("qualification authorization is not schema-valid") from error
    ccp = contract.get("ccp")
    authorization_ccp = authorization.get("ccp")
    if not isinstance(ccp, Mapping) or not isinstance(authorization_ccp, Mapping):
        raise A0XRunnerError("qualification authorization CCP scope is invalid")
    identity_fields = ("path", "source_commit", "qualified_source_tree", "sha256", "version")
    if authorization.get("qualification_status") != "authorized" or authorization.get("repository") != contract.get("repository") or authorization.get("source_head") != source_head or authorization.get("material_contract_raw_sha256") != hashlib.sha256(material_contract_raw).hexdigest() or any(authorization_ccp.get(field) != ccp.get(field) for field in identity_fields):
        raise A0XRunnerError("qualification authorization binding drifted")
    generation = authorization.get("generation")
    if not _is_integer(generation) or generation <= 0 or authorization.get("max_qualification_run_count") != 1 or authorization.get("stop_boundary") != "after_repository_qualification_receipt" or not isinstance(authorization.get("authorization_id"), str) or not authorization["authorization_id"]:
        raise A0XRunnerError("qualification authorization generation or limit is invalid")
    return authorization


def run_a0x_repository_qualification(
    *, material_contract_raw: bytes, authorization_path: str | Path,
    expected_authorization_raw_sha256: str, qualification_claim_path: str | Path,
    repository_root: str | Path, source_head_probe: Callable[[], str], executor: CcpExecutor,
    source_head: str,
) -> dict[str, Any]:
    """Perform the separately authorized Matrix-v2 qualification seam.

    This synthetic-only coordinator deliberately does not start a process by
    itself.  It accepts an injected executor so Task 10 can prove exact command
    and receipt binding without touching CCP, Docker, or admission state.
    """
    contract = strict_json_object(material_contract_raw)
    _validate_material_contract(contract)
    repository = Path(repository_root).resolve()
    qualification, authorization_raw = _read_json_document_with_raw(Path(authorization_path), "qualification authorization")
    if not _SHA256.fullmatch(expected_authorization_raw_sha256) or hashlib.sha256(authorization_raw).hexdigest() != expected_authorization_raw_sha256:
        raise A0XRunnerError("qualification authorization bytes are not hash-bound")
    qualification = validate_qualification_authorization(
        qualification, material_contract_raw=material_contract_raw, source_head=source_head, contract=contract,
    )
    if os.path.lexists(qualification_claim_path):
        raise A0XRunnerError("qualification claim already exists")
    preflight = _run_ccp_preflight(contract=contract, material_contract_raw=material_contract_raw, executor=executor, source_head=source_head)
    if executor.review_dry_run(preflight) is not True:
        raise A0XRunnerError("CCP dry-run review was rejected")
    if source_head_probe() != source_head:
        raise A0XRunnerError("qualification source HEAD drifted after CCP review")
    _validate_policy_binding(repository, contract)
    qualification, reread_authorization_raw = _read_json_document_with_raw(Path(authorization_path), "qualification authorization")
    if hashlib.sha256(reread_authorization_raw).hexdigest() != expected_authorization_raw_sha256:
        raise A0XRunnerError("qualification authorization bytes drifted after CCP review")
    qualification = validate_qualification_authorization(qualification, material_contract_raw=material_contract_raw, source_head=source_head, contract=contract)
    generation = qualification["generation"]
    ccp = contract["ccp"]
    observed_hash = executor.sha256(ccp["path"])
    if observed_hash != ccp["sha256"]:
        raise A0XRunnerError("CCP executable hash drift")
    _reserve_qualification_claim(
        qualification_claim_path, authorization=qualification,
        authorization_raw_sha256=expected_authorization_raw_sha256, source_head=source_head,
    )
    command_label, command_argv = _ccp_argvs(contract, generation=generation)[-1]
    observed_hash = executor.sha256(ccp["path"])
    if observed_hash != ccp["sha256"]:
        raise A0XRunnerError("CCP executable hash drift")
    exit_code, raw = executor.execute(command_argv)
    if not isinstance(exit_code, int) or exit_code != 0 or not isinstance(raw, bytes):
        raise A0XRunnerError("CCP Matrix qualification run failed")
    envelope = validate_matrix_qualification_receipt(raw, contract=contract, source_head=source_head, generation=generation)
    return {
        "source_head": source_head,
        "generation": generation,
        "receipt_id": envelope["receipt_id"],
        "receipt_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "receipt_raw_bytes": len(raw),
        "preflight": preflight,
        "run_record": {"command": command_label, "argv": list(command_argv), "executable_sha256": observed_hash, "exit_code": 0, "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw), "state": {"overall_status": "PASS", "receipt_id": envelope["receipt_id"]}},
    }


def _reserve_qualification_claim(
    path: str | Path, *, authorization: Mapping[str, Any], authorization_raw_sha256: str, source_head: str,
) -> Path:
    """Irreversibly consume one qualification authorization before Matrix run."""
    claim = Path(path)
    if claim.is_absolute() and claim.parent == Path("/"):
        raise A0XRunnerError("qualification claim path is unsafe")
    if os.path.lexists(claim):
        raise A0XRunnerError("qualification claim already exists")
    _reject_symlinked_parent(claim)
    claim.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_class": "a0x-qualification-attempt-claim",
        "claim_version": "a0x-qualification-attempt-claim-v1",
        "authorization_id": authorization["authorization_id"],
        "authorization_raw_sha256": authorization_raw_sha256,
        "source_head": source_head,
        "generation": authorization["generation"],
        "state": "reserved",
    }
    _exclusive_bytes(claim, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return claim


def _require_synthetic_run_authorization(
    authorization: Mapping[str, Any] | None, material_contract_raw: bytes, source_head: str, contract: Mapping[str, Any],
) -> None:
    if not isinstance(authorization, Mapping):
        raise A0XRunnerError("CCP run requires an exact authorization")
    try:
        from .a0x_contract import EXECUTION_AUTHORIZATION_PROFILE, canonical_commitment
        canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE)
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XRunnerError("CCP run authorization is not schema-valid") from error
    if authorization.get("commitment_profile") != "a0x-execution-authorization-json-v2":
        raise A0XRunnerError("CCP run authorization profile is invalid")
    if authorization.get("authorization_status") != "authorized":
        raise A0XRunnerError("CCP run authorization status is invalid")
    if not isinstance(authorization.get("authorization_id"), str) or not authorization["authorization_id"]:
        raise A0XRunnerError("CCP run authorization identity is invalid")
    if not isinstance(authorization.get("attempt_id"), str) or not authorization["attempt_id"]:
        raise A0XRunnerError("CCP run authorization attempt is invalid")
    if authorization.get("material_contract_raw_sha256") != hashlib.sha256(material_contract_raw).hexdigest():
        raise A0XRunnerError("CCP run material contract binding is invalid")
    identity_fields = ("path", "source_commit", "qualified_source_tree", "sha256", "version")
    authorization_ccp = authorization.get("ccp")
    contract_ccp = contract.get("ccp")
    if not isinstance(authorization_ccp, Mapping) or not isinstance(contract_ccp, Mapping):
        raise A0XRunnerError("CCP run CCP scope is invalid")
    if authorization.get("source_head") != source_head or any(authorization_ccp.get(field) != contract_ccp.get(field) for field in identity_fields):
        raise A0XRunnerError("CCP run source or CCP scope is invalid")
    if authorization.get("max_guard_exec_count") != 1:
        raise A0XRunnerError("CCP guard execution count is invalid")
    if not isinstance(authorization.get("qualification_receipt_raw_sha256"), str) or not _SHA256.fullmatch(authorization["qualification_receipt_raw_sha256"]):
        raise A0XRunnerError("CCP qualifying receipt binding is invalid")
    if not isinstance(authorization.get("guard_exec_argv_commitment"), str) or not _SHA256.fullmatch(authorization["guard_exec_argv_commitment"]):
        raise A0XRunnerError("CCP guard argv commitment is invalid")


def _claim_payload(pair: PairBinding, chain: Mapping[str, Any], authorization: Mapping[str, Any]) -> dict[str, Any]:
    """Build and validate the exact durable reservation record before writing it."""
    payload = {
        "artifact_class": "a0x-attempt-claim", "claim_version": "a0x-attempt-claim-v1",
        "pair_binding": pair.as_mapping(), "authorization_chain": dict(chain),
        "authorization_id": authorization.get("authorization_id"), "attempt_id": authorization.get("attempt_id"),
        "material_contract_raw_sha256": authorization.get("material_contract_raw_sha256"), "state": "reserved",
    }
    _validate_claim_payload(payload)
    return payload


def _validate_claim_payload(payload: Mapping[str, Any]) -> None:
    try:
        PairBinding.from_mapping(payload["pair_binding"])
        validate_authorization_chain(payload["authorization_chain"])
        if validate(payload, _read_schema(_REPOSITORY_ROOT / "schemas/a0x-attempt-claim.schema.json")):
            raise A0XRunnerError("attempt claim is not schema-valid")
    except (A0XContractError, A0XRunnerError, KeyError, TypeError, ValueError) as error:
        raise A0XRunnerError("attempt claim is invalid") from error


def run_a0x_guarded_pair(
    *, root: str | Path, dossier_path: str | Path, authorization_path: str | Path,
    material_contract_raw: bytes, executor: CcpExecutor, source_head: str,
    dependencies: A0XRunnerDependencies, attempt_claim_path: str | Path,
    source_head_probe: Callable[[], str] | None = None,
    qualification_receipt_probe: Callable[[], bytes] | None = None,
) -> dict[str, Any]:
    """One injected CCP review/run guard followed by one injected lifecycle.

    This coordinator has no production executor; a real one can be supplied
    only by the separately authorized material boundary. It deliberately does
    not offer a claim-free or preflight-free fallback.
    """
    repository = Path(root).resolve()
    contract = strict_json_object(material_contract_raw)
    _validate_policy_binding(repository, contract)
    authorization_source = Path(authorization_path)
    authorization, authorization_raw = _read_json_document_with_raw(authorization_source, "authorization")
    authorization_raw_sha256 = hashlib.sha256(authorization_raw).hexdigest()
    if qualification_receipt_probe is None:
        raise A0XRunnerError("qualifying receipt probe is required")
    ccp_observation = _run_ccp_preflight(
        contract=contract, material_contract_raw=material_contract_raw, executor=executor,
        source_head=source_head,
    )
    if executor.review_dry_run(ccp_observation) is not True:
        raise A0XRunnerError("CCP dry-run review was rejected")
    if source_head_probe is None:
        raise A0XRunnerError("live source HEAD probe is required after CCP review")
    current_source_head = source_head_probe()
    if current_source_head != source_head or not _REVISION.fullmatch(current_source_head):
        raise A0XRunnerError("source HEAD drifted after CCP review")
    _validate_policy_binding(repository, contract)
    authorization, reread_authorization_raw = _read_json_document_with_raw(authorization_source, "authorization")
    if hashlib.sha256(reread_authorization_raw).hexdigest() != authorization_raw_sha256:
        raise A0XRunnerError("authorization bytes drifted after CCP review")
    dossier = _read_json_document(Path(dossier_path), "dossier")
    material_contract_raw_sha256 = hashlib.sha256(material_contract_raw).hexdigest()
    if dossier.get("material_contract_raw_sha256") != material_contract_raw_sha256 or authorization.get("material_contract_raw_sha256") != material_contract_raw_sha256:
        raise A0XRunnerError("dossier, authorization, and live material contract must have one raw hash")
    try:
        pair = PairBinding.from_mapping(dossier["pair_binding"])
        chain = _authorization_chain(dossier, authorization)
        assert_authorization_chain(dossier, authorization, [{"pair_binding": pair.as_mapping(), "authorization_chain": chain}])
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XRunnerError("dossier and authorization chain drifted after CCP review") from error
    output = _repository_output(repository, pair)
    if output.exists() or output.is_symlink() or any(parent.is_symlink() for parent in output.parents if parent != repository):
        raise A0XRunnerError("pair output is not empty")
    _require_synthetic_run_authorization(authorization, material_contract_raw, source_head, contract)
    qualifying_receipt_raw = qualification_receipt_probe()
    if not isinstance(qualifying_receipt_raw, bytes) or hashlib.sha256(qualifying_receipt_raw).hexdigest() != authorization["qualification_receipt_raw_sha256"]:
        raise A0XRunnerError("qualifying receipt drifted after CCP review")
    try:
        qualifying_envelope = strict_json_object(qualifying_receipt_raw)
        qualifying_generation = qualifying_envelope["receipt"]["run"]["generation"]
    except (A0XContractError, KeyError, TypeError) as error:
        raise A0XRunnerError("qualifying receipt is not an authentic Matrix envelope") from error
    validate_matrix_qualification_receipt(
        qualifying_receipt_raw, contract=contract, source_head=source_head, generation=qualifying_generation,
    )
    claim = reserve_attempt_claim(attempt_claim_path, _claim_payload(pair, chain, authorization))
    pre_run = _build_pre_run_observation(pair, chain, authorization, source_head, material_contract_raw, contract, ccp_observation, claim)
    pre_run_raw = json.dumps(pre_run, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if validate(pre_run, _read_schema(_REPOSITORY_ROOT / "schemas/a0x-ccp-observation.schema.json")):
        raise A0XRunnerError("pre-run CCP observation is not schema-valid")
    pre_run_path = claim.parent / "pre-run-observation.json"
    _exclusive_bytes(pre_run_path, pre_run_raw)
    pre_run_hash = hashlib.sha256(pre_run_raw).hexdigest()
    try:
        pre_run_relative_path = pre_run_path.resolve(strict=True).relative_to(repository.resolve(strict=True)).as_posix()
    except (OSError, ValueError) as error:
        raise A0XRunnerError("pre-run observation path must be repository-relative") from error
    run_trace, result = _run_once(contract, executor, authorization["guard_exec_argv_commitment"], lambda: _run_injected_lifecycle(pair=pair, chain=chain, dependencies=dependencies,
        attempt_claim_path=claim, dossier=dossier, authorization=authorization, claim_reserved=True,
        pre_run_context={"ccp_observation_path": pre_run_relative_path, "ccp_observation_raw_sha256": pre_run_hash, "source_head": source_head, "material_contract_raw_sha256": hashlib.sha256(material_contract_raw).hexdigest()}))
    if result is None:
        _persist_guard_recovery(claim, run_trace, pre_run_hash)
        raise A0XRunnerError(f"CCP guard exec terminal classification: {run_trace['state']['guard_exit_classification']}")
    final_observation = {**pre_run, "pre_run_observation": pre_run, "pre_run_observation_sha256": pre_run_hash, "run_count": 1, "run_record": run_trace}
    if validate(final_observation, _read_schema(_REPOSITORY_ROOT / "schemas/a0x-ccp-observation.schema.json")):
        raise A0XRunnerError("final CCP observation is not schema-valid")
    final_observation_path = claim.parent / "final-observation.json"
    _exclusive_bytes(final_observation_path, json.dumps(final_observation, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    return {**result, "ccp_observation": final_observation, "ccp_observation_path": str(final_observation_path)}


def _persist_guard_recovery(claim: Path, run_trace: Mapping[str, Any], pre_run_observation_sha256: str) -> Path:
    """Seal non-scientific guard termination after a reserved one-shot attempt."""
    state = run_trace.get("state")
    if not isinstance(state, Mapping):
        raise A0XRunnerError("guard recovery state is malformed")
    recovery = {
        "artifact_class": "a0x-guard-recovery-observation",
        "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest(),
        "pre_run_observation_sha256": pre_run_observation_sha256,
        "guard_exit_classification": state.get("guard_exit_classification"),
        "exit_code": run_trace.get("exit_code"),
        "scientific_status": "not_interpretable",
        "retry_permitted": False,
    }
    path = claim.parent / "guard-recovery-observation.json"
    _exclusive_bytes(path, json.dumps(recovery, sort_keys=True, separators=(",", ":")).encode())
    return path


def _exclusive_bytes(path: Path, raw: bytes) -> None:
    if os.path.lexists(path):
        raise A0XRunnerError("pre-run observation already exists")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    _fsync_directory(path.parent)


def _validate_policy_binding(repository: Path, contract: Mapping[str, Any]) -> None:
    ccp = contract.get("ccp")
    if not isinstance(ccp, Mapping):
        raise A0XRunnerError("material configuration binding is invalid")
    for name in ("matrix_config_binding", "matrix_policy_binding"):
        binding = ccp.get(name)
        if not isinstance(binding, Mapping):
            raise A0XRunnerError("material configuration binding is invalid")
        path = repository / str(binding.get("path", ""))
        if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != binding.get("raw_sha256"):
            raise A0XRunnerError("material configuration raw bytes drifted or are unavailable")


def _build_pre_run_observation(pair: PairBinding, chain: Mapping[str, Any], authorization: Mapping[str, Any], source_head: str, material_raw: bytes, contract: Mapping[str, Any], preflight: Mapping[str, Any], claim: Path) -> dict[str, Any]:
    """Build the complete privacy-minimized pre-run record before the callback."""
    commands = list(preflight["commands"])
    by_command = {item["command"]: item for item in commands}
    ccp = contract["ccp"]
    return {
        "artifact_class": "a0x-ccp-observation", "empirical": True, "scientific_status": "exploratory",
        "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
        "pair_binding": pair.as_mapping(), "authorization_chain": dict(chain), "read_counter": 0,
        "admission_status": "not_requested",
        "binary": {"path": ccp["path"], "source_commit": ccp["source_commit"], "sha256": ccp["sha256"], "version_output": ccp["version"] + "\n"},
        "resource": dict(preflight["resource"]), "admission": dict(preflight["admission"]),
        "resource_raw_path": "resource-status.raw.json", "resource_raw_sha256": by_command["resource status --json"]["raw_sha256"], "resource_raw_bytes": by_command["resource status --json"]["raw_bytes"],
        "admission_raw_path": "admission-status.raw.json", "admission_raw_sha256": by_command["admission status --json"]["raw_sha256"], "admission_raw_bytes": by_command["admission status --json"]["raw_bytes"],
        "source_head": source_head, "material_contract_raw_sha256": hashlib.sha256(material_raw).hexdigest(),
        "policy_raw_sha256": ccp["matrix_policy_binding"]["raw_sha256"], "ccp_trace": commands,
        "dry_run_reviewed": True, "claim_identity": claim.as_posix(), "claim_sha256": hashlib.sha256(claim.read_bytes()).hexdigest(),
        "guard_exec_argv_commitment": authorization["guard_exec_argv_commitment"],
        "run_count": 0,
    }


def _run_injected_lifecycle(
    *, pair: PairBinding, chain: Mapping[str, Any], dependencies: A0XRunnerDependencies,
    attempt_claim_path: str | Path, dossier: Mapping[str, Any], authorization: Mapping[str, Any], claim_reserved: bool = False, pre_run_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute exactly one dependency-injected lifecycle with no fallback path."""
    if not _GUARD_EXEC_ACTIVE.get():
        raise A0XRunnerError("claimed lifecycle is reachable only inside guard exec")
    claim_payload = _claim_payload(pair, chain, authorization)
    if not claim_reserved:
        reserve_attempt_claim(attempt_claim_path, claim_payload)
    model: Any | None = None
    release_attempted = False
    stage = "static_preflight"
    try:
        if pre_run_context is None:
            raise A0XRunnerError("claimed lifecycle requires a persisted pre-run context")
        dependencies.static_preflight(pre_run_context)
        stage = "tokenizer_construction"
        tokenizer = dependencies.tokenizer_factory()
        stage = "model_construction"
        model = dependencies.model_factory(tokenizer)
        stage = "activation"
        activation = dependencies.activation(model)
        stage = "activation_sealing"
        sealed_activation = dependencies.activation_sealer(activation)
        stage = "sealed_target_capability"
        target = dependencies.target_capability_factory(sealed_activation)
        stage = "frozen_analysis"
        analysis = dependencies.analysis(target)
        stage = "terminal_package"
        package = dependencies.package_builder(analysis)
        if not isinstance(package, Path):
            raise A0XRunnerError("terminal package builder did not return a path")
        stage = "independent_package_verification"
        dependencies.package_verifier(package)
        stage = "protected_tree_postflight"
        dependencies.protected_tree_postflight(package)
        stage = "model_release"
        release_attempted = True
        dependencies.release_model(model)
        model = None
        return {
            "status": "completed", "pair_binding": pair.as_mapping(),
            "authorization_chain": dict(chain), "package_path": str(package),
            "attempt_claim_path": str(attempt_claim_path), "dossier_status": dossier.get("dossier_status"),
        }
    except BaseException as error:
        try:
            terminal = dependencies.failure_sealer(stage, error, pair, chain)
        except BaseException as sealing_error:
            raise A0XRunnerError("could not seal first terminal lifecycle outcome") from sealing_error
        if not isinstance(terminal, Mapping):
            raise A0XRunnerError("failure sealer did not return a terminal mapping")
        if model is not None and not release_attempted:
            release_attempted = True
            try:
                dependencies.release_model(model)
            except BaseException:
                # The first sealed outcome remains authoritative. Cleanup
                # uncertainty belongs in its terminal evidence; it must never
                # replace the first failure or trigger a retry here.
                pass
        if isinstance(error, KeyboardInterrupt):
            raise
        return dict(terminal)


def verify_a0x_implementation(root: str | Path) -> dict[str, Any]:
    """Validate the no-model A0X implementation surface, without inference."""
    repository = Path(root).resolve()
    if not repository.is_dir() or repository.is_symlink():
        raise A0XRunnerError("repository root is unavailable")
    schema_paths = sorted((repository / "schemas").glob(f"{_SCHEMA_PREFIX}*.schema.json"))
    if not schema_paths:
        raise A0XRunnerError("A0X schemas are unavailable")
    for path in schema_paths:
        _read_schema(path)
    material_contract_path = repository / "experiments/a0x-six-model/material-execution-contract.json"
    material_contract = _read_json_document(material_contract_path, "A0X material contract")
    if validate(material_contract, _read_schema(repository / "schemas/a0x-material-execution-contract.schema.json")):
        raise A0XRunnerError("A0X material contract fails its schema")
    cards = load_registry(repository / "experiments/a0x-six-model/model-registry.json")
    if len(cards) != 6:
        raise A0XRunnerError("A0X model registry must contain exactly six cards")
    for card in cards:
        verify_card_sources(repository, card)
        for leg in (Leg.A0, Leg.R1):
            bound = compute_dense_bound(
                leg,
                cases=48,
                hidden_width=card.hidden_size,
            )
            if bound.total_bytes > bound.cap_bytes:
                raise A0XRunnerError("A0X frozen cap calculation is invalid")
    _validate_selection_manifest(repository)
    _validate_protected_tree(repository, "protected-a0-tree.json")
    _validate_protected_tree(repository, "protected-a0r1-tree.json")
    _validate_fixed_surface(repository)
    return {
        "artifact_class": "a0x-synthetic-implementation-receipt",
        "phase": "synthetic_implementation",
        "schema_count": len(schema_paths),
        "model_card_count": len(cards),
        "fixed_material_target_count": len(_MATERIAL_DOSSIERS),
        "material_contract_status": "schema_validated_only",
        "protocol_and_dossier_frozen": False,
        "model_loaded": False,
        "tokenizer_constructed": False,
        "sealed_target_content_reads": 0,
        "ccp_invoked": False,
    }


def verify_a0x_no_model(root: str | Path) -> dict[str, Any]:
    """Verify the complete frozen Task-11 package without material access."""

    repository = Path(root).resolve()
    synthetic = verify_a0x_implementation(repository)
    verify_a0x_dossier_inventory(repository)
    try:
        bindings = verify_frozen_legs(repository)
    except A0XFreezeError as error:
        raise A0XRunnerError("A0X frozen leg package drifted") from error
    cards = {card.model_key: card for card in load_registry(
        repository / "experiments/a0x-six-model/model-registry.json",
    )}
    dossier_schema = _read_schema(repository / "schemas/a0x-authorization-dossier.schema.json")
    material_path = repository / "experiments/a0x-six-model/material-execution-contract.json"
    material_sha256 = sha256_file(material_path)
    dossiers_by_leg: dict[Leg, list[dict[str, Any]]] = {Leg.A0: [], Leg.R1: []}
    observed_pairs: set[tuple[str, str]] = set()
    for (leg_name, model_key), relative in sorted(_PAIR_DOSSIERS.items()):
        dossier = _read_json_document(repository / relative, "A0X approval dossier")
        issues = validate(dossier, dossier_schema)
        if issues:
            raise A0XRunnerError(f"A0X approval dossier fails its schema: {relative}")
        if dossier.get("material_contract_raw_sha256") != material_sha256:
            raise A0XRunnerError("A0X dossier material contract binding drifted")
        if "authorization_status" in dossier or dossier.get("dossier_status") != "approval_requested":
            raise A0XRunnerError("A0X dossier improperly grants material execution")
        pair = PairBinding.from_mapping(dossier["pair_binding"])
        leg = Leg(leg_name)
        card = cards.get(model_key)
        if card is None:
            raise A0XRunnerError("A0X dossier names an unregistered model")
        expected_dense = compute_dense_bound(leg, cases=48, hidden_width=card.hidden_size)
        if (
            pair.leg is not leg
            or pair.model_key != model_key
            or pair.model_id != card.model_id
            or pair.revision != card.revision
            or pair.leg_freeze_sha256 != bindings[leg].leg_freeze_sha256
            or pair.dense_bound != expected_dense
        ):
            raise A0XRunnerError("A0X dossier pair binding drifted")
        expected_output = f"results/a0x/{leg.value}/{model_key}/{pair.run_id}"
        if pair.output_path != expected_output:
            raise A0XRunnerError("A0X dossier output path is not pair-isolated")
        if dossier.get("future_authorization_path") != f"{expected_output}/execution-authorization.json":
            raise A0XRunnerError("A0X dossier authorization path is not pair-isolated")
        observed_pairs.add((leg.value, model_key))
        dossiers_by_leg[leg].append(dossier)
    if observed_pairs != set(_PAIR_DOSSIERS):
        raise A0XRunnerError("A0X dossier Cartesian product is incomplete")
    for leg, dossiers in dossiers_by_leg.items():
        try:
            assert_leg_freeze_binding(bindings[leg], dossiers)
        except A0XContractError as error:
            raise A0XRunnerError("A0X dossiers do not share their exact leg freeze") from error
    return {
        **synthetic,
        "artifact_class": "a0x-no-model-verification-receipt",
        "phase": "frozen_no_model",
        "frozen_leg_count": len(bindings),
        "approval_requested_dossier_count": len(observed_pairs),
        "protocol_and_dossier_frozen": True,
        "remote_mutations": False,
    }


def _seal_failure(pair: PairBinding, chain: Mapping[str, Any], terminal_path: Path, error: Exception) -> dict[str, Any]:
    try:
        return seal_terminal_attempt(
            state=AttemptState.ACTIVATION, status="failed", pair_binding=pair.as_mapping(),
            authorization_chain=chain, terminal_path=terminal_path,
        )
    except Exception as sealing_error:
        raise A0XRunnerError("could not seal first terminal attempt") from sealing_error


def _authorization_chain(dossier: Mapping[str, Any], authorization: Mapping[str, Any]) -> dict[str, Any]:
    from .a0x_contract import APPROVAL_DOSSIER_PROFILE, EXECUTION_AUTHORIZATION_PROFILE, canonical_commitment

    chain = {
        "dossier_commitment": canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping(),
        "authorization_commitment": canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE).as_mapping(),
    }
    return validate_authorization_chain(chain)


def _repository_output(repository: Path, pair: PairBinding) -> Path:
    relative = Path(pair.output_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise A0XRunnerError("pair output path is unsafe")
    output = repository / relative
    if not output.resolve().is_relative_to(repository):
        raise A0XRunnerError("pair output path escapes repository")
    return output


def _read_json_document(path: Path, label: str) -> dict[str, Any]:
    return _read_json_document_with_raw(path, label)[0]


def _read_json_document_with_raw(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = strict_json_object(raw)
    except (OSError, A0XContractError) as error:
        raise A0XRunnerError(f"{label} is unavailable or malformed") from error
    return value, raw


def _validate_selection_manifest(repository: Path) -> None:
    path = repository / "experiments/a0x-six-model/a0-selection-manifest.json"
    value = _read_json_document(path, "A0X selection manifest")
    if validate(value, _read_schema(repository / "schemas/a0x-selection-manifest.schema.json")):
        raise A0XRunnerError("A0X selection manifest fails its schema")
    if value.get("target_content_reads") != 0:
        raise A0XRunnerError("synthetic verification cannot contain target reads")
    try:
        verify_a0_selection_manifest(
            value,
            cases_path=repository / "data/a0/cases.jsonl",
            corpus_manifest_path=repository / "data/a0/manifest.json",
        )
    except A0XFreezeError as error:
        raise A0XRunnerError("A0X selection manifest binding drifted") from error


def _validate_protected_tree(repository: Path, filename: str) -> None:
    path = repository / "experiments/a0x-six-model" / filename
    value = _read_json_document(path, "A0X protected tree")
    if validate(value, _read_schema(repository / "schemas/a0x-protected-tree.schema.json")):
        raise A0XRunnerError("A0X protected tree fails its schema")
    try:
        verify_protected_tree_metadata_only(repository, value)
    except A0XFreezeError as error:
        raise A0XRunnerError("A0X protected tree binding drifted") from error


def _validate_fixed_surface(repository: Path) -> None:
    required = (
        "src/latent_triz/a0x_runner.py", "scripts/a0x_contract_check.py", "scripts/a0x_material.py",
        "tests/test_a0x_runner.py", "tests/test_a0x_contract_check.py", "tests/test_a0x_material.py",
    )
    for relative in required:
        if not (repository / relative).is_file():
            raise A0XRunnerError(f"A0X synthetic interface is missing: {relative}")
    makefile = (repository / "Makefile").read_text(encoding="utf-8")
    recipes = _parse_make_recipes(makefile)
    expected_labels: set[str] = set()
    for target, dossier in _MATERIAL_DOSSIERS.items():
        label = f"a0x-material-{target[0]}-{target[1]}"
        expected_labels.add(label)
        recipe = recipes.get(label)
        expected_recipe = f"PYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier {dossier}"
        if recipe is None or len(recipe) != 1 or recipe[0] != expected_recipe:
            raise A0XRunnerError("fixed A0X material target mapping is incomplete")
    observed = {name for name in recipes if name.startswith("a0x-material-")}
    if observed != expected_labels:
        raise A0XRunnerError("fixed A0X material target mapping is not bijective")
    synthetic = recipes.get("a0x-synthetic-verify", [])
    if len(synthetic) != 3:
        raise A0XRunnerError("synthetic aggregate structure is invalid")
    discovered_a0x_tests = {
        f"tests.{path.stem}"
        for path in (repository / "tests").glob("test_a0x_*.py")
    }
    aggregate_text = "\n".join(synthetic)
    if not discovered_a0x_tests or any(module not in aggregate_text for module in discovered_a0x_tests):
        raise A0XRunnerError("synthetic aggregate must include every A0X test module")
    scan_paths = [repository / "scripts/repository_check.py", repository / "src/latent_triz/cli.py"]
    workflows = repository / ".github/workflows"
    if workflows.is_dir():
        scan_paths.extend(sorted(workflows.rglob("*.y*ml")))
    for path in scan_paths:
        text = path.read_text(encoding="utf-8")
        if path.name == "cli.py" and "a0x-synthetic-verify" not in text:
            raise A0XRunnerError("A0X synthetic verifier is not reachable from the CLI")
        if "a0x-material-" in text:
            raise A0XRunnerError("automated surface must not invoke A0X material targets")


def _parse_make_recipes(text: str) -> dict[str, list[str]]:
    """Parse the limited target/recipe grammar used by the tracked Makefile."""
    recipes: dict[str, list[str]] = {}
    active: str | None = None
    for line in text.splitlines():
        if line and not line.startswith(("\t", " ")) and ":" in line and not line.startswith("#"):
            target, _, _rest = line.partition(":")
            active = target.strip() if target.strip() else None
            if active is not None:
                recipes.setdefault(active, [])
        elif line.startswith("\t") and active is not None:
            recipes[active].append(line[1:])
    return recipes


def _read_schema(path: Path) -> dict[str, Any]:
    """Schemas are JSON Schema documents and may contain numeric literals."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XRunnerError("A0X schema is unavailable or malformed") from error
    if not isinstance(value, dict):
        raise A0XRunnerError("A0X schema must be an object")
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        # The minimal local interpreter intentionally has no third-party
        # validator. CI invokes the complete Draft validator; this guard still
        # rejects a non-Draft schema before any synthetic verification.
        if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise A0XRunnerError("A0X schema declares the wrong Draft version")
    else:
        try:
            Draft202012Validator.check_schema(value)
        except Exception as error:
            raise A0XRunnerError("A0X schema fails Draft 2020-12 meta-validation") from error
    return value


__all__ = ["A0XRunnerDependencies", "A0XRunnerError", "planned_material_dossiers", "reserve_attempt_claim", "run_a0x_guarded_pair", "verify_a0x_implementation"]
