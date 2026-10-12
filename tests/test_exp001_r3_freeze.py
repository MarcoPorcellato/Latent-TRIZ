import json
import tempfile
import unittest
from pathlib import Path
from tests.a0x_test_support import synthetic_r3_root

from latent_triz.exp001_r3_freeze import Exp001FreezeError, build_freeze_manifest, verify_freeze_manifest


ROOT = Path(__file__).parents[1]


class Exp001FreezeTests(unittest.TestCase):
    def _copy(self) -> Path:
        temporary = Path(tempfile.mkdtemp(prefix="exp001-r3-freeze-"))
        destination = temporary / "repo"
        return synthetic_r3_root(destination)

    def test_review_protocol_cannot_build(self):
        repository = self._copy()
        protocol_path = repository / "experiments/exp001-reference-integrated/protocol.json"
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        protocol["protocol_status"] = "ready_for_review"
        protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
        with self.assertRaises(Exp001FreezeError):
            build_freeze_manifest(repository)

    def test_frozen_manifest_verifies_without_model_or_target(self):
        repository = self._copy()
        manifest = build_freeze_manifest(repository)
        self.assertEqual(verify_freeze_manifest(repository, manifest)["status"], "verified")
        self.assertFalse(manifest["access"]["model_loaded"])
        self.assertEqual(manifest["inventory"]["combined_records"], 85)

    def test_mutation_is_rejected(self):
        repository = self._copy()
        manifest = build_freeze_manifest(repository)
        manifest["inventory"]["combined_records"] = 84
        with self.assertRaises(Exp001FreezeError):
            verify_freeze_manifest(repository, manifest)


if __name__ == "__main__":
    unittest.main()
