from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import latent_triz.a0x_vertical_terminal_package as terminal_package

from latent_triz.a0x_vertical_production_adapter import bind_validated_vertical_graph
from latent_triz.a0x_public_closure import TerminalClosureStatus
from latent_triz.a0x_vertical_terminal_package import (
    A0XVerticalTerminalPackageError,
    PublicVerticalPackageIntegrity,
    VerticalTerminalExpectation,
    build_vertical_terminal_package,
    verify_vertical_terminal_package,
    verify_public_vertical_terminal_package,
    _cleanup_owned_stage,
    _open_directory_chain,
)
from tests.test_a0x_vertical_production_adapter import _graph


class A0XVerticalTerminalPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        # The repository's path verifier deliberately rejects symlink
        # components. macOS exposes the default temp root through `/var`, a
        # symlink to `/private/var`; use its resolved physical parent so the
        # fixture tests the package contract rather than that OS alias.
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.root = Path(self.temp.name).resolve()
        self.expected, self.result = self._fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _fixture(self, *, qualification_context: str = "synthetic-target-free", with_assets: bool = False):
        source = self.root / "schemas/a0x-execution-authorization-v4.schema.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        schema_source = Path(__file__).resolve().parents[1] / "schemas/a0x-execution-authorization-v4.schema.json"
        raw = schema_source.read_bytes()
        source.write_bytes(raw)
        info = source.stat()
        private = self.root / ".a0x-runtime/gate-b/v2/a/b/a0/smollm2_360m/run/runtime-mapping.json"
        private.parent.mkdir(parents=True, exist_ok=True)
        private_raw = b'{"private_runtime_mapping":"synthetic only"}\n'
        private.write_bytes(private_raw)
        private_info = private.stat()
        graph = _graph(qualification_context=qualification_context)
        graph["trust_file_identities"] = {
            source.relative_to(self.root).as_posix(): {
                "device": info.st_dev,
                "inode": info.st_ino,
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            private.relative_to(self.root).as_posix(): {
                "device": private_info.st_dev,
                "inode": private_info.st_ino,
                "size": len(private_raw),
                "sha256": hashlib.sha256(private_raw).hexdigest(),
            },
        }
        asset_paths = None
        if with_assets:
            pair_value = graph["descriptor"]["pair_binding"]
            asset_base = (
                self.root / "results/a0x-external-assets" / ("a" * 40) / ("b" * 40)
                / pair_value["leg"] / pair_value["model_key"] / pair_value["run_id"]
            )
            asset_paths = {
                "dense": asset_base / "dense-output.bin",
                "index": asset_base / "representation-index.json",
            }
            for role, asset_path in asset_paths.items():
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                asset_path.write_bytes((role + " synthetic asset\n").encode())
        context = bind_validated_vertical_graph(graph, qualification_context=qualification_context)
        expected = VerticalTerminalExpectation.from_context(
            context,
            repository_root=self.root if asset_paths else None,
            external_assets=asset_paths,
        )
        result = {
            "artifact_class": "a0x-vertical-terminal-result",
            "terminal_profile": "a0x-vertical-terminal-result-v1",
            "qualified_source": {
                "head": context.source_head,
                "tree": context.source_tree,
                "ref": "refs/heads/main",
            },
            "pair_binding": context.public_identity()["pair_binding"],
            "vertical_package_digests": context.public_identity()["vertical_package_digests"],
            "qualification_context": qualification_context,
            "authorization_id": context.authorization_id,
            "attempt_id": context.attempt_id,
            "reached_frontier": "validated_graph",
            "scientific_outcome": "failed",
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
            "result_payload": {"diagnostic_code": "SYNTHETIC_FIXTURE"},
        }
        return expected, result

    def test_synthetic_terminal_package_builds_and_independently_verifies(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )

        verified = verify_vertical_terminal_package(
            package_root=destination,
            repository_root=self.root,
            expected=self.expected,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertEqual("synthetic-target-free", verified.qualification_context)
        self.assertFalse(verified.publication_eligible)
        self.assertEqual("failed", verified.scientific_outcome)
        self.assertEqual(6, len(list(destination.iterdir())))

    def _engineering_fixture(self):
        self.root = self.root / ".a0x-runtime/rehearsal/1/synthetic-repository"
        self.root.mkdir(parents=True)
        expected, result = self._fixture(qualification_context="engineering_rehearsal", with_assets=True)
        result.update(reached_frontier="sealed", scientific_outcome="null",
                      result_payload={"statistical_result_sha256": hashlib.sha256(b"synthetic statistics").hexdigest()})
        return expected, result

    def test_engineering_rehearsal_sealed_package_stays_permanently_ineligible(self):
        expected, result = self._engineering_fixture()
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(repository_root=self.root, destination=destination,
            expected=expected, terminal_result=result)
        verified = verify_vertical_terminal_package(package_root=destination, repository_root=self.root,
            expected=expected, expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256)
        self.assertFalse(verified.publication_eligible)
        self.assertEqual("engineering_rehearsal", verified.qualification_context)
        self.assertEqual("null", verified.scientific_outcome)

    def test_engineering_rehearsal_cannot_publish_under_a_real_results_root(self):
        expected, result = self._engineering_fixture()
        outer_root = Path(self.temp.name).resolve()
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "rehearsal namespace"):
            build_vertical_terminal_package(repository_root=outer_root,
                destination=outer_root / expected.pair_binding["output_path"], expected=expected, terminal_result=result)
        self.assertFalse((outer_root / "results").exists())

    def test_public_verifier_rejects_engineering_rehearsal_even_with_correct_digest_anchors(self):
        expected, result = self._engineering_fixture()
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(repository_root=self.root, destination=destination,
            expected=expected, terminal_result=result)
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "qualification context"):
            verify_public_vertical_terminal_package(evidence_root=self.root, package_root=destination,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256)

    def test_private_verifier_refuses_rehearsal_package_relocated_outside_its_namespace(self):
        expected, result = self._engineering_fixture()
        reference = build_vertical_terminal_package(repository_root=self.root,
            destination=self.root / expected.pair_binding["output_path"],
            expected=expected, terminal_result=result)
        relocated = Path(self.temp.name).resolve() / "relocated-repository"
        self.root.rename(relocated)
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "rehearsal namespace"):
            verify_vertical_terminal_package(repository_root=relocated,
                package_root=relocated / expected.pair_binding["output_path"], expected=expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256)

    def test_public_trust_manifest_contains_only_allowlisted_public_schema(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        trust_raw = (destination / "trust-manifest.json").read_bytes()
        trust = json.loads(trust_raw)
        self.assertNotIn(b".a0x-runtime", trust_raw)
        self.assertNotIn(b"runtime-mapping.json", trust_raw)
        self.assertNotIn(hashlib.sha256(b'{"private_runtime_mapping":"synthetic only"}\n').hexdigest().encode(), trust_raw)
        self.assertTrue(trust["private_execution_inputs_excluded"])
        self.assertEqual(
            [{
                "role": "execution_authorization_schema",
                "path": "execution-authorization-v4.schema.json",
                "size": len((destination / "execution-authorization-v4.schema.json").read_bytes()),
                "raw_sha256": hashlib.sha256((destination / "execution-authorization-v4.schema.json").read_bytes()).hexdigest(),
            }],
            trust["files"],
        )

    def test_public_production_verifier_requires_pinned_closure_and_cross_binds_outcome(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        production_expected = replace(self.expected, qualification_context="production")
        production_result = dict(self.result)
        production_result.update(qualification_context="production", reached_frontier="sealed")
        # Production building remains disabled; this test-only seam creates a
        # structurally valid adversarial package for the public verifier path.
        with patch.object(terminal_package, "_validate_expectation_context", return_value=None):
            reference = build_vertical_terminal_package(
                repository_root=self.root,
                destination=destination,
                expected=production_expected,
                terminal_result=production_result,
            )

        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "independently pinned"):
            verify_public_vertical_terminal_package(
                package_root=destination, evidence_root=self.root,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

        closure_status = TerminalClosureStatus(
            document_bindings_consistent=True,
            derivation_authenticated=False,
            operator_approval_authenticated=False,
            authorization_verified=False,
            publication_eligible=False,
            private_originals_verified=False,
            manifest_sha256="a" * 64,
            terminal_outcome="failed",
        )
        with patch.object(terminal_package, "load_public_terminal_closure", return_value=closure_status) as loader:
            verified = verify_public_vertical_terminal_package(
                package_root=destination, evidence_root=self.root,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
                expected_public_closure_manifest_sha256="a" * 64,
            )
        self.assertTrue(verified.public_closure_verified)
        self.assertEqual("a" * 64, verified.public_closure_manifest_sha256)
        loader.assert_called_once()

        with patch.object(
            terminal_package, "load_public_terminal_closure",
            return_value=replace(closure_status, terminal_outcome="positive"),
        ):
            with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "outcome differs"):
                verify_public_vertical_terminal_package(
                    package_root=destination, evidence_root=self.root,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                    expected_public_closure_manifest_sha256="a" * 64,
                )

    def test_public_trust_manifest_refuses_missing_allowlisted_schema(self):
        expected, result = self._fixture()
        schema = self.root / "schemas/a0x-execution-authorization-v4.schema.json"
        schema.unlink()
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_fresh_public_verifier_needs_only_package_and_declared_assets(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        fresh = Path(self.temp.name) / "fresh-public-root"
        fresh.mkdir()
        fresh_package = fresh / self.expected.pair_binding["output_path"]
        fresh_package.parent.mkdir(parents=True)
        shutil.copytree(destination, fresh_package)
        self.assertFalse((fresh / ".a0x-runtime").exists())
        verified = verify_public_vertical_terminal_package(
            package_root=fresh_package,
            evidence_root=fresh,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertIsInstance(verified, PublicVerticalPackageIntegrity)
        self.assertTrue(verified.package_integrity_verified)
        self.assertFalse(verified.execution_evidence_verified)
        self.assertFalse(verified.publication_eligible)

    def test_fresh_public_verifier_checks_pair_bound_external_assets(self):
        expected, result = self._fixture(with_assets=True)
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=expected,
            terminal_result=result,
        )
        fresh = Path(self.temp.name) / "fresh-public-assets-root"
        fresh.mkdir()
        fresh_package = fresh / expected.pair_binding["output_path"]
        fresh_package.parent.mkdir(parents=True)
        shutil.copytree(destination, fresh_package)
        for asset in expected.external_assets:
            asset_destination = fresh / asset.path
            asset_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / asset.path, asset_destination)

        verified = verify_public_vertical_terminal_package(
            package_root=fresh_package,
            evidence_root=fresh,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertTrue(verified.package_integrity_verified)
        self.assertFalse(verified.execution_evidence_verified)
        self.assertFalse(verified.publication_eligible)

        dense = next(asset for asset in expected.external_assets if asset.role == "dense")
        (fresh / dense.path).write_bytes(b"mutated asset")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_public_vertical_terminal_package(
                package_root=fresh_package,
                evidence_root=fresh,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_fresh_public_verifier_rejects_missing_external_asset(self):
        expected, result = self._fixture(with_assets=True)
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=expected,
            terminal_result=result,
        )
        fresh = Path(self.temp.name) / "fresh-public-missing-asset-root"
        fresh.mkdir()
        fresh_package = fresh / expected.pair_binding["output_path"]
        fresh_package.parent.mkdir(parents=True)
        shutil.copytree(destination, fresh_package)
        for asset in expected.external_assets:
            asset_destination = fresh / asset.path
            asset_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / asset.path, asset_destination)
        dense = next(asset for asset in expected.external_assets if asset.role == "dense")
        (fresh / dense.path).unlink()
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_public_vertical_terminal_package(
                package_root=fresh_package,
                evidence_root=fresh,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_verifier_rejects_manifest_identity_not_matching_independent_expectation(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        altered = VerticalTerminalExpectation(
            **{
                **self.expected.__dict__,
                "source_tree": "f" * 40,
            },
        )
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=altered,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_expectation_is_recursively_immutable(self):
        with self.assertRaises(TypeError):
            self.expected.pair_binding["leg"] = "r1"
        with self.assertRaises(TypeError):
            self.expected.pair_binding["dense_bound"]["leg"] = "r1"
        with self.assertRaises(TypeError):
            self.expected.vertical_package_digests["dossier_sha256"] = "f" * 64

    def test_builder_refuses_mutated_trust_input(self):
        trust_path = self.root / "schemas/a0x-execution-authorization-v4.schema.json"
        trust_path.write_bytes(b"mutated")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / self.expected.pair_binding["output_path"],
                expected=self.expected,
                terminal_result=self.result,
            )

    def test_builder_refuses_existing_destination_without_overwrite(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        destination.mkdir(parents=True)
        (destination / "operator-file").write_bytes(b"preserve")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=destination,
                expected=self.expected,
                terminal_result=self.result,
            )
        self.assertEqual(b"preserve", (destination / "operator-file").read_bytes())

    def test_verifier_rejects_extra_or_missing_package_members(self):
        for mutation in ("extra", "missing"):
            with self.subTest(mutation=mutation):
                expected, result = self._fixture()
                destination = self.root / expected.pair_binding["output_path"]
                reference = build_vertical_terminal_package(
                    repository_root=self.root,
                    destination=destination,
                    expected=expected,
                    terminal_result=result,
                )
                if mutation == "extra":
                    (destination / "undeclared.json").write_bytes(b"{}")
                else:
                    (destination / "report.md").unlink()
                with self.assertRaises(A0XVerticalTerminalPackageError):
                    verify_vertical_terminal_package(
                        package_root=destination,
                        repository_root=self.root,
                        expected=expected,
                        expected_manifest_sha256=reference.manifest_sha256,
                        expected_root_receipt_sha256=reference.root_receipt_sha256,
                    )
                shutil.rmtree(destination)

    def test_verifier_re_reads_trust_inputs_after_package_build(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        (self.root / self.expected.trust_files[0].path).write_bytes(b"changed after package build")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=self.expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_verifier_revalidates_trust_after_package_contents_are_read(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        render = terminal_package._render_report

        def mutate_trust_after_first_validation(result, expected):
            rendered = render(result, expected)
            (self.root / expected.trust_files[0].path).write_bytes(b"late trust mutation")
            return rendered

        with patch.object(terminal_package, "_render_report", side_effect=mutate_trust_after_first_validation):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_verifier_rejects_package_directory_replacement_during_verification(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        render = terminal_package._render_report
        moved = destination.with_name(destination.name + ".moved")
        replaced = False

        def replace_package_after_initial_reads(result, expected):
            nonlocal replaced
            rendered = render(result, expected)
            if not replaced:
                replaced = True
                destination.rename(moved)
                destination.mkdir()
                for member in moved.iterdir():
                    (destination / member.name).write_bytes(member.read_bytes())
            return rendered

        with patch.object(terminal_package, "_render_report", side_effect=replace_package_after_initial_reads):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_verifier_rejects_parent_directory_replacement_during_verification(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        render = terminal_package._render_report
        parent = destination.parent
        moved_parent = parent.with_name(parent.name + ".moved")
        replaced = False

        def replace_parent_after_initial_reads(result, expected):
            nonlocal replaced
            rendered = render(result, expected)
            if not replaced:
                replaced = True
                parent.rename(moved_parent)
                parent.mkdir(parents=True)
                replacement = parent / destination.name
                replacement.mkdir()
                for member in (moved_parent / destination.name).iterdir():
                    (replacement / member.name).write_bytes(member.read_bytes())
            return rendered

        with patch.object(terminal_package, "_render_report", side_effect=replace_parent_after_initial_reads):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_verifier_rejects_same_inode_same_size_late_member_rewrite(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        membership = terminal_package._verify_package_membership_fd
        calls = 0

        def mutate_after_first_member_pass(directory_fd, *, expected_names):
            nonlocal calls
            membership(directory_fd, expected_names=expected_names)
            calls += 1
            if calls == 3:
                report = destination / "report.md"
                original = report.read_bytes()
                replacement = bytes([original[0] ^ 1]) + original[1:]
                with report.open("r+b") as stream:
                    stream.write(replacement)
                    stream.flush()
                    os.fsync(stream.fileno())

        with patch.object(terminal_package, "_verify_package_membership_fd", side_effect=mutate_after_first_member_pass):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_external_asset_locator_binds_dense_and_index_bytes(self):
        expected, result = self._fixture(with_assets=True)
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=expected,
            terminal_result=result,
        )
        verified = verify_vertical_terminal_package(
            package_root=destination,
            repository_root=self.root,
            expected=expected,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertFalse(verified.publication_eligible)
        self.assertTrue((destination / "external-assets-locator.json").is_file())
        dense = self.root / expected.external_assets[0].path
        dense.write_bytes(b"mutated dense asset")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_external_asset_paths_are_exact_pair_derived_public_destinations(self):
        graph = _graph()
        context = bind_validated_vertical_graph(graph, qualification_context="synthetic-target-free")
        private_assets = {
            "dense": self.root / ".a0x-runtime/private/dense.bin",
            "index": self.root / ".a0x-runtime/private/index.json",
        }
        for path in private_assets.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic asset")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            VerticalTerminalExpectation.from_context(
                context,
                repository_root=self.root,
                external_assets=private_assets,
            )

    def test_verifier_rejects_hardlinked_package_member(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        alias = self.root / "report-alias.md"
        alias.hardlink_to(destination / "report.md")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=self.expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_production_positive_result_requires_dense_assets(self):
        context = bind_validated_vertical_graph(_graph(qualification_context="production"), qualification_context="production")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            VerticalTerminalExpectation.from_context(context)

    def test_production_label_cannot_grant_publication_eligibility(self):
        expected = replace(self.expected, qualification_context="production")
        result = dict(self.result)
        result["qualification_context"] = "production"
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_unsealed_scientific_outcome_is_rejected_even_with_assets(self):
        expected, result = self._fixture()
        result["scientific_outcome"] = "positive"
        result["result_payload"] = {"statistical_result_sha256": "d" * 64}
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_unbounded_public_payload_fields_are_rejected(self):
        expected, result = self._fixture()
        result["result_payload"] = {"log": "authorization token=private"}
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_fabricated_production_context_cannot_create_package_expectation(self):
        context = bind_validated_vertical_graph(_graph(qualification_context="production"), qualification_context="production")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            VerticalTerminalExpectation.from_context(context)

    def test_cleanup_refuses_replacement_stage_directory(self):
        parent = self.root / "safe-parent"
        parent.mkdir()
        parent_fd = _open_directory_chain(self.root, parent, create=False)
        stage_name = ".owned-stage"
        os.mkdir(stage_name, dir_fd=parent_fd)
        owned_fd = os.open(stage_name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0), dir_fd=parent_fd)
        owned_info = os.fstat(owned_fd)
        os.rename(parent / stage_name, parent / ".moved-owned-stage")
        os.mkdir(parent / stage_name)
        (parent / stage_name / "do-not-delete").write_bytes(b"operator data")
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "OWNERSHIP_LOST"):
            _cleanup_owned_stage(
                parent_fd=parent_fd,
                stage_fd=owned_fd,
                stage_name=stage_name,
                stage_identity=(owned_info.st_dev, owned_info.st_ino),
                file_identities={},
            )
        self.assertEqual(b"operator data", (parent / stage_name / "do-not-delete").read_bytes())
        os.close(owned_fd)
        os.close(parent_fd)


if __name__ == "__main__":
    unittest.main()
