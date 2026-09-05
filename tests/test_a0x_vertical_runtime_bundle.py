from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from latent_triz.a0x_contract import Leg
from latent_triz.a0x_gate_contract import (
    GateBAuthorizationInputs,
    HashBoundPath,
    HostedInputBindings,
    VerifierIdentity,
    VerticalGateBAuthorizationInputs,
    build_vertical_gate_b_authorization,
)
from latent_triz.a0x_vertical_slice import (
    VerticalRuntimePackageRequest,
    generate_vertical_runtime_package,
)
from tests.test_a0x_vertical_slice import HEAD, TREE, ROOT, _copy_file, _publish_at, _synthetic_repository


class A0XVerticalRuntimeBundleTests(unittest.TestCase):
    """The v2 Gate B route accepts only a real Task-1 package binding."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        _synthetic_repository(self.root)
        _copy_file(ROOT, self.root, "schemas/a0x-vertical-slice-manifest-v2.schema.json")
        _copy_file(ROOT, self.root, "schemas/a0x-vertical-package-commitment-v2.schema.json")
        self.tree_patch = mock.patch("latent_triz.a0x_vertical_slice._git_tree_for_head", return_value=TREE)
        self.publish_patch = mock.patch("latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", new=_publish_at)
        self.checkout_patch = mock.patch("latent_triz.a0x_vertical_slice._checkout_state", return_value=(HEAD, TREE, True))
        self.tree_patch.start()
        self.publish_patch.start()
        self.checkout_patch.start()

    def tearDown(self) -> None:
        self.checkout_patch.stop()
        self.publish_patch.stop()
        self.tree_patch.stop()
        self.temporary.cleanup()

    def _binding(self):
        return generate_vertical_runtime_package(
            self.root,
            VerticalRuntimePackageRequest(
                qualified_source_head=HEAD,
                qualified_source_tree=TREE,
                leg=Leg.A0,
                model_key="smollm2_360m",
                output_root=f".a0x-runtime/p0/v2/{HEAD}/{TREE}/a0/smollm2_360m",
                authorization_id="p0-auth-test-01",
                attempt_id="p0-attempt-test-01",
            ),
        )

    def _request(self, binding):
        from latent_triz.a0x_runtime_bundle import VerticalRuntimePreparationRequest

        evidence = self.root / f".a0x-runtime/gate-a/evidence/{HEAD}"
        evidence.mkdir(parents=True)
        hosted: dict[str, HashBoundPath] = {}
        for name, filename in (
            ("manifest", "hosted-gate-a-evidence.json"),
            ("attestation_bundle", "hosted-gate-a-attestation.bundle.jsonl"),
            ("trusted_root", "github-trusted-root.jsonl"),
            ("transport", "hosted-gate-a-transport.json"),
        ):
            path = evidence / filename
            path.write_bytes(f"synthetic-{name}".encode())
            hosted[name] = HashBoundPath(
                path=path.relative_to(self.root).as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        verifier = self.root / "bin/gh"
        verifier.parent.mkdir(parents=True)
        verifier.write_bytes(b"synthetic verifier")
        verifier.chmod(0o700)
        policy = self.root / "gate-b/verifier-policy.json"
        policy.parent.mkdir()
        policy.write_bytes(b"{}")
        authorization = build_vertical_gate_b_authorization(
            binding.pair_binding,
            VerticalGateBAuthorizationInputs(
                base=GateBAuthorizationInputs(
                    authorization_id="gate-b-auth-test-01",
                    source_head=HEAD,
                    source_tree=TREE,
                    source_sha=HEAD,
                    job_workflow_sha=HEAD,
                    hosted_inputs=HostedInputBindings(**hosted),
                    verifier=VerifierIdentity(policy_raw_sha256=hashlib.sha256(policy.read_bytes()).hexdigest()),
                ),
                envelope_path=binding.envelope_path,
                package_path=binding.package_path,
                commitment_path=binding.commitment_path,
                commitment_raw_sha256=binding.commitment_raw_sha256,
                package_commitment_sha256=binding.package_commitment_sha256,
                dossier_path=binding.dossier_path,
                dossier_sha256=binding.dossier_sha256,
            ),
        )
        authorization_path = self.root / "gate-b/vertical-authorization.json"
        authorization_path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
        ccp = self.root / "bin/commit-ci-preflight"
        ccp.write_bytes(b"synthetic ccp")
        ccp.chmod(0o700)
        python = self.root / "bin/python"
        python.write_bytes(b"synthetic python")
        python.chmod(0o700)
        return VerticalRuntimePreparationRequest(
            package_binding=binding,
            gate_b_authorization=authorization_path,
            verifier_executable=verifier,
            verifier_policy=policy,
            ccp_executable=ccp,
            python_executable=python,
            authorization_id="gate-b-auth-test-01",
            attempt_id="gate-b-attempt-test-01",
        )

    def test_preflight_binds_real_v2_package_before_external_probes(self) -> None:
        from latent_triz.a0x_runtime_bundle import preflight_vertical_runtime_bundle

        binding = self._binding()
        request = self._request(binding)
        version = mock.Mock(return_value="commit-ci-preflight 0.1.0")
        expected_ccp = json.loads(
            (self.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(encoding="utf-8")
        )["ccp"]["sha256"]
        actual_hash = __import__("latent_triz.a0x_runtime_bundle", fromlist=["sha256_file"]).sha256_file
        with mock.patch(
            "latent_triz.a0x_runtime_bundle.sha256_file",
            side_effect=lambda path: (
                expected_ccp if Path(path).resolve() == request.ccp_executable.resolve()
                else "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
                if Path(path).resolve() == request.verifier_executable.resolve()
                else actual_hash(path)
            ),
        ):
            result = preflight_vertical_runtime_bundle(
                self.root,
                request,
                source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=version,
                runtime_readiness_probe=mock.Mock(side_effect=AssertionError("readiness reached")),
            )
        self.assertEqual({"head": HEAD, "tree": TREE}, result["qualified_source"])
        self.assertEqual(binding.package_commitment_sha256, result["package_commitment_sha256"])
        self.assertEqual(binding.dossier_sha256, result["dossier_sha256"])
        version.assert_called_once()

    def test_package_or_source_mismatch_refuses_before_version_probe(self) -> None:
        from dataclasses import replace
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, preflight_vertical_runtime_bundle

        binding = self._binding()
        request = self._request(binding)
        version = mock.Mock(side_effect=AssertionError("version reached"))
        for rejected, state in (
            (replace(binding, qualified_source_tree="c" * 40), (HEAD, TREE, True)),
            (binding, (HEAD, "c" * 40, True)),
        ):
            with self.subTest(rejected=rejected, state=state), self.assertRaises(A0XRuntimeBundleError):
                preflight_vertical_runtime_bundle(
                    self.root,
                    replace(request, package_binding=rejected),
                    source_state_probe=lambda state=state: state,
                    ccp_version_probe=version,
                    runtime_readiness_probe=mock.Mock(side_effect=AssertionError("readiness reached")),
                )
        version.assert_not_called()

    def test_missing_typed_binding_dirty_source_and_occupied_output_refuse_before_verifier(self) -> None:
        """The v2 selector has no batch fallback or output reuse path."""
        from dataclasses import replace
        from latent_triz.a0x_runtime_readiness import runtime_readiness_path
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, preflight_vertical_runtime_bundle

        binding = self._binding()
        request = self._request(binding)
        version = mock.Mock(side_effect=AssertionError("version reached"))
        verifier = mock.Mock(side_effect=AssertionError("verifier reached"))
        readiness = mock.Mock(side_effect=AssertionError("readiness reached"))
        with self.assertRaises(A0XRuntimeBundleError):
            preflight_vertical_runtime_bundle(
                self.root,
                replace(request, package_binding=object()),  # type: ignore[arg-type]
                source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=version,
                runtime_readiness_probe=readiness,
                gate_a_verifier=verifier,
            )
        with self.assertRaises(A0XRuntimeBundleError):
            preflight_vertical_runtime_bundle(
                self.root,
                request,
                source_state_probe=lambda: (HEAD, TREE, False),
                ccp_version_probe=version,
                runtime_readiness_probe=readiness,
                gate_a_verifier=verifier,
            )
        occupied = self.root / runtime_readiness_path(binding.pair_binding)
        occupied.parent.mkdir(parents=True, exist_ok=True)
        occupied.write_bytes(b"occupied")
        with self.assertRaises(A0XRuntimeBundleError):
            preflight_vertical_runtime_bundle(
                self.root,
                request,
                source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=version,
                runtime_readiness_probe=readiness,
                gate_a_verifier=verifier,
            )
        version.assert_not_called()
        verifier.assert_not_called()
        readiness.assert_not_called()

    def test_hosted_input_drift_refuses_before_verifier_or_readiness(self) -> None:
        binding = self._binding()
        request = self._request(binding)
        authorization = json.loads(request.gate_b_authorization.read_text(encoding="utf-8"))
        manifest = self.root / authorization["hosted_inputs"]["manifest"]["path"]
        manifest.write_bytes(b"drifted")
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, preflight_vertical_runtime_bundle

        verifier = mock.Mock(side_effect=AssertionError("verifier reached"))
        readiness = mock.Mock(side_effect=AssertionError("readiness reached"))
        expected_ccp = json.loads(
            (self.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(encoding="utf-8")
        )["ccp"]["sha256"]
        actual_hash = __import__("latent_triz.a0x_runtime_bundle", fromlist=["sha256_file"]).sha256_file
        with (
            mock.patch(
                "latent_triz.a0x_runtime_bundle.sha256_file",
                side_effect=lambda path: expected_ccp if Path(path).resolve() == request.ccp_executable.resolve() else actual_hash(path),
            ),
            self.assertRaises(A0XRuntimeBundleError),
        ):
            preflight_vertical_runtime_bundle(
                self.root,
                request,
                source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=readiness,
                gate_a_verifier=verifier,
            )
        verifier.assert_not_called()
        readiness.assert_not_called()

    def test_v2_authorization_rejects_v1_or_binding_drift(self) -> None:
        binding = self._binding()
        request = self._request(binding)
        raw = json.loads(request.gate_b_authorization.read_text(encoding="utf-8"))
        raw["authorization_profile"] = "a0x-gate-b-authorization-v1"
        request.gate_b_authorization.write_bytes(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode())
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, preflight_vertical_runtime_bundle
        with self.assertRaises(A0XRuntimeBundleError):
            preflight_vertical_runtime_bundle(
                self.root, request, source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=mock.Mock(side_effect=AssertionError("version reached")),
                runtime_readiness_probe=mock.Mock(side_effect=AssertionError("readiness reached")),
            )

    def test_package_mutation_and_cli_selector_refuse_before_external_probe(self) -> None:
        from latent_triz.a0x_runtime_bundle import (
            A0XRuntimeBundleError,
            preflight_vertical_runtime_bundle,
            vertical_package_binding_from_commitment,
        )

        binding = self._binding()
        request = self._request(binding)
        self.assertEqual(
            binding,
            vertical_package_binding_from_commitment(self.root, binding.commitment_path),
        )
        (self.root / binding.package_path / "unexpected.json").write_bytes(b"{}\n")
        version = mock.Mock(side_effect=AssertionError("version reached"))
        with self.assertRaises(A0XRuntimeBundleError):
            preflight_vertical_runtime_bundle(
                self.root, request, source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=version,
                runtime_readiness_probe=mock.Mock(side_effect=AssertionError("readiness reached")),
            )
        version.assert_not_called()

    def test_prepare_uses_v2_selector_and_writes_no_material_output(self) -> None:
        from latent_triz.a0x_runtime_bundle import prepare_vertical_runtime_bundle
        from tests.test_a0x_runtime_bundle import _synthetic_gate_a_verifier

        binding = self._binding()
        request = self._request(binding)
        expected_ccp = json.loads(
            (self.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(encoding="utf-8")
        )["ccp"]["sha256"]
        actual_hash = __import__("latent_triz.a0x_runtime_bundle", fromlist=["sha256_file"]).sha256_file
        readiness = {"artifact_class": "synthetic-readiness"}
        with (
            mock.patch(
                "latent_triz.a0x_runtime_bundle.sha256_file",
                side_effect=lambda path: (
                    expected_ccp if Path(path).resolve() == request.ccp_executable.resolve()
                    else "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
                    if Path(path).resolve() == request.verifier_executable.resolve()
                    else actual_hash(path)
                ),
            ),
            mock.patch("latent_triz.a0x_runtime_bundle._runtime_readiness", return_value=readiness),
            mock.patch("latent_triz.a0x_runtime_bundle.validate_gate_a_evidence", side_effect=lambda value: dict(value)),
        ):
            result = prepare_vertical_runtime_bundle(
                self.root,
                request,
                source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=mock.Mock(side_effect=AssertionError("direct readiness probe reached")),
                gate_a_verifier=_synthetic_gate_a_verifier,
            )
        self.assertEqual("prepared", result["status"])
        self.assertEqual(binding.package_commitment_sha256, result["package_commitment_sha256"])
        self.assertTrue((self.root / result["readiness_path"]).is_file())
        self.assertFalse((self.root / binding.pair_binding.output_path).exists())

    def test_prepare_revalidates_package_after_injected_verifier(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_vertical_runtime_bundle
        from tests.test_a0x_runtime_bundle import _synthetic_gate_a_verifier

        binding = self._binding()
        request = self._request(binding)
        expected_ccp = json.loads(
            (self.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(encoding="utf-8")
        )["ccp"]["sha256"]
        actual_hash = __import__("latent_triz.a0x_runtime_bundle", fromlist=["sha256_file"]).sha256_file

        def mutate_after_receipt(verifier_request):
            raw = _synthetic_gate_a_verifier(verifier_request)
            (self.root / binding.package_path / "protocol.json").write_bytes(b"{}\n")
            return raw

        with (
            mock.patch(
                "latent_triz.a0x_runtime_bundle.sha256_file",
                side_effect=lambda path: (
                    expected_ccp if Path(path).resolve() == request.ccp_executable.resolve()
                    else "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
                    if Path(path).resolve() == request.verifier_executable.resolve()
                    else actual_hash(path)
                ),
            ),
            mock.patch("latent_triz.a0x_runtime_bundle.validate_gate_a_evidence", side_effect=lambda value: dict(value)),
            self.assertRaises(A0XRuntimeBundleError),
        ):
            prepare_vertical_runtime_bundle(
                self.root, request, source_state_probe=lambda: (HEAD, TREE, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=mock.Mock(side_effect=AssertionError("readiness reached")),
                gate_a_verifier=mutate_after_receipt,
            )
        self.assertFalse((self.root / ".a0x-runtime/launches").exists())
