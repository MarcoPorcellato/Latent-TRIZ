"""Prepare one immutable, target-free A0X runtime binding bundle.

Preparation is deliberately limited to public documents and executable bytes.
It never starts a process, imports material libraries, reads a sealed target, or
opens a model.  Its three documents form an acyclic dependency chain:
descriptor -> authorization -> local role mapping.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .a0x_ccp_executor import (
    A0XCcpExecutorError,
    qualification_evidence_from_receipt,
    runtime_mapping_path,
)
from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    PairBinding,
    canonical_commitment,
    sha256_file,
    strict_json_object,
)
from .a0x_material_contract import (
    ADMISSION_TIMEOUT_SECONDS,
    CLEANUP_MARGIN_SECONDS,
    DESCRIPTOR_PROFILE,
    INTERNAL_BUDGET_SECONDS,
    MATERIAL_CONTRACT_PATH,
    MEMORY_LIMIT_BYTES,
    OUTER_TIMEOUT_SECONDS,
    derive_runtime_paths,
)
from .a0x_runner import planned_material_dossiers
from .validator import validate


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")
_MAPPING_PROFILE = "a0x-runtime-role-mapping-v1"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MATERIAL_CONTRACT_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-material-execution-contract.schema.json"
_ENVIRONMENT = (
    "HF_HUB_OFFLINE=1",
    "TRANSFORMERS_OFFLINE=1",
    "HF_DATASETS_OFFLINE=1",
    "TOKENIZERS_PARALLELISM=false",
    "PYTHONNOUSERSITE=1",
)


class A0XRuntimeBundleError(RuntimeError):
    """A target-free runtime preparation binding was not exact."""


@dataclass(frozen=True)
class RuntimePreparationRequest:
    fixed_dossier: str
    qualification_receipt: Path
    ccp_executable: Path
    python_executable: Path
    public_evidence_commit: str
    authorization_id: str
    attempt_id: str


@dataclass(frozen=True)
class _ValidatedPreparationInputs:
    ccp_path: Path
    python_path: Path
    child_path: Path
    ccp_sha256: str
    python_sha256: str
    child_sha256: str
    contract_sha256: str
    ccp_identity: Mapping[str, Any]
    qualification_evidence: Mapping[str, Any]
    descriptor_path: str


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Serialize one public document in its single permitted representation."""
    try:
        return json.dumps(
            dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("runtime bundle document is not canonical JSON") from error


def prepare_runtime_bundle(
    root: Path,
    request: RuntimePreparationRequest,
    *,
    source_state_probe: Callable[[], tuple[str, bool]],
    ccp_version_probe: Callable[[Path], str],
) -> dict[str, Any]:
    """Prepare the exact v2 bundle without accessing material resources."""
    repository = Path(root).resolve(strict=True)
    source_head, source_clean = _source_state(source_state_probe)
    if not source_clean:
        raise A0XRuntimeBundleError("runtime preparation requires a clean checkout")
    dossier, pair = _load_fixed_dossier(repository, request.fixed_dossier)
    inputs = _validate_preparation_inputs(
        repository, request, dossier=dossier, pair=pair, source_head=source_head,
        ccp_version_probe=ccp_version_probe,
    )
    descriptor = _build_descriptor(
        repository, pair, source_head, inputs.python_path, inputs.child_path, inputs.contract_sha256,
    )
    descriptor_raw = canonical_json_bytes(descriptor)
    descriptor_sha256 = hashlib.sha256(descriptor_raw).hexdigest()
    authorization = _build_authorization(
        dossier, pair, source_head, descriptor_sha256, inputs.qualification_evidence,
        inputs.ccp_identity, inputs.python_sha256, inputs.child_sha256,
        request.authorization_id, request.attempt_id,
    )
    mapping = _build_mapping(
        repository, pair, source_head, inputs.ccp_path, inputs.python_path,
        inputs.descriptor_path, descriptor_sha256,
    )
    if _source_state(source_state_probe) != (source_head, True):
        raise A0XRuntimeBundleError("runtime preparation source state drifted before output")
    return _write_and_verify_bundle(repository, pair, source_head, descriptor, authorization, mapping)


def _load_fixed_dossier(root: Path, relative: str) -> tuple[dict[str, Any], PairBinding]:
    """Load exactly one approved dossier from the fixed twelve-target set."""
    if _relative_path(relative, "fixed dossier") not in set(planned_material_dossiers().values()):
        raise A0XRuntimeBundleError("fixed dossier is not an exact planned material dossier")
    try:
        dossier = strict_json_object(_repository_file(root, relative).read_bytes())
        canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE)
        pair = PairBinding.from_mapping(_mapping(dossier, "pair_binding", "dossier"))
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("fixed dossier is not a valid approval dossier") from error
    expected = derive_runtime_paths(pair).authorization_path
    if dossier.get("runtime_authorization_path") != expected:
        raise A0XRuntimeBundleError("fixed dossier authorization path is not pair-derived")
    return dossier, pair


