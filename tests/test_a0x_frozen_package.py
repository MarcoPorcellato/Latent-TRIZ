from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import (  # noqa: E402
    A0XContractError,
    Leg,
    assert_leg_freeze_binding,
    build_leg_freeze_binding,
    sha256_file,
)
from latent_triz.a0x_freeze import (  # noqa: E402
    A0XFreezeError,
    freeze_a0x_campaign,
    verify_batch_pre_regeneration_ledger,
)
from latent_triz.a0x_runner import (  # noqa: E402
    A0XRunnerError,
    frozen_pair_dossiers,
    verify_a0x_dossier_inventory,
    verify_a0x_no_model,
)
from latent_triz.validator import validate  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "experiments/a0x-six-model"

A0_PROTOCOL_FIELDS = (
    "corpus_generation",
    "calibration_families_per_domain",
    "sealed_families_per_domain",
    "paired_syntax_templates",
    "neutral_domains",
    "target_families",
    "splits",
    "predeclared_calibration_rule",
    "frozen_analysis",
    "views",
    "token_sites",
    "preregistered_layers",
    "shortcut_evaluation",
    "outcome_rules",
    "shortcuts",
    "runtime",
)
R1_PROTOCOL_FIELDS = (
    "protocol_type",
    "independence_audit",
    "runtime",
    "primary_endpoint",
    "sensitivity_endpoints",
    "shortcut_evaluation",
    "thresholds",
    "calibration",
    "outcome_rules",
    "outcome_classes",
)


def load(relative: str) -> dict[str, object]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{relative} is not an object")
    return value


