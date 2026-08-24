from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import latent_triz.a0x_freeze as a0x_freeze  # noqa: E402
from latent_triz.a0x_freeze import (  # noqa: E402
    A0XFreezeError,
    build_a0_selection_manifest,
    build_protected_tree,
    verify_a0_selection_manifest,
    verify_protected_tree,
)
from latent_triz.validator import validate  # noqa: E402


class A0XFreezeTests(unittest.TestCase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures" / "a0x"

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary_directory.name)
        self.addCleanup(self._temporary_directory.cleanup)

    def test_selection_uses_public_cases_only_and_is_deterministic(self) -> None:
        manifest = build_a0_selection_manifest(
            cases_path=self.FIXTURES / "public-cases-mini.jsonl",
            corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
        )
        repeated = build_a0_selection_manifest(
            cases_path=self.FIXTURES / "public-cases-mini.jsonl",
            corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
        )
        self.assertEqual(48, len(manifest["cases"]))
        self.assertEqual(
            ["agriculture_01_a", "agriculture_01_b"],
            [row["case_id"] for row in manifest["cases"][:2]],
        )
        self.assertEqual(manifest, repeated)
        self.assertEqual(0, manifest["target_content_reads"])
        self.assertNotIn("agriculture_99", {row["problem_family_id"] for row in manifest["cases"]})
        self.assertEqual(
            {"case_id", "case_content_sha256", "domain", "problem_family_id", "split"},
            set(manifest["cases"][0]),
        )
        self.assertTrue(all("operator_proxy_family" not in row for row in manifest["cases"]))
        self.assertTrue(all("target" not in key for row in manifest["cases"] for key in row))
        verify_a0_selection_manifest(
            manifest,
            cases_path=self.FIXTURES / "public-cases-mini.jsonl",
            corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
        )

    def test_selection_fails_closed_when_a_family_does_not_have_two_cases(self) -> None:
        cases = (self.FIXTURES / "public-cases-mini.jsonl").read_text(encoding="utf-8").splitlines()
        truncated = self.root / "cases.jsonl"
        truncated.write_text("\n".join(cases[1:]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(A0XFreezeError, "two cases"):
            build_a0_selection_manifest(
                cases_path=truncated,
                corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
            )

    def test_selection_rejects_tampered_case_content_binding(self) -> None:
        manifest = build_a0_selection_manifest(
            cases_path=self.FIXTURES / "public-cases-mini.jsonl",
            corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
        )
        altered = copy.deepcopy(manifest)
        altered["cases"][0]["case_content_sha256"] = "0" * 64
        with self.assertRaisesRegex(A0XFreezeError, "selection manifest"):
            verify_a0_selection_manifest(
                altered,
                cases_path=self.FIXTURES / "public-cases-mini.jsonl",
                corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
            )

    def test_protected_tree_detects_one_byte_drift(self) -> None:
        protected = self.root / "historical"
        protected.mkdir()
        (protected / "input.json").write_text("original", encoding="utf-8")
        tree = build_protected_tree(self.root, roots=(Path("historical"),), external_assets=())
        (protected / "input.json").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(A0XFreezeError, "protected input drift"):
            verify_protected_tree(self.root, tree, phase="postflight")

    def test_protected_tree_is_sorted_and_rejects_symlinks(self) -> None:
        historical = self.root / "historical"
        historical.mkdir()
        (historical / "z.json").write_text("z", encoding="utf-8")
        (historical / "a.json").write_text("a", encoding="utf-8")
        tree = build_protected_tree(self.root, roots=(Path("historical"),), external_assets=())
        self.assertEqual(["historical/a.json", "historical/z.json"], [row["path"] for row in tree["entries"]])
        (historical / "link.json").symlink_to(historical / "a.json")
        with self.assertRaisesRegex(A0XFreezeError, "symlink"):
            build_protected_tree(self.root, roots=(Path("historical"),), external_assets=())

    def test_protected_tree_rejects_a_symlinked_directory_ancestor_during_construction(self) -> None:
        backing = self.root / "backing"
        (backing / "nested").mkdir(parents=True)
        (backing / "nested" / "input.json").write_text("input", encoding="utf-8")
        (self.root / "linked").symlink_to(backing, target_is_directory=True)
        with self.assertRaisesRegex(A0XFreezeError, "symlink"):
            build_protected_tree(self.root, roots=(Path("linked/nested"),), external_assets=())

    def test_protected_tree_rejects_a_symlinked_directory_ancestor_during_verification(self) -> None:
        alias = self.root / "alias"
        (alias / "nested").mkdir(parents=True)
        (alias / "nested" / "input.json").write_text("input", encoding="utf-8")
        tree = build_protected_tree(self.root, roots=(Path("alias/nested"),), external_assets=())
        backing = self.root / "backing"
        (backing / "nested").mkdir(parents=True)
        (backing / "nested" / "input.json").write_text("input", encoding="utf-8")
        (alias / "nested" / "input.json").unlink()
        (alias / "nested").rmdir()
        alias.rmdir()
        alias.symlink_to(backing, target_is_directory=True)
        with self.assertRaisesRegex(A0XFreezeError, "symlink"):
            verify_protected_tree(self.root, tree, phase="preflight")

    def test_protected_tree_never_opens_declared_target(self) -> None:
        target = self.root / "data/a0/sealed-targets/targets.jsonl"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"must-not-be-opened")
        provenance = self.root / "data/a0/manifest.json"
        provenance.parent.mkdir(parents=True, exist_ok=True)
        provenance.write_text(
            json.dumps({
                "files": {
                    "sealed": {
                        "path": "sealed-targets/targets.jsonl",
                        "sha256": hashlib.sha256(b"must-not-be-opened").hexdigest(),
                        "size": 18,
                    }
                }
            }) + "\n",
            encoding="utf-8",
        )
        declarations = {
            "data/a0/sealed-targets/targets.jsonl": {
                "sha256": hashlib.sha256(b"must-not-be-opened").hexdigest(),
                "bytes": 18,
                "provenance_manifest": "data/a0/manifest.json",
            }
        }
        original_open = Path.open
        original_read_bytes = Path.read_bytes
        original_read_text = Path.read_text
        original_stat = Path.stat
        original_sha256_file = a0x_freeze.sha256_file

        def deny_target_open(path: Path, *args: object, **kwargs: object):
            if path == target:
                raise AssertionError("target opened")
            return original_open(path, *args, **kwargs)

        def deny_target_read_bytes(path: Path, *args: object, **kwargs: object):
            if path == target:
                raise AssertionError("target read_bytes")
            return original_read_bytes(path, *args, **kwargs)

        def deny_target_read_text(path: Path, *args: object, **kwargs: object):
            if path == target:
                raise AssertionError("target read_text")
            return original_read_text(path, *args, **kwargs)

        def deny_target_stat(path: Path, *args: object, **kwargs: object):
            if path == target:
                raise AssertionError("target stat")
            return original_stat(path, *args, **kwargs)

        def deny_target_hash(path: str | Path) -> str:
            if Path(path) == target:
                raise AssertionError("target sha256_file")
            return original_sha256_file(path)

        with (
            patch.object(Path, "open", new=deny_target_open),
            patch.object(Path, "read_bytes", new=deny_target_read_bytes),
            patch.object(Path, "read_text", new=deny_target_read_text),
            patch.object(Path, "stat", new=deny_target_stat),
            patch.object(a0x_freeze, "sha256_file", new=deny_target_hash),
        ):
            tree = build_protected_tree(
                self.root,
                roots=(),
                external_assets=(),
                sealed_target_declarations=declarations,
            )
            verify_protected_tree(self.root, tree, phase="preflight")
        self.assertEqual("declaration_only", tree["entries"][0]["verification_phase"])

    def test_protected_tree_requires_explicit_external_assets(self) -> None:
        external = self.root / "external.bin"
        external.write_bytes(b"external")
        with self.assertRaisesRegex(A0XFreezeError, "external asset"):
            build_protected_tree(self.root, roots=(), external_assets=(Path("external.bin"),))

    def test_complete_artifacts_validate_the_strict_task_two_schemas(self) -> None:
        historical = self.root / "historical"
        historical.mkdir()
        (historical / "input.json").write_text("input", encoding="utf-8")
        tree = build_protected_tree(self.root, roots=(Path("historical"),), external_assets=())
        selection = build_a0_selection_manifest(
            cases_path=self.FIXTURES / "public-cases-mini.jsonl",
            corpus_manifest_path=self.FIXTURES / "public-manifest-mini.json",
        )
        schema_root = Path(__file__).resolve().parents[1] / "schemas"
        for payload, schema_name in (
            (tree, "a0x-protected-tree.schema.json"),
            (selection, "a0x-selection-manifest.schema.json"),
        ):
            with self.subTest(schema=schema_name):
                schema = json.loads((schema_root / schema_name).read_text(encoding="utf-8"))
                self.assertEqual([], validate(payload, schema))


if __name__ == "__main__":
    unittest.main()
