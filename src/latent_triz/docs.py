from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import os
import posixpath
import re
import stat
import tomllib
from urllib.parse import unquote

from typing import Dict, List, Tuple


REQUIRED_PROFILE_FIELDS = {
    "required_fields",
    "max_verification_age_days",
    "entry_points",
}
ALLOWED_ENTRY_POINT_SUFFIX = ".md"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Mirrors the N3 manifest's distinct dispositions. Keep in sync; tests
# compare these sets to the manifest using path strings only.
A0X_N3_PROTECTED_LINK_PATHS = frozenset(
    {
        "data/a0/procedural-targets/calibration-targets.jsonl",
        "data/a0/sealed-targets/targets.jsonl",
        "data/a0r1/targets/calibration.jsonl",
        "data/a0r1/targets/sealed.jsonl",
    }
)
A0X_N3_EXCLUDED_SENSITIVE_LINK_PATHS = frozenset(
    {
        "experiments/exp001-comparative-reference/additional-model-authorization.json",
        "experiments/exp001-comparative-reference/execution-authorization.json",
        "experiments/exp001-comparative-reference/next-model-authorization.json",
        "experiments/exp001-comparative-reference/qwen-download-authorization.json",
        "experiments/exp001-reference-integrated/execution-authorization.json",
        "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json",
        "results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json",
        "results/a0r2c1/preexecution/sealed-execution-authorization.json",
        "experiments/exp002-auto/combined-target-key-template.json",
        "experiments/exp002-qwen3-followup/transfer-target-key-template.json",
        "results/exp002/preexecution/sealed-key-access-template.json",
        "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/sealed-key-access.json",
        "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/sealed-key-access.json",
        "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/sealed-key-access.json",
    }
)
A0X_N3_DEFERRED_LINK_PATHS = A0X_N3_PROTECTED_LINK_PATHS | A0X_N3_EXCLUDED_SENSITIVE_LINK_PATHS
_A0X_N3_DEFERRED_LINK_DISPOSITIONS_CASEFOLDED = {
    **{path.casefold(): "deferred_protected" for path in A0X_N3_PROTECTED_LINK_PATHS},
    **{
        path.casefold(): "excluded_sensitive_role_unverified"
        for path in A0X_N3_EXCLUDED_SENSITIVE_LINK_PATHS
    },
}
_HAS_SAFE_NOFOLLOW_DIR_FD = (
    hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
    and os.open in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
    and os.stat in os.supports_follow_symlinks
)


@dataclass(frozen=True)
class OkfProfile:
    required_fields: tuple[str, ...]
    max_age_days: int
    entry_points: tuple[str, ...]


@dataclass(frozen=True)
class DocsIssue:
    file: str
    line: int
    code: str
    message: str


@dataclass(frozen=True)
class ParsedFrontmatter:
    path: str
    fields: Dict[str, str]
    field_lines: Dict[str, int]
    end_line: int


