"""Automated surface-shortcut audit for A0 calibration corpus.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import hashlib
import math
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Mapping


__all__ = ["audit_a0_shortcuts"]


_WORD_RE = re.compile(r"[a-z0-9]+")
_CONTROL_NAME = tuple[str, ...]
_WHITESPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")
_LOWER_RE = re.compile(r"[a-z0-9]")

_DEFAULT_A0_CONTROLS = (
    "bag_of_words_baselines",
    "character_ngram_baselines",
    "length_and_punctuation_baselines",
    "style_and_template_baselines",
    "provenance_classifiers",
    "problem_only_label_prediction",
    "leave_one_domain_out_surface_evaluation",
    "duplicate_and_near_duplicate_detection",
    "family_leakage_detection",
    "random_label_controls",
    "random_partition_controls",
    "generic_action_taxonomy_controls",
    "generic_transformation_taxonomy_controls",
    "adjacent_principle_proxy_controls",
)

_METRIC_DECIMAL_PLACES = 14


def audit_a0_shortcuts(
    cases_path: str | Path,
    targets_path: str | Path,
    protocol_path: str | Path,
    *,
    method_selection: Mapping[str, Any] | None = None,
    mechanical_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run deterministic shortcut controls on calibration-only A0 split.

    Parameters
    ----------
    cases_path:
        Path to ``cases.jsonl`` (label-free problem surfaces).
    targets_path:
        Path to ``procedural-targets/calibration-targets.jsonl``. Sealed
        targets are physically separate and must never be passed here.
    protocol_path:
        Path to the protocol JSON containing shortcut thresholds and control list.
    """

    _validate_prospective_selection(method_selection, mechanical_evidence)
    if method_selection is not None:
        return _audit_prospective_shortcuts(
            cases_path, targets_path, protocol_path, mechanical_evidence
        )

    protocol = _load_protocol(protocol_path)
    controls_required = tuple(protocol.get("shortcut_evaluation", {}).get("a0_controls", _DEFAULT_A0_CONTROLS))
    threshold = _coerce_float(
        protocol.get("shortcut_evaluation", {}).get("macro_f1_threshold"), 0.65
    )
    margin_over_majority = _coerce_float(
        protocol.get("shortcut_evaluation", {}).get("margin_over_majority"), 0.10
    )

    case_records = _read_jsonl(cases_path)
    target_records = _read_jsonl(targets_path)
    joined, integrity_issues = _join_and_validate(case_records, target_records)
    cal_records = [row for row in joined if row.get("split") == "calibration"]
    sealed_count = len([row for row in joined if row.get("split") == "sealed"])

    control_results: dict[str, Any] = {}
    for name in controls_required:
        control_results[name] = {"status": "not_evaluable", "reason": "unknown control"}

    if integrity_issues:
        for issue in integrity_issues:
            control_results["integrity"] = {
                "status": "failed",
                "issues": integrity_issues,
            }
        control_results["overall"] = {
            "status": "failed",
            "non_interpretable": False,
            "missing_required_controls": [],
            "integrity_issues": integrity_issues,
        }

        return _build_report(
            protocol=protocol,
            controls=control_results,
            counts={"families": len({row["problem_family_id"] for row in joined}), "total_cases": len(joined), "calibration_cases": len(cal_records), "sealed_cases": sealed_count},
            integrity_status="failed",
            protocol_threshold=threshold,
            protocol_margin=margin_over_majority,
        )

    controls_data = _run_controls(cal_records, threshold, margin_over_majority)
    for name, payload in controls_data.items():
        if name in control_results:
            control_results[name] = payload

    # Keep deterministic explicit controls in report even if protocol does not list them.
    for missing in {
        "generic_action_taxonomy_controls",
        "generic_transformation_taxonomy_controls",
        "adjacent_principle_proxy_controls",
    } - set(controls_required):
        control_results[missing] = controls_data[missing]

    missing_required_controls = [
        item
        for item in controls_required
        if item
        not in {"random_label_controls", "random_partition_controls"}
        and control_results.get(item, {}).get("status") == "not_evaluable"
    ]
    integrity_status = "failed" if missing_required_controls else "pass"
    if missing_required_controls:
        control_results["missing_controls"] = {
            "status": "failed",
            "controls": missing_required_controls,
        }

    real_controls = {
        key: value
        for key, value in control_results.items()
        if key not in {"random_label_controls", "random_partition_controls", "integrity", "missing_controls"}
    }
    non_interpretable = any(
        value.get("status") == "non_interpretable"
        for value in real_controls.values()
        if isinstance(value, Mapping)
    )

    if integrity_status == "failed" or missing_required_controls:
        overall_status = "failed"
    elif non_interpretable:
        overall_status = "non_interpretable"
    else:
        overall_status = "pass"

    control_results["overall"] = {
        "status": overall_status,
        "non_interpretable": bool(non_interpretable),
        "missing_required_controls": list(missing_required_controls),
    }
    control_results["integrity"] = {"status": integrity_status, "issues": []}

    return _build_report(
        protocol=protocol,
        controls=control_results,
        counts={"families": len({row["problem_family_id"] for row in cal_records}), "total_cases": len(cal_records), "calibration_cases": len(cal_records), "sealed_cases": 0},
        integrity_status=integrity_status,
        protocol_threshold=threshold,
        protocol_margin=margin_over_majority,
    )


