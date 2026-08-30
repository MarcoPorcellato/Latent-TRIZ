"""Offline, fail-closed A0X model identity and CCP preflight checks.

This module intentionally has no Transformers, Torch, network, subprocess, or
CCP-client dependency.  It only consumes already captured metadata and exact
stdout bytes handed to it by a later authorized boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from .a0x_contract import (
    Leg,
    PairBinding,
    assert_authorization_chain,
    endpoint_indices,
    sha256_file,
    strict_json_object,
)
from .a0x_execution import validate_authorization_chain
from latent_triz.validator import validate


class A0XPreflightError(ValueError):
    """Raised for an A0X preflight condition that must fail closed."""


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_MODEL_KEYS = (
    "smollm2_360m",
    "qwen3_0_6b_base",
    "gpt2",
    "smollm2_135m",
    "gpt_neo_125m",
    "qwen2_5_0_5b",
)
_RESOURCE_FIELDS = frozenset((
    "schema_version", "policy_version", "platform", "capability", "decision",
    "available_percent", "reclaimable_uncompressed_bytes", "compressor_occupied_bytes",
    "total_memory_bytes", "swap_used_bytes", "swap_total_bytes", "consecutive_soft_samples",
))
_ADMISSION_FIELDS = frozenset((
    "schema_version", "active", "queue_count", "ticket_ids", "slot", "queue_lock",
    "process_visibility_note",
))
_VISIBILITY_NOTE = "No process visible in the local shell does not prove global inactivity."
_CCP_SOURCE_COMMIT = "27adf8d0820b3cd96f9c5e149de9b580ae41f639"
_CCP_SOURCE_TREE = "d8e0364d1313fde0898a44517ae6d233d9e10763"
_CCP_BINARY_SHA256 = "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4"
_CCP_ROLE = "ccp_executable"
_CCP_VERSION = "commit-ci-preflight 0.1.0"
_CCP_LEGACY_PROFILE = "matrix-v2-legacy-v1"


@dataclass(frozen=True)
class RuntimeFile:
    path: str
    size_bytes: int
    sha256: str

    def with_integrity(self, *, size_bytes: int, sha256: str) -> "RuntimeFile":
        return replace(self, size_bytes=size_bytes, sha256=sha256)


@dataclass(frozen=True)
class A0XModelCard:
    model_key: str
    model_id: str
    revision: str
    license_id: str
    architecture: str
    model_type: str
    runtime_root: str
    runtime_files: tuple[RuntimeFile, ...]
    num_hidden_layers: int
    hidden_size: int
    vocab_size: int
    effective_context: int
    final_transformer_block_tuple_index: int
    tokenizer_metadata_class: str | None
    expected_runtime_tokenizer_class: str
    fast_offsets_required: bool
    pad_side: str | None
    trust_remote_code: bool
    source_receipt_path: str
    source_receipt_sha256: str
    official_audit_path: str
    official_audit_sha256: str
    config_fact_provenance: Mapping[str, Any]
    tokenizer_fact_provenance: Mapping[str, Any]
    card_path: str

    def with_runtime_files(self, runtime_files: tuple[RuntimeFile, ...]) -> "A0XModelCard":
        return replace(self, runtime_files=runtime_files)


def load_registry(path: str | Path) -> tuple[A0XModelCard, ...]:
    registry_path = Path(path)
    payload = _load_json_object(registry_path, "model registry")
    _require_exact_keys(payload, {
        "artifact_class", "registry_source_path", "registry_source_sha256", "cards",
    }, "model registry")
    if payload["artifact_class"] != "a0x-model-registry":
        raise A0XPreflightError("model registry artifact class mismatch")
    if not isinstance(payload["cards"], list) or len(payload["cards"]) != len(_MODEL_KEYS):
        raise A0XPreflightError("model registry must name exactly six cards")
    if not _safe_relative(payload["registry_source_path"]) or not _sha(payload["registry_source_sha256"]):
        raise A0XPreflightError("model registry source binding is invalid")
    source_path = registry_path.parents[2] / payload["registry_source_path"]
    if not source_path.is_file() or sha256_file(source_path) != payload["registry_source_sha256"]:
        raise A0XPreflightError("model registry source hash mismatch")
    source = _load_json_object(source_path, "model registry source")
    models = source.get("models")
    if not isinstance(models, list):
        raise A0XPreflightError("model registry source models are malformed")
    source_entries = tuple(
        (item.get("model_id"), item.get("revision"), item.get("runtime_root"))
        for item in models if isinstance(item, dict)
    )
    expected_entries = (
        ("HuggingFaceTB/SmolLM2-360M", "f8027fd0eaeea54caa13c31d31b9fdc459c38b49", "artifacts/models/smollm2-360m-f8027fd0"),
        ("Qwen/Qwen3-0.6B-Base", "da87bfb608c14b7cf20ba1ce41287e8de496c0cd", "artifacts/models/qwen3-0.6b-base-da87bfb"),
        ("openai-community/gpt2", "607a30d783dfa663caf39e06633721c8d4cfcd7e", "artifacts/models/gpt2-607a30d7"),
        ("HuggingFaceTB/SmolLM2-135M", "93efa2f097d58c2a74874c7e644dbc9b0cee75a2", "artifacts/models/smollm2-135m-93efa2f0"),
        ("EleutherAI/gpt-neo-125m", "21def0189f5705e2521767faed922f1f15e7d7db", "artifacts/models/gpt-neo-125m-21def018"),
        ("Qwen/Qwen2.5-0.5B", "060db6499f32faf8b98477b0a26969ef7d8b9987", "artifacts/models/qwen2.5-0.5b-060db649"),
    )
    if tuple(item for item in source_entries if item[0] != "EleutherAI/pythia-70m-deduped") != expected_entries:
        raise A0XPreflightError("model registry source order is not the frozen six-entry order")
    cards = tuple(load_model_card(registry_path.parent / value) for value in payload["cards"] if isinstance(value, str))
    if len(cards) != len(_MODEL_KEYS) or tuple(card.model_key for card in cards) != _MODEL_KEYS:
        raise A0XPreflightError("model registry must contain the frozen six-card order")
    card_entries = tuple((card.model_id, card.revision, card.runtime_root) for card in cards)
    if card_entries != expected_entries:
        raise A0XPreflightError("model registry card identity does not match frozen source order")
    return cards


def load_model_card(path: str | Path) -> A0XModelCard:
    card_path = Path(path)
    payload = _load_json_object(card_path, "model card")
    required = {
        "artifact_class", "empirical", "scientific_status", "evidence_eligible", "expert_validated", "claim_ids",
        "model_key", "model_id", "revision", "license_id", "architecture", "model_type", "runtime_root",
        "runtime_files", "num_hidden_layers", "hidden_size", "vocab_size", "effective_context",
        "final_transformer_block_tuple_index", "tokenizer_metadata_class", "expected_runtime_tokenizer_class",
        "fast_offsets_required", "pad_side", "trust_remote_code", "source_receipt_path",
        "source_receipt_sha256", "official_audit_path", "official_audit_sha256", "card_path",
        "config_fact_provenance", "tokenizer_fact_provenance",
    }
    _require_exact_keys(payload, required, "model card")
    _require_common_card_boundary(payload)
    runtime_files = _runtime_files(payload["runtime_files"])
    fields = ("model_key", "model_id", "revision", "license_id", "architecture", "model_type", "runtime_root", "expected_runtime_tokenizer_class", "source_receipt_path", "official_audit_path", "card_path")
    if any(not isinstance(payload[name], str) or not payload[name] for name in fields):
        raise A0XPreflightError("model card contains an empty identity field")
    if payload["model_key"] not in _MODEL_KEYS or not _REVISION.fullmatch(payload["revision"]):
        raise A0XPreflightError("model card identity is not frozen")
    if not all(_safe_relative(payload[name]) for name in ("runtime_root", "source_receipt_path", "official_audit_path", "card_path")):
        raise A0XPreflightError("model card path is unsafe")
    if not _sha(payload["source_receipt_sha256"]) or not _sha(payload["official_audit_sha256"]):
        raise A0XPreflightError("model card source hash is invalid")
    for name in ("num_hidden_layers", "hidden_size", "vocab_size", "effective_context", "final_transformer_block_tuple_index"):
        _positive_int(payload[name], name)
    if payload["final_transformer_block_tuple_index"] != payload["num_hidden_layers"]:
        raise A0XPreflightError("model card final transformer block index is inconsistent")
    if payload["tokenizer_metadata_class"] is not None and (not isinstance(payload["tokenizer_metadata_class"], str) or not payload["tokenizer_metadata_class"]):
        raise A0XPreflightError("model card tokenizer metadata class is invalid")
    if not isinstance(payload["fast_offsets_required"], bool) or not isinstance(payload["trust_remote_code"], bool):
        raise A0XPreflightError("model card boolean field is invalid")
    if payload["trust_remote_code"] is not False:
        raise A0XPreflightError("model card must forbid trust_remote_code")
    if payload["pad_side"] not in (None, "left", "right"):
        raise A0XPreflightError("model card padding side is invalid")
    return A0XModelCard(
        model_key=payload["model_key"], model_id=payload["model_id"], revision=payload["revision"],
        license_id=payload["license_id"], architecture=payload["architecture"], model_type=payload["model_type"],
        runtime_root=payload["runtime_root"], runtime_files=runtime_files,
        num_hidden_layers=payload["num_hidden_layers"], hidden_size=payload["hidden_size"],
        vocab_size=payload["vocab_size"], effective_context=payload["effective_context"],
        final_transformer_block_tuple_index=payload["final_transformer_block_tuple_index"],
        tokenizer_metadata_class=payload["tokenizer_metadata_class"],
        expected_runtime_tokenizer_class=payload["expected_runtime_tokenizer_class"],
        fast_offsets_required=payload["fast_offsets_required"],
        pad_side=payload["pad_side"], trust_remote_code=payload["trust_remote_code"],
        source_receipt_path=payload["source_receipt_path"], source_receipt_sha256=payload["source_receipt_sha256"],
        official_audit_path=payload["official_audit_path"], official_audit_sha256=payload["official_audit_sha256"],
        config_fact_provenance=_fact_provenance(payload["config_fact_provenance"], "config"),
        tokenizer_fact_provenance=_fact_provenance(payload["tokenizer_fact_provenance"], "tokenizer"),
        card_path=payload["card_path"],
    )


def verify_snapshot_files(root: str | Path, card: A0XModelCard) -> A0XModelCard:
    """Verify only an exact regular-file allowlist and JSON config metadata."""
    snapshot = Path(root)
    if not snapshot.is_dir() or snapshot.is_symlink():
        raise A0XPreflightError("snapshot root is unavailable")
    expected = {item.path: item for item in card.runtime_files}
    observed: set[str] = set()
    for path in snapshot.rglob("*"):
        relative = path.relative_to(snapshot).as_posix()
        if path.is_symlink() or path.is_dir() or not path.is_file() or relative not in expected:
            raise A0XPreflightError("snapshot contains unallowlisted or non-regular file")
        observed.add(relative)
        item = expected[relative]
        metadata = path.stat()
        if metadata.st_nlink != 1:
            raise A0XPreflightError("snapshot contains hardlinked runtime file")
        if metadata.st_size != item.size_bytes or sha256_file(path) != item.sha256:
            raise A0XPreflightError("snapshot file integrity mismatch")
    if observed != set(expected):
        raise A0XPreflightError("snapshot allowlist is incomplete")
    config = _load_json_object(snapshot / "config.json", "snapshot config")
    _verify_config(config, card)
    return card


def verify_card_sources(repository_root: str | Path, card: A0XModelCard) -> None:
    """Prove a card is an exact projection of tracked receipt/audit evidence."""
    root = Path(repository_root)
    receipt_path = root / card.source_receipt_path
    audit_path = root / card.official_audit_path
    if not receipt_path.is_file() or sha256_file(receipt_path) != card.source_receipt_sha256:
        raise A0XPreflightError("model card source receipt hash mismatch")
    if not audit_path.is_file() or sha256_file(audit_path) != card.official_audit_sha256:
        raise A0XPreflightError("model card official audit hash mismatch")
    receipt = _load_json_object(receipt_path, "model card source receipt")
    model = receipt.get("model") if isinstance(receipt.get("model"), dict) else receipt
    model_id = receipt.get("model_id", model.get("id"))
    revision = receipt.get("revision", model.get("revision"))
    license_id = receipt.get("license_id", model.get("license_id"))
    if model_id != card.model_id or revision != card.revision or license_id != card.license_id:
        raise A0XPreflightError("model card source receipt identity mismatch")
    root_value = receipt.get("runtime_root", receipt.get("local_locator"))
    if root_value != card.runtime_root or not isinstance(receipt.get("runtime_files"), list):
        raise A0XPreflightError("model card source receipt runtime root mismatch")
    received: dict[str, tuple[int, str]] = {}
    for item in receipt["runtime_files"]:
        if not isinstance(item, dict):
            raise A0XPreflightError("model card source receipt runtime file is malformed")
        path = item.get("path", item.get("name"))
        size = item.get("size_bytes", item.get("size"))
        digest = item.get("sha256")
        if not isinstance(path, str) or not isinstance(size, int) or isinstance(size, bool) or not _sha(digest):
            raise A0XPreflightError("model card source receipt runtime file is malformed")
        received[path] = (size, digest)
    expected = {item.path: (item.size_bytes, item.sha256) for item in card.runtime_files}
    if received != expected:
        raise A0XPreflightError("model card runtime allowlist does not match source receipt")
    _verify_fact_provenance(root, card.config_fact_provenance, "config")
    _verify_fact_provenance(root, card.tokenizer_fact_provenance, "tokenizer")


def require_empty_output(path: Path) -> None:
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise A0XPreflightError(f"output destination is not empty: {path}")


def parse_ccp_observation(
    *, resource_raw: bytes, admission_raw: bytes, binary: Mapping[str, str],
    pair_binding: PairBinding, authorization_chain: Mapping[str, Any], output_dir: Path,
    source_head: str | None = None, material_contract_raw_sha256: str | None = None,
    ccp_trace: list[Mapping[str, Any]] | None = None, dry_run_reviewed: bool | None = None,
    claim_locator: str | None = None, claim_sha256: str | None = None,
    policy_raw_sha256: str | None = None, guard_exec_argv_commitment: str | None = None,
    run_count: int | None = None,
) -> dict[str, object]:
    """Retired legacy parser; public observations come from guard preflight."""
    raise A0XPreflightError(
        "legacy CCP observation parsing is retired; use the canonical guard preflight observation"
    )
    # Historical implementation retained below temporarily for narrow source
    # archaeology only; it must never translate raw host observations into a
    # public artifact.
    _validate_binary_binding(binary)
    try:
        chain = validate_authorization_chain(authorization_chain)
    except Exception as error:
        raise A0XPreflightError("CCP observation authorization chain is invalid") from error
    resource = _parse_raw_object(resource_raw, "resource status")
    admission = _parse_raw_object(admission_raw, "admission status")
    _validate_resource(resource)
    _validate_admission(admission)
    require_empty_output(output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=False)
    resource_path = output_dir / "resource-status.raw.json"
    admission_path = output_dir / "admission-status.raw.json"
    _exclusive_write(resource_path, resource_raw)
    _exclusive_write(admission_path, admission_raw)
    receipt = {
        "artifact_class": "a0x-ccp-observation",
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": [],
        "pair_binding": pair_binding.as_mapping(),
        "authorization_chain": chain,
        "read_counter": 0,
        "admission_status": "not_requested",
        # Resolved executable locations are local runtime facts.  The public
        # receipt carries only a role plus hash-bound producer identity.
        "binary": {name: binary[name] for name in ("role", "source_commit", "source_tree", "sha256", "version")},
        "resource": resource,
        "admission": admission,
        "resource_raw_sha256": hashlib.sha256(resource_raw).hexdigest(),
        "resource_raw_bytes": len(resource_raw),
        "admission_raw_sha256": hashlib.sha256(admission_raw).hexdigest(),
        "admission_raw_bytes": len(admission_raw),
    }
    extension = (source_head, material_contract_raw_sha256, ccp_trace, dry_run_reviewed, claim_locator, claim_sha256, policy_raw_sha256, guard_exec_argv_commitment, run_count)
    if any(value is not None for value in extension):
        if not (_REVISION.fullmatch(str(source_head)) and _sha(material_contract_raw_sha256) and isinstance(ccp_trace, list) and isinstance(dry_run_reviewed, bool) and isinstance(run_count, int) and run_count in (0, 1)):
            raise A0XPreflightError("extended CCP observation binding is invalid")
        if (
            not isinstance(claim_locator, str) or not _safe_relative(claim_locator)
            or not _sha(claim_sha256) or not _sha(policy_raw_sha256)
            or not _sha(guard_exec_argv_commitment)
        ):
            raise A0XPreflightError("extended CCP observation claim locator is invalid")
        receipt.update({"source_head": source_head, "material_contract_raw_sha256": material_contract_raw_sha256, "ccp_trace": ccp_trace, "dry_run_reviewed": dry_run_reviewed, "claim_locator": claim_locator, "claim_sha256": claim_sha256, "policy_raw_sha256": policy_raw_sha256, "guard_exec_argv_commitment": guard_exec_argv_commitment, "run_count": run_count})
    schema_path = Path(__file__).resolve().parents[2] / "schemas/a0x-ccp-observation.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XPreflightError("CCP observation schema is unavailable") from error
    if validate(receipt, schema):
        raise A0XPreflightError("CCP observation does not satisfy its schema")
    _exclusive_write(output_dir / "a0x-ccp-observation.json", _stable_json_bytes(receipt))
    return receipt


def verify_static_preflight(
    *, card: A0XModelCard, snapshot_root: str | Path, expected_origin: str, observed_origin: str,
    output_dir: Path, environment: Mapping[str, str], pair_binding: PairBinding,
    protected_trees: Sequence[tuple[str | Path, Mapping[str, Any]]], protected_tree_verifier: Any,
    dossier_path: str | Path, expected_dossier_raw_sha256: str, authorization_path: str | Path,
    expected_authorization_raw_sha256: str, ccp_observation: Mapping[str, Any],
    authorization_chain: Mapping[str, Any], material_contract_raw_sha256: str,
    ccp_observation_path: str, ccp_observation_raw_sha256: str,
) -> dict[str, object]:
    """Validate every material no-load prerequisite and otherwise fail closed."""
    if expected_origin != observed_origin or not _REVISION.fullmatch(expected_origin):
        raise A0XPreflightError("origin anchor mismatch")
    try:
        chain = validate_authorization_chain(authorization_chain)
    except Exception as error:
        raise A0XPreflightError("preflight authorization chain is invalid") from error
    if not _sha(material_contract_raw_sha256) or not _sha(ccp_observation_raw_sha256) or not _safe_relative(ccp_observation_path):
        raise A0XPreflightError("hash-bound CCP/preflight provenance is invalid")
    values = dict(environment)
    if values.get("HF_HUB_OFFLINE") != "1" or values.get("TRANSFORMERS_OFFLINE") != "1":
        raise A0XPreflightError("offline environment is not enforced")
    require_empty_output(output_dir)
    if not isinstance(pair_binding, PairBinding):
        raise A0XPreflightError("pair binding is required")
    if pair_binding.model_key != card.model_key or pair_binding.model_id != card.model_id or pair_binding.revision != card.revision:
        raise A0XPreflightError("pair binding does not match model card")
    if pair_binding.dense_bound.total_bytes > pair_binding.dense_bound.cap_bytes:
        raise A0XPreflightError("dense bound exceeds cap")
    if not callable(protected_tree_verifier) or len(protected_trees) != 2:
        raise A0XPreflightError("both protected tree verification inputs are required")
    for root, tree in protected_trees:
        protected_tree_verifier(root, tree, phase="preflight")
    verify_snapshot_files(snapshot_root, card)
    endpoint = verify_static_endpoint_availability(card=card, leg=pair_binding.leg)
    dossier = _read_hash_bound_authorization_document(
        dossier_path, expected_dossier_raw_sha256, "dossier",
    )
    authorization = _read_hash_bound_authorization_document(
        authorization_path, expected_authorization_raw_sha256, "authorization",
    )
    try:
        assert_authorization_chain(
            dossier,
            authorization,
            ({"pair_binding": pair_binding.as_mapping(), "authorization_chain": chain},),
        )
    except Exception as error:
        raise A0XPreflightError("authorization source chain does not bind preflight inputs") from error
    _verify_guard_preflight_observation(
        ccp_observation, pair_binding=pair_binding, source_head=observed_origin,
        authorization=authorization,
    )
    receipt = {
        "artifact_class": "a0x-preflight-receipt",
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": [],
        "pair_binding": pair_binding.as_mapping(),
        "authorization_chain": chain,
        "preflight_status": "passed",
        "model_key": card.model_key,
        "origin": observed_origin,
        "endpoint_availability": endpoint,
        "source_head": observed_origin,
        "material_contract_raw_sha256": material_contract_raw_sha256,
        "ccp_observation_path": ccp_observation_path,
        "ccp_observation_raw_sha256": ccp_observation_raw_sha256,
    }
    schema_path = Path(__file__).resolve().parents[2] / "schemas/a0x-preflight-receipt.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XPreflightError("preflight receipt schema is unavailable") from error
    if validate(receipt, schema):
        raise A0XPreflightError("preflight receipt does not satisfy its schema")
    return receipt


def _require_common_card_boundary(value: Mapping[str, Any]) -> None:
    expected = {
        "artifact_class": "a0x-model-card", "empirical": True, "scientific_status": "exploratory",
        "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
    }
    for name, expected_value in expected.items():
        if value.get(name) != expected_value:
            raise A0XPreflightError("model card epistemic boundary mismatch")


def _runtime_files(value: Any) -> tuple[RuntimeFile, ...]:
    if not isinstance(value, list) or not value:
        raise A0XPreflightError("model card runtime allowlist is empty")
    files: list[RuntimeFile] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "size_bytes", "sha256"}:
            raise A0XPreflightError("model card runtime file is malformed")
        path, size, digest = item["path"], item["size_bytes"], item["sha256"]
        if not isinstance(path, str) or not _safe_relative(path) or not _positive_int(size, "runtime file size") or not _sha(digest):
            raise A0XPreflightError("model card runtime file is invalid")
        files.append(RuntimeFile(path, size, digest))
    if len({item.path for item in files}) != len(files) or files[0].path != "config.json":
        raise A0XPreflightError("model card runtime allowlist is not canonical")
    return tuple(files)


def _verify_config(config: Mapping[str, Any], card: A0XModelCard) -> None:
    if config.get("model_type") != card.model_type:
        raise A0XPreflightError("snapshot config model type mismatch")
    architectures = config.get("architectures")
    if not isinstance(architectures, list) or architectures != [card.architecture]:
        raise A0XPreflightError("snapshot config architecture mismatch")
    keys = {
        "gpt2": ("n_layer", "n_embd", "n_positions"),
        "gpt_neo": ("num_layers", "hidden_size", "max_position_embeddings"),
        "llama": ("num_hidden_layers", "hidden_size", "max_position_embeddings"),
        "qwen2": ("num_hidden_layers", "hidden_size", "max_position_embeddings"),
        "qwen3": ("num_hidden_layers", "hidden_size", "max_position_embeddings"),
    }
    if card.model_type not in keys:
        raise A0XPreflightError("snapshot model type is unsupported")
    layers_key, width_key, context_key = keys[card.model_type]
    if config.get(layers_key) != card.num_hidden_layers or config.get(width_key) != card.hidden_size:
        raise A0XPreflightError("snapshot config layer or width mismatch")
    if config.get("vocab_size") != card.vocab_size or config.get(context_key) != card.effective_context:
        raise A0XPreflightError("snapshot config vocabulary or context mismatch")


def verify_static_endpoint_availability(*, card: A0XModelCard, leg: Leg) -> dict[str, object]:
    """Prove frozen literal and final-block tuple indices from card/config facts."""
    literal = endpoint_indices(leg)
    if not literal or any(not isinstance(index, int) or index < 0 for index in literal):
        raise A0XPreflightError("frozen endpoint indices are invalid")
    final_index = card.final_transformer_block_tuple_index
    if final_index != card.num_hidden_layers:
        raise A0XPreflightError("final transformer block identity is inconsistent")
    if max(literal) > final_index:
        raise A0XPreflightError("snapshot does not expose every literal endpoint index")
    return {
        "leg": leg.value,
        "literal_tuple_indices": list(literal),
        "final_transformer_block_tuple_index": final_index,
        "tuple_indexing": "embedding_at_zero",
    }


def _fact_provenance(value: Any, label: str) -> Mapping[str, Any]:
    fields = {
        "config": {"model_type", "architecture", "num_hidden_layers", "hidden_size", "vocab_size", "effective_context", "final_transformer_block_tuple_index"},
        "tokenizer": {"tokenizer_metadata_class", "expected_runtime_tokenizer_class", "fast_offsets_required"},
    }[label]
    if not isinstance(value, dict) or set(value) != {"source_path", "source_sha256", "field_pointers"}:
        raise A0XPreflightError(f"model card {label} fact provenance is malformed")
    if not isinstance(value["source_path"], str) or not _safe_relative(value["source_path"]) or not _sha(value["source_sha256"]):
        raise A0XPreflightError(f"model card {label} fact provenance source is invalid")
    pointers = value["field_pointers"]
    if not isinstance(pointers, dict) or set(pointers) != fields or any(not isinstance(pointer, str) or not pointer for pointer in pointers.values()):
        raise A0XPreflightError(f"model card {label} fact provenance pointers are malformed")
    return value


def _verify_fact_provenance(root: Path, provenance: Mapping[str, Any], label: str) -> None:
    source = root / str(provenance["source_path"])
    if not source.is_file() or sha256_file(source) != provenance["source_sha256"]:
        raise A0XPreflightError(f"model card {label} fact provenance hash mismatch")
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise A0XPreflightError(f"model card {label} fact provenance source is unreadable") from error
    if any(pointer not in text for pointer in provenance["field_pointers"].values()):
        raise A0XPreflightError(f"model card {label} fact provenance pointer mismatch")


def _verify_guard_preflight_observation(
    observation: Mapping[str, Any], *, pair_binding: PairBinding, source_head: str,
    authorization: Mapping[str, Any],
) -> None:
    """Validate the canonical public guard-preflight projection directly.

    This observation intentionally carries no authorization chain and no raw
    command output. The execution authorization supplies its identity binding;
    the public record supplies the six zero-sensitive facts needed before the
    one guarded child can run.
    """
    schema_path = Path(__file__).resolve().parents[2] / "schemas/a0x-ccp-observation.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XPreflightError("guard preflight observation schema is unavailable") from error
    if not isinstance(observation, Mapping) or validate(observation, schema):
        raise A0XPreflightError("guard preflight observation does not satisfy its schema")
    if (
        observation.get("pair_binding") != pair_binding.as_mapping()
        or observation.get("source_head") != source_head
        or observation.get("source") != {"head": source_head, "clean": True}
        or observation.get("resource") != {"decision": "admit"}
        or observation.get("admission") != {"active": False, "queue_count": 0, "slot_state": "free"}
        or observation.get("runtime") != {"intended_runtime_responsive": True, "active_container_count": 0}
    ):
        raise A0XPreflightError("guard preflight observation state differs from the fixed safe boundary")
    ccp = observation.get("ccp")
    authorization_ccp = authorization.get("ccp")
    if not isinstance(ccp, Mapping) or not isinstance(authorization_ccp, Mapping) or any(
        ccp.get(left) != authorization_ccp.get(right)
        for left, right in (
            ("sha256", "sha256"), ("source_commit", "source_commit"),
            ("qualified_source_tree", "qualified_source_tree"), ("version", "version"),
        )
    ):
        raise A0XPreflightError("guard preflight observation CCP identity differs from authorization")
    expected_roles = (
        "ccp_version", "resource_status", "admission_status", "git_source_state",
        "docker_context", "docker_active_count",
    )
    commands = observation.get("commands")
    if not isinstance(commands, list) or tuple(item.get("role") for item in commands if isinstance(item, Mapping)) != expected_roles:
        raise A0XPreflightError("guard preflight observation command roles differ")
    _reject_public_observation_leaks(observation)


def _reject_public_observation_leaks(value: Any) -> None:
    forbidden = {"argv", "path", "raw", "stdout", "stderr", "environment", "container_id", "local_path"}
    if isinstance(value, Mapping):
        if set(value).intersection(forbidden):
            raise A0XPreflightError("guard preflight observation leaks a private field")
        for child in value.values():
            _reject_public_observation_leaks(child)
    elif isinstance(value, list):
        for child in value:
            _reject_public_observation_leaks(child)
    elif isinstance(value, str) and (value.startswith(("/", "~")) or "file://" in value.lower()):
        raise A0XPreflightError("guard preflight observation leaks a local locator")


def _verify_ccp_observation(
    observation: Mapping[str, Any], pair_binding: PairBinding, authorization_chain: Mapping[str, Any],
) -> None:
    base_fields = {
        "artifact_class", "empirical", "scientific_status", "evidence_eligible", "expert_validated", "claim_ids",
        "pair_binding", "authorization_chain", "read_counter", "admission_status", "binary", "resource", "admission",
        "resource_raw_sha256", "resource_raw_bytes", "admission_raw_sha256", "admission_raw_bytes",
    }
    pre_guard_fields = base_fields | {
        "source_head", "material_contract_raw_sha256", "policy_raw_sha256", "ccp_trace",
        "dry_run_reviewed", "claim_locator", "claim_sha256",
        "guard_exec_argv_commitment", "run_count",
    }
    observed_fields = frozenset(observation) if isinstance(observation, Mapping) else frozenset()
    if not isinstance(observation, Mapping) or observed_fields not in {frozenset(base_fields), frozenset(pre_guard_fields)} or observation.get("artifact_class") != "a0x-ccp-observation":
        raise A0XPreflightError("CCP observation is invalid")
    schema_path = Path(__file__).resolve().parents[2] / "schemas/a0x-ccp-observation.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XPreflightError("CCP observation schema is unavailable") from error
    if validate(observation, schema):
        raise A0XPreflightError("CCP observation does not satisfy its schema")
    if observation.get("pair_binding") != pair_binding.as_mapping():
        raise A0XPreflightError("CCP observation pair binding mismatch")
    try:
        observed_chain = validate_authorization_chain(observation["authorization_chain"])
    except Exception as error:
        raise A0XPreflightError("CCP observation authorization chain is invalid") from error
    if observed_chain != authorization_chain:
        raise A0XPreflightError("CCP observation authorization chain mismatch")
    if observation.get("read_counter") != 0 or observation.get("admission_status") != "not_requested":
        raise A0XPreflightError("CCP observation state is invalid")
    binary = observation.get("binary")
    resource = observation.get("resource")
    admission = observation.get("admission")
    if not isinstance(binary, Mapping) or not isinstance(resource, Mapping) or not isinstance(admission, Mapping):
        raise A0XPreflightError("CCP observation payload is invalid")
    _validate_public_binary_identity(binary)
    _validate_resource(resource)
    _validate_admission(admission)
    for label in ("resource", "admission"):
        if not _sha(observation.get(f"{label}_raw_sha256")) or not _positive_int(observation.get(f"{label}_raw_bytes"), f"{label} raw bytes"):
            raise A0XPreflightError("CCP observation raw binding is invalid")
    if set(observation) == pre_guard_fields:
        expected_roles = ["admission_status", "resource_status", "plan", "doctor", "dry_run"]
        trace = observation.get("ccp_trace")
        if (
            not _REVISION.fullmatch(str(observation.get("source_head")))
            or not _sha(observation.get("material_contract_raw_sha256"))
            or not _sha(observation.get("policy_raw_sha256"))
            or observation.get("dry_run_reviewed") is not True
            or not isinstance(observation.get("claim_locator"), str)
            or not _safe_relative(observation["claim_locator"])
            or not _sha(observation.get("claim_sha256"))
            or not _sha(observation.get("guard_exec_argv_commitment"))
            or observation.get("run_count") != 0
            or not isinstance(trace, list)
            or [item.get("command_role") for item in trace if isinstance(item, Mapping)] != expected_roles
        ):
            raise A0XPreflightError("pre-guard CCP observation binding is invalid")


def _validate_binary_binding(binary: Mapping[str, str]) -> None:
    """Validate a private runtime role map without serializing its host path."""
    fields = {"role", "source_commit", "source_tree", "sha256", "version", "resolved_path", "expected_role", "expected_source_commit", "expected_source_tree", "expected_sha256", "expected_version"}
    if set(binary) != fields:
        raise A0XPreflightError("CCP binary binding fields are incomplete")
    for actual, expected in (("role", "expected_role"), ("source_commit", "expected_source_commit"), ("source_tree", "expected_source_tree"), ("sha256", "expected_sha256"), ("version", "expected_version")):
        if not isinstance(binary[actual], str) or binary[actual] != binary[expected]:
            raise A0XPreflightError("CCP binary binding does not match dossier")
    if not isinstance(binary["resolved_path"], str) or not Path(binary["resolved_path"]).is_absolute():
        raise A0XPreflightError("CCP binary binding local runtime path is invalid")
    _validate_public_binary_identity(binary)


def _validate_public_binary_identity(binary: Mapping[str, Any]) -> None:
    fields = {"role", "source_commit", "source_tree", "sha256", "version"}
    if not fields.issubset(binary):
        raise A0XPreflightError("CCP binary public identity is incomplete")
    if (
        binary["role"] != _CCP_ROLE
        or binary["source_commit"] != _CCP_SOURCE_COMMIT
        or binary["source_tree"] != _CCP_SOURCE_TREE
        or binary["sha256"] != _CCP_BINARY_SHA256
        or binary["version"] != _CCP_VERSION
    ):
        raise A0XPreflightError("CCP binary binding is invalid")


def _validate_resource(resource: Mapping[str, Any]) -> None:
    _require_exact_keys(resource, _RESOURCE_FIELDS, "CCP resource status")
    constants = {"schema_version": "1.0", "policy_version": "macos-v4", "platform": "macos", "capability": "supported_enforced", "decision": "admit", "consecutive_soft_samples": 0}
    for name, expected in constants.items():
        if resource[name] != expected:
            raise A0XPreflightError("CCP resource status is not an exact admit observation")
    for name in ("available_percent", "reclaimable_uncompressed_bytes", "compressor_occupied_bytes", "total_memory_bytes", "swap_used_bytes", "swap_total_bytes", "consecutive_soft_samples"):
        _nonnegative_int(resource[name], name)
    if resource["available_percent"] > 100 or resource["swap_used_bytes"] > resource["swap_total_bytes"]:
        raise A0XPreflightError("CCP resource status has inconsistent metrics")


def _validate_admission(admission: Mapping[str, Any]) -> None:
    _require_exact_keys(admission, _ADMISSION_FIELDS, "CCP admission status")
    if admission["schema_version"] != "2.0" or admission["active"] is not False or admission["queue_count"] != 0 or admission["ticket_ids"] != []:
        raise A0XPreflightError("CCP admission status is not inactive and empty")
    if admission["process_visibility_note"] != _VISIBILITY_NOTE:
        raise A0XPreflightError("CCP process visibility note mismatch")
    _validate_lock(admission["slot"], "slot_lock")
    _validate_lock(admission["queue_lock"], "queue_lock")


def _validate_lock(value: Any, kind: str) -> None:
    fields = {"kind", "state", "owner_run_id", "acquired_at_unix_seconds", "heartbeat_at_unix_seconds", "lease_state"}
    if not isinstance(value, dict) or set(value) != fields:
        raise A0XPreflightError("CCP admission lock fields are malformed")
    if value != {"kind": kind, "state": "free", "owner_run_id": None, "acquired_at_unix_seconds": None, "heartbeat_at_unix_seconds": None, "lease_state": "not_applicable"}:
        raise A0XPreflightError("CCP admission lock is not free")


def _read_hash_bound_authorization_document(
    path: str | Path | None, expected_raw_sha256: str | None, label: str,
) -> dict[str, Any]:
    """Read one authorization source once, bind its raw bytes, then strict-parse them."""
    if path is None or expected_raw_sha256 is None or not _sha(expected_raw_sha256):
        raise A0XPreflightError(f"{label} raw hash binding mismatch")
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise A0XPreflightError(f"{label} raw hash binding mismatch") from error
    if hashlib.sha256(raw).hexdigest() != expected_raw_sha256:
        raise A0XPreflightError(f"{label} raw hash binding mismatch")
    try:
        return strict_json_object(raw)
    except Exception as error:
        raise A0XPreflightError(f"{label} authorization source is not strict JSON") from error


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XPreflightError(f"{label} is unreadable") from error
    if not isinstance(value, dict):
        raise A0XPreflightError(f"{label} must be an object")
    return value


def _parse_raw_object(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise A0XPreflightError(f"{label} raw observation must be bytes")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XPreflightError(f"{label} raw observation is invalid") from error
    if not isinstance(value, dict):
        raise A0XPreflightError(f"{label} raw observation is not an object")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str] | frozenset[str], label: str) -> None:
    if set(value) != set(expected):
        raise A0XPreflightError(f"{label} fields are not exact")


def _positive_int(value: Any, label: str) -> bool:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise A0XPreflightError(f"{label} must be a positive integer")
    return True


def _nonnegative_int(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise A0XPreflightError(f"{label} must be a non-negative integer")


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def _safe_relative(value: str) -> bool:
    return bool(value) and not value.startswith("/") and ".." not in Path(value).parts


def _exclusive_write(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except OSError as error:
        raise A0XPreflightError("CCP observation output is not empty") from error


def _stable_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