def _validate_preparation_inputs(
    root: Path,
    request: RuntimePreparationRequest,
    *,
    dossier: Mapping[str, Any],
    pair: PairBinding,
    source_head: str,
    ccp_version_probe: Callable[[Path], str],
) -> _ValidatedPreparationInputs:
    """Bind every input byte before any runtime output can be created."""
    _revision(source_head, "source HEAD")
    _preflight_output_paths(root, pair, source_head)
    _revision(request.public_evidence_commit, "public evidence commit")
    _identifier(request.authorization_id, "authorization ID")
    _identifier(request.attempt_id, "attempt ID")
    contract_path = _repository_file(root, MATERIAL_CONTRACT_PATH)
    contract_raw = contract_path.read_bytes()
    contract_sha256 = hashlib.sha256(contract_raw).hexdigest()
    if dossier.get("material_contract_path") != MATERIAL_CONTRACT_PATH or dossier.get("material_contract_raw_sha256") != contract_sha256:
        raise A0XRuntimeBundleError("fixed dossier material contract bytes are not exact")
    try:
        contract = strict_json_object(contract_raw)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("material contract bytes are not strict JSON") from error
    _validate_material_contract_schema(contract)
    ccp_identity = _ccp_identity(contract)
    ccp_path = _external_executable(request.ccp_executable, "CCP executable")
    ccp_sha256 = sha256_file(ccp_path)
    if ccp_sha256 != ccp_identity["sha256"]:
        raise A0XRuntimeBundleError("CCP executable bytes differ from material contract")
    if ccp_version_probe(ccp_path) != ccp_identity["version"]:
        raise A0XRuntimeBundleError("CCP executable version differs from material contract")
    python_path = _external_executable(request.python_executable, "Python executable")
    child_path = _repository_file(root, "scripts/a0x_material_child.py")
    expected_receipt = derive_runtime_paths(pair, source_head=source_head).qualification_receipt_path
    if expected_receipt is None or _external_file(request.qualification_receipt, "qualification receipt") != _repository_file(root, expected_receipt):
        raise A0XRuntimeBundleError("qualification receipt path is not source-derived")
    qualification_raw = _repository_file(root, expected_receipt).read_bytes()
    try:
        qualification = qualification_evidence_from_receipt(
            qualification_raw,
            source_head=source_head,
            ccp_identity=ccp_identity,
            public_evidence_commit=request.public_evidence_commit,
        )
    except A0XCcpExecutorError as error:
        raise A0XRuntimeBundleError("qualification receipt is invalid") from error
    descriptor_path = derive_runtime_paths(pair).launch_descriptor_path
    return _ValidatedPreparationInputs(
        ccp_path=ccp_path,
        python_path=python_path,
        child_path=child_path,
        ccp_sha256=ccp_sha256,
        python_sha256=sha256_file(python_path),
        child_sha256=sha256_file(child_path),
        contract_sha256=contract_sha256,
        ccp_identity=ccp_identity,
        qualification_evidence=qualification,
        descriptor_path=descriptor_path,
    )


