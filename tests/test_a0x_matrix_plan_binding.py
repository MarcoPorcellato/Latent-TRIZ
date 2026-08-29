"""Regression tests binding A0X to an independently observed CCP Matrix V2 plan."""
from __future__ import annotations

import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
OBSERVATION_PATH = ROOT / "tests/fixtures/a0x/ccp-matrix-v2-legacy-plan-27adf8d.json"
CONTRACT_PATH = ROOT / "experiments/a0x-six-model/material-execution-contract.json"
POLICY_PATH = ROOT / ".commit-ci-policy-v2.toml"
CONFIG_PATH = ROOT / ".commit-ci-preflight.toml"
MAKEFILE_PATH = ROOT / "Makefile"


def _exact_make_recipe(target: str) -> tuple[str, ...]:
    """Return one literal target recipe without invoking an external make."""

    lines = MAKEFILE_PATH.read_text(encoding="utf-8").splitlines()
    header = f"{target}:"
    matches = [index for index, line in enumerate(lines) if line == header]
    if len(matches) != 1:
        raise AssertionError(
            f"Makefile target must occur exactly once: {target} (found {len(matches)})"
        )
    start = matches[0] + 1

    recipe: list[str] = []
    for line in lines[start:]:
        if not line.startswith("\t"):
            break
        recipe.append(line.removeprefix("\t"))
    if not recipe:
        raise AssertionError(f"Makefile target has no recipe: {target}")
    return tuple(recipe)


class A0XMatrixPlanBindingTests(unittest.TestCase):
    def test_repository_checks_have_one_hour_without_inflating_schema_checks(self) -> None:
        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        timeouts = {check["id"]: check["timeout_seconds"] for check in config["checks"]}

        self.assertEqual(3600, timeouts["repository-check-py311"])
        self.assertEqual(3600, timeouts["repository-check-py312"])
        self.assertEqual(300, timeouts["schema-cross-validate-py311"])
        self.assertEqual(300, timeouts["schema-cross-validate-py312"])

    def test_operator_targets_pin_legacy_profile_and_matrix_policy(self) -> None:
        expected_recipes = {
            "preflight-plan": (
                "commit-ci-preflight plan --config .commit-ci-preflight.toml "
                "--matrix-plan-profile matrix-v2-legacy-v1 --json",
            ),
            "preflight-doctor": (
                "commit-ci-preflight doctor --config .commit-ci-preflight.toml "
                "--matrix-plan-profile matrix-v2-legacy-v1 --json",
            ),
            "preflight-dry-run": (
                "commit-ci-preflight dry-run --config .commit-ci-preflight.toml "
                "--repository . --matrix-plan-profile matrix-v2-legacy-v1 --json",
            ),
            "preflight-run": (
                "commit-ci-preflight run --config .commit-ci-preflight.toml "
                "--repository . --generation 1 "
                "--matrix-plan-profile matrix-v2-legacy-v1 --json",
            ),
            "preflight-verify": (
                "commit-ci-preflight verify --receipt .ccp/receipt.json "
                "--policy .commit-ci-policy-v2.toml --expected-commit \"$$(git rev-parse HEAD)\"",
            ),
        }
        for target, expected in expected_recipes.items():
            with self.subTest(target=target):
                self.assertEqual(expected, _exact_make_recipe(target))

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
            "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4",
            observation["ccp"]["sha256"],
        )
        self.assertEqual(
            "78d0ce348a864ea99a1a7018bc00403bdd2349b5f7f6e39d6a61ec10714a20fd",
            observation["matrix_config_binding"]["raw_sha256"],
        )
        self.assertEqual(
            {"plan_only": True, "doctor_executed": False, "dry_run_executed": False, "ccp_run_executed": False},
            observation["execution_boundary"],
        )
        contract_binding = contract["ccp"]["matrix_plan_binding"]
        self.assertEqual(expected_binding, {
            name: contract_binding[name] for name in expected_binding
        })
        self.assertEqual(
            "0969a1eeb62b2a92593cda0b75c8814d7eca893bebc736ec968f02aa9f2a5fad",
            contract_binding["plan_output_sha256"],
        )
        self.assertEqual(expected_binding["outer_digest"], policy["configuration_digest"])
        self.assertEqual(
            {runtime["id"]: runtime["configuration_digest"] for runtime in policy["runtimes"]},
            observed_runtimes,
        )
        _validate_ccp_response("plan --json", observed_plan, contract["ccp"])


if __name__ == "__main__":
    unittest.main()
