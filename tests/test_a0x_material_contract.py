from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import A0XContractError, Leg, PairBinding, assert_authorization_chain
from latent_triz.validator import validate
from tests.a0x_test_support import authorization_documents, pair_binding, sha


ROOT = Path(__file__).resolve().parents[1]


class A0XMaterialContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pair = PairBinding.from_mapping(pair_binding(Leg.A0, "gpt2"))
        self.source_head = "a" * 40
        self.runtime_root = ROOT / ".a0x-runtime"
        self.runtime_entries_before = (
            tuple(sorted(path.relative_to(self.runtime_root).as_posix() for path in self.runtime_root.rglob("*")))
            if self.runtime_root.exists() else None
        )

    def tearDown(self) -> None:
        entries_after = (
            tuple(sorted(path.relative_to(self.runtime_root).as_posix() for path in self.runtime_root.rglob("*")))
            if self.runtime_root.exists() else None
        )
        self.assertEqual(self.runtime_entries_before, entries_after)

    def _launch_mapping(self) -> dict[str, object]:
        from latent_triz.a0x_material_contract import derive_runtime_paths

        paths = derive_runtime_paths(self.pair, source_head=self.source_head)
        return {
            "launch_profile": "a0x-guard-launch-v2",
            "ccp": {"role": "ccp", "sha256": sha(10)},
            "python": {"role": "python", "sha256": sha(11)},
            "cwd_kind": "repository_root",
            "source_head": self.source_head,
            "child_script": {"role": "child", "path": "scripts/a0x_material_child.py", "sha256": sha(12)},
            "launch_descriptor": {"role": "descriptor", "path": paths.launch_descriptor_path, "sha256": sha(13)},
            "environment_template": [
                "HF_HUB_OFFLINE=1",
                "TRANSFORMERS_OFFLINE=1",
                "HF_DATASETS_OFFLINE=1",
                "TOKENIZERS_PARALLELISM=false",
                "PYTHONNOUSERSITE=1",
            ],
            "resource": {
                "profile": "a0x-material",
                "workload_family": "latent-triz-a0x-v1",
                "executor": "native",
                "cache_state": "warm",
                "execution_mode": "native",
                "target_platform": "macos-arm64",
                "memory_limit_bytes": 8_589_934_592,
            },
            "timeouts": {
                "outer_timeout_seconds": 3600,
                "internal_budget_seconds": 3300,
                "cleanup_margin_seconds": 300,
                "admission_timeout_seconds": 300,
            },
            "argv_template": [
                "{CCP}", "guard", "exec",
                "--admission-timeout-seconds", "300",
                "--timeout-seconds", "3600",
                "--resource-profile", "a0x-material",
                "--resource-workload-family", "latent-triz-a0x-v1",
                "--resource-executor", "native",
                "--resource-cache-state", "warm",
                "--resource-execution-mode", "native",
                "--resource-target-platform", "macos-arm64",
                "--resource-memory-limit-bytes", "8589934592",
                "--", "{PYTHON}", "{CHILD}",
                "--launch-descriptor", "{DESCRIPTOR}",
            ],
        }

    def _qualification_evidence(self) -> dict[str, object]:
        return {
            "artifact_class": "a0x-qualification-evidence",
            "evidence_profile": "a0x-qualification-evidence-v1",
            "qualification_receipt_id": f"sha256:{sha(20)}",
            "qualification_receipt_raw_sha256": sha(21),
            "qualified_source_head": self.source_head,
            "generation": 1,
            "ccp": {
                "executable_name": "commit-ci-preflight",
                "source_commit": "b" * 40,
                "qualified_source_tree": "c" * 40,
                "binary_sha256": sha(22),
                "version": "commit-ci-preflight 0.1.0",
            },
            "public_evidence": {
                "branch": f"ccp-evidence/{self.source_head}",
                "path": ".ccp/receipt.json",
                "commit": "d" * 40,
            },
        }

    def _gate_a_evidence(self) -> dict[str, object]:
        base = f".a0x-runtime/gate-a/evidence/{self.source_head}"
        return {
            "evidence_profile": "a0x-gate-a-evidence-binding-v2",
            "provider": "github-hosted-attestation-v1",
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "source_head": self.source_head,
            "source_tree": "b" * 40,
            "hosted_inputs": {
                "manifest": {"path": base + "/hosted-gate-a-evidence.json", "sha256": sha(30)},
                "attestation_bundle": {"path": base + "/hosted-gate-a-attestation.bundle.jsonl", "sha256": sha(31)},
                "trusted_root": {"path": base + "/github-trusted-root.jsonl", "sha256": sha(32)},
                "transport": {"path": base + "/hosted-gate-a-transport.json", "sha256": sha(33)},
            },
            "verification_receipt": {
                "path": ".a0x-runtime/gate-b-verifications/" + self.source_head
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

    def _schema(self, name: str) -> dict[str, object]:
        return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))

    def test_runtime_inlet_is_pair_derived_and_outside_results(self) -> None:
        from latent_triz.a0x_material_contract import (
            derive_runtime_paths,
            validate_dossier_authorization_path,
        )

        paths = derive_runtime_paths(self.pair, source_head=self.source_head)
        self.assertEqual(
            ".a0x-runtime/authorizations/a0/gpt2/a0x-a0-gpt2-run-1.json",
            paths.authorization_path,
        )
        self.assertEqual(
            ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json",
            paths.launch_descriptor_path,
        )
        self.assertFalse(paths.authorization_path.startswith("results/"))
        self.assertEqual(
            ".a0x-runtime/qualification/" + self.source_head + "/receipt.json",
            paths.qualification_receipt_path,
        )
        validate_dossier_authorization_path(self.pair, paths.authorization_path)
        for path in (
            self.pair.output_path + "execution-authorization.json",
            ".a0x-runtime/authorizations/r1/gpt2/a0x-a0-gpt2-run-1.json",
            ".a0x-runtime/authorizations/a0/gpt2/other.json",
        ):
            with self.subTest(path=path), self.assertRaisesRegex(A0XContractError, "authorization inlet"):
                validate_dossier_authorization_path(self.pair, path)
        self.assertIn(".a0x-runtime/", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_timeout_envelope_is_exact_and_rejects_variants(self) -> None:
        from latent_triz.a0x_material_contract import TimeoutEnvelope

        valid = {
            "outer_timeout_seconds": 3600,
            "internal_budget_seconds": 3300,
            "cleanup_margin_seconds": 300,
            "admission_timeout_seconds": 300,
        }
        envelope = TimeoutEnvelope.from_mapping(valid)
        self.assertEqual(valid, envelope.as_mapping())
        for key, value in (
            ("outer_timeout_seconds", 3599),
            ("internal_budget_seconds", 3301),
            ("cleanup_margin_seconds", True),
            ("admission_timeout_seconds", 0),
            ("admission_timeout_seconds", -1),
            ("outer_timeout_seconds", None),
        ):
            candidate = copy.deepcopy(valid)
            candidate[key] = value
            with self.subTest(key=key, value=value), self.assertRaisesRegex(A0XContractError, "timeout envelope"):
                TimeoutEnvelope.from_mapping(candidate)
        variant = {**valid, "per_model_timeout_seconds": 3600}
        with self.assertRaisesRegex(A0XContractError, "timeout envelope"):
            TimeoutEnvelope.from_mapping(variant)

    def test_guard_launch_has_one_recomputable_shell_free_argv(self) -> None:
        from latent_triz.a0x_material_contract import (
            A0XGuardLaunch,
            canonical_guard_commitment,
            validate_guard_launch_pair_binding,
        )

        launch = self._launch_mapping()
        parsed = A0XGuardLaunch.from_mapping(launch)
        self.assertEqual(launch["argv_template"], list(parsed.argv_template))
        self.assertEqual(canonical_guard_commitment(launch), canonical_guard_commitment(parsed))
        mutations = {
            "ccp_role": lambda value: value["ccp"].__setitem__("role", "other"),
            "python_role": lambda value: value["python"].__setitem__("role", "other"),
            "cwd_kind": lambda value: value.__setitem__("cwd_kind", "host_path"),
            "child_script": lambda value: value["child_script"].__setitem__("path", "scripts/other_child.py"),
            "descriptor": lambda value: value["launch_descriptor"].__setitem__("path", ".a0x-runtime/launches/a0/gpt2/other.json"),
            "environment_subset": lambda value: value["environment_template"].pop(),
            "environment_order": lambda value: value.__setitem__("environment_template", list(reversed(value["environment_template"]))),
            "timeout": lambda value: value["argv_template"].__setitem__(6, "3599"),
            "resource_label": lambda value: value["argv_template"].__setitem__(8, "other"),
            "memory_limit": lambda value: value["argv_template"].__setitem__(20, "1"),
            "separator": lambda value: value["argv_template"].__setitem__(21, "---"),
            "child_argument": lambda value: value["argv_template"].__setitem__(25, ".a0x-runtime/other.json"),
        }
        for name, mutate in mutations.items():
            candidate = copy.deepcopy(launch)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaisesRegex(A0XContractError, "guard launch"):
                parsed_candidate = A0XGuardLaunch.from_mapping(candidate)
                validate_guard_launch_pair_binding(self.pair, parsed_candidate)

    def test_qualification_evidence_is_public_safe_and_hash_bound(self) -> None:
        from latent_triz.a0x_material_contract import validate_qualification_evidence

        evidence = self._qualification_evidence()
        self.assertEqual(evidence, validate_qualification_evidence(evidence))
        self.assertEqual([], validate(evidence, self._schema("a0x-qualification-evidence.schema.json")))
        for field, mutate in (
            ("receipt_id", lambda value: value.__setitem__("qualification_receipt_id", "sha256:short")),
            ("receipt_hash", lambda value: value.__setitem__("qualification_receipt_raw_sha256", "f" * 63)),
            ("source_head", lambda value: value.__setitem__("qualified_source_head", "short")),
            ("local_branch", lambda value: value["public_evidence"].__setitem__("branch", "/Users/marco/private")),
            ("local_path", lambda value: value["public_evidence"].__setitem__("path", "/private/tmp/receipt.json")),
            ("private_field", lambda value: value.__setitem__("raw_log_path", "private.log")),
        ):
            candidate = copy.deepcopy(evidence)
            mutate(candidate)
            with self.subTest(field=field), self.assertRaisesRegex(A0XContractError, "qualification evidence"):
                validate_qualification_evidence(candidate)

    def test_gate_a_evidence_uses_an_explicit_current_or_historical_profile(self) -> None:
        from latent_triz.a0x_material_contract import validate_gate_a_evidence

        current = self._gate_a_evidence()
        self.assertEqual(current, validate_gate_a_evidence(current))
        self.assertEqual([], validate(current, self._schema("a0x-qualification-evidence.schema.json")))
        with self.assertRaisesRegex(A0XContractError, "Gate A"):
            validate_gate_a_evidence(self._qualification_evidence())
        self.assertEqual(
            self._qualification_evidence(),
            validate_gate_a_evidence(self._qualification_evidence(), historical=True),
        )

        for field, mutate in (
            ("provider", lambda value: value.__setitem__("provider", "ccp")),
            ("missing_input", lambda value: value["hosted_inputs"].pop("transport")),
            ("receipt_path", lambda value: value["verification_receipt"].__setitem__("path", "/private/receipt.json")),
            ("verifier_hash", lambda value: value["verifier"].__setitem__("sha256", sha(36))),
        ):
            candidate = copy.deepcopy(current)
            mutate(candidate)
            with self.subTest(field=field), self.assertRaisesRegex(A0XContractError, "Gate A"):
                validate_gate_a_evidence(candidate)

    def test_material_contract_requires_the_frozen_gate_a_policy(self) -> None:
        schema = self._schema("a0x-material-execution-contract.schema.json")
        contract = json.loads(
            (ROOT / "experiments/a0x-six-model/material-execution-contract.json").read_text(
                encoding="utf-8",
            ),
        )
        self.assertEqual([], validate(contract, schema))
        self.assertEqual(
            {"manifest": 32768, "attestation_bundle": 1048576, "trusted_root": 2097152, "transport": 16384},
            contract["gate_a"]["size_ceilings_bytes"],
        )
        contract.pop("gate_a")
        self.assertTrue(validate(contract, schema))

    def test_guard_launch_rejects_host_absolute_paths(self) -> None:
        from latent_triz.a0x_material_contract import A0XGuardLaunch

        launch = self._launch_mapping()
        for field, value in (
            ("ccp", "/Users/marco1/.cargo/bin/commit-ci-preflight"),
            ("python", "/private/tmp/python"),
            ("child_script", "/tmp/a0x_material_child.py"),
        ):
            candidate = copy.deepcopy(launch)
            candidate[field]["path"] = value
            with self.subTest(field=field), self.assertRaisesRegex(A0XContractError, "guard launch"):
                A0XGuardLaunch.from_mapping(candidate)

    def test_new_schemas_reject_local_and_opaque_contract_values(self) -> None:
        from latent_triz.a0x_material_contract import A0XGuardLaunch

        launch = self._launch_mapping()
        self.assertEqual([], validate(launch, self._schema("a0x-guard-launch.schema.json")))
        self.assertEqual([], validate(self._qualification_evidence(), self._schema("a0x-qualification-evidence.schema.json")))
        dossier, authorization, _ = authorization_documents(self.pair.as_mapping())
        authorization["guard_launch"] = launch
        authorization["qualification_evidence"] = self._qualification_evidence()
        self.assertEqual([], validate(authorization, self._schema("a0x-execution-authorization.schema.json")))
        self.assertEqual([], validate(dossier, self._schema("a0x-authorization-dossier.schema.json")))
        invalid = copy.deepcopy(launch)
        invalid["argv_template"].pop()
        self.assertTrue(validate(invalid, self._schema("a0x-guard-launch.schema.json")))
        with self.assertRaisesRegex(A0XContractError, "guard launch"):
            A0XGuardLaunch.from_mapping(invalid)

        malformed_runtime_path = copy.deepcopy(launch)
        malformed_runtime_path["launch_descriptor"]["path"] = ".a0x-runtime/launches/a0/gpt2/.."
        self.assertTrue(validate(malformed_runtime_path, self._schema("a0x-guard-launch.schema.json")))
        with self.assertRaisesRegex(A0XContractError, "guard launch"):
            A0XGuardLaunch.from_mapping(malformed_runtime_path)

    def test_authorization_chain_enforces_runtime_inlet_and_public_bindings(self) -> None:
        dossier, authorization, chain = authorization_documents(self.pair.as_mapping())
        downstream = {"pair_binding": self.pair.as_mapping(), "authorization_chain": chain}
        assert_authorization_chain(dossier, authorization, [downstream])
        invalid_authorization = copy.deepcopy(authorization)
        invalid_authorization["authorization_inlet_path"] = ".a0x-runtime/authorizations/a0/gpt2/other.json"
        with self.assertRaisesRegex(A0XContractError, "authorization inlet"):
            assert_authorization_chain(dossier, invalid_authorization, [downstream])

        mismatched_implementation_anchor = copy.deepcopy(authorization)
        mismatched_implementation_anchor["implementation_source_head"] = "f" * 40
        with self.assertRaisesRegex(A0XContractError, "implementation source head"):
            assert_authorization_chain(dossier, mismatched_implementation_anchor, [downstream])

    def test_authorization_chain_cross_binds_evidence_branch_and_ccp_identities(self) -> None:
        dossier, authorization, chain = authorization_documents(self.pair.as_mapping())
        downstream = {"pair_binding": self.pair.as_mapping(), "authorization_chain": chain}
        mutations = {
            "evidence_branch": lambda value: value["qualification_evidence"]["public_evidence"].__setitem__("branch", "ccp-evidence/" + "f" * 40),
            "evidence_source_head": lambda value: value["qualification_evidence"].__setitem__("qualified_source_head", "f" * 40),
            "authorization_ccp_sha": lambda value: value["ccp"].__setitem__("sha256", sha(99)),
            "guard_ccp_sha": lambda value: value["guard_launch"]["ccp"].__setitem__("sha256", sha(99)),
            "evidence_ccp_sha": lambda value: value["qualification_evidence"]["ccp"].__setitem__("binary_sha256", sha(99)),
            "authorization_ccp_source": lambda value: value["ccp"].__setitem__("source_commit", "f" * 40),
            "evidence_ccp_source": lambda value: value["qualification_evidence"]["ccp"].__setitem__("source_commit", "f" * 40),
            "authorization_ccp_tree": lambda value: value["ccp"].__setitem__("qualified_source_tree", "f" * 40),
            "evidence_ccp_tree": lambda value: value["qualification_evidence"]["ccp"].__setitem__("qualified_source_tree", "f" * 40),
            "authorization_ccp_version": lambda value: value["ccp"].__setitem__("version", "commit-ci-preflight 9.9.9"),
            "evidence_ccp_version": lambda value: value["qualification_evidence"]["ccp"].__setitem__("version", "commit-ci-preflight 9.9.9"),
        }
        for name, mutate in mutations.items():
            candidate = copy.deepcopy(authorization)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaisesRegex(A0XContractError, "source head|qualification evidence|CCP identity"):
                assert_authorization_chain(dossier, candidate, [downstream])


if __name__ == "__main__":
    unittest.main()
