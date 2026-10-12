import json
import tempfile
import unittest
from pathlib import Path
from tests.a0x_test_support import synthetic_comparative_root

from latent_triz.exp001_comparative_contract import (
    ComparativeContractError,
    validate_comparative_contract,
)


class ComparativeContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = synthetic_comparative_root(Path(self.temporary.name))

    def test_frozen_dossier_is_target_free_and_exact(self):
        audit = validate_comparative_contract(self.root)
        self.assertEqual(audit["status"], "pass")
        self.assertEqual(audit["model_count"], 3)
        self.assertEqual(audit["records_per_model"], 85)
        self.assertFalse(audit["model_accessed"])
        self.assertFalse(audit["sealed_targets_accessed"])

    def test_model_substitution_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_comparative_root(root)
            registry_path = root / "experiments/exp001-comparative-reference/model-registry.json"
            registry = json.loads(registry_path.read_text())
            registry["models"][2]["model_id"] = "google/gemma-3-270m"
            registry_path.write_text(json.dumps(registry))
            with self.assertRaises(ComparativeContractError):
                validate_comparative_contract(root)

    def test_network_and_target_boundaries_are_rejected_if_mutated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_comparative_root(root)
            protocol_path = root / "experiments/exp001-comparative-reference/protocol.json"
            protocol = json.loads(protocol_path.read_text())
            protocol["model_execution"]["network_access"] = True
            protocol_path.write_text(json.dumps(protocol))
            with self.assertRaises(ComparativeContractError):
                validate_comparative_contract(root)

    def test_qwen_download_authorization_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_comparative_root(root)
            dossier_path = root / "experiments/exp001-comparative-reference/qwen-acquisition-dossier.json"
            dossier = json.loads(dossier_path.read_text())
            dossier["download_authorized"] = False
            dossier_path.write_text(json.dumps(dossier))
            with self.assertRaises(ComparativeContractError):
                validate_comparative_contract(root)

    def test_material_permission_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            synthetic_comparative_root(root)
            auth_path = root / "experiments/exp001-comparative-reference/execution-authorization.json"
            auth = json.loads(auth_path.read_text())
            auth["permissions_requested"]["load_existing_pythia_once"] = False
            auth_path.write_text(json.dumps(auth))
            with self.assertRaises(ComparativeContractError):
                validate_comparative_contract(root)


if __name__ == "__main__":
    unittest.main()
