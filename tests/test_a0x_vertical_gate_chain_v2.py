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
import tempfile
import unittest
import inspect
from pathlib import Path
from unittest import mock

from latent_triz.a0x_contract import Leg
from latent_triz.a0x_runtime_bundle import (
    A0XRuntimeBundleError,
    VerticalRuntimePreparationRequest,
    preflight_vertical_runtime_bundle,
)
from latent_triz.a0x_vertical_slice import (
    A0XVerticalSliceError,
    VerticalRuntimePackageRequest,
    generate_vertical_runtime_package,
    load_vertical_runtime_package,
)
from tests.test_a0x_vertical_slice import ROOT, _copy_file, _synthetic_repository


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
        ):
            _copy_file(ROOT, self.root, relative)
        (self.root / ".gitignore").write_text(".a0x-runtime/\n", encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.name", "A0X Target-Free Test")
        self._git("config", "user.email", "a0x@example.invalid")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "real source fixture")
        self.head = self._git_output("rev-parse", "HEAD")
        self.tree = self._git_output("rev-parse", "HEAD^{tree}")

    def tearDown(self) -> None:
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
        mutations = ("member_bytes", "extra_member", "missing_member", "symlink", "hardlink")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                binding = self._binding()
                package = self.root / binding.package_path
                member = package / "protocol.json"
                if mutation == "member_bytes":
                    member.write_bytes(member.read_bytes() + b" ")
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
                self._assert_pre_gate_b_refusal(binding)
                shutil.rmtree(self.root / binding.envelope_path)

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
