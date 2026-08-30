"""Canonical, offline-only wheelhouse verification for A0X Gate B."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any


PROFILE = "a0x-offline-wheelhouse-v1"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_WHEEL = re.compile(
    r"^(?P<distribution>[^-]+)-(?P<version>[^-]+)(?:-(?P<build>\d[^-]*))?"
    r"-(?P<python>[^-]+)-(?P<abi>[^-]+)-(?P<platform>[^-]+)\.whl$",
)
_MANIFEST_KEYS = {"profile", "python_major_minor", "accepted_tags", "wheels"}
_WHEEL_KEYS = {"distribution", "version", "filename", "tag", "size_bytes", "sha256"}


class A0XWheelhouseError(RuntimeError):
    """An offline wheelhouse is not exactly bound by its manifest."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise A0XWheelhouseError("wheelhouse manifest contains duplicate keys")
        value[key] = item
    return value


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _normalized_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise A0XWheelhouseError(f"wheelhouse {label} is invalid")
    return value


def verify_offline_wheelhouse(directory: Path, manifest_raw: bytes) -> dict[str, object]:
    """Verify a complete wheel directory without invoking pip or any network API."""
    try:
        manifest = json.loads(manifest_raw, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as error:
        raise A0XWheelhouseError("wheelhouse manifest is not strict JSON") from error
    if not isinstance(manifest, dict) or _canonical(manifest) != manifest_raw:
        raise A0XWheelhouseError("wheelhouse manifest is not canonical JSON")
    if set(manifest) != _MANIFEST_KEYS or manifest.get("profile") != PROFILE:
        raise A0XWheelhouseError("wheelhouse manifest profile is invalid")
    if manifest.get("python_major_minor") != [3, 11]:
        raise A0XWheelhouseError("wheelhouse must target Python 3.11")
    accepted_tags = manifest.get("accepted_tags")
    if (
        not isinstance(accepted_tags, list)
        or not accepted_tags
        or any(not isinstance(item, str) or not item for item in accepted_tags)
        or accepted_tags != sorted(set(accepted_tags))
    ):
        raise A0XWheelhouseError("wheelhouse accepted tags are invalid")
    wheels = manifest.get("wheels")
    if not isinstance(wheels, list) or not wheels:
        raise A0XWheelhouseError("wheelhouse manifest has no wheels")

    expected_names: list[str] = []
    normalized_distributions: set[str] = set()
    validated: list[dict[str, Any]] = []
    for item in wheels:
        if not isinstance(item, dict) or set(item) != _WHEEL_KEYS:
            raise A0XWheelhouseError("wheelhouse record shape is invalid")
        distribution = _normalized_distribution(_string(item.get("distribution"), "distribution"))
        if distribution in normalized_distributions:
            raise A0XWheelhouseError("wheelhouse contains a duplicate distribution")
        normalized_distributions.add(distribution)
        filename = _string(item.get("filename"), "filename")
        if Path(filename).name != filename or not filename.endswith(".whl"):
            raise A0XWheelhouseError("wheelhouse filename is invalid")
        version = _string(item.get("version"), "version")
        tag = _string(item.get("tag"), "tag")
        digest = item.get("sha256")
        size = item.get("size_bytes")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise A0XWheelhouseError("wheelhouse SHA-256 is invalid")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise A0XWheelhouseError("wheelhouse size is invalid")
        parsed = _WHEEL.fullmatch(filename)
        if parsed is None:
            raise A0XWheelhouseError("wheelhouse filename does not follow the wheel format")
        filename_distribution = _normalized_distribution(parsed.group("distribution"))
        filename_tag = "-".join((parsed.group("python"), parsed.group("abi"), parsed.group("platform")))
        if filename_distribution != distribution or parsed.group("version") != version or filename_tag != tag:
            raise A0XWheelhouseError("wheelhouse filename binding is inconsistent")
        if tag not in accepted_tags:
            raise A0XWheelhouseError("wheelhouse tag is not accepted")
        expected_names.append(filename)
        validated.append(item)
    if expected_names != sorted(expected_names) or len(set(expected_names)) != len(expected_names):
        raise A0XWheelhouseError("wheelhouse records are not unique and sorted")

    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise A0XWheelhouseError("wheelhouse directory is unavailable")
    try:
        actual_names = sorted(item.name for item in root.iterdir())
    except OSError as error:
        raise A0XWheelhouseError("wheelhouse directory is unavailable") from error
    if actual_names != expected_names:
        raise A0XWheelhouseError("wheelhouse directory differs from the manifest")

    total_size = 0
    for item in validated:
        path = root / item["filename"]
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_nlink != 1:
            raise A0XWheelhouseError("wheelhouse file is not an independent regular file")
        if metadata.st_size != item["size_bytes"] or _sha256(path) != item["sha256"]:
            raise A0XWheelhouseError("wheelhouse file bytes differ from the manifest")
        total_size += metadata.st_size
    return {
        "status": "verified",
        "profile": PROFILE,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "python_major_minor": [3, 11],
        "wheel_count": len(validated),
        "total_size_bytes": total_size,
    }


__all__ = ["A0XWheelhouseError", "PROFILE", "verify_offline_wheelhouse"]
