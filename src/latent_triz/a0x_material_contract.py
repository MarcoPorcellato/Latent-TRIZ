"""Pure, fail-closed contracts for the A0X material runtime inlet.

This module deliberately does not spawn processes, load model libraries, read
sealed targets, or touch the runtime inlet.  It only makes the data handed to
the later launcher reconstructable and independently checkable.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from latent_triz.a0x_contract import A0XContractError, PairBinding
from latent_triz.validator import validate


_ROOT = Path(__file__).resolve().parents[2]
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_RUNTIME_PATH = re.compile(r"^\.a0x-runtime/(?:authorizations|launches|claims|observations|qualification|bin)/[A-Za-z0-9._/-]+$")
_RUN_ID = re.compile(r"^[A-Za-z0-9._-]+$")
_ENVIRONMENT_TEMPLATE = (
    "HF_HUB_OFFLINE=1",
    "TRANSFORMERS_OFFLINE=1",
    "HF_DATASETS_OFFLINE=1",
    "TOKENIZERS_PARALLELISM=false",
    "PYTHONNOUSERSITE=1",
)

OUTER_TIMEOUT_SECONDS = 3_600
INTERNAL_BUDGET_SECONDS = 3_300
CLEANUP_MARGIN_SECONDS = 300
ADMISSION_TIMEOUT_SECONDS = 300
MEMORY_LIMIT_BYTES = 8_589_934_592
GUARD_LAUNCH_PROFILE = "a0x-guard-launch-v2"
QUALIFICATION_EVIDENCE_PROFILE = "a0x-qualification-evidence-v1"
DESCRIPTOR_PROFILE = "a0x-material-child-descriptor-v2"
MATERIAL_CONTRACT_PATH = "experiments/a0x-six-model/material-execution-contract.json"


@dataclass(frozen=True)
class TimeoutEnvelope:
    """The uniform execution envelope shared by every A0X pair."""

    outer_timeout_seconds: int
    internal_budget_seconds: int
    cleanup_margin_seconds: int
    admission_timeout_seconds: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TimeoutEnvelope":
        expected = {
            "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
            "internal_budget_seconds": INTERNAL_BUDGET_SECONDS,
            "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
            "admission_timeout_seconds": ADMISSION_TIMEOUT_SECONDS,
        }
        if not isinstance(value, Mapping) or set(value) != set(expected):
            raise A0XContractError("timeout envelope fields do not match the frozen profile")
        for key, expected_value in expected.items():
            actual = value.get(key)
            if not isinstance(actual, int) or isinstance(actual, bool) or actual != expected_value:
                raise A0XContractError("timeout envelope does not match the uniform A0X limits")
        return cls(**expected)

    def as_mapping(self) -> dict[str, int]:
        return {
            "outer_timeout_seconds": self.outer_timeout_seconds,
            "internal_budget_seconds": self.internal_budget_seconds,
            "cleanup_margin_seconds": self.cleanup_margin_seconds,
            "admission_timeout_seconds": self.admission_timeout_seconds,
        }


@dataclass(frozen=True)
class RuntimePaths:
    """Pair-derived, Git-ignored locations for mutable runtime inputs."""

    authorization_path: str
    launch_descriptor_path: str
    claim_path: str
    observation_directory: str
    qualification_receipt_path: str | None


def derive_runtime_paths(
    pair: PairBinding | Mapping[str, Any], *, source_head: str | None = None,
) -> RuntimePaths:
    """Derive every mutable path from one frozen pair binding.

    Nothing is written.  The result path is intentionally not used as a parent
    so a durable authorization cannot pre-create and block an immutable output.
    """
    binding = pair if isinstance(pair, PairBinding) else PairBinding.from_mapping(pair)
    _validate_runtime_segment(binding.run_id, "run id")
    base = f".a0x-runtime/{{kind}}/{binding.leg.value}/{binding.model_key}/{binding.run_id}"
    qualification = None
    if source_head is not None:
        _require_revision(source_head, "source head")
        qualification = f".a0x-runtime/qualification/{source_head}/receipt.json"
    return RuntimePaths(
        authorization_path=base.format(kind="authorizations") + ".json",
        launch_descriptor_path=base.format(kind="launches") + ".json",
        claim_path=base.format(kind="claims") + ".json",
        observation_directory=base.format(kind="observations") + "/",
        qualification_receipt_path=qualification,
    )


def validate_dossier_authorization_path(
    pair: PairBinding | Mapping[str, Any], path: str,
) -> str:
    """Require the exact pair-derived authorization inlet path."""
    expected = derive_runtime_paths(pair).authorization_path
    if not isinstance(path, str) or path != expected:
        raise A0XContractError("authorization inlet path does not match the frozen pair binding")
    return path


def authorization_reference(value: Any, pair: PairBinding) -> str:
    """Require the descriptor's authorization reference to be pair-derived."""
    expected = derive_runtime_paths(pair).authorization_path
    if not isinstance(value, Mapping) or set(value) != {"role", "path"}:
        raise A0XContractError("authorization reference shape is invalid")
    if value.get("role") != "authorization" or value.get("path") != expected:
        raise A0XContractError("authorization reference is not pair-derived")
    return expected


