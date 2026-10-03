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



class A0XDefaultA0SelectionBridgeTests(unittest.TestCase):
    """Synthetic first-forward checks, not a material or completed extraction."""

    def setUp(self):
        supplied = os.environ.get("A0X_SYNTHETIC_ROOT")
        parent_path = Path("/private/tmp") if supplied is not None else Path(tempfile.gettempdir())
        parent = os.open(parent_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptor = None
        self._owns_root = supplied is None
        name = (
            "a0x-selection-contract-synthetic-" + os.urandom(16).hex()
            if supplied is None else Path(supplied).name
        )
        if supplied is not None and (
            Path(supplied).parent != Path("/private/tmp")
            or not name.startswith("a0x-selection-contract-synthetic-")
        ):
            os.close(parent)
            self.fail("focused synthetic root is outside the owned namespace")
        try:
            if self._owns_root:
                os.mkdir(name, 0o700, dir_fd=parent)
            descriptor = os.open(
                name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent,
            )
            identity = os.fstat(descriptor)
            self.assertEqual(os.getuid(), identity.st_uid)
            self.assertEqual(0o700, identity.st_mode & 0o777)
            self.synthetic_root = parent_path / name

            def close_owned_root():
                try:
                    if self._owns_root:
                        current = os.stat(name, dir_fd=parent, follow_symlinks=False)
                        self.assertEqual(
                            (identity.st_dev, identity.st_ino),
                            (current.st_dev, current.st_ino),
                            "synthetic root ownership lost; replacement preserved",
                        )
                        os.rmdir(name, dir_fd=parent)
                finally:
                    os.close(descriptor)
                    os.close(parent)

            self.addCleanup(close_owned_root)
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
            os.close(parent)
            raise

    def _fixture(self):
        from latent_triz.a0x_contract import (
            APPROVAL_DOSSIER_PROFILE, EXECUTION_AUTHORIZATION_PROFILE,
            LegFreezeBinding, compute_dense_bound, derive_pair_output_path,
        )
        from latent_triz.a0x_execution import _selection_capability
        from latent_triz.a0x_production_adapter import ProductionContext

        ids = tuple(f"synthetic-case-{index:02d}" for index in range(48))
        freeze = LegFreezeBinding(
            Leg.A0, "synthetic-a0", "1" * 64, "2" * 64, "3" * 64,
            "4" * 64, "5" * 64, "6" * 40,
        )
        pair = PairBinding.from_mapping({
            "binding_profile": "a0x-pair-scope-v2", "leg": "a0",
            "leg_freeze_sha256": freeze.leg_freeze_sha256,
            "model_key": "smollm2_360m", "model_id": "synthetic/fixture",
            "revision": "7" * 40, "run_id": "synthetic-selection-bridge",
            "output_path": derive_pair_output_path(
                Leg.A0, "smollm2_360m", "synthetic-selection-bridge",
            ),
            "dense_bound": compute_dense_bound(Leg.A0, cases=48, hidden_width=2).as_mapping(),
        })
        selection = _selection_capability(
            leg_freeze=freeze,
            source_path=Path("experiments/a0x-six-model/a0-selection-manifest.json"),
            source_sha256=freeze.selection_corpus_sha256,
            case_ids=ids, require_file_exact=False,
        )
        cases = [{
            "case_id": case_id, "problem_family_id": f"family-{index}",
            "domain": "synthetic", "problem": f"Synthetic problem {index}",
            "constraints": ["Synthetic constraint"], "initial_state": "Synthetic initial state",
            "desired_improvement": "Synthetic improvement",
            "worsening_consequence": "Synthetic worsening",
            "transformation": "Synthetic transformation", "solution": "Synthetic solution",
        } for index, case_id in enumerate(ids)]
        chain = {
            "dossier_commitment": {
                "profile": APPROVAL_DOSSIER_PROFILE, "commitment_sha256": "8" * 64,
            },
            "authorization_commitment": {
                "profile": EXECUTION_AUTHORIZATION_PROFILE, "commitment_sha256": "9" * 64,
            },
        }
        # The focused operator owns this empty private directory. No production
        # preflight, loader, schema, model, tokenizer or target is invoked.
        context = ProductionContext(
            self.synthetic_root, {}, "a" * 64, "b" * 40,
            pair, {}, "c" * 64, {}, "d" * 64,
        )
        return context, freeze, selection, cases, chain

    def _exercise(self, *, selection_change=None, cases_change=None, freeze_change=None):
        from unittest.mock import patch
        from latent_triz.a0x_a0_activations import extract_a0x_a0
        from latent_triz.a0x_production_adapter import _default_dependencies

        context, freeze, selection, cases, chain = self._fixture()
        if selection_change is not None:
            selection = selection_change(selection)
        if cases_change is not None:
            cases = cases_change(cases)
        if freeze_change is not None:
            freeze = freeze_change(freeze)
        forwarded = []
        payloads = []

        class FirstForwardBoundary(BaseException):
            pass

        class Adapter:
            hidden_width = 2

            def forward_hidden(self, text):
                forwarded.append(text)
                raise FirstForwardBoundary()

        def actual_extractor(**kwargs):
            payloads.append(kwargs["selection"])
            return extract_a0x_a0(**kwargs)

        with patch("latent_triz.a0x_execution.load_a0_public_selection", return_value=selection), \
             patch("latent_triz.a0x_production_adapter._public_cases", return_value=cases), \
             patch("latent_triz.a0x_production_adapter._authorization_chain", return_value=chain), \
             patch("latent_triz.a0x_a0_activations.extract_a0x_a0", side_effect=actual_extractor):
            dependencies = _default_dependencies(context)
            callback = dependencies.activation_by_leg[Leg.A0]
            inspect.getclosurevars(callback).nonlocals["state"]["freeze"] = freeze
            try:
                callback(Adapter(), lambda _stage: None)
            except FirstForwardBoundary:
                return "first_forward", forwarded, payloads
            except Exception as error:
                self.assertEqual([], forwarded, "invalid selection reached fake forward")
                return error, forwarded, payloads
        self.fail("synthetic callback returned a completed extraction")

    def test_real_default_a0_reaches_first_forward_with_ordered_manifest(self):
        outcome, forwarded, payloads = self._exercise(
            cases_change=lambda cases: list(reversed(cases)),
        )
        self.assertEqual("first_forward", outcome)
        self.assertEqual(1, len(forwarded))
        self.assertEqual(1, len(payloads))
        self.assertEqual([], list(self.synthetic_root.iterdir()))
        self.assertIn("Synthetic problem 0", forwarded[0])
        self.assertEqual({
            "target_content_reads": 0, "selected_case_count": 48,
            "cases": [{"case_id": f"synthetic-case-{index:02d}"} for index in range(48)],
        }, payloads[0])

    def test_invalid_capabilities_rejected_before_first_forward(self):
        from dataclasses import replace
        from latent_triz.a0x_production_adapter import A0XProductionAdapterError
        mutations = {
            "missing": lambda selection: None,
            "wrong_type": lambda selection: SimpleNamespace(**selection.__dict__),
            "wrong_leg": lambda selection: replace(selection, leg=Leg.R1),
            "freeze": lambda selection: replace(selection, leg_freeze_sha256="e" * 64),
            "source": lambda selection: replace(selection, source_sha256="e" * 64),
            "path": lambda selection: replace(selection, source_path="synthetic/alias.json"),
            "identity": lambda selection: replace(selection, ordered_case_ids_sha256="e" * 64),
            "attestation": lambda selection: replace(selection, _attestation_sha256="e" * 64),
            "reordered": lambda selection: replace(
                selection, expected_case_ids=tuple(reversed(selection.expected_case_ids)),
            ),
            "missing_id": lambda selection: replace(
                selection, expected_case_ids=selection.expected_case_ids[:-1],
            ),
            "duplicate_id": lambda selection: replace(
                selection, expected_case_ids=(selection.expected_case_ids[0],) * 48,
            ),
            "extra_id": lambda selection: replace(
                selection, expected_case_ids=selection.expected_case_ids + ("extra",),
            ),
            "exact_mode": lambda selection: replace(selection, require_file_exact=True),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                outcome, forwarded, payloads = self._exercise(selection_change=mutation)
                self.assertIsInstance(outcome, A0XProductionAdapterError)
                self.assertEqual([], forwarded)
                self.assertEqual([], payloads)

    def test_freeze_source_binding_rejected_even_with_valid_capability_integrity(self):
        from dataclasses import replace
        from latent_triz.a0x_execution import _selection_capability
        from latent_triz.a0x_production_adapter import A0XProductionAdapterError

        def mismatched_source(selection):
            _context, freeze, _selection, _cases, _chain = self._fixture()
            return _selection_capability(
                leg_freeze=freeze, source_path=Path(selection.source_path),
                source_sha256="e" * 64, case_ids=selection.expected_case_ids,
                require_file_exact=False,
            )

        for change in (
            {"selection_change": mismatched_source},
            {"freeze_change": lambda freeze: replace(freeze, leg=Leg.R1)},
            {"freeze_change": lambda freeze: replace(freeze, leg_freeze_sha256="e" * 64)},
            {"freeze_change": lambda freeze: replace(freeze, selection_corpus_sha256="e" * 64)},
            {"freeze_change": lambda freeze: None},
        ):
            with self.subTest(change=tuple(change)):
                outcome, forwarded, payloads = self._exercise(**change)
                self.assertIsInstance(outcome, A0XProductionAdapterError)
                self.assertEqual([], forwarded)
                self.assertEqual([], payloads)

    def test_bad_case_membership_or_fields_rejected_by_unchanged_extractor(self):
        from latent_triz.a0x_a0_activations import A0XActivationError
        mutations = {
            "missing": lambda cases: cases[:-1],
            "extra": lambda cases: cases + [dict(cases[0], case_id="extra")],
            "duplicate": lambda cases: cases[:-1] + [cases[0]],
            "unselected": lambda cases: cases[:-1] + [dict(cases[-1], case_id="other")],
        }
        required = (
            "case_id", "problem_family_id", "domain", "problem", "constraints",
            "initial_state", "desired_improvement", "worsening_consequence",
            "transformation", "solution",
        )
        for field in required:
            mutations[f"missing_field_{field}"] = (
                lambda cases, field=field: [
                    {key: value for key, value in cases[0].items() if key != field},
                    *cases[1:],
                ]
            )
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                outcome, forwarded, payloads = self._exercise(cases_change=mutation)
                self.assertIsInstance(outcome, A0XActivationError)
                self.assertEqual([], forwarded)
                self.assertEqual(1, len(payloads))

if __name__ == "__main__":
    unittest.main()
