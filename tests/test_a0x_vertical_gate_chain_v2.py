"""Disposable-real-Git proof for the target-free A0X vertical v2 boundary.

This suite deliberately uses the production P0 generator and loader against a
real committed repository.  It never invokes hosted tooling, CCP, Docker, a
model, a tokenizer, a target, or a scoring path.  The full positive Gate-B/C
leg is added only when the immutable pinned verifier executable is available;
the pre-Gate-B mutation cases here still prove that no external callback can
be reached through an invalid P0 package.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import inspect
import hashlib
import json
from dataclasses import replace
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
from latent_triz.a0x_runtime_bundle import (
    A0XRuntimeBundleError,
    VerticalRuntimePreparationRequest,
    canonical_json_bytes,
    preflight_vertical_runtime_bundle,
)
from latent_triz.a0x_vertical_slice import (
    A0XVerticalSliceError,
    VerticalRuntimePackageRequest,
    generate_vertical_runtime_package,
    load_vertical_runtime_package,
)
from tests.test_a0x_vertical_slice import ROOT, _copy_file, _publish_at, _synthetic_repository


_GIT_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}


class A0XVerticalGateChainV2RealGitTests(unittest.TestCase):
    """P0 v2 must be constructible without changing real Git identity."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        _synthetic_repository(self.root)
        for relative in (
            "schemas/a0x-vertical-slice-manifest-v2.schema.json",
            "schemas/a0x-vertical-package-commitment-v2.schema.json",
            "schemas/a0x-gate-b-authorization-v2.schema.json",
            "schemas/a0x-vertical-gate-b-output-v2.schema.json",
            "schemas/a0x-execution-authorization-v4.schema.json",
            "schemas/a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1.schema.json",
        ):
            _copy_file(ROOT, self.root, relative)
        (self.root / ".gitignore").write_text(
            ".a0x-runtime/\ngate-b/\nbin/\n", encoding="utf-8"
        )
        self._git("init", "-q")
        self._git("config", "user.name", "A0X Target-Free Test")
        self._git("config", "user.email", "a0x@example.invalid")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "real source fixture")
        self.head = self._git_output("rev-parse", "HEAD")
        self.tree = self._git_output("rev-parse", "HEAD^{tree}")
        self.publish_patch = None
        if sys.platform != "darwin":
            self.publish_patch = mock.patch(
                "latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at",
                new=_publish_at,
            )
            self.publish_patch.start()

    def tearDown(self) -> None:
        if self.publish_patch is not None:
            self.publish_patch.stop()
        self.temporary.cleanup()

    def _git(self, *argv: str) -> None:
        subprocess.run(
            ("/usr/bin/git", "-C", str(self.root), *argv), check=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_GIT_ENV,
        )

    def _git_output(self, *argv: str) -> str:
        return subprocess.check_output(
            ("/usr/bin/git", "-C", str(self.root), *argv), env=_GIT_ENV, text=True,
        ).strip()

    def _request(self) -> VerticalRuntimePackageRequest:
        return VerticalRuntimePackageRequest(
            qualified_source_head=self.head,
            qualified_source_tree=self.tree,
            leg=Leg.A0,
            model_key="smollm2_360m",
            output_root=(
                f".a0x-runtime/p0/v2/{self.head}/{self.tree}/a0/smollm2_360m"
            ),
            authorization_id="p0-real-git-auth-01",
            attempt_id="p0-real-git-attempt-01",
        )

    def _binding(self):
        return generate_vertical_runtime_package(self.root, self._request())

    def _source_state(self) -> tuple[str, str, bool]:
        return (
            self._git_output("rev-parse", "HEAD"),
            self._git_output("rev-parse", "HEAD^{tree}"),
            self._git_output("status", "--porcelain=v1", "--untracked-files=all") == "",
        )

    def _synthetic_gate_b_request(self, binding) -> VerticalRuntimePreparationRequest:
        """Create ignored, exact-bound synthetic external inputs for private core only."""
        hosted_root = self.root / f".a0x-runtime/gate-a/evidence/{self.head}"
        hosted_root.mkdir(parents=True, exist_ok=True)
        hosted: dict[str, HashBoundPath] = {}
        for name, filename in (
            ("manifest", "hosted-gate-a-evidence.json"),
            ("attestation_bundle", "hosted-gate-a-attestation.bundle.jsonl"),
            ("trusted_root", "github-trusted-root.jsonl"),
            ("transport", "hosted-gate-a-transport.json"),
        ):
            path = hosted_root / filename
            path.write_bytes(f"synthetic-{name}".encode("ascii"))
            hosted[name] = HashBoundPath(
                path=path.relative_to(self.root).as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        executable = self.root / "bin/gh"
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_bytes(b"synthetic hosted verifier")
        executable.chmod(0o700)
        policy = self.root / "gate-b/verifier-policy.json"
        policy.parent.mkdir(exist_ok=True)
        policy.write_bytes(b"{}")
        authorization = build_vertical_gate_b_authorization(
            binding.pair_binding,
            VerticalGateBAuthorizationInputs(
                base=GateBAuthorizationInputs(
                    authorization_id="gate-b-real-git-auth-01",
                    source_head=self.head,
                    source_tree=self.tree,
                    source_sha=self.head,
                    job_workflow_sha=self.head,
                    hosted_inputs=HostedInputBindings(**hosted),
                    verifier=VerifierIdentity(
                        policy_raw_sha256=hashlib.sha256(policy.read_bytes()).hexdigest(),
                    ),
                ),
                envelope_path=binding.envelope_path,
                package_path=binding.package_path,
                commitment_path=binding.commitment_path,
                commitment_raw_sha256=binding.commitment_raw_sha256,
                package_commitment_sha256=binding.package_commitment_sha256,
                dossier_path=binding.dossier_path,
                dossier_sha256=binding.dossier_sha256,
                qualification_context="synthetic-target-free",
            ),
        )
        authorization["verifier"]["sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
        authorization_path = self.root / "gate-b/vertical-authorization.json"
        authorization_path.write_bytes(canonical_json_bytes(authorization))
        ccp = self.root / "bin/commit-ci-preflight"
        ccp.write_bytes(b"synthetic ccp")
        ccp.chmod(0o700)
        python = self.root / "bin/python"
        python.write_bytes(b"synthetic python")
        python.chmod(0o700)
        return VerticalRuntimePreparationRequest(
            package_binding=binding,
            gate_b_authorization=authorization_path,
            verifier_executable=executable,
            verifier_policy=policy,
            ccp_executable=ccp,
            python_executable=python,
            authorization_id="gate-b-real-git-auth-01",
            attempt_id="gate-b-real-git-attempt-01",
        )

    def _synthetic_gate_b_dependencies(self, request, capabilities):
        """Private synthetic capability lane; all document checks remain production code."""
        from latent_triz.a0x_ccp_executor import _ExecutableIdentityEvidence
        from latent_triz.a0x_contract import sha256_file
        from latent_triz.a0x_hosted_gate_a import canonical_json_bytes as hosted_json
        from latent_triz.a0x_runtime_bundle import _GateBDependencies, _HostedVerificationResult
        from latent_triz.a0x_runtime_readiness import EXPECTED_API_SYMBOLS, EXPECTED_PACKAGES

        class HostedVerifier:
            calls = 0

            def verify(inner_self, verifier_request):
                inner_self.calls += 1
                capabilities["hosted"] += 1
                raw_authorization = verifier_request.authorization_path.read_bytes()
                value = json.loads(raw_authorization)
                receipt = {
                    "artifact_class": "a0x-hosted-gate-a-verification-receipt-synthetic-target-free",
                    "receipt_profile": "a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1",
                    "qualification_context": "synthetic-target-free",
                    "verification_status": "verified",
                    "repository": "MarcoPorcellato/Latent-TRIZ",
                    "qualified_source_head": value["source_head"],
                    "qualified_source_tree": value["source_tree"],
                    "pair_binding": value["pair_binding"],
                    "authorization_raw_sha256": hashlib.sha256(raw_authorization).hexdigest(),
                    "hosted_inputs": value["hosted_inputs"],
                    "verifier": value["verifier"],
                    "verified_at": "2026-09-05T00:00:00Z",
                }
                raw = hosted_json(receipt)
                output = verifier_request.repository_root / value["verification_receipt_path"]
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(raw)
                return _HostedVerificationResult(
                    raw,
                    _ExecutableIdentityEvidence(
                        role=value["verifier"]["role"], path=verifier_request.verifier_executable,
                        sha256=sha256_file(verifier_request.verifier_executable),
                        version=value["verifier"]["version"], synthetic=True,
                    ),
                    "synthetic-target-free",
                )

        class CcpIdentity:
            def verify(inner_self, *, role, path, expected_sha256, expected_version=None):
                return _ExecutableIdentityEvidence(
                    role=role, path=Path(path), sha256=expected_sha256,
                    version=expected_version, synthetic=True,
                )

        def readiness(_root, pair, source_head, python_path):
            capabilities["readiness"] += 1
            return {
                "artifact_class": "a0x-runtime-readiness",
                "readiness_profile": "a0x-runtime-readiness-v1",
                "source_head": source_head,
                "pair_binding": pair.as_mapping(),
                "python": {
                    "path": str(python_path), "sha256": sha256_file(python_path),
                    "version": "3.11.13", "major_minor": [3, 11],
                    "environment_root": str(python_path.parent.parent), "base_prefix": "/synthetic/base",
                    "packages": dict(EXPECTED_PACKAGES), "api_symbols": dict(EXPECTED_API_SYMBOLS),
                },
                "model_runtime": {
                    "model_key": pair.model_key, "model_id": pair.model_id, "revision": pair.revision,
                    "card_path": "experiments/a0x-six-model/model-cards/smollm2_360m.json",
                    "card_sha256": "0" * 64, "runtime_root": "artifacts/synthetic",
                    "runtime_file_count": 1, "runtime_total_bytes": 1,
                    "runtime_files_commitment_sha256": "1" * 64,
                },
            }

        return _GateBDependencies(
            hosted_verifier=HostedVerifier(), ccp_identity_verifier=CcpIdentity(),
            readiness_probe=readiness, context="synthetic-target-free",
        )

    def _assert_gate_b_refuses_before_hosted_or_readiness(self, binding, request) -> None:
        """A v2 selector/static binding failure spends neither external Gate-B capability."""
        from latent_triz.a0x_runtime_bundle import (
            A0XRuntimeBundleError, _prepare_vertical_runtime_bundle_core,
        )

        capabilities = {
            "guard": 0, "model": 0, "tokenizer": 0, "target": 0,
            "network": 0, "ccp": 0, "docker": 0, "hosted": 0, "readiness": 0,
        }
        with self.assertRaises(A0XRuntimeBundleError):
            _prepare_vertical_runtime_bundle_core(
                self.root, request, source_state_probe=self._source_state,
                dependencies=self._synthetic_gate_b_dependencies(request, capabilities),
            )
        self.assertEqual(0, capabilities["hosted"])
        self.assertEqual(0, capabilities["readiness"])
        self.assertEqual(
            {"guard": 0, "model": 0, "tokenizer": 0, "target": 0, "network": 0, "ccp": 0, "docker": 0},
            {name: capabilities[name] for name in ("guard", "model", "tokenizer", "target", "network", "ccp", "docker")},
        )

    def _rewrite_gate_b_authorization(self, request, mutate) -> None:
        """Apply one canonical raw-authority mutation before any Gate-B capability."""
        value = json.loads(request.gate_b_authorization.read_text(encoding="utf-8"))
        mutate(value)
        request.gate_b_authorization.write_bytes(canonical_json_bytes(value))

    def test_public_gate_b_entrypoint_has_no_dependency_injection(self) -> None:
        """Only the private core may accept synthetic target-free dependencies."""
        from latent_triz.a0x_runtime_bundle import prepare_vertical_runtime_bundle

        self.assertEqual(
            {"root", "request"},
            set(inspect.signature(prepare_vertical_runtime_bundle).parameters),
        )

    def _invalid_gate_b_request(self, binding):
        """A package refusal must occur before these deliberately unusable inputs."""
        return VerticalRuntimePreparationRequest(
            package_binding=binding,
            gate_b_authorization=self.root / "gate-b/authorization.json",
            verifier_executable=self.root / "bin/gh",
            verifier_policy=self.root / "gate-b/policy.json",
            ccp_executable=self.root / "bin/commit-ci-preflight",
            python_executable=self.root / "bin/python",
            authorization_id="gate-b-real-git-auth-01",
            attempt_id="gate-b-real-git-attempt-01",
        )

    def _assert_pre_gate_b_refusal(self, binding) -> None:
        version = mock.Mock(side_effect=AssertionError("CCP version probe reached"))
        readiness = mock.Mock(side_effect=AssertionError("runtime readiness reached"))
        verifier = mock.Mock(side_effect=AssertionError("hosted verifier reached"))
        with self.assertRaises(A0XRuntimeBundleError):
            preflight_vertical_runtime_bundle(
                self.root, self._invalid_gate_b_request(binding),
                source_state_probe=lambda: (self.head, self.tree, True),
                ccp_version_probe=version,
                runtime_readiness_probe=readiness,
                gate_a_verifier=verifier,
            )
        version.assert_not_called()
        readiness.assert_not_called()
        verifier.assert_not_called()

    def test_real_git_p0_v2_preserves_head_tree_and_clean_status(self) -> None:
        before = (self._git_output("rev-parse", "HEAD"), self._git_output("rev-parse", "HEAD^{tree}"), self._git_output("status", "--porcelain=v1", "--untracked-files=all"))
        binding = self._binding()
        loaded = load_vertical_runtime_package(self.root, binding)
        after = (self._git_output("rev-parse", "HEAD"), self._git_output("rev-parse", "HEAD^{tree}"), self._git_output("status", "--porcelain=v1", "--untracked-files=all"))

        self.assertEqual(before, after)
        self.assertEqual((self.head, self.tree, ""), after)
        envelope = self.root / binding.envelope_path
        self.assertEqual({"package", "p0-commitment.json"}, {entry.name for entry in envelope.iterdir()})
        self.assertEqual(
            {"protocol.json", "implementation.json", "freeze.json", "approval-dossier.json", "slice-manifest.json"},
            {entry.name for entry in (envelope / "package").iterdir()},
        )
        self.assertEqual(binding.package_commitment_sha256, loaded["package_commitment_sha256"])

    def test_real_git_p0_mutations_refuse_before_gate_b_capabilities(self) -> None:
        """Every damaged ignored P0 envelope is terminal before Gate-B hooks."""
        mutations = (
            "member_bytes", "manifest_member_order", "extra_member", "missing_member",
            "symlink", "hardlink", "nonregular_member", "renamed_member_same_cardinality",
            "commitment", "dossier",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                binding = self._binding()
                package = self.root / binding.package_path
                member = package / "protocol.json"
                if mutation == "member_bytes":
                    member.write_bytes(member.read_bytes() + b" ")
                elif mutation == "manifest_member_order":
                    manifest = package / "slice-manifest.json"
                    value = json.loads(manifest.read_text(encoding="utf-8"))
                    value["members"] = list(reversed(value["members"]))
                    manifest.write_bytes(canonical_json_bytes(value))
                elif mutation == "extra_member":
                    (package / "unexpected.json").write_bytes(b"{}\n")
                elif mutation == "missing_member":
                    (package / "freeze.json").unlink()
                elif mutation == "symlink":
                    member.unlink()
                    member.symlink_to("implementation.json")
                elif mutation == "hardlink":
                    member.unlink()
                    os.link(package / "implementation.json", member)
                elif mutation == "nonregular_member":
                    member.unlink()
                    member.mkdir()
                elif mutation == "renamed_member_same_cardinality":
                    member.rename(package / "protocol-renamed.json")
                elif mutation == "commitment":
                    commitment = self.root / binding.commitment_path
                    commitment.write_bytes(commitment.read_bytes() + b" ")
                elif mutation == "dossier":
                    dossier = self.root / binding.dossier_path
                    dossier.write_bytes(dossier.read_bytes() + b" ")
                self._assert_pre_gate_b_refusal(binding)
                shutil.rmtree(self.root / binding.envelope_path)

    def test_real_git_p0_v1_package_and_historical_batch_dossier_refuse_before_gate_b(self) -> None:
        """A v2 binding cannot reuse a historical package shape or the twelve-dossier batch."""
        historical = self.root / "experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json"
        for mutation in ("v1_package", "historical_batch_dossier"):
            with self.subTest(mutation=mutation):
                binding = self._binding()
                package = self.root / binding.package_path
                if mutation == "v1_package":
                    manifest = package / "slice-manifest.json"
                    value = json.loads(manifest.read_text(encoding="utf-8"))
                    value["artifact_class"] = "a0x-vertical-slice-manifest"
                    value["generator_profile"] = "a0x-vertical-slice-v1"
                    manifest.write_bytes(canonical_json_bytes(value))
                else:
                    (package / "approval-dossier.json").write_bytes(historical.read_bytes())
                self._assert_pre_gate_b_refusal(binding)
                shutil.rmtree(self.root / binding.envelope_path)

    def test_real_git_gate_b_refuses_pair_selector_drift_before_hosted_or_readiness(self) -> None:
        """Leg, model key, and revision are all typed selector fields, not labels."""
        for mutation in (
            lambda binding: replace(binding, leg=Leg.R1),
            lambda binding: replace(binding, model_key="gpt2"),
            lambda binding: replace(binding, model_revision="0" * 40),
        ):
            with self.subTest(mutation=mutation):
                binding = mutation(self._binding())
                request = self._synthetic_gate_b_request(binding)
                self._assert_gate_b_refuses_before_hosted_or_readiness(binding, request)
                shutil.rmtree(self.root / ".a0x-runtime/p0", ignore_errors=True)

    def test_real_git_gate_b_refuses_hosted_gate_a_head_or_tree_mismatch_before_verifier(self) -> None:
        """Hosted Gate-A source identity is not a mutable annotation on the Gate-B request."""
        for field in ("source_head", "source_tree"):
            with self.subTest(field=field):
                binding = self._binding()
                request = self._synthetic_gate_b_request(binding)
                self._rewrite_gate_b_authorization(request, lambda value, field=field: value.__setitem__(field, "0" * 40))
                self._assert_gate_b_refuses_before_hosted_or_readiness(binding, request)
                shutil.rmtree(self.root / ".a0x-runtime/p0", ignore_errors=True)

    def test_real_git_gate_b_occupied_destination_refuses_before_verifier_or_readiness(self) -> None:
        """One occupied derived output is terminal before external Gate-B capabilities."""
        from latent_triz.a0x_runtime_bundle import _vertical_output_paths

        binding = self._binding()
        request = self._synthetic_gate_b_request(binding)
        occupied = self.root / _vertical_output_paths(binding).readiness
        occupied.parent.mkdir(parents=True, exist_ok=True)
        occupied.write_bytes(b"occupied")
        self._assert_gate_b_refuses_before_hosted_or_readiness(binding, request)

    def test_real_git_p0_source_drift_refuses_before_gate_b_capabilities(self) -> None:
        binding = self._binding()
        tracked = self.root / "source-drift.txt"
        tracked.write_text("source drift\n", encoding="utf-8")
        self._git("add", "source-drift.txt")
        self._git("commit", "-q", "-m", "source drift")
        self._assert_pre_gate_b_refusal(binding)

    def test_real_git_p0_dirty_checkout_refuses_before_gate_b_capabilities(self) -> None:
        binding = self._binding()
        (self.root / "dirty-tracked.txt").write_text("dirty\n", encoding="utf-8")
        self._assert_pre_gate_b_refusal(binding)

    def _synthetic_execution_authorization(self, binding, prepared) -> dict[str, object]:
        """Build v4 bytes from actual private Gate-B wrappers, not a parallel fixture graph."""
        outputs = prepared["vertical_outputs"]
        references = {
            name: {"path": relative, "sha256": hashlib.sha256((self.root / relative).read_bytes()).hexdigest()}
            for name, relative in outputs.items()
        }
        descriptor = json.loads((self.root / outputs["descriptor"]).read_text(encoding="utf-8"))["payload"]
        mapping = json.loads((self.root / outputs["mapping"]).read_text(encoding="utf-8"))["payload"]
        guard_launch = {
            "launch_profile": "a0x-guard-launch-v2",
            "ccp": {"role": "ccp", "sha256": mapping["ccp"]["sha256"]},
            "python": {"role": "python", "sha256": mapping["python"]["sha256"]},
            "cwd_kind": "repository_root", "source_head": self.head,
            "child_script": descriptor["child_script"],
            "launch_descriptor": {
                "role": "descriptor", "path": outputs["descriptor"],
                "sha256": references["descriptor"]["sha256"],
            },
            "environment_template": descriptor["environment_template"],
            "resource": {
                "profile": "a0x-material", "workload_family": "latent-triz-a0x-v1",
                "executor": "native", "cache_state": "warm", "execution_mode": "native",
                "target_platform": "macos-arm64", "memory_limit_bytes": 8589934592,
            },
            "timeouts": {
                "outer_timeout_seconds": 3600, "internal_budget_seconds": 3300,
                "cleanup_margin_seconds": 300, "admission_timeout_seconds": 300,
            },
            "argv_template": [
                "{CCP}", "guard", "exec", "--admission-timeout-seconds", "300",
                "--timeout-seconds", "3600", "--resource-profile", "a0x-material",
                "--resource-workload-family", "latent-triz-a0x-v1", "--resource-executor", "native",
                "--resource-cache-state", "warm", "--resource-execution-mode", "native",
                "--resource-target-platform", "macos-arm64", "--resource-memory-limit-bytes", "8589934592",
                "--", "{PYTHON}", "{CHILD}", "--launch-descriptor", "{DESCRIPTOR}",
            ],
        }
        return {
            "artifact_class": "a0x-vertical-execution-authorization",
            "commitment_profile": "a0x-execution-authorization-json-v4",
            "qualified_source": {"head": self.head, "tree": self.tree, "ref": "refs/heads/main"},
            "pair_binding": binding.pair_binding.as_mapping(),
            "vertical_package": {
                "envelope_path": binding.envelope_path, "package_path": binding.package_path,
                "commitment_path": binding.commitment_path,
                "commitment_raw_sha256": binding.commitment_raw_sha256,
                "package_commitment_sha256": binding.package_commitment_sha256,
                "dossier_path": binding.dossier_path, "dossier_sha256": binding.dossier_sha256,
            },
            "qualification_context": "synthetic-target-free",
            "gate_b_authorization": {
                "path": prepared["gate_b_authorization_path"],
                "sha256": hashlib.sha256((self.root / prepared["gate_b_authorization_path"]).read_bytes()).hexdigest(),
            },
            "gate_a_verification_receipt": {
                "path": prepared["verification_receipt_path"],
                "sha256": hashlib.sha256((self.root / prepared["verification_receipt_path"]).read_bytes()).hexdigest(),
            },
            "gate_b_outputs": references, "guard_launch": guard_launch,
            "authorization_id": "gate-c-real-git-auth-01", "attempt_id": "gate-c-real-git-attempt-01",
            "max_guard_exec_count": 1, "stop_boundary": "after_one_sealed_target_read",
        }

    def _private_synthetic_chain(self):
        """Material-free P0/Gate-B graph rooted in this test's committed H/T."""
        from latent_triz.a0x_ccp_executor import vertical_execution_authorization_path
        from latent_triz.a0x_runtime_bundle import _prepare_vertical_runtime_bundle_core

        binding = self._binding()
        capabilities = {
            "guard": 0, "model": 0, "tokenizer": 0, "target": 0,
            "network": 0, "ccp": 0, "docker": 0, "hosted": 0, "readiness": 0,
        }
        request = self._synthetic_gate_b_request(binding)
        prepared = _prepare_vertical_runtime_bundle_core(
            self.root, request, source_state_probe=self._source_state,
            dependencies=self._synthetic_gate_b_dependencies(request, capabilities),
        )
        execution_path = self.root / vertical_execution_authorization_path(binding)
        execution_path.parent.mkdir(parents=True)
        execution_path.write_bytes(canonical_json_bytes(self._synthetic_execution_authorization(binding, prepared)))
        return binding, prepared, capabilities, execution_path

    def _assert_gate_c_refuses_before_guard(self, binding, execution_path) -> None:
        """Mutation matrix boundary: no identity, preflight, or guard capability is spent."""
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, _launch_validated_vertical_v2

        identity = mock.Mock()
        identity.verify.side_effect = AssertionError("executable identity reached")
        preflight = mock.Mock()
        preflight.produce.side_effect = AssertionError("guard preflight reached")
        executor = mock.Mock()
        executor.run.side_effect = AssertionError("guard reached")
        with self.assertRaises(A0XCcpExecutorError):
            _launch_validated_vertical_v2(
                repository_root=self.root, package_binding=binding,
                execution_authorization_path=execution_path.relative_to(self.root).as_posix(),
                source_state_probe=self._source_state, process_executor=executor,
                guard_preflight_producer=preflight, executable_identity_verifier=identity,
            )
        identity.verify.assert_not_called()
        preflight.produce.assert_not_called()
        executor.run.assert_not_called()

    def test_real_git_gate_c_refuses_package_drift_before_guard(self) -> None:
        binding, _prepared, _capabilities, execution_path = self._private_synthetic_chain()
        member = self.root / binding.package_path / "protocol.json"
        member.write_bytes(member.read_bytes() + b" ")
        self._assert_gate_c_refuses_before_guard(binding, execution_path)

    def test_real_git_gate_c_refuses_dossier_drift_before_guard(self) -> None:
        binding, _prepared, _capabilities, execution_path = self._private_synthetic_chain()
        dossier = self.root / binding.dossier_path
        dossier.write_bytes(dossier.read_bytes() + b" ")
        self._assert_gate_c_refuses_before_guard(binding, execution_path)

    def test_real_git_gate_c_refuses_hosted_receipt_drift_before_guard(self) -> None:
        binding, prepared, _capabilities, execution_path = self._private_synthetic_chain()
        (self.root / prepared["verification_receipt_path"]).write_bytes(b"{}")
        self._assert_gate_c_refuses_before_guard(binding, execution_path)

    def test_real_git_gate_c_refuses_every_gate_b_wrapper_drift_before_guard(self) -> None:
        """Every durable Gate-B wrapper is independently rebound before the one-shot guard."""
        for wrapper in ("gate_a_evidence", "readiness", "descriptor", "authorization", "mapping"):
            with self.subTest(wrapper=wrapper):
                binding, prepared, _capabilities, execution_path = self._private_synthetic_chain()
                (self.root / prepared["vertical_outputs"][wrapper]).write_bytes(b"{}")
                self._assert_gate_c_refuses_before_guard(binding, execution_path)
                shutil.rmtree(self.root / ".a0x-runtime", ignore_errors=True)

    def test_real_git_gate_c_refuses_source_tree_drift_after_gate_b(self) -> None:
        """Gate C reopens real Git state after Gate B rather than trusting its former snapshot."""
        binding, _prepared, capabilities, execution_path = self._private_synthetic_chain()
        tracked = self.root / "post-gate-b-source.txt"
        tracked.write_text("new commit\n", encoding="utf-8")
        self._git("add", tracked.name)
        self._git("commit", "-q", "-m", "post Gate-B source drift")
        self._assert_gate_c_refuses_before_guard(binding, execution_path)
        self.assertEqual(1, capabilities["hosted"])
        self.assertEqual(1, capabilities["readiness"])

    def test_real_git_gate_c_refuses_dirty_source_after_gate_b(self) -> None:
        binding, _prepared, capabilities, execution_path = self._private_synthetic_chain()
        (self.root / "post-gate-b-dirty.txt").write_text("dirty\n", encoding="utf-8")
        self._assert_gate_c_refuses_before_guard(binding, execution_path)
        self.assertEqual(1, capabilities["hosted"])
        self.assertEqual(1, capabilities["readiness"])

    def test_real_git_gate_c_refuses_execution_pair_drift_before_guard(self) -> None:
        binding, _prepared, _capabilities, execution_path = self._private_synthetic_chain()
        authorization = json.loads(execution_path.read_text(encoding="utf-8"))
        authorization["pair_binding"]["model_key"] = "wrong-model"
        execution_path.write_bytes(canonical_json_bytes(authorization))
        self._assert_gate_c_refuses_before_guard(binding, execution_path)

    def test_public_gate_c_rejects_synthetic_wrappers_before_execution(self) -> None:
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, launch_vertical_runtime_package

        binding, _prepared, _capabilities, execution_path = self._private_synthetic_chain()
        with self.assertRaises(A0XCcpExecutorError):
            launch_vertical_runtime_package(
                repository_root=self.root, package_binding=binding,
                execution_authorization_path=execution_path.relative_to(self.root).as_posix(),
            )
        self.assertEqual((self.head, self.tree, True), self._source_state())

    def test_real_git_p0_gate_b_and_private_gate_c_synthetic_chain(self) -> None:
        """One committed source proves P0/Gate-B/Gate-C document graph without material capabilities."""
        from latent_triz.a0x_ccp_executor import (
            ProcessResult, _ExecutableIdentityEvidence, _launch_validated_vertical_v2,
            vertical_execution_authorization_path,
        )
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight

        before = self._source_state()
        binding, prepared, capabilities, execution_path = self._private_synthetic_chain()

        class SyntheticIdentity:
            def verify(inner_self, *, role, path, expected_sha256, expected_version=None):
                candidate = Path(path)
                metadata = candidate.lstat()
                if not candidate.is_file() or metadata.st_nlink != 1:
                    raise AssertionError("synthetic identity requires independent regular input")
                return _ExecutableIdentityEvidence(
                    role=role, path=candidate, sha256=expected_sha256,
                    version=expected_version, synthetic=True,
                )

        class InertGuard:
            def run(inner_self, *args, **kwargs):
                capabilities["guard"] += 1
                terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
                return ProcessResult(
                    0, hashlib.sha256(terminal).hexdigest(), len(terminal), "0" * 64, 0,
                    stdout_prefix=terminal,
                )

        guard_version = json.loads((self.root / prepared["vertical_outputs"]["authorization"]).read_text())["payload"]["ccp"]["version"]
        result = _launch_validated_vertical_v2(
            repository_root=self.root, package_binding=binding,
            execution_authorization_path=execution_path.relative_to(self.root).as_posix(),
            source_state_probe=self._source_state, process_executor=InertGuard(),
            guard_preflight_producer=_FakeGuardPreflight(source_head=self.head, version=guard_version),
            executable_identity_verifier=SyntheticIdentity(),
        )
        self.assertEqual("synthetic_completed", result["status"])
        self.assertFalse(result["publication_eligible"])
        self.assertEqual((self.head, self.tree, True), self._source_state())
        self.assertEqual(
            {"guard": 1, "model": 0, "tokenizer": 0, "target": 0, "network": 0, "ccp": 0, "docker": 0},
            {key: capabilities[key] for key in ("guard", "model", "tokenizer", "target", "network", "ccp", "docker")},
        )
        self.assertEqual(1, capabilities["hosted"])
        self.assertEqual(1, capabilities["readiness"])
        self.assertEqual(before, self._source_state())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
