from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHILD = ROOT / "scripts" / "a0x_vertical_material_child.py"


class A0XVerticalMaterialChildTests(unittest.TestCase):
    """The v2 child refuses before any material capability is reachable."""

    def test_public_invalid_descriptor_returns_refused_terminal(self) -> None:
        """Removing static validation would turn an untrusted descriptor into a runtime path."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repository"
            root.mkdir()
            completed = subprocess.run(
                (
                    sys.executable, str(CHILD), "--launch-descriptor",
                    ".a0x-runtime/gate-b/v2/" + "a" * 40 + "/" + "b" * 40
                    + "/a0/model/run/launch-descriptor.json",
                ),
                cwd=root, check=False, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
        self.assertEqual(2, completed.returncode)
        self.assertEqual(
            '{"artifact_class":"a0x-vertical-material-child-terminal","exit_class":"refused","terminal_profile":"a0x-vertical-child-terminal-v1"}\n',
            completed.stdout,
        )

    def test_descriptor_argument_rejects_noncanonical_lexical_aliases(self) -> None:
        """The v2 inlet is a canonical string contract, not merely an equivalent path."""
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_path_test", CHILD)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        canonical = ".a0x-runtime/gate-b/v2/" + "a" * 40 + "/" + "b" * 40 + "/a0/model/run/launch-descriptor.json"
        for alias in (
            "./" + canonical,
            canonical.replace("gate-b/v2", "gate-b/./v2"),
            canonical.replace("gate-b/v2", "gate-b//v2"),
            canonical + "/",
        ):
            with self.subTest(alias=alias):
                with self.assertRaises(child.A0XVerticalMaterialChildError):
                    child._parse_descriptor_argument(["--launch-descriptor", alias])

    def test_v4_authorization_schema_uses_independent_identity_and_rejects_replacement(self) -> None:
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_identity_test", CHILD)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            schema = root / child._GATE_C_AUTHORIZATION_SCHEMA
            schema.parent.mkdir()
            schema.write_bytes(b'{"type":"object"}')
            raw, identity = child._read_independent(root, child._GATE_C_AUTHORIZATION_SCHEMA)
            self.assertEqual(b'{"type":"object"}', raw)
            self.assertEqual(1, schema.stat().st_nlink)
            schema.write_bytes(b'{"type":"array"}')
            with self.assertRaises(child.A0XVerticalMaterialChildError):
                child._revalidate(identity)


if __name__ == "__main__":
    unittest.main()
