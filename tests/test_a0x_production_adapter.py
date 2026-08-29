"""Synthetic contracts for the inert A0X production-adapter assembly.

These tests deliberately use injected lifecycle dependencies.  They prove the
adapter binds one descriptor/authentication/contract pair before it can expose
any material capability; they never load a model or open a sealed target.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from latent_triz.a0x_contract import Leg
from tests.a0x_test_support import artifact, authorization_documents, pair_binding


def _raw(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _model_module_state() -> dict[str, object | None]:
    return {name: sys.modules.get(name) for name in ("torch", "transformers")}


class A0XProductionAdapterTests(unittest.TestCase):
    def _descriptor_root(self, *, leg: Leg = Leg.A0):
        pair = pair_binding(leg)
        _dossier, authorization, _chain = authorization_documents(pair)
        contract = artifact("a0x-material-execution-contract.schema.json")
        contract_raw = _raw(contract)
        authorization["material_contract_raw_sha256"] = hashlib.sha256(contract_raw).hexdigest()
        source_head = str(authorization["source_head"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorization_path = root / str(authorization["authorization_inlet_path"])
            contract_path = root / "experiments/a0x-six-model/material-execution-contract.json"
            authorization_path.parent.mkdir(parents=True)
            contract_path.parent.mkdir(parents=True)
            authorization_raw = _raw(authorization)
            authorization_path.write_bytes(authorization_raw)
            contract_path.write_bytes(contract_raw)
            descriptor = {
                "descriptor_profile": "a0x-material-child-descriptor-v1",
                "source_head": source_head,
                "cwd_kind": "repository_root",
                "pair_binding": pair,
                "child_script": {"role": "child", "path": "scripts/a0x_material_child.py", "sha256": "a" * 64},
                "python": {"role": "python", "path": "/synthetic/python", "sha256": "b" * 64},
                "environment_template": [
                    "HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1", "HF_DATASETS_OFFLINE=1",
                    "TOKENIZERS_PARALLELISM=false", "PYTHONNOUSERSITE=1",
                ],
                "runtime_files": [
                    {"role": "authorization", "path": str(authorization["authorization_inlet_path"]), "sha256": hashlib.sha256(authorization_raw).hexdigest()},
                    {"role": "material_contract", "path": "experiments/a0x-six-model/material-execution-contract.json", "sha256": hashlib.sha256(contract_raw).hexdigest()},
                ],
                "execution": {
                    "network": "offline", "generation": "forbidden", "trust_remote_code": False,
                    "device": "cpu", "dtype": "float32", "outer_timeout_seconds": 3600,
                    "internal_budget_seconds": 3300, "cleanup_margin_seconds": 300,
                },
            }
            yield root, descriptor, pair

    def test_builder_is_inert_then_runs_only_the_descriptor_bound_pair(self) -> None:
        from latent_triz.a0x_production_adapter import ProductionFactories, build_production_executor

        for root, descriptor, pair in self._descriptor_root():
            calls: list[object] = []

            def build_dependencies(context):
                calls.append(("dependencies", context.pair.model_key, context.pair.leg.value))
                return object()

            def lifecycle_runner(*, pair, preflight_context, dependencies):
                calls.append(("run", pair.model_key, pair.leg.value, dependencies, preflight_context["outer_timeout_seconds"]))
                return {"terminal_outcome": {"status": "null"}}

            executor = build_production_executor(
                root=root, descriptor=descriptor,
                factories=ProductionFactories(
                    dependency_builder=build_dependencies,
                    lifecycle_runner=lifecycle_runner,
                ),
            )
            self.assertEqual([], calls, "build must not construct a tokenizer/model or open a target")
            self.assertEqual({"status": "null"}, executor(descriptor))
            self.assertEqual(("dependencies", pair["model_key"], pair["leg"]), calls[0])
            self.assertEqual(("run", pair["model_key"], pair["leg"]), calls[1][:3])
            self.assertIsNotNone(calls[1][3])
            self.assertEqual(3600, calls[1][4])

    def test_executor_rejects_any_selector_or_descriptor_override(self) -> None:
        from latent_triz.a0x_production_adapter import (
            A0XProductionAdapterError,
            ProductionFactories,
            build_production_executor,
        )

        for root, descriptor, _pair in self._descriptor_root():
            executor = build_production_executor(
                root=root, descriptor=descriptor,
                factories=ProductionFactories(
                    dependency_builder=lambda _context: object(),
                    lifecycle_runner=lambda **_kwargs: {"terminal_outcome": {"status": "null"}},
                ),
            )
            changed = dict(descriptor)
            changed["source_head"] = "f" * 40
            with self.assertRaisesRegex(A0XProductionAdapterError, "descriptor"):
                executor(changed)
            with self.assertRaises(TypeError):
                executor(descriptor, model_key="gpt2")  # type: ignore[call-arg]

    def test_default_assembly_exposes_distinct_leg_callbacks_without_material_imports(self) -> None:
        from latent_triz.a0x_production_adapter import _default_dependencies, _bind_context

        for root, descriptor, _pair in self._descriptor_root(leg=Leg.R1):
            before = _model_module_state()
            dependencies = _default_dependencies(_bind_context(root=root, descriptor=descriptor))
            self.assertIsNot(
                dependencies.activation_by_leg[Leg.A0], dependencies.activation_by_leg[Leg.R1],
            )
            self.assertIsNot(
                dependencies.analysis_by_leg[Leg.A0], dependencies.analysis_by_leg[Leg.R1],
            )
            self.assertEqual(before, _model_module_state())

    def test_default_assembly_installs_real_terminal_package_callbacks(self) -> None:
        from latent_triz.a0x_production_adapter import _default_dependencies, _bind_context

        for root, descriptor, _pair in self._descriptor_root():
            dependencies = _default_dependencies(_bind_context(root=root, descriptor=descriptor))
            self.assertNotEqual("unavailable_package", dependencies.package_builder.__name__)
            self.assertNotEqual("no_package_verifier", dependencies.package_verifier.__name__)
            self.assertNotEqual("no_package_verifier", dependencies.protected_tree_postflight.__name__)

    def test_release_helper_clears_loaded_adapter_references_without_model_imports(self) -> None:
        from latent_triz.a0x_production_adapter import _release_model_references

        class Adapter:
            def __init__(self) -> None:
                self.model = object()
                self.tokenizer = object()
                self.torch = object()
                self.model_loaded = True

        adapter = Adapter()
        before = _model_module_state()
        stages: list[str] = []
        _release_model_references(adapter, stages.append)
        self.assertEqual(["model-release-before-clear", "model-release-after-clear"], stages)
        self.assertIsNone(adapter.model)
        self.assertIsNone(adapter.tokenizer)
        self.assertIsNone(adapter.torch)
        self.assertFalse(adapter.model_loaded)
        self.assertEqual(before, _model_module_state())


if __name__ == "__main__":
    unittest.main()
