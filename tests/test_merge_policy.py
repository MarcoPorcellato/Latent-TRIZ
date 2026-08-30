import json
import tempfile
import unittest
from pathlib import Path

from latent_triz.merge_policy import (
    ChangedFile,
    MergePolicyError,
    audit_scientific_artifacts,
    classify_paths,
    load_changed_files,
)


class MergePolicyTests(unittest.TestCase):
    def test_docs_only_stays_lightweight(self) -> None:
        decision = classify_paths(["docs/ROADMAP.md", "README.md"])
        self.assertTrue(decision.docs_only)
        self.assertFalse(decision.require_repository_check)
        self.assertFalse(decision.require_python_311)
        self.assertFalse(decision.require_ccp)

    def test_code_requires_both_supported_python_versions(self) -> None:
        decision = classify_paths([
            "src/latent_triz/validator.py", "tests/test_validator.py",
        ])
        self.assertTrue(decision.require_repository_check)
        self.assertTrue(decision.require_python_311)
        self.assertFalse(decision.require_ccp)

    def test_scientific_artifact_uses_hosted_check_and_audit(self) -> None:
        decision = classify_paths(["experiments/exp-001/config.json"])
        self.assertFalse(decision.require_ccp)
        self.assertTrue(decision.require_repository_check)
        self.assertTrue(decision.require_scientific_audit)
        self.assertFalse(decision.require_python_311)

    def test_governance_uses_dual_python_without_automatic_ccp(self) -> None:
        decision = classify_paths([".github/workflows/merge-policy.yml"])
        self.assertFalse(decision.require_ccp)
        self.assertTrue(decision.require_repository_check)
        self.assertTrue(decision.require_python_311)

    def test_runtime_definition_uses_dual_python_without_scientific_audit(self) -> None:
        decision = classify_paths([
            ".dockerignore", "containers/verification/Dockerfile",
        ])
        self.assertEqual(decision.categories, ("runtime",))
        self.assertTrue(decision.require_repository_check)
        self.assertTrue(decision.require_python_311)
        self.assertFalse(decision.require_ccp)
        self.assertFalse(decision.require_scientific_audit)

    def test_model_artifact_is_highest_risk(self) -> None:
        decision = classify_paths([
            "results/lab01/model-representations/summary.json",
        ])
        self.assertFalse(decision.require_ccp)
        self.assertTrue(decision.require_repository_check)
        self.assertTrue(decision.require_scientific_audit)
        self.assertTrue(decision.require_model_artifact_audit)

    def test_unknown_path_fails_closed(self) -> None:
        decision = classify_paths(["new-surface/payload.dat"])
        self.assertIn("unknown", decision.categories)
        self.assertTrue(decision.require_python_311)
        self.assertFalse(decision.require_ccp)
        self.assertTrue(decision.require_repository_check)
        self.assertTrue(decision.require_scientific_audit)

    def test_unsafe_path_is_rejected(self) -> None:
        with self.assertRaises(MergePolicyError):
            classify_paths(["../outside.json"])

    def test_paginated_github_payload_is_flattened(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary) / "files.json"
            payload.write_text(
                json.dumps([[{"filename": "docs/README.md", "status": "modified"}]]),
                encoding="utf-8",
            )
            self.assertEqual(
                load_changed_files(payload),
                [ChangedFile("docs/README.md", "modified")],
            )

    def test_scientific_json_and_jsonl_are_audited(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data/config.json").write_text('{"ok":true}\n', encoding="utf-8")
            (root / "data/rows.jsonl").write_text('{"id":1}\n', encoding="utf-8")
            result = audit_scientific_artifacts(
                root,
                [ChangedFile("data/config.json"), ChangedFile("data/rows.jsonl")],
            )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(len(result["audited_paths"]), 2)

    def test_dense_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "results/lab01/model-representations/activations.safetensors"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"not-a-real-tensor")
            with self.assertRaisesRegex(MergePolicyError, "external and hash-referenced"):
                audit_scientific_artifacts(
                    root,
                    [ChangedFile(
                        "results/lab01/model-representations/activations.safetensors"
                    )],
                )

    def test_model_backed_metadata_requires_hash_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "results/lab01/model-representations/summary.json"
            target.parent.mkdir(parents=True)
            target.write_text('{"status":"pass"}\n', encoding="utf-8")
            with self.assertRaisesRegex(MergePolicyError, "containing a SHA-256"):
                audit_scientific_artifacts(
                    root,
                    [ChangedFile("results/lab01/model-representations/summary.json")],
                )

    def test_model_backed_metadata_accepts_hash_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "results/lab01/model-representations/summary.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps({"artifact_sha256": "a" * 64}) + "\n",
                encoding="utf-8",
            )
            result = audit_scientific_artifacts(
                root,
                [ChangedFile("results/lab01/model-representations/summary.json")],
            )
            self.assertEqual(result["model_artifact_gate"], "pass")

    def test_invalid_jsonl_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "data/rows.jsonl"
            target.parent.mkdir()
            target.write_text("not-json\n", encoding="utf-8")
            with self.assertRaisesRegex(MergePolicyError, "invalid JSONL"):
                audit_scientific_artifacts(root, [ChangedFile("data/rows.jsonl")])

    def test_removed_model_artifact_does_not_require_new_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = audit_scientific_artifacts(
                Path(temporary),
                [ChangedFile(
                    "results/lab01/model-representations/obsolete.json",
                    status="removed",
                )],
            )
            self.assertEqual(result["model_artifact_gate"], "pass")


if __name__ == "__main__":
    unittest.main()
