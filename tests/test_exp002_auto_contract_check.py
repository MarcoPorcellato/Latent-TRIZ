import subprocess
import os
import sys
import tempfile
import unittest
from pathlib import Path
from tests.a0x_test_support import synthetic_auto_contract_root


ROOT = Path(__file__).resolve().parents[1]


class Exp002AutoContractCheckTests(unittest.TestCase):
    def test_no_model_contract_check_passes_without_model_or_target_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = synthetic_auto_contract_root(Path(directory))
            completed = subprocess.run(
                [sys.executable, "scripts/exp002_auto_contract_check.py"],
                cwd=root, env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
                check=False, capture_output=True, text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("exp002-auto contract: PASS", completed.stdout)
        self.assertIn("model_access=false", completed.stdout)
        self.assertIn("sealed_target_access=false", completed.stdout)


if __name__ == "__main__":
    unittest.main()
