#!/usr/bin/env python3
"""Capture A0X Hosted Gate A through one pinned, shell-free transport."""

from __future__ import annotations

import argparse
import hashlib
import os
import selectors
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz import a0x_hosted_capture as capture_library


GH_VERSION = capture_library.GH_VERSION
GH_SHA256 = capture_library.GH_SHA256
FIXED_ENV = {
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
}
TRANSPORT_TIMEOUT_SECONDS = 30
MAX_VERSION_STDOUT_BYTES = capture_library.MAX_TRANSPORT_BYTES
MAX_HELP_STDOUT_BYTES = 16 * 1024
MAX_STDERR_BYTES = 16 * 1024
Runner = Callable[[tuple[str, ...], dict[str, str], int, int, Path | None], tuple[int, bytes, bytes]]
SubprocessCall = Callable[..., object]
DOWNLOAD_HELP_MARKERS = (
    "Any associated bundle(s) will be written to a file in the current directory named after the artifact's digest.",
    'the file will be named "sha256:1234.jsonl".',
    "gh attestation download [<file-path> | oci://<image-uri>] [--owner | --repo] [flags]",
    "-L, --limit int",
    "--predicate-type string",
    "-R, --repo string",
)
TRUSTED_ROOT_HELP_MARKERS = (
    "Output contents for a trusted_root.jsonl file",
    "gh attestation trusted-root [--tuf-url <url> --tuf-root <file-path>] [--verify-only] [flags]",
)


def _write_private_regular(path: Path, raw: bytes) -> None:
    """Create one private regular file exclusively without following a leaf link."""
    if not isinstance(raw, bytes) or not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_CLOEXEC")):
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError("short private write")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size != len(raw):
            raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    except capture_library.A0XHostedCaptureError:
        raise
    except OSError as error:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _run_bounded_subprocess(
    argv: tuple[str, ...], *, cwd: Path, stdin: int, stdout: int, stderr: int,
    check: bool, env: dict[str, str], timeout: int, shell: bool,
    stdout_limit: int, stderr_limit: int,
) -> subprocess.CompletedProcess[bytes]:
    """Read child pipes incrementally and terminate at the first byte over a cap."""
    if shell or check or stdout != subprocess.PIPE or stderr != subprocess.PIPE:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    try:
        process = subprocess.Popen(
            argv, cwd=cwd, stdin=stdin, stdout=stdout, stderr=stderr,
            env=env, shell=False,
        )
        if process.stdout is None or process.stderr is None:
            raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + timeout
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            events = selector.select(remaining)
            if not events:
                raise subprocess.TimeoutExpired(argv, timeout)
            for key, _mask in events:
                name = key.data
                allowance = limits[name] - len(buffers[name])
                chunk = os.read(key.fileobj.fileno(), min(64 * 1024, allowance + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffers[name].extend(chunk)
                if len(buffers[name]) > limits[name]:
                    raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(argv, timeout)
        return_code = process.wait(timeout=remaining)
        return subprocess.CompletedProcess(
            argv, return_code, bytes(buffers["stdout"]), bytes(buffers["stderr"]),
        )
    except capture_library.A0XHostedCaptureError:
        raise
    except (OSError, subprocess.TimeoutExpired, TypeError, ValueError) as error:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID) from error
    finally:
        selector.close()
        if process is not None:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                pass
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gh-path", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--artifact-id", required=True, type=int)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--archive-size-bytes", required=True, type=int)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def _require_result(value: object, stdout_limit: int) -> tuple[int, bytes, bytes]:
    if (
        not isinstance(value, tuple) or len(value) != 3 or type(value[0]) is not int
        or not isinstance(value[1], bytes) or not isinstance(value[2], bytes)
    ):
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    if value[0] != 0 or len(value[1]) > stdout_limit or len(value[2]) > MAX_STDERR_BYTES:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    return value


