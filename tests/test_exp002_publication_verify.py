import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import exp002_publication_verify as publication_verify  # noqa: E402
from exp002_publication_verify import PublicationVerificationError, verify_publication_manifest  # noqa: E402


class Exp002PublicationVerifyTests(unittest.TestCase):
    def test_published_manifest_tracked_bindings_are_source_snapshot_safe(self):
        verify_bindings = getattr(
            publication_verify, "verify_publication_manifest_bindings", None
        )
        self.assertIsNotNone(
            verify_bindings,
            "a tracked-bindings verifier is required for source-snapshot CI",
        )
        if verify_bindings is None:
            return
        result = verify_bindings(
            "results/exp002/preexecution/publication-manifest.json", root=ROOT
        )
        self.assertEqual(result["status"], "bindings_only")
        self.assertEqual(result["packages"], 7)
        self.assertEqual(result["declared_external_assets"], 7)
        self.assertEqual(result["verified_external_assets"], [])

    def test_missing_and_mutated_external_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "schemas").mkdir()
            (root / "results").mkdir()
            (root / "schemas/exp002-publication-manifest.schema.json").write_text((ROOT / "schemas/exp002-publication-manifest.schema.json").read_text(encoding="utf-8"), encoding="utf-8")
            asset = root / "asset.bin"
            asset.write_bytes(b"stable")
            digest = hashlib.sha256(b"stable").hexdigest()
            manifest = {"artifact_class": "exp002-publication-manifest", "protocol_id": "exp002-qwen3-followup-v1.0.0", "status": "published", "packages": [], "external_dense_assets": [{"locator": "asset.bin", "sha256": digest}], "claim_ids": [], "evidence_eligible": False, "expert_validated": False}
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(verify_publication_manifest(path, root=root)["status"], "pass")
            asset.write_bytes(b"mutated")
            with self.assertRaises(PublicationVerificationError):
                verify_publication_manifest(path, root=root)
            asset.unlink()
            with self.assertRaises(PublicationVerificationError):
                verify_publication_manifest(path, root=root)

    def test_missing_or_mutated_package_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "schemas").mkdir()
            (root / "results/exp002/preexecution").mkdir(parents=True)
            shutil.copy2(ROOT / "schemas/exp002-publication-manifest.schema.json", root / "schemas/exp002-publication-manifest.schema.json")
            manifest_path = root / "results/exp002/preexecution/publication-manifest.json"
            shutil.copy2(ROOT / "results/exp002/preexecution/publication-manifest.json", manifest_path)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            package = manifest["packages"][0]
            source_package = ROOT / package["package_locator"]
            package_path = root / package["package_locator"]
            shutil.copytree(source_package, package_path)
            artifact = package_path / "report.md"
            original = artifact.read_bytes()
            artifact.write_bytes(original + b"\nmutation")
            with self.assertRaises(PublicationVerificationError):
                verify_publication_manifest(manifest_path, root=root)


if __name__ == "__main__":
    unittest.main()
