"""Entry-point checks for the fixed A0X CCP material launcher."""
from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "a0x_material.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("a0x_material_entrypoint", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("A0X material entrypoint cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A0XMaterialEntrypointTests(unittest.TestCase):
    def test_entrypoint_has_only_one_fixed_dossier_argument(self) -> None:
        module = _load_module()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = module.main(["--fixed-dossier", "not-a-planned-dossier.json"])
        self.assertEqual(2, code)
        self.assertIn("exact twelve", stderr.getvalue())

    def test_entrypoint_rejects_path_traversal_before_process_execution(self) -> None:
        module = _load_module()
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = module.main(["--fixed-dossier", "../experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"])
        self.assertEqual(2, code)
        self.assertIn("traversal", stderr.getvalue())

    def test_entrypoint_import_does_not_import_model_libraries(self) -> None:
        import sys

        _load_module()
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("transformers", sys.modules)

