"""Prepare one immutable, target-free A0X runtime binding bundle.

Preparation is deliberately limited to public documents, executable/package
metadata, and the acquired runtime-file allowlist. It never constructs a
tokenizer or model and never reads a sealed target. Its Gate B chain is
verification receipt -> readiness -> descriptor -> authorization -> mapping.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .a0x_ccp_executor import runtime_mapping_path
from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
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
    validate_gate_a_evidence,
)
from .a0x_hosted_verifier import GateBVerificationRequest
from .a0x_runner import planned_material_dossiers
from .a0x_runtime_readiness import (
    A0XRuntimeReadinessError,
    runtime_readiness_path,
    validate_runtime_readiness,
)
from .validator import validate


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")
_MAPPING_PROFILE = "a0x-runtime-role-mapping-v1"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MATERIAL_CONTRACT_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-material-execution-contract.schema.json"
_GATE_B_AUTHORIZATION_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-gate-b-authorization.schema.json"
_GATE_A_RECEIPT_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-hosted-gate-a-verification-receipt.schema.json"
_ENVIRONMENT = (
    "HF_HUB_OFFLINE=1",
    "TRANSFORMERS_OFFLINE=1",
    "HF_DATASETS_OFFLINE=1",
    "TOKENIZERS_PARALLELISM=false",
    "PYTHONNOUSERSITE=1",
)


def _required_gate_a_verifier(_request: GateBVerificationRequest) -> bytes:
    raise A0XRuntimeBundleError("Gate B verifier callback is required")


class A0XRuntimeBundleError(RuntimeError):
    """A target-free runtime preparation binding was not exact."""

    def __init__(self, message: str, *, code: str = "A0X_RUNTIME_BUNDLE_REFUSED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class RuntimePreparationRequest:
    fixed_dossier: str
    gate_b_authorization: Path
    verifier_executable: Path
    verifier_policy: Path
    ccp_executable: Path
    python_executable: Path
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
    descriptor_path: str


@dataclass(frozen=True)
class _PreparedRuntimeBundle:
    repository: Path
    pair: PairBinding
    source_head: str
    readiness: Mapping[str, Any]
    descriptor: Mapping[str, Any]
    authorization: Mapping[str, Any]
    mapping: Mapping[str, Any]


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
    runtime_readiness_probe: Callable[[Path, PairBinding, str, Path], Mapping[str, Any]],
    gate_a_verifier: Callable[[GateBVerificationRequest], bytes] | None = None,
) -> dict[str, Any]:
    """Prepare the current Gate B bundle without accessing material resources."""
    bundle = _build_runtime_bundle(
        root,
        request,
        source_state_probe=source_state_probe,
        ccp_version_probe=ccp_version_probe,
        runtime_readiness_probe=runtime_readiness_probe,
        gate_a_verifier=_required_gate_a_verifier if gate_a_verifier is None else gate_a_verifier,
    )
    return _write_and_verify_bundle(
        bundle.repository, bundle.pair, bundle.source_head, bundle.readiness,
        bundle.descriptor, bundle.authorization, bundle.mapping,
    )


def preflight_runtime_bundle(
    root: Path,
    request: RuntimePreparationRequest,
    *,
    source_state_probe: Callable[[], tuple[str, bool]],
    ccp_version_probe: Callable[[Path], str],
    runtime_readiness_probe: Callable[[Path, PairBinding, str, Path], Mapping[str, Any]],
    gate_a_verifier: Callable[[GateBVerificationRequest], bytes] | None = None,
) -> dict[str, Any]:
    """Validate and construct one exact bundle in memory without writing it."""
    bundle = _build_runtime_bundle(
        root,
        request,
        source_state_probe=source_state_probe,
        ccp_version_probe=ccp_version_probe,
        runtime_readiness_probe=runtime_readiness_probe,
        gate_a_verifier=_required_gate_a_verifier if gate_a_verifier is None else gate_a_verifier,
    )
    return _bundle_summary(
        bundle.pair,
        bundle.source_head,
        bundle.readiness,
        bundle.descriptor,
        bundle.authorization,
        bundle.mapping,
        status="preflight",
    )


def _build_runtime_bundle(
    root: Path,
    request: RuntimePreparationRequest,
    *,
    source_state_probe: Callable[[], tuple[str, bool]],
    ccp_version_probe: Callable[[Path], str],
    runtime_readiness_probe: Callable[[Path, PairBinding, str, Path], Mapping[str, Any]],
    gate_a_verifier: Callable[[GateBVerificationRequest], bytes],
) -> _PreparedRuntimeBundle:
    """Verify hosted evidence, then construct the later documents in memory."""
    repository = Path(root).resolve(strict=True)
    source_head, source_clean = _source_state(source_state_probe)
    if not source_clean:
        raise A0XRuntimeBundleError("runtime preparation requires a clean checkout")
    dossier, pair = _load_fixed_dossier(repository, request.fixed_dossier)
    _preflight_output_paths(repository, pair, source_head)
    inputs = _validate_preparation_inputs(
        repository, request, dossier=dossier, pair=pair, source_head=source_head,
        ccp_version_probe=ccp_version_probe,
    )
    gate_a_evidence = _verify_gate_a_evidence(
        repository, request, pair=pair, source_head=source_head, verifier=gate_a_verifier,
    )
    readiness = _runtime_readiness(
        runtime_readiness_probe, repository, pair, source_head, inputs.python_path,
    )
    readiness_raw = canonical_json_bytes(readiness)
    readiness_sha256 = hashlib.sha256(readiness_raw).hexdigest()
    descriptor = _build_descriptor(
        repository, pair, source_head, inputs.python_path, inputs.child_path,
        inputs.contract_sha256, readiness_sha256,
    )
    descriptor_raw = canonical_json_bytes(descriptor)
    descriptor_sha256 = hashlib.sha256(descriptor_raw).hexdigest()
    authorization = _build_authorization(
        dossier, pair, source_head, descriptor_sha256, gate_a_evidence,
        inputs.ccp_identity, inputs.python_sha256, inputs.child_sha256,
        request.authorization_id, request.attempt_id,
    )
    mapping = _build_mapping(
        repository, pair, source_head, inputs.ccp_path, inputs.python_path,
        inputs.descriptor_path, descriptor_sha256,
    )
    _revalidate_gate_a_evidence(repository, request, pair=pair, source_head=source_head, evidence=gate_a_evidence)
    if _source_state(source_state_probe) != (source_head, True):
        raise A0XRuntimeBundleError("runtime preparation source state drifted before output")
    return _PreparedRuntimeBundle(
        repository=repository,
        pair=pair,
        source_head=source_head,
        readiness=readiness,
        descriptor=descriptor,
        authorization=authorization,
        mapping=mapping,
    )


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
        descriptor_path=descriptor_path,
    )


def _verify_gate_a_evidence(
    root: Path,
    request: RuntimePreparationRequest,
    *,
    pair: PairBinding,
    source_head: str,
    verifier: Callable[[GateBVerificationRequest], bytes],
) -> dict[str, Any]:
    """Create and bind Gate B's sole durable output before readiness starts."""
    authorization_path, authorization_raw, authorization = _gate_b_authorization(root, request)
    if authorization["source_head"] != source_head or authorization["pair_binding"] != pair.as_mapping():
        raise A0XRuntimeBundleError("Gate B authorization does not match runtime preparation")
    policy_path = _controlled_repository_file(root, request.verifier_policy, "verifier policy")
    executable = _external_executable(request.verifier_executable, "verifier executable")
    try:
        returned_raw = verifier(GateBVerificationRequest(root, authorization_path, executable, policy_path))
    except Exception as error:
        raise A0XRuntimeBundleError("Gate B verification refused") from error
    if not isinstance(returned_raw, bytes):
        raise A0XRuntimeBundleError("Gate B verifier returned invalid receipt bytes")
    return _gate_a_evidence_from_receipt(
        root, authorization_path, authorization_raw, authorization, returned_raw,
        pair=pair, source_head=source_head,
    )


