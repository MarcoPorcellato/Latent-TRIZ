import json
import shutil
import tempfile
import unittest
from pathlib import Path

from latent_triz.exp001_r3_contract import Exp001ContractError, verify_contract
from tests.a0x_test_support import synthetic_r3_root


ROOT = Path(__file__).parents[1]


class Exp001R3ContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.copy = Path(self.tmp.name) / "repo"
        synthetic_r3_root(self.copy)

    def tearDown(self):
        self.tmp.cleanup()

    def test_current_contract_passes(self):
        result = verify_contract(self.copy)
        self.assertEqual(result["principles"], 40)
        self.assertEqual(result["web_resources"], 18)
        self.assertEqual(result["items"], 8)
        self.assertEqual(result["public_record_stubs"], 20)

    def test_source_hash_mutation_fails_closed(self):
        path = self.copy / "data/triz-reference-sources.json"
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaises(Exp001ContractError):
            verify_contract(self.copy)

    def test_matrix_receipts_must_match(self):
        path = self.copy / "experiments/exp001-reference-integrated/fixtures/matrix-cells.jsonl"
        record = json.loads(path.read_text().splitlines()[0])
        record["transcription_receipts"][1]["normalized_cell_sha256"] = "b" * 64
        path.write_text(json.dumps(record) + "\n" + "\n".join(path.read_text().splitlines()[1:]) + "\n", encoding="utf-8")
        with self.assertRaises(Exp001ContractError):
            verify_contract(self.copy)

    def test_unpaired_item_fails_closed(self):
        path = self.copy / "experiments/exp001-reference-integrated/fixtures/items.jsonl"
        lines = path.read_text().splitlines()
        record = json.loads(lines[0])
        record["item_id"] = "exp001-r3-orphan-blinded"
        lines[0] = json.dumps(record)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(Exp001ContractError):
            verify_contract(self.copy)

    def test_unsafe_fixture_path_fails_closed(self):
        path = self.copy / "experiments/exp001-reference-integrated/protocol.json"
        protocol = json.loads(path.read_text())
        protocol["fixture_inputs"]["items"] = "../../data/triz-reference/principles.jsonl"
        path.write_text(json.dumps(protocol), encoding="utf-8")
        with self.assertRaises(Exp001ContractError):
            verify_contract(self.copy)

    def test_option_set_target_locator_mutation_fails_closed(self):
        path = self.copy / "experiments/exp001-reference-integrated/fixtures/option-sets.jsonl"
        lines = path.read_text().splitlines()
        record = json.loads(lines[0])
        record["target_locator"] = "sealed://exp001-r3/not-in-control-plan"
        lines[0] = json.dumps(record)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with self.assertRaises(Exp001ContractError):
            verify_contract(self.copy)

    def test_analysis_plan_primary_mutation_fails_closed(self):
        path = self.copy / "experiments/exp001-reference-integrated/analysis-plan.json"
        plan = json.loads(path.read_text())
        plan["primary"]["required_units"] = 12
        path.write_text(json.dumps(plan), encoding="utf-8")
        with self.assertRaises(Exp001ContractError):
            verify_contract(self.copy)

    def test_no_model_runtime_imports(self):
        source = (ROOT / "src/latent_triz/exp001_r3_contract.py").read_text()
        self.assertNotIn("transformers", source)
        self.assertNotIn("torch", source)
        self.assertNotIn("sealed_targets", source)


if __name__ == "__main__":
    unittest.main()
