"""Synthetic TDD coverage for independent A0X package verification."""
from __future__ import annotations

import hashlib
import json
import copy
import os
import shutil
from pathlib import Path

from tests.a0x_test_support import A0XTempTestCase
import tests.test_a0x_report as report_tests


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _reanchor_after_json_mutation(package: Path, role: str, mutate) -> str:
    """Rewrite one synthetic package JSON role and rebuild only its ledgers."""
    manifest_path = package / "publication-manifest.json"
    root_path = package / "output-occupancy-receipt.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(item for item in manifest["package_artifacts"] if item["role"] == role)
    artifact_path = package / entry["path"]
    value = json.loads(artifact_path.read_text(encoding="utf-8"))
    mutate(value)
    raw = _json_bytes(value)
    artifact_path.write_bytes(raw)
    entry["bytes"] = len(raw)
    entry["raw_sha256"] = hashlib.sha256(raw).hexdigest()

    manifest_raw = _json_bytes(manifest)
    manifest_path.write_bytes(manifest_raw)
    root = json.loads(root_path.read_text(encoding="utf-8"))
    component = {
        "manifest": len(manifest_raw),
        "package_artifacts": sum(item["bytes"] for item in manifest["package_artifacts"]),
        "external_outputs": sum(item["bytes"] for item in manifest["external_outputs"]),
        "source_inputs": sum(item["bytes"] for item in manifest["source_inputs"]),
        "retained_residue": sum(item["bytes"] for item in manifest["retained_residue"]),
    }
    final = (
        component["manifest"]
        + component["package_artifacts"]
        + component["external_outputs"]
        + component["retained_residue"]
    )
    root["manifest_raw_sha256"] = hashlib.sha256(manifest_raw).hexdigest()
    root["component_bytes"] = component
    root["final_bytes_excluding_this_receipt"] = final
    root["peak_bytes_before_this_receipt"] = final
    root["runtime_checkpoints"] = [
        {"phase": "pre_manifest_write", "bytes": final - len(manifest_raw)},
        {"phase": "pre_root_receipt_write", "bytes": final},
    ]
    if role == "activation_receipt":
        root["activation_receipt_raw_sha256"] = hashlib.sha256(raw).hexdigest()
    root_raw = _json_bytes(root)
    root_path.write_bytes(root_raw)
    return hashlib.sha256(root_raw).hexdigest()


