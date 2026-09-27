"""Deterministic, read-only data access for the local research observatory.

Only paths in ``SOURCE_FAMILIES`` are opened. In particular, result payloads,
response indexes, sealed targets, and model assets are never traversed.
"""

from __future__ import annotations

import hashlib
import json
import errno
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any


SOURCE_FAMILIES: dict[str, str] = {
    **{
        path: "selected_docs"
        for path in (
            "docs/ARTICLE.md",
            "docs/HYPOTHESES_AND_FALSIFICATION.md",
            "docs/EVIDENCE_LADDER.md",
            "docs/LABORATORY_MASTER_PLAN.md",
            "docs/ROADMAP.md",
            "docs/LAB_SUITE.md",
            *(f"docs/LAB{i:02}.md" for i in range(1, 7)),
            "docs/decisions/index.md",
            *(f"docs/decisions/{name}" for name in (
                "0001-official-lab-foundation.md",
                "0002-stage1-blinded-pilot.md",
                "0003-exp-001-model-selection.md",
                "0004-lab01-model-anatomy.md",
                "0005-lab02-dataset-anatomy.md",
                "0006-lab03-behavioral-baselines.md",
                "0007-lab04-decodability.md",
                "0008-local-visual-laboratory-suite.md",
                "0009-lab05-candidate-directions.md",
            )),
        )
    },
    "docs/README.md": "navigation_snapshot",
    "docs/CURRENT_STATUS.md": "navigation_snapshot",
    "results/README.md": "navigation_snapshot",
    "data/claims.jsonl": "formal_claims",
    "schemas/claim.schema.json": "formal_claims",
    "data/triz-reference-sources.json": "triz_reference",
    "data/triz-consulting-web-corpus.json": "triz_reference",
    "experiments/a0-automated-weak-proxy/protocol.json": "study_protocol",
    "experiments/a0r1-independent-proxy/protocol.json": "study_protocol",
    "experiments/a0r2-independent-model/study-protocol.json": "study_protocol",
    "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json": "a0",
    "results/a0/a0-v1.0.3-e93a9faa/report.html": "a0",
    "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json": "a0_r1",
    "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/report.md": "a0_r1",
    "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/publication-manifest.json": "a0_r2_c3",
    "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/report.md": "a0_r2_c3",
    "results/exp001-comparative/smollm2-135m-93efa2f0-smollm2-135m-20260819-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/smollm2-135m-93efa2f0-smollm2-135m-20260819-01/report.md": "exp001_comparative",
    "results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/report.md": "exp001_comparative",
    "results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01/report.md": "exp001_comparative",
    "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/report.md": "exp001_comparative",
    "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/report.md": "exp001_comparative",
    "results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01/report.md": "exp001_comparative",
    "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/publication-manifest.json": "exp001_comparative",
    "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/report.md": "exp001_comparative",
    "results/exp002/huggingfacetb-smollm2-135m/exp002-smollm2-135m-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/huggingfacetb-smollm2-135m/exp002-smollm2-135m-exp002a-20260820-01/report.md": "exp002_baseline",
    "results/exp002/eleutherai-pythia-70m-deduped/exp002-pythia-70m-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/eleutherai-pythia-70m-deduped/exp002-pythia-70m-exp002a-20260820-01/report.md": "exp002_baseline",
    "results/exp002/openai-community-gpt2/exp002-gpt2-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/openai-community-gpt2/exp002-gpt2-exp002a-20260820-01/report.md": "exp002_baseline",
    "results/exp002/eleutherai-gpt-neo-125m/exp002-gpt-neo-125m-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/eleutherai-gpt-neo-125m/exp002-gpt-neo-125m-exp002a-20260820-01/report.md": "exp002_baseline",
    "results/exp002/huggingfacetb-smollm2-360m/exp002-smollm2-360m-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/huggingfacetb-smollm2-360m/exp002-smollm2-360m-exp002a-20260820-01/report.md": "exp002_baseline",
    "results/exp002/qwen-qwen2-5-0-5b/exp002-qwen2-5-0-5b-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/qwen-qwen2-5-0-5b/exp002-qwen2-5-0-5b-exp002a-20260820-01/report.md": "exp002_baseline",
    "results/exp002/qwen-qwen3-0-6b-base/exp002-qwen3-0-6b-exp002a-20260820-01/publication-manifest.json": "exp002_baseline",
    "results/exp002/qwen-qwen3-0-6b-base/exp002-qwen3-0-6b-exp002a-20260820-01/report.md": "exp002_baseline",
}

