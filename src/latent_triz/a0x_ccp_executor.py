"""Fixed, shell-free CCP guard launcher for one A0X dossier.

This is an execution *adapter*, not a scientific runner.  It deliberately
knows no model, tokenizer, target, or scoring API.  It resolves the public
``a0x-guard-launch-v2`` commitment through a Git-ignored local role mapping,
claims the one permitted outer attempt, and records a privacy-minimised
terminal observation for every outer process outcome.

All process execution is injected for tests.  The production adapter uses
``subprocess.Popen`` with ``shell=False`` and temporary-file capture so output
cannot become an unbounded in-memory object.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import subprocess
import threading
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any, Callable, Literal, Mapping, Protocol, Sequence

from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    VERTICAL_EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    Leg,
    PairBinding,
    canonical_commitment,
    sha256_file,
    strict_json_object,
)
from .a0x_material_contract import (
    A0XGuardLaunch,
    VerticalA0XGuardLaunch,
    ADMISSION_TIMEOUT_SECONDS,
    CLEANUP_MARGIN_SECONDS,
    INTERNAL_BUDGET_SECONDS,
    OUTER_TIMEOUT_SECONDS,
    derive_runtime_paths,
    validate_gate_a_evidence,
    validate_vertical_gate_a_evidence,
    validate_guard_launch_pair_binding,
    validate_qualification_evidence,
)
from .a0x_hosted_gate_a import canonical_json_bytes as hosted_gate_a_canonical_json_bytes
from .a0x_public_closure import A0XPublicClosureError, load_pre_execution_public_closure
from .a0x_runner import A0XRunnerError, planned_material_dossiers, vertical_slice_dossier_path
from .a0x_runtime_readiness import (
    A0XRuntimeReadinessError,
    runtime_readiness_path,
    validate_runtime_readiness_live,
)
from .a0x_vertical_slice import A0XVerticalSliceError, VerticalPackageBinding, load_vertical_runtime_package, load_vertical_slice
from .validator import validate


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_MAPPING_PROFILE = "a0x-runtime-role-mapping-v1"
_CHILD_TERMINAL_CLASS = "a0x-material-child-terminal"
_CAPTURE_LIMIT_BYTES = 65_536
_SUPERVISION_TIMEOUT_SECONDS = OUTER_TIMEOUT_SECONDS + CLEANUP_MARGIN_SECONDS
_PREFLIGHT_TIMEOUT_SECONDS = 30
_PREFLIGHT_CAPTURE_LIMIT_BYTES = 65_536
_ACTIVE_CCP_SHA256 = "45127a90f1adace54547ccb997d2a1914fe421e8062b51a9ddd09fd9d5538bc2"
_GATE_A_FILE_ORDER = (
    "manifest",
    "attestation_bundle",
    "trusted_root",
    "transport",
    "verification_receipt",
)


class A0XCcpExecutorError(RuntimeError):
    """The fixed material launcher rejected its execution boundary."""


def rehash_gate_a_evidence(
    *, repository_root: Path, evidence: Mapping[str, Any], source_head: str,
) -> dict[str, Path]:
    """Rehash the five current Gate-A files without provenance interpretation.

    This is deliberately a pure local file boundary: it neither invokes GitHub
    tooling nor compares the hosted verifier with the independent CCP producer.
    Each caller invokes it at its own material boundary, so a second call closes
    the interval between an earlier binding and a later side effect.
    """
    try:
        parsed = validate_gate_a_evidence(evidence)
    except A0XContractError as error:
        raise A0XCcpExecutorError("Gate A evidence is invalid") from error
    if parsed["source_head"] != source_head:
        raise A0XCcpExecutorError("Gate A evidence source HEAD differs from authorization")
    bindings: dict[str, Mapping[str, Any]] = dict(parsed["hosted_inputs"])
    bindings["verification_receipt"] = parsed["verification_receipt"]
    if tuple(sorted(bindings)) != tuple(sorted(_GATE_A_FILE_ORDER)):
        raise A0XCcpExecutorError("Gate A evidence file set is invalid")
    files: dict[str, Path] = {}
    for role in _GATE_A_FILE_ORDER:
        binding = bindings[role]
        path = _unique_repository_file(repository_root, binding.get("path"), f"Gate A {role}")
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise A0XCcpExecutorError(f"Gate A {role} bytes are unavailable") from error
        if _sha256_bytes(raw) != binding.get("sha256"):
            raise A0XCcpExecutorError(f"Gate A {role} raw SHA-256 differs")
        files[role] = path
    return files


@dataclass(frozen=True)
class ProcessResult:
    """Privacy-minimised result supplied by a shell-free process adapter."""

    returncode: int
    stdout_sha256: str
    stdout_bytes: int
    stderr_sha256: str
    stderr_bytes: int
    stdout_prefix: bytes = b""
    stderr_prefix: bytes = b""
    timed_out: bool = False


class ProcessExecutor(Protocol):
    """Narrow injection seam used exclusively by synthetic tests."""

    def run(
        self,
        argv: Sequence[str], *, cwd: Path, env: Mapping[str, str],
        timeout_seconds: int, capture_limit_bytes: int,
    ) -> ProcessResult: ...


@dataclass(frozen=True)
class GuardPreflightOutput:
    """One read-only guard-preflight command result, retained privately only."""

    role: str
    exit_code: int
    raw: bytes


class GuardPreflightProducer(Protocol):
    """Produce the six semantic, read-only guard-preflight observations."""

    def produce(self, *, ccp_path: Path, repository_root: Path) -> Sequence[GuardPreflightOutput]: ...


@dataclass(frozen=True)
class _ExecutableIdentityEvidence:
    """One independently checked executable identity at a private boundary."""

    role: str
    path: Path
    sha256: str
    version: str | None
    synthetic: bool = False


@dataclass(frozen=True)
class _VerticalSchemaBinding:
    """No-follow schema bytes and inode captured before the guarded interval."""

    root: Path
    relative_path: str
    device: int
    inode: int
    size: int
    sha256: str
    document: Mapping[str, Any]


class _ExecutableIdentityVerifier(Protocol):
    """Private capability: production hashes bytes; tests may model an identity."""

    def verify(
        self, *, role: str, path: Path, expected_sha256: str, expected_version: str | None = None,
    ) -> _ExecutableIdentityEvidence: ...


class _ProductionExecutableIdentityVerifier:
    """Fail-closed no-follow identity verifier used by the public production path."""

    def verify(
        self, *, role: str, path: Path, expected_sha256: str, expected_version: str | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> _ExecutableIdentityEvidence:
        if role == "github_cli_verifier":
            if expected_version is None or not _valid_private_gh_environment(environment):
                raise A0XCcpExecutorError("github_cli_verifier requires its private transaction environment")
            probe_environment = dict(environment)
        else:
            if environment is not None:
                raise A0XCcpExecutorError(f"{role} executable does not accept a private GH environment")
            probe_environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
        try:
            metadata = path.lstat()
        except OSError as error:
            raise A0XCcpExecutorError(f"{role} executable is unavailable") from error
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise A0XCcpExecutorError(f"{role} executable is not an independent regular file")
        observed = sha256_file(path)
        if observed != expected_sha256:
            raise A0XCcpExecutorError(f"{role} executable bytes drifted")
        version: str | None = None
        if expected_version is not None:
            completed = subprocess.run(
                (str(path), "--version"), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, check=False, timeout=_PREFLIGHT_TIMEOUT_SECONDS,
                env=probe_environment,
            )
            if completed.returncode != 0:
                raise A0XCcpExecutorError(f"{role} executable version probe failed")
            version = _strict_executable_version(completed.stdout, role, expected_version)
            if version != expected_version:
                raise A0XCcpExecutorError(f"{role} executable version differs")
        return _ExecutableIdentityEvidence(role=role, path=path, sha256=observed, version=version)


class SubprocessGuardPreflightProducer:
    """Read-only producer for the six guard-preflight roles.

    It deliberately does not use configuration-backed ``plan``, ``doctor`` or
    ``dry-run``: those are not prerequisites for ``guard exec``.  The one
    public Git role combines exact HEAD and clean-status probes.
    """

    def produce(self, *, ccp_path: Path, repository_root: Path, allowed_untracked: frozenset[str] | None = None) -> Sequence[GuardPreflightOutput]:
        identity = _ProductionExecutableIdentityVerifier()
        identity.verify(role="ccp", path=ccp_path, expected_sha256=_ACTIVE_CCP_SHA256)
        version = self._run((str(ccp_path), "--version"), repository_root)
        status = self._run(("git", "-c", "core.fsmonitor=false", "-c", "core.trustctime=false", "status", "--short", "--branch"), repository_root)
        head = self._run(("git", "rev-parse", "HEAD"), repository_root)
        identity.verify(role="ccp", path=ccp_path, expected_sha256=_ACTIVE_CCP_SHA256)
        resource = self._run((str(ccp_path), "resource", "status", "--json"), repository_root)
        identity.verify(role="ccp", path=ccp_path, expected_sha256=_ACTIVE_CCP_SHA256)
        admission = self._run((str(ccp_path), "admission", "status", "--json"), repository_root)
        source_exit = 0 if head.exit_code == 0 and status.exit_code == 0 else 1
        try:
            status_lines = status.raw.decode("utf-8").splitlines()
            source_raw = _canonical_json({
                "head": head.raw.decode("ascii").strip(),
                "clean": bool(status_lines) and all(line.startswith("## ") for line in status_lines),
            })
        except UnicodeDecodeError:
            source_raw = b"{}"
            source_exit = 1
        if allowed_untracked is not None:
            from .a0x_vertical_slice import _checkout_state
            observed_head, _tree, clean = _checkout_state(repository_root, allowed_untracked)
            if observed_head != head.raw.decode("ascii").strip():
                raise A0XCcpExecutorError("source changed during scoped guard telemetry")
            source_raw = _canonical_json({"head": observed_head, "clean": clean})
        context = self._run(("docker", "context", "show"), repository_root)
        containers = self._run(("docker", "ps", "-q"), repository_root)
        return (
            GuardPreflightOutput("ccp_version", version.exit_code, version.raw),
            GuardPreflightOutput("resource_status", resource.exit_code, resource.raw),
            GuardPreflightOutput("admission_status", admission.exit_code, admission.raw),
            GuardPreflightOutput("git_source_state", source_exit, source_raw),
            GuardPreflightOutput("docker_context", context.exit_code, context.raw),
            GuardPreflightOutput("docker_active_count", containers.exit_code, containers.raw),
        )

    @staticmethod
    def _run(argv: Sequence[str], cwd: Path) -> GuardPreflightOutput:
        process = subprocess.Popen(
            list(argv), cwd=str(cwd), shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=_coordination_environment(),
        )
        capture = _StreamingCapture(_PREFLIGHT_CAPTURE_LIMIT_BYTES)
        thread = threading.Thread(target=capture.drain, args=(process.stdout,), daemon=True)
        thread.start()
        try:
            process.wait(timeout=_PREFLIGHT_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.wait()
            thread.join(timeout=CLEANUP_MARGIN_SECONDS)
            raise A0XCcpExecutorError("guard preflight probe timed out") from error
        thread.join(timeout=CLEANUP_MARGIN_SECONDS)
        if thread.is_alive():
            raise A0XCcpExecutorError("guard preflight output drain did not terminate")
        if capture.length > _PREFLIGHT_CAPTURE_LIMIT_BYTES:
            raise A0XCcpExecutorError("guard preflight probe output exceeded the fixed capture limit")
        return GuardPreflightOutput("private", int(process.returncode), capture.prefix)


def runtime_mapping_path(
    pair: PairBinding | Mapping[str, Any], *, source_head: str,
) -> str:
    """Return the pair/source/run-derived ignored local role-map location.

    A CCP digest alone is shared across every pair.  It is therefore not a
    safe namespace for private executable role resolution: every planned leg,
    model and one-shot run gets a distinct map below its exact source head.
    """
    binding = pair if isinstance(pair, PairBinding) else PairBinding.from_mapping(pair)
    _revision(source_head, "runtime mapping source head")
    return (
        f".a0x-runtime/bin/{source_head}/{binding.leg.value}/"
        f"{binding.model_key}/{binding.run_id}/runtime-mapping.json"
    )


def launch_fixed_dossier(
    *,
    repository_root: str | Path,
    fixed_dossier: str,
    source_head_probe: Callable[[], str],
    process_executor: ProcessExecutor | None = None,
    guard_preflight_producer: GuardPreflightProducer | None = None,
) -> dict[str, Any]:
    """Run the one exact public dossier through the local guard role map.

    This function performs no retry.  Before a process starts it validates the
    twelve-file selection restriction, both authorization documents, local
    role/map/descriptor bytes, the exact source HEAD, and the frozen
    environment and command tokens.  A claim is created immediately before
    the sole child process and every process result is durably summarized.
    """
    root = Path(repository_root).resolve(strict=True)
    relative_dossier = _fixed_dossier_path(fixed_dossier)
    _assert_fixed_dossier(relative_dossier)
    return _launch_validated_dossier(
        root=root,
        relative_dossier=relative_dossier,
        source_head_probe=source_head_probe,
        process_executor=process_executor,
        guard_preflight_producer=guard_preflight_producer,
    )


def launch_vertical_slice_dossier(
    *,
    repository_root: str | Path,
    implementation_source_head: str,
    leg: str,
    model_key: str,
    source_head_probe: Callable[[], str],
    process_executor: ProcessExecutor | None = None,
    guard_preflight_producer: GuardPreflightProducer | None = None,
) -> dict[str, Any]:
    """Load one selector-derived vertical package before material delegation."""
    root = Path(repository_root).resolve(strict=True)
    package_head = _revision(implementation_source_head, "vertical package source head")
    try:
        selected_leg = Leg(leg)
        relative_dossier = vertical_slice_dossier_path(package_head, selected_leg, model_key)
    except (A0XRunnerError, TypeError, ValueError) as error:
        raise A0XCcpExecutorError("vertical slice selector is invalid") from error
    try:
        package = load_vertical_slice(root, relative_dossier)
    except A0XVerticalSliceError as error:
        raise A0XCcpExecutorError("vertical slice package is invalid") from error
    if not isinstance(package, Mapping):
        raise A0XCcpExecutorError("vertical slice package is invalid")
    try:
        package_pair = PairBinding.from_mapping(_mapping(package, "pair", "vertical slice package"))
        dossier = _mapping(package, "dossier", "vertical slice package")
        dossier_pair = PairBinding.from_mapping(_mapping(dossier, "pair_binding", "vertical slice dossier"))
    except (A0XContractError, ValueError, TypeError) as error:
        raise A0XCcpExecutorError("vertical slice package is invalid") from error
    if (
        package.get("dossier_relative") != relative_dossier
        or package_pair.leg is not selected_leg
        or package_pair.model_key != model_key
        or dossier_pair.as_mapping() != package_pair.as_mapping()
        or dossier.get("implementation_source_head") != package_head
    ):
        raise A0XCcpExecutorError("vertical slice package selector binding differs")
    dossier_sha256 = _vertical_dossier_sha256(package, root=root, relative_dossier=relative_dossier)
    source_head = _revision(source_head_probe(), "repository source head")
    if source_head != package_head:
        raise A0XCcpExecutorError("repository source HEAD differs from vertical package")
    return _launch_validated_dossier(
        root=root,
        relative_dossier=relative_dossier,
        source_head_probe=source_head_probe,
        process_executor=process_executor,
        guard_preflight_producer=guard_preflight_producer,
        expected_dossier=dossier,
        expected_dossier_sha256=dossier_sha256,
        expected_vertical_package_head=package_head,
    )


def vertical_execution_authorization_path(binding: VerticalPackageBinding) -> str:
    """Derive the sole future-only Gate-C authorization inlet for one pair."""
    if not isinstance(binding, VerticalPackageBinding):
        raise A0XCcpExecutorError("vertical package binding is invalid")
    pair = binding.pair_binding
    return (
        f".a0x-runtime/gate-c/v2/{binding.qualified_source_head}/"
        f"{binding.qualified_source_tree}/{pair.leg.value}/{pair.model_key}/"
        f"{pair.run_id}/execution-authorization.json"
    )


def launch_vertical_runtime_package(
    *, repository_root: str | Path, package_binding: VerticalPackageBinding,
    execution_authorization_path: str,
) -> dict[str, Any]:
    """Production v2 entry point: adapters are fixed, never caller selected."""
    root = Path(repository_root).resolve(strict=True)
    from .a0x_vertical_slice import _checkout_state, vertical_public_pre_execution_paths
    allowed = vertical_public_pre_execution_paths(package_binding.pair_binding, package_binding.qualified_source_head, package_binding.qualified_source_tree)
    return _launch_validated_vertical_v2(
        repository_root=root, package_binding=package_binding,
        execution_authorization_path=execution_authorization_path,
        source_state_probe=lambda: _checkout_state(root, allowed), process_executor=_SubprocessExecutor(),
        guard_preflight_producer=SubprocessGuardPreflightProducer(),
        executable_identity_verifier=_ProductionExecutableIdentityVerifier(),
        expected_qualification_context="production",
    )


def _production_vertical_source_state(root: Path) -> tuple[str, str, bool]:
    """Read the execution identity directly; public callers cannot inject it."""
    def git(*argv: str) -> bytes:
        try:
            completed = subprocess.run(
                ("git", *argv), cwd=str(root), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
                timeout=_PREFLIGHT_TIMEOUT_SECONDS, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise A0XCcpExecutorError("vertical Gate C production source probe failed") from error
        if completed.returncode != 0:
            raise A0XCcpExecutorError("vertical Gate C production source probe failed")
        return completed.stdout
    return (
        _strict_text(git("rev-parse", "HEAD"), "vertical Gate C HEAD"),
        _strict_text(git("rev-parse", "HEAD^{tree}"), "vertical Gate C tree"),
        not git("status", "--porcelain=v1", "--untracked-files=all").strip(),
    )


def _launch_validated_vertical_v2(
    *,
    repository_root: str | Path,
    package_binding: VerticalPackageBinding,
    execution_authorization_path: str,
    source_state_probe: Callable[[], tuple[str, str, bool]],
    process_executor: ProcessExecutor,
    guard_preflight_producer: GuardPreflightProducer,
    executable_identity_verifier: _ExecutableIdentityVerifier,
    expected_qualification_context: Literal["production", "synthetic-target-free"] = "synthetic-target-free",
) -> dict[str, Any]:
    """Validate the v2 P0/Gate-B graph before one injected future Gate-C guard.

    This deliberately cannot route through the historical selector launcher.
    A real material adapter is not supplied by this target-free task: callers
    must provide an explicit process adapter under a later authorization.
    """
    if expected_qualification_context not in {"production", "synthetic-target-free"}:
        raise A0XCcpExecutorError("vertical Gate C qualification context is invalid")
    if not isinstance(package_binding, VerticalPackageBinding):
        raise A0XCcpExecutorError("vertical Gate C package binding is invalid")
    root = Path(repository_root).resolve(strict=True)
    terminal_schema_binding = _read_vertical_schema_binding(
        root, "a0x-vertical-child-terminal-v1.schema.json",
    )
    try:
        source_head, source_tree, clean = source_state_probe()
    except Exception as error:
        raise A0XCcpExecutorError("vertical Gate C source-state probe failed") from error
    if (
        not isinstance(clean, bool)
        or not clean
        or source_head != package_binding.qualified_source_head
        or source_tree != package_binding.qualified_source_tree
    ):
        raise A0XCcpExecutorError("vertical Gate C source state does not match package binding")
    _revision(source_head, "vertical Gate C source HEAD")
    _revision(source_tree, "vertical Gate C source tree")
    expected_authorization = vertical_execution_authorization_path(package_binding)
    if execution_authorization_path != expected_authorization:
        raise A0XCcpExecutorError("vertical Gate C authorization path is not derived")
    try:
        # Local import avoids the intentional Gate-B -> Gate-C import cycle.
        from .a0x_runtime_bundle import validate_vertical_runtime_output
        load_vertical_runtime_package(root, package_binding, allow_public_pre_execution=expected_qualification_context == "production")
        paths = _vertical_gate_b_output_paths(package_binding)
        outputs = {
            name: validate_vertical_runtime_output(
                root, path, package_binding, expected_qualification_context=expected_qualification_context,
            )
            for name, path in paths.items()
        }
    except Exception as error:
        raise A0XCcpExecutorError("vertical Gate C package or Gate B output is invalid") from error
    authorization_path = _unique_repository_file(root, execution_authorization_path, "vertical Gate C authorization")
    authorization_raw = authorization_path.read_bytes()
    authorization = _strict_object(authorization_raw, "vertical Gate C authorization")
    if _canonical_json(authorization) != authorization_raw:
        raise A0XCcpExecutorError("vertical Gate C authorization is not canonical JSON")
    try:
        canonical_commitment(authorization, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE)
        pair = PairBinding.from_mapping(_mapping(authorization, "pair_binding", "vertical Gate C authorization"))
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XCcpExecutorError("vertical Gate C authorization is not schema-valid") from error
    expected_source = {"head": source_head, "tree": source_tree, "ref": "refs/heads/main"}
    expected_package = _vertical_package_projection(package_binding)
    if (
        authorization.get("artifact_class") != "a0x-vertical-execution-authorization"
        or authorization.get("qualified_source") != expected_source
        or pair != package_binding.pair_binding
        or authorization.get("vertical_package") != expected_package
        or authorization.get("qualification_context") != expected_qualification_context
        or authorization.get("max_guard_exec_count") != 1
        or authorization.get("stop_boundary") != "after_one_sealed_target_read"
    ):
        raise A0XCcpExecutorError("vertical Gate C authorization binding differs")
    references = authorization.get("gate_b_outputs")
    if not isinstance(references, Mapping) or set(references) != set(paths):
        raise A0XCcpExecutorError("vertical Gate C Gate B output set is invalid")
    for name, relative in paths.items():
        reference = references.get(name)
        raw = _unique_repository_file(root, relative, f"vertical Gate B {name} output").read_bytes()
        if (
            reference != {"path": relative, "sha256": _sha256_bytes(raw)}
            or outputs[name].get("output_kind") != name
            or outputs[name].get("qualification_context") != expected_qualification_context
        ):
            raise A0XCcpExecutorError("vertical Gate C Gate B output binding drifted")
    gate_b_base = Path(next(iter(paths.values()))).parent
    gate_b_authorization_relative = (gate_b_base / "gate-b-authorization.json").as_posix()
    gate_b_receipt_relative = (gate_b_base / "gate-a-verification-receipt.json").as_posix()
    gate_b_authorization_raw = _unique_repository_file(root, gate_b_authorization_relative, "vertical Gate B authorization").read_bytes()
    gate_b_receipt_raw = _unique_repository_file(root, gate_b_receipt_relative, "vertical Gate B verification receipt").read_bytes()
    if (
        authorization.get("gate_b_authorization") != {"path": gate_b_authorization_relative, "sha256": _sha256_bytes(gate_b_authorization_raw)}
        or authorization.get("gate_a_verification_receipt") != {"path": gate_b_receipt_relative, "sha256": _sha256_bytes(gate_b_receipt_raw)}
    ):
        raise A0XCcpExecutorError("vertical Gate C Gate B raw binding drifted")
    reconstructed_evidence = _vertical_gate_a_evidence_from_raw(
        gate_b_authorization_raw=gate_b_authorization_raw,
        gate_b_authorization_path=gate_b_authorization_relative,
        gate_b_receipt_raw=gate_b_receipt_raw,
        gate_b_receipt_path=gate_b_receipt_relative,
        expected_source=expected_source,
        pair=pair,
        expected_package=expected_package,
        expected_qualification_context=expected_qualification_context,
    )
    gate_a_payload = _mapping(outputs["gate_a_evidence"], "payload", "vertical Gate B evidence")
    try:
        evidence = validate_vertical_gate_a_evidence(gate_a_payload)
    except A0XContractError as error:
        raise A0XCcpExecutorError("vertical Gate C Gate A evidence is invalid") from error
    if evidence != reconstructed_evidence:
        raise A0XCcpExecutorError("vertical Gate C Gate A evidence is not reconstructed from Gate B bytes")
    try:
        launch = VerticalA0XGuardLaunch.from_mapping(
            _mapping(authorization, "guard_launch", "vertical Gate C authorization")
        )
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XCcpExecutorError("vertical Gate C guard launch is invalid") from error
    descriptor_raw = _unique_repository_file(root, paths["descriptor"], "vertical Gate B descriptor").read_bytes()
    mapping_payload = _mapping(outputs["mapping"], "payload", "vertical Gate B mapping")
    descriptor_payload = _mapping(outputs["descriptor"], "payload", "vertical Gate B descriptor")
    if (
        launch.source_head != source_head
        or launch.launch_descriptor_path != paths["descriptor"]
        or launch.launch_descriptor_sha256 != _sha256_bytes(descriptor_raw)
        or descriptor_payload.get("child_script", {}).get("sha256") != launch.child_script_sha256
        or descriptor_payload.get("python", {}).get("sha256") != launch.python_sha256
        or mapping_payload.get("ccp", {}).get("sha256") != launch.ccp_sha256
    ):
        raise A0XCcpExecutorError("vertical Gate C guard launch graph differs")
    ccp_path = _role_path(mapping_payload.get("ccp"), role="ccp", expected_hash=launch.ccp_sha256)
    python_path = _role_path(mapping_payload.get("python"), role="python", expected_hash=launch.python_sha256)
    child_path = _unique_repository_file(root, launch.child_script_path, "vertical Gate C child script")
    ccp_identity = _mapping(
        _mapping(outputs["authorization"], "payload", "vertical Gate B authorization"),
        "ccp", "vertical Gate B authorization",
    )
    expected_synthetic_identity = expected_qualification_context == "synthetic-target-free"

    def require_identity_context(observed: _ExecutableIdentityEvidence) -> None:
        """Every identity observation must retain the selected Gate-C context."""
        if (
            not isinstance(observed, _ExecutableIdentityEvidence)
            or observed.synthetic != expected_synthetic_identity
        ):
            raise A0XCcpExecutorError("vertical Gate C executable identity context differs")

    public_extension_sha256: str | None = None

    def validate_public_pre_execution_binding() -> None:
        nonlocal public_extension_sha256
        if expected_qualification_context != "production":
            return
        try:
            p0_dossier_raw = _unique_repository_file(
                root, package_binding.dossier_path, "vertical P0 dossier",
            ).read_bytes()
            gate_b_v4_auth_raw = _unique_repository_file(
                root, paths["authorization"], "vertical Gate B authorization v4",
            ).read_bytes()
            gate_b_v4_readiness_raw = _unique_repository_file(
                root, paths["readiness"], "vertical Gate B readiness v4",
            ).read_bytes()
            observed = load_pre_execution_public_closure(
                root,
                expected_identity={
                    "qualified_source": expected_source,
                    "pair_binding": pair.as_mapping(),
                    "authorization_id": authorization["authorization_id"],
                    "attempt_id": authorization["attempt_id"],
                    "p0_package_commitment_sha256": package_binding.package_commitment_sha256,
                },
                private_input_sha256={
                    "p0_dossier_raw": _sha256_bytes(p0_dossier_raw),
                    "gate_b_authorization_v4": _sha256_bytes(gate_b_v4_auth_raw),
                    "gate_b_readiness_v4": _sha256_bytes(gate_b_v4_readiness_raw),
                },
            )
        except (A0XPublicClosureError, OSError, KeyError, TypeError, ValueError) as error:
            raise A0XCcpExecutorError("vertical Gate C public pre-execution closure is invalid") from error
        if public_extension_sha256 is None:
            public_extension_sha256 = observed.extension_sha256
        elif public_extension_sha256 != observed.extension_sha256:
            raise A0XCcpExecutorError("vertical Gate C public authorization extension drifted")

    # Production must prove the public inputs were pinned before the one-shot
    # guard. The private synthetic test seam intentionally cannot satisfy this.
    validate_public_pre_execution_binding()
    parent_capability = None

    child_identity = executable_identity_verifier.verify(
        role="child", path=child_path, expected_sha256=launch.child_script_sha256,
    )
    ccp_executable_identity = executable_identity_verifier.verify(
        role="ccp", path=ccp_path, expected_sha256=launch.ccp_sha256,
        expected_version=ccp_identity.get("version"),
    )
    python_identity = executable_identity_verifier.verify(
        role="python", path=python_path, expected_sha256=launch.python_sha256,
    )
    for observed in (child_identity, ccp_executable_identity, python_identity):
        require_identity_context(observed)
    if expected_qualification_context == "production":
        from .a0x_vertical_production_adapter import load_vertical_production_capability
        parent_capability = load_vertical_production_capability(root, launch.launch_descriptor_path)
    synthetic_identity = expected_synthetic_identity
    if expected_qualification_context == "production" and (
        pair.leg is not Leg.A0 or pair.model_key != "smollm2_360m"
        or pair.revision != "f8027fd0eaeea54caa13c31d31b9fdc459c38b49"
        or launch.ccp_sha256 != _ACTIVE_CCP_SHA256
    ):
        raise A0XCcpExecutorError("vertical production launch is outside the approved first-result producer/pair")
    from .a0x_vertical_slice import vertical_public_pre_execution_paths
    preflight_scope = vertical_public_pre_execution_paths(pair, source_head, source_tree)
    raw_preflight = (guard_preflight_producer.produce(ccp_path=ccp_path, repository_root=root, allowed_untracked=preflight_scope)
                     if expected_qualification_context == "production" else guard_preflight_producer.produce(ccp_path=ccp_path, repository_root=root))
    guard_preflight = _validate_guard_preflight(
        raw_preflight,
        launch=launch, pair=pair, source_head=source_head,
        ccp_identity=ccp_identity,
    )

    def revalidate_graph() -> None:
        """Re-open every mutable P0, Gate-B and Gate-C trust byte."""
        try:
            live_head, live_tree, live_clean = source_state_probe()
        except Exception as error:
            raise A0XCcpExecutorError("vertical Gate C source-state revalidation failed") from error
        if (live_head, live_tree, live_clean) != (source_head, source_tree, True):
            raise A0XCcpExecutorError("vertical Gate C source state drifted")
        try:
            load_vertical_runtime_package(root, package_binding, allow_public_pre_execution=expected_qualification_context == "production")
            for name, relative in paths.items():
                validate_vertical_runtime_output(
                    root, relative, package_binding,
                    expected_qualification_context=expected_qualification_context,
                )
        except Exception as error:
            raise A0XCcpExecutorError("vertical Gate C package or Gate B output drifted") from error
        if _sha256_bytes(_unique_repository_file(root, execution_authorization_path, "vertical Gate C authorization").read_bytes()) != _sha256_bytes(authorization_raw):
            raise A0XCcpExecutorError("vertical Gate C authorization drifted")
        if _sha256_bytes(_unique_repository_file(root, gate_b_authorization_relative, "vertical Gate B authorization").read_bytes()) != _sha256_bytes(gate_b_authorization_raw):
            raise A0XCcpExecutorError("vertical Gate B authorization drifted")
        if _sha256_bytes(_unique_repository_file(root, gate_b_receipt_relative, "vertical Gate B verification receipt").read_bytes()) != _sha256_bytes(gate_b_receipt_raw):
            raise A0XCcpExecutorError("vertical Gate B verification receipt drifted")
        validate_public_pre_execution_binding()

    # A preflight is not a reservation. Re-open every mutable trust input before claim.
    revalidate_graph()
    for role, path, digest, version in (
        ("child", child_path, launch.child_script_sha256, None),
        ("ccp", ccp_path, launch.ccp_sha256, ccp_identity.get("version")),
        ("python", python_path, launch.python_sha256, None),
    ):
        observed = executable_identity_verifier.verify(
            role=role, path=path, expected_sha256=digest, expected_version=version,
        )
        require_identity_context(observed)
    claim_path = authorization_path.with_name("attempt-claim.json")
    _reserve_claim(claim_path, {
        "artifact_class": "a0x-vertical-gate-c-attempt-claim",
        "qualified_source": expected_source,
        "pair_binding": pair.as_mapping(),
        "vertical_package": expected_package,
        "authorization_raw_sha256": _sha256_bytes(authorization_raw),
        "gate_b_authorization_raw_sha256": _sha256_bytes(gate_b_authorization_raw),
        "gate_a_verification_receipt_raw_sha256": _sha256_bytes(gate_b_receipt_raw),
        "guard_launch_sha256": _sha256_bytes(_canonical_json(launch.as_mapping())),
        "authorization_id": authorization["authorization_id"],
        "attempt_id": authorization["attempt_id"],
        "max_guard_exec_count": 1,
        "qualification_context": expected_qualification_context,
    })
    pre_run_path: str | None = None
    result: ProcessResult | None = None
    argv: tuple[str, ...] | None = None
    environment: dict[str, str] | None = None
    guard_invoked = False
    # Claim precedes the final revalidation deliberately: a later drift consumes
    # the one shot rather than silently authorizing a retry.
    try:
        pre_run_path = _write_vertical_pre_run(
            root, authorization_path, pair, launch, claim_path,
            _sha256_bytes(authorization_raw),
        )
        revalidate_graph()
        for role, path, digest, version in (
            ("child", child_path, launch.child_script_sha256, None),
            ("ccp", ccp_path, launch.ccp_sha256, ccp_identity.get("version")),
            ("python", python_path, launch.python_sha256, None),
        ):
            observed = executable_identity_verifier.verify(
                role=role, path=path, expected_sha256=digest, expected_version=version,
            )
            require_identity_context(observed)
        argv = _materialize_argv(launch, ccp_path=ccp_path, python_path=python_path, child_path=child_path)
        environment = _frozen_environment(launch)
        if expected_qualification_context == "production":
            # The active macOS producer requires HOME for its persistent
            # admission root. Credentials remain absent from the child.
            environment.update(_coordination_environment())
        permission_window = _a0_material_permission_window(root) if expected_qualification_context == "production" else nullcontext()
        with permission_window:
            guard_invoked = True
            result = process_executor.run(
                argv, cwd=root, env=environment, timeout_seconds=_SUPERVISION_TIMEOUT_SECONDS,
                capture_limit_bytes=_CAPTURE_LIMIT_BYTES,
            )
        # A child outcome is not authority to skip the final identity boundary:
        # a replacement during execution must seal recovery rather than publish
        # a completed attempt.
        for role, path, digest, version in (
            ("child", child_path, launch.child_script_sha256, None),
            ("ccp", ccp_path, launch.ccp_sha256, ccp_identity.get("version")),
            ("python", python_path, launch.python_sha256, None),
        ):
            observed = executable_identity_verifier.verify(
                role=role, path=path, expected_sha256=digest, expected_version=version,
            )
            require_identity_context(observed)
        _revalidate_vertical_schema_binding(terminal_schema_binding)
    except BaseException as error:
        if guard_invoked and expected_qualification_context == "production":
            try:
                guard_preflight_producer.produce(ccp_path=ccp_path, repository_root=root)
            except BaseException as post_error:
                _exclusive_write(authorization_path.parent / "observations/postflight-probe-failure.json", _canonical_json({
                    "artifact_class": "a0x-private-postflight-probe-failure", "error_type": type(post_error).__name__,
                    "state": "UNVERIFIED", "retry_permitted": False,
                }), "postflight probe failure")
        _write_vertical_terminal(
            root, authorization_path, pair, launch, result, "recovery_required",
            _sha256_bytes(authorization_raw), error, pre_run_path=pre_run_path,
            terminal_schema_raw_sha256=terminal_schema_binding.sha256,
        )
        raise A0XCcpExecutorError("vertical Gate C could not produce a terminal result") from error
    _validate_process_result(result)
    classification = _classify_outer_exit(result)
    child_terminal = (
        _parse_vertical_child_terminal(
            result.stdout_prefix,
            expected_source=expected_source,
            expected_pair=pair.as_mapping(),
            expected_authorization_id=str(authorization["authorization_id"]),
            expected_attempt_id=str(authorization["attempt_id"]),
            expected_qualification_context=expected_qualification_context,
            terminal_schema=terminal_schema_binding.document,
        )
        if classification == "completed" and result.stdout_bytes == len(result.stdout_prefix)
        else None
    )
    child_terminal_status = child_terminal.get("scientific_outcome") if child_terminal is not None else None
    package_verified, postflight_verified = False, False
    postflight_error: BaseException | None = None
    try:
        if expected_qualification_context == "production":
            # Guard exit is not a release handoff, including pressure/timeout.
            from .a0x_vertical_slice import _checkout_state, vertical_terminal_output_paths
            from .a0x_vertical_slice import vertical_public_pre_execution_paths
            postflight_scope = vertical_terminal_output_paths(pair, source_head, source_tree) | vertical_public_pre_execution_paths(pair, source_head, source_tree)
            postflight_outputs = guard_preflight_producer.produce(ccp_path=ccp_path, repository_root=root, allowed_untracked=postflight_scope)
            live_head, live_tree, live_clean = _checkout_state(root, postflight_scope)
            if (live_head, live_tree, live_clean) != (source_head, source_tree, True):
                raise A0XCcpExecutorError("post-guard source state differs outside the exact output set")
            _validate_guard_preflight(postflight_outputs, launch=launch, pair=pair, source_head=source_head, ccp_identity=ccp_identity)
            postflight_verified = True
            if child_terminal is not None:
                _verify_vertical_parent_package(root, package_binding, launch.launch_descriptor_path, child_terminal, parent_capability=parent_capability)
                package_verified = True
    except BaseException as error:
        postflight_error = error
    terminal_path = _write_vertical_terminal(
        root, authorization_path, pair, launch, result, classification, _sha256_bytes(authorization_raw), postflight_error,
        child_terminal_status=child_terminal_status, pre_run_path=pre_run_path,
        child_terminal=child_terminal,
        terminal_schema_raw_sha256=terminal_schema_binding.sha256,
        completion_verified=_vertical_completion_verified(
            expected_qualification_context, classification, child_terminal,
            package_verified=package_verified, postflight_verified=postflight_verified,
        ),
    )
    if (
        not _vertical_completion_verified(
            expected_qualification_context, classification, child_terminal,
            package_verified=package_verified, postflight_verified=postflight_verified,
        )
    ):
        raise A0XCcpExecutorError(
            "vertical Gate C terminal lacks independently verified package and postflight closure"
        )
    return {
        "status": "synthetic_completed" if expected_qualification_context == "synthetic-target-free" else "completed",
        "qualified_source": expected_source,
        "pair_binding": pair.as_mapping(),
        "package_commitment_sha256": package_binding.package_commitment_sha256,
        "execution_authorization_raw_sha256": _sha256_bytes(authorization_raw),
        "claim_path": claim_path.relative_to(root).as_posix(),
        "terminal_observation_path": terminal_path,
        "child_terminal_status": child_terminal_status,
        "child_terminal": child_terminal,
        "publication_eligible": False,
    }


@contextmanager
def _a0_material_permission_window(root: Path):
    """Metadata-only macOS descriptors restore two A0 targets for one guard.

    The operator must already have authorized this exact Gate C invocation.
    Requires the activity-owned source snapshot to have no concurrent mutator.
    Mode-000 files cannot be opened even with O_EVTONLY. Directory-relative
    metadata admission precedes chmod; the resulting inode is pinned before
    any content access. This detects drift, not hostile concurrent replacement.
    """
    event_only = getattr(os, "O_EVTONLY", None)
    if event_only is None:
        raise A0XCcpExecutorError("protected permission window requires the qualified macOS metadata API")
    relatives = ("data/a0/procedural-targets/calibration-targets.jsonl", "data/a0/sealed-targets/targets.jsonl")
    files: list[tuple[str, int, str, tuple[int, int, int], int | None]] = []
    try:
        for relative in relatives:
            directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                parts = PurePosixPath(relative).parts
                for part in parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    os.close(directory)
                    directory = child
                info = os.stat(parts[-1], dir_fd=directory, follow_symlinks=False)
            except BaseException:
                os.close(directory)
                raise
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0:
                os.close(directory)
                raise A0XCcpExecutorError("protected target is not an independent mode-000 regular file")
            files.append((relative, directory, parts[-1], (info.st_dev, info.st_ino, info.st_size), None))
        for index, (relative, directory, name, identity, _fd) in enumerate(files):
            info = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if (info.st_dev, info.st_ino, info.st_size) != identity or info.st_nlink != 1:
                raise A0XCcpExecutorError("protected target identity changed before permission restoration")
            os.chmod(name, 0o600, dir_fd=directory, follow_symlinks=False)
            fd = os.open(name, event_only | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            files[index] = (relative, directory, name, identity, fd)
            held = os.fstat(fd)
            if (held.st_dev, held.st_ino, held.st_size) != identity or held.st_nlink != 1:
                raise A0XCcpExecutorError("protected target identity changed during permission restoration")
        yield
    finally:
        failure = False
        for relative, directory, name, identity, fd in files:
            try:
                named = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if (named.st_dev, named.st_ino, named.st_size) != identity or named.st_nlink != 1:
                    failure = True
                if fd is not None:
                    held = os.fstat(fd)
                    if (held.st_dev, held.st_ino, held.st_size) == identity:
                        os.fchmod(fd, 0)
                    else:
                        failure = True
                elif not failure:
                    os.chmod(name, 0, dir_fd=directory, follow_symlinks=False)
            except OSError:
                failure = True
            finally:
                if fd is not None:
                    os.close(fd)
                os.close(directory)
        if failure:
            raise A0XCcpExecutorError("protected permission cleanup has uncertain ownership")


def _verify_vertical_parent_package(root: Path, binding: VerticalPackageBinding, descriptor_path: str, child_terminal: Mapping[str, Any], *, parent_capability: Any) -> None:
    """Recreate expectations independently; never trust adjacent package self-hashes."""
    from dataclasses import replace
    from .a0x_vertical_production_adapter import load_vertical_production_capability
    from .a0x_vertical_terminal_package import VerticalTerminalExpectation, verify_vertical_terminal_package, _read_independent, capture_material_evidence
    capability = load_vertical_production_capability(root, descriptor_path, _terminal_outputs=True)
    context = capability.context
    if parent_capability is None or context != parent_capability.context or capability.package_documents != parent_capability.package_documents:
        raise A0XCcpExecutorError("terminal inputs differ from the parent's pre-execution capability")
    if context.source_head != binding.qualified_source_head or context.source_tree != binding.qualified_source_tree or context.pair_binding != binding.pair_binding.as_mapping():
        raise A0XCcpExecutorError("independent terminal capability differs from the parent package")
    reference = child_terminal.get("terminal_package")
    if not isinstance(reference, Mapping) or reference.get("package_relative_path") != binding.pair_binding.output_path:
        raise A0XCcpExecutorError("child terminal package path is not the exact pair destination")
    manifest, _info = _read_independent(root, binding.pair_binding.output_path + "/publication-manifest.json")
    receipt, _info = _read_independent(root, binding.pair_binding.output_path + "/root-receipt.json")
    if _sha256_bytes(manifest) != reference.get("manifest_raw_sha256") or _sha256_bytes(receipt) != reference.get("root_receipt_raw_sha256"):
        raise A0XCcpExecutorError("child package reference differs from actual terminal bytes")
    terminal_raw, _info = _read_independent(root, binding.pair_binding.output_path + "/terminal-result.json")
    terminal = _strict_object(terminal_raw, "private terminal result")
    if terminal.get("scientific_outcome") != child_terminal.get("scientific_outcome") or terminal.get("reached_frontier") != child_terminal.get("reached_frontier"):
        raise A0XCcpExecutorError("child outcome differs from independently read package")
    assets = None
    if child_terminal.get("reached_frontier") == "sealed":
        pair = binding.pair_binding
        context = capture_material_evidence(root, context)
        base = root / "results/a0x-external-assets" / context.source_head / context.source_tree / "a0" / pair.model_key / pair.run_id
        assets = {"dense": base / "dense-output.bin", "index": base / "representation-index.json"}
    expectation = VerticalTerminalExpectation.from_production_capability(capability, material_context=context, external_assets=assets)
    verify_vertical_terminal_package(package_root=root / binding.pair_binding.output_path, repository_root=root,
        expected=expectation, expected_manifest_sha256=_sha256_bytes(manifest), expected_root_receipt_sha256=_sha256_bytes(receipt))


def _vertical_gate_b_output_paths(binding: VerticalPackageBinding) -> dict[str, str]:
    pair = binding.pair_binding
    base = (
        f".a0x-runtime/gate-b/v2/{binding.qualified_source_head}/"
        f"{binding.qualified_source_tree}/{pair.leg.value}/{pair.model_key}/{pair.run_id}"
    )
    return {
        "gate_a_evidence": f"{base}/gate-a-evidence.json",
        "readiness": f"{base}/runtime-readiness.json",
        "descriptor": f"{base}/launch-descriptor.json",
        "authorization": f"{base}/execution-authorization.json",
        "mapping": f"{base}/runtime-mapping.json",
    }


def _vertical_package_projection(binding: VerticalPackageBinding) -> dict[str, str]:
    return {
        "envelope_path": binding.envelope_path,
        "package_path": binding.package_path,
        "commitment_path": binding.commitment_path,
        "commitment_raw_sha256": binding.commitment_raw_sha256,
        "package_commitment_sha256": binding.package_commitment_sha256,
        "dossier_path": binding.dossier_path,
        "dossier_sha256": binding.dossier_sha256,
    }


def _vertical_gate_a_evidence_from_raw(
    *, gate_b_authorization_raw: bytes, gate_b_authorization_path: str,
    gate_b_receipt_raw: bytes, gate_b_receipt_path: str,
    expected_source: Mapping[str, str], pair: PairBinding,
    expected_package: Mapping[str, str],
    expected_qualification_context: Literal["production", "synthetic-target-free"] = "production",
) -> dict[str, Any]:
    """Reconstruct the sole v2 Gate-A projection from raw Gate-B documents."""
    authorization = _strict_object(gate_b_authorization_raw, "vertical Gate B authorization")
    receipt = _strict_object(gate_b_receipt_raw, "vertical Gate B verification receipt")
    # Hosted Gate B producers write one LF; historical synthetic fixtures do
    # not. Admit precisely these two serializations and retain the raw hash.
    canonical_authorization = _canonical_json(authorization)
    if gate_b_authorization_raw not in (canonical_authorization, canonical_authorization + b"\n"):
        raise A0XCcpExecutorError("vertical Gate B authorization is not canonical JSON")
    if hosted_gate_a_canonical_json_bytes(receipt) != gate_b_receipt_raw:
        raise A0XCcpExecutorError("vertical Gate B verification receipt is not canonical JSON")
    _validate_vertical_raw_schema(
        authorization, "a0x-gate-b-authorization-v2.schema.json", "vertical Gate B authorization",
    )
    receipt_schema = (
        "a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1.schema.json"
        if expected_qualification_context == "synthetic-target-free"
        else "a0x-hosted-gate-a-verification-receipt.schema.json"
    )
    _validate_vertical_raw_schema(receipt, receipt_schema, "vertical Gate B verification receipt")
    source_head, source_tree = expected_source["head"], expected_source["tree"]
    if (
        authorization.get("repository") != "MarcoPorcellato/Latent-TRIZ"
        or authorization.get("authorization_profile") != "a0x-gate-b-authorization-v2"
        or authorization.get("authorization_status") != "authorized"
        or authorization.get("source_head") != source_head
        or authorization.get("source_tree") != source_tree
        or authorization.get("source_sha") != source_head
        or authorization.get("job_workflow_sha") != source_head
        or authorization.get("pair_binding") != pair.as_mapping()
        or authorization.get("vertical_package") != dict(expected_package)
        or authorization.get("verification_receipt_path") != gate_b_receipt_path
        or authorization.get("max_verification_count") != 1
        or authorization.get("stop_boundary") != "after_gate_b_runtime_bundle"
        or authorization.get("qualification_context") != expected_qualification_context
    ):
        raise A0XCcpExecutorError("vertical Gate C Gate B authorization semantics differ")
    if (
        receipt.get("repository") != authorization["repository"]
        or receipt.get("qualified_source_head") != source_head
        or receipt.get("qualified_source_tree") != source_tree
        or receipt.get("pair_binding") != pair.as_mapping()
        or receipt.get("authorization_raw_sha256") != _sha256_bytes(gate_b_authorization_raw)
        or receipt.get("hosted_inputs") != authorization.get("hosted_inputs")
        or receipt.get("verifier") != authorization.get("verifier")
        or receipt.get("verification_status") != "verified"
        or receipt.get("qualification_context", "production") != expected_qualification_context
        or receipt.get("receipt_profile") != (
            "a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1"
            if expected_qualification_context == "synthetic-target-free"
            else "a0x-hosted-gate-a-verification-receipt-v1"
        )
    ):
        raise A0XCcpExecutorError("vertical Gate C Gate B receipt semantics differ")
    evidence = {
        "evidence_profile": "a0x-vertical-gate-a-evidence-binding-v1",
        "provider": "github-hosted-attestation-v1",
        "repository": authorization["repository"],
        "source_head": source_head,
        "source_tree": source_tree,
        "pair_binding": pair.as_mapping(),
        "gate_b_authorization_path": gate_b_authorization_path,
        "gate_b_authorization_raw_sha256": _sha256_bytes(gate_b_authorization_raw),
        "hosted_inputs": authorization["hosted_inputs"],
        "verification_receipt": {
            "path": gate_b_receipt_path,
            "sha256": _sha256_bytes(gate_b_receipt_raw),
        },
        "verifier": authorization["verifier"],
    }
    try:
        return validate_vertical_gate_a_evidence(evidence)
    except A0XContractError as error:
        raise A0XCcpExecutorError("vertical Gate C reconstructed Gate A evidence is invalid") from error


def _validate_vertical_raw_schema(
    value: Mapping[str, Any], filename: str, label: str, *,
    schema_document: Mapping[str, Any] | None = None,
) -> None:
    try:
        schema = (
            schema_document
            if schema_document is not None
            else _read_vertical_schema_binding(
                Path(__file__).resolve().parents[2], filename,
            ).document
        )
    except (A0XCcpExecutorError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XCcpExecutorError(f"{label} schema is unavailable") from error
    if not isinstance(schema, Mapping):
        raise A0XCcpExecutorError(f"{label} schema is invalid")
    issues = validate(dict(value), dict(schema))
    if issues:
        raise A0XCcpExecutorError(f"{label} schema rejected input: {issues[0].message}")


def _read_vertical_schema_binding(root: Path, filename: str) -> _VerticalSchemaBinding:
    """Read one schema through no-follow descriptors and retain inode identity."""
    if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".schema.json"):
        raise A0XCcpExecutorError("vertical schema filename is invalid")
    relative = f"schemas/{filename}"
    parts = PurePosixPath(relative).parts
    repository = root.resolve(strict=True)
    directory_fd = os.open(repository, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
            if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
                raise A0XCcpExecutorError("vertical schema path contains a non-directory")
        file_fd = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1_048_576:
                raise A0XCcpExecutorError("vertical schema is not an independent regular file")
            chunks: list[bytes] = []
            remaining = 1_048_577
            while remaining:
                chunk = os.read(file_fd, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            after = os.fstat(file_fd)
        finally:
            os.close(file_fd)
    except OSError as error:
        raise A0XCcpExecutorError("vertical schema is unavailable or uses a link") from error
    finally:
        os.close(directory_fd)
    if (
        len(raw) > 1_048_576 or after.st_nlink != 1
        or (before.st_dev, before.st_ino, before.st_size)
        != (after.st_dev, after.st_ino, after.st_size)
    ):
        raise A0XCcpExecutorError("vertical schema changed during read")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XCcpExecutorError("vertical schema bytes are not JSON") from error
    if not isinstance(document, dict):
        raise A0XCcpExecutorError("vertical schema root is not an object")
    return _VerticalSchemaBinding(
        root=repository, relative_path=relative, device=before.st_dev, inode=before.st_ino,
        size=len(raw), sha256=_sha256_bytes(raw), document=document,
    )


def _revalidate_vertical_schema_binding(binding: _VerticalSchemaBinding) -> None:
    observed = _read_vertical_schema_binding(binding.root, Path(binding.relative_path).name)
    if (
        observed.relative_path != binding.relative_path
        or (observed.device, observed.inode, observed.size, observed.sha256)
        != (binding.device, binding.inode, binding.size, binding.sha256)
    ):
        raise A0XCcpExecutorError("vertical schema inode or bytes changed after binding")


def _write_vertical_terminal(
    root: Path, authorization_path: Path, pair: PairBinding, launch: A0XGuardLaunch,
    result: ProcessResult | None, classification: str, authorization_raw_sha256: str,
    error: BaseException | None, *, child_terminal_status: str | None = None,
    pre_run_path: str | None = None,
    child_terminal: Mapping[str, Any] | None = None,
    completion_verified: bool = False,
    terminal_schema_raw_sha256: str | None = None,
) -> str:
    """Seal a v2 terminal record without borrowing the historical namespace."""
    directory = authorization_path.parent / "observations"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "terminal-observation.json"
    payload: dict[str, Any] = {
        "artifact_class": "a0x-vertical-gate-c-terminal-observation",
        "qualified_source": {"head": launch.source_head, "ref": "refs/heads/main"},
        "pair_binding": pair.as_mapping(),
        "authorization_raw_sha256": authorization_raw_sha256,
        "guard_launch_sha256": _sha256_bytes(_canonical_json(launch.as_mapping())),
        "outer_exit_classification": classification,
        "recovery_required": not completion_verified,
        "child_terminal_status": child_terminal_status,
        "child_terminal": dict(child_terminal) if child_terminal is not None else None,
        "terminal_schema_raw_sha256": terminal_schema_raw_sha256,
        "pre_run_observation_path": pre_run_path,
        # Eligibility is computed only by the final verifier after outer and
        # postflight closure. An inner child can never grant publication.
        "publication_eligible": False,
    }
    if result is None:
        payload["process"] = None
        payload["error_type"] = type(error).__name__ if error is not None else "unknown"
    else:
        payload["process"] = {
            "returncode": result.returncode, "timed_out": result.timed_out,
            "stdout_sha256": result.stdout_sha256, "stdout_bytes": result.stdout_bytes,
            "stderr_sha256": result.stderr_sha256, "stderr_bytes": result.stderr_bytes,
        }
    _exclusive_write(path, _canonical_json(payload), "vertical Gate C terminal observation")
    return path.relative_to(root).as_posix()


def _vertical_completion_verified(
    qualification_context: str, outer_classification: str,
    child_terminal: Mapping[str, Any] | None, *,
    package_verified: bool, postflight_verified: bool,
) -> bool:
    """Separate child completion from parent-owned package/postflight closure."""
    if (
        outer_classification != "completed"
        or not isinstance(child_terminal, Mapping)
        or child_terminal.get("exit_class") != "completed"
    ):
        return False
    if qualification_context == "synthetic-target-free":
        return (
            child_terminal.get("reached_frontier") == "validated_graph"
            and child_terminal.get("scientific_outcome") is None
            and child_terminal.get("terminal_package") is None
        )
    if qualification_context == "production":
        return (
            (child_terminal.get("reached_frontier") == "sealed"
             or child_terminal.get("reached_frontier") == "validated_graph" and child_terminal.get("scientific_outcome") in {"failed", "incompatible"})
            and child_terminal.get("scientific_outcome")
            in {"positive", "null", "non_interpretable", "incompatible", "failed"}
            and isinstance(child_terminal.get("terminal_package"), Mapping)
            and package_verified is True
            and postflight_verified is True
        )
    return False


def _write_vertical_pre_run(
    root: Path, authorization_path: Path, pair: PairBinding, launch: A0XGuardLaunch,
    claim_path: Path, authorization_raw_sha256: str,
) -> str:
    """Seal the claim-to-guard boundary without exposing argv or environment."""
    directory = authorization_path.parent / "observations"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "pre-run-observation.json"
    payload = {
        "artifact_class": "a0x-vertical-gate-c-pre-run-observation",
        "qualified_source": {"head": launch.source_head, "ref": "refs/heads/main"},
        "pair_binding": pair.as_mapping(),
        "claim_path": claim_path.relative_to(root).as_posix(),
        "authorization_raw_sha256": authorization_raw_sha256,
        "guard_launch_sha256": _sha256_bytes(_canonical_json(launch.as_mapping())),
        "publication_eligible": False,
    }
    _exclusive_write(path, _canonical_json(payload), "vertical Gate C pre-run observation")
    return path.relative_to(root).as_posix()


def _launch_validated_dossier(
    *,
    root: Path,
    relative_dossier: str,
    source_head_probe: Callable[[], str],
    process_executor: ProcessExecutor | None,
    guard_preflight_producer: GuardPreflightProducer | None,
    expected_dossier: Mapping[str, Any] | None = None,
    expected_dossier_sha256: str | None = None,
    expected_vertical_package_head: str | None = None,
) -> dict[str, Any]:
    """Consume an already selected dossier without selecting its namespace."""
    dossier_path = _repository_file(root, relative_dossier)
    dossier_raw = dossier_path.read_bytes()
    dossier = _strict_object(dossier_raw, "dossier")
    if expected_dossier is not None and dossier != dict(expected_dossier):
        raise A0XCcpExecutorError("vertical slice dossier bytes drifted")
    if expected_dossier_sha256 is not None and _sha256_bytes(dossier_raw) != expected_dossier_sha256:
        raise A0XCcpExecutorError("vertical slice dossier bytes drifted")
    try:
        canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE)
        pair = PairBinding.from_mapping(_mapping(dossier, "pair_binding", "dossier"))
    except (A0XContractError, ValueError, TypeError) as error:
        raise A0XCcpExecutorError("fixed dossier is not a valid authorization dossier") from error
    implementation_source_head = _revision(
        dossier.get("implementation_source_head"), "dossier implementation source head",
    )
    source_head = _revision(source_head_probe(), "repository source head")
    if (
        expected_vertical_package_head is not None
        and source_head != expected_vertical_package_head
    ):
        raise A0XCcpExecutorError("repository source HEAD differs from vertical package")
    expected_paths = derive_runtime_paths(pair, source_head=source_head)
    authorization_relative = expected_paths.authorization_path
    authorization_path = _repository_file(root, _relative_runtime_path(authorization_relative))
    authorization_raw = authorization_path.read_bytes()
    authorization = _strict_object(authorization_raw, "execution authorization")
    authorization_source_head = _revision(
        authorization.get("source_head"), "execution authorization source head",
    )
    if authorization_source_head != source_head:
        raise A0XCcpExecutorError("repository source HEAD differs from the execution authorization")
    launch = _validate_authorization(
        dossier=dossier,
        authorization=authorization,
        pair=pair,
        source_head=source_head,
        implementation_source_head=implementation_source_head,
        root=root,
    )
    authorization_profile = _authorization_profile(authorization)
    authorization_commitment = canonical_commitment(
        authorization, authorization_profile,
    ).as_mapping()
    material_contract_path = _repository_file(root, "experiments/a0x-six-model/material-execution-contract.json")
    material_contract_raw = material_contract_path.read_bytes()
    if _sha256_bytes(material_contract_raw) != authorization.get("material_contract_raw_sha256"):
        raise A0XCcpExecutorError("material contract bytes are not bound to the execution authorization")
    if source_head_probe() != source_head:
        raise A0XCcpExecutorError("repository source HEAD differs from the execution authorization")
    descriptor_relative = launch.launch_descriptor_path
    descriptor_path = _repository_file(root, descriptor_relative)
    if sha256_file(descriptor_path) != launch.launch_descriptor_sha256:
        raise A0XCcpExecutorError("launch descriptor bytes drifted")
    descriptor = _strict_object(descriptor_path.read_bytes(), "launch descriptor")
    _validate_runtime_readiness_binding(
        descriptor, root=root, pair=pair, source_head=source_head,
    )
    mapping_path = _repository_file(root, runtime_mapping_path(pair, source_head=source_head))
    mapping = _strict_object(mapping_path.read_bytes(), "runtime role mapping")
    ccp_path, python_path = _validate_runtime_mapping(
        mapping, root=root, launch=launch, descriptor_path=descriptor_path, pair=pair,
        source_head=source_head,
    )
    child_path = _repository_file(root, launch.child_script_path)
    _validate_file_hash(child_path, launch.child_script_sha256, "child script")
    _validate_file_hash(ccp_path, launch.ccp_sha256, "CCP executable")
    _validate_file_hash(python_path, launch.python_sha256, "Python executable")
    _rehash_gate_a_at_boundary(root, authorization, source_head)
    if guard_preflight_producer is None:
        raise A0XCcpExecutorError("fresh guard preflight producer is required before a material claim")
    _validate_file_hash(ccp_path, launch.ccp_sha256, "CCP executable")
    guard_preflight = _validate_guard_preflight(
        guard_preflight_producer.produce(ccp_path=ccp_path, repository_root=root),
        launch=launch, pair=pair, source_head=source_head,
        ccp_identity=_mapping(authorization, "ccp", "execution authorization"),
    )
    guard_preflight_path = _write_guard_preflight_observation(
        root, expected_paths.observation_directory, guard_preflight,
    )
    guard_preflight_raw_sha256 = _sha256_bytes(_canonical_json(guard_preflight))
    _assert_bound_authorization_and_contract(
        authorization_path=authorization_path,
        authorization_raw=authorization_raw,
        authorization_commitment=authorization_commitment,
        material_contract_path=material_contract_path,
        material_contract_raw=material_contract_raw,
    )
    # The guard preflight is an untrusted time interval.  Reopen the current
    # Gate-A byte boundary before reserving the one-shot claim.
    _rehash_gate_a_at_boundary(root, authorization, source_head)
    if source_head_probe() != source_head:
        raise A0XCcpExecutorError("repository source HEAD drifted before attempt claim")

    claim_path = _repository_file_for_write(root, expected_paths.claim_path)
    claim_payload = {
        "artifact_class": "a0x-guard-attempt-claim",
        "source_head": source_head,
        "authorization_id": authorization["authorization_id"],
        "attempt_id": authorization["attempt_id"],
        "pair_binding": pair.as_mapping(),
        "fixed_dossier": relative_dossier,
        "authorization_raw_sha256": _sha256_bytes(authorization_raw),
        "authorization_commitment": authorization_commitment,
        "guard_launch_sha256": _sha256_bytes(_canonical_json(launch.as_mapping())),
        "guard_preflight_observation_path": guard_preflight_path,
        "guard_preflight_observation_raw_sha256": guard_preflight_raw_sha256,
        "max_guard_exec_count": 1,
    }
    _reserve_claim(claim_path, claim_payload)
    argv = _materialize_argv(launch, ccp_path=ccp_path, python_path=python_path, child_path=child_path)
    environment = _frozen_environment(launch)
    executor = process_executor if process_executor is not None else _SubprocessExecutor()
    pre_run = _pre_run_observation(
        source_head=source_head, pair=pair, dossier=relative_dossier,
        authorization_raw=authorization_raw, launch=launch, claim_path=expected_paths.claim_path,
        authorization_commitment=authorization_commitment,
        gate_a_evidence=_authorization_gate_a_evidence(authorization), argv=argv,
        guard_preflight_path=guard_preflight_path, guard_preflight_raw_sha256=guard_preflight_raw_sha256,
    )
    pre_run_raw_sha256 = _sha256_bytes(_canonical_json(pre_run))
    pre_run_path = expected_paths.observation_directory + "pre-run-observation.json"
    try:
        _write_pre_run_observation(root, expected_paths.observation_directory, pre_run)
        # The claim is intentionally before the final recheck: a binding drift
        # in this narrow race window consumes the attempt and receives durable
        # recovery evidence rather than silently enabling a retry.
        _validate_file_hash(descriptor_path, launch.launch_descriptor_sha256, "launch descriptor")
        _validate_file_hash(child_path, launch.child_script_sha256, "child script")
        _validate_file_hash(ccp_path, launch.ccp_sha256, "CCP executable")
        _validate_file_hash(python_path, launch.python_sha256, "Python executable")
        _rehash_gate_a_at_boundary(root, authorization, source_head)
        if source_head_probe() != source_head:
            raise A0XCcpExecutorError("repository source HEAD drifted after attempt claim")
        _assert_bound_authorization_and_contract(
            authorization_path=authorization_path,
            authorization_raw=authorization_raw,
            authorization_commitment=authorization_commitment,
            material_contract_path=material_contract_path,
            material_contract_raw=material_contract_raw,
        )
        result = executor.run(
            argv, cwd=root, env=environment,
            timeout_seconds=_SUPERVISION_TIMEOUT_SECONDS,
            capture_limit_bytes=_CAPTURE_LIMIT_BYTES,
        )
    except BaseException as error:
        observation = _terminal_observation(
            source_head=source_head, pair=pair, dossier=relative_dossier,
            launch=launch, result=None, classification="launcher_internal_error",
            recovery_required=True, error_type=type(error).__name__,
            authorization_raw_sha256=_sha256_bytes(authorization_raw),
            authorization_commitment=authorization_commitment,
            pre_run_path=pre_run_path, pre_run_raw_sha256=pre_run_raw_sha256,
            guard_preflight_path=guard_preflight_path, guard_preflight_raw_sha256=guard_preflight_raw_sha256,
        )
        _write_terminal_observation(root, expected_paths.observation_directory, observation)
        raise A0XCcpExecutorError("guard process could not produce a terminal result") from error
    _validate_process_result(result)
    classification = _classify_outer_exit(result)
    child_terminal_status = _parse_child_terminal(result.stdout_prefix) if result.returncode == 0 else None
    observation = _terminal_observation(
        source_head=source_head, pair=pair, dossier=relative_dossier,
        launch=launch, result=result, classification=classification,
        recovery_required=classification != "completed" or child_terminal_status is None,
        child_terminal_status=child_terminal_status,
        authorization_raw_sha256=_sha256_bytes(authorization_raw),
        authorization_commitment=authorization_commitment,
        pre_run_path=pre_run_path, pre_run_raw_sha256=pre_run_raw_sha256,
        guard_preflight_path=guard_preflight_path, guard_preflight_raw_sha256=guard_preflight_raw_sha256,
    )
    observation_path = _write_terminal_observation(root, expected_paths.observation_directory, observation)
    if classification != "completed":
        raise A0XCcpExecutorError(f"guard process reached terminal outcome: {classification}")
    if observation["child_terminal_status"] is None:
        raise A0XCcpExecutorError("guard process succeeded without a valid child terminal status")
    return {
        "status": "completed",
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "authorization_raw_sha256": _sha256_bytes(authorization_raw),
        "authorization_commitment": authorization_commitment,
        "claim_path": expected_paths.claim_path,
        "terminal_observation_path": observation_path,
        "child_terminal_status": observation["child_terminal_status"],
    }


def _validate_authorization(
    *, dossier: Mapping[str, Any], authorization: Mapping[str, Any], pair: PairBinding,
    source_head: str, implementation_source_head: str, root: Path,
) -> A0XGuardLaunch:
    try:
        canonical_commitment(authorization, _authorization_profile(authorization))
        auth_pair = PairBinding.from_mapping(_mapping(authorization, "pair_binding", "execution authorization"))
    except (A0XContractError, ValueError, TypeError) as error:
        raise A0XCcpExecutorError("execution authorization is not schema-valid") from error
    if (
        auth_pair.as_mapping() != pair.as_mapping()
        or authorization.get("source_head") != source_head
        or authorization.get("implementation_source_head") != implementation_source_head
    ):
        raise A0XCcpExecutorError("execution authorization differs from dossier identity")
    approved = authorization.get("approved_dossier_commitment")
    expected = canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping()
    if approved != expected:
        raise A0XCcpExecutorError("execution authorization does not bind the fixed dossier")
    contract_path = dossier.get("material_contract_path")
    if not isinstance(contract_path, str) or contract_path != "experiments/a0x-six-model/material-execution-contract.json":
        raise A0XCcpExecutorError("material contract locator is invalid")
    material_contract = _repository_file(root, contract_path)
    if authorization.get("material_contract_raw_sha256") != dossier.get("material_contract_raw_sha256") or sha256_file(material_contract) != dossier.get("material_contract_raw_sha256"):
        raise A0XCcpExecutorError("material contract bytes are not bound to the authorization")
    expected_paths = derive_runtime_paths(pair, source_head=source_head)
    if authorization.get("authorization_inlet_path") != expected_paths.authorization_path:
        raise A0XCcpExecutorError("authorization inlet is not pair-derived")
    # Schema Task5 makes this binding mandatory.  The conditional preserves
    # compatibility only while a sibling-owned schema migration is in flight;
    # when present it is already exact and never accepts a future content hash.
    preflight_binding = authorization.get("guard_preflight_observation")
    if preflight_binding is not None and preflight_binding != {
        "profile": "a0x-guard-preflight-observation-v1",
        "path": expected_paths.observation_directory + "guard-preflight-observation.json",
    }:
        raise A0XCcpExecutorError("guard preflight observation locator is not pair-derived")
    if authorization.get("max_guard_exec_count") != 1 or authorization.get("stop_boundary") != "after_one_sealed_target_read":
        raise A0XCcpExecutorError("one-shot guard authorization is invalid")
    if not isinstance(authorization.get("authorization_id"), str) or not authorization["authorization_id"]:
        raise A0XCcpExecutorError("authorization ID is missing")
    if not isinstance(authorization.get("attempt_id"), str) or not authorization["attempt_id"]:
        raise A0XCcpExecutorError("attempt ID is missing")
    try:
        launch = A0XGuardLaunch.from_mapping(_mapping(authorization, "guard_launch", "execution authorization"))
        validate_guard_launch_pair_binding(pair, launch)
    except A0XContractError as error:
        raise A0XCcpExecutorError("guard launch is invalid") from error
    if launch.source_head != source_head:
        raise A0XCcpExecutorError("guard launch source HEAD differs from authorization")
    ccp = authorization.get("ccp")
    if not isinstance(ccp, Mapping) or ccp.get("sha256") != launch.ccp_sha256:
        raise A0XCcpExecutorError("guard launch CCP identity differs from authorization")
    if _authorization_profile(authorization) == CURRENT_EXECUTION_AUTHORIZATION_PROFILE:
        try:
            evidence = validate_gate_a_evidence(
                _mapping(authorization, "gate_a_evidence", "execution authorization"),
            )
        except A0XContractError as error:
            raise A0XCcpExecutorError("Gate A evidence is invalid") from error
        if evidence["source_head"] != source_head:
            raise A0XCcpExecutorError("Gate A evidence source head differs from execution authorization")
    else:
        try:
            qualification = validate_qualification_evidence(_mapping(authorization, "qualification_evidence", "execution authorization"))
        except A0XContractError as error:
            raise A0XCcpExecutorError("qualification evidence is invalid") from error
        qualification_ccp = qualification["ccp"]
        if (
            qualification["qualified_source_head"] != source_head
            or qualification_ccp["binary_sha256"] != ccp.get("sha256")
            or qualification_ccp["source_commit"] != ccp.get("source_commit")
            or qualification_ccp["qualified_source_tree"] != ccp.get("qualified_source_tree")
            or qualification_ccp["version"] != ccp.get("version")
        ):
            raise A0XCcpExecutorError("qualification evidence differs from execution authorization")
    return launch


def _authorization_profile(authorization: Mapping[str, Any]) -> str:
    profile = authorization.get("commitment_profile")
    if profile not in {EXECUTION_AUTHORIZATION_PROFILE, CURRENT_EXECUTION_AUTHORIZATION_PROFILE}:
        raise A0XCcpExecutorError("execution authorization profile is unsupported")
    return profile


def _authorization_gate_a_evidence(authorization: Mapping[str, Any]) -> Mapping[str, Any]:
    if _authorization_profile(authorization) == CURRENT_EXECUTION_AUTHORIZATION_PROFILE:
        return _mapping(authorization, "gate_a_evidence", "execution authorization")
    return _mapping(authorization, "qualification_evidence", "execution authorization")


def _rehash_gate_a_at_boundary(root: Path, authorization: Mapping[str, Any], source_head: str) -> None:
    """Dispatch current five-file rehashing without widening the legacy loader."""
    if _authorization_profile(authorization) == CURRENT_EXECUTION_AUTHORIZATION_PROFILE:
        rehash_gate_a_evidence(
            repository_root=root,
            evidence=_mapping(authorization, "gate_a_evidence", "execution authorization"),
            source_head=source_head,
        )
        return
    qualification_path = derive_runtime_paths(
        PairBinding.from_mapping(_mapping(authorization, "pair_binding", "execution authorization")),
        source_head=source_head,
    ).qualification_receipt_path
    if qualification_path is None:  # pragma: no cover - checked source heads always derive it
        raise A0XCcpExecutorError("local qualification receipt path is unavailable")
    _validate_local_qualification_receipt(
        _repository_file(root, qualification_path),
        evidence=_mapping(authorization, "qualification_evidence", "execution authorization"),
        source_head=source_head,
    )


def _validate_runtime_mapping(
    value: Mapping[str, Any], *, root: Path, launch: A0XGuardLaunch,
    descriptor_path: Path, pair: PairBinding, source_head: str,
) -> tuple[Path, Path]:
    expected_keys = {"mapping_profile", "source_head", "repository_root", "pair_binding", "ccp", "python", "descriptor"}
    if not isinstance(value, Mapping) or set(value) != expected_keys or value.get("mapping_profile") != _MAPPING_PROFILE:
        raise A0XCcpExecutorError("runtime role mapping shape is invalid")
    if (
        value.get("source_head") != source_head or value.get("repository_root") != str(root)
        or value.get("pair_binding") != pair.as_mapping()
    ):
        raise A0XCcpExecutorError("runtime role mapping source identity drifted")
    ccp_path = _role_path(value.get("ccp"), role="ccp", expected_hash=launch.ccp_sha256)
    python_path = _role_path(value.get("python"), role="python", expected_hash=launch.python_sha256)
    descriptor = value.get("descriptor")
    if not isinstance(descriptor, Mapping) or set(descriptor) != {"path", "sha256"}:
        raise A0XCcpExecutorError("runtime role mapping descriptor binding is invalid")
    if descriptor.get("path") != launch.launch_descriptor_path or descriptor.get("sha256") != launch.launch_descriptor_sha256:
        raise A0XCcpExecutorError("runtime role mapping descriptor differs from public launch")
    if descriptor_path != _repository_file(root, str(descriptor["path"])):
        raise A0XCcpExecutorError("runtime descriptor path is invalid")
    _validate_file_hash(ccp_path, launch.ccp_sha256, "CCP executable")
    _validate_file_hash(python_path, launch.python_sha256, "Python executable")
    return ccp_path, python_path


def _validate_runtime_readiness_binding(
    descriptor: Mapping[str, Any], *, root: Path, pair: PairBinding, source_head: str,
) -> None:
    binding = descriptor.get("runtime_readiness")
    python = descriptor.get("python")
    if (
        not isinstance(binding, Mapping)
        or set(binding) != {"role", "path", "sha256"}
        or binding.get("role") != "readiness"
        or binding.get("path") != runtime_readiness_path(pair)
        or not isinstance(python, Mapping)
        or not isinstance(python.get("path"), str)
    ):
        raise A0XCcpExecutorError("runtime readiness binding is invalid")
    readiness_path = _repository_file(root, str(binding["path"]))
    raw = readiness_path.read_bytes()
    if _sha256_bytes(raw) != binding.get("sha256"):
        raise A0XCcpExecutorError("runtime readiness bytes drifted")
    try:
        validate_runtime_readiness_live(
            _strict_object(raw, "runtime readiness"), repository_root=root,
            source_head=source_head, pair=pair, python_path=Path(python["path"]),
        )
    except A0XRuntimeReadinessError as error:
        raise A0XCcpExecutorError("runtime readiness is invalid") from error


def _validate_local_qualification_receipt(
    path: Path, *, evidence: Mapping[str, Any], source_head: str,
) -> None:
    """Check local receipt raw bytes and semantic CCP identity separately."""
    raw = path.read_bytes()
    if _sha256_bytes(raw) != evidence.get("qualification_receipt_raw_sha256"):
        raise A0XCcpExecutorError("local qualification receipt raw SHA-256 differs")
    ccp = evidence.get("ccp")
    public = evidence.get("public_evidence")
    if not isinstance(ccp, Mapping) or not isinstance(public, Mapping) or not isinstance(public.get("commit"), str):
        raise A0XCcpExecutorError("local qualification receipt CCP binding is invalid")
    try:
        observed = qualification_evidence_from_receipt(
            raw,
            source_head=source_head,
            ccp_identity=ccp,
            public_evidence_commit=public["commit"],
        )
    except A0XCcpExecutorError:
        raise
    if observed != dict(evidence):
        raise A0XCcpExecutorError("local qualification receipt CCP/source/generation binding differs")


def qualification_evidence_from_receipt(
    receipt_raw: bytes,
    *,
    source_head: str,
    ccp_identity: Mapping[str, Any],
    public_evidence_commit: str,
) -> dict[str, Any]:
    """Extract public-safe qualification evidence without launching anything."""
    _revision(source_head, "qualification receipt source head")
    _revision(public_evidence_commit, "qualification public evidence commit")
    if not isinstance(ccp_identity, Mapping):
        raise A0XCcpExecutorError("qualification receipt CCP binding is invalid")
    binary_sha256 = ccp_identity.get("sha256", ccp_identity.get("binary_sha256"))
    source_commit = ccp_identity.get("source_commit")
    source_tree = ccp_identity.get("qualified_source_tree", ccp_identity.get("source_tree"))
    version = ccp_identity.get("version")
    if (
        ccp_identity.get("executable_name") != "commit-ci-preflight"
        or not isinstance(binary_sha256, str) or not _SHA256.fullmatch(binary_sha256)
        or not isinstance(source_commit, str) or not _REVISION.fullmatch(source_commit)
        or not isinstance(source_tree, str) or not _REVISION.fullmatch(source_tree)
        or not isinstance(version, str) or not re.fullmatch(r"commit-ci-preflight [^\s]+", version)
    ):
        raise A0XCcpExecutorError("qualification receipt CCP binding is invalid")
    envelope = _strict_object(receipt_raw, "local qualification receipt")
    if set(envelope) != {"receipt_id", "receipt"} or not isinstance(envelope.get("receipt"), Mapping):
        raise A0XCcpExecutorError("local qualification receipt envelope is invalid")
    receipt = envelope["receipt"]
    semantic_id = "sha256:" + _sha256_bytes(_canonical_json(receipt))
    if envelope.get("receipt_id") != semantic_id:
        raise A0XCcpExecutorError("local qualification receipt semantic ID differs")
    producer, repository, run = receipt.get("producer"), receipt.get("repository"), receipt.get("run")
    expected_version = version.removeprefix("commit-ci-preflight ") + "+matrix-v2-legacy-v1"
    if (
        receipt.get("schema_version") != "2.0" or receipt.get("overall_status") != "PASS"
        or receipt.get("incomplete_reason") is not None
        or producer != {"name": "commit-ci-preflight", "version": expected_version}
        or not isinstance(repository, Mapping) or repository.get("commit_sha") != source_head
        or repository.get("dirty") is not False
        or not isinstance(run, Mapping) or not isinstance(run.get("generation"), int)
        or isinstance(run.get("generation"), bool) or run["generation"] < 1
    ):
        raise A0XCcpExecutorError("local qualification receipt CCP/source/generation binding differs")
    evidence = {
        "artifact_class": "a0x-qualification-evidence",
        "evidence_profile": "a0x-qualification-evidence-v1",
        "qualification_receipt_id": semantic_id,
        "qualification_receipt_raw_sha256": _sha256_bytes(receipt_raw),
        "qualified_source_head": source_head,
        "generation": run["generation"],
        "ccp": {
            "executable_name": "commit-ci-preflight",
            "source_commit": source_commit,
            "qualified_source_tree": source_tree,
            "binary_sha256": binary_sha256,
            "version": version,
        },
        "public_evidence": {
            "branch": f"ccp-evidence/{source_head}",
            "path": ".ccp/receipt.json",
            "commit": public_evidence_commit,
        },
    }
    try:
        return validate_qualification_evidence(evidence)
    except A0XContractError as error:
        raise A0XCcpExecutorError("qualification evidence is invalid") from error


_GUARD_PREFLIGHT_ROLES = (
    "ccp_version", "resource_status", "admission_status", "git_source_state",
    "docker_context", "docker_active_count",
)


def _validate_guard_preflight(
    outputs: Sequence[GuardPreflightOutput], *, launch: A0XGuardLaunch,
    pair: PairBinding, source_head: str, ccp_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize exactly six configuration-free, read-only guard probes."""
    if not isinstance(outputs, Sequence) or len(outputs) != len(_GUARD_PREFLIGHT_ROLES):
        raise A0XCcpExecutorError("guard preflight output set is incomplete")
    rows: list[dict[str, Any]] = []
    by_role: dict[str, bytes] = {}
    for expected_role, output in zip(_GUARD_PREFLIGHT_ROLES, outputs, strict=True):
        if not isinstance(output, GuardPreflightOutput) or output.role != expected_role:
            raise A0XCcpExecutorError("guard preflight command roles differ from the fixed sequence")
        if output.exit_code != 0 or not isinstance(output.raw, bytes):
            raise A0XCcpExecutorError(f"guard preflight {expected_role} did not complete")
        by_role[expected_role] = output.raw
        rows.append({
            "role": expected_role,
            "exit_code": 0,
            "output_sha256": _sha256_bytes(output.raw),
            "output_bytes": len(output.raw),
        })
    version = _strict_text(by_role["ccp_version"], "CCP version")
    if version != ccp_identity.get("version"):
        raise A0XCcpExecutorError("guard preflight CCP version differs from authorization")
    resource = _resource_status_object(by_role["resource_status"])
    if resource.get("decision") != "admit":
        raise A0XCcpExecutorError("guard preflight resource decision is not Admit")
    admission = _strict_object(by_role["admission_status"], "guard admission status")
    slot = admission.get("slot")
    if admission.get("active") is not False or admission.get("queue_count") != 0 or not isinstance(slot, Mapping) or slot.get("state") != "free":
        raise A0XCcpExecutorError("guard preflight admission is not inactive with a free slot")
    if ccp_identity.get("sha256") == _ACTIVE_CCP_SHA256:
        _validate_active_guard_status(resource, admission)
    source = _strict_object(by_role["git_source_state"], "guard Git source state")
    if source != {"head": source_head, "clean": True}:
        raise A0XCcpExecutorError("guard preflight source HEAD is dirty or differs from authorization")
    context = _strict_text(by_role["docker_context"], "Docker context")
    if not context:
        raise A0XCcpExecutorError("guard preflight intended runtime is unavailable")
    try:
        active = by_role["docker_active_count"].decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise A0XCcpExecutorError("Docker active-container output is not UTF-8") from error
    if active:
        raise A0XCcpExecutorError("guard preflight has active containers")
    observation = {
        "artifact_class": "a0x-guard-preflight-observation",
        "observation_profile": "a0x-guard-preflight-observation-v1",
        "pair_binding": pair.as_mapping(),
        "source_head": source_head,
        "ccp": {
            "role": "ccp", "source_commit": ccp_identity.get("source_commit"),
            "qualified_source_tree": ccp_identity.get("qualified_source_tree"),
            "sha256": launch.ccp_sha256, "version": version,
        },
        "source": {"head": source_head, "clean": True},
        "resource": {"decision": "admit"},
        "admission": {"active": False, "queue_count": 0, "slot_state": "free"},
        "runtime": {"intended_runtime_responsive": True, "active_container_count": 0},
        "commands": rows,
    }
    _assert_public_safe_preflight(observation)
    return observation


