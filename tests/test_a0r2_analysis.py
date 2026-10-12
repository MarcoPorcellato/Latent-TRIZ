from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz import a0r2_analysis as analysis
from latent_triz.validator import validate

try:
    import numpy as np
except ImportError:  # dependency-free repository gate
    np = None


@unittest.skipIf(np is None, "numpy is optional outside the A0-R2 runtime")
class A0R2AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = ROOT
        self.protocol_path = self.root / "experiments/a0r2-independent-model/study-protocol.json"
        self.shortcut_path = self.root / "results/a0r1/preoutput/shortcuts.json"
        self.protocol = json.loads(self.protocol_path.read_text(encoding="utf-8"))
        self.shortcuts = json.loads(self.shortcut_path.read_text(encoding="utf-8"))
        self.statistics_schema = json.loads((self.root / "schemas/a0r2-statistical-result.schema.json").read_text(encoding="utf-8"))

    @staticmethod
    def _model_payload() -> dict[str, object]:
        model = copy.deepcopy(json.loads((ROOT / "experiments/a0r2-independent-model/study-protocol.json").read_text(encoding="utf-8"))["model"])
        model.pop("integrity_receipt_sha256", None)
        model.pop("feasibility_receipt_sha256", None)
        return model

    def test_fixture_never_opens_repository_sealed_targets(self) -> None:
        forbidden = (ROOT / "data/a0r1/targets/sealed.jsonl").absolute()
        attempted: list[str] = []
        original_open = Path.open

        def deny_repository_target_open(path_obj: Path, *args: object, **kwargs: object):
            if path_obj.absolute() == forbidden:
                attempted.append(str(path_obj))
                raise AssertionError("analysis fixture must not open repository sealed targets")
            return original_open(path_obj, *args, **kwargs)

        with patch.object(Path, "open", new=deny_repository_target_open):
            with tempfile.TemporaryDirectory() as directory:
                self._build_fixture(Path(directory))

        self.assertEqual([], attempted)

    def _build_fixture(self, root: Path, *, primary_value: float = 0.9, surface_value: float = 0.1) -> dict[str, Path | dict[str, dict[str, int]]]:
        r1_result_source = self.root / "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/statistical-result.json"
        r1_result = json.loads(r1_result_source.read_text(encoding="utf-8"))
        domain_names = sorted(r1_result["primary"]["domain_direction_successes"])
        self.assertEqual(6, len(domain_names))
        target_rows = [
            {
                "case_id": f"synthetic_case_{family_index:02d}_{label}",
                # Keep only the domain vocabulary shared with the fixed R1 comparator;
                # case, family, and operator-label data remain synthetic.
                "domain": domain_names[family_index // 4],
                "problem_family_id": f"synthetic_family_{family_index:02d}",
                "operator_proxy_family": "segmentation_like" if label == 1 else "inversion_like",
            }
            for family_index in range(24)
            for label in (0, 1)
        ]
        positive_families = {f"synthetic_family_{family_index:02d}" for family_index in range(7, 24)}

        case_ids = sorted(row["case_id"] for row in target_rows)
        target_by_case = {str(row["case_id"]): row for row in target_rows}
        labels = [1 if target_by_case[case_id]["operator_proxy_family"] == "segmentation_like" else 0 for case_id in case_ids]
        signed = [1.0 if label == 1 else -1.0 for label in labels]

        dense_rows: dict[str, list[float]] = {}
        index_rows: list[dict[str, object]] = []
        positive_scores = []
        baseline_scores = []
        for case_id in case_ids:
            family_id = str(target_by_case[case_id]["problem_family_id"])
            label = int(labels[len(positive_scores)])
            family_positive = family_id in positive_families
            if family_positive:
                positive_scores.append(1.0 if label == 1 else -1.0)
            else:
                positive_scores.append(-1.0 if label == 1 else 1.0)
            baseline_scores.append(-1.0)

        def make_operator(scores: list[float]):
            operator = []
            for score in scores:
                operator.append([float(score) * signed_value / len(signed) for signed_value in signed])
            return np.asarray(operator, dtype=np.float64)

        primary_operator = make_operator(positive_scores)
        surface_operator = make_operator(baseline_scores)

        for case_id in case_ids:
            family_id = str(target_by_case[case_id]["problem_family_id"])
            domain = analysis._case_domain(target_by_case[case_id])
            for tuple_index in analysis.DESCRIPTIVE_TUPLE_INDICES:
                for view, token_site, fill_value in (
                    ("problem_only", "sentinel", surface_value),
                    ("problem_plus_transformation", "mean_transformation_span", primary_value),
                ):
                    record_id = f"{case_id}::{view}::{token_site}::{tuple_index}"
                    vector = [float(fill_value) for _ in range(960)]
                    dense_rows[record_id] = vector
                    index_rows.append(
                        {
                            "case_id": case_id,
                            "problem_family_id": family_id,
                            "domain": domain,
                            "view": view,
                            "tuple_index": tuple_index,
                            "token_site": token_site,
                            "record_id": record_id,
                            "hidden_size": 960,
                            "dtype": "float32",
                            "vector_sha256": analysis._canonical_json_sha256(vector),
                        }
                    )
        targets_path = root / "targets.jsonl"
        index_path = root / "activation-index.jsonl"
        dense_path = root / "dense.json"
        summary_path = root / "summary.json"
        output_path = root / "analysis.json"

        targets_path.write_text(
            "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in target_rows),
            encoding="utf-8",
        )

        repo_root = root / "analysis-root"
        protocol_path = repo_root / "experiments/a0r2-independent-model/study-protocol.json"
        protocol_schema_path = repo_root / "schemas/a0r2-study-protocol.schema.json"
        shortcut_path = repo_root / "results/a0r1/preoutput/shortcuts.json"
        r1_result_path = repo_root / "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/statistical-result.json"
        protocol_path.parent.mkdir(parents=True)
        protocol_schema_path.parent.mkdir(parents=True)
        shortcut_path.parent.mkdir(parents=True)
        r1_result_path.parent.mkdir(parents=True)
        shortcut_path.write_bytes(self.shortcut_path.read_bytes())
        r1_result_path.write_bytes(r1_result_source.read_bytes())
        protocol = copy.deepcopy(self.protocol)
        protocol["inputs"]["sealed_targets_sha256"] = analysis._sha256(targets_path)
        protocol["inputs"]["shortcuts_sha256"] = analysis._sha256(shortcut_path)
        protocol_path.write_text(json.dumps(protocol, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        protocol_schema = json.loads(analysis.PROTOCOL_SCHEMA_PATH.read_text(encoding="utf-8"))
        schema_inputs = protocol_schema["properties"]["inputs"]["properties"]
        schema_inputs["sealed_targets_sha256"]["const"] = protocol["inputs"]["sealed_targets_sha256"]
        schema_inputs["shortcuts_sha256"]["const"] = protocol["inputs"]["shortcuts_sha256"]
        protocol_schema_path.write_text(
            json.dumps(protocol_schema, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        index_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in index_rows) + "\n", encoding="utf-8")
        dense_path.write_text(json.dumps(dense_rows, sort_keys=True) + "\n", encoding="utf-8")
        summary_path.write_text(json.dumps({"summary": True}, sort_keys=True) + "\n", encoding="utf-8")

        receipt = {
            "artifact_class": "a0r2-activation-receipt",
            "status": "pass",
            "created_at": self.protocol["created_at"],
            "scientific_status": "exploratory",
            "empirical": True,
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
            "protocol_id": self.protocol["protocol_id"],
            "model": self._model_payload(),
            "runtime": {
                "device": "cpu",
                "torch_dtype": "float32",
                "network_access": False,
                "local_files_only": True,
                "generation": False,
                "fast_offsets_required": True,
            },
            "activation": {
                "tuple_index": 32,
                "primary_semantics": "final_transformer_block_output",
                "token_site": "mean_transformation_span",
                "primary_view": "problem_plus_transformation",
                "surface_baseline_view": "problem_only",
                "surface_baseline_token_site": "sentinel",
                "hidden_states_count": 33,
                "hidden_size": 960,
                "output_content_retained": True,
            },
            "access": {
                "model_loaded": True,
                "model_output_accessed": True,
                "sealed_targets_accessed": False,
                "claim_promotion": False,
            },
            "input_hashes": {
                "protocol_sha256": analysis._sha256(self.protocol_path),
                "r1_protocol_sha256": self.protocol["inputs"]["r1_protocol_sha256"],
                "r1_freeze_manifest_sha256": self.protocol["inputs"]["r1_freeze_manifest_sha256"],
                "corpus_manifest_sha256": self.protocol["inputs"]["corpus_manifest_sha256"],
                "cases_sha256": self.protocol["inputs"]["cases_sha256"],
                "sealed_targets_sha256": self.protocol["inputs"]["sealed_targets_sha256"],
                "shortcuts_sha256": self.protocol["inputs"]["shortcuts_sha256"],
                "integrity_receipt_sha256": self.protocol["model"]["integrity_receipt_sha256"],
                "feasibility_receipt_sha256": self.protocol["model"]["feasibility_receipt_sha256"],
            },
            "output_bundle": {
                "reports": ["report.md"],
                "dense_locator": "artifacts/a0r2/a0r2-run/activations.json",
                "artifact_hashes": {
                    "summary_sha256": analysis._sha256(summary_path),
                    "index_sha256": analysis._sha256(index_path),
                    "dense_sha256": analysis._sha256(dense_path),
                },
                "records": 1920,
                "hidden_size": 960,
                "exact_head": "4" * 40,
            },
        }
        receipt["input_hashes"]["protocol_sha256"] = analysis._sha256(protocol_path)
        receipt["input_hashes"]["sealed_targets_sha256"] = protocol["inputs"]["sealed_targets_sha256"]
        receipt["input_hashes"]["shortcuts_sha256"] = protocol["inputs"]["shortcuts_sha256"]
        receipt_path = root / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

        return {
            "repo_root": repo_root,
            "protocol_path": protocol_path,
            "protocol_schema_path": protocol_schema_path,
            "shortcut_path": shortcut_path,
            "r1_result_path": r1_result_path,
            "targets_path": targets_path,
            "index_path": index_path,
            "dense_path": dense_path,
            "output_path": output_path,
            "receipt_path": receipt_path,
            "primary_operator": primary_operator,
            "surface_operator": surface_operator,
            "case_ids": case_ids,
            "labels": labels,
            "positive_families": positive_families,
        }

    def _run_analysis(
        self,
        fixture: dict[str, Path | dict[str, dict[str, int]] | list[str] | set[str]],
        *,
        shortcut_path: Path | None = None,
        protocol_path: Path | None = None,
        score_mean_threshold: float = 0.5,
    ) -> dict[str, object]:
        primary_operator = fixture["primary_operator"]
        surface_operator = fixture["surface_operator"]

        def fake_score_operator(matrix, _domains, *, alpha: float):  # noqa: ARG001
            del alpha
            return primary_operator if float(matrix.mean()) > score_mean_threshold else surface_operator

        kwargs = {
            "protocol_path": protocol_path or fixture["protocol_path"],
            "activation_receipt_path": fixture["receipt_path"],
            "activation_index_path": fixture["index_path"],
            "dense_path": fixture["dense_path"],
            "targets_path": fixture["targets_path"],
            "output_path": fixture["output_path"],
            "shortcut_path": shortcut_path or fixture["shortcut_path"],
            "r1_result_path": fixture["r1_result_path"],
        }

        with patch.object(analysis, "REPO_ROOT", fixture["repo_root"]), patch.object(
            analysis, "PROTOCOL_SCHEMA_PATH", fixture["protocol_schema_path"]
        ):
            with patch.object(analysis, "_score_operator", side_effect=fake_score_operator):
                payload = analysis.analyze_a0r2(**kwargs)
        self.assertTrue(fixture["output_path"].exists())
        return payload

    def test_canonical_protocol_copy_is_positive_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build_fixture(Path(directory))
            first = self._run_analysis(fixture)
            self.assertEqual("positive", first["status"])
            self.assertEqual([], validate(first, self.statistics_schema))
            self.assertEqual(self.protocol["created_at"], first["created_at"])
            self.assertEqual(17, first["statistics"]["family_successes"])
            self.assertEqual(4, first["statistics"]["successful_domain_directions"])
            self.assertLessEqual(first["statistics"]["primary_permutation_p"], 0.05)
            self.assertGreater(first["statistics"]["macro_f1_margin_over_surface"], 0.1)
            self.assertEqual(["report.md"], first["result_bundle"]["reports"])
            self.assertEqual("4" * 40, first["result_bundle"]["exact_head"])
            self.assertEqual(analysis._canonical_json_sha256(first["descriptive_results"]["primary"]), first["artifact_hashes"]["primary_sha256"])
            self.assertFalse((fixture["output_path"].parent / "report.md").exists())
            self.assertEqual(
                {
                    "model_loaded": True,
                    "model_output_accessed": True,
                    "sealed_targets_accessed": True,
                    "claim_promotion": False,
                },
                first["access"],
            )

            fixture["output_path"].unlink()
            second = self._run_analysis(fixture)
            self.assertEqual(first, second)

    def test_no_target_read_on_prevalidation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build_fixture(Path(directory))
            receipt = json.loads(fixture["receipt_path"].read_text(encoding="utf-8"))
            receipt["input_hashes"]["protocol_sha256"] = "0" * 64
            fixture["receipt_path"].write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

            target_reads = 0
            target_opens = 0
            original_read_bytes = analysis.Path.read_bytes
            original_open = analysis.Path.open

            def counted_open(path_obj: Path, *args, **kwargs):
                nonlocal target_opens
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_opens += 1
                return original_open(path_obj, *args, **kwargs)

            def counted_read_bytes(path_obj: Path):
                nonlocal target_reads
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_reads += 1
                return original_read_bytes(path_obj)

            with patch.object(analysis.Path, "open", new=counted_open), patch.object(analysis.Path, "read_bytes", new=counted_read_bytes):
                with self.assertRaisesRegex(analysis.A0R2AnalysisError, "protocol hash mismatch"):
                    self._run_analysis(fixture)
            self.assertEqual(0, target_reads)
            self.assertEqual(0, target_opens)

    def test_reads_sealed_targets_exactly_once_at_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build_fixture(Path(directory))
            target_reads = 0
            target_opens = 0
            original_read_bytes = analysis.Path.read_bytes
            original_open = analysis.Path.open

            def counted_open(path_obj: Path, *args, **kwargs):
                nonlocal target_opens
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_opens += 1
                return original_open(path_obj, *args, **kwargs)

            def counted_read_bytes(path_obj: Path):
                nonlocal target_reads
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_reads += 1
                return original_read_bytes(path_obj)

            with patch.object(analysis.Path, "open", new=counted_open), patch.object(analysis.Path, "read_bytes", new=counted_read_bytes):
                payload = self._run_analysis(fixture)
            self.assertEqual("positive", payload["status"])
            self.assertEqual(1, target_reads)
            self.assertEqual(1, target_opens)

    def test_dense_hash_failure_precedes_target_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build_fixture(Path(directory))
            fixture["dense_path"].write_text("{}\n", encoding="utf-8")
            target_reads = 0
            original_read_bytes = analysis.Path.read_bytes

            def counted_read_bytes(path_obj: Path):
                nonlocal target_reads
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_reads += 1
                return original_read_bytes(path_obj)

            with patch.object(analysis.Path, "read_bytes", new=counted_read_bytes):
                with self.assertRaisesRegex(analysis.A0R2AnalysisError, "dense"):
                    self._run_analysis(fixture)
            self.assertEqual(0, target_reads)

    def test_shortcut_non_interpretable_short_circuits_without_target_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build_fixture(Path(directory))
            receipt = json.loads(fixture["receipt_path"].read_text(encoding="utf-8"))
            fixture["receipt_path"].write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

            target_reads = 0
            target_opens = 0
            original_read_bytes = analysis.Path.read_bytes
            original_open = analysis.Path.open

            def counted_open(path_obj: Path, *args, **kwargs):
                nonlocal target_opens
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_opens += 1
                return original_open(path_obj, *args, **kwargs)

            def counted_read_bytes(path_obj: Path):
                nonlocal target_reads
                if path_obj.resolve() == fixture["targets_path"].resolve():
                    target_reads += 1
                return original_read_bytes(path_obj)

            with patch.object(analysis, "_shortcut_refusal", return_value="non_interpretable"), patch.object(
                analysis.Path, "open", new=counted_open
            ), patch.object(analysis.Path, "read_bytes", new=counted_read_bytes):
                payload = self._run_analysis(
                    fixture,
                )
            self.assertEqual("non_interpretable", payload["status"])
            self.assertEqual(0, target_reads)
            self.assertEqual(0, target_opens)

    def test_refuses_to_overwrite_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._build_fixture(Path(directory))
            fixture["output_path"].write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(analysis.A0R2AnalysisError, "refusing to overwrite"):
                self._run_analysis(fixture)


if __name__ == "__main__":
    unittest.main()