CAMPAIGNS = (
    "A0",
    "A0-R1",
    "A0-R2-C3",
    "EXP-001 comparative",
    "EXP-002A baseline",
)
MODEL_NAMES = (
    "EleutherAI/gpt-neo-125m",
    "EleutherAI/pythia-70m-deduped",
    "HuggingFaceTB/SmolLM2-135M",
    "HuggingFaceTB/SmolLM2-360M",
    "Qwen/Qwen2.5-0.5B",
    "Qwen/Qwen3-0.6B-Base",
    "openai-community/gpt2",
)
STATUSES = {
    "positive": "positive_exploratory_proxy",
    "auto_proxy_signal": "auto_proxy_signal",
    "null": "null",
    "failed": "failed",
    "unavailable": "unavailable",
    "descriptive": "descriptive",
    "recovered_unbound": "recovered_unbound",
}
CLAIM_STATUSES = {
    "untested", "in-progress", "preliminary", "supported", "weakened",
    "falsified", "retracted",
}
CLAIM_LEVELS = {f"E{i}" for i in range(7)}
CLAIM_TRACKS = {"pretrained", "controlled-emergence", "cross-track"}
CLAIM_FIELDS = {
    "claim_id", "statement", "principle", "track", "model_scope", "status",
    "evidence_level", "falsification_condition", "preregistrations",
    "dataset_snapshots", "experiments", "results", "replications",
    "non_empirical", "evidence_profile", "last_verified",
}

_DECISION_PATHS = tuple(
    path for path, family in SOURCE_FAMILIES.items()
    if family == "selected_docs" and re.fullmatch(r"docs/decisions/000[1-9]-.*\.md", path)
)
_CAMPAIGN_SOURCE_PATHS: dict[str, tuple[str, ...]] = {
    "EXP-001 comparative": tuple(
        path for path, family in SOURCE_FAMILIES.items()
        if family == "exp001_comparative" and path.endswith("publication-manifest.json")
    ),
    "EXP-002A baseline": tuple(
        path for path, family in SOURCE_FAMILIES.items()
        if family == "exp002_baseline" and path.endswith("publication-manifest.json")
    ),
}


def resolve_repository_root(app_file: Path) -> Path:
    """Resolve the documented optional-tool layout, refusing an invalid checkout."""
    app_path = Path(os.path.abspath(app_file))
    if app_path.name != "app.py" or app_path.parent.name != "research_observatory" or app_path.parent.parent.name != "tools":
        raise ValueError("Observatory app is outside its documented repository layout")
    root = app_path.parents[2]
    for marker in (app_path, root / "pyproject.toml", root / "docs/ARTICLE.md"):
        try:
            mode = marker.lstat()
        except OSError as exc:
            raise ValueError(f"Missing repository marker: {marker.name}") from exc
        if not stat.S_ISREG(mode.st_mode) or mode.st_nlink != 1:
            raise ValueError(f"Unsafe repository marker: {marker.name}")
    return root


