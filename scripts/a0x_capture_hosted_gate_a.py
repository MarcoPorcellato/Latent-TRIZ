#!/usr/bin/env python3
"""Capture A0X Hosted Gate A only through an injected, shell-free transport."""

from __future__ import annotations

import argparse
import os
import sys
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
Runner = Callable[[tuple[str, ...], dict[str, str]], tuple[int, bytes, bytes]]


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
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def _require_result(value: object) -> tuple[int, bytes, bytes]:
    if (
        not isinstance(value, tuple) or len(value) != 3 or type(value[0]) is not int
        or not isinstance(value[1], bytes) or not isinstance(value[2], bytes)
    ):
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    if value[0] != 0:
        raise capture_library.A0XHostedCaptureError(capture_library.CAPTURE_INVALID)
    return value


def _invoke(runner: Runner, argv: tuple[str, ...]) -> bytes:
    try:
        _return_code, stdout, _stderr = _require_result(runner(argv, dict(FIXED_ENV)))
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
    pinned: capture_library.PinnedGitHubCLI, runner: Runner, command: tuple[str, ...],
) -> bytes:
    """Rehash and recheck exact CLI version immediately before one transport call."""
    fresh = _pinned_cli(pinned.path)
    if fresh.path != pinned.path or fresh.raw_sha256 != pinned.raw_sha256:
        raise capture_library.A0XHostedCaptureError(capture_library.PIN_INVALID)
    version = _invoke(runner, (str(pinned.path), "--version"))
    capture_library.revalidate_pinned_cli(pinned, pinned.path, version)
    return _invoke(runner, command)


def capture(
    arguments: argparse.Namespace,
    *,
    runner: Runner,
    publish_at: capture_library.PublishExclusiveAt | None = None,
    supported_host: Callable[[], bool] = lambda: sys.platform == "darwin",
) -> Path:
    """Perform one entirely injected capture transaction; never starts a real subprocess."""
    if not supported_host():
        raise capture_library.A0XHostedCaptureError(capture_library.PUBLICATION_UNSUPPORTED)
    pinned = _pinned_cli(arguments.gh_path)
    request = capture_library.CaptureRequest.from_mapping({
        "repository": arguments.repository,
        "source_head": arguments.source_head,
        "source_tree": arguments.source_tree,
        "run_id": arguments.run_id,
        "run_attempt": arguments.run_attempt,
        "artifact_id": arguments.artifact_id,
        "artifact_name": arguments.artifact_name,
        "archive_sha256": arguments.archive_sha256,
        "archive_size_bytes": arguments.archive_size_bytes,
        "manifest_sha256": arguments.manifest_sha256,
        "expires_at": arguments.expires_at,
        "output_root": arguments.output_root,
    })
    transport = capture_library.CaptureTransport.from_mapping({
        "artifact_id": request.artifact_id,
        "run_id": request.run_id,
        "run_attempt": request.run_attempt,
        "head_sha": request.source_head,
        "archive_digest": f"sha256:{request.archive_sha256}",
        "archive_size_bytes": request.archive_size_bytes,
        "created_at": arguments.created_at,
        "expires_at": request.expires_at,
        "captured_at": arguments.captured_at,
    })
    archive = _checked_transport_call(
        pinned, runner,
        (str(pinned.path), "api", "--method", "GET", f"/repos/{request.repository}/actions/artifacts/{request.artifact_id}/zip"),
    )
    bundle = _checked_transport_call(
        pinned, runner,
        (str(pinned.path), "attestation", "download", "--repo", request.repository, "--digest", f"sha256:{request.manifest_sha256}"),
    )
    trusted_root = _checked_transport_call(pinned, runner, (str(pinned.path), "attestation", "trusted-root"))
    with TemporaryDirectory(prefix="a0x-hosted-capture-") as temporary:
        archive_path = Path(temporary) / "archive.zip"
        archive_path.write_bytes(archive)
        return capture_library.capture_hosted_gate_a(
            request, transport, archive_path, bundle, trusted_root, publish_at=publish_at,
        )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    raise capture_library.A0XHostedCaptureError(capture_library.PUBLICATION_UNSUPPORTED)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except capture_library.A0XHostedCaptureError as error:
        print(error.code, file=sys.stderr)
        raise SystemExit(2)
