from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from latent_triz.a0x_public_closure import (
    PRE_EXECUTION_PUBLIC_ROLES,
    PRIVATE_PRE_EXECUTION_INPUTS,
    A0XPublicClosureError,
    PRE_EXECUTION_PUBLIC_ROLE_PATHS,
    PRE_EXECUTION_EXTENSION_PATH,
    TERMINAL_CLOSURE_MANIFEST_PATH,
    TERMINAL_CLOSURE_ROLE_PATHS,
    load_pre_execution_public_closure,
    load_public_terminal_closure,
    validate_pre_execution_extension,
    verify_public_terminal_closure,
)
from latent_triz.a0x_contract import build_vertical_package_commitment
from latent_triz.a0x_pair import Leg, PairBinding, compute_dense_bound


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class A0XPublicClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = {
            "qualified_source": {
                "head": "1" * 40,
                "tree": "2" * 40,
                "ref": "refs/heads/main",
            },
            "pair_binding": {
                "binding_profile": "a0x-pair-scope-v2",
                "leg": "a0",
                "leg_freeze_sha256": "3" * 64,
                "model_key": "smollm2_360m",
                "model_id": "HuggingFaceTB/SmolLM2-360M",
                "revision": "4" * 40,
                "run_id": "a0x-a0-smollm2_360m-test-attempt-01",
                "output_path": "results/a0x/a0/smollm2_360m/a0x-a0-smollm2_360m-test-attempt-01",
                "dense_bound": compute_dense_bound(Leg.A0, cases=48, hidden_width=8).as_mapping(),
            },
            "authorization_id": "auth-test-01",
            "attempt_id": "attempt-test-01",
        }
        self.private_inputs = {role: _sha(role.encode()) for role in PRIVATE_PRE_EXECUTION_INPUTS}
        p0_values = {
            "protocol.json": {"artifact_class": "synthetic-protocol"},
            "implementation.json": {"artifact_class": "synthetic-implementation"},
            "freeze.json": {"artifact_class": "synthetic-freeze"},
            "slice-manifest.json": {"artifact_class": "synthetic-slice-manifest"},
        }
        self.p0_raw = {name: _canonical(value) for name, value in p0_values.items()}
        dossier_raw = b"synthetic-private-p0-dossier"
        self.private_inputs["p0_dossier_raw"] = _sha(dossier_raw)
        commitment = build_vertical_package_commitment(
            qualified_source=self.identity["qualified_source"],
            pair=PairBinding.from_mapping(self.identity["pair_binding"]),
            members=[
                {"name": name, "size": len(raw), "sha256": _sha(raw)}
                for name, raw in (
                    ("protocol.json", self.p0_raw["protocol.json"]),
                    ("implementation.json", self.p0_raw["implementation.json"]),
                    ("freeze.json", self.p0_raw["freeze.json"]),
                    ("approval-dossier.json", dossier_raw),
                    ("slice-manifest.json", self.p0_raw["slice-manifest.json"]),
                )
            ],
            generator={"profile": "a0x-vertical-slice-v2", "repository": "MarcoPorcellato/Latent-TRIZ"},
            # P0 is a separate authorization phase from the later Gate-C
            # execution identity represented by ``self.identity``.
            authorization_id="p0-auth-test-01",
            attempt_id="p0-attempt-test-01",
        )
        self.identity["p0_package_commitment_sha256"] = commitment["package_commitment_sha256"]
        identity_fields = {key: self.identity[key] for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id")}
        self.public_roles = {
            "p0_commitment": _canonical(commitment),
            "p0_protocol": self.p0_raw["protocol.json"],
            "p0_implementation": self.p0_raw["implementation.json"],
            "p0_freeze": self.p0_raw["freeze.json"],
            "p0_slice_manifest": self.p0_raw["slice-manifest.json"],
            "public_dossier": _canonical({"artifact_class": "a0x-public-dossier-projection", "profile": "a0x-public-dossier-projection-v1", **identity_fields, "original_raw_sha256": self.private_inputs["p0_dossier_raw"]}),
            "execution_spec": _canonical({"artifact_class": "a0x-public-execution-specification", "profile": "a0x-public-execution-spec-v1", **identity_fields, "protocol_sha256": _sha(self.p0_raw["protocol.json"])}),
            "gate_a_evidence": _canonical({"artifact_class": "a0x-public-gate-a-evidence", "profile": "a0x-public-gate-a-evidence-v1", **identity_fields}),
            "gate_a_attestation_bundle": b'{"synthetic":true}\n',
            "gate_a_trusted_root": b'{"synthetic":true}\n',
            "gate_a_transport": _canonical({"synthetic": True}),
            "gate_b_authorization_projection": _canonical({"artifact_class": "a0x-public-gate-b-authorization-projection", "profile": "a0x-public-gate-b-authorization-projection-v1", **identity_fields, "source_raw_sha256": self.private_inputs["gate_b_authorization_v4"]}),
            "gate_b_readiness_projection": _canonical({"artifact_class": "a0x-public-gate-b-readiness-projection", "profile": "a0x-public-gate-b-readiness-projection-v1", **identity_fields, "source_raw_sha256": self.private_inputs["gate_b_readiness_v4"]}),
        }
        self.extension = {
            "artifact_class": "a0x-public-authorization-extension",
            "profile": "a0x-public-authorization-extension-v1",
            "schema_version": 1,
            **self.identity,
            "bindings": {
                "public_role_sha256": {role: _sha(self.public_roles[role]) for role in PRE_EXECUTION_PUBLIC_ROLES},
                "private_input_sha256": dict(self.private_inputs),
            },
            "claims": {
                "document_bindings_consistent": True,
                "derivation_authenticated": False,
                "operator_approval_authenticated": False,
                "authorization_verified": False,
                "publication_eligible": False,
            },
        }
        self.extension_raw = _canonical(self.extension)

    def test_valid_extension_binds_exact_public_and_private_inputs_only(self) -> None:
        status = validate_pre_execution_extension(
            self.extension_raw,
            public_role_bytes=self.public_roles,
            private_input_sha256=self.private_inputs,
            expected_identity=self.identity,
        )
        self.assertTrue(status.document_bindings_consistent)
        self.assertFalse(status.derivation_authenticated)
        self.assertFalse(status.operator_approval_authenticated)
        self.assertFalse(status.authorization_verified)
        self.assertFalse(status.publication_eligible)
        self.assertEqual(status.public_role_count, len(PRE_EXECUTION_PUBLIC_ROLES))

    def test_p0_commitment_keeps_its_own_phase_ids(self) -> None:
        """The P0 commitment and Gate-C extension bind distinct authorization phases."""
        commitment = json.loads(self.public_roles["p0_commitment"])
        self.assertEqual("p0-auth-test-01", commitment["authorization_id"])
        self.assertEqual("p0-attempt-test-01", commitment["attempt_id"])
        self.assertEqual("auth-test-01", self.extension["authorization_id"])
        self.assertEqual("attempt-test-01", self.extension["attempt_id"])
        status = validate_pre_execution_extension(
            self.extension_raw,
            public_role_bytes=self.public_roles,
            private_input_sha256=self.private_inputs,
            expected_identity=self.identity,
        )
        self.assertTrue(status.document_bindings_consistent)

    def test_p0_commitment_id_mutation_is_still_bound_by_commitment_digest(self) -> None:
        """A coherently rebuilt P0 commitment still cannot replace the expected package."""
        roles = dict(self.public_roles)
        original = json.loads(roles["p0_commitment"])
        commitment = build_vertical_package_commitment(
            qualified_source=original["qualified_source"],
            pair=PairBinding.from_mapping(original["pair_binding"]),
            members=original["members"],
            generator=original["generator"],
            authorization_id="p0-auth-mutated",
            attempt_id=original["attempt_id"],
        )
        roles["p0_commitment"] = _canonical(commitment)
        extension = json.loads(self.extension_raw)
        extension["bindings"]["public_role_sha256"]["p0_commitment"] = _sha(roles["p0_commitment"])
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(extension),
                public_role_bytes=roles,
                private_input_sha256=self.private_inputs,
                expected_identity=self.identity,
            )

    def test_rejects_unknown_or_missing_public_role(self) -> None:
        roles = dict(self.public_roles)
        roles.pop("execution_spec")
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                self.extension_raw,
                public_role_bytes=roles,
                private_input_sha256=self.private_inputs,
                expected_identity=self.identity,
            )

    def test_rejects_mutated_public_spec_even_if_other_bindings_match(self) -> None:
        roles = dict(self.public_roles)
        roles["execution_spec"] += b" "
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                self.extension_raw,
                public_role_bytes=roles,
                private_input_sha256=self.private_inputs,
                expected_identity=self.identity,
            )

    def test_rejects_unknown_public_spec_field_even_when_rehashed(self) -> None:
        roles = dict(self.public_roles)
        spec = json.loads(roles["execution_spec"])
        spec["operator_approval_authenticated"] = True
        roles["execution_spec"] = _canonical(spec)
        extension = json.loads(self.extension_raw)
        extension["bindings"]["public_role_sha256"]["execution_spec"] = _sha(roles["execution_spec"])
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(extension), public_role_bytes=roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )

    def test_rejects_p0_member_mutation_even_if_role_hash_is_rebound(self) -> None:
        roles = dict(self.public_roles)
        roles["p0_protocol"] = _canonical({"artifact_class": "changed"})
        extension = json.loads(self.extension_raw)
        extension["bindings"]["public_role_sha256"]["p0_protocol"] = _sha(roles["p0_protocol"])
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(extension), public_role_bytes=roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )

    def test_rejects_self_asserted_private_hash_mismatch(self) -> None:
        observed = dict(self.private_inputs)
        observed["gate_b_authorization_v4"] = "6" * 64
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                self.extension_raw,
                public_role_bytes=self.public_roles,
                private_input_sha256=observed,
                expected_identity=self.identity,
            )

    def test_rejects_execution_or_postflight_hashes_in_pre_execution_extension(self) -> None:
        value = json.loads(self.extension_raw)
        value["bindings"]["terminal_result_sha256"] = "7" * 64
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(value),
                public_role_bytes=self.public_roles,
                private_input_sha256=self.private_inputs,
                expected_identity=self.identity,
            )

    def test_rejects_identity_swap_and_synthetic_profile(self) -> None:
        value = json.loads(self.extension_raw)
        value["pair_binding"]["model_key"] = "synthetic_model"
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(value), public_role_bytes=self.public_roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )
        value = json.loads(self.extension_raw)
        value["profile"] = "a0x-public-evidence-closure-experimental-v1"
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(value), public_role_bytes=self.public_roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )

    def test_rejects_noncanonical_and_extra_claim_values(self) -> None:
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                self.extension_raw + b"\n", public_role_bytes=self.public_roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )

    def test_rejects_spec_protocol_hash_drift_even_when_rebound(self) -> None:
        roles = dict(self.public_roles)
        spec = json.loads(roles["execution_spec"])
        spec["protocol_sha256"] = "a" * 64
        roles["execution_spec"] = _canonical(spec)
        extension = json.loads(self.extension_raw)
        extension["bindings"]["public_role_sha256"]["execution_spec"] = _sha(roles["execution_spec"])
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(extension), public_role_bytes=roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )

    def test_rejects_gate_b_projection_value_drift_even_when_rebound(self) -> None:
        for role, field in (
            ("gate_b_authorization_projection", "artifact_class"),
            ("gate_b_authorization_projection", "profile"),
            ("gate_b_readiness_projection", "artifact_class"),
            ("gate_b_readiness_projection", "profile"),
        ):
            roles = dict(self.public_roles)
            projection = json.loads(roles[role])
            projection[field] = "synthetic-untrusted-value"
            roles[role] = _canonical(projection)
            extension = json.loads(self.extension_raw)
            extension["bindings"]["public_role_sha256"][role] = _sha(roles[role])
            with self.subTest(role=role, field=field), self.assertRaises(A0XPublicClosureError):
                validate_pre_execution_extension(
                    _canonical(extension), public_role_bytes=roles,
                    private_input_sha256=self.private_inputs, expected_identity=self.identity,
                )
        value = json.loads(self.extension_raw)
        value["claims"]["operator_approval_authenticated"] = True
        with self.assertRaises(A0XPublicClosureError):
            validate_pre_execution_extension(
                _canonical(value), public_role_bytes=self.public_roles,
                private_input_sha256=self.private_inputs, expected_identity=self.identity,
            )

    def test_loader_accepts_only_closed_independent_role_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_closure(Path(temp))
            status = load_pre_execution_public_closure(
                temp, expected_identity=self.identity,
                private_input_sha256=self.private_inputs,
            )
            self.assertTrue(status.document_bindings_consistent)
            self.assertEqual(root.name, "v1")

    def test_loader_rejects_unlisted_role_and_hardlink_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_closure(Path(temp))
            (root / "unexpected.json").write_bytes(b"{}")
            with self.assertRaises(A0XPublicClosureError):
                load_pre_execution_public_closure(
                    temp, expected_identity=self.identity,
                    private_input_sha256=self.private_inputs,
                )

    def test_loader_rejects_mutated_role_bytes_even_under_canonical_path(self) -> None:
        """Path ignores for runtime staging never replace the exact closure hash check."""
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_closure(Path(temp))
            member = root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["execution_spec"]
            member.write_bytes(member.read_bytes() + b" ")
            with self.assertRaises(A0XPublicClosureError):
                load_pre_execution_public_closure(
                    temp, expected_identity=self.identity,
                    private_input_sha256=self.private_inputs,
                )

    def test_loader_rejects_fifo_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_closure(Path(temp))
            fifo = root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["execution_spec"]
            fifo.unlink()
            os.mkfifo(fifo)
            payload = json.dumps({"root": temp, "identity": self.identity, "private": self.private_inputs})
            code = (
                "import json,sys; from latent_triz.a0x_public_closure import "
                "load_pre_execution_public_closure,A0XPublicClosureError; "
                "v=json.load(sys.stdin); "
                "exec('try:\\n load_pre_execution_public_closure(v[\"root\"], expected_identity=v[\"identity\"], private_input_sha256=v[\"private\"])\\nexcept A0XPublicClosureError:\\n raise SystemExit(2)'); "
                "raise SystemExit(0)"
            )
            completed = subprocess.run(
                (sys.executable, "-c", code), input=payload.encode(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, check=False,
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
            )
            self.assertEqual(2, completed.returncode, completed.stderr.decode(errors="replace"))
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_closure(Path(temp))
            source = root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["public_dossier"]
            alias = root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["execution_spec"]
            alias.unlink()
            os.link(source, alias)
            self._rewrite_extension_after_role_change(root)
            with self.assertRaises(A0XPublicClosureError):
                load_pre_execution_public_closure(
                    temp, expected_identity=self.identity,
                    private_input_sha256=self.private_inputs,
                )

    def test_loader_rejects_private_path_marker_but_does_not_claim_general_secret_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_closure(Path(temp))
            (root / PRE_EXECUTION_PUBLIC_ROLE_PATHS["public_dossier"]).write_bytes(b'{"runtime_authorization_path":".a0x-runtime/private.json"}')
            self._rewrite_extension_after_role_change(root)
            with self.assertRaises(A0XPublicClosureError):
                load_pre_execution_public_closure(
                    temp, expected_identity=self.identity,
                    private_input_sha256=self.private_inputs,
                )
        # Known-marker scanning is a narrow tripwire, not a general secret detector.
        self.assertNotIn(b"secret", self.public_roles["execution_spec"].lower())

    def test_terminal_manifest_binds_postflight_only_after_execution(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        manifest = {
            "artifact_class": "a0x-public-closure-manifest",
            "profile": "a0x-public-closure-manifest-v1",
            "schema_version": 1,
            **{key: self.identity[key] for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256")},
            "pre_execution_extension_sha256": _sha(self.extension_raw),
            "terminal_projection_sha256": _sha(terminal),
            "outer_postflight_projection_sha256": _sha(postflight),
            "private_original_sha256": private_originals,
            "claims": {
                "document_bindings_consistent": True,
                "derivation_authenticated": False,
                "operator_approval_authenticated": False,
                "authorization_verified": False,
                "publication_eligible": False,
            },
        }
        status = verify_public_terminal_closure(
            _canonical(manifest), pre_execution_extension_raw=self.extension_raw,
            terminal_projection_raw=terminal, outer_postflight_projection_raw=postflight,
            public_role_bytes=self.public_roles,
            expected_identity=self.identity,
        )
        self.assertTrue(status.document_bindings_consistent)
        self.assertFalse(status.publication_eligible)
        self.assertFalse(status.private_originals_verified)
        self.assertEqual("failed", status.terminal_outcome)

    def test_production_filesystem_loader_verifies_closed_terminal_tree_and_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_terminal_closure(Path(temp))
            manifest_raw = (root / TERMINAL_CLOSURE_MANIFEST_PATH).read_bytes()
            status = load_public_terminal_closure(
                temp,
                expected_identity=self.identity,
                expected_manifest_sha256=_sha(manifest_raw),
            )
            self.assertTrue(status.document_bindings_consistent)
            self.assertFalse(status.private_originals_verified)
            self.assertFalse(status.authorization_verified)
            self.assertFalse(status.publication_eligible)
            with self.assertRaises(A0XPublicClosureError):
                load_public_terminal_closure(
                    temp, expected_identity=self.identity,
                    expected_manifest_sha256="0" * 64,
                )

    def test_production_filesystem_loader_rejects_fifo_terminal_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = self._write_terminal_closure(Path(temp))
            terminal = root / TERMINAL_CLOSURE_ROLE_PATHS["terminal_projection"]
            terminal.unlink()
            os.mkfifo(terminal)
            payload = json.dumps({"root": temp, "identity": self.identity})
            code = (
                "import json,sys; from latent_triz.a0x_public_closure import "
                "load_public_terminal_closure,A0XPublicClosureError; "
                "v=json.load(sys.stdin); "
                "exec('try:\\n load_public_terminal_closure(v[\"root\"], expected_identity=v[\"identity\"], expected_manifest_sha256=\"1\"*64)\\nexcept A0XPublicClosureError:\\n raise SystemExit(2)'); "
                "raise SystemExit(0)"
            )
            completed = subprocess.run(
                (sys.executable, "-c", code), input=payload.encode(),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2, check=False,
                env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
            )
            self.assertEqual(2, completed.returncode, completed.stderr.decode(errors="replace"))

    def test_terminal_verifier_rejects_synthetic_extension_and_changed_postflight(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        manifest = {
            "artifact_class": "a0x-public-closure-manifest", "profile": "a0x-public-closure-manifest-v1",
            "schema_version": 1,
            **{key: self.identity[key] for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256")},
            "pre_execution_extension_sha256": _sha(self.extension_raw),
            "terminal_projection_sha256": _sha(terminal),
            "outer_postflight_projection_sha256": _sha(postflight),
            "private_original_sha256": private_originals,
            "claims": {"document_bindings_consistent": True, "derivation_authenticated": False,
                       "operator_approval_authenticated": False, "authorization_verified": False,
                       "publication_eligible": False},
        }
        with self.assertRaises(A0XPublicClosureError):
            verify_public_terminal_closure(
                _canonical(manifest), pre_execution_extension_raw=self.extension_raw,
                terminal_projection_raw=terminal, outer_postflight_projection_raw=postflight + b" ",
                public_role_bytes=self.public_roles,
                expected_identity=self.identity,
            )

    def test_terminal_verifier_rejects_unknown_fields_and_claim_promotion(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        base = {
            "artifact_class": "a0x-public-closure-manifest", "profile": "a0x-public-closure-manifest-v1",
            "schema_version": 1,
            **{key: self.identity[key] for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256")},
            "pre_execution_extension_sha256": _sha(self.extension_raw),
            "terminal_projection_sha256": _sha(terminal),
            "outer_postflight_projection_sha256": _sha(postflight),
            "private_original_sha256": private_originals,
            "claims": {"document_bindings_consistent": True, "derivation_authenticated": False,
                       "operator_approval_authenticated": False, "authorization_verified": False,
                       "publication_eligible": False},
        }
        for key, value in (("unreviewed_assertion", True), ("claims", {
            "document_bindings_consistent": True, "derivation_authenticated": True,
            "operator_approval_authenticated": False, "authorization_verified": False,
            "publication_eligible": False,
        })):
            candidate = dict(base)
            candidate[key] = value
            with self.subTest(field=key), self.assertRaises(A0XPublicClosureError):
                verify_public_terminal_closure(
                    _canonical(candidate), pre_execution_extension_raw=self.extension_raw,
                    terminal_projection_raw=terminal, outer_postflight_projection_raw=postflight,
                    public_role_bytes=self.public_roles,
                    expected_identity=self.identity,
                )

    def test_terminal_verifier_rejects_rebound_extension_claim_promotion(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        extension = json.loads(self.extension_raw)
        extension["claims"]["operator_approval_authenticated"] = True
        extension_raw = _canonical(extension)
        manifest = self._terminal_manifest(private_originals, terminal, postflight, extension_raw)
        with self.assertRaises(A0XPublicClosureError):
            verify_public_terminal_closure(
                _canonical(manifest), pre_execution_extension_raw=extension_raw,
                terminal_projection_raw=terminal, outer_postflight_projection_raw=postflight,
                public_role_bytes=self.public_roles, expected_identity=self.identity,
            )

    def test_terminal_verifier_rejects_rebound_extension_extra_field(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        extension = json.loads(self.extension_raw)
        extension["unreviewed"] = True
        extension_raw = _canonical(extension)
        manifest = self._terminal_manifest(private_originals, terminal, postflight, extension_raw)
        with self.assertRaises(A0XPublicClosureError):
            verify_public_terminal_closure(
                _canonical(manifest), pre_execution_extension_raw=extension_raw,
                terminal_projection_raw=terminal, outer_postflight_projection_raw=postflight,
                public_role_bytes=self.public_roles, expected_identity=self.identity,
            )

    def test_terminal_verifier_rejects_synthetic_profile_extension(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        extension = json.loads(self.extension_raw)
        extension["profile"] = "a0x-public-evidence-closure-experimental-v1"
        extension_raw = _canonical(extension)
        manifest = self._terminal_manifest(private_originals, terminal, postflight, extension_raw)
        with self.assertRaises(A0XPublicClosureError):
            verify_public_terminal_closure(
                _canonical(manifest), pre_execution_extension_raw=extension_raw,
                terminal_projection_raw=terminal, outer_postflight_projection_raw=postflight,
                public_role_bytes=self.public_roles, expected_identity=self.identity,
            )

    def test_terminal_verifier_rejects_boolean_schema_version_and_outcome_mismatch(self) -> None:
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        for mutation in (
            lambda value: value.__setitem__("schema_version", True),
            lambda value: value.__setitem__("completion_classification", "completed"),
        ):
            candidate_terminal = json.loads(terminal)
            mutation(candidate_terminal)
            candidate_raw = _canonical(candidate_terminal)
            manifest = self._terminal_manifest(private_originals, candidate_raw, postflight, self.extension_raw)
            with self.subTest(value=candidate_terminal), self.assertRaises(A0XPublicClosureError):
                verify_public_terminal_closure(
                    _canonical(manifest), pre_execution_extension_raw=self.extension_raw,
                    terminal_projection_raw=candidate_raw, outer_postflight_projection_raw=postflight,
                    public_role_bytes=self.public_roles, expected_identity=self.identity,
                )

    def _terminal_projections(self, private_originals: dict[str, str]) -> tuple[bytes, bytes]:
        identity = {key: self.identity[key] for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id")}
        terminal = _canonical({
            "artifact_class": "a0x-public-terminal-projection",
            "profile": "a0x-public-terminal-projection-v1", "schema_version": 1,
            **identity,
            "original_raw_sha256": private_originals["terminal_original"],
            "terminal_outcome": "failed", "completion_classification": "failed",
            "execution_assertions_only": True,
        })
        outer = _canonical({
            "artifact_class": "a0x-public-outer-postflight-projection",
            "profile": "a0x-public-outer-postflight-projection-v1", "schema_version": 1,
            **identity,
            "original_raw_sha256": private_originals["outer_postflight_original"],
            "admission_inactive": False, "runtime_clean": False, "cleanup_status": "uncertain",
        })
        return terminal, outer

    def _terminal_manifest(self, private_originals, terminal, postflight, extension_raw):
        return {
            "artifact_class": "a0x-public-closure-manifest",
            "profile": "a0x-public-closure-manifest-v1",
            "schema_version": 1,
            **{key: self.identity[key] for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256")},
            "pre_execution_extension_sha256": _sha(extension_raw),
            "terminal_projection_sha256": _sha(terminal),
            "outer_postflight_projection_sha256": _sha(postflight),
            "private_original_sha256": private_originals,
            "claims": {
                "document_bindings_consistent": True,
                "derivation_authenticated": False,
                "operator_approval_authenticated": False,
                "authorization_verified": False,
                "publication_eligible": False,
            },
        }

    def _write_closure(self, repository: Path) -> Path:
        relative = (
            "experiments/a0x-six-model/vertical-slices/"
            f"{self.identity['qualified_source']['head']}/a0/smollm2_360m/public-closure/v1"
        )
        root = repository / relative
        for role, path in PRE_EXECUTION_PUBLIC_ROLE_PATHS.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.public_roles[role])
        extension_path = root / PRE_EXECUTION_EXTENSION_PATH
        extension_path.parent.mkdir(parents=True, exist_ok=True)
        extension_path.write_bytes(self.extension_raw)
        return root

    def _write_terminal_closure(self, repository: Path) -> Path:
        root = self._write_closure(repository)
        private_originals = {"terminal_original": "8" * 64, "outer_postflight_original": "9" * 64}
        terminal, postflight = self._terminal_projections(private_originals)
        terminal_path = root / TERMINAL_CLOSURE_ROLE_PATHS["terminal_projection"]
        terminal_path.parent.mkdir(parents=True, exist_ok=True)
        terminal_path.write_bytes(terminal)
        postflight_path = root / TERMINAL_CLOSURE_ROLE_PATHS["outer_postflight_projection"]
        postflight_path.parent.mkdir(parents=True, exist_ok=True)
        postflight_path.write_bytes(postflight)
        manifest = self._terminal_manifest(private_originals, terminal, postflight, self.extension_raw)
        (root / TERMINAL_CLOSURE_MANIFEST_PATH).write_bytes(_canonical(manifest))
        return root

    def _rewrite_extension_after_role_change(self, root: Path) -> None:
        roles = {
            role: (root / path).read_bytes()
            for role, path in PRE_EXECUTION_PUBLIC_ROLE_PATHS.items()
        }
        value = json.loads(self.extension_raw)
        value["bindings"]["public_role_sha256"] = {role: _sha(raw) for role, raw in roles.items()}
        (root / PRE_EXECUTION_EXTENSION_PATH).write_bytes(_canonical(value))


if __name__ == "__main__":
    unittest.main()
