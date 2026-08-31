"""Synthetic TDD coverage for immutable A0X terminal-package construction."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from latent_triz.a0x_contract import Leg, LegFreezeBinding
from tests.a0x_test_support import A0XTempTestCase, artifact, authorization_documents, pair_binding


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class A0XReportTests(A0XTempTestCase):
    def _completed_fixture(self, *, leg: Leg = Leg.A0, status: str = "positive") -> dict[str, object]:
        pair = pair_binding(leg, hidden_width=2)
        dossier, authorization, chain = authorization_documents(pair)
        repository = self.temp_path / f"synthetic-repository-{leg.value}-{status}-{len(tuple(self.temp_path.iterdir()))}"
        repository.mkdir()
        dossier_path = repository / "dossiers" / "approval-dossier.json"
        authorization_path = repository / "authorizations" / "execution-authorization.json"
        dossier_path.parent.mkdir(parents=True)
        authorization_path.parent.mkdir(parents=True)
        dossier_path.write_bytes(_json_bytes(dossier))
        authorization_path.write_bytes(_json_bytes(authorization))
        if leg is Leg.A0:
            from tests.test_a0x_a0_analysis import synthetic_a0_inputs
            from latent_triz.a0x_a0_analysis import analyze_a0x_a0
            inputs = synthetic_a0_inputs(primary_signal=1.0 if status == "positive" else 0.0, final_signal=0.0)
            statistical = analyze_a0x_a0(**inputs)
        else:
            from tests.test_a0x_r1_analysis import synthetic_r1_inputs
            from latent_triz.a0x_r1_analysis import analyze_a0x_r1
            inputs = synthetic_r1_inputs(primary_signal=1.0 if status == "positive" else 0.0, final_signal=0.0)
            statistical = analyze_a0x_r1(**inputs)
        source = repository / "inputs"
        source.mkdir()
        artifact_paths: dict[str, Path] = {}
        for role, schema_name in (
            ("model_identity_receipt", "a0x-model-identity-receipt.schema.json"),
            ("preflight_receipt", "a0x-preflight-receipt.schema.json"),
        ):
            value = artifact(schema_name)
            value["pair_binding"] = pair
            value["authorization_chain"] = chain
            path = source / f"{role}.json"
            path.write_bytes(_json_bytes(value))
            artifact_paths[role] = path
        ccp_observation = {
            "artifact_class": "a0x-guard-preflight-observation",
            "observation_profile": "a0x-guard-preflight-observation-v1",
            "pair_binding": pair, "source_head": "a" * 40,
            "ccp": {"role": "ccp", "source_commit": "27adf8d0820b3cd96f9c5e149de9b580ae41f639", "qualified_source_tree": "d8e0364d1313fde0898a44517ae6d233d9e10763", "sha256": "c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4", "version": "commit-ci-preflight 0.1.0"},
            "source": {"head": "a" * 40, "clean": True},
            "resource": {"decision": "admit"},
            "admission": {"active": False, "queue_count": 0, "slot_state": "free"},
            "runtime": {"intended_runtime_responsive": True, "active_container_count": 0},
            "commands": [{"role": role, "exit_code": 0, "output_sha256": f"{index:064x}", "output_bytes": index} for index, role in enumerate(("ccp_version", "resource_status", "admission_status", "git_source_state", "docker_context", "docker_active_count"), 1)],
        }
        ccp_path = source / "ccp_observation.json"
        ccp_raw = _json_bytes(ccp_observation)
        ccp_path.write_bytes(ccp_raw)
        artifact_paths["ccp_observation"] = ccp_path
        preflight_path = artifact_paths["preflight_receipt"]
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        preflight["ccp_observation_path"] = "ccp-observation.json"
        preflight["ccp_observation_raw_sha256"] = hashlib.sha256(ccp_raw).hexdigest()
        preflight_path.write_bytes(_json_bytes(preflight))
        activation_path = source / "activation-receipt.json"
        activation = json.loads(inputs["activation_receipt_bytes"].decode("utf-8"))
        occupancy_raw = _json_bytes(activation["activation_stage_occupancy"]) + b"\n"
        activation["activation_stage_occupancy_sha256"] = hashlib.sha256(occupancy_raw).hexdigest()
        activation_path.write_bytes(_json_bytes(activation))
        target_path = source / "target-read-receipt.json"
        target = json.loads(inputs["target_read_receipt_bytes"].decode("utf-8"))
        target["selection_corpus_sha256"] = "4" * 64
        target["activation_receipt_sha256"] = hashlib.sha256(activation_path.read_bytes()).hexdigest()
        target_path.write_bytes(_json_bytes(target))
        result_path = source / "statistical-result.json"
        result_path.write_bytes(_json_bytes(statistical))
        artifact_paths.update({
            "activation_receipt": activation_path,
            "target_read_receipt": target_path,
            "statistical_result": result_path,
        })
        external = repository / "external"
        external.mkdir()
        dense_path = external / "activations.safetensors"
        index_path = external / "representations-index.jsonl"
        dense_path.write_bytes(inputs["dense_asset_bytes"])
        index_path.write_bytes(inputs["index_bytes"])
        terminal = {
            "artifact_class": "a0x-terminal-result", "empirical": True,
            "scientific_status": "exploratory", "evidence_eligible": False,
            "expert_validated": False, "claim_ids": [], "pair_binding": pair,
            "authorization_chain": chain, "status": statistical["status"],
            "sealed_from_state": "analysis", "analysis_target_content_reads": 1,
            "target_read_receipt_sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
            "statistical_result": statistical,
        }
        terminal_path = source / "terminal-result.json"
        terminal_path.write_bytes(_json_bytes(terminal))
        from latent_triz.a0x_freeze import build_protected_tree, verify_protected_tree

        protected = {}
        for name in ("a0", "r1"):
            tree = repository / "protected" / name
            tree.mkdir(parents=True, exist_ok=True)
            (tree / "marker.txt").write_text(name, encoding="utf-8")
            protected[name] = build_protected_tree(
                repository,
                roots=(Path("protected") / name,),
                external_assets=(),
                source_base_commit="5" * 40,
            )
        protected_calls: list[tuple[Path, str, str]] = []

        def record_and_verify_protected_tree(
            protected_root: str | Path,
            manifest: dict[str, object],
            *,
            phase: str,
        ) -> None:
            resolved_root = Path(protected_root).resolve(strict=True)
            protected_calls.append((resolved_root, str(manifest["protected_tree_sha256"]), phase))
            if resolved_root != repository.resolve(strict=True):
                raise AssertionError("protected-tree verifier received an alternate repository root")
            verify_protected_tree(resolved_root, manifest, phase=phase)
        record_and_verify_protected_tree.calls = protected_calls  # type: ignore[attr-defined]

        return {
            "repository_root": repository, "destination": repository / pair["output_path"],
            "leg_freeze": LegFreezeBinding(
                leg=leg, protocol_id=f"a0x-{leg.value}-replication-v1",
                protocol_sha256="1" * 64, implementation_sha256="2" * 64,
                leg_freeze_sha256=pair["leg_freeze_sha256"], protected_tree_sha256=protected[leg.value]["protected_tree_sha256"],
                selection_corpus_sha256="4" * 64, source_base_commit="5" * 40,
            ),
            "dossier_path": dossier_path, "authorization_path": authorization_path,
            "terminal_result_path": terminal_path, "artifacts": artifact_paths,
            "external_assets": {"dense": dense_path, "index": index_path},
            "protected_trees": protected,
            "protected_tree_verifier": record_and_verify_protected_tree,
        }

    def _completed_activation_frontier_fixture(self) -> dict[str, object]:
        fixture = self._completed_fixture()
        terminal_path = Path(fixture["terminal_result_path"])
        terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
        terminal.update({
            "sealed_from_state": "activation",
            "status": "failed",
            "analysis_target_content_reads": 0,
            "target_read_receipt_sha256": None,
            "statistical_result": None,
        })
        terminal_path.write_bytes(_json_bytes(terminal))
        fixture["artifacts"] = {
            role: path
            for role, path in fixture["artifacts"].items()
            if role not in {"target_read_receipt", "statistical_result"}
        }
        return fixture

    def test_current_gate_a_files_refuse_before_package_construction(self) -> None:
        """Current package construction rehashes every Gate-A file locally."""
        from latent_triz.a0x_report import A0XReportError, _gate_a_evidence_for_package
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        for role in ("manifest", "attestation_bundle", "trusted_root", "transport", "verification_receipt"):
            for mutation in ("missing", "mutated", "symlink", "hardlink", "nonregular"):
                with self.subTest(role=role, mutation=mutation):
                    bundle = prepare_constructible_runtime_bundle()
                    self.addCleanup(bundle.close)
                    authorization = json.loads((bundle.root / bundle.receipt["authorization_path"]).read_text())
                    evidence = authorization["gate_a_evidence"]
                    binding = evidence["verification_receipt"] if role == "verification_receipt" else evidence["hosted_inputs"][role]
                    path = bundle.root / binding["path"]
                    if mutation == "missing":
                        path.unlink()
                    elif mutation == "mutated":
                        path.write_bytes(b"mutated")
                    elif mutation == "symlink":
                        target = bundle.root / "untrusted-gate-a-package-bytes"
                        target.write_bytes(path.read_bytes())
                        path.unlink()
                        path.symlink_to(target)
                    elif mutation == "hardlink":
                        os.link(path, bundle.root / "untrusted-gate-a-package-alias")
                    else:
                        path.unlink()
                        path.mkdir()
                    with self.assertRaises(A0XReportError):
                        _gate_a_evidence_for_package(bundle.root, authorization)

    def test_builds_an_immutable_complete_a0_package(self) -> None:
        from latent_triz.a0x_report import build_terminal_package

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)

        self.assertEqual(fixture["destination"], package)
        self.assertTrue((package / "publication-manifest.json").is_file())
        self.assertTrue((package / "output-occupancy-receipt.json").is_file())
        self.assertTrue((package / "report.md").is_file())
        self.assertTrue((package / "qualification-evidence.json").is_file())
        self.assertEqual(
            Path(fixture["authorization_path"]).read_bytes(),
            (package / "execution-authorization.json").read_bytes(),
        )
        authorization = json.loads(
            Path(fixture["authorization_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            authorization["qualification_evidence"],
            json.loads((package / "qualification-evidence.json").read_text(encoding="utf-8")),
        )
        self.assertFalse((package / "activations.safetensors").exists())
        report = (package / "report.md").read_text(encoding="utf-8")
        self.assertIn("This exploratory automated-proxy result is not a general TRIZ, causal, mechanism, emergence, or training-data claim.", report)
        with self.assertRaisesRegex(Exception, "overwrite|exists|destination"):
            build_terminal_package(**fixture)

    def test_builds_both_statistical_leg_branches(self) -> None:
        from latent_triz.a0x_report import build_terminal_package

        for leg, status in ((Leg.A0, "null"), (Leg.R1, "positive")):
            with self.subTest(leg=leg, status=status):
                fixture = self._completed_fixture(leg=leg, status=status)
                package = build_terminal_package(**fixture)
                self.assertTrue((package / "statistical-result.json").is_file())

    def test_all_five_terminal_statuses_follow_the_frozen_artifact_matrix(self) -> None:
        from latent_triz.a0x_report import build_terminal_package

        for frontier, status in (
            ("preflight", "failed"), ("activation", "incompatible"),
            ("analysis", "non_interpretable"), ("analysis", "failed"),
            ("analysis", "positive"),
        ):
            with self.subTest(frontier=frontier, status=status):
                fixture = self._completed_fixture()
                terminal = json.loads(Path(fixture["terminal_result_path"]).read_text(encoding="utf-8"))
                terminal["sealed_from_state"] = frontier
                terminal["status"] = status
                terminal["statistical_result"] = terminal["statistical_result"] if status == "positive" else None
                if frontier == "preflight":
                    terminal["analysis_target_content_reads"] = 0
                    terminal["target_read_receipt_sha256"] = None
                    fixture["artifacts"] = {}
                    fixture["external_assets"] = {}
                elif frontier == "activation":
                    terminal["analysis_target_content_reads"] = 0
                    terminal["target_read_receipt_sha256"] = None
                    fixture["artifacts"] = {key: value for key, value in fixture["artifacts"].items() if key in {"model_identity_receipt", "ccp_observation", "preflight_receipt"}}
                    fixture["external_assets"] = {}
                elif status != "positive":
                    fixture["artifacts"].pop("statistical_result")
                Path(fixture["terminal_result_path"]).write_bytes(_json_bytes(terminal))
                package = build_terminal_package(**fixture)
                self.assertEqual(frontier == "analysis" and status == "positive", (package / "statistical-result.json").is_file())

    def test_refuses_cross_pair_artifact_and_terminal_statistical_swap(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package

        fixture = self._completed_fixture()
        identity_path = fixture["artifacts"]["model_identity_receipt"]
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["pair_binding"]["model_key"] = "smollm2_135m"
        identity_path.write_bytes(_json_bytes(identity))
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

    def test_persists_exact_terminal_bytes_and_rejects_alias_inputs(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package

        fixture = self._completed_fixture()
        terminal_raw = Path(fixture["terminal_result_path"]).read_bytes()
        package = build_terminal_package(**fixture)
        self.assertEqual(terminal_raw, (package / "terminal-result.json").read_bytes())
        fixture = self._completed_fixture()
        fixture["external_assets"]["index"] = fixture["external_assets"]["dense"]
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

    def test_rejects_completed_residue_and_non_finite_terminal_json(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package

        fixture = self._completed_fixture()
        residue = fixture["repository_root"] / "failure.bin"
        residue.write_bytes(b"x")
        fixture["retained_residue"] = {"failure_residue": residue}
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

    def test_refuses_destination_outside_frozen_pair_path(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package
        fixture = self._completed_fixture()
        fixture["destination"] = fixture["repository_root"] / "wrong-output"
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)
        fixture = self._completed_fixture()
        fixture["terminal_result_path"].write_text('{"bad":NaN}', encoding="utf-8")
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

        fixture = self._completed_fixture()
        result_path = fixture["artifacts"]["statistical_result"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["status"] = "null"
        result["outcome_rule"]["passed"] = False
        result_path.write_bytes(_json_bytes(result))
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

    def test_rejects_completed_activation_status_read_and_occupancy_mutations(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package

        mutations = {
            "status": lambda receipt: receipt.__setitem__("activation_status", "not_started"),
            "target-read": lambda receipt: receipt.__setitem__("activation_target_content_reads", 1),
            "occupancy-hash": lambda receipt: receipt.__setitem__("activation_stage_occupancy_sha256", "0" * 64),
        }
        for label, mutate in mutations.items():
            with self.subTest(mutation=label):
                fixture = self._completed_activation_frontier_fixture()
                activation_path = fixture["artifacts"]["activation_receipt"]
                activation = json.loads(activation_path.read_text(encoding="utf-8"))
                mutate(activation)
                activation_path.write_bytes(_json_bytes(activation))
                with self.assertRaises(A0XReportError):
                    build_terminal_package(**fixture)

    def test_rejects_activation_locator_and_planned_bound_mutations(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package

        def mutate_path(receipt: dict[str, object]) -> None:
            receipt["dense"]["path"] = "different.safetensors"

        def mutate_size(receipt: dict[str, object]) -> None:
            receipt["dense"]["bytes"] += 1

        def mutate_hash(receipt: dict[str, object]) -> None:
            receipt["dense"]["sha256"] = "0" * 64

        def mutate_bound(receipt: dict[str, object]) -> None:
            receipt["planned_dense_bound"]["total_bytes"] += 1

        for label, mutate in {
            "path": mutate_path,
            "size": mutate_size,
            "hash": mutate_hash,
            "planned-bound": mutate_bound,
        }.items():
            with self.subTest(mutation=label):
                fixture = self._completed_activation_frontier_fixture()
                activation_path = fixture["artifacts"]["activation_receipt"]
                activation = json.loads(activation_path.read_text(encoding="utf-8"))
                mutate(activation)
                activation_path.write_bytes(_json_bytes(activation))
                with self.assertRaises(A0XReportError):
                    build_terminal_package(**fixture)

    def test_rejects_lexical_symlink_and_cross_ledger_physical_aliases(self) -> None:
        from latent_triz.a0x_report import A0XReportError, build_terminal_package

        fixture = self._completed_fixture()
        fixture["external_assets"]["dense"] = (
            fixture["repository_root"] / "external" / ".." / "external" / "activations.safetensors"
        )
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

        fixture = self._completed_fixture()
        alias = fixture["repository_root"] / "external-alias"
        alias.symlink_to(fixture["repository_root"] / "external", target_is_directory=True)
        fixture["external_assets"]["dense"] = alias / "activations.safetensors"
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)

        fixture = self._completed_fixture()
        fixture["external_assets"]["dense"] = fixture["dossier_path"]
        with self.assertRaises(A0XReportError):
            build_terminal_package(**fixture)
