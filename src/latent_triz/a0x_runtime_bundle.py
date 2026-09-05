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
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Literal, Mapping, Protocol

from .a0x_ccp_executor import (
    _ExecutableIdentityEvidence,
    _ExecutableIdentityVerifier,
    _ProductionExecutableIdentityVerifier,
    runtime_mapping_path,
)
from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    PairBinding,
    canonical_commitment,
    sha256_file,
    strict_json_object,
)
from .a0x_gate_contract import (
    HashBoundPath, HostedInputBindings, VerifierIdentity,
    VERTICAL_GATE_B_AUTHORIZATION_PROFILE,
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
    validate_vertical_gate_a_evidence,
)
from .a0x_hosted_verifier import GateBVerificationRequest, verify_hosted_gate_a
from .a0x_runner import planned_material_dossiers
from .a0x_runtime_readiness import (
    A0XRuntimeReadinessError,
    build_runtime_readiness,
    runtime_readiness_path,
    validate_runtime_readiness,
)
from .a0x_vertical_slice import VerticalPackageBinding, load_vertical_runtime_package
from .validator import validate


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")
_MAPPING_PROFILE = "a0x-runtime-role-mapping-v1"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MATERIAL_CONTRACT_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-material-execution-contract.schema.json"
_GATE_B_AUTHORIZATION_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-gate-b-authorization.schema.json"
_VERTICAL_GATE_B_AUTHORIZATION_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-gate-b-authorization-v2.schema.json"
_VERTICAL_GATE_B_OUTPUT_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-vertical-gate-b-output-v2.schema.json"
_GATE_A_RECEIPT_SCHEMA = _REPOSITORY_ROOT / "schemas/a0x-hosted-gate-a-verification-receipt.schema.json"
_SYNTHETIC_GATE_A_RECEIPT_SCHEMA = (
    _REPOSITORY_ROOT / "schemas/a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1.schema.json"
)
_ENVIRONMENT = (
    "HF_HUB_OFFLINE=1",
    "TRANSFORMERS_OFFLINE=1",
    "HF_DATASETS_OFFLINE=1",
    "TOKENIZERS_PARALLELISM=false",
    "PYTHONNOUSERSITE=1",
)

