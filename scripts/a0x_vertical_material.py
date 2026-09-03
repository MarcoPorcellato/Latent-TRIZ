#!/usr/bin/env python3
"""Launch one selector-derived A0X vertical dossier through the CCP guard."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, launch_vertical_slice_dossier


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-source-head", required=True)
    parser.add_argument("--leg", required=True)
    parser.add_argument("--model-key", required=True)
    args = parser.parse_args(argv)
    try:
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
    print(result["terminal_observation_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
