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


if __name__ == "__main__":
    unittest.main()
