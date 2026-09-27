"""Fail-closed export of the reviewed Research Observatory snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import unicodedata
from datetime import datetime
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
_PAYLOAD_FIELDS = {
    "schema", "generated_at", "build_source", "source_inventory", "catalogue_sha256",
    "claims", "observations", "decisions", "sources", "warnings", "model_names", "campaign_names",
}
_MAX_PAYLOAD_BYTES = 1024 * 1024
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
_MAX_PUBLIC_TEXT = 1200
_FILE_URI = re.compile(r"(?i)\bfile:(?:/{1,3}|\\\\)[^\s\"'<>`]+")
_ABSOLUTE_PATH = re.compile(
    r"(?<![A-Za-z0-9:/])/(?!/)[^\s\"'<>`]+|"
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^\s\"'<>`]+|"
    r"(?<![A-Za-z0-9])\\\\[^\s\"'<>`]+"
)
_UTC_RFC3339 = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z\Z"
)
_FAMILY_SUMMARIES = {
    "selected_docs": "Reviewed project document. Open source path for authoritative text.",
    "navigation_snapshot": "Project navigation or status snapshot. Verify referenced canonical records.",
    "formal_claims": "Formal claim registry or schema. Claim status and evidence stay source-bound.",
    "triz_reference": "Citation metadata only. Third-party source text is not redistributed.",
    "study_protocol": "Study protocol defining scope and evidence boundaries.",
    "a0": "Published A0 manifest or report. Outcome applies only to its bound package.",
    "a0_r1": "Published A0-R1 manifest or report. Outcome applies only to its bound package.",
    "a0_r2_c3": "Published A0-R2-C3 manifest or report. Recovery is not claim promotion.",
    "exp001_comparative": "Published EXP-001 manifest or report. Outcomes remain package-specific.",
    "exp002_baseline": "Published EXP-002A manifest or report. Outcomes are not pooled.",
}


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
    if len(value) > _MAX_PUBLIC_TEXT:
        raise PermissionError(f"Oversized public {label}")
    if _FILE_URI.search(value) or _ABSOLUTE_PATH.search(value):
        raise PermissionError(f"Local path in public {label}")
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in value):
        raise PermissionError(f"Control character in public {label}")
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
        # Verify bytes and hash, but never redistribute source excerpts in v1.
        read_allowed_preview(root, path, max_chars=0, expected_sha256=digest)
        record = {
            "path": _validate_text(path, "source path"),
            "sha256": digest,
            "family": family,
            "summary": _FAMILY_SUMMARIES[family],
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
    if not isinstance(generated_at, str) or not _UTC_RFC3339.fullmatch(generated_at):
        raise PermissionError("Public export generation timestamp is invalid")
    try:
        datetime.fromisoformat(generated_at[:-1] + "+00:00")
    except ValueError as exc:
        raise PermissionError("Public export generation timestamp is invalid") from exc
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
    payload = {
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
    _validate_public_tree(payload)
    return payload


def _validate_public_tree(value: object) -> None:
    """Apply string safety bounds to every nested public value, not just records."""
    if isinstance(value, str):
        _validate_text(value, "field")
    elif isinstance(value, dict):
        for key, nested in value.items():
            _validate_text(key, "field name")
            _validate_public_tree(nested)
    elif isinstance(value, list):
        for nested in value:
            _validate_public_tree(nested)
    elif value is None or isinstance(value, (bool, int, float)):
        return
    else:
        raise PermissionError("Unsupported value in public export")


def _validate_writer_payload(payload: Mapping[str, object]) -> None:
    if set(payload) != _PAYLOAD_FIELDS or payload.get("schema") != _PAYLOAD_SCHEMA:
        raise PermissionError("Public export payload schema or fields are invalid")
    _validate_generation_time(payload.get("generated_at"))
    for name, fields in (("build_source", {"head", "tree"}),
                         ("source_inventory", {"sha256", "source_base_head", "source_base_tree"})):
        value = payload.get(name)
        if not isinstance(value, dict) or set(value) != fields:
            raise PermissionError(f"Public export {name} schema is invalid")
    build_source = payload["build_source"]
    inventory = payload["source_inventory"]
    if not _is_hex(build_source["head"], 40) or not _is_hex(build_source["tree"], 40):
        raise PermissionError("Public export source identity is invalid")
    if not _is_hex(inventory["sha256"], 64) or not _is_hex(inventory["source_base_head"], 40) or not _is_hex(inventory["source_base_tree"], 40):
        raise PermissionError("Public export inventory identity is invalid")
    if not _is_hex(payload.get("catalogue_sha256"), 64):
        raise PermissionError("Public export catalogue digest is invalid")

    claims = _validate_writer_records(payload, "claims", _CLAIM_FIELDS)
    claim_statuses = {"untested", "in-progress", "preliminary", "supported", "weakened", "falsified", "retracted", "not_interpretable"}
    for item in claims:
        if not isinstance(item["status"], str) or item["status"] not in claim_statuses:
            raise PermissionError("Public export claim is not admitted")
        if item["evidence_level"] is not None and item["evidence_level"] != "E0":
            raise PermissionError("Public export claim is not admitted")
        if not isinstance(item["source"], str) or item["source"] not in observatory_data.SOURCE_FAMILIES:
            raise PermissionError("Public export claim source is not allowlisted")

    observations = _validate_writer_records(payload, "observations", _OBSERVATION_FIELDS)
    for item in observations:
        if not isinstance(item["status"], str) or item["status"] not in STATUS_LABELS or item["metric"] is not None:
            raise PermissionError("Public export observation is not admitted")
        if item["source"] is not None and (
            not isinstance(item["source"], str) or item["source"] not in observatory_data.SOURCE_FAMILIES
        ):
            raise PermissionError("Public export observation source is not allowlisted")
        if not isinstance(item["source_paths"], list) or any(
            not isinstance(path, str) or path not in observatory_data.SOURCE_FAMILIES
            for path in item["source_paths"]
        ):
            raise PermissionError("Public export observation paths are not allowlisted")

    decisions = _validate_writer_records(payload, "decisions", _DECISION_FIELDS)
    for item in decisions:
        if not isinstance(item["source"], str) or item["source"] not in observatory_data.SOURCE_FAMILIES:
            raise PermissionError("Public export decision source is not allowlisted")

    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise PermissionError("Public export sources are malformed")
    # V1 intentionally has no raw excerpts. Reject unknown source fields and
    # reject even an empty preview marker so future callers cannot bypass policy.
    for item in sources:
        if (not isinstance(item, dict) or set(item) != _SOURCE_FIELDS
                or not isinstance(item["path"], str)
                or item["path"] not in observatory_data.SOURCE_FAMILIES):
            raise PermissionError("Public export source fields or path are invalid")
        if item["family"] != observatory_data.SOURCE_FAMILIES[item["path"]] or not _is_hex(item["sha256"], 64):
            raise PermissionError("Public export source identity is invalid")
        for key in ("stale_markers", "conflict_markers"):
            if not isinstance(item[key], list):
                raise PermissionError("Public export source markers are malformed")

    for name in ("warnings", "model_names", "campaign_names"):
        values = payload.get(name)
        if not isinstance(values, list):
            raise PermissionError(f"Public export {name} is malformed")
        for value in values:
            _validate_text(value, name)
    _validate_public_tree(dict(payload))


def _validate_writer_records(
    payload: Mapping[str, object], name: str, fields: set[str],
) -> list[dict[str, object]]:
    values = payload.get(name)
    if not isinstance(values, list):
        raise PermissionError(f"Public export {name} is malformed")
    for value in values:
        if not isinstance(value, dict) or set(value) != fields:
            raise PermissionError(f"Public export {name} record fields are invalid")
    return values


def _is_hex(value: object, length: int) -> bool:
    return isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is not None


def _validate_generation_time(value: object) -> None:
    if not isinstance(value, str) or not _UTC_RFC3339.fullmatch(value):
        raise PermissionError("Public export generation timestamp is invalid")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PermissionError("Public export generation timestamp is invalid") from exc


def _open_owned_directory(path: Path) -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise PermissionError("No-follow directory traversal is unavailable")
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        current_fd = os.open(absolute.anchor, flags)
        for part in absolute.parts[1:]:
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        metadata = os.fstat(current_fd)
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise PermissionError("Public export destination is not an owned directory")
        return current_fd
    except OSError as exc:
        if "current_fd" in locals():
            os.close(current_fd)
        raise PermissionError("Public export destination has an unsafe or non-directory parent") from exc


def write_public_payload(payload: Mapping[str, object], destination: Path) -> Path:
    """Write validated public JSON as site-data.json inside an owned directory."""
    if not isinstance(payload, dict):
        raise TypeError("payload must be a plain validated export mapping")
    _validate_writer_payload(payload)
    try:
        encoded = (json.dumps(
            payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"),
        ) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("payload is not canonical JSON data") from exc
    if len(encoded) > _MAX_PAYLOAD_BYTES:
        raise PermissionError("Public export exceeds the 1 MiB size limit")
    directory = Path(destination)
    directory_fd = _open_owned_directory(directory)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        try:
            fd = os.open("site-data.json", flags, 0o644, dir_fd=directory_fd)
        except FileExistsError as exc:
            raise FileExistsError("Public export destination already exists") from exc
        with os.fdopen(fd, "wb") as output:
            metadata = os.fstat(output.fileno())
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_uid != os.getuid():
                raise PermissionError("Public export output is not an independent owned file")
            output.write(encoded)
    finally:
        os.close(directory_fd)
    return directory / "site-data.json"
