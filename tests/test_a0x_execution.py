from __future__ import annotations

import hashlib
import inspect
import json
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from latent_triz.a0x_contract import Leg, LegFreezeBinding, sha256_file
from latent_triz.a0x_execution import A0XExecutionError
from latent_triz.validator import validate
from tests.a0x_test_support import A0XTempTestCase, artifact, pair_binding, sha


CASE_IDS = tuple(f"case-{index:02d}" for index in range(48))


def _rows(case_ids: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"case_id": case_id, "label": index} for index, case_id in enumerate(case_ids)]


def _jsonl(rows: list[dict[str, object]]) -> bytes:
    return b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        for row in rows
    )


class A0XExecutionTests(A0XTempTestCase):
    def _schema(self, name: str) -> dict[str, object]:
        root = Path(__file__).resolve().parents[1]
        return json.loads((root / "schemas" / name).read_text(encoding="utf-8"))

    def _assert_schema(self, name: str, value: dict[str, object]) -> None:
        self.assertEqual([], validate(value, self._schema(name)))

    def _reader(
        self,
        *,
        path: Path,
        leg: Leg = Leg.A0,
        selection=None,
        expected_sha256: str | None = None,
        receipt_path: Path | None = None,
    ):
        from latent_triz.a0x_execution import OneShotTargetReader

        return OneShotTargetReader(
            path=path,
            expected_sha256=expected_sha256 or sha256_file(path),
            receipt_path=receipt_path or self.temp_path / "target-read-receipt.json",
            pair_binding=pair_binding(leg),
            selection=selection or self._selection(leg),
            activation_receipt_sha256=sha(61),
            dense_sha256=sha(62),
            index_sha256=sha(63),
        )

    def _selection(self, leg: Leg = Leg.A0, case_ids: tuple[str, ...] = CASE_IDS):
        from latent_triz.a0x_execution import load_a0_public_selection, load_r1_public_selection

        root = self.temp_path / f"synthetic-repository-{leg.value}-{hash(case_ids)}"
        if leg is Leg.A0:
            manifest = artifact("a0x-selection-manifest.schema.json")
            template = manifest["cases"][0]
            manifest["cases"] = [{**template, "case_id": case_id} for case_id in case_ids]
            manifest["selected_case_count"] = len(case_ids)
            source = root / "experiments/a0x-six-model/a0-selection-manifest.json"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
            return load_a0_public_selection(
                repository_root=root, leg_freeze=self._freeze(leg, sha256_file(source)),
            )
        cases = root / "data/a0r1/cases.jsonl"
        cases.parent.mkdir(parents=True, exist_ok=True)
        cases.write_bytes(_jsonl(_rows(case_ids)))
        manifest = root / "data/a0r1/manifest.json"
        manifest.write_text(json.dumps({
            "artifact_class": "a0r1-public-corpus-manifest",
            "cases_path": "data/a0r1/cases.jsonl",
            "cases_sha256": sha256_file(cases),
            "case_count": len(case_ids),
            "case_ids": list(case_ids),
        }, sort_keys=True), encoding="utf-8")
        return load_r1_public_selection(
            repository_root=root, leg_freeze=self._freeze(leg, sha256_file(manifest)),
        )

    def _freeze(self, leg: Leg, selection_corpus_sha256: str) -> LegFreezeBinding:
        return LegFreezeBinding(
            leg=leg,
            protocol_id=f"a0x-{leg.value}-replication-v1",
            protocol_sha256=sha(70),
            implementation_sha256=sha(71),
            leg_freeze_sha256=sha(3),
            protected_tree_sha256=sha(72),
            selection_corpus_sha256=selection_corpus_sha256,
            source_base_commit="a" * 40,
        )

    def _successful_receipt(self, *, name: str = "success") -> Path:
        path = self.temp_path / f"{name}.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        receipt = self.temp_path / f"{name}-receipt.json"
        self._reader(path=path, receipt_path=receipt).read_jsonl_once()
        return receipt

    def test_analysis_reader_hashes_parses_and_persists_exact_48_in_one_open(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        receipt_path = self.temp_path / "target-read-receipt.json"
        reader = self._reader(path=path, receipt_path=receipt_path)
        rows, receipt = reader.read_jsonl_once()

        self.assertEqual(_rows(CASE_IDS), rows)
        self.assertEqual(48, len(rows))
        self.assertEqual(1, receipt.content_reads)
        persisted = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(1, persisted["content_reads"])
        self.assertEqual("pass", persisted["status"])
        self.assertEqual(sha256_file(path), persisted["observed_sha256"])
        self._assert_schema("a0x-target-read-receipt.schema.json", persisted)
        with self.assertRaisesRegex(A0XExecutionError, "already consumed"):
            reader.read_jsonl_once()

    def test_every_failure_receipt_validates_with_zero_or_one_reads(self) -> None:
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
                with self.assertRaisesRegex(A0XExecutionError, "sealed target"):
                    self._reader(path=path, expected_sha256=expected_hash, receipt_path=receipt_path).read_jsonl_once()
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(1, receipt["content_reads"])
                self.assertEqual(status, receipt["status"])
                self._assert_schema("a0x-target-read-receipt.schema.json", receipt)

        missing = self.temp_path / "synthetic-missing.jsonl"
        missing_receipt = self.temp_path / "missing-receipt.json"
        with self.assertRaisesRegex(A0XExecutionError, "sealed target read failed"):
            self._reader(path=missing, expected_sha256=sha(44), receipt_path=missing_receipt).read_jsonl_once()
        receipt = json.loads(missing_receipt.read_text(encoding="utf-8"))
        self.assertEqual(0, receipt["content_reads"])
        self.assertEqual("read_failed", receipt["status"])
        self._assert_schema("a0x-target-read-receipt.schema.json", receipt)

    def test_reader_requires_exactly_48_unique_expected_ids(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        for expected in (CASE_IDS[:1], CASE_IDS[:-1], CASE_IDS + ("case-48",), CASE_IDS[:-1] + (CASE_IDS[-2],)):
            with self.subTest(count=len(expected)):
                with self.assertRaisesRegex(A0XExecutionError, "48"):
                    self._selection(Leg.A0, expected)

    def test_a0_returns_the_exact_ordered_selected_48_subset(self) -> None:
        expected = tuple(reversed(CASE_IDS))
        path = self.temp_path / "synthetic-a0.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS + ("unselected",))))
        rows, _ = self._reader(path=path, selection=self._selection(Leg.A0, expected)).read_jsonl_once()
        self.assertEqual(expected, tuple(row["case_id"] for row in rows))

        for name, source_ids in (("missing", CASE_IDS[:-1]), ("duplicate", CASE_IDS + (CASE_IDS[-1],))):
            with self.subTest(name=name):
                target = self.temp_path / f"synthetic-a0-{name}.jsonl"
                target.write_bytes(_jsonl(_rows(source_ids)))
                receipt_path = self.temp_path / f"synthetic-a0-{name}-receipt.json"
                with self.assertRaisesRegex(A0XExecutionError, "selection"):
                    self._reader(path=target, receipt_path=receipt_path).read_jsonl_once()
                self._assert_schema("a0x-target-read-receipt.schema.json", json.loads(receipt_path.read_text(encoding="utf-8")))

    def test_r1_requires_complete_exact_ordered_48_selection(self) -> None:
        for name, source_ids in (("extra", CASE_IDS + ("extra",)), ("missing", CASE_IDS[:-1]), ("reordered", tuple(reversed(CASE_IDS)))):
            with self.subTest(name=name):
                path = self.temp_path / f"synthetic-r1-{name}.jsonl"
                path.write_bytes(_jsonl(_rows(source_ids)))
                receipt_path = self.temp_path / f"synthetic-r1-{name}-receipt.json"
                with self.assertRaisesRegex(A0XExecutionError, "selection"):
                    self._reader(path=path, leg=Leg.R1, receipt_path=receipt_path).read_jsonl_once()
                self._assert_schema("a0x-target-read-receipt.schema.json", json.loads(receipt_path.read_text(encoding="utf-8")))

        valid = self.temp_path / "synthetic-r1-valid.jsonl"
        valid.write_bytes(_jsonl(_rows(CASE_IDS)))
        selection = self._selection(Leg.R1)
        with self.assertRaisesRegex(A0XExecutionError, "exact-file mode"):
            self._reader(path=valid, leg=Leg.R1, selection=replace(selection, require_file_exact=False))

    def test_reader_requires_sealed_activation_dense_index_and_selection_bindings(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        from latent_triz.a0x_execution import OneShotTargetReader

        kwargs = {
            "path": path, "expected_sha256": sha256_file(path),
            "receipt_path": self.temp_path / "receipt.json",
            "pair_binding": pair_binding(), "selection": self._selection(),
            "activation_receipt_sha256": sha(61), "dense_sha256": sha(62), "index_sha256": sha(63),
        }
        for field in ("activation_receipt_sha256", "dense_sha256", "index_sha256"):
            with self.subTest(field=field):
                invalid = dict(kwargs)
                invalid[field] = "not-a-hash"
                with self.assertRaisesRegex(A0XExecutionError, "sealed"):
                    OneShotTargetReader(**invalid)

    def test_mutated_selection_capability_is_refused_before_target_open(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        expected_sha256 = sha256_file(path)
        selection = self._selection()
        substitutions = (
            replace(selection, source_path="experiments/a0x-six-model/alternate.json"),
            replace(selection, expected_case_ids=tuple(reversed(CASE_IDS))),
            replace(selection, source_sha256=sha(99)),
            replace(selection, leg_freeze_sha256=sha(98)),
            replace(selection, expected_case_ids=CASE_IDS[:-1]),
            replace(selection, expected_case_ids=CASE_IDS + ("case-48",)),
            replace(selection, expected_case_ids=CASE_IDS[:-1] + (CASE_IDS[-2],)),
            replace(selection, leg=Leg.R1),
        )
        original_open = Path.open
        target_opens = 0

        def guarded_open(candidate: Path, mode: str = "r", *args, **kwargs):
            nonlocal target_opens
            if candidate == path and mode == "rb":
                target_opens += 1
            return original_open(candidate, mode, *args, **kwargs)

        with patch.object(Path, "open", new=guarded_open):
            for index, mutated in enumerate(substitutions):
                with self.subTest(index=index):
                    with self.assertRaisesRegex(A0XExecutionError, "selection"):
                        self._reader(
                            path=path, expected_sha256=expected_sha256, selection=mutated,
                            receipt_path=self.temp_path / f"mutated-{index}.json",
                        )
        self.assertEqual(0, target_opens)

    def test_canonical_loaders_reject_mutated_freeze_and_r1_corpus_before_reader(self) -> None:
        from latent_triz.a0x_execution import load_a0_public_selection, load_r1_public_selection

        root = self.temp_path / "canonical-loader-root"
        a0_path = root / "experiments/a0x-six-model/a0-selection-manifest.json"
        a0_path.parent.mkdir(parents=True)
        a0_path.write_text(json.dumps(artifact("a0x-selection-manifest.schema.json")), encoding="utf-8")
        target = self.temp_path / "unopened-target.jsonl"
        target.write_bytes(_jsonl(_rows(CASE_IDS)))
        receipt = self.temp_path / "unreserved-receipt.json"

        with self.assertRaisesRegex(A0XExecutionError, "hash differs"):
            load_a0_public_selection(repository_root=root, leg_freeze=self._freeze(Leg.A0, sha(90)))
        with self.assertRaisesRegex(A0XExecutionError, "wrong leg"):
            load_a0_public_selection(
                repository_root=root, leg_freeze=self._freeze(Leg.R1, sha256_file(a0_path)),
            )
        self.assertFalse(receipt.exists())

        cases = root / "data/a0r1/cases.jsonl"
        cases.parent.mkdir(parents=True)
        cases.write_bytes(_jsonl(_rows(CASE_IDS)))
        manifest = root / "data/a0r1/manifest.json"
        manifest.write_text(json.dumps({
            "artifact_class": "a0r1-public-corpus-manifest",
            "cases_path": "alternate/cases.jsonl",
            "cases_sha256": sha256_file(cases),
            "case_count": 48,
            "case_ids": list(CASE_IDS),
        }), encoding="utf-8")
        with self.assertRaisesRegex(A0XExecutionError, "invalid frozen format"):
            load_r1_public_selection(
                repository_root=root, leg_freeze=self._freeze(Leg.R1, sha256_file(manifest)),
            )

        manifest.write_text(json.dumps({
            "artifact_class": "a0r1-public-corpus-manifest",
            "cases_path": "data/a0r1/cases.jsonl",
            "cases_sha256": sha256_file(cases),
            "case_count": 48,
            "case_ids": list(CASE_IDS),
        }), encoding="utf-8")
        cases.write_bytes(_jsonl(_rows(tuple(reversed(CASE_IDS)))))
        with self.assertRaisesRegex(A0XExecutionError, "cases hash differs"):
            load_r1_public_selection(
                repository_root=root, leg_freeze=self._freeze(Leg.R1, sha256_file(manifest)),
            )
        self.assertFalse(receipt.exists())

    def test_preexisting_receipt_destination_is_refused_before_target_open(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        expected_sha256 = sha256_file(path)
        receipt_path = self.temp_path / "existing-receipt.json"
        receipt_path.write_text("first receipt bytes", encoding="utf-8")
        original_open = Path.open
        target_opens = 0

        def guarded_open(candidate: Path, mode: str = "r", *args, **kwargs):
            nonlocal target_opens
            if candidate == path and mode == "rb":
                target_opens += 1
            return original_open(candidate, mode, *args, **kwargs)

        with patch.object(Path, "open", new=guarded_open):
            with self.assertRaisesRegex(A0XExecutionError, "already exists"):
                self._reader(path=path, expected_sha256=expected_sha256, receipt_path=receipt_path)
        self.assertEqual(0, target_opens)
        self.assertEqual("first receipt bytes", receipt_path.read_text(encoding="utf-8"))

    def test_receipt_reservation_race_refuses_before_target_open(self) -> None:
        path = self.temp_path / "synthetic-targets.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        receipt_path = self.temp_path / "race-receipt.json"
        expected_sha256 = sha256_file(path)
        original_open = Path.open
        target_opens = 0

        def racing_open(candidate: Path, mode: str = "r", *args, **kwargs):
            nonlocal target_opens
            if candidate == receipt_path and mode == "xb":
                raise FileExistsError("synthetic concurrent reservation")
            if candidate == path and mode == "rb":
                target_opens += 1
            return original_open(candidate, mode, *args, **kwargs)

        with patch.object(Path, "open", new=racing_open):
            with self.assertRaisesRegex(A0XExecutionError, "already exists"):
                self._reader(path=path, expected_sha256=expected_sha256, receipt_path=receipt_path)
        self.assertEqual(0, target_opens)
        self.assertFalse(receipt_path.exists())

    def test_read_failure_after_open_persists_one_read_receipt(self) -> None:
        path = self.temp_path / "synthetic-read-failure.jsonl"
        path.write_bytes(_jsonl(_rows(CASE_IDS)))
        receipt_path = self.temp_path / "read-failure-receipt.json"
        reader = self._reader(path=path, receipt_path=receipt_path)
        original_open = Path.open

        class BrokenStream:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self) -> bytes: raise OSError("synthetic stream failure")

        def open_for_target(candidate: Path, mode: str = "r", *args, **kwargs):
            if candidate == path and mode == "rb": return BrokenStream()
            return original_open(candidate, mode, *args, **kwargs)

        with patch.object(Path, "open", new=open_for_target):
            with self.assertRaisesRegex(A0XExecutionError, "sealed target read failed"):
                reader.read_jsonl_once()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(1, receipt["content_reads"])
        self.assertEqual("read_failed", receipt["status"])
        self.assertIsNone(receipt["observed_sha256"])
        self._assert_schema("a0x-target-read-receipt.schema.json", receipt)

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

    def test_terminal_taxonomy_pair_binding_and_exclusive_first_terminal(self) -> None:
        from latent_triz.a0x_execution import AttemptState, seal_terminal_attempt
        receipt_path, pair = self._successful_receipt(), pair_binding()
        for status in ("positive", "null"):
            with self.subTest(status=status):
                terminal_path = self.temp_path / f"{status}.json"
                terminal = seal_terminal_attempt(
                    state=AttemptState.ANALYSIS, status=status, target_receipt_path=receipt_path,
                    terminal_path=terminal_path, pair_binding=pair,
                    statistical_result={"p_value": 0.5, "result_status": "completed"},
                )
                self.assertEqual(1, terminal["analysis_target_content_reads"])
                self.assertEqual(pair, terminal["pair_binding"])
                self._assert_schema("a0x-terminal-result.schema.json", terminal)

        path = self.temp_path / "non-interpretable.json"
        terminal = seal_terminal_attempt(
            state=AttemptState.ANALYSIS, status="non_interpretable", target_receipt_path=receipt_path,
            terminal_path=path, pair_binding=pair,
        )
        self.assertIsNone(terminal["statistical_result"])
        self._assert_schema("a0x-terminal-result.schema.json", terminal)

        first_path = self.temp_path / "first-terminal.json"
        first = seal_terminal_attempt(
            state=AttemptState.PREFLIGHT, status="incompatible", terminal_path=first_path, pair_binding=pair,
        )
        before = first_path.read_bytes()
        self.assertEqual(0, first["analysis_target_content_reads"])
        self._assert_schema("a0x-terminal-result.schema.json", first)
        with self.assertRaisesRegex(A0XExecutionError, "already exists"):
            seal_terminal_attempt(
                state=AttemptState.PREFLIGHT, status="failed", terminal_path=first_path, pair_binding=pair,
            )
        self.assertEqual(before, first_path.read_bytes())
        with self.assertRaisesRegex(A0XExecutionError, "pair binding"):
            seal_terminal_attempt(
                state=AttemptState.PREFLIGHT, status="failed", terminal_path=self.temp_path / "missing-pair.json",
            )

    def test_terminal_refuses_statistic_for_read_error_and_requires_passing_read_for_result(self) -> None:
        from latent_triz.a0x_execution import AttemptState, seal_terminal_attempt
        failure = self.temp_path / "synthetic-failure.jsonl"
        failure.write_bytes(b"bad-json\n")
        failure_receipt = self.temp_path / "failure-receipt.json"
        with self.assertRaises(A0XExecutionError):
            self._reader(path=failure, expected_sha256=sha256_file(failure), receipt_path=failure_receipt).read_jsonl_once()
        with self.assertRaisesRegex(A0XExecutionError, "statistical result"):
            seal_terminal_attempt(
                state=AttemptState.ANALYSIS, status="failed", target_receipt_path=failure_receipt,
                terminal_path=self.temp_path / "failed-result.json", pair_binding=pair_binding(),
                statistical_result={"p_value": 0.5, "result_status": "completed"},
            )
        with self.assertRaisesRegex(A0XExecutionError, "passing target read"):
            seal_terminal_attempt(
                state=AttemptState.ANALYSIS, status="positive", target_receipt_path=failure_receipt,
                terminal_path=self.temp_path / "positive-failure.json", pair_binding=pair_binding(),
                statistical_result={"p_value": 0.5, "result_status": "completed"},
            )

    def test_missing_target_analysis_failure_keeps_zero_read_receipt_hash(self) -> None:
        from latent_triz.a0x_execution import AttemptState, seal_terminal_attempt

        missing = self.temp_path / "missing.jsonl"
        receipt_path = self.temp_path / "missing-receipt.json"
        with self.assertRaisesRegex(A0XExecutionError, "read failed"):
            self._reader(path=missing, expected_sha256=sha(77), receipt_path=receipt_path).read_jsonl_once()
        terminal = seal_terminal_attempt(
            state=AttemptState.ANALYSIS,
            status="failed",
            target_receipt_path=receipt_path,
            terminal_path=self.temp_path / "missing-terminal.json",
            pair_binding=pair_binding(),
        )
        self.assertEqual(0, terminal["analysis_target_content_reads"])
        self.assertIsInstance(terminal["target_read_receipt_sha256"], str)
        self._assert_schema("a0x-terminal-result.schema.json", terminal)


if __name__ == "__main__":
    unittest.main()