def load_observatory(repo_root: Path, *, strict_public: bool = False) -> dict[str, Any]:
    """Load the explicit public-source catalogue and categorical evidence model."""
    root = Path(repo_root)
    warnings: list[str] = []
    vcs_by_path = _git_vcs_states(root, warnings)
    if strict_public:
        unapproved = [path for path, state in vcs_by_path.items() if state != "tracked_clean"]
        if unapproved:
            raise PermissionError(
                "Public observatory refuses sources without clean Git provenance: "
                + ", ".join(unapproved[:3])
            )
    bytes_by_path: dict[str, bytes | None] = {
        path: _read_allowlisted(root, path) for path in SOURCE_FAMILIES
    }
    source_records = _build_source_records(bytes_by_path)
    source_by_path = {source["path"]: source for source in source_records}
    for source in source_records:
        for marker in source["stale_markers"]:
            warnings.append(f"Known stale source {source['path']}: {marker}")
    if strict_public:
        inventory = read_source_inventory(Path(__file__).with_name("source-inventory.json"))
        validate_source_inventory(source_records, inventory)
    for source in source_records:
        source["vcs_state"] = vcs_by_path[source["path"]]
        source["source_scope"] = "local checkout file; publication is not implied"

    invalid_manifests, mismatched_reports = _validate_report_bindings(bytes_by_path, warnings)
    for manifest_path in invalid_manifests:
        manifest_source = source_by_path.get(manifest_path)
        if manifest_source is not None:
            if manifest_source["freshness"] != "missing":
                manifest_source["freshness"] = "hash_mismatch"
            manifest_source["conflict_markers"].append("publication report binding missing or invalid")
    claims = _extract_claims(bytes_by_path.get("data/claims.jsonl"), warnings)
    decisions = _extract_decisions(root, bytes_by_path, warnings)
    observations = _extract_observations(
        root, bytes_by_path, warnings, invalid_manifests
    )

    missing = sum(source["freshness"] == "missing" for source in source_records)
    if missing:
        warnings.append(f"{missing} allowlisted sources missing; see source freshness fields.")
    for manifest_path, report_path, _expected_hash in mismatched_reports:
        report_source = source_by_path.get(report_path)
        if report_source is not None:
            report_source["freshness"] = "hash_mismatch"
            report_source["conflict_markers"].append(
                f"hash differs from {manifest_path} publication binding"
            )
        warnings.append(f"Local report hash conflicts with publication manifest: {report_path}")

    source_identity = json.dumps(
        [(item["path"], item["sha256"]) for item in source_records],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    head, tree = _git_source_identity(root)
    return {
        "claims": claims,
        "observations": observations,
        "decisions": decisions,
        "sources": source_records,
        "warnings": warnings,
        "model_names": list(MODEL_NAMES),
        "campaign_names": list(CAMPAIGNS),
        "snapshot_sha256": hashlib.sha256(source_identity).hexdigest(),
        "source_head": head,
        "source_tree": tree,
    }


def validate_source_inventory(records: list[dict[str, Any]], inventory: Any) -> None:
    """Refuse source additions or byte drift from the reviewed public inventory."""
    if not isinstance(inventory, dict) or inventory.get("schema") != "research-observatory-source-inventory-v1":
        raise PermissionError("Public source inventory schema mismatch")
    entries = inventory.get("entries")
    if not isinstance(entries, list) or len(entries) != len(records):
        raise PermissionError("Public source inventory cardinality mismatch")
    expected = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "family", "sha256"}:
            raise PermissionError("Public source inventory entry schema mismatch")
        path = entry["path"]
        if not isinstance(path, str) or path in expected:
            raise PermissionError("Public source inventory has duplicate or malformed paths")
        expected[path] = (entry["family"], entry["sha256"])
    observed = {item["path"]: (item["family"], item["sha256"]) for item in records}
    if observed != expected or any(sha is None for _family, sha in observed.values()):
        raise PermissionError("Public source inventory differs from local source bytes")


