"""Immutable, no-claim A0X terminal package construction.

This module is intentionally file/receipt oriented.  It never loads a model,
opens a target, computes a statistic, invokes a subprocess, or chooses a pair.
"""
from __future__ import annotations

import hashlib
import json
import ctypes
import errno
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from latent_triz.validator import validate

from .a0x_contract import (
    A0XContractError,
    LegFreezeBinding,
    PairBinding,
    assert_authorization_chain,
    assert_leg_freeze_binding,
    assert_pair_binding,
)


class A0XReportError(ValueError):
    """Raised when an immutable A0X package cannot be safely constructed."""


_ROOT = Path(__file__).resolve().parents[2]
_COMMON = {
    "empirical": True, "scientific_status": "exploratory",
    "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
}
_ROLE_FILES = {
    "authorization_record": "execution-authorization.json",
    "model_identity_receipt": "model-identity-receipt.json",
    "ccp_observation": "ccp-observation.json",
    "preflight_receipt": "preflight-receipt.json",
    "activation_receipt": "activation-receipt.json",
    "target_read_receipt": "target-read-receipt.json",
    "statistical_result": "statistical-result.json",
    "terminal_result": "terminal-result.json",
    "external_assets_locator": "external-assets-locator.json",
    "report": "report.md",
}
_ROLE_SCHEMAS = {
    "authorization_record": "a0x-execution-authorization.schema.json",
    "model_identity_receipt": "a0x-model-identity-receipt.schema.json",
    "ccp_observation": "a0x-ccp-observation.schema.json",
    "preflight_receipt": "a0x-preflight-receipt.schema.json",
    "activation_receipt": "a0x-activation-receipt.schema.json",
    "target_read_receipt": "a0x-target-read-receipt.schema.json",
    "statistical_result": "a0x-statistical-result.schema.json",
    "terminal_result": "a0x-terminal-result.schema.json",
    "external_assets_locator": "a0x-external-assets-locator.schema.json",
}