class A0XVerifyTests(A0XTempTestCase):
    _completed_fixture = report_tests.A0XReportTests._completed_fixture
    _completed_activation_frontier_fixture = (
        report_tests.A0XReportTests._completed_activation_frontier_fixture
    )
    def _verify(self, fixture: dict[str, object], package) -> None:
        from latent_triz.a0x_verify import verify_a0x_package
        root = package / "output-occupancy-receipt.json"
        verify_a0x_package(
            package_root=package, repository_root=fixture["repository_root"],
            leg_freeze=fixture["leg_freeze"], dossier_path=fixture["dossier_path"],
            authorization_path=fixture["authorization_path"],
            expected_root_receipt_sha256=hashlib.sha256(root.read_bytes()).hexdigest(),
            root_receipt_path=root, protected_trees=fixture["protected_trees"],
            protected_tree_verifier=fixture["protected_tree_verifier"],
        )

    def test_verifies_complete_package_from_external_root_anchor(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import verify_a0x_package

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)
        self._verify(fixture, package)
        calls = fixture["protected_tree_verifier"].calls
        expected_root = Path(fixture["repository_root"]).resolve(strict=True)
        self.assertEqual([expected_root, expected_root], [call[0] for call in calls])
        self.assertEqual(["postflight", "postflight"], [call[2] for call in calls])
        expected_hashes = {
            fixture["protected_trees"]["a0"]["protected_tree_sha256"],
            fixture["protected_trees"]["r1"]["protected_tree_sha256"],
        }
        self.assertEqual(2, len(expected_hashes))
        self.assertEqual(expected_hashes, {call[1] for call in calls})

    def test_rejects_mutated_external_dense_report_and_root_anchor(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError, verify_a0x_package

        for mutation in ("dense", "report", "anchor"):
            with self.subTest(mutation=mutation):
                fixture = self._completed_fixture()
                package = build_terminal_package(**fixture)
                root = package / "output-occupancy-receipt.json"
                if mutation == "dense":
                    (fixture["repository_root"] / "external" / "activations.safetensors").write_bytes(b"mutated")
                    expected = hashlib.sha256(root.read_bytes()).hexdigest()
                elif mutation == "report":
                    (package / "report.md").write_text("mutated", encoding="utf-8")
                    expected = hashlib.sha256(root.read_bytes()).hexdigest()
                else:
                    expected = "0" * 64
                with self.assertRaises(A0XVerificationError):
                    verify_a0x_package(
                        package_root=package, repository_root=fixture["repository_root"],
                        leg_freeze=fixture["leg_freeze"], dossier_path=fixture["dossier_path"],
                        authorization_path=fixture["authorization_path"], expected_root_receipt_sha256=expected,
                        root_receipt_path=root, protected_trees=fixture["protected_trees"],
                        protected_tree_verifier=fixture["protected_tree_verifier"],
                    )

    def test_rejects_undeclared_package_member_and_campaign_pooling_fields(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError, verify_a0x_campaign_separation

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)
        (package / "undeclared.txt").write_text("x", encoding="utf-8")
        with self.assertRaises(A0XVerificationError):
            self._verify(fixture, package)
        manifest = json.loads((package / "publication-manifest.json").read_text(encoding="utf-8"))
        manifest["aggregate"] = 1
        with self.assertRaises(A0XVerificationError):
            verify_a0x_campaign_separation([manifest])

    def test_verifies_each_terminal_frontier_without_pooling(self) -> None:
        from latent_triz.a0x_report import build_terminal_package

        for frontier, status in (("preflight", "incompatible"), ("activation", "failed"), ("analysis", "non_interpretable"), ("analysis", "failed")):
            with self.subTest(frontier=frontier, status=status):
                fixture = self._completed_fixture()
                terminal = json.loads(fixture["terminal_result_path"].read_text(encoding="utf-8"))
                terminal.update({"sealed_from_state": frontier, "status": status, "statistical_result": None})
                if frontier in {"preflight", "activation"}:
                    terminal["analysis_target_content_reads"] = 0
                    terminal["target_read_receipt_sha256"] = None
                if frontier == "preflight":
                    fixture["artifacts"] = {}
                    fixture["external_assets"] = {}
                elif frontier == "activation":
                    fixture["artifacts"] = {key: value for key, value in fixture["artifacts"].items() if key in {"model_identity_receipt", "ccp_observation", "preflight_receipt"}}
                    fixture["external_assets"] = {}
                else:
                    fixture["artifacts"].pop("statistical_result")
                fixture["terminal_result_path"].write_text(json.dumps(terminal, sort_keys=True, separators=(",", ":")), encoding="utf-8")
                self._verify(fixture, build_terminal_package(**fixture))

    def test_fails_closed_for_missing_protected_checks_and_duplicate_frozen_pair(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError, verify_a0x_campaign_separation, verify_a0x_package

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)
        root = package / "output-occupancy-receipt.json"
        with self.assertRaises(A0XVerificationError):
            verify_a0x_package(package_root=package, repository_root=fixture["repository_root"], leg_freeze=fixture["leg_freeze"], dossier_path=fixture["dossier_path"], authorization_path=fixture["authorization_path"], expected_root_receipt_sha256=hashlib.sha256(root.read_bytes()).hexdigest())
        manifest = json.loads((package / "publication-manifest.json").read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(manifest)
        duplicate["pair_binding"]["run_id"] = "different-run-id"
        with self.assertRaises(A0XVerificationError):
            verify_a0x_campaign_separation([manifest, duplicate])

    def test_rejects_report_claim_and_root_path_spoof(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError, verify_a0x_package

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)
        root = package / "output-occupancy-receipt.json"
        (package / "report.md").write_text("This exploratory automated-proxy result is not a general TRIZ, causal, mechanism, emergence, or training-data claim. EXP-002", encoding="utf-8")
        with self.assertRaises(A0XVerificationError):
            self._verify(fixture, package)
        with self.assertRaises(A0XVerificationError):
            verify_a0x_package(package_root=package, repository_root=fixture["repository_root"], leg_freeze=fixture["leg_freeze"], dossier_path=fixture["dossier_path"], authorization_path=fixture["authorization_path"], expected_root_receipt_sha256=hashlib.sha256(root.read_bytes()).hexdigest(), root_receipt_path=package / "publication-manifest.json", protected_trees=fixture["protected_trees"], protected_tree_verifier=fixture["protected_tree_verifier"])

    def test_rejects_protected_tree_substitution(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError, verify_a0x_package

        fixture = self._completed_fixture(); package = build_terminal_package(**fixture)
        root = package / "output-occupancy-receipt.json"
        trees = dict(fixture["protected_trees"])
        relevant = fixture["leg_freeze"].leg.value
        trees[relevant] = dict(trees[relevant])
        trees[relevant]["protected_tree_sha256"] = "0" * 64
        with self.assertRaises(A0XVerificationError):
            verify_a0x_package(package_root=package, repository_root=fixture["repository_root"], leg_freeze=fixture["leg_freeze"], dossier_path=fixture["dossier_path"], authorization_path=fixture["authorization_path"], expected_root_receipt_sha256=hashlib.sha256(root.read_bytes()).hexdigest(), protected_trees=trees, protected_tree_verifier=fixture["protected_tree_verifier"])

    def test_rejects_reanchored_completed_activation_mutations(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError

        def mutate_path(receipt: dict[str, object]) -> None:
            receipt["dense"]["path"] = "wrong.safetensors"

        def mutate_size(receipt: dict[str, object]) -> None:
            receipt["dense"]["bytes"] += 1

        def mutate_hash(receipt: dict[str, object]) -> None:
            receipt["dense"]["sha256"] = "0" * 64

        def mutate_bound(receipt: dict[str, object]) -> None:
            receipt["planned_dense_bound"]["total_bytes"] += 1

        mutations = {
            "status": lambda receipt: receipt.__setitem__("activation_status", "not_started"),
            "target-read": lambda receipt: receipt.__setitem__("activation_target_content_reads", 1),
            "occupancy-hash": lambda receipt: receipt.__setitem__("activation_stage_occupancy_sha256", "0" * 64),
            "locator-path": mutate_path,
            "locator-size": mutate_size,
            "locator-hash": mutate_hash,
            "planned-bound": mutate_bound,
        }
        for label, mutate in mutations.items():
            with self.subTest(mutation=label):
                fixture = self._completed_activation_frontier_fixture()
                package = build_terminal_package(**fixture)
                _reanchor_after_json_mutation(package, "activation_receipt", mutate)
                with self.assertRaises(A0XVerificationError):
                    self._verify(fixture, package)

    def test_rejects_one_byte_cap_overflow(self) -> None:
        from latent_triz.a0x_contract import PairBinding
        from latent_triz.a0x_verify import A0XVerificationError, _root
        from tests.a0x_test_support import pair_binding

        pair = PairBinding.from_mapping(pair_binding(hidden_width=2))
        manifest_raw = b"x"
        ledgers = {
            "package_artifacts": [],
            "external_outputs": [{"bytes": pair.dense_bound.cap_bytes}],
            "source_inputs": [],
            "retained_residue": [],
        }
        final = pair.dense_bound.cap_bytes + 1
        component = {
            "manifest": 1,
            "package_artifacts": 0,
            "external_outputs": pair.dense_bound.cap_bytes,
            "source_inputs": 0,
            "retained_residue": 0,
        }
        receipt = {
            "manifest_raw_sha256": hashlib.sha256(manifest_raw).hexdigest(),
            "component_bytes": component,
            "final_bytes_excluding_this_receipt": final,
            "cap_bytes": pair.dense_bound.cap_bytes,
            "peak_bytes_before_this_receipt": final,
            "runtime_checkpoints": [
                {"phase": "pre_manifest_write", "bytes": final},
                {"phase": "pre_root_receipt_write", "bytes": final},
            ],
            "activation_receipt_raw_sha256": None,
        }
        with self.assertRaises(A0XVerificationError):
            _root(receipt, b"{}", manifest_raw, ledgers, pair)

    def test_fresh_copy_verifies_then_refuses_mutation(self) -> None:
        from latent_triz.a0x_freeze import verify_protected_tree
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError, verify_a0x_package

        fixture = self._completed_fixture()
        build_terminal_package(**fixture)
        copied_root = self.temp_path / "fresh-copy"
        shutil.copytree(fixture["repository_root"], copied_root)
        pair_output = json.loads(
            (copied_root / "dossiers" / "approval-dossier.json").read_text(encoding="utf-8")
        )["pair_binding"]["output_path"]
        package = copied_root / pair_output
        calls: list[Path] = []

        def verify_from_copy(root: str | Path, manifest: dict[str, object], *, phase: str) -> None:
            resolved = Path(root).resolve(strict=True)
            calls.append(resolved)
            self.assertEqual(copied_root.resolve(strict=True), resolved)
            verify_protected_tree(resolved, manifest, phase=phase)

        root_receipt = package / "output-occupancy-receipt.json"
        kwargs = {
            "package_root": package,
            "repository_root": copied_root,
            "leg_freeze": fixture["leg_freeze"],
            "dossier_path": copied_root / "dossiers" / "approval-dossier.json",
            "authorization_path": copied_root / "authorizations" / "execution-authorization.json",
            "expected_root_receipt_sha256": hashlib.sha256(root_receipt.read_bytes()).hexdigest(),
            "root_receipt_path": root_receipt,
            "protected_trees": fixture["protected_trees"],
            "protected_tree_verifier": verify_from_copy,
        }
        verify_a0x_package(**kwargs)
        self.assertEqual([copied_root.resolve(strict=True)] * 2, calls)
        (copied_root / "external" / "activations.safetensors").write_bytes(b"mutated")
        with self.assertRaises(A0XVerificationError):
            verify_a0x_package(**kwargs)

    def test_rejects_non_finite_json_symlink_ancestor_and_cross_ledger_alias(self) -> None:
        from latent_triz.a0x_report import build_terminal_package
        from latent_triz.a0x_verify import A0XVerificationError

        for token in ("NaN", "Infinity"):
            with self.subTest(token=token):
                fixture = self._completed_fixture()
                package = build_terminal_package(**fixture)
                manifest_path = package / "publication-manifest.json"
                raw = manifest_path.read_text(encoding="utf-8")
                manifest_path.write_text(raw[:-1] + f',"non_finite":{token}}}', encoding="utf-8")
                with self.assertRaises(A0XVerificationError):
                    self._verify(fixture, package)

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)
        external = fixture["repository_root"] / "external"
        actual = fixture["repository_root"] / "external-real"
        external.rename(actual)
        external.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(A0XVerificationError):
            self._verify(fixture, package)

        fixture = self._completed_fixture()
        package = build_terminal_package(**fixture)
        dense = fixture["repository_root"] / "external" / "activations.safetensors"
        dense.unlink()
        os.link(fixture["dossier_path"], dense)
        with self.assertRaises(A0XVerificationError):
            self._verify(fixture, package)
