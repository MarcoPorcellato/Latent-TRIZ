import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from latent_triz.validator import validate as validate_minimal
from tests.a0x_test_support import synthetic_acquisition_authorization


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/exp001-next-model-authorization.schema.json").read_text(encoding="utf-8"))
INSTANCE = synthetic_acquisition_authorization(next_models=True)


class NextModelAuthorizationTests(unittest.TestCase):
    def test_exact_request_is_valid_and_operator_authorized(self):
        self.assertEqual(validate_minimal(INSTANCE, SCHEMA), [])
        self.assertEqual(list(Draft202012Validator(SCHEMA).iter_errors(INSTANCE)), [])
        self.assertEqual(INSTANCE["status"], "authorized")
        self.assertTrue(INSTANCE["operator_approval"]["granted"])
        self.assertFalse(INSTANCE["source_metadata"]["content_bytes_downloaded"])
        self.assertEqual(
            {candidate["model_id"] for candidate in INSTANCE["candidates"]},
            {"EleutherAI/gpt-neo-125m", "Qwen/Qwen2.5-0.5B"},
        )

    def test_exact_sizes_and_metadata_hashes_are_bound(self):
        candidates = {candidate["model_id"]: candidate for candidate in INSTANCE["candidates"]}
        self.assertEqual(candidates["EleutherAI/gpt-neo-125m"]["declared_total_bytes"], 529444041)
        self.assertEqual(candidates["EleutherAI/gpt-neo-125m"]["source_tree_metadata_sha256"], "d1ccf3ef0d557671bddcc36d212b4d911bc1acdb3f80d54847270b316dd3692b")
        self.assertEqual(candidates["Qwen/Qwen2.5-0.5B"]["declared_total_bytes"], 999586188)
        self.assertEqual(candidates["Qwen/Qwen2.5-0.5B"]["source_tree_metadata_sha256"], "ef8a4ae0108fc7582ce1104466c49dc37d1fa057dc854a01d0e1342f76b6efab")

    def test_mutations_fail_closed(self):
        mutations = []
        revoked_status = copy.deepcopy(INSTANCE)
        revoked_status["status"] = "approval_requested"
        mutations.append(revoked_status)
        wrong_revision = copy.deepcopy(INSTANCE)
        wrong_revision["candidates"][1]["revision"] = "0" * 40
        mutations.append(wrong_revision)
        wrong_operator = copy.deepcopy(INSTANCE)
        wrong_operator["operator_approval"]["operator_id"] = "other"
        mutations.append(wrong_operator)
        for mutation in mutations:
            self.assertTrue(validate_minimal(mutation, SCHEMA))
            self.assertTrue(list(Draft202012Validator(SCHEMA).iter_errors(mutation)))


if __name__ == "__main__":
    unittest.main()
