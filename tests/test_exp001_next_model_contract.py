import json
import shutil
import tempfile
import unittest
from pathlib import Path
from tests.a0x_test_support import synthetic_next_model_root

from latent_triz.exp001_next_model_contract import (
    NEXT_MODELS,
    NextModelContractError,
    validate_next_model_contract,
)


ROOT = Path(__file__).resolve().parents[1]


class NextModelContractTests(unittest.TestCase):
    def test_refuses_material_execution_without_receipts(self):
        # Keep this regression independent from the now-published integrity
        # receipts: material execution must fail closed when the receipt is
        # absent, even though the selection and authorization are valid.
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            synthetic_next_model_root(repo)
            for model_id in NEXT_MODELS:
                with self.assertRaises(NextModelContractError):
                    validate_next_model_contract(repo, model_id, material_execution=True)

    def test_target_free_audit_accepts_unapproved_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = synthetic_next_model_root(Path(directory))
            for model_id in NEXT_MODELS:
                audit = validate_next_model_contract(repo, model_id, material_execution=False)
                self.assertFalse(audit["model_accessed"])
                self.assertFalse(audit["sealed_targets_accessed"])

    def test_refuses_unknown_model_without_model_or_target_access(self):
        with self.assertRaises(NextModelContractError):
            validate_next_model_contract(ROOT, "unknown/model")

    def test_contract_records_complementary_architecture_and_context(self):
        self.assertEqual(NEXT_MODELS["EleutherAI/gpt-neo-125m"]["model_type"], "gpt_neo")
        self.assertEqual(NEXT_MODELS["Qwen/Qwen2.5-0.5B"]["model_type"], "qwen2")
        self.assertEqual(NEXT_MODELS["Qwen/Qwen2.5-0.5B"]["tokenizer_max_length"], 131072)
        self.assertEqual(NEXT_MODELS["Qwen/Qwen2.5-0.5B"]["model_context"], 32768)


if __name__ == "__main__":
    unittest.main()
