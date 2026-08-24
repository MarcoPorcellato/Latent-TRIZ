from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from latent_triz.validator import validate


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_REVISION_PATTERN = re.compile(r"^[a-f0-9]{40}$")
_SAFE_PATH_PATTERN = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
_MODEL_KEYS = frozenset((
    "smollm2_360m",
    "qwen3_0_6b_base",
    "gpt2",
    "smollm2_135m",
    "gpt_neo_125m",
    "qwen2_5_0_5b",
))
PAIR_BINDING_PROFILE = "a0x-pair-scope-v2"
APPROVAL_DOSSIER_PROFILE = "a0x-approval-dossier-json-v1"
EXECUTION_AUTHORIZATION_PROFILE = "a0x-execution-authorization-json-v1"
_COMMITMENT_PREFIXES = {
    APPROVAL_DOSSIER_PROFILE: b"A0X-APPROVAL-DOSSIER-COMMITMENT-V1\x00",
    EXECUTION_AUTHORIZATION_PROFILE: b"A0X-EXECUTION-AUTHORIZATION-COMMITMENT-V1\x00",
}
_COMMITMENT_SCHEMAS = {
    APPROVAL_DOSSIER_PROFILE: "a0x-authorization-dossier.schema.json",
    EXECUTION_AUTHORIZATION_PROFILE: "a0x-execution-authorization.schema.json",
}
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class A0XContractError(ValueError):
    """Raised when immutable A0X identity or per-pair bindings disagree."""


