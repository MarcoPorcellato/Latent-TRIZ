"""Regression tests binding A0X to an independently observed CCP Matrix V2 plan."""
from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
OBSERVATION_PATH = ROOT / "tests/fixtures/a0x/ccp-matrix-v2-plan-3fccc197.json"
CONTRACT_PATH = ROOT / "experiments/a0x-six-model/material-execution-contract.json"
POLICY_PATH = ROOT / ".commit-ci-policy-v2.toml"


class A0XMatrixPlanBindingTests(unittest.TestCase):
    def test_policy_and_material_contract_match_independent_real_plan_observation(self) -> None:
        from latent_triz.a0x_runner import _validate_ccp_response

        observation = json.loads(OBSERVATION_PATH.read_text(encoding="utf-8"))
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        policy = tomllib.loads(POLICY_PATH.read_text(encoding="utf-8"))
        observed_plan = observation["observed_plan"]
        observed_runtimes = {
            runtime["id"]: runtime["configuration_digest"]
            for runtime in observed_plan["plan"]["runtimes"]
        }
        expected_binding = {
            "outer_digest": observed_plan["plan_digest"],
            "python311_digest": observed_runtimes["python311"],
            "python312_digest": observed_runtimes["python312"],
        }

        self.assertEqual(
            "b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c",
            observation["ccp"]["sha256"],
        )
        self.assertEqual(
            "3dc320e11a22cd0774a64b4a3773fd7568e389b1092b165da17b073685832a9b",
            observation["matrix_config_binding"]["raw_sha256"],
        )
        self.assertEqual(
            {"plan_only": True, "doctor_executed": False, "dry_run_executed": False, "ccp_run_executed": False},
            observation["execution_boundary"],
        )
        self.assertEqual(expected_binding, contract["ccp"]["matrix_plan_binding"])
        self.assertEqual(expected_binding["outer_digest"], policy["configuration_digest"])
        self.assertEqual(
            {runtime["id"]: runtime["configuration_digest"] for runtime in policy["runtimes"]},
            observed_runtimes,
        )
        _validate_ccp_response("plan --json", observed_plan, contract["ccp"])


if __name__ == "__main__":
    unittest.main()