def material_contract_binding(value: Any) -> tuple[str, str]:
    """Validate the byte-bound public material-contract entry."""
    if not isinstance(value, Mapping) or set(value) != {"role", "path", "sha256"}:
        raise A0XContractError("material contract binding shape is invalid")
    if value.get("role") != "material_contract" or value.get("path") != MATERIAL_CONTRACT_PATH:
        raise A0XContractError("material contract binding path is invalid")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise A0XContractError("material contract binding hash is invalid")
    return MATERIAL_CONTRACT_PATH, digest


@dataclass(frozen=True)
class A0XGuardLaunch:
    """A public-safe, shell-free `commit-ci-preflight guard exec` template."""

    launch_profile: str
    ccp_role: str
    ccp_sha256: str
    python_role: str
    python_sha256: str
    cwd_kind: str
    source_head: str
    child_script_path: str
    child_script_sha256: str
    launch_descriptor_path: str
    launch_descriptor_sha256: str
    environment_template: tuple[str, ...]
    resource: tuple[tuple[str, str | int], ...]
    timeouts: TimeoutEnvelope
    argv_template: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "A0XGuardLaunch":
        expected_keys = {
            "launch_profile", "ccp", "python", "cwd_kind", "source_head", "child_script",
            "launch_descriptor", "environment_template", "resource", "timeouts", "argv_template",
        }
        if not isinstance(value, Mapping) or set(value) != expected_keys:
            raise A0XContractError("guard launch fields do not match the frozen profile")
        if value["launch_profile"] != GUARD_LAUNCH_PROFILE:
            raise A0XContractError("guard launch profile is unsupported")
        ccp_role, ccp_sha256 = _runtime_role(value.get("ccp"), "CCP", "ccp")
        python_role, python_sha256 = _runtime_role(value.get("python"), "Python", "python")
        cwd_kind = value.get("cwd_kind")
        if cwd_kind != "repository_root":
            raise A0XContractError("guard launch cwd kind must identify the repository root")
        source_head = value.get("source_head")
        _require_revision(source_head, "source head")
        child_script_path, child_script_sha256 = _child_script(value.get("child_script"))
        descriptor_path, descriptor_sha256 = _launch_descriptor(value.get("launch_descriptor"))
        if not descriptor_path.startswith(".a0x-runtime/launches/"):
            raise A0XContractError("guard launch descriptor is outside the runtime inlet")
        environment = _environment(value.get("environment_template"))
        resource = _resource(value.get("resource"))
        timeouts = TimeoutEnvelope.from_mapping(_mapping(value, "timeouts", "guard launch"))
        argv = _argv_template(value.get("argv_template"))
        expected_argv = _build_guard_argv_template(
            resource=dict(resource),
            timeouts=timeouts,
        )
        if argv != expected_argv:
            raise A0XContractError("guard launch argv template does not match the canonical shell-free command")
        return cls(
            launch_profile=GUARD_LAUNCH_PROFILE,
            ccp_role=ccp_role,
            ccp_sha256=ccp_sha256,
            python_role=python_role,
            python_sha256=python_sha256,
            cwd_kind=cwd_kind,
            source_head=source_head,
            child_script_path=child_script_path,
            child_script_sha256=child_script_sha256,
            launch_descriptor_path=descriptor_path,
            launch_descriptor_sha256=descriptor_sha256,
            environment_template=environment,
            resource=resource,
            timeouts=timeouts,
            argv_template=argv,
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "launch_profile": self.launch_profile,
            "ccp": {"role": self.ccp_role, "sha256": self.ccp_sha256},
            "python": {"role": self.python_role, "sha256": self.python_sha256},
            "cwd_kind": self.cwd_kind,
            "source_head": self.source_head,
            "child_script": {"role": "child", "path": self.child_script_path, "sha256": self.child_script_sha256},
            "launch_descriptor": {"role": "descriptor", "path": self.launch_descriptor_path, "sha256": self.launch_descriptor_sha256},
            "environment_template": list(self.environment_template),
            "resource": dict(self.resource),
            "timeouts": self.timeouts.as_mapping(),
            "argv_template": list(self.argv_template),
        }


