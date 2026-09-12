"""Synthetic tests for the injected A0X Hosted Gate A capture adapter."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from latent_triz import a0x_hosted_capture as capture_library


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SCRIPT_PATH = ROOT / "scripts" / "a0x_capture_hosted_gate_a.py"
HEAD = "a" * 40
TREE = "b" * 40
DOWNLOAD_HELP = b"""Download attestations associated with an artifact for offline use.
Any associated bundle(s) will be written to a file in the current directory named after the artifact's digest.
the file will be named "sha256:1234.jsonl".
USAGE
  gh attestation download [<file-path> | oci://<image-uri>] [--owner | --repo] [flags]
  -L, --limit int
      --predicate-type string
  -R, --repo string
"""
TRUSTED_ROOT_HELP = b"""Output contents for a trusted_root.jsonl file, likely for offline verification.
USAGE
  gh attestation trusted-root [--tuf-url <url> --tuf-root <file-path>] [--verify-only] [flags]
"""


def _help_output(argv: tuple[str, ...]) -> bytes | None:
    if argv[1:] == ("attestation", "download", "--help"):
        return DOWNLOAD_HELP
    if argv[1:] == ("attestation", "trusted-root", "--help"):
        return TRUSTED_ROOT_HELP
    return None


def _script_module():
    spec = importlib.util.spec_from_file_location("a0x_capture_hosted_gate_a", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _manifest() -> bytes:
    from latent_triz.a0x_hosted_gate_a import LANE_IDS, build_lane_receipt, build_manifest

    commands = {
        "a0x-no-model": ("make", "a0x-no-model-verify"),
        "a0x-synthetic": ("make", "a0x-synthetic-verify"),
        "documentation-audit": ("make", "docs-audit"),
        "repository-python311": ("python", "scripts/repository_check.py"),
        "repository-python312": ("python", "scripts/repository_check.py"),
        "schema-cross-validation-python311": ("python", "scripts/schema_cross_validate.py"),
        "schema-cross-validation-python312": ("python", "scripts/schema_cross_validate.py"),
    }
    outputs = [
        base64.urlsafe_b64encode(build_lane_receipt(lane, HEAD, TREE, commands[lane], "PASS"))
        .rstrip(b"=").decode("ascii")
        for lane in LANE_IDS
    ]
    return build_manifest(
        repository="MarcoPorcellato/Latent-TRIZ", source_head=HEAD, source_tree=TREE,
        workflow_sha256="c" * 64, run_id=123, run_attempt=1,
        requirements_lock_sha256="d" * 64, action_manifest_sha256="e" * 64,
        lane_manifest_sha256="f" * 64, encoded_lane_outputs=outputs,
    )


def _archive(manifest: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        member = zipfile.ZipInfo("a0x-hosted-gate-a-evidence.json")
        member.external_attr = 0o100644 << 16
        archive.writestr(member, manifest)
    return output.getvalue()


class CaptureHostedGateAAdapterTest(unittest.TestCase):
    def _arguments(self, module: object, executable: Path, archive: bytes, manifest: bytes, output: Path):
        return module._parser().parse_args([
            "--gh-path", str(executable), "--repository", "MarcoPorcellato/Latent-TRIZ",
            "--source-head", HEAD, "--source-tree", TREE, "--run-id", "123", "--run-attempt", "1",
            "--artifact-id", "456", "--artifact-name", f"a0x-hosted-gate-a-{HEAD}",
            "--archive-sha256", hashlib.sha256(archive).hexdigest(), "--archive-size-bytes", str(len(archive)),
            "--created-at", "2026-09-01T11:00:00Z", "--expires-at", "2026-09-02T12:00:00Z",
            "--captured-at", "2026-09-01T12:00:00Z", "--output-root", str(output),
        ])

    def test_parser_requires_all_capture_bindings(self) -> None:
        """Removing an explicit binding must prevent adapter admission."""
        module = _script_module()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            module._parser().parse_args(["--gh-path", "/absolute/gh"])

    def test_manifest_hash_is_derived_from_the_single_downloaded_archive(self) -> None:
        """The operator must not be able to inject a manifest hash before archive retrieval."""
        module = _script_module()
        manifest = _manifest()
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            arguments = self._arguments(module, root / "gh", _archive(manifest), manifest, root / "capture")
            self.assertFalse(hasattr(arguments, "manifest_sha256"))

    def test_official_gh_297_download_contract_uses_subject_file_and_reads_bundle_file(self) -> None:
        """The 2.97.0 CLI consumes a subject path and writes its JSONL bundle in cwd."""
        module = _script_module()
        manifest = _manifest()
        archive = _archive(manifest)
        bundle = b'{"synthetic":"bundle"}\n'
        trusted_root = b'{"synthetic":"trusted-root"}\n'
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                arguments = self._arguments(module, executable, archive, manifest, root / "capture")
                calls: list[tuple[tuple[str, ...], Path | None]] = []

                def runner(
                    argv: tuple[str, ...], _env: dict[str, str], _timeout: int,
                    _stdout_limit: int, cwd: Path | None,
                ) -> tuple[int, bytes, bytes]:
                    calls.append((argv, cwd))
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    help_output = _help_output(argv)
                    if help_output is not None:
                        return 0, help_output, b""
                    if "/zip" in argv[-1]:
                        return 0, archive, b""
                    if argv[1:3] == ("attestation", "download"):
                        assert cwd is not None
                        expected_subject = cwd / "a0x-hosted-gate-a-evidence.json"
                        self.assertEqual(expected_subject, Path(argv[3]))
                        self.assertEqual(manifest, expected_subject.read_bytes())
                        (cwd / ("sha256:" + hashlib.sha256(manifest).hexdigest() + ".jsonl")).write_bytes(bundle)
                        return 0, b"", b""
                    if argv[1:] == ("attestation", "trusted-root"):
                        return 0, trusted_root, b""
                    self.fail(f"unexpected argv: {argv!r}")

                result = module.capture(
                    arguments, runner=runner, publish_at=self._publish_at,
                    supported_host=lambda: True,
                )
                self.assertEqual(root / "capture", result)
                download = [
                    argv for argv, _cwd in calls
                    if argv[1:3] == ("attestation", "download") and argv[-1] != "--help"
                ]
                self.assertEqual(1, len(download))
                self.assertEqual(
                    (
                        str(executable), "attestation", "download",
                        str(next(cwd for argv, cwd in calls if argv[1:3] == ("attestation", "download"))
                            / "a0x-hosted-gate-a-evidence.json"),
                        "--repo", "MarcoPorcellato/Latent-TRIZ",
                        "--predicate-type", "https://slsa.dev/provenance/v1",
                        "--limit", "30",
                    ),
                    download[0],
                )
                self.assertEqual(bundle, (result / "hosted-gate-a-attestation.bundle.jsonl").read_bytes())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_injected_transport_revalidates_pinned_cli_before_each_fixed_operation(self) -> None:
        """Removing a version/hash preflight would let one later operation use replaced CLI bytes."""
        module = _script_module()
        manifest, archive = _manifest(), _archive(_manifest())
        bundle, trusted_root = b'{"synthetic":"bundle"}\n', b'{"synthetic":"trusted-root"}\n'
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                arguments = self._arguments(module, executable, archive, manifest, root / "capture")
                calls: list[tuple[tuple[str, ...], dict[str, str], Path | None]] = []

                def runner(
                    argv: tuple[str, ...], env: dict[str, str], _timeout: int,
                    _stdout_limit: int, cwd: Path | None,
                ) -> tuple[int, bytes, bytes]:
                    calls.append((argv, env, cwd))
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    help_output = _help_output(argv)
                    if help_output is not None:
                        return 0, help_output, b""
                    if "/zip" in argv[-1]:
                        return 0, archive, b""
                    if argv[1:3] == ("attestation", "download"):
                        assert cwd is not None
                        (cwd / ("sha256:" + hashlib.sha256(manifest).hexdigest() + ".jsonl")).write_bytes(bundle)
                        return 0, b"", b""
                    if argv[1:] == ("attestation", "trusted-root"):
                        return 0, trusted_root, b""
                    self.fail(f"unexpected argv: {argv!r}")

                result = module.capture(
                    arguments, runner=runner, publish_at=self._publish_at,
                    supported_host=lambda: True,
                )

                self.assertEqual(root / "capture", result)
                self.assertEqual(
                    [
                        (str(executable), "--version"),
                        (str(executable), "attestation", "download", "--help"),
                        (str(executable), "--version"),
                        (str(executable), "attestation", "trusted-root", "--help"),
                        (str(executable), "--version"),
                        (str(executable), "api", "--method", "GET", "/repos/MarcoPorcellato/Latent-TRIZ/actions/artifacts/456/zip"),
                        (str(executable), "--version"),
                        (
                            str(executable), "attestation", "download",
                            str(calls[0][2] / "a0x-hosted-gate-a-evidence.json"),
                            "--repo", "MarcoPorcellato/Latent-TRIZ",
                            "--predicate-type", "https://slsa.dev/provenance/v1",
                            "--limit", "30",
                        ),
                        (str(executable), "--version"),
                        (str(executable), "attestation", "trusted-root"),
                    ],
                    [argv for argv, _env, _cwd in calls],
                )
                self.assertTrue(all(env == module.FIXED_ENV for _argv, env, _cwd in calls))
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_replaced_cli_is_refused_before_later_transport_operation(self) -> None:
        """Removing each-operation pin refresh would admit a replacement after archive retrieval."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, PIN_INVALID

        module = _script_module()
        manifest, archive = _manifest(), _archive(_manifest())
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                arguments = self._arguments(module, executable, archive, manifest, root / "capture")
                calls: list[tuple[str, ...]] = []

                def runner(
                    argv: tuple[str, ...], _env: dict[str, str], _timeout: int,
                    _stdout_limit: int, _cwd: Path | None,
                ) -> tuple[int, bytes, bytes]:
                    calls.append(argv)
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    help_output = _help_output(argv)
                    if help_output is not None:
                        return 0, help_output, b""
                    executable.write_bytes(b"replaced gh bytes\n")
                    return 0, archive, b""

                with self.assertRaisesRegex(A0XHostedCaptureError, PIN_INVALID):
                    module.capture(
                        arguments, runner=runner, publish_at=self._publish_at,
                        supported_host=lambda: True,
                    )
                self.assertEqual(
                    [
                        (str(executable), "--version"),
                        (str(executable), "attestation", "download", "--help"),
                        (str(executable), "--version"),
                        (str(executable), "attestation", "trusted-root", "--help"),
                        (str(executable), "--version"),
                        (str(executable), "api", "--method", "GET", "/repos/MarcoPorcellato/Latent-TRIZ/actions/artifacts/456/zip"),
                    ],
                    calls,
                )
                self.assertFalse((root / "capture").exists())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_invalid_transport_timestamps_refuse_before_every_runner_call(self) -> None:
        """Removing pre-transport transport validation would send malformed explicit bindings."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        manifest, archive = _manifest(), _archive(_manifest())
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                for field in ("created_at", "captured_at"):
                    with self.subTest(field=field):
                        arguments = self._arguments(module, executable, archive, manifest, root / f"capture-{field}")
                        setattr(arguments, field, "not-a-timestamp")
                        calls: list[tuple[str, ...]] = []

                        def runner(
                            argv: tuple[str, ...], _env: dict[str, str], _timeout: int,
                            _stdout_limit: int, _cwd: Path | None,
                        ) -> tuple[int, bytes, bytes]:
                            calls.append(argv)
                            self.fail(f"unexpected runner call: {argv!r}")

                        with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                            module.capture(
                                arguments, runner=runner, publish_at=self._publish_at,
                                supported_host=lambda: True,
                            )
                        self.assertEqual([], calls)
                        self.assertFalse(arguments.output_root.exists())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_oversized_runner_output_refuses_before_staging_or_next_operation(self) -> None:
        """Removing operation caps would retain oversized untrusted transport stdout."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        manifest, archive = _manifest(), _archive(_manifest())
        limits = {
            "archive": len(archive),
            "bundle": capture_library.MAX_BUNDLE_BYTES,
            "trusted": capture_library.MAX_TRUSTED_ROOT_BYTES,
        }
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                for operation, limit in limits.items():
                    with self.subTest(operation=operation):
                        arguments = self._arguments(module, executable, archive, manifest, root / f"capture-{operation}")
                        calls: list[tuple[tuple[str, ...], int, int]] = []

                        def runner(
                            argv: tuple[str, ...], _env: dict[str, str], timeout: int,
                            stdout_limit: int, cwd: Path | None,
                        ) -> tuple[int, bytes, bytes]:
                            calls.append((argv, timeout, stdout_limit))
                            if argv[-1] == "--version":
                                return 0, b"synthetic gh version\n", b""
                            help_output = _help_output(argv)
                            if help_output is not None:
                                return 0, help_output, b""
                            if operation == "archive" and "/zip" in argv[-1]:
                                return 0, b"x" * (limit + 1), b""
                            if operation == "bundle" and argv[1:3] == ("attestation", "download"):
                                assert cwd is not None
                                (cwd / ("sha256:" + hashlib.sha256(manifest).hexdigest() + ".jsonl")).write_bytes(
                                    b"x" * (limit + 1)
                                )
                                return 0, b"", b""
                            if operation == "trusted" and argv[1:] == ("attestation", "trusted-root"):
                                return 0, b"x" * (limit + 1), b""
                            if "/zip" in argv[-1]:
                                return 0, archive, b""
                            if argv[1:3] == ("attestation", "download"):
                                assert cwd is not None
                                (cwd / ("sha256:" + hashlib.sha256(manifest).hexdigest() + ".jsonl")).write_bytes(
                                    b'{"synthetic":"bundle"}\n'
                                )
                                return 0, b"", b""
                            return 0, b'{"synthetic":"trusted-root"}\n', b""

                        with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                            module.capture(
                                arguments, runner=runner, publish_at=self._publish_at,
                                supported_host=lambda: True,
                            )
                        self.assertFalse(arguments.output_root.exists())
                        if operation != "bundle":
                            self.assertEqual(limit, [entry[2] for entry in calls if entry[0][-1] != "--version"][-1])
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_runner_timeout_contract_is_passed_and_refused_before_output(self) -> None:
        """Removing timeout propagation would permit an injected runner to wait without a bound."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        manifest, archive = _manifest(), _archive(_manifest())
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                arguments = self._arguments(module, executable, archive, manifest, root / "capture-timeout")
                calls: list[tuple[tuple[str, ...], int, int]] = []

                def runner(
                    argv: tuple[str, ...], _env: dict[str, str], timeout: int,
                    stdout_limit: int, _cwd: Path | None,
                ) -> tuple[int, bytes, bytes]:
                    calls.append((argv, timeout, stdout_limit))
                    raise TimeoutError("synthetic timeout")

                with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                    module.capture(
                        arguments, runner=runner, publish_at=self._publish_at,
                        supported_host=lambda: True,
                    )
                self.assertEqual([(str(executable), "--version")], [entry[0] for entry in calls])
                self.assertEqual(module.TRANSPORT_TIMEOUT_SECONDS, calls[0][1])
                self.assertEqual(module.MAX_VERSION_STDOUT_BYTES, calls[0][2])
                self.assertFalse(arguments.output_root.exists())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_production_runner_requires_token_before_starting_subprocess(self) -> None:
        """An absent credential must fail before any child or transport can start."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        calls: list[object] = []

        def fake_run(*args: object, **kwargs: object) -> object:
            calls.append((args, kwargs))
            self.fail("subprocess must not start without GH_TOKEN")

        with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
            module._production_runner(environ={}, run=fake_run)
        self.assertEqual([], calls)

    def test_production_runner_is_shell_free_and_keeps_token_only_in_child_environment(self) -> None:
        """Credentials must never enter argv, cwd, returned output, or inherited ambient state."""
        module = _script_module()
        token = "synthetic-secret-token"
        observed: list[tuple[tuple[str, ...], dict[str, object]]] = []

        def fake_run(argv: tuple[str, ...], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            observed.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout=b"ok\n", stderr=b"")

        runner = module._production_runner(
            environ={"GH_TOKEN": token, "UNRELATED_SECRET": "must-not-pass"}, run=fake_run,
        )
        result = runner(("/absolute/gh", "--version"), dict(module.FIXED_ENV), 9, 32, Path("/private/tmp"))

        self.assertEqual((0, b"ok\n", b""), result)
        self.assertEqual(1, len(observed))
        argv, kwargs = observed[0]
        self.assertNotIn(token, repr(argv))
        self.assertNotIn(token, repr(kwargs["cwd"]))
        self.assertFalse(kwargs["shell"])
        self.assertIs(subprocess.DEVNULL, kwargs["stdin"])
        self.assertEqual(9, kwargs["timeout"])
        self.assertEqual(32, kwargs["stdout_limit"])
        self.assertEqual(module.MAX_STDERR_BYTES, kwargs["stderr_limit"])
        child_env = kwargs["env"]
        self.assertEqual(token, child_env["GH_TOKEN"])
        self.assertNotIn("UNRELATED_SECRET", child_env)
        self.assertNotIn(token.encode(), result[1] + result[2])

    def test_production_runner_refuses_oversized_stderr(self) -> None:
        """Untrusted stderr is bounded independently from operation stdout."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()

        def fake_run(argv: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
            return subprocess.CompletedProcess(
                argv, 0, stdout=b"", stderr=b"x" * (module.MAX_STDERR_BYTES + 1),
            )

        runner = module._production_runner(environ={"GH_TOKEN": "secret"}, run=fake_run)
        with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
            runner(("/absolute/gh", "api"), dict(module.FIXED_ENV), 9, 32, Path("/private/tmp"))

    def test_bounded_subprocess_stops_while_stdout_exceeds_limit(self) -> None:
        """The real pipe reader must reject during acquisition, not after unbounded buffering."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
            module._run_bounded_subprocess(
                (sys.executable, "-c", "import os; os.write(1, b'x' * 65536)"),
                cwd=Path("/private/tmp"), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                env=dict(module.FIXED_ENV), timeout=5, shell=False,
                stdout_limit=32, stderr_limit=32,
            )

    def test_private_input_writer_refuses_symlink_and_existing_file(self) -> None:
        """Temporary archive and subject bytes must never follow or overwrite a path."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / "target"
            target.write_bytes(b"preserve")
            link = root / "input"
            link.symlink_to(target)
            with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                module._write_private_regular(link, b"replacement")
            self.assertEqual(b"preserve", target.read_bytes())
            link.unlink()
            link.write_bytes(b"occupied")
            with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                module._write_private_regular(link, b"replacement")
            self.assertEqual(b"occupied", link.read_bytes())

    def test_operational_main_executes_injected_shell_free_capture(self) -> None:
        """The public entry point must execute the validated transaction, not refuse unconditionally."""
        module = _script_module()
        manifest = _manifest()
        archive = _archive(manifest)
        bundle = b'{"synthetic":"bundle"}\n'
        trusted_root = b'{"synthetic":"trusted-root"}\n'
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                arguments = self._arguments(module, executable, archive, manifest, root / "capture")

                def runner(
                    argv: tuple[str, ...], _env: dict[str, str], _timeout: int,
                    _stdout_limit: int, cwd: Path | None,
                ) -> tuple[int, bytes, bytes]:
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    help_output = _help_output(argv)
                    if help_output is not None:
                        return 0, help_output, b""
                    if "/zip" in argv[-1]:
                        return 0, archive, b""
                    if argv[1:3] == ("attestation", "download"):
                        assert cwd is not None
                        (cwd / ("sha256:" + hashlib.sha256(manifest).hexdigest() + ".jsonl")).write_bytes(bundle)
                        return 0, b"", b""
                    return 0, trusted_root, b""

                self.assertEqual(
                    0,
                    module.main(
                        self._argv(arguments), runner=runner, publish_at=self._publish_at,
                        supported_host=lambda: True,
                    ),
                )
                self.assertTrue((root / "capture" / "hosted-gate-a-evidence.json").is_file())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    def test_cli_help_contract_refuses_before_archive_transport(self) -> None:
        """A pinned version with incompatible attestation syntax must stop before network transport."""
        from latent_triz.a0x_hosted_capture import A0XHostedCaptureError, CAPTURE_INVALID

        module = _script_module()
        manifest = _manifest()
        archive = _archive(manifest)
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = root / "synthetic-gh"
            executable.write_bytes(b"synthetic pinned gh\n")
            original_sha, original_version = capture_library.GH_SHA256, capture_library.GH_VERSION
            try:
                module.GH_SHA256 = hashlib.sha256(executable.read_bytes()).hexdigest()
                module.GH_VERSION = "synthetic gh version"
                arguments = self._arguments(module, executable, archive, manifest, root / "capture")
                calls: list[tuple[str, ...]] = []

                def runner(
                    argv: tuple[str, ...], _env: dict[str, str], _timeout: int,
                    _stdout_limit: int, _cwd: Path | None,
                ) -> tuple[int, bytes, bytes]:
                    calls.append(argv)
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    return 0, b"incompatible help\n", b""

                with self.assertRaisesRegex(A0XHostedCaptureError, CAPTURE_INVALID):
                    module.capture(
                        arguments, runner=runner, publish_at=self._publish_at,
                        supported_host=lambda: True,
                    )
                self.assertFalse(any("/zip" in value for call in calls for value in call))
                self.assertFalse(arguments.output_root.exists())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    @staticmethod
    def _argv(arguments: object) -> list[str]:
        values = vars(arguments)
        result: list[str] = []
        for key, value in values.items():
            result.extend(("--" + key.replace("_", "-"), str(value)))
        return result

    @staticmethod
    def _publish_at(parent_fd: int, stage_name: str, destination_name: str) -> None:
        os.rename(stage_name, destination_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
