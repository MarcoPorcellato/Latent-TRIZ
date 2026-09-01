from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

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
    "a0x-material-execution-contract.schema.json",
    "a0x-attempt-claim.schema.json",
    "a0x-authorization-dossier.schema.json",
    "a0x-execution-authorization.schema.json",
    "a0x-guard-launch.schema.json",
    "a0x-qualification-evidence.schema.json",
    "a0x-qualification-authorization.schema.json",
    "a0x-model-identity-receipt.schema.json",
    "a0x-ccp-observation.schema.json",
    "a0x-preflight-receipt.schema.json",
    "a0x-activation-stage-occupancy-receipt.schema.json",
    "a0x-activation-receipt.schema.json",
    "a0x-target-read-receipt.schema.json",
    "a0x-output-occupancy-receipt.schema.json",
    "a0x-representation-record.schema.json",
    "a0x-statistical-result.schema.json",
    "a0x-terminal-result.schema.json",
    "a0x-external-assets-locator.schema.json",
    "a0x-publication-manifest.schema.json",
    "a0x-hosted-gate-a-transport.schema.json",
    "a0x-hosted-gate-a-verifier-policy.schema.json",
    "a0x-hosted-gate-a-verification-receipt.schema.json",
    "a0x-gate-b-authorization.schema.json",
)


# Literal mutations intentionally remain independent from compiler output.
SCHEMA_MUTATIONS = {
    "a0x-model-card.schema.json": lambda value: value["runtime_files"][0].__setitem__("sha256", "short"),
    "a0x-protected-tree.schema.json": lambda value: value.__setitem__("protected_tree_sha256", "short"),
    "a0x-selection-manifest.schema.json": lambda value: value.__setitem__("selection_corpus_sha256", "short"),
    "a0x-protocol.schema.json": lambda value: value.__setitem__("claim_ids", ["claim"]),
    "a0x-implementation.schema.json": lambda value: value["identity"].__setitem__("source_base_commit", "short"),
    "a0x-freeze-manifest.schema.json": lambda value: value.__setitem__("protocol_sha256", "short"),
    "a0x-material-execution-contract.schema.json": lambda value: value["ccp"]["matrix_plan_binding"].__setitem__("outer_digest", "sha256:" + "0" * 64),
    "a0x-attempt-claim.schema.json": lambda value: value.__setitem__("state", "reused"),
    "a0x-authorization-dossier.schema.json": lambda value: value["pair_binding"].__setitem__("model_key", ""),
    "a0x-execution-authorization.schema.json": lambda value: value["pair_binding"].__setitem__("revision", "short"),
    "a0x-guard-launch.schema.json": lambda value: value["timeouts"].__setitem__("outer_timeout_seconds", 3599),
    "a0x-qualification-evidence.schema.json": lambda value: value.__setitem__("qualification_receipt_raw_sha256", "short"),
    "a0x-qualification-authorization.schema.json": lambda value: value.__setitem__("generation", 0),
    "a0x-model-identity-receipt.schema.json": lambda value: value["pair_binding"].__setitem__("run_id", ""),
    "a0x-ccp-observation.schema.json": lambda value: value.__setitem__("read_counter", -1),
    "a0x-preflight-receipt.schema.json": lambda value: value["pair_binding"].__setitem__("leg", "other"),
    "a0x-activation-stage-occupancy-receipt.schema.json": lambda value: value["included_paths"].append("activations.safetensors"),
    "a0x-activation-receipt.schema.json": lambda value: value["pair_binding"].__setitem__("output_path", "/absolute"),
    "a0x-target-read-receipt.schema.json": lambda value: value.__setitem__("content_reads", 2),
    "a0x-output-occupancy-receipt.schema.json": lambda value: value.__setitem__("occupancy_profile", "legacy"),
    "a0x-representation-record.schema.json": lambda value: value.__setitem__("representation_path", "/absolute"),
    "a0x-statistical-result.schema.json": lambda value: value["pair_binding"].__setitem__("binding_profile", "legacy"),
    "a0x-terminal-result.schema.json": lambda value: value.__setitem__("statistical_result", None),
    "a0x-external-assets-locator.schema.json": lambda value: value["assets"][0].__setitem__("raw_sha256", "short"),
    "a0x-publication-manifest.schema.json": lambda value: value.__setitem__("manifest_profile", "legacy"),
    "a0x-hosted-gate-a-transport.schema.json": lambda value: value.__setitem__("run_attempt", 2),
    "a0x-hosted-gate-a-verifier-policy.schema.json": lambda value: value.__setitem__("required_ref", "refs/heads/feature"),
    "a0x-hosted-gate-a-verification-receipt.schema.json": lambda value: value.__setitem__("verification_status", "pending"),
    "a0x-gate-b-authorization.schema.json": lambda value: value.__setitem__("max_verification_count", 2),
}

