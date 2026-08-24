from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import A0XContractError, assert_pair_binding
from latent_triz.validator import validate
from tests.a0x_test_support import artifact


SCHEMA_FILES = (
    "a0x-model-card.schema.json",
    "a0x-protected-tree.schema.json",
    "a0x-selection-manifest.schema.json",
    "a0x-protocol.schema.json",
    "a0x-implementation.schema.json",
    "a0x-freeze-manifest.schema.json",
    "a0x-authorization-dossier.schema.json",
    "a0x-execution-authorization.schema.json",
    "a0x-model-identity-receipt.schema.json",
    "a0x-ccp-observation.schema.json",
    "a0x-preflight-receipt.schema.json",
    "a0x-activation-receipt.schema.json",
    "a0x-target-read-receipt.schema.json",
    "a0x-output-occupancy-receipt.schema.json",
    "a0x-representation-record.schema.json",
    "a0x-statistical-result.schema.json",
    "a0x-terminal-result.schema.json",
    "a0x-publication-manifest.schema.json",
)


class A0XSchemasTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.schemas = {
            name: json.loads((root / "schemas" / name).read_text(encoding="utf-8"))
            for name in SCHEMA_FILES
        }

    def test_every_schema_accepts_its_complete_fixture(self) -> None:
        for name, schema in self.schemas.items():
            with self.subTest(schema=name):
                self.assertEqual([], validate(artifact(name), schema))

    def test_every_schema_rejects_one_required_invariant_mutation(self) -> None:
        mutations = {
            "a0x-model-card.schema.json": lambda value: value.__setitem__("model_key", ""),
            "a0x-protected-tree.schema.json": lambda value: value.__setitem__("protected_tree_sha256", "short"),
            "a0x-selection-manifest.schema.json": lambda value: value.__setitem__("selection_corpus_sha256", "short"),
            "a0x-protocol.schema.json": lambda value: value.__setitem__("claim_ids", ["claim"]),
            "a0x-implementation.schema.json": lambda value: value["identity"].__setitem__("source_base_commit", "short"),
            "a0x-freeze-manifest.schema.json": lambda value: value.__setitem__("protocol_sha256", "short"),
            "a0x-authorization-dossier.schema.json": lambda value: value["pair_binding"].__setitem__("model_key", ""),
            "a0x-execution-authorization.schema.json": lambda value: value["pair_binding"].__setitem__("revision", "short"),
            "a0x-model-identity-receipt.schema.json": lambda value: value["pair_binding"].__setitem__("run_id", ""),
            "a0x-ccp-observation.schema.json": lambda value: value.__setitem__("read_counter", -1),
            "a0x-preflight-receipt.schema.json": lambda value: value["pair_binding"].__setitem__("leg", "other"),
            "a0x-activation-receipt.schema.json": lambda value: value["pair_binding"].__setitem__("output_path", "/absolute"),
            "a0x-target-read-receipt.schema.json": lambda value: value.__setitem__("target_read_count", 1),
            "a0x-output-occupancy-receipt.schema.json": lambda value: value["pair_binding"]["dense_bound"].__setitem__("cap_bytes", 0),
            "a0x-representation-record.schema.json": lambda value: value.__setitem__("representation_path", "/absolute"),
            "a0x-statistical-result.schema.json": lambda value: value["pair_binding"].__setitem__("dossier_sha256", "short"),
            "a0x-terminal-result.schema.json": lambda value: value.__setitem__("statistical_result", None),
            "a0x-publication-manifest.schema.json": lambda value: value.__setitem__("report_input_path", "/absolute"),
        }
        for name, mutate in mutations.items():
            with self.subTest(schema=name):
                value = copy.deepcopy(artifact(name))
                mutate(value)
                self.assertTrue(validate(value, self.schemas[name]))

    def test_terminal_preanalysis_failures_prohibit_results_and_success_requires_one(self) -> None:
        terminal_schema = self.schemas["a0x-terminal-result.schema.json"]
        failed = artifact("a0x-terminal-result.schema.json")
        failed["status"] = "failed"
        failed["statistical_result"] = None
        self.assertEqual([], validate(failed, terminal_schema))

        contradictory = copy.deepcopy(failed)
        contradictory["statistical_result"] = {"p_value": 0.5, "result_status": "completed"}
        self.assertTrue(validate(contradictory, terminal_schema))

        passed = artifact("a0x-terminal-result.schema.json")
        passed["statistical_result"] = None
        self.assertTrue(validate(passed, terminal_schema))

    def test_pair_binding_detects_mismatch_even_when_documents_validate(self) -> None:
        publication = artifact("a0x-publication-manifest.schema.json")
        receipt = artifact("a0x-model-identity-receipt.schema.json")
        receipt["pair_binding"]["model_key"] = "smollm2_135m"
        self.assertEqual([], validate(publication, self.schemas["a0x-publication-manifest.schema.json"]))
        self.assertEqual([], validate(receipt, self.schemas["a0x-model-identity-receipt.schema.json"]))
        with self.assertRaisesRegex(A0XContractError, "pair binding"):
            assert_pair_binding(publication["pair_binding"], [publication, receipt])