def _validate_active_guard_status(resource: Mapping[str, Any], admission: Mapping[str, Any]) -> None:
    """Validate the active macos-v5 contract without treating static swap as a veto."""
    constants = {"schema_version": "1.0", "policy_version": "macos-v5", "platform": "macos",
                 "capability": "supported_enforced", "decision": "admit", "consecutive_soft_samples": 0}
    numbers = {"available_percent", "reclaimable_uncompressed_bytes", "compressor_occupied_bytes",
               "total_memory_bytes", "swap_used_bytes", "swap_total_bytes"}
    if set(resource) != set(constants) | numbers or any(resource.get(key) != value for key, value in constants.items()):
        raise A0XCcpExecutorError("active guard resource contract is incomplete or differs")
    if type(resource["consecutive_soft_samples"]) is not int:
        raise A0XCcpExecutorError("active guard resource counter is malformed")
    if any(isinstance(resource[key], bool) or not isinstance(resource[key], (int, float))
           or not math.isfinite(resource[key]) or resource[key] < 0 for key in numbers):
        raise A0XCcpExecutorError("active guard resource telemetry is malformed")
    if resource["available_percent"] < 20 or resource["available_percent"] > 100 or resource["reclaimable_uncompressed_bytes"] < 3 * 1024**3:
        raise A0XCcpExecutorError("active guard resource telemetry contradicts Admit")
    if resource["total_memory_bytes"] <= 0 or resource["reclaimable_uncompressed_bytes"] > resource["total_memory_bytes"] or resource["compressor_occupied_bytes"] > resource["total_memory_bytes"] or resource["swap_used_bytes"] > resource["swap_total_bytes"]:
        raise A0XCcpExecutorError("active guard resource telemetry is contradictory")
    if set(admission) != {"schema_version", "active", "queue_count", "ticket_ids", "slot", "queue_lock", "process_visibility_note"} or admission.get("schema_version") != "1.0" or admission.get("active") is not False or type(admission.get("queue_count")) is not int or admission["queue_count"] != 0 or admission.get("ticket_ids") != [] or not isinstance(admission.get("process_visibility_note"), str):
        raise A0XCcpExecutorError("active guard admission evidence is incomplete or busy")
    for key in ("slot", "queue_lock"):
        lock = admission[key]
        if not isinstance(lock, Mapping) or set(lock) != {"kind", "state", "owner_run_id", "acquired_at_unix_seconds", "heartbeat_at_unix_seconds", "lease_state"} or lock.get("kind") != key or lock.get("state") != "free" or lock.get("lease_state") != "not_applicable" or any(lock.get(field) is not None for field in ("owner_run_id", "acquired_at_unix_seconds", "heartbeat_at_unix_seconds")):
            raise A0XCcpExecutorError("active guard admission lock is not demonstrably free")