def _build_descriptor(
    root: Path,
    pair: PairBinding,
    source_head: str,
    python_path: Path,
    child_path: Path,
    contract_sha256: str,
) -> dict[str, Any]:
    """Construct a descriptor that has no authorization-byte dependency."""
    if child_path != _repository_file(root, "scripts/a0x_material_child.py"):
        raise A0XRuntimeBundleError("child script is not the fixed repository child")
    return {
        "descriptor_profile": DESCRIPTOR_PROFILE,
        "source_head": source_head,
        "cwd_kind": "repository_root",
        "pair_binding": pair.as_mapping(),
        "child_script": {
            "role": "child", "path": "scripts/a0x_material_child.py", "sha256": sha256_file(child_path),
        },
        "python": {"role": "python", "path": str(python_path), "sha256": sha256_file(python_path)},
        "environment_template": list(_ENVIRONMENT),
        "authorization_reference": {
            "role": "authorization", "path": derive_runtime_paths(pair).authorization_path,
        },
        "material_contract": {
            "role": "material_contract", "path": MATERIAL_CONTRACT_PATH, "sha256": contract_sha256,
        },
        "execution": {
            "network": "offline", "generation": "forbidden", "trust_remote_code": False,
            "device": "cpu", "dtype": "float32", "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
            "internal_budget_seconds": INTERNAL_BUDGET_SECONDS, "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
        },
    }


def _build_authorization(
    dossier: Mapping[str, Any],
    pair: PairBinding,
    source_head: str,
    descriptor_sha256: str,
    qualification_evidence: Mapping[str, Any],
    ccp_identity: Mapping[str, Any],
    python_sha256: str,
    child_sha256: str,
    authorization_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    """Bind the completed descriptor, receipt evidence, and fixed guard launch."""
    _digest(descriptor_sha256, "descriptor SHA-256")
    _digest(python_sha256, "Python SHA-256")
    _digest(child_sha256, "child SHA-256")
    paths = derive_runtime_paths(pair)
    authorization = {
        "artifact_class": "a0x-execution-authorization",
        "commitment_profile": EXECUTION_AUTHORIZATION_PROFILE,
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": [],
        "pair_binding": pair.as_mapping(),
        "authorization_status": "authorized",
        "approved_dossier_commitment": canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping(),
        "repository": "MarcoPorcellato/Latent-TRIZ",
        "implementation_source_head": dossier["implementation_source_head"],
        "source_head": source_head,
        "material_contract_raw_sha256": dossier["material_contract_raw_sha256"],
        "ccp": dict(ccp_identity),
        "authorization_inlet_path": paths.authorization_path,
        "guard_launch": {
            "launch_profile": "a0x-guard-launch-v2",
            "ccp": {"role": "ccp", "sha256": ccp_identity["sha256"]},
            "python": {"role": "python", "sha256": python_sha256},
            "cwd_kind": "repository_root",
            "source_head": source_head,
            "child_script": {"role": "child", "path": "scripts/a0x_material_child.py", "sha256": child_sha256},
            "launch_descriptor": {"role": "descriptor", "path": paths.launch_descriptor_path, "sha256": descriptor_sha256},
            "environment_template": list(_ENVIRONMENT),
            "resource": {
                "profile": "a0x-material", "workload_family": "latent-triz-a0x-v1", "executor": "native",
                "cache_state": "warm", "execution_mode": "native", "target_platform": "macos-arm64",
                "memory_limit_bytes": MEMORY_LIMIT_BYTES,
            },
            "timeouts": {
                "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
                "internal_budget_seconds": INTERNAL_BUDGET_SECONDS,
                "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
                "admission_timeout_seconds": ADMISSION_TIMEOUT_SECONDS,
            },
            "argv_template": [
                "{CCP}", "guard", "exec", "--admission-timeout-seconds", str(ADMISSION_TIMEOUT_SECONDS),
                "--timeout-seconds", str(OUTER_TIMEOUT_SECONDS), "--resource-profile", "a0x-material",
                "--resource-workload-family", "latent-triz-a0x-v1", "--resource-executor", "native",
                "--resource-cache-state", "warm", "--resource-execution-mode", "native",
                "--resource-target-platform", "macos-arm64", "--resource-memory-limit-bytes", str(MEMORY_LIMIT_BYTES),
                "--", "{PYTHON}", "{CHILD}", "--launch-descriptor", "{DESCRIPTOR}",
            ],
        },
        "guard_preflight_observation": {
            "profile": "a0x-guard-preflight-observation-v1",
            "path": paths.observation_directory + "guard-preflight-observation.json",
        },
        "qualification_evidence": dict(qualification_evidence),
        "max_guard_exec_count": 1,
        "stop_boundary": "after_one_sealed_target_read",
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
    }
    try:
        canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE)
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("runtime authorization does not satisfy its frozen contract") from error
    return authorization