def _production_runner(
    *, environ: Mapping[str, str] = os.environ, run: SubprocessCall = _run_bounded_subprocess,
) -> Runner:
    """Build the only real runner: shell-free, bounded, and credential-minimal."""
    token = environ.get("GH_TOKEN")
    if not isinstance(token, str) or not token or any(character in token for character in ("\x00", "\r", "\n")):
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)

    def invoke(
        argv: tuple[str, ...], env: dict[str, str], timeout: int,
        stdout_limit: int, cwd: Path | None,
    ) -> tuple[int, bytes, bytes]:
        if (
            env != FIXED_ENV or not isinstance(argv, tuple) or not argv
            or not all(isinstance(value, str) and value and "\x00" not in value for value in argv)
            or not Path(argv[0]).is_absolute()
            or type(timeout) is not int or not 1 <= timeout <= TRANSPORT_TIMEOUT_SECONDS
            or type(stdout_limit) is not int or not 0 <= stdout_limit <= capture_library.MAX_ARCHIVE_BYTES
            or cwd is None or not isinstance(cwd, Path) or not cwd.is_absolute() or not cwd.is_dir()
        ):
            raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
        child_env = dict(FIXED_ENV)
        child_env.update({"GH_PROMPT_DISABLED": "1", "GH_TOKEN": token})
        try:
            process = run(
                argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, env=child_env, timeout=timeout,
                shell=False, stdout_limit=stdout_limit, stderr_limit=MAX_STDERR_BYTES,
            )
            result = (process.returncode, process.stdout, process.stderr)
        except (AttributeError, OSError, subprocess.TimeoutExpired, TypeError, ValueError) as error:
            raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID) from error
        return _require_result(result, stdout_limit)

    return invoke


def _invoke(
    runner: Runner, argv: tuple[str, ...], stdout_limit: int, *, cwd: Path | None = None,
) -> bytes:
    try:
        _return_code, stdout, _stderr = _require_result(
            runner(argv, dict(FIXED_ENV), TRANSPORT_TIMEOUT_SECONDS, stdout_limit, cwd), stdout_limit,
        )
    except capture_library.A0XHostedCaptureError:
        raise
    except Exception as error:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID) from error
    return stdout


def _pinned_cli(path: Path) -> capture_library.PinnedGitHubCLI:
    """Bind only the script's exact frozen identity to the public library API."""
    capture_library.GH_VERSION = GH_VERSION
    capture_library.GH_SHA256 = GH_SHA256
    return capture_library.PinnedGitHubCLI.from_path(path)


def _checked_transport_call(
    pinned: capture_library.PinnedGitHubCLI, runner: Runner, command: tuple[str, ...], stdout_limit: int,
    *, cwd: Path | None = None,
) -> bytes:
    """Rehash and recheck exact CLI version immediately before one transport call."""
    fresh = _pinned_cli(pinned.path)
    if fresh.path != pinned.path or fresh.raw_sha256 != pinned.raw_sha256:
        raise capture_library.A0XHostedCaptureError(capture_library.PIN_INVALID)
    version = _invoke(runner, (str(pinned.path), "--version"), MAX_VERSION_STDOUT_BYTES, cwd=cwd)
    capture_library.revalidate_pinned_cli(pinned, pinned.path, version)
    return _invoke(runner, command, stdout_limit, cwd=cwd)


def _validate_cli_help_contract(
    pinned: capture_library.PinnedGitHubCLI, runner: Runner, *, cwd: Path,
) -> None:
    """Refuse before transport unless the exact CLI exposes the frozen 2.97.0 shapes."""
    for command, markers in (
        ((str(pinned.path), "attestation", "download", "--help"), DOWNLOAD_HELP_MARKERS),
        ((str(pinned.path), "attestation", "trusted-root", "--help"), TRUSTED_ROOT_HELP_MARKERS),
    ):
        raw = _checked_transport_call(
            pinned, runner, command, MAX_HELP_STDOUT_BYTES, cwd=cwd,
        )
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as error:
            raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID) from error
        if not all(marker in text for marker in markers):
            raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)


