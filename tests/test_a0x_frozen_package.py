from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import (  # noqa: E402
    A0XContractError,
    Leg,
    assert_leg_freeze_binding,
    build_leg_freeze_binding,
    sha256_file,
)
from latent_triz.a0x_freeze import freeze_a0x_campaign  # noqa: E402
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
                for row in bindings:
                    path = ROOT / row["path"]
                    self.assertEqual(path.stat().st_size, row["bytes"])
                    self.assertEqual(sha256_file(path), row["sha256"])

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
        expected = {
            path.relative_to(ROOT): path.read_bytes()
            for pattern in ("a0/*.json", "r1/*.json", "freeze/*.json", "approval-dossiers/**/*.json")
            for path in sorted(CAMPAIGN.glob(pattern))
            if path.is_file()
        }
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            receipt = freeze_a0x_campaign(ROOT, prepare_dossiers=True, output_root=destination)
            generated = {
                path.relative_to(destination): path.read_bytes()
                for path in sorted((destination / "experiments/a0x-six-model").glob("**/*.json"))
            }
        self.assertEqual(expected, generated)
        self.assertEqual(12, receipt["dossier_count"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertEqual(0, receipt["model_loads"])
        self.assertEqual(0, receipt["ccp_invocations"])

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


if __name__ == "__main__":
    unittest.main()