def _build_mapping(
    root: Path,
    pair: PairBinding,
    source_head: str,
    ccp_path: Path,
    python_path: Path,
    descriptor_path: str,
    descriptor_sha256: str,
) -> dict[str, Any]:
    """Build the private role map only after descriptor bytes are known."""
    return {
        "mapping_profile": _MAPPING_PROFILE,
        "source_head": source_head,
        "repository_root": str(root),
        "pair_binding": pair.as_mapping(),
        "ccp": {"role": "ccp", "path": str(ccp_path), "sha256": sha256_file(ccp_path)},
        "python": {"role": "python", "path": str(python_path), "sha256": sha256_file(python_path)},
        "descriptor": {"path": descriptor_path, "sha256": descriptor_sha256},
    }


def _write_and_verify_bundle(
    root: Path,
    pair: PairBinding,
    source_head: str,
    descriptor: Mapping[str, Any],
    authorization: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> dict[str, Any]:
    """Write descriptor, authorization, then mapping using exclusive creates."""
    paths = derive_runtime_paths(pair)
    relative_paths = {
        "descriptor": paths.launch_descriptor_path,
        "authorization": paths.authorization_path,
        "mapping": runtime_mapping_path(pair, source_head=source_head),
    }
    _preflight_output_paths(root, pair, source_head)
    documents = {"descriptor": descriptor, "authorization": authorization, "mapping": mapping}
    raw_documents = {name: canonical_json_bytes(document) for name, document in documents.items()}
    for name in ("descriptor", "authorization", "mapping"):
        path = _write_path(root, relative_paths[name])
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _exclusive_write(path, raw_documents[name])
    for name, raw in raw_documents.items():
        if _repository_file(root, relative_paths[name]).read_bytes() != raw:
            raise A0XRuntimeBundleError("runtime bundle bytes did not persist exactly")
    return {
        "status": "prepared",
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "descriptor_path": relative_paths["descriptor"],
        "descriptor_sha256": hashlib.sha256(raw_documents["descriptor"]).hexdigest(),
        "authorization_path": relative_paths["authorization"],
        "authorization_sha256": hashlib.sha256(raw_documents["authorization"]).hexdigest(),
        "mapping_path": relative_paths["mapping"],
        "mapping_sha256": hashlib.sha256(raw_documents["mapping"]).hexdigest(),
        "authorization_id": authorization["authorization_id"],
        "attempt_id": authorization["attempt_id"],
    }


def _exclusive_write(path: Path, raw: bytes) -> None:
    """Reserve an already preflighted runtime document without overwrite fallback."""
    if os.path.lexists(path):
        raise A0XRuntimeBundleError("runtime bundle output is already occupied")
    try:
        with path.open("xb") as handle:
            handle.write(raw)
    except FileExistsError as error:
        raise A0XRuntimeBundleError("runtime bundle output is already occupied") from error


def _source_state(probe: Callable[[], tuple[str, bool]]) -> tuple[str, bool]:
    try:
        source_head, clean = probe()
    except Exception as error:
        raise A0XRuntimeBundleError("runtime preparation source-state probe failed") from error
    _revision(source_head, "source HEAD")
    if not isinstance(clean, bool):
        raise A0XRuntimeBundleError("runtime preparation source cleanliness is invalid")
    return source_head, clean


def _ccp_identity(contract: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, Mapping) or contract.get("artifact_class") != "a0x-material-execution-contract":
        raise A0XRuntimeBundleError("material contract profile is invalid")
    ccp = _mapping(contract, "ccp", "material contract")
    try:
        identity = {
            "executable_name": "commit-ci-preflight",
            "source_commit": ccp["source_commit"],
            "qualified_source_tree": ccp["source_tree"],
            "sha256": ccp["sha256"],
            "version": ccp["version"],
        }
    except KeyError as error:
        raise A0XRuntimeBundleError("material contract CCP identity is incomplete") from error
    _revision(identity["source_commit"], "CCP source commit")
    _revision(identity["qualified_source_tree"], "CCP source tree")
    _digest(identity["sha256"], "CCP SHA-256")
    if not isinstance(identity["version"], str) or not re.fullmatch(r"commit-ci-preflight [^\s]+", identity["version"]):
        raise A0XRuntimeBundleError("material contract CCP version is invalid")
    return identity


def _validate_material_contract_schema(contract: Mapping[str, Any]) -> None:
    """Require the complete frozen material contract before executable checks."""
    try:
        schema = json.loads(_MATERIAL_CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XRuntimeBundleError("material contract schema is unavailable") from error
    if not isinstance(schema, dict):
        raise A0XRuntimeBundleError("material contract schema is malformed")
    issues = validate(dict(contract), schema)
    if issues:
        raise A0XRuntimeBundleError("material contract fails the frozen schema")


def _preflight_output_paths(root: Path, pair: PairBinding, source_head: str) -> None:
    paths = derive_runtime_paths(pair)
    material_workspace = f".a0x-runtime/material/{pair.leg.value}/{pair.model_key}/{pair.run_id}"
    for relative in (
        paths.launch_descriptor_path,
        paths.authorization_path,
        runtime_mapping_path(pair, source_head=source_head),
        paths.claim_path,
        paths.observation_directory,
        material_workspace,
        pair.output_path,
    ):
        path = _write_path(root, relative)
        if os.path.lexists(path):
            raise A0XRuntimeBundleError("pair-scoped runtime destination is already occupied")


def _write_path(root: Path, relative: str) -> Path:
    candidate = root / _relative_path(relative, "runtime output")
    current = candidate.parent
    while current != root:
        if os.path.lexists(current) and current.is_symlink():
            raise A0XRuntimeBundleError("runtime output parent uses a symlink")
        current = current.parent
    return candidate


def _repository_file(root: Path, relative: str) -> Path:
    candidate = root / _relative_path(relative, "repository file")
    current = candidate
    while current != root:
        if current.is_symlink():
            raise A0XRuntimeBundleError("repository input uses a symlink")
        current = current.parent
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise A0XRuntimeBundleError("repository input is unavailable") from error
    if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.is_symlink():
        raise A0XRuntimeBundleError("repository input is not a regular file")
    return resolved


def _external_file(path: Path, label: str) -> Path:
    try:
        resolved = Path(path).resolve(strict=True)
    except OSError as error:
        raise A0XRuntimeBundleError(f"{label} is unavailable") from error
    if not resolved.is_file() or resolved.is_symlink():
        raise A0XRuntimeBundleError(f"{label} is not a regular file")
    return resolved


def _external_executable(path: Path, label: str) -> Path:
    resolved = _external_file(path, label)
    if not os.access(resolved, os.X_OK):
        raise A0XRuntimeBundleError(f"{label} is not executable")
    return resolved


def _relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\x00" in value:
        raise A0XRuntimeBundleError(f"{label} path is invalid")
    path = Path(value)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise A0XRuntimeBundleError(f"{label} path contains traversal")
    return path.as_posix()


def _mapping(value: Mapping[str, Any], key: str, label: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise A0XRuntimeBundleError(f"{label} {key} is invalid")
    return item


def _revision(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise A0XRuntimeBundleError(f"{label} is invalid")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XRuntimeBundleError(f"{label} is invalid")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise A0XRuntimeBundleError(f"{label} is invalid")
    return value


__all__ = [
    "A0XRuntimeBundleError", "RuntimePreparationRequest", "canonical_json_bytes",
    "prepare_runtime_bundle", "_build_authorization", "_build_descriptor", "_build_mapping",
    "_exclusive_write", "_load_fixed_dossier", "_write_and_verify_bundle",
]