def capture(
    arguments: argparse.Namespace,
    *,
    runner: Runner,
    publish_at: capture_library.PublishExclusiveAt | None = None,
    supported_host: Callable[[], bool] = lambda: sys.platform == "darwin",
) -> Path:
    """Perform one capture transaction through the caller-selected runner."""
    if not supported_host():
        raise capture_library.A0XHostedCaptureError(capture_library.PUBLICATION_UNSUPPORTED)
    pinned = _pinned_cli(arguments.gh_path)
    bootstrap = capture_library.CaptureBootstrapRequest.from_mapping({
        "repository": arguments.repository,
        "source_head": arguments.source_head,
        "source_tree": arguments.source_tree,
        "run_id": arguments.run_id,
        "run_attempt": arguments.run_attempt,
        "artifact_id": arguments.artifact_id,
        "artifact_name": arguments.artifact_name,
        "archive_sha256": arguments.archive_sha256,
        "archive_size_bytes": arguments.archive_size_bytes,
        "expires_at": arguments.expires_at,
        "output_root": arguments.output_root,
    })
    transport = capture_library.CaptureTransport.from_mapping({
        "artifact_id": bootstrap.artifact_id,
        "run_id": bootstrap.run_id,
        "run_attempt": bootstrap.run_attempt,
        "head_sha": bootstrap.source_head,
        "archive_digest": f"sha256:{bootstrap.archive_sha256}",
        "archive_size_bytes": bootstrap.archive_size_bytes,
        "created_at": arguments.created_at,
        "expires_at": bootstrap.expires_at,
        "captured_at": arguments.captured_at,
    })
    if len(transport.as_document()) > capture_library.MAX_TRANSPORT_BYTES:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    with TemporaryDirectory(prefix="a0x-hosted-capture-") as temporary:
        work = Path(temporary).resolve()
        _validate_cli_help_contract(pinned, runner, cwd=work)
        archive = _checked_transport_call(
            pinned, runner,
            (str(pinned.path), "api", "--method", "GET", f"/repos/{bootstrap.repository}/actions/artifacts/{bootstrap.artifact_id}/zip"),
            bootstrap.archive_size_bytes, cwd=work,
        )
        archive_path = work / "archive.zip"
        _write_private_regular(archive_path, archive)
        manifest = capture_library.derive_verified_manifest(bootstrap, archive_path)
        manifest_sha256 = hashlib.sha256(manifest).hexdigest()
        request = capture_library.CaptureRequest.from_bootstrap(bootstrap, manifest_sha256)
        subject_path = work / capture_library.MANIFEST_NAME
        _write_private_regular(subject_path, manifest)
        expected_bundle = work / f"sha256:{manifest_sha256}.jsonl"
        _checked_transport_call(
            pinned, runner,
            (
                str(pinned.path), "attestation", "download", str(subject_path),
                "--repo", request.repository, "--predicate-type",
                "https://slsa.dev/provenance/v1", "--limit", "30",
            ),
            capture_library.MAX_TRANSPORT_BYTES, cwd=work,
        )
        bundle = capture_library.read_regular_file(
            expected_bundle, capture_library.CAPTURE_INVALID, capture_library.MAX_BUNDLE_BYTES,
        )
        trusted_root = _checked_transport_call(
            pinned, runner, (str(pinned.path), "attestation", "trusted-root"),
            capture_library.MAX_TRUSTED_ROOT_BYTES, cwd=work,
        )
        return capture_library.capture_hosted_gate_a(
            request, transport, archive_path, bundle, trusted_root, publish_at=publish_at,
        )


def main(
    argv: list[str] | None = None,
    *,
    runner: Runner | None = None,
    publish_at: capture_library.PublishExclusiveAt | None = None,
    supported_host: Callable[[], bool] = lambda: sys.platform == "darwin",
) -> int:
    arguments = _parser().parse_args(argv)
    selected_runner = _production_runner() if runner is None else runner
    capture(
        arguments, runner=selected_runner, publish_at=publish_at,
        supported_host=supported_host,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except capture_library.A0XHostedCaptureError as error:
        print(error.code, file=sys.stderr)
        raise SystemExit(2)
