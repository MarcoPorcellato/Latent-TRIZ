"""Non-consuming production boundaries; temporary synthetic files only."""
from __future__ import annotations

import os
from pathlib import Path
import hashlib
import builtins
import importlib.util
import io
import json
from dataclasses import replace
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from unittest import mock

from latent_triz import a0x_ccp_executor as executor
from latent_triz.a0x_contract import Leg, PairBinding, canonical_json_sha256
from latent_triz.a0x_vertical_slice import VerticalPackageBinding
from tests.a0x_test_support import pair_binding


TARGETS = ("data/a0/procedural-targets/calibration-targets.jsonl", "data/a0/sealed-targets/targets.jsonl")


def _write_synthetic_json(root: Path, relative: str, value: object) -> bytes:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    path.write_bytes(raw)
    return raw


class _ActiveA0MetadataFixture:
    """Hash-linked public metadata fixture; never creates protected target files."""

    def __init__(self, root: Path):
        self.root = root
        self.a0_targets = ("synthetic/a0/calibration.jsonl", "synthetic/a0/sealed/targets.jsonl")
        self.r1_targets = ("synthetic/r1/calibration.jsonl", "synthetic/r1/sealed.jsonl")
        self.sensitive_paths = tuple(f"synthetic/sensitive/{index}.json" for index in range(14))
        self.profile_path = "synthetic-profile/manifest.json"
        self.package_path = "synthetic/active-p0"
        self.a0_tree_path = "experiments/a0x-six-model/protected-a0-tree.json"
        self.r1_tree_path = "experiments/a0x-six-model/protected-a0r1-tree.json"
        self.selection_path = "experiments/a0x-six-model/a0-selection-manifest.json"
        self.manifest_path = "data/a0/manifest.json"
        self._write_tree(
            leg=Leg.A0, target_path=self.a0_targets[1],
            manifest_path="synthetic/a0/target-provenance.json", tree_path=self.a0_tree_path,
        )
        self._write_tree(
            leg=Leg.R1, target_path=self.r1_targets[1],
            manifest_path="synthetic/r1/target-provenance.json", tree_path=self.r1_tree_path,
        )
        self.manifest_raw = _write_synthetic_json(root, self.manifest_path, {
            "files": {
                "calibration_targets_jsonl": {
                    "path": "procedural-targets/calibration-targets.jsonl",
                    "size": 19,
                    "sha256": "1" * 64,
                },
            },
        })
        cases = []
        for domain in ("agriculture", "energy", "manufacturing", "medicine", "software", "transport"):
            for family_index in range(4):
                family = f"{domain}-family-{family_index}"
                for case_index in range(2):
                    cases.append({
                        "case_id": f"{family}-case-{case_index}",
                        "case_content_sha256": "2" * 64,
                        "domain": domain,
                        "problem_family_id": family,
                        "split": "synthetic",
                    })
        selection = {
            "artifact_class": "a0x-selection-manifest",
            "empirical": True,
            "scientific_status": "exploratory",
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
            "selection_corpus_sha256": "3" * 64,
            "selection_path": self.selection_path,
            "selected_case_count": 48,
            "source_cases_path": "synthetic/cases.jsonl",
            "source_corpus_manifest_path": self.manifest_path,
            "source_cases_sha256": "4" * 64,
            "source_corpus_manifest_sha256": hashlib.sha256(self.manifest_raw).hexdigest(),
            "selection_rule": {
                "cases_per_family": 2,
                "families_per_domain": 4,
                "family_order": "lexicographic",
                "domain_order": "frozen",
            },
            "cases": cases,
            "target_content_reads": 0,
        }
        self.selection_raw = _write_synthetic_json(root, self.selection_path, selection)
        a0_identity = self._identity(
            Leg.A0, protected_tree_sha256=self.a0_tree_sha256,
            selection_corpus_sha256=hashlib.sha256(self.selection_raw).hexdigest(),
        )
        self.a0_freeze_raw = self._write_leg_wrapper(self.package_path, a0_identity)
        r1_identity = self._identity(
            Leg.R1, protected_tree_sha256=self.r1_tree_sha256,
            selection_corpus_sha256="5" * 64,
        )
        self.r1_freeze_raw = self._write_leg_wrapper("experiments/a0x-six-model/r1", r1_identity)

        # Intentionally invalid historical docs and a different batch freeze.
        # Active A0 validation must not read or fall back to these.
        _write_synthetic_json(root, "experiments/a0-automated-weak-proxy/protocol.json", {
            "artifact_class": "legacy-protocol-without-identity",
        })
        _write_synthetic_json(root, "experiments/a0-automated-weak-proxy/implementation.json", {
            "artifact_class": "legacy-implementation-without-identity",
        })
        self.batch_freeze_raw = _write_synthetic_json(
            root, "experiments/a0x-six-model/freeze/a0-freeze.json", {
                "artifact_class": "different-batch-freeze",
                "identity": {"leg": "a0"},
            },
        )
        _write_synthetic_json(root, "experiments/a0r1-independent-proxy/protocol.json", {
            "artifact_class": "legacy-r1-protocol-without-identity",
        })
        _write_synthetic_json(root, "experiments/a0r1-independent-proxy/implementation.json", {
            "artifact_class": "legacy-r1-implementation-without-identity",
        })
        self.profile_raw = _write_synthetic_json(root, self.profile_path, {
            "instance_dispositions": {
                "excluded_sensitive_role_unverified": list(self.sensitive_paths),
            },
        })
        pair = PairBinding.from_mapping(pair_binding(Leg.A0, "smollm2_360m", hidden_width=960))
        self.active_freeze_sha256 = hashlib.sha256(self.a0_freeze_raw).hexdigest()
        self.pair = replace(pair, leg_freeze_sha256=self.active_freeze_sha256)
        self.package_binding = VerticalPackageBinding(
            envelope_path="synthetic/active-p0/envelope.json",
            package_path=self.package_path,
            commitment_path="synthetic/active-p0/commitment.json",
            commitment_raw_sha256="6" * 64,
            package_commitment_sha256="7" * 64,
            dossier_path="synthetic/active-p0/dossier.json",
            dossier_sha256="8" * 64,
            qualified_source_head="a" * 40,
            qualified_source_tree="b" * 40,
            leg=Leg.A0,
            model_key=self.pair.model_key,
            model_revision=self.pair.revision,
            pair_binding=self.pair,
        )

    def _write_tree(self, *, leg: Leg, target_path: str, manifest_path: str, tree_path: str) -> None:
        target_bytes = 23
        provenance = {
            "files": {
                "synthetic-target": {
                    "path": Path(target_path).relative_to(Path(manifest_path).parent).as_posix(),
                    "sha256": "9" * 64,
                    "size": target_bytes,
                },
            },
        }
        provenance_raw = _write_synthetic_json(self.root, manifest_path, provenance)
        entry = {
            "entry_kind": "sealed_target",
            "path": target_path,
            "bytes": target_bytes,
            "sha256": "9" * 64,
            "provenance_manifest": manifest_path,
            "provenance_manifest_sha256": hashlib.sha256(provenance_raw).hexdigest(),
            "verification_phase": "synthetic-pre-model",
        }
        payload = {
            "artifact_class": "a0x-protected-tree",
            "source_base_commit": "c" * 40,
            "entries": [entry],
        }
        tree_sha256 = canonical_json_sha256(payload)
        _write_synthetic_json(self.root, tree_path, {
            **payload,
            "protected_tree_sha256": tree_sha256,
        })
        setattr(self, f"{leg.value}_tree_sha256", tree_sha256)

    @staticmethod
    def _identity(leg: Leg, *, protected_tree_sha256: str, selection_corpus_sha256: str) -> dict[str, str]:
        return {
            "leg": leg.value,
            "protocol_id": f"synthetic-{leg.value}-protocol",
            "protected_tree_sha256": protected_tree_sha256,
            "selection_corpus_sha256": selection_corpus_sha256,
            "source_base_commit": "c" * 40,
        }

    def _write_leg_wrapper(self, package_path: str, identity: dict[str, str]) -> bytes:
        protocol_raw = _write_synthetic_json(self.root, f"{package_path}/protocol.json", {
            "identity": identity,
        })
        implementation_raw = _write_synthetic_json(self.root, f"{package_path}/implementation.json", {
            "identity": identity,
        })
        freeze_relative = (
            f"{package_path}/freeze.json"
            if identity["leg"] == "a0"
            else "experiments/a0x-six-model/freeze/r1-freeze.json"
        )
        freeze = {
            "identity": identity,
            "protocol_sha256": hashlib.sha256(protocol_raw).hexdigest(),
            "implementation_sha256": hashlib.sha256(implementation_raw).hexdigest(),
        }
        return _write_synthetic_json(self.root, freeze_relative, freeze)

    def patch_constants(self):
        return (
            mock.patch.object(executor, "_A0_TARGET_PATHS", self.a0_targets),
            mock.patch.object(executor, "_R1_TARGET_PATHS", self.r1_targets),
            mock.patch.object(executor, "_N3_SENSITIVE_PATHS", self.profile_path),
            mock.patch.object(executor, "_N3_SENSITIVE_PATHS_SHA256", hashlib.sha256(self.profile_raw).hexdigest()),
        )


