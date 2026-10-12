from __future__ import annotations

import json
import sys
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz import a0r2_authorization as authorization  # noqa: E402
from tests.a0x_test_support import synthetic_schema_object, copy_public_contract_inputs
from latent_triz.a0r2_authorization import (
    A0R2AuthorizationError,
    verify_a0r2_sealed_execution_authorization,
)


class A0R2AuthorizationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        copy_public_contract_inputs(self.root, (
            "schemas/a0r2-sealed-execution-authorization.schema.json",
            "experiments/a0r2-independent-model/implementation.json",
            "experiments/a0r2-independent-model/study-protocol.json",
        ))
        schema = json.loads((self.root / "schemas/a0r2-sealed-execution-authorization.schema.json").read_text())
        receipt = synthetic_schema_object(schema)
        dossier = self.root / "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json"
        dossier.write_text(json.dumps({"dossier_id": "a0r2-sealed-execution-approval-v1"}), encoding="utf-8")
        receipt["bindings"] = {
            name: hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
            for name, relative in (
                ("approval_dossier_sha256", dossier.relative_to(self.root).as_posix()),
                ("implementation_sha256", "experiments/a0r2-independent-model/implementation.json"),
                ("study_protocol_sha256", "experiments/a0r2-independent-model/study-protocol.json"),
            )
        }
        self.receipt = self.root / "results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json"
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

    def test_receipt_verifies_without_model_or_target_access(self) -> None:
        result = verify_a0r2_sealed_execution_authorization(self.root)
        self.assertEqual("pass", result["status"])
        self.assertFalse(result["model_output_accessed"])
        self.assertFalse(result["sealed_targets_accessed"])

    def test_binding_mutation_fails_closed(self) -> None:
        receipt_path = self.receipt
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["bindings"]["study_protocol_sha256"] = "0" * 64
        original_read_json = authorization._read_json

        def read_json(path: Path, label: str):
            if path.resolve() == receipt_path.resolve():
                return receipt
            return original_read_json(path, label)

        with patch.object(authorization, "_read_json", side_effect=read_json):
            with self.assertRaisesRegex(A0R2AuthorizationError, "binding mismatch"):
                verify_a0r2_sealed_execution_authorization(self.root)

    def test_scope_mutation_fails_closed(self) -> None:
        receipt_path = self.receipt
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["scope"]["generation_allowed"] = True
        original_read_json = authorization._read_json

        def read_json(path: Path, label: str):
            if path.resolve() == receipt_path.resolve():
                return receipt
            return original_read_json(path, label)

        with patch.object(authorization, "_read_json", side_effect=read_json):
            with self.assertRaisesRegex(A0R2AuthorizationError, "schema validation"):
                verify_a0r2_sealed_execution_authorization(self.root)


if __name__ == "__main__":
    unittest.main()