def _load_protocol(protocol_path: str | Path) -> dict[str, Any]:
    path = Path(protocol_path)
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("protocol is not a JSON object")
    return payload


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _join_and_validate(
    case_records: list[dict[str, Any]],
    target_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    joined: list[dict[str, Any]] = []
    case_ids = [str(row.get("case_id", "")) for row in case_records]
    target_ids = [str(row.get("case_id", "")) for row in target_records]
    if len(case_ids) != len(set(case_ids)):
        issues.append({"code": "duplicate_case_id"})
    if len(target_ids) != len(set(target_ids)):
        issues.append({"code": "duplicate_target_case_id"})

    family_splits: dict[str, set[str]] = defaultdict(set)
    for case in case_records:
        family_splits[str(case.get("problem_family_id", ""))].add(str(case.get("split", "")))
    for family_id, splits in family_splits.items():
        if len(splits) != 1:
            issues.append({"code": "split_crosses_family", "family_id": family_id})

    calibration_cases = [row for row in case_records if row.get("split") == "calibration"]
    by_case = {str(row.get("case_id", "")): row for row in calibration_cases}
    target_by_case: dict[str, dict[str, Any]] = {}
    for target in target_records:
        case_id = str(target.get("case_id", ""))
        if target.get("split") != "calibration":
            issues.append({"code": "non_calibration_target_supplied", "case_id": case_id})
            continue
        target_by_case[case_id] = target

    for case_id, case in by_case.items():
        if case_id not in target_by_case:
            issues.append({"code": "missing_target", "case_id": case_id})
            continue
        target = target_by_case[case_id]
        family = str(case.get("problem_family_id", "")).strip()
        split = str(case.get("split", "")).strip()
        domain = str(case.get("domain", "")).strip() or "unknown"
        if not family:
            issues.append({"code": "missing_family", "case_id": case_id})
            continue
        if split != "calibration":
            issues.append({"code": "invalid_split", "case_id": case_id, "split": split})
            continue

        operator_family = str(target.get("operator_proxy_family", "")).strip()
        row = {
            "case_id": case_id,
            "problem_family_id": family,
            "solution_variant_id": str(case.get("solution_variant_id", "")).strip(),
            "domain": domain,
            "split": split,
            "problem": str(case.get("problem", "")),
            "constraints": _coerce_list(case.get("constraints", [])),
            "initial_state": str(case.get("initial_state", "")),
            "desired_improvement": str(case.get("desired_improvement", "")),
            "worsening_consequence": str(case.get("worsening_consequence", "")),
            "transformation": str(case.get("transformation", "")),
            "resulting_state": str(case.get("resulting_state", "")),
            "solution": str(case.get("solution", "")),
            "label": operator_family,
            "template_id": _coerce_text(
                target.get("provenance", {}).get("template_id")
                if isinstance(target.get("provenance"), Mapping)
                else None
            ),
            "generator_id": _coerce_text(
                target.get("provenance", {}).get("generator_id")
                if isinstance(target.get("provenance"), Mapping)
                else None
            ),
        }
        if not row["label"]:
            issues.append({"code": "missing_label", "case_id": case_id})
            continue
        if row["template_id"] in {"", "unknown"}:
            issues.append({"code": "missing_template", "case_id": case_id})
        if row["generator_id"] in {"", "unknown"}:
            issues.append({"code": "missing_generator", "case_id": case_id})
        joined.append(row)

    family_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in joined:
        family_map[row["problem_family_id"]].append(row)

    for family_id, rows in family_map.items():
        if not rows:
            issues.append({"code": "empty_family", "family_id": family_id})
            continue
        labels = sorted({row["label"] for row in rows})
        if labels != ["inversion_like", "segmentation_like"]:
            issues.append(
                {
                    "code": "non_opposite_labels_in_family",
                    "family_id": family_id,
                    "labels": ",".join(labels),
                }
            )
        if len({row.get("domain", "") for row in rows}) != 1:
            issues.append({"code": "domain_mismatch_in_family", "family_id": family_id})
    seen: dict[str, tuple[str, str]] = {}
    for row in joined:
        normalized = _normalize_text(_join_all_fields(row))
        key = normalized
        if key in seen and seen[key] != (row["problem_family_id"], row["split"]):
            issues.append(
                {
                    "code": "cross_family_duplicate",
                    "problem_family_id": row["problem_family_id"],
                    "other_family_id": seen[key][0],
                    "split": row["split"],
                }
            )
        seen[key] = (row["problem_family_id"], row["split"])

    return joined, issues


def _coerce_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if value else ""


def _coerce_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _coerce_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float(default)
    return parsed


def _join_all_fields(row: Mapping[str, Any]) -> str:
    chunks = [
        str(row.get("problem", "")),
        str(row.get("initial_state", "")),
        str(row.get("desired_improvement", "")),
        str(row.get("worsening_consequence", "")),
        str(row.get("transformation", "")),
        str(row.get("resulting_state", "")),
        str(row.get("solution", "")),
        " ".join(_coerce_list(row.get("constraints", []))),
    ]
    return " ".join(part.strip() for part in chunks if str(part).strip())


def _normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _tokenize(value: str) -> list[str]:
    return _WORD_RE.findall(_normalize_text(value))


def _char_ngrams(value: str, min_n: int = 3, max_n: int = 5) -> list[str]:
    text = _normalize_text(value)
    if len(text) < min_n:
        return []
    grams: list[str] = []
    for n in range(min_n, max_n + 1):
        if len(text) < n:
            continue
        for index in range(len(text) - n + 1):
            grams.append(text[index : index + n])
    return grams


def _length_features(value: str) -> tuple[float, float, float, float]:
    text = value
    chars = len(text)
    digits = sum(1 for ch in text if ch.isdigit())
    punct = sum(1 for ch in text if (not ch.isalnum() and not ch.isspace()))
    words = len(_tokenize(text)) or 1
    return (
        float(chars),
        float(chars / max(words, 1)),
        float(punct / max(chars, 1)),
        float(digits / max(chars, 1)),
    )


def _row_text(row: Mapping[str, Any], *, view: str) -> str:
    if view == "problem_only":
        return str(row.get("problem", ""))
    return _join_all_fields(row)


def _build_feature(row: Mapping[str, Any], view: str) -> Any:
    text = _row_text(row, view=view)
    if view == "word_unigrams":
        return Counter(_tokenize(text))
    if view == "char_3_5_grams":
        return Counter(_char_ngrams(text))
    if view == "length_and_punctuation_baselines":
        return _length_features(text)
    if view == "template_provenance_categorical":
        return {
            "template_id": str(row.get("template_id", "")),
            "generator_id": str(row.get("generator_id", "")),
            "domain": str(row.get("domain", "")),
        }
    if view == "problem_only":
        return Counter(_tokenize(str(row.get("problem", ""))))
    if view == "generic_action_taxonomy_controls":
        return _keyword_features(str(row.get("transformation", "")), _ACTION_LEXICON)
    if view == "generic_transformation_taxonomy_controls":
        return _keyword_features(str(row.get("solution", "")), _TRANSFORMATION_LEXICON)
    if view == "adjacent_principle_proxy_controls":
        return _keyword_features(_join_all_fields(row), _ADJACENT_LEXICON)
    return _join_all_fields(row)


def _keyword_features(text: str, vocab: dict[str, list[str]]) -> dict[str, int]:
    tokens = Counter(_tokenize(text))
    return {
        label: sum(tokens[token] for token in keywords)
        for label, keywords in vocab.items()
    }


_ACTION_LEXICON = {
    "segmentation_like": [
        "divide",
        "segment",
        "partition",
        "split",
        "components",
        "decompose",
        "local",
        "distributed",
    ],
    "inversion_like": [
        "reverse",
        "invert",
        "swap",
        "exchange",
        "opposite",
        "central",
        "controller",
    ],
}

_TRANSFORMATION_LEXICON = {
    "segmentation_like": ["local", "stage", "system", "subsystem", "component", "parallel"],
    "inversion_like": ["system", "before", "after", "overall", "single", "global", "endpoint"],
}

_ADJACENT_LEXICON = {
    "segmentation_like": ["adjacent", "neighbor", "around", "near", "side", "proximity"],
    "inversion_like": ["far", "away", "isolate", "distance", "separate", "apart"],
}


def _evaluate_textual_control(
    rows: list[dict[str, Any]],
    view: str,
    threshold: float,
    margin: float,
) -> dict[str, Any]:
    if len(rows) < 4:
        return {"status": "not_evaluable", "aggregate": _empty_metrics(), "threshold": threshold, "margin": margin}

    labels = sorted({row["label"] for row in rows})
    folds = _leave_one_domain_out_folds(rows)
    if not folds:
        return {"status": "fail", "aggregate": _empty_metrics(), "reason": "no folds"}

    fold_metrics = []
    for domain, train, test in folds:
        if len(set(row["label"] for row in test)) < 2:
            continue
        train_features = [_build_feature(row, view=view) for row in train]
        test_features = [_build_feature(row, view=view) for row in test]
        y_true = [row["label"] for row in test]
        y_pred, train_labels = _nearest_centroid_predict(
            train_features,
            [row["label"] for row in train],
            test_features,
            labels,
        )
        metrics = _classification_metrics(y_true, y_pred, labels)
        majority = _majority_baseline_pred(train_labels, y_true)
        majority_metrics = _classification_metrics(y_true, majority, labels)
        margin_value = metrics["macro_f1"] - majority_metrics["macro_f1"]
        fold_metrics.append(
            {
                "domain": domain,
                "metrics": dict(metrics),
                "majority_metrics": dict(majority_metrics),
                "margin_over_majority": margin_value,
                "train_count": len(train),
                "test_count": len(test),
            }
        )
    if not fold_metrics:
        return {"status": "fail", "aggregate": _empty_metrics(), "reason": "insufficient support"}
    aggregate = _aggregate_folds(fold_metrics)
    margin = min(item["margin_over_majority"] for item in fold_metrics)
    status = (
        "non_interpretable"
        if (aggregate["macro_f1"] >= threshold and margin >= margin)
        else "pass"
    )
    return {
        "status": status,
        "aggregate": aggregate,
        "folds": fold_metrics,
        "threshold": threshold,
        "margin_over_majority": margin,
        "min_margin_over_majority": margin,
    }


def _evaluate_random_partition(
    rows: list[dict[str, Any]],
    controls: list[str],
    threshold: float,
    margin: float,
) -> dict[str, Any]:
    if len(rows) < 6:
        return {"status": "not_evaluable", "aggregate": _empty_metrics(), "seed": 0}

    labels = sorted({row["label"] for row in rows})
    if len(labels) < 2:
        return {"status": "fail", "aggregate": _empty_metrics(), "seed": 0}

    rng = random.Random(20260814)
    runs = []
    for index, control in enumerate(controls):
        order = list(rows)
        rng.shuffle(order)
        fold_size = max(1, len(order) // 5)
        diagnostics = []
        macro_f1_values: list[float] = []
        for fold_index in range(5):
            start = fold_index * fold_size
            end = len(order) if fold_index == 4 else (fold_index + 1) * fold_size
            test = order[start:end]
            if not test:
                continue
            test_ids = {row["case_id"] for row in test}
            train = [row for row in rows if row["case_id"] not in test_ids]
            y_true = [row["label"] for row in test]
            if len(set(y_true)) < 2:
                continue
            y_pred, _ = _nearest_centroid_predict(
                [_build_feature(row, view=control) for row in train],
                [row["label"] for row in train],
                [_build_feature(row, view=control) for row in test],
                labels,
            )
            metrics = _classification_metrics(y_true, y_pred, labels)
            macro_f1_values.append(metrics["macro_f1"])
            diagnostics.append(
                {
                    "fold": fold_index,
                    "metrics": dict(metrics),
                    "train_count": len(train),
                    "test_count": len(test),
                }
            )
        aggregate = _aggregate_metric_values(macro_f1_values)
        runs.append(
            {
                "control": control,
                "folds": diagnostics,
                "aggregate": aggregate,
            }
        )
    if runs:
        aggregate_macro = {
            "macro_f1": sum(run["aggregate"].get("macro_f1", 0.0) for run in runs) / len(runs),
            "accuracy": 0.0,
            "balanced_accuracy": 0.0,
        }
    else:
        aggregate_macro = _empty_metrics()
    status = (
        "non_interpretable"
        if aggregate_macro["macro_f1"] >= threshold
        and aggregate_macro["macro_f1"] - aggregate_macro.get("macro_f1_majority", 0.0) >= margin
        else "pass"
    )
    return {
        "status": status,
        "seed": 20260814,
        "runs": runs,
        "aggregate": aggregate_macro,
        "threshold": threshold,
        "margin_over_majority": margin,
    }


def _run_controls(
    rows: list[dict[str, Any]],
    threshold: float,
    margin: float,
) -> dict[str, dict[str, Any]]:
    controls = {
        "bag_of_words_baselines": _evaluate_textual_control(rows, "word_unigrams", threshold, margin),
        "character_ngram_baselines": _evaluate_textual_control(rows, "char_3_5_grams", threshold, margin),
        "length_and_punctuation_baselines": _evaluate_textual_control(
            rows, "length_and_punctuation_baselines", threshold, margin
        ),
        "style_and_template_baselines": _evaluate_textual_control(
            rows, "template_provenance_categorical", threshold, margin
        ),
        "provenance_classifiers": _evaluate_textual_control(
            rows, "template_provenance_categorical", threshold, margin
        ),
        "problem_only_label_prediction": _evaluate_textual_control(
            rows, "problem_only", threshold, margin
        ),
        "leave_one_domain_out_surface_evaluation": _evaluate_textual_control(
            rows, "word_unigrams", threshold, margin
        ),
        "duplicate_and_near_duplicate_detection": {
            "status": "pass",
            "reason": "no exact normalized duplicates across families/splits in calibration",
        },
        "family_leakage_detection": {
            "status": "pass",
            "families_checked": len({row["problem_family_id"] for row in rows}),
            "note": "all families hold one split and two opposite labels",
        },
        "random_label_controls": _evaluate_random_label(rows, threshold, margin),
        "random_partition_controls": _evaluate_random_partition(
            rows,
            ["word_unigrams", "problem_only", "template_provenance_categorical"],
            threshold,
            margin,
        ),
        "generic_action_taxonomy_controls": _evaluate_lexicon_controls(
            rows, "generic_action_taxonomy_controls", _ACTION_LEXICON, threshold, margin
        ),
        "generic_transformation_taxonomy_controls": _evaluate_lexicon_controls(
            rows,
            "generic_transformation_taxonomy_controls",
            _TRANSFORMATION_LEXICON,
            threshold,
            margin,
        ),
        "adjacent_principle_proxy_controls": _evaluate_lexicon_controls(
            rows,
            "adjacent_principle_proxy_controls",
            _ADJACENT_LEXICON,
            threshold,
            margin,
        ),
    }
    return controls


def _evaluate_random_label(
    rows: list[dict[str, Any]],
    threshold: float,
    margin: float,
) -> dict[str, Any]:
    if len(rows) < 6:
        return {"status": "not_evaluable", "macro_f1": 0.0, "seed": 0}
    labels = sorted({row["label"] for row in rows})
    if len(labels) < 2:
        return {"status": "fail", "seed": 20260814, "macro_f1": 0.0}

    base_rows = list(rows)
    true_labels = [row["label"] for row in base_rows]
    majorities = []
    macro_values = []
    rng = random.Random(20260814)

    for _ in range(30):
        permuted = list(base_rows)
        perm_labels = true_labels.copy()
        rng.shuffle(perm_labels)
        for row, label in zip(permuted, perm_labels):
            row["random_label"] = label
        folds = _leave_one_domain_out_folds(permuted)
        if not folds:
            continue
        fold_metrics = []
        for _domain, train, test in folds:
            train_labels = [row["random_label"] for row in train]
            if len(set(train_labels)) < 2 or len(set(row["label"] for row in test)) < 2:
                continue
            y_pred, _ = _nearest_centroid_predict(
                [_build_feature(row, view="word_unigrams") for row in train],
                train_labels,
                [_build_feature(row, view="word_unigrams") for row in test],
                labels,
            )
            metrics = _classification_metrics(
                [row["label"] for row in test],
                y_pred,
                labels,
            )
            majorities.append(
                _classification_metrics(
                    [row["label"] for row in test],
                    [_majority_label(train_labels)] * len(test),
                    labels,
                )
            )
            fold_metrics.append(metrics)
        if fold_metrics:
            macro_values.append(sum(item["macro_f1"] for item in fold_metrics) / len(fold_metrics))

    aggregate = _aggregate_from_macro(macro_values)
    status = "non_interpretable" if aggregate["macro_f1"] >= threshold else "pass"
    return {
        "status": status,
        "seed": 20260814,
        "permutations": 30,
        "aggregate": aggregate,
        "majority_macrof1": sum(item["macro_f1"] for item in majorities) / len(majorities) if majorities else 0.0,
        "threshold": threshold,
        "margin_over_majority": margin,
    }


def _evaluate_lexicon_controls(
    rows: list[dict[str, Any]],
    name: str,
    lexicon: dict[str, list[str]],
    threshold: float,
    margin: float,
) -> dict[str, Any]:
    if not rows:
        return {"name": name, "status": "not_evaluable", "aggregate": _empty_metrics()}

    if "action" in name or "transformation" in name:
        if name == "generic_action_taxonomy_controls":
            view = "generic_action_taxonomy_controls"
        elif name == "generic_transformation_taxonomy_controls":
            view = "generic_transformation_taxonomy_controls"
        else:
            view = "adjacent_principle_proxy_controls"
    else:
        view = "adjacent_principle_proxy_controls"

    labels = sorted({row["label"] for row in rows})
    folds = _leave_one_domain_out_folds(rows)
    fold_metrics = []
    for _domain, train, test in folds:
        if len(set(row["label"] for row in test)) < 2:
            continue
        y_pred: list[str] = []
        for row in test:
            counts = _keyword_features(_join_all_fields(row) if view != "problem_only" else str(row.get("problem", "")), lexicon)
            pred = max(counts, key=counts.get, default="")
            y_pred.append(pred or _majority_label([r["label"] for r in train] if train else labels))
        metrics = _classification_metrics([row["label"] for row in test], y_pred, labels)
        y_true = [row["label"] for row in test]
        majority = _majority_baseline_pred([row["label"] for row in train], y_true)
        majority_metrics = _classification_metrics(y_true, majority, labels)
        fold_metrics.append(
            {
                "metrics": dict(metrics),
                "majority_metrics": dict(majority_metrics),
                "margin_over_majority": metrics["macro_f1"] - majority_metrics["macro_f1"],
            }
        )
    if not fold_metrics:
        return {"name": name, "status": "not_evaluable", "aggregate": _empty_metrics()}
    aggregate = _aggregate_folds(fold_metrics)
    min_margin = min(fold["margin_over_majority"] for fold in fold_metrics)
    status = (
        "non_interpretable"
        if aggregate["macro_f1"] >= threshold and min_margin >= margin
        else "pass"
    )
    return {
        "name": name,
        "status": status,
        "aggregate": aggregate,
        "folds": fold_metrics,
        "threshold": threshold,
        "margin_over_majority": margin,
        "min_margin_over_majority": min_margin,
    }


def _leave_one_domain_out_folds(rows: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]]:
    by_domain: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_domain[str(row.get("domain", "unknown"))].append(row)
    folds = []
    domains = sorted(by_domain)
    for domain in domains:
        test = by_domain[domain]
        train = [row for key, records in by_domain.items() if key != domain for row in records]
        if train and test:
            folds.append((domain, train, test))
    return folds


def _nearest_centroid_predict(
    train_features: list[Any],
    train_labels: list[str],
    test_features: list[Any],
    labels: list[str],
) -> tuple[list[str], list[str]]:
    if not train_features or not labels:
        return [], train_labels
    majority = _majority_label(train_labels)
    centroids = {}
    for label in labels:
        vectors = [feature for feature, lab in zip(train_features, train_labels) if lab == label]
        if not vectors:
            continue
        centroids[label] = _centroid(vectors)
    if len(centroids) < len(labels):
        return [majority] * len(test_features), labels

    predictions: list[str] = []
    for feature in test_features:
        distances = {
            label: _vector_distance(feature, centroid)
            for label, centroid in centroids.items()
        }
        if not distances:
            predictions.append(majority)
            continue
        best_label = min(distances.items(), key=lambda item: (item[1], item[0]))[0]
        predictions.append(best_label)
    return predictions, labels


def _centroid(vectors: list[Any]) -> Any:
    if not vectors:
        return {}
    first = vectors[0]
    if isinstance(first, Counter):
        counter = Counter()
        for vector in vectors:
            counter.update(vector)
        return {key: value / len(vectors) for key, value in counter.items()}
    if isinstance(first, dict):
        if all(isinstance(value, (int, float)) for value in first.values()):
            sums = Counter()
            for vector in vectors:
                sums.update(vector)
            return {key: value / len(vectors) for key, value in sums.items()}
        sums = Counter()
        for vector in vectors:
            if not isinstance(vector, Mapping):
                continue
            for key, value in vector.items():
                sums[f"{key}::{value}"] += 1
        return {key: value / len(vectors) for key, value in sums.items()}
    values = [tuple(float(v) for v in vector) for vector in vectors]
    dim = len(values[0])
    means = []
    for index in range(dim):
        means.append(sum(vec[index] for vec in values) / len(values))
    return tuple(means)


def _vector_distance(first: Any, second: Any) -> float:
    if isinstance(first, Mapping) and isinstance(second, Mapping):
        first_has_text = any(isinstance(value, str) for value in first.values())
        second_has_text = any(isinstance(value, str) for value in second.values())
        if first_has_text and not second_has_text:
            first = _encode_categorical_mapping(first)
        elif second_has_text and not first_has_text:
            second = _encode_categorical_mapping(second)
        return math.sqrt(
            sum((float(first.get(key, 0.0)) - float(second.get(key, 0.0))) ** 2
            for key in set(first) | set(second)
        ))
    if isinstance(first, tuple) and isinstance(second, tuple):
        dim = max(len(first), len(second))
        padded_a = tuple(float(first[i]) if i < len(first) else 0.0 for i in range(dim))
        padded_b = tuple(float(second[i]) if i < len(second) else 0.0 for i in range(dim))
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(padded_a, padded_b)))
    if isinstance(first, Counter) and isinstance(second, Mapping):
        return _vector_distance(dict(first), second)
    return 0.0


