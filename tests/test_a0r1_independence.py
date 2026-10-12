from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0r1_independence import run_a0r1_independence_audit


class A0R1IndependenceTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def setUp(self) -> None:
        self.workdir = Path(tempfile.mkdtemp())
        self.candidate_manifest_path = self.workdir / "candidate_protocol.json"
        self.source_manifest_path = self.workdir / "source_protocol.json"
        self.case_candidate_path = self.workdir / "candidate_cases.jsonl"
        self.targets_candidate_calibration_path = self.workdir / "candidate_targets_calibration.jsonl"
        self.targets_candidate_sealed_path = self.workdir / "candidate_targets_sealed.jsonl"
        self.case_source_path = self.workdir / "source_cases.jsonl"
        self.targets_source_calibration_path = self.workdir / "source_targets_calibration.jsonl"
        self.targets_source_sealed_path = self.workdir / "source_targets_sealed.jsonl"

        candidate_payload = {
            "protocol_id": "a0-r1-tier-r1-v1.0.0",
            "deterministic_seed": 20260815,
            "partitions": {
                "calibration_split": "calibration",
                "sealed_split": "sealed",
                "split_field": "split",
            },
        }
        source_payload = {
            "protocol_id": "a0-r1-tier-r1-v1.0.0-source",
            "seed": 20260814,
            "partitions": {
                "calibration_split": "calibration",
                "sealed_split": "sealed",
                "split_field": "split",
            },
        }
        self.candidate_manifest_path.write_text(json.dumps(candidate_payload, indent=2), encoding="utf-8")
        self.source_manifest_path.write_text(json.dumps(source_payload, indent=2), encoding="utf-8")

    def _set_candidate_seed(self, value: int) -> None:
        payload = json.loads(self.candidate_manifest_path.read_text(encoding="utf-8"))
        payload["deterministic_seed"] = value
        self.candidate_manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _set_source_seed(self, value: int) -> None:
        payload = json.loads(self.source_manifest_path.read_text(encoding="utf-8"))
        payload["seed"] = value
        self.source_manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_cases(self, path: Path, records: list[dict]) -> None:
        lines = [json.dumps(item) for item in records]
        data = "\n".join(lines)
        if data:
            data += "\n"
        path.write_text(data, encoding="utf-8")

    def _base_case(self, case_id: str, family_id: str, template_id: str, problem: str) -> dict:
        return {
            "case_id": case_id,
            "problem_family_id": family_id,
            "provenance": {"template_id": template_id},
            "problem": problem,
            "constraints": ["budget"],
            "initial_state": "baseline machine state",
            "desired_improvement": "improved speed",
            "worsening_consequence": "waste",
            "transformation": "adjust flow",
            "resulting_state": "steady operation",
        }

    def _base_target(self, case_id: str, split: str, text: str) -> dict:
        return {"case_id": case_id, "split": split, "target_text": text}

    def _run_audit(
        self,
        candidate_cases: list[dict],
        candidate_calibration_targets: list[dict],
        candidate_sealed_targets: list[dict],
        source_cases: list[dict],
        source_calibration_targets: list[dict],
        source_sealed_targets: list[dict],
    ):
        self._write_cases(self.case_candidate_path, candidate_cases)
        self._write_cases(self.targets_candidate_calibration_path, candidate_calibration_targets)
        self._write_cases(self.targets_candidate_sealed_path, candidate_sealed_targets)
        self._write_cases(self.case_source_path, source_cases)
        self._write_cases(self.targets_source_calibration_path, source_calibration_targets)
        self._write_cases(self.targets_source_sealed_path, source_sealed_targets)

        return run_a0r1_independence_audit(
            candidate_manifest_path=self.candidate_manifest_path,
            candidate_cases_path=self.case_candidate_path,
            candidate_calibration_targets_path=self.targets_candidate_calibration_path,
            candidate_sealed_targets_path=self.targets_candidate_sealed_path,
            source_manifest_path=self.source_manifest_path,
            source_cases_path=self.case_source_path,
            source_calibration_targets_path=self.targets_source_calibration_path,
            source_sealed_targets_path=self.targets_source_sealed_path,
        )

    def test_audit_pass_with_separate_partitions_and_no_reuse(self) -> None:
        candidate_cases = [
            self._base_case("r1_a", "fam_a", "tpl_a", "A machine slows on peak load."),
            self._base_case("r1_b", "fam_b", "tpl_b", "A pump pulses irregularly."),
        ]
        source_cases = [
            self._base_case("a0_a", "a0fam_a", "a0tpl_a", "The machine is cold."),
            self._base_case("a0_b", "a0fam_b", "a0tpl_b", "The filter blocks airflow."),
        ]
        report = self._run_audit(
            candidate_cases,
            [self._base_target("r1_a", "calibration", "expected output for calibration")],
            [self._base_target("r1_b", "sealed", "expected output for sealed")],
            source_cases,
            [self._base_target("a0_a", "calibration", "A source calibration target")],
            [self._base_target("a0_b", "sealed", "A source sealed target")],
        )

        self.assertEqual("pass", report["status"])
        self.assertEqual([], report["violations"])
        self.assertTrue(report["ready"])
        self.assertIn("candidate_manifest_sha256", report["hashes"])

    def test_published_a0_manifest_and_nested_template_contract_are_supported(self) -> None:
        candidate_cases = [
            self._base_case("r1_a", "r1fam_a", "r1tpl_a", "A cryogenic valve chatters during lunar sampling."),
            self._base_case("r1_b", "r1fam_b", "r1tpl_b", "A ceramic rotor drifts during vacuum inspection."),
        ]
        self._write_cases(self.case_candidate_path, candidate_cases)
        self._write_cases(
            self.targets_candidate_calibration_path,
            [self._base_target("r1_a", "calibration", "candidate calibration target")],
        )
        self._write_cases(
            self.targets_candidate_sealed_path,
            [self._base_target("r1_b", "sealed", "candidate sealed target")],
        )

        source_manifest_path = self.ROOT / "data/a0/manifest.json"
        source_cases_path = self.ROOT / "data/a0/cases.jsonl"
        source_calibration_targets_path = self.targets_source_calibration_path
        repository_sealed_path = (
            self.ROOT / "data/a0/sealed-targets/targets.jsonl"
        ).resolve()

        # Manifest/template compatibility uses public cases. Both sets of target
        # rows are synthetic, never read from either protected target file.
        source_cases = [
            json.loads(line)
            for line in source_cases_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        synthetic_source_sealed_targets = [
            self._base_target(case["case_id"], "sealed", f"synthetic sealed target {index}")
            for index, case in enumerate(source_cases, start=1)
            if case.get("split") == "sealed"
        ]
        self._write_cases(source_calibration_targets_path, [
            self._base_target(case["case_id"], "calibration", f"synthetic calibration target {index}")
            for index, case in enumerate(source_cases, start=1)
            if case.get("split") == "calibration"
        ])
        self._write_cases(self.targets_source_sealed_path, synthetic_source_sealed_targets)
        self.assertTrue(self.targets_source_sealed_path.is_relative_to(self.workdir))

        original_open = Path.open
        original_read_text = Path.read_text
        original_read_bytes = Path.read_bytes

        def reject_repository_sealed_open(path: Path, *args, **kwargs):
            if path.resolve() == repository_sealed_path:
                raise AssertionError("repository sealed-target path must not be opened")
            return original_open(path, *args, **kwargs)

        def reject_repository_sealed_read_text(path: Path, *args, **kwargs):
            if path.resolve() == repository_sealed_path:
                raise AssertionError("repository sealed-target path must not be read")
            return original_read_text(path, *args, **kwargs)

        def reject_repository_sealed_read_bytes(path: Path, *args, **kwargs):
            if path.resolve() == repository_sealed_path:
                raise AssertionError("repository sealed-target path must not be read")
            return original_read_bytes(path, *args, **kwargs)

        with (
            patch.object(Path, "open", new=reject_repository_sealed_open),
            patch.object(Path, "read_text", new=reject_repository_sealed_read_text),
            patch.object(Path, "read_bytes", new=reject_repository_sealed_read_bytes),
        ):
            # Prove the guard rejects the prohibited path before any OS open.
            with self.assertRaisesRegex(AssertionError, "must not be opened"):
                repository_sealed_path.open("r", encoding="utf-8")

            report = run_a0r1_independence_audit(
                candidate_manifest_path=self.candidate_manifest_path,
                candidate_cases_path=self.case_candidate_path,
                candidate_calibration_targets_path=self.targets_candidate_calibration_path,
                candidate_sealed_targets_path=self.targets_candidate_sealed_path,
                source_manifest_path=source_manifest_path,
                source_cases_path=source_cases_path,
                source_calibration_targets_path=source_calibration_targets_path,
                source_sealed_targets_path=self.targets_source_sealed_path,
            )

        self.assertEqual("pass", report["status"])
        self.assertEqual([], report["violations"])
        self.assertTrue(report["ready"])

    def test_reused_case_family_template_and_seed_fail(self) -> None:
        candidate_cases = [self._base_case("a0_a", "a0fam_a", "a0tpl_a", "A machine slows on peak load.")]
        source_cases = [self._base_case("a0_a", "a0fam_a", "a0tpl_a", "The machine is cold.")]
        self._set_candidate_seed(42)
        self._set_source_seed(42)

        report = self._run_audit(
            candidate_cases,
            [self._base_target("a0_a", "calibration", "expected")],
            [],
            source_cases,
            [self._base_target("a0_a", "calibration", "expected")],
            [],
        )

        self.assertEqual("fail", report["status"])
        self.assertFalse(report["ready"])
        codes = {item["code"] for item in report["violations"]}
        self.assertIn("reused_case_id", codes)
        self.assertIn("reused_family_id", codes)
        self.assertIn("reused_template_id", codes)
        self.assertIn("reused_seed", codes)

    def test_partition_checks_fail_when_case_crosses_partitions(self) -> None:
        candidate_cases = [
            self._base_case("r1_a", "fam_a", "tpl_a", "A machine slows on peak load."),
            self._base_case("r1_b", "fam_b", "tpl_b", "A pump pulses irregularly."),
        ]
        source_cases = [
            self._base_case("a0_a", "a0fam_a", "a0tpl_a", "The machine is cold."),
            self._base_case("a0_b", "a0fam_b", "a0tpl_b", "The filter blocks airflow."),
        ]
        report = self._run_audit(
            candidate_cases,
            [
                self._base_target("r1_a", "calibration", "cal target"),
                self._base_target("r1_b", "calibration", "another cal target"),
            ],
            [self._base_target("r1_b", "sealed", "should trigger cross-partition")],
            source_cases,
            [self._base_target("a0_a", "calibration", "source cal")],
            [self._base_target("a0_b", "sealed", "source sealed")],
        )
        self.assertEqual("fail", report["status"])
        codes = {item["code"] for item in report["violations"]}
        self.assertIn("target_case_cross_partition", codes)

    def test_invalid_target_partition_value_is_caught(self) -> None:
        candidate_cases = [self._base_case("r1_a", "fam_a", "tpl_a", "A pump loses pressure.")]
        source_cases = [self._base_case("a0_a", "a0fam_a", "a0tpl_a", "The machine is cold.")]
        report = self._run_audit(
            candidate_cases,
            [self._base_target("r1_a", "validation", "wrong partition")],
            [],
            source_cases,
            [self._base_target("a0_a", "calibration", "source cal")],
            [],
        )
        self.assertEqual("fail", report["status"])
        codes = {item["code"] for item in report["violations"]}
        self.assertIn("invalid_target_partition", codes)

    def test_target_leakage_in_case_fields_is_caught(self) -> None:
        candidate_cases = [self._base_case("r1_a", "fam_a", "tpl_a", "A machine loses pressure.")]
        candidate_cases[0]["transformation"] = "Expected target from source with unique fingerprint for leak."
        source_cases = [self._base_case("a0_a", "a0fam_a", "a0tpl_a", "A source case baseline.")]
        report = self._run_audit(
            candidate_cases,
            [self._base_target("r1_a", "calibration", "expected")],
            [],
            source_cases,
            [
                self._base_target(
                    "a0_a", "sealed", "Expected target from source with unique fingerprint for leak."
                ),
                self._base_target("a0_a", "calibration", "other"),
            ],
            [],
        )
        self.assertIn("target_content_leakage", {item["code"] for item in report["violations"]})

    def test_exact_and_near_duplicate_text_detected(self) -> None:
        candidate_cases = [
            self._base_case("r1_a", "fam_a", "tpl_a", "A pump loses pressure under load."),
            self._base_case(
                "r1_b", "fam_b", "tpl_b", "A pump loses pressure under heavy load. It oscillates."
            ),
        ]
        source_cases = [
            self._base_case("a0_a", "a0fam_a", "a0tpl_a", "A pump loses pressure under load."),
            self._base_case("a0_b", "a0fam_b", "a0tpl_b", "Completely different source text."),
        ]
        report = self._run_audit(
            candidate_cases,
            [self._base_target("r1_a", "calibration", "expected")],
            [self._base_target("r1_b", "sealed", "expected")],
            source_cases,
            [self._base_target("a0_a", "calibration", "s target one")],
            [self._base_target("a0_b", "sealed", "s target two")],
        )
        codes = {item["code"] for item in report["violations"]}
        self.assertIn("exact_normalized_text_reused", codes)
        self.assertIn("near_duplicate_shingles", codes)


if __name__ == "__main__":
    unittest.main()
