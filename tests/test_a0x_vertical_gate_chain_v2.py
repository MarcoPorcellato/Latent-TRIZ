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
import importlib.util
import io
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


def _load_prepare_runtime_module():
    script = ROOT / "scripts/a0x_prepare_runtime.py"
    spec = importlib.util.spec_from_file_location("a0x_prepare_runtime_for_vertical_test", script)
    if spec is None or spec.loader is None:
        raise AssertionError("A0X runtime preparation CLI is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A0XVerticalGateChainV2RealGitTests(unittest.TestCase):
    """P0 v2 must be constructible without changing real Git identity."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        self.root.mkdir()
        _synthetic_repository(self.root)
        for relative in (
            "scripts/a0x_vertical_material_child.py",
            "schemas/a0x-vertical-slice-manifest-v2.schema.json",
            "schemas/a0x-vertical-package-commitment-v2.schema.json",
            "schemas/a0x-gate-b-authorization-v2.schema.json",
            "schemas/a0x-vertical-gate-b-output-v2.schema.json",
            "schemas/a0x-execution-authorization-v4.schema.json",
            "schemas/a0x-vertical-child-terminal-v1.schema.json",
            "schemas/a0x-public-authorization-extension-v1.schema.json",
            "schemas/a0x-public-closure-manifest-v1.schema.json",
            "schemas/a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1.schema.json",
            "src/latent_triz/a0x_public_closure.py",
        ):
            _copy_file(ROOT, self.root, relative)
        source_gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        (self.root / ".gitignore").write_text(
            source_gitignore + "\ngate-b/\nbin/\n__pycache__/\n", encoding="utf-8"
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

    def _write_valid_public_closure(self, binding, prepared, gate_c):
        """Build actual canonical closure bytes from independently read chain files.

        The closure loader, schema validation, hash checks, and parent/child Git
        probes remain production code. Only source documents are synthetic.
        """
        from latent_triz.a0x_public_closure import (
            PRE_EXECUTION_EXTENSION_PATH,
            PRE_EXECUTION_PUBLIC_ROLE_PATHS,
            PRE_EXECUTION_PUBLIC_ROLES,
            pre_execution_closure_relative_path,
        )

        source = {"head": self.head, "tree": self.tree, "ref": "refs/heads/main"}
        pair = binding.pair_binding.as_mapping()
        authorization_id = gate_c["authorization_id"]
        attempt_id = gate_c["attempt_id"]
        identity = {
            "qualified_source": source,
            "pair_binding": pair,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "p0_package_commitment_sha256": binding.package_commitment_sha256,
        }
        private_paths = {
            "p0_dossier_raw": binding.dossier_path,
            "gate_b_authorization_v4": prepared["vertical_outputs"]["authorization"],
            "gate_b_readiness_v4": prepared["vertical_outputs"]["readiness"],
        }
        private_hashes = {
            role: hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
            for role, relative in private_paths.items()
        }
        package_root = self.root / binding.package_path
        roles = {
            "p0_commitment": canonical_json_bytes(json.loads(
                (self.root / binding.commitment_path).read_bytes()
            )),
            "p0_protocol": (package_root / "protocol.json").read_bytes(),
            "p0_implementation": (package_root / "implementation.json").read_bytes(),
            "p0_freeze": (package_root / "freeze.json").read_bytes(),
            "p0_slice_manifest": (package_root / "slice-manifest.json").read_bytes(),
        }
        roles.update({
            "public_dossier": canonical_json_bytes({
                "artifact_class": "a0x-public-dossier-projection",
                "profile": "a0x-public-dossier-projection-v1",
                **{key: identity[key] for key in (
                    "qualified_source", "pair_binding", "authorization_id", "attempt_id",
                )},
                "original_raw_sha256": private_hashes["p0_dossier_raw"],
            }),
            "execution_spec": canonical_json_bytes({
                "artifact_class": "a0x-public-execution-specification",
                "profile": "a0x-public-execution-spec-v1",
                **{key: identity[key] for key in (
                    "qualified_source", "pair_binding", "authorization_id", "attempt_id",
                )},
                "protocol_sha256": hashlib.sha256(roles["p0_protocol"]).hexdigest(),
            }),
            "gate_a_evidence": canonical_json_bytes({
                "artifact_class": "a0x-public-gate-a-evidence",
                "profile": "a0x-public-gate-a-evidence-v1",
                **{key: identity[key] for key in (
                    "qualified_source", "pair_binding", "authorization_id", "attempt_id",
                )},
            }),
            "gate_a_attestation_bundle": b'{"synthetic":true}\n',
            "gate_a_trusted_root": b'{"synthetic":true}\n',
            "gate_a_transport": canonical_json_bytes({"synthetic": True}),
            "gate_b_authorization_projection": canonical_json_bytes({
                "artifact_class": "a0x-public-gate-b-authorization-projection",
                "profile": "a0x-public-gate-b-authorization-projection-v1",
                **{key: identity[key] for key in (
                    "qualified_source", "pair_binding", "authorization_id", "attempt_id",
                )},
                "source_raw_sha256": private_hashes["gate_b_authorization_v4"],
            }),
            "gate_b_readiness_projection": canonical_json_bytes({
                "artifact_class": "a0x-public-gate-b-readiness-projection",
                "profile": "a0x-public-gate-b-readiness-projection-v1",
                **{key: identity[key] for key in (
                    "qualified_source", "pair_binding", "authorization_id", "attempt_id",
                )},
                "source_raw_sha256": private_hashes["gate_b_readiness_v4"],
            }),
        })
        self.assertEqual(set(PRE_EXECUTION_PUBLIC_ROLES), set(roles))
        root = self.root / pre_execution_closure_relative_path(identity)
        for role, relative in PRE_EXECUTION_PUBLIC_ROLE_PATHS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(roles[role])
        extension = {
            "artifact_class": "a0x-public-authorization-extension",
            "profile": "a0x-public-authorization-extension-v1",
            "schema_version": 1,
            **identity,
            "bindings": {
                "public_role_sha256": {
                    role: hashlib.sha256(raw).hexdigest() for role, raw in roles.items()
                },
                "private_input_sha256": private_hashes,
            },
            "claims": {
                "document_bindings_consistent": True,
                "derivation_authenticated": False,
                "operator_approval_authenticated": False,
                "authorization_verified": False,
                "publication_eligible": False,
            },
        }
        extension_path = root / PRE_EXECUTION_EXTENSION_PATH
        extension_path.parent.mkdir(parents=True, exist_ok=True)
        extension_path.write_bytes(canonical_json_bytes(extension))
        self.assertEqual((self.head, self.tree, True), self._source_state())
        return root

    def _prepare_production_context(self, binding, prepared, execution_path):
        """Create a production Gate-C identity without rewriting Gate-B bytes."""
        wrappers = {
            name: json.loads((self.root / path).read_bytes())
            for name, path in prepared["vertical_outputs"].items()
        }
        gate_c = self._synthetic_execution_authorization(binding, prepared)
        gate_c["qualification_context"] = "production"
        execution_path.write_bytes(canonical_json_bytes(gate_c))
        return wrappers, gate_c

    def _production_closure_chain(self):
        binding, prepared, _capabilities, execution_path = self._private_synthetic_chain()
        wrappers, gate_c = self._prepare_production_context(binding, prepared, execution_path)
        p0_commitment = json.loads((self.root / binding.commitment_path).read_bytes())
        gate_b_authorization = json.loads(
            (self.root / prepared["gate_b_authorization_path"]).read_bytes()
        )
        authorization_ids = {
            p0_commitment["authorization_id"],
            gate_b_authorization["authorization_id"],
            gate_c["authorization_id"],
        }
        if len(authorization_ids) != 3 or p0_commitment["attempt_id"] == gate_c["attempt_id"]:
            raise AssertionError("synthetic P0, Gate-B, and Gate-C phase IDs must be distinct")
        closure_root = self._write_valid_public_closure(binding, prepared, gate_c)
        self.assertEqual((self.head, self.tree, True), self._source_state())
        return binding, prepared, execution_path, wrappers, gate_c, closure_root

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

    def test_real_vertical_cli_production_dispatch_has_no_private_callback_typeerror(self) -> None:
        """The actual vertical CLI must call its hardened public entrypoint only."""
        binding = self._binding()
        request = self._synthetic_gate_b_request(binding)
        module = _load_prepare_runtime_module()
        stdout = io.StringIO()
        code = module.main(
            [
                "--vertical-commitment", binding.commitment_path,
                "--gate-b-authorization", str(request.gate_b_authorization),
                "--verifier", str(request.verifier_executable),
                "--verifier-policy", str(request.verifier_policy),
                "--ccp", str(request.ccp_executable),
                "--python", str(request.python_executable),
                "--authorization-id", request.authorization_id,
                "--attempt-id", request.attempt_id,
            ],
            root=self.root,
            stdout=stdout,
        )
        self.assertEqual(2, code)
        self.assertEqual({"status": "refused"}, json.loads(stdout.getvalue()))

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

    def test_real_git_public_closure_is_ignored_but_unrelated_dirt_is_not(self) -> None:
        """Only the canonical runtime closure stays outside the frozen source tree."""
        binding = self._binding()
        closure_member = (
            self.root / "experiments/a0x-six-model/vertical-slices"
            / self.head / "a0/smollm2_360m/public-closure/v1/public/dossier.json"
        )
        closure_member.parent.mkdir(parents=True, exist_ok=True)
        closure_member.write_bytes(b"synthetic closure fixture")
        self.assertEqual(
            "",
            self._git_output("status", "--porcelain=v1", "--untracked-files=all"),
            "the exact canonical closure path must not dirty the qualified checkout",
        )
        unrelated = self.root / "unrelated-untracked.txt"
        unrelated.write_text("not part of the closure\n", encoding="utf-8")
        self.assertNotEqual(
            "",
            self._git_output("status", "--porcelain=v1", "--untracked-files=all"),
            "the narrow ignore rule must not hide unrelated untracked files",
        )

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

    def test_v4_schema_rejects_open_pair_and_guard_launch_shapes(self) -> None:
        """A v4 authorization must close both trust-bearing nested objects."""
        from latent_triz.validator import validate

        binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        authorization = self._synthetic_execution_authorization(binding, prepared)
        schema = json.loads((ROOT / "schemas/a0x-execution-authorization-v4.schema.json").read_bytes())
        self.assertEqual([], validate(authorization, schema))

        open_pair = dict(authorization)
        open_pair["pair_binding"] = {**authorization["pair_binding"], "unexpected": "accepted?"}
        self.assertTrue(validate(open_pair, schema), "v4 pair binding accepted an unknown field")

        open_launch = dict(authorization)
        open_launch["guard_launch"] = {**authorization["guard_launch"], "unexpected": "accepted?"}
        self.assertTrue(validate(open_launch, schema), "v4 guard launch accepted an unknown field")

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

    def test_vertical_gate_b_binds_only_the_fixed_v2_child(self) -> None:
        """The v2 descriptor and its inlet share one internal, non-legacy child binding."""
        binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        descriptor = json.loads((self.root / prepared["vertical_outputs"]["descriptor"]).read_text(encoding="utf-8"))["payload"]
        inlet = json.loads((self.root / prepared["vertical_outputs"]["authorization"]).read_text(encoding="utf-8"))["payload"]
        child = self.root / "scripts/a0x_vertical_material_child.py"
        self.assertTrue(child.is_file())
        self.assertEqual("scripts/a0x_vertical_material_child.py", descriptor["child_script"]["path"])
        self.assertEqual(hashlib.sha256(child.read_bytes()).hexdigest(), descriptor["child_script"]["sha256"])
        self.assertEqual(descriptor["child_script"]["sha256"], inlet["child_sha256"])
        self.assertEqual("gate-b-real-git-auth-01", descriptor["authorization_id"])
        self.assertEqual("gate-b-real-git-attempt-01", descriptor["attempt_id"])

    def test_private_v2_child_revalidates_every_bound_trust_file_before_factory(self) -> None:
        """Replacing a bound graph member after its read must refuse before the inert factory."""
        import contextlib
        import importlib.util

        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_mutation_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)

        for target_kind in (
            "descriptor", "readiness", "gate_a_evidence", "commitment", "dossier", "authorization",
            "execution-authorization", "child",
        ):
            with self.subTest(target_kind=target_kind):
                shutil.rmtree(self.root / ".a0x-runtime", ignore_errors=True)
                binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
                paths = {
                    "descriptor": prepared["vertical_outputs"]["descriptor"],
                    "readiness": prepared["vertical_outputs"]["readiness"],
                    "gate_a_evidence": prepared["vertical_outputs"]["gate_a_evidence"],
                    "commitment": binding.commitment_path,
                    "dossier": binding.dossier_path,
                    "authorization": prepared["vertical_outputs"]["authorization"],
                    "execution-authorization": _execution_path.relative_to(self.root).as_posix(),
                    "child": "scripts/a0x_vertical_material_child.py",
                }
                target = paths[target_kind]
                original_read = child._read_independent
                replaced = False

                def replace_after_read(root, relative):
                    nonlocal replaced
                    raw, identity = original_read(root, relative)
                    if relative == target and not replaced:
                        replaced = True
                        (Path(root) / relative).write_bytes(b"{}")
                    return raw, identity

                calls = []
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(child, "_read_independent", side_effect=replace_after_read))
                    code = child._run_child_core(
                        ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                        root=self.root,
                        source_head_probe=lambda: (self.head, self.tree, True),
                        environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                        cwd=self.root,
                        child_script_path=child_path,
                        qualification_context="synthetic-target-free",
                        inert_factory=lambda graph: calls.append(graph),
                        stdout=io.StringIO(),
                    )
                self.assertTrue(replaced)
                self.assertEqual(2, code)
                self.assertEqual([], calls)
                shutil.rmtree(self.root / ".a0x-runtime", ignore_errors=True)

    def test_private_v2_child_reaches_inert_factory_once_for_the_exact_graph(self) -> None:
        """Only an entirely rebound synthetic graph may cross the private target-free seam."""
        import importlib.util

        binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_valid_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        calls = []
        output = io.StringIO()
        graph = child._validate_graph(
            self.root,
            prepared["vertical_outputs"]["descriptor"],
            source_state_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            expected_context="synthetic-target-free",
        )
        self.assertEqual(binding.pair_binding.as_mapping(), graph["descriptor"]["pair_binding"])
        trust_files = graph["trust_file_identities"]
        self.assertEqual(
            {
                binding.commitment_path,
                binding.dossier_path,
                prepared["vertical_outputs"]["descriptor"],
                prepared["vertical_outputs"]["readiness"],
                prepared["vertical_outputs"]["gate_a_evidence"],
                prepared["vertical_outputs"]["authorization"],
                prepared["vertical_outputs"]["mapping"],
                prepared["gate_b_authorization_path"],
                prepared["verification_receipt_path"],
                "scripts/a0x_vertical_material_child.py",
                "schemas/a0x-execution-authorization-v4.schema.json",
                _execution_path.relative_to(self.root).as_posix(),
            },
            set(trust_files) - {f".a0x-runtime/gate-a/evidence/{self.head}/{name}" for name in (
                "hosted-gate-a-evidence.json", "hosted-gate-a-attestation.bundle.jsonl",
                "github-trusted-root.jsonl", "hosted-gate-a-transport.json")},
        )
        self.assertTrue({f".a0x-runtime/gate-a/evidence/{self.head}/{name}" for name in (
            "hosted-gate-a-evidence.json", "hosted-gate-a-attestation.bundle.jsonl",
            "github-trusted-root.jsonl", "hosted-gate-a-transport.json")} <= set(trust_files))
        with self.assertRaises(TypeError):
            trust_files["injected"] = {}
        with self.assertRaises(TypeError):
            trust_files["scripts/a0x_vertical_material_child.py"]["sha256"] = "0" * 64
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=output,
        )
        self.assertEqual(0, code)
        self.assertEqual(1, len(calls))
        terminal = json.loads(output.getvalue())
        self.assertEqual("a0x-vertical-child-terminal-v1", terminal["terminal_profile"])
        self.assertEqual("completed", terminal["exit_class"])
        self.assertEqual("validated_graph", terminal["reached_frontier"])
        self.assertIsNone(terminal["scientific_outcome"])
        self.assertEqual("synthetic-target-free", terminal["qualification_context"])
        self.assertEqual(binding.pair_binding.as_mapping(), terminal["pair_binding"])
        self.assertEqual(self.head, terminal["qualified_source"]["head"])
        self.assertEqual("gate-c-real-git-auth-01", terminal["authorization_id"])
        self.assertEqual("gate-c-real-git-attempt-01", terminal["attempt_id"])
        self.assertEqual(binding.pair_binding.as_mapping(), calls[0].descriptor["pair_binding"])

    def test_private_v2_child_refuses_semantic_inlet_mutations_before_factory(self) -> None:
        """Canonical inlet bytes must still agree with every descriptor-bound identity."""
        import importlib.util

        for field in ("qualified_source", "gate_a_evidence", "runtime_readiness", "ccp", "python_sha256", "child_sha256"):
            with self.subTest(field=field):
                shutil.rmtree(self.root / ".a0x-runtime", ignore_errors=True)
                _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
                child_path = self.root / "scripts/a0x_vertical_material_child.py"
                spec = importlib.util.spec_from_file_location(f"a0x_vertical_child_semantic_{field}", child_path)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                child = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(child)
                authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
                authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
                payload = authorization["payload"]
                if field == "qualified_source":
                    payload[field] = {"head": "0" * 40, "tree": "1" * 40, "ref": "refs/heads/main"}
                elif field in {"gate_a_evidence", "runtime_readiness"}:
                    payload[field] = {**payload[field], "sha256": "0" * 64}
                elif field == "ccp":
                    payload[field] = {**payload[field], "sha256": "0" * 64}
                else:
                    payload[field] = "0" * 64
                authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
                authorization_path.write_bytes(canonical_json_bytes(authorization))
                calls = []
                code = child._run_child_core(
                    ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                    root=self.root,
                    source_head_probe=lambda: (self.head, self.tree, True),
                    environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                    cwd=self.root,
                    child_script_path=child_path,
                    qualification_context="synthetic-target-free",
                    inert_factory=lambda graph: calls.append(graph),
                    stdout=io.StringIO(),
                )
                self.assertEqual(2, code)
                self.assertEqual([], calls)
                shutil.rmtree(self.root / ".a0x-runtime", ignore_errors=True)

    def test_private_v2_child_refuses_live_tree_or_cleanliness_drift_before_factory(self) -> None:
        """The private factory requires the committed descriptor head, tree, and clean state."""
        import importlib.util

        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_source_state_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        for observed in ((self.head, "0" * 40, True), (self.head, self.tree, False)):
            with self.subTest(observed=observed):
                shutil.rmtree(self.root / ".a0x-runtime", ignore_errors=True)
                _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
                calls = []
                code = child._run_child_core(
                    ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                    root=self.root,
                    source_head_probe=lambda observed=observed: observed,
                    environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                    cwd=self.root,
                    child_script_path=child_path,
                    qualification_context="synthetic-target-free",
                    inert_factory=lambda graph: calls.append(graph),
                    stdout=io.StringIO(),
                )
                self.assertEqual(2, code)
                self.assertEqual([], calls)

    def test_default_source_state_refuses_failed_git_status(self) -> None:
        """A failed cleanliness probe is not interchangeable with an empty clean-status result."""
        import importlib.util

        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_git_status_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        results = [
            subprocess.CompletedProcess(("git", "rev-parse", "HEAD"), 0, stdout=(self.head + "\n").encode("ascii")),
            subprocess.CompletedProcess(("git", "rev-parse", "HEAD^{tree}"), 0, stdout=(self.tree + "\n").encode("ascii")),
            subprocess.CompletedProcess(("git", "status"), 1, stdout=b""),
        ]
        with mock.patch.object(child.subprocess, "run", side_effect=results):
            self.assertEqual(("", "", False), child._default_source_state(self.root))

    def test_private_v2_child_refuses_descriptor_commitment_binding_drift_before_factory(self) -> None:
        """A self-consistent descriptor/inlet cannot substitute the committed P0 package digest."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_commitment_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["payload"]["vertical_package"]["package_commitment_sha256"] = "0" * 64
        descriptor["payload_sha256"] = hashlib.sha256(canonical_json_bytes(descriptor["payload"])).hexdigest()
        descriptor_path.write_bytes(canonical_json_bytes(descriptor))
        authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["payload"]["vertical_package"]["package_commitment_sha256"] = "0" * 64
        authorization["payload"]["descriptor"]["sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
        authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(authorization["payload"])).hexdigest()
        authorization_path.write_bytes(canonical_json_bytes(authorization))
        calls = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_refuses_semantically_invalid_gate_a_payload_before_factory(self) -> None:
        """A coherent wrapper-hash rewrite cannot replace the validated hosted-evidence payload."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_gate_a_semantics_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)

        evidence_path = self.root / prepared["vertical_outputs"]["gate_a_evidence"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["payload"]["repository"] = "Wrong/Repository"
        evidence["payload_sha256"] = hashlib.sha256(canonical_json_bytes(evidence["payload"])).hexdigest()
        evidence_path.write_bytes(canonical_json_bytes(evidence))

        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["payload"]["gate_a_evidence"]["sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        descriptor["payload_sha256"] = hashlib.sha256(canonical_json_bytes(descriptor["payload"])).hexdigest()
        descriptor_path.write_bytes(canonical_json_bytes(descriptor))

        authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["payload"]["gate_a_evidence"]["sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        authorization["payload"]["descriptor"]["sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
        authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(authorization["payload"])).hexdigest()
        authorization_path.write_bytes(canonical_json_bytes(authorization))

        calls = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_refuses_noncanonical_gate_a_reference_before_factory(self) -> None:
        """A valid output copied to an arbitrary root-relative path is not a derived v2 dependency."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_gate_a_path_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)

        evidence_path = self.root / prepared["vertical_outputs"]["gate_a_evidence"]
        alternate_relative = prepared["vertical_outputs"]["gate_a_evidence"].replace(
            "gate-a-evidence.json", "alternate-gate-a-evidence.json",
        )
        alternate_path = self.root / alternate_relative
        alternate_path.write_bytes(evidence_path.read_bytes())

        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["payload"]["gate_a_evidence"] = {
            "role": "gate_a_evidence", "path": alternate_relative,
            "sha256": hashlib.sha256(alternate_path.read_bytes()).hexdigest(),
        }
        descriptor["payload_sha256"] = hashlib.sha256(canonical_json_bytes(descriptor["payload"])).hexdigest()
        descriptor_path.write_bytes(canonical_json_bytes(descriptor))

        authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["payload"]["gate_a_evidence"] = dict(descriptor["payload"]["gate_a_evidence"])
        authorization["payload"]["descriptor"]["sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
        authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(authorization["payload"])).hexdigest()
        authorization_path.write_bytes(canonical_json_bytes(authorization))

        calls = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_refuses_same_inode_same_size_trust_rewrite_before_factory(self) -> None:
        """Final revalidation must hash bytes, not merely compare an inode and its size."""
        import contextlib
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_same_size_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        target = prepared["vertical_outputs"]["descriptor"]
        original_read = child._read_independent
        rewritten = False

        def same_size_rewrite(root, relative):
            nonlocal rewritten
            raw, identity = original_read(root, relative)
            if relative == target and not rewritten:
                rewritten = True
                (Path(root) / relative).write_bytes(b" " * len(raw))
            return raw, identity

        calls = []
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(child, "_read_independent", side_effect=same_size_rewrite))
            code = child._run_child_core(
                ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                root=self.root,
                source_head_probe=lambda: (self.head, self.tree, True),
                environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                cwd=self.root,
                child_script_path=child_path,
                qualification_context="synthetic-target-free",
                inert_factory=lambda graph: calls.append(graph),
                stdout=io.StringIO(),
            )
        self.assertTrue(rewritten)
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_binds_gate_b_authorization_identity_to_raw_authority(self) -> None:
        """Descriptor/inlet agreement alone cannot substitute the raw Gate-B authorization ID."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_gate_b_id_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["payload"]["authorization_id"] = "substituted-gate-b-auth"
        descriptor["payload_sha256"] = hashlib.sha256(canonical_json_bytes(descriptor["payload"])).hexdigest()
        descriptor_path.write_bytes(canonical_json_bytes(descriptor))
        authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["payload"]["authorization_id"] = "substituted-gate-b-auth"
        authorization["payload"]["descriptor"]["sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
        authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(authorization["payload"])).hexdigest()
        authorization_path.write_bytes(canonical_json_bytes(authorization))
        calls = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_refuses_descriptor_wrapper_context_drift_before_factory(self) -> None:
        """The descriptor wrapper context is a bound capability boundary, not a cosmetic field."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_context_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["qualification_context"] = "production"
        descriptor_path.write_bytes(canonical_json_bytes(descriptor))
        authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["payload"]["descriptor"]["sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
        authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(authorization["payload"])).hexdigest()
        authorization_path.write_bytes(canonical_json_bytes(authorization))
        calls = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_refuses_descriptor_wrapper_package_drift_before_factory(self) -> None:
        """A coherently rehashed wrapper cannot replace its validated vertical-package identity."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_wrapper_package_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        descriptor["vertical_package"] = {}
        descriptor_path.write_bytes(canonical_json_bytes(descriptor))
        authorization_path = self.root / prepared["vertical_outputs"]["authorization"]
        authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
        authorization["payload"]["descriptor"]["sha256"] = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()
        authorization["payload_sha256"] = hashlib.sha256(canonical_json_bytes(authorization["payload"])).hexdigest()
        authorization_path.write_bytes(canonical_json_bytes(authorization))
        calls = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: calls.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(2, code)
        self.assertEqual([], calls)

    def test_private_v2_child_refuses_fifo_within_bounded_subprocess(self) -> None:
        """A nonregular trust leaf must refuse; it must never wait for a FIFO writer."""
        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        readiness = self.root / prepared["vertical_outputs"]["readiness"]
        readiness.unlink()
        os.mkfifo(readiness)
        runner = (
            "import importlib.util,sys;from pathlib import Path;"
            "root=Path(sys.argv[1]);path=root/'scripts/a0x_vertical_material_child.py';"
            "spec=importlib.util.spec_from_file_location('vertical_fifo_runner',path);"
            "child=importlib.util.module_from_spec(spec);spec.loader.exec_module(child);"
            "env={item.split('=',1)[0]:item.split('=',1)[1] for item in child._ENVIRONMENT};"
            "raise SystemExit(child._run_child_core(['--launch-descriptor',sys.argv[2]],root=root,source_head_probe=None,environment=env,cwd=root,child_script_path=path,qualification_context='synthetic-target-free',inert_factory=lambda _graph:None,stdout=sys.stdout))"
        )
        completed = subprocess.run(
            (sys.executable, "-c", runner, str(self.root), prepared["vertical_outputs"]["descriptor"]),
            cwd=self.root, check=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5,
        )
        self.assertEqual(2, completed.returncode)
        self.assertEqual(
            '{"artifact_class":"a0x-vertical-material-child-terminal","exit_class":"refused","terminal_profile":"a0x-vertical-child-terminal-v1"}\n',
            completed.stdout,
        )

    def test_private_v2_child_returns_a_deeply_immutable_graph(self) -> None:
        """A private factory receives immutable snapshots, not mutable nested live dictionaries."""
        import importlib.util

        _binding, prepared, _capabilities, _execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_immutable_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        captured = []
        code = child._run_child_core(
            ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
            root=self.root,
            source_head_probe=lambda: (self.head, self.tree, True),
            environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
            cwd=self.root,
            child_script_path=child_path,
            qualification_context="synthetic-target-free",
            inert_factory=lambda graph: captured.append(graph),
            stdout=io.StringIO(),
        )
        self.assertEqual(0, code)
        self.assertIsInstance(captured[0].descriptor["environment_template"], tuple)
        with self.assertRaises(TypeError):
            captured[0].descriptor["child_script"]["path"] = "wrong"

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

    def test_production_parent_refuses_missing_public_closure_before_claim_or_guard(self) -> None:
        """The production parent checks closure before identity, claim, preflight, or execution."""
        import latent_triz.a0x_ccp_executor as executor_module
        import latent_triz.a0x_public_closure as public_closure
        import latent_triz.a0x_runtime_bundle as runtime_bundle
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, _launch_validated_vertical_v2

        binding, prepared, _capabilities, execution_path = self._private_synthetic_chain()
        authorization = self._synthetic_execution_authorization(binding, prepared)
        authorization["qualification_context"] = "production"
        execution_path.write_bytes(canonical_json_bytes(authorization))
        output_documents = {
            name: json.loads((self.root / path).read_bytes())
            for name, path in prepared["vertical_outputs"].items()
        }
        real_output_validator = runtime_bundle.validate_vertical_runtime_output

        def production_context_output(root, relative, package_binding, *, expected_qualification_context=None):
            value = real_output_validator(
                root, relative, package_binding,
                expected_qualification_context="synthetic-target-free",
            )
            value["qualification_context"] = "production"
            return value

        identity = mock.Mock()
        identity.verify.side_effect = AssertionError("executable identity reached before closure")
        preflight = mock.Mock()
        preflight.produce.side_effect = AssertionError("guard preflight reached before closure")
        executor = mock.Mock()
        executor.run.side_effect = AssertionError("guard reached before closure")
        closure_calls = []
        real_closure_loader = executor_module.load_pre_execution_public_closure

        def observe_closure(*args, **kwargs):
            closure_calls.append((args, kwargs))
            return real_closure_loader(*args, **kwargs)

        with (
            mock.patch.object(runtime_bundle, "validate_vertical_runtime_output", side_effect=production_context_output),
            mock.patch.object(
                executor_module, "_vertical_gate_a_evidence_from_raw",
                return_value=output_documents["gate_a_evidence"]["payload"],
            ),
            mock.patch.object(executor_module, "load_pre_execution_public_closure", side_effect=observe_closure),
        ):
            with self.assertRaises(A0XCcpExecutorError) as raised:
                _launch_validated_vertical_v2(
                    repository_root=self.root, package_binding=binding,
                    execution_authorization_path=execution_path.relative_to(self.root).as_posix(),
                    source_state_probe=self._source_state, process_executor=executor,
                    guard_preflight_producer=preflight, executable_identity_verifier=identity,
                    expected_qualification_context="production",
                )
        identity.verify.assert_not_called()
        preflight.produce.assert_not_called()
        executor.run.assert_not_called()
        self.assertIn("public pre-execution closure is invalid", str(raised.exception))
        self.assertEqual(1, len(closure_calls))
        self.assertFalse(execution_path.with_name("attempt-claim.json").exists())

    def test_production_child_refuses_incomplete_ignored_closure_before_bind_or_dispatch(self) -> None:
        """An ignored canonical path is still content-validated before graph binding."""
        import importlib.util
        from latent_triz.a0x_public_closure import pre_execution_closure_relative_path

        binding, prepared, _capabilities, execution_path = self._private_synthetic_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_production_closure_test", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)

        wrappers = {
            name: json.loads((self.root / path).read_bytes())
            for name, path in prepared["vertical_outputs"].items()
        }
        for name, document in wrappers.items():
            document["qualification_context"] = "production"
            (self.root / prepared["vertical_outputs"][name]).write_bytes(canonical_json_bytes(document))

        readiness_hash = hashlib.sha256(
            (self.root / prepared["vertical_outputs"]["readiness"]).read_bytes()
        ).hexdigest()
        evidence_hash = hashlib.sha256(
            (self.root / prepared["vertical_outputs"]["gate_a_evidence"]).read_bytes()
        ).hexdigest()
        descriptor_path = self.root / prepared["vertical_outputs"]["descriptor"]
        descriptor_document = json.loads(descriptor_path.read_bytes())
        descriptor = descriptor_document["payload"]
        descriptor["runtime_readiness"]["sha256"] = readiness_hash
        descriptor["gate_a_evidence"]["sha256"] = evidence_hash
        descriptor_document["payload_sha256"] = hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest()
        descriptor_path.write_bytes(canonical_json_bytes(descriptor_document))
        descriptor_hash = hashlib.sha256(descriptor_path.read_bytes()).hexdigest()

        inlet_path = self.root / prepared["vertical_outputs"]["authorization"]
        inlet_document = json.loads(inlet_path.read_bytes())
        inlet = inlet_document["payload"]
        inlet["runtime_readiness"]["sha256"] = readiness_hash
        inlet["gate_a_evidence"]["sha256"] = evidence_hash
        inlet["descriptor"]["sha256"] = descriptor_hash
        inlet_document["payload_sha256"] = hashlib.sha256(canonical_json_bytes(inlet)).hexdigest()
        inlet_path.write_bytes(canonical_json_bytes(inlet_document))

        gate_c = self._synthetic_execution_authorization(binding, prepared)
        gate_c["qualification_context"] = "production"
        execution_path.write_bytes(canonical_json_bytes(gate_c))
        closure_root = self.root / pre_execution_closure_relative_path({
            "qualified_source": gate_c["qualified_source"],
            "pair_binding": gate_c["pair_binding"],
            "authorization_id": gate_c["authorization_id"],
            "attempt_id": gate_c["attempt_id"],
            "p0_package_commitment_sha256": binding.package_commitment_sha256,
        })
        only_projection = closure_root / "public/dossier.json"
        only_projection.parent.mkdir(parents=True, exist_ok=True)
        only_projection.write_bytes(b"synthetic incomplete closure")
        self.assertEqual("", self._git_output("status", "--porcelain=v1", "--untracked-files=all"))

        evidence_payload = wrappers["gate_a_evidence"]["payload"]
        calls = []
        closure_calls = []
        real_closure_loader = child.load_pre_execution_public_closure

        def observe_closure(*args, **kwargs):
            closure_calls.append((args, kwargs))
            return real_closure_loader(*args, **kwargs)

        def production_gate_c(*_args, **_kwargs):
            return gate_c, ()

        with (
            mock.patch.object(child, "_validate_inlet"),
            mock.patch.object(child, "_read_gate_c_authorization", side_effect=production_gate_c),
            mock.patch.object(child, "_vertical_gate_a_evidence_from_raw", return_value=evidence_payload),
            mock.patch.object(child, "load_pre_execution_public_closure", side_effect=observe_closure),
            mock.patch.object(child, "bind_validated_vertical_graph") as bind_graph,
        ):
            code = child._run_child_core(
                ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                root=self.root,
                source_head_probe=lambda: (self.head, self.tree, True),
                environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                cwd=self.root,
                child_script_path=child_path,
                qualification_context="production",
                inert_factory=lambda graph: calls.append(graph),
                stdout=io.StringIO(),
            )
        self.assertEqual(2, code)
        self.assertEqual([], calls)
        self.assertEqual(1, len(closure_calls))
        bind_graph.assert_not_called()

    def test_production_parent_valid_closure_reaches_identity_sentinel_before_claim_or_guard(self) -> None:
        """Real closure validation accepts distinct P0/B/C IDs before later capabilities."""
        import latent_triz.a0x_ccp_executor as executor_module
        import latent_triz.a0x_runtime_bundle as runtime_bundle
        from latent_triz.a0x_ccp_executor import _launch_validated_vertical_v2

        binding, prepared, execution_path, wrappers, gate_c, _closure_root = self._production_closure_chain()

        class ReachedIdentity(RuntimeError):
            pass

        class IdentitySentinel:
            calls = 0

            def verify(inner_self, **_kwargs):
                inner_self.calls += 1
                raise ReachedIdentity("valid public closure reached next identity boundary")

        identity = IdentitySentinel()
        preflight = mock.Mock(side_effect=AssertionError("preflight must remain after sentinel"))
        executor = mock.Mock(side_effect=AssertionError("guard must remain after sentinel"))
        closure_results = []
        real_closure_loader = executor_module.load_pre_execution_public_closure

        def observe_closure(*args, **kwargs):
            result = real_closure_loader(*args, **kwargs)
            closure_results.append(result)
            return result

        real_output_validator = runtime_bundle.validate_vertical_runtime_output

        def production_context_output(root, relative, package_binding, *, expected_qualification_context=None):
            value = real_output_validator(
                root, relative, package_binding,
                expected_qualification_context="synthetic-target-free",
            )
            value["qualification_context"] = "production"
            return value

        before = self._source_state()
        with (
            # The graph wrappers were created in the synthetic Gate-B lane.
            # Validate their actual bytes and dependencies, then adapt only the
            # outer context label to exercise the later production parent path.
            mock.patch.object(runtime_bundle, "validate_vertical_runtime_output", side_effect=production_context_output),
            # Hosted evidence is fixture-generated, so reconstructing its real
            # signature chain is outside this closure-boundary test.
            mock.patch.object(
                executor_module, "_vertical_gate_a_evidence_from_raw",
                return_value=wrappers["gate_a_evidence"]["payload"],
            ),
            mock.patch.object(executor_module, "load_pre_execution_public_closure", side_effect=observe_closure),
        ):
            with self.assertRaises(ReachedIdentity):
                _launch_validated_vertical_v2(
                    repository_root=self.root, package_binding=binding,
                    execution_authorization_path=execution_path.relative_to(self.root).as_posix(),
                    source_state_probe=self._source_state, process_executor=executor,
                    guard_preflight_producer=preflight, executable_identity_verifier=identity,
                    expected_qualification_context="production",
                )

        self.assertEqual(1, len(closure_results))
        self.assertTrue(closure_results[0].document_bindings_consistent)
        self.assertEqual(13, closure_results[0].public_role_count)
        self.assertFalse(closure_results[0].operator_approval_authenticated)
        self.assertEqual(1, identity.calls)
        preflight.assert_not_called()
        executor.assert_not_called()
        self.assertFalse(execution_path.with_name("attempt-claim.json").exists())
        self.assertEqual(before, self._source_state())
        self.assertEqual((self.head, self.tree, True), before)
        self.assertEqual("gate-c-real-git-auth-01", gate_c["authorization_id"])
        self.assertEqual(
            "p0-real-git-auth-01",
            json.loads((self.root / binding.commitment_path).read_bytes())["authorization_id"],
        )
        self.assertEqual(
            "gate-b-real-git-auth-01",
            json.loads((self.root / prepared["gate_b_authorization_path"]).read_bytes())["authorization_id"],
        )

    def test_production_parent_rejects_corrupted_valid_closure_before_identity_sentinel(self) -> None:
        """A semantic member mutation with its public role hash rebound still refuses."""
        import latent_triz.a0x_ccp_executor as executor_module
        import latent_triz.a0x_runtime_bundle as runtime_bundle
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, _launch_validated_vertical_v2
        from latent_triz.a0x_public_closure import PRE_EXECUTION_EXTENSION_PATH, PRE_EXECUTION_PUBLIC_ROLE_PATHS

        binding, prepared, execution_path, wrappers, _gate_c, closure_root = self._production_closure_chain()
        member = closure_root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["execution_spec"]
        document = json.loads(member.read_bytes())
        document["protocol_sha256"] = "0" * 64
        member_raw = canonical_json_bytes(document)
        member.write_bytes(member_raw)
        extension_path = closure_root / PRE_EXECUTION_EXTENSION_PATH
        extension = json.loads(extension_path.read_bytes())
        extension["bindings"]["public_role_sha256"]["execution_spec"] = hashlib.sha256(member_raw).hexdigest()
        extension_path.write_bytes(canonical_json_bytes(extension))
        self.assertEqual((self.head, self.tree, True), self._source_state())

        identity = mock.Mock()
        identity.verify.side_effect = AssertionError("corrupt closure must refuse before identity")
        preflight = mock.Mock(side_effect=AssertionError("preflight must remain after closure"))
        executor = mock.Mock(side_effect=AssertionError("guard must remain after closure"))
        closure_calls = []
        real_closure_loader = executor_module.load_pre_execution_public_closure

        def observe_closure(*args, **kwargs):
            closure_calls.append(True)
            return real_closure_loader(*args, **kwargs)

        real_output_validator = runtime_bundle.validate_vertical_runtime_output

        def production_context_output(root, relative, package_binding, *, expected_qualification_context=None):
            value = real_output_validator(
                root, relative, package_binding,
                expected_qualification_context="synthetic-target-free",
            )
            value["qualification_context"] = "production"
            return value

        with (
            mock.patch.object(runtime_bundle, "validate_vertical_runtime_output", side_effect=production_context_output),
            mock.patch.object(
                executor_module, "_vertical_gate_a_evidence_from_raw",
                return_value=wrappers["gate_a_evidence"]["payload"],
            ),
            mock.patch.object(executor_module, "load_pre_execution_public_closure", side_effect=observe_closure),
        ):
            with self.assertRaises(A0XCcpExecutorError) as raised:
                _launch_validated_vertical_v2(
                    repository_root=self.root, package_binding=binding,
                    execution_authorization_path=execution_path.relative_to(self.root).as_posix(),
                    source_state_probe=self._source_state, process_executor=executor,
                    guard_preflight_producer=preflight, executable_identity_verifier=identity,
                    expected_qualification_context="production",
                )
        self.assertIn("public pre-execution closure is invalid", str(raised.exception))
        self.assertEqual([True], closure_calls)
        identity.verify.assert_not_called()
        preflight.assert_not_called()
        executor.assert_not_called()
        self.assertFalse(execution_path.with_name("attempt-claim.json").exists())
        self.assertEqual((self.head, self.tree, True), self._source_state())

    def test_production_child_valid_closure_reaches_post_bind_sentinel_before_dispatch(self) -> None:
        """The real child loader and binder accept a fully canonical synthetic closure."""
        import importlib.util
        binding, prepared, execution_path, wrappers, gate_c, _closure_root = self._production_closure_chain()
        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_production_positive", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        closure_results = []
        bound_graphs = []
        factory_calls = []
        real_loader = child.load_pre_execution_public_closure
        real_binder = child.bind_validated_vertical_graph

        class ReachedDispatch(RuntimeError):
            pass

        def observe_loader(*args, **kwargs):
            result = real_loader(*args, **kwargs)
            closure_results.append(result)
            return result

        def bind_then_stop(graph, *, qualification_context):
            bound = real_binder(graph, qualification_context=qualification_context)
            bound_graphs.append(bound)
            raise ReachedDispatch("valid production graph reached post-bind stop boundary")

        def production_gate_c(*_args, **_kwargs):
            return gate_c, ()

        real_canonical_output = child._canonical_output

        def production_context_output(raw, label):
            value = real_canonical_output(raw, label)
            if value.get("qualification_context") == "synthetic-target-free":
                value["qualification_context"] = "production"
            return value

        before = self._source_state()
        output = io.StringIO()
        with (
            # Production expects production outer labels. Translate only the
            # synthetic Gate-B wrapper context after canonical-byte parsing;
            # closure loading and its independent hash checks remain real.
            mock.patch.object(child, "_canonical_output", side_effect=production_context_output),
            # These bypass synthetic upstream auth/attestation reconstruction,
            # not the public closure loader, Git probe, or graph binder.
            mock.patch.object(child, "_validate_inlet"),
            mock.patch.object(child, "_read_gate_c_authorization", side_effect=production_gate_c),
            mock.patch.object(
                child, "_vertical_gate_a_evidence_from_raw",
                return_value=wrappers["gate_a_evidence"]["payload"],
            ),
            mock.patch.object(child, "load_pre_execution_public_closure", side_effect=observe_loader),
            mock.patch.object(child, "bind_validated_vertical_graph", side_effect=bind_then_stop),
        ):
            try:
                child._run_child_core(
                    ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                    root=self.root, source_head_probe=self._source_state,
                    environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                    cwd=self.root, child_script_path=child_path,
                    qualification_context="production",
                    inert_factory=lambda graph: factory_calls.append(graph),
                    stdout=output,
                )
            except ReachedDispatch:
                pass
            else:
                self.fail(f"valid closure did not reach post-bind sentinel: {output.getvalue()}")

        self.assertEqual(2, len(closure_results))
        self.assertEqual(closure_results[0], closure_results[1])
        self.assertTrue(closure_results[0].document_bindings_consistent)
        self.assertEqual(13, closure_results[0].public_role_count)
        self.assertEqual(1, len(bound_graphs))
        self.assertEqual("production", bound_graphs[0].qualification_context)
        self.assertEqual([], factory_calls)
        self.assertEqual(before, self._source_state())
        self.assertEqual((self.head, self.tree, True), before)
        self.assertEqual("gate-c-real-git-auth-01", gate_c["authorization_id"])

    def test_production_child_rejects_corrupted_valid_closure_before_bind_or_dispatch(self) -> None:
        """A semantically corrupted closure member cannot reach the real graph binder."""
        import importlib.util
        from latent_triz.a0x_public_closure import PRE_EXECUTION_EXTENSION_PATH, PRE_EXECUTION_PUBLIC_ROLE_PATHS

        binding, prepared, _execution_path, wrappers, gate_c, closure_root = self._production_closure_chain()
        member = closure_root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["execution_spec"]
        document = json.loads(member.read_bytes())
        document["protocol_sha256"] = "0" * 64
        member_raw = canonical_json_bytes(document)
        member.write_bytes(member_raw)
        extension_path = closure_root / PRE_EXECUTION_EXTENSION_PATH
        extension = json.loads(extension_path.read_bytes())
        extension["bindings"]["public_role_sha256"]["execution_spec"] = hashlib.sha256(member_raw).hexdigest()
        extension_path.write_bytes(canonical_json_bytes(extension))
        self.assertEqual((self.head, self.tree, True), self._source_state())

        child_path = self.root / "scripts/a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("a0x_vertical_child_production_corrupt", child_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)
        loader_calls = []
        real_loader = child.load_pre_execution_public_closure

        def observe_loader(*args, **kwargs):
            loader_calls.append(True)
            return real_loader(*args, **kwargs)

        def production_gate_c(*_args, **_kwargs):
            return gate_c, ()

        real_canonical_output = child._canonical_output

        def production_context_output(raw, label):
            value = real_canonical_output(raw, label)
            if value.get("qualification_context") == "synthetic-target-free":
                value["qualification_context"] = "production"
            return value

        factory_calls = []
        with (
            mock.patch.object(child, "_canonical_output", side_effect=production_context_output),
            mock.patch.object(child, "_validate_inlet"),
            mock.patch.object(child, "_read_gate_c_authorization", side_effect=production_gate_c),
            mock.patch.object(
                child, "_vertical_gate_a_evidence_from_raw",
                return_value=wrappers["gate_a_evidence"]["payload"],
            ),
            mock.patch.object(child, "load_pre_execution_public_closure", side_effect=observe_loader),
            mock.patch.object(child, "bind_validated_vertical_graph") as bind_graph,
        ):
            code = child._run_child_core(
                ["--launch-descriptor", prepared["vertical_outputs"]["descriptor"]],
                root=self.root, source_head_probe=self._source_state,
                environment={item.split("=", 1)[0]: item.split("=", 1)[1] for item in child._ENVIRONMENT},
                cwd=self.root, child_script_path=child_path,
                qualification_context="production",
                inert_factory=lambda graph: factory_calls.append(graph), stdout=io.StringIO(),
            )
        self.assertEqual(2, code)
        self.assertEqual([True], loader_calls)
        bind_graph.assert_not_called()
        self.assertEqual([], factory_calls)
        self.assertEqual((self.head, self.tree, True), self._source_state())

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
            def run(inner_self, argv, *, cwd, env, timeout_seconds, capture_limit_bytes):
                import contextlib
                import importlib.util
                import io

                capabilities["guard"] += 1
                child_path = self.root / "scripts/a0x_vertical_material_child.py"
                spec = importlib.util.spec_from_file_location("a0x_vertical_child_e2e", child_path)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                child = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(child)
                delimiter = argv.index("--")
                descriptor_argv = argv[delimiter + 3:]
                terminal_stream = io.StringIO()
                error_stream = io.StringIO()
                with contextlib.redirect_stderr(error_stream):
                    child_exit = child._run_child_core(
                        descriptor_argv, root=cwd, source_head_probe=self._source_state,
                        environment=env, cwd=cwd, child_script_path=child_path,
                        qualification_context="synthetic-target-free",
                        inert_factory=lambda graph: capabilities.update(child_graph=graph),
                        stdout=terminal_stream,
                    )
                self.assertEqual(0, child_exit, error_stream.getvalue() + terminal_stream.getvalue())
                terminal = terminal_stream.getvalue().encode("utf-8")
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