class ActiveA0MetadataBindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.fixture = _ActiveA0MetadataFixture(self.root)

    def _with_metadata_constants(self, callback):
        patches = self.fixture.patch_constants()
        with patches[0], patches[1], patches[2], patches[3]:
            return callback()

    def _without_target_opens(self, callback):
        targets = {
            (self.root / relative).absolute()
            for relative in (*self.fixture.a0_targets, *self.fixture.r1_targets)
        }

        def forbid(opener):
            def guarded(path, *args, **kwargs):
                try:
                    candidate = Path(os.fsdecode(path)).absolute()
                except (TypeError, ValueError):
                    candidate = None
                if candidate in targets:
                    raise AssertionError("synthetic protected target content open attempted")
                return opener(path, *args, **kwargs)
            return guarded

        with (
            mock.patch.object(builtins, "open", side_effect=forbid(builtins.open)),
            mock.patch.object(io, "open", side_effect=forbid(io.open)),
            mock.patch.object(os, "open", side_effect=forbid(os.open)),
        ):
            return callback()

    def test_metadata_expectations_follow_active_p0_not_legacy_or_batch_freeze(self):
        self.assertNotEqual(
            hashlib.sha256(self.fixture.batch_freeze_raw).hexdigest(),
            self.fixture.active_freeze_sha256,
        )
        self.assertEqual(self.fixture.active_freeze_sha256, self.fixture.pair.leg_freeze_sha256)

        # Bind from the validated active P0. Independently invalid legacy and
        # batch documents must not participate in this metadata decision.
        sizes, other_paths, sources = self._without_target_opens(lambda: self._with_metadata_constants(lambda: (
            executor._bound_a0_material_metadata_expectations(self.root, self.fixture.package_binding)
        )))
        self.assertEqual(
            {self.fixture.a0_targets[0]: 19, self.fixture.a0_targets[1]: 23},
            sizes,
        )
        self.assertEqual(16, len(other_paths))
        self.assertEqual(16, sources["other_protected_path_count"])

    def test_active_p0_freeze_drift_is_refused(self):
        drifted_pair = replace(self.fixture.pair, leg_freeze_sha256="0" * 64)
        drifted_binding = replace(self.fixture.package_binding, pair_binding=drifted_pair)
        with self.assertRaisesRegex(executor.A0XCcpExecutorError, "bound active P0 freeze"):
            self._with_metadata_constants(lambda: (
                executor._bound_a0_material_metadata_expectations(self.root, drifted_binding)
            ))

    def test_r1_wrapper_identity_mismatch_is_refused(self):
        _write_synthetic_json(self.root, "experiments/a0x-six-model/r1/implementation.json", {
            "identity": self.fixture._identity(
                Leg.R1,
                protected_tree_sha256=self.fixture.r1_tree_sha256,
                selection_corpus_sha256="a" * 64,
            ),
        })
        with self.assertRaisesRegex(executor.A0XContractError, "identity mismatch"):
            self._with_metadata_constants(lambda: (
                executor._bound_a0_material_metadata_expectations(self.root, self.fixture.package_binding)
            ))

    def test_preflight_writes_canonical_refusal_for_metadata_contract_failure(self):
        # Malform the validated active P0 protocol identity. The real metadata
        # helper/build-leg-freeze validator must produce the contract failure.
        _write_synthetic_json(self.root, f"{self.fixture.package_path}/protocol.json", {
            "identity": "malformed synthetic P0 identity",
        })

        def validate_metadata(**_kwargs):
            return self._with_metadata_constants(lambda: (
                executor._bound_a0_material_metadata_expectations(self.root, self.fixture.package_binding)
            ))

        with mock.patch.object(executor, "_launch_validated_vertical_v2", side_effect=validate_metadata):
            with self.assertRaises(executor.A0XCcpExecutorError) as refused:
                executor.preflight_vertical_runtime_package(
                    repository_root=self.root,
                    package_binding=self.fixture.package_binding,
                    execution_authorization_path=executor.vertical_execution_authorization_path(
                        self.fixture.package_binding,
                    ),
                )

        report_relative = str(refused.exception).split("private report: ", 1)[1]
        report = json.loads((self.root / report_relative).read_bytes())
        self.assertEqual("REFUSED", report["status"])
        self.assertEqual("A0XContractError", report["failure_type"])
        self.assertFalse(report["permission_window_entered"])
        self.assertFalse(report["claim_created"])
        self.assertFalse(report["material_directory_created"])
        self.assertFalse(report["guard_invoked"])
        self.assertEqual([], list(self.root.rglob("attempt-claim.json")))
        self.assertFalse((self.root / self.fixture.package_binding.pair_binding.output_path).exists())

    def test_preflight_does_not_relabel_programming_errors_as_refusals(self):
        with mock.patch.object(
            executor, "_launch_validated_vertical_v2",
            side_effect=RuntimeError("synthetic programming defect"),
        ):
            with self.assertRaisesRegex(RuntimeError, "synthetic programming defect"):
                executor.preflight_vertical_runtime_package(
                    repository_root=self.root,
                    package_binding=self.fixture.package_binding,
                    execution_authorization_path=executor.vertical_execution_authorization_path(
                        self.fixture.package_binding,
                    ),
                )
        self.assertFalse((self.root / ".a0x-runtime/gate-c-preflight").exists())


