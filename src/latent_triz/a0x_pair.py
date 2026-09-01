"""Pure canonical identity and output derivation for one A0X pair."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Mapping


_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
_REVISION_PATTERN = re.compile(r"^[a-f0-9]{40}$")
_SAFE_PATH_PATTERN = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
PAIR_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MODEL_KEYS = frozenset((
    "smollm2_360m",
    "qwen3_0_6b_base",
    "gpt2",
    "smollm2_135m",
    "gpt_neo_125m",
    "qwen2_5_0_5b",
))
PAIR_BINDING_PROFILE = "a0x-pair-scope-v2"

# JSON Schema projection metadata for PairBinding.  This is the only
# future-facing field contract consumed by the offline schema compiler.
PAIR_BINDING_FIELD_METADATA: dict[str, dict[str, Any]] = {
    "binding_profile": {"const": PAIR_BINDING_PROFILE},
    "leg": {"enum": ["a0", "r1"]},
    "leg_freeze_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    "model_key": {"enum": sorted(MODEL_KEYS)},
    "model_id": {"type": "string", "minLength": 1},
    "revision": {"type": "string", "pattern": "^[a-f0-9]{40}$"},
    "run_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"},
    "output_path": {
        "type": "string",
        "pattern": "^results/a0x/(?:a0|r1)/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$",
    },
    "dense_bound": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "leg", "cases", "view_site_count", "endpoint_count", "hidden_width",
            "scalar_bytes", "vector_count", "dense_bytes", "dense_copy_count",
            "atomic_dense_bytes", "index_copy_count", "index_reservation_bytes",
            "payload_allowance_bytes", "total_bytes", "cap_bytes",
        ],
        "properties": {
            "leg": {"enum": ["a0", "r1"]},
            "cases": {"type": "integer", "const": 48},
            "view_site_count": {"type": "integer", "minimum": 1},
            "endpoint_count": {"type": "integer", "minimum": 1},
            "hidden_width": {"type": "integer", "minimum": 1},
            "scalar_bytes": {"type": "integer", "const": 4},
            "vector_count": {"type": "integer", "minimum": 1},
            "dense_bytes": {"type": "integer", "minimum": 1},
            "dense_copy_count": {"type": "integer", "const": 2},
            "atomic_dense_bytes": {"type": "integer", "minimum": 1},
            "index_copy_count": {"type": "integer", "const": 2},
            "index_reservation_bytes": {"enum": [6_291_456, 1_048_576]},
            "payload_allowance_bytes": {"enum": [2_097_152, 524_288]},
            "total_bytes": {"type": "integer", "minimum": 1},
            "cap_bytes": {"enum": [33_554_432, 4_194_304]},
        },
    },
}


class A0XContractError(ValueError):
    """Raised when immutable A0X identity or per-pair bindings disagree."""


class Leg(StrEnum):
    A0 = "a0"
    R1 = "r1"


def derive_pair_output_path(leg: Leg | str, model_key: str, run_id: str) -> str:
    """Return sole public, run-specific output directory for one A0X pair."""
    try:
        parsed_leg = Leg(leg)
    except (TypeError, ValueError) as error:
        raise A0XContractError("leg is not a supported A0X pair segment") from error
    for label, value in (("model key", model_key), ("run id", run_id)):
        if not isinstance(value, str) or not PAIR_SEGMENT.fullmatch(value):
            raise A0XContractError(f"{label} is not a safe pair segment")
    return f"results/a0x/{parsed_leg.value}/{model_key}/{run_id}"


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
            _exact_keys(
                value,
                set(PAIR_BINDING_FIELD_METADATA["dense_bound"]["required"]),
                "dense bound",
            )
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
                run_id=_pair_segment(value, "run_id", "run id"),
                output_path=_relative_path(value, "output_path"),
                dense_bound=DenseBound.from_mapping(dense),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise A0XContractError("pair binding is incomplete") from error
        if binding.dense_bound.leg is not binding.leg:
            raise A0XContractError("pair binding dense bound leg mismatch")
        if binding.output_path != derive_pair_output_path(
            binding.leg, binding.model_key, binding.run_id,
        ):
            raise A0XContractError("pair binding output path differs from derived output path")
        return binding

    @classmethod
    def from_dossier(cls, dossier: Mapping[str, Any]) -> "PairBinding":
        try:
            return cls.from_mapping(dossier["pair_binding"])
        except (KeyError, TypeError) as error:
            raise A0XContractError("dossier pair binding is incomplete") from error

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

    def assert_equivalent(self, value: Mapping[str, Any]) -> None:
        if self.as_mapping() != PairBinding.from_mapping(value).as_mapping():
            raise A0XContractError("pair binding differs from canonical pair")


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


def _pair_segment(value: Mapping[str, Any], key: str, label: str) -> str:
    candidate = _nonempty_string(value, key)
    if not PAIR_SEGMENT.fullmatch(candidate):
        raise ValueError(f"{label} is not a safe pair segment")
    return candidate


def _model_key(value: Mapping[str, Any]) -> str:
    candidate = _pair_segment(value, "model_key", "model key")
    if candidate not in MODEL_KEYS:
        raise ValueError("model_key is not an approved A0X model")
    return candidate


def _profile(value: Mapping[str, Any], key: str, expected: str) -> str:
    candidate = _nonempty_string(value, key)
    if candidate != expected:
        raise ValueError(f"{key} must equal {expected}")
    return candidate


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} fields do not match the frozen profile")