def load_profile(profile_path: str) -> OkfProfile:
    try:
        data = Path(profile_path).read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read profile {profile_path}: {exc}") from None

    try:
        document = tomllib.loads(data.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML in profile {profile_path}: {exc}") from None

    if not isinstance(document, dict):
        raise ValueError("profile must be a TOML table")

    profile = document.get("okf", document)
    if not isinstance(profile, dict):
        raise ValueError("profile section 'okf' must be a TOML table")

    if "max_age_days" in profile and "max_verification_age_days" not in profile:
        profile = dict(profile)
        profile["max_verification_age_days"] = profile["max_age_days"]

    missing = REQUIRED_PROFILE_FIELDS - set(profile)
    if missing:
        raise ValueError(f"missing profile fields: {', '.join(sorted(missing))}")

    required_fields = profile["required_fields"]
    if not isinstance(required_fields, list) or not all(isinstance(v, str) for v in required_fields):
        raise ValueError("required_fields must be a list of strings")
    if not required_fields:
        raise ValueError("required_fields must not be empty")

    max_age_days = profile["max_verification_age_days"]
    if not isinstance(max_age_days, int) or max_age_days < 1:
        raise ValueError("max_verification_age_days must be an int greater than 0")

    entry_points_raw = profile["entry_points"]
    if not isinstance(entry_points_raw, list) or not all(isinstance(v, str) for v in entry_points_raw):
        raise ValueError("entry_points must be a list of strings")
    if not entry_points_raw:
        raise ValueError("entry_points must not be empty")
    entry_points: list[str] = []
    for entry_point in entry_points_raw:
        clean = entry_point.strip()
        if not clean:
            raise ValueError("entry_points must not include empty paths")
        if clean.startswith(("/", "\\")):
            raise ValueError(f"absolute entry point is not allowed: {clean}")
        if Path(clean).is_absolute():
            raise ValueError(f"absolute entry point is not allowed: {clean}")
        if clean.startswith("..") or ".." in Path(clean).parts:
            raise ValueError(f"entry point escapes docs root: {clean}")
        if not clean.lower().endswith(ALLOWED_ENTRY_POINT_SUFFIX):
            raise ValueError(f"entry point must be Markdown: {clean}")
        entry_points.append(clean)

    return OkfProfile(
        required_fields=tuple(required_fields),
        max_age_days=max_age_days,
        entry_points=tuple(entry_points),
    )


def audit_docs(profile: OkfProfile, root: Path, as_of: date) -> List[DocsIssue]:
    issues: List[DocsIssue] = []
    canonical_seen: Dict[Tuple[str, str], str] = {}
    canonical_status = "canonical"
    root_path = root.resolve()

    for entry_point in profile.entry_points:
        rel = _normalize_repo_relative_path(entry_point)
        if rel is None:
            issues.append(
                DocsIssue(
                    file=entry_point.replace("\\", "/"),
                    line=1,
                    code="DOCS_ROOT_ESCAPE",
                    message=f"entry point escapes repository root: {entry_point}",
                )
            )
            continue

        entry_disposition = _deferred_link_disposition(rel)
        if entry_disposition is not None:
            if entry_disposition == "deferred_protected":
                code = "DOCS_ENTRY_POINT_DEFERRED_PROTECTED"
                message = "deferred_protected / UNVERIFIED: entry point was not resolved or inspected"
            else:
                code = "DOCS_ENTRY_POINT_EXCLUDED_SENSITIVE_UNVERIFIED"
                message = "excluded_sensitive_role_unverified / UNVERIFIED: entry point was not resolved or inspected"
            issues.append(
                DocsIssue(
                    file=rel,
                    line=1,
                    code=code,
                    message=message,
                )
            )
            continue

        entry_status, text = _inspect_repo_file(root_path, rel, read_contents=True)
        if entry_status == "missing":
            issues.append(
                DocsIssue(
                    file=rel,
                    line=1,
                    code="PROFILE_MISSING_ENTRY",
                    message=f"entry point missing: {entry_point}",
                )
            )
            continue
        if entry_status != "ok" or text is None:
            issues.append(
                DocsIssue(
                    file=rel,
                    line=1,
                    code="DOCS_ENTRY_POINT_UNVERIFIED",
                    message="UNVERIFIED: entry point could not be opened without following a filesystem link",
                )
            )
            continue

        path = root_path.joinpath(*rel.split("/"))

        reserved_nested_index = rel.endswith("/index.md") and rel != "docs/index.md"
        frontmatter, fm_issues = _parse_frontmatter(rel, text)
        if reserved_nested_index and frontmatter is None and any(issue.code == "DOCS_MISSING_FRONTMATTER" for issue in fm_issues):
            fm_issues = []
        issues.extend(fm_issues)

        if frontmatter is None:
            if reserved_nested_index:
                issues.extend(_validate_markdown_links(path, rel, root_path, text))
            continue

        for field in profile.required_fields:
            if field not in frontmatter.fields or frontmatter.fields[field] == "":
                line = frontmatter.field_lines.get(field, frontmatter.end_line)
                issues.append(
                    DocsIssue(
                        file=rel,
                        line=line,
                        code="DOCS_MISSING_FIELD",
                        message=f"missing required field in frontmatter: {field}",
                    )
                )

        last_verified = frontmatter.fields.get("last_verified")
        if last_verified is not None:
            _validate_last_verified(
                rel,
                frontmatter.field_lines.get("last_verified", frontmatter.end_line),
                last_verified,
                profile,
                as_of,
                issues,
            )

        if frontmatter.fields.get("status") == canonical_status:
            type_value = frontmatter.fields.get("type")
            if type_value:
                key = (canonical_status, type_value)
                if key in canonical_seen:
                    issues.append(
                        DocsIssue(
                            file=rel,
                            line=frontmatter.field_lines.get("type", frontmatter.end_line),
                            code="DOCS_DUP_CANONICAL_TYPE",
                            message=f"duplicate canonical type '{type_value}' also used by {canonical_seen[key]}",
                        )
                    )
                else:
                    canonical_seen[key] = rel

        issues.extend(_validate_markdown_links(path, rel, root_path, text))

    issues.sort(key=lambda item: (item.file, item.line, item.code, item.message))
    return issues


def _parse_frontmatter(path: str, text: str) -> tuple[ParsedFrontmatter | None, List[DocsIssue]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, [
            DocsIssue(
                file=path,
                line=1,
                code="DOCS_MISSING_FRONTMATTER",
                message="missing YAML frontmatter block",
            )
        ]

    try:
        end_index = lines[1:].index("---") + 2
    except ValueError:
        return None, [
            DocsIssue(
                file=path,
                line=1,
                code="DOCS_UNTERMINATED_FRONTMATTER",
                message="unterminated YAML frontmatter block",
            )
        ]

    fields: Dict[str, str] = {}
    field_lines: Dict[str, int] = {}
    for idx in range(1, end_index - 1):
        raw = lines[idx].strip()
        if raw == "" or raw.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", raw)
        if match:
            key, value = match.groups()
            fields[key] = value.strip()
            field_lines[key] = idx + 1
    return ParsedFrontmatter(path=path, fields=fields, field_lines=field_lines, end_line=end_index), []


def _validate_last_verified(
    path: str,
    line: int,
    value: str,
    profile: OkfProfile,
    as_of: date,
    issues: List[DocsIssue],
) -> None:
    if not DATE_PATTERN.match(value):
        issues.append(
            DocsIssue(
                file=path,
                line=line,
                code="DOCS_LAST_VERIFIED_FORMAT",
                message=f"invalid last_verified date: {value}",
            )
        )
        return
    try:
        verified = date.fromisoformat(value)
    except ValueError:
        issues.append(
            DocsIssue(
                file=path,
                line=line,
                code="DOCS_LAST_VERIFIED_FORMAT",
                message=f"invalid last_verified date: {value}",
            )
        )
        return
    if verified > as_of:
        issues.append(
            DocsIssue(
                file=path,
                line=line,
                code="DOCS_LAST_VERIFIED_FUTURE",
                message="last_verified is in the future",
            )
        )
        return
    age = (as_of - verified).days
    if age > profile.max_age_days:
        issues.append(
            DocsIssue(
                file=path,
                line=line,
                code="DOCS_LAST_VERIFIED_STALE",
                message=f"last_verified is stale by {age} days",
            )
        )


def _normalize_repo_relative_path(raw_path: str) -> str | None:
    try:
        normalized = posixpath.normpath(unquote(raw_path, errors="strict").replace("\\", "/"))
    except UnicodeError:
        return None
    if (
        not normalized
        or normalized in {".", ".."}
        or normalized.startswith("../")
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
    ):
        return None
    return normalized


def _normalize_link_target(root: Path, source_rel: str, target_path: str) -> str | None:
    try:
        decoded = unquote(target_path, errors="strict").replace("\\", "/")
    except UnicodeError:
        return None

    if re.match(r"^[A-Za-z]:", decoded):
        return None
    if decoded.startswith("/"):
        root_text = posixpath.normpath(root.as_posix())
        target_text = posixpath.normpath(decoded)
        if target_text == root_text:
            candidate = "."
        elif target_text.startswith(root_text.rstrip("/") + "/"):
            candidate = posixpath.relpath(target_text, root_text)
        else:
            return None
    else:
        candidate = posixpath.normpath(
            posixpath.join(posixpath.dirname(source_rel.replace("\\", "/")), decoded)
        )

    if candidate in {".", ".."} or candidate.startswith("../") or candidate.startswith("/"):
        return None
    return candidate


def _is_deferred_link_path(repo_relative_path: str) -> bool:
    return _deferred_link_disposition(repo_relative_path) is not None


def _deferred_link_disposition(repo_relative_path: str) -> str | None:
    folded = posixpath.normpath(repo_relative_path.replace("\\", "/")).casefold()
    for blocked, disposition in _A0X_N3_DEFERRED_LINK_DISPOSITIONS_CASEFOLDED.items():
        if folded == blocked or folded.startswith(blocked + "/"):
            return disposition
    return None


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _inspect_repo_file(
    root: Path,
    repo_relative_path: str,
    *,
    read_contents: bool,
) -> tuple[str, str | None]:
    """Inspect a public repository file without following symlink components."""
    if not _HAS_SAFE_NOFOLLOW_DIR_FD:
        return "unverified", None

    parts = repo_relative_path.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return "unverified", None

    root_fd: int | None = None
    current_fd: int | None = None
    file_fd: int | None = None
    try:
        root_fd = os.open(
            os.fspath(root),
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        current_fd = root_fd

        for component in parts[:-1]:
            observed = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            if stat.S_ISLNK(observed.st_mode):
                return "unverified", None
            if not stat.S_ISDIR(observed.st_mode):
                return "missing", None
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=current_fd,
            )
            opened = os.fstat(child_fd)
            if not stat.S_ISDIR(opened.st_mode) or not _same_file_identity(observed, opened):
                os.close(child_fd)
                return "unverified", None
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = child_fd

        leaf = parts[-1]
        observed = os.stat(leaf, dir_fd=current_fd, follow_symlinks=False)
        if stat.S_ISLNK(observed.st_mode):
            return "unverified", None
        if not stat.S_ISREG(observed.st_mode):
            return "missing", None
        if observed.st_nlink != 1:
            return "unverified", None
        if not read_contents:
            return "ok", None

        file_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current_fd)
        opened = os.fstat(file_fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not _same_file_identity(observed, opened)
        ):
            return "unverified", None
        with os.fdopen(file_fd, "rb") as handle:
            file_fd = None
            return "ok", handle.read().decode("utf-8")
    except FileNotFoundError:
        return "missing", None
    except (OSError, ValueError, UnicodeError):
        return "unverified", None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if current_fd is not None and current_fd != root_fd:
            os.close(current_fd)
        if root_fd is not None:
            os.close(root_fd)


def _validate_markdown_links(
    path: Path,
    rel: str,
    root: Path,
    text: str,
) -> List[DocsIssue]:
    issues: List[DocsIssue] = []
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

    lines = text.splitlines()
    in_fence: str | None = None
    for line_no, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        fence = _fence_token(line)
        if fence is not None:
            if in_fence is None:
                in_fence = fence
            elif in_fence == fence:
                in_fence = None
            continue
        if in_fence is not None:
            continue

        for match in link_re.findall(line):
            target = match.strip()
            if _is_external(target):
                continue

            target_path, anchor = _split_link_target(target)
            if target_path is None and not anchor:
                continue

            repo_relative_path = (
                _normalize_repo_relative_path(rel)
                if target_path is None
                else _normalize_link_target(root, rel, target_path)
            )
            if repo_relative_path is None:
                issues.append(
                    DocsIssue(
                        file=rel,
                        line=line_no,
                        code="DOCS_ROOT_ESCAPE",
                        message=f"link escapes docs root: {target}",
                    )
                )
                continue

            link_disposition = _deferred_link_disposition(repo_relative_path)
            if link_disposition is not None:
                if link_disposition == "deferred_protected":
                    code = "DOCS_LINK_TARGET_DEFERRED_PROTECTED"
                    message = "deferred_protected / UNVERIFIED: N3 target was not resolved or inspected"
                else:
                    code = "DOCS_LINK_TARGET_EXCLUDED_SENSITIVE_UNVERIFIED"
                    message = "excluded_sensitive_role_unverified / UNVERIFIED: N3 target was not resolved or inspected"
                issues.append(
                    DocsIssue(
                        file=rel,
                        line=line_no,
                        code=code,
                        message=message,
                    )
                )
                continue

            target_status, target_text = (
                ("ok", text)
                if target_path is None
                else _inspect_repo_file(
                    root,
                    repo_relative_path,
                    read_contents=bool(anchor),
                )
            )
            if target_status == "missing":
                issues.append(
                    DocsIssue(
                        file=rel,
                        line=line_no,
                        code="DOCS_LINK_TARGET_MISSING",
                        message=f"missing link target: {target_path or path.name}",
                    )
                )
                continue
            if target_status != "ok" or (anchor and target_text is None):
                issues.append(
                    DocsIssue(
                        file=rel,
                        line=line_no,
                        code="DOCS_LINK_TARGET_UNVERIFIED",
                        message="UNVERIFIED: target could not be classified without following a filesystem link",
                    )
                )
                continue

            if anchor:
                if anchor not in _collect_heading_anchors(target_text):
                    issues.append(
                        DocsIssue(
                            file=rel,
                            line=line_no,
                            code="DOCS_LINK_ANCHOR_MISSING",
                            message=f"missing link anchor: {anchor}",
                        )
                    )

    return issues


def _split_link_target(raw: str) -> tuple[str | None, str | None]:
    if "#" not in raw:
        return raw, None
    path_text, anchor = raw.split("#", 1)
    anchor = anchor.strip()
    if path_text == "":
        return None, _normalize_anchor(anchor)
    return path_text.strip(), _normalize_anchor(anchor)


def _is_external(raw: str) -> bool:
    lowered = raw.lower()
    return lowered.startswith(("http://", "https://", "ftp://", "mailto:", "//"))


def _normalize_anchor(anchor: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", anchor.strip().lower()))).strip("-")


def _collect_heading_anchors(text: str) -> set[str]:
    anchor_re = re.compile(r"^#{1,6}\s+(.+)$")
    headings: set[str] = set()
    for line in text.splitlines():
        match = anchor_re.match(line.strip())
        if match:
            headings.add(_normalize_anchor(match.group(1)))
    return headings


def _fence_token(line: str) -> str | None:
    if line.startswith("```"):
        return "```"
    if line.startswith("~~~"):
        return "~~~"
    return None
