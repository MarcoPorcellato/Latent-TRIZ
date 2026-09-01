from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from latent_triz.validator import validate

from .a0x_pair import (
    A0XContractError,
    DenseBound,
    Leg,
    MODEL_KEYS as _MODEL_KEYS,
    PAIR_BINDING_PROFILE,
    PairBinding,
    compute_dense_bound,
    derive_pair_output_path,
)


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_REVISION_PATTERN = re.compile(r"^[a-f0-9]{40}$")
APPROVAL_DOSSIER_PROFILE = "a0x-approval-dossier-json-v2"
EXECUTION_AUTHORIZATION_PROFILE = "a0x-execution-authorization-json-v2"
LEGACY_EXECUTION_AUTHORIZATION_PROFILE = EXECUTION_AUTHORIZATION_PROFILE
CURRENT_EXECUTION_AUTHORIZATION_PROFILE = "a0x-execution-authorization-json-v3"
QUALIFICATION_AUTHORIZATION_PROFILE = "a0x-qualification-authorization-json-v1"
_COMMITMENT_PREFIXES = {
    APPROVAL_DOSSIER_PROFILE: b"A0X-APPROVAL-DOSSIER-COMMITMENT-V2\x00",
    EXECUTION_AUTHORIZATION_PROFILE: b"A0X-EXECUTION-AUTHORIZATION-COMMITMENT-V2\x00",
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE: b"A0X-EXECUTION-AUTHORIZATION-COMMITMENT-V3\x00",
    QUALIFICATION_AUTHORIZATION_PROFILE: b"A0X-QUALIFICATION-AUTHORIZATION-COMMITMENT-V1\x00",
}
_COMMITMENT_SCHEMAS = {
    APPROVAL_DOSSIER_PROFILE: "a0x-authorization-dossier.schema.json",
    EXECUTION_AUTHORIZATION_PROFILE: "a0x-execution-authorization.schema.json",
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE: "a0x-execution-authorization-v3.schema.json",
    QUALIFICATION_AUTHORIZATION_PROFILE: "a0x-qualification-authorization.schema.json",
}
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class TerminalStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class LegContractIdentity:
    leg: Leg
    protocol_id: str
    protected_tree_sha256: str
    selection_corpus_sha256: str
    source_base_commit: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LegContractIdentity":
        try:
            return cls(
                leg=Leg(value["leg"]),
                protocol_id=str(value["protocol_id"]),
                protected_tree_sha256=str(value["protected_tree_sha256"]),
                selection_corpus_sha256=str(value["selection_corpus_sha256"]),
                source_base_commit=str(value["source_base_commit"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("leg contract identity is incomplete") from error

    def as_mapping(self) -> dict[str, str]:
        return {**asdict(self), "leg": self.leg.value}


@dataclass(frozen=True)
class LegFreezeBinding:
    leg: Leg
    protocol_id: str
    protocol_sha256: str
    implementation_sha256: str
    leg_freeze_sha256: str
    protected_tree_sha256: str
    selection_corpus_sha256: str
    source_base_commit: str


@dataclass(frozen=True)
class Commitment:
    profile: str
    commitment_sha256: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Commitment":
        try:
            _exact_keys(value, {"profile", "commitment_sha256"}, "commitment")
            profile = _nonempty_string(value, "profile")
            if profile not in _COMMITMENT_PREFIXES:
                raise ValueError("unknown commitment profile")
            return cls(profile=profile, commitment_sha256=_sha256(value, "commitment_sha256"))
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("commitment is incomplete or uses an unsupported profile") from error

    def as_mapping(self) -> dict[str, str]:
        return {"profile": self.profile, "commitment_sha256": self.commitment_sha256}


@dataclass(frozen=True)
class ModelCard:
    model_key: str
    model_id: str
    revision: str
    license_id: str
    architecture: str


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def strict_json_object(raw: bytes) -> dict[str, Any]:
    """Parse a commitment document without BOM, duplicate keys, or floats."""
    if not isinstance(raw, bytes) or raw.startswith(b"\xef\xbb\xbf"):
        raise A0XContractError("strict JSON rejects a BOM or non-bytes input")
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_strict_json_object_pairs,
            parse_float=_reject_json_float,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise A0XContractError("strict JSON parsing failed") from error
    _validate_commitment_value(value)
    if not isinstance(value, dict):
        raise A0XContractError("strict JSON commitment document must be an object")
    return value


def canonical_commitment(document: Mapping[str, Any], profile: str) -> Commitment:
    """Return a profile-separated commitment for one complete authorization document."""
    if profile not in _COMMITMENT_PREFIXES:
        raise A0XContractError("canonical commitment profile is unsupported")
    _validate_commitment_value(document)
    if not isinstance(document, Mapping):
        raise A0XContractError("canonical commitment document must be an object")
    _validate_authorization_document(document, _COMMITMENT_SCHEMAS[profile])
    try:
        encoded = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XContractError("canonical commitment cannot encode document") from error
    return Commitment(
        profile=profile,
        commitment_sha256=hashlib.sha256(_COMMITMENT_PREFIXES[profile] + encoded).hexdigest(),
    )


def assert_authorization_chain(
    dossier: Mapping[str, Any] | str | Path,
    authorization: Mapping[str, Any] | str | Path,
    downstream_artifacts: Iterable[Any],
) -> None:
    """Verify the acyclic dossier -> authorization -> downstream commitment chain."""
    dossier_value = _strict_document(dossier)
    authorization_value = _strict_document(authorization)
    _validate_authorization_document(dossier_value, "a0x-authorization-dossier.schema.json")
    authorization_profile = _execution_authorization_profile(authorization_value)
    _validate_authorization_document(
        authorization_value, _COMMITMENT_SCHEMAS[authorization_profile],
    )
    _reject_self_commitment(dossier_value, "dossier")
    _reject_self_commitment(authorization_value, "authorization")
    _document_profile(dossier_value, APPROVAL_DOSSIER_PROFILE)
    _document_profile(authorization_value, authorization_profile)

    dossier_pair = PairBinding.from_mapping(_mapping(dossier_value, "pair_binding"))
    authorization_pair = PairBinding.from_mapping(_mapping(authorization_value, "pair_binding"))
    if authorization_pair.as_mapping() != dossier_pair.as_mapping():
        raise A0XContractError("pair binding differs across authorization documents")
    dossier_implementation_source_head = _revision(
        dossier_value, "implementation_source_head",
    )
    if authorization_value.get("implementation_source_head") != dossier_implementation_source_head:
        raise A0XContractError("implementation source head differs across authorization documents")
    _revision(authorization_value, "source_head")

    # Runtime inlets are intentionally outside immutable result directories.
    # Keep their derivation and all public-safe execution bindings semantic, not
    # merely schema-shaped, before any commitment comparison can mask drift.
    from latent_triz.a0x_material_contract import (
        A0XGuardLaunch,
        validate_gate_a_evidence,
        validate_dossier_authorization_path,
        validate_guard_launch_pair_binding,
        validate_qualification_evidence,
    )

    dossier_inlet = validate_dossier_authorization_path(
        dossier_pair, _nonempty_string(authorization_value, "authorization_inlet_path"),
    )
    if authorization_value.get("authorization_inlet_path") != dossier_inlet:
        raise A0XContractError("authorization inlet is not pair-derived")
    launch = A0XGuardLaunch.from_mapping(_mapping(authorization_value, "guard_launch"))
    validate_guard_launch_pair_binding(authorization_pair, launch)
    if launch.source_head != authorization_value.get("source_head"):
        raise A0XContractError("guard launch source head differs from execution authorization")
    authorization_ccp = _mapping(authorization_value, "ccp")
    if authorization_ccp.get("sha256") != launch.ccp_sha256:
        raise A0XContractError("Gate C CCP identity differs from guard launch")
    if authorization_profile == CURRENT_EXECUTION_AUTHORIZATION_PROFILE:
        gate_a_evidence = validate_gate_a_evidence(
            _mapping(authorization_value, "gate_a_evidence"),
        )
        if gate_a_evidence["source_head"] != authorization_value.get("source_head"):
            raise A0XContractError("Gate A evidence source head differs from execution authorization")
        if gate_a_evidence["source_tree"] != authorization_value.get("source_tree"):
            raise A0XContractError("Gate A evidence source tree differs from execution authorization")
    else:
        qualification_evidence = validate_qualification_evidence(
            _mapping(authorization_value, "qualification_evidence"),
        )
        if qualification_evidence["qualified_source_head"] != authorization_value.get("source_head"):
            raise A0XContractError("qualification evidence source head differs from execution authorization")
        evidence_ccp = _mapping(qualification_evidence, "ccp")
        if (
            authorization_ccp.get("sha256") != evidence_ccp.get("binary_sha256")
            or authorization_ccp.get("source_commit") != evidence_ccp.get("source_commit")
            or authorization_ccp.get("qualified_source_tree") != evidence_ccp.get("qualified_source_tree")
            or authorization_ccp.get("version") != evidence_ccp.get("version")
        ):
            raise A0XContractError("qualification evidence CCP identity differs from execution authorization")

    expected_dossier = canonical_commitment(dossier_value, APPROVAL_DOSSIER_PROFILE)
    approved_dossier = Commitment.from_mapping(_mapping(authorization_value, "approved_dossier_commitment"))
    if approved_dossier != expected_dossier:
        raise A0XContractError("approved dossier commitment does not match dossier")
    expected_authorization = canonical_commitment(
        authorization_value, authorization_profile,
    )

    downstream_values = list(downstream_artifacts)
    if not downstream_values:
        raise A0XContractError("at least one downstream artifact is required")
    for downstream in downstream_values:
        _assert_downstream_authorization(
            _load_artifact(downstream),
            expected_pair=dossier_pair.as_mapping(),
            expected_dossier=expected_dossier,
            expected_authorization=expected_authorization,
            is_root=True,
        )


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def endpoint_indices(leg: Leg) -> tuple[int, ...]:
    return (0, 2, 4, 6) if leg is Leg.A0 else (6,)


def build_leg_freeze_binding(
    protocol_path: str | Path,
    implementation_path: str | Path,
    freeze_path: str | Path,
) -> LegFreezeBinding:
    protocol_file = Path(protocol_path)
    implementation_file = Path(implementation_path)
    freeze_file = Path(freeze_path)
    protocol = _read_json_object(protocol_file)
    implementation = _read_json_object(implementation_file)
    freeze = _read_json_object(freeze_file)
    protocol_identity = LegContractIdentity.from_mapping(_mapping(protocol, "identity"))
    implementation_identity = LegContractIdentity.from_mapping(_mapping(implementation, "identity"))
    freeze_identity = LegContractIdentity.from_mapping(_mapping(freeze, "identity"))
    if protocol_identity != implementation_identity or protocol_identity != freeze_identity:
        raise A0XContractError("leg freeze binding identity mismatch")
    protocol_sha256 = sha256_file(protocol_file)
    implementation_sha256 = sha256_file(implementation_file)
    if freeze.get("protocol_sha256") != protocol_sha256 or freeze.get("implementation_sha256") != implementation_sha256:
        raise A0XContractError("leg freeze binding shared artifact hash mismatch")
    return LegFreezeBinding(
        leg=freeze_identity.leg,
        protocol_id=freeze_identity.protocol_id,
        protocol_sha256=protocol_sha256,
        implementation_sha256=implementation_sha256,
        leg_freeze_sha256=sha256_file(freeze_file),
        protected_tree_sha256=freeze_identity.protected_tree_sha256,
        selection_corpus_sha256=freeze_identity.selection_corpus_sha256,
        source_base_commit=freeze_identity.source_base_commit,
    )


def assert_leg_freeze_binding(binding: LegFreezeBinding, dossiers: Iterable[Mapping[str, Any]]) -> None:
    for dossier in dossiers:
        pair = _mapping(dossier, "pair_binding")
        if pair.get("leg") != binding.leg.value or pair.get("leg_freeze_sha256") != binding.leg_freeze_sha256:
            raise A0XContractError("leg freeze binding does not match dossier pair binding")


def assert_pair_binding(root: PairBinding | Mapping[str, Any], referenced_artifacts: Iterable[Any]) -> None:
    root_mapping = root.as_mapping() if isinstance(root, PairBinding) else root
    expected = PairBinding.from_mapping(root_mapping).as_mapping()
    for artifact in referenced_artifacts:
        loaded = _load_artifact(artifact)
        for found in _find_pair_bindings(loaded):
            actual = PairBinding.from_mapping(found).as_mapping()
            if actual != expected:
                raise A0XContractError("pair binding differs from the required single leg/model pair")
        for occupancy in _find_occupancy_receipts(loaded):
            _assert_occupancy(expected, occupancy)


def assert_single_pair(rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    pairs: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise A0XContractError("exactly one leg/model pair is required")
        try:
            leg = Leg(row["leg"])
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("exactly one leg/model pair is required") from error
        model_key = row.get("model_key")
        if not isinstance(model_key, str) or model_key not in _MODEL_KEYS:
            raise A0XContractError("exactly one leg/model pair is required")
        pairs.add((leg.value, model_key))
    if len(pairs) != 1:
        raise A0XContractError("exactly one leg/model pair is required")
    return next(iter(pairs))


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XContractError(f"cannot read immutable contract artifact {path}") from error
    if not isinstance(value, dict):
        raise A0XContractError("immutable contract artifact must be a JSON object")
    return value


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    child = value.get(key)
    if not isinstance(child, Mapping):
        raise A0XContractError(f"{key} must be an object")
    return child


def _load_artifact(value: Any) -> Any:
    return _read_json_object(Path(value)) if isinstance(value, (str, Path)) else value


def _strict_document(value: Mapping[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, (str, Path)):
        try:
            raw = Path(value).read_bytes()
        except OSError as error:
            raise A0XContractError("cannot read strict authorization document") from error
        return strict_json_object(raw)
    _validate_commitment_value(value)
    if not isinstance(value, dict):
        raise A0XContractError("strict authorization document must be an object")
    return value


def _validate_authorization_document(value: Mapping[str, Any], schema_name: str) -> None:
    try:
        schema = json.loads((_REPOSITORY_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XContractError("authorization document schema is unavailable") from error
    issues = validate(dict(value), schema)
    if issues:
        raise A0XContractError(f"authorization document schema rejected input: {issues[0].message}")


def _execution_authorization_profile(value: Mapping[str, Any]) -> str:
    profile = value.get("commitment_profile")
    if profile not in {
        LEGACY_EXECUTION_AUTHORIZATION_PROFILE,
        CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
    }:
        raise A0XContractError("execution authorization commitment profile is unsupported")
    return profile


def _assert_downstream_authorization(
    value: Any,
    *,
    expected_pair: Mapping[str, Any],
    expected_dossier: Commitment,
    expected_authorization: Commitment,
    is_root: bool,
) -> None:
    if isinstance(value, Mapping):
        has_pair = "pair_binding" in value
        has_chain = "authorization_chain" in value
        if is_root and (not has_pair or not has_chain):
            raise A0XContractError("downstream artifact root must carry pair binding and authorization chain")
        if has_pair != has_chain:
            raise A0XContractError("authorization chain is missing for a downstream pair binding")
        if has_pair:
            pair = PairBinding.from_mapping(_mapping(value, "pair_binding")).as_mapping()
            if pair != expected_pair:
                raise A0XContractError("pair binding differs from the required single leg/model pair")
            chain = _mapping(value, "authorization_chain")
            _exact_keys(chain, {"dossier_commitment", "authorization_commitment"}, "authorization chain")
            dossier_commitment = Commitment.from_mapping(_mapping(chain, "dossier_commitment"))
            authorization_commitment = Commitment.from_mapping(_mapping(chain, "authorization_commitment"))
            if dossier_commitment != expected_dossier or authorization_commitment != expected_authorization:
                raise A0XContractError("authorization chain does not match authorization documents")
        for child in value.values():
            _assert_downstream_authorization(
                child,
                expected_pair=expected_pair,
                expected_dossier=expected_dossier,
                expected_authorization=expected_authorization,
                is_root=False,
            )
        return
    if isinstance(value, list):
        for child in value:
            _assert_downstream_authorization(
                child,
                expected_pair=expected_pair,
                expected_dossier=expected_dossier,
                expected_authorization=expected_authorization,
                is_root=False,
            )
        return
    if is_root:
        raise A0XContractError("downstream artifact root must be an object with authorization chain")


def _strict_json_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_float(value: str) -> None:
    raise ValueError(f"floating point number {value!r} is not permitted")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value!r} is not permitted")


def _validate_commitment_value(value: Any) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for child in value:
            _validate_commitment_value(child)
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise A0XContractError("canonical commitment rejects a non-string object key")
            _validate_commitment_value(child)
        return
    raise A0XContractError("canonical commitment rejects floats and unsupported types")


def _reject_self_commitment(value: Mapping[str, Any], document_kind: str) -> None:
    forbidden = (
        {"dossier_commitment", "authorization_commitment", "approved_dossier_commitment", "authorization_chain"}
        if document_kind == "dossier"
        else {"dossier_commitment", "authorization_commitment", "authorization_chain"}
    )
    if set(value).intersection(forbidden):
        raise A0XContractError(f"{document_kind} document contains its own commitment")


def _document_profile(value: Mapping[str, Any], expected: str) -> None:
    try:
        if _nonempty_string(value, "commitment_profile") != expected:
            raise ValueError("profile mismatch")
    except (KeyError, TypeError, ValueError) as error:
        raise A0XContractError("authorization document commitment profile is invalid") from error


def _find_pair_bindings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        pair = value.get("pair_binding")
        if isinstance(pair, Mapping):
            yield pair
        for child in value.values():
            yield from _find_pair_bindings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _find_pair_bindings(child)


def _find_occupancy_receipts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if value.get("artifact_class") == "a0x-output-occupancy-receipt":
            yield value
        for child in value.values():
            yield from _find_occupancy_receipts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _find_occupancy_receipts(child)


def _assert_occupancy(binding: Mapping[str, Any], occupancy: Mapping[str, Any]) -> None:
    dense = binding["dense_bound"]
    expected_total = dense["total_bytes"]
    expected_cap = dense["cap_bytes"]
    if expected_total > expected_cap:
        raise A0XContractError("occupancy reservation exceeds cap")
    if occupancy.get("allocated_bytes") != expected_total or occupancy.get("total_bytes") != expected_total:
        raise A0XContractError("occupancy receipt total does not match dense reservation")
    if occupancy.get("cap_bytes") != expected_cap:
        raise A0XContractError("occupancy receipt cap does not match dense reservation")


def _nonempty_string(value: Mapping[str, Any], key: str) -> str:
    candidate = value[key]
    if not isinstance(candidate, str) or not candidate:
        raise TypeError(f"{key} must be a non-empty string")
    return candidate


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} fields do not match the frozen profile")


def _sha256(value: Mapping[str, Any], key: str) -> str:
    candidate = _nonempty_string(value, key)
    if not _SHA256_PATTERN.fullmatch(candidate):
        raise ValueError(f"{key} must be a SHA-256")
    return candidate


def _revision(value: Mapping[str, Any], key: str) -> str:
    candidate = _nonempty_string(value, key)
    if not _REVISION_PATTERN.fullmatch(candidate):
        raise ValueError(f"{key} must be a revision")
    return candidate
