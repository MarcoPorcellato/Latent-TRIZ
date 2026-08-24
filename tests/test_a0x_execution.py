from __future__ import annotations

import hashlib
import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from latent_triz.a0x_contract import Leg, sha256_file
from latent_triz.a0x_execution import A0XExecutionError
from tests.a0x_test_support import A0XTempTestCase, pair_binding, sha


def _rows(case_ids: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"case_id": case_id, "label": index} for index, case_id in enumerate(case_ids)]


def _jsonl(rows: list[dict[str, object]]) -> bytes:
    return b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for row in rows
    )


class A0XExecutionTests(A0XTempTestCase):
    def _reader(
        self,
        *,
        path: Path,
        expected_case_ids: tuple[str, ...],
        leg: Leg = Leg.A0,
        require_file_exact: bool = False,
        expected_sha256: str | None = None,
        receipt_path: Path | None = None,
    ):
        from latent_triz.a0x_execution import OneShotTargetReader

        return OneShotTargetReader(
            path=path,
            expected_sha256=expected_sha256 or sha256_file(path),
            expected_case_ids=expected_case_ids,
            require_file_exact=require_file_exact,
            receipt_path=receipt_path or self.temp_path / "target-read-receipt.json",
            pair_binding=pair_binding(leg),
            activation_receipt_sha256=sha(61),
            dense_sha256=sha(62),
            index_sha256=sha(63),
        )

    def test_analysis_reader_hashes_parses_and_persists_in_one_open(self) -> None:
        case_ids = tuple(f"case-{index:02d}" for index in range(48))
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(case_ids)))
        receipt_path = self.temp_path / "target-read-receipt.json"

        reader = self._reader(
            path=path, expected_case_ids=case_ids, receipt_path=receipt_path,
        )
        rows, receipt = reader.read_jsonl_once()

        self.assertEqual(_rows(case_ids), rows)
        self.assertEqual(1, receipt.content_reads)
        persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(1, persisted["content_reads"])
        self.assertEqual("pass", persisted["status"])
        self.assertEqual(sha256_file(path), persisted["observed_sha256"])
        with self.assertRaisesRegex(A0XExecutionError, "already consumed"):
            reader.read_jsonl_once()

    def test_post_open_hash_or_parse_failure_still_persists_one_read(self) -> None:
        cases = ("case-00",)
        payloads = (
            (b"bad-json\n", hashlib.sha256(b"bad-json\n").hexdigest(), "parse_failed"),
            (b"\xff\n", hashlib.sha256(b"\xff\n").hexdigest(), "parse_failed"),
            (_jsonl([{}]), "0" * 64, "hash_mismatch"),
        )
        for index, (payload, expected_hash, status) in enumerate(payloads):
            with self.subTest(status=status):
                path = self.temp_path / f"synthetic-{index}.jsonl"
                path.write_bytes(payload)
                receipt_path = self.temp_path / f"receipt-{index}.json"
                reader = self._reader(
                    path=path, expected_case_ids=cases, expected_sha256=expected_hash,
                    receipt_path=receipt_path,
                )
                with self.assertRaisesRegex(A0XExecutionError, "sealed target"):
                    reader.read_jsonl_once()
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(1, receipt["content_reads"])
                self.assertEqual(status, receipt["status"])

    def test_missing_target_persists_zero_read_receipt(self) -> None:
        missing = self.temp_path / "synthetic-missing.jsonl"
        receipt_path = self.temp_path / "missing-receipt.json"
        reader = self._reader(
            path=missing, expected_case_ids=("case-00",), receipt_path=receipt_path,
            expected_sha256=sha(44),
        )

        with self.assertRaisesRegex(A0XExecutionError, "sealed target read failed"):
            reader.read_jsonl_once()
        persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(0, persisted["content_reads"])
        self.assertEqual("read_failed", persisted["status"])

    def test_failed_read_after_open_persists_one_read_receipt(self) -> None:
        path = self.temp_path / "synthetic-read-failure.jsonl"
        path.write_bytes(_jsonl(_rows(("case-00",))))
        receipt_path = self.temp_path / "read-failure-receipt.json"
        reader = self._reader(
            path=path, expected_case_ids=("case-00",), receipt_path=receipt_path,
        )
        original_open = Path.open

        class BrokenStream:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self) -> bytes:
                raise OSError("synthetic stream failure")

        def open_for_target(candidate: Path, mode: str = "r", *args, **kwargs):
            if candidate == path and mode == "rb":
                return BrokenStream()
            return original_open(candidate, mode, *args, **kwargs)

        with patch.object(Path, "open", new=open_for_target):
            with self.assertRaisesRegex(A0XExecutionError, "sealed target read failed"):
                reader.read_jsonl_once()
        persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(1, persisted["content_reads"])
        self.assertEqual("read_failed", persisted["status"])
        self.assertIsNone(persisted["observed_sha256"])
        from latent_triz.a0x_execution import AttemptState, seal_terminal_attempt

        terminal = seal_terminal_attempt(
            state=AttemptState.ANALYSIS, status="failed", target_receipt_path=receipt_path,
        )
        self.assertEqual(1, terminal["analysis_target_content_reads"])

    def test_a0_selects_ordered_subset_and_rejects_selected_reorder_missing_or_duplicate(self) -> None:
        expected = ("case-b", "case-a")
        path = self.temp_path / "synthetic-a0.jsonl"
        path.write_bytes(_jsonl(_rows(("case-a", "case-b", "unselected"))))
        rows, _ = self._reader(path=path, expected_case_ids=expected).read_jsonl_once()
        self.assertEqual(["case-b", "case-a"], [row["case_id"] for row in rows])

        for name, source_ids in (
            ("missing", ("case-a",)),
            ("duplicate", ("case-a", "case-b", "case-b")),
        ):
            with self.subTest(name=name):
                target = self.temp_path / f"synthetic-a0-{name}.jsonl"
                target.write_bytes(_jsonl(_rows(source_ids)))
                receipt = self.temp_path / f"synthetic-a0-{name}-receipt.json"
                with self.assertRaisesRegex(A0XExecutionError, "selection"):
                    self._reader(
                        path=target, expected_case_ids=expected, receipt_path=receipt,
                    ).read_jsonl_once()
                self.assertEqual(
                    "selection_mismatch",
                    json.loads(receipt.read_text(encoding="utf-8"))["status"],
                )

    def test_r1_requires_complete_exact_ordered_selection(self) -> None:
        expected = ("case-a", "case-b")
        for name, source_ids in (
            ("extra", ("case-a", "case-b", "extra")),
            ("missing", ("case-a",)),
            ("reordered", ("case-b", "case-a")),
        ):
            with self.subTest(name=name):
                path = self.temp_path / f"synthetic-r1-{name}.jsonl"
                path.write_bytes(_jsonl(_rows(source_ids)))
                receipt = self.temp_path / f"synthetic-r1-{name}-receipt.json"
                with self.assertRaisesRegex(A0XExecutionError, "selection"):
                    self._reader(
                        path=path, expected_case_ids=expected, leg=Leg.R1,
                        require_file_exact=True, receipt_path=receipt,
                    ).read_jsonl_once()
                self.assertEqual(
                    "selection_mismatch",
                    json.loads(receipt.read_text(encoding="utf-8"))["status"],
                )

    def test_reader_requires_sealed_activation_and_dense_index_hash_bindings(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(("case-00",))))
        from latent_triz.a0x_execution import OneShotTargetReader

        kwargs = {
            "path": path,
            "expected_sha256": sha256_file(path),
            "expected_case_ids": ("case-00",),
            "require_file_exact": True,
            "receipt_path": self.temp_path / "receipt.json",
            "pair_binding": pair_binding(),
            "activation_receipt_sha256": sha(61),
            "dense_sha256": sha(62),
            "index_sha256": sha(63),
        }
        for field in ("activation_receipt_sha256", "dense_sha256", "index_sha256"):
            with self.subTest(field=field):
                invalid = dict(kwargs)
                invalid[field] = "not-a-hash"
                with self.assertRaisesRegex(A0XExecutionError, "sealed activation"):
                    OneShotTargetReader(**invalid)

    def test_r1_reader_refuses_non_exact_target_mode(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(("case-00",))))
        from latent_triz.a0x_execution import OneShotTargetReader

        with self.assertRaisesRegex(A0XExecutionError, "R1 target selection"):
            OneShotTargetReader(
                path=path,
                expected_sha256=sha256_file(path),
                expected_case_ids=("case-00",),
                require_file_exact=False,
                receipt_path=self.temp_path / "receipt.json",
                pair_binding=pair_binding(Leg.R1),
                activation_receipt_sha256=sha(61),
                dense_sha256=sha(62),
                index_sha256=sha(63),
            )

    def test_activation_interfaces_have_no_target_reader_or_generic_filesystem_capability(self) -> None:
        from latent_triz.a0x_a0_activations import extract_a0x_a0
        from latent_triz.a0x_r1_activations import extract_a0x_r1

        forbidden = {"targets_path", "target_reader", "filesystem", "target_path"}
        for callable_ in (extract_a0x_a0, extract_a0x_r1):
            with self.subTest(callable=callable_.__name__):
                self.assertFalse(forbidden.intersection(inspect.signature(callable_).parameters))

    def test_state_machine_refuses_backwards_transitions_and_terminal_retry(self) -> None:
        from latent_triz.a0x_execution import AttemptState, advance_attempt

        self.assertIs(AttemptState.ACTIVATION, advance_attempt(AttemptState.PREFLIGHT))
        self.assertIs(AttemptState.ANALYSIS, advance_attempt(AttemptState.ACTIVATION))
        self.assertIs(AttemptState.SEALED, advance_attempt(AttemptState.ANALYSIS))
        with self.assertRaisesRegex(A0XExecutionError, "sealed"):
            advance_attempt(AttemptState.SEALED)

    def test_terminal_requires_persisted_receipt_after_analysis_and_no_statistic_before_analysis(self) -> None:
        from latent_triz.a0x_execution import (
            AttemptState,
            seal_terminal_attempt,
        )

        terminal = seal_terminal_attempt(
            state=AttemptState.PREFLIGHT, status="incompatible", target_reads=0,
        )
        self.assertEqual(0, terminal["analysis_target_content_reads"])
        self.assertIsNone(terminal["statistical_result"])
        with self.assertRaisesRegex(A0XExecutionError, "persisted target-read receipt"):
            seal_terminal_attempt(
                state=AttemptState.ANALYSIS, status="failed", target_reads=1,
            )

    def test_terminal_refuses_statistic_after_read_error(self) -> None:
        from latent_triz.a0x_execution import AttemptState, seal_terminal_attempt

        path = self.temp_path / "synthetic-failure.jsonl"
        path.write_bytes(b"bad-json\n")
        receipt_path = self.temp_path / "failure-receipt.json"
        reader = self._reader(
            path=path,
            expected_case_ids=("case-00",),
            expected_sha256=sha256_file(path),
            receipt_path=receipt_path,
        )
        with self.assertRaises(A0XExecutionError):
            reader.read_jsonl_once()
        with self.assertRaisesRegex(A0XExecutionError, "statistical result"):
            seal_terminal_attempt(
                state=AttemptState.ANALYSIS,
                status="failed",
                target_receipt_path=receipt_path,
                statistical_result={"p_value": 0.5, "result_status": "completed"},
            )

    def test_terminal_uses_persisted_successful_read_receipt(self) -> None:
        from latent_triz.a0x_execution import AttemptState, seal_terminal_attempt

        path = self.temp_path / "synthetic-success.jsonl"
        path.write_bytes(_jsonl(_rows(("case-00",))))
        receipt_path = self.temp_path / "success-receipt.json"
        self._reader(
            path=path, expected_case_ids=("case-00",), receipt_path=receipt_path,
        ).read_jsonl_once()

        terminal = seal_terminal_attempt(
            state=AttemptState.ANALYSIS,
            status="passed",
            target_receipt_path=receipt_path,
            statistical_result={"p_value": 0.5, "result_status": "completed"},
        )
        self.assertEqual(1, terminal["analysis_target_content_reads"])
        self.assertEqual("passed", terminal["status"])
        self.assertEqual("completed", terminal["statistical_result"]["result_status"])
        self.assertEqual(pair_binding(), terminal["pair_binding"])

    def test_receipt_refuses_overwrite_and_reader_never_retries_after_receipt_failure(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(("case-00",))))
        receipt_path = self.temp_path / "existing-receipt.json"
        receipt_path.write_text("already here", encoding="utf-8")
        reader = self._reader(path=path, expected_case_ids=("case-00",), receipt_path=receipt_path)

        with self.assertRaisesRegex(A0XExecutionError, "already exists"):
            reader.read_jsonl_once()
        self.assertEqual("already here", receipt_path.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(A0XExecutionError, "already consumed"):
            reader.read_jsonl_once()


if __name__ == "__main__":
    unittest.main()
