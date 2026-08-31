"""Synthetic, offline contract tests for Hosted Gate A verifier."""

from __future__ import annotations

import unittest
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from latent_triz.a0x_hosted_gate_a import LANE_COMMANDS, build_lane_receipt, build_manifest, canonical_json_bytes


class HostedVerifierContractTest(unittest.TestCase):
    def test_public_verifier_interface_is_available(self) -> None:
        """Removing offline Gate B verifier must reject every hosted dossier."""
        from latent_triz.a0x_hosted_verifier import GateBVerificationRequest, verify_hosted_gate_a

        self.assertTrue(callable(verify_hosted_gate_a))
        self.assertTrue(GateBVerificationRequest)

    def test_timestamp_accepts_only_utc_rfc3339_z_with_stable_refusal(self) -> None:
        """Clock and transport parsing never leak a TypeError or local offset."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, _parse_timestamp

        self.assertEqual(_parse_timestamp("2026-08-31T12:04:00Z").tzinfo.utcoffset(None).total_seconds(), 0)
        for value in (None, 3, "2026-08-31T12:04:00+00:00", "2026-08-31 12:04:00Z", "not-a-time"):
            with self.subTest(value=value), self.assertRaises(A0XHostedVerifierError) as raised:
                _parse_timestamp(value)
            self.assertEqual(raised.exception.code, "A0X_GATE_B_INPUT_INVALID")

    def test_signed_fixture_verifies_one_exact_manifest(self) -> None:
        """Changing any signed binding must make offline Gate B refuse it."""
        from latent_triz.a0x_hosted_verifier import validate_verification_result

        fixture = Path(__file__).parent / "fixtures/a0x/hosted-gate-a/positive/gh-2.97.0-verification-result.json"
        result = fixture.read_bytes()
        self.assertEqual(
            validate_verification_result(
                result,
                manifest_sha256="1" * 64,
                job_workflow_sha="a" * 40, source_sha="a" * 40,
                repository="MarcoPorcellato/Latent-TRIZ",
                signer_workflow="MarcoPorcellato/Latent-TRIZ/.github/workflows/a0x-hosted-gate-a.yml",
                predicate_type="https://slsa.dev/provenance/v1",
                cert_oidc_issuer="https://token.actions.githubusercontent.com",
                required_ref="refs/heads/main",
                run_id=2002, run_attempt=1,
            )["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"],
            "1" * 64,
        )

    def test_verifier_writes_one_receipt_after_one_bound_runner_call(self) -> None:
        """Missing any preflight must prevent the one authenticated runner call."""
        from latent_triz.a0x_hosted_verifier import GateBVerificationRequest, verify_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            authorization_path, policy_path, manifest_path, bundle_path, trusted_root_path, transport_path = self._packet(root)
            calls: list[tuple[tuple[str, ...], Path]] = []
            manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            result = json.loads(self._result_fixture().decode("utf-8"))
            result[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = manifest_sha256

            def runner(argv: tuple[str, ...], cwd: Path) -> tuple[int, bytes, bytes]:
                calls.append((argv, cwd))
                return 0, json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8"), b""

            raw = verify_hosted_gate_a(
                GateBVerificationRequest(root, authorization_path, Path("/opt/homebrew/bin/gh").resolve(), policy_path),
                runner=runner,
                source_state_probe=lambda _root: ("a" * 40, "b" * 40, True),
                clock=lambda: "2026-08-31T12:04:00Z",
            )
            receipt = json.loads(raw)
            self.assertEqual(receipt["verification_status"], "verified")
            self.assertTrue(raw.endswith(b"\n"))
            self.assertEqual(len(calls), 1)
            argv, cwd = calls[0]
            self.assertEqual(cwd, root.resolve())
            self.assertEqual(argv[0], str(Path("/opt/homebrew/bin/gh").resolve()))
            self.assertIn("--signer-digest", argv)
            self.assertEqual(argv[argv.index("--signer-digest") + 1], "a" * 40)
            self.assertIn("--source-digest", argv)
            self.assertEqual(argv[argv.index("--source-digest") + 1], "a" * 40)
            output = root / ".a0x-runtime/gate-b-verifications/" / ("a" * 40) / "a0/gpt2/a0x-a0-gpt2-run-1/gate-a-verification-receipt.json"
            self.assertEqual(output.read_bytes(), raw)

    def test_signed_result_mutation_matrix_refuses_exact_contract_drift(self) -> None:
        """Every altered signed claim or output-shape field must be refused."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, validate_verification_result

        baseline = json.loads(self._result_fixture())
        mutations = {
            "wrong_subject": lambda value: value[0]["verificationResult"]["statement"]["subject"][0]["digest"].__setitem__("sha256", "2" * 64),
            "wrong_signer": lambda value: value[0]["verificationResult"]["signature"]["certificate"].__setitem__("buildSignerDigest", "b" * 40),
            "wrong_source": lambda value: value[0]["verificationResult"]["signature"]["certificate"].__setitem__("sourceRepositoryDigest", "b" * 40),
            "wrong_issuer": lambda value: value[0]["verificationResult"]["signature"]["certificate"].__setitem__("issuer", "https://wrong.invalid"),
            "wrong_builder": lambda value: value[0]["verificationResult"]["statement"]["predicate"]["runDetails"]["builder"].__setitem__("id", "https://wrong.invalid"),
            "permissive_san_matcher": lambda value: value[0]["verificationResult"]["verifiedIdentity"]["subjectAlternativeName"].__setitem__("regexp", ".*"),
            "wrong_predicate": lambda value: value[0]["verificationResult"]["statement"].__setitem__("predicateType", "https://wrong.invalid"),
            "missing_timestamp": lambda value: value[0]["verificationResult"].__setitem__("verifiedTimestamps", []),
            "extra_field": lambda value: value[0].__setitem__("extra", True),
            "two_results": lambda value: value.append(json.loads(self._result_fixture())[0]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                value = json.loads(json.dumps(baseline))
                mutate(value)
                with self.assertRaises(A0XHostedVerifierError):
                    validate_verification_result(
                        json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
                        manifest_sha256="1" * 64, job_workflow_sha="a" * 40, source_sha="a" * 40,
                        repository="MarcoPorcellato/Latent-TRIZ",
                        signer_workflow="MarcoPorcellato/Latent-TRIZ/.github/workflows/a0x-hosted-gate-a.yml",
                        predicate_type="https://slsa.dev/provenance/v1",
                        cert_oidc_issuer="https://token.actions.githubusercontent.com", required_ref="refs/heads/main",
                        run_id=2002, run_attempt=1,
                    )

    def test_signer_and_source_revisions_are_independent_bindings(self) -> None:
        """A valid-looking signer/source revision cannot substitute for the other."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, validate_verification_result

        kwargs = dict(
            manifest_sha256="1" * 64, repository="MarcoPorcellato/Latent-TRIZ",
            signer_workflow="MarcoPorcellato/Latent-TRIZ/.github/workflows/a0x-hosted-gate-a.yml",
            predicate_type="https://slsa.dev/provenance/v1", cert_oidc_issuer="https://token.actions.githubusercontent.com",
            required_ref="refs/heads/main", run_id=2002, run_attempt=1,
        )
        for field in ("job_workflow_sha", "source_sha"):
            with self.subTest(field=field), self.assertRaises(A0XHostedVerifierError):
                validate_verification_result(self._result_fixture(), **kwargs, **{field: "b" * 40, **({"source_sha": "a" * 40} if field == "job_workflow_sha" else {"job_workflow_sha": "a" * 40})})

    def test_pre_runner_input_mutation_matrix_refuses_without_receipt_or_runner(self) -> None:
        """Unauthenticated input changes never reach gh or create an output."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, GateBVerificationRequest, verify_hosted_gate_a

        cases = ("manifest_hash", "invalid_manifest", "policy", "source_state", "expired", "output_collision", "output_parent_symlink", "input_traversal", "input_parent_symlink", "workflow_parent_symlink", "symlink", "hardlink", "nonregular", "oversized")
        for case in cases:
            with self.subTest(case=case), TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                authorization_path, policy_path, manifest_path, bundle_path, trusted_root_path, transport_path = self._packet(root)
                output = root / ".a0x-runtime/gate-b-verifications/" / ("a" * 40) / "a0/gpt2/a0x-a0-gpt2-run-1/gate-a-verification-receipt.json"
                if case == "manifest_hash":
                    manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
                elif case == "invalid_manifest":
                    manifest_path.write_bytes(b"not-json")
                    authorization = json.loads(authorization_path.read_text())
                    authorization["hosted_inputs"]["manifest"]["sha256"] = self._sha(manifest_path)
                    authorization_path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
                elif case == "policy":
                    policy = json.loads(policy_path.read_text())
                    policy["required_ref"] = "refs/heads/wrong"
                    policy_path.write_bytes(json.dumps(policy, sort_keys=True, separators=(",", ":")).encode())
                elif case == "expired":
                    transport = json.loads(transport_path.read_text())
                    transport["expires_at"] = "2027-01-01T00:00:00Z"
                    transport_path.write_bytes(canonical_json_bytes(transport))
                    authorization = json.loads(authorization_path.read_text())
                    authorization["hosted_inputs"]["transport"]["sha256"] = self._sha(transport_path)
                    authorization_path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
                elif case == "output_collision":
                    output.parent.mkdir(parents=True)
                    output.write_bytes(b"occupied")
                elif case == "output_parent_symlink":
                    output.parent.mkdir(parents=True)
                    output.parent.rmdir()
                    redirect = root / "redirect"
                    redirect.mkdir()
                    output.parent.symlink_to(redirect, target_is_directory=True)
                elif case == "input_traversal":
                    authorization = json.loads(authorization_path.read_text())
                    authorization["hosted_inputs"]["manifest"]["path"] = "../hosted-gate-a-evidence.json"
                    authorization_path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
                elif case == "input_parent_symlink":
                    evidence = manifest_path.parent
                    redirect = root / "redirect"
                    redirect.mkdir()
                    evidence.rename(redirect / "evidence")
                    evidence.symlink_to(redirect / "evidence", target_is_directory=True)
                elif case == "workflow_parent_symlink":
                    github = root / ".github"
                    redirect = root / "redirect-github"
                    github.rename(redirect)
                    github.symlink_to(redirect, target_is_directory=True)
                elif case == "symlink":
                    bundle_path.unlink(); bundle_path.symlink_to(manifest_path)
                elif case == "hardlink":
                    duplicate = bundle_path.with_name("bundle-copy.jsonl")
                    os.link(bundle_path, duplicate)
                elif case == "nonregular":
                    bundle_path.unlink(); bundle_path.mkdir()
                elif case == "oversized":
                    bundle_path.write_bytes(b"x" * (1024 * 1024 + 1))
                states = [("a" * 40, "b" * 40, True)] if case != "source_state" else [("a" * 40, "b" * 40, False)]
                calls: list[tuple[str, ...]] = []
                with self.assertRaises(A0XHostedVerifierError):
                    verify_hosted_gate_a(
                        GateBVerificationRequest(root, authorization_path, Path("/opt/homebrew/bin/gh").resolve(), policy_path),
                        runner=lambda argv, _cwd: calls.append(tuple(argv)) or (0, self._result_fixture(), b""),
                        source_state_probe=lambda _root: states[0], clock=lambda: "2027-01-02T00:00:00Z" if case == "expired" else "2026-08-31T12:04:00Z",
                    )
                self.assertEqual(calls, [])
                if case == "output_collision":
                    self.assertEqual(output.read_bytes(), b"occupied")
                else:
                    self.assertFalse(output.exists())

    def test_post_runner_drift_and_invalid_runner_output_write_nothing(self) -> None:
        """A successful process status cannot bypass result, source, or rehash checks."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, GateBVerificationRequest, verify_hosted_gate_a

        for case in ("nonzero", "malformed", "runner_shape", "oversized_output", "source_drift", "input_drift"):
            with self.subTest(case=case), TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                authorization_path, policy_path, manifest_path, _bundle, _trusted, _transport = self._packet(root)
                output = root / ".a0x-runtime/gate-b-verifications/" / ("a" * 40) / "a0/gpt2/a0x-a0-gpt2-run-1/gate-a-verification-receipt.json"
                manifest_sha256 = self._sha(manifest_path)
                result = json.loads(self._result_fixture())
                result[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = manifest_sha256
                states = iter((("a" * 40, "b" * 40, True), ("b" * 40, "b" * 40, True)))

                def runner(_argv: tuple[str, ...], _cwd: Path) -> tuple[int, bytes, bytes]:
                    if case == "input_drift":
                        manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
                    if case == "nonzero":
                        return 1, b"", b"synthetic refusal"
                    if case == "runner_shape":
                        return (0, b"")  # type: ignore[return-value]
                    if case == "oversized_output":
                        return 0, b"x" * (1024 * 1024 + 1), b""
                    if case == "malformed":
                        return 0, b"not-json", b""
                    return 0, json.dumps(result, sort_keys=True, separators=(",", ":")).encode(), b""

                with self.assertRaises(A0XHostedVerifierError):
                    verify_hosted_gate_a(
                        GateBVerificationRequest(root, authorization_path, Path("/opt/homebrew/bin/gh").resolve(), policy_path),
                        runner=runner,
                        source_state_probe=lambda _root: next(states) if case == "source_drift" else ("a" * 40, "b" * 40, True),
                        clock=lambda: "2026-08-31T12:04:00Z",
                    )
                self.assertFalse(output.exists())

    def test_existing_receipt_refuses_before_second_runner_call(self) -> None:
        """A completed Gate B receipt is one-shot and never overwritten."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, GateBVerificationRequest, verify_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            authorization_path, policy_path, manifest_path, _bundle, _trusted, _transport = self._packet(root)
            result = json.loads(self._result_fixture())
            result[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = self._sha(manifest_path)
            calls: list[tuple[str, ...]] = []

            def runner(argv: tuple[str, ...], _cwd: Path) -> tuple[int, bytes, bytes]:
                calls.append(argv)
                return 0, json.dumps(result, sort_keys=True, separators=(",", ":")).encode(), b""

            request = GateBVerificationRequest(root, authorization_path, Path("/opt/homebrew/bin/gh").resolve(), policy_path)
            first = verify_hosted_gate_a(request, runner=runner, source_state_probe=lambda _root: ("a" * 40, "b" * 40, True), clock=lambda: "2026-08-31T12:04:00Z")
            with self.assertRaises(A0XHostedVerifierError) as raised:
                verify_hosted_gate_a(request, runner=runner, source_state_probe=lambda _root: ("a" * 40, "b" * 40, True), clock=lambda: "2026-08-31T12:04:00Z")
            self.assertEqual(raised.exception.code, "A0X_GATE_B_OUTPUT_EXISTS")
            self.assertEqual(len(calls), 1)
            self.assertEqual(first, (root / ".a0x-runtime/gate-b-verifications/" / ("a" * 40) / "a0/gpt2/a0x-a0-gpt2-run-1/gate-a-verification-receipt.json").read_bytes())

    def test_control_paths_reject_symlink_before_runner(self) -> None:
        """Resolving a symlink must never convert it into an accepted control file."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, GateBVerificationRequest, verify_hosted_gate_a

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            authorization_path, policy_path, _manifest, _bundle, _trusted, _transport = self._packet(root)
            alias = root / "authorization-link.json"
            alias.symlink_to(authorization_path)
            calls: list[tuple[str, ...]] = []
            with self.assertRaises(A0XHostedVerifierError):
                verify_hosted_gate_a(
                    GateBVerificationRequest(root, alias, Path("/opt/homebrew/bin/gh").resolve(), policy_path),
                    runner=lambda argv, _cwd: calls.append(tuple(argv)) or (0, self._result_fixture(), b""),
                    source_state_probe=lambda _root: ("a" * 40, "b" * 40, True), clock=lambda: "2026-08-31T12:04:00Z",
                )
            self.assertEqual(calls, [])

    def test_control_parent_and_output_traversal_refuse_before_runner(self) -> None:
        """Caller-controlled control parents and output traversal cannot escape root."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, GateBVerificationRequest, verify_hosted_gate_a

        for case in ("control_parent", "output_traversal"):
            with self.subTest(case=case), TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                authorization_path, policy_path, _manifest, _bundle, _trusted, _transport = self._packet(root)
                if case == "control_parent":
                    alias_parent = root / "authorization-parent"
                    alias_parent.symlink_to(authorization_path.parent, target_is_directory=True)
                    authorization_path = alias_parent / authorization_path.name
                else:
                    authorization = json.loads(authorization_path.read_text())
                    authorization["verification_receipt_path"] = ".a0x-runtime/gate-b-verifications/" + "a" * 40 + "/a0/gpt2/../gate-a-verification-receipt.json"
                    authorization_path.write_bytes(canonical_json_bytes(authorization))
                calls: list[tuple[str, ...]] = []
                with self.assertRaises(A0XHostedVerifierError):
                    verify_hosted_gate_a(
                        GateBVerificationRequest(root, authorization_path, Path("/opt/homebrew/bin/gh").resolve(), policy_path),
                        runner=lambda argv, _cwd: calls.append(tuple(argv)) or (0, self._result_fixture(), b""),
                        source_state_probe=lambda _root: ("a" * 40, "b" * 40, True), clock=lambda: "2026-08-31T12:04:00Z",
                    )
                self.assertEqual(calls, [])

    def test_post_runner_control_and_workflow_rehash_refuse_without_receipt(self) -> None:
        """Runner-time swaps of authorization, policy, or raw workflow are terminal."""
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError, GateBVerificationRequest, verify_hosted_gate_a

        for case in ("authorization", "policy", "workflow", "input_parent", "workflow_parent"):
            with self.subTest(case=case), TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                authorization_path, policy_path, manifest_path, _bundle, _trusted, _transport = self._packet(root)
                result = json.loads(self._result_fixture())
                result[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = self._sha(manifest_path)

                def runner(_argv: tuple[str, ...], _cwd: Path) -> tuple[int, bytes, bytes]:
                    if case in {"authorization", "policy", "workflow"}:
                        target = {"authorization": authorization_path, "policy": policy_path, "workflow": root / ".github/workflows/a0x-hosted-gate-a.yml"}[case]
                        target.write_bytes(target.read_bytes() + b" ")
                    elif case == "input_parent":
                        evidence = manifest_path.parent
                        redirect = root / "redirect-evidence"
                        evidence.rename(redirect)
                        evidence.symlink_to(redirect, target_is_directory=True)
                    else:
                        github = root / ".github"
                        redirect = root / "redirect-github"
                        github.rename(redirect)
                        github.symlink_to(redirect, target_is_directory=True)
                    return 0, json.dumps(result, sort_keys=True, separators=(",", ":")).encode(), b""

                with self.assertRaises(A0XHostedVerifierError):
                    verify_hosted_gate_a(
                        GateBVerificationRequest(root, authorization_path, Path("/opt/homebrew/bin/gh").resolve(), policy_path),
                        runner=runner, source_state_probe=lambda _root: ("a" * 40, "b" * 40, True), clock=lambda: "2026-08-31T12:04:00Z",
                    )
                self.assertFalse((root / ".a0x-runtime/gate-b-verifications").exists())

    def test_cli_wraps_only_injected_shell_free_verifier(self) -> None:
        """CLI constructs no shell and exposes only a stable refusal code."""
        script_path = Path(__file__).parents[1] / "scripts/a0x_verify_hosted_gate_a.py"
        spec = importlib.util.spec_from_file_location("a0x_verify_hosted_gate_a", script_path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        stream = io.StringIO()
        arguments = [
            "--repository-root", "/private/tmp", "--authorization", "/private/tmp/authorization.json",
            "--verifier", "/opt/homebrew/bin/gh", "--policy", "/private/tmp/policy.json",
        ]
        code = module.main(
            arguments, stderr=stream,
            runner=lambda _argv, _cwd: (_ for _ in ()).throw(AssertionError("must not invoke runner")),
            source_state_probe=lambda _root: (_ for _ in ()).throw(AssertionError("must not probe source")),
        )
        self.assertEqual(code, 2)
        self.assertEqual(stream.getvalue(), "A0X_GATE_B_INPUT_INVALID\n")

    def test_wrapper_scrubs_child_environment_and_uses_absolute_git(self) -> None:
        """No inherited credential, proxy, or GitHub variable reaches a child."""
        script_path = Path(__file__).parents[1] / "scripts/a0x_verify_hosted_gate_a.py"
        spec = importlib.util.spec_from_file_location("a0x_verify_hosted_gate_a_env", script_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        observed: list[dict[str, object]] = []

        class Process:
            returncode = 0
            stdout = b"a" * 40 + b"\n"
            stderr = b""

        with mock.patch.dict(os.environ, {"GH_TOKEN": "secret", "GITHUB_TOKEN": "secret", "HTTPS_PROXY": "bad"}, clear=False), mock.patch.object(module.subprocess, "run", side_effect=lambda *args, **kwargs: observed.append({"argv": args[0], "env": kwargs["env"], "timeout": kwargs["timeout"]}) or Process()):
            module._runner(("/opt/homebrew/bin/gh", "attestation"), Path("/private/tmp"))
            module._source_state(Path("/private/tmp"))
        self.assertEqual(len(observed), 4)
        for child in observed:
            self.assertEqual(child["env"], {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"})
        self.assertEqual(observed[0]["timeout"], 300)
        self.assertTrue(all(child["timeout"] == 30 for child in observed[1:]))
        self.assertTrue(all(child["argv"][0] == "/usr/bin/git" for child in observed[1:]))
        from latent_triz.a0x_hosted_verifier import A0XHostedVerifierError

        with mock.patch.object(module.subprocess, "run", side_effect=OSError("synthetic")):
            with self.assertRaises(A0XHostedVerifierError) as runner_error:
                module._runner(("/opt/homebrew/bin/gh", "attestation"), Path("/private/tmp"))
            with self.assertRaises(A0XHostedVerifierError) as source_error:
                module._source_state(Path("/private/tmp"))
        self.assertEqual(runner_error.exception.code, "A0X_GATE_B_ATTESTATION_REFUSED")
        self.assertEqual(source_error.exception.code, "A0X_GATE_B_SOURCE_DRIFT")


    @staticmethod
    def _result_fixture() -> bytes:
        return (Path(__file__).parent / "fixtures/a0x/hosted-gate-a/positive/gh-2.97.0-verification-result.json").read_bytes()

    def _packet(self, root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
        head, tree = "a" * 40, "b" * 40
        encoded = []
        for lane_id, command in sorted(LANE_COMMANDS.items()):
            raw = build_lane_receipt(lane_id, head, tree, command, "PASS")
            encoded.append(base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii"))
        workflow_path = root / ".github/workflows/a0x-hosted-gate-a.yml"
        workflow_path.parent.mkdir(parents=True)
        workflow_path.write_bytes(b"name: synthetic-hosted-gate-a\n")
        manifest_raw = build_manifest(
            repository="MarcoPorcellato/Latent-TRIZ", source_head=head, source_tree=tree,
            workflow_sha256=self._sha(workflow_path), run_id=2002, run_attempt=1,
            requirements_lock_sha256="d" * 64, action_manifest_sha256="e" * 64,
            lane_manifest_sha256="f" * 64, encoded_lane_outputs=encoded,
        )
        evidence = root / f".a0x-runtime/gate-a/evidence/{head}"
        evidence.mkdir(parents=True)
        manifest_path = evidence / "hosted-gate-a-evidence.json"
        bundle_path = evidence / "hosted-gate-a-attestation.bundle.jsonl"
        trusted_root_path = evidence / "github-trusted-root.jsonl"
        transport_path = evidence / "hosted-gate-a-transport.json"
        manifest_path.write_bytes(manifest_raw)
        bundle_path.write_bytes(b'{"synthetic":"bundle"}\n')
        trusted_root_path.write_bytes(b'{"synthetic":"root"}\n')
        transport_path.write_bytes(canonical_json_bytes({
            "artifact_class": "a0x-hosted-gate-a-transport", "transport_profile": "a0x-hosted-gate-a-transport-v1",
            "repository": "MarcoPorcellato/Latent-TRIZ", "artifact_id": 1001, "run_id": 2002, "run_attempt": 1,
            "head_sha": head, "archive_digest": "sha256:" + "c" * 64, "archive_size_bytes": 512,
            "created_at": "2026-08-31T12:00:00Z", "expires_at": "2026-09-30T12:00:00Z", "captured_at": "2026-08-31T12:03:00Z",
        }))
        policy_path = root / ".a0x-runtime/gate-a/verifier-policy.json"
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        policy_path.write_bytes((Path(__file__).parent / "fixtures/a0x/hosted-gate-a/positive/verifier-policy.json").read_bytes())
        hosted_inputs = {
            "manifest": {"path": str(manifest_path.relative_to(root)), "sha256": self._sha(manifest_path)},
            "attestation_bundle": {"path": str(bundle_path.relative_to(root)), "sha256": self._sha(bundle_path)},
            "trusted_root": {"path": str(trusted_root_path.relative_to(root)), "sha256": self._sha(trusted_root_path)},
            "transport": {"path": str(transport_path.relative_to(root)), "sha256": self._sha(transport_path)},
        }
        output_relative = f".a0x-runtime/gate-b-verifications/{head}/a0/gpt2/a0x-a0-gpt2-run-1/gate-a-verification-receipt.json"
        authorization = json.loads((Path(__file__).parent / "fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json").read_text())
        authorization["hosted_inputs"] = hosted_inputs
        authorization["verifier"]["policy_raw_sha256"] = self._sha(policy_path)
        authorization_path = root / ".a0x-runtime/gate-b-authorizations/a0/gpt2/authorization.json"
        authorization_path.parent.mkdir(parents=True)
        authorization_path.write_bytes(canonical_json_bytes(authorization))
        return authorization_path, policy_path, manifest_path, bundle_path, trusted_root_path, transport_path

    @staticmethod
    def _sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
