import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from latent_triz.validator import validate as validate_minimal
from tests.a0x_test_support import synthetic_acquisition_authorization


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/exp001-additional-model-authorization.schema.json"
INSTANCE = ROOT / "experiments/exp001-comparative-reference/additional-model-authorization.json"


class AdditionalModelAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.instance = synthetic_acquisition_authorization()

    def test_authorization_is_valid_under_both_validators(self):
        self.assertEqual(validate_minimal(self.instance, self.schema), [])
        self.assertEqual(list(Draft202012Validator(self.schema).iter_errors(self.instance)), [])
        self.assertEqual(self.instance["status"], "authorized")
        self.assertTrue(self.instance["execution"]["one_run_per_model"])

    def test_authorization_mutations_fail_closed(self):
        mutations = []
        for path, value in ((["operator_approval", "granted"], False), (["execution", "network"], True)):
            mutated = copy.deepcopy(self.instance)
            mutated[path[0]][path[1]] = value
            mutations.append(mutated)
        unknown = copy.deepcopy(self.instance)
        unknown["candidates"][0]["model_id"] = "unknown/model"
        mutations.append(unknown)
        for mutation in mutations:
            self.assertTrue(validate_minimal(mutation, self.schema))
            self.assertTrue(list(Draft202012Validator(self.schema).iter_errors(mutation)))


if __name__ == "__main__":
    unittest.main()
