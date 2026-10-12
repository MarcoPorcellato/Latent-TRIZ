import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from tests.a0x_test_support import synthetic_schema_object


ROOT = Path(__file__).resolve().parents[1]


class Exp002SchemaGuardTests(unittest.TestCase):
    def setUp(self):
        self.answer_schema = json.loads((ROOT / "schemas/exp002-direct-answer-key.schema.json").read_text(encoding="utf-8"))
        self.answer_template = json.loads((ROOT / "results/exp002/preexecution/direct-answer-key-template.json").read_text(encoding="utf-8"))
        self.collection_schema = json.loads((ROOT / "schemas/exp002-expert-review-collection.schema.json").read_text(encoding="utf-8"))
        self.collection_template = json.loads((ROOT / "experiments/exp002-qwen3-followup/expert-review-collection.json").read_text(encoding="utf-8"))
        self.transfer_schema = json.loads((ROOT / "schemas/exp002-transfer-corpus.schema.json").read_text(encoding="utf-8"))
        self.transfer_template = json.loads((ROOT / "experiments/exp002-qwen3-followup/transfer-corpus-template.json").read_text(encoding="utf-8"))
        self.target_schema = json.loads((ROOT / "schemas/exp002-transfer-target-key.schema.json").read_text(encoding="utf-8"))
        self.target_template = synthetic_schema_object(self.target_schema)
        self.target_template["target_content_sha256"] = None
        self.dossier_schema = json.loads((ROOT / "schemas/exp002-study-approval-dossier.schema.json").read_text(encoding="utf-8"))
        self.dossier = json.loads((ROOT / "experiments/exp002-qwen3-followup/exp002b-approval-dossier.json").read_text(encoding="utf-8"))

    def test_tracked_empty_templates_validate(self):
        self.assertFalse(list(Draft202012Validator(self.answer_schema).iter_errors(self.answer_template)))
        self.assertFalse(list(Draft202012Validator(self.collection_schema).iter_errors(self.collection_template)))
        self.assertFalse(list(Draft202012Validator(self.transfer_schema).iter_errors(self.transfer_template)))
        self.assertFalse(list(Draft202012Validator(self.target_schema).iter_errors(self.target_template)))
        self.assertFalse(list(Draft202012Validator(self.dossier_schema).iter_errors(self.dossier)))

    def test_exact_answer_and_frozen_review_requirements_are_schema_bound(self):
        invalid_record = copy.deepcopy(self.answer_template)
        invalid_record["status"] = "expert_review"
        invalid_record["records"] = [{"question_id": "exp002-q1", "key_type": "exact", "expert_status": "reviewed"}]
        invalid_record["expert_review"]["status"] = "pending"
        self.assertTrue(list(Draft202012Validator(self.answer_schema).iter_errors(invalid_record)))

        invalid_frozen = copy.deepcopy(self.answer_template)
        invalid_frozen["status"] = "frozen"
        invalid_frozen["records"] = [{"question_id": "exp002-q1", "key_type": "rubric_required", "expert_status": "reviewed"}]
        invalid_frozen["expert_review"].update({"status": "complete", "reviewer_count": 2, "reviewer_ids": ["r1", "r2"]})
        self.assertTrue(list(Draft202012Validator(self.answer_schema).iter_errors(invalid_frozen)))

    def test_submitted_collection_requires_three_packets(self):
        invalid = copy.deepcopy(self.collection_template)
        invalid["status"] = "submitted"
        invalid["packets"] = []
        self.assertTrue(list(Draft202012Validator(self.collection_schema).iter_errors(invalid)))

    def test_frozen_transfer_corpus_cannot_be_empty(self):
        invalid = copy.deepcopy(self.transfer_template)
        invalid["status"] = "frozen_no_model"
        self.assertTrue(list(Draft202012Validator(self.transfer_schema).iter_errors(invalid)))

    def test_frozen_target_key_requires_sealed_hash_and_records(self):
        valid = copy.deepcopy(self.target_template)
        valid["status"] = "frozen_no_model"
        valid["records"] = [{"case_id": "exp002c-case-1", "domain": "manufacturing", "expected_candidate_index": 0}]
        valid["target_content_sha256"] = "b" * 64
        self.assertFalse(list(Draft202012Validator(self.target_schema).iter_errors(valid)))

        invalid = copy.deepcopy(valid)
        invalid["target_content_sha256"] = None
        self.assertTrue(list(Draft202012Validator(self.target_schema).iter_errors(invalid)))

    def test_authorized_dossier_requires_source_proximity_pass(self):
        invalid = copy.deepcopy(self.dossier)
        invalid["status"] = "authorized"
        invalid["operator_approval"] = {"granted": True, "operator_id": "MarcoPorcellato", "approved_at": "2026-08-20", "approval_text_sha256": "a" * 64}
        invalid["prerequisites"]["answer_key_status"] = "frozen"
        invalid["prerequisites"]["source_proximity_status"] = "pending"
        self.assertTrue(list(Draft202012Validator(self.dossier_schema).iter_errors(invalid)))


if __name__ == "__main__":
    unittest.main()
