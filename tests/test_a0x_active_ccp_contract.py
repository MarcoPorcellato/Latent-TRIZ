"""Captured active-producer contracts, not synthetic hybrid coordinator states."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from latent_triz import a0x_ccp_executor as executor
from latent_triz import a0x_freeze
from latent_triz import a0x_material_contract as material
from latent_triz.a0x_contract import Leg, PairBinding
from tests.a0x_test_support import pair_binding


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/a0x/ccp-active-producer"


def _guard_outputs(admission_raw: bytes):
    return (
        executor.GuardPreflightOutput("ccp_version", 0, (FIXTURES / "version.txt").read_bytes()),
        executor.GuardPreflightOutput("resource_status", 0, (FIXTURES / "resource-status-admit.json").read_bytes()),
        executor.GuardPreflightOutput("admission_status", 0, admission_raw),
        executor.GuardPreflightOutput("git_source_state", 0, json.dumps({"head": "a" * 40, "clean": True}).encode()),
        executor.GuardPreflightOutput("docker_context", 0, b"orbstack\n"),
        executor.GuardPreflightOutput("docker_active_count", 0, b""),
    )


def _active_identity():
    pin = material._ACTIVE_VERTICAL_GUARD
    return {
        "sha256": executor._ACTIVE_CCP_SHA256,
        "version": pin["version"],
        "source_commit": pin["source_commit"],
        "qualified_source_tree": pin["source_tree"],
    }


def _validate_active_guard_preflight(admission_raw: bytes):
    pair = PairBinding.from_mapping(pair_binding(Leg.A0, "smollm2_360m", hidden_width=960))
    return executor._validate_guard_preflight(
        _guard_outputs(admission_raw),
        launch=SimpleNamespace(ccp_sha256=executor._ACTIVE_CCP_SHA256),
        pair=pair,
        source_head="a" * 40,
        ccp_identity=_active_identity(),
    )


class ActiveProducerContractTests(unittest.TestCase):
    def setUp(self):
        self.resource = json.loads((FIXTURES / "resource-status-admit.json").read_bytes())
        self.admission = json.loads((FIXTURES / "admission-status-free.json").read_bytes())

    def test_captured_free_status_reaches_actual_active_hash_parent_validator(self):
        try:
            result = _validate_active_guard_preflight((FIXTURES / "admission-status-free.json").read_bytes())
        except executor.A0XCcpExecutorError as error:
            self.fail(f"captured free active-producer status was refused: {error}")
        self.assertEqual({"active": False, "queue_count": 0, "slot_state": "free"}, result["admission"])
        self.assertEqual(_active_identity()["source_commit"], result["ccp"]["source_commit"])
        self.assertEqual(_active_identity()["qualified_source_tree"], result["ccp"]["qualified_source_tree"])

    def test_source_derived_release_status_is_valid_for_postflight(self):
        release_raw = (FIXTURES / "admission-status-released.json").read_bytes()
        released = json.loads(release_raw)
        self.assertEqual("2.0", released["schema_version"])
        result = _validate_active_guard_preflight(release_raw)
        self.assertEqual({"decision": "admit"}, result["resource"])
        self.assertEqual({"active": False, "queue_count": 0, "slot_state": "free"}, result["admission"])

    def test_fixture_provenance_and_bytes_are_coupled_to_every_active_pin(self):
        provenance = json.loads((FIXTURES / "PROVENANCE.json").read_bytes())
        pin = material._ACTIVE_VERTICAL_GUARD
        contract = json.loads((ROOT / "experiments/a0x-six-model/material-execution-contract.json").read_bytes())
        self.assertEqual(pin, contract["vertical_guard"])
        self.assertEqual(executor._ACTIVE_CCP_SHA256, provenance["binary_sha256"])
        for name in ("source_commit", "source_tree", "version"):
            self.assertEqual(pin[name], provenance[name])
        for item in provenance["fixtures"]:
            raw = (FIXTURES / item["path"]).read_bytes()
            self.assertEqual(item["bytes"], len(raw))
            self.assertEqual(item["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(0, item["exit_code"])
        derived = {item["name"]: item for item in provenance["source_derived_admission_states"]}
        self.assertEqual({"released-postflight", "held", "queued", "expired-held-lease"}, set(derived))
        release = derived["released-postflight"]
        self.assertEqual("source-derived-not-captured", release["kind"])
        self.assertEqual("busy", derived["held"]["expected_validator_result"])
        self.assertEqual("busy", derived["queued"]["expected_validator_result"])
        self.assertEqual("invalid-or-unsupported", derived["expired-held-lease"]["expected_validator_result"])
        self.assertNotIn("argv", release)
        release_raw = (FIXTURES / release["path"]).read_bytes()
        self.assertEqual(release["bytes"], len(release_raw))
        self.assertEqual(release["sha256"], hashlib.sha256(release_raw).hexdigest())
        references = {item["path"]: item for item in provenance["source_references"]}
        self.assertIn([1031, 1089], references["src/admission.rs"]["lines"])
        self.assertIn([1366, 1371], references["src/admission.rs"]["lines"])
        self.assertIn([87, 130], references["docs/COORDINATION_RUNBOOK.md"]["lines"])

    def test_freeze_inventory_covers_wp1_wp2_tests_and_all_active_producer_fixtures(self):
        required = {
            "tests/test_a0x_ccp_executor.py",
            "tests/test_a0x_active_ccp_contract.py",
            "tests/test_a0x_gate_c_preflight.py",
        }
        required.update(path.relative_to(ROOT).as_posix() for path in FIXTURES.iterdir() if path.is_file())
        inventory = a0x_freeze._IMPLEMENTATION_PATHS
        self.assertTrue(required.issubset(inventory))
        self.assertEqual(tuple(sorted(set(inventory))), inventory)

    def test_unknown_hybrid_or_contradictory_status_is_invalid_not_busy(self):
        mutations = [
            lambda v: v.update(schema_version="1.0"),
            lambda v: v.update(schema_version="3.0"),
            lambda v: v.update(process_visibility_note="different note"),
            lambda v: v.update(extra=True),
            lambda v: v.pop("ticket_ids"),
            lambda v: v["slot"].update(kind="slot"),
            lambda v: v["slot"].update(lease_state="not_applicable"),
            lambda v: v["slot"].update(state="unknown"),
            lambda v: v["slot"].update(owner_run_id="unexpected owner"),
            lambda v: v.update(queue_count=True),
            lambda v: v.update(active=0),
        ]
        for mutate in mutations:
            value = copy.deepcopy(self.admission); mutate(value)
            with self.subTest(value=value), self.assertRaisesRegex(executor.A0XCcpExecutorError, "invalid|unsupported"):
                executor._validate_active_guard_status(self.resource, value)

    def test_source_derived_held_and_queued_states_are_busy_not_invalid(self):
        # These source-derived states are not captured by occupying CCP.
        held = copy.deepcopy(self.admission)
        held.update(active=True)
        held["slot"].update(state="held", lease_state="active", owner_run_id="synthetic-opaque-owner",
                            acquired_at_unix_seconds=100, heartbeat_at_unix_seconds=101)
        queued = copy.deepcopy(self.admission)
        queued.update(queue_count=1, ticket_ids=["synthetic-opaque-ticket"])
        for value in (held, queued):
            with self.subTest(value=value), self.assertRaisesRegex(executor.A0XCcpExecutorError, "busy"):
                executor._validate_active_guard_status(self.resource, value)

    def test_source_derived_expired_lease_while_slot_lock_is_held_fails_closed(self):
        expired = copy.deepcopy(self.admission)
        expired.update(active=True)
        expired["slot"].update(state="held", lease_state="expired", owner_run_id="synthetic-opaque-owner",
                                acquired_at_unix_seconds=0, heartbeat_at_unix_seconds=0)
        with self.assertRaisesRegex(executor.A0XCcpExecutorError, "invalid|unsupported"):
            executor._validate_active_guard_status(self.resource, expired)

    def test_resource_contract_stays_schema_one_and_macos_v5(self):
        for change in ({"schema_version": "2.0"}, {"policy_version": "macos-v4"}):
            with self.subTest(change=change), self.assertRaises(executor.A0XCcpExecutorError):
                executor._validate_active_guard_status({**self.resource, **change}, self.admission)


if __name__ == "__main__":
    unittest.main()
