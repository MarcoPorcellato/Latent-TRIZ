"""Fail-closed path classification and artifact checks for pull requests."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


DOC_ROOT_FILES = {
    "CITATION.cff", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "LICENSE",
    "NOTICE", "README.md", "SECURITY.md",
}
GOVERNANCE_ROOT_FILES = {
    ".commit-ci-policy.toml", ".commit-ci-preflight.toml", ".gitignore",
    "Makefile", "pyproject.toml",
}
CODE_PREFIXES = ("schemas/", "scripts/", "src/", "tests/")
RUNTIME_PREFIXES = ("containers/",)
RUNTIME_ROOT_FILES = {".dockerignore"}
SCIENTIFIC_PREFIXES = (
    "artifacts/", "data/", "experiments/", "preregistrations/", "results/",
)
MODEL_BACKED_PREFIXES = (
    "artifacts/models/",
    "results/lab01/model-anatomy/",
    "results/lab01/model-representations/",
)
DENSE_ARTIFACT_SUFFIXES = {
    ".bin", ".npy", ".npz", ".onnx", ".pt", ".pth", ".safetensors",
}
AUDITED_TEXT_SUFFIXES = {
    ".csv", ".html", ".json", ".jsonl", ".md", ".toml", ".tsv", ".txt",
    ".yaml", ".yml",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_AUDITED_ARTIFACT_BYTES = 10 * 1024 * 1024


class MergePolicyError(ValueError):
    """Raised when pull-request metadata or an artifact fails closed."""


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str = "modified"


@dataclass(frozen=True)
class PolicyDecision:
    categories: tuple[str, ...]
    docs_only: bool
    require_repository_check: bool
    require_python_311: bool
    require_ccp: bool
    require_scientific_audit: bool
    require_model_artifact_audit: bool
    paths: tuple[str, ...]


def _normalize_path(raw_path: str) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise MergePolicyError("changed file path must be a non-empty string")
    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or "\x00" in raw_path:
        raise MergePolicyError(f"unsafe changed file path: {raw_path!r}")
    normalized = path.as_posix()
    if normalized in {".", ""}:
        raise MergePolicyError(f"unsafe changed file path: {raw_path!r}")
    return normalized


def _flatten_file_payload(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, list):
        raise MergePolicyError("GitHub files payload must be an array")
    flattened: list[Mapping[str, Any]] = []
    for item in payload:
        if isinstance(item, list):
            flattened.extend(_flatten_file_payload(item))
        elif isinstance(item, Mapping):
            flattened.append(item)
        else:
            raise MergePolicyError("GitHub files payload contains a non-object entry")
    return flattened


def load_changed_files(path: Path) -> list[ChangedFile]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    changed: list[ChangedFile] = []
    for entry in _flatten_file_payload(payload):
        filename = entry.get("filename")
        status = entry.get("status", "modified")
        if not isinstance(status, str) or not status:
            raise MergePolicyError("changed file status must be a non-empty string")
        changed.append(ChangedFile(_normalize_path(filename), status))
    if not changed:
        raise MergePolicyError("pull request has no changed files")
    return changed


def _is_requirement(path: str) -> bool:
    return path.startswith("requirements-") and path.endswith((".in", ".lock", ".txt"))


def _categories_for_path(path: str) -> set[str]:
    categories: set[str] = set()
    if path.startswith("docs/") or path in DOC_ROOT_FILES:
        categories.add("docs")
    if path.startswith(".github/") or path in GOVERNANCE_ROOT_FILES:
        categories.add("governance")
    if path.startswith(CODE_PREFIXES) or path in {"Makefile", "pyproject.toml"} or _is_requirement(path):
        categories.add("code")
    if path.startswith(RUNTIME_PREFIXES) or path in RUNTIME_ROOT_FILES:
        categories.add("runtime")
    if path.startswith(SCIENTIFIC_PREFIXES):
        categories.add("scientific")
    if path.startswith(MODEL_BACKED_PREFIXES) or PurePosixPath(path).suffix.lower() in DENSE_ARTIFACT_SUFFIXES:
        categories.update(("model_backed", "scientific"))
    if not categories:
        categories.add("unknown")
    return categories


def classify_paths(files: Iterable[ChangedFile | str]) -> PolicyDecision:
    normalized_files: list[ChangedFile] = []
    categories: set[str] = set()
    for item in files:
        changed = item if isinstance(item, ChangedFile) else ChangedFile(str(item))
        normalized = ChangedFile(_normalize_path(changed.path), changed.status)
        normalized_files.append(normalized)
        categories.update(_categories_for_path(normalized.path))
    if not normalized_files:
        raise MergePolicyError("pull request has no changed files")

    docs_only = categories == {"docs"}
    scientific = "scientific" in categories
    model_backed = "model_backed" in categories
    require_python_311 = bool(
        categories.intersection({"code", "governance", "runtime", "unknown"})
    )
    return PolicyDecision(
        categories=tuple(sorted(categories)),
        docs_only=docs_only,
        require_repository_check=not docs_only,
        require_python_311=require_python_311,
        require_ccp=False,
        require_scientific_audit=scientific or "unknown" in categories,
        require_model_artifact_audit=model_backed,
        paths=tuple(sorted(item.path for item in normalized_files)),
    )


def _load_json_lines(path: Path) -> None:
    records = 0
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError as error:
            raise MergePolicyError(
                f"{path}: invalid JSONL at line {line_number}: {error.msg}"
            ) from error
        records += 1
    if records == 0:
        raise MergePolicyError(f"{path}: JSONL artifact contains no records")


def audit_scientific_artifacts(
    repository: Path, files: Sequence[ChangedFile]
) -> dict[str, Any]:
    root = repository.resolve()
    decision = classify_paths(files)
    audited: list[str] = []
    selected: list[ChangedFile] = []
    model_hash_receipt_found = False
    for changed in files:
        path = changed.path
        categories = _categories_for_path(path)
        if not categories.intersection({"scientific", "model_backed", "unknown"}):
            continue
        selected.append(changed)
        if changed.status == "removed":
            continue
        candidate = repository / path
        if candidate.is_symlink():
            raise MergePolicyError(f"scientific artifact must not be a symlink: {path}")
        try:
            candidate.resolve().relative_to(root)
        except ValueError as error:
            raise MergePolicyError(f"scientific artifact escapes repository: {path}") from error
        if not candidate.is_file():
            raise MergePolicyError(f"changed scientific artifact is missing: {path}")
        if candidate.stat().st_size > MAX_AUDITED_ARTIFACT_BYTES:
            raise MergePolicyError(
                f"scientific artifact exceeds the 10 MiB audit limit: {path}"
            )

        suffix = candidate.suffix.lower()
        if suffix in DENSE_ARTIFACT_SUFFIXES:
            raise MergePolicyError(
                f"dense model artifact must be external and hash-referenced, not committed: {path}"
            )
        if suffix not in AUDITED_TEXT_SUFFIXES:
            raise MergePolicyError(
                f"unsupported scientific artifact type requires explicit policy: {path}"
            )
        if suffix == ".json":
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            model_hash_receipt_found = model_hash_receipt_found or _contains_sha256(payload)
        elif suffix == ".jsonl":
            _load_json_lines(candidate)
            for line in candidate.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    model_hash_receipt_found = (
                        model_hash_receipt_found or _contains_sha256(json.loads(line))
                    )
        else:
            candidate.read_text(encoding="utf-8")
        audited.append(path)

    if decision.require_scientific_audit and not audited and not all(
        changed.status == "removed" for changed in selected
    ):
        raise MergePolicyError("scientific audit selected but no changed artifact was audited")
    selected_are_removals = bool(selected) and all(
        changed.status == "removed" for changed in selected
    )
    if (
        decision.require_model_artifact_audit
        and not selected_are_removals
        and not model_hash_receipt_found
    ):
        raise MergePolicyError(
            "model-backed changes require a changed JSON or JSONL receipt containing a SHA-256"
        )
    return {
        "status": "pass",
        "audited_paths": sorted(audited),
        "model_artifact_gate": (
            "pass" if decision.require_model_artifact_audit else "not_required"
        ),
    }


def _contains_sha256(payload: Any) -> bool:
    if isinstance(payload, str):
        return bool(SHA256_PATTERN.fullmatch(payload))
    if isinstance(payload, Mapping):
        return any(_contains_sha256(value) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_sha256(value) for value in payload)
    return False


def _write_github_outputs(path: Path, decision: PolicyDecision) -> None:
    payload = asdict(decision)
    keys = (
        "docs_only", "require_repository_check", "require_python_311",
        "require_ccp", "require_scientific_audit",
        "require_model_artifact_audit",
    )
    lines = [f"{key}={str(payload[key]).lower()}" for key in keys]
    lines.append(f"categories={','.join(decision.categories)}")
    with path.open("a", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    classify = subparsers.add_parser("classify")
    classify.add_argument("--files-json", type=Path, required=True)
    classify.add_argument("--github-output", type=Path)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--files-json", type=Path, required=True)
    audit.add_argument("--repository", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    files = load_changed_files(args.files_json)
    if args.command == "classify":
        decision = classify_paths(files)
        if args.github_output:
            _write_github_outputs(args.github_output, decision)
        print(json.dumps(asdict(decision), sort_keys=True, separators=(",", ":")))
        return 0
    result = audit_scientific_artifacts(args.repository, files)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
