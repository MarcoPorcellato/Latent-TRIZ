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
from latent_triz.a0x_contract import Leg, LegFreezeBinding, PairBinding, sha256_file
from latent_triz.validator import validate
from tests.a0x_test_support import A0XTempTestCase, authorization_documents, pair_binding, sha


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
    chain = authorization_documents(pair)[2]
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
    common = {"empirical": True, "scientific_status": "exploratory", "evidence_eligible": False, "expert_validated": False, "claim_ids": []}
    receipt = {
        "artifact_class": "a0x-activation-receipt",
        **common,
        "pair_binding": pair,
        "authorization_chain": chain,
        "leg": "a0",
        "created_at": "2026-08-24T00:00:00Z",
        "activation_status": "completed",
        "activation_target_content_reads": 0,
        "literal_tuple_indices": list(_LITERAL),
        "final_block_tuple_index": 12,
        "record_count": len(index_rows),
        "dense": {"path": "activations.safetensors", "sha256": hashlib.sha256(dense_asset_bytes).hexdigest(), "bytes": len(dense_asset_bytes), "format": "safetensors"},
        "index": {"path": "representations-index.jsonl", "sha256": hashlib.sha256(index_bytes).hexdigest(), "bytes": len(index_bytes)},
        "planned_dense_bound": pair["dense_bound"],
        "activation_stage_occupancy": {"artifact_class": "a0x-activation-stage-occupancy-receipt", **common, "pair_binding": pair, "authorization_chain": chain, "leg": "a0", "occupancy_scope": "activation_stage", "included_paths": ["activations.safetensors", "representations-index.jsonl"], "actual_total_bytes": len(dense_asset_bytes) + len(index_bytes), "cap_bytes": 33554432},
        "activation_stage_occupancy_sha256": sha(31),
        "occupancy_checkpoints": [],
    }
    activation_receipt_bytes = _canonical_receipt_bytes(receipt)
    target_receipt = {
        "artifact_class": "a0x-target-read-receipt", **common, "pair_binding": pair,
        "authorization_chain": chain,
        "selection_corpus_sha256": sha(30),
        "content_reads": 1, "status": "pass", "observed_sha256": sha(32),
        "activation_receipt_sha256": hashlib.sha256(activation_receipt_bytes).hexdigest(),
        "dense_sha256": receipt["dense"]["sha256"], "index_sha256": receipt["index"]["sha256"],
    }
    return {
        "pair_binding": pair,
        "authorization_chain": chain,
        "target_rows": target_rows,
        "target_read_receipt_bytes": _canonical_receipt_bytes(target_receipt),
        "activation_receipt_bytes": activation_receipt_bytes,
        "index_bytes": index_bytes,
        "dense_asset_bytes": dense_asset_bytes,
        "shortcut_result": {"status": "pass"},
}


