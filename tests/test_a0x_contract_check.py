"""Synthetic-only checks must report their material-access boundary."""
from __future__ import annotations

from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

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

    def test_adding_a0x_cli_command_preserves_a0r1_verify_success_return(self) -> None:
        from latent_triz.cli import main

        with patch("latent_triz.cli.verify_a0r1_foundation", return_value={"status": "pass"}):
            with redirect_stdout(StringIO()):
                self.assertEqual(0, main(["a0r1-verify", "--root", "."]))
