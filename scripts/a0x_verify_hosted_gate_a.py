#!/usr/bin/env python3
"""Offline wrapper for one exact, hash-bound Hosted Gate A verification."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import subprocess
import sys
from typing import TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
_CHILD_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}
_GIT = "/usr/bin/git"
_VERIFIER_TIMEOUT_SECONDS = 300
_GIT_TIMEOUT_SECONDS = 30

from latent_triz.a0x_hosted_verifier import (
    A0XHostedVerifierError,
    GateBVerificationRequest,
    SourceStateProbe,
    VerifierRunner,
    verify_hosted_gate_a,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--verifier", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    return parser


def _runner(argv: Sequence[str], cwd: Path) -> tuple[int, bytes, bytes]:
    """Execute only verifier-provided argv with a fixed non-networking environment."""
    try:
        process = subprocess.run(
            tuple(argv), cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, env=dict(_CHILD_ENV), timeout=_VERIFIER_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise A0XHostedVerifierError("A0X_GATE_B_ATTESTATION_REFUSED") from error
    return process.returncode, process.stdout, process.stderr


def _source_state(root: Path) -> tuple[str, str, bool]:
    """Read exact local HEAD/tree and reject a dirty or inaccessible checkout."""
    def capture(*argv: str) -> bytes:
        try:
            process = subprocess.run(
                argv, cwd=root, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, env=dict(_CHILD_ENV), timeout=_GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise A0XHostedVerifierError("A0X_GATE_B_SOURCE_DRIFT") from error
        if process.returncode != 0:
            raise A0XHostedVerifierError("A0X_GATE_B_SOURCE_DRIFT")
        return process.stdout

    head = capture(_GIT, "rev-parse", "HEAD").decode("ascii", "strict").strip()
    tree = capture(_GIT, "rev-parse", "HEAD^{tree}").decode("ascii", "strict").strip()
    clean = capture(_GIT, "status", "--porcelain=v1", "--untracked-files=all") == b""
    return head, tree, clean


def main(
    argv: list[str] | None = None,
    *,
    stderr: TextIO | None = None,
    runner: VerifierRunner = _runner,
    source_state_probe: SourceStateProbe = _source_state,
) -> int:
    args = _parser().parse_args(argv)
    stream = sys.stderr if stderr is None else stderr
    try:
        verify_hosted_gate_a(
            GateBVerificationRequest(args.repository_root, args.authorization, args.verifier, args.policy),
            runner=runner, source_state_probe=source_state_probe,
        )
    except A0XHostedVerifierError as error:
        print(error.code, file=stream)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
