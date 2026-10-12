from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0r1_verify import A0R1VerifyError, _require_equal, verify_a0r1_foundation
from latent_triz.a0r1_corpus import generate_a0r1_corpus
from latent_triz.a0r1_preoutput import run_a0r1_preoutput_audits
from latent_triz.a0r1_freeze import run_a0r1_freeze
from tests.a0x_test_support import synthetic_a0_source


class A0R1VerifyTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[1]
    protocol = root / "experiments/a0r1-independent-proxy/protocol.json"

    def _build_mutation_root(self) -> tempfile.TemporaryDirectory:
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        source = synthetic_a0_source(root)
        protocol = root / "experiments/a0r1-independent-proxy/protocol.json"
        protocol.parent.mkdir(parents=True)
        payload = json.loads((self.root / "results/a0r1/freeze/protocol-planned.json").read_text())
        payload["protocol_id"] = "a0-r1-tier-r1-v99.99"
        protocol.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        candidate = root / "data/a0r1"
        preoutput = root / "results/a0r1/preoutput"
        freeze = root / "results/a0r1/freeze"
        generate_a0r1_corpus(protocol, candidate)
        run_a0r1_preoutput_audits(protocol, candidate, source, preoutput)
        run_a0r1_freeze(protocol, candidate, source, preoutput, freeze)
        protocol.write_bytes((freeze / "protocol-frozen.json").read_bytes())
        return directory

    def test_tracked_foundation_reproduces_byte_for_byte(self) -> None:
        with self._build_mutation_root() as directory:
            result = verify_a0r1_foundation(Path(directory))
        self.assertEqual("pass", result["status"])
        self.assertFalse(result["model_output_accessed"])
        self.assertEqual(4, result["corpus_files_verified"])
        self.assertEqual(4, result["preoutput_files_verified"])
        self.assertEqual("frozen", result["protocol_status"])
        self.assertTrue(result["protocol_file_matches_frozen"])
        self.assertEqual("frozen", result["freeze_status"])
        self.assertGreater(result["freeze_files_verified"], 5)

    def test_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected"
            actual = root / "actual"
            expected.mkdir()
            actual.mkdir()
            (expected / "artifact.json").write_text("expected", encoding="utf-8")
            (actual / "artifact.json").write_text("changed", encoding="utf-8")
            with self.assertRaises(A0R1VerifyError):
                _require_equal(expected, actual, ("artifact.json",))

    def test_frozen_protocol_requires_frozen_snapshot_match(self) -> None:
        with self._build_mutation_root() as root_tmp:
            root = Path(root_tmp)
            protocol = (root / "results/a0r1/freeze/protocol-frozen.json").read_text(encoding="utf-8")
            payload = json.loads(protocol)
            payload["protocol_status"] = "frozen"
            payload["status"] = "frozen"
            payload["protocol_id"] = payload["protocol_id"] + "-tamper"
            (root / "experiments/a0r1-independent-proxy/protocol.json").write_text(
                json.dumps(payload, sort_keys=True), encoding="utf-8"
            )
            with self.assertRaises(A0R1VerifyError):
                verify_a0r1_foundation(root)

    def test_planned_protocol_paths_skip_freeze_artifact_verification(self) -> None:
        with self._build_mutation_root() as directory:
            root = Path(directory)
            planned_protocol = root / "results/a0r1/freeze/protocol-planned.json"

            (root / "experiments/a0r1-independent-proxy/protocol.json").write_bytes(
                planned_protocol.read_bytes()
            )
            summary = verify_a0r1_foundation(root)
            self.assertEqual("pass", summary["status"])
            self.assertEqual("planned", summary["protocol_status"])
            self.assertEqual("not_applicable", summary["freeze_status"])
            self.assertEqual(0, summary["freeze_files_verified"])

    def test_frozen_manifest_hash_mismatch_fails(self) -> None:
        with self._build_mutation_root() as directory:
            root = Path(directory)
            freeze_manifest = root / "results/a0r1/freeze/freeze-manifest.json"
            payload = json.loads(freeze_manifest.read_text(encoding="utf-8"))
            payload["planned_protocol_snapshot_hash"] = "0" * 64
            freeze_manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            with self.assertRaises(A0R1VerifyError):
                verify_a0r1_foundation(root)

    def test_failed_freeze_manifest_never_verifies_as_pass(self) -> None:
        with self._build_mutation_root() as directory:
            root = Path(directory)
            freeze_manifest = root / "results/a0r1/freeze/freeze-manifest.json"
            payload = json.loads(freeze_manifest.read_text(encoding="utf-8"))
            payload["status"] = "failed"
            freeze_manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            with self.assertRaises(A0R1VerifyError):
                verify_a0r1_foundation(root)
