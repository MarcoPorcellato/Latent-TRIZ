from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    Leg,
    PairBinding,
    assert_authorization_chain,
    assert_leg_freeze_binding,
    assert_pair_binding,
    assert_single_pair,
    build_leg_freeze_binding,
    canonical_commitment,
    canonical_json_sha256,
    compute_dense_bound,
    endpoint_indices,
    sha256_file,
    strict_json_object,
)
from latent_triz.validator import validate
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

    def test_single_pair_rejects_missing_invalid_and_unknown_identity(self) -> None:
        for rows in ([{}], [{"leg": "other", "model_key": "gpt2"}], [{"leg": "a0", "model_key": ""}], [{"leg": "a0", "model_key": "unknown"}]):
            with self.subTest(rows=rows), self.assertRaisesRegex(A0XContractError, "exactly one leg/model pair"):
                assert_single_pair(rows)

    def test_pair_binding_rejects_invalid_identity_and_malformed_dense_bound(self) -> None:
        for mutate in (
            lambda value: value.__setitem__("leg", "other"),
            lambda value: value.__setitem__("model_key", "unknown"),
            lambda value: value["dense_bound"].__setitem__("leg", "r1"),
            lambda value: value["dense_bound"].__setitem__("total_bytes", 1),
            lambda value: value["dense_bound"].__setitem__("scalar_bytes", 8),
        ):
            value = pair_binding()
            mutate(value)
            with self.subTest(value=value), self.assertRaisesRegex(A0XContractError, "pair binding|dense bound"):
                PairBinding.from_mapping(value)

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

    def test_direct_pair_binding_root_is_revalidated(self) -> None:
        value = pair_binding()
        malformed_dense = copy.deepcopy(value["dense_bound"])
        malformed_dense["leg"] = "r1"
        invalid_root = PairBinding(
            binding_profile="a0x-pair-scope-v2",
            leg=Leg.A0,
            leg_freeze_sha256=value["leg_freeze_sha256"],
            model_key="unknown",
            model_id=value["model_id"],
            revision=value["revision"],
            run_id=value["run_id"],
            output_path=value["output_path"],
            dense_bound=malformed_dense,
        )
        with self.assertRaisesRegex(A0XContractError, "pair binding|dense bound"):
            assert_pair_binding(invalid_root, [])

        valid_root = PairBinding.from_mapping(pair_binding())
        assert_pair_binding(valid_root, [])

    def test_pair_binding_rejects_misleading_occupancy_totals(self) -> None:
        root = pair_binding()
        occupancy = artifact("a0x-output-occupancy-receipt.schema.json")
        occupancy["pair_binding"] = copy.deepcopy(root)
        for field in ("allocated_bytes", "total_bytes"):
            misleading = copy.deepcopy(occupancy)
            misleading[field] = 1
            with self.subTest(field=field), self.assertRaisesRegex(A0XContractError, "occupancy"):
                assert_pair_binding(root, [misleading])

    def _authorization_documents(self):
        return (
            artifact("a0x-authorization-dossier.schema.json"),
            artifact("a0x-execution-authorization.schema.json"),
            artifact("a0x-model-identity-receipt.schema.json"),
        )

    def _schema(self, name: str) -> dict[str, object]:
        root = Path(__file__).resolve().parents[1]
        return json.loads((root / "schemas" / name).read_text(encoding="utf-8"))

    def test_commitments_are_canonical_domain_separated_and_semantic(self) -> None:
        dossier, authorization, _ = self._authorization_documents()
        self.assertEqual([], validate(dossier, self._schema("a0x-authorization-dossier.schema.json")))
        self.assertEqual([], validate(authorization, self._schema("a0x-execution-authorization.schema.json")))
        first = canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE)
        self.assertEqual(
            "e0f7053ece6c554e505094faffa847239b5346cfa722f4ac2526da4f85da341c",
            first.commitment_sha256,
        )
        compact_variant = strict_json_object(
            json.dumps(dossier, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        )
        whitespace_variant = strict_json_object(
            json.dumps({key: dossier[key] for key in reversed(tuple(dossier))}, indent=2, ensure_ascii=False).encode("utf-8"),
        )
        self.assertEqual(
            canonical_commitment(whitespace_variant, APPROVAL_DOSSIER_PROFILE),
            canonical_commitment(compact_variant, APPROVAL_DOSSIER_PROFILE),
        )
        mutated = copy.deepcopy(dossier)
        mutated["pair_binding"]["output_path"] = "results/a0x/a0/gpt2/semantic-mutation/"
        self.assertEqual([], validate(mutated, self._schema("a0x-authorization-dossier.schema.json")))
        self.assertNotEqual(first, canonical_commitment(mutated, APPROVAL_DOSSIER_PROFILE))
        self.assertNotEqual(
            canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE), first,
        )
        self.assertEqual(
            "88713dc61edc945f66fe027dc0819d2cdf087a670b427a1047c0eb844d852835",
            canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE).commitment_sha256,
        )
        for invalid_document, profile in (
            ({"arbitrary": True}, APPROVAL_DOSSIER_PROFILE),
            (dossier, EXECUTION_AUTHORIZATION_PROFILE),
            (authorization, APPROVAL_DOSSIER_PROFILE),
        ):
            with self.subTest(profile=profile), self.assertRaisesRegex(A0XContractError, "schema"):
                canonical_commitment(invalid_document, profile)

    def test_strict_commitment_json_rejects_noncanonical_inputs(self) -> None:
        valid = b'{"a":1,"b":[true,null]}'
        self.assertEqual({"a": 1, "b": [True, None]}, strict_json_object(valid))
        for raw in (
            b'\xef\xbb\xbf{"a":1}',
            b'{"a":1,"a":2}',
            b'{"a":1.0}',
            b'{"a":NaN}',
            b'{"a":Infinity}',
        ):
            with self.subTest(raw=raw), self.assertRaisesRegex(A0XContractError, "strict JSON"):
                strict_json_object(raw)
        for value in ({"a": 1.0}, {"a": float("nan")}, {"a": {1, 2}}):
            with self.subTest(value=value), self.assertRaisesRegex(A0XContractError, "canonical commitment"):
                canonical_commitment(value, APPROVAL_DOSSIER_PROFILE)

    def test_authorization_chain_rejects_legacy_profile_pair_and_chain_substitution(self) -> None:
        dossier, authorization, downstream = self._authorization_documents()
        assert_authorization_chain(dossier, authorization, [downstream])

        legacy = copy.deepcopy(dossier)
        legacy["pair_binding"]["dossier_sha256"] = sha(4)
        with self.assertRaisesRegex(A0XContractError, "schema|pair binding"):
            assert_authorization_chain(legacy, authorization, [downstream])

        wrong_profile = copy.deepcopy(authorization)
        wrong_profile["approved_dossier_commitment"]["profile"] = "unexpected"
        with self.assertRaisesRegex(A0XContractError, "schema|commitment"):
            assert_authorization_chain(dossier, wrong_profile, [downstream])

        wrong_pair = copy.deepcopy(downstream)
        wrong_pair["pair_binding"]["model_key"] = "smollm2_135m"
        with self.assertRaisesRegex(A0XContractError, "pair binding"):
            assert_authorization_chain(dossier, authorization, [wrong_pair])

        wrong_chain = copy.deepcopy(downstream)
        wrong_chain["authorization_chain"]["authorization_commitment"]["commitment_sha256"] = sha(99)
        with self.assertRaisesRegex(A0XContractError, "authorization chain"):
            assert_authorization_chain(dossier, authorization, [wrong_chain])

        self_committing = copy.deepcopy(authorization)
        self_committing["authorization_commitment"] = sha(99)
        with self.assertRaisesRegex(A0XContractError, "schema|own commitment"):
            assert_authorization_chain(dossier, self_committing, [downstream])

    def test_authorization_chain_rejects_empty_masked_and_schema_invalid_documents(self) -> None:
        dossier, authorization, downstream = self._authorization_documents()
        with self.assertRaisesRegex(A0XContractError, "at least one downstream"):
            assert_authorization_chain(dossier, authorization, [])

        chainless_root = {"nested": downstream}
        with self.assertRaisesRegex(A0XContractError, "downstream artifact root"):
            assert_authorization_chain(dossier, authorization, [chainless_root])

        nested_mask = copy.deepcopy(downstream)
        nested_mask["nested"] = {"pair_binding": copy.deepcopy(downstream["pair_binding"])}
        with self.assertRaisesRegex(A0XContractError, "authorization chain"):
            assert_authorization_chain(dossier, authorization, [nested_mask])

        nested_pair_mismatch = copy.deepcopy(downstream)
        nested_pair_mismatch["nested"] = {
            "pair_binding": copy.deepcopy(downstream["pair_binding"]),
            "authorization_chain": copy.deepcopy(downstream["authorization_chain"]),
        }
        nested_pair_mismatch["nested"]["pair_binding"]["model_key"] = "smollm2_135m"
        with self.assertRaisesRegex(A0XContractError, "pair binding"):
            assert_authorization_chain(dossier, authorization, [nested_pair_mismatch])

        nested_chain_mismatch = copy.deepcopy(downstream)
        nested_chain_mismatch["nested"] = {
            "pair_binding": copy.deepcopy(downstream["pair_binding"]),
            "authorization_chain": copy.deepcopy(downstream["authorization_chain"]),
        }
        nested_chain_mismatch["nested"]["authorization_chain"]["dossier_commitment"]["commitment_sha256"] = sha(99)
        with self.assertRaisesRegex(A0XContractError, "authorization chain"):
            assert_authorization_chain(dossier, authorization, [nested_chain_mismatch])

        invalid_dossier = copy.deepcopy(dossier)
        invalid_dossier["evidence_eligible"] = True
        with self.assertRaisesRegex(A0XContractError, "schema"):
            assert_authorization_chain(invalid_dossier, authorization, [downstream])

        invalid_authorization = copy.deepcopy(authorization)
        invalid_authorization["claim_ids"] = ["forbidden"]
        with self.assertRaisesRegex(A0XContractError, "schema"):
            assert_authorization_chain(dossier, invalid_authorization, [downstream])
