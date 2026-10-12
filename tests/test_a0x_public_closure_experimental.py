from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import latent_triz.a0x_public_closure_experimental as closure_module
from latent_triz.a0x_public_closure_experimental import (
    A0XExperimentalPublicClosureError,
    ROLE_PATHS,
    build_synthetic_authorization_extension,
    verify_experimental_public_closure,
)


def _canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class A0XExperimentalPublicClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(tempfile.gettempdir()).resolve())
        self.root = Path(self.temp.name) / "fresh-package"
        self.root.mkdir()
        self.head = "1" * 40
        self.tree = "2" * 40
        self.pair = {"leg": "a0", "model_key": "synthetic_model", "model_id": "synthetic/model", "revision": "3" * 40}
        self.auth_id = "synthetic-auth-01"
        self.attempt_id = "synthetic-attempt-01"
        self.docs, self.manifest = self._fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _fixture(self):
        safe_names = ("protocol.json", "implementation.json", "freeze.json", "slice-manifest.json")
        safe_values = {
            "protocol.json": {"artifact_class": "synthetic-p0-protocol", "synthetic_only": True, "identity": {"leg": "a0", "protocol_id": "synthetic-a0-v1"}},
            "implementation.json": {"artifact_class": "synthetic-p0-implementation", "synthetic_only": True, "identity": {"leg": "a0", "protocol_id": "synthetic-a0-v1"}},
            "freeze.json": {"artifact_class": "synthetic-p0-freeze", "synthetic_only": True, "identity": {"leg": "a0", "protocol_id": "synthetic-a0-v1"}},
            "slice-manifest.json": {"artifact_class": "synthetic-p0-slice-manifest", "synthetic_only": True, "implementation_source_head": self.head, "implementation_source_tree": self.tree, "pair": self.pair},
        }
        raw_dossier = _canonical({"runtime_authorization_path": ".a0x-runtime/authorizations/private.json"})
        safe_raw = {name: _canonical(safe_values[name]) for name in safe_names}
        commitment_projection = {
            "profile": "a0x-vertical-package-commitment-v2",
            "qualified_source": {"head": self.head, "tree": self.tree, "ref": "refs/heads/main"},
            "pair_binding": self.pair,
            "members": [
                {"name": name, "size": len(raw), "sha256": _sha(raw)}
                for name, raw in (
                    ("protocol.json", safe_raw["protocol.json"]),
                    ("implementation.json", safe_raw["implementation.json"]),
                    ("freeze.json", safe_raw["freeze.json"]),
                    ("approval-dossier.json", raw_dossier),
                    ("slice-manifest.json", safe_raw["slice-manifest.json"]),
                )
            ],
            "generator": {"profile": "a0x-vertical-slice-v2", "repository": "MarcoPorcellato/Latent-TRIZ"},
            "authorization_id": self.auth_id,
            "attempt_id": self.attempt_id,
        }
        commitment_hash = _sha(b"A0X-VERTICAL-PACKAGE-COMMITMENT-V2\\x00" + _canonical(commitment_projection)[:-1])
        commitment = {**commitment_projection, "package_commitment_sha256": commitment_hash}
        identity = {"source": {"head": self.head, "tree": self.tree}, "pair_binding": self.pair, "authorization_id": self.auth_id, "attempt_id": self.attempt_id}
        private_hashes = {"authorization": "8" * 64, "readiness": "9" * 64, "terminal": "a" * 64, "outer_postflight": "b" * 64}
        docs = {
            "p0_commitment": commitment,
            "p0_protocol": safe_values["protocol.json"],
            "p0_implementation": safe_values["implementation.json"],
            "p0_freeze": safe_values["freeze.json"],
            "p0_slice_manifest": safe_values["slice-manifest.json"],
            "p0_dossier_projection": {"profile": "a0x-public-dossier-projection-v1", **identity, "original_raw_sha256": _sha(raw_dossier), "contents": {"public_safe": True}},
            "public_execution_spec": {"profile": "a0x-public-execution-spec-v1", **identity, "requirements": ["synthetic-only"]},
            "gate_a_evidence": {"profile": "synthetic-gate-a-evidence-v1", **identity, "run_id": "synthetic-run-01", "attempt": 1},
            "gate_a_attestation_bundle": {"profile": "synthetic-attestation-bundle-v1", **identity, "run_id": "synthetic-run-01"},
            "gate_a_trusted_root": {"profile": "synthetic-trusted-root-v1", **identity},
            "gate_a_transport": {"profile": "synthetic-gate-a-transport-v1", **identity, "artifact_id": "synthetic-artifact-01"},
            "gate_b_authorization_projection": {"profile": "a0x-public-gate-b-authorization-projection-v1", **identity, "source_raw_sha256": private_hashes["authorization"]},
            "gate_b_readiness_projection": {"profile": "a0x-public-gate-b-readiness-projection-v1", **identity, "source_raw_sha256": private_hashes["readiness"]},
            "terminal_projection": {"profile": "a0x-public-terminal-projection-v1", **identity, "source_raw_sha256": private_hashes["terminal"]},
            "outer_postflight_projection": {"profile": "a0x-public-outer-postflight-projection-v1", **identity, "source_raw_sha256": private_hashes["outer_postflight"]},
        }
        raw_by_role = {"p0_commitment": _canonical(commitment)}
        for name, role in (("protocol.json", "p0_protocol"), ("implementation.json", "p0_implementation"), ("freeze.json", "p0_freeze"), ("slice-manifest.json", "p0_slice_manifest")):
            raw_by_role[role] = safe_raw[name]
        for role, document in docs.items():
            if role != "p0_commitment":
                raw_by_role[role] = _canonical(document)
        auth_bindings = {
            "p0_commitment_sha256": _sha(raw_by_role["p0_commitment"]),
            "p0_package_commitment_sha256": commitment_hash,
            "p0_dossier_raw_sha256": _sha(raw_dossier),
            "p0_dossier_projection_sha256": _sha(raw_by_role["p0_dossier_projection"]),
            "execution_spec_sha256": _sha(raw_by_role["public_execution_spec"]),
            "gate_a_role_sha256": {role: _sha(raw_by_role[role]) for role in ("gate_a_evidence", "gate_a_attestation_bundle", "gate_a_trusted_root", "gate_a_transport")},
            "gate_b_private_v4_sha256": {"authorization": private_hashes["authorization"], "readiness": private_hashes["readiness"]},
            "gate_b_projection_sha256": {role: _sha(raw_by_role[role]) for role in ("gate_b_authorization_projection", "gate_b_readiness_projection")},
        }
        docs["authorization_extension"] = build_synthetic_authorization_extension(identity, auth_bindings)
        raw_by_role["authorization_extension"] = _canonical(docs["authorization_extension"])
        for role, raw in raw_by_role.items():
            path = self.root / ROLE_PATHS[role]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        manifest = {
            "artifact_class": "a0x-experimental-public-evidence-closure",
            "profile": "a0x-public-evidence-closure-experimental-v1",
            "synthetic_only": True,
            **identity,
            "p0_package_commitment_sha256": commitment_hash,
            "post_execution_bindings": {
                "authorization_extension_sha256": _sha(raw_by_role["authorization_extension"]),
                "terminal_projection_sha256": _sha(raw_by_role["terminal_projection"]),
                "terminal_private_raw_sha256": private_hashes["terminal"],
                "outer_postflight_projection_sha256": _sha(raw_by_role["outer_postflight_projection"]),
                "outer_postflight_private_raw_sha256": private_hashes["outer_postflight"],
            },
            "roles": [{"role": role, "path": ROLE_PATHS[role], "bytes": len(raw_by_role[role]), "raw_sha256": _sha(raw_by_role[role])} for role in ROLE_PATHS],
        }
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))
        return docs, manifest

    def test_fresh_package_verifies_only_bytes_and_internal_bindings(self) -> None:
        result = verify_experimental_public_closure(self.root)
        self.assertTrue(result.bytes_verified)
        self.assertTrue(result.document_bindings_consistent)
        self.assertFalse(result.derivation_authenticated)
        self.assertFalse(result.authorization_verified)
        self.assertFalse(result.operator_approval_authenticated)
        self.assertFalse(result.gate_a_attestation_verified)
        self.assertTrue(result.execution_assertions_only)
        self.assertFalse(result.publication_eligible)

    def test_authorization_extension_is_pre_execution_only(self) -> None:
        extension = json.loads((self.root / ROLE_PATHS["authorization_extension"]).read_bytes())
        terminal_files = [self.root / ROLE_PATHS[role] for role in ("terminal_projection", "outer_postflight_projection")]
        saved = [path.read_bytes() for path in terminal_files]
        try:
            for path in terminal_files:
                path.unlink()
            pre_execution_bindings = {key: value for key, value in extension["bindings"].items()}
            commitment_raw = (self.root / ROLE_PATHS["p0_commitment"]).read_bytes()
            commitment = json.loads(commitment_raw)
            pre_roles = {
                "authorization_extension", "p0_dossier_projection", "public_execution_spec",
                "gate_a_evidence", "gate_a_attestation_bundle", "gate_a_trusted_root",
                "gate_a_transport", "gate_b_authorization_projection", "gate_b_readiness_projection",
            }
            pre_documents = {role: json.loads((self.root / ROLE_PATHS[role]).read_bytes()) for role in pre_roles}
            pre_raw = {role: (self.root / ROLE_PATHS[role]).read_bytes() for role in pre_roles}
            pre_raw["p0_commitment"] = commitment_raw
            dossier_hash = next(item["sha256"] for item in commitment["members"] if item["name"] == "approval-dossier.json")
            closure_module._validate_authorization_extension(
                pre_documents, pre_raw,
                {key: extension[key] for key in ("source", "pair_binding", "authorization_id", "attempt_id")},
                dossier_hash, commitment,
            )
            rebuilt = build_synthetic_authorization_extension(
                {key: extension[key] for key in ("source", "pair_binding", "authorization_id", "attempt_id")},
                pre_execution_bindings,
            )
            self.assertFalse(any(path.exists() for path in terminal_files))
            self.assertEqual(rebuilt, extension)
            forbidden = {"terminal_projection_sha256", "terminal_private_raw_sha256", "outer_postflight_projection_sha256", "outer_postflight_private_raw_sha256"}
            self.assertFalse(forbidden.intersection(rebuilt["bindings"]))
        finally:
            for path, raw in zip(terminal_files, saved, strict=True):
                path.write_bytes(raw)

    def test_rejects_future_output_fields_in_authorization_extension(self) -> None:
        value = json.loads((self.root / ROLE_PATHS["authorization_extension"]).read_bytes())
        value["bindings"]["terminal_projection_sha256"] = "a" * 64
        self._rewrite_role_and_manifest("authorization_extension", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_manifest_binds_post_execution_projections_and_private_raw_sources(self) -> None:
        manifest = json.loads((self.root / "closure-manifest.json").read_bytes())
        post = manifest["post_execution_bindings"]
        self.assertEqual(post["authorization_extension_sha256"], _sha((self.root / ROLE_PATHS["authorization_extension"]).read_bytes()))
        for role, projected, source in (
            ("terminal_projection", "terminal_projection_sha256", "terminal_private_raw_sha256"),
            ("outer_postflight_projection", "outer_postflight_projection_sha256", "outer_postflight_private_raw_sha256"),
        ):
            document = json.loads((self.root / ROLE_PATHS[role]).read_bytes())
            self.assertEqual(post[projected], _sha((self.root / ROLE_PATHS[role]).read_bytes()))
            self.assertEqual(post[source], document["source_raw_sha256"])
        post["terminal_private_raw_sha256"] = "f" * 64
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def _rewrite_role_and_manifest(self, role: str, value: object) -> None:
        raw = _canonical(value)
        path = self.root / ROLE_PATHS[role]
        path.write_bytes(raw)
        manifest = json.loads((self.root / "closure-manifest.json").read_bytes())
        entry = next(item for item in manifest["roles"] if item["role"] == role)
        entry["bytes"] = len(raw)
        entry["raw_sha256"] = _sha(raw)
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))

    def _rebind_p0_member(self, role: str, value: object) -> None:
        raw = _canonical(value)
        name = {"p0_protocol": "protocol.json", "p0_implementation": "implementation.json", "p0_freeze": "freeze.json", "p0_slice_manifest": "slice-manifest.json"}[role]
        member_path = self.root / ROLE_PATHS[role]
        member_path.write_bytes(raw)
        commitment_path = self.root / ROLE_PATHS["p0_commitment"]
        commitment = json.loads(commitment_path.read_bytes())
        member = next(item for item in commitment["members"] if item["name"] == name)
        member["size"] = len(raw)
        member["sha256"] = _sha(raw)
        projection = {key: item for key, item in commitment.items() if key != "package_commitment_sha256"}
        commitment["package_commitment_sha256"] = _sha(b"A0X-VERTICAL-PACKAGE-COMMITMENT-V2\\x00" + _canonical(projection)[:-1])
        commitment_raw = _canonical(commitment)
        commitment_path.write_bytes(commitment_raw)
        manifest_path = self.root / "closure-manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        for entry in manifest["roles"]:
            if entry["role"] == role:
                entry.update({"bytes": len(raw), "raw_sha256": _sha(raw)})
            elif entry["role"] == "p0_commitment":
                entry.update({"bytes": len(commitment_raw), "raw_sha256": _sha(commitment_raw)})
        manifest["p0_package_commitment_sha256"] = commitment["package_commitment_sha256"]
        extension_path = self.root / ROLE_PATHS["authorization_extension"]
        extension = json.loads(extension_path.read_bytes())
        extension["bindings"]["p0_commitment_sha256"] = _sha(commitment_raw)
        extension["bindings"]["p0_package_commitment_sha256"] = commitment["package_commitment_sha256"]
        extension_raw = _canonical(extension)
        extension_path.write_bytes(extension_raw)
        next(entry for entry in manifest["roles"] if entry["role"] == "authorization_extension").update({"bytes": len(extension_raw), "raw_sha256": _sha(extension_raw)})
        manifest_path.write_bytes(_canonical(manifest))

    def test_rejects_missing_role(self) -> None:
        (self.root / ROLE_PATHS["gate_a_transport"]).unlink()
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_every_missing_role_file_and_manifest_entry(self) -> None:
        import shutil

        for role, relative in ROLE_PATHS.items():
            for missing_file in (True, False):
                with self.subTest(role=role, missing_file=missing_file):
                    clone = Path(self.temp.name) / f"missing-{role}-{missing_file}"
                    shutil.copytree(self.root, clone)
                    if missing_file:
                        (clone / relative).unlink()
                    else:
                        manifest_path = clone / "closure-manifest.json"
                        manifest = json.loads(manifest_path.read_bytes())
                        manifest["roles"] = [entry for entry in manifest["roles"] if entry["role"] != role]
                        manifest_path.write_bytes(_canonical(manifest))
                    with self.assertRaises(A0XExperimentalPublicClosureError):
                        verify_experimental_public_closure(clone)
                    shutil.rmtree(clone)

    def test_rejects_manifest_role_omission(self) -> None:
        manifest = json.loads((self.root / "closure-manifest.json").read_bytes())
        manifest["roles"].pop()
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_synthetic_only_false(self) -> None:
        manifest = json.loads((self.root / "closure-manifest.json").read_bytes())
        manifest["synthetic_only"] = False
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_non_synthetic_identifiers(self) -> None:
        value = json.loads((self.root / ROLE_PATHS["gate_a_evidence"]).read_bytes())
        value["run_id"] = "33986455529"
        self._rewrite_role_and_manifest("gate_a_evidence", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_non_synthetic_authorization_and_attempt_ids(self) -> None:
        manifest_path = self.root / "closure-manifest.json"
        original = manifest_path.read_bytes()
        manifest = json.loads(original)
        manifest["authorization_id"] = "operator-approved-01"
        manifest_path.write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_non_synthetic_artifact_identifier(self) -> None:
        value = json.loads((self.root / ROLE_PATHS["gate_a_transport"]).read_bytes())
        value["artifact_id"] = "9873481955"
        self._rewrite_role_and_manifest("gate_a_transport", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_promotion_attempt_for_each_prohibited_status(self) -> None:
        prohibited = (
            "derivation_authenticated", "authorization_verified",
            "operator_approval_authenticated", "gate_a_attestation_verified",
            "publication_eligible",
        )
        role_path = self.root / ROLE_PATHS["public_execution_spec"]
        manifest_path = self.root / "closure-manifest.json"
        baseline_role = role_path.read_bytes()
        baseline_manifest = manifest_path.read_bytes()
        for field in prohibited:
            with self.subTest(field=field):
                value = json.loads(baseline_role)
                value[field] = True
                self._rewrite_role_and_manifest("public_execution_spec", value)
                with self.assertRaises(A0XExperimentalPublicClosureError):
                    verify_experimental_public_closure(self.root)
                role_path.write_bytes(baseline_role)
                manifest_path.write_bytes(baseline_manifest)

    def test_rejects_extra_pair_claim_and_private_pair_string(self) -> None:
        manifest = json.loads((self.root / "closure-manifest.json").read_bytes())
        manifest["pair_binding"]["account_path"] = "/Users/private"
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_non_synthetic_pair_values(self) -> None:
        manifest_path = self.root / "closure-manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["pair_binding"]["model_id"] = "HuggingFaceTB/SmolLM2-360M"
        manifest_path.write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_extra_role_file(self) -> None:
        (self.root / "unexpected.json").write_bytes(b"{}\n")
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_role_mutation_even_when_file_remains_canonical(self) -> None:
        path = self.root / ROLE_PATHS["public_execution_spec"]
        value = json.loads(path.read_bytes())
        value["requirements"].append("mutated")
        path.write_bytes(_canonical(value))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_noncanonical_role_json_even_with_updated_manifest_hash(self) -> None:
        path = self.root / ROLE_PATHS["public_execution_spec"]
        value = json.loads(path.read_bytes())
        raw = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
        path.write_bytes(raw)
        manifest = json.loads((self.root / "closure-manifest.json").read_bytes())
        entry = next(item for item in manifest["roles"] if item["role"] == "public_execution_spec")
        entry["bytes"] = len(raw)
        entry["raw_sha256"] = _sha(raw)
        (self.root / "closure-manifest.json").write_bytes(_canonical(manifest))
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_extension_cross_binding_drift_after_role_hash_is_updated(self) -> None:
        path = self.root / ROLE_PATHS["authorization_extension"]
        value = json.loads(path.read_bytes())
        value["bindings"]["p0_dossier_raw_sha256"] = "a" * 64
        self._rewrite_role_and_manifest("authorization_extension", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_private_path_in_projection(self) -> None:
        path = self.root / ROLE_PATHS["p0_dossier_projection"]
        value = json.loads(path.read_bytes())
        value["contents"]["path"] = ".a0x-runtime/private.json"
        self._rewrite_role_and_manifest("p0_dossier_projection", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_private_file_uri_in_projection(self) -> None:
        path = self.root / ROLE_PATHS["p0_dossier_projection"]
        value = json.loads(path.read_bytes())
        value["contents"]["source"] = "file:///Users/marco1/private.json"
        self._rewrite_role_and_manifest("p0_dossier_projection", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_attempt_to_promote_publication_status(self) -> None:
        value = json.loads((self.root / ROLE_PATHS["public_execution_spec"]).read_bytes())
        value["publication_eligible"] = True
        self._rewrite_role_and_manifest("public_execution_spec", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_rejects_hardlinked_member(self) -> None:
        source = self.root / ROLE_PATHS["p0_protocol"]
        alias = Path(self.temp.name) / "outside-alias.bin"
        os.link(source, alias)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)

    def test_enforces_byte_cap_during_streamed_read(self) -> None:
        real_read = os.read
        injected = False

        def oversized_read(fd: int, size: int) -> bytes:
            nonlocal injected
            data = real_read(fd, size)
            if data and not injected:
                injected = True
                return data + b"x" * (64 * 1024)
            return data

        with patch.object(closure_module, "_MAX_ROLE_BYTES", 32 * 1024), patch.object(closure_module.os, "read", side_effect=oversized_read):
            with self.assertRaisesRegex(A0XExperimentalPublicClosureError, "while reading"):
                verify_experimental_public_closure(self.root)

    def test_rechecks_link_count_after_read(self) -> None:
        real_read = os.read
        target = self.root / ROLE_PATHS["p0_protocol"]
        alias = Path(self.temp.name) / "late-hardlink.bin"
        linked = False

        def link_during_read(fd: int, size: int) -> bytes:
            nonlocal linked
            data = real_read(fd, size)
            if not linked and os.fstat(fd).st_ino == target.stat().st_ino:
                linked = True
                os.link(target, alias)
            return data

        try:
            with patch.object(closure_module.os, "read", side_effect=link_during_read):
                with self.assertRaisesRegex(A0XExperimentalPublicClosureError, "changed while reading"):
                    verify_experimental_public_closure(self.root)
        finally:
            alias.unlink(missing_ok=True)

    def test_rechecks_role_path_inode_after_read(self) -> None:
        real_read = os.read
        target = self.root / ROLE_PATHS["p0_protocol"]
        replacement = Path(self.temp.name) / "replacement.bin"
        replacement.write_bytes(target.read_bytes())
        replaced = False

        def replace_during_read(fd: int, size: int) -> bytes:
            nonlocal replaced
            data = real_read(fd, size)
            if not replaced and os.fstat(fd).st_ino == target.stat().st_ino:
                replaced = True
                os.replace(replacement, target)
            return data

        with patch.object(closure_module.os, "read", side_effect=replace_during_read):
            with self.assertRaisesRegex(A0XExperimentalPublicClosureError, "changed while reading"):
                verify_experimental_public_closure(self.root)

    def test_rejects_rebound_p0_slice_manifest_with_wrong_source(self) -> None:
        value = json.loads((self.root / ROLE_PATHS["p0_slice_manifest"]).read_bytes())
        value["implementation_source_head"] = "f" * 40
        self._rebind_p0_member("p0_slice_manifest", value)
        with self.assertRaises(A0XExperimentalPublicClosureError):
            verify_experimental_public_closure(self.root)
