from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from latent_triz.a0x_contract import Leg, PairBinding, compute_dense_bound


def sha(value: int) -> str:
    return f"{value:064x}"[-64:]


def identity(leg: Leg = Leg.A0) -> dict[str, str]:
    return {
        "leg": leg.value,
        "protocol_id": f"a0x-{leg.value}-replication-v1",
        "protected_tree_sha256": sha(1),
        "selection_corpus_sha256": sha(2),
        "source_base_commit": "a" * 40,
    }


def pair_binding(leg: Leg = Leg.A0, model_key: str = "gpt2") -> dict[str, object]:
    dense = asdict(compute_dense_bound(leg, cases=48, hidden_width=1024))
    dense["leg"] = leg.value
    return asdict(
        PairBinding(
            leg=leg,
            leg_freeze_sha256=sha(3),
            model_key=model_key,
            model_id="openai-community/gpt2",
            revision="b" * 40,
            run_id=f"a0x-{leg.value}-{model_key}-run-1",
            dossier_sha256=sha(4),
            authorization_sha256=sha(5),
            output_path=f"results/a0x/{leg.value}/{model_key}/",
            dense_bound=dense,
        )
    )


def common() -> dict[str, object]:
    return {
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": [],
    }


def artifact(name: str) -> dict[str, object]:
    common_fields = common()
    pair = pair_binding()
    if name == "a0x-model-card.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-model-card",
            "model_key": "gpt2",
            "model_id": "openai-community/gpt2",
            "revision": "b" * 40,
            "license_id": "MIT",
            "architecture": "GPT2LMHeadModel",
            "model_type": "gpt2",
            "runtime_root": "artifacts/models/gpt2-607a30d7",
            "runtime_files": [{"path": "config.json", "size_bytes": 1, "sha256": sha(6)}],
            "num_hidden_layers": 12,
            "hidden_size": 768,
            "vocab_size": 50257,
            "effective_context": 1024,
            "final_transformer_block_tuple_index": 12,
            "tokenizer_metadata_class": None,
            "expected_runtime_tokenizer_class": "GPT2TokenizerFast",
            "fast_offsets_required": True,
            "pad_side": None,
            "trust_remote_code": False,
            "source_receipt_path": "results/exp001-comparative/preexecution/gpt2-integrity-receipt.json",
            "source_receipt_sha256": sha(7),
            "official_audit_path": "docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md",
            "official_audit_sha256": sha(8),
            "config_fact_provenance": {
                "source_path": "docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md", "source_sha256": sha(8),
                "field_pointers": {name: "gpt2" for name in ("model_type", "architecture", "num_hidden_layers", "hidden_size", "vocab_size", "effective_context", "final_transformer_block_tuple_index")},
            },
            "tokenizer_fact_provenance": {
                "source_path": "docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md", "source_sha256": sha(8),
                "field_pointers": {name: "GPT-2" for name in ("tokenizer_metadata_class", "expected_runtime_tokenizer_class", "fast_offsets_required")},
            },
            "card_path": "artifacts/a0x/model-cards/gpt2.json",
        }
    if name == "a0x-protected-tree.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-protected-tree",
            "protected_tree_sha256": sha(1),
            "source_base_commit": "a" * 40,
            "protected_paths": ["src/latent_triz/a0x_contract.py"],
            "entries": [{
                "entry_kind": "file",
                "path": "src/latent_triz/a0x_contract.py",
                "bytes": 1,
                "sha256": sha(2),
                "provenance_manifest": "src/latent_triz/a0x_contract.py",
                "provenance_manifest_sha256": sha(3),
                "verification_phase": "preflight_postflight",
            }],
        }
    if name == "a0x-selection-manifest.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-selection-manifest",
            "selection_corpus_sha256": sha(2),
            "selection_path": "experiments/a0x-six-model/a0-selection-manifest.json",
            "selected_case_count": 48,
            "source_cases_path": "data/a0/cases.jsonl",
            "source_corpus_manifest_path": "data/a0/manifest.json",
            "source_cases_sha256": sha(3),
            "source_corpus_manifest_sha256": sha(4),
            "selection_rule": {
                "cases_per_family": 2,
                "families_per_domain": 4,
                "family_order": "lexicographic",
                "domain_order": "frozen",
            },
            "cases": [{
                "case_id": f"case-{index}",
                "case_content_sha256": sha(index + 10),
                "domain": ("agriculture", "energy", "manufacturing", "medicine", "software", "transport")[index % 6],
                "problem_family_id": f"family-{index // 2}",
                "split": "sealed",
            } for index in range(48)],
            "target_content_reads": 0,
        }
    if name == "a0x-protocol.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-leg-protocol",
            "identity": identity(),
            "protocol_status": "frozen",
            "endpoint_indices": [0, 2, 4, 6],
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
        }
    if name == "a0x-implementation.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-leg-implementation",
            "identity": identity(),
            "implementation_status": "frozen_before_model_output",
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
            "implementation_paths": ["src/latent_triz/a0x_contract.py"],
        }
    if name == "a0x-freeze-manifest.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-leg-freeze-manifest",
            "identity": identity(),
            "protocol_sha256": sha(10),
            "implementation_sha256": sha(11),
            "freeze_status": "frozen",
        }
    pair_artifacts = {
        "a0x-authorization-dossier.schema.json": ("a0x-authorization-dossier", {"dossier_status": "approval_requested"}),
        "a0x-execution-authorization.schema.json": ("a0x-execution-authorization", {"authorization_status": "authorized"}),
        "a0x-model-identity-receipt.schema.json": ("a0x-model-identity-receipt", {"identity_status": "verified"}),
        "a0x-ccp-observation.schema.json": ("a0x-ccp-observation", {"read_counter": 0, "admission_status": "not_requested"}),
        "a0x-preflight-receipt.schema.json": ("a0x-preflight-receipt", {"preflight_status": "passed"}),
        "a0x-activation-receipt.schema.json": ("a0x-activation-receipt", {"activation_status": "not_started"}),
        "a0x-target-read-receipt.schema.json": (
            "a0x-target-read-receipt",
            {
                "selection_corpus_sha256": sha(20),
                "activation_receipt_sha256": sha(21),
                "dense_sha256": sha(22),
                "index_sha256": sha(23),
                "content_reads": 0,
                "status": "read_failed",
                "observed_sha256": None,
            },
        ),
        "a0x-output-occupancy-receipt.schema.json": ("a0x-output-occupancy-receipt", {"allocated_bytes": 28049408, "total_bytes": 28049408, "cap_bytes": 33554432}),
        "a0x-representation-record.schema.json": ("a0x-representation-record", {"representation_path": "results/a0x/a0/gpt2/representation.json"}),
        "a0x-statistical-result.schema.json": ("a0x-statistical-result", {"result_status": "completed", "p_value": 0.5}),
    }
    if name in pair_artifacts:
        artifact_class, fields = pair_artifacts[name]
        return {**common_fields, "artifact_class": artifact_class, "pair_binding": pair, **fields}
    if name == "a0x-terminal-result.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-terminal-result",
            "pair_binding": pair,
            "status": "positive",
            "analysis_target_content_reads": 1,
            "target_read_receipt_sha256": sha(24),
            "statistical_result": {"p_value": 0.5, "result_status": "completed"},
        }
    if name == "a0x-publication-manifest.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-publication-manifest",
            "pair_binding": pair,
            "publication_status": "draft",
            "report_input_path": "results/a0x/a0/gpt2/terminal-result.json",
        }
    raise KeyError(name)


class A0XTempTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.temp_path = Path(self._temporary_directory.name)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def write_json(self, relative_path: str, value: object) -> Path:
        path = self.temp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return path
