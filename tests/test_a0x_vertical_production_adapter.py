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


if __name__ == "__main__":
    unittest.main()
