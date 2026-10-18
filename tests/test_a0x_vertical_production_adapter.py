from __future__ import annotations

import unittest
from types import MappingProxyType

from latent_triz.a0x_vertical_production_adapter import (
    A0XVerticalProductionAdapterError,
    _dispatch_synthetic_target_free,
    bind_validated_vertical_graph,
)
from tests.a0x_test_support import pair_binding


def _graph(*, qualification_context="synthetic-target-free"):
    pair = pair_binding()
    source = {"head": "a" * 40, "tree": "b" * 40, "ref": "refs/heads/main"}
    package = {
        "envelope_path": ".a0x-runtime/p0/v2/envelope",
        "package_path": ".a0x-runtime/p0/v2/package",
        "commitment_path": ".a0x-runtime/p0/v2/p0-commitment.json",
        "commitment_raw_sha256": "1" * 64,
        "package_commitment_sha256": "2" * 64,
        "dossier_path": ".a0x-runtime/p0/v2/package/approval-dossier.json",
        "dossier_sha256": "3" * 64,
    }
    descriptor = {
        "descriptor_profile": "a0x-vertical-launch-descriptor-v2",
        "qualified_source": source,
        "pair_binding": pair,
        "vertical_package": package,
        "authorization_id": "auth-test-01",
        "attempt_id": "attempt-test-01",
    }
    authorization = {
        "artifact_class": "a0x-vertical-execution-authorization",
        "commitment_profile": "a0x-execution-authorization-json-v4",
        "qualified_source": source,
        "pair_binding": pair,
        "vertical_package": package,
        "qualification_context": qualification_context,
        "authorization_id": "auth-test-01",
        "attempt_id": "attempt-test-01",
        "max_guard_exec_count": 1,
        "stop_boundary": "after_one_sealed_target_read",
    }
    inlet = {
        "artifact_class": "a0x-vertical-gate-b-execution-inlet",
        "inlet_profile": "a0x-vertical-gate-b-execution-inlet-v2",
        "qualified_source": source,
        "pair_binding": pair,
        "vertical_package": package,
        "authorization_id": "auth-test-01",
        "attempt_id": "attempt-test-01",
    }
    return {
        "descriptor": descriptor,
        "readiness": {"source_head": source["head"], "pair_binding": pair, "python": {}, "model_runtime": {}},
        "gate_a_evidence": {"source_head": source["head"], "source_tree": source["tree"], "pair_binding": pair, "evidence_profile": "synthetic-fixture"},
        "execution_inlet": inlet,
        "gate_c_authorization": authorization,
        "trust_file_identities": {
            "schemas/a0x-execution-authorization-v4.schema.json": {
                "device": 1, "inode": 2, "size": 3, "sha256": "4" * 64,
            },
        },
    }


class A0XVerticalProductionAdapterTests(unittest.TestCase):
    def test_context_projection_cannot_authorize_material_execution(self):
        from latent_triz import a0x_vertical_production_adapter as adapter
        execute = getattr(adapter, "run_vertical_production", None)
        self.assertTrue(callable(execute), "production dispatcher is absent")
        context = bind_validated_vertical_graph(_graph(qualification_context="production"), qualification_context="production")
        with self.assertRaisesRegex(A0XVerticalProductionAdapterError, "validated production capability"):
            execute(context)

    def test_v4_graph_binds_a_detached_immutable_context(self):
        graph = _graph()
        context = bind_validated_vertical_graph(graph, qualification_context="synthetic-target-free")

        self.assertEqual("a" * 40, context.source_head)
        self.assertEqual("b" * 40, context.source_tree)
        self.assertEqual("auth-test-01", context.authorization_id)
        self.assertEqual("attempt-test-01", context.attempt_id)
        self.assertIsInstance(context.pair_binding, MappingProxyType)
        self.assertIsInstance(context.trust_file_identities, MappingProxyType)
        identity = context.public_identity()
        self.assertEqual({"commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256"}, set(identity["vertical_package_digests"]))
        self.assertNotIn("vertical_package", identity)

        graph["descriptor"]["qualified_source"]["head"] = "f" * 40
        self.assertEqual("a" * 40, context.source_head)
        with self.assertRaises(TypeError):
            context.pair_binding["model_key"] = "gpt2"

    def test_legacy_or_mixed_graph_is_rejected_before_dispatch(self):
        calls = []
        graph = _graph()
        graph["gate_c_authorization"]["commitment_profile"] = "a0x-execution-authorization-json-v3"

        with self.assertRaises(A0XVerticalProductionAdapterError):
            _dispatch_synthetic_target_free(graph, lambda context: calls.append(context))
        self.assertEqual([], calls)

    def test_only_explicit_synthetic_context_can_reach_injected_dispatch(self):
        calls = []
        result = _dispatch_synthetic_target_free(_graph(), lambda context: calls.append(context) or "synthetic-ok")

        self.assertEqual("synthetic-ok", result)
        self.assertEqual(1, len(calls))
        self.assertEqual("synthetic-target-free", calls[0].qualification_context)

        with self.assertRaises(A0XVerticalProductionAdapterError):
            _dispatch_synthetic_target_free(_graph(qualification_context="production"), lambda _context: self.fail("dispatch reached"))

    def test_graph_shape_and_cross_bindings_fail_closed(self):
        for mutate in (
            lambda graph: graph.pop("trust_file_identities"),
            lambda graph: graph["execution_inlet"].update(attempt_id="other-attempt"),
            lambda graph: graph["readiness"].update(source_head="f" * 40),
        ):
            graph = _graph()
            mutate(graph)
            with self.subTest(graph=graph), self.assertRaises(A0XVerticalProductionAdapterError):
                bind_validated_vertical_graph(graph, qualification_context="synthetic-target-free")


