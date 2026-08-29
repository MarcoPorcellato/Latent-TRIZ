"""Target-free A0X input freezing for the historical A0 and A0-R1 legs.

The module deliberately separates public-case selection from sealed-target
declarations.  A sealed target is represented only by commitments carried by
its already-frozen provenance manifest until an explicitly authorized analysis
boundary is reached elsewhere.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    Leg,
    PairBinding,
    LegFreezeBinding,
    build_leg_freeze_binding,
    canonical_json_sha256,
    compute_dense_bound,
    sha256_file,
)
from .validator import validate


class A0XFreezeError(ValueError):
    """Raised when a protected input or target-free selection cannot be frozen."""


SOURCE_BASE_COMMIT = "188eb65b5e249923baddadeba52659f07fcd1609"
FROZEN_DOMAINS = ("agriculture", "energy", "manufacturing", "medicine", "software", "transport")
SELECTION_PATH = "experiments/a0x-six-model/a0-selection-manifest.json"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_SAFE_RELATIVE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
_COMMON = {
    "empirical": True,
    "scientific_status": "exploratory",
    "evidence_eligible": False,
    "expert_validated": False,
    "claim_ids": [],
}

_LEG_SOURCES = {
    Leg.A0: {
        "protocol": "experiments/a0-automated-weak-proxy/protocol.json",
        "implementation": "experiments/a0-automated-weak-proxy/implementation.json",
        "protected_tree": "experiments/a0x-six-model/protected-a0-tree.json",
        "selection": "experiments/a0x-six-model/a0-selection-manifest.json",
        "protocol_fields": (
            "corpus_generation", "calibration_families_per_domain", "sealed_families_per_domain",
            "paired_syntax_templates", "neutral_domains", "target_families", "splits",
            "predeclared_calibration_rule", "frozen_analysis", "views", "token_sites",
            "preregistered_layers", "shortcut_evaluation", "outcome_rules", "shortcuts", "runtime",
        ),
        "implementation_fields": (
            "primary_view", "surface_baseline_view", "sensitivity_views", "sentinel_text",
            "layer_index_semantics", "classifier", "cross_validation", "paired_family_success",
            "primary_aggregation", "surface_margin", "permutations", "token_site_applicability",
            "epistemic_boundary",
        ),
    },
    Leg.R1: {
        "protocol": "experiments/a0r1-independent-proxy/protocol.json",
        "implementation": "experiments/a0r1-independent-proxy/implementation.json",
        "protected_tree": "experiments/a0x-six-model/protected-a0r1-tree.json",
        "selection": "data/a0r1/manifest.json",
        "protocol_fields": (
            "protocol_type", "independence_audit", "runtime", "primary_endpoint",
            "sensitivity_endpoints", "shortcut_evaluation", "thresholds", "calibration",
            "outcome_rules", "outcome_classes",
        ),
        "implementation_fields": (
            "classifier", "permutations", "primary_endpoint", "surface_baseline_view",
            "surface_baseline_token_site", "sentinel_text", "sensitivity_view_definition",
            "sensitivity_may_replace_primary", "hidden_state_contract", "domain_direction",
            "outcome_rules", "outcome_classes", "token_site_applicability", "epistemic_boundary",
        ),
    },
}

_IMPLEMENTATION_PATHS = (
    "schemas/a0x-authorization-dossier.schema.json",
    "schemas/a0x-ccp-observation.schema.json",
    "schemas/a0x-execution-authorization.schema.json",
    "schemas/a0x-guard-launch.schema.json",
    "schemas/a0x-material-execution-contract.schema.json",
    "schemas/a0x-publication-manifest.schema.json",
    "schemas/a0x-qualification-authorization.schema.json",
    "schemas/a0x-qualification-evidence.schema.json",
    "scripts/a0x_contract_check.py",
    "scripts/a0x_material.py",
    "scripts/a0x_material_child.py",
    "src/latent_triz/a0x_a0_activations.py",
    "src/latent_triz/a0x_a0_analysis.py",
    "src/latent_triz/a0x_contract.py",
    "src/latent_triz/a0x_ccp_executor.py",
    "src/latent_triz/a0x_execution.py",
    "src/latent_triz/a0x_freeze.py",
    "src/latent_triz/a0x_material_contract.py",
    "src/latent_triz/a0x_material_runtime.py",
    "src/latent_triz/a0x_model_adapter.py",
    "src/latent_triz/a0x_preflight.py",
    "src/latent_triz/a0x_production_adapter.py",
    "src/latent_triz/a0x_r1_analysis.py",
    "src/latent_triz/a0x_r1_activations.py",
    "src/latent_triz/a0x_report.py",
    "src/latent_triz/a0x_runner.py",
    "src/latent_triz/a0x_verify.py",
    "tests/test_a0x_activations.py",
    "tests/test_a0x_a0_analysis.py",
    "tests/test_a0x_contract.py",
    "tests/test_a0x_contract_check.py",
    "tests/test_a0x_ccp_executor.py",
    "tests/test_a0x_execution.py",
    "tests/test_a0x_freeze.py",
    "tests/test_a0x_frozen_package.py",
    "tests/test_a0x_material.py",
    "tests/test_a0x_material_child.py",
    "tests/test_a0x_material_contract.py",
    "tests/test_a0x_material_runtime.py",
    "tests/test_a0x_matrix_plan_binding.py",
    "tests/test_a0x_preflight.py",
    "tests/test_a0x_production_adapter.py",
    "tests/test_a0x_r1_analysis.py",
    "tests/test_a0x_report.py",
    "tests/test_a0x_runner.py",
    "tests/test_a0x_schemas.py",
    "tests/test_a0x_verify.py",
    "tests/fixtures/a0x/ccp-matrix-v2-legacy-plan-27adf8d.json",
)

_DOSSIER_FILENAMES = {
    "smollm2_360m": "smollm2_360m.json",
    "qwen3_0_6b_base": "qwen3_0_6b_base.json",
    "gpt2": "gpt2.json",
    "smollm2_135m": "smollm2_135m.json",
    "gpt_neo_125m": "gpt_neo_125m.json",
    "qwen2_5_0_5b": "qwen2_5_0_5b.json",
}


def build_protected_tree(
    root: str | Path,
    *,
    roots: Sequence[Path],
    external_assets: Sequence[Mapping[str, Any]],
    sealed_target_declarations: Mapping[str, Mapping[str, Any]] | None = None,
    provenance_manifests: Mapping[str, str] | None = None,
    source_base_commit: str = SOURCE_BASE_COMMIT,
) -> dict[str, Any]:
    """Freeze non-target inputs and declaration-only sealed-target commitments.

    ``roots`` may name files or directories relative to ``root``.  Directory
    walks are deterministic, reject symlinks, and omit sealed target paths
    before any file metadata or byte operation is attempted on them.
    """

    repository = Path(root).resolve()
    _require_revision(source_base_commit, "source_base_commit")
    declared_targets = _normalized_declarations(sealed_target_declarations or {})
    provenance_by_root = dict(provenance_manifests or {})
    entries: list[dict[str, Any]] = []

    for relative_root in roots:
        root_relative = _safe_relative(relative_root.as_posix(), "protected root")
        source = _resolve_non_target(repository, root_relative, declared_targets)
        if not source.exists():
            raise A0XFreezeError(f"protected root is missing: {root_relative}")
        if source.is_symlink():
            raise A0XFreezeError(f"protected root is a symlink: {root_relative}")
        for path in _sorted_files(repository, source, declared_targets):
            relative = _safe_relative(path.relative_to(repository).as_posix(), "protected path")
            provenance = _provenance_for(relative, root_relative, provenance_by_root)
            entries.append(_hashed_entry(repository, path, relative, provenance))

    for relative, declaration in declared_targets.items():
        entries.append(_declaration_entry(repository, relative, declaration))

    for external in external_assets:
        entries.append(_external_asset_entry(repository, external))

    entries.sort(key=lambda row: row["path"])
    if len({entry["path"] for entry in entries}) != len(entries):
        raise A0XFreezeError("protected tree contains duplicate paths")

    payload: dict[str, Any] = {
        **_COMMON,
        "artifact_class": "a0x-protected-tree",
        "source_base_commit": source_base_commit,
        "protected_paths": sorted({entry["path"] for entry in entries}),
        "entries": entries,
    }
    payload["protected_tree_sha256"] = _tree_sha256(payload)
    return payload


def verify_protected_tree(
    root: str | Path,
    tree: Mapping[str, Any],
    *,
    phase: str,
) -> None:
    """Fail closed if a non-target input drifted or a declaration is malformed."""

    if phase not in {"preflight", "postflight"}:
        raise A0XFreezeError(f"unsupported verification phase: {phase!r}")
    repository = Path(root).resolve()
    _verify_tree_shape(tree)
    expected_tree_sha = _tree_sha256(dict(tree))
    if tree.get("protected_tree_sha256") != expected_tree_sha:
        raise A0XFreezeError("protected tree digest mismatch")

    for entry in tree["entries"]:
        entry_kind = entry["entry_kind"]
        if entry_kind == "sealed_target":
            _verify_sealed_target_declaration(repository, entry)
            continue
        if entry_kind == "external_asset":
            _verify_provenance_manifest(repository, entry)
            continue
        if entry_kind != "file":
            raise A0XFreezeError("protected tree has unknown entry kind")
        relative = _safe_relative(entry["path"], "protected path")
        path = _resolve_non_target(repository, relative, {})
        if not path.is_file() or path.is_symlink():
            raise A0XFreezeError(f"protected input drift: unavailable file {relative}")
        if path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise A0XFreezeError(f"protected input drift: {relative}")
        _verify_provenance_manifest(repository, entry)


def verify_protected_tree_metadata_only(root: str | Path, tree: Mapping[str, Any]) -> None:
    """Validate only tree declarations/provenance without opening protected inputs.

    This is the synthetic verifier's boundary: sealed target and calibration
    paths remain names plus committed metadata, never file handles.
    """
    repository = Path(root).resolve()
    _verify_tree_shape(tree)
    if tree.get("protected_tree_sha256") != _tree_sha256(dict(tree)):
        raise A0XFreezeError("protected tree digest mismatch")
    for entry in tree["entries"]:
        if entry["entry_kind"] == "sealed_target":
            _verify_sealed_target_declaration(repository, entry)
        elif entry["entry_kind"] == "external_asset":
            _verify_provenance_manifest(repository, entry)
        elif entry["entry_kind"] != "file":
            raise A0XFreezeError("protected tree has unknown entry kind")


def build_a0_selection_manifest(
    *,
    cases_path: str | Path,
    corpus_manifest_path: str | Path,
    selection_path: str = SELECTION_PATH,
) -> dict[str, Any]:
    """Select exactly four lexicographic public problem families per domain."""

    cases_file = Path(cases_path)
    manifest_file = Path(corpus_manifest_path)
    records = _read_public_cases(cases_file)
    corpus_manifest = _read_json_object(manifest_file, "corpus manifest")
    domains = corpus_manifest.get("neutral_domains")
    if domains != list(FROZEN_DOMAINS):
        raise A0XFreezeError("corpus manifest does not declare the six frozen domains")

    selected: list[dict[str, str]] = []
    by_domain: dict[str, dict[str, list[Mapping[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        domain, family = _public_case_identity(record)
        if domain not in FROZEN_DOMAINS:
            raise A0XFreezeError(f"case uses an unfrozen domain: {domain}")
        by_domain[domain][family].append(record)

    for domain in FROZEN_DOMAINS:
        families = sorted(by_domain[domain])
        if len(families) < 4:
            raise A0XFreezeError(f"domain {domain} does not provide four families")
        for family in families[:4]:
            paired = sorted(by_domain[domain][family], key=lambda row: str(row["case_id"]))
            if len(paired) != 2:
                raise A0XFreezeError(f"family {family} must contain exactly two cases")
            for record in paired:
                selected.append({
                    "case_id": str(record["case_id"]),
                    "case_content_sha256": str(record["case_content_sha256"]),
                    "domain": domain,
                    "problem_family_id": family,
                    "split": str(record["split"]),
                })

    if len(selected) != 48 or len({row["problem_family_id"] for row in selected}) != 24:
        raise A0XFreezeError("selection must contain exactly 24 families and 48 cases")
    source_cases_sha256 = sha256_file(cases_file)
    source_corpus_manifest_sha256 = sha256_file(manifest_file)
    source_binding = {
        "source_cases_sha256": source_cases_sha256,
        "source_corpus_manifest_sha256": source_corpus_manifest_sha256,
    }
    return {
        **_COMMON,
        "artifact_class": "a0x-selection-manifest",
        "selection_corpus_sha256": canonical_json_sha256(source_binding),
        "selection_path": _repository_relative(cases_file, selection_path),
        "selected_case_count": 48,
        "source_cases_path": _repository_relative(cases_file),
        "source_corpus_manifest_path": _repository_relative(manifest_file),
        **source_binding,
        "selection_rule": {
            "cases_per_family": 2,
            "families_per_domain": 4,
            "family_order": "lexicographic",
            "domain_order": "frozen",
        },
        "cases": selected,
        "target_content_reads": 0,
    }


def verify_a0_selection_manifest(
    selection: Mapping[str, Any],
    *,
    cases_path: str | Path,
    corpus_manifest_path: str | Path,
) -> None:
    """Rebuild and compare the target-free manifest byte-for-byte in structure."""

    expected = build_a0_selection_manifest(
        cases_path=cases_path,
        corpus_manifest_path=corpus_manifest_path,
        selection_path=str(selection.get("selection_path", SELECTION_PATH)),
    )
    if dict(selection) != expected:
        raise A0XFreezeError("selection manifest does not match public-case inputs")


def _sorted_files(repository: Path, source: Path, declared_targets: Mapping[str, Mapping[str, Any]]) -> Iterable[Path]:
    candidates = [source] if source.is_file() else sorted(source.rglob("*"), key=lambda item: item.as_posix())
    for path in candidates:
        relative = _safe_relative(path.relative_to(repository).as_posix(), "protected path")
        if relative in declared_targets:
            continue
        _reject_symlink_components(repository, relative)
        if path.is_symlink():
            raise A0XFreezeError(f"protected tree rejects symlink: {relative}")
        if path.is_file():
            yield path


def _hashed_entry(repository: Path, path: Path, relative: str, provenance_manifest: str) -> dict[str, Any]:
    _safe_relative(provenance_manifest, "provenance manifest")
    return {
        "entry_kind": "file",
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "provenance_manifest": provenance_manifest,
        "provenance_manifest_sha256": _provenance_sha(repository, provenance_manifest),
        "verification_phase": "preflight_postflight",
    }


def _declaration_entry(repository: Path, relative: str, declaration: Mapping[str, Any]) -> dict[str, Any]:
    provenance_manifest = _safe_relative(str(declaration["provenance_manifest"]), "provenance manifest")
    return {
        "entry_kind": "sealed_target",
        "path": relative,
        "bytes": _nonnegative_int(declaration["bytes"], "sealed target bytes"),
        "sha256": _sha256_value(declaration["sha256"], "sealed target sha256"),
        "provenance_manifest": provenance_manifest,
        "provenance_manifest_sha256": _provenance_sha(repository, provenance_manifest),
        "verification_phase": "declaration_only",
    }


def _external_asset_entry(repository: Path, external: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(external, Mapping):
        raise A0XFreezeError("external asset entries must be explicit mappings")
    required = {"path", "bytes", "sha256", "provenance_manifest"}
    if set(external) != required:
        raise A0XFreezeError("external asset entry has incomplete declaration")
    provenance_manifest = _safe_relative(str(external["provenance_manifest"]), "provenance manifest")
    return {
        "entry_kind": "external_asset",
        "path": _safe_relative(str(external["path"]), "external asset path"),
        "bytes": _nonnegative_int(external["bytes"], "external asset bytes"),
        "sha256": _sha256_value(external["sha256"], "external asset sha256"),
        "provenance_manifest": provenance_manifest,
        "provenance_manifest_sha256": _provenance_sha(repository, provenance_manifest),
        "verification_phase": "external_declaration",
    }


def _normalized_declarations(value: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    normalized: dict[str, Mapping[str, Any]] = {}
    for path, declaration in value.items():
        relative = _safe_relative(path, "sealed target path")
        if not isinstance(declaration, Mapping):
            raise A0XFreezeError("sealed target declaration must be a mapping")
        if set(declaration) != {"sha256", "bytes", "provenance_manifest"}:
            raise A0XFreezeError("sealed target declaration is incomplete")
        _sha256_value(declaration["sha256"], "sealed target sha256")
        _nonnegative_int(declaration["bytes"], "sealed target bytes")
        _safe_relative(str(declaration["provenance_manifest"]), "provenance manifest")
        normalized[relative] = declaration
    return normalized


def _verify_sealed_target_declaration(repository: Path, entry: Mapping[str, Any]) -> None:
    _verify_provenance_manifest(repository, entry)
    manifest = _read_json_object(repository / entry["provenance_manifest"], "target provenance manifest")
    files = manifest.get("files")
    if not isinstance(files, Mapping):
        raise A0XFreezeError("target provenance manifest lacks files")
    relative = _safe_relative(str(entry["path"]), "sealed target path")
    manifest_relative = Path(relative).relative_to(Path(entry["provenance_manifest"]).parent).as_posix()
    expected = next(
        (
            candidate for candidate in files.values()
            if isinstance(candidate, Mapping) and candidate.get("path") == manifest_relative
        ),
        None,
    )
    if not isinstance(expected, Mapping):
        raise A0XFreezeError("sealed target declaration is absent from provenance manifest")
    if expected.get("sha256") != entry["sha256"] or expected.get("size") != entry["bytes"]:
        raise A0XFreezeError("sealed target declaration drift")


def _verify_provenance_manifest(repository: Path, entry: Mapping[str, Any]) -> None:
    provenance = _safe_relative(str(entry["provenance_manifest"]), "provenance manifest")
    manifest_path = _resolve_non_target(repository, provenance, {})
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise A0XFreezeError(f"protected input drift: provenance manifest {provenance}")
    if sha256_file(manifest_path) != entry["provenance_manifest_sha256"]:
        raise A0XFreezeError(f"protected input drift: provenance manifest {provenance}")


def _verify_tree_shape(tree: Mapping[str, Any]) -> None:
    if tree.get("artifact_class") != "a0x-protected-tree" or not isinstance(tree.get("entries"), list):
        raise A0XFreezeError("protected tree is malformed")
    _require_revision(tree.get("source_base_commit"), "source_base_commit")
    for entry in tree["entries"]:
        if not isinstance(entry, Mapping):
            raise A0XFreezeError("protected tree entry is malformed")
        required = {
            "entry_kind", "path", "bytes", "sha256", "provenance_manifest",
            "provenance_manifest_sha256", "verification_phase",
        }
        if set(entry) != required:
            raise A0XFreezeError("protected tree entry has unexpected fields")
        _safe_relative(str(entry["path"]), "protected path")
        _safe_relative(str(entry["provenance_manifest"]), "provenance manifest")
        _nonnegative_int(entry["bytes"], "protected bytes")
        _sha256_value(entry["sha256"], "protected sha256")
        _sha256_value(entry["provenance_manifest_sha256"], "provenance sha256")


def _tree_sha256(payload: Mapping[str, Any]) -> str:
    normalized = dict(payload)
    normalized.pop("protected_tree_sha256", None)
    return canonical_json_sha256(normalized)


def _provenance_for(relative: str, root_relative: str, provenance_by_root: Mapping[str, str]) -> str:
    configured = provenance_by_root.get(root_relative)
    if configured is not None:
        return _safe_relative(configured, "provenance manifest")
    candidate = f"{root_relative.rstrip('/')}/manifest.json"
    return candidate if relative == candidate else relative


def _provenance_sha(repository: Path, provenance_manifest: str) -> str:
    path = _resolve_non_target(repository, provenance_manifest, {})
    if not path.is_file() or path.is_symlink():
        raise A0XFreezeError(f"provenance manifest is missing: {provenance_manifest}")
    return sha256_file(path)


def _resolve_non_target(repository: Path, relative: str, declared_targets: Mapping[str, Mapping[str, Any]]) -> Path:
    if relative in declared_targets:
        raise A0XFreezeError("sealed target cannot be treated as a non-target file")
    _reject_symlink_components(repository, relative)
    path = repository / relative
    resolved = path.resolve()
    if not resolved.is_relative_to(repository):
        raise A0XFreezeError(f"path escapes protected root: {relative}")
    return path


def _reject_symlink_components(repository: Path, relative: str) -> None:
    candidate = repository
    for component in Path(relative).parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise A0XFreezeError(f"protected tree rejects symlink component: {relative}")


def _safe_relative(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_RELATIVE.fullmatch(value):
        raise A0XFreezeError(f"{label} must be a safe relative path")
    return value


def _sha256_value(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XFreezeError(f"{label} must be a SHA-256 digest")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise A0XFreezeError(f"{label} must be a non-negative integer")
    return value


def _require_revision(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{40}", value):
        raise A0XFreezeError(f"{label} must be a full Git revision")
    return value


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XFreezeError(f"cannot read {label}") from error
    if not isinstance(value, dict):
        raise A0XFreezeError(f"{label} must be an object")
    return value


def _read_public_cases(path: Path) -> list[Mapping[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise A0XFreezeError("cannot read public cases") from error
    rows: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise A0XFreezeError(f"public case JSON is invalid at line {line_number}") from error
        if not isinstance(value, Mapping):
            raise A0XFreezeError(f"public case is not an object at line {line_number}")
        rows.append(value)
    return rows


def _public_case_identity(record: Mapping[str, Any]) -> tuple[str, str]:
    required = ("case_id", "case_content_sha256", "domain", "problem_family_id", "split")
    if any(not isinstance(record.get(field), str) or not str(record[field]).strip() for field in required):
        raise A0XFreezeError("public case is missing a selection field")
    _sha256_value(record["case_content_sha256"], "case content sha256")
    return str(record["domain"]), str(record["problem_family_id"])


def _repository_relative(path: Path, fallback: str | None = None) -> str:
    if fallback is not None:
        return _safe_relative(fallback, "selection path")
    try:
        return _safe_relative(path.resolve().relative_to(Path.cwd().resolve()).as_posix(), "source path")
    except ValueError:
        return _safe_relative(path.name, "source path")


def _sealed_declarations(root: Path, corpus: str, manifest: str, target: str) -> dict[str, dict[str, Any]]:
    manifest_value = _read_json_object(root / manifest, "corpus manifest")
    files = manifest_value.get("files")
    if not isinstance(files, Mapping):
        raise A0XFreezeError("corpus manifest lacks files")
    entry = next(
        (value for value in files.values() if isinstance(value, Mapping) and value.get("path") == target),
        None,
    )
    if not isinstance(entry, Mapping):
        raise A0XFreezeError("corpus manifest lacks sealed target declaration")
    return {f"{corpus}/{target}": {
        "sha256": entry.get("sha256"),
        "bytes": entry.get("size"),
        "provenance_manifest": manifest,
    }}


def _canonical_tree_inputs(
    root: Path,
    leg: str,
) -> tuple[tuple[Path, ...], dict[str, dict[str, Any]], dict[str, str], tuple[dict[str, Any], ...]]:
    if leg == "a0":
        corpus = "data/a0"
        manifest = "data/a0/manifest.json"
        target = "sealed-targets/targets.jsonl"
        roots = (
            Path("experiments/a0-automated-weak-proxy"), Path("data/a0/cases.jsonl"),
            Path("data/a0/procedural-targets/calibration-targets.jsonl"), Path(manifest),
            Path("results/a0/calibration"), Path("results/a0/a0-v1.0.3-e93a9faa"),
        )
        provenance = {
            "experiments/a0-automated-weak-proxy": "experiments/a0-automated-weak-proxy/protocol.json",
            "data/a0/cases.jsonl": manifest,
            "data/a0/procedural-targets/calibration-targets.jsonl": manifest,
            manifest: manifest,
            "results/a0/calibration": "results/a0/calibration/freeze-manifest.json",
            "results/a0/a0-v1.0.3-e93a9faa": "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json",
        }
        external_assets: tuple[dict[str, Any], ...] = ()
    elif leg == "r1":
        corpus = "data/a0r1"
        manifest = "data/a0r1/manifest.json"
        target = "targets/sealed.jsonl"
        roots = (
            Path("experiments/a0r1-independent-proxy"), Path("data/a0r1/cases.jsonl"),
            Path("data/a0r1/targets/calibration.jsonl"), Path(manifest), Path("results/a0r1/freeze"),
            Path("results/a0r1/a0r1-v1.0.0-e93a9faa-r1"),
        )
        publication_manifest = "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json"
        provenance = {
            "experiments/a0r1-independent-proxy": "experiments/a0r1-independent-proxy/protocol.json",
            "data/a0r1/cases.jsonl": manifest,
            "data/a0r1/targets/calibration.jsonl": manifest,
            manifest: manifest,
            "results/a0r1/freeze": "results/a0r1/freeze/freeze-manifest.json",
            "results/a0r1/a0r1-v1.0.0-e93a9faa-r1": publication_manifest,
        }
        publication = _read_json_object(root / publication_manifest, "A0-R1 publication manifest")
        dense = publication.get("activation_dense")
        if not isinstance(dense, Mapping):
            raise A0XFreezeError("A0-R1 publication manifest lacks external dense asset")
        external_assets = ({
            "path": dense.get("path"),
            "bytes": dense.get("bytes"),
            "sha256": dense.get("sha256"),
            "provenance_manifest": publication_manifest,
        },)
    else:
        raise A0XFreezeError("unknown A0X leg")
    declarations = _sealed_declarations(root, corpus, manifest, target)
    return roots, declarations, provenance, external_assets


def freeze_a0x_campaign(
    root: str | Path,
    *,
    prepare_dossiers: bool,
    implementation_source_head: str,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    """Write the two target-free leg freezes and twelve approval requests.

    The operation reads only public manifests, already-frozen declarations,
    source/test files, and model-card metadata.  It has no model, tokenizer,
    target-content, CCP, subprocess, network, or authorization capability.
    """

    if not isinstance(implementation_source_head, str) or not _REVISION.fullmatch(implementation_source_head):
        raise A0XFreezeError("implementation source head must be an exact revision")
    repository = Path(root).resolve()
    destination = repository if output_root is None else Path(output_root).resolve()
    campaign = repository / "experiments/a0x-six-model"
    output_campaign = destination / "experiments/a0x-six-model"
    material_path = campaign / "material-execution-contract.json"
    material_sha256 = sha256_file(material_path)
    registry = _read_json_object(campaign / "model-registry.json", "A0X model registry")
    cards = _load_model_cards(repository, campaign, registry)
    written: list[str] = []
    bindings: dict[Leg, str] = {}

    for leg in (Leg.A0, Leg.R1):
        spec = _LEG_SOURCES[leg]
        protocol_path = output_campaign / leg.value / "protocol.json"
        implementation_path = output_campaign / leg.value / "implementation.json"
        freeze_path = output_campaign / "freeze" / f"{leg.value}-freeze.json"
        identity = _leg_identity(repository, leg, spec)
        source_protocol_path = str(spec["protocol"])
        source_implementation_path = str(spec["implementation"])
        source_protocol = _read_json_object(repository / source_protocol_path, f"historical {leg.value} protocol")
        source_implementation = _read_json_object(
            repository / source_implementation_path, f"historical {leg.value} implementation",
        )
        protocol = {
            **_COMMON,
            "artifact_class": "a0x-leg-protocol",
            "identity": identity,
            "protocol_status": "frozen",
            "endpoint_indices": [0, 2, 4, 6] if leg is Leg.A0 else [6],
            "descriptive_final_block_endpoint": {
                "model_card_index_field": "final_transformer_block_tuple_index",
                "required_equal_model_card_field": "num_hidden_layers",
                "role": "descriptive_sensitivity",
                "rescues_primary": False,
            },
            "source_protocol_path": source_protocol_path,
            "source_protocol_raw_sha256": sha256_file(repository / source_protocol_path),
            "inherited_rules": _copy_fields(source_protocol, spec["protocol_fields"], f"{leg.value} protocol"),
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
        }
        implementation = {
            **_COMMON,
            "artifact_class": "a0x-leg-implementation",
            "identity": identity,
            "implementation_status": "frozen_before_model_output",
            "source_implementation_path": source_implementation_path,
            "source_implementation_raw_sha256": sha256_file(repository / source_implementation_path),
            "inherited_rules": _copy_fields(
                source_implementation, spec["implementation_fields"], f"{leg.value} implementation",
            ),
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
            "implementation_paths": list(_IMPLEMENTATION_PATHS),
            "implementation_files": [_file_binding(repository, relative) for relative in _IMPLEMENTATION_PATHS],
        }
        _write_json(protocol_path, protocol)
        _write_json(implementation_path, implementation)
        freeze = {
            **_COMMON,
            "artifact_class": "a0x-leg-freeze-manifest",
            "identity": identity,
            "protocol_sha256": sha256_file(protocol_path),
            "implementation_sha256": sha256_file(implementation_path),
            "freeze_status": "frozen",
        }
        _write_json(freeze_path, freeze)
        bindings[leg] = sha256_file(freeze_path)
        written.extend(_relative_paths(destination, (protocol_path, implementation_path, freeze_path)))

    dossier_count = 0
    if prepare_dossiers:
        for leg in (Leg.A0, Leg.R1):
            for card_path, card in cards:
                model_key = str(card.get("model_key"))
                filename = _DOSSIER_FILENAMES.get(model_key)
                if filename is None:
                    raise A0XFreezeError(f"unsupported A0X model key: {model_key}")
                hidden_size = card.get("hidden_size")
                if not isinstance(hidden_size, int) or isinstance(hidden_size, bool):
                    raise A0XFreezeError(f"A0X card lacks hidden size: {model_key}")
                run_id = f"a0x-{leg.value}-{model_key}-{str(card['revision'])[:8]}-attempt-01"
                output_path = f"results/a0x/{leg.value}/{model_key}/{run_id}"
                pair = PairBinding(
                    binding_profile="a0x-pair-scope-v2",
                    leg=leg,
                    leg_freeze_sha256=bindings[leg],
                    model_key=model_key,
                    model_id=str(card["model_id"]),
                    revision=str(card["revision"]),
                    run_id=run_id,
                    output_path=output_path,
                    dense_bound=compute_dense_bound(leg, cases=48, hidden_width=hidden_size),
                ).as_mapping()
                dossier = {
                    **_COMMON,
                    "artifact_class": "a0x-authorization-dossier",
                    "commitment_profile": APPROVAL_DOSSIER_PROFILE,
                    "pair_binding": pair,
                    "dossier_status": "approval_requested",
                    "implementation_source_head": implementation_source_head,
                    "material_contract_path": "experiments/a0x-six-model/material-execution-contract.json",
                    "material_contract_raw_sha256": material_sha256,
                    "runtime_authorization_path": (
                        f".a0x-runtime/authorizations/{leg.value}/{model_key}/{run_id}.json"
                    ),
                }
                dossier_path = output_campaign / "approval-dossiers" / leg.value / filename
                _write_json(dossier_path, dossier)
                written.append(dossier_path.relative_to(destination).as_posix())
                dossier_count += 1

    return {
        "artifact_class": "a0x-freeze-generation-receipt",
        "written": written,
        "frozen_leg_count": 2,
        "dossier_count": dossier_count,
        "sealed_target_content_reads": 0,
        "model_loads": 0,
        "tokenizer_constructions": 0,
        "ccp_invocations": 0,
        "remote_mutations": 0,
    }


def verify_frozen_legs(root: str | Path) -> dict[Leg, LegFreezeBinding]:
    """Verify the frozen leg artifacts and exact source/test bindings read-only."""

    repository = Path(root).resolve()
    campaign = repository / "experiments/a0x-six-model"
    schemas = repository / "schemas"
    protocol_schema = _read_json_object(schemas / "a0x-protocol.schema.json", "A0X protocol schema")
    implementation_schema = _read_json_object(
        schemas / "a0x-implementation.schema.json", "A0X implementation schema",
    )
    freeze_schema = _read_json_object(schemas / "a0x-freeze-manifest.schema.json", "A0X freeze schema")
    bindings: dict[Leg, LegFreezeBinding] = {}
    for leg in (Leg.A0, Leg.R1):
        spec = _LEG_SOURCES[leg]
        protocol_path = campaign / leg.value / "protocol.json"
        implementation_path = campaign / leg.value / "implementation.json"
        freeze_path = campaign / "freeze" / f"{leg.value}-freeze.json"
        protocol = _read_json_object(protocol_path, f"frozen {leg.value} protocol")
        implementation = _read_json_object(implementation_path, f"frozen {leg.value} implementation")
        freeze = _read_json_object(freeze_path, f"frozen {leg.value} manifest")
        for value, schema, label in (
            (protocol, protocol_schema, "protocol"),
            (implementation, implementation_schema, "implementation"),
            (freeze, freeze_schema, "freeze"),
        ):
            issues = validate(value, schema)
            if issues:
                raise A0XFreezeError(f"{leg.value} {label} fails schema: {issues[0].message}")
        if {"protocol_sha256", "leg_freeze_sha256"}.intersection(protocol):
            raise A0XFreezeError(f"{leg.value} protocol contains a self-dependent hash")
        if {"implementation_sha256", "leg_freeze_sha256"}.intersection(implementation):
            raise A0XFreezeError(f"{leg.value} implementation contains a self-dependent hash")
        if "leg_freeze_sha256" in freeze:
            raise A0XFreezeError(f"{leg.value} freeze contains its own hash")
        expected_identity = _leg_identity(repository, leg, spec)
        if protocol.get("identity") != expected_identity or implementation.get("identity") != expected_identity:
            raise A0XFreezeError(f"{leg.value} frozen identity drifted")
        source_protocol = _read_json_object(repository / str(spec["protocol"]), f"historical {leg.value} protocol")
        source_implementation = _read_json_object(
            repository / str(spec["implementation"]), f"historical {leg.value} implementation",
        )
        if (
            protocol.get("source_protocol_path") != spec["protocol"]
            or protocol.get("source_protocol_raw_sha256") != sha256_file(repository / str(spec["protocol"]))
            or protocol.get("inherited_rules")
            != _copy_fields(source_protocol, spec["protocol_fields"], f"{leg.value} protocol")
        ):
            raise A0XFreezeError(f"{leg.value} inherited protocol rules drifted")
        if (
            implementation.get("source_implementation_path") != spec["implementation"]
            or implementation.get("source_implementation_raw_sha256")
            != sha256_file(repository / str(spec["implementation"]))
            or implementation.get("inherited_rules")
            != _copy_fields(source_implementation, spec["implementation_fields"], f"{leg.value} implementation")
        ):
            raise A0XFreezeError(f"{leg.value} inherited implementation rules drifted")
        rows = implementation.get("implementation_files")
        if implementation.get("implementation_paths") != list(_IMPLEMENTATION_PATHS) or not isinstance(rows, list):
            raise A0XFreezeError(f"{leg.value} implementation path binding drifted")
        if rows != [_file_binding(repository, relative) for relative in _IMPLEMENTATION_PATHS]:
            raise A0XFreezeError(f"{leg.value} source/test hash binding drifted")
        try:
            bindings[leg] = build_leg_freeze_binding(protocol_path, implementation_path, freeze_path)
        except Exception as error:
            raise A0XFreezeError(f"{leg.value} freeze binding drifted") from error
    return bindings


def _leg_identity(repository: Path, leg: Leg, spec: Mapping[str, Any]) -> dict[str, str]:
    tree = _read_json_object(repository / str(spec["protected_tree"]), f"{leg.value} protected tree")
    protected_sha = tree.get("protected_tree_sha256")
    if not isinstance(protected_sha, str) or not _SHA256.fullmatch(protected_sha):
        raise A0XFreezeError(f"{leg.value} protected tree lacks its commitment")
    selection_path = repository / str(spec["selection"])
    return {
        "leg": leg.value,
        "protocol_id": f"a0x-{leg.value}-six-model-v1",
        "protected_tree_sha256": protected_sha,
        "selection_corpus_sha256": sha256_file(selection_path),
        "source_base_commit": SOURCE_BASE_COMMIT,
    }


def _copy_fields(source: Mapping[str, Any], fields: object, label: str) -> dict[str, Any]:
    if not isinstance(fields, tuple):
        raise A0XFreezeError(f"{label} field declaration is invalid")
    missing = [field for field in fields if field not in source]
    if missing:
        raise A0XFreezeError(f"{label} is missing inherited fields: {missing}")
    # JSON round-trip prevents accidental shared mutable references and keeps
    # the exact JSON value domain used by the frozen source artifacts.
    return {field: json.loads(json.dumps(source[field])) for field in fields}


def _file_binding(repository: Path, relative: str) -> dict[str, Any]:
    path = repository / relative
    if not path.is_file() or path.is_symlink():
        raise A0XFreezeError(f"implementation binding is unavailable: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _load_model_cards(
    repository: Path, campaign: Path, registry: Mapping[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    declared = registry.get("cards")
    if not isinstance(declared, list) or len(declared) != 6 or len(set(declared)) != 6:
        raise A0XFreezeError("A0X model registry must declare six unique cards")
    cards: list[tuple[str, dict[str, Any]]] = []
    for relative in declared:
        if not isinstance(relative, str):
            raise A0XFreezeError("A0X model card path is invalid")
        path = campaign / _safe_relative(relative, "model card path")
        card = _read_json_object(path, "A0X model card")
        if card.get("card_path") != path.relative_to(repository).as_posix():
            raise A0XFreezeError("A0X model card path binding drifted")
        cards.append((path.relative_to(repository).as_posix(), card))
    return cards


def _relative_paths(repository: Path, paths: Iterable[Path]) -> list[str]:
    return [path.relative_to(repository).as_posix() for path in paths]


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--write-protected-trees", action="store_true")
    parser.add_argument("--write-a0-selection", action="store_true")
    parser.add_argument("--freeze-all", action="store_true")
    parser.add_argument("--prepare-dossiers", action="store_true")
    parser.add_argument("--implementation-source-head")
    args = parser.parse_args(argv)
    repository = Path(args.root).resolve()
    written: list[str] = []
    output_root = repository / "experiments/a0x-six-model"
    if args.write_protected_trees:
        for leg, filename in (("a0", "protected-a0-tree.json"), ("r1", "protected-a0r1-tree.json")):
            roots, declarations, provenance, external_assets = _canonical_tree_inputs(repository, leg)
            tree = build_protected_tree(
                repository, roots=roots, external_assets=external_assets, sealed_target_declarations=declarations,
                provenance_manifests=provenance,
            )
            path = output_root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(tree, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            written.append(path.relative_to(repository).as_posix())
    if args.write_a0_selection:
        selection = build_a0_selection_manifest(
            cases_path=repository / "data/a0/cases.jsonl",
            corpus_manifest_path=repository / "data/a0/manifest.json",
        )
        path = output_root / "a0-selection-manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(selection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path.relative_to(repository).as_posix())
    receipt: dict[str, Any] = {"written": written, "sealed_target_content_reads": 0}
    if args.freeze_all:
        if args.implementation_source_head is None:
            parser.error("--freeze-all requires --implementation-source-head")
        receipt = freeze_a0x_campaign(
            repository,
            prepare_dossiers=args.prepare_dossiers,
            implementation_source_head=args.implementation_source_head,
        )
    elif args.prepare_dossiers:
        parser.error("--prepare-dossiers requires --freeze-all")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
