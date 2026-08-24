#!/usr/bin/env python3
"""Fixed-dossier A0X material entrypoint; unavailable until Task 11 freezes it."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-dossier", required=True)
    args = parser.parse_args(argv)
    dossier = Path(args.fixed_dossier)
    if dossier.is_absolute() or ".." in dossier.parts:
        print("a0x-material: dossier path is not a fixed repository-relative path", file=sys.stderr)
        return 2
    if not (ROOT / dossier).is_file():
        print("a0x-material: planned Task-11 dossier is absent; refusing before CCP or model access", file=sys.stderr)
        return 2
    print("a0x-material: Task-11 material bindings are not available; refusing before CCP or model access", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
