"""Frozen, target-reader-free A0X-A0 statistical analysis."""
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


class A0XA0AnalysisError(RuntimeError):
    """Raised when a frozen A0X-A0 analysis input is inconsistent."""


_COMMON = {"empirical": True, "scientific_status": "exploratory", "evidence_eligible": False, "expert_validated": False, "claim_ids": []}
_LITERAL = (0, 2, 4, 6)
_SITES = ("sentinel", "final_transformation_token", "mean_transformation_span")
_VIEWS = {"problem_only": ("sentinel",), "transformation_only": _SITES, "problem_plus_transformation": _SITES, "problem_plus_solution": _SITES}


def analyze_a0x_a0(
    *, pair_binding: Mapping[str, Any], target_rows: Sequence[Mapping[str, Any]],
    target_read_receipt_bytes: bytes, activation_receipt_bytes: bytes,
    dense_asset_bytes: bytes, index_bytes: bytes,
    shortcut_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Analyze already-read one-shot rows and already-verified in-memory assets.

    The signature intentionally has no target path, reader, root, or generic
    filesystem capability.  Target bytes must have been consumed exactly once
    by Task 6 before this function receives their parsed rows.
    """
    pair = _pair(pair_binding)
    if pair.leg is not Leg.A0:
        raise A0XA0AnalysisError("A0X A0 analysis requires leg a0")
    if shortcut_result.get("status") != "pass":
        return {"status": "non_interpretable", "reason": "shortcut gate is not pass"}
    activation_receipt = _parse_registered_receipt(
        activation_receipt_bytes, "a0x-activation-receipt.schema.json", require_trailing_newline=True,
    )
    target_read_receipt = _parse_registered_receipt(
        target_read_receipt_bytes, "a0x-target-read-receipt.schema.json", require_trailing_newline=True,
    )
    _validate_activation_receipt(activation_receipt, pair)
    _validate_target_receipt(
        target_read_receipt, pair, activation_receipt_bytes, dense_asset_bytes, index_bytes,
    )
    case_ids, labels, families, domains = _target_metadata(target_rows)
    combos, final_index = _materialize_combos(index_bytes, dense_asset_bytes, case_ids, pair, activation_receipt)
    primary_combos = [("problem_plus_transformation", index, site) for index in _LITERAL for site in _SITES]
    surface_combos = [("problem_only", index, "sentinel") for index in _LITERAL]
    if set(primary_combos) - set(combos) or set(surface_combos) - set(combos):
        raise A0XA0AnalysisError("frozen primary or surface representation is missing")
    operators = {combo: _score_operator(matrix, domains, alpha=1.0) for combo, matrix in combos.items()}
    primary_metrics = {_combo_name(index, site): _combo_metrics(operators[(view, index, site)], labels, families, domains) for view, index, site in primary_combos}
    surface_metrics = {_combo_name(index, site): _combo_metrics(operators[(view, index, site)], labels, families, domains) for view, index, site in surface_combos}
    observed = max(value["family_successes"] for value in primary_metrics.values())
    null_maxima = _null_maxima(operators, primary_combos, labels, families, seed=20260814, budget=199)
    p_value = (1 + sum(value >= observed for value in null_maxima)) / 200
    primary_f1 = max(value["macro_f1"] for value in primary_metrics.values())
    surface_f1 = max(value["macro_f1"] for value in surface_metrics.values())
    margin = primary_f1 - surface_f1
    final_metrics = {
        f"{view}::{site}": _combo_metrics(operators[(view, final_index, site)], labels, families, domains)
        for view, sites in _VIEWS.items() for site in sites
    }
    positive = p_value <= 0.05 and margin >= 0.10 and observed >= 19
    return {
        "artifact_class": "a0x-statistical-result", **_COMMON, "pair_binding": pair.as_mapping(),
        "status": "positive" if positive else "null", "p_value": p_value,
        "primary": {"multiplicity": 12, "combinations": primary_metrics, "observed_max_family_successes": observed, "max_statistic_p": p_value, "maximum_macro_f1": primary_f1, "null_maxima_sha256": _sha(null_maxima)},
        "surface_baseline": {"multiplicity": 4, "combinations": surface_metrics, "maximum_macro_f1": surface_f1},
        "macro_f1_margin_over_surface": margin,
        "descriptive_final_block": {"rescues_primary": False, "tuple_index": final_index, "combinations": final_metrics},
        "outcome_rule": {"max_statistic_p_at_most": 0.05, "macro_f1_margin_at_least": 0.10, "family_successes_at_least": 19, "passed": positive},
    }


def _pair(value: Mapping[str, Any]) -> PairBinding:
    try:
        return PairBinding.from_mapping(value)
    except Exception as error:
        raise A0XA0AnalysisError("analysis pair binding is invalid") from error


def _validate_target_receipt(receipt: Mapping[str, Any], pair: PairBinding, activation_bytes: bytes, dense: bytes, index: bytes) -> None:
    if receipt.get("content_reads") != 1 or receipt.get("status") != "pass":
        raise A0XA0AnalysisError("analysis requires one passing target read")
    if _pair(_mapping(receipt, "pair_binding")).as_mapping() != pair.as_mapping():
        raise A0XA0AnalysisError("target receipt pair binding differs from analysis pair binding")
    expected = {"activation_receipt_sha256": _bytes_sha(activation_bytes), "dense_sha256": _bytes_sha(dense), "index_sha256": _bytes_sha(index)}
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise A0XA0AnalysisError("target receipt activation asset links differ from analysis inputs")


def _validate_activation_receipt(receipt: Mapping[str, Any], pair: PairBinding) -> None:
    if receipt.get("leg") != "a0" or receipt.get("activation_status") != "completed" or receipt.get("activation_target_content_reads") != 0:
        raise A0XA0AnalysisError("activation receipt is not a target-free completed A0 receipt")
    if _pair(_mapping(receipt, "pair_binding")).as_mapping() != pair.as_mapping():
        raise A0XA0AnalysisError("activation receipt pair binding differs from analysis pair binding")
    if _mapping(receipt, "planned_dense_bound") != pair.dense_bound.as_mapping():
        raise A0XA0AnalysisError("activation planned dense bound differs from analysis pair binding")
    if tuple(receipt.get("literal_tuple_indices", ())) != _LITERAL:
        raise A0XA0AnalysisError("activation literal tuple indices drift")
    final = receipt.get("final_block_tuple_index")
    if not isinstance(final, int) or final in _LITERAL or final < 0:
        raise A0XA0AnalysisError("activation final block tuple index drift")
    if receipt.get("record_count") != pair.dense_bound.vector_count:
        raise A0XA0AnalysisError("activation record count differs from frozen A0 dense bound")


def _target_metadata(rows: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[int], list[str], list[str]]:
    if len(rows) != 48:
        raise A0XA0AnalysisError("analysis requires exactly 48 selected target rows")
    ids: list[str] = []; labels: list[int] = []; families: list[str] = []; domains: list[str] = []
    for row in rows:
        case_id = row.get("case_id"); family = row.get("problem_family_id"); domain = row.get("domain")
        proxy = row.get("operator_proxy_family")
        if not all(isinstance(value, str) and value for value in (case_id, family, domain)):
            raise A0XA0AnalysisError("target rows have incomplete public identity")
        if proxy not in {"segmentation_like", "inversion_like"}:
            raise A0XA0AnalysisError("target rows have an unsupported frozen proxy family")
        ids.append(case_id); families.append(family); domains.append(domain); labels.append(1 if proxy == "segmentation_like" else 0)
    if len(set(ids)) != 48 or len(set(families)) != 24 or len(set(domains)) != 6:
        raise A0XA0AnalysisError("target rows violate frozen A0 case/family/domain cardinality")
    _family_successes([float(label) for label in labels], labels, families)
    return ids, labels, families, domains


def _materialize_combos(index_bytes: bytes, dense_bytes: bytes, case_ids: Sequence[str], pair: PairBinding, receipt: Mapping[str, Any]) -> tuple[dict[tuple[str, int, str], list[list[float]]], int]:
    if not isinstance(index_bytes, bytes) or not isinstance(dense_bytes, bytes):
        raise A0XA0AnalysisError("analysis assets must be immutable bytes")
    if receipt.get("dense", {}).get("sha256") != _bytes_sha(dense_bytes) or receipt.get("index", {}).get("sha256") != _bytes_sha(index_bytes):
        raise A0XA0AnalysisError("activation receipt asset hash differs from analysis bytes")
    rows = _parse_index(index_bytes)
    vectors = _parse_safetensors(dense_bytes, pair.dense_bound.hidden_width)
    if len(rows) != 2400 or len(vectors) != 2400:
        raise A0XA0AnalysisError("A0 dense/index assets differ from the frozen 2400-vector bound")
    final = int(receipt["final_block_tuple_index"])
    by_combo: dict[tuple[str, int, str], dict[str, list[float]]] = defaultdict(dict)
    for row in rows:
        try:
            case_id = str(row["case_id"]); view = str(row["view"]); site = str(row["token_site"]); index = int(row["tuple_index"]); key = str(row["tensor_key"])
        except (KeyError, TypeError, ValueError) as error:
            raise A0XA0AnalysisError("representation index record is invalid") from error
        expected_role = "primary" if index in _LITERAL else "descriptive"
        if view not in _VIEWS or site not in _VIEWS[view] or index not in (*_LITERAL, final) or row.get("endpoint_role") != expected_role:
            raise A0XA0AnalysisError("representation index endpoint contract drift")
        raw = vectors.get(key)
        if case_id in by_combo[(view, index, site)] or raw is None:
            raise A0XA0AnalysisError("representation index is duplicate or vector is unavailable")
        if row.get("vector_dim") != pair.dense_bound.hidden_width or row.get("dtype") != "float32" or row.get("vector_sha256") != _bytes_sha(raw):
            raise A0XA0AnalysisError("representation vector identity differs from frozen index")
        vector = list(struct.unpack(f"<{pair.dense_bound.hidden_width}f", raw))
        if not vector or not all(math.isfinite(value) for value in vector):
            raise A0XA0AnalysisError("representation vector is invalid")
        by_combo[(view, index, site)][case_id] = vector
    expected = {(view, index, site) for view, sites in _VIEWS.items() for site in sites for index in (*_LITERAL, final)}
    if set(by_combo) != expected or any(set(values) != set(case_ids) for values in by_combo.values()):
        raise A0XA0AnalysisError("representation index does not cover the frozen A0 grid")
    return {combo: [values[case_id] for case_id in case_ids] for combo, values in by_combo.items()}, final


def _score_operator(matrix: Any, domains: Sequence[str], *, alpha: float) -> Any:
    """Historical L2 dual LODO operator, using NumPy when available."""
    try:
        import numpy as np
    except ModuleNotFoundError:
        return _score_operator_pure(matrix, domains, alpha=alpha)
    matrix = np.asarray(matrix, dtype=np.float64); count = matrix.shape[0]; operator = np.zeros((count, count), dtype=np.float64)
    for held_domain in sorted(set(domains)):
        train = np.asarray([index for index, domain in enumerate(domains) if domain != held_domain]); test = np.asarray([index for index, domain in enumerate(domains) if domain == held_domain])
        if not len(train) or not len(test): raise A0XA0AnalysisError("leave-one-domain-out split is empty")
        mean = matrix[train].mean(axis=0); std = matrix[train].std(axis=0); std[std < 1e-12] = 1.0
        train_x = (matrix[train] - mean) / std; test_x = (matrix[test] - mean) / std; kernel = train_x @ train_x.T
        solved = np.linalg.solve(kernel + alpha * np.eye(len(train)), np.eye(len(train))); operator[np.ix_(test, train)] = test_x @ train_x.T @ solved
    return operator


def _score_operator_pure(matrix: Sequence[Sequence[float]], domains: Sequence[str], *, alpha: float) -> list[list[float]]:
    rows = [[float(item) for item in row] for row in matrix]
    if not rows or any(len(row) != len(rows[0]) for row in rows): raise A0XA0AnalysisError("activation matrix is invalid")
    operator = [[0.0 for _ in rows] for _ in rows]
    for held in sorted(set(domains)):
        train = [i for i, domain in enumerate(domains) if domain != held]; test = [i for i, domain in enumerate(domains) if domain == held]
        if not train or not test: raise A0XA0AnalysisError("leave-one-domain-out split is empty")
        mean = [math.fsum(rows[i][j] for i in train) / len(train) for j in range(len(rows[0]))]
        std = [math.sqrt(math.fsum((rows[i][j] - mean[j]) ** 2 for i in train) / len(train)) or 1.0 for j in range(len(rows[0]))]
        tx = [[(rows[i][j] - mean[j]) / std[j] for j in range(len(mean))] for i in train]; vx = [[(rows[i][j] - mean[j]) / std[j] for j in range(len(mean))] for i in test]
        kernel = [[_dot(left, right) + (alpha if i == j else 0.0) for j, right in enumerate(tx)] for i, left in enumerate(tx)]
        inverse = _inverse(kernel)
        for row_index, values in zip(test, vx, strict=True):
            cross = [_dot(values, train_row) for train_row in tx]
            operator[row_index] = [_dot(cross, [inverse[k][column] for k in range(len(train))]) for column in range(len(train))]
            full = [0.0] * len(rows)
            for column, source in enumerate(train): full[source] = operator[row_index][column]
            operator[row_index] = full
    return operator


def _inverse(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    size = len(matrix); augmented = [[float(value) for value in row] + [1.0 if row_index == column else 0.0 for column in range(size)] for row_index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-15: raise A0XA0AnalysisError("L2 solve is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]; divisor = augmented[column][column]; augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row != column:
                factor = augmented[row][column]; augmented[row] = [value - factor * pivot_value for value, pivot_value in zip(augmented[row], augmented[column], strict=True)]
    return [row[size:] for row in augmented]


def _dot(left: Sequence[float], right: Sequence[float]) -> float: return math.fsum(a * b for a, b in zip(left, right, strict=True))
def _apply(operator: Any, labels: Sequence[int]) -> list[float]:
    signed = [1.0 if value == 1 else -1.0 for value in labels]
    return [float(math.fsum(float(value) * signed[index] for index, value in enumerate(row))) for row in operator]
def _macro_f1(labels: Sequence[int], predictions: Sequence[int]) -> float:
    values=[]
    for label in (0, 1):
        tp=sum(y==label and p==label for y,p in zip(labels,predictions,strict=True)); fp=sum(y!=label and p==label for y,p in zip(labels,predictions,strict=True)); fn=sum(y==label and p!=label for y,p in zip(labels,predictions,strict=True)); values.append(0.0 if 2*tp+fp+fn==0 else 2*tp/(2*tp+fp+fn))
    return math.fsum(values)/2
def _wilson(successes: int, total: int) -> list[float]:
    z=1.959963984540054; p=successes/total; den=1+z*z/total; center=(p+z*z/(2*total))/den; radius=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den; return [max(0.0,center-radius),min(1.0,center+radius)]
def _family_successes(scores: Sequence[float], labels: Sequence[int], families: Sequence[str]) -> tuple[int, dict[str,bool]]:
    members: dict[str,list[int]]=defaultdict(list)
    for index,family in enumerate(families): members[family].append(index)
    outcomes={}
    for family,indices in sorted(members.items()):
        if len(indices)!=2 or sorted(labels[index] for index in indices)!=[0,1]: raise A0XA0AnalysisError(f"family {family} is not a balanced pair")
        positive=next(index for index in indices if labels[index]==1); negative=next(index for index in indices if labels[index]==0); outcomes[family]=float(scores[positive])>float(scores[negative])
    return sum(outcomes.values()),outcomes
def _combo_metrics(operator: Any, labels: Sequence[int], families: Sequence[str], domains: Sequence[str]) -> dict[str,Any]:
    scores=_apply(operator,labels); predictions=[int(value>=0.0) for value in scores]; successes,outcomes=_family_successes(scores,labels,families); per_domain={domain:sum(predictions[index]==labels[index] for index,value in enumerate(domains) if value==domain)/sum(value==domain for value in domains) for domain in sorted(set(domains))}
    return {"family_successes":successes,"family_success_rate":successes/len(outcomes),"family_success_wilson_95":_wilson(successes,len(outcomes)),"macro_f1":_macro_f1(labels,predictions),"accuracy":sum(p==y for p,y in zip(predictions,labels,strict=True))/len(labels),"per_domain_accuracy":per_domain}
def _null_maxima(operators: Mapping[tuple[str,int,str],Any], combos: Sequence[tuple[str,int,str]], labels: Sequence[int], families: Sequence[str], *, seed:int,budget:int)->list[int]:
    members=defaultdict(list)
    for index,family in enumerate(families): members[family].append(index)
    ordered=[members[family] for family in sorted(members)]; rng=random.Random(seed); seen=set(); output=[]
    while len(output)<budget:
        mask=rng.getrandbits(len(ordered))
        if mask in seen: continue
        seen.add(mask); permuted=list(labels)
        for bit,indices in enumerate(ordered):
            if mask&(1<<bit): permuted[indices[0]],permuted[indices[1]]=permuted[indices[1]],permuted[indices[0]]
        output.append(max(_family_successes(_apply(operators[combo],permuted),permuted,families)[0] for combo in combos))
    return output
def _mapping(value: Mapping[str,Any], key:str)->Mapping[str,Any]:
    nested=value.get(key)
    if not isinstance(nested,Mapping): raise A0XA0AnalysisError(f"{key} is missing")
    return nested
def _combo_name(index:int,site:str)->str: return f"tuple-{index}::{site}"
def _sha(value: Any)->str: return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
def _bytes_sha(value: bytes)->str: return hashlib.sha256(value).hexdigest()
def _parse_registered_receipt(payload: bytes, schema_name: str, *, require_trailing_newline: bool) -> Mapping[str, Any]:
    """Parse the exact persisted UTF-8 JSON receipt bytes, never a rebuilt object."""
    if not isinstance(payload, bytes) or (require_trailing_newline and not payload.endswith(b"\n")):
        raise A0XA0AnalysisError("persisted receipt bytes must be UTF-8 JSON ending in one LF")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XA0AnalysisError("persisted receipt bytes are not valid UTF-8 JSON") from error
    if not isinstance(value, Mapping):
        raise A0XA0AnalysisError("persisted receipt must be a JSON object")
    from .a0x_execution import _validate_artifact
    try:
        _validate_artifact(schema_name, value)
    except Exception as error:
        raise A0XA0AnalysisError("persisted receipt fails its strict registered schema") from error
    return value
def _parse_index(payload: bytes)->list[Mapping[str, Any]]:
    try: rows=[json.loads(line) for line in payload.decode("utf-8").splitlines() if line]
    except (UnicodeDecodeError,json.JSONDecodeError) as error: raise A0XA0AnalysisError("representation index bytes are invalid") from error
    if any(not isinstance(row,Mapping) for row in rows): raise A0XA0AnalysisError("representation index rows are invalid")
    return rows
def _parse_safetensors(payload: bytes, width: int)->dict[str, bytes]:
    if len(payload)<8: raise A0XA0AnalysisError("dense asset is not a safetensors payload")
    header_size=int.from_bytes(payload[:8],"little")
    try: header=json.loads(payload[8:8+header_size]); data=payload[8+header_size:]
    except (UnicodeDecodeError,json.JSONDecodeError) as error: raise A0XA0AnalysisError("dense safetensors header is invalid") from error
    if not isinstance(header,Mapping): raise A0XA0AnalysisError("dense safetensors header is invalid")
    vectors={}; expected=0
    for key, value in sorted(header.items()):
        if not isinstance(key,str) or not isinstance(value,Mapping) or value.get("dtype")!="F32" or value.get("shape")!=[width]: raise A0XA0AnalysisError("dense safetensors tensor contract drift")
        offsets=value.get("data_offsets")
        if not isinstance(offsets,list) or len(offsets)!=2 or offsets[0]!=expected or offsets[1]-offsets[0]!=width*4: raise A0XA0AnalysisError("dense safetensors offsets are invalid")
        start,end=offsets; vectors[key]=data[start:end]; expected=end
    if expected!=len(data): raise A0XA0AnalysisError("dense safetensors data has an extra or missing byte")
    return vectors


__all__ = ["A0XA0AnalysisError", "analyze_a0x_a0"]