def render_a0x_report(*, terminal_result: Mapping[str, Any]) -> bytes:
    """Render a plain-language report without promoting an exploratory result."""
    pair = _pair(terminal_result)
    status = _text(terminal_result, "status")
    reads = terminal_result.get("analysis_target_content_reads")
    statistical = terminal_result.get("statistical_result")
    endpoint = "tuple indices 0, 2, 4, and 6" if pair.leg.value == "a0" else "tuple index 6"
    thresholds = "not available before a completed analysis"
    descriptive = "not available before a completed analysis"
    if isinstance(statistical, Mapping):
        rule = statistical.get("outcome_rule")
        if isinstance(rule, Mapping):
            thresholds = ", ".join(f"{key}={value}" for key, value in sorted(rule.items()) if key != "passed") or "frozen rule"
        final = statistical.get("descriptive_final_block")
        if isinstance(final, Mapping):
            descriptive = f"tuple index {final.get('tuple_index')}; rescues_primary={final.get('rescues_primary')}"
    lines = [
        "# A0X terminal package",
        "",
        f"- Leg: `{pair.leg.value}`",
        f"- Model: `{pair.model_id}`",
        f"- Revision: `{pair.revision}`",
        f"- Run: `{pair.run_id}`",
        f"- Terminal status: `{status}`",
        f"- Frozen primary endpoint: {endpoint}",
        f"- Frozen primary thresholds: {thresholds}",
        f"- Descriptive final-block status: {descriptive}",
        f"- Target content reads: `{reads}`",
        f"- Runtime limit: `1800` seconds; peak RSS limit: `8589934592` bytes",
        f"- New dense/index cap: `{pair.dense_bound.cap_bytes}` bytes",
        "",
        "This exploratory automated-proxy result is not a general TRIZ, causal, mechanism, emergence, or training-data claim.",
        "",
        "Limitations: this package concerns one frozen leg/model/revision pair only; no cross-model pooling, ranking, or primary-rescue interpretation is permitted.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def build_terminal_package(
    *,
    destination: str | Path,
    repository_root: str | Path,
    leg_freeze: LegFreezeBinding,
    dossier_path: str | Path,
    authorization_path: str | Path,
    terminal_result_path: str | Path,
    artifacts: Mapping[str, str | Path],
    external_assets: Mapping[str, str | Path],
    retained_residue: Mapping[str, str | Path] | None = None,
    protected_trees: object | None = None,
    protected_tree_verifier: object | None = None,
) -> Path:
    """Build one atomic terminal package from already sealed synthetic/real receipts.

    The caller supplies sealed evidence.  The builder only checks and copies
    bytes; it never interprets an unsealed model or target.
    """
    target = Path(destination)
    root = Path(repository_root)
    if os.path.lexists(target):
        raise A0XReportError("terminal destination already exists and cannot be overwritten")
    if not root.is_dir() or root.is_symlink():
        raise A0XReportError("repository root is unavailable")
    terminal_bytes, terminal_result = _read_json_file(Path(terminal_result_path), "terminal result")
    pair = _pair(terminal_result)
    _validate_mapping(terminal_result, "a0x-terminal-result.schema.json", "terminal result")
    _require_frozen_destination(root, target, pair)
    dossier_raw, dossier = _read_json_file(Path(dossier_path), "dossier")
    authorization_raw, authorization = _read_json_file(Path(authorization_path), "authorization")
    try:
        assert_leg_freeze_binding(leg_freeze, [dossier])
    except A0XContractError as error:
        raise A0XReportError("leg freeze or authorization chain is invalid") from error
    if pair.leg is not leg_freeze.leg:
        raise A0XReportError("terminal leg differs from leg freeze")
    _require_terminal_shape(terminal_result, artifacts, external_assets, retained_residue or {})
    _assert_distinct_inputs(root, [Path(dossier_path), Path(authorization_path), Path(terminal_result_path), *map(Path, artifacts.values()), *map(Path, external_assets.values()), *map(Path, (retained_residue or {}).values())])
    source_entries = _source_entries(root, dossier_path=Path(dossier_path), authorization_path=Path(authorization_path))
    source_entries[0]["raw_sha256"] = _sha(dossier_raw)
    source_entries[0]["bytes"] = len(dossier_raw)
    source_entries[1]["raw_sha256"] = _sha(authorization_raw)
    source_entries[1]["bytes"] = len(authorization_raw)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".a0x-terminal-stage-", dir=target.parent))
    try:
        ledger: list[dict[str, Any]] = []
        bound_documents: dict[str, dict[str, Any]] = {}
        bound_raw: dict[str, bytes] = {}
        _write_package_bytes(stage, "authorization_record", authorization_raw, ledger)
        _validate_mapping(authorization, _ROLE_SCHEMAS["authorization_record"], "authorization record")
        for role, path in artifacts.items():
            if role not in _ROLE_FILES or role in {"authorization_record", "terminal_result", "external_assets_locator", "report"}:
                raise A0XReportError("unknown or builder-owned package artifact role")
            raw, document = _read_json_file(Path(path), role)
            _validate_mapping(document, _ROLE_SCHEMAS[role], role)
            _require_pair_chain(document, pair)
            bound_documents[role] = document
            bound_raw[role] = raw
            _write_package_bytes(stage, role, raw, ledger)
        _write_package_bytes(stage, "terminal_result", terminal_bytes, ledger)
        external_entries = _external_entries(root, external_assets)
        _validate_completed_links(terminal_result, bound_documents, bound_raw, external_entries, leg_freeze)
        try:
            assert_authorization_chain(dossier, authorization, [terminal_result, *bound_documents.values()])
            assert_pair_binding(pair, [terminal_result, *bound_documents.values()])
        except A0XContractError as error:
            raise A0XReportError("package artifact authorization chain differs") from error
        if external_entries:
            locator = {
                "artifact_class": "a0x-external-assets-locator", **_COMMON,
                "locator_profile": "a0x-external-assets-locator-v1",
                "pair_binding": pair.as_mapping(),
                "authorization_chain": dict(terminal_result["authorization_chain"]),
                "assets": [
                    {"role": entry["role"], "repository_relative_path": entry["repository_relative_path"], "bytes": entry["bytes"], "raw_sha256": entry["raw_sha256"]}
                    for entry in external_entries
                ],
            }
            _validate_mapping(locator, _ROLE_SCHEMAS["external_assets_locator"], "external assets locator")
            _write_package_bytes(stage, "external_assets_locator", _stable_json_bytes(locator), ledger)
        _write_package_bytes(stage, "report", render_a0x_report(terminal_result=terminal_result), ledger)
        residues = _residue_entries(root, retained_residue or {})
        manifest = {
            "artifact_class": "a0x-publication-manifest", **_COMMON,
            "pair_binding": pair.as_mapping(), "authorization_chain": dict(terminal_result["authorization_chain"]),
            "manifest_profile": "a0x-terminal-package-v1",
            "root_receipt_profile": "a0x-complete-attempt-root-v2",
            "root_receipt_package_relative_path": "output-occupancy-receipt.json",
            "terminal_status": terminal_result["status"], "package_status": "complete",
            "package_artifacts": ledger, "external_outputs": external_entries,
            "source_inputs": source_entries, "retained_residue": residues,
        }
        _validate_mapping(manifest, "a0x-publication-manifest.schema.json", "publication manifest")
        manifest_bytes = _stable_json_bytes(manifest)
        (stage / "publication-manifest.json").write_bytes(manifest_bytes)
        component = {
            "manifest": len(manifest_bytes),
            "package_artifacts": sum(entry["bytes"] for entry in ledger),
            "external_outputs": sum(entry["bytes"] for entry in external_entries),
            "source_inputs": sum(entry["bytes"] for entry in source_entries),
            "retained_residue": sum(entry["bytes"] for entry in residues),
        }
        final = component["manifest"] + component["package_artifacts"] + component["external_outputs"] + component["retained_residue"]
        activation_entry = next((entry for entry in ledger if entry["role"] == "activation_receipt"), None)
        root_receipt = {
            "artifact_class": "a0x-output-occupancy-receipt", **_COMMON,
            "occupancy_profile": "a0x-complete-attempt-root-v2", "occupancy_scope": "complete_attempt",
            "pair_binding": pair.as_mapping(), "authorization_chain": dict(terminal_result["authorization_chain"]),
            "manifest_package_relative_path": "publication-manifest.json", "manifest_raw_sha256": _sha(manifest_bytes),
            "activation_receipt_raw_sha256": None if activation_entry is None else activation_entry["raw_sha256"],
            "component_bytes": component, "final_bytes_excluding_this_receipt": final,
            "peak_bytes_before_this_receipt": final, "cap_bytes": pair.dense_bound.cap_bytes,
            "runtime_checkpoints": [
                {"phase": "pre_manifest_write", "bytes": final - len(manifest_bytes)},
                {"phase": "pre_root_receipt_write", "bytes": final},
            ],
            "self_counting_rule": "final_bytes_excluding_this_receipt + serialized_root_receipt_bytes <= cap_bytes",
        }
        _validate_mapping(root_receipt, "a0x-output-occupancy-receipt.schema.json", "root occupancy receipt")
        root_bytes = _stable_json_bytes(root_receipt)
        if final + len(root_bytes) > pair.dense_bound.cap_bytes:
            raise A0XReportError("complete terminal package exceeds frozen output cap")
        (stage / "output-occupancy-receipt.json").write_bytes(root_bytes)
        _atomic_publish_no_replace(stage, target)
    except Exception as error:
        if isinstance(error, A0XReportError):
            error.stage_path = stage
            raise
        wrapped = A0XReportError("terminal package staging failed")
        wrapped.stage_path = stage
        raise wrapped from error
    return target


