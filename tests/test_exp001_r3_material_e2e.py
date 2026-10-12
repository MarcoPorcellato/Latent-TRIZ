"""No-model end-to-end package test for the EXP-001 R3 material boundary.

This test deliberately exercises the production runner, report writer, and
package verifier in a copied repository.  The adapter and sealed-key reader
are deterministic test capabilities; no model, target file, network, or CCP
is used.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from tests.a0x_test_support import synthetic_r3_root

from latent_triz.exp001_r3_implementation import build_implementation_binding
from latent_triz.exp001_r3_material_runner import run_material
from latent_triz.exp001_r3_report import R3ReportError, verify_r3_report_package
from latent_triz.exp001_r3_runner import run_analysis_boundary


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "HuggingFaceTB/SmolLM2-360M"
REVISION = "f8027fd0eaeea54caa13c31d31b9fdc459c38b49"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


class _FakeAdapter:
    model_loaded = True

    def score_prompt_choice(self, prompt: str, label: str) -> float:
        # A deterministic finite score is sufficient to exercise all 340
        # teacher-forced calls without loading a runtime or generating text.
        return float("ABCD".index(label))


class MaterialEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        synthetic_r3_root(self.root)

        protocol_path = self.root / "experiments/exp001-reference-integrated/protocol.json"
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        protocol["protocol_status"] = "frozen"
        protocol_path.write_text(json.dumps(protocol, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

        # These are copied, synthetic A0 receipts: preflight checks identity
        # and terminal compatibility only.  They are not model execution.
        receipt_dir = self.root / "results/a0r2/preexecution/smollm2-360m-f8027fd0"
        identity = {"id": MODEL_ID, "revision": REVISION}
        _json(receipt_dir / "integrity-receipt.json", {"status": "pass", "integrity_status": "integrity_verified", "model": identity})
        _json(receipt_dir / "feasibility-receipt.json", {"status": "compatible", "compatibility": {"compatible": True}, "model": identity})

        self.authorization_path = self.root / "results/exp001-r3/preexecution/authorization.json"
        _json(self.authorization_path, {"artifact_class": "test-authorization", "model": identity})
        self.authorization = {"status": "authorized", "model_id": MODEL_ID, "revision": REVISION, "one_run": True}
        self.provenance = {}
        for name, value in (("authorization", self.authorization_path),
                            ("integrity", receipt_dir / "integrity-receipt.json"),
                            ("feasibility", receipt_dir / "feasibility-receipt.json")):
            self.provenance[name] = {"path": value.relative_to(self.root).as_posix(), "sha256": _sha(value)}
        binding = build_implementation_binding(self.root)
        self.binding_path = self.root / "results/exp001-r3/preexecution/implementation-binding.json"
        _json(self.binding_path, binding)
        self.provenance["implementation"] = {"path": self.binding_path.relative_to(self.root).as_posix(), "sha256": _sha(self.binding_path)}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _targets(self, records):
        # Six of each choice for each primary condition, with exposed and
        # blinded transfer labels agreeing as required by the key validator.
        primary = [r for r in records if "unit_id" in r]
        targets = {}
        for suffix in ("transfer-blinded", "lexical-control"):
            rows = [r for r in primary if r["record_id"].endswith(suffix)]
            for index, row in enumerate(rows):
                targets[row["record_id"]] = "ABCD"[index % 4]
        for row in primary:
            if row["record_id"].endswith("transfer-exposed"):
                twin = row["record_id"].replace("-transfer-exposed", "-transfer-blinded")
                targets[row["record_id"]] = targets[twin]
        for row in records:
            targets.setdefault(row["record_id"], "A")
        return [{"record_id": key, "expected_choice": value} for key, value in targets.items()]

    def _run(self, run_id: str):
        return run_material(
            root=self.root,
            run_id=run_id,
            authorization=self.authorization,
            adapter=_FakeAdapter(),
            target_reader=self._targets,
            created_at="2026-08-18T00:00:00Z",
            resource_probe=lambda: {"wall_seconds": 1.0, "peak_rss_bytes": 1024},
            provenance_artifacts=self.provenance,
        )

    def test_real_runner_writer_and_verifier_round_trip(self) -> None:
        result = self._run("e2e")
        self.assertEqual(result["status"], "null")
        package = self.root / "results/exp001-r3/e2e"
        manifest = verify_r3_report_package(package_dir="results/exp001-r3/e2e", repo_root=self.root)
        self.assertEqual(manifest["terminal_status"], "null")
        self.assertTrue((package / "report.md").is_file())
        self.assertEqual(json.loads((package / "response-index.json").read_text())["record_count"], 85)

    def test_external_response_asset_mutation_fails_closed(self) -> None:
        self._run("asset-mutation")
        asset = self.root / "artifacts/exp001-r3/asset-mutation/response-scores.json"
        asset.write_text(asset.read_text(encoding="utf-8") + "mutated\n", encoding="utf-8")
        with self.assertRaises(R3ReportError):
            verify_r3_report_package(package_dir="results/exp001-r3/asset-mutation", repo_root=self.root)

    def test_provenance_mutation_fails_closed(self) -> None:
        self._run("provenance-mutation")
        self.authorization_path.write_text("mutated\n", encoding="utf-8")
        with self.assertRaises(R3ReportError):
            verify_r3_report_package(package_dir="results/exp001-r3/provenance-mutation", repo_root=self.root)

    def test_preflight_failure_publishes_empty_report_verifiable_terminal_package(self) -> None:
        """A failure before scoring or target access remains fully publishable."""
        adapter = Mock()
        target_reader = Mock()
        failing_preflight = Mock(side_effect=RuntimeError("synthetic preflight failure"))
        with patch("latent_triz.exp001_r3_material_runner._records") as records:
            result = run_material(
                root=self.root,
                run_id="preflight-failure",
                authorization=self.authorization,
                adapter=adapter,
                target_reader=target_reader,
                created_at="2026-08-18T00:00:00Z",
                preflight_fn=failing_preflight,
                provenance_artifacts=self.provenance,
            )

        self.assertEqual(result["status"], "failed")
        failing_preflight.assert_called_once()
        self.assertEqual(failing_preflight.call_args.args, (self.root.resolve(), self.authorization))
        records.assert_not_called()
        self.assertEqual(adapter.mock_calls, [])
        target_reader.assert_not_called()
        package_dir = "results/exp001-r3/preflight-failure"
        manifest = verify_r3_report_package(package_dir=package_dir, repo_root=self.root)
        self.assertEqual(manifest["terminal_status"], "failed")
        self.assertNotIn("response_index", manifest)

        receipt = json.loads((self.root / package_dir / "execution-receipt.json").read_text(encoding="utf-8"))
        asset = json.loads((self.root / receipt["external_response_asset"]["locator"]).read_text(encoding="utf-8"))
        sealed = json.loads((self.root / package_dir / "sealed-key-access.json").read_text(encoding="utf-8"))
        recovery = json.loads((self.root / package_dir / "recovery-observation.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["execution"]["runtime_status"], "not_started")
        self.assertEqual(receipt["access"], {"model_loaded": False, "model_output_accessed": "not_accessed", "sealed_targets_accessed": "not_accessed", "target_reads": 0})
        self.assertEqual(asset["record_count"], 0)
        self.assertEqual(asset["records"], [])
        self.assertEqual(set(receipt["provenance"]), {"implementation", "authorization", "integrity", "feasibility", "sealed_key_access", "recovery"})
        self.assertEqual(sealed, {"artifact_class": "exp001-r3-sealed-key-access-observation", "status": "not_accessed", "target_reads": 0, "sealed_targets_accessed": "not_accessed"})
        self.assertEqual(recovery, {"artifact_class": "exp001-r3-recovery-observation", "status": "terminal_failure", "terminal_status": "failed", "retry_performed": False})


if __name__ == "__main__":
    unittest.main()
