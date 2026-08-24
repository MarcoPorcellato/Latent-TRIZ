"""Target-free, bounded A0X-A0 activation extraction.

This module consumes only an already-constructed hidden-state capability and
public cases.  It intentionally has no target-reader, model-loader, network,
or CCP dependency.  The occupancy receipt is limited to the activation stage:
the dense asset, JSONL index, and any staging/crash residue beneath its output
root.  Later packaging is responsible for the complete-package accounting.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .a0_activation_sites import build_view_texts, select_token_indices
from .a0x_contract import DenseBound, Leg, compute_dense_bound


class A0XActivationError(RuntimeError):
    """Raised when an A0X target-free activation cannot be safely persisted."""


_COMMON = {
    "empirical": True,
    "scientific_status": "exploratory",
    "evidence_eligible": False,
    "expert_validated": False,
    "claim_ids": [],
}
_SENTINEL = "Analysis anchor:"
_A0_SITES = {
    "problem_only": ("sentinel",),
    "transformation_only": ("sentinel", "final_transformation_token", "mean_transformation_span"),
    "problem_plus_transformation": ("sentinel", "final_transformation_token", "mean_transformation_span"),
    "problem_plus_solution": ("sentinel", "final_transformation_token", "mean_transformation_span"),
}
_ANCHOR_TEXT = {
    "problem_only": "transformation",
    "transformation_only": "transformation",
    "problem_plus_transformation": "transformation",
    "problem_plus_solution": "solution",
}


@dataclass(frozen=True)
class OutputOccupancyReceipt:
    """Actual recursive bytes in the narrow activation-stage output tree."""

    leg: Leg
    occupancy_scope: str
    included_paths: tuple[str, ...]
    actual_total_bytes: int
    cap_bytes: int

    def as_mapping(self) -> dict[str, Any]:
        return {
            "artifact_class": "a0x-output-occupancy-receipt",
            **_COMMON,
            "leg": self.leg.value,
            "occupancy_scope": self.occupancy_scope,
            "included_paths": list(self.included_paths),
            "actual_total_bytes": self.actual_total_bytes,
            "cap_bytes": self.cap_bytes,
        }

    @property
    def sha256(self) -> str:
        return _sha256_bytes(_stable_json_bytes(self.as_mapping()))


@dataclass(frozen=True)
class ActivationArtifacts:
    dense_path: Path
    index_path: Path
    receipt_path: Path
    receipt: Mapping[str, Any]
    occupancy: OutputOccupancyReceipt


def measure_output_occupancy(
    root: str | Path, *, leg: Leg, enforce_cap: bool = True,
) -> OutputOccupancyReceipt:
    """Count activation files and residue, excluding only this receipt itself.

    ``activation-receipt.json`` is excluded at the root because it contains the
    occupancy receipt and including it would make its own byte count recursive.
    Every other regular file, including dense/index staging and crash residue,
    is included.  ``enforce_cap=False`` exists only to preserve a measured
    failure-stage receipt after a cap violation.
    """
    output_root = Path(root)
    if not output_root.exists() or not output_root.is_dir() or output_root.is_symlink():
        raise A0XActivationError("activation output root is unavailable")
    included: list[str] = []
    total = 0
    for path in sorted(output_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise A0XActivationError("activation output must not contain symlinks")
        if path.is_dir():
            continue
        if not path.is_file():
            raise A0XActivationError("activation output contains a non-regular entry")
        relative = path.relative_to(output_root).as_posix()
        if relative == "activation-receipt.json":
            continue
        included.append(relative)
        total += path.stat().st_size
    receipt = OutputOccupancyReceipt(
        leg=leg,
        occupancy_scope="activation_stage",
        included_paths=tuple(included),
        actual_total_bytes=total,
        cap_bytes=_cap(leg),
    )
    if enforce_cap and total > receipt.cap_bytes:
        raise A0XActivationError("dense output cap exceeded by activation-stage occupancy")
    return receipt


def verify_output_occupancy(planned: DenseBound, actual: OutputOccupancyReceipt) -> None:
    """Verify only the shared leg/cap invariant, not future package files."""
    if planned.leg is not actual.leg:
        raise A0XActivationError("occupancy receipt leg differs from dense bound")
    if planned.cap_bytes != actual.cap_bytes:
        raise A0XActivationError("occupancy receipt cap differs from dense bound")
    if actual.actual_total_bytes > planned.cap_bytes:
        raise A0XActivationError("dense output cap exceeded by activation-stage occupancy")


def extract_a0x_a0(
    *, adapter: Any, cases: Sequence[Mapping[str, Any]], selection: Mapping[str, Any],
    output_dir: str | Path, created_at: str,
) -> ActivationArtifacts:
    """Extract the frozen A0 views without any sealed-target capability."""
    return _extract(
        leg=Leg.A0, adapter=adapter, cases=cases, selection=selection,
        output_dir=output_dir, created_at=created_at,
        literal_indices=(0, 2, 4, 6), combinations=_A0_SITES,
    )


def _extract(
    *, leg: Leg, adapter: Any, cases: Sequence[Mapping[str, Any]], selection: Mapping[str, Any],
    output_dir: str | Path, created_at: str, literal_indices: tuple[int, ...],
    combinations: Mapping[str, tuple[str, ...]],
) -> ActivationArtifacts:
    created_at = _timestamp(created_at)
    selected_cases = _validate_public_selection(cases, selection)
    destination = Path(output_dir)
    if destination.exists():
        raise A0XActivationError("refusing to overwrite activation output")
    width = _adapter_width(adapter)
    try:
        planned = compute_dense_bound(leg, cases=48, hidden_width=width)
    except Exception as error:
        raise A0XActivationError("dense output cap exceeds frozen reservation") from error
    if planned.total_bytes > planned.cap_bytes:
        raise A0XActivationError("dense output cap exceeds frozen reservation")

    vectors: dict[str, bytes] = {}
    index_rows: list[dict[str, Any]] = []
    expected_records = planned.vector_count
    for case in selected_cases:
        views = build_view_texts(case, sentinel_text=_SENTINEL)
        for view, expected_sites in combinations.items():
            payload = _forward(adapter, views[view])
            sites = select_token_indices(
                view_text=views[view], transformation_text=str(case[_ANCHOR_TEXT[view]]),
                sentinel_text=_SENTINEL, offsets=payload.offsets,
                special_flags=payload.special_tokens_mask, attention_mask=payload.attention_mask,
            )
            if any(site not in sites for site in expected_sites):
                raise A0XActivationError("token-site applicability drift")
            final_index = payload.final_block_tuple_index
            endpoints = tuple(literal_indices) + (final_index,)
            if len(set(endpoints)) != len(endpoints) or any(index < 0 or index >= len(payload.hidden_states) for index in endpoints):
                raise A0XActivationError("required hidden-state tuple endpoint is unavailable")
            for tuple_index in endpoints:
                role = "primary" if tuple_index in literal_indices else "descriptive"
                state = _matrix(payload.hidden_states[tuple_index], width=width, token_count=len(payload.input_ids))
                for site in expected_sites:
                    vector = _average(state, sites[site], width=width)
                    raw = struct.pack(f"<{width}f", *vector)
                    record_id = f"{case['case_id']}::{view}::{site}::tuple-{tuple_index}"
                    vectors[record_id] = raw
                    index_rows.append({
                        "record_id": record_id,
                        "case_id": str(case["case_id"]),
                        "problem_family_id": str(case["problem_family_id"]),
                        "domain": str(case["domain"]),
                        "view": view,
                        "token_site": site,
                        "tuple_index": tuple_index,
                        "endpoint_role": role,
                        "vector_dim": width,
                        "dtype": "float32",
                        "vector_sha256": _sha256_bytes(raw),
                        "tensor_key": record_id,
                    })
    if len(index_rows) != expected_records:
        raise A0XActivationError("activation vector count differs from frozen dense bound")

    dense_payload = _serialize_safetensors(vectors, width=width)
    index_payload = b"".join(_stable_json_bytes(row) for row in index_rows)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".a0x-activation-stage-", dir=destination.parent))
    checkpoints: list[dict[str, Any]] = []
    try:
        dense_path = stage / "activations.safetensors"
        checkpoints.append(_checkpoint(
            stage, phase="pre_dense_write", planned=planned,
            additions={"activations.safetensors": dense_payload}, leg=leg,
        ))
        _verify_checkpoint(checkpoints[-1])
        _write_safetensors(dense_path, vectors, width=width, payload=dense_payload)
        index_path = stage / "representations-index.jsonl"
        checkpoints.append(_checkpoint(
            stage, phase="pre_index_write", planned=planned,
            additions={"representations-index.jsonl": index_payload}, leg=leg,
        ))
        _verify_checkpoint(checkpoints[-1])
        index_path.write_bytes(index_payload)
        checkpoints.append(_checkpoint(
            stage, phase="pre_final_rename", planned=planned, additions={}, leg=leg,
        ))
        _verify_checkpoint(checkpoints[-1])
        occupancy = measure_output_occupancy(stage, leg=leg)
        verify_output_occupancy(planned, occupancy)
        receipt = {
            "artifact_class": "a0x-activation-receipt",
            **_COMMON,
            "leg": leg.value,
            "created_at": created_at,
            "activation_status": "completed",
            "activation_target_content_reads": 0,
            "literal_tuple_indices": list(literal_indices),
            "final_block_tuple_index": _final_index(index_rows, literal_indices),
            "record_count": len(index_rows),
            "dense": {
                "path": "activations.safetensors", "sha256": _sha256_file(dense_path),
                "bytes": dense_path.stat().st_size, "format": "safetensors",
            },
            "index": {"path": "representations-index.jsonl", "sha256": _sha256_file(index_path), "bytes": index_path.stat().st_size},
            "planned_dense_bound": planned.as_mapping(),
            "activation_stage_occupancy": occupancy.as_mapping(),
            "activation_stage_occupancy_sha256": occupancy.sha256,
            "occupancy_checkpoints": checkpoints,
        }
        receipt_path = stage / "activation-receipt.json"
        receipt_path.write_bytes(_stable_json_bytes(receipt))
        # The receipt describes only the dense/index activation stage.  It is
        # intentionally outside this occupancy scope, preventing a self-hash
        # cycle and avoiding any claim about later package files.
        final_occupancy = measure_output_occupancy(stage, leg=leg)
        if final_occupancy != occupancy:
            raise A0XActivationError("activation receipt self-exclusion remeasurement drift")
        os.replace(stage, destination)
    except Exception as error:
        failure = A0XActivationError("activation stage failed; staging residue retained")
        failure.stage_path = stage
        failure.occupancy_checkpoints = tuple(checkpoints)
        try:
            failure.activation_stage_occupancy = measure_output_occupancy(stage, leg=leg, enforce_cap=False)
        except Exception as measure_error:  # pragma: no cover - only malformed local filesystem entries
            failure.activation_stage_occupancy = None
            failure.occupancy_measurement_error = str(measure_error)
        raise failure from error
    return ActivationArtifacts(destination / "activations.safetensors", destination / "representations-index.jsonl", destination / "activation-receipt.json", receipt, occupancy)


def _validate_public_selection(cases: Sequence[Mapping[str, Any]], selection: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if selection.get("target_content_reads") != 0 or selection.get("selected_case_count") != 48:
        raise A0XActivationError("selection must be a 48-case target-free public manifest")
    selected = selection.get("cases")
    if not isinstance(selected, list) or len(selected) != 48:
        raise A0XActivationError("selection manifest must contain exactly 48 public cases")
    if len(cases) != 48:
        raise A0XActivationError("activation requires exactly 48 public cases")
    case_by_id = {str(case.get("case_id", "")): case for case in cases}
    selected_ids = [str(row.get("case_id", "")) for row in selected if isinstance(row, Mapping)]
    if len(case_by_id) != 48 or len(selected_ids) != 48 or len(set(selected_ids)) != 48 or set(selected_ids) != set(case_by_id):
        raise A0XActivationError("public cases do not match frozen selection")
    required = ("case_id", "problem_family_id", "domain", "problem", "constraints", "initial_state", "desired_improvement", "worsening_consequence", "transformation", "solution")
    ordered = [case_by_id[case_id] for case_id in selected_ids]
    for case in ordered:
        if any(key not in case for key in required):
            raise A0XActivationError("public case is missing a required activation field")
    return ordered


def _adapter_width(adapter: Any) -> int:
    for candidate in (getattr(adapter, "hidden_width", None), getattr(adapter, "width", None), getattr(getattr(adapter, "card", None), "hidden_size", None)):
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
            return candidate
    raise A0XActivationError("adapter must declare hidden width before activation")


def _forward(adapter: Any, text: str) -> Any:
    forward = getattr(adapter, "forward_hidden", None)
    if not callable(forward):
        raise A0XActivationError("adapter lacks target-free forward_hidden capability")
    try:
        return forward(text)
    except Exception as error:
        raise A0XActivationError("target-free hidden-state forward failed") from error


def _matrix(value: Any, *, width: int, token_count: int) -> list[list[float]]:
    value = _plain(value)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 1:
        raise A0XActivationError("hidden state must have one batch")
    rows = value[0]
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) != token_count:
        raise A0XActivationError("hidden state token count drift")
    result: list[list[float]] = []
    for row in rows:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) != width:
            raise A0XActivationError("hidden state width drift")
        try:
            converted = [float(item) for item in row]
        except (TypeError, ValueError) as error:
            raise A0XActivationError("hidden state must be numeric") from error
        if not all(math.isfinite(item) for item in converted):
            raise A0XActivationError("hidden state must be finite")
        result.append(converted)
    return result


def _plain(value: Any) -> Any:
    for method_name in ("detach", "cpu"):
        method = getattr(value, method_name, None)
        if callable(method):
            value = method()
    tolist = getattr(value, "tolist", None)
    return tolist() if callable(tolist) else value


def _average(matrix: Sequence[Sequence[float]], positions: Sequence[int], *, width: int) -> list[float]:
    if not positions or any(not isinstance(position, int) or position < 0 or position >= len(matrix) for position in positions):
        raise A0XActivationError("token site is unavailable")
    total = [0.0] * width
    for position in positions:
        for index, value in enumerate(matrix[position]):
            total[index] += value
    return [value / len(positions) for value in total]


def _write_safetensors(
    path: Path, vectors: Mapping[str, bytes], *, width: int, payload: bytes | None = None,
) -> None:
    path.write_bytes(payload if payload is not None else _serialize_safetensors(vectors, width=width))


def _serialize_safetensors(vectors: Mapping[str, bytes], *, width: int) -> bytes:
    offset = 0
    header: dict[str, Any] = {}
    payloads: list[bytes] = []
    for key, raw in sorted(vectors.items()):
        if len(raw) != width * 4:
            raise A0XActivationError("non-contiguous float32 vector bytes")
        header[key] = {"dtype": "F32", "shape": [width], "data_offsets": [offset, offset + len(raw)]}
        offset += len(raw)
        payloads.append(raw)
    encoded_header = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return len(encoded_header).to_bytes(8, "little") + encoded_header + b"".join(payloads)


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise A0XActivationError("created_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise A0XActivationError("created_at must include timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _final_index(rows: Sequence[Mapping[str, Any]], literal: tuple[int, ...]) -> int:
    descriptive = {int(row["tuple_index"]) for row in rows if row["endpoint_role"] == "descriptive"}
    if len(descriptive) != 1 or descriptive.intersection(literal):
        raise A0XActivationError("final-block endpoint drift")
    return next(iter(descriptive))


def _cap(leg: Leg) -> int:
    return 33_554_432 if leg is Leg.A0 else 4_194_304


def _checkpoint(
    root: Path, *, phase: str, planned: DenseBound, additions: Mapping[str, bytes], leg: Leg,
) -> dict[str, Any]:
    current = measure_output_occupancy(root, leg=leg, enforce_cap=False)
    projected_paths = list(current.included_paths)
    projected_total = current.actual_total_bytes
    for relative, payload in sorted(additions.items()):
        if relative in projected_paths:
            raise A0XActivationError("occupancy projection would overwrite an existing file")
        projected_paths.append(relative)
        projected_total += len(payload)
    checkpoint = {
        "phase": phase,
        "planned_dense_bound": planned.as_mapping(),
        "current_occupancy": current.as_mapping(),
        "projected_included_paths": projected_paths,
        "projected_total_bytes": projected_total,
        "cap_bytes": planned.cap_bytes,
    }
    return checkpoint


def _verify_checkpoint(checkpoint: Mapping[str, Any]) -> None:
    current = checkpoint["current_occupancy"]
    if current["cap_bytes"] != checkpoint["cap_bytes"] or checkpoint["projected_total_bytes"] > checkpoint["cap_bytes"]:
        raise A0XActivationError("dense output cap exceeded by activation-stage checkpoint")


def _stable_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


__all__ = [
    "A0XActivationError", "ActivationArtifacts", "OutputOccupancyReceipt",
    "extract_a0x_a0", "measure_output_occupancy", "verify_output_occupancy",
]
