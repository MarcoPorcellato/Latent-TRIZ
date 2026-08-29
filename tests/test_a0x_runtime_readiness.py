from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from latent_triz.a0x_contract import PairBinding
from latent_triz.a0x_preflight import A0XPreflightError, RuntimeFile, load_registry
from latent_triz.a0x_runtime_readiness import (
    A0XRuntimeReadinessError,
    EXPECTED_API_SYMBOLS,
    EXPECTED_PACKAGES,
    build_runtime_readiness,
    canonical_json_sha256,
    validate_runtime_readiness,
    validate_runtime_readiness_live,
)
from tests.a0x_test_support import pair_binding


ROOT = Path(__file__).resolve().parents[1]


class A0XRuntimeReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.environment = self.root / "venv"
        self.python = self.environment / "bin/python3.11-a0x"
        self.python.parent.mkdir(parents=True)
        self.python.write_bytes(b"regular copied python")
        self.python.chmod(0o700)
        self.runtime = self.root / "artifacts/models/gpt2-test"
        self.runtime.mkdir(parents=True)
        self.runtime_file = self.runtime / "model.safetensors"
        self.runtime_file.write_bytes(b"weights")
        self.pair = PairBinding.from_mapping(pair_binding())
        card = next(card for card in load_registry(ROOT / "experiments/a0x-six-model/model-registry.json") if card.model_key == "gpt2")
        self.card_path = self.root / "experiments/a0x-six-model/model-cards/gpt2.json"
        self.card_path.parent.mkdir(parents=True)
        self.card_path.write_bytes(b"synthetic card")
        self.card = replace(
            card,
            revision=self.pair.revision,
            runtime_root="artifacts/models/gpt2-test",
            runtime_files=(RuntimeFile(
                path="model.safetensors", size_bytes=7,
                sha256=hashlib.sha256(b"weights").hexdigest(),
            ),),
            card_path="experiments/a0x-six-model/model-cards/gpt2.json",
        )
        self.source_head = "a" * 40

    def probe(self, **changes):
        value = {
            "sys_executable": str(self.python),
            "python_version": "3.11.13",
            "python_major_minor": [3, 11],
            "sys_prefix": str(self.environment),
            "sys_base_prefix": "/opt/python/3.11",
            "packages": dict(EXPECTED_PACKAGES),
            "api_symbols": dict(EXPECTED_API_SYMBOLS),
        }
        value.update(changes)
        return value

    def build(self, *, probe=None, cards=None, snapshot_verifier=None):
        def exact_snapshot(root, card):
            path = Path(root) / "model.safetensors"
            if (
                not path.is_file() or path.is_symlink()
                or path.stat().st_size != card.runtime_files[0].size_bytes
                or hashlib.sha256(path.read_bytes()).hexdigest() != card.runtime_files[0].sha256
            ):
                raise A0XPreflightError("snapshot mismatch")
            return card

        return build_runtime_readiness(
            repository_root=self.root,
            source_head=self.source_head,
            pair=self.pair,
            python_path=self.python,
            environment_root=self.environment,
            python_probe=self.probe() if probe is None else probe,
            registry_loader=lambda _path: (self.card,) if cards is None else cards,
            card_source_verifier=lambda _root, _card: None,
            snapshot_verifier=exact_snapshot if snapshot_verifier is None else snapshot_verifier,
        )

    def test_binds_exact_venv_packages_api_and_runtime_snapshot(self):
        receipt = self.build()
        self.assertEqual("a0x-runtime-readiness-v1", receipt["readiness_profile"])
        self.assertEqual(self.pair.as_mapping(), receipt["pair_binding"])
        self.assertEqual(EXPECTED_PACKAGES, receipt["python"]["packages"])
        self.assertEqual(1, receipt["model_runtime"]["runtime_file_count"])
        self.assertEqual(7, receipt["model_runtime"]["runtime_total_bytes"])
        self.assertEqual(64, len(canonical_json_sha256(receipt)))
        self.assertEqual(receipt, validate_runtime_readiness(
            receipt, source_head=self.source_head, pair=self.pair, python_path=self.python,
        ))

    def test_rejects_symlinked_python_and_base_interpreter(self):
        alias = self.environment / "bin/python"
        alias.symlink_to(self.python.name)
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "symlink"):
            build_runtime_readiness(
                repository_root=self.root, source_head=self.source_head, pair=self.pair,
                python_path=alias, environment_root=self.environment, python_probe=self.probe(),
                registry_loader=lambda _path: (self.card,),
                card_source_verifier=lambda _root, _card: None,
                snapshot_verifier=lambda _root, card: card,
            )
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "exact environment"):
            self.build(probe=self.probe(sys_base_prefix=str(self.environment)))

    def test_rejects_package_or_api_drift(self):
        packages = dict(EXPECTED_PACKAGES)
        packages["numpy"] = "0.0.0"
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "exact environment"):
            self.build(probe=self.probe(packages=packages))
        symbols = dict(EXPECTED_API_SYMBOLS)
        symbols["transformers.AutoTokenizer"] = False
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "exact environment"):
            self.build(probe=self.probe(api_symbols=symbols))

    def test_rejects_missing_mutated_symlinked_and_hardlinked_runtime_files(self):
        self.runtime_file.unlink()
        with self.assertRaises(A0XRuntimeReadinessError):
            self.build()
        self.runtime_file.write_bytes(b"changed")
        with self.assertRaises(A0XRuntimeReadinessError):
            self.build()
        self.runtime_file.unlink()
        backing = self.root / "backing"
        backing.write_bytes(b"weights")
        self.runtime_file.symlink_to(backing)
        with self.assertRaises(A0XRuntimeReadinessError):
            self.build(snapshot_verifier=lambda _root, card: card)
        self.runtime_file.unlink()
        os.link(backing, self.runtime_file)
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "independent regular"):
            self.build(snapshot_verifier=lambda _root, card: card)

    def test_rejects_pair_without_one_exact_card(self):
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "exactly one"):
            self.build(cards=())

    def test_live_validation_rejects_post_receipt_python_and_snapshot_aliases(self):
        receipt = self.build()

        def validate_live():
            return validate_runtime_readiness_live(
                receipt,
                repository_root=self.root,
                source_head=self.source_head,
                pair=self.pair,
                python_path=self.python,
                card_loader=lambda _path: self.card,
                card_source_verifier=lambda _root, _card: None,
                snapshot_verifier=lambda _root, card: card,
            )

        self.assertEqual(receipt, validate_live())
        python_alias = self.root / "python-hardlink"
        os.link(self.python, python_alias)
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "independent regular"):
            validate_live()
        python_alias.unlink()

        runtime_alias = self.root / "runtime-hardlink"
        os.link(self.runtime_file, runtime_alias)
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "independent regular"):
            validate_live()
        runtime_alias.unlink()

        replacement = self.root / "python-replacement"
        replacement.write_bytes(self.python.read_bytes())
        replacement.chmod(0o700)
        self.python.unlink()
        self.python.symlink_to(replacement)
        with self.assertRaisesRegex(A0XRuntimeReadinessError, "symlink"):
            validate_live()


if __name__ == "__main__":
    unittest.main()
