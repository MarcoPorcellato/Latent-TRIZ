"""Fail-closed export of the reviewed Research Observatory snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Mapping

try:  # Support both package invocation and the local Observatory script path.
    from . import observatory_data
    from .observatory_data import load_observatory, read_allowed_preview
    from .observatory_views import STATUS_LABELS
except ImportError:  # pragma: no cover - exercised by direct script imports
    import observatory_data
    from observatory_data import load_observatory, read_allowed_preview
    from observatory_views import STATUS_LABELS


_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_INVENTORY_SCHEMA = "research-observatory-source-inventory-v1"
_PAYLOAD_SCHEMA = "research-observatory-site-v1"
_CLAIM_FIELDS = {
    "claim_id", "statement", "status", "evidence_level", "last_verified", "source",
}
_OBSERVATION_FIELDS = {
    "model", "campaign", "status", "source", "source_paths", "scope", "notes", "metric",
}
_DECISION_FIELDS = {"id", "title", "category", "declared_date", "source", "notes"}
_SOURCE_FIELDS = {
    "path", "sha256", "family", "summary", "declared_date", "freshness",
    "stale_markers", "conflict_markers",
}
_FIRST_PARTY_FAMILIES = {
    "selected_docs", "navigation_snapshot", "formal_claims", "study_protocol",
    "a0", "a0_r1", "a0_r2_c3", "exp001_comparative", "exp002_baseline",
}
_LOCAL_PATH = re.compile(
    r"(?:^|[\s\"'=:(])(?:/(?!/)[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+|[A-Za-z]:[\\/])"
)


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], check=False,
            capture_output=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PermissionError("Unable to verify public export Git identity") from exc
    if result.returncode:
        raise PermissionError("Unable to verify public export Git identity")
    try:
        return result.stdout.decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise PermissionError("Malformed public export Git identity") from exc


def _regular_inventory(root: Path) -> tuple[dict[str, object], str]:
    inventory_path = root / "scripts/research_observatory/source-inventory.json"
    if not hasattr(os, "O_NOFOLLOW"):
        raise PermissionError("No-follow inventory reads are unavailable")
    try:
        fd = os.open(inventory_path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > 65536:
                raise PermissionError("Public source inventory is not an independent bounded file")
            raw = source.read(65537)
        if len(raw) > 65536:
            raise PermissionError("Public source inventory exceeded its size limit")
        inventory = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise PermissionError("Unable to read reviewed source inventory") from exc
    if not isinstance(inventory, dict):
        raise PermissionError("Public source inventory must be an object")
    digest = hashlib.sha256(raw).hexdigest()
    if not _HEX64.fullmatch(digest):
        raise PermissionError("Malformed source inventory digest")
    if inventory.get("schema") != _INVENTORY_SCHEMA:
        raise PermissionError("Public source inventory schema mismatch")
    if not _HEX40.fullmatch(str(inventory.get("source_base_head", ""))):
        raise PermissionError("Public source inventory base HEAD is invalid")
    if not _HEX40.fullmatch(str(inventory.get("source_base_tree", ""))):
        raise PermissionError("Public source inventory base tree is invalid")
    return inventory, digest


def _validate_text(value: object, label: str, *, allow_none: bool = False) -> str | None:
    if allow_none and value is None:
        return None
    if not isinstance(value, str):
        raise PermissionError(f"Malformed public {label}")
    if _LOCAL_PATH.search(value):
        raise PermissionError(f"Local path in public {label}")
    return value


def _project_records(
    data: Mapping[str, object], root: Path,
    inventory: Mapping[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    required = {"claims", "observations", "decisions", "sources", "warnings", "model_names", "campaign_names", "snapshot_sha256"}
    if not required <= set(data):
        raise PermissionError("Observatory catalogue schema is incomplete")
    sources = data["sources"]
    if not isinstance(sources, list):
        raise PermissionError("Observatory source catalogue is malformed")
    try:
        observatory_data.validate_source_inventory(sources, inventory)
    except (PermissionError, TypeError, KeyError) as exc:
        raise PermissionError("Public source inventory differs from catalogue") from exc

    exported_sources: list[dict[str, object]] = []
    for source in sources:
        if not isinstance(source, dict) or not _SOURCE_FIELDS <= set(source):
            raise PermissionError("Malformed public source record")
        path = source["path"]
        family = source["family"]
        digest = source["sha256"]
        if not isinstance(path, str) or family != observatory_data.SOURCE_FAMILIES.get(path):
            raise PermissionError("Public source is outside the reviewed source catalogue")
        if not isinstance(digest, str) or not _HEX64.fullmatch(digest):
            raise PermissionError("Public source has invalid SHA-256")
        if source["freshness"] == "missing":
            raise PermissionError("Missing public source cannot be exported")
        family = str(family)
        # Read each source again against its catalogue hash to close the gap
        # between loader validation and data assembly.
        preview = read_allowed_preview(
            root, path, max_chars=1200 if family in _FIRST_PARTY_FAMILIES else 0,
            expected_sha256=digest,
        )
        record = {
            "path": _validate_text(path, "source path"),
            "sha256": digest,
            "family": family,
            "summary": _validate_text(source["summary"], "source summary"),
            "declared_date": _validate_text(source["declared_date"], "source date", allow_none=True),
            "freshness": _validate_text(source["freshness"], "source freshness"),
            "stale_markers": source["stale_markers"],
            "conflict_markers": source["conflict_markers"],
        }
        for key in ("stale_markers", "conflict_markers"):
            values = source[key]
            if not isinstance(values, list):
                raise PermissionError("Malformed public source markers")
            record[key] = [_validate_text(value, "source marker") for value in values]
        if family in _FIRST_PARTY_FAMILIES:
            record["preview"] = _validate_text(preview, "source preview")
        exported_sources.append(record)

    claims = _records(data["claims"], _CLAIM_FIELDS, "claim")
    for claim in claims:
        claim_statuses = {"untested", "in-progress", "preliminary", "supported", "weakened", "falsified", "retracted", "not_interpretable"}
        if not isinstance(claim["status"], str) or claim["status"] not in claim_statuses:
            raise PermissionError("Unknown public claim status")
        if claim["evidence_level"] is not None and not isinstance(claim["evidence_level"], str):
            raise PermissionError("Malformed public claim evidence level")
        if claim["evidence_level"] not in {"E0", None}:
            raise PermissionError("Future claim evidence promotion is not admitted")
        for key in _CLAIM_FIELDS - {"evidence_level"}:
            _validate_text(claim[key], f"claim {key}", allow_none=key == "source")
        if claim["source"] not in observatory_data.SOURCE_FAMILIES:
            raise PermissionError("Claim source is not allowlisted")

    observations = _records(data["observations"], _OBSERVATION_FIELDS, "observation")
    for item in observations:
        if not isinstance(item["status"], str) or item["status"] not in STATUS_LABELS:
            raise PermissionError("Unknown public observation status")
        for key in ("model", "campaign", "scope", "notes"):
            _validate_text(item[key], f"observation {key}")
        _validate_text(item["source"], "observation source", allow_none=True)
        if not isinstance(item["source_paths"], list):
            raise PermissionError("Malformed public observation source paths")
        for path in item["source_paths"]:
            _validate_text(path, "observation source path")
            if path not in observatory_data.SOURCE_FAMILIES:
                raise PermissionError("Observation source path is not allowlisted")
        if item["source"] is not None and item["source"] not in observatory_data.SOURCE_FAMILIES:
            raise PermissionError("Observation source is not allowlisted")
        if item["metric"] is not None:
            raise PermissionError("Unreviewed observation metric is not exportable")

    decisions = _records(data["decisions"], _DECISION_FIELDS, "decision")
    for item in decisions:
        for key in _DECISION_FIELDS:
            _validate_text(item[key], f"decision {key}", allow_none=key == "declared_date")
        if item["source"] not in observatory_data.SOURCE_FAMILIES:
            raise PermissionError("Decision source is not allowlisted")
    return claims, observations, decisions, exported_sources


def _records(value: object, fields: set[str], label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise PermissionError(f"Malformed public {label} catalogue")
    records = []
    for item in value:
        if not isinstance(item, dict) or not fields <= set(item):
            raise PermissionError(f"Malformed public {label} record")
        records.append({key: item[key] for key in fields})
    return records


def build_public_payload(
    repo_root: Path, *, expected_head: str, generated_at: str,
) -> dict[str, object]:
    """Verify selected checkout and return a minimal reviewed public snapshot."""
    root = Path(repo_root)
    if not isinstance(expected_head, str) or not _HEX40.fullmatch(expected_head):
        raise PermissionError("Expected public export HEAD must be a full 40-hex commit")
    if not isinstance(generated_at, str) or not generated_at.strip() or _LOCAL_PATH.search(generated_at):
        raise PermissionError("Public export generation timestamp is invalid")
    head = _git(root, "rev-parse", "--verify", "HEAD")
    tree = _git(root, "rev-parse", "--verify", "HEAD^{tree}")
    if head != expected_head or not _HEX40.fullmatch(head) or not _HEX40.fullmatch(tree):
        raise PermissionError("Public export Git identity is missing or mismatched")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise PermissionError("Public export checkout is dirty")

    inventory, inventory_digest = _regular_inventory(root)
    data = load_observatory(root, strict_public=True)
    if data.get("source_head") != head or data.get("source_tree") != tree:
        raise PermissionError("Observatory source identity differs from build checkout")
    claims, observations, decisions, sources = _project_records(data, root, inventory)
    warnings = data["warnings"]
    if not isinstance(warnings, list):
        raise PermissionError("Malformed public Observatory warnings")
    warning_copy = [_validate_text(value, "warning") for value in warnings]
    for label in ("model_names", "campaign_names"):
        if not isinstance(data[label], list):
            raise PermissionError(f"Malformed public {label}")
    catalogue_digest = data["snapshot_sha256"]
    if not isinstance(catalogue_digest, str) or not _HEX64.fullmatch(catalogue_digest):
        raise PermissionError("Observatory catalogue digest is invalid")
    return {
        "schema": _PAYLOAD_SCHEMA,
        "generated_at": generated_at,
        "build_source": {"head": head, "tree": tree},
        "source_inventory": {
            "sha256": inventory_digest,
            "source_base_head": inventory["source_base_head"],
            "source_base_tree": inventory["source_base_tree"],
        },
        "catalogue_sha256": catalogue_digest,
        "claims": claims,
        "observations": observations,
        "decisions": decisions,
        "sources": sources,
        "warnings": warning_copy,
        "model_names": [_validate_text(item, "model name") for item in data["model_names"]],
        "campaign_names": [_validate_text(item, "campaign name") for item in data["campaign_names"]],
    }


def write_public_payload(payload: Mapping[str, object], destination: Path) -> Path:
    """Write canonical UTF-8 JSON to a new independent regular file only."""
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    try:
        encoded = (json.dumps(
            payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"),
        ) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("payload is not canonical JSON data") from exc
    path = Path(destination)
    if not hasattr(os, "O_NOFOLLOW"):
        raise PermissionError("No-follow output creation is unavailable")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o644)
    except FileExistsError as exc:
        raise FileExistsError("Public export destination already exists") from exc
    with os.fdopen(fd, "wb") as output:
        if not stat.S_ISREG(os.fstat(output.fileno()).st_mode):
            raise PermissionError("Public export destination is not a regular file")
        output.write(encoded)
    return path