def _resource_status_object(raw: bytes) -> dict[str, Any]:
    """Native telemetry may contain decimal percentages; commitments may not."""
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError("duplicate telemetry key")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("non-finite telemetry constant")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeError, ValueError, TypeError) as error:
        raise A0XCcpExecutorError("guard resource status is malformed native JSON") from error
    if not isinstance(value, dict):
        raise A0XCcpExecutorError("guard resource status is not an object")
    return value


def _strict_text(raw: bytes, label: str) -> str:
    try:
        text = raw.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise A0XCcpExecutorError(f"{label} output is not UTF-8") from error
    if not text or "\n" in text or "\r" in text:
        raise A0XCcpExecutorError(f"{label} output is not one strict line")
    return text


def _strict_executable_version(raw: bytes, role: str, expected_version: str) -> str:
    if role != "github_cli_verifier":
        return _strict_text(raw, f"{role} executable version")
    match = re.fullmatch(
        r"gh version ([0-9]+\.[0-9]+\.[0-9]+) \([0-9]{4}-[0-9]{2}-[0-9]{2}\)",
        expected_version,
    )
    if match is None:
        raise A0XCcpExecutorError("github_cli_verifier expected version is invalid")
    expected_output = (
        expected_version + "\nhttps://github.com/cli/cli/releases/tag/v" + match.group(1) + "\n"
    ).encode("ascii")
    if raw != expected_output:
        raise A0XCcpExecutorError("github_cli_verifier executable version output differs")
    return expected_version


