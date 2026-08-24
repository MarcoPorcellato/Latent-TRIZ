from __future__ import annotations

import inspect
import json
import hashlib
import struct
import unittest
import copy
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
    from latent_triz.a0x_a0_activations import _serialize_safetensors
    pair = pair_binding(Leg.A0, hidden_width=2)
    target_rows: list[dict[str, object]] = []
    index_rows: list[dict[str, object]] = []
    dense_vectors: dict[str, bytes] = {}
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
                    raw = struct.pack("<2f", signed * signal, float(case_number % 3))
                    dense_vectors[record_id] = raw
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
                        "vector_sha256": hashlib.sha256(raw).hexdigest(),
                        "tensor_key": record_id,
                    })
    dense_asset_bytes = _serialize_safetensors(dense_vectors, width=2)
    index_bytes = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" for row in index_rows)
    receipt = {
        "artifact_class": "a0x-activation-receipt",
        "pair_binding": pair,
        "leg": "a0",
        "activation_status": "completed",
        "activation_target_content_reads": 0,
        "literal_tuple_indices": list(_LITERAL),
        "final_block_tuple_index": 12,
        "record_count": len(index_rows),
        "dense": {"path": "activations.safetensors", "sha256": hashlib.sha256(dense_asset_bytes).hexdigest(), "bytes": len(dense_asset_bytes), "format": "safetensors"},
        "index": {"path": "representations-index.jsonl", "sha256": hashlib.sha256(index_bytes).hexdigest(), "bytes": len(index_bytes)},
        "planned_dense_bound": pair["dense_bound"],
    }
    receipt_sha = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "pair_binding": pair,
        "target_rows": target_rows,
        "target_read_receipt": {
            "pair_binding": pair,
            "content_reads": 1,
            "status": "pass",
            "activation_receipt_sha256": receipt_sha,
            "dense_sha256": receipt["dense"]["sha256"],
            "index_sha256": receipt["index"]["sha256"],
        },
        "activation_receipt": receipt,
        "index_bytes": index_bytes,
        "dense_asset_bytes": dense_asset_bytes,
        "shortcut_result": {"status": "pass"},
    }


def rebind_asset_receipts(inputs: dict[str, object]) -> None:
    """Rebind a synthetic receipt after an intentional immutable-byte mutation."""
    activation = inputs["activation_receipt"]
    dense = inputs["dense_asset_bytes"]
    index = inputs["index_bytes"]
    target = inputs["target_read_receipt"]
    assert isinstance(activation, dict) and isinstance(target, dict)
    assert isinstance(dense, bytes) and isinstance(index, bytes)
    activation["dense"]["sha256"] = hashlib.sha256(dense).hexdigest()
    activation["dense"]["bytes"] = len(dense)
    activation["index"]["sha256"] = hashlib.sha256(index).hexdigest()
    activation["index"]["bytes"] = len(index)
    target["activation_receipt_sha256"] = hashlib.sha256(json.dumps(activation, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    target["dense_sha256"] = activation["dense"]["sha256"]
    target["index_sha256"] = activation["index"]["sha256"]


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
        self.assertEqual(
            "9af1622cda37821018baccfb7de0d83a6b5da5a1c3887fa47892e506f989a1af",
            result["primary"]["null_maxima_sha256"],
        )
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

    def test_activation_receipt_pair_must_equal_the_single_result_pair(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
        activation = inputs["activation_receipt"]
        assert isinstance(activation, dict)
        activation["pair_binding"] = pair_binding(Leg.A0, model_key="smollm2_135m", hidden_width=2)
        rebind_asset_receipts(inputs)
        with self.assertRaisesRegex(A0XA0AnalysisError, "activation receipt pair binding"):
            analyze_a0x_a0(**inputs)

    def test_raw_asset_and_target_link_drift_are_rejected(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        for label, mutate in (
            ("dense", lambda value: value.__setitem__("dense_asset_bytes", value["dense_asset_bytes"] + b"x")),
            ("index", lambda value: value.__setitem__("index_bytes", value["index_bytes"] + b"\n")),
            ("target-link", lambda value: value["target_read_receipt"].__setitem__("activation_receipt_sha256", "0" * 64)),
        ):
            with self.subTest(label=label):
                inputs = copy.deepcopy(synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0))
                mutate(inputs)
                with self.assertRaises(A0XA0AnalysisError):
                    analyze_a0x_a0(**inputs)

    def test_index_identity_width_and_tensor_set_mismatches_are_rejected(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0, _parse_safetensors
        from latent_triz.a0x_a0_activations import _serialize_safetensors

        for label, mutate in (
            ("vector-sha", lambda rows: rows[0].__setitem__("vector_sha256", "0" * 64)),
            ("wrong-width", lambda rows: rows[0].__setitem__("vector_dim", 3)),
            ("missing-key", lambda rows: rows[0].__setitem__("tensor_key", "absent-tensor")),
        ):
            with self.subTest(label=label):
                inputs = copy.deepcopy(synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0))
                rows = [json.loads(line) for line in inputs["index_bytes"].decode("utf-8").splitlines()]
                mutate(rows)
                inputs["index_bytes"] = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" for row in rows)
                rebind_asset_receipts(inputs)
                with self.assertRaises(A0XA0AnalysisError):
                    analyze_a0x_a0(**inputs)

        inputs = copy.deepcopy(synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0))
        vectors = _parse_safetensors(inputs["dense_asset_bytes"], 2)
        vectors["unexpected-tensor"] = struct.pack("<2f", 0.0, 0.0)
        inputs["dense_asset_bytes"] = _serialize_safetensors(vectors, width=2)
        rebind_asset_receipts(inputs)
        with self.assertRaisesRegex(A0XA0AnalysisError, "2400-vector"):
            analyze_a0x_a0(**inputs)


if __name__ == "__main__":
    unittest.main()
