"""Synthetic contracts for the inert A0X production-adapter assembly.

These tests deliberately use injected lifecycle dependencies.  They prove the
adapter binds one descriptor/authentication/contract pair before it can expose
any material capability; they never load a model or open a sealed target.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import Leg, PairBinding
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
            contract_path.write_bytes(contract_raw)
            python_path = root / ".a0x-runtime/bin/python"
            python_path.parent.mkdir(parents=True)
            python_path.write_bytes(b"synthetic python")
            python_path.chmod(0o700)
            pair_object = PairBinding.from_mapping(pair)
            from latent_triz.a0x_runtime_readiness import canonical_json_bytes, runtime_readiness_path
            from tests.test_a0x_runtime_bundle import _synthetic_runtime_readiness
            readiness = _synthetic_runtime_readiness(root, pair_object, source_head, python_path)
            readiness_path = root / runtime_readiness_path(pair_object)
            readiness_path.parent.mkdir(parents=True, exist_ok=True)
            readiness_raw = canonical_json_bytes(readiness)
            readiness_path.write_bytes(readiness_raw)
            descriptor = {
                "descriptor_profile": "a0x-material-child-descriptor-v2",
                "source_head": source_head,
                "cwd_kind": "repository_root",
                "pair_binding": pair,
                "child_script": {"role": "child", "path": "scripts/a0x_material_child.py", "sha256": "a" * 64},
                "python": {
                    "role": "python", "path": str(python_path),
                    "sha256": hashlib.sha256(python_path.read_bytes()).hexdigest(),
                },
                "runtime_readiness": {
                    "role": "readiness",
                    "path": readiness_path.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(readiness_raw).hexdigest(),
                },
                "environment_template": [
                    "HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1", "HF_DATASETS_OFFLINE=1",
                    "TOKENIZERS_PARALLELISM=false", "PYTHONNOUSERSITE=1",
                ],
                "authorization_reference": {
                    "role": "authorization", "path": str(authorization["authorization_inlet_path"]),
                },
                "material_contract": {
                    "role": "material_contract", "path": "experiments/a0x-six-model/material-execution-contract.json",
                    "sha256": hashlib.sha256(contract_raw).hexdigest(),
                },
                "execution": {
                    "network": "offline", "generation": "forbidden", "trust_remote_code": False,
                    "device": "cpu", "dtype": "float32", "outer_timeout_seconds": 3600,
                    "internal_budget_seconds": 3300, "cleanup_margin_seconds": 300,
                },
            }
            from latent_triz.a0x_material_contract import derive_runtime_paths

            descriptor_raw = _raw(descriptor)
            authorization["guard_launch"]["launch_descriptor"]["sha256"] = hashlib.sha256(descriptor_raw).hexdigest()
            authorization_path.write_bytes(_raw(authorization))
            launch_path = root / derive_runtime_paths(pair).launch_descriptor_path
            launch_path.parent.mkdir(parents=True, exist_ok=True)
            launch_path.write_bytes(descriptor_raw)
            yield root, descriptor, pair

    def test_builder_is_inert_then_runs_only_the_descriptor_bound_pair(self) -> None:
        from latent_triz.a0x_production_adapter import ProductionFactories, build_production_executor
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        root = bundle.root
        descriptor = json.loads((root / bundle.receipt["descriptor_path"]).read_text())
        pair = descriptor["pair_binding"]
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

    def test_descriptor_v2_binds_authorization_to_exact_descriptor(self) -> None:
        from latent_triz.a0x_material_contract import derive_runtime_paths
        from latent_triz.a0x_production_adapter import ProductionFactories, build_production_executor

        for root, descriptor, pair in self._descriptor_root():
            contract = root / "experiments/a0x-six-model/material-execution-contract.json"
            authorization_path = root / derive_runtime_paths(pair).authorization_path
            launch_path = root / derive_runtime_paths(pair).launch_descriptor_path
            v2 = dict(descriptor)
            v2["descriptor_profile"] = "a0x-material-child-descriptor-v2"
            v2["authorization_reference"] = {
                "role": "authorization",
                "path": derive_runtime_paths(pair).authorization_path,
            }
            v2["material_contract"] = {
                "role": "material_contract",
                "path": "experiments/a0x-six-model/material-execution-contract.json",
                "sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
            }
            descriptor_raw = _raw(v2)
            authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
            authorization["guard_launch"]["launch_descriptor"]["sha256"] = hashlib.sha256(descriptor_raw).hexdigest()
            authorization_path.write_bytes(_raw(authorization))
            launch_path.write_bytes(descriptor_raw)

            executor = build_production_executor(
                root=root,
                descriptor=v2,
                factories=ProductionFactories(
                    dependency_builder=lambda _context: object(),
                    lifecycle_runner=lambda **_kwargs: {"terminal_outcome": {"status": "null"}},
                ),
            )

            self.assertEqual({"status": "null"}, executor(v2))

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

    def test_default_assembly_has_no_stage_to_state_mapping(self) -> None:
        from latent_triz.a0x_production_adapter import _default_dependencies

        self.assertNotIn("state_for_stage", inspect.getsource(_default_dependencies))

    def test_model_load_revalidates_live_readiness_after_binding(self) -> None:
        from latent_triz.a0x_production_adapter import (
            _bind_context,
            _load_model_after_live_readiness,
        )
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        descriptor = json.loads((bundle.root / bundle.receipt["descriptor_path"]).read_text())
        context = _bind_context(root=bundle.root, descriptor=descriptor)
        runtime_file = bundle.root / "artifacts/models/gpt2-synthetic/config.json"
        os.link(runtime_file, bundle.root / "config-hardlink")
        load_calls: list[object] = []
        card = object()
        with self.assertRaisesRegex(Exception, "runtime documents"):
            _load_model_after_live_readiness(
                context=context,
                card=card,
                identity=card,
                expected_card=card,
                loader=lambda *_args, **_kwargs: load_calls.append(object()),
            )
        self.assertEqual([], load_calls, "model loader must not run after live alias drift")

    def test_current_gate_a_files_refuse_immediately_before_model_loader(self) -> None:
        """The model boundary repeats all current Gate-A file commitments."""
        from latent_triz.a0x_production_adapter import (
            A0XProductionAdapterError,
            _bind_context,
            _load_model_after_live_readiness,
        )
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        for role in ("manifest", "attestation_bundle", "trusted_root", "transport", "verification_receipt"):
            for mutation in ("missing", "mutated", "symlink", "hardlink", "nonregular"):
                with self.subTest(role=role, mutation=mutation):
                    bundle = prepare_constructible_runtime_bundle()
                    self.addCleanup(bundle.close)
                    descriptor = json.loads((bundle.root / bundle.receipt["descriptor_path"]).read_text())
                    context = _bind_context(root=bundle.root, descriptor=descriptor)
                    authorization = json.loads((bundle.root / bundle.receipt["authorization_path"]).read_text())
                    evidence = authorization["gate_a_evidence"]
                    binding = evidence["verification_receipt"] if role == "verification_receipt" else evidence["hosted_inputs"][role]
                    path = bundle.root / binding["path"]
                    if mutation == "missing":
                        path.unlink()
                    elif mutation == "mutated":
                        path.write_bytes(b"mutated")
                    elif mutation == "symlink":
                        target = bundle.root / "untrusted-gate-a-model-bytes"
                        target.write_bytes(path.read_bytes())
                        path.unlink()
                        path.symlink_to(target)
                    elif mutation == "hardlink":
                        os.link(path, bundle.root / "untrusted-gate-a-model-alias")
                    else:
                        path.unlink()
                        path.mkdir()
                    loader_calls: list[object] = []
                    card = SimpleNamespace(runtime_root="artifacts/models/gpt2-synthetic")
                    with self.assertRaises(A0XProductionAdapterError):
                        _load_model_after_live_readiness(
                            context=context,
                            card=card,
                            identity=card,
                            expected_card=card,
                            loader=lambda *_args, **_kwargs: loader_calls.append(object()),
                        )
                    self.assertEqual([], loader_calls)

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
