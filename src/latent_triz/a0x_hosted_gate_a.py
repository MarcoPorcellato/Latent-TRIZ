"""Pure canonical contracts for A0X GitHub-hosted Gate A evidence."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


LANE_INVALID = "A0X_GATE_A_LANE_INVALID"
LANE_OVERSIZED = "A0X_GATE_A_LANE_OVERSIZED"
LANE_SET_MISMATCH = "A0X_GATE_A_LANE_SET_MISMATCH"
SOURCE_MISMATCH = "A0X_GATE_A_SOURCE_MISMATCH"
MANIFEST_NONCANONICAL = "A0X_GATE_A_MANIFEST_NONCANONICAL"

MAX_LANE_BYTES = 4096
MAX_MANIFEST_BYTES = 32 * 1024
REPOSITORY = "MarcoPorcellato/Latent-TRIZ"
WORKFLOW_PATH = ".github/workflows/a0x-hosted-gate-a.yml"
LANE_COMMANDS = {
    "a0x-no-model": ("make", "a0x-no-model-verify"),
    "a0x-synthetic": ("make", "a0x-synthetic-verify"),
    "documentation-audit": ("make", "docs-audit"),
    "repository-python311": ("python", "scripts/repository_check.py"),
    "repository-python312": ("python", "scripts/repository_check.py"),
    "schema-cross-validation-python311": ("python", "scripts/schema_cross_validate.py"),
    "schema-cross-validation-python312": ("python", "scripts/schema_cross_validate.py"),
}
LANE_IDS = tuple(sorted(LANE_COMMANDS))
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")


class A0XHostedGateAError(ValueError):
    """Stable refusal raised for an invalid Gate A lane or manifest."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def canonical_json_bytes(value: Any) -> bytes:
    """Return contract JSON: finite, compact, sorted UTF-8 and one LF."""
    _validate_json_value(value)
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL) from error


def build_lane_receipt(
    lane_id: str,
    source_head: str,
    source_tree: str,
    command: Sequence[str],
    status: str,
) -> bytes:
    """Build one bounded, canonical PASS receipt after its lane succeeded."""
    _validate_lane_fields(lane_id, source_head, source_tree, command, status)
    raw = canonical_json_bytes({
        "artifact_class": "a0x-hosted-gate-a-lane-receipt",
        "receipt_profile": "a0x-hosted-gate-a-lane-receipt-v1",
        "lane_id": lane_id,
        "qualified_source_head": source_head,
        "qualified_source_tree": source_tree,
        "command": list(command),
        "status": status,
    })
    if len(raw) > MAX_LANE_BYTES:
        raise A0XHostedGateAError(LANE_OVERSIZED)
    return raw


def decode_lane_output(encoded: str) -> dict[str, Any]:
    """Decode and strictly validate one unpadded base64url lane output."""
    if not isinstance(encoded, str) or not encoded or not _BASE64URL.fullmatch(encoded) or len(encoded) % 4 == 1:
        raise A0XHostedGateAError(LANE_INVALID)
    try:
        raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
    except (ValueError, TypeError) as error:
        raise A0XHostedGateAError(LANE_INVALID) from error
    if base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != encoded:
        raise A0XHostedGateAError(LANE_INVALID)
    if len(raw) > MAX_LANE_BYTES:
        raise A0XHostedGateAError(LANE_OVERSIZED)
    lane = _parse_canonical_object(raw, LANE_INVALID)
    _validate_lane_document(lane)
    return lane


def build_manifest(
    *,
    repository: str,
    source_head: str,
    source_tree: str,
    workflow_sha256: str,
    run_id: int,
    run_attempt: int,
    requirements_lock_sha256: str,
    action_manifest_sha256: str,
    lane_manifest_sha256: str,
    encoded_lane_outputs: Sequence[str],
) -> bytes:
    """Build one strict, seven-lane canonical aggregate manifest."""
    if repository != REPOSITORY or not _is_revision(source_head) or not _is_revision(source_tree):
        raise A0XHostedGateAError(SOURCE_MISMATCH)
    if not all(_is_sha256(value) for value in (
        workflow_sha256, requirements_lock_sha256, action_manifest_sha256, lane_manifest_sha256,
    )) or type(run_id) is not int or run_id < 1 or type(run_attempt) is not int or run_attempt != 1:
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    if isinstance(encoded_lane_outputs, (str, bytes)) or not isinstance(encoded_lane_outputs, Sequence):
        raise A0XHostedGateAError(LANE_SET_MISMATCH)
    lanes = [decode_lane_output(encoded) for encoded in encoded_lane_outputs]
    lane_ids = [lane["lane_id"] for lane in lanes]
    if lane_ids != list(LANE_IDS):
        raise A0XHostedGateAError(LANE_SET_MISMATCH)
    for lane in lanes:
        if lane["qualified_source_head"] != source_head or lane["qualified_source_tree"] != source_tree:
            raise A0XHostedGateAError(SOURCE_MISMATCH)
    raw = canonical_json_bytes({
        "artifact_class": "a0x-hosted-gate-a-evidence",
        "evidence_profile": "a0x-hosted-gate-a-evidence-v1",
        "repository": repository,
        "event": "push",
        "ref": "refs/heads/main",
        "qualified_source_head": source_head,
        "qualified_source_tree": source_tree,
        "workflow": {
            "path": WORKFLOW_PATH,
            "raw_sha256": workflow_sha256,
            "run_id": run_id,
            "run_attempt": run_attempt,
        },
        "inputs": {
            "requirements_schema_lock_sha256": requirements_lock_sha256,
            "action_pin_manifest_sha256": action_manifest_sha256,
            "lane_manifest_sha256": lane_manifest_sha256,
        },
        "required_lanes": [
            {
                "id": lane["lane_id"],
                "receipt_sha256": hashlib.sha256(
                    base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_")
                ).hexdigest(),
                "status": "PASS",
            }
            for lane, encoded in zip(lanes, encoded_lane_outputs, strict=True)
        ],
        "overall_status": "PASS",
    })
    if len(raw) > MAX_MANIFEST_BYTES:
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    return raw