def _encode_categorical_mapping(row: Mapping[str, Any]) -> dict[str, float]:
    encoded: dict[str, float] = {}
    for key, value in row.items():
        encoded[f"{key}::{value}"] = 1.0
    return encoded


def _majority_label(labels: list[str]) -> str:
    if not labels:
        return "segmentation_like"
    counts = Counter(labels)
    max_count = max(counts.values())
    candidates = sorted(label for label, count in counts.items() if count == max_count)
    return candidates[0]


def _majority_baseline_pred(train_labels: list[str], test_labels: list[str]) -> list[str]:
    predicted = _majority_label(train_labels)
    return [predicted for _ in test_labels]


def _classification_metrics(y_true: list[str], y_pred: list[str], label_space: list[str]) -> dict[str, float]:
    if not y_true or not label_space:
        return _empty_metrics()
    total = len(y_true)
    accuracy = sum(1 for a, b in zip(y_true, y_pred) if a == b) / float(total)
    labels = sorted(label_space)
    f1_scores: list[float] = []
    recalls: list[float] = []
    for label in labels:
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
        precision = tp / float(tp + fp) if (tp + fp) else 0.0
        recall = tp / float(tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        f1_scores.append(f1)
        recalls.append(recall)
    return {
        "accuracy": accuracy,
        "macro_f1": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
        "balanced_accuracy": sum(recalls) / len(recalls) if recalls else 0.0,
    }


def _empty_metrics() -> dict[str, float]:
    return {"accuracy": 0.0, "macro_f1": 0.0, "balanced_accuracy": 0.0}


def _aggregate_folds(folds: list[Mapping[str, Any]]) -> dict[str, float]:
    if not folds:
        return _empty_metrics()
    return {
        "accuracy": sum(fold["metrics"]["accuracy"] for fold in folds) / len(folds),
        "macro_f1": sum(fold["metrics"]["macro_f1"] for fold in folds) / len(folds),
        "balanced_accuracy": sum(fold["metrics"]["balanced_accuracy"] for fold in folds) / len(folds),
    }


def _aggregate_metric_values(values: list[float]) -> dict[str, float]:
    if not values:
        return {"macro_f1": 0.0, "accuracy": 0.0, "balanced_accuracy": 0.0}
    return {"macro_f1": sum(values) / len(values), "accuracy": 0.0, "balanced_accuracy": 0.0}


def _aggregate_from_macro(values: list[float]) -> dict[str, float]:
    if not values:
        return {"macro_f1": 0.0, "accuracy": 0.0, "balanced_accuracy": 0.0}
    return {"macro_f1": sum(values) / len(values), "accuracy": 0.0, "balanced_accuracy": 0.0}


def _build_report(
    *,
    protocol: Mapping[str, Any],
    controls: dict[str, Any],
    counts: Mapping[str, int],
    integrity_status: str,
    protocol_threshold: float,
    protocol_margin: float,
) -> dict[str, Any]:
    report = {
        "artifact_class": "a0-shortcut-audit",
        "protocol_id": protocol.get("protocol_id", "unknown"),
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": list(protocol.get("claim_ids", [])) if isinstance(protocol.get("claim_ids"), list) else [],
        "status": controls.get("overall", {}).get("status", "failed" if integrity_status == "failed" else "pass"),
        "counts": dict(counts),
        "controls": controls,
        "shortcut_threshold": protocol_threshold,
        "margin_over_majority": protocol_margin,
    }
    return _normalize_metric_floats(report)


def _normalize_metric_floats(value: Any) -> Any:
    """Quantize reported metrics so canonical JSON is stable across runtimes."""

    if isinstance(value, float):
        normalized = round(value, _METRIC_DECIMAL_PLACES)
        return 0.0 if normalized == 0.0 else normalized
    if isinstance(value, list):
        return [_normalize_metric_floats(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_metric_floats(item) for item in value)
    if isinstance(value, Mapping):
        return {key: _normalize_metric_floats(item) for key, item in value.items()}
    return value


# Prospective engineering route. No production schema, schedule or freeze is
# supplied by these helpers. The caller must explicitly bind every supported
# mechanical choice; the historical route above remains opt-out and unchanged.
_V2_SELECTION = {
    "method_id": "a0x-shortcut-calibration-method-v2.0.0",
    "leg": "A0", "model": "HuggingFaceTB/SmolLM2-360M",
    "revision": "f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
}
_V2_PROPOSAL_SHA256 = "be3494238904b64a756425eec464a941ef453bf9745fcc4392bc9666f69ce13c"
_V2_TEXT_FIELDS = {
    "problem", "initial_state", "desired_improvement", "worsening_consequence",
    "transformation", "resulting_state", "solution",
}
_V2_METRIC_CONTROLS = tuple(name for name in _DEFAULT_A0_CONTROLS
    if name not in {"duplicate_and_near_duplicate_detection", "family_leakage_detection"})
_V2_REQUIRED_FIELDS = {
    "schema", "classes", "views", "control_views", "units", "replicas", "randomizer",
    "python_version", "partition_train_families", "partition_assignments", "algorithm",
    "numerics", "tie_break", "payload_stages", "payload_encoding", "normalization",
    "unicode_version", "boundaries",
}
_PRODUCTION_PAYLOAD_FIELDS = {
    "__model_problem_only", "__model_transformation_only",
    "__model_problem_plus_transformation", "__model_problem_plus_solution",
}
_PRODUCTION_EVALUATION_PROFILE = "a0x-shortcut-mechanics-production-evaluation-v1"


def _validate_prospective_selection(selection, evidence):
    """Reject a conflicting opt-in before any path operation; no fallback."""
    if selection is None:
        if evidence is not None:
            raise ValueError("mechanical evidence requires explicit method selection")
        return
    if not isinstance(selection, Mapping) or dict(selection) != _V2_SELECTION:
        raise ValueError("unknown or conflicting prospective method/model/leg/revision")


def _v2_canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _v2_id(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("malformed canonical identity")
    value.encode("utf-8")
    return value


def _v2_names(value):
    if not isinstance(value, list):
        raise ValueError("identity registry must be a list")
    names = [_v2_id(item) for item in value]
    if len(names) != len(set(names)):
        raise ValueError("duplicate canonical identity")
    return names


def _v2_contract(evidence):
    if evidence is None:
        raise LookupError("mechanical evidence absent")
    if not isinstance(evidence, Mapping) or set(evidence) - {"contract", "sha256"}:
        raise ValueError("unknown mechanical envelope")
    if set(evidence) != {"contract", "sha256"}:
        raise LookupError("mechanical envelope incomplete")
    if not isinstance(evidence["contract"], Mapping):
        raise ValueError("contract must be an object")
    raw = _v2_canonical(evidence["contract"])
    digest = hashlib.sha256(raw).hexdigest()
    if digest != evidence["sha256"]:
        raise ValueError("mechanical evidence hash mismatch")
    # Work on the supplied byte-bound snapshot, not a mutable caller alias.
    contract = json.loads(raw)
    production = contract.get("schema") == _PRODUCTION_EVALUATION_PROFILE
    required = _V2_REQUIRED_FIELDS | ({"production_recipe_sha256"} if production else set())
    if set(contract) - required:
        raise ValueError("unknown mechanical contract fields")
    if required - set(contract):
        raise LookupError("required mechanical contract fields absent")
    modes = {
        "schema": _PRODUCTION_EVALUATION_PROFILE if production else "a0x-shortcut-mechanics-engineering-v1",
        "randomizer": "python-mt19937-shuffle-v1", "python_version": sys.version.split()[0],
        "algorithm": "nearest-centroid-squared-euclidean-v1",
        "numerics": "binary64-features-fraction-metrics-v1", "tie_break": "utf8-lexicographic",
        "payload_encoding": "length-prefixed-utf8-v1", "normalization": "utf8-nfc-lf-v1",
        "unicode_version": unicodedata.unidata_version,
    }
    if any(contract[key] != value for key, value in modes.items()):
        raise ValueError("unsupported or mismatched explicit mechanical mode")
    if production:
        recipe = production_mechanics_recipe()
        if contract["production_recipe_sha256"] != hashlib.sha256(_v2_canonical(recipe)).hexdigest():
            raise ValueError("production recipe digest differs")
        for key in ("classes", "views", "control_views", "payload_stages", "boundaries"):
            if contract[key] != recipe[key]:
                raise ValueError("production evaluation differs from its frozen recipe")
        if contract["replicas"] != [{"id": f"replica-{index:02d}", "seed": seed}
                                    for index, seed in enumerate(recipe["replica_seeds"])]:
            raise ValueError("production random replica schedule differs")
    classes = _v2_names(contract["classes"])
    if not classes:
        raise LookupError("canonical classes absent")
    views = contract["views"]
    if not isinstance(views, dict):
        raise ValueError("feature views must be an object")
    if not views:
        raise LookupError("feature views absent")
    for name, view in views.items():
        _v2_id(name)
        if not isinstance(view, dict) or set(view) - {"kind", "fields", "lexicon"}:
            raise ValueError("malformed feature view")
        if not {"kind", "fields"} <= set(view):
            raise LookupError("feature view incomplete")
        kind, fields = view["kind"], _v2_names(view["fields"])
        allowed = {"domain", "template_id", "generator_id"} if kind == "categorical" else _V2_TEXT_FIELDS
        if not fields or not set(fields) <= allowed:
            raise ValueError("unsupported feature field role")
        if kind not in {"word_unigrams", "char_3_5_grams", "length_and_punctuation",
                        "categorical", "keyword_counts"}:
            raise ValueError("unsupported feature representation")
        if kind == "keyword_counts":
            lexicon = view.get("lexicon")
            if not isinstance(lexicon, dict) or set(lexicon) != set(classes):
                raise ValueError("keyword representation does not bind canonical classes")
            for tokens in lexicon.values():
                for token in _v2_names(tokens):
                    if _tokenize(token) != [token]:
                        raise ValueError("keyword must be a canonical single token")
        elif "lexicon" in view:
            raise ValueError("unused lexicon evidence")
    crosswalk = contract["control_views"]
    if not isinstance(crosswalk, dict) or set(crosswalk) - set(_V2_METRIC_CONTROLS):
        raise ValueError("unknown control or applicability exemption")
    if set(_V2_METRIC_CONTROLS) - set(crosswalk):
        raise LookupError("required control views absent")
    kinds = {
        "bag_of_words_baselines": "word_unigrams", "character_ngram_baselines": "char_3_5_grams",
        "length_and_punctuation_baselines": "length_and_punctuation",
        "style_and_template_baselines": "categorical", "provenance_classifiers": "categorical",
        "problem_only_label_prediction": "word_unigrams",
        "generic_action_taxonomy_controls": "keyword_counts",
        "generic_transformation_taxonomy_controls": "keyword_counts",
        "adjacent_principle_proxy_controls": "keyword_counts",
    }
    for control, names in crosswalk.items():
        names = _v2_names(names)
        if not names:
            raise LookupError("empty planned control view registry")
        if not set(names) <= set(views):
            raise ValueError("unknown planned feature view")
        if control in kinds and any(views[name]["kind"] != kinds[control] for name in names):
            raise ValueError("control feature representation conflicts with its declared role")
        if control == "problem_only_label_prediction" and any(views[name]["fields"] != ["problem"] for name in names):
            raise ValueError("problem-only view includes other fields")
    applicable = {name for control, names in crosswalk.items()
                  if not control.startswith("random_") for name in names}
    if set(views) != applicable:
        raise ValueError("unbound or unused feature view")
    for control in ("random_label_controls", "random_partition_controls"):
        if set(crosswalk[control]) != applicable:
            raise ValueError("random control must cover every applicable nonactivation view")
    units = contract["units"]
    if not isinstance(units, list):
        raise ValueError("planned evaluation schedule must be a list")
    if not units:
        raise LookupError("planned evaluation schedule absent")
    unit_ids = []
    domain_folds = []
    for unit in units:
        if not isinstance(unit, dict) or set(unit) != {"id", "fold", "domain", "train_ids", "test_ids"}:
            raise ValueError("invalid planned unit")
        unit_ids.append(_v2_id(unit["id"]))
        domain_folds.append((_v2_id(unit["domain"]), _v2_id(unit["fold"])))
        for side in ("train_ids", "test_ids"):
            if not _v2_names(unit[side]):
                raise LookupError("empty planned training or held-out support")
        if set(unit["train_ids"]) & set(unit["test_ids"]):
            raise ValueError("same case crosses a forbidden evaluation boundary")
    if len(unit_ids) != len(set(unit_ids)) or len(domain_folds) != len(set(domain_folds)):
        raise ValueError("duplicate planned unit/domain-fold")
    replicas = contract["replicas"]
    if not isinstance(replicas, list):
        raise ValueError("random replica schedule must be a list")
    if not replicas:
        raise LookupError("random replica schedule absent")
    replica_ids = []
    for replica in replicas:
        if not isinstance(replica, dict) or set(replica) != {"id", "seed"}:
            raise ValueError("malformed random replica")
        replica_ids.append(_v2_id(replica["id"]))
        if isinstance(replica["seed"], bool) or not isinstance(replica["seed"], int):
            raise ValueError("random seed must be explicitly integral")
    if len(replica_ids) != len(set(replica_ids)):
        raise ValueError("duplicate replica")
    domains = {unit["domain"] for unit in units}
    counts = contract["partition_train_families"]
    assignments = contract["partition_assignments"]
    if not isinstance(counts, dict):
        raise ValueError("partition counts must be an object")
    if set(counts) - domains:
        raise ValueError("unknown partition count domain")
    if set(counts) != domains:
        raise LookupError("partition domain/count schedule incomplete")
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in counts.values()):
        raise ValueError("invalid partition family count")
    if not isinstance(assignments, dict):
        raise ValueError("partition assignments must be an object")
    if set(assignments) - set(replica_ids):
        raise ValueError("unknown partition assignment replica")
    if set(assignments) != set(replica_ids):
        raise LookupError("partition assignments incomplete")
    for domain_assignments in assignments.values():
        if not isinstance(domain_assignments, dict):
            raise ValueError("partition domain assignments must be an object")
        if set(domain_assignments) - domains:
            raise ValueError("unknown partition assignment domain")
        if set(domain_assignments) != domains:
            raise LookupError("partition assignment domains incomplete")
        for assignment in domain_assignments.values():
            if not isinstance(assignment, dict) or set(assignment) != {"train_families", "test_families"}:
                raise ValueError("malformed partition assignment")
            for side in assignment:
                if not _v2_names(assignment[side]):
                    raise LookupError("empty partition assignment support")
            if set(assignment["train_families"]) & set(assignment["test_families"]):
                raise ValueError("declared partition crosses family boundary")
    if contract["boundaries"] != [["train", "test"]]:
        raise ValueError("unsupported or incomplete forbidden boundary map")
    stages = contract["payload_stages"]
    if not isinstance(stages, list):
        raise ValueError("payload stages must be a list")
    if not stages:
        raise LookupError("relevant payload stage scope absent")
    stage_ids = []
    for stage in stages:
        if not isinstance(stage, dict) or set(stage) != {"id", "fields"}:
            raise ValueError("malformed payload stage")
        stage_ids.append(_v2_id(stage["id"]))
        fields = _v2_names(stage["fields"])
        allowed_payload = _PRODUCTION_PAYLOAD_FIELDS if production else _V2_TEXT_FIELDS
        if not fields or not set(fields) <= allowed_payload:
            raise ValueError("payload field roles must be declared input text, not labels/metadata")
    if len(stage_ids) != len(set(stage_ids)):
        raise ValueError("duplicate relevant payload stage")
    return contract, digest


def _v2_sentinel(f1, margin):
    return f1 >= Fraction(13, 20) and margin >= Fraction(1, 10)


def _v2_metric(y_true, y_pred, classes):
    if not y_true or len(y_true) != len(y_pred) or not classes:
        raise LookupError("missing paired prediction support")
    if any(value not in classes for value in [*y_true, *y_pred]):
        raise ValueError("class outside fixed registry")
    values = []
    for label in classes:
        tp = sum(a == label and b == label for a, b in zip(y_true, y_pred))
        fp = sum(a != label and b == label for a, b in zip(y_true, y_pred))
        fn = sum(a == label and b != label for a, b in zip(y_true, y_pred))
        denominator = 2 * tp + fp + fn
        values.append(Fraction(2 * tp, denominator) if denominator else Fraction(0))
    return sum(values, Fraction(0)) / len(classes)


def _v2_majority(labels, classes):
    if not labels:
        raise LookupError("empty training support")
    if any(label not in classes for label in labels):
        raise ValueError("invalid training label")
    counts = Counter(labels)
    return min(counts, key=lambda label: (-counts[label], label.encode("utf-8")))


def _v2_aggregate(units):
    if not units:
        raise LookupError("no planned unit evidence")
    grouped = defaultdict(list)
    for unit in units:
        grouped[unit["domain"]].append(unit)
    domains = {domain: (sum((row["f1"] for row in rows), Fraction(0)) / len(rows),
                        sum((row["f1"] - row["baseline"] for row in rows), Fraction(0)) / len(rows))
               for domain, rows in grouped.items()}
    f1 = sum((pair[0] for pair in domains.values()), Fraction(0)) / len(domains)
    margin = sum((pair[1] for pair in domains.values()), Fraction(0)) / len(domains)
    return f1, margin, domains


def _v2_gate(statuses):
    allowed = {"PASS", "FAIL", "NON_INTERPRETABLE", "UNEVALUABLE"}
    if set(statuses) - set(_DEFAULT_A0_CONTROLS) or any(value not in allowed for value in statuses.values()):
        return "FAIL"
    values = list(statuses.values())
    if set(_DEFAULT_A0_CONTROLS) - set(statuses):
        values.append("UNEVALUABLE")
    return next(status for status in ("FAIL", "NON_INTERPRETABLE", "UNEVALUABLE", "PASS") if status in values)


def _v2_normalize(text):
    if not isinstance(text, str):
        raise ValueError("payload is not UTF-8 text")
    try:
        text.encode("utf-8")
        return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("invalid UTF-8 payload") from exc


def _v2_payload(row, fields):
    components = [_v2_normalize(row[field]) for field in fields]
    return len(components).to_bytes(8, "big") + b"".join(
        len(component).to_bytes(8, "big") + component for component in components)


def _v2_features(row, view):
    if view["kind"] == "categorical":
        return {json.dumps([field, row[field]], ensure_ascii=False): 1.0 for field in view["fields"]}
    text = " ".join(row[field] for field in view["fields"])
    kind = view["kind"]
    if kind == "word_unigrams":
        return dict(Counter(_tokenize(text)))
    if kind == "char_3_5_grams":
        return dict(Counter(_char_ngrams(text)))
    if kind == "length_and_punctuation":
        return dict(zip(("characters", "mean_word_length", "punctuation", "digits"), _length_features(text)))
    tokens = Counter(_tokenize(text))
    return {label: sum(tokens[token] for token in words) for label, words in view["lexicon"].items()}


def _v2_predict(train, test, train_labels, classes, view):
    if not train or not test or len(train_labels) != len(train):
        raise LookupError("empty or unpaired classifier support")
    if any(label not in classes for label in train_labels):
        raise ValueError("invalid classifier class")
    features = [_v2_features(row, view) for row in train]
    centroids = {}
    for label in classes:
        selected = [feature for feature, actual in zip(features, train_labels) if actual == label]
        if selected:
            keys = {key for feature in selected for key in feature}
            centroids[label] = {key: math.fsum(feature.get(key, 0.0) for feature in selected) / len(selected) for key in keys}
    predictions = []
    for row in test:
        feature = _v2_features(row, view)
        distances = {}
        for label, centroid in centroids.items():
            distance = math.fsum((feature.get(key, 0.0) - centroid.get(key, 0.0)) ** 2
                                 for key in sorted(set(feature) | set(centroid)))
            if not math.isfinite(distance):
                raise ValueError("nonfinite classifier evidence")
            distances[label] = distance
        predictions.append(min(distances, key=lambda label: (distances[label], label.encode("utf-8"))))
    return predictions


def _v2_rows(cases, targets, contract):
    if not isinstance(cases, list) or not isinstance(targets, list):
        raise ValueError("case/target records must be lists")
    if not cases or not targets:
        raise LookupError("calibration support absent")
    by_case = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("invalid case record")
        if "case_id" not in case:
            raise LookupError("case identity absent")
        identity = _v2_id(case["case_id"])
        if identity in by_case:
            raise ValueError("duplicate case identity")
        if case.get("split") != "calibration":
            raise ValueError("prospective consumer accepts calibration records only")
        by_case[identity] = case
    by_target = {}
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("invalid target identity")
        if "case_id" not in target:
            raise LookupError("target identity absent")
        identity = _v2_id(target["case_id"])
        if identity in by_target or identity not in by_case or target.get("split") != "calibration":
            raise ValueError("duplicate, unmatched or non-calibration target")
        if "operator_proxy_family" not in target:
            raise LookupError("required target label absent")
        if target["operator_proxy_family"] not in contract["classes"]:
            raise ValueError("target label outside fixed class registry")
        by_target[identity] = target
    if set(by_case) != set(by_target):
        raise LookupError("required paired targets missing")
    fields = {field for view in contract["views"].values() for field in view["fields"]}
    fields.update(field for stage in contract["payload_stages"] for field in stage["fields"])
    rows = {}
    for identity, case in by_case.items():
        target = by_target[identity]
        if not {"domain", "problem_family_id"} <= set(case):
            raise LookupError("domain/family identity absent")
        row = dict(case)
        row["domain"] = _v2_id(case["domain"])
        row["problem_family_id"] = _v2_id(case["problem_family_id"])
        row["label"] = target["operator_proxy_family"]
        provenance = target.get("provenance", {})
        if not isinstance(provenance, dict):
            raise ValueError("invalid categorical provenance object")
        for field in ("template_id", "generator_id"):
            if field in fields:
                if field not in provenance:
                    raise LookupError("mapped categorical field absent")
                row[field] = provenance[field]
        for field in fields:
            if field not in row:
                raise LookupError("mapped input field absent")
            if not isinstance(row[field], str):
                raise ValueError("mapped input field must be text")
            row[field].encode("utf-8")
        rows[identity] = row
    if {row["domain"] for row in rows.values()} != {unit["domain"] for unit in contract["units"]}:
        raise LookupError("planned domain schedule does not cover supplied support")
    for unit in contract["units"]:
        if not set(unit["train_ids"] + unit["test_ids"]) <= set(rows):
            raise LookupError("planned case support absent")
        if any(rows[identity]["domain"] != unit["domain"] for identity in unit["test_ids"]):
            raise ValueError("held-out unit/domain identity mismatch")
        if any(rows[identity]["domain"] == unit["domain"] for identity in unit["train_ids"]):
            raise ValueError("LODO training contains held-out domain")
    return rows


def _v2_integrity(rows, contract, scope_kind="original_lodo", replica=None):
    duplicate_issues, family_issues = [], []
    for unit in contract["units"]:
        train = [rows[identity] for identity in unit["train_ids"]]
        test = [rows[identity] for identity in unit["test_ids"]]
        crossed = {row["problem_family_id"] for row in train} & {row["problem_family_id"] for row in test}
        for family in sorted(crossed):
            family_issues.append({"unit": unit["id"], "family": family,
                                  "scope_kind": scope_kind, "replica": replica})
        for first in train:
            for second in test:
                for first_stage in contract["payload_stages"]:
                    for second_stage in contract["payload_stages"]:
                        # Hashes may index candidates later; actual byte equality is decisive.
                        a = _v2_payload(first, first_stage["fields"])
                        b = _v2_payload(second, second_stage["fields"])
                        if a == b:
                            duplicate_issues.append({"unit": unit["id"], "train_case": first["case_id"],
                                "test_case": second["case_id"], "train_stage": first_stage["id"],
                                "train_family": first["problem_family_id"], "test_family": second["problem_family_id"],
                                "scope_kind": scope_kind, "replica": replica,
                                "test_stage": second_stage["id"], "normalized_sha256": hashlib.sha256(a).hexdigest()})
    return {
        "duplicate_and_near_duplicate_detection": {"status": "FAIL" if duplicate_issues else "PASS",
            "reason": "prohibited exact normalized match" if duplicate_issues else "complete scoped exact comparison",
            "coverage": "exact-normalized-only; no near-duplicate, paraphrase or semantic screening", "issues": duplicate_issues},
        "family_leakage_detection": {"status": "FAIL" if family_issues else "PASS",
            "reason": "family crosses evaluation boundary" if family_issues else "complete scoped family comparison", "issues": family_issues},
    }


def _v2_fraction(value):
    return {"numerator": value.numerator, "denominator": value.denominator, "display": float(value)}


def _v2_evaluate(rows, units, contract, view_name, replica=None, random_labels=False, lodo=False):
    measured, details = [], []
    for unit in units:
        train = [rows[identity] for identity in unit["train_ids"]]
        test = [rows[identity] for identity in unit["test_ids"]]
        original = [row["label"] for row in train]
        labels = list(original)
        if random_labels:
            random.Random(replica["seed"]).shuffle(labels)
        truth = [row["label"] for row in test]
        predicted = _v2_predict(train, test, labels, contract["classes"], contract["views"][view_name])
        majority = _v2_majority(labels, contract["classes"])
        f1 = _v2_metric(truth, predicted, contract["classes"])
        baseline = _v2_metric(truth, [majority] * len(truth), contract["classes"])
        measured.append({"domain": unit["domain"], "f1": f1, "baseline": baseline})
        assignment = {"train_ids": unit["train_ids"], "test_ids": unit["test_ids"], "training_labels": labels}
        details.append({"id": unit["id"], "domain": unit["domain"], "fold": unit["fold"], **assignment,
            "original_training_labels": original, "heldout_labels": truth, "predictions": predicted,
            "majority_label": majority, "f1": _v2_fraction(f1), "baseline": _v2_fraction(baseline),
            "paired_margin": _v2_fraction(f1-baseline),
            "class_support": {label: {"train": labels.count(label), "heldout": truth.count(label)} for label in contract["classes"]},
            "assignment_sha256": hashlib.sha256(_v2_canonical(assignment)).hexdigest(),
            "train_families": sorted({row["problem_family_id"] for row in train}),
            "test_families": sorted({row["problem_family_id"] for row in test})})
        if random_labels:
            details[-1]["training_labels"] = original
            details[-1]["permuted_training_labels"] = labels
    f1, margin, domains = _v2_aggregate(measured)
    adverse = any(_v2_sentinel(*pair) for pair in domains.values()) if lodo else _v2_sentinel(f1, margin)
    return {"view": view_name, "replica": replica["id"] if replica else None,
        "status": "NON_INTERPRETABLE" if adverse else "PASS",
        "reason": "conjunctive sentinel triggered" if adverse else "specified sentinel not triggered",
        "f1": _v2_fraction(f1), "paired_margin": _v2_fraction(margin),
        "domains": {name: {"f1": _v2_fraction(pair[0]), "paired_margin": _v2_fraction(pair[1])} for name, pair in domains.items()},
        "units": details}


def _v2_partition_units(rows, contract, replica):
    units = []
    for domain in sorted(contract["partition_train_families"]):
        families = sorted({row["problem_family_id"] for row in rows.values() if row["domain"] == domain})
        count = contract["partition_train_families"][domain]
        if count >= len(families):
            raise LookupError("random partition cannot provide nonempty held-out family support")
        shuffled = list(families)
        random.Random(replica["seed"]).shuffle(shuffled)
        train_families, test_families = sorted(shuffled[:count]), sorted(shuffled[count:])
        observed = {"train_families": train_families, "test_families": test_families}
        if observed != contract["partition_assignments"][replica["id"]][domain]:
            raise ValueError("derived partition differs from supplied declared assignment")
        train_ids = sorted(identity for identity, row in rows.items() if row["domain"] == domain and row["problem_family_id"] in train_families)
        test_ids = sorted(identity for identity, row in rows.items() if row["domain"] == domain and row["problem_family_id"] in test_families)
        units.append({"id": replica["id"]+":"+domain, "fold": replica["id"], "domain": domain,
                      "train_ids": train_ids, "test_ids": test_ids})
    return units


def _v2_integrity_scopes(rows, contract, scope_kind, replica=None):
    """Record actual checked boundaries, not planned or failed derivations."""
    return [{"scope_kind": scope_kind, "replica": replica, "unit": unit["id"],
             "domain": unit["domain"], "fold": unit["fold"],
             "train_ids": list(unit["train_ids"]), "test_ids": list(unit["test_ids"]),
             "train_families": sorted({rows[i]["problem_family_id"] for i in unit["train_ids"]}),
             "test_families": sorted({rows[i]["problem_family_id"] for i in unit["test_ids"]}),
             "boundaries": [list(boundary) for boundary in contract["boundaries"]],
             "payload_stage_ids": [stage["id"] for stage in contract["payload_stages"]]}
            for unit in contract["units"]]


def _v2_report(controls, digest=None, contract=None, scopes=None):
    # Retain a canonical snapshot only after complete mechanical validation.
    # This is reconstructible integrity evidence, not consent or qualification.
    retained = json.loads(_v2_canonical(contract)) if contract is not None else None
    return {"artifact_class": "a0-shortcut-audit-prospective", "method_selection": dict(_V2_SELECTION),
        "method_proposal_sha256": _V2_PROPOSAL_SHA256,
        "status": _v2_gate({name: item["status"] for name, item in controls.items()}),
        "controls": controls, "mechanical_evidence_sha256": digest,
        "mechanical_evidence_contract": retained,
        "mechanical_evidence_validation": "validated" if retained is not None else "UNVERIFIED",
        "evaluated_integrity_scopes": json.loads(_v2_canonical(scopes or [])),
        "mechanical_freeze_independently_verified": False,
        "duplicate_coverage": "exact-normalized-only; no near-duplicate, paraphrase or semantic screening",
        "empirical": False, "scientific_status": "exploratory", "evidence_eligible": False,
        "expert_validated": False, "claim_ids": [], "primary_scientific_success": False}


def _audit_prospective_shortcuts(cases_path, targets_path, protocol_path, evidence):
    """Admit mechanical evidence before file access, then use the shared real consumer."""
    contract, digest = None, None
    try:
        contract, digest = _v2_contract(evidence)
        protocol = _load_protocol(protocol_path)
        _validate_prospective_controls(protocol)
        def load_rows(path):
            return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
        return _audit_prospective_records(load_rows(cases_path), load_rows(targets_path), protocol, evidence)
    except LookupError as exc:
        return _v2_report({name: {"status": "UNEVALUABLE", "reason": str(exc)} for name in _DEFAULT_A0_CONTROLS}, digest, contract)
    except (ValueError, TypeError, UnicodeError, OSError) as exc:
        return _v2_report({name: {"status": "FAIL", "reason": str(exc)} for name in _DEFAULT_A0_CONTROLS}, digest, contract)


def _validate_prospective_controls(protocol):
    """Require the complete frozen control registry before reading any data."""
    configuration = protocol.get("shortcut_evaluation")
    if configuration is None:
        raise LookupError("shortcut control configuration absent")
    if not isinstance(configuration, dict):
        raise ValueError("shortcut control configuration must be an object")
    if "a0_controls" not in configuration:
        raise LookupError("required shortcut controls absent")
    requested = configuration["a0_controls"]
    if not isinstance(requested, list) or len(requested) != len(_DEFAULT_A0_CONTROLS) or set(requested) != set(_DEFAULT_A0_CONTROLS):
        raise ValueError("all fourteen controls must remain required and applicable")


def _audit_prospective_records(cases, targets, protocol, evidence):
    """Execute the same fourteen D1–D7 controls on already captured records."""
    contract, digest, scopes = None, None, []
    try:
        contract, digest = _v2_contract(evidence)
        _validate_prospective_controls(protocol)
        rows = _v2_rows(cases, targets, contract)
        controls = _v2_integrity(rows, contract)
        scopes.extend(_v2_integrity_scopes(rows, contract, "original_lodo"))
        partition_units, partition_errors = {}, {}
        # Integrity is scoped to each actual evaluation, including every
        # supplied random replica. Never merge fold memberships into a split.
        for replica in contract["replicas"]:
            try:
                units = _v2_partition_units(rows, contract, replica)
                partition_units[replica["id"]] = units
                derived_contract = {**contract, "units": units}
                checked = _v2_integrity(rows, derived_contract, "derived_random_partition", replica["id"])
                scopes.extend(_v2_integrity_scopes(rows, derived_contract, "derived_random_partition", replica["id"]))
                for name, result in checked.items():
                    controls[name]["issues"].extend(result["issues"])
                    if result["status"] == "FAIL":
                        controls[name]["status"] = "FAIL"
                        controls[name]["reason"] = result["reason"]
            except (LookupError, ValueError) as exc:
                partition_errors[replica["id"]] = exc
                status = "UNEVALUABLE" if isinstance(exc, LookupError) else "FAIL"
                for result in controls.values():
                    if result["status"] != "FAIL":
                        result["status"] = status
                        result["reason"] = str(exc)
        for control in _V2_METRIC_CONTROLS:
            evaluations = []
            try:
                replicas = contract["replicas"] if control.startswith("random_") else [None]
                for replica in replicas:
                    if control == "random_partition_controls":
                        if replica["id"] in partition_errors:
                            raise partition_errors[replica["id"]]
                        units = partition_units[replica["id"]]
                    else:
                        units = contract["units"]
                    for view in contract["control_views"][control]:
                        evaluations.append(_v2_evaluate(rows, units, contract, view, replica,
                            random_labels=control == "random_label_controls",
                            lodo=control == "leave_one_domain_out_surface_evaluation"))
                adverse = any(item["status"] == "NON_INTERPRETABLE" for item in evaluations)
                controls[control] = {"status": "NON_INTERPRETABLE" if adverse else "PASS",
                    "reason": "at least one view/replica triggered" if adverse else "all required view/replica sentinels complete",
                    "evaluations": evaluations}
            except (LookupError, ValueError) as exc:
                controls[control] = {"status": "UNEVALUABLE" if isinstance(exc, LookupError) else "FAIL",
                    "reason": str(exc), "evaluations": evaluations}
        return _v2_report(controls, digest, contract, scopes)
    except LookupError as exc:
        return _v2_report({name: {"status": "UNEVALUABLE", "reason": str(exc)} for name in _DEFAULT_A0_CONTROLS}, digest, contract, scopes)
    except (ValueError, TypeError, UnicodeError, OSError) as exc:
        return _v2_report({name: {"status": "FAIL", "reason": str(exc)} for name in _DEFAULT_A0_CONTROLS}, digest, contract, scopes)


PRODUCTION_MECHANICS_PROFILE = "a0x-shortcut-mechanics-production-v1"
_PRODUCTION_DOMAINS = (
    "agriculture", "energy", "manufacturing", "medicine", "software", "transport",
)


def production_mechanics_recipe() -> dict[str, Any]:
    """Return the prospective declaration, chosen before any corpus or labels.

    Twenty fixed replicas exercise both negative controls independently; they
    are not a permutation p-value or the primary analysis budget of 199.
    The existing configured seed is retained without outcome-driven selection.
    Case/family assignments are derived later from metadata by a frozen rule.
    This declaration establishes no human consent or observed scientific gate.
    """
    fields = ["problem", "initial_state", "desired_improvement", "worsening_consequence",
              "transformation", "resulting_state", "solution"]
    views = {
        "surface_words": {"kind": "word_unigrams", "fields": fields},
        "surface_chars": {"kind": "char_3_5_grams", "fields": fields},
        "surface_length": {"kind": "length_and_punctuation", "fields": fields},
        "template_style": {"kind": "categorical", "fields": ["template_id"]},
        "provenance": {"kind": "categorical", "fields": ["generator_id", "domain"]},
        "problem_words": {"kind": "word_unigrams", "fields": ["problem"]},
        "action_taxonomy": {"kind": "keyword_counts", "fields": ["transformation"], "lexicon": _ACTION_LEXICON},
        "transformation_taxonomy": {"kind": "keyword_counts", "fields": ["solution"], "lexicon": _TRANSFORMATION_LEXICON},
        "adjacent_proxy": {"kind": "keyword_counts", "fields": fields, "lexicon": _ADJACENT_LEXICON},
    }
    controls = {
        "bag_of_words_baselines": ["surface_words"],
        "character_ngram_baselines": ["surface_chars"],
        "length_and_punctuation_baselines": ["surface_length"],
        "style_and_template_baselines": ["template_style"],
        "provenance_classifiers": ["provenance"],
        "problem_only_label_prediction": ["problem_words"],
        "leave_one_domain_out_surface_evaluation": [
            "surface_words", "surface_chars", "surface_length", "template_style", "provenance", "problem_words",
        ],
        "generic_action_taxonomy_controls": ["action_taxonomy"],
        "generic_transformation_taxonomy_controls": ["transformation_taxonomy"],
        "adjacent_principle_proxy_controls": ["adjacent_proxy"],
        "random_label_controls": sorted(views),
        "random_partition_controls": sorted(views),
    }
    recipe = {
        "schema": PRODUCTION_MECHANICS_PROFILE,
        "method_selection": _V2_SELECTION,
        "method_proposal_sha256": _V2_PROPOSAL_SHA256,
        "protocol_id": "a0-automated-weak-proxy-v1.0.3",
        "classes": ["inversion_like", "segmentation_like"],
        "domains": list(_PRODUCTION_DOMAINS),
        "calibration_families_per_domain": 8,
        "cases_per_family": 2,
        "evaluation_rule": "leave-one-declared-domain-out-lexical-id-v1",
        "partition_rule": "sorted-family-mt19937-shuffle-first-four-v1",
        "partition_train_families": 4,
        "replica_seeds": list(range(20260814, 20260834)),
        "views": views,
        "control_views": controls,
        "algorithm": "nearest-centroid-squared-euclidean-v1",
        "numerics": "binary64-features-fraction-metrics-v1",
        "tie_break": "utf8-lexicographic",
        "randomizer": "python-mt19937-shuffle-v1",
        "runtime_version_binding": "exact-native-version-in-gate-b-readiness-v1",
        "payload_stages": [
            {"id": f"rendered:{view}", "fields": [f"__model_{view}"]}
            for view in ("problem_only", "transformation_only", "problem_plus_transformation", "problem_plus_solution")
        ],
        "payload_rendering": "a0-activation-sites-build-view-texts-v1",
        "sentinel_text": "Analysis anchor:",
        "payload_encoding": "length-prefixed-utf8-v1",
        "normalization": "utf8-nfc-lf-v1",
        "unicode_version_binding": "native-unidata-version-in-effective-contract-v1",
        "boundaries": [["train", "test"]],
    }
    return json.loads(_v2_canonical(recipe))


def bind_production_mechanics(
    cases: list[Mapping[str, Any]], recipe: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the complete calibration schedule from label-free metadata only.

    Recipe admission precedes examining records. This pure constructor performs
    no filesystem access and never chooses mechanics from measured outcomes.
    A hash proves consistency, not owner consent or scientific qualification.
    """
    expected = production_mechanics_recipe()
    if not isinstance(recipe, Mapping) or _v2_canonical(recipe) != _v2_canonical(expected):
        raise ValueError("production mechanical recipe does not match the frozen declaration")
    if not isinstance(cases, list) or len(cases) != 96:
        raise ValueError("production calibration must provide all 96 planned cases")
    rows: dict[str, dict[str, Any]] = {}
    families: dict[str, dict[str, list[str]]] = {domain: {} for domain in _PRODUCTION_DOMAINS}
    forbidden = {"label", "operator_proxy_family", "target", "gold", "y_true"}
    for row in cases:
        if not isinstance(row, Mapping) or forbidden & set(row):
            raise ValueError("production public calibration metadata contains a target role")
        identity = _v2_id(row.get("case_id"))
        family = _v2_id(row.get("problem_family_id"))
        domain = _v2_id(row.get("domain"))
        if row.get("split") != "calibration" or domain not in families or identity in rows:
            raise ValueError("production calibration identity or split differs")
        rows[identity] = dict(row)
        families[domain].setdefault(family, []).append(identity)
    if any(len(groups) != 8 or any(len(ids) != 2 for ids in groups.values()) for groups in families.values()):
        raise ValueError("production calibration family support differs from the frozen schedule")
    family_domains: dict[str, str] = {}
    for domain, groups in families.items():
        for family in groups:
            if family in family_domains:
                raise ValueError("production family identity crosses a domain")
            family_domains[family] = domain
    units = [
        {"id": f"lodo:{domain}", "fold": "fold-0", "domain": domain,
         "train_ids": sorted(identity for identity, row in rows.items() if row["domain"] != domain),
         "test_ids": sorted(identity for identity, row in rows.items() if row["domain"] == domain)}
        for domain in _PRODUCTION_DOMAINS
    ]
    replicas = [{"id": f"replica-{index:02d}", "seed": seed} for index, seed in enumerate(expected["replica_seeds"])]
    assignments: dict[str, dict[str, Any]] = {}
    for replica in replicas:
        assignments[replica["id"]] = {}
        for domain in _PRODUCTION_DOMAINS:
            shuffled = sorted(families[domain])
            random.Random(replica["seed"]).shuffle(shuffled)
            assignments[replica["id"]][domain] = {
                "train_families": sorted(shuffled[:4]), "test_families": sorted(shuffled[4:]),
            }
    effective = {
        "schema": _PRODUCTION_EVALUATION_PROFILE,
        "production_recipe_sha256": hashlib.sha256(_v2_canonical(expected)).hexdigest(),
        "classes": expected["classes"], "views": expected["views"], "control_views": expected["control_views"],
        "units": units, "replicas": replicas, "partition_assignments": assignments,
        "partition_train_families": {domain: 4 for domain in _PRODUCTION_DOMAINS},
        "python_version": sys.version.split()[0], "unicode_version": unicodedata.unidata_version,
        **{key: expected[key] for key in ("randomizer", "algorithm", "numerics", "tie_break",
                                       "payload_stages", "payload_encoding", "normalization", "boundaries")},
    }
    digest = hashlib.sha256(_v2_canonical(effective)).hexdigest()
    _v2_contract({"contract": effective, "sha256": digest})
    return {
        "artifact_class": "a0x-production-mechanics-binding-v1",
        "recipe": expected, "recipe_sha256": hashlib.sha256(_v2_canonical(expected)).hexdigest(),
        "evaluation": {"contract": effective, "sha256": digest},
        "human_consent_verified": False, "scientific_gate_pass": False,
    }
