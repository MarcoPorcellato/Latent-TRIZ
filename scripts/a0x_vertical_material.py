#!/usr/bin/env python3
"""Launch one selector-derived A0X vertical dossier through the CCP guard."""
from __future__ import annotations

import argparse
import hashlib
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_ccp_executor import (
    A0XCcpExecutorError,
    launch_vertical_runtime_package,
    launch_vertical_slice_dossier,
)
from latent_triz.a0x_runtime_bundle import vertical_package_binding_from_commitment


def _source_head() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=str(ROOT), check=False,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
        },
    )
    if completed.returncode != 0:
        raise A0XCcpExecutorError("repository source HEAD is unavailable")
    return completed.stdout.decode("ascii", "strict").strip()


_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def _external_raw_sha256(relative: str, *, expected: str, label: str) -> None:
    """Bind a v2 external raw file before JSON parsing or path selection."""
    if not isinstance(relative, str) or not isinstance(expected, str) or _SHA256.fullmatch(expected) is None:
        raise A0XCcpExecutorError(f"{label} external raw binding is invalid")
    parts = Path(relative).parts
    if Path(relative).is_absolute() or not parts or any(part in {"", ".", ".."} for part in parts):
        raise A0XCcpExecutorError(f"{label} external raw path is invalid")
    candidate = ROOT.resolve(strict=True)
    for part in parts:
        candidate = candidate / part
        try:
            metadata = candidate.lstat()
        except OSError as error:
            raise A0XCcpExecutorError(f"{label} external raw file is unavailable") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise A0XCcpExecutorError(f"{label} external raw path contains a symlink")
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise A0XCcpExecutorError(f"{label} external raw file is not independent")
    observed = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if observed != expected:
        raise A0XCcpExecutorError(f"{label} external raw SHA-256 differs")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    historical = commands.add_parser("historical-v1")
    historical.add_argument("--implementation-source-head", required=True)
    historical.add_argument("--leg", required=True)
    historical.add_argument("--model-key", required=True)
    vertical = commands.add_parser("vertical-v2")
    vertical.add_argument("--vertical-commitment", required=True)
    vertical.add_argument("--vertical-commitment-raw-sha256", required=True)
    vertical.add_argument("--execution-authorization", required=True)
    vertical.add_argument("--execution-authorization-raw-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "vertical-v2":
            _external_raw_sha256(
                args.vertical_commitment,
                expected=args.vertical_commitment_raw_sha256,
                label="vertical commitment",
            )
            _external_raw_sha256(
                args.execution_authorization,
                expected=args.execution_authorization_raw_sha256,
                label="vertical execution authorization",
            )
            binding = vertical_package_binding_from_commitment(ROOT, args.vertical_commitment)
            result = launch_vertical_runtime_package(
                repository_root=ROOT, package_binding=binding,
                execution_authorization_path=args.execution_authorization,
            )
        else:
            result = launch_vertical_slice_dossier(
                repository_root=ROOT,
                implementation_source_head=args.implementation_source_head,
                leg=args.leg,
                model_key=args.model_key,
                source_head_probe=_source_head,
            )
    except A0XCcpExecutorError as error:
        print(f"a0x-vertical-material: {error}", file=sys.stderr)
        return 2
    print(result.get("terminal_observation_path", result["status"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