def _require_terminal_shape(terminal: Mapping[str, Any], artifacts: Mapping[str, Any], external_assets: Mapping[str, Any], residues: Mapping[str, Any]) -> None:
    state, status = terminal["sealed_from_state"], terminal["status"]
    roles = set(artifacts)
    external = set(external_assets)
    completed = {"activation_receipt", "target_read_receipt", "statistical_result"}
    if state == "preflight":
        if status not in {"failed", "incompatible"} or roles.intersection(completed) or external or roles.intersection({"model_identity_receipt", "preflight_receipt"}):
            raise A0XReportError("preflight terminal role matrix is invalid")
    elif state == "activation":
        required = {"model_identity_receipt", "ccp_observation", "preflight_receipt"}
        if status not in {"failed", "incompatible"} or not required.issubset(roles) or roles.intersection({"target_read_receipt", "statistical_result"}):
            raise A0XReportError("activation terminal role matrix is invalid")
        active = "activation_receipt" in roles
        if active != bool(external) or (active and set(external_assets) != {"dense", "index"}):
            raise A0XReportError("activation frontier assets must be all present or all absent")
    elif state == "analysis":
        required = {"model_identity_receipt", "ccp_observation", "preflight_receipt", "activation_receipt", "target_read_receipt"}
        if not required.issubset(roles) or set(external_assets) != {"dense", "index"}:
            raise A0XReportError("analysis terminal lacks completed activation evidence")
        has_stat = "statistical_result" in roles
        if status in {"positive", "null"} and not has_stat:
            raise A0XReportError("completed positive/null analysis requires statistical result")
        if status not in {"positive", "null"} and has_stat:
            raise A0XReportError("non-statistical analysis terminal includes a statistical result")
        if status in {"positive", "null", "non_interpretable"} and residues:
            raise A0XReportError("completed analysis cannot retain failure residue")
    else:
        raise A0XReportError("unknown terminal frontier")


