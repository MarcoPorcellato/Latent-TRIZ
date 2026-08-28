from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import Leg, PairBinding
from latent_triz.a0x_preflight import (
    A0XPreflightError,
    load_model_card,
    load_registry,
    require_empty_output,
    verify_snapshot_files,
    verify_static_preflight,
    verify_card_sources,
    verify_static_endpoint_availability,
)
from tests.a0x_test_support import A0XTempTestCase, artifact, authorization_documents, pair_binding


ROOT = Path(__file__).resolve().parents[1]
VISIBILITY_NOTE = "No process visible in the local shell does not prove global inactivity."


def stable_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def valid_ccp_raw_observations() -> tuple[dict[str, object], dict[str, object]]:
    return (
        {
            "schema_version": "1.0",
            "policy_version": "macos-v4",
            "platform": "macos",
            "capability": "supported_enforced",
            "decision": "admit",
            "available_percent": 40,
            "reclaimable_uncompressed_bytes": 7_800_000_000,
            "compressor_occupied_bytes": 6_900_000_000,
            "total_memory_bytes": 16_000_000_000,
            "swap_used_bytes": 4_000_000_000,
            "swap_total_bytes": 5_000_000_000,
            "consecutive_soft_samples": 0,
        },
        {
            "schema_version": "2.0",
            "active": False,
            "queue_count": 0,
            "ticket_ids": [],
            "slot": {
                "kind": "slot_lock",
                "state": "free",
                "owner_run_id": None,
                "acquired_at_unix_seconds": None,
                "heartbeat_at_unix_seconds": None,
                "lease_state": "not_applicable",
            },
            "queue_lock": {
                "kind": "queue_lock",
                "state": "free",
                "owner_run_id": None,
                "acquired_at_unix_seconds": None,
                "heartbeat_at_unix_seconds": None,
                "lease_state": "not_applicable",
            },
            "process_visibility_note": VISIBILITY_NOTE,
        },
    )


def valid_ccp_binary_binding() -> dict[str, str]:
    return {
        "role": "ccp_executable",
        "source_commit": "faf587890e4f899803f027660bc66452623f405e",
        "source_tree": "4615028176f3d594fbce0554f5e5edecfb802af1",
        "sha256": "7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8",
        "version": "commit-ci-preflight 0.1.0",
        "resolved_path": "/private/tmp/commit-ci-preflight",
        "expected_role": "ccp_executable",
        "expected_source_commit": "faf587890e4f899803f027660bc66452623f405e",
        "expected_source_tree": "4615028176f3d594fbce0554f5e5edecfb802af1",
        "expected_sha256": "7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8",
        "expected_version": "commit-ci-preflight 0.1.0",
    }


