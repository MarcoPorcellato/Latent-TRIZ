from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


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
            return cls(
                leg=Leg(value["leg"]),
                cases=int(value["cases"]),
                view_site_count=int(value["view_site_count"]),
                endpoint_count=int(value["endpoint_count"]),
                hidden_width=int(value["hidden_width"]),
                scalar_bytes=int(value["scalar_bytes"]),
                vector_count=int(value["vector_count"]),
                dense_bytes=int(value["dense_bytes"]),
                dense_copy_count=int(value["dense_copy_count"]),
                atomic_dense_bytes=int(value["atomic_dense_bytes"]),
                index_copy_count=int(value["index_copy_count"]),
                index_reservation_bytes=int(value["index_reservation_bytes"]),
                payload_allowance_bytes=int(value["payload_allowance_bytes"]),
                total_bytes=int(value["total_bytes"]),
                cap_bytes=int(value["cap_bytes"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("dense bound is incomplete") from error

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
    leg: Leg
    leg_freeze_sha256: str
    model_key: str
    model_id: str
    revision: str
    run_id: str
    dossier_sha256: str
    authorization_sha256: str
    output_path: str
    dense_bound: DenseBound | Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PairBinding":
        try:
            dense = value["dense_bound"]
            return cls(
                leg=Leg(value["leg"]),
                leg_freeze_sha256=str(value["leg_freeze_sha256"]),
                model_key=str(value["model_key"]),
                model_id=str(value["model_id"]),
                revision=str(value["revision"]),
                run_id=str(value["run_id"]),
                dossier_sha256=str(value["dossier_sha256"]),
                authorization_sha256=str(value["authorization_sha256"]),
                output_path=str(value["output_path"]),
                dense_bound=DenseBound.from_mapping(dense) if isinstance(dense, Mapping) else dense,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("pair binding is incomplete") from error

    def as_mapping(self) -> dict[str, Any]:
        dense = self.dense_bound
        dense_mapping = dense.as_mapping() if isinstance(dense, DenseBound) else dict(dense)
        return {
            "leg": self.leg.value,
            "leg_freeze_sha256": self.leg_freeze_sha256,
            "model_key": self.model_key,
            "model_id": self.model_id,
            "revision": self.revision,
            "run_id": self.run_id,
            "dossier_sha256": self.dossier_sha256,
            "authorization_sha256": self.authorization_sha256,
            "output_path": self.output_path,
            "dense_bound": dense_mapping,
        }


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
    expected = root.as_mapping() if isinstance(root, PairBinding) else PairBinding.from_mapping(root).as_mapping()
    for artifact in referenced_artifacts:
        for found in _find_pair_bindings(_load_artifact(artifact)):
            actual = PairBinding.from_mapping(found).as_mapping()
            if actual != expected:
                raise A0XContractError("pair binding differs from the required single leg/model pair")


def assert_single_pair(rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    pairs = {(str(row.get("leg")), str(row.get("model_key"))) for row in rows}
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
