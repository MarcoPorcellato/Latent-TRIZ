"""Synthetic-only checks must report their material-access boundary."""
from __future__ import annotations

from pathlib import Path

from tests.a0x_test_support import A0XTempTestCase


class A0XContractCheckTests(A0XTempTestCase):
    def test_synthetic_verifier_reports_no_material_access(self) -> None:
        from latent_triz.a0x_runner import verify_a0x_implementation

        receipt = verify_a0x_implementation(Path(__file__).resolve().parents[1])
        self.assertEqual("synthetic_implementation", receipt["phase"])
        self.assertFalse(receipt["model_loaded"])
        self.assertFalse(receipt["tokenizer_constructed"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertFalse(receipt["ccp_invoked"])
        self.assertFalse(receipt["protocol_and_dossier_frozen"])

