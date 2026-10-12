"""Fail-closed tests for the pre-execution A0-R2.3 approval request."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from latent_triz.validator import validate
from tests.a0x_test_support import synthetic_schema_object


ROOT = Path(__file__).parents[1]
DOSSIER_PATH = ROOT / "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json"
SCHEMA_PATH = ROOT / "schemas/a0r2-sealed-execution-approval-dossier.schema.json"
PROTOCOL_PATH = ROOT / "experiments/a0r2-independent-model/study-protocol.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ApprovalDossierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.dossier = synthetic_schema_object(self.schema)
        self.validator = Draft202012Validator(self.schema)

    def assert_rejected(self, mutation) -> None:
        payload = copy.deepcopy(self.dossier)
        mutation(payload)
        self.assertTrue(list(self.validator.iter_errors(payload)))
        self.assertTrue(validate(payload, self.schema))

    def test_exact_request_validates_and_is_not_authorization(self) -> None:
        self.assertEqual(list(self.validator.iter_errors(self.dossier)), [])
        self.assertEqual(self.dossier["dossier_status"], "approval_requested")
        self.assertIs(self.dossier["operator_approval_granted"], False)
        self.assertIs(self.dossier["authorization_receipt_present"], False)
        self.assertIs(self.dossier["access_history"]["sealed_execution_attempted"], False)
        self.assertIs(self.dossier["access_history"]["sealed_targets_accessed_for_dossier"], False)
        self.assertEqual(self.dossier["run_contract"]["maximum_material_runs"], 1)
        self.assertEqual(self.dossier["run_contract"]["activation_target_content_reads"], 0)
        self.assertEqual(self.dossier["run_contract"]["analysis_target_content_reads"], 1)

    def test_material_or_scientific_boundary_mutations_fail_closed(self) -> None:
        mutations = (
            lambda row: row.__setitem__("operator_approval_granted", True),
            lambda row: row.__setitem__("authorization_receipt_present", True),
            lambda row: row["run_contract"].__setitem__("maximum_material_runs", 2),
            lambda row: row["run_contract"].__setitem__("network_access", True),
            lambda row: row["run_contract"].__setitem__("maximum_wall_seconds", 1801),
            lambda row: row["run_contract"].__setitem__("analysis_target_content_reads", 2),
            lambda row: row["scientific_boundaries"].__setitem__("tuning", True),
            lambda row: row["scientific_boundaries"].__setitem__("claim_promotion", True),
            lambda row: row["guard_history"].__setitem__("feasibility_outer_guard_status", "pass"),
            lambda row: row.__setitem__("terminal_outcomes", ["positive", "null"]),
            lambda row: row["model"]["runtime_snapshot"]["files"][0].__setitem__("sha256", "0" * 64),
            lambda row: row["bindings"]["implementation"].__setitem__("sha256", "0" * 64),
            lambda row: row.__setitem__("unexpected", "not allowed"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_rejected(mutation)

    def test_safe_tracked_bindings_match_without_target_read(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            self.dossier["protocol"]["r1_declared_inputs"],
            {**protocol["inputs"], "source": "frozen_study_protocol_declarations_no_target_reread"},
        )
        # The merged approval dossier is historical evidence of the original
        # implementation.  The corrective authorization receipt binds the
        # current runner hash after the out-of-boundary hash observation.
        self.assertEqual(
            self.dossier["bindings"]["implementation"]["sha256"],
            "d97c55ded53e74245fba374ad63b502bb2f48eef04e2dfa6845a298034ffbabc",
        )
        entries = [
            self.dossier["protocol"],
            *(entry for name, entry in self.dossier["bindings"].items() if name != "implementation"),
        ]
        for entry in entries:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, entry["size"])
            self.assertEqual(_sha256(path), entry["sha256"])

    def test_no_absolute_or_parent_traversal_paths(self) -> None:
        paths = [
            self.dossier["protocol"]["path"],
            self.dossier["model"]["local_locator"],
            *(entry["path"] for entry in self.dossier["bindings"].values()),
        ]
        for value in paths:
            path = Path(value)
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)


if __name__ == "__main__":
    unittest.main()