def canonical_guard_commitment(value: A0XGuardLaunch | Mapping[str, Any]) -> str:
    """Return the canonical SHA-256 commitment of a complete guard launch."""
    launch = value if isinstance(value, A0XGuardLaunch) else A0XGuardLaunch.from_mapping(value)
    raw = json.dumps(
        launch.as_mapping(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_guard_launch_pair_binding(
    pair: PairBinding | Mapping[str, Any], launch: A0XGuardLaunch | Mapping[str, Any],
) -> None:
    """Bind a public guard template's descriptor to one frozen pair only."""
    binding = pair if isinstance(pair, PairBinding) else PairBinding.from_mapping(pair)
    parsed = launch if isinstance(launch, A0XGuardLaunch) else A0XGuardLaunch.from_mapping(launch)
    expected = derive_runtime_paths(binding).launch_descriptor_path
    if parsed.launch_descriptor_path != expected:
        raise A0XContractError("guard launch descriptor does not match the frozen pair binding")


def validate_qualification_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate public-safe CCP receipt identity and raw-byte hash bindings.

    CCP's semantic ``receipt_id`` and the SHA-256 of the serialized receipt are
    distinct commitments.  The later verifier checks each independently
    against the recovered public receipt; they must not be equated here.
    """
    if not isinstance(value, Mapping):
        raise A0XContractError("qualification evidence must be an object")
    schema = _read_schema("a0x-qualification-evidence.schema.json")
    issues = validate(dict(value), schema)
    if issues:
        raise A0XContractError(f"qualification evidence schema rejected input: {issues[0].message}")
    evidence = dict(value)
    public = evidence["public_evidence"]
    if public["branch"] != f"ccp-evidence/{evidence['qualified_source_head']}":
        raise A0XContractError("qualification evidence branch is not bound to source HEAD")
    if public["path"] != ".ccp/receipt.json":
        raise A0XContractError("qualification evidence path is not the public receipt path")
    if _contains_local_or_private_value(evidence):
        raise A0XContractError("qualification evidence contains a local path or private field")
    return evidence


def _build_guard_argv_template(
    *, resource: Mapping[str, str | int], timeouts: TimeoutEnvelope,
) -> tuple[str, ...]:
    return (
        "{CCP}", "guard", "exec",
        "--admission-timeout-seconds", str(timeouts.admission_timeout_seconds),
        "--timeout-seconds", str(timeouts.outer_timeout_seconds),
        "--resource-profile", str(resource["profile"]),
        "--resource-workload-family", str(resource["workload_family"]),
        "--resource-executor", str(resource["executor"]),
        "--resource-cache-state", str(resource["cache_state"]),
        "--resource-execution-mode", str(resource["execution_mode"]),
        "--resource-target-platform", str(resource["target_platform"]),
        "--resource-memory-limit-bytes", str(resource["memory_limit_bytes"]),
        "--", "{PYTHON}", "{CHILD}", "--launch-descriptor", "{DESCRIPTOR}",
    )


def _runtime_role(value: Any, label: str, expected_role: str) -> tuple[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"role", "sha256"}:
        raise A0XContractError(f"guard launch {label} role binding is incomplete")
    if value.get("role") != expected_role:
        raise A0XContractError(f"guard launch {label} role is unsupported")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise A0XContractError(f"guard launch {label} SHA-256 is invalid")
    return expected_role, digest


def _child_script(value: Any) -> tuple[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"role", "path", "sha256"} or value.get("role") != "child":
        raise A0XContractError("guard launch child script role binding is incomplete")
    path, digest = _file_binding({"path": value.get("path"), "sha256": value.get("sha256")}, "child script", absolute=False)
    if path != "scripts/a0x_material_child.py":
        raise A0XContractError("guard launch child script must be the fixed repository script")
    return path, digest


def _launch_descriptor(value: Any) -> tuple[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"role", "path", "sha256"} or value.get("role") != "descriptor":
        raise A0XContractError("guard launch descriptor role binding is incomplete")
    return _file_binding(
        {"path": value.get("path"), "sha256": value.get("sha256")},
        "launch descriptor",
        absolute=False,
    )


def _file_binding(value: Any, label: str, *, absolute: bool) -> tuple[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        raise A0XContractError(f"guard launch {label} binding is incomplete")
    path = value.get("path")
    if not isinstance(path, str) or not path:
        raise A0XContractError(f"guard launch {label} path is invalid")
    if absolute:
        if not path.startswith("/") or "\x00" in path:
            raise A0XContractError(f"guard launch {label} path must be absolute")
    elif (
        (not _RUNTIME_PATH.fullmatch(path) and path != "scripts/a0x_material_child.py")
        or any(segment in {".", ".."} for segment in path.split("/"))
        or path.startswith("/")
    ):
        raise A0XContractError(f"guard launch {label} path must be runtime-relative")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise A0XContractError(f"guard launch {label} SHA-256 is invalid")
    return path, digest


def _environment(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise A0XContractError("guard launch environment allowlist is invalid")
    if tuple(value) != _ENVIRONMENT_TEMPLATE:
        raise A0XContractError("guard launch environment template does not match the frozen profile")
    return _ENVIRONMENT_TEMPLATE


def _resource(value: Any) -> tuple[tuple[str, str | int], ...]:
    expected: dict[str, str | int] = {
        "profile": "a0x-material",
        "workload_family": "latent-triz-a0x-v1",
        "executor": "native",
        "cache_state": "warm",
        "execution_mode": "native",
        "target_platform": "macos-arm64",
        "memory_limit_bytes": MEMORY_LIMIT_BYTES,
    }
    if not isinstance(value, Mapping) or set(value) != set(expected) or dict(value) != expected:
        raise A0XContractError("guard launch resource labels do not match the frozen profile")
    return tuple(expected.items())


def _argv(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise A0XContractError("guard launch argv must be a non-empty string array")
    return tuple(value)


def _argv_template(value: Any) -> tuple[str, ...]:
    template = _argv(value)
    allowed_tokens = {"{CCP}", "{PYTHON}", "{CHILD}", "{DESCRIPTOR}"}
    found_tokens = {item for item in template if item.startswith("{") or item.endswith("}")}
    if found_tokens != allowed_tokens:
        raise A0XContractError("guard launch argv template contains undeclared or missing tokens")
    return template


def _mapping(value: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    child = value.get(key)
    if not isinstance(child, Mapping):
        raise A0XContractError(f"{label} {key} must be an object")
    return child


def _require_revision(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise A0XContractError(f"{label} must be a full Git revision")
    return value


def _validate_runtime_segment(value: str, label: str) -> None:
    if not _RUN_ID.fullmatch(value):
        raise A0XContractError(f"{label} is unsafe for the runtime inlet")


def _read_schema(name: str) -> dict[str, Any]:
    try:
        value = json.loads((_ROOT / "schemas" / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XContractError("qualification evidence schema is unavailable") from error
    if not isinstance(value, dict):
        raise A0XContractError("qualification evidence schema is malformed")
    return value


def _contains_local_or_private_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in {"raw_log_path", "local_path", "environment", "container_id", "username", "secret"}
            or _contains_local_or_private_value(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_local_or_private_value(child) for child in value)
    if isinstance(value, str):
        lowered = value.lower()
        return value.startswith(("/Users/", "/private/", "/tmp/", "~")) or "file://" in lowered
    return False