def parse_manifest_bytes(raw: bytes) -> dict[str, Any]:
    """Strictly parse a canonical aggregate manifest for offline consumers."""
    if not isinstance(raw, bytes) or len(raw) > MAX_MANIFEST_BYTES:
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    manifest = _parse_canonical_object(raw, MANIFEST_NONCANONICAL)
    _validate_manifest_document(manifest)
    return manifest


def _parse_canonical_object(raw: bytes, code: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or raw.startswith(b"\xef\xbb\xbf"):
        raise A0XHostedGateAError(code)
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_number, parse_constant=_reject_number,
        )
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise A0XHostedGateAError(code) from error
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_number(value: str) -> None:
    raise ValueError(f"non-integer JSON number {value!r}")


def _validate_json_value(value: Any) -> None:
    if value is None or type(value) in (str, int):
        return
    if type(value) is list or type(value) is tuple:
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if type(key) is not str:
                raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
            _validate_json_value(item)
        return
    raise A0XHostedGateAError(MANIFEST_NONCANONICAL)


def _validate_lane_fields(lane_id: Any, source_head: Any, source_tree: Any, command: Any, status: Any) -> None:
    if (
        not isinstance(lane_id, str) or lane_id not in LANE_COMMANDS
        or not _is_revision(source_head) or not _is_revision(source_tree)
        or isinstance(command, (str, bytes)) or not isinstance(command, Sequence)
        or tuple(command) != LANE_COMMANDS[lane_id] or status != "PASS"
    ):
        raise A0XHostedGateAError(LANE_INVALID)


def _validate_lane_document(lane: Mapping[str, Any]) -> None:
    if set(lane) != {
        "artifact_class", "receipt_profile", "lane_id", "qualified_source_head", "qualified_source_tree", "command", "status",
    } or lane.get("artifact_class") != "a0x-hosted-gate-a-lane-receipt" or lane.get("receipt_profile") != "a0x-hosted-gate-a-lane-receipt-v1":
        raise A0XHostedGateAError(LANE_INVALID)
    _validate_lane_fields(
        lane.get("lane_id"), lane.get("qualified_source_head"), lane.get("qualified_source_tree"), lane.get("command"), lane.get("status"),
    )


def _validate_manifest_document(manifest: Mapping[str, Any]) -> None:
    required = {
        "artifact_class", "evidence_profile", "repository", "event", "ref", "qualified_source_head", "qualified_source_tree", "workflow", "inputs", "required_lanes", "overall_status",
    }
    if set(manifest) != required or manifest.get("artifact_class") != "a0x-hosted-gate-a-evidence" or manifest.get("evidence_profile") != "a0x-hosted-gate-a-evidence-v1" or manifest.get("repository") != REPOSITORY or manifest.get("event") != "push" or manifest.get("ref") != "refs/heads/main" or manifest.get("overall_status") != "PASS":
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    if not _is_revision(manifest.get("qualified_source_head")) or not _is_revision(manifest.get("qualified_source_tree")):
        raise A0XHostedGateAError(SOURCE_MISMATCH)
    workflow = manifest.get("workflow")
    inputs = manifest.get("inputs")
    lanes = manifest.get("required_lanes")
    if not isinstance(workflow, Mapping) or set(workflow) != {"path", "raw_sha256", "run_id", "run_attempt"} or workflow.get("path") != WORKFLOW_PATH or not _is_sha256(workflow.get("raw_sha256")) or type(workflow.get("run_id")) is not int or workflow["run_id"] < 1 or type(workflow.get("run_attempt")) is not int or workflow["run_attempt"] != 1:
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    if not isinstance(inputs, Mapping) or set(inputs) != {"requirements_schema_lock_sha256", "action_pin_manifest_sha256", "lane_manifest_sha256"} or not all(_is_sha256(inputs.get(key)) for key in inputs):
        raise A0XHostedGateAError(MANIFEST_NONCANONICAL)
    if not isinstance(lanes, list) or len(lanes) != len(LANE_IDS):
        raise A0XHostedGateAError(LANE_SET_MISMATCH)
    if [lane.get("id") if isinstance(lane, Mapping) else None for lane in lanes] != list(LANE_IDS):
        raise A0XHostedGateAError(LANE_SET_MISMATCH)
    for lane in lanes:
        if not isinstance(lane, Mapping) or set(lane) != {"id", "receipt_sha256", "status"} or not _is_sha256(lane.get("receipt_sha256")) or lane.get("status") != "PASS":
            raise A0XHostedGateAError(MANIFEST_NONCANONICAL)


def _is_revision(value: Any) -> bool:
    return isinstance(value, str) and _REVISION.fullmatch(value) is not None


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


__all__ = [
    "A0XHostedGateAError", "LANE_IDS", "LANE_INVALID", "LANE_OVERSIZED", "LANE_SET_MISMATCH",
    "MANIFEST_NONCANONICAL", "MAX_LANE_BYTES", "SOURCE_MISMATCH", "build_lane_receipt", "build_manifest",
    "canonical_json_bytes", "decode_lane_output", "parse_manifest_bytes",
]
