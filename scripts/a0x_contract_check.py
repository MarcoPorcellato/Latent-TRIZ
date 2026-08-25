#!/usr/bin/env python3
"""Run only the A0X synthetic implementation verification phase."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_runner import (  # noqa: E402
    A0XRunnerError,
    verify_a0x_implementation,
    verify_a0x_no_model,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True, choices=("synthetic", "frozen"))
    args = parser.parse_args(argv)
    try:
        receipt = verify_a0x_implementation(ROOT) if args.phase == "synthetic" else verify_a0x_no_model(ROOT)
    except A0XRunnerError as error:
        print(f"a0x-contract-check: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
