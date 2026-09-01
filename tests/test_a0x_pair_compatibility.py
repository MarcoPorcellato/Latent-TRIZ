from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from latent_triz.a0x_compatibility import (
    CompatibilityOracleError,
    check_frozen_pair_compatibility,
    discover_frozen_dossier_paths,
)


ROOT = Path(__file__).resolve().parents[1]


def _repository_snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append((path.relative_to(root).as_posix(), digest))
    return tuple(entries)


def _copy_oracle_tree(destination: Path) -> None:
    dossier_root = ROOT / "experiments/a0x-six-model/approval-dossiers"
    shutil.copytree(dossier_root, destination / "experiments/a0x-six-model/approval-dossiers")
    for relative in (
        "scripts/a0x_compatibility_check.py",
        "src/latent_triz/__init__.py",
        "src/latent_triz/a0x_compatibility.py",
        "src/latent_triz/validator.py",
        "schemas/a0x-gate-b-authorization.schema.json",
        "schemas/a0x-hosted-gate-a-verification-receipt.schema.json",
        "tests/fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json",
        "tests/fixtures/a0x/hosted-gate-a/positive/verification-receipt.json",
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def _remove_bytecode_caches(root: Path) -> None:
    for cache in sorted(root.rglob("__pycache__"), reverse=True):
        shutil.rmtree(cache)


class A0XPairCompatibilityTests(unittest.TestCase):
    def test_all_real_dossiers_cross_both_hosted_boundaries(self) -> None:
        report = check_frozen_pair_compatibility(ROOT)
        self.assertEqual(24, report.expected_case_count)
        self.assertEqual(24, report.passed_case_count)
        self.assertEqual((), report.failures)

    def test_oracle_is_repeatable_and_writes_no_repository_files(self) -> None:
        before = _repository_snapshot(ROOT)
        first = check_frozen_pair_compatibility(ROOT)
        second = check_frozen_pair_compatibility(ROOT)
        after = _repository_snapshot(ROOT)

        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_exactly_six_tracked_models_exist_for_each_leg(self) -> None:
        paths = discover_frozen_dossier_paths(ROOT)
        self.assertEqual(12, len(paths))
        by_leg = {leg: [path for path in paths if f"/{leg}/" in path.as_posix()] for leg in ("a0", "r1")}
        self.assertEqual(6, len(by_leg["a0"]))
        self.assertEqual(6, len(by_leg["r1"]))

    def test_missing_extra_and_duplicate_dossiers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_oracle_tree(root)
            missing = root / "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"
            missing.unlink()
            with self.assertRaisesRegex(CompatibilityOracleError, "missing"):
                check_frozen_pair_compatibility(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_oracle_tree(root)
            dossiers = root / "experiments/a0x-six-model/approval-dossiers/a0"
            shutil.copy2(dossiers / "gpt2.json", dossiers / "unexpected.json")
            with self.assertRaisesRegex(CompatibilityOracleError, "unexpected"):
                check_frozen_pair_compatibility(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_oracle_tree(root)
            duplicate = root / "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"
            payload = json.loads(duplicate.read_text(encoding="utf-8"))
            payload["pair_binding"]["model_key"] = "gpt_neo_125m"
            duplicate.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CompatibilityOracleError, "duplicate"):
                check_frozen_pair_compatibility(root)

    def test_cli_rejects_malformed_copied_input_without_bytecode_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _copy_oracle_tree(root)
            dossier = root / "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"
            payload = json.loads(dossier.read_text(encoding="utf-8"))
            payload["pair_binding"]["output_path"] = "not-a-results-path"
            dossier.write_text(json.dumps(payload), encoding="utf-8")
            _remove_bytecode_caches(root)
            before = _repository_snapshot(root)
            environment = dict(os.environ)
            environment.pop("PYTHONDONTWRITEBYTECODE", None)
            completed = subprocess.run(
                [sys.executable, str(root / "scripts/a0x_compatibility_check.py"), "--root", str(root)],
                cwd=root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            after = _repository_snapshot(root)

            self.assertEqual(1, completed.returncode)
            self.assertIn("failures", completed.stdout)
            self.assertEqual(before, after)
            self.assertFalse((root / "src/latent_triz/__pycache__").exists())

    def test_cli_exit_code_matches_real_root_report(self) -> None:
        report = check_frozen_pair_compatibility(ROOT)
        environment = dict(os.environ)
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        completed = subprocess.run(
            [sys.executable, "scripts/a0x_compatibility_check.py", "--root", str(ROOT)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

        if report.passed_case_count == report.expected_case_count:
            self.assertEqual(0, completed.returncode)
        else:
            self.assertEqual(1, completed.returncode)
        self.assertIn(
            f"{report.expected_case_count} expected; {report.passed_case_count} passed; {len(report.failures)} failures",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()