_QualificationContext = Literal["production", "synthetic-target-free"]
_CcpVersionProbe = Callable[[Path], str]
_RuntimeReadinessProbe = Callable[[Path, PairBinding, str, Path], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class _HostedVerificationResult:
    """One verifier receipt plus the executable identity that produced it."""

    receipt_raw: bytes
    identity: _ExecutableIdentityEvidence
    context: _QualificationContext


class _HostedGateAVerifier(Protocol):
    """Private Gate-B dependency; the public entrypoint never accepts it."""

    def verify(self, request: GateBVerificationRequest) -> _HostedVerificationResult: ...


@dataclass(frozen=True, slots=True)
class _GateBDependencies:
    """Private capability bundle for production or synthetic target-free work."""

    hosted_verifier: _HostedGateAVerifier
    ccp_identity_verifier: _ExecutableIdentityVerifier
    readiness_probe: _RuntimeReadinessProbe
    context: _QualificationContext


def _required_gate_a_verifier(_request: GateBVerificationRequest) -> bytes:
    raise A0XRuntimeBundleError("Gate B verifier callback is required")


class _ProductionHostedGateAVerifier:
    """The only production verifier path: fixed executable, identity, and runner."""

    def verify(self, request: GateBVerificationRequest) -> _HostedVerificationResult:
        authorization = _strict_repository_json(
            request.repository_root, request.authorization_path, "vertical Gate B authorization",
        )
        verifier = _mapping(authorization, "verifier", "vertical Gate B authorization")
        expected_sha256 = verifier.get("sha256")
        expected_version = verifier.get("version")
        if not isinstance(expected_sha256, str) or not isinstance(expected_version, str):
            raise A0XRuntimeBundleError("vertical Gate B verifier identity is invalid")
        identity_verifier = _ProductionExecutableIdentityVerifier()
        before = identity_verifier.verify(
            role="hosted_verifier", path=request.verifier_executable,
            expected_sha256=expected_sha256, expected_version=expected_version,
        )

        def runner(argv: tuple[str, ...], cwd: Path) -> tuple[int, bytes, bytes]:
            try:
                completed = subprocess.run(
                    argv, cwd=str(cwd), shell=False, check=False, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, timeout=60,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise A0XRuntimeBundleError("vertical Gate B hosted verifier execution failed") from error
            return completed.returncode, completed.stdout, completed.stderr

        raw = verify_hosted_gate_a(
            request, runner=runner, source_state_probe=_production_vertical_source_state,
        )
        after = identity_verifier.verify(
            role="hosted_verifier", path=request.verifier_executable,
            expected_sha256=expected_sha256, expected_version=expected_version,
        )
        if after != before:
            raise A0XRuntimeBundleError("vertical Gate B verifier identity drifted")
        return _HostedVerificationResult(raw, after, "production")


def _strict_repository_json(root: Path, path: Path, label: str) -> dict[str, Any]:
    try:
        controlled = _controlled_repository_file(root, path, label)
        return strict_json_object(controlled.read_bytes())
    except (A0XContractError, OSError) as error:
        raise A0XRuntimeBundleError(f"{label} is invalid") from error


def _production_vertical_source_state(root: Path) -> tuple[str, str, bool]:
    """Production Git identity probe; failures are terminal before Gate B."""
    def git(*argv: str) -> str:
        try:
            completed = subprocess.run(
                ("git", *argv), cwd=str(root), shell=False, check=False, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise A0XRuntimeBundleError("vertical Gate B production source probe failed") from error
        if completed.returncode != 0:
            raise A0XRuntimeBundleError("vertical Gate B production source probe failed")
        try:
            return completed.stdout.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise A0XRuntimeBundleError("vertical Gate B production source probe failed") from error
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    return head, tree, status == ""


def _production_ccp_version_probe(path: Path) -> str:
    try:
        completed = subprocess.run(
            (str(path), "--version"), shell=False, check=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise A0XRuntimeBundleError("vertical Gate B CCP version probe failed") from error
    if completed.returncode != 0:
        raise A0XRuntimeBundleError("vertical Gate B CCP version probe failed")
    try:
        return completed.stdout.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise A0XRuntimeBundleError("vertical Gate B CCP version probe failed") from error


def _production_runtime_readiness(
    root: Path, pair: PairBinding, source_head: str, python_path: Path,
) -> Mapping[str, Any]:
    """Run the fixed metadata probe; no model or tokenizer API is imported here."""
    program = (
        "import importlib.metadata as m,json,sys,torch,transformers;"
        "names=('numpy','safetensors','tokenizers','torch','transformers');"
        "print(json.dumps({'sys_executable':sys.executable,'python_version':'.'.join(str(x) for x in sys.version_info[:3]),"
        "'python_major_minor':list(sys.version_info[:2]),'sys_prefix':sys.prefix,'sys_base_prefix':sys.base_prefix,"
        "'packages':{n:m.version(n) for n in names},'api_symbols':{'torch.float32':hasattr(torch,'float32'),"
        "'transformers.AutoConfig':hasattr(transformers,'AutoConfig'),'transformers.AutoModelForCausalLM':hasattr(transformers,'AutoModelForCausalLM'),"
        "'transformers.AutoTokenizer':hasattr(transformers,'AutoTokenizer')}},sort_keys=True,separators=(',',':')))"
    )
    try:
        completed = subprocess.run(
            (str(python_path), "-I", "-c", program), cwd=str(root), shell=False, check=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, timeout=60,
        )
        metadata = json.loads(completed.stdout.decode("utf-8")) if completed.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XRuntimeBundleError("vertical Gate B runtime metadata probe failed") from error
    if not isinstance(metadata, Mapping):
        raise A0XRuntimeBundleError("vertical Gate B runtime metadata probe failed")
    return build_runtime_readiness(
        repository_root=root, source_head=source_head, pair=pair, python_path=python_path,
        environment_root=python_path.parent.parent, python_probe=metadata,
    )


def _production_gate_b_dependencies() -> _GateBDependencies:
    return _GateBDependencies(
        hosted_verifier=_ProductionHostedGateAVerifier(),
        ccp_identity_verifier=_ProductionExecutableIdentityVerifier(),
        readiness_probe=_production_runtime_readiness,
        context="production",
    )


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
class VerticalRuntimePreparationRequest:
    """Future-only Gate B request anchored by one P0 v2 package binding."""

    package_binding: VerticalPackageBinding
    gate_b_authorization: Path
    verifier_executable: Path
    verifier_policy: Path
    ccp_executable: Path
    python_executable: Path
    authorization_id: str
    attempt_id: str


@dataclass(frozen=True)
class _VerticalOutputPaths:
    """All v2 durable Gate-B paths derived from one source and pair."""

    raw_receipt: str
    gate_b_authorization: str
    gate_a_evidence: str
    readiness: str
    descriptor: str
    authorization: str
    mapping: str

    def durable(self) -> dict[str, str]:
        return {
            "gate_a_evidence": self.gate_a_evidence,
            "readiness": self.readiness,
            "descriptor": self.descriptor,
            "authorization": self.authorization,
            "mapping": self.mapping,
        }


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
    # Historical v1 preparation needs this derived legacy route.  V2 must not
    # even compute it: all of its durable paths are _VerticalOutputPaths.
    descriptor_path: str | None


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
    """Check static inputs only; never consume verifier or readiness capability."""
    del runtime_readiness_probe, gate_a_verifier
    repository = Path(root).resolve(strict=True)
    source_head, source_clean = _source_state(source_state_probe)
    if not source_clean:
        raise A0XRuntimeBundleError("runtime preparation requires a clean checkout")
    dossier, pair = _load_fixed_dossier(repository, request.fixed_dossier)
    _preflight_output_paths(repository, pair, source_head)
    _validate_preparation_inputs(
        repository, request, dossier=dossier, pair=pair, source_head=source_head,
        ccp_version_probe=ccp_version_probe,
    )
    authorization_path, authorization_raw, authorization = _gate_b_authorization(repository, request)
    _validate_gate_b_static(
        repository, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head,
    )
    return {
        "status": "preflight",
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "readiness_path": runtime_readiness_path(pair),
        "descriptor_path": derive_runtime_paths(pair).launch_descriptor_path,
        "authorization_path": derive_runtime_paths(pair).authorization_path,
        "mapping_path": runtime_mapping_path(pair, source_head=source_head),
        "authorization_id": request.authorization_id,
        "attempt_id": request.attempt_id,
    }


def preflight_vertical_runtime_bundle(
    root: Path,
    request: VerticalRuntimePreparationRequest,
    *,
    source_state_probe: Callable[[], tuple[str, str, bool]],
    ccp_version_probe: Callable[[Path], str],
    runtime_readiness_probe: Callable[[Path, PairBinding, str, Path], Mapping[str, Any]],
    gate_a_verifier: Callable[[GateBVerificationRequest], bytes] | None = None,
) -> dict[str, Any]:
    """Validate exactly one v2 package before Gate B may use any capability.

    The preflight deliberately ignores capability callbacks.  It is a strict
    no-write selector for the later materialisation route.
    """
    del runtime_readiness_probe, gate_a_verifier
    repository = Path(root).resolve(strict=True)
    source_head, source_tree, source_clean = _vertical_source_state(source_state_probe)
    binding = request.package_binding
    if (
        not isinstance(binding, VerticalPackageBinding)
        or (source_head, source_tree) != (binding.qualified_source_head, binding.qualified_source_tree)
        or not source_clean
    ):
        raise A0XRuntimeBundleError("vertical Gate B source state does not match package binding")
    package = _load_vertical_package(repository, binding)
    dossier, pair = _vertical_dossier(package, binding)
    output_paths = _vertical_output_paths(binding)
    _preflight_vertical_output_paths(repository, pair, output_paths)
    inputs = _validate_preparation_inputs(
        repository, request, dossier=dossier, pair=pair, source_head=source_head,
        ccp_version_probe=ccp_version_probe, derive_legacy_paths=False,
    )
    authorization_path, authorization_raw, authorization = _vertical_gate_b_authorization(repository, request)
    _validate_vertical_gate_b_static(
        repository, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head, source_tree=source_tree, binding=binding,
    )
    return {
        "status": "preflight",
        "qualified_source": {"head": source_head, "tree": source_tree},
        "pair_binding": pair.as_mapping(),
        "package_commitment_sha256": binding.package_commitment_sha256,
        "commitment_raw_sha256": binding.commitment_raw_sha256,
        "dossier_path": binding.dossier_path,
        "dossier_sha256": binding.dossier_sha256,
        "verification_receipt_path": output_paths.raw_receipt,
        "vertical_outputs": output_paths.durable(),
        "authorization_id": request.authorization_id,
        "attempt_id": request.attempt_id,
        "ccp_sha256": inputs.ccp_sha256,
    }


def prepare_vertical_runtime_bundle(
    root: Path,
    request: VerticalRuntimePreparationRequest,
) -> dict[str, Any]:
    """Prepare Gate-B v2 using only the fixed production capability factory."""
    repository = Path(root).resolve(strict=True)
    return _prepare_vertical_runtime_bundle_core(
        repository, request,
        source_state_probe=lambda: _production_vertical_source_state(repository),
        dependencies=_production_gate_b_dependencies(),
    )


def _prepare_vertical_runtime_bundle_core(
    root: Path,
    request: VerticalRuntimePreparationRequest,
    *,
    source_state_probe: Callable[[], tuple[str, str, bool]],
    dependencies: _GateBDependencies,
) -> dict[str, Any]:
    """Private v2 constructor used by target-free tests and the production wrapper.

    The caller must provide one internally consistent context.  Public callers
    never receive this capability surface.
    """
    repository = Path(root).resolve(strict=True)
    if not isinstance(dependencies, _GateBDependencies):
        raise A0XRuntimeBundleError("vertical Gate B dependencies are invalid")
    context = dependencies.context
    if context not in {"production", "synthetic-target-free"}:
        raise A0XRuntimeBundleError("vertical Gate B qualification context is invalid")
    source_head, source_tree, source_clean = _vertical_source_state(source_state_probe)
    binding = request.package_binding
    if not source_clean or (source_head, source_tree) != (binding.qualified_source_head, binding.qualified_source_tree):
        raise A0XRuntimeBundleError("vertical Gate B source state does not match package binding")
    package = _load_vertical_package(repository, binding)
    dossier, pair = _vertical_dossier(package, binding)
    paths = _vertical_output_paths(binding)
    _preflight_vertical_output_paths(repository, pair, paths)
    inputs = _validate_preparation_inputs(
        repository, request, dossier=dossier, pair=pair, source_head=source_head,
        ccp_identity_verifier=dependencies.ccp_identity_verifier,
        qualification_context=context, derive_legacy_paths=False,
    )
    authorization_path, authorization_raw, authorization = _vertical_gate_b_authorization(repository, request)
    _validate_vertical_gate_b_static(
        repository, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head, source_tree=source_tree, binding=binding, context=context,
    )
    gate_a_evidence, verification = _verify_vertical_gate_a_evidence(
        repository, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head, source_tree=source_tree, verifier=dependencies.hosted_verifier,
        context=context,
        canonical_authorization_path=paths.gate_b_authorization,
    )
    # The hosted verifier is an external capability. Re-bind the P0 envelope
    # before spending the next capability (the readiness probe).
    _vertical_dossier(_load_vertical_package(repository, binding), binding)
    readiness = _runtime_readiness(dependencies.readiness_probe, repository, pair, source_head, inputs.python_path)
    documents = _build_vertical_output_documents(
        repository, binding, pair, source_head, source_tree, inputs,
        gate_a_evidence, readiness, request.authorization_id, request.attempt_id, context,
    )
    # Re-read the ignored envelope after every injected capability and before
    # the first readiness/descriptor/authorization/mapping write.
    _vertical_dossier(_load_vertical_package(repository, binding), binding)
    _validate_vertical_gate_b_static(
        repository, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head, source_tree=source_tree, binding=binding,
        context=context, receipt_must_be_absent=False,
    )
    raw_receipt = _independent_repository_file(
        repository, authorization["verification_receipt_path"], "vertical Gate B verification receipt",
    )
    revalidated_evidence = _gate_a_evidence_from_receipt(
        repository, authorization_path, authorization_raw, authorization, raw_receipt.read_bytes(),
        pair=pair, source_head=source_head, canonical_authorization_path=paths.gate_b_authorization,
        qualification_context=context,
    )
    if revalidated_evidence != gate_a_evidence:
        raise A0XRuntimeBundleError("vertical Gate B verification evidence drifted before output")
    if verification.context != context:
        raise A0XRuntimeBundleError("vertical Gate B verifier context drifted before output")
    if _vertical_source_state(source_state_probe) != (source_head, source_tree, True):
        raise A0XRuntimeBundleError("vertical Gate B source state drifted before output")
    summary = _write_and_verify_vertical_bundle(
        repository, binding, pair, source_head, source_tree, documents, authorization_raw,
    )
    summary.update({
        "qualified_source": {"head": source_head, "tree": source_tree},
        "package_commitment_sha256": binding.package_commitment_sha256,
        "commitment_raw_sha256": binding.commitment_raw_sha256,
        "dossier_path": binding.dossier_path,
        "dossier_sha256": binding.dossier_sha256,
        "qualification_context": context,
    })
    return summary


def vertical_package_binding_from_commitment(
    root: Path, commitment_path: str,
) -> VerticalPackageBinding:
    """Derive the complete v2 selector from its sole external commitment path."""
    repository = Path(root).resolve(strict=True)
    relative = _relative_path(commitment_path, "vertical commitment")
    parts = PurePosixPath(relative).parts
    if len(parts) != 8 or parts[:3] != (".a0x-runtime", "p0", "v2") or parts[-1] != "p0-commitment.json":
        raise A0XRuntimeBundleError("vertical commitment path is not canonical")
    _, _, _, head, tree, leg, model_key, _filename = parts
    _revision(head, "vertical commitment source HEAD")
    _revision(tree, "vertical commitment source tree")
    try:
        pair_leg = PairBinding.from_mapping
        raw = _repository_file(repository, relative).read_bytes()
        commitment = strict_json_object(raw)
        from .a0x_contract import validate_vertical_package_commitment
        validated = validate_vertical_package_commitment(commitment)
        pair = pair_leg(_mapping(validated, "pair_binding", "vertical commitment"))
        dossier_member = next(member for member in validated["members"] if member["name"] == "approval-dossier.json")
    except (A0XContractError, StopIteration, TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("vertical commitment is invalid") from error
    if pair.leg.value != leg or pair.model_key != model_key or validated["qualified_source"] != {"head": head, "tree": tree, "ref": "refs/heads/main"}:
        raise A0XRuntimeBundleError("vertical commitment selector does not match its path")
    envelope = "/".join(parts[:-1])
    package = f"{envelope}/package"
    return VerticalPackageBinding(
        envelope_path=envelope,
        package_path=package,
        commitment_path=relative,
        commitment_raw_sha256=hashlib.sha256(raw).hexdigest(),
        package_commitment_sha256=str(validated["package_commitment_sha256"]),
        dossier_path=f"{package}/approval-dossier.json",
        dossier_sha256=str(dossier_member["sha256"]),
        qualified_source_head=head,
        qualified_source_tree=tree,
        leg=pair.leg,
        model_key=pair.model_key,
        model_revision=pair.revision,
        pair_binding=pair,
    )


def _vertical_output_paths(binding: VerticalPackageBinding) -> _VerticalOutputPaths:
    """Derive the v2-only durable namespace without caller-selected paths."""
    if not isinstance(binding, VerticalPackageBinding):
        raise A0XRuntimeBundleError("vertical Gate B package binding is invalid")
    pair = binding.pair_binding
    base = (
        f".a0x-runtime/gate-b/v2/{binding.qualified_source_head}/"
        f"{binding.qualified_source_tree}/{pair.leg.value}/{pair.model_key}/{pair.run_id}"
    )
    return _VerticalOutputPaths(
        raw_receipt=f"{base}/gate-a-verification-receipt.json",
        gate_b_authorization=f"{base}/gate-b-authorization.json",
        gate_a_evidence=f"{base}/gate-a-evidence.json",
        readiness=f"{base}/runtime-readiness.json",
        descriptor=f"{base}/launch-descriptor.json",
        authorization=f"{base}/execution-authorization.json",
        mapping=f"{base}/runtime-mapping.json",
    )


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


def _vertical_output_document(
    *,
    kind: str,
    payload: Mapping[str, Any],
    binding: VerticalPackageBinding,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    qualification_context: _QualificationContext,
) -> dict[str, Any]:
    if kind not in {"gate_a_evidence", "readiness", "descriptor", "authorization", "mapping"}:
        raise A0XRuntimeBundleError("vertical Gate B output kind is invalid")
    if qualification_context not in {"production", "synthetic-target-free"}:
        raise A0XRuntimeBundleError("vertical Gate B qualification context is invalid")
    if pair != binding.pair_binding or (source_head, source_tree) != (
        binding.qualified_source_head, binding.qualified_source_tree,
    ):
        raise A0XRuntimeBundleError("vertical Gate B output binding is invalid")
    payload_copy = dict(payload)
    return {
        "artifact_class": "a0x-vertical-gate-b-output",
        "output_profile": "a0x-vertical-gate-b-output-v2",
        "output_kind": kind,
        "qualified_source": {"head": source_head, "tree": source_tree, "ref": "refs/heads/main"},
        "pair_binding": pair.as_mapping(),
        "vertical_package": _vertical_package_projection(binding),
        "qualification_context": qualification_context,
        "payload": payload_copy,
        "payload_sha256": hashlib.sha256(canonical_json_bytes(payload_copy)).hexdigest(),
    }


def _vertical_document_sha256(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _vertical_document_reference(
    paths: _VerticalOutputPaths, name: str, document: Mapping[str, Any], *, role: str | None = None,
) -> dict[str, str]:
    reference = {"path": paths.durable()[name], "sha256": _vertical_document_sha256(document)}
    if role is not None:
        reference = {"role": role, **reference}
    return reference


def _build_vertical_descriptor(
    root: Path,
    binding: VerticalPackageBinding,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    inputs: _ValidatedPreparationInputs,
    paths: _VerticalOutputPaths,
    gate_a_evidence: Mapping[str, Any],
    readiness: Mapping[str, Any],
    gate_a_evidence_document: Mapping[str, Any],
    readiness_document: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the acyclic V2 descriptor without touching legacy route builders."""
    if inputs.child_path != _repository_file(root, "scripts/a0x_material_child.py"):
        raise A0XRuntimeBundleError("child script is not the fixed repository child")
    del gate_a_evidence, readiness
    return {
        "artifact_class": "a0x-vertical-launch-descriptor",
        "descriptor_profile": "a0x-vertical-launch-descriptor-v2",
        "qualified_source": {"head": source_head, "tree": source_tree, "ref": "refs/heads/main"},
        "pair_binding": pair.as_mapping(),
        "vertical_package": _vertical_package_projection(binding),
        "child_script": {
            "role": "child", "path": "scripts/a0x_material_child.py", "sha256": inputs.child_sha256,
        },
        "python": {"role": "python", "path": str(inputs.python_path), "sha256": inputs.python_sha256},
        "runtime_readiness": _vertical_document_reference(
            paths, "readiness", readiness_document, role="readiness",
        ),
        "gate_a_evidence": _vertical_document_reference(
            paths, "gate_a_evidence", gate_a_evidence_document, role="gate_a_evidence",
        ),
        # Deliberately path-only: authorization is downstream of descriptor,
        # so a hash here would create a cycle.
        "authorization_reference": {"role": "authorization", "path": paths.authorization},
        "environment_template": list(_ENVIRONMENT),
        "material_contract": {
            "role": "material_contract", "path": MATERIAL_CONTRACT_PATH, "sha256": inputs.contract_sha256,
        },
        "execution": {
            "network": "offline", "generation": "forbidden", "trust_remote_code": False,
            "device": "cpu", "dtype": "float32", "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
            "internal_budget_seconds": INTERNAL_BUDGET_SECONDS, "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
        },
    }


def _build_vertical_execution_inlet(
    *,
    binding: VerticalPackageBinding,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    paths: _VerticalOutputPaths,
    gate_a_evidence_document: Mapping[str, Any],
    readiness_document: Mapping[str, Any],
    descriptor_document: Mapping[str, Any],
    ccp_identity: Mapping[str, Any],
    python_sha256: str,
    child_sha256: str,
    authorization_id: str,
    attempt_id: str,
) -> dict[str, Any]:
    """Create a v2-only Gate-B inlet; Task 3 owns final Guard authorization."""
    _digest(python_sha256, "vertical Python SHA-256")
    _digest(child_sha256, "vertical child SHA-256")
    _identifier(authorization_id, "vertical authorization ID")
    _identifier(attempt_id, "vertical attempt ID")
    return {
        "artifact_class": "a0x-vertical-gate-b-execution-inlet",
        "inlet_profile": "a0x-vertical-gate-b-execution-inlet-v2",
        "qualified_source": {"head": source_head, "tree": source_tree, "ref": "refs/heads/main"},
        "pair_binding": pair.as_mapping(),
        "vertical_package": _vertical_package_projection(binding),
        "gate_a_evidence": _vertical_document_reference(
            paths, "gate_a_evidence", gate_a_evidence_document, role="gate_a_evidence",
        ),
        "runtime_readiness": _vertical_document_reference(
            paths, "readiness", readiness_document, role="readiness",
        ),
        "descriptor": _vertical_document_reference(paths, "descriptor", descriptor_document, role="descriptor"),
        "ccp": dict(ccp_identity),
        "python_sha256": python_sha256,
        "child_sha256": child_sha256,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "stop_boundary": "after_gate_b_runtime_bundle",
    }


def _build_vertical_mapping(
    root: Path,
    binding: VerticalPackageBinding,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    inputs: _ValidatedPreparationInputs,
    paths: _VerticalOutputPaths,
    descriptor_document: Mapping[str, Any],
    authorization_document: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind only V2 wrapper references; no legacy descriptor route exists here."""
    return {
        "artifact_class": "a0x-vertical-runtime-role-mapping",
        "mapping_profile": "a0x-vertical-runtime-role-mapping-v2",
        "qualified_source": {"head": source_head, "tree": source_tree, "ref": "refs/heads/main"},
        "pair_binding": pair.as_mapping(),
        "vertical_package": _vertical_package_projection(binding),
        "repository_root": str(root),
        "ccp": {"role": "ccp", "path": str(inputs.ccp_path), "sha256": inputs.ccp_sha256},
        "python": {"role": "python", "path": str(inputs.python_path), "sha256": inputs.python_sha256},
        "descriptor": _vertical_document_reference(paths, "descriptor", descriptor_document, role="descriptor"),
        "authorization": _vertical_document_reference(
            paths, "authorization", authorization_document, role="authorization",
        ),
    }


def _build_vertical_output_documents(
    root: Path,
    binding: VerticalPackageBinding,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    inputs: _ValidatedPreparationInputs,
    gate_a_evidence: Mapping[str, Any],
    readiness: Mapping[str, Any],
    authorization_id: str,
    attempt_id: str,
    qualification_context: _QualificationContext,
) -> dict[str, dict[str, Any]]:
    """Project the V2 durable graph in its only acyclic dependency order."""
    paths = _vertical_output_paths(binding)
    documents: dict[str, dict[str, Any]] = {}
    for name, payload in (("gate_a_evidence", gate_a_evidence), ("readiness", readiness)):
        documents[name] = _vertical_output_document(
            kind=name, payload=payload, binding=binding, pair=pair,
            source_head=source_head, source_tree=source_tree, qualification_context=qualification_context,
        )
    descriptor = _build_vertical_descriptor(
        root, binding, pair, source_head, source_tree, inputs, paths, gate_a_evidence, readiness,
        documents["gate_a_evidence"], documents["readiness"],
    )
    documents["descriptor"] = _vertical_output_document(
        kind="descriptor", payload=descriptor, binding=binding, pair=pair,
        source_head=source_head, source_tree=source_tree, qualification_context=qualification_context,
    )
    authorization = _build_vertical_execution_inlet(
        binding=binding, pair=pair, source_head=source_head, source_tree=source_tree, paths=paths,
        gate_a_evidence_document=documents["gate_a_evidence"], readiness_document=documents["readiness"],
        descriptor_document=documents["descriptor"], ccp_identity=inputs.ccp_identity,
        python_sha256=inputs.python_sha256, child_sha256=inputs.child_sha256,
        authorization_id=authorization_id, attempt_id=attempt_id,
    )
    documents["authorization"] = _vertical_output_document(
        kind="authorization", payload=authorization, binding=binding, pair=pair,
        source_head=source_head, source_tree=source_tree, qualification_context=qualification_context,
    )
    mapping = _build_vertical_mapping(
        root, binding, pair, source_head, source_tree, inputs, paths,
        documents["descriptor"], documents["authorization"],
    )
    documents["mapping"] = _vertical_output_document(
        kind="mapping", payload=mapping, binding=binding, pair=pair,
        source_head=source_head, source_tree=source_tree, qualification_context=qualification_context,
    )
    return documents


def _preflight_vertical_output_paths(
    root: Path, pair: PairBinding, paths: _VerticalOutputPaths, *, raw_receipt_must_be_absent: bool = True,
) -> None:
    """Refuse reused v2 documents and later material destinations before probes."""
    candidates = [paths.gate_b_authorization, *paths.durable().values(), pair.output_path]
    if raw_receipt_must_be_absent:
        candidates.append(paths.raw_receipt)
    for relative in candidates:
        if os.path.lexists(_write_path(root, relative)):
            raise A0XRuntimeBundleError("vertical Gate B destination is already occupied")


def validate_vertical_runtime_output(
    root: Path, relative: str, binding: VerticalPackageBinding,
    *, expected_qualification_context: _QualificationContext | None = None,
) -> dict[str, Any]:
    """Validate one canonical v2 projection against the typed P0 selector."""
    repository = Path(root).resolve(strict=True)
    paths = _vertical_output_paths(binding)
    by_path = {value: name for name, value in paths.durable().items()}
    if relative not in by_path:
        raise A0XRuntimeBundleError("vertical Gate B output path is not canonical")
    path = _independent_repository_file(repository, relative, "vertical Gate B output")
    raw = path.read_bytes()
    try:
        value = strict_json_object(raw)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("vertical Gate B output is not strict JSON") from error
    if canonical_json_bytes(value) != raw:
        raise A0XRuntimeBundleError("vertical Gate B output is not canonical JSON")
    _validate_schema(value, _VERTICAL_GATE_B_OUTPUT_SCHEMA, "vertical Gate B output")
    pair = binding.pair_binding
    expected_source = {
        "head": binding.qualified_source_head,
        "tree": binding.qualified_source_tree,
        "ref": "refs/heads/main",
    }
    if (
        value.get("output_kind") != by_path[relative]
        or value.get("qualified_source") != expected_source
        or value.get("pair_binding") != pair.as_mapping()
        or value.get("vertical_package") != _vertical_package_projection(binding)
        or value.get("qualification_context") not in {"production", "synthetic-target-free"}
        or (
            expected_qualification_context is not None
            and value.get("qualification_context") != expected_qualification_context
        )
    ):
        raise A0XRuntimeBundleError("vertical Gate B output binding drifted")
    payload = value.get("payload")
    if not isinstance(payload, Mapping) or value.get("payload_sha256") != hashlib.sha256(
        canonical_json_bytes(dict(payload))
    ).hexdigest():
        raise A0XRuntimeBundleError("vertical Gate B output payload binding drifted")
    _validate_vertical_output_dependencies(repository, by_path[relative], dict(payload), paths)
    return value


def _vertical_persisted_reference(
    root: Path, paths: _VerticalOutputPaths, name: str, *, role: str,
) -> dict[str, str]:
    relative = paths.durable()[name]
    raw = _independent_repository_file(root, relative, f"vertical Gate B {name} output").read_bytes()
    return {"role": role, "path": relative, "sha256": hashlib.sha256(raw).hexdigest()}


def _require_exact_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise A0XRuntimeBundleError(f"vertical Gate B {label} shape is invalid")


def _validate_vertical_output_dependencies(
    root: Path, name: str, payload: Mapping[str, Any], paths: _VerticalOutputPaths,
) -> None:
    """Reject substituted V2 references before any later material probe."""
    if name in {"gate_a_evidence", "readiness"}:
        return
    if name == "descriptor":
        _require_exact_fields(
            payload,
            {
                "artifact_class", "descriptor_profile", "qualified_source", "pair_binding", "vertical_package",
                "child_script", "python", "runtime_readiness", "gate_a_evidence", "authorization_reference",
                "environment_template", "material_contract", "execution",
            },
            "descriptor payload",
        )
        if (
            payload.get("artifact_class") != "a0x-vertical-launch-descriptor"
            or payload.get("descriptor_profile") != "a0x-vertical-launch-descriptor-v2"
            or payload.get("runtime_readiness") != _vertical_persisted_reference(root, paths, "readiness", role="readiness")
            or payload.get("gate_a_evidence") != _vertical_persisted_reference(root, paths, "gate_a_evidence", role="gate_a_evidence")
            or payload.get("authorization_reference") != {"role": "authorization", "path": paths.authorization}
        ):
            raise A0XRuntimeBundleError("vertical Gate B descriptor dependency binding drifted")
        return
    if name == "authorization":
        _require_exact_fields(
            payload,
            {
                "artifact_class", "inlet_profile", "qualified_source", "pair_binding", "vertical_package",
                "gate_a_evidence", "runtime_readiness", "descriptor", "ccp", "python_sha256", "child_sha256",
                "authorization_id", "attempt_id", "stop_boundary",
            },
            "authorization payload",
        )
        if (
            payload.get("artifact_class") != "a0x-vertical-gate-b-execution-inlet"
            or payload.get("inlet_profile") != "a0x-vertical-gate-b-execution-inlet-v2"
            or payload.get("gate_a_evidence") != _vertical_persisted_reference(root, paths, "gate_a_evidence", role="gate_a_evidence")
            or payload.get("runtime_readiness") != _vertical_persisted_reference(root, paths, "readiness", role="readiness")
            or payload.get("descriptor") != _vertical_persisted_reference(root, paths, "descriptor", role="descriptor")
        ):
            raise A0XRuntimeBundleError("vertical Gate B authorization dependency binding drifted")
        return
    if name == "mapping":
        _require_exact_fields(
            payload,
            {
                "artifact_class", "mapping_profile", "qualified_source", "pair_binding", "vertical_package",
                "repository_root", "ccp", "python", "descriptor", "authorization",
            },
            "mapping payload",
        )
        if (
            payload.get("artifact_class") != "a0x-vertical-runtime-role-mapping"
            or payload.get("mapping_profile") != "a0x-vertical-runtime-role-mapping-v2"
            or payload.get("descriptor") != _vertical_persisted_reference(root, paths, "descriptor", role="descriptor")
            or payload.get("authorization") != _vertical_persisted_reference(root, paths, "authorization", role="authorization")
        ):
            raise A0XRuntimeBundleError("vertical Gate B mapping dependency binding drifted")
        return
    raise A0XRuntimeBundleError("vertical Gate B output kind is invalid")


def _independent_repository_file(root: Path, relative: str, label: str) -> Path:
    path = _repository_file(root, relative)
    metadata = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise A0XRuntimeBundleError(f"{label} is not an independent regular file")
    return path


def _write_and_verify_vertical_bundle(
    root: Path,
    binding: VerticalPackageBinding,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    documents: Mapping[str, Mapping[str, Any]], gate_b_authorization_raw: bytes,
) -> dict[str, Any]:
    """Publish only v2 projections; v1/batch bytes are never reused or changed."""
    paths = _vertical_output_paths(binding)
    _preflight_vertical_output_paths(root, pair, paths, raw_receipt_must_be_absent=False)
    if set(documents) != set(paths.durable()):
        raise A0XRuntimeBundleError("vertical Gate B durable output set is invalid")
    created: list[tuple[Path, os.stat_result]] = []
    try:
        authorization_copy = _write_path(root, paths.gate_b_authorization)
        authorization_copy.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _exclusive_write(authorization_copy, gate_b_authorization_raw)
        created.append((authorization_copy, authorization_copy.stat(follow_symlinks=False)))
        _independent_repository_file(root, paths.gate_b_authorization, "vertical Gate B authorization")
        for name, relative in paths.durable().items():
            destination = _write_path(root, relative)
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            _exclusive_write(destination, canonical_json_bytes(documents[name]))
            created.append((destination, destination.stat(follow_symlinks=False)))
            validate_vertical_runtime_output(root, relative, binding)
    except Exception:
        for path, created_stat in reversed(created):
            try:
                current = path.stat(follow_symlinks=False)
                if current.st_ino == created_stat.st_ino and current.st_dev == created_stat.st_dev and path.is_file():
                    path.unlink()
            except OSError:
                pass
        raise
    summary = {
        "status": "prepared",
        "qualified_source": {"head": source_head, "tree": source_tree},
        "pair_binding": pair.as_mapping(),
        "vertical_outputs": paths.durable(),
        "gate_b_authorization_path": paths.gate_b_authorization,
        "gate_b_authorization_sha256": hashlib.sha256(gate_b_authorization_raw).hexdigest(),
        "verification_receipt_path": paths.raw_receipt,
        "verification_receipt_sha256": hashlib.sha256(
            _repository_file(root, paths.raw_receipt).read_bytes()
        ).hexdigest(),
    }
    for name, relative in paths.durable().items():
        summary[f"{name}_sha256"] = hashlib.sha256(_repository_file(root, relative).read_bytes()).hexdigest()
    return summary


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
        _required_legacy_descriptor_path(inputs), descriptor_sha256,
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


def _required_legacy_descriptor_path(inputs: _ValidatedPreparationInputs) -> str:
    if inputs.descriptor_path is None:
        raise A0XRuntimeBundleError("historical runtime preparation lacks its legacy descriptor path")
    return inputs.descriptor_path


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
    ccp_version_probe: Callable[[Path], str] | None = None,
    ccp_identity_verifier: _ExecutableIdentityVerifier | None = None,
    qualification_context: _QualificationContext = "production",
    derive_legacy_paths: bool = True,
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
    if ccp_identity_verifier is not None:
        try:
            evidence = ccp_identity_verifier.verify(
                role="ccp", path=ccp_path, expected_sha256=ccp_identity["sha256"],
                expected_version=ccp_identity["version"],
            )
        except Exception as error:
            raise A0XRuntimeBundleError("CCP executable identity verification failed") from error
        if (
            not isinstance(evidence, _ExecutableIdentityEvidence)
            or evidence.role != "ccp" or evidence.path != ccp_path
            or evidence.sha256 != ccp_identity["sha256"] or evidence.version != ccp_identity["version"]
            or evidence.synthetic != (qualification_context == "synthetic-target-free")
        ):
            raise A0XRuntimeBundleError("CCP executable identity context differs")
        ccp_sha256 = evidence.sha256
    else:
        if ccp_version_probe is None:
            raise A0XRuntimeBundleError("CCP version probe is required")
        ccp_sha256 = sha256_file(ccp_path)
        if ccp_sha256 != ccp_identity["sha256"]:
            raise A0XRuntimeBundleError("CCP executable bytes differ from material contract")
        if ccp_version_probe(ccp_path) != ccp_identity["version"]:
            raise A0XRuntimeBundleError("CCP executable version differs from material contract")
    python_path = _external_executable(request.python_executable, "Python executable")
    child_path = _repository_file(root, "scripts/a0x_material_child.py")
    descriptor_path = derive_runtime_paths(pair).launch_descriptor_path if derive_legacy_paths else None
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
    policy_path, executable = _validate_gate_b_static(
        root, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head,
    )
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
    _validate_gate_b_static(
        root, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head, receipt_must_be_absent=False,
    )
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
    try:
        value["pair_binding"] = PairBinding.from_mapping(value["pair_binding"]).as_mapping()
    except (A0XContractError, KeyError, TypeError) as error:
        raise A0XRuntimeBundleError("Gate B authorization pair binding is invalid") from error
    return path, raw, value


def _vertical_source_state(
    probe: Callable[[], tuple[str, str, bool]],
) -> tuple[str, str, bool]:
    try:
        source_head, source_tree, clean = probe()
    except Exception as error:
        raise A0XRuntimeBundleError("vertical Gate B source-state probe failed") from error
    _revision(source_head, "vertical source HEAD")
    _revision(source_tree, "vertical source tree")
    if not isinstance(clean, bool):
        raise A0XRuntimeBundleError("vertical Gate B source cleanliness is invalid")
    return source_head, source_tree, clean


def _load_vertical_package(root: Path, binding: VerticalPackageBinding) -> Mapping[str, Any]:
    try:
        return load_vertical_runtime_package(root, binding)
    except Exception as error:
        raise A0XRuntimeBundleError("vertical Gate B package binding is invalid") from error


def _vertical_dossier(
    package: Mapping[str, Any], binding: VerticalPackageBinding,
) -> tuple[Mapping[str, Any], PairBinding]:
    try:
        documents = _mapping(package, "documents", "vertical package")
        dossier = _mapping(documents, "approval-dossier.json", "vertical package")
        pair = PairBinding.from_mapping(_mapping(dossier, "pair_binding", "vertical dossier"))
        raw = _vertical_canonical_json_bytes(dossier)
        if (
            hashlib.sha256(raw).hexdigest() != binding.dossier_sha256
            or pair != binding.pair_binding
            or pair.leg != binding.leg
            or pair.model_key != binding.model_key
            or pair.revision != binding.model_revision
        ):
            raise ValueError("dossier binding")
        canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE)
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("vertical Gate B dossier binding is invalid") from error
    return dossier, pair


def _vertical_canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Match Task-1's canonical JSON representation, including its single LF."""
    try:
        return (
            json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("vertical package document is not canonical JSON") from error


def _vertical_gate_b_authorization(
    root: Path, request: VerticalRuntimePreparationRequest,
) -> tuple[Path, bytes, dict[str, Any]]:
    path = _controlled_repository_file(root, request.gate_b_authorization, "vertical Gate B authorization")
    raw = path.read_bytes()
    try:
        value = strict_json_object(raw)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("vertical Gate B authorization is not strict JSON") from error
    _validate_schema(value, _VERTICAL_GATE_B_AUTHORIZATION_SCHEMA, "vertical Gate B authorization")
    try:
        value["pair_binding"] = PairBinding.from_mapping(value["pair_binding"]).as_mapping()
    except (A0XContractError, KeyError, TypeError) as error:
        raise A0XRuntimeBundleError("vertical Gate B authorization pair binding is invalid") from error
    return path, raw, value


def _validate_vertical_gate_b_static(
    root: Path,
    request: VerticalRuntimePreparationRequest,
    authorization_path: Path,
    authorization_raw: bytes,
    authorization: Mapping[str, Any],
    *,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    binding: VerticalPackageBinding,
    context: _QualificationContext = "production",
    receipt_must_be_absent: bool = True,
) -> tuple[Path, Path]:
    if (
        authorization.get("authorization_profile") != VERTICAL_GATE_B_AUTHORIZATION_PROFILE
        or authorization.get("source_head") != source_head
        or authorization.get("source_tree") != source_tree
        or authorization.get("pair_binding") != pair.as_mapping()
        or authorization.get("authorization_id") != request.authorization_id
        or authorization.get("qualification_context") != context
    ):
        raise A0XRuntimeBundleError("vertical Gate B authorization does not match package binding")
    expected_package = {
        "envelope_path": binding.envelope_path,
        "package_path": binding.package_path,
        "commitment_path": binding.commitment_path,
        "commitment_raw_sha256": binding.commitment_raw_sha256,
        "package_commitment_sha256": binding.package_commitment_sha256,
        "dossier_path": binding.dossier_path,
        "dossier_sha256": binding.dossier_sha256,
    }
    if authorization.get("vertical_package") != expected_package:
        raise A0XRuntimeBundleError("vertical Gate B authorization package binding drifted")
    if authorization.get("verification_receipt_path") != _vertical_output_paths(binding).raw_receipt:
        raise A0XRuntimeBundleError("vertical Gate B verification receipt path is not derived")
    if context == "production":
        verifier = authorization.get("verifier")
        if not isinstance(verifier, Mapping) or verifier != VerifierIdentity(
            policy_raw_sha256=str(verifier.get("policy_raw_sha256", "")),
        ).as_mapping():
            raise A0XRuntimeBundleError("production vertical Gate B verifier identity is not pinned")
    try:
        hosted_inputs = HostedInputBindings(**{
            name: HashBoundPath(**value) for name, value in authorization["hosted_inputs"].items()
        })
        hosted_inputs.require_source_head(source_head)
    except (TypeError, ValueError) as error:
        raise A0XRuntimeBundleError("vertical Gate B hosted input paths are invalid") from error
    policy_path = _controlled_repository_file(root, request.verifier_policy, "verifier policy")
    executable = _external_executable(request.verifier_executable, "verifier executable")
    if hashlib.sha256(policy_path.read_bytes()).hexdigest() != authorization["verifier"]["policy_raw_sha256"]:
        raise A0XRuntimeBundleError("verifier policy bytes differ from vertical Gate B authorization")
    if sha256_file(executable) != authorization["verifier"]["sha256"]:
        raise A0XRuntimeBundleError("verifier executable bytes differ from vertical Gate B authorization")
    for hosted_binding in authorization["hosted_inputs"].values():
        path = _repository_file(root, hosted_binding["path"])
        metadata = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or hashlib.sha256(path.read_bytes()).hexdigest() != hosted_binding["sha256"]
        ):
            raise A0XRuntimeBundleError("hosted input bytes differ from vertical Gate B authorization")
    if receipt_must_be_absent and os.path.lexists(root / authorization["verification_receipt_path"]):
        raise A0XRuntimeBundleError("vertical Gate B verification receipt destination is already occupied")
    return policy_path, executable


def _verify_vertical_gate_a_evidence(
    root: Path,
    request: VerticalRuntimePreparationRequest,
    authorization_path: Path,
    authorization_raw: bytes,
    authorization: Mapping[str, Any],
    *,
    pair: PairBinding,
    source_head: str,
    source_tree: str,
    verifier: _HostedGateAVerifier,
    context: _QualificationContext,
    canonical_authorization_path: str,
) -> tuple[dict[str, Any], _HostedVerificationResult]:
    policy_path, executable = _validate_vertical_gate_b_static(
        root, request, authorization_path, authorization_raw, authorization,
        pair=pair, source_head=source_head, source_tree=source_tree, binding=request.package_binding,
        context=context,
    )
    try:
        result = verifier.verify(
            GateBVerificationRequest(
                root, authorization_path, executable, policy_path,
                authorization_schema_name="a0x-gate-b-authorization-v2.schema.json",
            ),
        )
    except Exception as error:
        raise A0XRuntimeBundleError("vertical Gate B verification refused") from error
    if (
        not isinstance(result, _HostedVerificationResult)
        or result.context != context
        or result.identity.synthetic != (context == "synthetic-target-free")
        or not isinstance(result.receipt_raw, bytes)
    ):
        raise A0XRuntimeBundleError("vertical Gate B verifier returned invalid receipt bytes")
    return _gate_a_evidence_from_receipt(
        root, authorization_path, authorization_raw, authorization, result.receipt_raw,
        pair=pair, source_head=source_head, canonical_authorization_path=canonical_authorization_path,
        qualification_context=context,
    ), result


def _validate_gate_b_static(
    root: Path,
    request: RuntimePreparationRequest,
    authorization_path: Path,
    authorization_raw: bytes,
    authorization: Mapping[str, Any],
    *,
    pair: PairBinding,
    source_head: str,
    receipt_must_be_absent: bool = True,
) -> tuple[Path, Path]:
    if authorization["source_head"] != source_head or authorization["pair_binding"] != pair.as_mapping():
        raise A0XRuntimeBundleError("Gate B authorization does not match runtime preparation")
    policy_path = _controlled_repository_file(root, request.verifier_policy, "verifier policy")
    executable = _external_executable(request.verifier_executable, "verifier executable")
    if hashlib.sha256(policy_path.read_bytes()).hexdigest() != authorization["verifier"]["policy_raw_sha256"]:
        raise A0XRuntimeBundleError("verifier policy bytes differ from Gate B authorization")
    if sha256_file(executable) != authorization["verifier"]["sha256"]:
        raise A0XRuntimeBundleError("verifier executable bytes differ from Gate B authorization")
    for binding in authorization["hosted_inputs"].values():
        path = _repository_file(root, binding["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != binding["sha256"]:
            raise A0XRuntimeBundleError("hosted input bytes differ from Gate B authorization")
    if receipt_must_be_absent and os.path.lexists(root / authorization["verification_receipt_path"]):
        raise A0XRuntimeBundleError("Gate B verification receipt destination is already occupied")
    return policy_path, executable


def _gate_a_evidence_from_receipt(
    root: Path,
    authorization_path: Path,
    authorization_raw: bytes,
    authorization: Mapping[str, Any],
    returned_raw: bytes,
    *,
    pair: PairBinding,
    source_head: str,
    canonical_authorization_path: str | None = None,
    qualification_context: _QualificationContext = "production",
) -> dict[str, Any]:
    receipt_path = _repository_file(root, authorization["verification_receipt_path"])
    receipt_raw = receipt_path.read_bytes()
    if receipt_raw != returned_raw:
        raise A0XRuntimeBundleError("Gate B verifier receipt bytes did not persist exactly")
    try:
        receipt = strict_json_object(receipt_raw)
    except A0XContractError as error:
        raise A0XRuntimeBundleError("Gate B verifier receipt is not strict JSON") from error
    schema = _SYNTHETIC_GATE_A_RECEIPT_SCHEMA if qualification_context == "synthetic-target-free" else _GATE_A_RECEIPT_SCHEMA
    _validate_schema(receipt, schema, "Gate B verifier receipt")
    expected_artifact = (
        "a0x-hosted-gate-a-verification-receipt-synthetic-target-free"
        if qualification_context == "synthetic-target-free"
        else "a0x-hosted-gate-a-verification-receipt"
    )
    if (
        receipt.get("artifact_class") != expected_artifact
        or receipt.get("qualification_context", "production") != qualification_context
    ):
        raise A0XRuntimeBundleError("Gate B verifier receipt qualification context differs")
    if (
        authorization["source_head"] != source_head
        or receipt["qualified_source_head"] != source_head
        or receipt["qualified_source_tree"] != authorization["source_tree"]
        or receipt["pair_binding"] != pair.as_mapping()
        or receipt["authorization_raw_sha256"] != hashlib.sha256(authorization_raw).hexdigest()
        or receipt["hosted_inputs"] != authorization["hosted_inputs"]
        or receipt["verifier"] != authorization["verifier"]
        or receipt.get("qualification_context") != authorization.get("qualification_context", "production")
    ):
        raise A0XRuntimeBundleError("Gate B verifier receipt does not bind authorized hosted evidence")
    vertical = authorization.get("authorization_profile") == VERTICAL_GATE_B_AUTHORIZATION_PROFILE
    if vertical and canonical_authorization_path is None:
        raise A0XRuntimeBundleError("vertical Gate B canonical authorization path is required")
    evidence = {
        "evidence_profile": "a0x-vertical-gate-a-evidence-binding-v1" if vertical else "a0x-gate-a-evidence-binding-v2",
        "provider": "github-hosted-attestation-v1",
        "repository": authorization["repository"],
        "source_head": source_head,
        "source_tree": authorization["source_tree"],
        **({"pair_binding": pair.as_mapping(), "gate_b_authorization_path": canonical_authorization_path} if vertical else {}),
        "gate_b_authorization_raw_sha256": hashlib.sha256(authorization_raw).hexdigest(),
        "hosted_inputs": dict(authorization["hosted_inputs"]),
        "verification_receipt": {
            "path": authorization["verification_receipt_path"],
            "sha256": hashlib.sha256(receipt_raw).hexdigest(),
        },
        "verifier": dict(authorization["verifier"]),
    }
    validator = validate_vertical_gate_a_evidence if vertical else validate_gate_a_evidence
    try:
        return validator(evidence)
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
    "A0XRuntimeBundleError", "RuntimePreparationRequest", "VerticalRuntimePreparationRequest", "canonical_json_bytes",
    "preflight_runtime_bundle", "prepare_runtime_bundle", "preflight_vertical_runtime_bundle",
    "prepare_vertical_runtime_bundle", "vertical_package_binding_from_commitment",
    "_build_authorization", "_build_descriptor", "_build_mapping",
    "_exclusive_write", "_load_fixed_dossier", "_write_and_verify_bundle",
]
