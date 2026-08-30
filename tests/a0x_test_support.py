from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from latent_triz.a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    Leg,
    PairBinding,
    canonical_commitment,
    compute_dense_bound,
)


def sha(value: int) -> str:
    return f"{value:064x}"[-64:]


def qualification_receipt(source_head: str, *, generation: int = 1, version: str = "commit-ci-preflight 0.1.0") -> bytes:
    """Return a strict synthetic PASS receipt envelope for boundary tests."""
    receipt = {
        "schema_version": "2.0",
        "producer": {
            "name": "commit-ci-preflight",
            "version": version.removeprefix("commit-ci-preflight ") + "+matrix-v2-legacy-v1",
        },
        "repository": {
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "commit_sha": source_head,
            "dirty": False,
        },
        "run": {"generation": generation},
        "overall_status": "PASS",
        "incomplete_reason": None,
    }
    receipt_raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    envelope = {
        "receipt_id": "sha256:" + hashlib.sha256(receipt_raw).hexdigest(),
        "receipt": receipt,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")


def identity(leg: Leg = Leg.A0) -> dict[str, str]:
    return {
        "leg": leg.value,
        "protocol_id": f"a0x-{leg.value}-replication-v1",
        "protected_tree_sha256": sha(1),
        "selection_corpus_sha256": sha(2),
        "source_base_commit": "a" * 40,
    }


def pair_binding(leg: Leg = Leg.A0, model_key: str = "gpt2", hidden_width: int = 1024) -> dict[str, object]:
    dense = asdict(compute_dense_bound(leg, cases=48, hidden_width=hidden_width))
    dense["leg"] = leg.value
    return PairBinding(
            binding_profile="a0x-pair-scope-v2",
            leg=leg,
            leg_freeze_sha256=sha(3),
            model_key=model_key,
            model_id="openai-community/gpt2",
            revision="b" * 40,
            run_id=f"a0x-{leg.value}-{model_key}-run-1",
            output_path=f"results/a0x/{leg.value}/{model_key}/",
        dense_bound=dense,
    ).as_mapping()


def common() -> dict[str, object]:
    return {
        "empirical": True,
        "scientific_status": "exploratory",
        "evidence_eligible": False,
        "expert_validated": False,
        "claim_ids": [],
    }


def authorization_documents(pair: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    from latent_triz.a0x_material_contract import derive_runtime_paths

    binding = PairBinding.from_mapping(pair)
    implementation_source_head = "b" * 40
    source_head = "a" * 40
    runtime_paths = derive_runtime_paths(binding, source_head=source_head)
    dossier = {
        **common(),
        "artifact_class": "a0x-authorization-dossier",
        "commitment_profile": APPROVAL_DOSSIER_PROFILE,
        "pair_binding": pair,
        "dossier_status": "approval_requested",
        "implementation_source_head": implementation_source_head,
        "material_contract_path": "experiments/a0x-six-model/material-execution-contract.json",
        "material_contract_raw_sha256": sha(900),
        "runtime_authorization_path": runtime_paths.authorization_path,
    }
    dossier_commitment = canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping()
    authorization = {
        **common(),
        "artifact_class": "a0x-execution-authorization",
        "commitment_profile": EXECUTION_AUTHORIZATION_PROFILE,
        "pair_binding": pair,
        "authorization_status": "authorized",
        "approved_dossier_commitment": dossier_commitment,
        "repository": "MarcoPorcellato/Latent-TRIZ",
        "implementation_source_head": implementation_source_head,
        "source_head": source_head,
        "material_contract_raw_sha256": sha(900),
        "ccp": {
            "executable_name": "commit-ci-preflight",
            "source_commit": "27adf8d0820b3cd96f9c5e149de9b580ae41f639",
            "qualified_source_tree": "d8e0364d1313fde0898a44517ae6d233d9e10763",
            "sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4",
            "version": "commit-ci-preflight 0.1.0",
        },
        "authorization_inlet_path": runtime_paths.authorization_path,
        "guard_launch": {
            "launch_profile": "a0x-guard-launch-v2",
            "ccp": {"role": "ccp", "sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4"},
            "python": {"role": "python", "sha256": sha(903)},
            "cwd_kind": "repository_root",
            "source_head": source_head,
            "child_script": {"role": "child", "path": "scripts/a0x_material_child.py", "sha256": sha(904)},
            "launch_descriptor": {"role": "descriptor", "path": runtime_paths.launch_descriptor_path, "sha256": sha(905)},
            "environment_template": ["HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1", "HF_DATASETS_OFFLINE=1", "TOKENIZERS_PARALLELISM=false", "PYTHONNOUSERSITE=1"],
            "resource": {"profile": "a0x-material", "workload_family": "latent-triz-a0x-v1", "executor": "native", "cache_state": "warm", "execution_mode": "native", "target_platform": "macos-arm64", "memory_limit_bytes": 8589934592},
            "timeouts": {"outer_timeout_seconds": 3600, "internal_budget_seconds": 3300, "cleanup_margin_seconds": 300, "admission_timeout_seconds": 300},
            "argv_template": ["{CCP}", "guard", "exec", "--admission-timeout-seconds", "300", "--timeout-seconds", "3600", "--resource-profile", "a0x-material", "--resource-workload-family", "latent-triz-a0x-v1", "--resource-executor", "native", "--resource-cache-state", "warm", "--resource-execution-mode", "native", "--resource-target-platform", "macos-arm64", "--resource-memory-limit-bytes", "8589934592", "--", "{PYTHON}", "{CHILD}", "--launch-descriptor", "{DESCRIPTOR}"],
        },
        "guard_preflight_observation": {"profile": "a0x-guard-preflight-observation-v1", "path": runtime_paths.observation_directory + "guard-preflight-observation.json"},
        "qualification_evidence": {
            "artifact_class": "a0x-qualification-evidence",
            "evidence_profile": "a0x-qualification-evidence-v1",
            "qualification_receipt_id": f"sha256:{sha(906)}",
            "qualification_receipt_raw_sha256": sha(907),
            "qualified_source_head": source_head,
            "generation": 1,
            "ccp": {"executable_name": "commit-ci-preflight", "source_commit": "27adf8d0820b3cd96f9c5e149de9b580ae41f639", "qualified_source_tree": "d8e0364d1313fde0898a44517ae6d233d9e10763", "binary_sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4", "version": "commit-ci-preflight 0.1.0"},
            "public_evidence": {"branch": f"ccp-evidence/{source_head}", "path": ".ccp/receipt.json", "commit": "e" * 40},
        },
        "max_guard_exec_count": 1,
        "stop_boundary": "after_one_sealed_target_read",
        "authorization_id": "synthetic-authorization",
        "attempt_id": "synthetic-attempt",
    }
    authorization_commitment = canonical_commitment(
        authorization, EXECUTION_AUTHORIZATION_PROFILE,
    ).as_mapping()
    chain = {
        "dossier_commitment": dossier_commitment,
        "authorization_commitment": authorization_commitment,
    }
    return dossier, authorization, chain


def rich_statistical_result(
    pair: dict[str, object] | None = None, *, status: str = "positive", authorization_chain: dict[str, object] | None = None,
) -> dict[str, object]:
    """A complete A0X-A0 statistical artifact fixture for strict schemas."""
    binding = pair_binding() if pair is None else pair
    metric = {
        "family_successes": 20,
        "family_success_rate": 20 / 24,
        "family_success_wilson_95": [0.6, 0.95],
        "macro_f1": 0.8,
        "accuracy": 0.8,
        "per_domain_accuracy": {"domain-0": 0.8},
    }
    primary_names = [
        f"tuple-{tuple_index}::{site}"
        for tuple_index in (0, 2, 4, 6)
        for site in ("sentinel", "final_transformation_token", "mean_transformation_span")
    ]
    final_names = [
        "problem_only::sentinel",
        *[
            f"{view}::{site}"
            for view in ("transformation_only", "problem_plus_transformation", "problem_plus_solution")
            for site in ("sentinel", "final_transformation_token", "mean_transformation_span")
        ],
    ]
    chain = authorization_documents(binding)[2] if authorization_chain is None else authorization_chain
    return {
        **common(),
        "artifact_class": "a0x-statistical-result",
        "pair_binding": binding,
        "authorization_chain": chain,
        "status": status,
        "score_quantization_decimals": 12,
        "p_value": 0.01 if status == "positive" else 0.5,
        "primary": {
            "multiplicity": 12,
            "combinations": {name: dict(metric) for name in primary_names},
            "observed_max_family_successes": 20,
            "max_statistic_p": 0.01 if status == "positive" else 0.5,
            "maximum_macro_f1": 0.8,
            "null_maxima_sha256": sha(110),
        },
        "surface_baseline": {
            "multiplicity": 4,
            "combinations": {f"tuple-{tuple_index}::sentinel": dict(metric) for tuple_index in (0, 2, 4, 6)},
            "maximum_macro_f1": 0.6,
        },
        "macro_f1_margin_over_surface": 0.2,
        "descriptive_final_block": {
            "rescues_primary": False,
            "tuple_index": 12,
            "combinations": {name: dict(metric) for name in final_names},
        },
        "outcome_rule": {
            "max_statistic_p_at_most": 0.05,
            "macro_f1_margin_at_least": 0.10,
            "family_successes_at_least": 19,
            "passed": status == "positive",
        },
    }


def rich_r1_statistical_result(
    pair: dict[str, object] | None = None, *, status: str = "positive", authorization_chain: dict[str, object] | None = None,
) -> dict[str, object]:
    """A complete frozen R1 result fixture, separate from the A0 grid."""
    binding = pair_binding(Leg.R1) if pair is None else pair
    metric = {
        "family_successes": 17,
        "family_success_rate": 17 / 24,
        "family_success_wilson_95": [0.5, 0.85],
        "macro_f1": 0.8,
        "accuracy": 0.8,
        "per_domain_accuracy": {f"domain-{index}": 0.8 for index in range(6)},
    }
    passed = status == "positive"
    chain = authorization_documents(binding)[2] if authorization_chain is None else authorization_chain
    return {
        **common(), "artifact_class": "a0x-statistical-result", "pair_binding": binding, "authorization_chain": chain,
        "status": status, "p_value": 0.05 if passed else 0.5, "score_quantization_decimals": 12,
        "primary": {"tuple_index": 6, **metric, "max_statistic_p": 0.05 if passed else 0.5, "permutation_seed": 20260815, "permutation_budget": 999, "null_distribution_sha256": sha(121)},
        "surface_baseline": {"tuple_index": 6, **{**metric, "macro_f1": 0.6}},
        "macro_f1_margin_over_surface": 0.2,
        "domain_direction_successes": {f"domain-{index}": 1.0 for index in range(6)},
        "domain_direction_success_count": 6,
        "descriptive_final_block": {"rescues_primary": False, "tuple_index": 12, "primary_analogue": dict(metric), "surface_baseline_analogue": dict(metric)},
        "outcome_rule": {"permutation_p_at_most": 0.05, "macro_f1_margin_at_least": 0.10, "family_successes_at_least": 17, "positive_direction_domains_at_least": 4, "passed": passed},
    }


def artifact(name: str) -> dict[str, object]:
    common_fields = common()
    pair = pair_binding()
    dossier, authorization, chain = authorization_documents(pair)
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
            "descriptive_final_block_endpoint": {
                "model_card_index_field": "final_transformer_block_tuple_index",
                "required_equal_model_card_field": "num_hidden_layers",
                "role": "descriptive_sensitivity",
                "rescues_primary": False,
            },
            "source_protocol_path": "experiments/a0-automated-weak-proxy/protocol.json",
            "source_protocol_raw_sha256": sha(30),
            "inherited_rules": {"views": ["problem_plus_transformation"]},
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
        }
    if name == "a0x-implementation.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-leg-implementation",
            "identity": identity(),
            "implementation_status": "frozen_before_model_output",
            "source_implementation_path": "experiments/a0-automated-weak-proxy/implementation.json",
            "source_implementation_raw_sha256": sha(31),
            "inherited_rules": {"primary_view": "problem_plus_transformation"},
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
            "implementation_paths": ["src/latent_triz/a0x_contract.py"],
            "implementation_files": [{
                "path": "src/latent_triz/a0x_contract.py", "bytes": 1, "sha256": sha(32),
            }],
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
        "a0x-model-identity-receipt.schema.json": ("a0x-model-identity-receipt", {"identity_status": "verified"}),
        "a0x-ccp-observation.schema.json": ("a0x-guard-preflight-observation", {
            "observation_profile": "a0x-guard-preflight-observation-v1",
            "source_head": "a" * 40,
            "ccp": {"role": "ccp", "source_commit": "27adf8d0820b3cd96f9c5e149de9b580ae41f639", "qualified_source_tree": "d8e0364d1313fde0898a44517ae6d233d9e10763", "sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4", "version": "commit-ci-preflight 0.1.0"},
            "source": {"head": "a" * 40, "clean": True},
            "resource": {"decision": "admit"},
            "admission": {"active": False, "queue_count": 0, "slot_state": "free"},
            "runtime": {"intended_runtime_responsive": True, "active_container_count": 0},
            "commands": [{"role": role, "exit_code": 0, "output_sha256": sha(index), "output_bytes": index} for index, role in enumerate(("ccp_version", "resource_status", "admission_status", "git_source_state", "docker_context", "docker_active_count"), 1)],
        }),
        "a0x-preflight-receipt.schema.json": ("a0x-preflight-receipt", {"preflight_status": "passed", "model_key": "gpt2", "origin": "a" * 40, "endpoint_availability": {}, "source_head": "a" * 40, "material_contract_raw_sha256": sha(303), "ccp_observation_path": "a0x-ccp-observation.json", "ccp_observation_raw_sha256": sha(304)}),
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
        "a0x-representation-record.schema.json": ("a0x-representation-record", {"representation_path": "results/a0x/a0/gpt2/representation.json"}),
    }
    if name == "a0x-authorization-dossier.schema.json":
        return dossier
    if name == "a0x-execution-authorization.schema.json":
        return authorization
    if name == "a0x-guard-launch.schema.json":
        return authorization["guard_launch"]
    if name == "a0x-qualification-evidence.schema.json":
        return authorization["qualification_evidence"]
    if name == "a0x-qualification-authorization.schema.json":
        return {
            **common_fields, "artifact_class": "a0x-qualification-authorization",
            "commitment_profile": "a0x-qualification-authorization-json-v2",
            "qualification_status": "authorized", "repository": "MarcoPorcellato/Latent-TRIZ",
            "source_head": "a" * 40, "material_contract_raw_sha256": sha(900),
            "ccp": {"producer_role": "ccp_executable", "source_commit": "27adf8d0820b3cd96f9c5e149de9b580ae41f639", "source_tree": "d8e0364d1313fde0898a44517ae6d233d9e10763", "sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4", "version": "commit-ci-preflight 0.1.0", "matrix_plan_profile": "matrix-v2-legacy-v1", "plan_output_sha256": "0969a1eeb62b2a92593cda0b75c8814d7eca893bebc736ec968f02aa9f2a5fad", "outer_digest": "sha256:8eb0172c30aac8f9b47f65cebd222ee6615b17e4053a5a16e2be5583f3a10331", "python311_digest": "sha256:aa69a8795e20733a516fac99b253cfc26a9f963825ff1fa9ca5638364f7fc943", "python312_digest": "sha256:072e50972a02f2df710bf81620ca058d230f0637bcc16a47ba35562fe1358510"},
            "generation": 1, "max_qualification_run_count": 1,
            "stop_boundary": "after_repository_qualification_receipt",
            "authorization_id": "synthetic-qualification",
        }
    if name == "a0x-material-execution-contract.schema.json":
        return {
            "artifact_class": "a0x-material-execution-contract",
            "contract_version": "a0x-material-execution-contract-v2",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "ccp": {
                "producer_role": "ccp_executable",
                "source_commit": "27adf8d0820b3cd96f9c5e149de9b580ae41f639",
                "source_tree": "d8e0364d1313fde0898a44517ae6d233d9e10763",
                "sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4",
                "version": "commit-ci-preflight 0.1.0",
                "qualification_status": "terminal_heavy_qualified",
                "command_roles": ["admission_status", "resource_status", "plan", "doctor", "dry_run", "repository_run", "guard_exec"],
                "hash_before_command": True,
                "matrix_plan_profile": "matrix-v2-legacy-v1",
                "matrix_config_binding": {"locator": ".commit-ci-preflight.toml", "raw_sha256": "78d0ce348a864ea99a1a7018bc00403bdd2349b5f7f6e39d6a61ec10714a20fd"},
                "matrix_policy_binding": {"locator": ".commit-ci-policy-v2.toml", "raw_sha256": "258361889b30ee6c18f3c2cd901672d43827c786cc05c599eb7f9cb09cb65048"},
                "location_roles": {"repository_root": "repository_root", "managed_cache_root": "managed_cache_root"},
                "matrix_plan_binding": {"plan_output_sha256": "0969a1eeb62b2a92593cda0b75c8814d7eca893bebc736ec968f02aa9f2a5fad", "outer_digest": "sha256:8eb0172c30aac8f9b47f65cebd222ee6615b17e4053a5a16e2be5583f3a10331", "python311_digest": "sha256:aa69a8795e20733a516fac99b253cfc26a9f963825ff1fa9ca5638364f7fc943", "python312_digest": "sha256:072e50972a02f2df710bf81620ca058d230f0637bcc16a47ba35562fe1358510"},
            },
            "offline": {"network": False, "generation": False, "local_cpu_float32": True},
            "max_run_count": 1,
            "stop_boundaries": ["before_model_load", "after_first_terminal_outcome", "after_one_sealed_target_read"],
        }
    if name == "a0x-attempt-claim.schema.json":
        return {
            "artifact_class": "a0x-attempt-claim", "claim_version": "a0x-attempt-claim-v1",
            "pair_binding": pair, "authorization_chain": chain, "authorization_id": "synthetic-auth",
            "attempt_id": "synthetic-attempt", "material_contract_raw_sha256": sha(700), "state": "reserved",
        }
    if name == "a0x-activation-stage-occupancy-receipt.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-activation-stage-occupancy-receipt",
            "pair_binding": pair,
            "authorization_chain": chain,
            "leg": "a0",
            "occupancy_scope": "activation_stage",
            "included_paths": ["activations.safetensors", "representations-index.jsonl"],
            "actual_total_bytes": 1,
            "cap_bytes": 33554432,
        }
    if name == "a0x-ccp-observation.schema.json":
        artifact_class, fields = pair_artifacts[name]
        return {"artifact_class": artifact_class, "pair_binding": pair, **fields}
    if name in pair_artifacts:
        artifact_class, fields = pair_artifacts[name]
        return {**common_fields, "artifact_class": artifact_class, "pair_binding": pair, "authorization_chain": chain, **fields}
    if name == "a0x-external-assets-locator.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-external-assets-locator",
            "locator_profile": "a0x-external-assets-locator-v1",
            "pair_binding": pair,
            "authorization_chain": chain,
            "assets": [
                {"role": "dense", "repository_relative_path": "external/a0/gpt2/activations.safetensors", "bytes": 1024, "raw_sha256": sha(401)},
                {"role": "index", "repository_relative_path": "external/a0/gpt2/representations-index.jsonl", "bytes": 512, "raw_sha256": sha(402)},
            ],
        }
    if name == "a0x-output-occupancy-receipt.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-output-occupancy-receipt",
            "occupancy_profile": "a0x-complete-attempt-root-v2",
            "occupancy_scope": "complete_attempt",
            "pair_binding": pair,
            "authorization_chain": chain,
            "manifest_package_relative_path": "publication-manifest.json",
            "manifest_raw_sha256": sha(403),
            "activation_receipt_raw_sha256": sha(404),
            "component_bytes": {
                "manifest": 256,
                "package_artifacts": 2048,
                "external_outputs": 1536,
                "source_inputs": 1024,
                "retained_residue": 0,
            },
            "final_bytes_excluding_this_receipt": 3840,
            "peak_bytes_before_this_receipt": 3840,
            "cap_bytes": 33554432,
            "runtime_checkpoints": [
                {"phase": "pre_manifest_write", "bytes": 3584},
                {"phase": "pre_root_receipt_write", "bytes": 3840},
            ],
            "self_counting_rule": "final_bytes_excluding_this_receipt + serialized_root_receipt_bytes <= cap_bytes",
        }
    if name == "a0x-statistical-result.schema.json":
        return rich_statistical_result(pair, authorization_chain=chain)
    if name == "a0x-terminal-result.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-terminal-result",
            "pair_binding": pair,
            "authorization_chain": chain,
            "status": "positive",
            "sealed_from_state": "analysis",
            "analysis_target_content_reads": 1,
            "target_read_receipt_sha256": sha(24),
            "statistical_result": rich_statistical_result(pair, authorization_chain=chain),
        }
    if name == "a0x-publication-manifest.schema.json":
        return {
            **common_fields,
            "artifact_class": "a0x-publication-manifest",
            "pair_binding": pair,
            "authorization_chain": chain,
            "manifest_profile": "a0x-terminal-package-v1",
            "root_receipt_profile": "a0x-complete-attempt-root-v2",
            "root_receipt_package_relative_path": "output-occupancy-receipt.json",
            "terminal_status": "positive",
            "package_status": "complete",
            "package_artifacts": [
                {"role": "authorization_record", "path": "execution-authorization.json", "bytes": 256, "raw_sha256": sha(301)},
                {"role": "model_identity_receipt", "path": "model-identity-receipt.json", "bytes": 256, "raw_sha256": sha(302)},
                {"role": "ccp_observation", "path": "ccp-observation.json", "bytes": 256, "raw_sha256": sha(303)},
                {"role": "preflight_receipt", "path": "preflight-receipt.json", "bytes": 256, "raw_sha256": sha(304)},
                {"role": "activation_receipt", "path": "activation-receipt.json", "bytes": 256, "raw_sha256": sha(305)},
                {"role": "target_read_receipt", "path": "target-read-receipt.json", "bytes": 256, "raw_sha256": sha(306)},
                {"role": "statistical_result", "path": "statistical-result.json", "bytes": 256, "raw_sha256": sha(307)},
                {"role": "terminal_result", "path": "terminal-result.json", "bytes": 256, "raw_sha256": sha(308)},
                {"role": "external_assets_locator", "path": "external-assets-locator.json", "bytes": 256, "raw_sha256": sha(309)},
                {"role": "report", "path": "report.md", "bytes": 256, "raw_sha256": sha(310)},
            ],
            "external_outputs": [
                {"role": "dense", "repository_relative_path": "external/a0/gpt2/activations.safetensors", "bytes": 1024, "raw_sha256": sha(401)},
                {"role": "index", "repository_relative_path": "external/a0/gpt2/representations-index.jsonl", "bytes": 512, "raw_sha256": sha(402)},
            ],
            "source_inputs": [
                {"role": "dossier", "repository_relative_path": "experiments/a0x-six-model/a0/gpt2/approval-dossier.json", "bytes": 256, "raw_sha256": sha(311)},
                {"role": "authorization", "repository_relative_path": "results/a0x/a0/gpt2/execution-authorization.json", "bytes": 256, "raw_sha256": sha(312)},
            ],
            "retained_residue": [],
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
