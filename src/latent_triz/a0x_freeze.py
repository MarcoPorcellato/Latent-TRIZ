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

from .a0x_contract import canonical_json_sha256, sha256_file


class A0XFreezeError(ValueError):
    """Raised when a protected input or target-free selection cannot be frozen."""


SOURCE_BASE_COMMIT = "188eb65b5e249923baddadeba52659f07fcd1609"
FROZEN_DOMAINS = ("agriculture", "energy", "manufacturing", "medicine", "software", "transport")
SELECTION_PATH = "experiments/a0x-six-model/a0-selection-manifest.json"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SAFE_RELATIVE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._/-]+$")
_COMMON = {
    "empirical": True,
    "scientific_status": "exploratory",
    "evidence_eligible": False,
    "expert_validated": False,
    "claim_ids": [],
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
    path = repository / relative
    resolved = path.resolve()
    if not resolved.is_relative_to(repository):
        raise A0XFreezeError(f"path escapes protected root: {relative}")
    return path


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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--write-protected-trees", action="store_true")
    parser.add_argument("--write-a0-selection", action="store_true")
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
    print(json.dumps({"written": written, "sealed_target_content_reads": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