def _validate_completed_links(
    terminal: Mapping[str, Any], documents: Mapping[str, Mapping[str, Any]], raw_documents: Mapping[str, bytes], external_entries: list[dict[str, Any]], leg_freeze: LegFreezeBinding,
) -> None:
    """Bind the terminal envelope to exact receipt and external-asset facts."""
    if terminal["sealed_from_state"] == "activation":
        activation = documents.get("activation_receipt")
        if activation is None:
            return
        _validate_activation_material(terminal, activation, external_entries)
        return
    if terminal["sealed_from_state"] != "analysis":
        return
    target = documents.get("target_read_receipt")
    activation = documents.get("activation_receipt")
    if target is None or activation is None:
        raise A0XReportError("analysis terminal lacks linked activation or target receipt")
    if terminal.get("target_read_receipt_sha256") != _sha(raw_documents["target_read_receipt"]):
        raise A0XReportError("terminal target receipt hash differs from persisted receipt")
    assets = {entry["role"]: entry for entry in external_entries}
    dense = activation.get("dense") if isinstance(activation.get("dense"), Mapping) else None
    index = activation.get("index") if isinstance(activation.get("index"), Mapping) else None
    if not isinstance(dense, Mapping) or not isinstance(index, Mapping):
        raise A0XReportError("activation receipt lacks dense/index links")
    if assets.get("dense", {}).get("raw_sha256") != dense.get("sha256") or assets.get("index", {}).get("raw_sha256") != index.get("sha256"):
        raise A0XReportError("activation receipt external asset links differ")
    _validate_activation_material(terminal, activation, external_entries)
    if target.get("status") != "pass" or target.get("content_reads") != 1 or terminal.get("analysis_target_content_reads") != 1:
        raise A0XReportError("completed analysis must have exactly one successful target read")
    if target.get("selection_corpus_sha256") != leg_freeze.selection_corpus_sha256:
        raise A0XReportError("target receipt selection corpus differs from leg freeze")
    if target.get("activation_receipt_sha256") != _sha(raw_documents["activation_receipt"]):
        raise A0XReportError("target receipt activation raw hash differs")
    if target.get("dense_sha256") != assets["dense"]["raw_sha256"] or target.get("index_sha256") != assets["index"]["raw_sha256"]:
        raise A0XReportError("target receipt external asset hash differs")
    if activation.get("activation_status") != "completed" or activation.get("activation_target_content_reads") != 0:
        raise A0XReportError("analysis requires completed target-free activation")
    occupancy = activation.get("activation_stage_occupancy")
    if not isinstance(occupancy, Mapping) or activation.get("activation_stage_occupancy_sha256") != _sha(_stable_json_bytes(occupancy) + b"\n"):
        raise A0XReportError("activation occupancy receipt hash differs")
    _require_pair_chain(occupancy, _pair(terminal))
    if terminal["status"] in {"positive", "null"}:
        result = documents.get("statistical_result")
        if result is None or terminal.get("statistical_result") != result:
            raise A0XReportError("terminal statistical result differs from persisted result")


