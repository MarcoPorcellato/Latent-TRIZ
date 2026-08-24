from __future__ import annotations

import json
import hashlib
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from latent_triz.a0x_contract import Leg, compute_dense_bound
from latent_triz.a0x_model_adapter import HiddenPayload


def public_cases() -> list[dict[str, object]]:
    return [
        {
            "case_id": f"case-{index:02d}",
            "problem_family_id": f"family-{index // 2:02d}",
            "domain": ("agriculture", "energy", "manufacturing", "medicine", "software", "transport")[index % 6],
            "split": "calibration",
            "problem": f"Problem {index}",
            "constraints": ["Keep cost bounded"],
            "initial_state": "Initial state",
            "desired_improvement": "Improve safely",
            "worsening_consequence": "Do not increase risk",
            "transformation": "Split the component",
            "solution": "Use two smaller components",
        }
        for index in range(48)
    ]


def selection_manifest() -> dict[str, object]:
    cases = public_cases()
    return {
        "artifact_class": "a0x-selection-manifest",
        "selected_case_count": 48,
        "target_content_reads": 0,
        "cases": [
            {
                key: case[key]
                for key in ("case_id", "problem_family_id", "domain", "split")
            }
            for case in cases
        ],
    }


@dataclass
class _SyntheticAdapter:
    layers: int
    width: int
    forwards: int = 0

    def forward_hidden(self, text: str) -> HiddenPayload:
        self.forwards += 1
        offsets = tuple((index, index + 1) for index in range(len(text)))
        hidden_states = tuple(
            [[[(layer + 1) * 0.1 + coordinate * 0.001 for coordinate in range(self.width)] for _ in text]]
            for layer in range(self.layers)
        )
        return HiddenPayload(
            input_ids=tuple(range(len(text))),
            attention_mask=tuple(1 for _ in text),
            offsets=offsets,
            special_tokens_mask=tuple(0 for _ in text),
            hidden_states=hidden_states,
            final_block_tuple_index=self.layers - 1,
        )


def synthetic_hidden_adapter(*, layers: int, width: int) -> _SyntheticAdapter:
    return _SyntheticAdapter(layers=layers, width=width)


def oversized_adapter() -> _SyntheticAdapter:
    return _SyntheticAdapter(layers=13, width=3_000)


def synthetic_occupied_tree(root: Path, *, total_bytes: int) -> Path:
    root.mkdir(parents=True)
    (root / "payload.bin").write_bytes(b"x" * total_bytes)
    return root


