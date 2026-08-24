from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import (
    A0XContractError,
    Leg,
    assert_leg_freeze_binding,
    assert_pair_binding,
    assert_single_pair,
    build_leg_freeze_binding,
    canonical_json_sha256,
    compute_dense_bound,
    endpoint_indices,
    sha256_file,
)
from tests.a0x_test_support import A0XTempTestCase, artifact, pair_binding, sha


class A0XContractTests(A0XTempTestCase):
    def _frozen_binding(self):
        protocol = artifact("a0x-protocol.schema.json")
        implementation = artifact("a0x-implementation.schema.json")
        protocol_path = self.write_json("protocol.json", protocol)
        implementation_path = self.write_json("implementation.json", implementation)
        freeze = artifact("a0x-freeze-manifest.schema.json")
        freeze["protocol_sha256"] = sha256_file(protocol_path)
        freeze["implementation_sha256"] = sha256_file(implementation_path)
        freeze_path = self.write_json("freeze.json", freeze)
        return build_leg_freeze_binding(protocol_path, implementation_path, freeze_path)

    def test_exact_endpoints_and_dense_bounds(self) -> None:
        self.assertEqual((0, 2, 4, 6), endpoint_indices(Leg.A0))
        self.assertEqual((6,), endpoint_indices(Leg.R1))
        self.assertEqual(28_049_408, compute_dense_bound(Leg.A0, cases=48, hidden_width=1024).total_bytes)
        self.assertEqual(3_145_728, compute_dense_bound(Leg.R1, cases=48, hidden_width=1024).total_bytes)

    def test_cross_pair_collection_is_rejected(self) -> None:
        rows = [
            {"leg": "a0", "model_key": "gpt2"},
            {"leg": "a0", "model_key": "smollm2_135m"},
        ]
        with self.assertRaisesRegex(A0XContractError, "exactly one leg/model pair"):
            assert_single_pair(rows)

    def test_dense_bound_rejects_wrong_case_count_and_cap_overflow(self) -> None:
        with self.assertRaisesRegex(A0XContractError, "dense output reservation exceeds frozen contract"):
            compute_dense_bound(Leg.A0, cases=47, hidden_width=1024)
        with self.assertRaisesRegex(A0XContractError, "dense output reservation exceeds frozen contract"):
            compute_dense_bound(Leg.R1, cases=48, hidden_width=10000)

    def test_freeze_binding_is_derived_without_a_self_hash(self) -> None:
        binding = self._frozen_binding()
        freeze = artifact("a0x-freeze-manifest.schema.json")
        protocol = artifact("a0x-protocol.schema.json")
        implementation = artifact("a0x-implementation.schema.json")
        self.assertEqual(sha256_file(self.temp_path / "freeze.json"), binding.leg_freeze_sha256)
        self.assertNotIn("freeze_sha256", freeze)
        self.assertNotIn("protocol_sha256", protocol)
        self.assertNotIn("implementation_sha256", implementation)

    def test_leg_freeze_binding_rejects_wrong_dossier_leg_or_hash(self) -> None:
        binding = self._frozen_binding()
        dossiers = [{"pair_binding": pair_binding(model_key=f"model-{index}")} for index in range(6)]
        for dossier in dossiers:
            dossier["pair_binding"]["leg_freeze_sha256"] = binding.leg_freeze_sha256
        assert_leg_freeze_binding(binding, dossiers)

        wrong_leg = copy.deepcopy(dossiers)
        wrong_leg[0]["pair_binding"]["leg"] = "r1"
        with self.assertRaisesRegex(A0XContractError, "leg freeze binding"):
            assert_leg_freeze_binding(binding, wrong_leg)

        wrong_hash = copy.deepcopy(dossiers)
        wrong_hash[0]["pair_binding"]["leg_freeze_sha256"] = sha(99)
        with self.assertRaisesRegex(A0XContractError, "leg freeze binding"):
            assert_leg_freeze_binding(binding, wrong_hash)

    def test_pair_binding_rejects_recursive_mismatched_model(self) -> None:
        root = pair_binding()
        publication = artifact("a0x-publication-manifest.schema.json")
        receipt = artifact("a0x-model-identity-receipt.schema.json")
        publication["pair_binding"] = copy.deepcopy(root)
        receipt["pair_binding"] = copy.deepcopy(root)
        receipt["pair_binding"]["model_key"] = "smollm2_135m"
        with self.assertRaisesRegex(A0XContractError, "pair binding"):
            assert_pair_binding(root, [publication, {"nested": [receipt]}])
