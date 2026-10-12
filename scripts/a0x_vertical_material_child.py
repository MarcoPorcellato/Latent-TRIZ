#!/usr/bin/env python3
"""Fail-closed v2-only child for a selector-derived vertical Gate-B graph.

The public route validates and pins the complete v4 graph before fixed
production dispatch. The private synthetic seam remains target-free and
cannot select a production adapter or authorize material access.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_contract import (  # noqa: E402
    A0XContractError,
    PairBinding,
    VERTICAL_EXECUTION_AUTHORIZATION_PROFILE,
    canonical_commitment,
    strict_json_object,
    validate_vertical_package_commitment,
)
from latent_triz.validator import validate as validate_schema  # noqa: E402
from latent_triz.a0x_ccp_executor import (  # noqa: E402
    A0XCcpExecutorError,
    _vertical_gate_a_evidence_from_raw,
)
from latent_triz.a0x_material_contract import validate_vertical_gate_a_evidence  # noqa: E402
from latent_triz.a0x_vertical_production_adapter import (  # noqa: E402
    A0XVerticalProductionAdapterError,
    VerticalProductionContext,
    _dispatch_synthetic_target_free,
    bind_validated_vertical_graph,
    load_vertical_production_capability,
    run_vertical_production,
)
from latent_triz.a0x_public_closure import (  # noqa: E402
    A0XPublicClosureError,
    load_pre_execution_public_closure,
    PRE_EXECUTION_PUBLIC_ROLE_PATHS,
    PRE_EXECUTION_EXTENSION_PATH,
    pre_execution_closure_relative_path,
)


_REVISION = re.compile(r"^[a-f0-9]{40}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_TRUST_BYTES = 1_048_576
_GATE_C_AUTHORIZATION_SCHEMA = "schemas/a0x-execution-authorization-v4.schema.json"
_ENVIRONMENT = (
    "HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1", "HF_DATASETS_OFFLINE=1",
    "TOKENIZERS_PARALLELISM=false", "PYTHONNOUSERSITE=1",
)
_EXECUTION = {
    "network": "offline", "generation": "forbidden", "trust_remote_code": False,
    "device": "cpu", "dtype": "float32", "outer_timeout_seconds": 3600,
    "internal_budget_seconds": 3300, "cleanup_margin_seconds": 300,
}


class A0XVerticalMaterialChildError(RuntimeError):
    """One untrusted v2 graph member failed its static binding."""


class _TrustIdentity:
    """Independent bytes and inode identity reopened through the trusted root."""

    __slots__ = ("root", "relative", "path", "device", "inode", "size", "sha256")

    def __init__(
        self, *, root: Path, relative: str, path: Path, device: int, inode: int, size: int, sha256: str,
    ) -> None:
        self.root = root
        self.relative = relative
        self.path = path
        self.device = device
        self.inode = inode
        self.size = size
        self.sha256 = sha256


def run_child(
    argv: Sequence[str] | None = None,
    *,
    root: Path = ROOT,
    source_head_probe: Callable[[], tuple[str, str, bool]] | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    child_script_path: Path | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Public production wrapper: admit the complete graph before fixed dispatch."""
    return _run_child_core(
        argv,
        root=root,
        source_head_probe=source_head_probe,
        environment=environment,
        cwd=cwd,
        child_script_path=child_script_path,
        qualification_context="production",
        inert_factory=None,
        stdout=stdout,
    )


