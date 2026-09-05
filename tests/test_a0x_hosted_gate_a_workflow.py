from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any

import yaml


ACTION_PINS = {
    "actions/attest": "508db95dd578ae2727ebd6217d5ba78e4fbda05d",
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
}

EXPECTED_ACTIONS = {"actions": ACTION_PINS, "format": "actions-v1"}

EXPECTED_LANES = {
    "format": "lanes-v1",
    "lanes": [
        {"argv": ["make", "a0x-no-model-verify"], "id": "a0x-no-model", "python": "3.11"},
        {"argv": ["make", "a0x-synthetic-verify"], "id": "a0x-synthetic", "python": "3.11"},
        {"argv": ["make", "docs-audit"], "id": "documentation-audit", "python": "3.11"},
        {"argv": ["python", "scripts/repository_check.py"], "id": "repository-python311", "python": "3.11"},
        {"argv": ["python", "scripts/repository_check.py"], "id": "repository-python312", "python": "3.12"},
        {"argv": ["python", "scripts/schema_cross_validate.py"], "id": "schema-cross-validation-python311", "python": "3.11"},
        {"argv": ["python", "scripts/schema_cross_validate.py"], "id": "schema-cross-validation-python312", "python": "3.12"},
    ],
}

LANE_IDS = (
    "a0x-no-model",
    "a0x-synthetic",
    "documentation-audit",
    "repository-python311",
    "repository-python312",
    "schema-cross-validation-python311",
    "schema-cross-validation-python312",
)

WORKFLOW_PATH = ".github/workflows/a0x-hosted-gate-a.yml"
AGGREGATE_JOB = "aggregate"
AGGREGATE_PERMISSIONS = {
    "attestations": "write",
    "contents": "read",
    "id-token": "write",
}
LANE_PERMISSIONS = {"contents": "read"}
EVIDENCE_PATH = "a0x-hosted-gate-a-evidence.json"


class UniqueSafeLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: UniqueSafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError("while constructing mapping", node.start_mark, f"duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _reject_legacy_yaml_booleans() -> None:
    """Keep GitHub's literal `on` key from YAML 1.1 boolean coercion."""
    resolvers = {}
    for initial, entries in UniqueSafeLoader.yaml_implicit_resolvers.items():
        resolvers[initial] = [
            entry for entry in entries if entry[0] != "tag:yaml.org,2002:bool"
        ]
    UniqueSafeLoader.yaml_implicit_resolvers = resolvers
    UniqueSafeLoader.add_implicit_resolver(
        "tag:yaml.org,2002:bool",
        re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
        list("tTfF"),
    )


_reject_legacy_yaml_booleans()


def _walk_mapping(value: Any) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        mappings.append(value)
        for nested in value.values():
            mappings.extend(_walk_mapping(nested))
    elif isinstance(value, list):
        for nested in value:
            mappings.extend(_walk_mapping(nested))
    return mappings


class A0XHostedGateAWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]

    def _assert_canonical_json(self, path: Path, expected: dict) -> None:
        encoded = path.read_bytes()
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertFalse(encoded.endswith(b"\n\n"))
        self.assertEqual(
            json.dumps(expected, separators=(",", ":"), sort_keys=True) + "\n",
            encoded.decode("utf-8"),
        )

    def _workflow(self) -> tuple[str, dict[str, Any]]:
        path = self.root / WORKFLOW_PATH
        raw = path.read_text(encoding="utf-8")
        workflow = yaml.load(raw, Loader=UniqueSafeLoader)
        self.assertIsInstance(workflow, dict)
        return raw, workflow

    def _step_with_id(self, job: dict[str, Any], step_id: str) -> tuple[int, dict[str, Any]]:
        for index, step in enumerate(job["steps"]):
            if step.get("id") == step_id:
                return index, step
        self.fail(f"missing step id {step_id!r}")

    def test_actions_and_lanes_are_canonical_frozen_inputs(self) -> None:
        actions_path = self.root / ".github/a0x-hosted-gate-a-actions.json"
        lanes_path = self.root / ".github/a0x-hosted-gate-a-lanes.json"
        actions = json.loads(actions_path.read_text(encoding="utf-8"))
        lanes = json.loads(lanes_path.read_text(encoding="utf-8"))
        self.assertEqual(EXPECTED_ACTIONS, actions)
        self.assertEqual(EXPECTED_LANES, lanes)
        self.assertEqual(LANE_IDS, tuple(lane["id"] for lane in lanes["lanes"]))
        self.assertEqual(sorted(LANE_IDS), list(LANE_IDS))
        self._assert_canonical_json(actions_path, EXPECTED_ACTIONS)
        self._assert_canonical_json(lanes_path, EXPECTED_LANES)

    def test_schema_requirements_are_hash_locked_and_safe_yaml_is_strict(self) -> None:
        requirements = (self.root / "requirements-schema.in").read_text(encoding="utf-8")
        lock = (self.root / "requirements-schema.lock").read_text(encoding="utf-8")
        self.assertIn("jsonschema==4.26.0", requirements)
        self.assertIn("PyYAML==6.0.3", requirements)
        requirement_blocks = [block for block in lock.split("\n\n") if "==" in block]
        self.assertTrue(requirement_blocks)
        for block in requirement_blocks:
            self.assertIn("--hash=sha256:", block)
        with self.assertRaises(yaml.constructor.ConstructorError):
            yaml.load("a: 1\na: 2\n", Loader=UniqueSafeLoader)
        with self.assertRaises(yaml.constructor.ConstructorError):
            yaml.load("!!python/tuple [1, 2]\n", Loader=UniqueSafeLoader)

    def test_current_operator_documents_state_hosted_gate_a_boundaries(self) -> None:
        paths = (
            "docs/A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md",
            "docs/A0X_SIX_MODEL_CAMPAIGN.md",
            "docs/A0X_GATE_B_OPERATOR_HARDENING.md",
            "docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md",
            "docs/CURRENT_STATUS.md",
            "docs/PERSISTENT_GOAL.txt",
            "artifacts/checkpoints/A0X_RESTART_CHECKPOINT_2026-08-30.md",
        )
        text = "\n".join((self.root / path).read_text(encoding="utf-8") for path in paths)
        required = (
            "repository-python311",
            "schema-cross-validation-python311",
            "repository-python312",
            "schema-cross-validation-python312",
            "a0x-no-model",
            "a0x-synthetic",
            "documentation-audit",
            "32 KiB",
            "1 MiB",
            "2 MiB",
            "16 KiB",
            "four hosted inputs",
            "fifth verification receipt",
            "no rerun",
            "CCP Gate C",
            "Historical evidence",
            "first real post-merge hosted Gate A run",
            "revocations published after that snapshot",
            "separate authorization",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        runbook = (self.root / paths[0]).read_text(encoding="utf-8")
        for flag in (
            "--bundle",
            "--custom-trusted-root",
            "--signer-workflow",
            "--source-digest",
            "--predicate-type",
            "--deny-self-hosted-runners",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, runbook)
        for filename in (
            "hosted-gate-a-evidence.json",
            "hosted-gate-a-attestation.bundle.jsonl",
            "github-trusted-root.jsonl",
            "hosted-gate-a-transport.json",
        ):
            with self.subTest(filename=filename):
                self.assertIn(filename, runbook)

    def test_workflow_is_exact_main_hosted_and_hash_bound(self) -> None:
        raw, workflow = self._workflow()
        self.assertEqual({"name", "on", "permissions", "concurrency", "jobs"}, set(workflow))
        self.assertEqual({"push": {"branches": ["main"]}}, workflow["on"])
        self.assertEqual({}, workflow["permissions"])
        self.assertEqual(
            {"group": "a0x-gate-a-${{ github.sha }}", "cancel-in-progress": False},
            workflow["concurrency"],
        )
        self.assertNotIn("secrets.", raw.lower())

        jobs = workflow["jobs"]
        self.assertEqual(set(LANE_IDS) | {AGGREGATE_JOB}, set(jobs))
        mappings = _walk_mapping(workflow)
        self.assertFalse(any("continue-on-error" in mapping for mapping in mappings))
        uses = [mapping["uses"] for mapping in mappings if "uses" in mapping]
        self.assertTrue(uses)
        for action in uses:
            name, separator, revision = action.partition("@")
            self.assertEqual("@", separator)
            self.assertEqual(ACTION_PINS[name], revision)
            self.assertRegex(revision, r"^[a-f0-9]{40}$")

        for lane in EXPECTED_LANES["lanes"]:
            lane_id = lane["id"]
            job = jobs[lane_id]
            self.assertEqual("ubuntu-latest", job["runs-on"])
            self.assertEqual(LANE_PERMISSIONS, job["permissions"])
            self.assertEqual(
                {"gate_a_lane_receipt": "${{ steps.receipt.outputs.gate_a_lane_receipt }}"},
                job["outputs"],
            )
            checkout_index, checkout = self._step_with_id(job, "checkout")
            self.assertEqual(f"actions/checkout@{ACTION_PINS['actions/checkout']}", checkout["uses"])
            self.assertEqual(
                {"fetch-depth": 0, "persist-credentials": False, "ref": "${{ github.sha }}"},
                checkout["with"],
            )
            source_index, source = self._step_with_id(job, "source")
            self.assertGreater(source_index, checkout_index)
            self.assertIn('test "$GITHUB_RUN_ATTEMPT" = "1"', source["run"])
            self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', source["run"])
            self.assertIn("git rev-parse HEAD^{tree}", source["run"])

            python_index, python = self._step_with_id(job, "python")
            self.assertGreater(python_index, source_index)
            self.assertEqual(
                f"actions/setup-python@{ACTION_PINS['actions/setup-python']}", python["uses"]
            )
            self.assertEqual({"python-version": lane["python"]}, python["with"])
            observed_index, observed = self._step_with_id(job, "observed-python")
            install_index, install = self._step_with_id(job, "install")
            self.assertGreater(observed_index, python_index)
            self.assertGreater(install_index, observed_index)
            expected_tuple = tuple(int(part) for part in lane["python"].split("."))
            self.assertIn(f"sys.version_info[:2] == {expected_tuple}", observed["run"])
            self.assertEqual(
                "python -m pip install --require-hashes -r requirements-schema.lock",
                install["run"],
            )
            command_index, command = self._step_with_id(job, "command")
            self.assertGreater(command_index, install_index)

            self.assertEqual(" ".join(lane["argv"]), command["run"])
            receipt_index, receipt = self._step_with_id(job, "receipt")
            self.assertGreater(receipt_index, command_index)
            self.assertIn("python scripts/a0x_hosted_gate_a.py lane", receipt["run"])
            self.assertIn(f'--lane-id "{lane_id}"', receipt["run"])
            self.assertIn('--source-head "$GITHUB_SHA"', receipt["run"])
            self.assertIn('--source-tree "$SOURCE_TREE"', receipt["run"])
            self.assertIn('--github-output "$GITHUB_OUTPUT"', receipt["run"])
            self.assertIn("-- " + " ".join(lane["argv"]), receipt["run"])

        aggregate = jobs[AGGREGATE_JOB]
        self.assertEqual("${{ always() }}", aggregate["if"])
        self.assertEqual(
            {AGGREGATE_JOB: "${{ always() }}"},
            {job_id: job["if"] for job_id, job in jobs.items() if "if" in job},
        )
        self.assertEqual(list(LANE_IDS), aggregate["needs"])
        self.assertEqual("ubuntu-latest", aggregate["runs-on"])
        self.assertEqual(AGGREGATE_PERMISSIONS, aggregate["permissions"])
        aggregate_checkout_index, aggregate_checkout = self._step_with_id(aggregate, "checkout")
        self.assertEqual(f"actions/checkout@{ACTION_PINS['actions/checkout']}", aggregate_checkout["uses"])
        self.assertEqual(
            {"fetch-depth": 0, "persist-credentials": False, "ref": "${{ github.sha }}"},
            aggregate_checkout["with"],
        )
        aggregate_source_index, aggregate_source = self._step_with_id(aggregate, "source")
        self.assertGreater(aggregate_source_index, aggregate_checkout_index)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = "1"', aggregate_source["run"])
        self.assertIn('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', aggregate_source["run"])
        _, manifest = self._step_with_id(aggregate, "manifest")
        self.assertIn("python scripts/a0x_hosted_gate_a.py aggregate", manifest["run"])
        self.assertEqual(7, manifest["run"].count("--lane-output"))
        self.assertIn(f'--output "{EVIDENCE_PATH}"', manifest["run"])
        for lane_id in LANE_IDS:
            self.assertIn(f"needs['{lane_id}'].outputs.gate_a_lane_receipt", manifest["run"])

        _, upload = self._step_with_id(aggregate, "upload")
        self.assertEqual(f"actions/upload-artifact@{ACTION_PINS['actions/upload-artifact']}", upload["uses"])
        self.assertEqual(
            {
                "if-no-files-found": "error",
                "name": "a0x-hosted-gate-a-${{ github.sha }}",
                "path": EVIDENCE_PATH,
            },
            upload["with"],
        )
        _, attest = self._step_with_id(aggregate, "attest")
        self.assertEqual(f"actions/attest@{ACTION_PINS['actions/attest']}", attest["uses"])
        self.assertEqual({"subject-path": EVIDENCE_PATH}, attest["with"])