class Leg(StrEnum):
    A0 = "a0"
    R1 = "r1"


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
class DenseBound:
    leg: Leg
    cases: int
    view_site_count: int
    endpoint_count: int
    hidden_width: int
    scalar_bytes: int
    vector_count: int
    dense_bytes: int
    dense_copy_count: int
    atomic_dense_bytes: int
    index_copy_count: int
    index_reservation_bytes: int
    payload_allowance_bytes: int
    total_bytes: int
    cap_bytes: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DenseBound":
        try:
            bound = cls(
                leg=Leg(value["leg"]),
                cases=_integer(value, "cases"),
                view_site_count=_integer(value, "view_site_count"),
                endpoint_count=_integer(value, "endpoint_count"),
                hidden_width=_integer(value, "hidden_width"),
                scalar_bytes=_integer(value, "scalar_bytes"),
                vector_count=_integer(value, "vector_count"),
                dense_bytes=_integer(value, "dense_bytes"),
                dense_copy_count=_integer(value, "dense_copy_count"),
                atomic_dense_bytes=_integer(value, "atomic_dense_bytes"),
                index_copy_count=_integer(value, "index_copy_count"),
                index_reservation_bytes=_integer(value, "index_reservation_bytes"),
                payload_allowance_bytes=_integer(value, "payload_allowance_bytes"),
                total_bytes=_integer(value, "total_bytes"),
                cap_bytes=_integer(value, "cap_bytes"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("dense bound is incomplete") from error
        expected = compute_dense_bound(bound.leg, cases=bound.cases, hidden_width=bound.hidden_width)
        if bound != expected:
            raise A0XContractError("dense bound violates frozen reservation contract")
        return bound

    def as_mapping(self) -> dict[str, Any]:
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
class PairBinding:
    binding_profile: str
    leg: Leg
    leg_freeze_sha256: str
    model_key: str
    model_id: str
    revision: str
    run_id: str
    output_path: str
    dense_bound: DenseBound | Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PairBinding":
        try:
            _exact_keys(
                value,
                {
                    "binding_profile", "leg", "leg_freeze_sha256", "model_key", "model_id",
                    "revision", "run_id", "output_path", "dense_bound",
                },
                "pair binding",
            )
            dense = value["dense_bound"]
            if not isinstance(dense, Mapping):
                raise TypeError("dense_bound must be an object")
            binding = cls(
                binding_profile=_profile(value, "binding_profile", PAIR_BINDING_PROFILE),
                leg=Leg(value["leg"]),
                leg_freeze_sha256=_sha256(value, "leg_freeze_sha256"),
                model_key=_model_key(value),
                model_id=_nonempty_string(value, "model_id"),
                revision=_revision(value, "revision"),
                run_id=_nonempty_string(value, "run_id"),
                output_path=_relative_path(value, "output_path"),
                dense_bound=DenseBound.from_mapping(dense),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("pair binding is incomplete") from error
        if binding.dense_bound.leg is not binding.leg:
            raise A0XContractError("pair binding dense bound leg mismatch")
        return binding

    def as_mapping(self) -> dict[str, Any]:
        dense = self.dense_bound
        dense_mapping = dense.as_mapping() if isinstance(dense, DenseBound) else dict(dense)
        return {
            "binding_profile": self.binding_profile,
            "leg": self.leg.value,
            "leg_freeze_sha256": self.leg_freeze_sha256,
            "model_key": self.model_key,
            "model_id": self.model_id,
            "revision": self.revision,
            "run_id": self.run_id,
            "output_path": self.output_path,
            "dense_bound": dense_mapping,
        }


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
    _validate_authorization_document(authorization_value, "a0x-execution-authorization.schema.json")
    _reject_self_commitment(dossier_value, "dossier")
    _reject_self_commitment(authorization_value, "authorization")
    _document_profile(dossier_value, APPROVAL_DOSSIER_PROFILE)
    _document_profile(authorization_value, EXECUTION_AUTHORIZATION_PROFILE)

    dossier_pair = PairBinding.from_mapping(_mapping(dossier_value, "pair_binding"))
    authorization_pair = PairBinding.from_mapping(_mapping(authorization_value, "pair_binding"))
    if authorization_pair.as_mapping() != dossier_pair.as_mapping():
        raise A0XContractError("pair binding differs across authorization documents")

    expected_dossier = canonical_commitment(dossier_value, APPROVAL_DOSSIER_PROFILE)
    approved_dossier = Commitment.from_mapping(_mapping(authorization_value, "approved_dossier_commitment"))
    if approved_dossier != expected_dossier:
        raise A0XContractError("approved dossier commitment does not match dossier")
    expected_authorization = canonical_commitment(
        authorization_value, EXECUTION_AUTHORIZATION_PROFILE,
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


def compute_dense_bound(leg: Leg, *, cases: int, hidden_width: int) -> DenseBound:
    vectors = 48 * 10 * 5 if leg is Leg.A0 else 48 * 2 * 2
    dense = vectors * hidden_width * 4
    index_bytes = 6_291_456 if leg is Leg.A0 else 1_048_576
    payload_bytes = 2_097_152 if leg is Leg.A0 else 524_288
    cap = 33_554_432 if leg is Leg.A0 else 4_194_304
    total = dense * 2 + index_bytes + payload_bytes
    if cases != 48 or hidden_width <= 0 or total > cap:
        raise A0XContractError("dense output reservation exceeds frozen contract")
    return DenseBound(
        leg, cases, 10 if leg is Leg.A0 else 2,
        5 if leg is Leg.A0 else 2, hidden_width, 4, vectors,
        dense, 2, dense * 2, 2, index_bytes, payload_bytes, total, cap,
    )


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


def _integer(value: Mapping[str, Any], key: str) -> int:
    candidate = value[key]
    if not isinstance(candidate, int) or isinstance(candidate, bool):
        raise TypeError(f"{key} must be an integer")
    return candidate


def _nonempty_string(value: Mapping[str, Any], key: str) -> str:
    candidate = value[key]
    if not isinstance(candidate, str) or not candidate:
        raise TypeError(f"{key} must be a non-empty string")
    return candidate


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


def _relative_path(value: Mapping[str, Any], key: str) -> str:
    candidate = _nonempty_string(value, key)
    if not _SAFE_PATH_PATTERN.fullmatch(candidate):
        raise ValueError(f"{key} must be a repository-relative path")
    return candidate


def _model_key(value: Mapping[str, Any]) -> str:
    candidate = _nonempty_string(value, "model_key")
    if candidate not in _MODEL_KEYS:
        raise ValueError("model_key is not an approved A0X model")
    return candidate


def _profile(value: Mapping[str, Any], key: str, expected: str) -> str:
    candidate = _nonempty_string(value, key)
    if candidate != expected:
        raise ValueError(f"{key} must equal {expected}")
    return candidate


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{label} fields do not match the frozen profile")
