"""Frozen, target-reader-free A0X-R1 fixed-primary analysis."""
from __future__ import annotations

import hashlib
import json
import math
import random
import struct
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .a0x_contract import Leg, PairBinding
from .a0x_a0_analysis import (
    _apply,
    _bytes_sha,
    _combo_metrics,
    _mapping,
    _pair,
    _parse_registered_receipt,
    _parse_safetensors,
    _score_operator,
    _target_metadata,
    SCORE_QUANTIZATION_DECIMALS,
)


class A0XR1AnalysisError(RuntimeError):
    """Raised when a frozen A0X-R1 analysis input is inconsistent."""


_COMMON = {"empirical": True, "scientific_status": "exploratory", "evidence_eligible": False, "expert_validated": False, "claim_ids": []}
_PRIMARY = ("problem_plus_transformation", 6, "mean_transformation_span")
_BASELINE = ("problem_only", 6, "sentinel")
_PERMUTATION_SEED = 20260815
_PERMUTATION_BUDGET = 999


def frozen_positive(*, p_value: float, margin: float, family_successes: int, domain_successes: int) -> bool:
    """Return the sole predeclared R1 positive decision, including boundaries."""
    return p_value <= 0.05 and margin >= 0.10 and family_successes >= 17 and domain_successes >= 4


