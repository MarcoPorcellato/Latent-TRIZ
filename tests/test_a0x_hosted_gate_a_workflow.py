from __future__ import annotations

import json
import unittest
from pathlib import Path

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
        {"argv": ["make", "a0x-no-model-verify"], "id": "a0x-no-model", "python": None},
        {"argv": ["make", "a0x-synthetic-verify"], "id": "a0x-synthetic", "python": None},
        {"argv": ["make", "docs-audit"], "id": "documentation-audit", "python": None},
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