def _run_child_core(
    argv: Sequence[str] | None,
    *,
    root: Path,
    source_head_probe: Callable[[], tuple[str, str, bool]] | None,
    environment: Mapping[str, str] | None,
    cwd: Path | None,
    child_script_path: Path | None,
    qualification_context: str,
    inert_factory: Callable[[VerticalProductionContext], Any] | None,
    stdout: TextIO | None,
) -> int:
    """Private target-free test seam; public callers cannot select this context."""
    stream = stdout if stdout is not None else sys.stdout
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv in (["--help"], ["-h"]):
        print("usage: a0x_vertical_material_child.py --launch-descriptor <derived-v2-path>", file=stream)
        return 0
    try:
        descriptor_path = _parse_descriptor_argument(raw_argv)
        if environment is None:
            admitted_environment = _admit_vertical_process_environment(dict(os.environ))
            os.environ.clear()
            os.environ.update(admitted_environment)
        else:
            admitted_environment = environment
        graph = _validate_graph(
            Path(root), descriptor_path,
            source_state_probe=source_head_probe or (lambda: _operational_source_state(Path(root), descriptor_path)),
            environment=admitted_environment,
            cwd=Path.cwd() if cwd is None else Path(cwd),
            child_script_path=Path(__file__) if child_script_path is None else Path(child_script_path),
            expected_context=qualification_context,
        )
        # A pure projection is not material authority. Production subsequently
        # reloads the complete capability; synthetic tests retain an inert seam.
        bind_validated_vertical_graph(graph, qualification_context=qualification_context)
    except (A0XVerticalMaterialChildError, A0XVerticalProductionAdapterError, A0XContractError, OSError, TypeError, ValueError):
        _emit_terminal(stream, "refused")
        return 2
    if qualification_context == "production":
        try:
            result = run_vertical_production(load_vertical_production_capability(Path(root), descriptor_path))
        except Exception:
            _emit_terminal(stream, "executor_failed", graph=graph, qualification_context=qualification_context, reached_frontier="validated_graph")
            return 4
        package_path = result.get("package_path")
        if not _lifecycle_can_complete(result) or not isinstance(package_path, str):
            _emit_terminal(stream, "executor_failed", graph=graph, qualification_context=qualification_context, reached_frontier="validated_graph")
            return 4
        package = Path(package_path)
        terminal = result["terminal_outcome"]
        reference = {"package_relative_path": package.relative_to(Path(root)).as_posix(),
            "manifest_raw_sha256": hashlib.sha256((package / "publication-manifest.json").read_bytes()).hexdigest(),
            "root_receipt_raw_sha256": hashlib.sha256((package / "root-receipt.json").read_bytes()).hexdigest()}
        _emit_terminal(stream, "completed", graph=graph, qualification_context=qualification_context,
            reached_frontier=terminal["reached_frontier"], scientific_outcome=terminal["scientific_outcome"], terminal_package=reference)
        return 0
    if qualification_context != "synthetic-target-free" or inert_factory is None:
        _emit_terminal(stream, "runtime_unavailable", graph=graph, qualification_context=qualification_context, reached_frontier="validated_graph")
        return 3
    try:
        _dispatch_synthetic_target_free(graph, inert_factory)
    except Exception:
        _emit_terminal(stream, "executor_failed", graph=graph, qualification_context=qualification_context, reached_frontier="validated_graph")
        return 4
    _emit_terminal(stream, "completed", graph=graph, qualification_context=qualification_context, reached_frontier="validated_graph")
    return 0


def _parse_descriptor_argument(argv: Sequence[str]) -> str:
    if len(argv) != 2 or argv[0] != "--launch-descriptor" or not isinstance(argv[1], str):
        raise A0XVerticalMaterialChildError("exactly one descriptor argument is required")
    relative = PurePosixPath(argv[1])
    parts = relative.parts
    if (
        argv[1] != relative.as_posix() or relative.is_absolute() or any(part in {"", ".", ".."} for part in parts)
        or len(parts) != 9 or parts[:3] != (".a0x-runtime", "gate-b", "v2")
        or not _REVISION.fullmatch(parts[3]) or not _REVISION.fullmatch(parts[4])
        or parts[5] not in {"a0", "r1"} or not _safe_segment(parts[6]) or not _safe_segment(parts[7])
        or parts[8] != "launch-descriptor.json"
    ):
        raise A0XVerticalMaterialChildError("descriptor path is not the derived v2 inlet")
    return relative.as_posix()


def _safe_segment(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]+", value))


