"""Synthetic state-machine tests for the future A0X one-pair runner."""
from __future__ import annotations

import json

from tests.a0x_test_support import A0XTempTestCase, authorization_documents, pair_binding


class A0XRunnerTests(A0XTempTestCase):
    def _dossier(self):
        pair = pair_binding()
        dossier, authorization, _chain = authorization_documents(pair)
        dossier_path = self.temp_path / "approval-dossier.json"
        authorization_path = self.temp_path / "execution-authorization.json"
        dossier_path.write_text(json.dumps(dossier), encoding="utf-8")
        authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
        return dossier_path, authorization_path

    def test_runner_seals_first_failure_and_refuses_second_attempt(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, run_a0x_pair

        dossier, authorization = self._dossier()

        def failing_adapter():
            raise RuntimeError("synthetic adapter failure")

        first = run_a0x_pair(
            root=self.temp_path,
            dossier_path=dossier,
            authorization_path=authorization,
            adapter_factory=failing_adapter,
        )
        self.assertEqual("failed", first["status"])
        with self.assertRaisesRegex(A0XRunnerError, "terminal attempt already exists"):
            run_a0x_pair(
                root=self.temp_path,
                dossier_path=dossier,
                authorization_path=authorization,
                adapter_factory=lambda: object(),
            )