def _validate_activation_material(terminal: Mapping[str, Any], activation: Mapping[str, Any], external_entries: list[dict[str, Any]]) -> None:
    assets = {entry["role"]: entry for entry in external_entries}
    dense = activation.get("dense") if isinstance(activation.get("dense"), Mapping) else None
    index = activation.get("index") if isinstance(activation.get("index"), Mapping) else None
    if not isinstance(dense, Mapping) or not isinstance(index, Mapping) or set(assets) != {"dense", "index"}:
        raise A0XReportError("activation receipt lacks exact dense/index material")
    for role, receipt in (("dense", dense), ("index", index)):
        entry = assets[role]
        if receipt.get("sha256") != entry["raw_sha256"] or receipt.get("bytes") != entry["bytes"] or Path(str(receipt.get("path", ""))).name != Path(entry["repository_relative_path"]).name:
            raise A0XReportError("activation receipt external path, size, or hash differs")
    if activation.get("planned_dense_bound") != terminal["pair_binding"]["dense_bound"]:
        raise A0XReportError("activation planned dense bound differs")
    occupancy = activation.get("activation_stage_occupancy")
    if activation.get("activation_status") != "completed" or activation.get("activation_target_content_reads") != 0 or not isinstance(occupancy, Mapping) or activation.get("activation_stage_occupancy_sha256") != _sha(_stable_json_bytes(occupancy) + b"\n") or occupancy.get("leg") != terminal["pair_binding"]["leg"] or occupancy.get("cap_bytes") != terminal["pair_binding"]["dense_bound"]["cap_bytes"] or occupancy.get("actual_total_bytes") != dense["bytes"] + index["bytes"] or occupancy.get("included_paths") != [str(dense["path"]), str(index["path"])]:
        raise A0XReportError("activation occupancy paths or arithmetic differs")


def _write_package_bytes(stage: Path, role: str, raw: bytes, ledger: list[dict[str, Any]]) -> None:
    path = stage / _ROLE_FILES[role]
    path.write_bytes(raw)
    ledger.append({"role": role, "path": path.name, "bytes": len(raw), "raw_sha256": _sha(raw)})


def _external_entries(root: Path, assets: Mapping[str, str | Path]) -> list[dict[str, Any]]:
    if set(assets) not in (set(), {"dense", "index"}):
        raise A0XReportError("external dense and index assets must be an exact pair")
    entries: list[dict[str, Any]] = []
    for role in ("dense", "index"):
        if role not in assets:
            continue
        path = _regular(Path(assets[role]), role)
        relative = _repository_relative(root, path, role)
        raw = path.read_bytes()
        entries.append({"role": role, "repository_relative_path": relative, "bytes": len(raw), "raw_sha256": _sha(raw)})
    return entries