class RehearsalBoundaryTests(unittest.TestCase):
    def test_rehearsal_calibration_uses_the_production_recipe_and_real_consumer(self):
        import tempfile
        from pathlib import Path
        from scripts import a0x_rehearsal as rehearsal
        from latent_triz.a0_calibration import run_production_shortcut_calibration
        from latent_triz.a0_shortcuts import production_mechanics_recipe
        prepare = getattr(rehearsal, "_calibration_inputs", None)
        self.assertTrue(callable(prepare), "shared production calibration preparation is absent")
        with tempfile.TemporaryDirectory() as temporary:
            protocol, cases, targets = prepare(Path(temporary), rehearsal.ROOT)
            result = run_production_shortcut_calibration(protocol, cases, targets, production_mechanics_recipe())
            self.assertEqual("PASS", result["status"])
            self.assertEqual(14, len(result["controls"]))
            self.assertFalse(result["mechanical_freeze_independently_verified"])

    def test_rehearsal_cannot_write_into_scientific_results_namespace(self):
        import tempfile
        from pathlib import Path
        from scripts.a0x_rehearsal import RehearsalError, validate_output_root

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaisesRegex(RehearsalError, "rehearsal namespace"):
                validate_output_root(root, root / "results/a0x/rehearsal")
            self.assertFalse((root / "results").exists())

    def test_rehearsal_refuses_occupied_attempt_without_overwriting(self):
        import tempfile
        from pathlib import Path
        from scripts.a0x_rehearsal import RehearsalError, validate_output_root

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            output = root / ".a0x-runtime/rehearsal/1"
            output.mkdir(parents=True)
            marker = output / "preserved"
            marker.write_bytes(b"keep")
            with self.assertRaisesRegex(RehearsalError, "occupied"):
                validate_output_root(root, output)
            self.assertEqual(b"keep", marker.read_bytes())

    def test_rehearsal_inputs_are_independently_balanced_and_public_rows_have_no_labels(self):
        from scripts.a0x_rehearsal import synthetic_inputs

        cases, targets = synthetic_inputs()
        self.assertEqual(48, len(cases))
        self.assertEqual(48, len(targets))
        self.assertEqual(24, len({row["problem_family_id"] for row in cases}))
        self.assertEqual(6, len({row["domain"] for row in cases}))
        self.assertTrue(all("operator_proxy_family" not in row for row in cases))
        for family in {row["problem_family_id"] for row in cases}:
            labels = [row["operator_proxy_family"] for row in targets if row["problem_family_id"] == family]
            self.assertEqual({"inversion_like", "segmentation_like"}, set(labels))