def _revalidate_gate_a_evidence(
    root: Path,
    request: RuntimePreparationRequest,
    *,
    pair: PairBinding,
    source_head: str,
    evidence: Mapping[str, Any],
) -> None:
    """Reject any Gate A or verifier byte drift after receipt creation."""
    authorization_path, authorization_raw, authorization = _gate_b_authorization(root, request)
    policy_path = _controlled_repository_file(root, request.verifier_policy, "verifier policy")
    executable = _external_executable(request.verifier_executable, "verifier executable")
    if hashlib.sha256(policy_path.read_bytes()).hexdigest() != authorization["verifier"]["policy_raw_sha256"]:
        raise A0XRuntimeBundleError("verifier policy bytes drifted after Gate B verification")
    if sha256_file(executable) != authorization["verifier"]["sha256"]:
        raise A0XRuntimeBundleError("verifier executable bytes drifted after Gate B verification")
    for binding in authorization["hosted_inputs"].values():
        path = _repository_file(root, binding["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != binding["sha256"]:
            raise A0XRuntimeBundleError("hosted input bytes drifted after Gate B verification")
    receipt_path = _repository_file(root, authorization["verification_receipt_path"])
    _gate_a_evidence_from_receipt(
        root, authorization_path, authorization_raw, authorization, receipt_path.read_bytes(),
        pair=pair, source_head=source_head,
    )
    try:
        if validate_gate_a_evidence(evidence) != dict(evidence):
            raise A0XRuntimeBundleError("Gate A evidence changed after Gate B verification")
    except A0XContractError as error:
        raise A0XRuntimeBundleError("Gate A evidence is invalid") from error


def _gate_b_authorization(root: Path, request: RuntimePreparationRequest) -> tuple[Path, bytes, dict[str, Any]]:
    path = _controlled_repository_file(root, request.gate_b_authorization, "Gate B authorization")
    raw = path.read_bytes()
    try:
        value = strict_json_object(raw)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("Gate B authorization is not strict JSON") from error
    _validate_schema(value, _GATE_B_AUTHORIZATION_SCHEMA, "Gate B authorization")
    return path, raw, value


def _gate_a_evidence_from_receipt(
    root: Path,
    authorization_path: Path,
    authorization_raw: bytes,
    authorization: Mapping[str, Any],
    returned_raw: bytes,
    *,
    pair: PairBinding,
    source_head: str,
) -> dict[str, Any]:
    receipt_path = _repository_file(root, authorization["verification_receipt_path"])
    receipt_raw = receipt_path.read_bytes()
    if receipt_raw != returned_raw:
        raise A0XRuntimeBundleError("Gate B verifier receipt bytes did not persist exactly")
    try:
        receipt = strict_json_object(receipt_raw)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("Gate B verifier receipt is not strict JSON") from error
    _validate_schema(receipt, _GATE_A_RECEIPT_SCHEMA, "Gate B verifier receipt")
    if (
        authorization["source_head"] != source_head
        or receipt["qualified_source_head"] != source_head
        or receipt["qualified_source_tree"] != authorization["source_tree"]
        or receipt["pair_binding"] != pair.as_mapping()
        or receipt["authorization_raw_sha256"] != hashlib.sha256(authorization_raw).hexdigest()
        or receipt["hosted_inputs"] != authorization["hosted_inputs"]
        or receipt["verifier"] != authorization["verifier"]
    ):
        raise A0XRuntimeBundleError("Gate B verifier receipt does not bind authorized hosted evidence")
    evidence = {
        "evidence_profile": "a0x-gate-a-evidence-binding-v2",
        "provider": "github-hosted-attestation-v1",
        "repository": authorization["repository"],
        "source_head": source_head,
        "source_tree": authorization["source_tree"],
        "hosted_inputs": dict(authorization["hosted_inputs"]),
        "verification_receipt": {
            "path": authorization["verification_receipt_path"],
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
        },
        "verifier": dict(authorization["verifier"]),
    }
    try:
        return validate_gate_a_evidence(evidence)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("Gate A evidence binding is invalid") from error


def _controlled_repository_file(root: Path, candidate: Path, label: str) -> Path:
    path = _external_file(candidate, label)
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise A0XRuntimeBundleError(f"{label} is outside repository") from error
    return _repository_file(root, relative.as_posix())


def _validate_schema(value: Mapping[str, Any], path: Path, label: str) -> None:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XRuntimeBundleError(f"{label} schema is unavailable") from error
    if not isinstance(schema, dict) or validate(dict(value), schema):
        raise A0XRuntimeBundleError(f"{label} schema rejected input")


def _build_descriptor(
    root: Path,
    pair: PairBinding,
    source_head: str,
    python_path: Path,
    child_path: Path,
    contract_sha256: str,
    readiness_sha256: str,
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
        "runtime_readiness": {
            "role": "readiness", "path": runtime_readiness_path(pair),
            "sha256": readiness_sha256,
        },
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
    gate_a_evidence: Mapping[str, Any],
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
        "commitment_profile": CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
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
        "source_tree": gate_a_evidence["source_tree"],
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
        "gate_a_evidence": dict(gate_a_evidence),
        "max_guard_exec_count": 1,
        "stop_boundary": "after_one_sealed_target_read",
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
    }
    try:
        canonical_commitment(authorization, CURRENT_EXECUTION_AUTHORIZATION_PROFILE)
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
    readiness: Mapping[str, Any],
    descriptor: Mapping[str, Any],
    authorization: Mapping[str, Any],
    mapping: Mapping[str, Any],
) -> dict[str, Any]:
    """Write readiness, descriptor, authorization, and mapping exclusively."""
    paths = derive_runtime_paths(pair)
    relative_paths = {
        "readiness": runtime_readiness_path(pair),
        "descriptor": paths.launch_descriptor_path,
        "authorization": paths.authorization_path,
        "mapping": runtime_mapping_path(pair, source_head=source_head),
    }
    _preflight_output_paths(root, pair, source_head)
    documents = {
        "readiness": readiness, "descriptor": descriptor,
        "authorization": authorization, "mapping": mapping,
    }
    raw_documents = {name: canonical_json_bytes(document) for name, document in documents.items()}
    created: list[tuple[Path, os.stat_result]] = []
    try:
        for name in ("readiness", "descriptor", "authorization", "mapping"):
            path = _write_path(root, relative_paths[name])
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _exclusive_write(path, raw_documents[name])
            created.append((path, path.stat(follow_symlinks=False)))
        for name, raw in raw_documents.items():
            if _repository_file(root, relative_paths[name]).read_bytes() != raw:
                raise A0XRuntimeBundleError("runtime bundle bytes did not persist exactly")
    except Exception:
        for path, created_stat in reversed(created):
            try:
                current = path.stat(follow_symlinks=False)
                if current.st_ino == created_stat.st_ino and current.st_dev == created_stat.st_dev and path.is_file():
                    path.unlink()
            except OSError:
                pass
        raise
    return _bundle_summary(
        pair, source_head, readiness, descriptor, authorization, mapping, status="prepared",
    )


def _bundle_summary(
    pair: PairBinding,
    source_head: str,
    readiness: Mapping[str, Any],
    descriptor: Mapping[str, Any],
    authorization: Mapping[str, Any],
    mapping: Mapping[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    """Describe exact bundle bytes without exposing private mapping contents."""
    paths = derive_runtime_paths(pair)
    relative_paths = {
        "readiness": runtime_readiness_path(pair),
        "descriptor": paths.launch_descriptor_path,
        "authorization": paths.authorization_path,
        "mapping": runtime_mapping_path(pair, source_head=source_head),
    }
    raw_documents = {
        "readiness": canonical_json_bytes(readiness),
        "descriptor": canonical_json_bytes(descriptor),
        "authorization": canonical_json_bytes(authorization),
        "mapping": canonical_json_bytes(mapping),
    }
    return {
        "status": status,
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "readiness_path": relative_paths["readiness"],
        "readiness_sha256": hashlib.sha256(raw_documents["readiness"]).hexdigest(),
        "descriptor_path": relative_paths["descriptor"],
        "descriptor_sha256": hashlib.sha256(raw_documents["descriptor"]).hexdigest(),
        "authorization_path": relative_paths["authorization"],
        "authorization_sha256": hashlib.sha256(raw_documents["authorization"]).hexdigest(),
        "mapping_path": relative_paths["mapping"],
        "mapping_sha256": hashlib.sha256(raw_documents["mapping"]).hexdigest(),
        "verification_receipt_path": authorization["gate_a_evidence"]["verification_receipt"]["path"],
        "verification_receipt_sha256": authorization["gate_a_evidence"]["verification_receipt"]["sha256"],
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


def _runtime_readiness(
    probe: Callable[[Path, PairBinding, str, Path], Mapping[str, Any]],
    root: Path,
    pair: PairBinding,
    source_head: str,
    python_path: Path,
) -> dict[str, Any]:
    try:
        value = probe(root, pair, source_head, python_path)
        return validate_runtime_readiness(
            value, source_head=source_head, pair=pair, python_path=python_path,
        )
    except (A0XRuntimeReadinessError, OSError, TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("runtime readiness probe refused") from error


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
        runtime_readiness_path(pair),
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
    "preflight_runtime_bundle", "prepare_runtime_bundle", "_build_authorization", "_build_descriptor", "_build_mapping",
    "_exclusive_write", "_load_fixed_dossier", "_write_and_verify_bundle",
]