class A0XFrozenPackageTests(unittest.TestCase):
    def test_implementation_inventory_is_sorted_unique_and_regular(self) -> None:
        from latent_triz import a0x_freeze

        paths = a0x_freeze._IMPLEMENTATION_PATHS
        self.assertEqual(tuple(sorted(paths)), paths)
        self.assertEqual(len(paths), len(set(paths)))
        for relative in paths:
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(1, path.stat().st_nlink)

    def test_frozen_protocols_copy_scientific_rules_by_value(self) -> None:
        for leg, source_path, fields, endpoints in (
            ("a0", "experiments/a0-automated-weak-proxy/protocol.json", A0_PROTOCOL_FIELDS, [0, 2, 4, 6]),
            ("r1", "experiments/a0r1-independent-proxy/protocol.json", R1_PROTOCOL_FIELDS, [6]),
        ):
            with self.subTest(leg=leg):
                source = load(source_path)
                protocol = load(f"experiments/a0x-six-model/{leg}/protocol.json")
                self.assertEqual({field: source[field] for field in fields}, protocol["inherited_rules"])
                self.assertEqual(endpoints, protocol["endpoint_indices"])
                self.assertEqual({
                    "model_card_index_field": "final_transformer_block_tuple_index",
                    "required_equal_model_card_field": "num_hidden_layers",
                    "role": "descriptive_sensitivity",
                    "rescues_primary": False,
                }, protocol["descriptive_final_block_endpoint"])
                self.assertEqual(f"a0x-{leg}-six-model-v1", protocol["identity"]["protocol_id"])
                self.assertEqual(source_path, protocol["source_protocol_path"])
                self.assertEqual(sha256_file(ROOT / source_path), protocol["source_protocol_raw_sha256"])
                self.assertFalse(protocol["sealed_targets_accessed"])
                self.assertFalse(protocol["model_output_accessed"])

    def test_implementations_bind_every_declared_source_and_test_file(self) -> None:
        for leg in ("a0", "r1"):
            with self.subTest(leg=leg):
                implementation = load(f"experiments/a0x-six-model/{leg}/implementation.json")
                paths = implementation["implementation_paths"]
                bindings = implementation["implementation_files"]
                self.assertEqual(paths, [row["path"] for row in bindings])
                self.assertIn("tests/test_a0x_frozen_package.py", paths)
                self.assertIn("src/latent_triz/a0x_runner.py", paths)
                self.assertTrue({
                    "scripts/a0x_build_gate_b_runtime.py",
                    "scripts/a0x_prepare_runtime.py",
                    "src/latent_triz/a0x_apfs.py",
                    "src/latent_triz/a0x_gate_b_builder.py",
                    "src/latent_triz/a0x_runtime_bundle.py",
                    "src/latent_triz/a0x_runtime_readiness.py",
                    "src/latent_triz/a0x_wheelhouse.py",
                    "tests/test_a0x_apfs.py",
                    "tests/test_a0x_gate_b_builder.py",
                    "tests/test_a0x_runtime_bundle.py",
                    "tests/test_a0x_runtime_readiness.py",
                    "tests/test_a0x_wheelhouse.py",
                    "schemas/a0x-execution-authorization-v4.schema.json",
                    "schemas/a0x-gate-b-authorization-v2.schema.json",
                    "schemas/a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1.schema.json",
                    "schemas/a0x-vertical-gate-a-evidence-binding-v1.schema.json",
                    "schemas/a0x-vertical-gate-b-output-v2.schema.json",
                    "schemas/a0x-vertical-package-commitment-v2.schema.json",
                    "schemas/a0x-vertical-slice-manifest-v2.schema.json",
                    "src/latent_triz/validator.py",
                    "tests/test_a0x_vertical_gate_chain_v2.py",
                    "tests/test_a0x_vertical_runtime_bundle.py",
                    "tests/test_a0x_vertical_slice_v2.py",
                    "docs/qualification/a0x-vertical-chain-historical-protection.json",
                }.issubset(paths))
                for row in bindings:
                    with self.subTest(leg=leg, path=row["path"]):
                        path = ROOT / row["path"]
                        self.assertEqual(path.stat().st_size, row["bytes"])
                        self.assertEqual(sha256_file(path), row["sha256"])

    def test_implementation_inventory_rejects_a_nonfinal_binding_mutation(self) -> None:
        """Catch an assertion loop that checks only the last implementation row."""
        for leg in ("a0", "r1"):
            with self.subTest(leg=leg), tempfile.TemporaryDirectory() as directory:
                clone = Path(directory) / "repository"
                completed = subprocess.run(
                    ["git", "clone", "--no-hardlinks", str(ROOT), str(clone)],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                implementation_path = clone / f"experiments/a0x-six-model/{leg}/implementation.json"
                implementation = json.loads(implementation_path.read_text(encoding="utf-8"))
                rows = implementation["implementation_files"]
                self.assertGreater(len(rows), 1)
                nonfinal = rows[0]
                source = clone / nonfinal["path"]
                original = source.read_bytes()
                source.write_bytes(original + b"# nonfinal inventory mutation\\n")
                with self.assertRaisesRegex(A0XFreezeError, "source/test hash binding drifted"):
                    from latent_triz import a0x_freeze
                    with patch.object(a0x_freeze, "_IMPLEMENTATION_PATHS", tuple(implementation["implementation_paths"])):
                        a0x_freeze.verify_frozen_legs(clone)

    def test_batch_pre_regeneration_ledger_replays_exact_parent_blobs(self) -> None:
        """Keep the one historical batch snapshot auditable without making it active input."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        verified = verify_batch_pre_regeneration_ledger(ROOT, ledger)
        self.assertEqual("d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d", verified["parent_head"])
        self.assertEqual("54c59868802af381f57f830102a01be54410e718", verified["parent_tree"])
        self.assertEqual(17, verified["entry_count"])
        self.assertEqual(
            "a0x-batch-pre-regeneration-ledger-v1",
            verified["profile"],
        )

    def test_batch_pre_regeneration_ledger_refuses_missing_parent(self) -> None:
        """Historical verification must fail closed when Git lacks its exact parent."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        with tempfile.TemporaryDirectory() as directory:
            shallow = Path(directory) / "shallow"
            completed = subprocess.run(
                ["git", "clone", "--depth", "1", f"file://{ROOT}", str(shallow)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            copied = shallow / ledger.relative_to(ROOT)
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(ledger.read_bytes())
            with self.assertRaisesRegex(A0XFreezeError, "historical parent is unavailable"):
                verify_batch_pre_regeneration_ledger(shallow, copied)

    def test_historical_vertical_evidence_manifest_remains_byte_identical(self) -> None:
        manifest = load("docs/qualification/a0x-vertical-chain-historical-protection.json")
        self.assertEqual("a0x-vertical-chain-historical-protection-v1", manifest["profile"])
        self.assertEqual("2026-09-05", manifest["recorded_on"])
        protected = manifest["protected_files"]
        self.assertEqual(7, len(protected))
        self.assertEqual(sorted(item["path"] for item in protected), [item["path"] for item in protected])
        for item in protected:
            with self.subTest(path=item["path"]):
                path = ROOT / item["path"]
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(1, path.stat().st_nlink)
                self.assertEqual(item["bytes"], path.stat().st_size)
                self.assertEqual(item["sha256"], sha256_file(path))

    def test_protocol_implementation_and_freeze_do_not_self_hash(self) -> None:
        forbidden_by_kind = {
            "protocol.json": {"protocol_sha256", "leg_freeze_sha256"},
            "implementation.json": {"implementation_sha256", "leg_freeze_sha256"},
            "freeze.json": {"leg_freeze_sha256"},
        }
        for leg in ("a0", "r1"):
            paths = {
                "protocol.json": CAMPAIGN / leg / "protocol.json",
                "implementation.json": CAMPAIGN / leg / "implementation.json",
                "freeze.json": CAMPAIGN / "freeze" / f"{leg}-freeze.json",
            }
            for kind, path in paths.items():
                with self.subTest(leg=leg, kind=kind):
                    value = json.loads(path.read_text(encoding="utf-8"))
                    self.assertTrue(forbidden_by_kind[kind].isdisjoint(value))

    def test_freeze_bindings_match_exact_components_and_leg_sources(self) -> None:
        selection_raw_sha = sha256_file(CAMPAIGN / "a0-selection-manifest.json")
        r1_manifest_raw_sha = sha256_file(ROOT / "data/a0r1/manifest.json")
        expected_selection = {Leg.A0: selection_raw_sha, Leg.R1: r1_manifest_raw_sha}
        expected_tree = {
            Leg.A0: load("experiments/a0x-six-model/protected-a0-tree.json")["protected_tree_sha256"],
            Leg.R1: load("experiments/a0x-six-model/protected-a0r1-tree.json")["protected_tree_sha256"],
        }
        for leg in (Leg.A0, Leg.R1):
            binding = build_leg_freeze_binding(
                CAMPAIGN / leg.value / "protocol.json",
                CAMPAIGN / leg.value / "implementation.json",
                CAMPAIGN / "freeze" / f"{leg.value}-freeze.json",
            )
            self.assertEqual(expected_selection[leg], binding.selection_corpus_sha256)
            self.assertEqual(expected_tree[leg], binding.protected_tree_sha256)

    def test_twelve_dossiers_are_one_pair_each_and_share_only_their_leg_freeze(self) -> None:
        expected = frozen_pair_dossiers()
        self.assertEqual(12, len(expected))
        cards = load("experiments/a0x-six-model/model-registry.json")["cards"]
        self.assertEqual(6, len(cards))
        schema = load("schemas/a0x-authorization-dossier.schema.json")
        by_leg: dict[Leg, list[dict[str, object]]] = {Leg.A0: [], Leg.R1: []}
        for (leg_name, model_key), relative in expected.items():
            dossier = load(relative)
            self.assertEqual([], validate(dossier, schema))
            self.assertEqual("approval_requested", dossier["dossier_status"])
            pair = dossier["pair_binding"]
            self.assertEqual(leg_name, pair["leg"])
            self.assertEqual(model_key, pair["model_key"])
            self.assertNotIn("authorization_status", dossier)
            by_leg[Leg(leg_name)].append(dossier)
        for leg, dossiers in by_leg.items():
            binding = build_leg_freeze_binding(
                CAMPAIGN / leg.value / "protocol.json",
                CAMPAIGN / leg.value / "implementation.json",
                CAMPAIGN / "freeze" / f"{leg.value}-freeze.json",
            )
            self.assertEqual(1, len({item["pair_binding"]["leg_freeze_sha256"] for item in dossiers}))
            assert_leg_freeze_binding(binding, dossiers)

    def test_wrong_leg_or_freeze_hash_is_rejected(self) -> None:
        dossier = load("experiments/a0x-six-model/approval-dossiers/a0/gpt2.json")
        binding = build_leg_freeze_binding(
            CAMPAIGN / "a0/protocol.json",
            CAMPAIGN / "a0/implementation.json",
            CAMPAIGN / "freeze/a0-freeze.json",
        )
        wrong_leg = copy.deepcopy(dossier)
        wrong_leg["pair_binding"]["leg"] = "r1"
        with self.assertRaises(A0XContractError):
            assert_leg_freeze_binding(binding, [wrong_leg])
        wrong_hash = copy.deepcopy(dossier)
        wrong_hash["pair_binding"]["leg_freeze_sha256"] = "0" * 64
        with self.assertRaises(A0XContractError):
            assert_leg_freeze_binding(binding, [wrong_hash])

    def test_dossier_inventory_rejects_any_extra_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in frozen_pair_dossiers().values():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
            verify_a0x_dossier_inventory(root)
            extra = root / "experiments/a0x-six-model/approval-dossiers/pooled.json"
            extra.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(A0XRunnerError, "inventory"):
                verify_a0x_dossier_inventory(root)

    def test_freeze_generation_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = Path(first_directory)
            second = Path(second_directory)
            receipt = freeze_a0x_campaign(
                ROOT,
                prepare_dossiers=True,
                output_root=first,
                implementation_source_head="f" * 40,
            )
            freeze_a0x_campaign(
                ROOT,
                prepare_dossiers=True,
                output_root=second,
                implementation_source_head="f" * 40,
            )
            generated = {
                path.relative_to(first): path.read_bytes()
                for path in sorted((first / "experiments/a0x-six-model").glob("**/*.json"))
            }
            repeated = {
                path.relative_to(second): path.read_bytes()
                for path in sorted((second / "experiments/a0x-six-model").glob("**/*.json"))
            }
            dossier_schema = json.loads(
                (ROOT / "schemas/a0x-authorization-dossier.schema.json").read_text(encoding="utf-8"),
            )
            dossiers = sorted((first / "experiments/a0x-six-model/approval-dossiers").glob("**/*.json"))
            self.assertEqual(12, len(dossiers))
            for dossier_path in dossiers:
                dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
                self.assertEqual("f" * 40, dossier["implementation_source_head"])
                self.assertEqual([], validate(dossier, dossier_schema))
        self.assertEqual(generated, repeated)
        self.assertEqual(12, receipt["dossier_count"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertEqual(0, receipt["model_loads"])
        self.assertEqual(0, receipt["ccp_invocations"])

    def test_regeneration_is_byte_identical_for_same_implementation_head(self) -> None:
        """The committed implementation anchor regenerates the tracked package byte-for-byte."""
        current_implementation_head = json.loads((
            CAMPAIGN / "approval-dossiers/a0/gpt2.json"
        ).read_text(encoding="utf-8"))["implementation_source_head"]
        with tempfile.TemporaryDirectory() as directory:
            generated_root = Path(directory)
            freeze_a0x_campaign(
                ROOT,
                prepare_dossiers=True,
                implementation_source_head=current_implementation_head,
                output_root=generated_root,
            )
            tracked_paths = [
                CAMPAIGN / leg / filename
                for leg in ("a0", "r1")
                for filename in ("protocol.json", "implementation.json")
            ] + [
                CAMPAIGN / "freeze" / f"{leg}-freeze.json"
                for leg in ("a0", "r1")
            ] + [
                ROOT / relative for relative in frozen_pair_dossiers().values()
            ]
            tracked = {
                path.relative_to(ROOT): path.read_bytes() for path in sorted(tracked_paths)
            }
            regenerated = {
                path.relative_to(generated_root): path.read_bytes()
                for path in sorted((generated_root / "experiments/a0x-six-model").glob("**/*.json"))
            }
        self.assertEqual(tracked, regenerated)

    def test_freeze_generator_requires_an_explicit_implementation_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TypeError, "implementation_source_head"):
                freeze_a0x_campaign(ROOT, prepare_dossiers=True, output_root=Path(directory))

    def test_no_model_verifier_is_a_strict_frozen_phase_superset(self) -> None:
        receipt = verify_a0x_no_model(ROOT)
        self.assertEqual("frozen_no_model", receipt["phase"])
        self.assertEqual(2, receipt["frozen_leg_count"])
        self.assertEqual(12, receipt["approval_requested_dossier_count"])
        self.assertFalse(receipt["model_loaded"])
        self.assertFalse(receipt["tokenizer_constructed"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertFalse(receipt["ccp_invoked"])
        self.assertFalse(receipt["remote_mutations"])

    def test_tracked_no_model_receipt_matches_canonical_recomputation(self) -> None:
        """The tracked receipt is an exact canonical projection, not merely valid JSON."""
        from scripts.a0x_materialize_no_model_receipt import _canonical_receipt_bytes

        tracked = ROOT / "results/a0x/preexecution/a0x-no-model-verification-receipt.json"
        self.assertEqual(_canonical_receipt_bytes(verify_a0x_no_model(ROOT)), tracked.read_bytes())


if __name__ == "__main__":
    unittest.main()
