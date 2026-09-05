from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    LEGACY_EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    Leg,
    PairBinding,
    V2_MEMBER_NAMES,
    VERTICAL_PACKAGE_COMMITMENT_PROFILE,
    assert_authorization_chain,
    assert_leg_freeze_binding,
    assert_pair_binding,
    assert_single_pair,
    build_leg_freeze_binding,
    build_vertical_package_commitment,
    canonical_commitment,
    canonical_json_sha256,
    compute_dense_bound,
    derive_pair_output_path,
    endpoint_indices,
    sha256_file,
    strict_json_object,
    validate_vertical_package_commitment,
)
from latent_triz.validator import validate
from tests.a0x_test_support import A0XTempTestCase, artifact, pair_binding, sha


class A0XContractTests(A0XTempTestCase):
    def test_v2_package_commitment_is_external_ordered_and_domain_separated(self) -> None:
        pair = PairBinding.from_mapping(pair_binding())
        members = [
            {"name": name, "size": index + 1, "sha256": sha(index + 70)}
            for index, name in enumerate(V2_MEMBER_NAMES)
        ]
        document = build_vertical_package_commitment(
            qualified_source={"head": "a" * 40, "tree": "b" * 40, "ref": "refs/heads/main"},
            pair=pair,
            members=members,
            generator={"profile": "a0x-vertical-slice-v2", "repository": "MarcoPorcellato/Latent-TRIZ"},
            authorization_id="p0-auth-test-01",
            attempt_id="p0-attempt-test-01",
        )
        self.assertEqual(VERTICAL_PACKAGE_COMMITMENT_PROFILE, document["profile"])
        self.assertNotIn("commitment_raw_sha256", document)
        self.assertEqual(document, validate_vertical_package_commitment(document))
        for mutate in (
            lambda value: value.__setitem__("members", list(reversed(value["members"]))),
            lambda value: value["members"][0].__setitem__("size", 0),
            lambda value: value.__setitem__("package_commitment_sha256", "A" * 64),
            lambda value: value.__setitem__("raw_sha256", sha(99)),
        ):
            rejected = copy.deepcopy(document)
            mutate(rejected)
            with self.subTest(rejected=rejected), self.assertRaisesRegex(A0XContractError, "vertical package"):
                validate_vertical_package_commitment(rejected)

    def _current_gate_a_evidence(self, source_head: str = "a" * 40) -> dict[str, object]:
        base = f".a0x-runtime/gate-a/evidence/{source_head}"
        return {
            "evidence_profile": "a0x-gate-a-evidence-binding-v2",
            "provider": "github-hosted-attestation-v1",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "source_head": source_head,
            "source_tree": "b" * 40,
            "gate_b_authorization_raw_sha256": sha(35),
            "hosted_inputs": {
                "manifest": {"path": base + "/hosted-gate-a-evidence.json", "sha256": sha(30)},
                "attestation_bundle": {"path": base + "/hosted-gate-a-attestation.bundle.jsonl", "sha256": sha(31)},
                "trusted_root": {"path": base + "/github-trusted-root.jsonl", "sha256": sha(32)},
                "transport": {"path": base + "/hosted-gate-a-transport.json", "sha256": sha(33)},
            },
            "verification_receipt": {
                "path": ".a0x-runtime/gate-b-verifications/" + source_head
                + "/a0/gpt2/synthetic/gate-a-verification-receipt.json",
                "sha256": sha(34),
            },
            "verifier": {
                "role": "github_cli_verifier",
                "version": "gh version 2.97.0 (2026-07-31)",
                "sha256": "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c",
                "policy_raw_sha256": "e2e11f6bec9740d7e2025eae80fe87fa29d79436faa3a2c5c1ca7d55ceb9e4b4",
            },
        }

    def _current_authorization_documents(self):
        dossier, authorization, downstream = self._authorization_documents()
        authorization["commitment_profile"] = "a0x-execution-authorization-json-v3"
        authorization.pop("qualification_evidence")
        authorization["source_tree"] = "b" * 40
        authorization["gate_a_evidence"] = self._current_gate_a_evidence(authorization["source_head"])
        downstream["authorization_chain"]["authorization_commitment"] = canonical_commitment(
            authorization, "a0x-execution-authorization-json-v3",
        ).as_mapping()
        return dossier, authorization, downstream

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

    def test_pair_rejects_model_root_output(self) -> None:
        value = pair_binding()
        value["output_path"] = f"results/a0x/{value['leg']}/{value['model_key']}/"
        with self.assertRaisesRegex(A0XContractError, "derived output path"):
            PairBinding.from_mapping(value)

    def test_pair_rejects_noncanonical_output_paths(self) -> None:
        value = pair_binding()
        canonical = value["output_path"]
        invalid_paths = (
            canonical + "-different",
            f"results/a0x/r1/{value['model_key']}/{value['run_id']}",
            f"results/a0x/{value['leg']}/smollm2_135m/{value['run_id']}",
            canonical + "/",
        )
        for output_path in invalid_paths:
            rejected = copy.deepcopy(value)
            rejected["output_path"] = output_path
            with self.subTest(output_path=output_path), self.assertRaisesRegex(
                A0XContractError, "derived output path",
            ):
                PairBinding.from_mapping(rejected)

        traversal = copy.deepcopy(value)
        traversal["output_path"] = f"results/a0x/{value['leg']}/{value['model_key']}/../{value['run_id']}"
        with self.assertRaisesRegex(A0XContractError, "pair binding"):
            PairBinding.from_mapping(traversal)

    def test_pair_derivation_rejects_unsafe_segments(self) -> None:
        self.assertEqual(
            "results/a0x/a0/gpt2/run-1",
            derive_pair_output_path(Leg.A0, "gpt2", "run-1"),
        )
        for model_key, run_id in (
            ("../gpt2", "run-1"),
            ("gpt2", "../run-1"),
            ("gpt2/other", "run-1"),
            ("gpt2", "run-1/other"),
            ("gpt2", ""),
        ):
            with self.subTest(model_key=model_key, run_id=run_id), self.assertRaisesRegex(
                A0XContractError, "safe pair segment",
            ):
                derive_pair_output_path("a0", model_key, run_id)

    def test_all_tracked_dossier_pairs_reserialize_byte_identically(self) -> None:
        dossier_root = Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/approval-dossiers"
        dossiers = sorted(dossier_root.glob("*/*.json"))
        self.assertEqual(12, len(dossiers))
        for path in dossiers:
            with self.subTest(path=path):
                original = json.loads(path.read_text(encoding="utf-8"))["pair_binding"]
                parsed = PairBinding.from_mapping(original)
                original_bytes = json.dumps(original, sort_keys=True, separators=(",", ":")).encode("utf-8")
                reserialized_bytes = json.dumps(
                    parsed.as_mapping(), sort_keys=True, separators=(",", ":"),
                ).encode("utf-8")
                self.assertEqual(original_bytes, reserialized_bytes)
                self.assertEqual(
                    parsed.output_path,
                    derive_pair_output_path(parsed.leg, parsed.model_key, parsed.run_id),
                )

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
            "48debe880fc4a24b0ebaf35a67ff0b6bd278e4a28333f88090f9e9403de8fef8",
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
        mutated["pair_binding"]["output_path"] = "results/a0x/a0/gpt2/semantic-mutation"
        self.assertEqual([], validate(mutated, self._schema("a0x-authorization-dossier.schema.json")))
        self.assertNotEqual(first, canonical_commitment(mutated, APPROVAL_DOSSIER_PROFILE))
        self.assertNotEqual(
            canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE), first,
        )
        self.assertEqual(
            "9314b1e47bcb63086fbcf7365b1b32bb375f89411b16378d5bcfa2e2451ae470",
            canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE).commitment_sha256,
        )
        for invalid_document, profile in (
            ({"arbitrary": True}, APPROVAL_DOSSIER_PROFILE),
            (dossier, EXECUTION_AUTHORIZATION_PROFILE),
            (authorization, APPROVAL_DOSSIER_PROFILE),
        ):
            with self.subTest(profile=profile), self.assertRaisesRegex(A0XContractError, "schema"):
                canonical_commitment(invalid_document, profile)

    def test_current_hosted_gate_a_and_gate_c_ccp_identities_are_independent(self) -> None:
        dossier, authorization, downstream = self._current_authorization_documents()
        self.assertEqual(
            "a0x-execution-authorization-json-v3", CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
        )
        self.assertEqual(
            "a0x-execution-authorization-json-v2", LEGACY_EXECUTION_AUTHORIZATION_PROFILE,
        )
        assert_authorization_chain(dossier, authorization, [downstream])

        changed_ccp = copy.deepcopy(authorization)
        changed_ccp["ccp"]["sha256"] = sha(99)
        with self.assertRaisesRegex(A0XContractError, "CCP identity"):
            assert_authorization_chain(dossier, changed_ccp, [downstream])

        same_tree_different_head = copy.deepcopy(authorization)
        changed_head = "f" * 40
        evidence = same_tree_different_head["gate_a_evidence"]
        evidence["source_head"] = changed_head
        for binding in evidence["hosted_inputs"].values():
            binding["path"] = binding["path"].replace("a" * 40, changed_head)
        evidence["verification_receipt"]["path"] = evidence["verification_receipt"]["path"].replace(
            "a" * 40, changed_head,
        )
        with self.assertRaisesRegex(A0XContractError, "source head"):
            assert_authorization_chain(dossier, same_tree_different_head, [downstream])

    def test_legacy_v2_authorization_retains_its_schema_and_commitment_bytes(self) -> None:
        _, authorization, _ = self._authorization_documents()
        self.assertEqual(
            "9314b1e47bcb63086fbcf7365b1b32bb375f89411b16378d5bcfa2e2451ae470",
            canonical_commitment(authorization, LEGACY_EXECUTION_AUTHORIZATION_PROFILE).commitment_sha256,
        )
        with self.assertRaisesRegex(A0XContractError, "schema"):
            canonical_commitment(authorization, CURRENT_EXECUTION_AUTHORIZATION_PROFILE)

    def test_current_v3_schema_preserves_gate_c_structural_constraints(self) -> None:
        _, authorization, _ = self._current_authorization_documents()
        schema = self._schema("a0x-execution-authorization-v3.schema.json")
        self.assertEqual([], validate(authorization, schema))
        mutations = {
            "pair": lambda value: value["pair_binding"].__setitem__("binding_profile", "legacy"),
            "dense": lambda value: value["pair_binding"]["dense_bound"].__setitem__("scalar_bytes", 8),
            "guard_resource": lambda value: value["guard_launch"]["resource"].__setitem__("executor", "other"),
            "guard_timeout": lambda value: value["guard_launch"]["timeouts"].__setitem__("outer_timeout_seconds", 3599),
            "preflight": lambda value: value["guard_preflight_observation"].__setitem__("profile", "legacy"),
            "gate_b_authorization_raw_sha256": lambda value: value["gate_a_evidence"].__setitem__("gate_b_authorization_raw_sha256", "0" * 63),
        }
        for name, mutate in mutations.items():
            candidate = copy.deepcopy(authorization)
            mutate(candidate)
            with self.subTest(name=name):
                self.assertTrue(validate(candidate, schema))

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

    def test_dossier_uses_a_committed_implementation_anchor_not_its_future_live_head(self) -> None:
        dossier, authorization, downstream = self._authorization_documents()
        implementation_source_head = "b" * 40
        live_source_head = authorization["source_head"]
        dossier["implementation_source_head"] = implementation_source_head
        authorization["implementation_source_head"] = implementation_source_head
        authorization["approved_dossier_commitment"] = canonical_commitment(
            dossier, APPROVAL_DOSSIER_PROFILE,
        ).as_mapping()
        downstream["dossier_commitment"] = authorization["approved_dossier_commitment"]
        downstream["authorization_commitment"] = canonical_commitment(
            authorization, EXECUTION_AUTHORIZATION_PROFILE,
        ).as_mapping()

        self.assertNotEqual(implementation_source_head, live_source_head)
        assert_authorization_chain(dossier, authorization, [downstream])

    def test_authorization_rejects_an_implementation_anchor_mutation(self) -> None:
        dossier, authorization, downstream = self._authorization_documents()
        dossier["implementation_source_head"] = "b" * 40
        authorization["implementation_source_head"] = "c" * 40
        authorization["approved_dossier_commitment"] = canonical_commitment(
            dossier, APPROVAL_DOSSIER_PROFILE,
        ).as_mapping()
        downstream["dossier_commitment"] = authorization["approved_dossier_commitment"]
        downstream["authorization_commitment"] = canonical_commitment(
            authorization, EXECUTION_AUTHORIZATION_PROFILE,
        ).as_mapping()

        with self.assertRaisesRegex(A0XContractError, "implementation source head"):
            assert_authorization_chain(dossier, authorization, [downstream])

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
