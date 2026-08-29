#!/usr/bin/env python3
"""Prepare one A0X runtime bundle without invoking a material workload."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence, TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_runtime_bundle import (  # noqa: E402
    A0XRuntimeBundleError,
    RuntimePreparationRequest,
    prepare_runtime_bundle,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-dossier", required=True)
    parser.add_argument("--qualification-receipt", required=True)
    parser.add_argument("--ccp", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--public-evidence-commit", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    return parser


def _probe(argv: Sequence[str], root: Path) -> str:
    result = subprocess.run(
        list(argv), cwd=str(root), shell=False, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise A0XRuntimeBundleError("runtime preparation probe refused")
    return result.stdout


def main(
    argv: Sequence[str] | None = None,
    *,
    root: Path | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run the three shell-free probes and emit one sorted public receipt."""
    arguments = _parser().parse_args(argv)
    repository = (ROOT if root is None else Path(root)).resolve(strict=True)
    stream = sys.stdout if stdout is None else stdout
    request = RuntimePreparationRequest(
        fixed_dossier=arguments.fixed_dossier,
        qualification_receipt=Path(arguments.qualification_receipt),
        ccp_executable=Path(arguments.ccp),
        python_executable=Path(arguments.python),
        public_evidence_commit=arguments.public_evidence_commit,
        authorization_id=arguments.authorization_id,
        attempt_id=arguments.attempt_id,
    )

    def source_state_probe() -> tuple[str, bool]:
        head = _probe(("git", "rev-parse", "HEAD"), repository).strip()
        status = _probe(("git", "status", "--porcelain", "--untracked-files=all"), repository)
        return head, status == ""

    def ccp_version_probe(path: Path) -> str:
        return _probe((str(path), "--version"), repository).strip()

    try:
        receipt = prepare_runtime_bundle(
            repository,
            request,
            source_state_probe=source_state_probe,
            ccp_version_probe=ccp_version_probe,
        )
    except (A0XRuntimeBundleError, OSError, ValueError, subprocess.SubprocessError):
        print(json.dumps({"status": "refused"}, sort_keys=True, separators=(",", ":")), file=stream)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")), file=stream)
    return 0


if __name__ == "__main__":  # pragma: no cover - direct CLI boundary
    raise SystemExit(main())