def _assert_public_safe_preflight(value: Mapping[str, Any]) -> None:
    forbidden_keys = {"argv", "path", "raw", "stdout", "stderr", "environment", "container_id", "local_path"}
    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            if set(item).intersection(forbidden_keys):
                raise A0XCcpExecutorError("public guard preflight observation leaks a private field")
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, str) and (item.startswith(("/", "~")) or "file://" in item.lower()):
            raise A0XCcpExecutorError("public guard preflight observation leaks a local locator")
    walk(value)


def _write_guard_preflight_observation(root: Path, directory_relative: str, observation: Mapping[str, Any]) -> str:
    directory = _repository_file_for_write(root, directory_relative)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "guard-preflight-observation.json"
    _exclusive_write(path, _canonical_json(observation), "guard preflight observation")
    return path.relative_to(root).as_posix()


def _role_path(value: Any, *, role: str, expected_hash: str) -> Path:
    if not isinstance(value, Mapping) or set(value) != {"role", "path", "sha256"} or value.get("role") != role:
        raise A0XCcpExecutorError(f"runtime role mapping {role} binding is invalid")
    if value.get("sha256") != expected_hash or not isinstance(value.get("path"), str):
        raise A0XCcpExecutorError(f"runtime role mapping {role} hash is invalid")
    path = Path(value["path"])
    if not path.is_absolute() or "\x00" in value["path"]:
        raise A0XCcpExecutorError(f"runtime role mapping {role} path is invalid")
    try:
        return path.resolve(strict=True)
    except OSError as error:
        raise A0XCcpExecutorError(f"runtime role mapping {role} executable is unavailable") from error


