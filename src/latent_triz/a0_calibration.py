"""Atomic calibration runner and freeze-candidate receipt for Phase A0."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .a0_power import calibrate_a0_power
from .a0_shortcuts import (
    audit_a0_shortcuts, _validate_prospective_selection, bind_production_mechanics,
    production_mechanics_recipe, _audit_prospective_records, _validate_prospective_controls,
)


class A0CalibrationError(RuntimeError):
    """Raised when calibration inputs or publication integrity fail."""


def _stable(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise A0CalibrationError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise A0CalibrationError(f"{label} must be an object")
    return dict(value)


def _verify_file(corpus_root: Path, entry: Mapping[str, Any], label: str) -> Path:
    relative = Path(str(entry.get("path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise A0CalibrationError(f"unsafe {label} path")
    path = (corpus_root / relative).resolve()
    if not path.is_relative_to(corpus_root.resolve()) or not path.is_file():
        raise A0CalibrationError(f"missing {label}")
    if _sha256(path) != entry.get("sha256") or path.stat().st_size != entry.get("size"):
        raise A0CalibrationError(f"{label} receipt mismatch")
    return path


def run_production_shortcut_calibration(
    protocol_path: str | Path, cases_path: str | Path, targets_path: str | Path,
    recipe: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute the approved prospective controls without recalibrating primary analysis.

    The production caller owns material authorization and input hash checks.
    Recipe and public metadata are admitted before calibration targets are read.
    Derived hashes prove integrity only, never human consent or independent review.
    The frozen primary power, sample size, permutations and stopping rules remain
    unchanged; an adverse shortcut remains adverse rather than a literal PASS.
    """
    if not isinstance(recipe, Mapping) or _stable(recipe) != _stable(production_mechanics_recipe()):
        raise A0CalibrationError("production mechanical recipe differs")
    protocol = _load_object(Path(protocol_path), "frozen production protocol")
    if (
        protocol.get("protocol_id") != recipe["protocol_id"]
        or protocol.get("protocol_status") != "frozen"
        or set(protocol.get("target_families", ())) != set(recipe["classes"])
        or set(protocol.get("neutral_domains", ())) != set(recipe["domains"])
        or protocol.get("calibration_families_per_domain") != 8
    ):
        raise A0CalibrationError("frozen production protocol does not bind the mechanical recipe")
    frozen = protocol.get("frozen_analysis", {})
    for key, expected in (("selected_families_per_domain", 4), ("selected_family_count", 24),
                          ("selected_permutation_budget", 199), ("critical_successes", 19),
                          ("max_statistic_multiplicity", 12)):
        if frozen.get(key) != expected:
            raise A0CalibrationError("frozen primary analysis changed")
    configuration = protocol.get("shortcut_evaluation", {})
    _validate_prospective_controls(protocol)
    if configuration.get("macro_f1_threshold") != 0.65 or configuration.get("margin_over_majority") != 0.10:
        raise A0CalibrationError("approved prospective sentinel thresholds changed")
    def rows(path: str | Path) -> list[dict[str, Any]]:
        return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [row for row in rows(cases_path) if row.get("split") == "calibration"]
    binding = bind_production_mechanics(cases, recipe)
    from .a0_activation_sites import build_view_texts
    rendered = []
    for case in cases:
        if any(key.startswith("__model_") for key in case):
            raise A0CalibrationError("public inputs contain reserved rendered-payload fields")
        views = build_view_texts(case, sentinel_text=recipe["sentinel_text"])
        rendered.append({**case, **{f"__model_{name}": value for name, value in views.items()}})
    targets = rows(targets_path)
    result = _audit_prospective_records(rendered, targets, protocol, binding["evaluation"])
    result.update({
        "production_mechanics_profile": recipe["schema"],
        "production_recipe_sha256": binding["recipe_sha256"],
        "production_binding_status": "validated_against_source_recipe",
        "human_consent_verified": False,
        "primary_analysis_recalibrated": False,
        "input_hashes": {"protocol": hashlib.sha256(Path(protocol_path).read_bytes()).hexdigest(),
            "cases": hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
            "targets": hashlib.sha256(Path(targets_path).read_bytes()).hexdigest()},
    })
    return result


