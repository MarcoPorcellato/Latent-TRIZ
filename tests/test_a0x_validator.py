"""A0X-only Draft 2020-12 positional-schema validation boundaries."""

from __future__ import annotations

import builtins
import copy
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_validator import validate  # noqa: E402


_SOURCE = {"head": "a" * 40, "tree": "b" * 40, "ref": "refs/heads/main"}
_MEMBER_NAMES = (
    "protocol.json",
    "implementation.json",
    "freeze.json",
    "approval-dossier.json",
    "slice-manifest.json",
)
_LANE_IDS = (
    "a0x-no-model",
    "a0x-synthetic",
    "documentation-audit",
    "repository-python311",
    "repository-python312",
    "schema-cross-validation-python311",
    "schema-cross-validation-python312",
)


def _members() -> list[dict[str, object]]:
    return [
        {"name": name, "size": index + 1, "sha256": "c" * 64}
        for index, name in enumerate(_MEMBER_NAMES)
    ]


def _valid_instances() -> dict[str, dict[str, object]]:
    members = _members()
    return {
        "a0x-hosted-gate-a-evidence.schema.json": {
            "artifact_class": "a0x-hosted-gate-a-evidence",
            "evidence_profile": "a0x-hosted-gate-a-evidence-v1",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "event": "push",
            "ref": "refs/heads/main",
            "qualified_source_head": "a" * 40,
            "qualified_source_tree": "b" * 40,
            "workflow": {
                "path": ".github/workflows/a0x-hosted-gate-a.yml",
                "raw_sha256": "c" * 64,
                "run_id": 1,
                "run_attempt": 1,
            },
            "inputs": {
                "requirements_schema_lock_sha256": "c" * 64,
                "action_pin_manifest_sha256": "c" * 64,
                "lane_manifest_sha256": "c" * 64,
            },
            "required_lanes": [
                {"id": lane_id, "receipt_sha256": "c" * 64, "status": "PASS"}
                for lane_id in _LANE_IDS
            ],
            "overall_status": "PASS",
        },
        "a0x-vertical-slice-manifest-v2.schema.json": {
            "artifact_class": "a0x-vertical-slice-manifest-v2",
            "generator_profile": "a0x-vertical-slice-v2",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "qualified_source": _SOURCE,
            "pair_binding": {"one": "pair"},
            "members": members[:-1],
        },
        "a0x-vertical-package-commitment-v2.schema.json": {
            "profile": "a0x-vertical-package-commitment-v2",
            "qualified_source": _SOURCE,
            "pair_binding": {"one": "pair"},
            "members": members,
            "generator": {"profile": "a0x-vertical-slice-v2", "repository": "MarcoPorcellato/Latent-TRIZ"},
            "authorization_id": "p0-auth-test-01",
            "attempt_id": "p0-attempt-test-01",
            "package_commitment_sha256": "d" * 64,
        },
    }


class A0XValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schemas = {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "schemas").glob("*.json"))
            if "prefixItems" in path.read_text(encoding="utf-8")
        }
        self.instances = _valid_instances()
        self.assertEqual(set(self.instances), set(self.schemas))

    def _assert_agrees(self, instance: object, schema: object, *, valid: bool) -> None:
        a0x_valid = not validate(instance, schema)
        reference_valid = not list(Draft202012Validator(schema).iter_errors(instance))
        self.assertEqual(valid, a0x_valid)
        self.assertEqual(valid, reference_valid)

    def test_all_positional_schemas_agree_on_valid_instances(self) -> None:
        for name, instance in self.instances.items():
            with self.subTest(schema=name):
                self._assert_agrees(instance, self.schemas[name], valid=True)

    def test_all_positional_schemas_reject_order_duplicate_missing_and_extra_members(self) -> None:
        for name, instance in self.instances.items():
            for mutation in (
                lambda value: value["required_lanes"].reverse() if "required_lanes" in value else value["members"].reverse(),
                lambda value: value["required_lanes"].__setitem__(1, copy.deepcopy(value["required_lanes"][0])) if "required_lanes" in value else value["members"].__setitem__(1, copy.deepcopy(value["members"][0])),
                lambda value: value["required_lanes"].pop() if "required_lanes" in value else value["members"].pop(),
                lambda value: value["required_lanes"].append(copy.deepcopy(value["required_lanes"][-1])) if "required_lanes" in value else value["members"].append(copy.deepcopy(value["members"][-1])),
            ):
                rejected = copy.deepcopy(instance)
                mutation(rejected)
                with self.subTest(schema=name, mutation=mutation.__code__.co_firstlineno):
                    self._assert_agrees(rejected, self.schemas[name], valid=False)

    def test_all_positional_schemas_reject_malformed_prefix_items_and_non_schema_child(self) -> None:
        for name, schema in self.schemas.items():
            array_schema = schema["properties"]["required_lanes" if "required_lanes" in self.instances[name] else "members"]
            for mutation in (
                lambda value: value.__setitem__("prefixItems", "not-an-array"),
                lambda value: value["prefixItems"].__setitem__(0, 7),
            ):
                malformed = copy.deepcopy(schema)
                target = malformed["properties"]["required_lanes" if "required_lanes" in self.instances[name] else "members"]
                mutation(target)
                with self.subTest(schema=name, mutation=mutation.__code__.co_firstlineno):
                    self.assertTrue(validate(self.instances[name], malformed))
                    with self.assertRaises(SchemaError):
                        Draft202012Validator.check_schema(malformed)

    def test_a0r2_and_c3_imports_do_not_load_a0x_validator(self) -> None:
        code = (
            "import sys; sys.path.insert(0, " + repr(str(ROOT / "src")) + "); "
            "import latent_triz.a0r2_execution, latent_triz.a0r2c3_authorization; "
            "assert 'latent_triz.a0x_validator' not in sys.modules"
        )
        completed = subprocess.run([sys.executable, "-c", code], check=False, text=True, capture_output=True)
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_a0x_validator_import_does_not_require_jsonschema(self) -> None:
        original = builtins.__import__

        def guarded_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "jsonschema" or name.startswith("jsonschema."):
                raise AssertionError("a0x validator imported jsonschema")
            return original(name, *args, **kwargs)

        sys.modules.pop("latent_triz.a0x_validator", None)
        try:
            builtins.__import__ = guarded_import
            importlib.import_module("latent_triz.a0x_validator")
        finally:
            builtins.__import__ = original


if __name__ == "__main__":
    unittest.main()
