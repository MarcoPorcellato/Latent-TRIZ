from __future__ import annotations

import hashlib
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

LANES = (
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

    def test_actions_and_lanes_are_canonical_frozen_inputs(self) -> None:
        actions_path = self.root / ".github/a0x-hosted-gate-a-actions.json"
        lanes_path = self.root / ".github/a0x-hosted-gate-a-lanes.json"
        actions = json.loads(actions_path.read_text(encoding="utf-8"))
        lanes = json.loads(lanes_path.read_text(encoding="utf-8"))
        self.assertEqual({"format", "actions"}, set(actions))
        self.assertEqual("actions-v1", actions["format"])
        self.assertEqual(ACTION_PINS, actions["actions"])
        self.assertEqual({"format", "lanes"}, set(lanes))
        self.assertEqual("lanes-v1", lanes["format"])
        self.assertEqual(LANES, tuple(lane["id"] for lane in lanes["lanes"]))
        self.assertEqual(sorted(LANES), list(LANES))
        for lane in lanes["lanes"]:
            self.assertEqual({"id", "python", "argv"}, set(lane))
            self.assertIsInstance(lane["argv"], list)
        self.assertEqual(hashlib.sha256(actions_path.read_bytes()).hexdigest(), hashlib.sha256(actions_path.read_bytes()).hexdigest())

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
