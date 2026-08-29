#!/usr/bin/env python3
"""Launch exactly one frozen A0X dossier through the shell-free CCP guard."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, launch_fixed_dossier


def _source_head() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=str(ROOT), check=False,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        raise A0XCcpExecutorError("repository source HEAD is unavailable")
    return completed.stdout.decode("ascii", "strict").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-dossier", required=True)
    args = parser.parse_args(argv)
    try:
        result = launch_fixed_dossier(
            repository_root=ROOT,
            fixed_dossier=args.fixed_dossier,
            source_head_probe=_source_head,
        )
    except A0XCcpExecutorError as error:
        print(f"a0x-material: {error}", file=sys.stderr)
        return 2
    print(result["terminal_observation_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
