"""Synthetic contract tests for the frozen A0X-R1 analysis path."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
import struct
import unittest
from pathlib import Path

from tests.a0x_test_support import A0XTempTestCase, pair_binding, sha
from latent_triz.a0x_contract import Leg
from latent_triz.validator import validate


_VIEWS = {
    "problem_only": ("sentinel",),
    "problem_plus_transformation": ("mean_transformation_span",),
}


def _receipt_bytes(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def synthetic_r1_inputs(*, primary_signal: float, final_signal: float) -> dict[str, object]:
    """Build only in-memory synthetic R1 assets; it never opens a target file."""
    from latent_triz.a0x_a0_activations import _serialize_safetensors

    pair = pair_binding(Leg.R1, hidden_width=2)
    rows: list[dict[str, object]] = []
    index_rows: list[dict[str, object]] = []
    tensors: dict[str, bytes] = {}
    for number in range(48):
        label = number % 2
        case_id = f"case-{number:02d}"
        family = f"family-{number // 2:02d}"
        domain = f"domain-{number // 8}"
        rows.append({
            "case_id": case_id,
            "operator_proxy_family": "segmentation_like" if label else "inversion_like",
            "problem_family_id": family,
            "domain": domain,
        })
        signed = 1.0 if label else -1.0
        for view, sites in _VIEWS.items():
            for site in sites:
                for tuple_index in (6, 12):
                    signal = primary_signal if (view, tuple_index) == ("problem_plus_transformation", 6) else final_signal if tuple_index == 12 else 0.0
                    tensor_key = f"{case_id}::{view}::{site}::tuple-{tuple_index}"
                    raw = struct.pack("<2f", signed * signal, float(number % 3))
                    tensors[tensor_key] = raw
                    index_rows.append({
                        "record_id": tensor_key, "case_id": case_id, "problem_family_id": family,
                        "domain": domain, "view": view, "token_site": site,
                        "tuple_index": tuple_index,
                        "endpoint_role": "primary" if tuple_index == 6 else "descriptive",
                        "vector_dim": 2, "dtype": "float32",
                        "vector_sha256": hashlib.sha256(raw).hexdigest(), "tensor_key": tensor_key,
                    })
    dense = _serialize_safetensors(tensors, width=2)
    index = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" for row in index_rows)
    common = {"empirical": True, "scientific_status": "exploratory", "evidence_eligible": False, "expert_validated": False, "claim_ids": []}
    activation = {
        "artifact_class": "a0x-activation-receipt", **common, "pair_binding": pair,
        "leg": "r1", "created_at": "2026-08-24T00:00:00Z", "activation_status": "completed",
        "activation_target_content_reads": 0, "literal_tuple_indices": [6], "final_block_tuple_index": 12,
        "record_count": len(index_rows),
        "dense": {"path": "activations.safetensors", "sha256": hashlib.sha256(dense).hexdigest(), "bytes": len(dense), "format": "safetensors"},
        "index": {"path": "representations-index.jsonl", "sha256": hashlib.sha256(index).hexdigest(), "bytes": len(index)},
        "planned_dense_bound": pair["dense_bound"],
        "activation_stage_occupancy": {"artifact_class": "a0x-output-occupancy-receipt", **common, "leg": "r1", "occupancy_scope": "activation_stage", "included_paths": ["activations.safetensors", "representations-index.jsonl"], "actual_total_bytes": len(dense) + len(index), "cap_bytes": 4194304},
        "activation_stage_occupancy_sha256": sha(81), "occupancy_checkpoints": [],
    }
    activation_bytes = _receipt_bytes(activation)
    target_receipt = {
        "artifact_class": "a0x-target-read-receipt", **common, "pair_binding": pair,
        "selection_corpus_sha256": sha(82), "content_reads": 1, "status": "pass", "observed_sha256": sha(83),
        "activation_receipt_sha256": hashlib.sha256(activation_bytes).hexdigest(),
        "dense_sha256": activation["dense"]["sha256"], "index_sha256": activation["index"]["sha256"],
    }
    return {
        "pair_binding": pair, "target_rows": rows,
        "target_read_receipt_bytes": _receipt_bytes(target_receipt),
        "activation_receipt_bytes": activation_bytes, "dense_asset_bytes": dense,
        "index_bytes": index, "shortcut_result": {"status": "pass"},
    }


class A0XR1AnalysisTests(A0XTempTestCase):
    def _schema(self) -> dict[str, object]:
        return json.loads((Path(__file__).resolve().parents[1] / "schemas/a0x-statistical-result.schema.json").read_text(encoding="utf-8"))

    def test_final_block_never_replaces_literal_index_six(self) -> None:
        from latent_triz.a0x_r1_analysis import analyze_a0x_r1

        result = analyze_a0x_r1(**synthetic_r1_inputs(primary_signal=0.0, final_signal=10.0))

        self.assertEqual("null", result["status"])
        self.assertEqual(6, result["primary"]["tuple_index"])
        self.assertFalse(result["descriptive_final_block"]["rescues_primary"])

    def test_primary_positive_uses_literal_index_six_and_all_four_conditions(self) -> None:
        from latent_triz.a0x_r1_analysis import analyze_a0x_r1

        result = analyze_a0x_r1(**synthetic_r1_inputs(primary_signal=1.0, final_signal=0.0))

        self.assertEqual("positive", result["status"])
        self.assertEqual(6, result["primary"]["tuple_index"])
        self.assertGreaterEqual(result["primary"]["family_successes"], 17)
        self.assertGreaterEqual(result["domain_direction_success_count"], 4)
        self.assertEqual(
            tuple(f"domain-{index}" for index in range(6)),
            tuple(result["domain_direction_successes"]),
        )
        self.assertEqual(12, result["score_quantization_decimals"])
        self.assertEqual("9f6e1e1722f9cde622c3c4cc65c2293ab8dc7f0f4622c8becd6182872cd3145b", result["primary"]["null_distribution_sha256"])
        self.assertEqual([], validate(result, self._schema()))

    def test_positive_predicate_requires_each_frozen_condition(self) -> None:
        from latent_triz.a0x_r1_analysis import frozen_positive

        self.assertTrue(frozen_positive(p_value=0.05, margin=0.10, family_successes=17, domain_successes=4))
        for values in ((0.050001, 0.10, 17, 4), (0.05, 0.099999, 17, 4), (0.05, 0.10, 16, 4), (0.05, 0.10, 17, 3)):
            with self.subTest(values=values):
                self.assertFalse(frozen_positive(p_value=values[0], margin=values[1], family_successes=values[2], domain_successes=values[3]))

    def test_analysis_has_no_target_reader_or_filesystem_capability(self) -> None:
        from latent_triz.a0x_r1_analysis import analyze_a0x_r1

        forbidden = {"target_path", "targets_path", "target_reader", "filesystem", "path", "root"}
        self.assertFalse(forbidden.intersection(inspect.signature(analyze_a0x_r1).parameters))

    def test_pair_binding_and_raw_asset_links_are_strict(self) -> None:
        from latent_triz.a0x_r1_analysis import A0XR1AnalysisError, analyze_a0x_r1

        inputs = synthetic_r1_inputs(primary_signal=1.0, final_signal=0.0)
        receipt = json.loads(inputs["target_read_receipt_bytes"])
        receipt["activation_receipt_sha256"] = "0" * 64
        inputs["target_read_receipt_bytes"] = _receipt_bytes(receipt)
        with self.assertRaisesRegex(A0XR1AnalysisError, "asset links"):
            analyze_a0x_r1(**inputs)

        inputs = synthetic_r1_inputs(primary_signal=1.0, final_signal=0.0)
        receipt = json.loads(inputs["target_read_receipt_bytes"])
        receipt["pair_binding"] = pair_binding(Leg.R1, model_key="smollm2_135m", hidden_width=2)
        inputs["target_read_receipt_bytes"] = _receipt_bytes(receipt)
        with self.assertRaisesRegex(A0XR1AnalysisError, "pair binding"):
            analyze_a0x_r1(**inputs)

    def test_r1_helpers_match_historical_fixed_primary_helpers(self) -> None:
        try:
            import numpy as np
        except ModuleNotFoundError:
            self.skipTest("numpy unavailable for historical-helper parity comparison")
        from latent_triz.a0r1_analysis import _family_permutation_null as historical_null
        from latent_triz.a0x_r1_analysis import _family_permutation_null

        operator = np.eye(4)
        labels = (0, 1, 0, 1)
        families = ("f0", "f0", "f1", "f1")
        self.assertEqual(
            historical_null(operator, labels, families, seed=20260815, budget=3),
            _family_permutation_null(operator, labels, families, seed=20260815, budget=3),
        )


if __name__ == "__main__":
    unittest.main()