def _validate_graph(
    root: Path,
    descriptor_path: str,
    *,
    source_state_probe: Callable[[], tuple[str, str, bool]],
    environment: Mapping[str, str],
    cwd: Path,
    child_script_path: Path,
    expected_context: str,
) -> Mapping[str, Any]:
    if expected_context not in {"production", "synthetic-target-free"}:
        raise A0XVerticalMaterialChildError("private context is invalid")
    repository = root.resolve(strict=True)
    descriptor_raw, descriptor_identity = _read_independent(repository, descriptor_path)
    descriptor_document = _canonical_output(descriptor_raw, "descriptor")
    descriptor = _mapping(descriptor_document, "payload")
    _validate_descriptor_shape(descriptor)
    qualified = _qualified_source(descriptor, descriptor_path)
    source_state = source_state_probe()
    if not isinstance(source_state, tuple) or len(source_state) != 3 or source_state != (
        qualified["head"], qualified["tree"], True,
    ):
        raise A0XVerticalMaterialChildError("source state drifted")
    if cwd.resolve(strict=True) != repository:
        raise A0XVerticalMaterialChildError("cwd is not the repository root")
    if (
        descriptor_document["qualified_source"] != qualified
        or descriptor_document["qualification_context"] != expected_context
    ):
        raise A0XVerticalMaterialChildError("descriptor output source drifted")
    pair = _pair(descriptor, descriptor_document)
    package = _vertical_package(descriptor, descriptor_path, qualified, pair)
    child_identity = _validate_child(descriptor, repository, child_script_path)
    _validate_environment(descriptor.get("environment_template"), environment)
    if descriptor.get("execution") != _EXECUTION:
        raise A0XVerticalMaterialChildError("execution envelope is invalid")

    base = PurePosixPath(descriptor_path).parent
    readiness, readiness_identity, readiness_raw = _read_referenced_output(
        repository, descriptor["runtime_readiness"], "readiness",
        expected_path=(base / "runtime-readiness.json").as_posix(),
    )
    evidence, evidence_identity, _evidence_raw = _read_referenced_output(
        repository, descriptor["gate_a_evidence"], "gate_a_evidence",
        expected_path=(base / "gate-a-evidence.json").as_posix(),
    )
    expected_common = {
        "qualified_source": qualified,
        "pair_binding": pair.as_mapping(),
        "vertical_package": package,
        "qualification_context": expected_context,
    }
    for document in (descriptor_document, readiness, evidence):
        if any(document[key] != value for key, value in expected_common.items()):
            raise A0XVerticalMaterialChildError("referenced v2 output binding drifted")

    try:
        evidence_payload = validate_vertical_gate_a_evidence(_mapping(evidence, "payload"))
    except A0XContractError as error:
        raise A0XVerticalMaterialChildError("Gate A evidence semantics drifted") from error
    gate_b_authorization_raw, gate_b_authorization_identity = _read_independent(
        repository, evidence_payload["gate_b_authorization_path"],
    )
    gate_b_receipt_raw, gate_b_receipt_identity = _read_independent(
        repository, _mapping(evidence_payload, "verification_receipt")["path"],
    )
    try:
        gate_b_authorization = strict_json_object(gate_b_authorization_raw)
        if gate_b_authorization.get("authorization_id") != descriptor["authorization_id"]:
            raise A0XVerticalMaterialChildError("Gate B authorization identity drifted")
        reconstructed_evidence = _vertical_gate_a_evidence_from_raw(
            gate_b_authorization_raw=gate_b_authorization_raw,
            gate_b_authorization_path=evidence_payload["gate_b_authorization_path"],
            gate_b_receipt_raw=gate_b_receipt_raw,
            gate_b_receipt_path=_mapping(evidence_payload, "verification_receipt")["path"],
            expected_source=qualified,
            pair=pair,
            expected_package=package,
            expected_qualification_context=expected_context,
        )
    except (A0XCcpExecutorError, A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XVerticalMaterialChildError("Gate A evidence reconstruction failed") from error
    if reconstructed_evidence != evidence_payload:
        raise A0XVerticalMaterialChildError("Gate A evidence reconstruction drifted")
    hosted_identities = []
    for reference in evidence_payload["hosted_inputs"].values():
        raw, identity = _read_independent(repository, reference["path"])
        if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
            raise A0XVerticalMaterialChildError("Hosted Gate A input bytes drifted")
        hosted_identities.append(identity)

    commitment_raw, commitment_identity = _read_independent(repository, package["commitment_path"])
    if hashlib.sha256(commitment_raw).hexdigest() != package["commitment_raw_sha256"]:
        raise A0XVerticalMaterialChildError("P0 commitment bytes drifted")
    commitment = validate_vertical_package_commitment(strict_json_object(commitment_raw))
    if (
        commitment["qualified_source"] != qualified
        or commitment["pair_binding"] != pair.as_mapping()
        or commitment.get("package_commitment_sha256") != package["package_commitment_sha256"]
    ):
        raise A0XVerticalMaterialChildError("P0 commitment identity drifted")
    dossier_raw, dossier_identity = _read_independent(repository, package["dossier_path"])
    if hashlib.sha256(dossier_raw).hexdigest() != package["dossier_sha256"]:
        raise A0XVerticalMaterialChildError("P0 dossier bytes drifted")

    authorization_reference = descriptor.get("authorization_reference")
    expected_authorization_path = descriptor_path.removesuffix("launch-descriptor.json") + "execution-authorization.json"
    if authorization_reference != {"role": "authorization", "path": expected_authorization_path}:
        raise A0XVerticalMaterialChildError("authorization reference is not derived")
    authorization_raw, authorization_identity = _read_independent(repository, expected_authorization_path)
    authorization = _canonical_output(authorization_raw, "authorization")
    if any(authorization[key] != value for key, value in expected_common.items()):
        raise A0XVerticalMaterialChildError("execution inlet binding drifted")
    inlet = _mapping(authorization, "payload")
    _validate_inlet(inlet, descriptor_path, descriptor_raw, pair, package, descriptor, expected_context)

    gate_c_path = _gate_c_authorization_path(qualified, pair)
    gate_c_raw, gate_c_identity = _read_independent(repository, gate_c_path)
    gate_c_authorization, gate_c_output_identities = _read_gate_c_authorization(
        repository, gate_c_raw, gate_c_path, qualified, pair, package, expected_context,
        descriptor_path, descriptor_raw, descriptor_document, readiness, evidence,
        evidence_payload, gate_b_authorization_raw, gate_b_receipt_raw,
    )

    public_identities = []
    if expected_context == "production":
        try:
            public_identity = {
                    "qualified_source": qualified,
                    "pair_binding": pair.as_mapping(),
                    "authorization_id": gate_c_authorization["authorization_id"],
                    "attempt_id": gate_c_authorization["attempt_id"],
                    "p0_package_commitment_sha256": package["package_commitment_sha256"],
                }
            private_inputs = {
                    "p0_dossier_raw": hashlib.sha256(dossier_raw).hexdigest(),
                    "gate_b_authorization_v4": hashlib.sha256(authorization_raw).hexdigest(),
                    "gate_b_readiness_v4": hashlib.sha256(readiness_raw).hexdigest(),
                }
            observed = load_pre_execution_public_closure(repository, expected_identity=public_identity, private_input_sha256=private_inputs)
            public_base = pre_execution_closure_relative_path(public_identity)
            for name in (*PRE_EXECUTION_PUBLIC_ROLE_PATHS.values(), PRE_EXECUTION_EXTENSION_PATH):
                raw, identity = _read_independent(repository, f"{public_base}/{name}")
                public_identities.append(identity)
                if name == PRE_EXECUTION_EXTENSION_PATH and hashlib.sha256(raw).hexdigest() != observed.extension_sha256:
                    raise A0XVerticalMaterialChildError("public pre-execution extension changed during admission")
            repeated = load_pre_execution_public_closure(repository, expected_identity=public_identity, private_input_sha256=private_inputs)
            if repeated != observed:
                raise A0XVerticalMaterialChildError("public pre-execution closure changed during admission")
        except (A0XPublicClosureError, KeyError, OSError, TypeError, ValueError) as error:
            raise A0XVerticalMaterialChildError("public pre-execution closure is invalid") from error

    # Rebind every consumed trust inode before the private factory seam.
    trust_identities = (
        descriptor_identity, readiness_identity, evidence_identity, child_identity,
        gate_b_authorization_identity, gate_b_receipt_identity,
        commitment_identity, dossier_identity, authorization_identity, gate_c_identity,
        *gate_c_output_identities,
        *hosted_identities,
        *public_identities,
    )
    for identity in trust_identities:
        _revalidate(identity)
    return _freeze({
        "descriptor": descriptor,
        "readiness": _mapping(readiness, "payload"),
        "gate_a_evidence": _mapping(evidence, "payload"),
        "execution_inlet": inlet,
        "gate_c_authorization": gate_c_authorization,
        "trust_file_identities": _trust_file_manifest(repository, trust_identities),
    })


def _gate_c_authorization_path(qualified: Mapping[str, str], pair: PairBinding) -> str:
    return (
        f".a0x-runtime/gate-c/v2/{qualified['head']}/{qualified['tree']}/"
        f"{pair.leg.value}/{pair.model_key}/{pair.run_id}/execution-authorization.json"
    )


def _read_gate_c_authorization(
    root: Path, raw: bytes, relative: str, qualified: Mapping[str, str], pair: PairBinding,
    package: Mapping[str, str], expected_context: str, descriptor_path: str, descriptor_raw: bytes,
    descriptor_document: Mapping[str, Any], readiness: Mapping[str, Any], evidence: Mapping[str, Any],
    evidence_payload: Mapping[str, Any], gate_b_authorization_raw: bytes, gate_b_receipt_raw: bytes,
) -> tuple[Mapping[str, Any], tuple[_TrustIdentity, ...]]:
    """Rebind the separately derived v4 inlet before any synthetic/real factory."""
    try:
        value = strict_json_object(raw)
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        if raw != canonical:
            raise A0XVerticalMaterialChildError("Gate C authorization is not canonical JSON")
        schema_raw, schema_identity = _read_independent(root, _GATE_C_AUTHORIZATION_SCHEMA)
        schema = json.loads(schema_raw)
        issues = validate_schema(value, schema)
        if issues:
            raise A0XVerticalMaterialChildError("Gate C authorization schema is invalid")
        canonical_commitment(value, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE)
    except (A0XContractError, OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise A0XVerticalMaterialChildError("Gate C authorization is invalid") from error

    try:
        pair_binding = PairBinding.from_mapping(_mapping(value, "pair_binding"))
        gate_b_base = PurePosixPath(descriptor_path).parent
        base = f".a0x-runtime/gate-b/v2/{qualified['head']}/{qualified['tree']}/{pair.leg.value}/{pair.model_key}/{pair.run_id}"
        expected_paths = {
            "gate_a_evidence": f"{base}/gate-a-evidence.json",
            "readiness": f"{base}/runtime-readiness.json",
            "descriptor": descriptor_path,
            "authorization": f"{base}/execution-authorization.json",
            "mapping": f"{base}/runtime-mapping.json",
        }
        declared_outputs = _mapping(value, "gate_b_outputs")
        if set(declared_outputs) != set(expected_paths):
            raise A0XVerticalMaterialChildError("Gate B output set is invalid")
        output_identities: list[_TrustIdentity] = []
        output_documents: dict[str, Mapping[str, Any]] = {}
        expected_outputs: dict[str, dict[str, str]] = {}
        for name, expected_path in expected_paths.items():
            raw_output, identity = _read_independent(root, expected_path)
            output_identities.append(identity)
            digest = hashlib.sha256(raw_output).hexdigest()
            if declared_outputs.get(name) != {"path": expected_path, "sha256": digest}:
                raise A0XVerticalMaterialChildError("Gate B output raw binding differs")
            output_document = _canonical_output(raw_output, name)
            output_documents[name] = output_document
            if any(output_document[key] != expected for key, expected in {
                "qualified_source": dict(qualified), "pair_binding": pair.as_mapping(),
                "vertical_package": dict(package), "qualification_context": expected_context,
            }.items()):
                raise A0XVerticalMaterialChildError("Gate B output semantic binding differs")
            expected_outputs[name] = {"path": expected_path, "sha256": digest}
        descriptor_payload = _mapping(descriptor_document, "payload")
        evidence_reference = descriptor_payload.get("gate_a_evidence")
        readiness_reference = descriptor_payload.get("runtime_readiness")
        if (
            not isinstance(evidence_reference, Mapping)
            or expected_outputs["gate_a_evidence"] != {key: evidence_reference[key] for key in ("path", "sha256")}
            or not isinstance(readiness_reference, Mapping)
            or expected_outputs["readiness"] != {key: readiness_reference[key] for key in ("path", "sha256")}
        ):
            raise A0XVerticalMaterialChildError("Gate B descriptor output references differ")
        evidence_reference_payload = validate_vertical_gate_a_evidence(evidence_payload)
        if (
            value.get("qualified_source") != dict(qualified)
            or pair_binding.as_mapping() != pair.as_mapping()
            or value.get("vertical_package") != dict(package)
            or value.get("qualification_context") != expected_context
            or value.get("gate_b_authorization") != {
                "path": evidence_reference_payload["gate_b_authorization_path"],
                "sha256": hashlib.sha256(gate_b_authorization_raw).hexdigest(),
            }
            or value.get("gate_a_verification_receipt") != {
                "path": evidence_reference_payload["verification_receipt"]["path"],
                "sha256": hashlib.sha256(gate_b_receipt_raw).hexdigest(),
            }
            or value.get("gate_b_outputs") != expected_outputs
            or not _IDENTIFIER.fullmatch(str(value.get("authorization_id")))
            or not _IDENTIFIER.fullmatch(str(value.get("attempt_id")))
        ):
            raise A0XVerticalMaterialChildError("Gate C authorization bindings differ")
        launch = _mapping(value, "guard_launch")
        mapping_document = output_documents["mapping"]
        mapping_payload = _mapping(mapping_document, "payload")
        descriptor_payload = _mapping(descriptor_document, "payload")
        if (
            launch.get("source_head") != qualified["head"]
            or launch.get("child_script") != descriptor_payload.get("child_script")
            or launch.get("launch_descriptor") != {"role": "descriptor", "path": descriptor_path, "sha256": hashlib.sha256(descriptor_raw).hexdigest()}
            or _mapping(launch, "ccp").get("sha256") != _mapping(mapping_payload, "ccp").get("sha256")
            or _mapping(launch, "python").get("sha256") != _mapping(mapping_payload, "python").get("sha256")
        ):
            raise A0XVerticalMaterialChildError("Gate C launch binding differs")
    except (A0XContractError, A0XVerticalMaterialChildError, KeyError, OSError, TypeError, ValueError) as error:
        raise A0XVerticalMaterialChildError("Gate C authorization semantic binding is invalid") from error
    return value, (schema_identity, *output_identities)


def _validate_descriptor_shape(descriptor: Mapping[str, Any]) -> None:
    expected = {
        "artifact_class", "descriptor_profile", "qualified_source", "pair_binding", "vertical_package",
        "authorization_id", "attempt_id", "child_script", "python", "ccp", "runtime_readiness", "gate_a_evidence", "authorization_reference",
        "environment_template", "material_contract", "execution",
    }
    if set(descriptor) != expected or descriptor.get("artifact_class") != "a0x-vertical-launch-descriptor" or descriptor.get("descriptor_profile") != "a0x-vertical-launch-descriptor-v2":
        raise A0XVerticalMaterialChildError("descriptor profile is invalid")
    if not _IDENTIFIER.fullmatch(str(descriptor.get("authorization_id"))) or not _IDENTIFIER.fullmatch(str(descriptor.get("attempt_id"))):
        raise A0XVerticalMaterialChildError("descriptor authorization or attempt identity is invalid")


def _qualified_source(descriptor: Mapping[str, Any], descriptor_path: str) -> dict[str, str]:
    value = _mapping(descriptor, "qualified_source")
    if set(value) != {"head", "tree", "ref"} or value.get("ref") != "refs/heads/main":
        raise A0XVerticalMaterialChildError("qualified source is invalid")
    if not _REVISION.fullmatch(str(value.get("head"))) or not _REVISION.fullmatch(str(value.get("tree"))):
        raise A0XVerticalMaterialChildError("qualified source revision is invalid")
    path_parts = PurePosixPath(descriptor_path).parts
    if (value["head"], value["tree"]) != (path_parts[3], path_parts[4]):
        raise A0XVerticalMaterialChildError("descriptor path identity drifted")
    return dict(value)


def _pair(descriptor: Mapping[str, Any], document: Mapping[str, Any]) -> PairBinding:
    try:
        pair = PairBinding.from_mapping(_mapping(descriptor, "pair_binding"))
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XVerticalMaterialChildError("pair binding is invalid") from error
    if document.get("pair_binding") != pair.as_mapping() or descriptor.get("pair_binding") != pair.as_mapping():
        raise A0XVerticalMaterialChildError("pair binding is noncanonical")
    return pair


def _vertical_package(
    descriptor: Mapping[str, Any], descriptor_path: str, qualified: Mapping[str, str], pair: PairBinding,
) -> dict[str, str]:
    package = _mapping(descriptor, "vertical_package")
    expected = {
        "envelope_path", "package_path", "commitment_path", "commitment_raw_sha256",
        "package_commitment_sha256", "dossier_path", "dossier_sha256",
    }
    base = f".a0x-runtime/p0/v2/{qualified['head']}/{qualified['tree']}/{pair.leg.value}/{pair.model_key}"
    if set(package) != expected or package != {
        "envelope_path": base,
        "package_path": base + "/package",
        "commitment_path": base + "/p0-commitment.json",
        "commitment_raw_sha256": package.get("commitment_raw_sha256"),
        "package_commitment_sha256": package.get("package_commitment_sha256"),
        "dossier_path": base + "/package/approval-dossier.json",
        "dossier_sha256": package.get("dossier_sha256"),
    } or any(not _SHA256.fullmatch(str(package[key])) for key in ("commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256")):
        raise A0XVerticalMaterialChildError("vertical package binding is invalid")
    if PurePosixPath(descriptor_path).parts[5:8] != (pair.leg.value, pair.model_key, pair.run_id):
        raise A0XVerticalMaterialChildError("descriptor path pair drifted")
    return dict(package)


def _validate_child(descriptor: Mapping[str, Any], root: Path, current: Path) -> _TrustIdentity:
    child = _mapping(descriptor, "child_script")
    if child.get("role") != "child" or child.get("path") != "scripts/a0x_vertical_material_child.py" or set(child) != {"role", "path", "sha256"} or not _SHA256.fullmatch(str(child.get("sha256"))):
        raise A0XVerticalMaterialChildError("vertical child binding is invalid")
    raw, identity = _read_independent(root, "scripts/a0x_vertical_material_child.py")
    _revalidate(identity)
    if current.resolve(strict=True) != (root / child["path"]).resolve(strict=True) or hashlib.sha256(raw).hexdigest() != child["sha256"]:
        raise A0XVerticalMaterialChildError("vertical child bytes drifted")
    return identity


def _validate_environment(value: Any, environment: Mapping[str, str]) -> None:
    if not isinstance(value, list) or tuple(value) != _ENVIRONMENT or dict(environment) != dict(item.split("=", 1) for item in _ENVIRONMENT):
        raise A0XVerticalMaterialChildError("environment template is invalid")


def _admit_vertical_process_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Reject outer variables; admit only deterministic native startup metadata.

    The emitted env -i boundary removes coordination and credentials. CPython
    locale coercion and macOS CoreFoundation may then create these two keys;
    validate them before removing them, never silently strip unknown fields.
    """
    expected = dict(item.split("=", 1) for item in _ENVIRONMENT)
    if set(environment) - set(expected) - {"LC_CTYPE", "__CF_USER_TEXT_ENCODING"}:
        raise A0XVerticalMaterialChildError("unexpected child environment field")
    if any(environment.get(key) != value for key, value in expected.items()):
        raise A0XVerticalMaterialChildError("offline child environment differs")
    if "LC_CTYPE" in environment and environment["LC_CTYPE"] not in {"C.UTF-8", "UTF-8"}:
        raise A0XVerticalMaterialChildError("unexpected native locale coercion")
    if "__CF_USER_TEXT_ENCODING" in environment:
        value = environment["__CF_USER_TEXT_ENCODING"]
        if sys.platform != "darwin" or not re.fullmatch(r"0x[0-9A-Fa-f]{1,16}:0x[0-9A-Fa-f]{1,16}:0x[0-9A-Fa-f]{1,16}", value):
            raise A0XVerticalMaterialChildError("unexpected native CoreFoundation metadata")
        if int(value.split(":")[0], 16) != os.getuid():
            raise A0XVerticalMaterialChildError("native CoreFoundation owner differs")
    return expected


def _lifecycle_can_complete(result: Mapping[str, Any]) -> bool:
    return (result.get("package_verified") is True and result.get("lifecycle_status") in {"completed", "sealed_failure"}
        and "post_terminal_failure" in result and result["post_terminal_failure"] is None)


def _read_referenced_output(
    root: Path, reference: Any, kind: str, *, expected_path: str,
) -> tuple[dict[str, Any], _TrustIdentity, bytes]:
    if (
        not isinstance(reference, Mapping) or set(reference) != {"role", "path", "sha256"}
        or reference.get("role") != kind or reference.get("path") != expected_path
        or not _SHA256.fullmatch(str(reference.get("sha256")))
    ):
        raise A0XVerticalMaterialChildError("output reference is invalid")
    raw, identity = _read_independent(root, str(reference["path"]))
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise A0XVerticalMaterialChildError("output reference bytes drifted")
    return _canonical_output(raw, kind), identity, raw


def _canonical_output(raw: bytes, kind: str) -> dict[str, Any]:
    value = strict_json_object(raw)
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    if raw != canonical or set(value) != {
        "artifact_class", "output_profile", "output_kind", "qualified_source", "pair_binding", "vertical_package",
        "qualification_context", "payload", "payload_sha256",
    } or value.get("artifact_class") != "a0x-vertical-gate-b-output" or value.get("output_profile") != "a0x-vertical-gate-b-output-v2" or value.get("output_kind") != kind or not isinstance(value.get("payload"), Mapping) or value.get("payload_sha256") != hashlib.sha256(canonical_json(dict(value["payload"]))).hexdigest():
        raise A0XVerticalMaterialChildError("v2 output document is invalid")
    return value


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _validate_inlet(
    inlet: Mapping[str, Any], descriptor_path: str, descriptor_raw: bytes, pair: PairBinding,
    package: Mapping[str, str], descriptor: Mapping[str, Any], context: str,
) -> None:
    expected = {
        "artifact_class", "inlet_profile", "qualified_source", "pair_binding", "vertical_package",
        "gate_a_evidence", "runtime_readiness", "descriptor", "ccp", "python_sha256", "child_sha256",
        "authorization_id", "attempt_id", "stop_boundary",
    }
    if (
        set(inlet) != expected
        or inlet.get("artifact_class") != "a0x-vertical-gate-b-execution-inlet"
        or inlet.get("inlet_profile") != "a0x-vertical-gate-b-execution-inlet-v2"
        or inlet.get("qualified_source") != descriptor["qualified_source"]
        or inlet.get("pair_binding") != pair.as_mapping()
        or inlet.get("vertical_package") != package
        or inlet.get("gate_a_evidence") != descriptor["gate_a_evidence"]
        or inlet.get("runtime_readiness") != descriptor["runtime_readiness"]
        or inlet.get("descriptor") != {"role": "descriptor", "path": descriptor_path, "sha256": hashlib.sha256(descriptor_raw).hexdigest()}
        or inlet.get("ccp") != descriptor["ccp"]
        or inlet.get("child_sha256") != descriptor["child_script"]["sha256"]
        or inlet.get("python_sha256") != descriptor["python"]["sha256"]
        or inlet.get("stop_boundary") != "after_gate_b_runtime_bundle"
    ):
        raise A0XVerticalMaterialChildError("execution inlet is invalid")
    if not _IDENTIFIER.fullmatch(str(inlet.get("authorization_id"))) or not _IDENTIFIER.fullmatch(str(inlet.get("attempt_id"))) or (inlet["authorization_id"], inlet["attempt_id"]) != (descriptor["authorization_id"], descriptor["attempt_id"]):
        raise A0XVerticalMaterialChildError("authorization or attempt identity drifted")
    if not _SHA256.fullmatch(str(inlet.get("child_sha256"))) or not _SHA256.fullmatch(str(inlet.get("python_sha256"))):
        raise A0XVerticalMaterialChildError("inlet executable binding is invalid")


def _read_independent(root: Path, relative: str) -> tuple[bytes, _TrustIdentity]:
    repository = root.resolve(strict=True)
    parts = _safe_relative_parts(relative)
    root_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(repository, root_flags)
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
                raise A0XVerticalMaterialChildError("trust path contains a non-directory")
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
            dir_fd=directory_fd,
        )
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened.st_size > _MAX_TRUST_BYTES:
                raise A0XVerticalMaterialChildError("trust file is not an independent regular file")
            raw = _read_bounded(descriptor)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    if len(raw) > _MAX_TRUST_BYTES or after.st_nlink != 1 or (after.st_dev, after.st_ino, after.st_size) != (opened.st_dev, opened.st_ino, opened.st_size):
        raise A0XVerticalMaterialChildError("trust file identity changed during read")
    path = repository.joinpath(*parts)
    return raw, _TrustIdentity(
        root=repository, relative=PurePosixPath(*parts).as_posix(), path=path,
        device=opened.st_dev, inode=opened.st_ino, size=opened.st_size,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def _safe_relative_parts(relative: str) -> tuple[str, ...]:
    relative_path = PurePosixPath(relative)
    if (
        not isinstance(relative, str) or relative != relative_path.as_posix()
        or relative_path.is_absolute() or not relative_path.parts
        or any(part in {"", ".", ".."} for part in relative_path.parts)
    ):
        raise A0XVerticalMaterialChildError("trust path is unsafe")
    return relative_path.parts


def _read_bounded(descriptor: int) -> bytes:
    chunks: list[bytes] = []
    remaining = _MAX_TRUST_BYTES + 1
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _revalidate(identity: _TrustIdentity) -> None:
    raw, observed = _read_independent(identity.root, identity.relative)
    if (
        observed.path != identity.path
        or (observed.device, observed.inode, observed.size, observed.sha256)
        != (identity.device, identity.inode, identity.size, identity.sha256)
        or hashlib.sha256(raw).hexdigest() != identity.sha256
    ):
        raise A0XVerticalMaterialChildError("trust file changed after graph binding")


def _mapping(value: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    result = value.get(name)
    if not isinstance(result, Mapping):
        raise A0XVerticalMaterialChildError(f"{name} is not an object")
    return result


def _default_source_state(root: Path) -> tuple[str, str, bool]:
    """A bounded clean Git-state probe for the private factory boundary."""
    try:
        def git(*argv: str) -> str | None:
            completed = subprocess.run(
                ("/usr/bin/git", "-c", "core.fsmonitor=false", "-c", "core.trustctime=false", *argv), cwd=str(root), shell=False, check=False,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, timeout=30,
            )
            if completed.returncode != 0:
                return None
            return completed.stdout.decode("ascii").strip()
        head = git("rev-parse", "HEAD")
        tree = git("rev-parse", "HEAD^{tree}")
        status = git("status", "--porcelain=v1", "--untracked-files=all")
        if head is None or tree is None or status is None:
            return "", "", False
        clean = status == ""
    except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired):
        return "", "", False
    return head, tree, clean


def _operational_source_state(root: Path, descriptor_path: str) -> tuple[str, str, bool]:
    from latent_triz.a0x_vertical_slice import _checkout_state, vertical_public_pre_execution_paths
    raw, _identity = _read_independent(root, descriptor_path)
    descriptor = _canonical_output(raw, "descriptor")["payload"]
    pair = PairBinding.from_mapping(descriptor["pair_binding"])
    source = descriptor["qualified_source"]
    return _checkout_state(root, vertical_public_pre_execution_paths(pair, source["head"], source["tree"]))


def _freeze(value: Any) -> Any:
    """Recursively detach validated JSON-shaped data from later caller mutation."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(member) for key, member in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(member) for member in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise A0XVerticalMaterialChildError(f"validated graph contains a non-JSON value: {type(value).__name__}")


def _trust_file_manifest(root: Path, identities: Sequence[_TrustIdentity]) -> dict[str, dict[str, Any]]:
    """Return a private JSON view of every accepted inode for adapter revalidation."""
    result: dict[str, dict[str, Any]] = {}
    for identity in identities:
        try:
            relative = identity.path.relative_to(root).as_posix()
        except ValueError as error:
            raise A0XVerticalMaterialChildError("trust identity escaped the repository") from error
        value = {
            "device": identity.device,
            "inode": identity.inode,
            "size": identity.size,
            "sha256": identity.sha256,
        }
        previous = result.get(relative)
        if previous is not None and previous != value:
            raise A0XVerticalMaterialChildError("trust identity changed within the validated graph")
        result[relative] = value
    return dict(sorted(result.items()))


def _emit_terminal(
    stream: TextIO,
    exit_class: str,
    *,
    graph: Mapping[str, Any] | None = None,
    qualification_context: str | None = None,
    reached_frontier: str = "before_graph",
    scientific_outcome: str | None = None,
    terminal_package: Mapping[str, Any] | None = None,
) -> None:
    """Emit the versioned child wire; only a rebound graph carries identity."""
    value: dict[str, Any] = {
        "artifact_class": "a0x-vertical-material-child-terminal",
        "terminal_profile": "a0x-vertical-child-terminal-v1",
        "exit_class": exit_class,
    }
    if graph is not None:
        descriptor = _mapping(graph, "descriptor")
        gate_c_authorization = _mapping(graph, "gate_c_authorization")
        value.update({
            "qualified_source": _plain_json_value(descriptor["qualified_source"]),
            "pair_binding": _plain_json_value(descriptor["pair_binding"]),
            "authorization_id": gate_c_authorization["authorization_id"],
            "attempt_id": gate_c_authorization["attempt_id"],
            "qualification_context": qualification_context,
            "reached_frontier": reached_frontier,
            "scientific_outcome": scientific_outcome,
            "terminal_package": terminal_package,
        })
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False), file=stream)


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json_value(member) for key, member in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_json_value(member) for member in value]
    return value


def main(argv: Sequence[str] | None = None) -> int:
    return run_child(argv)


if __name__ == "__main__":
    raise SystemExit(main())