class ProductionDispatcherCoverageTests(unittest.TestCase):
    def _fixture(self):
        """Independent temporary inputs; source/runtime admission is a seam.

        The dispatcher, freeze/selection consumers, calibration, extraction,
        one-shot receiver, analysis and production package verifier stay real.
        The simulated process identity is not a Python/runtime qualification.
        """
        import copy
        import json
        import sys
        from dataclasses import replace
        from pathlib import Path
        from scripts import a0x_rehearsal as rehearsal
        from latent_triz import a0x_vertical_production_adapter as adapter
        from latent_triz.a0x_contract import derive_pair_output_path, Leg
        from latent_triz.a0x_freeze import _tree_sha256
        from latent_triz.a0x_vertical_terminal_package import _freeze_json, _plain_json
        from tests.test_a0x_vertical_terminal_package import A0XVerticalTerminalPackageTests

        helper = A0XVerticalTerminalPackageTests()
        helper.setUp()
        self.addCleanup(helper.tearDown)
        expected, _result = helper._production_material_fixture()
        previous = expected._production_capability
        helper.doCleanups()  # Do not retain the other test's loader patch.
        root = helper.root
        source = Path(__file__).resolve().parents[1]
        canonical, sha = rehearsal.canonical, rehearsal.sha

        def write(relative, value):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value if isinstance(value, bytes) else canonical(value))
            return path

        protocol_path, calibration_cases, calibration_targets = rehearsal._calibration_inputs(root / "dispatcher", source)
        cases, targets = rehearsal.synthetic_inputs()
        cases_raw = calibration_cases.read_bytes() + b"".join(canonical(row) + b"\n" for row in cases)
        targets_raw = b"".join(canonical(row) + b"\n" for row in targets)
        calibration_raw = calibration_targets.read_bytes()
        write("fixture/cases.jsonl", cases_raw)
        write("data/a0/procedural-targets/calibration-targets.jsonl", calibration_raw)
        write("data/a0/sealed-targets/targets.jsonl", targets_raw)
        manifest = {"files": {"calibration_targets_jsonl": {
            "path": "procedural-targets/calibration-targets.jsonl",
            "sha256": sha(calibration_raw), "size": len(calibration_raw)}}}
        manifest_raw = canonical(manifest)
        write("data/a0/manifest.json", manifest_raw)
        selection = {
            "artifact_class": "a0x-selection-manifest", **rehearsal.COMMON,
            "selection_corpus_sha256": sha(cases_raw),
            "selection_path": "experiments/a0x-six-model/a0-selection-manifest.json",
            "selected_case_count": 48, "source_cases_path": "fixture/cases.jsonl",
            "source_corpus_manifest_path": "data/a0/manifest.json",
            "source_cases_sha256": sha(cases_raw), "source_corpus_manifest_sha256": sha(manifest_raw),
            "selection_rule": {"cases_per_family": 2, "families_per_domain": 4,
                               "family_order": "lexicographic", "domain_order": "frozen"},
            "cases": [{key: row[key] for key in ("case_id", "problem_family_id", "domain", "split")} |
                      {"case_content_sha256": sha(canonical(row))} for row in cases], "target_content_reads": 0,
        }
        selection_raw = canonical(selection)
        write("experiments/a0x-six-model/a0-selection-manifest.json", selection_raw)
        declaration = {"entries": [{"path": "data/a0/sealed-targets/targets.jsonl", "entry_kind": "sealed_target",
                                    "sha256": sha(targets_raw), "size": len(targets_raw)}]}
        write("experiments/a0x-six-model/protected-a0-tree.json", declaration)
        identity = {"leg": "a0", "protocol_id": "synthetic-production-dispatch",
                    "protected_tree_sha256": _tree_sha256(declaration),
                    "selection_corpus_sha256": sha(selection_raw), "source_base_commit": "a" * 40}
        protocol = {"identity": identity, "source_protocol_path": protocol_path.relative_to(root).as_posix(),
                    "source_protocol_raw_sha256": sha(protocol_path.read_bytes())}
        implementation = {"identity": identity}
        package = previous.context.vertical_package["package_path"]
        write(package + "/protocol.json", protocol)
        write(package + "/implementation.json", implementation)
        freeze = {"identity": identity, "protocol_sha256": sha(canonical(protocol)),
                  "implementation_sha256": sha(canonical(implementation))}
        freeze_path = write(package + "/freeze.json", freeze)
        pair = pair_binding(Leg.A0, "smollm2_360m", hidden_width=8)
        pair.update(model_id="HuggingFaceTB/SmolLM2-360M",
                    revision="f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
                    leg_freeze_sha256=sha(freeze_path.read_bytes()), run_id="synthetic-production-dispatch")
        pair["output_path"] = derive_pair_output_path(Leg.A0, "smollm2_360m", pair["run_id"])

        def rebind(value):
            value = copy.deepcopy(_plain_json(value))
            value["pair_binding"] = pair
            return _freeze_json(value)

        context = replace(previous.context, pair_binding=_freeze_json(pair),
                          descriptor=rebind(previous.context.descriptor),
                          execution_inlet=rebind(previous.context.execution_inlet),
                          gate_c_authorization=rebind(previous.context.gate_c_authorization),
                          gate_a_evidence=rebind(previous.context.gate_a_evidence),
                          readiness=_freeze_json({**_plain_json(rebind(previous.context.readiness)),
                              "python": {"path": sys.executable, "version": "3.11.16"},
                              "model_runtime": {"card_path": "fixture/model-card.json"}}))
        dossier = _plain_json(previous.package_documents["approval-dossier.json"])
        dossier["pair_binding"] = pair
        write(package + "/approval-dossier.json", dossier)
        # Retain only known public/synthetic trust objects and rebind identities
        # to the fixture bytes. No real target path is consulted by this test.
        trust = {}
        for relative in previous.context.trust_file_identities:
            raw = (root / relative).read_bytes()
            info = (root / relative).stat()
            trust[relative] = {"device": info.st_dev, "inode": info.st_ino,
                               "size": len(raw), "sha256": sha(raw)}
        context = replace(context, trust_file_identities=_freeze_json(trust))
        capability = adapter._ValidatedProductionCapability(root, "synthetic-dispatch-descriptor.json", context,
            _freeze_json({"approval-dossier.json": dossier, "protocol.json": protocol}), adapter._PRODUCTION_CAPABILITY)
        return capability

    def test_real_production_dispatcher_seals_and_verifies_synthetic_material_once(self):
        import json
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        from latent_triz import a0x_vertical_production_adapter as adapter
        from tests.test_a0x_activations import synthetic_hidden_adapter

        capability = self._fixture()
        model = synthetic_hidden_adapter(layers=33, width=8)
        card = SimpleNamespace(runtime_root="fixture/snapshot")
        # This models an already-admitted Python 3.11 process without loading
        # torch or any tokenizer/weights. Recipe algorithms still run on ASCII
        # synthetic data; this is not proof of a real 3.11 Unicode runtime.
        with patch.object(adapter, "load_vertical_production_capability", return_value=capability), \
             patch.object(adapter.sys, "version_info", (3, 11, 16)), \
             patch.object(adapter.sys, "version", "3.11.16 (synthetic process identity)"), \
             patch("latent_triz.a0_shortcuts.unicodedata.unidata_version", "14.0.0"), \
             patch("latent_triz.a0x_runtime_readiness.validate_runtime_readiness_live"), \
             patch("latent_triz.a0x_preflight.load_model_card", return_value=card), \
             patch("latent_triz.a0x_model_adapter.A0XHiddenStateAdapter.load", return_value=model) as load, \
             patch.dict(sys.modules, {"torch": SimpleNamespace(set_num_threads=lambda value: self.assertEqual(1, value))}):
            result = adapter.run_vertical_production(capability)
        self.assertEqual("completed", result["lifecycle_status"], result)
        self.assertTrue(result["package_verified"])
        self.assertFalse(result["publication_eligible"])
        load.assert_called_once()
        self.assertGreater(model.forwards, 0)
        base = capability.repository_root / ".a0x-runtime/gate-c/v2" / capability.context.source_head / capability.context.source_tree / "a0" / "smollm2_360m" / capability.context.pair_binding["run_id"] / "material"
        target = json.loads((base / "target-read-receipt.json").read_bytes())
        self.assertEqual(1, target["content_reads"])
        self.assertEqual("pass", target["status"])
        self.assertEqual("PASS", result["calibration_status"])
        self.assertIsNone(model.model)
        self.assertIsNone(model.tokenizer)


if __name__ == "__main__":
    unittest.main()