def analyze_a0x_r1(
    *, pair_binding: Mapping[str, Any], target_rows: Sequence[Mapping[str, Any]],
    target_read_receipt_bytes: bytes, activation_receipt_bytes: bytes,
    dense_asset_bytes: bytes, index_bytes: bytes, shortcut_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Analyze already-read one-shot rows and immutable activation bytes.

    This signature deliberately excludes a target path, reader, root, and
    filesystem capability.  Task 6 alone reads target content exactly once.
    """
    try:
        pair = PairBinding.from_mapping(pair_binding)
    except Exception as error:
        raise A0XR1AnalysisError("analysis pair binding is invalid") from error
    if pair.leg is not Leg.R1:
        raise A0XR1AnalysisError("A0X R1 analysis requires leg r1")
    if shortcut_result.get("status") != "pass":
        return {"status": "non_interpretable", "reason": "shortcut gate is not pass"}
    activation = _parse_receipt(activation_receipt_bytes, "a0x-activation-receipt.schema.json")
    target_receipt = _parse_receipt(target_read_receipt_bytes, "a0x-target-read-receipt.schema.json")
    _validate_activation_receipt(activation, pair)
    _validate_target_receipt(target_receipt, pair, activation_receipt_bytes, dense_asset_bytes, index_bytes)
    case_ids, labels, families, domains = _target_metadata(target_rows)
    combos, final_index = _materialize_combos(index_bytes, dense_asset_bytes, case_ids, pair, activation)
    if set(combos) != {_PRIMARY, _BASELINE, (_PRIMARY[0], final_index, _PRIMARY[2]), (_BASELINE[0], final_index, _BASELINE[2])}:
        raise A0XR1AnalysisError("representation index does not cover the frozen R1 grid")
    primary_operator = _score_operator(combos[_PRIMARY], domains, alpha=1.0)
    baseline_operator = _score_operator(combos[_BASELINE], domains, alpha=1.0)
    primary = _combo_metrics(primary_operator, labels, families, domains)
    baseline = _combo_metrics(baseline_operator, labels, families, domains)
    primary_scores = _apply(primary_operator, labels)
    directions = _domain_direction_metrics(primary_scores, labels, families, domains)
    direction_count = sum(value > 0.0 for value in directions.values()) if len(directions) == 6 else 0
    null_values = _family_permutation_null(primary_operator, labels, families, seed=_PERMUTATION_SEED, budget=_PERMUTATION_BUDGET)
    p_value = (1 + sum(value >= primary["family_successes"] for value in null_values)) / (_PERMUTATION_BUDGET + 1)
    margin = float(primary["macro_f1"]) - float(baseline["macro_f1"])
    positive = frozen_positive(
        p_value=p_value, margin=margin, family_successes=int(primary["family_successes"]), domain_successes=direction_count,
    )
    final_primary = _combo_metrics(combos_to_operator(combos[(_PRIMARY[0], final_index, _PRIMARY[2])], domains), labels, families, domains)
    final_baseline = _combo_metrics(combos_to_operator(combos[(_BASELINE[0], final_index, _BASELINE[2])], domains), labels, families, domains)
    return {
        "artifact_class": "a0x-statistical-result", **_COMMON, "pair_binding": pair.as_mapping(),
        "status": "positive" if positive else "null", "p_value": p_value,
        "score_quantization_decimals": SCORE_QUANTIZATION_DECIMALS,
        "primary": {"tuple_index": 6, **primary, "max_statistic_p": p_value, "permutation_seed": _PERMUTATION_SEED, "permutation_budget": _PERMUTATION_BUDGET, "null_distribution_sha256": _canonical_sha(null_values)},
        "surface_baseline": {"tuple_index": 6, **baseline},
        "macro_f1_margin_over_surface": margin, "domain_direction_successes": directions,
        "domain_direction_success_count": direction_count,
        "descriptive_final_block": {
            "rescues_primary": False, "tuple_index": final_index,
            "primary_analogue": final_primary, "surface_baseline_analogue": final_baseline,
        },
        "outcome_rule": {
            "permutation_p_at_most": 0.05, "macro_f1_margin_at_least": 0.10,
            "family_successes_at_least": 17, "positive_direction_domains_at_least": 4,
            "passed": positive,
        },
    }


def combos_to_operator(matrix: Sequence[Sequence[float]], domains: Sequence[str]) -> Any:
    """Name the fixed historical LODO operator used for final-block description."""
    return _score_operator(matrix, domains, alpha=1.0)


def _parse_receipt(payload: bytes, schema_name: str) -> Mapping[str, Any]:
    try:
        return _parse_registered_receipt(payload, schema_name, require_trailing_newline=True)
    except Exception as error:
        raise A0XR1AnalysisError("persisted receipt fails strict schema or exact LF encoding") from error


def _validate_target_receipt(receipt: Mapping[str, Any], pair: PairBinding, activation: bytes, dense: bytes, index: bytes) -> None:
    if receipt.get("content_reads") != 1 or receipt.get("status") != "pass":
        raise A0XR1AnalysisError("analysis requires one passing target read")
    try:
        observed = PairBinding.from_mapping(_mapping(receipt, "pair_binding"))
    except Exception as error:
        raise A0XR1AnalysisError("target receipt pair binding is invalid") from error
    if observed.as_mapping() != pair.as_mapping():
        raise A0XR1AnalysisError("target receipt pair binding differs from analysis pair binding")
    expected = {"activation_receipt_sha256": _bytes_sha(activation), "dense_sha256": _bytes_sha(dense), "index_sha256": _bytes_sha(index)}
    if any(receipt.get(name) != value for name, value in expected.items()):
        raise A0XR1AnalysisError("target receipt activation asset links differ from analysis inputs")


def _validate_activation_receipt(receipt: Mapping[str, Any], pair: PairBinding) -> None:
    if receipt.get("leg") != "r1" or receipt.get("activation_status") != "completed" or receipt.get("activation_target_content_reads") != 0:
        raise A0XR1AnalysisError("activation receipt is not a target-free completed R1 receipt")
    try:
        observed = PairBinding.from_mapping(_mapping(receipt, "pair_binding"))
    except Exception as error:
        raise A0XR1AnalysisError("activation receipt pair binding is invalid") from error
    if observed.as_mapping() != pair.as_mapping():
        raise A0XR1AnalysisError("activation receipt pair binding differs from analysis pair binding")
    if _mapping(receipt, "planned_dense_bound") != pair.dense_bound.as_mapping():
        raise A0XR1AnalysisError("activation planned dense bound differs from analysis pair binding")
    if tuple(receipt.get("literal_tuple_indices", ())) != (6,):
        raise A0XR1AnalysisError("activation literal tuple index drift")
    final = receipt.get("final_block_tuple_index")
    if not isinstance(final, int) or final < 7:
        raise A0XR1AnalysisError("activation final block tuple index drift")
    if receipt.get("record_count") != pair.dense_bound.vector_count:
        raise A0XR1AnalysisError("activation record count differs from frozen R1 dense bound")


def _materialize_combos(index_bytes: bytes, dense_bytes: bytes, case_ids: Sequence[str], pair: PairBinding, receipt: Mapping[str, Any]) -> tuple[dict[tuple[str, int, str], list[list[float]]], int]:
    if not isinstance(index_bytes, bytes) or not isinstance(dense_bytes, bytes):
        raise A0XR1AnalysisError("analysis assets must be immutable bytes")
    if _mapping(receipt, "dense").get("sha256") != _bytes_sha(dense_bytes) or _mapping(receipt, "index").get("sha256") != _bytes_sha(index_bytes):
        raise A0XR1AnalysisError("activation receipt asset hash differs from analysis bytes")
    rows = _parse_index(index_bytes)
    vectors = _parse_safetensors(dense_bytes, pair.dense_bound.hidden_width)
    if len(rows) != 192 or len(vectors) != 192:
        raise A0XR1AnalysisError("R1 dense/index assets differ from frozen 192-vector bound")
    final = int(receipt["final_block_tuple_index"])
    expected = {_PRIMARY, _BASELINE, (_PRIMARY[0], final, _PRIMARY[2]), (_BASELINE[0], final, _BASELINE[2])}
    grouped: dict[tuple[str, int, str], dict[str, list[float]]] = defaultdict(dict)
    for row in rows:
        try:
            case_id = str(row["case_id"]); combo = (str(row["view"]), int(row["tuple_index"]), str(row["token_site"])); key = str(row["tensor_key"])
        except (KeyError, TypeError, ValueError) as error:
            raise A0XR1AnalysisError("representation index record is invalid") from error
        if combo not in expected or row.get("endpoint_role") != ("primary" if combo[1] == 6 else "descriptive"):
            raise A0XR1AnalysisError("representation index endpoint contract drift")
        raw = vectors.get(key)
        if raw is None or case_id in grouped[combo]:
            raise A0XR1AnalysisError("representation index is duplicate or vector is unavailable")
        if row.get("vector_dim") != pair.dense_bound.hidden_width or row.get("dtype") != "float32" or row.get("vector_sha256") != _bytes_sha(raw):
            raise A0XR1AnalysisError("representation vector identity differs from frozen index")
        vector = list(struct.unpack(f"<{pair.dense_bound.hidden_width}f", raw))
        if not vector or not all(math.isfinite(value) for value in vector):
            raise A0XR1AnalysisError("representation vector is invalid")
        grouped[combo][case_id] = vector
    if set(grouped) != expected or any(set(values) != set(case_ids) for values in grouped.values()):
        raise A0XR1AnalysisError("representation index does not cover the frozen R1 grid")
    return {combo: [values[case_id] for case_id in case_ids] for combo, values in grouped.items()}, final


def _parse_index(payload: bytes) -> list[Mapping[str, Any]]:
    try:
        rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XR1AnalysisError("representation index bytes are invalid") from error
    if any(not isinstance(row, Mapping) for row in rows):
        raise A0XR1AnalysisError("representation index rows are invalid")
    return rows


def _domain_direction_metrics(scores: Sequence[float], labels: Sequence[int], families: Sequence[str], domains: Sequence[str]) -> dict[str, float]:
    grouped: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for index, (family, domain) in enumerate(zip(families, domains, strict=True)):
        grouped[str(domain)][str(family)].append(index)
    output: dict[str, float] = {}
    for domain, per_family in sorted(grouped.items()):
        deltas: list[float] = []
        for family, indices in sorted(per_family.items()):
            if len(indices) != 2 or sorted(labels[index] for index in indices) != [0, 1]:
                raise A0XR1AnalysisError(f"family {family} in {domain} is not balanced")
            positive = next(index for index in indices if labels[index] == 1)
            negative = next(index for index in indices if labels[index] == 0)
            deltas.append(float(scores[positive]) - float(scores[negative]))
        output[domain] = math.fsum(deltas) / len(deltas)
    return output


def _family_permutation_null(operator: Any, labels: Sequence[int], families: Sequence[str], *, seed: int, budget: int) -> list[int]:
    """Exact historical R1 within-family-swap null, with deterministic 999 draws."""
    members: dict[str, list[int]] = defaultdict(list)
    for index, family in enumerate(families):
        members[str(family)].append(index)
    ordered = [members[family] for family in sorted(members)]
    if any(len(indices) != 2 for indices in ordered):
        raise A0XR1AnalysisError("non-paired family in permutation")
    rng = random.Random(seed)
    seen: set[int] = set(); values: list[int] = []
    while len(values) < budget:
        mask = rng.getrandbits(len(ordered))
        if mask in seen:
            continue
        seen.add(mask)
        permuted = list(labels)
        for bit, indices in enumerate(ordered):
            if mask & (1 << bit):
                first, second = indices
                permuted[first], permuted[second] = permuted[second], permuted[first]
        scores = _apply(operator, permuted)
        values.append(_family_successes(scores, permuted, families))
    return values


def _family_successes(scores: Sequence[float], labels: Sequence[int], families: Sequence[str]) -> int:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, family in enumerate(families):
        grouped[str(family)].append(index)
    successes = 0
    for family, indices in sorted(grouped.items()):
        if len(indices) != 2 or sorted(labels[index] for index in indices) != [0, 1]:
            raise A0XR1AnalysisError(f"family {family} is not a balanced pair")
        positive = next(index for index in indices if labels[index] == 1)
        negative = next(index for index in indices if labels[index] == 0)
        successes += float(scores[positive]) > float(scores[negative])
    return successes


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


__all__ = ["A0XR1AnalysisError", "analyze_a0x_r1", "frozen_positive"]
