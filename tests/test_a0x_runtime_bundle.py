from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from latent_triz.a0x_contract import PairBinding
from latent_triz.a0x_material_contract import derive_runtime_paths
from tests.a0x_test_support import authorization_documents, pair_binding, qualification_receipt


class A0XRuntimeBundleTests(unittest.TestCase):
    @staticmethod
    def _cli_module():
        path = Path(__file__).parents[1] / "scripts/a0x_prepare_runtime.py"
        specification = importlib.util.spec_from_file_location("a0x_prepare_runtime_test", path)
        if specification is None or specification.loader is None:
            raise AssertionError("runtime preparation CLI is unavailable")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, object]:
        from latent_triz.a0x_runtime_bundle import RuntimePreparationRequest

        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        pair = PairBinding.from_mapping(pair_binding())
        source_head = "a" * 40
        paths = derive_runtime_paths(pair, source_head=source_head)
        contract = {
            "artifact_class": "a0x-material-execution-contract",
            "contract_version": "a0x-material-execution-contract-v2",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "ccp": {
                "source_commit": "b" * 40,
                "source_tree": "c" * 40,
                "sha256": hashlib.sha256(b"synthetic ccp").hexdigest(),
                "version": "commit-ci-preflight 0.1.0",
            },
        }
        contract_path = root / "experiments/a0x-six-model/material-execution-contract.json"
        contract_path.parent.mkdir(parents=True)
        contract_path.write_bytes(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode())
        dossier, _authorization, _chain = authorization_documents(pair.as_mapping())
        dossier["implementation_source_head"] = source_head
        dossier["material_contract_raw_sha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        dossier["runtime_authorization_path"] = paths.authorization_path
        fixed_dossier = "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"
        dossier_path = root / fixed_dossier
        dossier_path.parent.mkdir(parents=True)
        dossier_path.write_bytes(json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode())
        receipt_path = root / paths.qualification_receipt_path
        receipt_path.parent.mkdir(parents=True)
        receipt_path.write_bytes(qualification_receipt(source_head))
        child_path = root / "scripts/a0x_material_child.py"
        child_path.parent.mkdir(parents=True)
        child_path.write_bytes(b"synthetic child")
        ccp_path = root / "bin/commit-ci-preflight"
        ccp_path.parent.mkdir(parents=True)
        ccp_path.write_bytes(b"synthetic ccp")
        ccp_path.chmod(0o700)
        python_path = root / "bin/python"
        python_path.write_bytes(b"synthetic python")
        python_path.chmod(0o700)
        request = RuntimePreparationRequest(
            fixed_dossier=fixed_dossier,
            qualification_receipt=receipt_path,
            ccp_executable=ccp_path,
            python_executable=python_path,
            public_evidence_commit="e" * 40,
            authorization_id="a0x-auth-a0-gpt2-attempt-01",
            attempt_id="a0x-a0-gpt2-attempt-01",
        )
        return temporary, root, request

    def test_prepares_one_acyclic_bundle_in_dependency_order(self) -> None:
        from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        with patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}):
            receipt = prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )
        descriptor = root / receipt["descriptor_path"]
        authorization = root / receipt["authorization_path"]
        mapping = root / receipt["mapping_path"]
        self.assertTrue(descriptor.is_file())
        self.assertTrue(authorization.is_file())
        self.assertTrue(mapping.is_file())
        descriptor_document = json.loads(descriptor.read_text(encoding="utf-8"))
        authorization_document = json.loads(authorization.read_text(encoding="utf-8"))
        mapping_document = json.loads(mapping.read_text(encoding="utf-8"))
        self.assertNotIn("authorization", descriptor_document)
        descriptor_sha256 = hashlib.sha256(descriptor.read_bytes()).hexdigest()
        self.assertEqual(descriptor_sha256, authorization_document["guard_launch"]["launch_descriptor"]["sha256"])
        self.assertEqual(receipt["descriptor_path"], mapping_document["descriptor"]["path"])
        self.assertEqual(descriptor_sha256, mapping_document["descriptor"]["sha256"])

    def test_second_preparation_refuses_without_changing_first_bundle_bytes(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        patch_target = "latent_triz.a0x_runtime_bundle.planned_material_dossiers"
        with patch(patch_target, return_value={("a0", "gpt2"): request.fixed_dossier}):
            receipt = prepare_runtime_bundle(root, request, source_state_probe=lambda: ("a" * 40, True), ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0")
            first_bytes = {name: (root / receipt[f"{name}_path"]).read_bytes() for name in ("descriptor", "authorization", "mapping")}
            with self.assertRaises(A0XRuntimeBundleError):
                prepare_runtime_bundle(root, request, source_state_probe=lambda: ("a" * 40, True), ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0")
        self.assertEqual(first_bytes, {name: (root / receipt[f"{name}_path"]).read_bytes() for name in first_bytes})

    def test_preparation_never_reaches_material_or_process_seams(self) -> None:
        from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        patch_target = "latent_triz.a0x_runtime_bundle.planned_material_dossiers"
        with (
            patch(patch_target, return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch("subprocess.run", side_effect=AssertionError("subprocess.run reached")) as process_run,
            patch("subprocess.Popen", side_effect=AssertionError("subprocess.Popen reached")) as process_open,
            patch("latent_triz.a0x_ccp_executor.launch_fixed_dossier", side_effect=AssertionError("guard launch reached")) as launch,
            patch("latent_triz.a0x_execution.OneShotTargetReader", side_effect=AssertionError("target reader reached")) as target_reader,
            patch("latent_triz.a0x_model_adapter.A0XHiddenStateAdapter", side_effect=AssertionError("model adapter reached")) as model_adapter,
            patch("latent_triz.a0x_production_adapter._default_dependencies", side_effect=AssertionError("model factory reached")) as model_factory,
        ):
            receipt = prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )
        self.assertEqual("prepared", receipt["status"])
        process_run.assert_not_called()
        process_open.assert_not_called()
        launch.assert_not_called()
        target_reader.assert_not_called()
        model_adapter.assert_not_called()
        model_factory.assert_not_called()

    def test_dirty_source_refuses_before_any_runtime_output(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(A0XRuntimeBundleError, "clean checkout"):
            prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, False),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )
        self.assertFalse((root / ".a0x-runtime/launches").exists())
        self.assertFalse((root / ".a0x-runtime/authorizations").exists())
        self.assertFalse((root / ".a0x-runtime/bin").exists())

    def test_cli_prepares_sorted_public_receipt_from_shell_free_probes(self) -> None:
        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        cli = self._cli_module()
        output = io.StringIO()

        class Result:
            def __init__(self, stdout: str) -> None:
                self.returncode = 0
                self.stdout = stdout

        def probe(argv, **_kwargs):
            if argv == ["git", "rev-parse", "HEAD"]:
                return Result("a" * 40 + "\n")
            if argv == ["git", "status", "--porcelain", "--untracked-files=all"]:
                return Result("")
            if argv == [str(request.ccp_executable.resolve()), "--version"]:
                return Result("commit-ci-preflight 0.1.0\n")
            raise AssertionError(f"unexpected probe argv: {argv}")

        argv = [
            "--fixed-dossier", request.fixed_dossier,
            "--qualification-receipt", str(request.qualification_receipt),
            "--ccp", str(request.ccp_executable),
            "--python", str(request.python_executable),
            "--public-evidence-commit", request.public_evidence_commit,
            "--authorization-id", request.authorization_id,
            "--attempt-id", request.attempt_id,
        ]
        with (
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch.object(cli.subprocess, "run", side_effect=probe),
        ):
            code = cli.main(argv, root=root, stdout=output)
        self.assertEqual(0, code)
        receipt = json.loads(output.getvalue())
        self.assertEqual("prepared", receipt["status"])
        self.assertEqual(sorted(receipt), list(receipt))