TERMINAL_NESTED_RESULT_MUTATIONS = (
    ("status-passed", lambda value: value["outcome_rule"].__setitem__("passed", False)),
    ("literal-final-index", lambda value: value["descriptive_final_block"].__setitem__("tuple_index", 6)),
    ("r1-dense", lambda value: value["pair_binding"].__setitem__("dense_bound", pair_binding(Leg.R1)["dense_bound"])),
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
        for name, mutate in SCHEMA_MUTATIONS.items():
            with self.subTest(schema=name):
                value = copy.deepcopy(artifact(name))
                mutate(value)
                self.assertTrue(validate(value, self.schemas[name]))

    def test_terminal_taxonomy_requires_receipt_and_statistics_by_status(self) -> None:
        terminal_schema = self.schemas["a0x-terminal-result.schema.json"]
        failed = artifact("a0x-terminal-result.schema.json")
        failed["status"] = "failed"
        failed["sealed_from_state"] = "preflight"
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

        for label, mutate in TERMINAL_NESTED_RESULT_MUTATIONS:
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

    def test_complete_attempt_root_receipt_requires_acyclic_commitment_fields(self) -> None:
        occupancy_schema = self.schemas["a0x-output-occupancy-receipt.schema.json"]
        for field in ("manifest_package_relative_path", "manifest_raw_sha256", "final_bytes_excluding_this_receipt", "self_counting_rule", "activation_receipt_raw_sha256", "runtime_checkpoints"):
            value = artifact("a0x-output-occupancy-receipt.schema.json")
            value.pop(field)
            with self.subTest(field=field):
                self.assertTrue(validate(value, occupancy_schema))

        self_counted = artifact("a0x-output-occupancy-receipt.schema.json")
        self_counted["root_receipt_raw_sha256"] = "a" * 64
        self.assertTrue(validate(self_counted, occupancy_schema))

        for field, invalid in (("occupancy_profile", "legacy"), ("manifest_raw_sha256", "short"), ("manifest_package_relative_path", "../manifest.json")):
            mutated = artifact("a0x-output-occupancy-receipt.schema.json")
            mutated[field] = invalid
            with self.subTest(field=field):
                self.assertTrue(validate(mutated, occupancy_schema))

        legacy = artifact("a0x-output-occupancy-receipt.schema.json")
        legacy["activation_stage_receipt_sha256"] = legacy.pop("activation_receipt_raw_sha256")
        self.assertTrue(validate(legacy, occupancy_schema))

        short_checkpoints = artifact("a0x-output-occupancy-receipt.schema.json")
        short_checkpoints["runtime_checkpoints"].pop()
        self.assertTrue(validate(short_checkpoints, occupancy_schema))

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

    def test_authorization_schemas_reject_legacy_pair_fields_and_incomplete_chain(self) -> None:
        dossier_schema = self.schemas["a0x-authorization-dossier.schema.json"]
        dossier = artifact("a0x-authorization-dossier.schema.json")
        self.assertEqual([], validate(dossier, dossier_schema))
        legacy = copy.deepcopy(dossier)
        legacy["pair_binding"]["dossier_sha256"] = "a" * 64
        self.assertTrue(validate(legacy, dossier_schema))

        authorization_schema = self.schemas["a0x-execution-authorization.schema.json"]
        authorization = artifact("a0x-execution-authorization.schema.json")
        self.assertEqual([], validate(authorization, authorization_schema))
        wrong_profile = copy.deepcopy(authorization)
        wrong_profile["approved_dossier_commitment"]["profile"] = "a0x-execution-authorization-json-v1"
        self.assertTrue(validate(wrong_profile, authorization_schema))
        missing_qualification = copy.deepcopy(authorization)
        missing_qualification["qualification_evidence"].pop("qualification_receipt_raw_sha256")
        self.assertTrue(validate(missing_qualification, authorization_schema))
        missing_guard = copy.deepcopy(authorization)
        missing_guard["guard_launch"].pop("argv_template")
        self.assertTrue(validate(missing_guard, authorization_schema))

        downstream_schema = self.schemas["a0x-model-identity-receipt.schema.json"]
        downstream = artifact("a0x-model-identity-receipt.schema.json")
        self.assertEqual([], validate(downstream, downstream_schema))
        missing_chain = copy.deepcopy(downstream)
        missing_chain.pop("authorization_chain")
        self.assertTrue(validate(missing_chain, downstream_schema))
        incomplete_chain = copy.deepcopy(downstream)
        incomplete_chain["authorization_chain"].pop("authorization_commitment")
        self.assertTrue(validate(incomplete_chain, downstream_schema))

    def test_terminal_package_ledger_is_closed_and_has_no_manifest_self_hash(self) -> None:
        schema = self.schemas["a0x-publication-manifest.schema.json"]
        manifest = artifact("a0x-publication-manifest.schema.json")
        for field in ("manifest_profile", "root_receipt_profile", "root_receipt_package_relative_path", "terminal_status", "package_status", "package_artifacts", "external_outputs", "source_inputs", "retained_residue"):
            missing = copy.deepcopy(manifest)
            missing.pop(field, None)
            with self.subTest(field=field):
                self.assertTrue(validate(missing, schema))
        for field, invalid in (("root_receipt_package_relative_path", "/absolute/root.json"), ("root_receipt_package_relative_path", "../root.json")):
            mutated = copy.deepcopy(manifest)
            mutated[field] = invalid
            with self.subTest(field=field):
                self.assertTrue(validate(mutated, schema))
        self_hashed = copy.deepcopy(manifest)
        self_hashed["manifest_raw_sha256"] = "a" * 64
        self.assertTrue(validate(self_hashed, schema))

        bad_role = copy.deepcopy(manifest)
        bad_role["package_artifacts"][0]["role"] = "undeclared"
        self.assertTrue(validate(bad_role, schema))

        wrong_namespace = copy.deepcopy(manifest)
        wrong_namespace["external_outputs"][0]["path"] = wrong_namespace["external_outputs"][0].pop("repository_relative_path")
        self.assertTrue(validate(wrong_namespace, schema))

    def test_authorization_record_role_is_reserved_for_a_schema_valid_execution_authorization_copy(self) -> None:
        """The later builder copies these exact bytes and validates this schema."""
        manifest = artifact("a0x-publication-manifest.schema.json")
        authorization = artifact("a0x-execution-authorization.schema.json")
        schema = self.schemas["a0x-execution-authorization.schema.json"]
        self.assertEqual([], validate(authorization, schema))
        roles = [entry["role"] for entry in manifest["package_artifacts"]]
        self.assertEqual(1, roles.count("authorization_record"))

    def test_root_cap_and_runtime_checkpoint_phases_are_structurally_frozen(self) -> None:
        schema = self.schemas["a0x-output-occupancy-receipt.schema.json"]
        invalid_cap = artifact("a0x-output-occupancy-receipt.schema.json")
        invalid_cap["cap_bytes"] = 1
        self.assertTrue(validate(invalid_cap, schema))

        legacy_checkpoints = artifact("a0x-output-occupancy-receipt.schema.json")
        legacy_checkpoints["checkpoints"] = legacy_checkpoints.pop("runtime_checkpoints")
        self.assertTrue(validate(legacy_checkpoints, schema))

    def test_root_fixture_excludes_source_inputs_from_complete_attempt_occupancy(self) -> None:
        root = artifact("a0x-output-occupancy-receipt.schema.json")
        components = root["component_bytes"]
        self.assertEqual(1024, components["source_inputs"])
        self.assertEqual(3840, root["final_bytes_excluding_this_receipt"])
        self.assertEqual(3840, root["peak_bytes_before_this_receipt"])
        self.assertEqual(
            3840,
            components["manifest"] + components["package_artifacts"]
            + components["external_outputs"] + components["retained_residue"],
        )
        self.assertEqual(
            ["pre_manifest_write", "pre_root_receipt_write"],
            [checkpoint["phase"] for checkpoint in root["runtime_checkpoints"]],
        )
        self.assertEqual([3584, 3840], [checkpoint["bytes"] for checkpoint in root["runtime_checkpoints"]])

    def test_positive_terminal_requires_analysis_frontier(self) -> None:
        schema = self.schemas["a0x-terminal-result.schema.json"]
        terminal = artifact("a0x-terminal-result.schema.json")
        terminal["sealed_from_state"] = "activation"
        self.assertTrue(validate(terminal, schema))

    def test_analysis_frontier_always_requires_a_target_receipt_hash(self) -> None:
        schema = self.schemas["a0x-terminal-result.schema.json"]
        terminal = artifact("a0x-terminal-result.schema.json")
        terminal["status"] = "failed"
        terminal["statistical_result"] = None
        terminal["analysis_target_content_reads"] = 0
        terminal["target_read_receipt_sha256"] = None
        self.assertTrue(validate(terminal, schema))

    def test_external_locator_requires_equal_shape_dense_and_index_assets(self) -> None:
        schema = self.schemas["a0x-external-assets-locator.schema.json"]
        locator = artifact("a0x-external-assets-locator.schema.json")
        self.assertEqual([], validate(locator, schema))
        for mutation in (
            lambda value: value["assets"].pop(),
            lambda value: value["assets"][0].__setitem__("role", "other"),
            lambda value: value["assets"][1].__setitem__("repository_relative_path", "/absolute/index.jsonl"),
            lambda value: value.__setitem__("locator_profile", "legacy"),
            lambda value: value["assets"][0].__setitem__("unexpected", "field"),
            lambda value: value["assets"][0].__setitem__("path", value["assets"][0].pop("repository_relative_path")),
        ):
            mutated = copy.deepcopy(locator)
            mutation(mutated)
            self.assertTrue(validate(mutated, schema))

    def test_hosted_gate_a_schemas_are_closed_and_reject_integer_booleans(self) -> None:
        root = Path(__file__).resolve().parents[1]
        lane_schema = json.loads((root / "schemas/a0x-hosted-gate-a-lane-receipt.schema.json").read_text(encoding="utf-8"))
        evidence_schema = json.loads((root / "schemas/a0x-hosted-gate-a-evidence.schema.json").read_text(encoding="utf-8"))
        lane = {
            "artifact_class": "a0x-hosted-gate-a-lane-receipt",
            "receipt_profile": "a0x-hosted-gate-a-lane-receipt-v1",
            "lane_id": "repository-python311",
            "qualified_source_head": "a" * 40,
            "qualified_source_tree": "b" * 40,
            "command": ["python", "scripts/repository_check.py"],
            "status": "PASS",
        }
        evidence = {
            "artifact_class": "a0x-hosted-gate-a-evidence",
            "evidence_profile": "a0x-hosted-gate-a-evidence-v1",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "event": "push",
            "ref": "refs/heads/main",
            "qualified_source_head": "a" * 40,
            "qualified_source_tree": "b" * 40,
            "workflow": {"path": ".github/workflows/a0x-hosted-gate-a.yml", "raw_sha256": "c" * 64, "run_id": 1, "run_attempt": 1},
            "inputs": {"requirements_schema_lock_sha256": "d" * 64, "action_pin_manifest_sha256": "e" * 64, "lane_manifest_sha256": "f" * 64},
            "required_lanes": [{"id": lane_id, "receipt_sha256": "1" * 64, "status": "PASS"} for lane_id in (
                "a0x-no-model", "a0x-synthetic", "documentation-audit", "repository-python311", "repository-python312", "schema-cross-validation-python311", "schema-cross-validation-python312",
            )],
            "overall_status": "PASS",
        }
        self.assertEqual([], list(Draft202012Validator(lane_schema).iter_errors(lane)))
        self.assertEqual([], list(Draft202012Validator(evidence_schema).iter_errors(evidence)))
        for value, schema, mutate in (
            (lane, lane_schema, lambda item: item.__setitem__("extra", True)),
            (lane, lane_schema, lambda item: item.__setitem__("command", ["make", "docs-audit"])),
            (evidence, evidence_schema, lambda item: item["workflow"].__setitem__("run_id", True)),
            (evidence, evidence_schema, lambda item: item["required_lanes"].pop()),
            (evidence, evidence_schema, lambda item: item["required_lanes"].__setitem__(1, item["required_lanes"][0])),
            (evidence, evidence_schema, lambda item: item["required_lanes"].__setitem__(0, item["required_lanes"][1])),
            (evidence, evidence_schema, lambda item: item["required_lanes"][0].__setitem__("unexpected", "field")),
        ):
            invalid = copy.deepcopy(value)
            mutate(invalid)
            with self.subTest(invalid=invalid):
                self.assertTrue(list(Draft202012Validator(schema).iter_errors(invalid)))

    def test_hosted_gate_b_schemas_bind_only_four_safe_inputs_and_one_future_output(self) -> None:
        schemas = {
            name: self.schemas[name]
            for name in (
                "a0x-hosted-gate-a-transport.schema.json",
                "a0x-hosted-gate-a-verifier-policy.schema.json",
                "a0x-hosted-gate-a-verification-receipt.schema.json",
                "a0x-gate-b-authorization.schema.json",
            )
        }
        values = {name: artifact(name) for name in schemas}
        for name, schema in schemas.items():
            with self.subTest(schema=name):
                self.assertEqual([], validate(values[name], schema))
                self.assertEqual([], list(Draft202012Validator(schema).iter_errors(values[name])))

        authorization = values["a0x-gate-b-authorization.schema.json"]
        self.assertEqual(
            {
                "artifact_class", "authorization_profile", "authorization_status",
                "repository", "source_head", "source_tree", "job_workflow_sha", "source_sha", "pair_binding",
                "hosted_inputs", "verifier", "verification_receipt_path",
                "max_verification_count", "stop_boundary", "authorization_id",
            },
            set(authorization),
        )
        self.assertEqual(
            {"manifest", "attestation_bundle", "trusted_root", "transport"},
            set(authorization["hosted_inputs"]),
        )
        self.assertNotIn("verification_receipt_raw_sha256", authorization)

        mutations = (
            ("fifth-input", "a0x-gate-b-authorization.schema.json", lambda value: value["hosted_inputs"].__setitem__("receipt", {"path": ".a0x-runtime/gate-a/evidence/" + "a" * 40 + "/receipt.json", "sha256": "f" * 64})),
            ("prebound-receipt-hash", "a0x-gate-b-authorization.schema.json", lambda value: value.__setitem__("verification_receipt_raw_sha256", "f" * 64)),
            ("local-input-path", "a0x-gate-b-authorization.schema.json", lambda value: value["hosted_inputs"]["manifest"].__setitem__("path", "/private/tmp/hosted-gate-a-evidence.json")),
            ("unsafe-input-path", "a0x-gate-b-authorization.schema.json", lambda value: value["hosted_inputs"]["transport"].__setitem__("path", ".a0x-runtime/gate-a/evidence/" + "a" * 40 + "/../hosted-gate-a-transport.json")),
            ("output-outside-inlet", "a0x-gate-b-authorization.schema.json", lambda value: value.__setitem__("verification_receipt_path", "results/a0x/a0/gpt2/gate-a-verification-receipt.json")),
            ("overlong-authorization-id", "a0x-gate-b-authorization.schema.json", lambda value: value.__setitem__("authorization_id", "a" * 129)),
            ("uppercase-input-hash", "a0x-gate-b-authorization.schema.json", lambda value: value["hosted_inputs"]["manifest"].__setitem__("sha256", "A" * 64)),
            ("integer-boolean", "a0x-hosted-gate-a-verifier-policy.schema.json", lambda value: value.__setitem__("deny_self_hosted_runners", 1)),
            ("local-policy-string", "a0x-hosted-gate-a-verifier-policy.schema.json", lambda value: value.__setitem__("signer_workflow", "/Users/marco1/.a0x-runtime/workflow.yml")),
            ("wrong-type", "a0x-hosted-gate-a-transport.schema.json", lambda value: value.__setitem__("artifact_id", True)),
            ("uppercase-archive-hash", "a0x-hosted-gate-a-transport.schema.json", lambda value: value.__setitem__("archive_digest", "sha256:" + "A" * 64)),
            ("receipt-self-hash", "a0x-hosted-gate-a-verification-receipt.schema.json", lambda value: value.__setitem__("verification_receipt_raw_sha256", "f" * 64)),
            ("uppercase-receipt-input-hash", "a0x-hosted-gate-a-verification-receipt.schema.json", lambda value: value["hosted_inputs"]["manifest"].__setitem__("sha256", "A" * 64)),
        )
        for label, schema_name, mutate in mutations:
            invalid = copy.deepcopy(values[schema_name])
            mutate(invalid)
            with self.subTest(label=label):
                self.assertTrue(validate(invalid, schemas[schema_name]))
                self.assertTrue(list(Draft202012Validator(schemas[schema_name]).iter_errors(invalid)))

        shape_mutations = (
            ("a0x-hosted-gate-a-transport.schema.json", "artifact_id", True),
            ("a0x-hosted-gate-a-verifier-policy.schema.json", "deny_self_hosted_runners", 1),
            ("a0x-hosted-gate-a-verification-receipt.schema.json", "authorization_raw_sha256", 1),
            ("a0x-gate-b-authorization.schema.json", "source_head", True),
        )
        for schema_name, typed_field, wrong_value in shape_mutations:
            unknown = copy.deepcopy(values[schema_name])
            unknown["unexpected"] = "field"
            missing = copy.deepcopy(values[schema_name])
            missing.pop(typed_field)
            wrong_type = copy.deepcopy(values[schema_name])
            wrong_type[typed_field] = wrong_value
            for label, invalid in (("unknown", unknown), ("missing", missing), ("wrong-type", wrong_type)):
                with self.subTest(schema=schema_name, label=label):
                    self.assertTrue(validate(invalid, schemas[schema_name]))
                    self.assertTrue(list(Draft202012Validator(schemas[schema_name]).iter_errors(invalid)))
