from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import latent_triz.a0x_vertical_terminal_package as terminal_package

from latent_triz.a0x_vertical_production_adapter import bind_validated_vertical_graph
from latent_triz.a0x_public_closure import TerminalClosureStatus
from latent_triz.a0x_vertical_terminal_package import (
    A0XVerticalTerminalPackageError,
    PublicVerticalPackageIntegrity,
    VerticalTerminalExpectation,
    build_vertical_terminal_package,
    verify_vertical_terminal_package,
    verify_public_vertical_terminal_package,
    _cleanup_owned_stage,
    _open_directory_chain,
)
from tests.test_a0x_vertical_production_adapter import _graph


class A0XVerticalTerminalPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        # The repository's path verifier deliberately rejects symlink
        # components. macOS exposes the default temp root through `/var`, a
        # symlink to `/private/var`; use its resolved physical parent so the
        # fixture tests the package contract rather than that OS alias.
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.root = Path(self.temp.name).resolve()
        self.expected, self.result = self._fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _fixture(self, *, qualification_context: str = "synthetic-target-free", with_assets: bool = False):
        source = self.root / "schemas/a0x-execution-authorization-v4.schema.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        schema_source = Path(__file__).resolve().parents[1] / "schemas/a0x-execution-authorization-v4.schema.json"
        raw = schema_source.read_bytes()
        source.write_bytes(raw)
        info = source.stat()
        private = self.root / ".a0x-runtime/gate-b/v2/a/b/a0/smollm2_360m/run/runtime-mapping.json"
        private.parent.mkdir(parents=True, exist_ok=True)
        private_raw = b'{"private_runtime_mapping":"synthetic only"}\n'
        private.write_bytes(private_raw)
        private_info = private.stat()
        graph = _graph(qualification_context=qualification_context)
        if qualification_context == "engineering_rehearsal":
            from tests.a0x_test_support import pair_binding
            from latent_triz.a0x_contract import Leg
            binding = pair_binding(Leg.A0, "smollm2_360m", hidden_width=960)
            binding.update(model_id="HuggingFaceTB/SmolLM2-360M",revision="f8027fd0eaeea54caa13c31d31b9fdc459c38b49")
            for role in ("descriptor", "readiness", "execution_inlet", "gate_c_authorization", "gate_a_evidence"):
                graph[role]["pair_binding"] = binding
        graph["trust_file_identities"] = {
            source.relative_to(self.root).as_posix(): {
                "device": info.st_dev,
                "inode": info.st_ino,
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            private.relative_to(self.root).as_posix(): {
                "device": private_info.st_dev,
                "inode": private_info.st_ino,
                "size": len(private_raw),
                "sha256": hashlib.sha256(private_raw).hexdigest(),
            },
        }
        asset_paths = None
        if with_assets:
            pair_value = graph["descriptor"]["pair_binding"]
            asset_base = (
                self.root / "results/a0x-external-assets" / ("a" * 40) / ("b" * 40)
                / pair_value["leg"] / pair_value["model_key"] / pair_value["run_id"]
            )
            asset_paths = {
                "dense": asset_base / "dense-output.bin",
                "index": asset_base / "representation-index.json",
            }
            for role, asset_path in asset_paths.items():
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                asset_path.write_bytes((role + " synthetic asset\n").encode())
        context = bind_validated_vertical_graph(graph, qualification_context=qualification_context)
        self._last_fixture_context = context
        expected = VerticalTerminalExpectation.from_context(
            context,
            repository_root=self.root if asset_paths else None,
            external_assets=asset_paths,
        )
        result = {
            "artifact_class": "a0x-vertical-terminal-result",
            "terminal_profile": "a0x-vertical-terminal-result-v1",
            "qualified_source": {
                "head": context.source_head,
                "tree": context.source_tree,
                "ref": "refs/heads/main",
            },
            "pair_binding": context.public_identity()["pair_binding"],
            "vertical_package_digests": context.public_identity()["vertical_package_digests"],
            "qualification_context": qualification_context,
            "authorization_id": context.authorization_id,
            "attempt_id": context.attempt_id,
            "reached_frontier": "validated_graph",
            "scientific_outcome": "failed",
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
            "result_payload": {"diagnostic_code": "SYNTHETIC_FIXTURE"},
        }
        return expected, result

    def test_synthetic_terminal_package_builds_and_independently_verifies(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )

        verified = verify_vertical_terminal_package(
            package_root=destination,
            repository_root=self.root,
            expected=self.expected,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertEqual("synthetic-target-free", verified.qualification_context)
        self.assertFalse(verified.publication_eligible)
        self.assertEqual("failed", verified.scientific_outcome)
        self.assertEqual(6, len(list(destination.iterdir())))

    def _engineering_fixture(self):
        self.root = self.root / ".a0x-runtime/rehearsal/1/synthetic-repository"
        self.root.mkdir(parents=True)
        expected, result = self._fixture(qualification_context="engineering_rehearsal", with_assets=True)
        from tests.a0x_test_support import artifact, rich_statistical_result
        from scripts.a0x_rehearsal import _calibration_inputs
        from latent_triz.a0_calibration import run_production_shortcut_calibration
        from latent_triz.a0_shortcuts import production_mechanics_recipe
        from latent_triz.a0x_execution import seal_terminal_attempt, AttemptState
        context = self._last_fixture_context
        pair = context.public_identity()["pair_binding"]
        chain={"dossier_commitment":{"profile":"a0x-approval-dossier-json-v2","commitment_sha256":"c"*64},
            "authorization_commitment":{"profile":"a0x-execution-authorization-json-v4","commitment_sha256":"d"*64}}
        base=self.root/".a0x-runtime/engineering/material"
        base.mkdir(parents=True)
        def write(name,value):
            path=base/name; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(terminal_package._canonical_json(value)+b"\n")
            return path
        def rebind(value):
            if isinstance(value,dict):
                for key in list(value):
                    if key=="pair_binding": value[key]=pair
                    elif key=="authorization_chain": value[key]=chain
                    else: rebind(value[key])
            elif isinstance(value,list):
                for item in value: rebind(item)
        activation=artifact("a0x-activation-receipt.schema.json"); rebind(activation)
        occupancy=artifact("a0x-activation-stage-occupancy-receipt.schema.json"); rebind(occupancy)
        occupancy.update(actual_total_bytes=sum(item.size for item in expected.external_assets),
            included_paths=["activations.safetensors","representations-index.jsonl"])
        activation.update(activation_status="completed",leg="a0",created_at="2026-10-12T00:00:00Z",activation_target_content_reads=0,
            literal_tuple_indices=[0,2,4,6],planned_dense_bound=pair["dense_bound"],
            dense={"format":"safetensors","path":"activations.safetensors"},index={"path":"representations-index.jsonl"},
            activation_stage_occupancy=occupancy,activation_stage_occupancy_sha256=hashlib.sha256(terminal_package._canonical_json(occupancy)).hexdigest(),
            occupancy_checkpoints=[{"phase":phase,"planned_dense_bound":pair["dense_bound"],"current_occupancy":occupancy,
                "projected_included_paths":occupancy["included_paths"],"projected_total_bytes":occupancy["actual_total_bytes"],
                "cap_bytes":pair["dense_bound"]["cap_bytes"]} for phase in ("pre_dense_write","pre_index_write","pre_final_rename")])
        for asset in expected.external_assets:
            activation[asset.role].update(bytes=asset.size,sha256=asset.sha256)
        activation["record_count"]=pair["dense_bound"]["vector_count"]
        activation["final_block_tuple_index"]=32
        activation_path=write("activation/activation-receipt.json",activation)
        target=artifact("a0x-target-read-receipt.schema.json"); rebind(target)
        target.update(status="pass",content_reads=1,observed_sha256="a"*64)
        target["activation_receipt_sha256"]=hashlib.sha256(activation_path.read_bytes()).hexdigest()
        for asset in expected.external_assets: target[asset.role+"_sha256"]=asset.sha256
        target_path=write("target-read-receipt.json",target)
        statistic=rich_statistical_result(pair,status="null",authorization_chain=chain)
        statistic["descriptive_final_block"]["tuple_index"]=32
        statistic_path=write("statistical-result.json",statistic)
        seal_terminal_attempt(state=AttemptState.ANALYSIS,status="null",target_receipt_path=target_path,
            statistical_result=statistic,pair_binding=pair,authorization_chain=chain,terminal_path=base/"analysis-terminal-result.json")
        protocol,cases,targets=_calibration_inputs(self.root,Path(__file__).resolve().parents[1])
        write("calibration-result.json",run_production_shortcut_calibration(protocol,cases,targets,production_mechanics_recipe()))
        context=terminal_package.capture_material_evidence(self.root,context)
        self._last_fixture_context=context
        expected=VerticalTerminalExpectation.from_context(context,repository_root=self.root,
            external_assets={item.role:self.root/item.path for item in expected.external_assets})
        result.update(reached_frontier="sealed", scientific_outcome="null",
                      result_payload={"statistical_result_sha256": hashlib.sha256(statistic_path.read_bytes()).hexdigest()})
        return expected, result

    def test_scientific_terminal_rejects_missing_observed_statistics(self):
        expected,result=self._engineering_fixture()
        expected=replace(expected,trust_files=tuple(item for item in expected.trust_files if not item.path.endswith("statistical-result.json")))
        with self.assertRaises(A0XVerticalTerminalPackageError):
            terminal_package._validate_terminal_result(result,expected)

    def _production_material_fixture(self):
        """Real production verifier, public declarations, synthetic receipts only.

        Only the expensive source/runtime graph-admission loader is doubled.
        Capability membership, selection receiver, material verification,
        package construction and terminal verification remain real. This
        disposable fixture is not evidence of model execution or target truth.
        """
        import copy
        from latent_triz import a0x_vertical_production_adapter as adapter
        from latent_triz.a0x_contract import (
            APPROVAL_DOSSIER_PROFILE, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE,
            PairBinding, canonical_commitment,
        )
        from latent_triz.a0x_execution import (
            LegFreezeBinding, OneShotTargetReader, _load_a0_public_selection,
        )
        from tests.test_a0x_vertical_material import A0XVerticalMaterialTests

        engineering, result = self._engineering_fixture()
        original = self._last_fixture_context
        source = Path(__file__).resolve().parents[1]
        public_paths = (
            "experiments/a0x-six-model/a0-selection-manifest.json",
            "experiments/a0x-six-model/protected-a0-tree.json",
            "experiments/a0x-six-model/freeze/a0-freeze.json",
            "experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json",
            "data/a0/manifest.json",
            "experiments/a0x-six-model/a0/protocol.json",
        )
        for relative in public_paths:
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((source / relative).read_bytes())

        freeze_raw = (self.root / public_paths[2]).read_bytes()
        freeze_value = json.loads(freeze_raw)
        pair = original.public_identity()["pair_binding"]
        pair["leg_freeze_sha256"] = hashlib.sha256(freeze_raw).hexdigest()
        selection = _load_a0_public_selection(
            self.root, LegFreezeBinding(
                leg=PairBinding.from_mapping(pair).leg,
                leg_freeze_sha256=pair["leg_freeze_sha256"],
                selection_corpus_sha256=freeze_value["identity"]["selection_corpus_sha256"],
                protocol_id=freeze_value["identity"]["protocol_id"],
                protocol_sha256=freeze_value["protocol_sha256"],
                implementation_sha256=freeze_value["implementation_sha256"],
                protected_tree_sha256=freeze_value["identity"]["protected_tree_sha256"],
                source_base_commit=freeze_value["identity"]["source_base_commit"],
            ),
        )
        # Exercise the actual receiver against synthetic rows in the temporary
        # root. Its selection hash is not calculated by the test expectation.
        sentinel = self.root / "synthetic-receiver-input.jsonl"
        sentinel_raw = b"".join((json.dumps({"case_id": name}) + "\n").encode()
                                for name in selection.expected_case_ids)
        sentinel.write_bytes(sentinel_raw)
        receiver = OneShotTargetReader(
            path=sentinel, expected_sha256=hashlib.sha256(sentinel_raw).hexdigest(),
            selection=selection, activation_receipt_sha256="a" * 64,
            dense_sha256="b" * 64, index_sha256="c" * 64,
            authorization_chain=json.loads((self.root / ".a0x-runtime/engineering/material/target-read-receipt.json").read_bytes())["authorization_chain"],
            pair_binding=pair, receipt_path=self.root / "synthetic-receiver-receipt.json",
        )
        _rows, receiver_receipt = receiver.read_jsonl_once()

        helper = A0XVerticalMaterialTests()
        try:
            other_root, binding, prepared, head, tree = helper._prepared_v2_graph()
            authorization = helper._v4_authorization(other_root, binding, prepared, head, tree,
                                                     qualification_context="production")
        finally:
            helper.doCleanups()
        authorization["pair_binding"] = pair
        dossier = json.loads((self.root / public_paths[3]).read_bytes())
        chain = {
            "dossier_commitment": canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping(),
            "authorization_commitment": canonical_commitment(authorization, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE).as_mapping(),
        }
        material_base = self.root / ".a0x-runtime/gate-c/v2" / original.source_head / original.source_tree / "a0" / pair["model_key"] / pair["run_id"] / "material"
        material_base.mkdir(parents=True)
        retained = {}
        for role, name in terminal_package._MATERIAL_EVIDENCE_MEMBERS.items():
            value = json.loads((self.root / ".a0x-runtime/engineering/material" / name).read_bytes())
            if "pair_binding" in value:
                value["pair_binding"] = pair
            if "authorization_chain" in value:
                value["authorization_chain"] = chain
            retained[role] = value
        retained["target"]["selection_corpus_sha256"] = receiver_receipt.selection_corpus_sha256
        declared = json.loads((self.root / public_paths[1]).read_bytes())
        retained["target"]["observed_sha256"] = next(item["sha256"] for item in declared["entries"]
                                                       if item["entry_kind"] == "sealed_target")
        retained["statistic"]["authorization_chain"] = chain
        retained["analysis_seal"]["statistical_result"] = retained["statistic"]
        selected = json.loads((self.root / public_paths[0]).read_bytes())
        corpus = json.loads((self.root / "data/a0/manifest.json").read_bytes())
        protocol = json.loads((self.root / "experiments/a0x-six-model/a0/protocol.json").read_bytes())
        # Simulated observations use the public input commitments, never the
        # protected inputs. This receipt remains test-only synthetic evidence.
        retained["calibration"]["input_hashes"] = {
            "protocol": protocol["source_protocol_raw_sha256"],
            "cases": selected["source_cases_sha256"],
            "targets": corpus["files"]["calibration_targets_jsonl"]["sha256"],
        }
        mechanical = retained["calibration"]["mechanical_evidence_contract"]
        mechanical.update(python_version="3.11.16", unicode_version="14.0.0")
        retained["calibration"]["mechanical_evidence_sha256"] = hashlib.sha256(
            terminal_package._canonical_json(mechanical)).hexdigest()
        for role in ("calibration", "activation", "target", "statistic", "analysis_seal"):
            if role == "target":
                retained[role]["activation_receipt_sha256"] = hashlib.sha256((material_base / terminal_package._MATERIAL_EVIDENCE_MEMBERS["activation"]).read_bytes()).hexdigest()
            if role == "analysis_seal":
                retained[role]["target_read_receipt_sha256"] = hashlib.sha256((material_base / terminal_package._MATERIAL_EVIDENCE_MEMBERS["target"]).read_bytes()).hexdigest()
            destination = material_base / terminal_package._MATERIAL_EVIDENCE_MEMBERS[role]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(terminal_package._canonical_json(retained[role]) + b"\n")

        def rebind(document):
            value = copy.deepcopy(terminal_package._plain_json(document))
            value["pair_binding"] = pair
            return value
        trust = {path: identity for path, identity in original.trust_file_identities.items()
                 if not path.startswith(".a0x-runtime/engineering/material/")}
        for relative in public_paths:
            raw = (self.root / relative).read_bytes(); info = (self.root / relative).stat()
            trust[relative] = {"device": info.st_dev, "inode": info.st_ino,
                               "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        context = replace(original, pair_binding=terminal_package._freeze_json(pair), qualification_context="production",
                          gate_c_authorization=terminal_package._freeze_json(authorization),
                          descriptor=terminal_package._freeze_json(rebind(original.descriptor)),
                          readiness=terminal_package._freeze_json({**rebind(original.readiness), "python": {"version": "3.11.16"}}),
                          gate_a_evidence=terminal_package._freeze_json(rebind(original.gate_a_evidence)),
                          execution_inlet=terminal_package._freeze_json(rebind(original.execution_inlet)),
                          trust_file_identities=terminal_package._freeze_json(trust))
        capability = adapter._ValidatedProductionCapability(
            self.root, "synthetic-admitted-descriptor.json", context,
            terminal_package._freeze_json({"approval-dossier.json": dossier, "protocol.json": protocol}), adapter._PRODUCTION_CAPABILITY,
        )
        # Graph acquisition is an external prerequisite of this verifier test;
        # every downstream production validation runs without replacement.
        admission = patch.object(adapter, "load_vertical_production_capability", return_value=capability)
        admission.start(); self.addCleanup(admission.stop)
        material_context = terminal_package.capture_material_evidence(self.root, context)
        expected = VerticalTerminalExpectation.from_production_capability(
            capability, material_context=material_context,
            external_assets={item.role: self.root / item.path for item in engineering.external_assets},
        )
        result.update(expected.identity())
        result["result_payload"] = {"statistical_result_sha256": hashlib.sha256(
            (material_base / terminal_package._MATERIAL_EVIDENCE_MEMBERS["statistic"]).read_bytes()).hexdigest()}
        return expected, result

    def test_production_selection_receipt_uses_frozen_selection_hash_not_corpus_hash(self):
        expected, result = self._production_material_fixture()
        try:
            terminal_package._verify_material_evidence(self.root, expected, result)
        except A0XVerticalTerminalPackageError as error:
            self.fail(f"valid receiver selection binding was refused: {error}")
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(repository_root=self.root, destination=destination,
                                                    expected=expected, terminal_result=result)
        verified = verify_vertical_terminal_package(repository_root=self.root, package_root=destination,
            expected=expected, expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256)
        self.assertEqual("production", verified.qualification_context)
        self.assertEqual("null", verified.scientific_outcome)
        self.assertFalse(verified.publication_eligible)

    def test_private_execution_evidence_rejects_self_consistently_rehashed_wrong_count(self):
        expected,result=self._engineering_fixture()
        terminal_package._verify_material_evidence(self.root,expected,result)
        paths=terminal_package._material_evidence_paths(expected)
        target=json.loads((self.root/paths["target"]).read_bytes()); target["content_reads"]=2
        raw=terminal_package._canonical_json(target)+b"\n"; (self.root/paths["target"]).write_bytes(raw)
        seal=json.loads((self.root/paths["analysis_seal"]).read_bytes()); seal["analysis_target_content_reads"]=2
        seal["target_read_receipt_sha256"]=hashlib.sha256(raw).hexdigest()
        (self.root/paths["analysis_seal"]).write_bytes(terminal_package._canonical_json(seal)+b"\n")
        context=terminal_package.capture_material_evidence(self.root,self._last_fixture_context)
        changed=VerticalTerminalExpectation.from_context(context,repository_root=self.root,
            external_assets={item.role:self.root/item.path for item in expected.external_assets})
        with self.assertRaises(A0XVerticalTerminalPackageError):
            terminal_package._verify_material_evidence(self.root,changed,result)

    def test_private_execution_evidence_rejects_rehashed_contradictory_outcome_and_missing_receipt(self):
        expected,result=self._engineering_fixture()
        paths=terminal_package._material_evidence_paths(expected)
        statistic=json.loads((self.root/paths["statistic"]).read_bytes()); statistic["status"]="positive"
        raw=terminal_package._canonical_json(statistic)+b"\n"; (self.root/paths["statistic"]).write_bytes(raw)
        seal=json.loads((self.root/paths["analysis_seal"]).read_bytes()); seal.update(status="positive",statistical_result=statistic)
        (self.root/paths["analysis_seal"]).write_bytes(terminal_package._canonical_json(seal)+b"\n")
        context=terminal_package.capture_material_evidence(self.root,self._last_fixture_context)
        changed=VerticalTerminalExpectation.from_context(context,repository_root=self.root,
            external_assets={item.role:self.root/item.path for item in expected.external_assets})
        false_positive={**result,"scientific_outcome":"positive","result_payload":{"statistical_result_sha256":hashlib.sha256(raw).hexdigest()}}
        with self.assertRaises(A0XVerticalTerminalPackageError):
            terminal_package._verify_material_evidence(self.root,changed,false_positive)
        without_calibration=replace(expected,trust_files=tuple(item for item in expected.trust_files if item.path!=paths["calibration"]))
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError,"missing"):
            terminal_package._verify_material_evidence(self.root,without_calibration,result)

    def test_engineering_rehearsal_sealed_package_stays_permanently_ineligible(self):
        expected, result = self._engineering_fixture()
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(repository_root=self.root, destination=destination,
            expected=expected, terminal_result=result)
        verified = verify_vertical_terminal_package(package_root=destination, repository_root=self.root,
            expected=expected, expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256)
        self.assertFalse(verified.publication_eligible)
        self.assertEqual("engineering_rehearsal", verified.qualification_context)
        self.assertEqual("null", verified.scientific_outcome)

    def test_private_execution_evidence_rejects_rehashed_calibration_sentinel_and_asset_drift(self):
        expected, result = self._engineering_fixture()
        paths = terminal_package._material_evidence_paths(expected)
        calibration_raw = (self.root / paths["calibration"]).read_bytes()
        calibration = json.loads(calibration_raw)
        control = next(item for name, item in calibration["controls"].items()
                       if not name.startswith("random_") and "evaluations" in item)
        metric = next(iter(control["evaluations"][0]["domains"].values()))
        metric["f1"] = {"numerator": 1, "denominator": 1, "display": 1.0}
        metric["paired_margin"] = {"numerator": 1, "denominator": 1, "display": 1.0}
        (self.root / paths["calibration"]).write_bytes(terminal_package._canonical_json(calibration) + b"\n")
        context = terminal_package.capture_material_evidence(self.root, self._last_fixture_context)
        changed = VerticalTerminalExpectation.from_context(context, repository_root=self.root,
            external_assets={item.role: self.root / item.path for item in expected.external_assets})
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "sentinel"):
            terminal_package._verify_material_evidence(self.root, changed, result)
        (self.root / paths["calibration"]).write_bytes(calibration_raw)
        changed = replace(expected, external_assets=tuple(replace(item, sha256="0" * 64) for item in expected.external_assets))
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "actual assets"):
            terminal_package._verify_material_evidence(self.root, changed, result)

    def test_engineering_rehearsal_cannot_publish_under_a_real_results_root(self):
        expected, result = self._engineering_fixture()
        outer_root = Path(self.temp.name).resolve()
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "rehearsal namespace"):
            build_vertical_terminal_package(repository_root=outer_root,
                destination=outer_root / expected.pair_binding["output_path"], expected=expected, terminal_result=result)
        self.assertFalse((outer_root / "results").exists())

    def test_public_verifier_rejects_engineering_rehearsal_even_with_correct_digest_anchors(self):
        expected, result = self._engineering_fixture()
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(repository_root=self.root, destination=destination,
            expected=expected, terminal_result=result)
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "qualification context"):
            verify_public_vertical_terminal_package(evidence_root=self.root, package_root=destination,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256)

    def test_private_verifier_refuses_rehearsal_package_relocated_outside_its_namespace(self):
        expected, result = self._engineering_fixture()
        reference = build_vertical_terminal_package(repository_root=self.root,
            destination=self.root / expected.pair_binding["output_path"],
            expected=expected, terminal_result=result)
        relocated = Path(self.temp.name).resolve() / "relocated-repository"
        self.root.rename(relocated)
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "rehearsal namespace"):
            verify_vertical_terminal_package(repository_root=relocated,
                package_root=relocated / expected.pair_binding["output_path"], expected=expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256)

    def test_public_trust_manifest_contains_only_allowlisted_public_schema(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        trust_raw = (destination / "trust-manifest.json").read_bytes()
        trust = json.loads(trust_raw)
        self.assertNotIn(b".a0x-runtime", trust_raw)
        self.assertNotIn(b"runtime-mapping.json", trust_raw)
        self.assertNotIn(hashlib.sha256(b'{"private_runtime_mapping":"synthetic only"}\n').hexdigest().encode(), trust_raw)
        self.assertTrue(trust["private_execution_inputs_excluded"])
        self.assertEqual(
            [{
                "role": "execution_authorization_schema",
                "path": "execution-authorization-v4.schema.json",
                "size": len((destination / "execution-authorization-v4.schema.json").read_bytes()),
                "raw_sha256": hashlib.sha256((destination / "execution-authorization-v4.schema.json").read_bytes()).hexdigest(),
            }],
            trust["files"],
        )

    def test_public_production_verifier_requires_pinned_closure_and_cross_binds_outcome(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        production_expected = replace(self.expected, qualification_context="production")
        production_result = dict(self.result)
        production_result.update(qualification_context="production", reached_frontier="sealed")
        # Production building remains disabled; this test-only seam creates a
        # structurally valid adversarial package for the public verifier path.
        with patch.object(terminal_package, "_validate_expectation_context", return_value=None):
            reference = build_vertical_terminal_package(
                repository_root=self.root,
                destination=destination,
                expected=production_expected,
                terminal_result=production_result,
            )

        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "independently pinned"):
            verify_public_vertical_terminal_package(
                package_root=destination, evidence_root=self.root,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

        closure_status = TerminalClosureStatus(
            document_bindings_consistent=True,
            derivation_authenticated=False,
            operator_approval_authenticated=False,
            authorization_verified=False,
            publication_eligible=False,
            private_originals_verified=False,
            manifest_sha256="a" * 64,
            terminal_outcome="failed",
        )
        with patch.object(terminal_package, "load_public_terminal_closure", return_value=closure_status) as loader:
            verified = verify_public_vertical_terminal_package(
                package_root=destination, evidence_root=self.root,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
                expected_public_closure_manifest_sha256="a" * 64,
            )
        self.assertTrue(verified.public_closure_verified)
        self.assertEqual("a" * 64, verified.public_closure_manifest_sha256)
        loader.assert_called_once()

        with patch.object(
            terminal_package, "load_public_terminal_closure",
            return_value=replace(closure_status, terminal_outcome="positive"),
        ):
            with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "outcome differs"):
                verify_public_vertical_terminal_package(
                    package_root=destination, evidence_root=self.root,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                    expected_public_closure_manifest_sha256="a" * 64,
                )

    def test_public_trust_manifest_refuses_missing_allowlisted_schema(self):
        expected, result = self._fixture()
        schema = self.root / "schemas/a0x-execution-authorization-v4.schema.json"
        schema.unlink()
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_fresh_public_verifier_needs_only_package_and_declared_assets(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        fresh = Path(self.temp.name) / "fresh-public-root"
        fresh.mkdir()
        fresh_package = fresh / self.expected.pair_binding["output_path"]
        fresh_package.parent.mkdir(parents=True)
        shutil.copytree(destination, fresh_package)
        self.assertFalse((fresh / ".a0x-runtime").exists())
        verified = verify_public_vertical_terminal_package(
            package_root=fresh_package,
            evidence_root=fresh,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertIsInstance(verified, PublicVerticalPackageIntegrity)
        self.assertTrue(verified.package_integrity_verified)
        self.assertFalse(verified.execution_evidence_verified)
        self.assertFalse(verified.publication_eligible)

    def test_fresh_public_verifier_checks_pair_bound_external_assets(self):
        expected, result = self._fixture(with_assets=True)
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=expected,
            terminal_result=result,
        )
        fresh = Path(self.temp.name) / "fresh-public-assets-root"
        fresh.mkdir()
        fresh_package = fresh / expected.pair_binding["output_path"]
        fresh_package.parent.mkdir(parents=True)
        shutil.copytree(destination, fresh_package)
        for asset in expected.external_assets:
            asset_destination = fresh / asset.path
            asset_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / asset.path, asset_destination)

        verified = verify_public_vertical_terminal_package(
            package_root=fresh_package,
            evidence_root=fresh,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertTrue(verified.package_integrity_verified)
        self.assertFalse(verified.execution_evidence_verified)
        self.assertFalse(verified.publication_eligible)

        dense = next(asset for asset in expected.external_assets if asset.role == "dense")
        (fresh / dense.path).write_bytes(b"mutated asset")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_public_vertical_terminal_package(
                package_root=fresh_package,
                evidence_root=fresh,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_fresh_public_verifier_rejects_missing_external_asset(self):
        expected, result = self._fixture(with_assets=True)
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=expected,
            terminal_result=result,
        )
        fresh = Path(self.temp.name) / "fresh-public-missing-asset-root"
        fresh.mkdir()
        fresh_package = fresh / expected.pair_binding["output_path"]
        fresh_package.parent.mkdir(parents=True)
        shutil.copytree(destination, fresh_package)
        for asset in expected.external_assets:
            asset_destination = fresh / asset.path
            asset_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / asset.path, asset_destination)
        dense = next(asset for asset in expected.external_assets if asset.role == "dense")
        (fresh / dense.path).unlink()
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_public_vertical_terminal_package(
                package_root=fresh_package,
                evidence_root=fresh,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_verifier_rejects_manifest_identity_not_matching_independent_expectation(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        altered = VerticalTerminalExpectation(
            **{
                **self.expected.__dict__,
                "source_tree": "f" * 40,
            },
        )
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=altered,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_expectation_is_recursively_immutable(self):
        with self.assertRaises(TypeError):
            self.expected.pair_binding["leg"] = "r1"
        with self.assertRaises(TypeError):
            self.expected.pair_binding["dense_bound"]["leg"] = "r1"
        with self.assertRaises(TypeError):
            self.expected.vertical_package_digests["dossier_sha256"] = "f" * 64

    def test_builder_refuses_mutated_trust_input(self):
        trust_path = self.root / "schemas/a0x-execution-authorization-v4.schema.json"
        trust_path.write_bytes(b"mutated")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / self.expected.pair_binding["output_path"],
                expected=self.expected,
                terminal_result=self.result,
            )

    def test_builder_refuses_existing_destination_without_overwrite(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        destination.mkdir(parents=True)
        (destination / "operator-file").write_bytes(b"preserve")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=destination,
                expected=self.expected,
                terminal_result=self.result,
            )
        self.assertEqual(b"preserve", (destination / "operator-file").read_bytes())

    def test_verifier_rejects_extra_or_missing_package_members(self):
        for mutation in ("extra", "missing"):
            with self.subTest(mutation=mutation):
                expected, result = self._fixture()
                destination = self.root / expected.pair_binding["output_path"]
                reference = build_vertical_terminal_package(
                    repository_root=self.root,
                    destination=destination,
                    expected=expected,
                    terminal_result=result,
                )
                if mutation == "extra":
                    (destination / "undeclared.json").write_bytes(b"{}")
                else:
                    (destination / "report.md").unlink()
                with self.assertRaises(A0XVerticalTerminalPackageError):
                    verify_vertical_terminal_package(
                        package_root=destination,
                        repository_root=self.root,
                        expected=expected,
                        expected_manifest_sha256=reference.manifest_sha256,
                        expected_root_receipt_sha256=reference.root_receipt_sha256,
                    )
                shutil.rmtree(destination)

    def test_verifier_re_reads_trust_inputs_after_package_build(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        (self.root / self.expected.trust_files[0].path).write_bytes(b"changed after package build")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=self.expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_verifier_revalidates_trust_after_package_contents_are_read(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        render = terminal_package._render_report

        def mutate_trust_after_first_validation(result, expected):
            rendered = render(result, expected)
            (self.root / expected.trust_files[0].path).write_bytes(b"late trust mutation")
            return rendered

        with patch.object(terminal_package, "_render_report", side_effect=mutate_trust_after_first_validation):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_verifier_rejects_package_directory_replacement_during_verification(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        render = terminal_package._render_report
        moved = destination.with_name(destination.name + ".moved")
        replaced = False

        def replace_package_after_initial_reads(result, expected):
            nonlocal replaced
            rendered = render(result, expected)
            if not replaced:
                replaced = True
                destination.rename(moved)
                destination.mkdir()
                for member in moved.iterdir():
                    (destination / member.name).write_bytes(member.read_bytes())
            return rendered

        with patch.object(terminal_package, "_render_report", side_effect=replace_package_after_initial_reads):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_verifier_rejects_parent_directory_replacement_during_verification(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        render = terminal_package._render_report
        parent = destination.parent
        moved_parent = parent.with_name(parent.name + ".moved")
        replaced = False

        def replace_parent_after_initial_reads(result, expected):
            nonlocal replaced
            rendered = render(result, expected)
            if not replaced:
                replaced = True
                parent.rename(moved_parent)
                parent.mkdir(parents=True)
                replacement = parent / destination.name
                replacement.mkdir()
                for member in (moved_parent / destination.name).iterdir():
                    (replacement / member.name).write_bytes(member.read_bytes())
            return rendered

        with patch.object(terminal_package, "_render_report", side_effect=replace_parent_after_initial_reads):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_verifier_rejects_same_inode_same_size_late_member_rewrite(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        membership = terminal_package._verify_package_membership_fd
        calls = 0

        def mutate_after_first_member_pass(directory_fd, *, expected_names):
            nonlocal calls
            membership(directory_fd, expected_names=expected_names)
            calls += 1
            if calls == 3:
                report = destination / "report.md"
                original = report.read_bytes()
                replacement = bytes([original[0] ^ 1]) + original[1:]
                with report.open("r+b") as stream:
                    stream.write(replacement)
                    stream.flush()
                    os.fsync(stream.fileno())

        with patch.object(terminal_package, "_verify_package_membership_fd", side_effect=mutate_after_first_member_pass):
            with self.assertRaises(A0XVerticalTerminalPackageError):
                verify_vertical_terminal_package(
                    package_root=destination,
                    repository_root=self.root,
                    expected=self.expected,
                    expected_manifest_sha256=reference.manifest_sha256,
                    expected_root_receipt_sha256=reference.root_receipt_sha256,
                )

    def test_external_asset_locator_binds_dense_and_index_bytes(self):
        expected, result = self._fixture(with_assets=True)
        destination = self.root / expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=expected,
            terminal_result=result,
        )
        verified = verify_vertical_terminal_package(
            package_root=destination,
            repository_root=self.root,
            expected=expected,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        self.assertFalse(verified.publication_eligible)
        self.assertTrue((destination / "external-assets-locator.json").is_file())
        dense = self.root / expected.external_assets[0].path
        dense.write_bytes(b"mutated dense asset")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_external_asset_paths_are_exact_pair_derived_public_destinations(self):
        graph = _graph()
        context = bind_validated_vertical_graph(graph, qualification_context="synthetic-target-free")
        private_assets = {
            "dense": self.root / ".a0x-runtime/private/dense.bin",
            "index": self.root / ".a0x-runtime/private/index.json",
        }
        for path in private_assets.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic asset")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            VerticalTerminalExpectation.from_context(
                context,
                repository_root=self.root,
                external_assets=private_assets,
            )

    def test_verifier_rejects_hardlinked_package_member(self):
        destination = self.root / self.expected.pair_binding["output_path"]
        reference = build_vertical_terminal_package(
            repository_root=self.root,
            destination=destination,
            expected=self.expected,
            terminal_result=self.result,
        )
        alias = self.root / "report-alias.md"
        alias.hardlink_to(destination / "report.md")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            verify_vertical_terminal_package(
                package_root=destination,
                repository_root=self.root,
                expected=self.expected,
                expected_manifest_sha256=reference.manifest_sha256,
                expected_root_receipt_sha256=reference.root_receipt_sha256,
            )

    def test_production_positive_result_requires_dense_assets(self):
        context = bind_validated_vertical_graph(_graph(qualification_context="production"), qualification_context="production")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            VerticalTerminalExpectation.from_context(context)

    def test_production_label_cannot_grant_publication_eligibility(self):
        expected = replace(self.expected, qualification_context="production")
        result = dict(self.result)
        result["qualification_context"] = "production"
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_unsealed_scientific_outcome_is_rejected_even_with_assets(self):
        expected, result = self._fixture()
        result["scientific_outcome"] = "positive"
        result["result_payload"] = {"statistical_result_sha256": "d" * 64}
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_unbounded_public_payload_fields_are_rejected(self):
        expected, result = self._fixture()
        result["result_payload"] = {"log": "authorization token=private"}
        with self.assertRaises(A0XVerticalTerminalPackageError):
            build_vertical_terminal_package(
                repository_root=self.root,
                destination=self.root / expected.pair_binding["output_path"],
                expected=expected,
                terminal_result=result,
            )

    def test_fabricated_production_context_cannot_create_package_expectation(self):
        context = bind_validated_vertical_graph(_graph(qualification_context="production"), qualification_context="production")
        with self.assertRaises(A0XVerticalTerminalPackageError):
            VerticalTerminalExpectation.from_context(context)

    def test_cleanup_refuses_replacement_stage_directory(self):
        parent = self.root / "safe-parent"
        parent.mkdir()
        parent_fd = _open_directory_chain(self.root, parent, create=False)
        stage_name = ".owned-stage"
        os.mkdir(stage_name, dir_fd=parent_fd)
        owned_fd = os.open(stage_name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0), dir_fd=parent_fd)
        owned_info = os.fstat(owned_fd)
        os.rename(parent / stage_name, parent / ".moved-owned-stage")
        os.mkdir(parent / stage_name)
        (parent / stage_name / "do-not-delete").write_bytes(b"operator data")
        with self.assertRaisesRegex(A0XVerticalTerminalPackageError, "OWNERSHIP_LOST"):
            _cleanup_owned_stage(
                parent_fd=parent_fd,
                stage_fd=owned_fd,
                stage_name=stage_name,
                stage_identity=(owned_info.st_dev, owned_info.st_ino),
                file_identities={},
            )
        self.assertEqual(b"operator data", (parent / stage_name / "do-not-delete").read_bytes())
        os.close(owned_fd)
        os.close(parent_fd)


if __name__ == "__main__":
    unittest.main()
