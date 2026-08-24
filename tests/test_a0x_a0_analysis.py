from __future__ import annotations

import inspect
import json
import unittest
from pathlib import Path

from latent_triz.a0_analysis import _family_successes as historical_family_successes
from latent_triz.a0_analysis import _score_operator as historical_score_operator
from latent_triz.a0x_contract import Leg
from latent_triz.validator import validate
from tests.a0x_test_support import A0XTempTestCase, pair_binding, sha


_LITERAL = (0, 2, 4, 6)
_VIEWS = {
    "problem_only": ("sentinel",),
    "transformation_only": ("sentinel", "final_transformation_token", "mean_transformation_span"),
    "problem_plus_transformation": ("sentinel", "final_transformation_token", "mean_transformation_span"),
    "problem_plus_solution": ("sentinel", "final_transformation_token", "mean_transformation_span"),
}


def synthetic_a0_inputs(*, primary_signal: float, final_signal: float) -> dict[str, object]:
    pair = pair_binding(Leg.A0)
    target_rows: list[dict[str, object]] = []
    index_rows: list[dict[str, object]] = []
    dense_vectors: dict[str, list[float]] = {}
    for case_number in range(48):
        label = case_number % 2
        family = f"family-{case_number // 2:02d}"
        case_id = f"case-{case_number:02d}"
        target_rows.append({
            "case_id": case_id,
            "operator_proxy_family": "segmentation_like" if label else "inversion_like",
            "problem_family_id": family,
            "domain": f"domain-{case_number // 8}",
        })
        signed = 1.0 if label else -1.0
        for view, sites in _VIEWS.items():
            for site in sites:
                for tuple_index in (*_LITERAL, 12):
                    signal = 0.0
                    if view == "problem_plus_transformation" and tuple_index in _LITERAL:
                        signal = primary_signal
                    elif tuple_index == 12:
                        signal = final_signal
                    record_id = f"{case_id}::{view}::{site}::tuple-{tuple_index}"
                    dense_vectors[record_id] = [signed * signal, float(case_number % 3)]
                    index_rows.append({
                        "record_id": record_id,
                        "case_id": case_id,
                        "problem_family_id": family,
                        "domain": f"domain-{case_number // 8}",
                        "view": view,
                        "token_site": site,
                        "tuple_index": tuple_index,
                        "endpoint_role": "primary" if tuple_index in _LITERAL else "descriptive",
                        "vector_dim": 2,
                        "dtype": "float32",
                        "vector_sha256": sha(case_number + tuple_index + 100),
                        "tensor_key": record_id,
                    })
    return {
        "pair_binding": pair,
        "target_rows": target_rows,
        "target_read_receipt": {
            "pair_binding": pair,
            "content_reads": 1,
            "status": "pass",
        },
        "activation_receipt": {
            "leg": "a0",
            "activation_status": "completed",
            "activation_target_content_reads": 0,
            "literal_tuple_indices": list(_LITERAL),
            "final_block_tuple_index": 12,
            "record_count": len(index_rows),
        },
        "index_rows": index_rows,
        "dense_vectors": dense_vectors,
        "shortcut_result": {"status": "pass"},
    }


class A0XA0AnalysisTests(A0XTempTestCase):
    def _schema(self) -> dict[str, object]:
        root = Path(__file__).resolve().parents[1]
        return json.loads((root / "schemas/a0x-statistical-result.schema.json").read_text(encoding="utf-8"))

    def test_favourable_final_block_cannot_rescue_null_primary(self) -> None:
        from latent_triz.a0x_a0_analysis import analyze_a0x_a0

        result = analyze_a0x_a0(**synthetic_a0_inputs(primary_signal=0.0, final_signal=10.0))

        self.assertEqual("null", result["status"])
        self.assertGreater(result["primary"]["max_statistic_p"], 0.05)
        self.assertFalse(result["descriptive_final_block"]["rescues_primary"])

    def test_primary_has_exact_twelve_combinations(self) -> None:
        from latent_triz.a0x_a0_analysis import analyze_a0x_a0

        result = analyze_a0x_a0(**synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0))

        self.assertEqual(12, result["primary"]["multiplicity"])
        self.assertEqual(12, len(result["primary"]["combinations"]))
        self.assertEqual("positive", result["status"])
        self.assertEqual([], validate(result, self._schema()))

    def test_shortcut_refusal_is_non_statistical_non_interpretable(self) -> None:
        from latent_triz.a0x_a0_analysis import analyze_a0x_a0

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=1.0)
        inputs["shortcut_result"] = {"status": "refused"}
        result = analyze_a0x_a0(**inputs)

        self.assertEqual({"status", "reason"}, set(result))
        self.assertEqual("non_interpretable", result["status"])

    def test_analysis_has_no_target_reader_or_filesystem_capability(self) -> None:
        from latent_triz.a0x_a0_analysis import analyze_a0x_a0

        forbidden = {"target_path", "targets_path", "target_reader", "filesystem", "path", "root"}
        self.assertFalse(forbidden.intersection(inspect.signature(analyze_a0x_a0).parameters))

    def test_a0x_helpers_have_historical_lodo_and_family_parity(self) -> None:
        try:
            import numpy as np
        except ModuleNotFoundError:
            self.skipTest("numpy unavailable for historical-helper parity comparison")
        from latent_triz.a0x_a0_analysis import _family_successes, _score_operator

        matrix = np.asarray(((-2.0, 0.0), (2.0, 0.0), (-1.0, 0.5), (1.0, 0.5), (-3.0, -0.5), (3.0, -0.5)))
        domains = ("a", "a", "b", "b", "c", "c")
        self.assertTrue(np.array_equal(
            historical_score_operator(matrix, domains, alpha=1.0),
            _score_operator(matrix, domains, alpha=1.0),
        ))
        self.assertEqual(
            historical_family_successes((-1.0, 2.0, 0.5, -0.5), (0, 1, 1, 0), ("a", "a", "b", "b")),
            _family_successes((-1.0, 2.0, 0.5, -0.5), (0, 1, 1, 0), ("a", "a", "b", "b")),
        )

    def test_target_receipt_binding_must_equal_the_single_result_pair(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
        receipt = dict(inputs["target_read_receipt"])
        mismatched = pair_binding(Leg.A0, model_key="smollm2_135m")
        receipt["pair_binding"] = mismatched
        inputs["target_read_receipt"] = receipt
        with self.assertRaisesRegex(A0XA0AnalysisError, "pair binding"):
            analyze_a0x_a0(**inputs)


if __name__ == "__main__":
    unittest.main()