def _materialize_argv(
    launch: A0XGuardLaunch, *, ccp_path: Path, python_path: Path, child_path: Path,
) -> tuple[str, ...]:
    mapping = {
        "{CCP}": str(ccp_path), "{PYTHON}": str(python_path),
        "{CHILD}": str(child_path), "{DESCRIPTOR}": launch.launch_descriptor_path,
    }
    try:
        argv = tuple(mapping.get(token, token) for token in launch.argv_template)
    except TypeError as error:  # pragma: no cover - parsed contract has strings
        raise A0XCcpExecutorError("guard argv template cannot be materialized") from error
    if any(token.startswith("{") or token.endswith("}") for token in argv):
        raise A0XCcpExecutorError("guard argv template retained an unresolved token")
    if argv[:3] != (str(ccp_path), "guard", "exec") or "--" not in argv:
        raise A0XCcpExecutorError("guard argv is not the frozen shell-free launch")
    return argv


def _frozen_environment(launch: A0XGuardLaunch) -> dict[str, str]:
    environment = dict(item.split("=", 1) for item in launch.environment_template)
    if len(environment) != len(launch.environment_template):
        raise A0XCcpExecutorError("guard environment template is not exact")
    return environment


def _coordination_environment() -> dict[str, str]:
    """Minimal private environment shared by guard and its status probes."""
    home = os.environ.get("HOME")
    if not isinstance(home, str) or not Path(home).is_absolute() or ".." in Path(home).parts or home == "/":
        raise A0XCcpExecutorError("native persistent coordination HOME is unavailable")
    return {"HOME": home, "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}


@contextmanager
def _private_gh_environment():
    """Own one credential-free HOME/XDG tree for a complete GH transaction."""
    with TemporaryDirectory(prefix="a0x-gh-private-") as temporary:
        root = Path(temporary).resolve(strict=True)
        if not _private_owned_directory(root):
            raise A0XCcpExecutorError("private GH transaction root is not owned and mode 0700")
        environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
        for key, name in (
            ("HOME", "home"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_CACHE_HOME", "cache"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_STATE_HOME", "state"),
        ):
            path = root / name
            try:
                path.mkdir(mode=0o700)
            except OSError as error:
                raise A0XCcpExecutorError("private GH transaction directory could not be created") from error
            environment[key] = str(path)
        if not _valid_private_gh_environment(environment):
            raise A0XCcpExecutorError("private GH transaction environment is invalid")
        yield environment


def _private_owned_directory(path: Path) -> bool:
    try:
        metadata = path.lstat()
        return (
            path.is_absolute()
            and path.resolve(strict=True) == path
            and stat.S_ISDIR(metadata.st_mode)
            and metadata.st_uid == os.getuid()
            and stat.S_IMODE(metadata.st_mode) == 0o700
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def _valid_private_gh_environment(environment: Mapping[str, str] | None) -> bool:
    if not isinstance(environment, Mapping) or set(environment) != {
        "PATH", "LC_ALL", "HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
    }:
        return False
    if environment.get("PATH") != "/usr/bin:/bin" or environment.get("LC_ALL") != "C":
        return False
    home = environment.get("HOME")
    if not isinstance(home, str) or not home:
        return False
    root = Path(home).parent
    expected = {
        "HOME": root / "home",
        "XDG_CONFIG_HOME": root / "config",
        "XDG_CACHE_HOME": root / "cache",
        "XDG_DATA_HOME": root / "data",
        "XDG_STATE_HOME": root / "state",
    }
    if any(environment.get(key) != str(path) for key, path in expected.items()):
        return False
    return _private_owned_directory(root) and all(_private_owned_directory(path) for path in expected.values())


def _classify_outer_exit(result: ProcessResult) -> str:
    if result.timed_out or result.returncode == 124:
        return "timeout"
    if result.returncode == 0:
        return "completed"
    return {
        5: "admission_rejected",
        6: "resource_rejected",
        70: "cleanup_or_internal",
        130: "cancelled",
    }.get(result.returncode, f"child_exit_{result.returncode}")


def _terminal_observation(
    *, source_head: str, pair: PairBinding, dossier: str, launch: A0XGuardLaunch,
    result: ProcessResult | None, classification: str, recovery_required: bool,
    error_type: str | None = None, child_terminal_status: str | None = None,
    authorization_raw_sha256: str, authorization_commitment: Mapping[str, Any],
    pre_run_path: str, pre_run_raw_sha256: str,
    guard_preflight_path: str, guard_preflight_raw_sha256: str,
) -> dict[str, Any]:
    observation: dict[str, Any] = {
        "artifact_class": "a0x-guard-terminal-observation",
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "fixed_dossier": dossier,
        "authorization_raw_sha256": authorization_raw_sha256,
        "authorization_commitment": dict(authorization_commitment),
        "guard_launch_sha256": _sha256_bytes(_canonical_json(launch.as_mapping())),
        "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
        "internal_budget_seconds": INTERNAL_BUDGET_SECONDS,
        "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
        "admission_timeout_seconds": ADMISSION_TIMEOUT_SECONDS,
        "outer_exit_classification": classification,
        "recovery_required": recovery_required,
        "child_terminal_status": child_terminal_status,
        "pre_run_observation_path": pre_run_path,
        "pre_run_observation_raw_sha256": pre_run_raw_sha256,
        "guard_preflight_observation_path": guard_preflight_path,
        "guard_preflight_observation_raw_sha256": guard_preflight_raw_sha256,
    }
    if result is None:
        observation["process"] = None
        observation["error_type"] = error_type
    else:
        observation["process"] = {
            "returncode": result.returncode,
            "timed_out": result.timed_out,
            "stdout_sha256": result.stdout_sha256,
            "stdout_bytes": result.stdout_bytes,
            "stderr_sha256": result.stderr_sha256,
            "stderr_bytes": result.stderr_bytes,
        }
    return observation


def _pre_run_observation(
    *, source_head: str, pair: PairBinding, dossier: str, authorization_raw: bytes,
    launch: A0XGuardLaunch, claim_path: str, authorization_commitment: Mapping[str, Any], gate_a_evidence: Any,
    argv: Sequence[str], guard_preflight_path: str, guard_preflight_raw_sha256: str,
) -> dict[str, Any]:
    """Record the private process binding before the OS can start a child."""
    if not isinstance(gate_a_evidence, Mapping):
        raise A0XCcpExecutorError("Gate A evidence is unavailable for pre-run observation")
    return {
        "artifact_class": "a0x-guard-pre-run-observation",
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "fixed_dossier": dossier,
        "claim_path": claim_path,
        "authorization_raw_sha256": _sha256_bytes(authorization_raw),
        "authorization_commitment": dict(authorization_commitment),
        "gate_a_verification_receipt_raw_sha256": (
            gate_a_evidence.get("verification_receipt", {}).get("sha256")
            if isinstance(gate_a_evidence.get("verification_receipt"), Mapping)
            else gate_a_evidence.get("qualification_receipt_raw_sha256")
        ),
        # Historical observations retain their legacy fields; current Gate A
        # observations leave them absent rather than manufacturing CCP meaning.
        "qualification_receipt_id": gate_a_evidence.get("qualification_receipt_id"),
        "qualification_receipt_raw_sha256": gate_a_evidence.get("qualification_receipt_raw_sha256"),
        "guard_launch_sha256": _sha256_bytes(_canonical_json(launch.as_mapping())),
        "guard_preflight_observation_path": guard_preflight_path,
        "guard_preflight_observation_raw_sha256": guard_preflight_raw_sha256,
        # This line is deliberately private in the ignored runtime inlet.  The
        # terminal observation retains only its hash, not local paths.
        "resolved_argv": list(argv),
        "resolved_argv_sha256": _sha256_bytes(_canonical_json({"argv": list(argv)})),
        "guard_timeout_seconds": OUTER_TIMEOUT_SECONDS,
        "supervision_timeout_seconds": _SUPERVISION_TIMEOUT_SECONDS,
    }


def _assert_bound_authorization_and_contract(
    *, authorization_path: Path, authorization_raw: bytes, authorization_commitment: Mapping[str, Any],
    material_contract_path: Path, material_contract_raw: bytes,
) -> None:
    """Reject a changed trust root before claim creation or process launch."""
    try:
        observed_authorization_raw = authorization_path.read_bytes()
        observed_contract_raw = material_contract_path.read_bytes()
    except OSError as error:
        raise A0XCcpExecutorError("bound runtime document is unavailable") from error
    if observed_authorization_raw != authorization_raw:
        raise A0XCcpExecutorError("execution authorization bytes drifted")
    try:
        observed_authorization = _strict_object(observed_authorization_raw, "execution authorization")
        observed_commitment = canonical_commitment(
            observed_authorization, _authorization_profile(observed_authorization),
        ).as_mapping()
    except (A0XCcpExecutorError, A0XContractError, TypeError, ValueError) as error:
        raise A0XCcpExecutorError("execution authorization commitment is invalid") from error
    if observed_commitment != dict(authorization_commitment):
        raise A0XCcpExecutorError("execution authorization commitment drifted")
    if observed_contract_raw != material_contract_raw:
        raise A0XCcpExecutorError("material contract bytes drifted")


def _write_pre_run_observation(root: Path, directory_relative: str, observation: Mapping[str, Any]) -> str:
    directory = _repository_file_for_write(root, directory_relative)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "pre-run-observation.json"
    _exclusive_write(path, _canonical_json(observation), "pre-run observation")
    return path.relative_to(root).as_posix()


def _write_terminal_observation(root: Path, directory_relative: str, observation: Mapping[str, Any]) -> str:
    directory = _repository_file_for_write(root, directory_relative)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "terminal-observation.json"
    raw = _canonical_json(observation)
    _exclusive_write(path, raw, "terminal observation")
    return path.relative_to(root).as_posix()


def _exclusive_write(path: Path, raw: bytes, label: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise A0XCcpExecutorError(f"{label} already exists; recovery is fail-closed") from error
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise A0XCcpExecutorError(f"{label} could not be durably written") from error


def _reserve_claim(path: Path, payload: Mapping[str, Any]) -> None:
    """Seal this adapter's own opaque one-shot claim without legacy callbacks."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw = _canonical_json(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise A0XCcpExecutorError("attempt claim already exists; retry is forbidden") from error
    except OSError as error:
        raise A0XCcpExecutorError("attempt claim could not be reserved") from error
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise A0XCcpExecutorError("attempt claim could not be durably sealed") from error


class _SubprocessExecutor:
    """Shell-free adapter with bounded streaming capture and grace supervision.

    CCP owns the child timeout through the exact ``--timeout-seconds 3600``
    token.  This adapter waits an additional cleanup margin so it cannot kill
    CCP while CCP is sealing its own terminal state.  Output is continuously
    drained in fixed chunks; only a fixed-size prefix remains in memory and no
    unbounded raw stdout/stderr file is created.
    """

    def run(self, argv: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout_seconds: int, capture_limit_bytes: int) -> ProcessResult:
        if timeout_seconds != _SUPERVISION_TIMEOUT_SECONDS:
            raise A0XCcpExecutorError("subprocess supervision timeout must preserve CCP cleanup margin")
        process = subprocess.Popen(
            list(argv), cwd=str(cwd), env=dict(env), shell=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout = _StreamingCapture(capture_limit_bytes)
        stderr = _StreamingCapture(capture_limit_bytes)
        stdout_thread = threading.Thread(target=stdout.drain, args=(process.stdout,), daemon=True)
        stderr_thread = threading.Thread(target=stderr.drain, args=(process.stderr,), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                process.wait(timeout=CLEANUP_MARGIN_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        stdout_thread.join(timeout=CLEANUP_MARGIN_SECONDS)
        stderr_thread.join(timeout=CLEANUP_MARGIN_SECONDS)
        if stdout_thread.is_alive() or stderr_thread.is_alive():
            raise A0XCcpExecutorError("bounded output drain did not terminate")
        return ProcessResult(
            returncode=124 if timed_out else int(process.returncode), timed_out=timed_out,
            stdout_sha256=stdout.sha256, stdout_bytes=stdout.length, stdout_prefix=stdout.prefix,
            stderr_sha256=stderr.sha256, stderr_bytes=stderr.length, stderr_prefix=stderr.prefix,
        )


class _StreamingCapture:
    """Drain a pipe without retaining more than its declared prefix cap."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._digest = hashlib.sha256()
        self._length = 0
        self._prefix = bytearray()

    def drain(self, stream: Any) -> None:
        if stream is None:
            return
        try:
            while True:
                block = stream.read(64 * 1024)
                if not block:
                    return
                self._digest.update(block)
                self._length += len(block)
                if len(self._prefix) < self._limit:
                    self._prefix.extend(block[: self._limit - len(self._prefix)])
        finally:
            stream.close()

    @property
    def sha256(self) -> str:
        return self._digest.hexdigest()

    @property
    def length(self) -> int:
        return self._length

    @property
    def prefix(self) -> bytes:
        return bytes(self._prefix)


def _parse_child_terminal(raw: bytes) -> str | None:
    try:
        lines = raw.decode("utf-8").splitlines()
        if len(lines) != 1:
            return None
        value = strict_json_object(lines[0].encode("utf-8"))
        if set(value) != {"artifact_class", "exit_class", "terminal_status"}:
            return None
        if value.get("artifact_class") != _CHILD_TERMINAL_CLASS or value.get("exit_class") != "completed":
            return None
        status = value.get("terminal_status")
        return status if status in {"positive", "null", "non_interpretable", "incompatible", "failed"} else None
    except (UnicodeDecodeError, A0XContractError):
        return None


def _parse_vertical_child_terminal(
    raw: bytes,
    *,
    expected_source: Mapping[str, str],
    expected_pair: Mapping[str, Any],
    expected_authorization_id: str,
    expected_attempt_id: str,
    expected_qualification_context: Literal["production", "synthetic-target-free"],
    terminal_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Parse only the exact, context-bound v1 vertical child terminal wire.

    This parser is intentionally separate from the historical child parser.
    Invalid or unbound bytes return ``None`` so the outer guard records a
    recovery-required engineering outcome rather than inferring a result.
    """
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or raw.endswith(b"\n\n") or b"\r" in raw:
        return None
    body = raw[:-1]
    if not body or b"\n" in body:
        return None
    try:
        value = strict_json_object(body)
        canonical = _canonical_json(value)
        if canonical != body:
            return None
        _validate_vertical_raw_schema(
            value, "a0x-vertical-child-terminal-v1.schema.json", "vertical child terminal",
            schema_document=terminal_schema,
        )
        pair = PairBinding.from_mapping(value["pair_binding"])
    except (A0XCcpExecutorError, A0XContractError, KeyError, TypeError, ValueError):
        return None
    if (
        value.get("exit_class") != "completed"
        or value.get("qualified_source") != dict(expected_source)
        or pair.as_mapping() != dict(expected_pair)
        or value.get("authorization_id") != expected_authorization_id
        or value.get("attempt_id") != expected_attempt_id
        or value.get("qualification_context") != expected_qualification_context
    ):
        return None
    if expected_qualification_context == "synthetic-target-free":
        if (
            value.get("reached_frontier") != "validated_graph"
            or value.get("scientific_outcome") is not None
            or value.get("terminal_package") is not None
        ):
            return None
    elif (
        expected_qualification_context != "production"
        or value.get("reached_frontier") != "sealed"
        or value.get("scientific_outcome") not in {"positive", "null", "non_interpretable", "incompatible", "failed"}
        or not isinstance(value.get("terminal_package"), Mapping)
        or not _valid_vertical_terminal_package_reference(
            value.get("terminal_package"), expected_pair,
        )
    ):
        return None
    return value


def _valid_vertical_terminal_package_reference(
    value: Any, expected_pair: Mapping[str, Any],
) -> bool:
    """Check reference shape/path; parent must independently verify package bytes."""
    if not isinstance(value, Mapping) or set(value) != {
        "package_relative_path", "manifest_raw_sha256", "root_receipt_raw_sha256",
    }:
        return False
    return (
        value.get("package_relative_path") == expected_pair.get("output_path")
        and isinstance(value.get("manifest_raw_sha256"), str)
        and _SHA256.fullmatch(value["manifest_raw_sha256"]) is not None
        and isinstance(value.get("root_receipt_raw_sha256"), str)
        and _SHA256.fullmatch(value["root_receipt_raw_sha256"]) is not None
    )


def _validate_process_result(value: ProcessResult) -> None:
    if not isinstance(value.returncode, int) or isinstance(value.returncode, bool):
        raise A0XCcpExecutorError("guard process return code is invalid")
    if (
        not isinstance(value.timed_out, bool)
        or value.stdout_bytes < 0 or value.stderr_bytes < 0
        or value.stdout_bytes < len(value.stdout_prefix)
        or value.stderr_bytes < len(value.stderr_prefix)
    ):
        raise A0XCcpExecutorError("guard process terminal metadata is invalid")
    for digest in (value.stdout_sha256, value.stderr_sha256):
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise A0XCcpExecutorError("guard process terminal digest is invalid")
    if len(value.stdout_prefix) > _CAPTURE_LIMIT_BYTES or len(value.stderr_prefix) > _CAPTURE_LIMIT_BYTES:
        raise A0XCcpExecutorError("guard process capture exceeded the fixed limit")


def _vertical_dossier_sha256(
    package: Mapping[str, Any], *, root: Path, relative_dossier: str,
) -> str:
    """Rebind the loader's dossier digest before common material processing."""
    try:
        manifest = _mapping(package, "manifest", "vertical slice package")
        members = _mapping(manifest, "members", "vertical slice manifest")
        binding = _mapping(members, "approval-dossier.json", "vertical slice manifest")
        digest = binding.get("sha256")
    except A0XCcpExecutorError:
        raise A0XCcpExecutorError("vertical slice dossier binding is invalid") from None
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise A0XCcpExecutorError("vertical slice dossier binding is invalid")
    try:
        raw = _repository_file(root, relative_dossier).read_bytes()
    except A0XCcpExecutorError:
        raise A0XCcpExecutorError("vertical slice dossier binding is invalid") from None
    if _sha256_bytes(raw) != digest:
        raise A0XCcpExecutorError("vertical slice dossier bytes drifted")
    return digest


def _fixed_dossier_path(value: str) -> str:
    if not isinstance(value, str) or not value.endswith(".json"):
        raise A0XCcpExecutorError("fixed dossier path is invalid")
    return _relative_runtime_path(value)


def _assert_fixed_dossier(relative: str) -> None:
    if relative not in set(planned_material_dossiers().values()):
        raise A0XCcpExecutorError("dossier path is not one of the exact twelve planned targets")


def _relative_runtime_path(value: Any) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\x00" in value:
        raise A0XCcpExecutorError("repository-relative path is invalid")
    path = Path(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise A0XCcpExecutorError("repository-relative path contains traversal")
    return path.as_posix()


def _repository_file(root: Path, relative: str) -> Path:
    path = root / _relative_runtime_path(relative)
    current = path
    while current != root:
        if current.is_symlink():
            raise A0XCcpExecutorError("repository binding uses a symlink")
        current = current.parent
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise A0XCcpExecutorError("repository binding is unavailable") from error
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise A0XCcpExecutorError("repository binding is not a regular file")
    return resolved


def _unique_repository_file(root: Path, relative: Any, label: str) -> Path:
    """Return one regular, non-aliased repository file without following links."""
    path = root / _relative_runtime_path(relative)
    current = path
    while current != root:
        try:
            status = current.lstat()
        except OSError as error:
            raise A0XCcpExecutorError(f"{label} is unavailable") from error
        if stat.S_ISLNK(status.st_mode):
            raise A0XCcpExecutorError(f"{label} uses a symlink")
        current = current.parent
    try:
        status = path.lstat()
    except OSError as error:
        raise A0XCcpExecutorError(f"{label} is unavailable") from error
    if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
        raise A0XCcpExecutorError(f"{label} is not an independent regular file")
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise A0XCcpExecutorError(f"{label} escapes the repository") from error
    return path


def _repository_file_for_write(root: Path, relative: str) -> Path:
    path = root / _relative_runtime_path(relative)
    current = path.parent
    while current != root:
        if os.path.lexists(current) and current.is_symlink():
            raise A0XCcpExecutorError("runtime output parent uses a symlink")
        current = current.parent
    return path


def _strict_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        return strict_json_object(raw)
    except A0XContractError as error:
        raise A0XCcpExecutorError(f"{label} bytes are not strict JSON") from error


def _mapping(value: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise A0XCcpExecutorError(f"{label} {key} is invalid")
    return item


def _revision(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise A0XCcpExecutorError(f"{label} is invalid")
    return value


def _validate_file_hash(path: Path, expected: str, label: str) -> None:
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected) or sha256_file(path) != expected:
        raise A0XCcpExecutorError(f"{label} bytes drifted")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


__all__ = [
    "A0XCcpExecutorError", "GuardPreflightOutput", "GuardPreflightProducer",
    "ProcessExecutor", "ProcessResult", "SubprocessGuardPreflightProducer",
    "launch_fixed_dossier", "launch_vertical_runtime_package", "launch_vertical_slice_dossier", "qualification_evidence_from_receipt", "rehash_gate_a_evidence",
    "vertical_execution_authorization_path",
    "runtime_mapping_path",
]