class A0XPreflightTests(A0XTempTestCase):
    def _authorization_bound_preflight_arguments(self) -> tuple[dict[str, object], dict[str, object]]:
        binding = PairBinding.from_mapping(pair_binding())
        dossier, authorization, chain = authorization_documents(binding.as_mapping())
        dossier_path = self.temp_path / "dossier.json"
        authorization_path = self.temp_path / "authorization.json"
        dossier_path.write_bytes(stable_json_bytes(dossier))
        authorization_path.write_bytes(stable_json_bytes(authorization))
        arguments: dict[str, object] = {
            "card": SimpleNamespace(
                model_key=binding.model_key, model_id=binding.model_id,
                revision=binding.revision,
            ),
            "snapshot_root": self.temp_path / "snapshot",
            "expected_origin": "a" * 40,
            "observed_origin": "a" * 40,
            "output_dir": self.temp_path / "preflight",
            "environment": {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
            "pair_binding": binding,
            "protected_trees": ((self.temp_path / "protected-a", {}), (self.temp_path / "protected-b", {})),
            "protected_tree_verifier": lambda *_args, **_kwargs: None,
            "dossier_path": dossier_path,
            "expected_dossier_raw_sha256": hashlib.sha256(dossier_path.read_bytes()).hexdigest(),
            "authorization_path": authorization_path,
            "expected_authorization_raw_sha256": hashlib.sha256(authorization_path.read_bytes()).hexdigest(),
            "ccp_observation": artifact("a0x-ccp-observation.schema.json"),
            "material_contract_raw_sha256": "c" * 64,
            "ccp_observation_path": "ccp-observation.json",
            "ccp_observation_raw_sha256": "d" * 64,
            "authorization_chain": chain,
        }
        return arguments, {"dossier": dossier, "authorization": authorization, "chain": chain}

    def test_static_preflight_binds_exact_source_bytes_to_chain_and_ccp_observation(self) -> None:
        arguments, _documents = self._authorization_bound_preflight_arguments()
        with (
            patch("latent_triz.a0x_preflight.verify_snapshot_files"),
            patch("latent_triz.a0x_preflight.verify_static_endpoint_availability", return_value={}),
        ):
            receipt = verify_static_preflight(**arguments)
        self.assertEqual(arguments["authorization_chain"], receipt["authorization_chain"])

    def test_static_preflight_rejects_swapped_or_unrelated_valid_authorization_chain(self) -> None:
        arguments, _documents = self._authorization_bound_preflight_arguments()
        alternate_pair_data = pair_binding()
        alternate_pair_data["run_id"] = "a0x-a0-gpt2-run-2"
        alternate_pair_data["output_path"] = "results/a0x/a0/gpt2/alternate/"
        alternate_pair = PairBinding.from_mapping(alternate_pair_data)
        alternate_dossier, alternate_authorization, alternate_chain = authorization_documents(alternate_pair.as_mapping())
        alternate_authorization_path = self.temp_path / "alternate-authorization.json"
        alternate_authorization_path.write_bytes(stable_json_bytes(alternate_authorization))

        unrelated_chain = dict(arguments)
        unrelated_chain["authorization_chain"] = alternate_chain
        swapped_source = dict(arguments)
        swapped_source["authorization_path"] = alternate_authorization_path
        swapped_source["expected_authorization_raw_sha256"] = hashlib.sha256(
            alternate_authorization_path.read_bytes(),
        ).hexdigest()
        swapped_source["authorization_chain"] = alternate_chain
        del alternate_dossier

        for label, candidate in (("unrelated-chain", unrelated_chain), ("swapped-source", swapped_source)):
            with self.subTest(label=label), self.assertRaisesRegex(A0XPreflightError, "authorization"):
                with (
                    patch("latent_triz.a0x_preflight.verify_snapshot_files"),
                    patch("latent_triz.a0x_preflight.verify_static_endpoint_availability", return_value={}),
                ):
                    verify_static_preflight(**candidate)

    def test_registry_contains_only_six_non_pythia_cards(self) -> None:
        cards = load_registry(ROOT / "experiments/a0x-six-model/model-registry.json")
        self.assertEqual(
            tuple(card.model_key for card in cards),
            (
                "smollm2_360m",
                "qwen3_0_6b_base",
                "gpt2",
                "smollm2_135m",
                "gpt_neo_125m",
                "qwen2_5_0_5b",
            ),
        )

    def test_registry_rejects_card_identity_drift_with_unchanged_model_key(self) -> None:
        registry = ROOT / "experiments/a0x-six-model/model-registry.json"
        cards = load_registry(registry)
        mutations = (
            {"model_id": "HuggingFaceTB/SmolLM2-360M-drift"},
            {"revision": "0" * 40},
            {"runtime_root": "artifacts/models/drift"},
        )
        for mutation in mutations:
            drifted = replace(cards[0], **mutation)
            with self.subTest(mutation=mutation), patch(
                "latent_triz.a0x_preflight.load_model_card",
                side_effect=(drifted, *cards[1:]),
            ), self.assertRaisesRegex(A0XPreflightError, "identity"):
                load_registry(registry)

    def test_gpt2_requires_fast_runtime_type_and_offsets(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        self.assertIsNone(card.tokenizer_metadata_class)
        self.assertEqual("GPT2TokenizerFast", card.expected_runtime_tokenizer_class)
        self.assertTrue(card.fast_offsets_required)
        self.assertEqual("gpt2", card.model_type)
        self.assertEqual(12, card.num_hidden_layers)
        self.assertEqual(768, card.hidden_size)

    def test_every_card_separates_pinned_metadata_from_required_fast_runtime(self) -> None:
        expected = {
            "smollm2_360m": ("GPT2Tokenizer", "GPT2TokenizerFast"),
            "qwen3_0_6b_base": ("Qwen2Tokenizer", "Qwen2TokenizerFast"),
            "gpt2": (None, "GPT2TokenizerFast"),
            "smollm2_135m": ("GPT2Tokenizer", "GPT2TokenizerFast"),
            "gpt_neo_125m": ("GPT2Tokenizer", "GPT2TokenizerFast"),
            "qwen2_5_0_5b": ("Qwen2Tokenizer", "Qwen2TokenizerFast"),
        }
        for card in load_registry(ROOT / "experiments/a0x-six-model/model-registry.json"):
            with self.subTest(card=card.model_key):
                metadata, runtime = expected[card.model_key]
                self.assertEqual(metadata, card.tokenizer_metadata_class)
                self.assertEqual(runtime, card.expected_runtime_tokenizer_class)
                self.assertTrue(card.fast_offsets_required)

    def test_all_cards_bind_a_tracked_integrity_receipt_and_allowlist(self) -> None:
        for card in load_registry(ROOT / "experiments/a0x-six-model/model-registry.json"):
            with self.subTest(card=card.model_key):
                self.assertTrue((ROOT / card.source_receipt_path).is_file())
                self.assertEqual(64, len(card.source_receipt_sha256))
                self.assertTrue(card.runtime_files)
                self.assertEqual("config.json", card.runtime_files[0].path)

    def test_card_sources_reproduce_every_frozen_receipt_and_audit_hash(self) -> None:
        for card in load_registry(ROOT / "experiments/a0x-six-model/model-registry.json"):
            with self.subTest(card=card.model_key):
                verify_card_sources(ROOT, card)

    def test_every_committed_card_is_accepted_by_the_strict_schema(self) -> None:
        from latent_triz.validator import validate

        schema = json.loads((ROOT / "schemas/a0x-model-card.schema.json").read_text(encoding="utf-8"))
        for path in sorted((ROOT / "experiments/a0x-six-model/model-cards").glob("*.json")):
            with self.subTest(card=path.name):
                self.assertEqual([], validate(json.loads(path.read_text(encoding="utf-8")), schema))

    def test_snapshot_verifier_accepts_exact_allowlist_without_model_construction(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        snapshot = self.temp_path / "gpt2"
        snapshot.mkdir()
        config = {
            "model_type": card.model_type,
            "architectures": [card.architecture],
            "n_layer": card.num_hidden_layers,
            "n_embd": card.hidden_size,
            "vocab_size": card.vocab_size,
            "n_positions": card.effective_context,
        }
        for file in card.runtime_files:
            payload = stable_json_bytes(config) if file.path == "config.json" else (file.path + "\n").encode("utf-8")
            (snapshot / file.path).write_bytes(payload)
        synthetic = card.with_runtime_files(
            tuple(
                item.with_integrity(size_bytes=(snapshot / item.path).stat().st_size, sha256=hashlib.sha256((snapshot / item.path).read_bytes()).hexdigest())
                for item in card.runtime_files
            )
        )
        verified = verify_snapshot_files(snapshot, synthetic)
        self.assertEqual(card.model_key, verified.model_key)

    def test_snapshot_verifier_rejects_extra_missing_hash_and_config_drift(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        snapshot = self.temp_path / "gpt2"
        snapshot.mkdir()
        for file in card.runtime_files:
            (snapshot / file.path).write_bytes(b"x")
        with self.assertRaisesRegex(A0XPreflightError, "snapshot"):
            verify_snapshot_files(snapshot, card)

    def test_snapshot_verifier_rejects_empty_directories_and_config_drift_after_integrity(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        snapshot = self.temp_path / "snapshot"
        snapshot.mkdir()
        config = {"model_type": card.model_type, "architectures": [card.architecture], "n_layer": card.num_hidden_layers, "n_embd": card.hidden_size, "vocab_size": card.vocab_size, "n_positions": card.effective_context}
        for file in card.runtime_files:
            payload = stable_json_bytes(config) if file.path == "config.json" else (file.path + "\n").encode()
            (snapshot / file.path).write_bytes(payload)
        synthetic = card.with_runtime_files(tuple(item.with_integrity(size_bytes=(snapshot / item.path).stat().st_size, sha256=hashlib.sha256((snapshot / item.path).read_bytes()).hexdigest()) for item in card.runtime_files))
        (snapshot / "empty").mkdir()
        with self.assertRaisesRegex(A0XPreflightError, "unallowlisted"):
            verify_snapshot_files(snapshot, synthetic)
        (snapshot / "empty").rmdir()
        config["n_layer"] = 13
        (snapshot / "config.json").write_bytes(stable_json_bytes(config))
        drifted = synthetic.with_runtime_files(tuple(item.with_integrity(size_bytes=(snapshot / item.path).stat().st_size, sha256=hashlib.sha256((snapshot / item.path).read_bytes()).hexdigest()) for item in synthetic.runtime_files))
        with self.assertRaisesRegex(A0XPreflightError, "layer"):
            verify_snapshot_files(snapshot, drifted)

    def test_static_endpoint_availability_rejects_missing_literal_or_final_identity(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        self.assertEqual(12, verify_static_endpoint_availability(card=card, leg=Leg.A0)["final_transformer_block_tuple_index"])
        with self.assertRaisesRegex(A0XPreflightError, "literal"):
            verify_static_endpoint_availability(card=card.__class__(**{**card.__dict__, "num_hidden_layers": 4, "final_transformer_block_tuple_index": 4}), leg=Leg.A0)
        with self.assertRaisesRegex(A0XPreflightError, "identity"):
            verify_static_endpoint_availability(card=card.__class__(**{**card.__dict__, "final_transformer_block_tuple_index": 11}), leg=Leg.R1)

    def test_public_ccp_contract_schemas_expose_only_roles_and_hash_bound_identity(self) -> None:
        schemas = (
            ROOT / "schemas/a0x-material-execution-contract.schema.json",
            ROOT / "schemas/a0x-qualification-authorization.schema.json",
        )
        for path in schemas:
            with self.subTest(path=path.name):
                serialized = path.read_text(encoding="utf-8")
                # The schemas deliberately mention ``file://`` only in a
                # negative validator pattern; no host-derived value may occur.
                for forbidden in ("/Users/", "/private/", "/tmp/", "commit-ci-preflight-build-v1"):
                    self.assertNotIn(forbidden, serialized)
                self.assertIn("ccp_executable", serialized)
                self.assertIn("faf587890e4f899803f027660bc66452623f405e", serialized)
                self.assertIn("4615028176f3d594fbce0554f5e5edecfb802af1", serialized)
                self.assertIn("7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8", serialized)

    def test_material_contract_selects_the_terminally_qualified_corrected_producer(self) -> None:
        contract = json.loads(
            (ROOT / "experiments/a0x-six-model/material-execution-contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            {
                "source_commit": "faf587890e4f899803f027660bc66452623f405e",
                "source_tree": "4615028176f3d594fbce0554f5e5edecfb802af1",
                "sha256": "7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8",
                "qualification_status": "terminal_heavy_qualified",
            },
            {
                name: contract["ccp"][name]
                for name in ("source_commit", "source_tree", "sha256", "qualification_status")
            },
        )

    def test_public_contract_schemas_reject_host_locators_and_producer_drift(self) -> None:
        from latent_triz.validator import validate

        ccp = {
            "producer_role": "ccp_executable",
            "source_commit": "faf587890e4f899803f027660bc66452623f405e",
            "source_tree": "4615028176f3d594fbce0554f5e5edecfb802af1",
            "sha256": "7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8",
            "version": "commit-ci-preflight 0.1.0",
            "qualification_status": "terminal_heavy_qualified",
            "command_roles": ["admission_status", "resource_status", "plan", "doctor", "dry_run", "repository_run", "guard_exec"],
            "hash_before_command": True,
            "matrix_plan_profile": "matrix-v2-legacy-v1",
            "matrix_config_binding": {"locator": ".commit-ci-preflight.toml", "raw_sha256": "a" * 64},
            "matrix_policy_binding": {"locator": ".commit-ci-policy-v2.toml", "raw_sha256": "b" * 64},
            "location_roles": {"repository_root": "repository_root", "managed_cache_root": "managed_cache_root"},
            "matrix_plan_binding": {
                "plan_output_sha256": "4f401a3c13d94c48c722137511515bdb70099b596bbdb9756ec2cb491282e9e",
                "outer_digest": "sha256:13f4cb39b7e1a8ed31cae64502cc8e4d80d040230d3fb410a6afc3bad3b76178",
                "python311_digest": "sha256:eff5b7d55bb0220890dbfb050bb68a1e0fbba8f9a30a69e2f66085354fcc8562",
                "python312_digest": "sha256:7afb3e6dd435d9d5a317e4d9d85e80527431044312bbe299e9a70b6ba9e994c8",
            },
        }
        contract = {
            "artifact_class": "a0x-material-execution-contract",
            "contract_version": "a0x-material-execution-contract-v2",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "ccp": ccp,
            "offline": {"network": False, "generation": False, "local_cpu_float32": True},
            "max_run_count": 1,
            "stop_boundaries": ["before_model_load", "after_first_terminal_outcome", "after_one_sealed_target_read"],
        }
        contract_schema = json.loads((ROOT / "schemas/a0x-material-execution-contract.schema.json").read_text())
        self.assertEqual([], validate(contract, contract_schema))
        for locator in ("/Users/marco1/.cargo/bin/commit-ci-preflight", "file:///private/tmp/x", "../cache", "results/marco1/private.json"):
            mutated = copy.deepcopy(contract)
            mutated["ccp"]["matrix_config_binding"]["locator"] = locator
            with self.subTest(locator=locator):
                self.assertTrue(validate(mutated, contract_schema))
        mutated = copy.deepcopy(contract)
        mutated["ccp"]["source_tree"] = "0" * 40
        self.assertTrue(validate(mutated, contract_schema))

        qualification_ccp = {name: ccp[name] for name in ("producer_role", "source_commit", "source_tree", "sha256", "version", "matrix_plan_profile")}
        qualification_ccp.update(ccp["matrix_plan_binding"])
        qualification = {
            "artifact_class": "a0x-qualification-authorization", "claim_ids": [],
            "commitment_profile": "a0x-qualification-authorization-json-v2", "qualification_status": "authorized",
            "empirical": True, "evidence_eligible": False, "expert_validated": False, "scientific_status": "exploratory",
            "repository": "MarcoPorcellato/Latent-TRIZ", "source_head": "c" * 40,
            "material_contract_raw_sha256": "d" * 64, "ccp": qualification_ccp,
            "generation": 1, "max_qualification_run_count": 1,
            "stop_boundary": "after_repository_qualification_receipt", "authorization_id": "qualified-once",
        }
        qualification_schema = json.loads((ROOT / "schemas/a0x-qualification-authorization.schema.json").read_text())
        self.assertEqual([], validate(qualification, qualification_schema))
        for identifier in ("file:///private/tmp/leak", "marco1-local-authorization"):
            qualification["authorization_id"] = identifier
            with self.subTest(identifier=identifier):
                self.assertTrue(validate(qualification, qualification_schema))

    def test_empty_output_rejects_files_and_nonempty_directories(self) -> None:
        absent = self.temp_path / "absent"
        require_empty_output(absent)
        file_path = self.temp_path / "file"
        file_path.write_bytes(b"x")
        with self.assertRaisesRegex(A0XPreflightError, "empty"):
            require_empty_output(file_path)
        directory = self.temp_path / "directory"
        directory.mkdir()
        (directory / "x").write_bytes(b"x")
        with self.assertRaisesRegex(A0XPreflightError, "empty"):
            require_empty_output(directory)

    def test_static_preflight_material_interface_is_required(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        with self.assertRaises(TypeError):
            verify_static_preflight(
                card=card,
                expected_origin="188eb65b5e249923baddadeba52659f07fcd1609",
                observed_origin="188eb65b5e249923baddadeba52659f07fcd1609",
                output_dir=self.temp_path / "result",
                environment={},
            )

    def test_static_preflight_rejects_missing_hash_bound_material_inputs(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        snapshot = self.temp_path / "snapshot"
        snapshot.mkdir()
        config = {
            "model_type": card.model_type, "architectures": [card.architecture],
            "n_layer": card.num_hidden_layers, "n_embd": card.hidden_size,
            "vocab_size": card.vocab_size, "n_positions": card.effective_context,
        }
        for file in card.runtime_files:
            payload = stable_json_bytes(config) if file.path == "config.json" else (file.path + "\n").encode("utf-8")
            (snapshot / file.path).write_bytes(payload)
        synthetic_card = card.with_runtime_files(tuple(
            item.with_integrity(size_bytes=(snapshot / item.path).stat().st_size, sha256=hashlib.sha256((snapshot / item.path).read_bytes()).hexdigest())
            for item in card.runtime_files
        ))
        binding_data = pair_binding()
        binding_data.update(model_id=card.model_id, revision=card.revision)
        binding = PairBinding.from_mapping(binding_data)
        observation = artifact("a0x-ccp-observation.schema.json")
        observation["pair_binding"] = binding.as_mapping()
        dossier, authorization = self.temp_path / "dossier.json", self.temp_path / "authorization.json"
        dossier.write_bytes(b"dossier")
        authorization.write_bytes(b"authorization")
        protected = ((self.temp_path / "protected-a", {}), (self.temp_path / "protected-b", {}))
        for root, _tree in protected:
            root.mkdir()
        arguments = {
            "card": synthetic_card, "snapshot_root": snapshot,
            "expected_origin": "a" * 40, "observed_origin": "a" * 40,
            "output_dir": self.temp_path / "result", "environment": {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
            "pair_binding": binding, "protected_trees": protected,
            "protected_tree_verifier": lambda *_args, **_kwargs: None,
            "dossier_path": dossier, "expected_dossier_raw_sha256": hashlib.sha256(dossier.read_bytes()).hexdigest(),
            "authorization_path": authorization, "expected_authorization_raw_sha256": hashlib.sha256(authorization.read_bytes()).hexdigest(),
            "ccp_observation": observation,
            "material_contract_raw_sha256": "c" * 64,
            "ccp_observation_path": "a0x-ccp-observation.json",
            "ccp_observation_raw_sha256": "d" * 64,
            "authorization_chain": authorization_documents(binding.as_mapping())[2],
        }
        for missing in ("dossier", "authorization"):
            changed = dict(arguments)
            changed[f"{missing}_path"] = None
            changed[f"expected_{missing}_raw_sha256"] = None
            with self.subTest(missing=missing), self.assertRaises(A0XPreflightError):
                verify_static_preflight(**changed)
        changed = dict(arguments)
        changed["pair_binding"] = None
        with self.assertRaises(A0XPreflightError):
            verify_static_preflight(**changed)