def read_source_inventory(path: Path) -> dict[str, Any]:
    """Read a bounded independent inventory without following a final symlink."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise PermissionError("No-follow inventory reads are unavailable")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise PermissionError("Unable to open public source inventory safely") from exc
    with os.fdopen(fd, "rb") as source:
        file_stat = os.fstat(source.fileno())
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1 or file_stat.st_size > 65536:
            raise PermissionError("Public source inventory is not an independent bounded file")
        payload = source.read(65537)
    if len(payload) > 65536:
        raise PermissionError("Public source inventory exceeded its size limit")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PermissionError("Public source inventory is malformed") from exc
    if not isinstance(value, dict):
        raise PermissionError("Public source inventory must be an object")
    return value


def _git_source_identity(root: Path) -> tuple[str | None, str | None]:
    values = []
    for ref in ("HEAD", "HEAD^{tree}"):
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--verify", ref],
                check=False, capture_output=True, timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None, None
        value = result.stdout.decode("ascii", errors="ignore").strip()
        if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40,64}", value):
            return None, None
        values.append(value)
    return values[0], values[1]


def read_allowed_preview(
    repo_root: Path, path: str, *, max_chars: int = 1200,
    expected_sha256: str | None = None,
) -> str:
    """Return a bounded excerpt for one exact allowlisted public source path."""
    if path not in SOURCE_FAMILIES:
        raise PermissionError(f"Source is not allowlisted: {path}")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or not 0 <= max_chars <= 12000:
        raise ValueError("max_chars must be an integer from 0 through 12000")
    payload = _read_allowlisted(Path(repo_root), path)
    if payload is None:
        return ""
    if expected_sha256 is not None:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise ValueError("expected_sha256 must be a lowercase SHA-256 digest")
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise PermissionError(f"Source changed since catalogue snapshot: {path}")
    return payload.decode("utf-8", errors="replace")[:max_chars]


def _read_allowlisted(
    root: Path, relative: str, *, max_bytes: int | None = None
) -> bytes | None:
    """Read one exact regular file with descriptor-relative no-follow opens."""
    if relative not in SOURCE_FAMILIES:
        raise PermissionError(f"Source is not allowlisted: {relative}")
    parts = Path(relative).parts
    if not parts or any(part in {".", ".."} for part in parts):
        raise PermissionError(f"Invalid allowlisted path: {relative}")
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise OSError("Secure descriptor-relative source reads are unavailable on this platform")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_RDONLY | os.O_NOFOLLOW
    root_fd = current_fd = final_fd = -1
    try:
        # Traverse the caller's absolute path from / with O_NOFOLLOW at every
        # component. This binds the root without a check-then-realpath race.
        root_path = Path(os.path.abspath(root))
        root_fd = os.open(root_path.anchor, directory_flags)
        current_fd = root_fd
        for part in root_path.parts[1:]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        final_fd = os.open(parts[-1], file_flags, dir_fd=current_fd)
        file_stat = os.fstat(final_fd)
        if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink != 1:
            raise PermissionError(f"Non-independent regular source rejected: {relative}")
        if file_stat.st_size > 2 * 1024 * 1024:
            raise PermissionError(f"Oversized source rejected: {relative}")
        with os.fdopen(final_fd, "rb") as source_file:
            final_fd = -1
            limit = 2 * 1024 * 1024
            payload = source_file.read(limit + 1 if max_bytes is None else min(max_bytes, limit + 1))
            if len(payload) > limit:
                raise PermissionError(f"Oversized source rejected: {relative}")
            return payload
    except PermissionError:
        raise
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise PermissionError(f"Symlink source rejected: {relative}") from exc
        raise OSError(f"Unable to read allowlisted source {relative}: {exc}") from exc
    finally:
        if final_fd >= 0:
            os.close(final_fd)
        if current_fd >= 0 and current_fd != root_fd:
            os.close(current_fd)
        if root_fd >= 0:
            os.close(root_fd)


def _build_source_records(bytes_by_path: dict[str, bytes | None]) -> list[dict[str, Any]]:
    records = []
    for path, family in SOURCE_FAMILIES.items():
        payload = bytes_by_path[path]
        text = payload.decode("utf-8", errors="replace") if payload is not None else ""
        stale: list[str] = []
        conflicts: list[str] = []
        freshness = "missing" if payload is None else "local_snapshot"
        if path == "docs/CURRENT_STATUS.md":
            stale.append("Known stale public-main and historical CCP snapshot per approved work plan.")
            freshness = "stale_snapshot" if payload is not None else "missing"
        elif path == "results/README.md":
            stale.append("Known index omits campaign history per approved work plan.")
            freshness = "stale_snapshot" if payload is not None else "missing"
        record = {
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest() if payload is not None else None,
            "family": family,
            "declared_date": _declared_date(text),
            "freshness": freshness,
            "stale_markers": stale,
            "conflict_markers": conflicts,
        }
        records.append(record)
    return records


def _git_vcs_states(root: Path, warnings: list[str]) -> dict[str, str]:
    """Classify only allowlisted paths using read-only Git pathspec queries."""
    paths = list(SOURCE_FAMILIES)
    base = ["git", "-C", str(root)]
    try:
        tracked = subprocess.run(
            base + ["ls-files", "-z", "--", *paths],
            check=False, capture_output=True, timeout=3,
        )
        changed = subprocess.run(
            base + ["diff", "--name-only", "-z", "HEAD", "--", *paths],
            check=False, capture_output=True, timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        warnings.append("Git provenance unavailable for allowlisted source paths.")
        return {path: "unknown" for path in paths}
    if tracked.returncode != 0 or changed.returncode != 0:
        warnings.append("Git provenance unavailable for allowlisted source paths.")
        return {path: "unknown" for path in paths}
    tracked_paths = set(tracked.stdout.decode("utf-8", errors="replace").split("\0"))
    changed_paths = set(changed.stdout.decode("utf-8", errors="replace").split("\0"))
    return {
        path: "untracked" if path not in tracked_paths
        else "tracked_modified" if path in changed_paths
        else "tracked_clean"
        for path in paths
    }


def _declared_date(text: str) -> str | None:
    patterns = (
        r"(?im)^\s*(?:date|last_verified|created_at|created|as_of|updated)\s*:\s*[`\"]?(20\d{2}-\d{2}-\d{2})",
        r'"(?:created_at|last_verified|date|as_of)"\s*:\s*"(20\d{2}-\d{2}-\d{2})',
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _extract_claims(payload: bytes | None, warnings: list[str]) -> list[dict[str, Any]]:
    if payload is None:
        return []
    claims = []
    for line_number, line in enumerate(payload.decode("utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            warnings.append(f"Formal claims line {line_number} is malformed.")
            claims.append({
                "claim_id": f"line-{line_number}", "statement": "",
                "status": "not_interpretable", "evidence_level": None,
                "source": "data/claims.jsonl",
            })
            continue
        valid = _valid_claim(entry)
        status = entry.get("status") if valid else "not_interpretable"
        if not valid:
            warnings.append(f"Formal claim line {line_number} has an unsupported level or malformed schema/status.")
        claims.append({
            "claim_id": entry.get("claim_id", f"line-{line_number}") if isinstance(entry, dict) else f"line-{line_number}",
            "statement": entry.get("statement", "") if isinstance(entry, dict) else "",
            "status": status,
            "evidence_level": entry.get("evidence_level") if valid else None,
            "last_verified": entry.get("last_verified") if valid else None,
            "source": "data/claims.jsonl",
        })
    return claims


def _valid_claim(entry: Any) -> bool:
    if not isinstance(entry, dict) or set(entry) != CLAIM_FIELDS:
        return False
    if not all(isinstance(entry.get(key), str) for key in (
        "claim_id", "statement", "principle", "track", "status",
        "evidence_level", "falsification_condition", "last_verified",
    )):
        return False
    if (
        entry["track"] not in CLAIM_TRACKS
        or entry["status"] not in CLAIM_STATUSES
        or entry["evidence_level"] not in CLAIM_LEVELS
        or entry["evidence_level"] != "E0"
    ):
        return False
    model_scope = entry.get("model_scope")
    evidence_profile = entry.get("evidence_profile")
    profile_keys = {
        "behavioral_effect", "lexical_controls", "cross_domain", "decodable",
        "positive_causal_intervention", "negative_causal_intervention",
        "dose_response", "capability_preserved", "independent_replication",
        "cross_model_replication", "controlled_training",
    }
    list_keys = ("preregistrations", "dataset_snapshots", "experiments", "results", "replications")
    lists_valid = all(
        isinstance(entry.get(key), list) and all(isinstance(item, str) for item in entry[key])
        for key in list_keys
    )
    e0_consistent = (
        entry.get("evidence_level") != "E0"
        or (
            entry.get("status") == "untested"
            and entry.get("non_empirical") is True
            and all(not entry[key] for key in list_keys)
        )
    )
    return (
        re.fullmatch(r"CLM-[0-9]{3,}", entry.get("claim_id", "")) is not None
        and isinstance(entry.get("statement"), str) and bool(entry["statement"].strip())
        and isinstance(entry.get("principle"), str) and bool(entry["principle"].strip())
        and entry.get("track") in CLAIM_TRACKS
        and isinstance(model_scope, dict)
        and set(model_scope) == {"name", "family", "revision"}
        and all(isinstance(value, str) and value for value in model_scope.values())
        and entry.get("status") in CLAIM_STATUSES
        and entry.get("evidence_level") in CLAIM_LEVELS
        and isinstance(entry.get("falsification_condition"), str)
        and lists_valid
        and isinstance(entry.get("non_empirical"), bool)
        and isinstance(evidence_profile, dict)
        and set(evidence_profile) == profile_keys
        and all(isinstance(value, bool) for value in evidence_profile.values())
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry.get("last_verified", "")) is not None
        and e0_consistent
    )


def _extract_decisions(
    root: Path, bytes_by_path: dict[str, bytes | None], warnings: list[str]
) -> list[dict[str, Any]]:
    decisions = []
    for path in _DECISION_PATHS:
        payload = bytes_by_path.get(path)
        if payload is None:
            continue
        text = payload.decode("utf-8", errors="replace")
        title_match = re.search(r"(?m)^#\s+(.+?)\s*$", text)
        if not title_match:
            warnings.append(f"Decision title missing: {path}")
        decisions.append({
            "id": Path(path).stem[:4],
            "title": title_match.group(1) if title_match else Path(path).stem,
            "category": _decision_category(path, text),
            "declared_date": _declared_date(text),
            "source": path,
            "notes": "Indexed ADR; timeline coverage remains incomplete.",
        })
    return decisions


_ADR_CATEGORIES = {
    "0001": "scientific design",
    "0002": "scientific design",
    "0003": "scientific design",
    "0004": "education",
    "0005": "education",
    "0006": "education",
    "0007": "scientific design",
    "0008": "tooling",
    "0009": "scientific design",
}


def _decision_category(path: str, _text: str) -> str:
    """Use a reviewed ADR index; incidental body words cannot change a filter."""
    return _ADR_CATEGORIES.get(Path(path).stem[:4], "uncategorized")


def _extract_observations(
    root: Path,
    bytes_by_path: dict[str, bytes | None],
    warnings: list[str],
    invalid_report_manifests: set[str],
) -> list[dict[str, Any]]:
    known: dict[tuple[str, str], tuple[str, str, list[str], str]] = {}

    # Bind A0-series summaries to their explicitly named, frozen public protocols.
    for campaign, model, manifest_path, report_path, protocol_path, expected_id, status_field in (
        ("A0", "EleutherAI/pythia-70m-deduped",
         "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json",
         "results/a0/a0-v1.0.3-e93a9faa/report.html",
         "experiments/a0-automated-weak-proxy/protocol.json",
         "a0-automated-weak-proxy-v1.0.3", "status"),
        ("A0-R1", "EleutherAI/pythia-70m-deduped",
         "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json",
         "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/report.md",
         "experiments/a0r1-independent-proxy/protocol.json",
         "a0-r1-tier-r1-v1.0", "result_status"),
        ("A0-R2-C3", "HuggingFaceTB/SmolLM2-360M",
         "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/publication-manifest.json",
         "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/report.md",
         "experiments/a0r2-independent-model/study-protocol.json",
         "a0r2-independent-model-v1.0.0", "terminal_status"),
    ):
        manifest = _json_at(bytes_by_path, manifest_path, warnings)
        report = _decode_at(bytes_by_path, report_path)
        protocol = _json_at(bytes_by_path, protocol_path, warnings)
        if manifest is None or report is None or protocol is None:
            warnings.append(f"Required public summary/protocol missing for {campaign}.")
            known[(model, campaign)] = (
                "not_interpretable", manifest_path,
                [manifest_path, report_path, protocol_path],
                "Required public summary or frozen protocol is missing; outcome not interpreted.",
            )
            continue
        if manifest_path in invalid_report_manifests:
            warnings.append(f"Publication report binding did not verify for {campaign}.")
            known[(model, campaign)] = (
                "not_interpretable", manifest_path,
                [manifest_path, report_path, protocol_path],
                "Publication report is missing, unbound, or hash-conflicted; outcome not interpreted.",
            )
            continue
        protocol_model = _protocol_model(protocol, expected_id)
        protocol_bound = protocol_model == model
        if campaign == "A0-R2-C3":
            binding = manifest.get("protocol")
            protocol_bound = (
                protocol_bound
                and isinstance(binding, dict)
                and binding.get("path") == protocol_path
                and binding.get("sha256") == hashlib.sha256(bytes_by_path[protocol_path] or b"").hexdigest()
            )
        elif campaign == "A0":
            protocol_bound = protocol_bound and expected_id in report
        if not protocol_bound:
            warnings.append(f"Frozen protocol identity/binding could not be verified for {campaign}.")
            known[(model, campaign)] = (
                "not_interpretable", manifest_path, [manifest_path, report_path, protocol_path],
                "Protocol identity or manifest binding did not verify; result is not interpreted.",
            )
            continue
        raw_status = _summary_status(report, campaign)
        if raw_status is None:
            raw_status = manifest.get(status_field)
        status = _map_summary_status(raw_status, manifest, warnings, campaign)
        notes = {
            "A0": "Exploratory automated weak-proxy report; model bound by frozen protocol; not evidence-eligible.",
            "A0-R1": "Exploratory recovery report; model bound by frozen protocol; not expert-validated or claim-promoting.",
            "A0-R2-C3": "Analysis-only dtype-metadata recovery; model bound by protocol hash; no model load or claim promotion.",
        }[campaign]
        known[(model, campaign)] = (
            status, manifest_path, [manifest_path, report_path, protocol_path], notes
        )

    for campaign, manifest_paths in _CAMPAIGN_SOURCE_PATHS.items():
        for manifest_path in manifest_paths:
            manifest = _json_at(bytes_by_path, manifest_path, warnings)
            if manifest is None:
                continue
            if campaign == "EXP-001 comparative":
                model = manifest.get("model_id")
                raw_status = manifest.get("terminal_status")
                if not isinstance(model, str):
                    warnings.append(f"EXP-001 manifest missing model_id: {manifest_path}")
                    continue
                if manifest_path in invalid_report_manifests:
                    known[(model, campaign)] = (
                        "not_interpretable", manifest_path,
                        [manifest_path, _sibling_report(manifest_path)],
                        "Publication report is missing, unbound, or hash-conflicted; outcome not interpreted.",
                    )
                    continue
                known[(model, campaign)] = (
                    _map_summary_status(raw_status, manifest, warnings, campaign),
                    manifest_path,
                    [manifest_path, _sibling_report(manifest_path)],
                    "Exploratory single-model package; outcomes and strata remain separate.",
                )
                continue
            packages = manifest.get("packages")
            if not isinstance(packages, list):
                warnings.append(f"EXP-002 manifest packages has unknown schema: {manifest_path}")
                continue
            for package in packages:
                if not isinstance(package, dict) or not isinstance(package.get("model_id"), str):
                    warnings.append(f"EXP-002 package entry malformed: {manifest_path}")
                    continue
                model = package["model_id"]
                if manifest_path in invalid_report_manifests:
                    known[(model, campaign)] = (
                        "not_interpretable", manifest_path,
                        [manifest_path, _sibling_report(manifest_path)],
                        "Publication report is missing, unbound, or hash-conflicted; outcome not interpreted.",
                    )
                    continue
                known[(model, campaign)] = (
                    _map_summary_status(package.get("terminal_status"), manifest, warnings, campaign),
                    manifest_path,
                    [manifest_path, _sibling_report(manifest_path)],
                    "Exploratory EXP-002A baseline package; no pooling across protocols.",
                )

    observations = []
    for model in MODEL_NAMES:
        for campaign in CAMPAIGNS:
            observed = known.get((model, campaign))
            if observed is None:
                observations.append({
                    "model": model,
                    "campaign": campaign,
                    "status": "not_inspected",
                    "source": None,
                    "source_paths": [],
                    "scope": "No inspected source binds this model to this campaign; absence is not a null result.",
                    "notes": "Not inspected; do not infer a run or zero outcome.",
                    "metric": None,
                })
                continue
            status, source, source_paths, notes = observed
            observations.append({
                "model": model,
                "campaign": campaign,
                "status": status,
                "source": source,
                "source_paths": source_paths,
                "scope": "One source package and protocol only; never pool or rank across campaigns.",
                "notes": notes,
                "metric": None,
            })
    return observations


def _map_summary_status(
    raw_status: Any, manifest: dict[str, Any], warnings: list[str], context: str
) -> str:
    if not isinstance(raw_status, str) or raw_status not in STATUSES:
        warnings.append(f"Unknown terminal status in {context}: {raw_status!r}")
        return "not_interpretable"
    if raw_status == "positive":
        if manifest.get("evidence_eligible") is not False:
            warnings.append(f"Positive status lacks explicit evidence_eligible=false in {context}.")
            return "not_interpretable"
        scientific_status = manifest.get("scientific_status")
        if scientific_status is not None and scientific_status != "exploratory":
            warnings.append(f"Positive status has unexpected scientific_status in {context}.")
            return "not_interpretable"
    if context == "A0-R2-C3" and raw_status == "positive":
        return "analysis_only_recovery"
    return STATUSES[raw_status]


def _summary_status(text: str, campaign: str) -> str | None:
    if campaign == "A0":
        match = re.search(r"Final status:</strong>\s*([a-z_]+)", text, re.I)
    else:
        match = re.search(r"(?:Result|Terminal) status:\s*`?([a-z_]+)", text, re.I)
    return match.group(1).lower() if match else None


def _protocol_model(protocol: dict[str, Any], expected_id: str) -> str | None:
    """Accept only the expected frozen protocol and a well-shaped model identity."""
    if (
        protocol.get("protocol_status") != "frozen"
        or protocol.get("protocol_id") != expected_id
        or protocol.get("scientific_status") != "exploratory"
        or protocol.get("evidence_eligible") is not False
    ):
        return None
    model = protocol.get("model")
    if not isinstance(model, dict):
        return None
    name = model.get("name", model.get("id"))
    revision = model.get("revision")
    if not isinstance(name, str) or not name or not isinstance(revision, str) or not revision:
        return None
    return name


def _json_at(
    bytes_by_path: dict[str, bytes | None], path: str, warnings: list[str]
) -> dict[str, Any] | None:
    payload = bytes_by_path.get(path)
    if payload is None:
        return None
    try:
        value = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        warnings.append(f"Allowlisted JSON source malformed: {path}")
        return None
    if not isinstance(value, dict):
        warnings.append(f"Allowlisted JSON source has unexpected root schema: {path}")
        return None
    return value


def _decode_at(bytes_by_path: dict[str, bytes | None], path: str) -> str | None:
    payload = bytes_by_path.get(path)
    return payload.decode("utf-8", errors="replace") if payload is not None else None


def _sibling_report(manifest_path: str) -> str:
    return f"{Path(manifest_path).parent}/report.md"


def _validate_report_bindings(
    bytes_by_path: dict[str, bytes | None], warnings: list[str]
) -> tuple[set[str], list[tuple[str, str, str]]]:
    """Require each result manifest to bind its allowlisted summary report."""
    invalid_manifests: set[str] = set()
    mismatched_reports: list[tuple[str, str, str]] = []
    for manifest_path, family in SOURCE_FAMILIES.items():
        if family not in {"a0", "a0_r1", "a0_r2_c3", "exp001_comparative", "exp002_baseline"}:
            continue
        if not manifest_path.endswith("publication-manifest.json"):
            continue
        try:
            manifest = json.loads((bytes_by_path[manifest_path] or b"").decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            invalid_manifests.add(manifest_path)
            continue
        if not isinstance(manifest, dict):
            invalid_manifests.add(manifest_path)
            continue
        report = manifest.get("report")
        if not isinstance(report, dict):
            bindings_map = manifest.get("bindings")
            report = bindings_map.get("report.md") if isinstance(bindings_map, dict) else None
        if not isinstance(report, dict):
            invalid_manifests.add(manifest_path)
            warnings.append(f"Publication manifest lacks report binding: {manifest_path}")
            continue
        relative = report.get("path")
        digest = report.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            invalid_manifests.add(manifest_path)
            warnings.append(f"Publication report binding malformed: {manifest_path}")
            continue
        report_path = (
            relative if relative.startswith("results/")
            else f"{Path(manifest_path).parent}/{relative}"
        )
        expected_report_path = (
            f"{Path(manifest_path).parent}/report.html"
            if family == "a0"
            else f"{Path(manifest_path).parent}/report.md"
        )
        if (
            report_path not in SOURCE_FAMILIES
            or SOURCE_FAMILIES[report_path] != family
            or report_path != expected_report_path
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            invalid_manifests.add(manifest_path)
            warnings.append(f"Publication report path/hash is outside its reviewed source scope: {manifest_path}")
            continue
        payload = bytes_by_path.get(report_path)
        if payload is None:
            invalid_manifests.add(manifest_path)
            warnings.append(f"Publication-bound report is missing: {report_path}")
            continue
        if hashlib.sha256(payload).hexdigest() != digest:
            invalid_manifests.add(manifest_path)
            mismatched_reports.append((manifest_path, report_path, digest))
    return invalid_manifests, mismatched_reports
