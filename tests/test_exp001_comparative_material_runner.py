import json
import shutil
import tempfile
import unittest
from pathlib import Path
from tests.a0x_test_support import synthetic_comparative_root, copy_public_contract_inputs

from latent_triz.exp001_comparative_material_runner import (
    ComparativeMaterialError,
    run_comparative_material,
)
from latent_triz.exp001_comparative_report import ComparativeReportError, verify_comparative_publication


ROOT = Path(__file__).parents[1]


def _authorization(model_id: str, revision: str):
    return {
        "status": "authorized",
        "exact_models": [{"model_id": model_id, "revision": revision}],
        "operator_approval": {"granted": True},
        "permissions_requested": {
            "load_existing_pythia_once": model_id.startswith("EleutherAI/"),
            "load_existing_smollm2_once": model_id.startswith("HuggingFaceTB/"),
            "load_qwen_once_after_integrity": model_id.startswith("Qwen/"),
            "network": False,
            "generation": False,
            "sealed_target_read": "exactly_one_per_model_at_analysis_boundary",
        },
    }


class FakeAdapter:
    model_loaded = True

    def score_prompt_choice(self, prompt, label):
        return {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.4}[label]


def _targets(records):
    counters = {"transfer-blinded": 0, "lexical-control": 0, "transfer-exposed": 0}
    choices = ("A", "B", "C", "D")
    targets = []
    for record in records:
        record_id = record["record_id"]
        suffix = next((name for name in counters if record_id.endswith(name)), None)
        if suffix is None:
            targets.append({"record_id": record_id, "expected_choice": "A"})
            continue
        index = counters[suffix]
        counters[suffix] += 1
        targets.append({"record_id": record_id, "expected_choice": choices[index % 4]})
    return targets


class ComparativeMaterialRunnerTests(unittest.TestCase):
    def test_requires_admit_empty_ccp_gate_before_adapter(self):
        calls = []
        class Adapter(FakeAdapter):
            def score_prompt_choice(self, prompt, label):
                calls.append(1)
                return super().score_prompt_choice(prompt, label)
        with self.assertRaises(ComparativeMaterialError):
            run_comparative_material(root=ROOT, run_id="gate", model_id="EleutherAI/pythia-70m-deduped", revision="e93a9faa9c77e5d09219f6c868bfc7a1bd65593c", authorization=_authorization("EleutherAI/pythia-70m-deduped", "e93a9faa9c77e5d09219f6c868bfc7a1bd65593c"), ccp_gate={"resource_decision": "unknown", "admission_active": False, "queue_count": 0}, adapter=Adapter(), target_reader=_targets, analysis_plan=json.loads((ROOT / "experiments/exp001-comparative-reference/analysis-plan.json").read_text()))
        self.assertEqual(calls, [])

    def test_synthetic_run_reads_targets_once_and_publishes_terminal_package(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # CCP mounts the checkout read-only. Copy only public protocol and
            # fixtures into a writable synthetic root; no model or target
            # bytes are copied or opened.
            synthetic_comparative_root(root)
            copy_public_contract_inputs(root, tuple(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / "experiments/exp001-reference-integrated/fixtures").iterdir()
                if path.is_file()
            ))
            (root / "results/lab01/model-anatomy").mkdir(parents=True)
            shutil.copy2(ROOT / "results/lab01/model-anatomy/model_receipt.json", root / "results/lab01/model-anatomy/model_receipt.json")
            run_id = "synthetic-run-fixed"
            result = run_comparative_material(root=root, run_id=run_id, model_id="EleutherAI/pythia-70m-deduped", revision="e93a9faa9c77e5d09219f6c868bfc7a1bd65593c", authorization=_authorization("EleutherAI/pythia-70m-deduped", "e93a9faa9c77e5d09219f6c868bfc7a1bd65593c"), ccp_gate={"resource_decision": "admit", "admission_active": False, "queue_count": 0}, adapter=FakeAdapter(), target_reader=_targets, analysis_plan=json.loads((root / "experiments/exp001-comparative-reference/analysis-plan.json").read_text()))
            self.assertIn(result["status"], {"positive", "null", "failed"})
            self.assertEqual(result["access"]["target_reads"], 1)
            self.assertTrue(result["access"]["sealed_targets_accessed"])
            package = root / result["package_dir"]
            self.assertTrue((package / "execution-receipt.json").is_file())
            self.assertEqual(verify_comparative_publication(repo_root=root, package_dir=result["package_dir"])["status"], "pass")
            asset_path = root / result["external_response_asset"]["locator"]
            original = asset_path.read_bytes()
            asset_path.write_bytes(original + b"mutation")
            with self.assertRaises(ComparativeReportError):
                verify_comparative_publication(repo_root=root, package_dir=result["package_dir"])
            asset_path.write_bytes(original)
            asset_path.unlink()
            with self.assertRaises(ComparativeReportError):
                verify_comparative_publication(repo_root=root, package_dir=result["package_dir"])
            # The package verifier must also reject drift in a bound receipt.
            # Rebuild the synthetic package once, then mutate the receipt only.
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_bytes(original)
            result = run_comparative_material(root=root, run_id="synthetic-run-bound", model_id="EleutherAI/pythia-70m-deduped", revision="e93a9faa9c77e5d09219f6c868bfc7a1bd65593c", authorization=_authorization("EleutherAI/pythia-70m-deduped", "e93a9faa9c77e5d09219f6c868bfc7a1bd65593c"), ccp_gate={"resource_decision": "admit", "admission_active": False, "queue_count": 0}, adapter=FakeAdapter(), target_reader=_targets, analysis_plan=json.loads((root / "experiments/exp001-comparative-reference/analysis-plan.json").read_text()))
            bound_receipt = root / result["package_dir"] / "execution-receipt.json"
            receipt = json.loads(bound_receipt.read_text())
            receipt["access"]["target_reads"] = 2
            bound_receipt.write_text(json.dumps(receipt))
            with self.assertRaises(ComparativeReportError):
                verify_comparative_publication(repo_root=root, package_dir=result["package_dir"])
            # Leave no model or dense output content tracked by the test suite.
            shutil.rmtree(root / "artifacts", ignore_errors=True)
            shutil.rmtree(root / "results", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
