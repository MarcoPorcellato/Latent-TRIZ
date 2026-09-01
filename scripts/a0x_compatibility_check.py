#!/usr/bin/env python3
"""Run A0X frozen-pair compatibility oracle without writing repository state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from latent_triz.a0x_compatibility import CompatibilityOracleError, check_frozen_pair_compatibility


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args(argv)
    try:
        report = check_frozen_pair_compatibility(arguments.root)
    except CompatibilityOracleError as error:
        print(f"a0x-compatibility-check: FAIL: {error}")
        return 2

    print(
        "a0x-compatibility-check: "
        f"{report.expected_case_count} expected; {report.passed_case_count} passed; {len(report.failures)} failures"
    )
    for failure in report.failures:
        print(
            f"{failure.dossier_path}: {failure.consumer_schema}: "
            f"{failure.issue_path}: {failure.message}"
        )
    return 0 if report.passed_case_count == report.expected_case_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
