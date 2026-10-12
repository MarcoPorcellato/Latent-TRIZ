"""Exact child-wire parsing for the A0X vertical Gate-C path."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from latent_triz import a0x_ccp_executor
from latent_triz.a0x_pair import Leg, PairBinding, compute_dense_bound


class A0XVerticalTerminalTests(unittest.TestCase):
    def _expected(self):
        pair = PairBinding.from_mapping({
            "binding_profile": "a0x-pair-scope-v2",
            "leg": "a0",
            "leg_freeze_sha256": "c" * 64,
            "model_key": "smollm2_360m",
            "model_id": "HuggingFaceTB/SmolLM2-360M",
            "revision": "a" * 40,
            "run_id": "run-01",
            "output_path": "results/a0x/a0/smollm2_360m/run-01",
            "dense_bound": compute_dense_bound(Leg.A0, cases=48, hidden_width=8).as_mapping(),
        }).as_mapping()
        return {
            "source": {"head": "a" * 40, "tree": "b" * 40, "ref": "refs/heads/main"},
            "pair": pair,
            "authorization_id": "gate-c-auth-01",
            "attempt_id": "gate-c-attempt-01",
            "qualification_context": "synthetic-target-free",
        }

    def _wire(self):
        expected = self._expected()
        return {
            "artifact_class": "a0x-vertical-material-child-terminal",
            "terminal_profile": "a0x-vertical-child-terminal-v1",
            "exit_class": "completed",
            "qualified_source": expected["source"],
            "pair_binding": expected["pair"],
            "authorization_id": expected["authorization_id"],
            "attempt_id": expected["attempt_id"],
            "qualification_context": expected["qualification_context"],
            "reached_frontier": "validated_graph",
            "scientific_outcome": None,
            "terminal_package": None,
        }

    def _parse(self, value=None, *, expected=None):
        parser = getattr(a0x_ccp_executor, "_parse_vertical_child_terminal", None)
        self.assertTrue(callable(parser), "vertical terminal parser is missing")
        binding = expected or self._expected()
        raw = (json.dumps(value if value is not None else self._wire(), sort_keys=True, separators=(",", ":")) + "\n").encode()
        return parser(
            raw,
            expected_source=binding["source"],
            expected_pair=binding["pair"],
            expected_authorization_id=binding["authorization_id"],
            expected_attempt_id=binding["attempt_id"],
            expected_qualification_context=binding["qualification_context"],
        )

    def test_parser_accepts_bound_synthetic_observation_without_scientific_claim(self):
        terminal = self._parse()
        self.assertEqual("completed", terminal["exit_class"])
        self.assertEqual("validated_graph", terminal["reached_frontier"])
        self.assertIsNone(terminal["scientific_outcome"])
        self.assertIsNone(terminal["terminal_package"])

    def test_parser_rejects_any_source_pair_authorization_or_attempt_drift(self):
        wrong_pair = dict(self._expected()["pair"])
        wrong_pair["run_id"] = "other"
        for field, replacement in (
            ("qualified_source", {"head": "0" * 40, "tree": "b" * 40, "ref": "refs/heads/main"}),
            ("pair_binding", wrong_pair),
            ("authorization_id", "other-auth"),
            ("attempt_id", "other-attempt"),
            ("qualification_context", "production"),
        ):
            with self.subTest(field=field):
                wire = self._wire()
                wire[field] = replacement
                self.assertIsNone(self._parse(wire))

    def test_production_completed_terminal_requires_sealed_package(self):
        wire = self._wire()
        wire["qualification_context"] = "production"
        wire["reached_frontier"] = "validated_graph"
        expected = self._expected()
        expected["qualification_context"] = "production"
        self.assertIsNone(self._parse(wire, expected=expected))

    def test_production_terminal_rejects_unstructured_package_claim(self):
        wire = self._wire()
        wire.update({
            "qualification_context": "production",
            "reached_frontier": "sealed",
            "scientific_outcome": "positive",
            "terminal_package": {},
        })
        expected = self._expected()
        expected["qualification_context"] = "production"
        self.assertIsNone(self._parse(wire, expected=expected))

    def test_production_terminal_requires_exact_package_path_and_raw_hashes(self):
        expected = self._expected()
        expected["qualification_context"] = "production"
        base = {
            "package_relative_path": expected["pair"]["output_path"],
            "manifest_raw_sha256": "c" * 64,
            "root_receipt_raw_sha256": "d" * 64,
        }
        for replacement in (
            base,
            {**base, "package_relative_path": "results/other"},
            {**base, "manifest_raw_sha256": "not-a-digest"},
            {**base, "unexpected": "field"},
        ):
            with self.subTest(reference=replacement):
                wire = self._wire()
                wire.update({
                    "qualification_context": "production",
                    "reached_frontier": "sealed",
                    "scientific_outcome": "null",
                    "terminal_package": replacement,
                })
                parsed = self._parse(wire, expected=expected)
                if replacement == base:
                    self.assertIsNotNone(parsed)
                else:
                    self.assertIsNone(parsed)

    def test_production_completion_needs_parent_package_and_postflight_proofs(self):
        terminal = self._wire()
        terminal.update({
            "qualification_context": "production",
            "reached_frontier": "sealed",
            "scientific_outcome": "failed",
            "terminal_package": {
                "package_relative_path": self._expected()["pair"]["output_path"],
                "manifest_raw_sha256": "c" * 64,
                "root_receipt_raw_sha256": "d" * 64,
            },
        })
        self.assertFalse(a0x_ccp_executor._vertical_completion_verified(
            "production", "completed", terminal,
            package_verified=False, postflight_verified=True,
        ))
        self.assertFalse(a0x_ccp_executor._vertical_completion_verified(
            "production", "completed", terminal,
            package_verified=True, postflight_verified=False,
        ))
        self.assertTrue(a0x_ccp_executor._vertical_completion_verified(
            "production", "completed", terminal,
            package_verified=True, postflight_verified=True,
        ))
        self.assertFalse(a0x_ccp_executor._vertical_completion_verified(
            "production", "cleanup_or_internal", terminal,
            package_verified=True, postflight_verified=True,
        ))

    def test_terminal_record_keeps_recovery_required_without_parent_closure(self):
        pair = PairBinding.from_mapping(self._expected()["pair"])
        launch = SimpleNamespace(
            source_head="a" * 40,
            as_mapping=lambda: {"source_head": "a" * 40, "test": "bounded"},
        )
        child_terminal = {
            "exit_class": "completed",
            "reached_frontier": "sealed",
            "scientific_outcome": "null",
            "terminal_package": {
                "package_relative_path": pair.output_path,
                "manifest_raw_sha256": "c" * 64,
                "root_receipt_raw_sha256": "d" * 64,
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            authorization_path = root / "authorization.json"
            authorization_path.write_bytes(b"{}")
            relative = a0x_ccp_executor._write_vertical_terminal(
                root, authorization_path, pair, launch, None, "completed", "e" * 64, None,
                child_terminal=child_terminal,
            )
            payload = json.loads((root / relative).read_bytes())
        self.assertTrue(payload["recovery_required"])
        self.assertFalse(payload["publication_eligible"])

    def test_terminal_schema_binding_refuses_replacement_before_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema_path = root / "schemas/a0x-vertical-child-terminal-v1.schema.json"
            schema_path.parent.mkdir()
            schema_path.write_bytes((a0x_ccp_executor.Path(__file__).resolve().parents[1] / "schemas/a0x-vertical-child-terminal-v1.schema.json").read_bytes())
            binding = a0x_ccp_executor._read_vertical_schema_binding(
                root, "a0x-vertical-child-terminal-v1.schema.json",
            )
            schema_path.write_bytes(schema_path.read_bytes() + b" ")
            with self.assertRaises(a0x_ccp_executor.A0XCcpExecutorError):
                a0x_ccp_executor._revalidate_vertical_schema_binding(binding)

    def test_terminal_schema_binding_refuses_symlink_and_hardlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema_dir = root / "schemas"
            schema_dir.mkdir()
            source = schema_dir / "source.json"
            source.write_bytes(b'{"type":"object"}')
            symlink_root = root / "symlink-case"
            (symlink_root / "schemas").mkdir(parents=True)
            (symlink_root / "schemas/a0x-vertical-child-terminal-v1.schema.json").symlink_to(source)
            with self.assertRaises(a0x_ccp_executor.A0XCcpExecutorError):
                a0x_ccp_executor._read_vertical_schema_binding(
                    symlink_root, "a0x-vertical-child-terminal-v1.schema.json",
                )

            hardlink_root = root / "hardlink-case"
            (hardlink_root / "schemas").mkdir(parents=True)
            (hardlink_root / "schemas/a0x-vertical-child-terminal-v1.schema.json").hardlink_to(source)
            with self.assertRaises(a0x_ccp_executor.A0XCcpExecutorError):
                a0x_ccp_executor._read_vertical_schema_binding(
                    hardlink_root, "a0x-vertical-child-terminal-v1.schema.json",
                )

    def test_pre_run_is_never_marked_publication_eligible(self):
        pair = PairBinding.from_mapping(self._expected()["pair"])
        launch = SimpleNamespace(
            source_head="a" * 40,
            as_mapping=lambda: {"source_head": "a" * 40, "test": "bounded"},
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            authorization_path = root / "authorization.json"
            authorization_path.write_bytes(b"{}")
            claim_path = root / "claim.json"
            claim_path.write_bytes(b"{}")
            relative = a0x_ccp_executor._write_vertical_pre_run(
                root, authorization_path, pair, launch, claim_path, "a" * 64,
            )
            payload = json.loads((root / relative).read_bytes())
        self.assertFalse(payload["publication_eligible"])


if __name__ == "__main__":
    unittest.main()