class ProductionPipelineCoverageTests(unittest.TestCase):
    """Production admission, with only process/identity/git effects doubled."""

    def _production_fixture(self):
        if sys.platform != "darwin" or getattr(self, "_portable_metadata", False):
            # Linux hosted CI has no Darwin ACL/flags/O_EVTONLY APIs. These
            # external metadata observations are simulated only on disposable
            # files; common ownership, size, inode, mode and link checks stay real.
            for patcher in (
                mock.patch.object(executor, "_check_acl_absent"),
                mock.patch.object(executor, "_read_target_flags", return_value=0),
                mock.patch.object(os, "O_EVTONLY", os.O_NONBLOCK, create=True),
            ):
                patcher.start()
                self.addCleanup(patcher.stop)
        from tests.test_a0x_vertical_runtime_bundle import A0XVerticalRuntimeBundleTests, HEAD, TREE
        from tests.test_a0x_vertical_material import A0XVerticalMaterialTests
        from latent_triz.a0x_gate_contract import VerifierIdentity
        from latent_triz.a0x_public_closure import PRE_EXECUTION_PUBLIC_ROLE_PATHS, PRE_EXECUTION_EXTENSION_PATH
        fixture = A0XVerticalRuntimeBundleTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        root, binding = fixture.root, fixture._binding()
        prepared, request, _verifier = fixture._prepare_synthetic(binding)
        paths = prepared["vertical_outputs"]
        compact = executor._canonical_json

        def read(relative):
            return json.loads((root / relative).read_bytes())

        def write(relative, value, *, lf=False):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(compact(value) + (b"\n" if lf else b""))
            return hashlib.sha256(path.read_bytes()).hexdigest()

        authorization_path = prepared["gate_b_authorization_path"]
        gate_b = read(authorization_path)
        gate_b["qualification_context"] = "production"
        gate_b["verifier"] = VerifierIdentity(
            policy_raw_sha256=gate_b["verifier"]["policy_raw_sha256"],
        ).as_mapping()
        write(authorization_path, gate_b)
        receipt_path = prepared["verification_receipt_path"]
        receipt = read(receipt_path)
        receipt.pop("qualification_context", None)
        receipt.update(artifact_class="a0x-hosted-gate-a-verification-receipt",
                       receipt_profile="a0x-hosted-gate-a-verification-receipt-v1",
                       authorization_raw_sha256=hashlib.sha256((root / authorization_path).read_bytes()).hexdigest(),
                       verifier=gate_b["verifier"])
        write(receipt_path, receipt, lf=True)
        source = {"head": HEAD, "tree": TREE, "ref": "refs/heads/main"}
        evidence = executor._vertical_gate_a_evidence_from_raw(
            gate_b_authorization_raw=(root / authorization_path).read_bytes(),
            gate_b_authorization_path=authorization_path,
            gate_b_receipt_raw=(root / receipt_path).read_bytes(), gate_b_receipt_path=receipt_path,
            expected_source=source, pair=binding.pair_binding,
            expected_package=executor._vertical_package_projection(binding),
        )

        def output(name, mutate):
            document = read(paths[name])
            document["qualification_context"] = "production"
            mutate(document["payload"])
            document["payload_sha256"] = hashlib.sha256(compact(document["payload"])).hexdigest()
            write(paths[name], document)

        def reference(name, role):
            return {"role": role, "path": paths[name],
                    "sha256": hashlib.sha256((root / paths[name]).read_bytes()).hexdigest()}

        output("gate_a_evidence", lambda value: (value.clear(), value.update(evidence)))
        output("readiness", lambda value: value["python"].update(version="3.11.16"))
        output("descriptor", lambda value: value.update(
            ccp={**value["ccp"], "sha256": executor._ACTIVE_CCP_SHA256},
            runtime_readiness=reference("readiness", "readiness"),
            gate_a_evidence=reference("gate_a_evidence", "gate_a_evidence")))
        output("authorization", lambda value: value.update(
            ccp={**value["ccp"], "sha256": executor._ACTIVE_CCP_SHA256},
            runtime_readiness=reference("readiness", "readiness"),
            gate_a_evidence=reference("gate_a_evidence", "gate_a_evidence"),
            descriptor=reference("descriptor", "descriptor")))
        output("mapping", lambda value: value.update(
            ccp={**value["ccp"], "sha256": executor._ACTIVE_CCP_SHA256},
            descriptor=reference("descriptor", "descriptor"),
            authorization=reference("authorization", "authorization")))
        authorization = A0XVerticalMaterialTests()._v4_authorization(
            root, binding, prepared, HEAD, TREE, qualification_context="production")
        execution_relative = executor.vertical_execution_authorization_path(binding)
        write(execution_relative, authorization)

        # The real public-closure parser validates all links; these are synthetic
        # projections, not a claim of attestation, human consent or model truth.
        identity = {"qualified_source": source, "pair_binding": binding.pair_binding.as_mapping(),
                    "authorization_id": authorization["authorization_id"],
                    "attempt_id": authorization["attempt_id"]}
        private = {"p0_dossier_raw": binding.dossier_sha256,
                   "gate_b_authorization_v4": hashlib.sha256((root / paths["authorization"]).read_bytes()).hexdigest(),
                   "gate_b_readiness_v4": hashlib.sha256((root / paths["readiness"]).read_bytes()).hexdigest()}
        roles = {"p0_commitment": compact(read(binding.commitment_path))}
        for role, name in (("p0_protocol", "protocol.json"), ("p0_implementation", "implementation.json"),
                           ("p0_freeze", "freeze.json"), ("p0_slice_manifest", "slice-manifest.json")):
            roles[role] = (root / binding.package_path / name).read_bytes()
        for role, artifact_class, profile in (
            ("public_dossier", "a0x-public-dossier-projection", "a0x-public-dossier-projection-v1"),
            ("execution_spec", "a0x-public-execution-specification", "a0x-public-execution-spec-v1"),
            ("gate_a_evidence", "a0x-public-gate-a-evidence", "a0x-public-gate-a-evidence-v1"),
            ("gate_b_authorization_projection", "a0x-public-gate-b-authorization-projection", "a0x-public-gate-b-authorization-projection-v1"),
            ("gate_b_readiness_projection", "a0x-public-gate-b-readiness-projection", "a0x-public-gate-b-readiness-projection-v1"),
        ):
            value = {"artifact_class": artifact_class, "profile": profile, **identity}
            if role == "public_dossier": value["original_raw_sha256"] = private["p0_dossier_raw"]
            if role == "execution_spec": value["protocol_sha256"] = hashlib.sha256(roles["p0_protocol"]).hexdigest()
            if role.startswith("gate_b_"):
                value["source_raw_sha256"] = private["gate_b_authorization_v4" if role == "gate_b_authorization_projection" else "gate_b_readiness_v4"]
            roles[role] = compact(value)
        for role in ("gate_a_attestation_bundle", "gate_a_trusted_root", "gate_a_transport"):
            roles[role] = b'{"synthetic":true}\n'
        public_base = f"experiments/a0x-six-model/vertical-slices/{HEAD}/a0/smollm2_360m/public-closure/v1"
        for role, relative in PRE_EXECUTION_PUBLIC_ROLE_PATHS.items():
            destination = root / public_base / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(roles[role])
        write(f"{public_base}/{PRE_EXECUTION_EXTENSION_PATH}", {
            "artifact_class": "a0x-public-authorization-extension", "profile": "a0x-public-authorization-extension-v1",
            "schema_version": 1, **identity, "p0_package_commitment_sha256": binding.package_commitment_sha256,
            "bindings": {"public_role_sha256": {role: hashlib.sha256(raw).hexdigest() for role, raw in roles.items()},
                         "private_input_sha256": private},
            "claims": {"document_bindings_consistent": True, "derivation_authenticated": False,
                       "operator_approval_authenticated": False, "authorization_verified": False,
                       "publication_eligible": False},
        })
        repository = Path(__file__).resolve().parents[1]
        for relative in (
            "docs/qualification/a0x-target-free-schema-profile-v1-manifest.json", "data/a0/manifest.json",
            "experiments/a0x-six-model/r1/protocol.json", "experiments/a0x-six-model/r1/implementation.json",
            "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((repository / relative).read_bytes())
        # Fixture inputs come from independent public declarations, not the
        # metadata helper whose production call this test must exercise.
        sizes = {TARGETS[0]: read("data/a0/manifest.json")["files"]["calibration_targets_jsonl"]["size"]}
        declared = read("experiments/a0x-six-model/protected-a0-tree.json")
        sizes[TARGETS[1]] = next(entry["bytes"] for entry in declared["entries"]
                                if entry["entry_kind"] == "sealed_target")
        profile = read("docs/qualification/a0x-target-free-schema-profile-v1-manifest.json")
        other_paths = ("data/a0r1/targets/calibration.jsonl", "data/a0r1/targets/sealed.jsonl",
                       *profile["instance_dispositions"]["excluded_sensitive_role_unverified"])
        for relative in (*sizes, *other_paths):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"x" * sizes.get(relative, 1))
            destination.chmod(0)
        return root, binding, authorization

    def _seed_completed_package(self, root, binding, authorization):
        """Produce valid synthetic material evidence, never model/target truth."""
        import copy
        from tests.test_a0x_vertical_terminal_package import A0XVerticalTerminalPackageTests
        from latent_triz import a0x_vertical_production_adapter as adapter
        from latent_triz import a0x_vertical_terminal_package as package
        from latent_triz.a0x_contract import canonical_commitment, APPROVAL_DOSSIER_PROFILE, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE
        template = A0XVerticalTerminalPackageTests()
        template.setUp()
        self.addCleanup(template.tearDown)
        try:
            old_expectation, terminal = template._production_material_fixture()
        finally:
            # The older fixture doubles graph acquisition. Do not retain that
            # patch: this test validates its own complete real production graph.
            template.doCleanups()
        paths = executor._vertical_gate_b_output_paths(binding)
        capability = adapter.load_vertical_production_capability(root, paths["descriptor"])
        context = capability.context
        pair = binding.pair_binding.as_mapping()
        dossier = json.loads((root / binding.dossier_path).read_bytes())
        chain = {
            "dossier_commitment": canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping(),
            "authorization_commitment": canonical_commitment(authorization, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE).as_mapping(),
        }

        def rebind(value):
            if isinstance(value, dict):
                for key in list(value):
                    if key == "pair_binding": value[key] = pair
                    elif key == "authorization_chain": value[key] = chain
                    else: rebind(value[key])
            elif isinstance(value, list):
                for item in value: rebind(item)

        old_context = old_expectation._production_capability.context
        def material_base(repository, ctx, value):
            return repository / ".a0x-runtime/gate-c/v2" / ctx.source_head / ctx.source_tree / "a0" / value["model_key"] / value["run_id"] / "material"
        old_base = material_base(template.root, old_context, old_context.pair_binding)
        base = material_base(root, context, pair)
        base.mkdir(parents=True, exist_ok=True)
        for role, name in package._MATERIAL_EVIDENCE_MEMBERS.items():
            value = copy.deepcopy(json.loads((old_base / name).read_bytes()))
            rebind(value)
            if role == "target":
                value["activation_receipt_sha256"] = hashlib.sha256((base / package._MATERIAL_EVIDENCE_MEMBERS["activation"]).read_bytes()).hexdigest()
            if role == "analysis_seal":
                value["target_read_receipt_sha256"] = hashlib.sha256((base / package._MATERIAL_EVIDENCE_MEMBERS["target"]).read_bytes()).hexdigest()
                value["statistical_result"] = json.loads((base / package._MATERIAL_EVIDENCE_MEMBERS["statistic"]).read_bytes())
            destination = base / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package._canonical_json(value) + b"\n")
        assets = {}
        asset_base = root / "results/a0x-external-assets" / context.source_head / context.source_tree / "a0" / pair["model_key"] / pair["run_id"]
        for asset in old_expectation.external_assets:
            destination = asset_base / ("dense-output.bin" if asset.role == "dense" else "representation-index.json")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((template.root / asset.path).read_bytes())
            assets[asset.role] = destination
        material_context = package.capture_material_evidence(root, context)
        expected = package.VerticalTerminalExpectation.from_production_capability(
            capability, material_context=material_context, external_assets=assets)
        terminal.update(expected.identity())
        terminal["result_payload"] = {"statistical_result_sha256": hashlib.sha256((base / package._MATERIAL_EVIDENCE_MEMBERS["statistic"]).read_bytes()).hexdigest()}
        destination = root / binding.pair_binding.output_path
        reference = package.build_vertical_terminal_package(
            repository_root=root, destination=destination, expected=expected, terminal_result=terminal)
        return {"package_relative_path": binding.pair_binding.output_path,
                "manifest_raw_sha256": reference.manifest_sha256,
                "root_receipt_raw_sha256": reference.root_receipt_sha256}

    def test_actual_production_preflight_passes_without_claim_window_or_guard(self):
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight
        root, binding, authorization = self._production_fixture()

        class Identity:
            def verify(self, *, role, path, expected_sha256, expected_version=None):
                return executor._ExecutableIdentityEvidence(role, path, expected_sha256, expected_version, synthetic=False)

        class Preflight:
            def produce(self, **_kwargs):
                return _FakeGuardPreflight().produce(ccp_path=root / "bin/commit-ci-preflight", repository_root=root)

        with (
            mock.patch.object(executor, "_reserve_claim", side_effect=AssertionError("claim forbidden")),
            mock.patch.object(executor, "_a0_material_permission_window", side_effect=AssertionError("window forbidden")),
        ):
            result = executor._launch_validated_vertical_v2(
                repository_root=root, package_binding=binding,
                execution_authorization_path=executor.vertical_execution_authorization_path(binding),
                source_state_probe=lambda: (binding.qualified_source_head, binding.qualified_source_tree, True),
                process_executor=mock.Mock(run=mock.Mock(side_effect=AssertionError("guard forbidden"))),
                guard_preflight_producer=Preflight(), executable_identity_verifier=Identity(),
                expected_qualification_context="production", preflight_only=True,
            )
        report = json.loads((root / result["preflight_report_path"]).read_bytes())
        self.assertEqual("preflight_passed", result["status"])
        self.assertEqual("PASS", report["status"])
        self.assertEqual(18, len(report["protected_metadata"]))
        self.assertEqual(2, sum(item["path"] in TARGETS for item in report["protected_metadata"]))
        self.assertEqual(16, report["public_target_size_sources"]["other_protected_path_count"])
        self.assertFalse(report["claim_created"])
        self.assertFalse(report["permission_window_entered"])
        self.assertFalse(report["guard_invoked"])
        self.assertEqual([], list(root.rglob("attempt-claim.json")))
        self.assertFalse((root / binding.pair_binding.output_path).exists())

    def test_production_parent_verifies_real_package_and_completes_without_recovery(self):
        """Catch a late parent admission/package failure after a successful child."""
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight
        root, binding, authorization = self._production_fixture()
        owner = self

        class Identity:
            def verify(self, *, role, path, expected_sha256, expected_version=None):
                return executor._ExecutableIdentityEvidence(role, path, expected_sha256, expected_version, synthetic=False)

        class Preflight:
            def produce(self, **_kwargs):
                return _FakeGuardPreflight().produce(ccp_path=root / "bin/commit-ci-preflight", repository_root=root)

        class SyntheticProcess:
            def run(self, *_args, **_kwargs):
                reference = owner._seed_completed_package(root, binding, authorization)
                terminal = {"artifact_class": "a0x-vertical-material-child-terminal",
                            "terminal_profile": "a0x-vertical-child-terminal-v1", "exit_class": "completed",
                            "qualified_source": authorization["qualified_source"],
                            "pair_binding": binding.pair_binding.as_mapping(),
                            "authorization_id": authorization["authorization_id"], "attempt_id": authorization["attempt_id"],
                            "qualification_context": "production", "reached_frontier": "sealed",
                            "scientific_outcome": "null", "terminal_package": reference}
                raw = executor._canonical_json(terminal) + b"\n"
                return executor.ProcessResult(0, hashlib.sha256(raw).hexdigest(), len(raw),
                                              hashlib.sha256(b"").hexdigest(), 0, stdout_prefix=raw)

        result = executor._launch_validated_vertical_v2(
            repository_root=root, package_binding=binding,
            execution_authorization_path=executor.vertical_execution_authorization_path(binding),
            source_state_probe=lambda: (binding.qualified_source_head, binding.qualified_source_tree, True),
            process_executor=SyntheticProcess(), guard_preflight_producer=Preflight(),
            executable_identity_verifier=Identity(), expected_qualification_context="production",
        )
        observed = json.loads((root / result["terminal_observation_path"]).read_bytes())
        self.assertEqual("completed", result["status"])
        self.assertEqual("null", result["child_terminal_status"])
        self.assertFalse(observed["recovery_required"])
        self.assertFalse(observed["publication_eligible"])
        self.assertTrue(all((root / relative).stat().st_mode & 0o777 == 0 for relative in TARGETS))

    def test_production_positive_fixtures_remain_portable_without_darwin_metadata_apis(self):
        """Hosted Linux doubles only the unavailable native metadata seams."""
        original_acl, original_flags = executor._check_acl_absent, executor._read_target_flags
        absent = object()
        original_event_only = getattr(os, "O_EVTONLY", absent)
        self._portable_metadata = True
        with mock.patch.object(executor, "_check_acl_absent", side_effect=AssertionError("native ACL unavailable")), \
             mock.patch.object(executor, "_read_target_flags", side_effect=AssertionError("native flags unavailable")), \
             mock.patch.object(os, "O_EVTONLY", None, create=True):
            try:
                self.test_actual_production_preflight_passes_without_claim_window_or_guard()
                self.test_production_parent_verifies_real_package_and_completes_without_recovery()
            finally:
                # Unwind fixture patches while their enclosing native-absence
                # patches are still active, not later in unittest teardown.
                self.doCleanups()
        self.doCleanups()
        self.assertIs(original_acl, executor._check_acl_absent)
        self.assertIs(original_flags, executor._read_target_flags)
        if original_event_only is absent:
            self.assertFalse(hasattr(os, "O_EVTONLY"))
        else:
            self.assertEqual(original_event_only, os.O_EVTONLY)


class GateCPreclaimBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _targets(self):
        for relative in TARGETS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic sentinel\n")
            path.chmod(0)
        return {relative: len(b"synthetic sentinel\n") for relative in TARGETS}

    def _admit_synthetic_metadata(self, **kwargs):
        """Portable fixture shim; Darwin-native checks have dedicated tests."""
        with mock.patch.object(executor, "_check_acl_absent"), mock.patch.object(
            executor, "_read_target_flags", return_value=0
        ):
            return executor._admit_a0_material_metadata(self.root, **kwargs)

    def _synthetic_event_only(self):
        event_only = getattr(os, "O_EVTONLY", os.O_NONBLOCK)
        return mock.patch.object(os, "O_EVTONLY", event_only, create=not hasattr(os, "O_EVTONLY"))

    def test_target_metadata_is_admitted_without_open_before_claim(self):
        expected = self._targets()
        validator = self._admit_synthetic_metadata
        target_paths = {(self.root / relative).absolute() for relative in TARGETS}

        def forbid_leaf_open(opener):
            def guarded(path, *args, **kwargs):
                try:
                    candidate = Path(os.fsdecode(path)).absolute()
                except (TypeError, ValueError):
                    candidate = None
                if candidate in target_paths:
                    raise AssertionError(f"protected target content open attempted: {candidate}")
                return opener(path, *args, **kwargs)
            return guarded

        with (
            mock.patch.object(builtins, "open", side_effect=forbid_leaf_open(builtins.open)),
            mock.patch.object(io, "open", side_effect=forbid_leaf_open(io.open)),
            mock.patch.object(os, "open", side_effect=forbid_leaf_open(os.open)),
        ):
            rows = self._admit_synthetic_metadata(expected_sizes=expected)
        self.assertEqual(set(TARGETS), {row["path"] for row in rows})
        self.assertTrue(all(row["mode"] == 0 and row["nlink"] == 1 for row in rows))
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(expected_sizes={**expected, TARGETS[0]: 1})
        (self.root / TARGETS[0]).chmod(0o600)
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(expected_sizes=expected)

    def test_target_metadata_rejects_hardlinks_and_symlink_ancestors(self):
        expected = self._targets()
        validator = self._admit_synthetic_metadata
        path = self.root / TARGETS[0]
        alias = self.root / "synthetic-alias"
        os.link(path, alias)
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(expected_sizes=expected)
        alias.unlink()
        directory = path.parent; renamed = directory.with_name("synthetic-moved")
        directory.rename(renamed); directory.symlink_to(renamed, target_is_directory=True)
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(expected_sizes=expected)
        directory.unlink(); renamed.rename(directory)

    def test_target_metadata_rejects_bool_size_and_checks_other_protected_modes(self):
        expected = self._targets()
        validator = self._admit_synthetic_metadata
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(expected_sizes={**expected, TARGETS[0]: True})
        other = tuple(f"synthetic-protected/{index}.json" for index in range(16))
        for relative in other:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"metadata only")
            path.chmod(0)
        rows = validator(expected_sizes=expected, other_protected_paths=other)
        self.assertEqual(18, len(rows))
        self.assertTrue(all(row["mode"] == 0 and row["nlink"] == 1 for row in rows))
        (self.root / other[0]).chmod(0o600)
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(expected_sizes=expected, other_protected_paths=other)

    @unittest.skipUnless(sys.platform == "darwin", "Darwin xattr fixture required")
    def test_target_metadata_does_not_gate_on_xattrs(self):
        expected = self._targets()
        path = self.root / TARGETS[0]
        path.chmod(0o600)
        try:
            tool = Path("/usr/bin/xattr")
            if not tool.is_file():
                self.skipTest("Darwin xattr utility unavailable")
            completed = subprocess.run(
                (str(tool), "-w", "com.example.synthetic", "synthetic", str(path)),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                check=False, timeout=5,
            )
            if completed.returncode != 0:
                self.skipTest("synthetic Darwin xattr creation unsupported")
        except (OSError, subprocess.TimeoutExpired):
            self.skipTest("synthetic Darwin xattr creation unsupported")
        finally:
            path.chmod(0)
        rows = self._admit_synthetic_metadata(expected_sizes=expected)
        self.assertEqual(2, len(rows))

    @unittest.skipUnless(sys.platform == "darwin", "macOS ACL API required")
    def test_target_metadata_rejects_synthetic_extended_acl(self):
        expected = self._targets()
        path = self.root / TARGETS[0]
        path.chmod(0o600)
        completed = subprocess.run(
            ("chmod", "+a", "everyone deny read", str(path)),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=5,
        )
        if completed.returncode != 0:
            self.skipTest("synthetic ACL creation unsupported")
        path.chmod(0)
        with self.assertRaises(executor.A0XCcpExecutorError):
            executor._admit_a0_material_metadata(self.root, expected_sizes=expected)

    @unittest.skipUnless(sys.platform == "darwin" and hasattr(os, "chflags"), "macOS file flags required")
    def test_target_metadata_rejects_synthetic_immutable_flag(self):
        expected = self._targets()
        path = self.root / TARGETS[0]
        try:
            os.chflags(path, getattr(stat, "UF_IMMUTABLE", 0x2))
            with self.assertRaises(executor.A0XCcpExecutorError):
                executor._admit_a0_material_metadata(self.root, expected_sizes=expected)
        finally:
            try:
                os.chflags(path, 0)
            except OSError:
                pass

    def test_occupied_or_symlinked_output_is_refused_before_claim(self):
        validator = getattr(executor, "_require_vertical_outputs_absent", None)
        self.assertTrue(callable(validator), "preclaim output admission is absent")
        pair = PairBinding.from_mapping(pair_binding(Leg.A0, "smollm2_360m", hidden_width=960))
        authorization = self.root / ".a0x-runtime/gate-c/synthetic/execution-authorization.json"
        authorization.parent.mkdir(parents=True)
        result = self.root / pair.output_path
        validator(self.root, pair=pair, source_head="a" * 40, source_tree="b" * 40,
                  authorization_path=authorization)
        result.mkdir(parents=True)
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(self.root, pair=pair, source_head="a" * 40, source_tree="b" * 40,
                      authorization_path=authorization)

    def test_output_absence_rejects_dangling_symlink(self):
        validator = getattr(executor, "_require_vertical_outputs_absent", None)
        self.assertTrue(callable(validator), "preclaim output admission is absent")
        pair = PairBinding.from_mapping(pair_binding(Leg.A0, "smollm2_360m", hidden_width=960))
        authorization = self.root / ".a0x-runtime/gate-c/synthetic/execution-authorization.json"
        authorization.parent.mkdir(parents=True)
        destination = self.root / pair.output_path
        destination.parent.mkdir(parents=True)
        destination.symlink_to(self.root / "missing-synthetic-destination")
        with self.assertRaises(executor.A0XCcpExecutorError):
            validator(self.root, pair=pair, source_head="a" * 40, source_tree="b" * 40,
                      authorization_path=authorization)

    def test_sigterm_and_sighup_reprotect_only_owned_synthetic_targets(self):
        self._targets()
        script = """
import os,signal,sys
from pathlib import Path
if not hasattr(os,"O_EVTONLY"): os.O_EVTONLY=os.O_NONBLOCK
from latent_triz.a0x_ccp_executor import _a0_material_permission_window,A0XCcpExecutorError
try:
    with _a0_material_permission_window(Path(sys.argv[1])):
        signal.raise_signal(int(sys.argv[2]))
except A0XCcpExecutorError:
    pass
"""
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        for signum in (signal.SIGTERM, signal.SIGHUP):
            result = subprocess.run([sys.executable, "-B", "-c", script, str(self.root), str(int(signum))],
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            modes = [((self.root / path).stat().st_mode & 0o777) for path in TARGETS]
            # Reprotect disposable fixture files before the assertion even in
            # RED; no real repository target is involved in this signal test.
            for path in TARGETS:
                (self.root / path).chmod(0)
            self.assertEqual(0, result.returncode, result.stderr.decode())
            self.assertEqual([0, 0], modes)

    def test_partial_permission_window_failure_reprotects_both_targets(self):
        self._targets()
        original_open = os.open
        event_opens = 0

        def fail_second_event_open(path, flags, *args, **kwargs):
            nonlocal event_opens
            if flags & os.O_EVTONLY:
                event_opens += 1
                if event_opens == 2:
                    raise OSError("synthetic second target open failure")
            return original_open(path, flags, *args, **kwargs)

        with self._synthetic_event_only(), mock.patch.object(executor.os, "open", side_effect=fail_second_event_open):
            with self.assertRaises(executor.A0XCcpExecutorError):
                with executor._a0_material_permission_window(self.root):
                    self.fail("partial window must refuse")
        self.assertEqual([0, 0], [((self.root / path).stat().st_mode & 0o777) for path in TARGETS])

    def test_identity_replacement_does_not_skip_other_target_reprotection(self):
        self._targets()
        replacement = self.root / "replacement"
        with self._synthetic_event_only(), self.assertRaises(executor.A0XCcpExecutorError):
            with executor._a0_material_permission_window(self.root):
                target = self.root / TARGETS[1]
                target.rename(replacement)
                target.write_bytes(b"different synthetic inode")
                target.chmod(0o600)
        self.assertEqual(0, (self.root / TARGETS[0]).stat().st_mode & 0o777)
        self.assertEqual(0o600, (self.root / TARGETS[1]).stat().st_mode & 0o777)

    def test_one_cleanup_error_does_not_skip_next_target_reprotection(self):
        self._targets()
        original_fchmod = os.fchmod
        attempted: list[int] = []

        def fail_first_fchmod(fd, mode):
            attempted.append(fd)
            if len(attempted) == 1:
                raise OSError("synthetic reprotection failure")
            return original_fchmod(fd, mode)

        with self._synthetic_event_only(), mock.patch.object(executor.os, "fchmod", side_effect=fail_first_fchmod):
            with self.assertRaises(executor.A0XCcpExecutorError):
                with executor._a0_material_permission_window(self.root):
                    pass
        self.assertEqual(2, len(attempted))
        self.assertEqual(0, (self.root / TARGETS[1]).stat().st_mode & 0o777)

    def test_permission_window_refuses_non_main_thread_before_chmod(self):
        self._targets()
        failures: list[BaseException] = []

        def enter_window():
            try:
                with executor._a0_material_permission_window(self.root):
                    pass
            except BaseException as error:
                failures.append(error)

        thread = threading.Thread(target=enter_window)
        thread.start(); thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(1, len(failures))
        self.assertIsInstance(failures[0], executor.A0XCcpExecutorError)
        self.assertEqual([0, 0], [((self.root / path).stat().st_mode & 0o777) for path in TARGETS])

    def test_signal_handler_install_failure_precedes_any_permission_change(self):
        self._targets()
        original_signal = signal.signal
        original_handlers = {signum: signal.getsignal(signum) for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)}
        calls = 0

        def fail_second_install(signum, handler):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise ValueError("synthetic signal-handler install failure")
            return original_signal(signum, handler)

        with self._synthetic_event_only(), mock.patch.object(executor.signal, "signal", side_effect=fail_second_install):
            with self.assertRaises(executor.A0XCcpExecutorError):
                with executor._a0_material_permission_window(self.root):
                    self.fail("handler-install failure must refuse before yielding")
        self.assertEqual([0, 0], [((self.root / path).stat().st_mode & 0o777) for path in TARGETS])
        self.assertEqual(original_handlers, {signum: signal.getsignal(signum) for signum in original_handlers})

    def test_signals_ignore_repeats_during_cleanup_and_restore_previous_handlers(self):
        self._targets()
        script = """
import os,signal,sys
from pathlib import Path
if not hasattr(os,"O_EVTONLY"): os.O_EVTONLY=os.O_NONBLOCK
from latent_triz import a0x_ccp_executor as executor
root=Path(sys.argv[1]); signum=int(sys.argv[2])
old=lambda *_: None
signal.signal(signum,old)
real_fchmod=os.fchmod
sent=False
def repeated(fd,mode):
    global sent
    if not sent:
        sent=True
        signal.raise_signal(signum)
    return real_fchmod(fd,mode)
executor.os.fchmod=repeated
try:
    with executor._a0_material_permission_window(root):
        signal.raise_signal(signum)
except executor.A0XCcpExecutorError:
    pass
assert signal.getsignal(signum) is old
assert all((root/path).stat().st_mode & 0o777 == 0 for path in (
    "data/a0/procedural-targets/calibration-targets.jsonl",
    "data/a0/sealed-targets/targets.jsonl"))
"""
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            result = subprocess.run([sys.executable, "-B", "-c", script, str(self.root), str(int(signum))],
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr.decode())

    def test_missing_probe_program_returns_controlled_refusal_not_oserror(self):
        with self.assertRaises(executor.A0XCcpExecutorError):
            executor.SubprocessGuardPreflightProducer._run(("__a0x_nonexistent_synthetic_program__",), self.root)

    def test_production_guard_preflight_rejects_non_active_hash_before_lax_schema_path(self):
        with self.assertRaisesRegex(executor.A0XCcpExecutorError, "active CCP"):
            executor._validate_guard_preflight(
                (), launch=None, pair=None, source_head="a" * 40,
                ccp_identity={"sha256": "0" * 64}, production_context=True,
            )

    def test_resource_telemetry_is_retained_only_as_private_report_data(self):
        fixture = Path(__file__).resolve().parent / "fixtures/a0x/ccp-active-producer/resource-status-admit.json"
        raw = fixture.read_bytes()
        private = executor._private_guard_resource_telemetry((
            executor.GuardPreflightOutput("resource_status", 0, raw),
        ))
        self.assertEqual(json.loads(raw), private)
        self.assertIn("available_percent", private)
        self.assertIn("swap_used_bytes", private)

    def test_reserved_guard_exit_codes_are_not_mislabeled_as_child_exit(self):
        expected = {2: "invalid_arguments", 4: "queue_full", 5: "admission_timeout_or_cancelled",
                    6: "resource_rejected", 70: "cleanup_or_internal", 124: "timeout", 130: "cancelled"}
        for code, label in expected.items():
            with self.subTest(code=code):
                result = executor.ProcessResult(code, "0" * 64, 0, "0" * 64, 0)
                self.assertEqual(label, executor._classify_vertical_outer_exit(result, None))

    def test_child_terminal_cannot_override_outer_timeout_resource_or_cleanup(self):
        classifier = getattr(executor, "_classify_vertical_outer_exit", None)
        self.assertTrue(callable(classifier), "bound vertical exit classifier is absent")
        terminal = {"exit_class": "completed"}
        for code, expected in ((124, "timeout"), (6, "resource_rejected"), (70, "cleanup_or_internal")):
            result = executor.ProcessResult(code, "0" * 64, 0, "0" * 64, 0)
            self.assertEqual(expected, classifier(result, terminal))
        timed_out = executor.ProcessResult(0, "0" * 64, 0, "0" * 64, 0, timed_out=True)
        self.assertEqual("timeout", classifier(timed_out, terminal))
        forced_cleanup = executor.ProcessResult(70, "0" * 64, 0, "0" * 64, 0, timed_out=True)
        self.assertEqual("cleanup_or_internal", classifier(forced_cleanup, terminal))

    def test_bound_child_failure_wire_matches_return_code_before_child_classification(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "a0x_vertical_material_child.py"
        spec = importlib.util.spec_from_file_location("synthetic_child_failure_wire", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        child = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(child)

        source = {"head": "a" * 40, "tree": "b" * 40, "ref": "refs/heads/main"}
        pair = pair_binding(Leg.A0, "smollm2_360m", hidden_width=960)
        authorization_id, attempt_id = "synthetic-auth", "synthetic-attempt"
        graph = {
            "descriptor": {"qualified_source": source, "pair_binding": pair},
            "gate_c_authorization": {
                "authorization_id": authorization_id, "attempt_id": attempt_id,
            },
        }
        classifier = executor._classify_vertical_outer_exit
        parse_failure = executor._parse_vertical_child_failure_terminal
        parsed_failures = {}
        for code, exit_class, expected in (
            (2, "refused", "child_exit_2"),
            (4, "executor_failed", "child_exit_4"),
        ):
            stream = io.StringIO()
            child._emit_terminal(
                stream, exit_class, graph=graph, qualification_context="production",
                reached_frontier="validated_graph",
            )
            raw = stream.getvalue().encode("utf-8")
            terminal = parse_failure(
                raw, expected_source=source, expected_pair=pair,
                expected_authorization_id=authorization_id,
                expected_attempt_id=attempt_id,
                expected_qualification_context="production",
            )
            self.assertIsNotNone(terminal)
            self.assertEqual(exit_class, terminal["exit_class"])
            parsed_failures[exit_class] = terminal
            result = executor.ProcessResult(
                code, hashlib.sha256(raw).hexdigest(), len(raw),
                hashlib.sha256(b"").hexdigest(), 0, stdout_prefix=raw,
            )
            self.assertEqual(expected, classifier(result, terminal))

        mismatched = executor.ProcessResult(2, "0" * 64, 0, "0" * 64, 0)
        self.assertEqual("invalid_arguments", classifier(mismatched, parsed_failures["executor_failed"]))
        for code, expected in (
            (6, "resource_rejected"), (70, "cleanup_or_internal"),
            (124, "timeout"), (130, "cancelled"),
        ):
            result = executor.ProcessResult(code, "0" * 64, 0, "0" * 64, 0)
            self.assertEqual(expected, classifier(result, parsed_failures["executor_failed"]))
        timed_out = executor.ProcessResult(0, "0" * 64, 0, "0" * 64, 0, timed_out=True)
        self.assertEqual("timeout", classifier(timed_out, parsed_failures["executor_failed"]))

        stream = io.StringIO()
        child._emit_terminal(stream, "refused")
        self.assertIsNone(parse_failure(
            stream.getvalue().encode("utf-8"), expected_source=source,
            expected_pair=pair, expected_authorization_id=authorization_id,
            expected_attempt_id=attempt_id,
            expected_qualification_context="production",
        ))

    def test_target_size_sources_are_hash_bound_fixed_and_strict(self):
        tree = {
            "protected_tree_sha256": "b" * 64,
            "entries": [{
                "entry_kind": "sealed_target", "path": TARGETS[1], "bytes": 54_528,
                "sha256": "c" * 64,
            }],
        }
        manifest_sha = "a" * 64
        selection = {
            "source_corpus_manifest_path": "data/a0/manifest.json",
            "source_corpus_manifest_sha256": manifest_sha,
        }
        manifest = {"files": {"calibration_targets_jsonl": {
            "path": "procedural-targets/calibration-targets.jsonl",
            "size": 55_008, "sha256": "d" * 64,
        }}}
        sizes, sources = executor._a0_target_size_bindings(
            protected_tree=tree, selection=selection, manifest=manifest,
            manifest_sha256=manifest_sha,
        )
        self.assertEqual({TARGETS[0]: 55_008, TARGETS[1]: 54_528}, sizes)
        self.assertEqual(manifest_sha, sources["calibration"]["sha256"])
        self.assertEqual("c" * 64, sources["sealed"]["target_sha256"])
        invalid_documents = (
            (tree, selection, {"files": {"calibration_targets_jsonl": {**manifest["files"]["calibration_targets_jsonl"], "size": True}}}, manifest_sha),
            ({**tree, "entries": [*tree["entries"], {"path": TARGETS[0], "entry_kind": "file", "bytes": 1}]}, selection, manifest, manifest_sha),
            (tree, {**selection, "source_corpus_manifest_sha256": "e" * 64}, manifest, manifest_sha),
            (tree, selection, {"files": {"calibration_targets_jsonl": {**manifest["files"]["calibration_targets_jsonl"], "path": "other.jsonl"}}}, manifest_sha),
        )
        for protected_tree, bound_selection, bound_manifest, bound_hash in invalid_documents:
            with self.subTest(bound_selection=bound_selection, bound_manifest=bound_manifest):
                with self.assertRaises(executor.A0XCcpExecutorError):
                    executor._a0_target_size_bindings(
                        protected_tree=protected_tree, selection=bound_selection,
                        manifest=bound_manifest, manifest_sha256=bound_hash,
                    )

    def test_private_preflight_reports_are_repeatable_and_do_not_claim_or_materialize(self):
        payload = {
            "artifact_class": "a0x-vertical-gate-c-preflight-report",
            "status": "PASS", "permission_window_entered": False,
            "claim_created": False, "material_directory_created": False, "guard_invoked": False,
        }
        first = executor._write_vertical_preflight_report(self.root, payload)
        second = executor._write_vertical_preflight_report(self.root, payload)
        self.assertNotEqual(first, second)
        for relative in (first, second):
            path = self.root / relative
            self.assertTrue(path.is_file())
            self.assertEqual(0, stat.S_IMODE(path.stat().st_mode) & 0o077)
            self.assertEqual(0o700, stat.S_IMODE(path.parent.stat().st_mode))
            self.assertEqual(payload, json.loads(path.read_text()))
        self.assertFalse((self.root / ".a0x-runtime/gate-c/synthetic/attempt-claim.json").exists())
        self.assertFalse((self.root / ".a0x-runtime/gate-c/synthetic/material").exists())

    def test_cli_preflight_uses_same_external_bindings_without_production_launch(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "a0x_vertical_material.py"
        spec = importlib.util.spec_from_file_location("synthetic_vertical_material", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for command, selected in (("vertical-v2", "launch"), ("vertical-v2-preflight", "preflight")):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                commitment = root / "commitment.json"
                authorization = root / "authorization.json"
                commitment.write_bytes(b"synthetic commitment")
                authorization.write_bytes(b"synthetic authorization")
                commitment_hash = hashlib.sha256(commitment.read_bytes()).hexdigest()
                authorization_hash = hashlib.sha256(authorization.read_bytes()).hexdigest()
                with (
                    mock.patch.object(module, "ROOT", root),
                    mock.patch.object(module, "vertical_package_binding_from_commitment", return_value=object()) as load,
                    mock.patch.object(module, "launch_vertical_runtime_package", return_value={"status": "launch-called"}) as launch,
                    mock.patch.object(module, "preflight_vertical_runtime_package", return_value={"status": "preflight-called", "preflight_report_path": "private/report.json"}) as preflight,
                    redirect_stdout(io.StringIO()) as output,
                ):
                    code = module.main([
                        command,
                        "--vertical-commitment", "commitment.json",
                        "--vertical-commitment-raw-sha256", commitment_hash,
                        "--execution-authorization", "authorization.json",
                        "--execution-authorization-raw-sha256", authorization_hash,
                    ])
                self.assertEqual(0, code)
                load.assert_called_once_with(root, "commitment.json")
                chosen = launch if selected == "launch" else preflight
                other = preflight if selected == "launch" else launch
                chosen.assert_called_once()
                other.assert_not_called()
                self.assertIn("report.json" if selected == "preflight" else "launch-called", output.getvalue())

    @unittest.skipUnless(hasattr(os, "killpg") and hasattr(signal, "SIGUSR1"), "POSIX process-group supervision required")
    def test_guard_timeout_escalation_fails_closed_without_signaling_unrelated_group(self):
        unrelated = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            code = (
                "import signal,time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(20)"
            )
            with (
                mock.patch.object(executor, "_SUPERVISION_TIMEOUT_SECONDS", 0.1),
                mock.patch.object(executor, "CLEANUP_MARGIN_SECONDS", 0.15),
            ):
                result = executor._SubprocessExecutor().run(
                    [sys.executable, "-c", code], cwd=self.root,
                    env={"PATH": "/usr/bin:/bin"}, timeout_seconds=0.1,
                    capture_limit_bytes=128,
                )
            self.assertEqual(70, result.returncode)
            self.assertTrue(result.timed_out)
            self.assertIsNone(unrelated.poll(), "timeout cleanup signaled a process outside the owned session")
        finally:
            if unrelated.poll() is None:
                unrelated.terminate()
                unrelated.wait(timeout=3)

    @unittest.skipUnless(hasattr(os, "killpg"), "POSIX process-group supervision required")
    def test_guard_graceful_timeout_keeps_timeout_classification(self):
        marker = self.root / "timeout-cleaned-by-term"
        code = (
            "import signal,sys,time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM, lambda *_: (Path(sys.argv[1]).write_text('term'), sys.exit(0))); "
            "time.sleep(20)"
        )
        with (
            mock.patch.object(executor, "_SUPERVISION_TIMEOUT_SECONDS", 0.1),
            mock.patch.object(executor, "CLEANUP_MARGIN_SECONDS", 0.5),
        ):
            result = executor._SubprocessExecutor().run(
                [sys.executable, "-c", code, str(marker)], cwd=self.root,
                env={"PATH": "/usr/bin:/bin"}, timeout_seconds=0.1,
                capture_limit_bytes=128,
            )
        self.assertEqual(124, result.returncode)
        self.assertTrue(result.timed_out)
        self.assertEqual("term", marker.read_text())

    @unittest.skipUnless(hasattr(os, "killpg") and hasattr(signal, "SIGTERM"), "POSIX signal supervision required")
    def test_guard_cancellation_cooperatively_terminates_dedicated_outer_group(self):
        marker = self.root / "cancelled-by-term"
        code = (
            "import signal,sys,time; from pathlib import Path; "
            "signal.signal(signal.SIGTERM, lambda *_: (Path(sys.argv[1]).write_text('term'), sys.exit(0))); "
            "time.sleep(20)"
        )
        timer = threading.Timer(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM))
        timer.daemon = True
        timer.start()
        with (
            mock.patch.object(executor, "_SUPERVISION_TIMEOUT_SECONDS", 2.0),
            mock.patch.object(executor, "CLEANUP_MARGIN_SECONDS", 0.5),
        ):
            result = executor._SubprocessExecutor().run(
                [sys.executable, "-c", code, str(marker)], cwd=self.root,
                env={"PATH": "/usr/bin:/bin"}, timeout_seconds=2.0,
                capture_limit_bytes=128,
            )
        timer.join(timeout=2)
        self.assertEqual(130, result.returncode)
        self.assertFalse(result.timed_out)
        self.assertEqual("term", marker.read_text())

    def _run_with_synthetic_signal_lifecycle(
        self, *, signal_stage=None, timeout_ticks=False, fail_install_signum=None,
        non_main_thread=False, repeat_during_cleanup=False,
    ):
        events = []
        signals = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
        previous_handlers = {signum: object() for signum in signals}
        active_handlers = dict(previous_handlers)
        signal_calls = {signum: 0 for signum in signals}
        clock = [0.0]
        worker_thread_type = threading.Thread
        cancel_handler = None

        class SyntheticProcess:
            pid = 424242

            def __init__(self):
                self.stdout = io.BytesIO()
                self.stderr = io.BytesIO()
                self.returncode = None
                self.wait_count = 0

            def wait(self, timeout=None):
                self.wait_count += 1
                events.append(("wait", timeout))
                if timeout_ticks:
                    clock[0] += timeout
                    if self.wait_count == 3 and signal_stage == "deadline_tick":
                        active_handlers[signal.SIGTERM](int(signal.SIGTERM), None)
                    raise subprocess.TimeoutExpired("synthetic-guard", timeout)
                if signal_stage == "wait":
                    active_handlers[signal.SIGTERM](int(signal.SIGTERM), None)
                self.returncode = 0
                return self.returncode

            def poll(self):
                return self.returncode

        process = SyntheticProcess()
        threads = []

        class SyntheticThread:
            def __init__(self, *_args, **_kwargs):
                self.index = len(threads)
                self.ident = None
                self._alive = False
                threads.append(self)

            def start(self):
                events.append(("start", self.index))
                self.ident = 100 + self.index
                self._alive = True
                if signal_stage == "post_popen" and self.index == 0:
                    active_handlers[signal.SIGTERM](int(signal.SIGTERM), None)

            def join(self, timeout=None):
                events.append(("join", self.index, timeout))
                if signal_stage == "drain" and self.index == 0:
                    active_handlers[signal.SIGTERM](int(signal.SIGTERM), None)
                    active_handlers[signal.SIGHUP](int(signal.SIGHUP), None)
                    active_handlers[signal.SIGINT](int(signal.SIGINT), None)
                self._alive = False

            def is_alive(self):
                return self._alive

        def fake_signal(signum, handler):
            nonlocal cancel_handler
            signal_calls[signum] += 1
            if signal_calls[signum] == 1:
                events.append(("install", signum))
                if signum == fail_install_signum:
                    raise OSError("synthetic signal handler install failure")
                active_handlers[signum] = handler
                cancel_handler = handler
                if signal_stage == "before_spawn" and signum == signals[0]:
                    handler(int(signum), None)
                return previous_handlers[signum]
            events.append(("restore", signum))
            active_handlers[signum] = handler
            return cancel_handler

        def fake_getsignal(signum):
            return previous_handlers[signum]

        def terminate(_process, *, grace_seconds):
            # Deliver at the helper boundary: a signal cannot throw past the
            # cleanup entry or restart the fixed grace interval.
            if signal_stage == "cleanup_entry":
                for signum in signals:
                    active_handlers[signum](int(signum), None)
                events.append(("cleanup_handler_returned",))
            if repeat_during_cleanup:
                for signum in signals:
                    active_handlers[signum](int(signum), None)
            events.append(("terminate", grace_seconds))
            if _process.returncode is None:
                _process.returncode = -int(signal.SIGTERM)
            return True

        class SyntheticPermissionWindow:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                events.append(("window_exit",))

        result = None
        failure = None
        supervision_timeout = 0.25 if timeout_ticks else 1.0
        with (
            mock.patch.object(executor, "_SUPERVISION_TIMEOUT_SECONDS", supervision_timeout),
            mock.patch.object(executor.subprocess, "Popen", side_effect=lambda *_a, **_k: (events.append(("popen",)) or process)),
            mock.patch.object(executor.threading, "Thread", side_effect=lambda *_a, **_k: SyntheticThread()),
            mock.patch.object(executor.signal, "getsignal", side_effect=fake_getsignal),
            mock.patch.object(executor.signal, "signal", side_effect=fake_signal),
            mock.patch.object(executor.time, "monotonic", side_effect=lambda: clock[0]),
            mock.patch.object(executor, "_owned_process_group_exists", return_value=False),
            mock.patch.object(executor, "_terminate_owned_process_group", side_effect=terminate),
        ):
            try:
                if non_main_thread:
                    outcome = []

                    def invoke_from_worker():
                        try:
                            with SyntheticPermissionWindow():
                                outcome.append(executor._SubprocessExecutor().run(
                                    ["synthetic-guard"], cwd=self.root, env={}, timeout_seconds=supervision_timeout,
                                    capture_limit_bytes=32,
                                ))
                        except BaseException as error:
                            outcome.append(error)

                    worker = worker_thread_type(target=invoke_from_worker)
                    worker.start()
                    worker.join()
                    if outcome and isinstance(outcome[0], BaseException):
                        failure = outcome[0]
                    elif outcome:
                        result = outcome[0]
                else:
                    with SyntheticPermissionWindow():
                        result = executor._SubprocessExecutor().run(
                            ["synthetic-guard"], cwd=self.root, env={}, timeout_seconds=supervision_timeout,
                            capture_limit_bytes=32,
                        )
            except BaseException as error:
                events.append(("failure_caught", type(error).__name__))
                failure = error
        return result, failure, events, process, active_handlers, previous_handlers, threads

    def test_signal_before_spawn_restores_handlers_and_propagates_without_process_result(self):
        result, failure, events, _process, active, previous, _threads = self._run_with_synthetic_signal_lifecycle(
            signal_stage="before_spawn",
        )
        self.assertIsNone(result)
        self.assertIsInstance(failure, executor._GateCSignalInterrupt)
        self.assertNotIn(("popen",), events)
        self.assertTrue(all(active[s] is previous[s] for s in previous))
        last_restore = max(i for i, event in enumerate(events) if event[0] == "restore")
        self.assertLess(last_restore, events.index(("failure_caught", "_GateCSignalInterrupt")))

    def test_partial_signal_handler_install_failure_restores_prior_handlers_before_popen(self):
        result, failure, events, _process, active, previous, _threads = self._run_with_synthetic_signal_lifecycle(
            fail_install_signum=signal.SIGHUP,
        )
        self.assertIsNone(result)
        self.assertIsInstance(failure, executor.A0XCcpExecutorError)
        self.assertNotIn(("popen",), events)
        self.assertTrue(all(active[s] is previous[s] for s in previous))

    def test_post_popen_signal_before_wait_terminates_owned_guard_before_window_exit(self):
        result, failure, events, process, active, previous, _threads = self._run_with_synthetic_signal_lifecycle(
            signal_stage="post_popen",
        )
        self.assertIsNone(failure, repr(failure))
        self.assertNotIn("wait", [event[0] for event in events])
        self.assertEqual(1, sum(event[0] == "terminate" for event in events))
        self.assertLess(next(i for i, event in enumerate(events) if event[0] == "terminate"), next(i for i, event in enumerate(events) if event[0] == "window_exit"))
        self.assertEqual(130, result.returncode)
        self.assertEqual("cancelled", executor._classify_vertical_outer_exit(result, None))
        self.assertEqual(-int(signal.SIGTERM), process.returncode)
        self.assertTrue(all(active[s] is previous[s] for s in previous))

    def test_wait_signal_is_cooperative_and_does_not_escape_cleanup(self):
        result, failure, events, process, active, previous, _threads = self._run_with_synthetic_signal_lifecycle(
            signal_stage="wait",
        )
        self.assertIsNone(failure, repr(failure))
        self.assertEqual(130, result.returncode)
        self.assertEqual(0, process.returncode)
        self.assertTrue(any(event[0] == "terminate" for event in events))
        self.assertLess(next(i for i, event in enumerate(events) if event[0] == "terminate"), next(i for i, event in enumerate(events) if event[0] == "window_exit"))
        self.assertTrue(all(active[s] is previous[s] for s in previous))

    def test_repeated_signals_during_drain_reprotect_before_window_exit(self):
        result, failure, events, process, active, previous, _threads = self._run_with_synthetic_signal_lifecycle(
            signal_stage="drain",
        )
        self.assertIsNone(failure, repr(failure))
        self.assertEqual(130, result.returncode)
        self.assertEqual(0, process.returncode)
        self.assertEqual(1, sum(event[0] == "terminate" for event in events))
        self.assertLess(next(i for i, event in enumerate(events) if event[0] == "terminate"), next(i for i, event in enumerate(events) if event[0] == "window_exit"))
        last_join = max(i for i, event in enumerate(events) if event[0] == "join")
        first_restore = min(i for i, event in enumerate(events) if event[0] == "restore")
        self.assertLess(last_join, first_restore)
        self.assertTrue(all(active[s] is previous[s] for s in previous))

    def test_absolute_deadline_uses_bounded_ticks_and_timeout_precedes_cleanup_signal(self):
        result, failure, events, _process, active, previous, _threads = self._run_with_synthetic_signal_lifecycle(
            timeout_ticks=True, signal_stage="cleanup_entry", repeat_during_cleanup=True,
        )
        self.assertIsNone(failure, repr(failure))
        self.assertEqual(124, result.returncode)
        waits = [event[1] for event in events if event[0] == "wait"]
        self.assertEqual([0.1, 0.1, 0.04999999999999999], waits)
        self.assertTrue(result.timed_out)
        terminations = [event for event in events if event[0] == "terminate"]
        self.assertEqual([("terminate", executor.CLEANUP_MARGIN_SECONDS)], terminations)
        self.assertIn(("cleanup_handler_returned",), events)
        self.assertTrue(all(active[s] is previous[s] for s in previous))

    def test_non_main_thread_refuses_before_handler_install_or_popen(self):
        result, failure, events, _process, _active, _previous, _threads = self._run_with_synthetic_signal_lifecycle(
            non_main_thread=True,
        )
        self.assertIsNone(result)
        self.assertIsInstance(failure, executor.A0XCcpExecutorError)
        self.assertNotIn(("popen",), events)
        self.assertFalse(any(event[0] == "install" for event in events))


if __name__ == "__main__":
    unittest.main()
