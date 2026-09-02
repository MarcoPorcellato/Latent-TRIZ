"""Synthetic tests for the injected A0X Hosted Gate A capture adapter."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
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
            "--artifact-id", "456", "--artifact-name", "a0x-hosted-gate-a-evidence",
            "--archive-sha256", hashlib.sha256(archive).hexdigest(), "--archive-size-bytes", str(len(archive)),
            "--manifest-sha256", hashlib.sha256(manifest).hexdigest(),
            "--created-at", "2026-09-01T11:00:00Z", "--expires-at", "2026-09-02T12:00:00Z",
            "--captured-at", "2026-09-01T12:00:00Z", "--output-root", str(output),
        ])

    def test_parser_requires_all_capture_bindings(self) -> None:
        """Removing an explicit binding must prevent adapter admission."""
        module = _script_module()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            module._parser().parse_args(["--gh-path", "/absolute/gh"])

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
                calls: list[tuple[tuple[str, ...], dict[str, str]]] = []

                def runner(argv: tuple[str, ...], env: dict[str, str]) -> tuple[int, bytes, bytes]:
                    calls.append((argv, env))
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    if "/zip" in argv[-1]:
                        return 0, archive, b""
                    if argv[1:3] == ("attestation", "download"):
                        return 0, bundle, b""
                    if argv[1:] == ("attestation", "trusted-root"):
                        return 0, trusted_root, b""
                    self.fail(f"unexpected argv: {argv!r}")

                result = module.capture(arguments, runner=runner, publish_at=self._publish_at)

                self.assertEqual(root / "capture", result)
                self.assertEqual(
                    [
                        (str(executable), "--version"),
                        (str(executable), "api", "--method", "GET", "/repos/MarcoPorcellato/Latent-TRIZ/actions/artifacts/456/zip"),
                        (str(executable), "--version"),
                        (str(executable), "attestation", "download", "--repo", "MarcoPorcellato/Latent-TRIZ", "--digest", "sha256:" + hashlib.sha256(manifest).hexdigest()),
                        (str(executable), "--version"),
                        (str(executable), "attestation", "trusted-root"),
                    ],
                    [argv for argv, _env in calls],
                )
                self.assertTrue(all(env == module.FIXED_ENV for _argv, env in calls))
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

                def runner(argv: tuple[str, ...], _env: dict[str, str]) -> tuple[int, bytes, bytes]:
                    calls.append(argv)
                    if argv[-1] == "--version":
                        return 0, b"synthetic gh version\n", b""
                    executable.write_bytes(b"replaced gh bytes\n")
                    return 0, archive, b""

                with self.assertRaisesRegex(A0XHostedCaptureError, PIN_INVALID):
                    module.capture(arguments, runner=runner, publish_at=self._publish_at)
                self.assertEqual([(str(executable), "--version"), (str(executable), "api", "--method", "GET", "/repos/MarcoPorcellato/Latent-TRIZ/actions/artifacts/456/zip")], calls)
                self.assertFalse((root / "capture").exists())
            finally:
                capture_library.GH_SHA256, capture_library.GH_VERSION = original_sha, original_version

    @staticmethod
    def _publish_at(parent_fd: int, stage_name: str, destination_name: str) -> None:
        os.rename(stage_name, destination_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
