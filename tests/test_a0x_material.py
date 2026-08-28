"""Entry-point checks for the fixed A0X CCP material launcher."""
from __future__ import annotations

import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path
import subprocess
import sys
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
        probe = "\n".join(
            (
                "import importlib.util",
                "import pathlib",
                "import sys",
                f"script = pathlib.Path({str(SCRIPT)!r})",
                "spec = importlib.util.spec_from_file_location('a0x_material_entrypoint_probe', script)",
                "assert spec is not None and spec.loader is not None",
                "module = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(module)",
                "assert 'torch' not in sys.modules",
                "assert 'transformers' not in sys.modules",
            )
        )
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
