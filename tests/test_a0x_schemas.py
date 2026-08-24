from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import A0XContractError, assert_pair_binding
from latent_triz.validator import validate
from tests.a0x_test_support import artifact, pair_binding, rich_r1_statistical_result, rich_statistical_result
from latent_triz.a0x_contract import Leg


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
            "a0x-model-card.schema.json": lambda value: value["runtime_files"][0].__setitem__("sha256", "short"),
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
            "a0x-target-read-receipt.schema.json": lambda value: value.__setitem__("content_reads", 2),
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

    def test_terminal_taxonomy_requires_receipt_and_statistics_by_status(self) -> None:
        terminal_schema = self.schemas["a0x-terminal-result.schema.json"]
        failed = artifact("a0x-terminal-result.schema.json")
        failed["status"] = "failed"
        failed["analysis_target_content_reads"] = 0
        failed["target_read_receipt_sha256"] = None
        failed["statistical_result"] = None
        self.assertEqual([], validate(failed, terminal_schema))

        contradictory = copy.deepcopy(failed)
        contradictory["statistical_result"] = rich_statistical_result()
        self.assertTrue(validate(contradictory, terminal_schema))

        positive = artifact("a0x-terminal-result.schema.json")
        positive["statistical_result"] = None
        self.assertTrue(validate(positive, terminal_schema))

        non_interpretable = artifact("a0x-terminal-result.schema.json")
        non_interpretable["status"] = "non_interpretable"
        non_interpretable["statistical_result"] = None
        self.assertEqual([], validate(non_interpretable, terminal_schema))

    def test_terminal_nested_a0_result_matches_canonical_a0_schema(self) -> None:
        canonical = self.schemas["a0x-statistical-result.schema.json"]
        terminal_schema = self.schemas["a0x-terminal-result.schema.json"]
        result = rich_statistical_result(pair_binding(Leg.A0))
        terminal = artifact("a0x-terminal-result.schema.json")
        terminal["statistical_result"] = result
        self.assertEqual([], validate(result, canonical))
        self.assertEqual([], validate(terminal, terminal_schema))

        mutations = (
            ("status-passed", lambda value: value["outcome_rule"].__setitem__("passed", False)),
            ("literal-final-index", lambda value: value["descriptive_final_block"].__setitem__("tuple_index", 6)),
            ("r1-dense", lambda value: value["pair_binding"].__setitem__("dense_bound", pair_binding(Leg.R1)["dense_bound"])),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                invalid_result = copy.deepcopy(result)
                mutate(invalid_result)
                invalid_terminal = copy.deepcopy(terminal)
                invalid_terminal["statistical_result"] = invalid_result
                self.assertTrue(validate(invalid_result, canonical))
                self.assertTrue(validate(invalid_terminal, terminal_schema))

    def test_terminal_nested_r1_result_is_strict_and_preserves_all_four_conditions(self) -> None:
        terminal_schema = self.schemas["a0x-terminal-result.schema.json"]
        pair = pair_binding(Leg.R1)
        terminal = {
            **artifact("a0x-terminal-result.schema.json"),
            "pair_binding": pair, "status": "positive", "analysis_target_content_reads": 1,
            "statistical_result": rich_r1_statistical_result(pair),
        }
        self.assertEqual([], validate(terminal, terminal_schema))
        for mutate in (
            lambda value: value["statistical_result"]["primary"].__setitem__("tuple_index", 7),
            lambda value: value["statistical_result"]["descriptive_final_block"].__setitem__("rescues_primary", True),
            lambda value: value["statistical_result"]["outcome_rule"].__setitem__("positive_direction_domains_at_least", 3),
        ):
            invalid = copy.deepcopy(terminal)
            mutate(invalid)
            self.assertTrue(validate(invalid, terminal_schema))

    def test_target_read_schema_represents_preopen_and_postopen_terminal_states(self) -> None:
        schema = self.schemas["a0x-target-read-receipt.schema.json"]
        preopen = artifact("a0x-target-read-receipt.schema.json")
        self.assertEqual([], validate(preopen, schema))

        postopen = copy.deepcopy(preopen)
        postopen["content_reads"] = 1
        postopen["status"] = "parse_failed"
        postopen["observed_sha256"] = "a" * 64
        self.assertEqual([], validate(postopen, schema))

        contradictory = copy.deepcopy(preopen)
        contradictory["status"] = "pass"
        self.assertTrue(validate(contradictory, schema))

    def test_protocol_binds_leg_to_exact_frozen_endpoints(self) -> None:
        protocol_schema = self.schemas["a0x-protocol.schema.json"]
        arbitrary = artifact("a0x-protocol.schema.json")
        arbitrary["endpoint_indices"] = [7]
        self.assertTrue(validate(arbitrary, protocol_schema))

        mismatch = artifact("a0x-protocol.schema.json")
        mismatch["identity"]["leg"] = "r1"
        self.assertTrue(validate(mismatch, protocol_schema))

        r1 = artifact("a0x-protocol.schema.json")
        r1["identity"]["leg"] = "r1"
        r1["endpoint_indices"] = [6]
        self.assertEqual([], validate(r1, protocol_schema))

    def test_output_occupancy_binds_fixture_reservation_totals(self) -> None:
        occupancy_schema = self.schemas["a0x-output-occupancy-receipt.schema.json"]
        for field in ("allocated_bytes", "total_bytes"):
            value = artifact("a0x-output-occupancy-receipt.schema.json")
            value[field] = 1
            with self.subTest(field=field):
                self.assertTrue(validate(value, occupancy_schema))

    def test_task_two_schemas_reject_nested_boundary_mutations(self) -> None:
        protected_tree = artifact("a0x-protected-tree.schema.json")
        protected_tree["entries"][0]["verification_phase"] = "declaration_only"
        self.assertTrue(validate(protected_tree, self.schemas["a0x-protected-tree.schema.json"]))

        selection = artifact("a0x-selection-manifest.schema.json")
        selection["cases"][0]["target_label"] = "forbidden"
        self.assertTrue(validate(selection, self.schemas["a0x-selection-manifest.schema.json"]))

    def test_pair_binding_detects_mismatch_even_when_documents_validate(self) -> None:
        publication = artifact("a0x-publication-manifest.schema.json")
        receipt = artifact("a0x-model-identity-receipt.schema.json")
        receipt["pair_binding"]["model_key"] = "smollm2_135m"
        self.assertEqual([], validate(publication, self.schemas["a0x-publication-manifest.schema.json"]))
        self.assertEqual([], validate(receipt, self.schemas["a0x-model-identity-receipt.schema.json"]))
        with self.assertRaisesRegex(A0XContractError, "pair binding"):
            assert_pair_binding(publication["pair_binding"], [publication, receipt])