def run_a0_calibration(
    protocol_path: str | Path,
    corpus_dir: str | Path,
    output_dir: str | Path,
    *,
    method_selection: Mapping[str, Any] | None = None,
    mechanical_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_prospective_selection(method_selection, mechanical_evidence)
    protocol_file = Path(protocol_path).resolve()
    corpus_root = Path(corpus_dir).resolve()
    output_root = Path(output_dir).resolve()
    if output_root.exists():
        if not output_root.is_dir() or any(output_root.iterdir()):
            raise A0CalibrationError(f"output directory already exists: {output_root}")
        output_root.rmdir()

    protocol = _load_object(protocol_file, "protocol")
    manifest_path = corpus_root / "manifest.json"
    manifest = _load_object(manifest_path, "corpus manifest")
    protocol_hash = hashlib.sha256(_stable(protocol).encode("utf-8")).hexdigest()
    if manifest.get("protocol_hash") != protocol_hash or manifest.get("protocol_id") != protocol.get("protocol_id"):
        raise A0CalibrationError("corpus does not match protocol")
    for field, expected in (
        ("empirical", True),
        ("scientific_status", "exploratory"),
        ("evidence_eligible", False),
        ("expert_validated", False),
        ("claim_ids", []),
    ):
        if manifest.get(field) != expected:
            raise A0CalibrationError(f"invalid A0 epistemic field: {field}")

    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise A0CalibrationError("corpus manifest has no files")
    cases_path = _verify_file(corpus_root, files["cases_jsonl"], "cases")
    calibration_targets_path = _verify_file(
        corpus_root, files["calibration_targets_jsonl"], "calibration targets"
    )
    sealed_entry = files.get("sealed_targets_jsonl")
    if not isinstance(sealed_entry, Mapping):
        raise A0CalibrationError("sealed target receipt is missing")
    # Deliberately do not open the sealed target file during calibration.

    power = calibrate_a0_power(protocol_file)
    if method_selection is None:
        shortcuts = audit_a0_shortcuts(cases_path, calibration_targets_path, protocol_file)
    else:
        shortcuts = audit_a0_shortcuts(
            cases_path, calibration_targets_path, protocol_file,
            method_selection=method_selection, mechanical_evidence=mechanical_evidence,
        )
    if protocol.get("protocol_status") == "frozen":
        frozen = protocol.get("frozen_analysis")
        selected = power.get("selected")
        if not isinstance(frozen, Mapping) or not isinstance(selected, Mapping):
            raise A0CalibrationError("frozen protocol has no valid selected analysis")
        expected_selection = {
            "families_per_domain": frozen.get("selected_families_per_domain"),
            "family_count": frozen.get("selected_family_count"),
            "permutation_budget": frozen.get("selected_permutation_budget"),
            "critical_successes": frozen.get("critical_successes"),
        }
        if any(selected.get(key) != value for key, value in expected_selection.items()):
            raise A0CalibrationError("frozen selection does not match exact recalibration")
    status = "pass" if power["status"] == "pass" and shortcuts["status"] == "pass" else "failed"
    if method_selection is not None:
        status = shortcuts["status"] if power["status"] == "pass" else "FAIL"
    summary = {
        "artifact_class": "a0-calibration-summary",
        "protocol_id": protocol["protocol_id"],
        "protocol_status": protocol["protocol_status"],
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": [],
        "status": status,
        "power_status": power["status"],
        "shortcut_status": shortcuts["status"],
        "selected": power.get("selected"),
        "sealed_targets_accessed": False,
        "limitations": [
            "Calibration tests a procedural operator proxy, not the TRIZ construct.",
            "No model activation or sealed outcome is inspected in this phase.",
        ],
    }
    if method_selection is not None:
        summary.update({
            "method_selection": dict(method_selection),
            "production_qualified": False,
            "shortcut_reasons": shortcuts["controls"],
        })
        summary["limitations"].append(
            "Prospective engineering evidence is not an independently qualified production freeze."
        )

    output_root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(output_root.parent)) as temporary:
        staging = Path(temporary) / output_root.name
        staging.mkdir()
        payloads = {"power.json": power, "shortcuts.json": shortcuts, "summary.json": summary}
        for name, payload in payloads.items():
            (staging / name).write_text(_stable(payload) + "\n", encoding="utf-8", newline="\n")
        artifact_hashes = {name: _sha256(staging / name) for name in sorted(payloads)}
        freeze_manifest = {
            "artifact_class": "a0-protocol-freeze-manifest",
            "protocol_id": protocol["protocol_id"],
            "protocol_hash": protocol_hash,
            "corpus_manifest_sha256": _sha256(manifest_path),
            "cases_sha256": files["cases_jsonl"]["sha256"],
            "calibration_targets_sha256": files["calibration_targets_jsonl"]["sha256"],
            "sealed_targets_sha256": sealed_entry.get("sha256"),
            "sealed_targets_accessed": False,
            "selected": power.get("selected"),
            "calibration_artifact_hashes": artifact_hashes,
            "empirical": True,
            "scientific_status": "exploratory",
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
            "status": "frozen" if status == "pass" and protocol.get("protocol_status") == "frozen" else "failed",
        }
        if method_selection is not None:
            freeze_manifest.update({
                "status": status,
                "production_qualified": False,
                "method_selection": dict(method_selection),
            })
        (staging / "freeze-manifest.json").write_text(
            _stable(freeze_manifest) + "\n", encoding="utf-8", newline="\n"
        )
        if output_root.exists():
            raise A0CalibrationError(f"output directory already exists: {output_root}")
        staging.replace(output_root)
    return summary