def _residue_entries(root: Path, residues: Mapping[str, str | Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for role, value in residues.items():
        if role not in {"activation_stage_residue", "package_stage_residue", "failure_residue"}:
            raise A0XReportError("unknown retained residue role")
        path = _regular(Path(value), role)
        raw = path.read_bytes()
        entries.append({"role": role, "repository_relative_path": _repository_relative(root, path, role), "bytes": len(raw), "raw_sha256": _sha(raw)})
    if len({entry["role"] for entry in entries}) != len(entries):
        raise A0XReportError("duplicate retained residue role")
    return entries


def _source_entries(root: Path, *, dossier_path: Path, authorization_path: Path) -> list[dict[str, Any]]:
    return [
        {"role": "dossier", "repository_relative_path": _repository_relative(root, _regular(dossier_path, "dossier"), "dossier"), "bytes": 0, "raw_sha256": "0" * 64},
        {"role": "authorization", "repository_relative_path": _repository_relative(root, _regular(authorization_path, "authorization"), "authorization"), "bytes": 0, "raw_sha256": "0" * 64},
    ]


def _read_json_file(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    raw = _regular(path, label).read_bytes()
    try:
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("BOM")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_object, parse_constant=_reject_non_finite)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise A0XReportError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise A0XReportError(f"{label} must be a JSON object")
    return raw, value


def _validate_mapping(value: Mapping[str, Any], schema_name: str, label: str) -> None:
    try:
        schema = json.loads((_ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XReportError(f"{label} schema is unavailable") from error
    issues = validate(dict(value), schema)
    if issues:
        raise A0XReportError(f"{label} schema rejected input: {issues[0].message}")


def _pair(value: Mapping[str, Any]) -> PairBinding:
    try:
        return PairBinding.from_mapping(value["pair_binding"])
    except Exception as error:
        raise A0XReportError("terminal pair binding is invalid") from error


def _require_pair_chain(value: Mapping[str, Any], pair: PairBinding) -> None:
    try:
        if PairBinding.from_mapping(value["pair_binding"]).as_mapping() != pair.as_mapping():
            raise ValueError("pair drift")
        if value.get("authorization_chain") is None:
            raise ValueError("missing chain")
    except Exception as error:
        raise A0XReportError("package artifact pair or authorization chain differs") from error


def _regular(path: Path, label: str) -> Path:
    try:
        info = path.lstat()
    except OSError as error:
        raise A0XReportError(f"{label} is unavailable") from error
    if path.is_symlink() or not path.is_file() or info.st_nlink != 1:
        raise A0XReportError(f"{label} must be a unique regular file")
    return path


def _repository_relative(root: Path, path: Path, label: str) -> str:
    _assert_safe_ancestors(root, path, label)
    try:
        relative = path.resolve(strict=True).relative_to(root.resolve(strict=True)).as_posix()
    except (OSError, ValueError) as error:
        raise A0XReportError(f"{label} must stay under repository root") from error
    if not relative or relative == "." or ".." in relative.split("/"):
        raise A0XReportError(f"{label} has an unsafe repository-relative path")
    return relative


def _stable_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text(value: Mapping[str, Any], key: str) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str):
        raise A0XReportError(f"terminal {key} is invalid")
    return candidate


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_non_finite(_: str) -> Any:
    raise ValueError("non-finite JSON constant")


def _require_frozen_destination(root: Path, destination: Path, pair: PairBinding) -> None:
    expected = root / pair.output_path
    if destination.is_absolute() != expected.is_absolute() or destination.absolute() != expected.absolute():
        raise A0XReportError("terminal destination differs from frozen PairBinding output path")
    cursor = root
    for part in Path(pair.output_path).parts:
        cursor /= part
        if os.path.lexists(cursor) and cursor.is_symlink():
            raise A0XReportError("terminal destination has a symlink ancestor")


def _assert_safe_ancestors(root: Path, path: Path, label: str) -> None:
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError as error:
        raise A0XReportError(f"{label} must stay under repository root") from error
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts) or relative.as_posix() != str(relative).replace(os.sep, "/"):
        raise A0XReportError(f"{label} has a non-canonical path")
    cursor = root
    for part in relative.parts:
        cursor /= part
        try:
            if cursor.lstat() and cursor.is_symlink():
                raise A0XReportError(f"{label} has a symlink ancestor")
        except OSError as error:
            raise A0XReportError(f"{label} is unavailable") from error


def _assert_distinct_inputs(root: Path, paths: list[Path]) -> None:
    seen: set[tuple[int, int]] = set()
    for path in paths:
        regular = _regular(path, "package input")
        # all externally supplied evidence must be rooted in the synthetic/repository tree.
        _repository_relative(root, regular, "package input")
        inode = (regular.stat().st_dev, regular.stat().st_ino)
        if inode in seen:
            raise A0XReportError("package input aliases another supplied artifact")
        seen.add(inode)


def _atomic_publish_no_replace(stage: Path, target: Path) -> None:
    """Publish with an OS no-replace primitive; unsupported platforms fail closed."""
    if os.path.lexists(target):
        raise A0XReportError("terminal destination already exists and cannot be overwritten")
    try:
        if os.uname().sysname == "Darwin":
            function = ctypes.CDLL(None, use_errno=True).renamex_np
            function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            function.restype = ctypes.c_int
            result = function(os.fsencode(stage), os.fsencode(target), 0x00000004)  # RENAME_EXCL
        elif os.uname().sysname == "Linux":
            libc = ctypes.CDLL(None, use_errno=True)
            function = libc.renameat2
            function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            function.restype = ctypes.c_int
            result = function(-100, os.fsencode(stage), -100, os.fsencode(target), 1)  # RENAME_NOREPLACE
        else:
            raise A0XReportError("atomic no-replace publication is unsupported on this platform")
    except AttributeError as error:
        raise A0XReportError("atomic no-replace publication is unavailable") from error
    if result != 0:
        number = ctypes.get_errno()
        if number == errno.EEXIST:
            raise A0XReportError("terminal destination already exists and cannot be overwritten")
        raise A0XReportError(f"atomic no-replace publication failed (errno={number})")


__all__ = ["A0XReportError", "build_terminal_package", "render_a0x_report"]