class A0XActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._temporary_directory = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._temporary_directory.name)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_a0_extracts_literal_and_final_endpoints_without_targets(self) -> None:
        from latent_triz.a0x_a0_activations import extract_a0x_a0

        artifacts = extract_a0x_a0(
            adapter=synthetic_hidden_adapter(layers=13, width=8),
            cases=public_cases(), selection=selection_manifest(),
            output_dir=self.tmp_path / "a0", created_at="2026-08-24T00:00:00Z",
        )

        self.assertEqual(0, artifacts.receipt["activation_target_content_reads"])
        self.assertEqual({0, 2, 4, 6}, set(artifacts.receipt["literal_tuple_indices"]))
        self.assertEqual(12, artifacts.receipt["final_block_tuple_index"])
        self.assertEqual(2_400, artifacts.receipt["record_count"])
        rows = [json.loads(line) for line in artifacts.index_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(2_400, len(rows))
        self.assertEqual({"primary", "descriptive"}, {row["endpoint_role"] for row in rows})
        self.assertEqual(64, len(rows[0]["vector_sha256"]))

    def test_completed_output_remeasures_to_the_persisted_activation_stage_receipt(self) -> None:
        from latent_triz.a0x_a0_activations import extract_a0x_a0, measure_output_occupancy

        artifacts = extract_a0x_a0(
            adapter=synthetic_hidden_adapter(layers=13, width=8),
            cases=public_cases(), selection=selection_manifest(),
            output_dir=self.tmp_path / "remeasure", created_at="2026-08-24T00:00:00Z",
        )
        persisted = artifacts.receipt["activation_stage_occupancy"]
        remeasured = measure_output_occupancy(artifacts.dense_path.parent, leg=Leg.A0)

        self.assertEqual(persisted, remeasured.as_mapping())
        self.assertEqual(artifacts.receipt["activation_stage_occupancy_sha256"], remeasured.sha256)
        self.assertNotIn("activation-receipt.json", remeasured.included_paths)

    def test_a0_receipt_attests_cap_checked_prewrite_sequence(self) -> None:
        from latent_triz.a0x_a0_activations import extract_a0x_a0

        artifacts = extract_a0x_a0(
            adapter=synthetic_hidden_adapter(layers=13, width=8),
            cases=public_cases(), selection=selection_manifest(),
            output_dir=self.tmp_path / "checkpoints", created_at="2026-08-24T00:00:00Z",
        )

        checkpoints = artifacts.receipt["occupancy_checkpoints"]
        self.assertEqual(
            ["pre_dense_write", "pre_index_write", "pre_final_rename"],
            [checkpoint["phase"] for checkpoint in checkpoints],
        )
        self.assertTrue(all(checkpoint["projected_total_bytes"] <= checkpoint["cap_bytes"] for checkpoint in checkpoints))
        self.assertEqual(artifacts.receipt["planned_dense_bound"], checkpoints[0]["planned_dense_bound"])

    def test_failed_dense_write_preserves_measured_stage_residue_without_final_output(self) -> None:
        from latent_triz.a0x_a0_activations import A0XActivationError, extract_a0x_a0

        def partial_then_fail(path, _vectors, *, width, payload):
            del width, payload
            path.write_bytes(b"partial-dense-bytes")
            raise RuntimeError("induced dense write failure")

        with patch("latent_triz.a0x_a0_activations._write_safetensors", side_effect=partial_then_fail):
            with self.assertRaisesRegex(A0XActivationError, "activation stage failed") as raised:
                extract_a0x_a0(
                    adapter=synthetic_hidden_adapter(layers=13, width=8),
                    cases=public_cases(), selection=selection_manifest(),
                    output_dir=self.tmp_path / "failed", created_at="2026-08-24T00:00:00Z",
                )

        error = raised.exception
        self.assertFalse((self.tmp_path / "failed").exists())
        self.assertTrue(error.stage_path.is_dir())
        self.assertEqual(["pre_dense_write"], [checkpoint["phase"] for checkpoint in error.occupancy_checkpoints])
        self.assertIn("activations.safetensors", error.activation_stage_occupancy.included_paths)
        self.assertEqual(len(b"partial-dense-bytes"), error.activation_stage_occupancy.actual_total_bytes)

    def test_prewrite_occupancy_failure_records_the_attempted_checkpoint(self) -> None:
        from latent_triz.a0x_a0_activations import A0XActivationError, extract_a0x_a0

        with patch("latent_triz.a0x_a0_activations._cap", return_value=1):
            with self.assertRaisesRegex(A0XActivationError, "activation stage failed") as raised:
                extract_a0x_a0(
                    adapter=synthetic_hidden_adapter(layers=13, width=8),
                    cases=public_cases(), selection=selection_manifest(),
                    output_dir=self.tmp_path / "cap-failed", created_at="2026-08-24T00:00:00Z",
                )

        error = raised.exception
        self.assertFalse((self.tmp_path / "cap-failed").exists())
        self.assertEqual(["pre_dense_write"], [checkpoint["phase"] for checkpoint in error.occupancy_checkpoints])
        self.assertEqual(0, error.activation_stage_occupancy.actual_total_bytes)
        self.assertEqual(1, error.activation_stage_occupancy.cap_bytes)

    def test_safetensors_payload_slices_match_every_jsonl_record(self) -> None:
        from latent_triz.a0x_a0_activations import extract_a0x_a0

        artifacts = extract_a0x_a0(
            adapter=synthetic_hidden_adapter(layers=13, width=8),
            cases=public_cases(), selection=selection_manifest(),
            output_dir=self.tmp_path / "readback", created_at="2026-08-24T00:00:00Z",
        )
        encoded = artifacts.dense_path.read_bytes()
        header_bytes = int.from_bytes(encoded[:8], "little")
        header = json.loads(encoded[8:8 + header_bytes])
        payload = encoded[8 + header_bytes:]
        rows = [json.loads(line) for line in artifacts.index_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(2_400, len(header))
        for row in rows:
            entry = header[row["tensor_key"]]
            self.assertEqual("F32", entry["dtype"])
            self.assertEqual([row["vector_dim"]], entry["shape"])
            start, end = entry["data_offsets"]
            self.assertEqual(row["vector_sha256"], hashlib.sha256(payload[start:end]).hexdigest())

    def test_r1_keeps_literal_six_primary_and_final_descriptive(self) -> None:
        from latent_triz.a0x_r1_activations import extract_a0x_r1

        artifacts = extract_a0x_r1(
            adapter=synthetic_hidden_adapter(layers=13, width=8),
            cases=public_cases(), selection=selection_manifest(), output_dir=self.tmp_path / "r1",
        )

        rows = [json.loads(line) for line in artifacts.index_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(192, len(rows))
        primary = [row for row in rows if row["endpoint_role"] == "primary"]
        descriptive = [row for row in rows if row["endpoint_role"] == "descriptive"]
        self.assertEqual({6}, {row["tuple_index"] for row in primary})
        self.assertEqual({12}, {row["tuple_index"] for row in descriptive})
        self.assertEqual(12, artifacts.receipt["final_block_tuple_index"])
        self.assertEqual(0, artifacts.receipt["activation_target_content_reads"])

    def test_synthetic_overflow_is_rejected_before_write(self) -> None:
        from latent_triz.a0x_r1_activations import A0XActivationError, extract_a0x_r1

        adapter = oversized_adapter()
        with self.assertRaisesRegex(A0XActivationError, "dense output cap"):
            extract_a0x_r1(adapter=adapter, cases=public_cases(), selection=selection_manifest(), output_dir=self.tmp_path / "r1")
        self.assertEqual(0, adapter.forwards)
        self.assertFalse((self.tmp_path / "r1").exists())

    def test_actual_occupied_bytes_accept_exact_cap_and_reject_one_over(self) -> None:
        from latent_triz.a0x_a0_activations import A0XActivationError, measure_output_occupancy

        exact = synthetic_occupied_tree(self.tmp_path / "exact", total_bytes=4_194_304)
        receipt = measure_output_occupancy(exact, leg=Leg.R1)
        self.assertEqual(4_194_304, receipt.actual_total_bytes)
        self.assertEqual("activation_stage", receipt.occupancy_scope)
        one_over = synthetic_occupied_tree(self.tmp_path / "over", total_bytes=4_194_305)
        with self.assertRaisesRegex(A0XActivationError, "dense output cap"):
            measure_output_occupancy(one_over, leg=Leg.R1)

    def test_recursive_occupancy_counts_staging_and_crash_residue(self) -> None:
        from latent_triz.a0x_a0_activations import measure_output_occupancy

        root = self.tmp_path / "occupancy"
        root.mkdir()
        (root / "activations.safetensors").write_bytes(b"a" * 7)
        (root / ".dense-stage").mkdir()
        (root / ".dense-stage" / "copy").write_bytes(b"b" * 11)
        (root / ".index-crash").mkdir()
        (root / ".index-crash" / "residue").write_bytes(b"c" * 13)

        receipt = measure_output_occupancy(root, leg=Leg.A0)

        self.assertEqual(31, receipt.actual_total_bytes)
        self.assertIn(".dense-stage/copy", receipt.included_paths)
        self.assertIn(".index-crash/residue", receipt.included_paths)

    def test_verify_occupancy_rejects_leg_mismatch(self) -> None:
        from latent_triz.a0x_a0_activations import A0XActivationError, measure_output_occupancy, verify_output_occupancy

        root = synthetic_occupied_tree(self.tmp_path / "mismatch", total_bytes=1)
        actual = measure_output_occupancy(root, leg=Leg.R1)
        with self.assertRaisesRegex(A0XActivationError, "leg"):
            verify_output_occupancy(compute_dense_bound(Leg.A0, cases=48, hidden_width=8), actual)


if __name__ == "__main__":
    unittest.main()
