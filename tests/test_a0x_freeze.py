from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
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
    verify_protected_tree_metadata_only,
)
from latent_triz.validator import validate  # noqa: E402
from latent_triz.a0x_contract import PairBinding, derive_pair_output_path  # noqa: E402


class A0XFreezeTests(unittest.TestCase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures" / "a0x"
    ROOT = Path(__file__).resolve().parents[1]

    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary_directory.name)
        self.addCleanup(self._temporary_directory.cleanup)

    def test_implementation_inventory_is_stable_and_binds_task_one_to_six_surface(self) -> None:
        required = {
            "schemas/a0x-activation-receipt.schema.json",
            "schemas/a0x-activation-stage-occupancy-receipt.schema.json",
            "schemas/a0x-attempt-claim.schema.json",
            "schemas/a0x-external-assets-locator.schema.json",
            "schemas/a0x-model-identity-receipt.schema.json",
            "schemas/a0x-output-occupancy-receipt.schema.json",
            "schemas/a0x-preflight-receipt.schema.json",
            "schemas/a0x-representation-record.schema.json",
            "schemas/a0x-statistical-result.schema.json",
            "schemas/a0x-target-read-receipt.schema.json",
            "schemas/a0x-terminal-result.schema.json",
            "scripts/repository_check.py",
            "tests/a0x_test_support.py",
            "src/latent_triz/a0x_pair.py",
            "src/latent_triz/a0x_compatibility.py",
            "src/latent_triz/a0x_gate_contract.py",
            "src/latent_triz/a0x_schema_projection.py",
            "scripts/a0x_compatibility_check.py",
            "scripts/a0x_compile_pair_schemas.py",
            "Makefile",
            "schemas/a0x-pair-binding.fragment.json",
            "schemas/a0x-pair-projections.json",
            "tests/test_a0x_pair_compatibility.py",
            "tests/test_a0x_schema_projection.py",
            "tests/test_a0x_architecture.py",
        }
        paths = a0x_freeze._IMPLEMENTATION_PATHS
        self.assertEqual(tuple(sorted(paths)), paths)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(required.issubset(paths))
        for relative in paths:
            path = self.ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(1, path.stat().st_nlink)

    def test_schema_cross_validate_accepts_pinned_style_interpreter_path_with_spaces(self) -> None:
        interpreter = self.root / "pinned schema venv/bin/python"
        interpreter.parent.mkdir(parents=True)
        invocation_log = self.root / "interpreter-invocation.json"
        interpreter.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' \"$@\" > \"$A0X_FAKE_INTERPRETER_LOG\"\n"
            "exit 0\n",
            encoding="utf-8",
        )
        interpreter.chmod(0o700)
        environment = dict(os.environ)
        environment["A0X_FAKE_INTERPRETER_LOG"] = str(invocation_log)
        completed = subprocess.run(
            ["make", "-s", "schema-cross-validate", f"LAB01_PYTHON={interpreter}"],
            cwd=self.ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(["scripts/schema_cross_validate.py"], invocation_log.read_text(encoding="utf-8").splitlines())

    def test_file_binding_rejects_hardlink_in_temporary_tree(self) -> None:
        source = self.root / "source.py"
        bound = self.root / "bound.py"
        source.write_text("x = 1\n", encoding="utf-8")
        bound.hardlink_to(source)
        with self.assertRaisesRegex(A0XFreezeError, "hardlink"):
            a0x_freeze._file_binding(self.root, "bound.py")

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

    def test_frozen_dossier_pairs_use_canonical_output_derivation(self) -> None:
        dossiers = sorted((self.ROOT / "experiments/a0x-six-model/approval-dossiers").glob("*/*.json"))
        self.assertEqual(12, len(dossiers))
        for path in dossiers:
            with self.subTest(path=path):
                binding = PairBinding.from_dossier(json.loads(path.read_text(encoding="utf-8")))
                self.assertEqual(
                    binding.output_path,
                    derive_pair_output_path(binding.leg, binding.model_key, binding.run_id),
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

    def test_metadata_only_verifier_never_opens_any_sealed_or_calibration_target(self) -> None:
        targets = (
            "data/a0/sealed-targets/targets.jsonl",
            "data/a0/procedural-targets/calibration-targets.jsonl",
            "data/a0r1/targets/sealed.jsonl",
            "data/a0r1/targets/calibration.jsonl",
        )
        declarations: dict[str, dict[str, object]] = {}
        files: dict[str, dict[str, object]] = {}
        for index, relative in enumerate(targets):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = f"sealed-{index}".encode()
            path.write_bytes(raw)
            declarations[relative] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "provenance_manifest": "data/provenance.json"}
            files[relative] = {"path": Path(relative).relative_to("data").as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        provenance = self.root / "data/provenance.json"
        provenance.write_text(json.dumps({"files": files}), encoding="utf-8")
        tree = build_protected_tree(self.root, roots=(), external_assets=(), sealed_target_declarations=declarations)
        original_open = Path.open
        def deny_target_open(path: Path, *args: object, **kwargs: object):
            if path.resolve() in {(self.root / item).resolve() for item in targets}:
                raise AssertionError("sealed or calibration target opened")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", new=deny_target_open):
            verify_protected_tree_metadata_only(self.root, tree)

    def test_protected_tree_requires_explicit_external_assets(self) -> None:
        external = self.root / "external.bin"
        external.write_bytes(b"external")
        with self.assertRaisesRegex(A0XFreezeError, "external asset"):
            build_protected_tree(self.root, roots=(), external_assets=(Path("external.bin"),))

    def test_each_leg_inventory_binds_the_runtime_preparer_surface(self) -> None:
        """Each frozen leg must bind the preparer, its core, and its regression suite."""
        required = {
            "scripts/a0x_build_gate_b_runtime.py",
            "scripts/a0x_prepare_runtime.py",
            "src/latent_triz/a0x_apfs.py",
            "src/latent_triz/a0x_gate_b_builder.py",
            "src/latent_triz/a0x_runtime_bundle.py",
            "src/latent_triz/a0x_runtime_readiness.py",
            "src/latent_triz/a0x_wheelhouse.py",
            "tests/test_a0x_apfs.py",
            "tests/test_a0x_gate_b_builder.py",
            "tests/test_a0x_runtime_bundle.py",
            "tests/test_a0x_runtime_readiness.py",
            "tests/test_a0x_wheelhouse.py",
        }
        for leg in ("a0", "r1"):
            with self.subTest(leg=leg):
                implementation = json.loads((
                    self.ROOT / f"experiments/a0x-six-model/{leg}/implementation.json"
                ).read_text(encoding="utf-8"))
                self.assertTrue(required.issubset(implementation["implementation_paths"]))

    def test_hosted_gate_a_paths_are_bound_in_both_implementation_inventories(self) -> None:
        """Catch a hosted trust input omitted from either generated leg inventory."""
        required = {
            ".github/a0x-hosted-gate-a-actions.json",
            ".github/a0x-hosted-gate-a-lanes.json",
            ".github/workflows/a0x-hosted-gate-a.yml",
            "requirements-schema.in",
            "requirements-schema.lock",
            "schemas/a0x-execution-authorization-v3.schema.json",
            "schemas/a0x-gate-b-authorization.schema.json",
            "schemas/a0x-hosted-gate-a-evidence.schema.json",
            "schemas/a0x-hosted-gate-a-lane-receipt.schema.json",
            "schemas/a0x-hosted-gate-a-transport.schema.json",
            "schemas/a0x-hosted-gate-a-verification-receipt.schema.json",
            "schemas/a0x-hosted-gate-a-verifier-policy.schema.json",
            "scripts/a0x_hosted_gate_a.py",
            "scripts/a0x_materialize_no_model_receipt.py",
            "scripts/a0x_verify_hosted_gate_a.py",
            "src/latent_triz/a0x_hosted_gate_a.py",
            "src/latent_triz/a0x_hosted_verifier.py",
            "tests/test_a0x_hosted_gate_a.py",
            "tests/test_a0x_hosted_gate_a_workflow.py",
            "tests/test_a0x_hosted_verifier.py",
        }
        required.update(
            path.relative_to(self.ROOT).as_posix()
            for path in (self.ROOT / "tests/fixtures/a0x/hosted-gate-a").rglob("*")
            if path.is_file()
        )

        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            a0x_freeze.freeze_a0x_campaign(
                self.ROOT,
                prepare_dossiers=True,
                output_root=output_root,
                implementation_source_head="f" * 40,
            )
            implementations = {
                leg: json.loads((output_root / f"experiments/a0x-six-model/{leg}/implementation.json").read_text(encoding="utf-8"))
                for leg in ("a0", "r1")
            }

        self.assertTrue(required.issubset(a0x_freeze._IMPLEMENTATION_PATHS))
        self.assertEqual(tuple(sorted(a0x_freeze._IMPLEMENTATION_PATHS)), a0x_freeze._IMPLEMENTATION_PATHS)
        self.assertEqual(
            implementations["a0"]["implementation_paths"],
            implementations["r1"]["implementation_paths"],
        )
        self.assertEqual(
            implementations["a0"]["implementation_files"],
            implementations["r1"]["implementation_files"],
        )
        self.assertTrue(required.issubset(implementations["a0"]["implementation_paths"]))

    def test_capture_wrapper_paths_are_bound_in_both_implementation_inventories(self) -> None:
        """Catch a capture trust input omitted from either generated leg inventory."""
        required = {
            "schemas/a0x-hosted-gate-a-capture-request.schema.json",
            "schemas/a0x-hosted-gate-a-capture-transport.schema.json",
            "scripts/a0x_capture_hosted_gate_a.py",
            "src/latent_triz/a0x_hosted_capture.py",
            "tests/test_a0x_capture_hosted_gate_a.py",
            "tests/test_a0x_hosted_capture.py",
        }

        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            a0x_freeze.freeze_a0x_campaign(
                self.ROOT,
                prepare_dossiers=True,
                output_root=output_root,
                implementation_source_head="f" * 40,
            )
            path_sets = {
                leg: set(json.loads((
                    output_root / f"experiments/a0x-six-model/{leg}/implementation.json"
                ).read_text(encoding="utf-8"))["implementation_paths"])
                for leg in ("a0", "r1")
            }

        self.assertTrue(required.issubset(a0x_freeze._IMPLEMENTATION_PATHS))
        self.assertTrue(required.issubset(path_sets["a0"]))
        self.assertTrue(required.issubset(path_sets["r1"]))

    def test_vertical_slice_paths_are_bound_in_both_implementation_inventories(self) -> None:
        """Catch a pair-scoped package dependency omitted from either leg inventory."""
        required = {
            "schemas/a0x-vertical-slice-manifest.schema.json",
            "scripts/a0x_vertical_material.py",
            "src/latent_triz/a0x_vertical_slice.py",
            "tests/test_a0x_vertical_material.py",
            "tests/test_a0x_vertical_slice.py",
        }

        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            a0x_freeze.freeze_a0x_campaign(
                self.ROOT,
                prepare_dossiers=True,
                output_root=output_root,
                implementation_source_head="f" * 40,
            )
            path_sets = {
                leg: set(json.loads((
                    output_root / f"experiments/a0x-six-model/{leg}/implementation.json"
                ).read_text(encoding="utf-8"))["implementation_paths"])
                for leg in ("a0", "r1")
            }

        self.assertTrue(required.issubset(a0x_freeze._IMPLEMENTATION_PATHS))
        self.assertTrue(required.issubset(path_sets["a0"]))
        self.assertTrue(required.issubset(path_sets["r1"]))

    def test_capture_wrapper_tests_are_in_the_synthetic_aggregate(self) -> None:
        """Catch a capture-wrapper regression suite skipped by the synthetic target."""
        completed = subprocess.run(
            ["make", "-n", "a0x-synthetic-verify"],
            cwd=self.ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("tests.test_a0x_hosted_capture", completed.stdout)
        self.assertIn("tests.test_a0x_capture_hosted_gate_a", completed.stdout)

    def test_vertical_slice_test_is_once_in_the_synthetic_aggregate(self) -> None:
        """Catch an omitted or duplicated pair-package regression suite."""
        completed = subprocess.run(
            ["make", "-n", "a0x-synthetic-verify"],
            cwd=self.ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        tokens = completed.stdout.split()
        self.assertEqual(1, tokens.count("tests.test_a0x_vertical_slice"))
        self.assertEqual(1, tokens.count("tests.test_a0x_vertical_material"))

    def test_active_hosted_verifier_schemas_are_bound_in_both_implementation_inventories(self) -> None:
        """Catch a schema read by the active Hosted Gate A verifier outside both freezes."""
        active_verifier_schemas = {
            "schemas/a0x-gate-b-authorization.schema.json",
            "schemas/a0x-gh-2.97.0-verification-result.schema.json",
            "schemas/a0x-hosted-gate-a-transport.schema.json",
            "schemas/a0x-hosted-gate-a-verification-receipt.schema.json",
            "schemas/a0x-hosted-gate-a-verifier-policy.schema.json",
        }

        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            a0x_freeze.freeze_a0x_campaign(
                self.ROOT,
                prepare_dossiers=True,
                output_root=output_root,
                implementation_source_head="f" * 40,
            )
            path_sets = {
                leg: set(json.loads((
                    output_root / f"experiments/a0x-six-model/{leg}/implementation.json"
                ).read_text(encoding="utf-8"))["implementation_paths"])
                for leg in ("a0", "r1")
            }

        self.assertTrue(active_verifier_schemas.issubset(a0x_freeze._IMPLEMENTATION_PATHS))
        self.assertTrue(active_verifier_schemas.issubset(path_sets["a0"]))
        self.assertTrue(active_verifier_schemas.issubset(path_sets["r1"]))

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
