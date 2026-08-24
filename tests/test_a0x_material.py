"""The material entrypoint has no selectable execution surface."""
from __future__ import annotations

import unittest
from contextlib import redirect_stderr
from io import StringIO


class A0XMaterialEntrypointTests(unittest.TestCase):
    def test_material_entrypoint_rejects_cli_model_or_leg_override(self) -> None:
        from scripts.a0x_material import main

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                main(["--model", "gpt2"])

    def test_material_entrypoint_fails_closed_when_planned_dossier_is_absent(self) -> None:
        from scripts.a0x_material import main

        with redirect_stderr(StringIO()):
            self.assertNotEqual(0, main(["--fixed-dossier", "experiments/a0x-six-model/dossiers/a0/gpt2.json"]))
