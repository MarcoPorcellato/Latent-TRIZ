from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import Leg, PairBinding
from latent_triz.a0x_preflight import (
    A0XPreflightError,
    load_model_card,
    load_registry,
    parse_ccp_observation,
    require_empty_output,
    verify_snapshot_files,
    verify_static_preflight,
    verify_card_sources,
)
from tests.a0x_test_support import A0XTempTestCase, pair_binding


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
        "path": "/private/tmp/commit-ci-preflight",
        "source_commit": "866db18a571f55ed3d9b481d6c9c9c3bd5e98d55",
        "sha256": "a" * 64,
        "version_output": "commit-ci-preflight 0.1.0\n",
        "expected_path": "/private/tmp/commit-ci-preflight",
        "expected_source_commit": "866db18a571f55ed3d9b481d6c9c9c3bd5e98d55",
        "expected_sha256": "a" * 64,
        "expected_version_output": "commit-ci-preflight 0.1.0\n",
    }


class A0XPreflightTests(A0XTempTestCase):
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

    def test_gpt2_requires_fast_runtime_type_and_offsets(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        self.assertEqual("GPT2TokenizerFast", card.tokenizer_class)
        self.assertTrue(card.fast_offsets_required)
        self.assertEqual("gpt2", card.model_type)
        self.assertEqual(12, card.num_hidden_layers)
        self.assertEqual(768, card.hidden_size)

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
        (snapshot / "unexpected.bin").write_bytes(b"x")
        with self.assertRaisesRegex(A0XPreflightError, "snapshot"):
            verify_snapshot_files(snapshot, card)

    def test_unknown_or_busy_ccp_fails_closed(self) -> None:
        resource, admission = valid_ccp_raw_observations()
        for mutator in (
            lambda r, a: r.update(decision="unknown"),
            lambda r, a: a.update(active=True),
            lambda r, a: a.update(queue_count=1),
            lambda r, a: a["slot"].update(state="unknown"),
        ):
            changed_resource, changed_admission = copy.deepcopy(resource), copy.deepcopy(admission)
            mutator(changed_resource, changed_admission)
            with self.subTest(mutator=mutator), self.assertRaises(A0XPreflightError):
                parse_ccp_observation(
                    resource_raw=stable_json_bytes(changed_resource),
                    admission_raw=stable_json_bytes(changed_admission),
                    binary=valid_ccp_binary_binding(),
                    pair_binding=PairBinding.from_mapping(pair_binding()),
                    output_dir=self.temp_path / f"ccp-{len(str(mutator))}",
                )

    def test_ccp_requires_exact_fields_types_binary_and_visibility_binding(self) -> None:
        resource, admission = valid_ccp_raw_observations()
        mutations = (
            lambda r, a, b: r.__setitem__("extra", True),
            lambda r, a, b: r.__setitem__("available_percent", True),
            lambda r, a, b: r.__setitem__("policy_version", "macos-v3"),
            lambda r, a, b: a["slot"].__setitem__("owner_run_id", "opaque"),
            lambda r, a, b: a.__setitem__("process_visibility_note", "wrong"),
            lambda r, a, b: b.__setitem__("sha256", "b" * 64),
        )
        for index, mutate in enumerate(mutations):
            changed_resource, changed_admission, changed_binary = copy.deepcopy(resource), copy.deepcopy(admission), valid_ccp_binary_binding()
            mutate(changed_resource, changed_admission, changed_binary)
            with self.subTest(index=index), self.assertRaises(A0XPreflightError):
                parse_ccp_observation(
                    resource_raw=stable_json_bytes(changed_resource),
                    admission_raw=stable_json_bytes(changed_admission),
                    binary=changed_binary,
                    pair_binding=PairBinding.from_mapping(pair_binding()),
                    output_dir=self.temp_path / f"invalid-{index}",
                )

    def test_ccp_persists_raw_bytes_exclusively_and_receipt_binds_hashes(self) -> None:
        resource, admission = valid_ccp_raw_observations()
        out = self.temp_path / "observation"
        observed = parse_ccp_observation(
            resource_raw=stable_json_bytes(resource),
            admission_raw=stable_json_bytes(admission),
            binary=valid_ccp_binary_binding(),
            pair_binding=PairBinding.from_mapping(pair_binding()),
            output_dir=out,
        )
        self.assertEqual("a0x-ccp-observation", observed["artifact_class"])
        self.assertEqual(hashlib.sha256(stable_json_bytes(resource)).hexdigest(), observed["resource_raw_sha256"])
        self.assertEqual(len(stable_json_bytes(admission)), observed["admission_raw_bytes"])
        with self.assertRaisesRegex(A0XPreflightError, "empty"):
            parse_ccp_observation(
                resource_raw=stable_json_bytes(resource),
                admission_raw=stable_json_bytes(admission),
                binary=valid_ccp_binary_binding(),
                pair_binding=PairBinding.from_mapping(pair_binding()),
                output_dir=out,
            )

    def test_ccp_accepts_a_precreated_empty_destination_but_not_reuse(self) -> None:
        resource, admission = valid_ccp_raw_observations()
        out = self.temp_path / "empty-observation"
        out.mkdir()
        parse_ccp_observation(
            resource_raw=stable_json_bytes(resource), admission_raw=stable_json_bytes(admission),
            binary=valid_ccp_binary_binding(), pair_binding=PairBinding.from_mapping(pair_binding()), output_dir=out,
        )
        self.assertTrue((out / "a0x-ccp-observation.json").is_file())

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

    def test_static_preflight_requires_offline_environment_and_empty_output(self) -> None:
        card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
        with self.assertRaisesRegex(A0XPreflightError, "offline"):
            verify_static_preflight(
                card=card,
                expected_origin="188eb65b5e249923baddadeba52659f07fcd1609",
                observed_origin="188eb65b5e249923baddadeba52659f07fcd1609",
                output_dir=self.temp_path / "result",
                environment={},
            )
        receipt = verify_static_preflight(
            card=card,
            expected_origin="188eb65b5e249923baddadeba52659f07fcd1609",
            observed_origin="188eb65b5e249923baddadeba52659f07fcd1609",
            output_dir=self.temp_path / "result",
            environment={"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
        )
        self.assertEqual("passed", receipt["preflight_status"])