def _canonical_receipt_bytes(value: dict[str, object]) -> bytes:
    """Task 5/6 receipt encoding: canonical UTF-8 JSON followed by one LF."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"


def rebind_asset_receipts(inputs: dict[str, object]) -> None:
    """Rebind a synthetic receipt after an intentional immutable-byte mutation."""
    activation_bytes = inputs["activation_receipt_bytes"]
    dense = inputs["dense_asset_bytes"]
    index = inputs["index_bytes"]
    target_bytes = inputs["target_read_receipt_bytes"]
    assert isinstance(activation_bytes, bytes) and isinstance(target_bytes, bytes)
    activation = json.loads(activation_bytes)
    target = json.loads(target_bytes)
    assert isinstance(dense, bytes) and isinstance(index, bytes)
    activation["dense"]["sha256"] = hashlib.sha256(dense).hexdigest()
    activation["dense"]["bytes"] = len(dense)
    activation["index"]["sha256"] = hashlib.sha256(index).hexdigest()
    activation["index"]["bytes"] = len(index)
    inputs["activation_receipt_bytes"] = _canonical_receipt_bytes(activation)
    target["activation_receipt_sha256"] = hashlib.sha256(inputs["activation_receipt_bytes"]).hexdigest()
    target["dense_sha256"] = activation["dense"]["sha256"]
    target["index_sha256"] = activation["index"]["sha256"]
    inputs["target_read_receipt_bytes"] = _canonical_receipt_bytes(target)


def receipt_object(inputs: dict[str, object], key: str) -> dict[str, object]:
    value = inputs[key]
    assert isinstance(value, bytes)
    parsed = json.loads(value)
    assert isinstance(parsed, dict)
    return parsed


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
        self.assertEqual(12, result["score_quantization_decimals"])
        self.assertEqual(
            "1f50742b974a580c45e1fe39341a73d9a384698d5aaa1fcd745948e892d2a5ce",
            result["primary"]["null_maxima_sha256"],
        )
        self.assertEqual([], validate(result, self._schema()))

    def test_analysis_requires_one_exact_authorization_chain_across_both_receipts(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
        result = analyze_a0x_a0(**inputs)
        self.assertEqual(inputs["authorization_chain"], result["authorization_chain"])

        target = receipt_object(inputs, "target_read_receipt_bytes")
        target["authorization_chain"] = authorization_documents(
            pair_binding(Leg.A0, model_key="smollm2_135m", hidden_width=2)
        )[2]
        inputs["target_read_receipt_bytes"] = _canonical_receipt_bytes(target)
        with self.assertRaisesRegex(A0XA0AnalysisError, "authorization chain"):
            analyze_a0x_a0(**inputs)

    def test_quantized_null_schedule_matches_numpy_and_pure_lodo_backends(self) -> None:
        try:
            import numpy  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest("numpy unavailable for backend-parity comparison")
        from latent_triz.a0x_a0_analysis import _SITES, _materialize_combos, _null_maxima, _score_operator, _score_operator_pure, _target_metadata

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
        receipt = json.loads(inputs["activation_receipt_bytes"])
        pair = pair_binding(Leg.A0, hidden_width=2)
        cases, labels, families, domains = _target_metadata(inputs["target_rows"])
        combos, _ = _materialize_combos(inputs["index_bytes"], inputs["dense_asset_bytes"], cases, PairBinding.from_mapping(pair), receipt)
        primary = [("problem_plus_transformation", index, site) for index in _LITERAL for site in _SITES]
        numpy_operators = {combo: _score_operator(combos[combo], domains, alpha=1.0) for combo in primary}
        pure_operators = {combo: _score_operator_pure(combos[combo], domains, alpha=1.0) for combo in primary}
        self.assertEqual(
            _null_maxima(numpy_operators, primary, labels, families, seed=20260814, budget=199),
            _null_maxima(pure_operators, primary, labels, families, seed=20260814, budget=199),
        )

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
        receipt = receipt_object(inputs, "target_read_receipt_bytes")
        mismatched = pair_binding(Leg.A0, model_key="smollm2_135m")
        receipt["pair_binding"] = mismatched
        inputs["target_read_receipt_bytes"] = _canonical_receipt_bytes(receipt)
        with self.assertRaisesRegex(A0XA0AnalysisError, "pair binding"):
            analyze_a0x_a0(**inputs)

    def test_activation_receipt_pair_must_equal_the_single_result_pair(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
        activation = receipt_object(inputs, "activation_receipt_bytes")
        activation["pair_binding"] = pair_binding(Leg.A0, model_key="smollm2_135m", hidden_width=2)
        inputs["activation_receipt_bytes"] = _canonical_receipt_bytes(activation)
        rebind_asset_receipts(inputs)
        with self.assertRaisesRegex(A0XA0AnalysisError, "activation receipt pair binding"):
            analyze_a0x_a0(**inputs)

    def test_raw_asset_and_target_link_drift_are_rejected(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        for label, mutate in (
            ("dense", lambda value: value.__setitem__("dense_asset_bytes", value["dense_asset_bytes"] + b"x")),
            ("index", lambda value: value.__setitem__("index_bytes", value["index_bytes"] + b"\n")),
            ("target-link", lambda value: value.__setitem__("target_read_receipt_bytes", _canonical_receipt_bytes({**receipt_object(value, "target_read_receipt_bytes"), "activation_receipt_sha256": "0" * 64}))),
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

    def test_registered_receipt_schemas_reject_missing_envelope_and_completed_fields(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        mutations = (
            ("activation-artifact", "activation_receipt_bytes", "artifact_class"),
            ("activation-checkpoints", "activation_receipt_bytes", "occupancy_checkpoints"),
            ("target-selection", "target_read_receipt_bytes", "selection_corpus_sha256"),
        )
        for label, key, field in mutations:
            with self.subTest(label=label):
                inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
                receipt = receipt_object(inputs, key)
                del receipt[field]
                inputs[key] = _canonical_receipt_bytes(receipt)
                with self.assertRaisesRegex(A0XA0AnalysisError, "strict registered schema"):
                    analyze_a0x_a0(**inputs)

    def test_activation_receipt_requires_the_exact_persisted_trailing_newline(self) -> None:
        from latent_triz.a0x_a0_analysis import A0XA0AnalysisError, analyze_a0x_a0

        inputs = synthetic_a0_inputs(primary_signal=1.0, final_signal=0.0)
        payload = inputs["activation_receipt_bytes"]
        assert isinstance(payload, bytes)
        inputs["activation_receipt_bytes"] = payload.rstrip(b"\n")
        with self.assertRaisesRegex(A0XA0AnalysisError, "UTF-8 JSON ending in one LF"):
            analyze_a0x_a0(**inputs)

    def test_task5_to_task6_to_task7_exact_receipt_bytes_integrate(self) -> None:
        from latent_triz.a0x_a0_analysis import analyze_a0x_a0
        from latent_triz.a0x_a0_activations import extract_a0x_a0
        from latent_triz.a0x_execution import OneShotTargetReader, _selection_capability
        from tests.test_a0x_activations import public_cases, selection_manifest, synthetic_hidden_adapter

        pair = pair_binding(Leg.A0, hidden_width=8)
        chain = authorization_documents(pair)[2]
        artifacts = extract_a0x_a0(
            adapter=synthetic_hidden_adapter(layers=13, width=8), cases=public_cases(),
            selection=selection_manifest(), pair_binding=pair, output_dir=self.temp_path / "activation",
            authorization_chain=chain, created_at="2026-08-24T00:00:00Z",
        )
        activation_bytes = artifacts.receipt_path.read_bytes()
        self.assertTrue(activation_bytes.endswith(b"\n"))
        freeze = LegFreezeBinding(Leg.A0, "a0x-a0-replication-v1", sha(70), sha(71), sha(3), sha(72), sha(90), "a" * 40)
        selection = _selection_capability(
            leg_freeze=freeze, source_path=Path("experiments/a0x-six-model/a0-selection-manifest.json"),
            source_sha256=sha(90), case_ids=tuple(f"case-{index:02d}" for index in range(48)), require_file_exact=False,
        )
        target_rows = [{"case_id": f"case-{index:02d}", "problem_family_id": f"family-{index // 2:02d}", "domain": f"domain-{index // 8}", "operator_proxy_family": "segmentation_like" if index % 2 else "inversion_like"} for index in range(48)]
        target_path = self.temp_path / "synthetic-targets.jsonl"
        target_path.write_bytes(b"".join(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n" for row in target_rows))
        target_receipt_path = self.temp_path / "target-receipt.json"
        reader = OneShotTargetReader(
            path=target_path, expected_sha256=sha256_file(target_path), receipt_path=target_receipt_path,
            pair_binding=pair, selection=selection,
            activation_receipt_sha256=hashlib.sha256(activation_bytes).hexdigest(),
            dense_sha256=sha256_file(artifacts.dense_path), index_sha256=sha256_file(artifacts.index_path),
            authorization_chain=chain,
        )
        selected_rows, _receipt = reader.read_jsonl_once()
        result = analyze_a0x_a0(
            pair_binding=pair, target_rows=selected_rows,
            activation_receipt_bytes=activation_bytes, target_read_receipt_bytes=target_receipt_path.read_bytes(),
            dense_asset_bytes=artifacts.dense_path.read_bytes(), index_bytes=artifacts.index_path.read_bytes(),
            shortcut_result={"status": "pass"}, authorization_chain=chain,
        )
        self.assertIn(result["status"], {"positive", "null"})


if __name__ == "__main__":
    unittest.main()
