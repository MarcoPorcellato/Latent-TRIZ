"""Synthetic-only public evidence closure verifier for the A0X B04 spike.

This module is deliberately not imported by a production entrypoint. A passing
result proves canonical package bytes and internal document consistency only;
it does not authenticate derivation, authorization, operator approval, Gate A
attestation, execution, scientific findings, or publication eligibility.
Its P0 checks accept only a bounded synthetic fixture shape; they make no
claim of compatibility with the full production P0 package contract.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

from .a0x_validator import validate as validate_schema


PROFILE = "a0x-public-evidence-closure-experimental-v1"
_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "a0x-public-closure-experimental-v1.schema.json"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_HEAD = re.compile(r"^[a-f0-9]{40}$")
_PAIR_FIELDS = frozenset({"leg", "model_key", "model_id", "revision"})
_SYNTHETIC_ID = re.compile(r"^synthetic-[a-z0-9][a-z0-9-]{0,62}$")
_SYNTHETIC_PAIR = {
    "leg": "a0",
    "model_key": "synthetic_model",
    "model_id": "synthetic/model",
    "revision": "3" * 40,
}
_P0_MEMBER_NAMES = (
    "protocol.json", "implementation.json", "freeze.json",
    "approval-dossier.json", "slice-manifest.json",
)
_COMMITMENT_DOMAIN = b"A0X-VERTICAL-PACKAGE-COMMITMENT-V2\\x00"
_FORBIDDEN_STATUS_VALUES = {
    "derivation_authenticated": False,
    "authorization_verified": False,
    "operator_approval_authenticated": False,
    "gate_a_attestation_verified": False,
    "publication_eligible": False,
}
_PRIVATE_MARKERS = (
    ".a0x-runtime", "runtime_authorization_path", "runtime-mapping.json",
)
_ABSOLUTE_PRIVATE_PATH = re.compile(r"/(?:Users|private/(?:tmp|var)|var/folders)/", re.IGNORECASE)
_MAX_ROLE_BYTES = 8 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024

# Ordered mapping is part of this experimental wire profile. It is not a
# production trust allowlist and must not be imported by production callers.
ROLE_PATHS: Mapping[str, str] = MappingProxyType({
    "p0_commitment": "p0/commitment.json",
    "p0_protocol": "p0/protocol.json",
    "p0_implementation": "p0/implementation.json",
    "p0_freeze": "p0/freeze.json",
    "p0_slice_manifest": "p0/slice-manifest.json",
    "p0_dossier_projection": "p0/dossier-projection.json",
    "public_execution_spec": "execution/public-spec.json",
    "authorization_extension": "authorization/extension-v1.json",
    "gate_a_evidence": "gate-a/evidence.json",
    "gate_a_attestation_bundle": "gate-a/attestation.bundle.jsonl",
    "gate_a_trusted_root": "gate-a/trusted-root.jsonl",
    "gate_a_transport": "gate-a/transport.json",
    "gate_b_authorization_projection": "gate-b/authorization-projection.json",
    "gate_b_readiness_projection": "gate-b/readiness-projection.json",
    "terminal_projection": "terminal/terminal-projection.json",
    "outer_postflight_projection": "terminal/outer-postflight-projection.json",
})


class A0XExperimentalPublicClosureError(ValueError):
    """The synthetic public closure is incomplete, inconsistent, or unsafe."""


@dataclass(frozen=True)
class ExperimentalPublicClosureStatus:
    bytes_verified: bool
    document_bindings_consistent: bool
    derivation_authenticated: bool
    authorization_verified: bool
    operator_approval_authenticated: bool
    gate_a_attestation_verified: bool
    execution_assertions_only: bool
    publication_eligible: bool
    manifest_sha256: str
    role_count: int


def verify_experimental_public_closure(
    package_root: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str | None = None,
) -> ExperimentalPublicClosureStatus:
    """Verify a fresh synthetic package; never promote its evidence status.

    ``expected_manifest_sha256`` is an optional caller-supplied byte pin. It
    still authenticates no issuer or derivation. Caller must ensure no untrusted
    concurrent same-user mutation of the package directory during verification;
    descriptor checks detect ordinary replacement but do not claim race-proof
    isolation against a hostile same-user process. All members must be
    independent regular files with no symlink in their path components.
    """
    root = Path(package_root).absolute()
    _check_directory_path(root)
    manifest_raw = _read_independent(root, "closure-manifest.json")
    manifest_hash = _sha256(manifest_raw)
    if expected_manifest_sha256 is not None and _valid_sha(expected_manifest_sha256) != manifest_hash:
        raise A0XExperimentalPublicClosureError("closure manifest digest differs from caller pin")
    manifest = _canonical_json_object(manifest_raw, "closure manifest")
    _validate_manifest_schema(manifest)
    if manifest.get("profile") != PROFILE or manifest.get("synthetic_only") is not True:
        raise A0XExperimentalPublicClosureError("only the explicit synthetic experimental profile is accepted")
    _reject_status_promotion(manifest)
    _reject_private_content(manifest_raw, "closure manifest")

    role_entries = manifest["roles"]
    if len(role_entries) != len(ROLE_PATHS):
        raise A0XExperimentalPublicClosureError("role set cardinality differs")
    expected_roles = tuple(ROLE_PATHS.items())
    _verify_exact_tree(root)
    role_raw: dict[str, bytes] = {}
    role_documents: dict[str, dict[str, Any]] = {}
    for entry, (expected_role, expected_path) in zip(role_entries, expected_roles, strict=True):
        if entry["role"] != expected_role or entry["path"] != expected_path:
            raise A0XExperimentalPublicClosureError("role allowlist or canonical order differs")
        _safe_relative_path(entry["path"])
        raw = _read_independent(root, entry["path"])
        if len(raw) != entry["bytes"] or _sha256(raw) != _valid_sha(entry["raw_sha256"]):
            raise A0XExperimentalPublicClosureError(f"role bytes or digest differ: {expected_role}")
        _reject_private_content(raw, expected_role)
        role_raw[expected_role] = raw
        if expected_role in {"gate_a_attestation_bundle", "gate_a_trusted_root"}:
            role_documents[expected_role] = _canonical_jsonl_object(raw, expected_role)
        else:
            role_documents[expected_role] = _canonical_json_object(raw, expected_role)
        _reject_status_promotion(role_documents[expected_role])

    if sum(map(len, role_raw.values())) > _MAX_TOTAL_BYTES:
        raise A0XExperimentalPublicClosureError("closure package exceeds total byte limit")

    identity = _identity(manifest)
    commitment = _validate_p0_commitment(role_documents["p0_commitment"])
    if commitment["qualified_source"]["head"] != identity["source"]["head"] or commitment["qualified_source"]["tree"] != identity["source"]["tree"]:
        raise A0XExperimentalPublicClosureError("P0 commitment source differs from closure identity")
    if commitment["pair_binding"] != identity["pair_binding"]:
        raise A0XExperimentalPublicClosureError("P0 commitment pair differs from closure identity")
    if commitment["authorization_id"] != identity["authorization_id"] or commitment["attempt_id"] != identity["attempt_id"]:
        raise A0XExperimentalPublicClosureError("P0 commitment attempt identity differs")
    if commitment["package_commitment_sha256"] != manifest["p0_package_commitment_sha256"]:
        raise A0XExperimentalPublicClosureError("P0 package commitment digest differs")

    member_by_name = {member["name"]: member for member in commitment["members"]}
    safe_roles = {
        "p0_protocol": "protocol.json",
        "p0_implementation": "implementation.json",
        "p0_freeze": "freeze.json",
        "p0_slice_manifest": "slice-manifest.json",
    }
    p0_member_documents: dict[str, Mapping[str, Any]] = {}
    for role, name in safe_roles.items():
        raw = role_raw[role]
        committed = member_by_name[name]
        if len(raw) != committed["size"] or _sha256(raw) != committed["sha256"]:
            raise A0XExperimentalPublicClosureError(f"exact P0 member differs from commitment: {name}")
        p0_member_documents[role] = role_documents[role]
    _check_synthetic_p0_member_semantics(p0_member_documents, identity)

    dossier_digest = member_by_name["approval-dossier.json"]["sha256"]
    dossier_projection = role_documents["p0_dossier_projection"]
    _check_document_identity(dossier_projection, identity, "P0 dossier projection")
    if dossier_projection.get("profile") != "a0x-public-dossier-projection-v1" or dossier_projection.get("original_raw_sha256") != dossier_digest:
        raise A0XExperimentalPublicClosureError("dossier projection does not reference the committed raw dossier")

    for role, document in role_documents.items():
        if role in {"p0_commitment", "p0_protocol", "p0_implementation", "p0_freeze", "p0_slice_manifest"}:
            continue
        _check_document_identity(document, identity, role)
    _validate_closed_roles(role_documents)
    _validate_authorization_extension(role_documents, role_raw, identity, dossier_digest, commitment)
    _validate_post_execution_bindings(manifest, role_documents, role_raw)

    return ExperimentalPublicClosureStatus(
        bytes_verified=True,
        document_bindings_consistent=True,
        derivation_authenticated=False,
        authorization_verified=False,
        operator_approval_authenticated=False,
        gate_a_attestation_verified=False,
        execution_assertions_only=True,
        publication_eligible=False,
        manifest_sha256=manifest_hash,
        role_count=len(role_raw),
    )


def _validate_manifest_schema(value: Mapping[str, Any]) -> None:
    try:
        schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise A0XExperimentalPublicClosureError("experimental closure schema unavailable or invalid") from error
    issues = validate_schema(dict(value), schema)
    if issues:
        raise A0XExperimentalPublicClosureError("closure manifest fails experimental schema")


def _validate_p0_commitment(value: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "profile", "qualified_source", "pair_binding", "members", "generator",
        "authorization_id", "attempt_id", "package_commitment_sha256",
    }
    if set(value) != expected_keys or value.get("profile") != "a0x-vertical-package-commitment-v2":
        raise A0XExperimentalPublicClosureError("P0 commitment is not the exact v2 profile shape")
    source = value.get("qualified_source")
    if not isinstance(source, dict) or set(source) != {"head", "tree", "ref"} or source.get("ref") != "refs/heads/main":
        raise A0XExperimentalPublicClosureError("P0 commitment source shape differs")
    if not _HEAD.fullmatch(str(source.get("head", ""))) or not _HEAD.fullmatch(str(source.get("tree", ""))):
        raise A0XExperimentalPublicClosureError("P0 commitment source digest is invalid")
    pair = value.get("pair_binding")
    _validate_synthetic_pair(pair)
    if not _HEAD.fullmatch(str(pair.get("revision", ""))):
        raise A0XExperimentalPublicClosureError("P0 commitment model revision is invalid")
    members = value.get("members")
    if not isinstance(members, list) or tuple(item.get("name") for item in members if isinstance(item, dict)) != _P0_MEMBER_NAMES:
        raise A0XExperimentalPublicClosureError("P0 commitment member order or set differs")
    for member in members:
        if not isinstance(member, dict) or set(member) != {"name", "size", "sha256"}:
            raise A0XExperimentalPublicClosureError("P0 commitment member shape differs")
        if not isinstance(member["size"], int) or isinstance(member["size"], bool) or member["size"] < 1:
            raise A0XExperimentalPublicClosureError("P0 commitment member size is invalid")
        _valid_sha(member["sha256"])
    expected_generator = {"profile": "a0x-vertical-slice-v2", "repository": "MarcoPorcellato/Latent-TRIZ"}
    if value.get("generator") != expected_generator:
        raise A0XExperimentalPublicClosureError("P0 commitment generator differs")
    for key in ("authorization_id", "attempt_id"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise A0XExperimentalPublicClosureError(f"P0 commitment {key} is invalid")
    commitment = _valid_sha(value.get("package_commitment_sha256"))
    projection = {key: value[key] for key in value if key != "package_commitment_sha256"}
    raw = json.dumps(projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    if hashlib.sha256(_COMMITMENT_DOMAIN + raw).hexdigest() != commitment:
        raise A0XExperimentalPublicClosureError("P0 v2 commitment digest is invalid")
    return dict(value)


def _validate_authorization_extension(
    documents: Mapping[str, Mapping[str, Any]],
    raw: Mapping[str, bytes],
    identity: Mapping[str, Any],
    dossier_sha256: str,
    commitment: Mapping[str, Any],
) -> None:
    extension = documents["authorization_extension"]
    if extension.get("profile") != "a0x-public-authorization-extension-v1":
        raise A0XExperimentalPublicClosureError("authorization extension profile differs")
    _check_document_identity(extension, identity, "authorization extension")
    bindings = extension.get("bindings")
    if not isinstance(bindings, dict):
        raise A0XExperimentalPublicClosureError("authorization extension bindings are missing")
    expected: dict[str, Any] = {
        "p0_commitment_sha256": _sha256(raw["p0_commitment"]),
        "p0_package_commitment_sha256": commitment["package_commitment_sha256"],
        "p0_dossier_raw_sha256": dossier_sha256,
        "p0_dossier_projection_sha256": _sha256(raw["p0_dossier_projection"]),
        "execution_spec_sha256": _sha256(raw["public_execution_spec"]),
        "gate_a_role_sha256": {role: _sha256(raw[role]) for role in (
            "gate_a_evidence", "gate_a_attestation_bundle", "gate_a_trusted_root", "gate_a_transport",
        )},
        "gate_b_private_v4_sha256": {"authorization": _sha256_hex_field(bindings, "gate_b_private_v4_sha256", "authorization"), "readiness": _sha256_hex_field(bindings, "gate_b_private_v4_sha256", "readiness")},
        "gate_b_projection_sha256": {role: _sha256(raw[role]) for role in (
            "gate_b_authorization_projection", "gate_b_readiness_projection",
        )},
    }
    for key, expected_value in expected.items():
        if bindings.get(key) != expected_value:
            raise A0XExperimentalPublicClosureError(f"authorization extension binding differs: {key}")
    if set(bindings) != set(expected):
        raise A0XExperimentalPublicClosureError("authorization extension has missing or extra bindings")
    projected = {
        "gate_b_authorization_projection": _sha256_hex_field(bindings, "gate_b_private_v4_sha256", "authorization"),
        "gate_b_readiness_projection": _sha256_hex_field(bindings, "gate_b_private_v4_sha256", "readiness"),
    }
    for role, source_hash in projected.items():
        if documents[role].get("source_raw_sha256") != source_hash:
            raise A0XExperimentalPublicClosureError(f"projection source hash reference differs: {role}")


def build_synthetic_authorization_extension(
    identity: Mapping[str, Any], pre_execution_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    """Construct the experimental extension from pre-execution inputs only.

    This pure helper deliberately receives no package path or terminal output;
    its closed key allowlist excludes every future execution/postflight result.
    It is synthetic tooling, not an authorization issuer or production API.
    """
    expected_keys = {
        "p0_commitment_sha256", "p0_package_commitment_sha256",
        "p0_dossier_raw_sha256", "p0_dossier_projection_sha256",
        "execution_spec_sha256", "gate_a_role_sha256",
        "gate_b_private_v4_sha256", "gate_b_projection_sha256",
    }
    if set(pre_execution_bindings) != expected_keys:
        raise A0XExperimentalPublicClosureError("synthetic authorization extension requires the exact pre-execution bindings")
    _check_synthetic_identity(identity)
    for key in ("p0_commitment_sha256", "p0_package_commitment_sha256", "p0_dossier_raw_sha256", "p0_dossier_projection_sha256", "execution_spec_sha256"):
        _valid_sha(pre_execution_bindings[key])
    gate_roles = {"gate_a_evidence", "gate_a_attestation_bundle", "gate_a_trusted_root", "gate_a_transport"}
    gate_a = pre_execution_bindings["gate_a_role_sha256"]
    gate_b_roles = {"gate_b_authorization_projection", "gate_b_readiness_projection"}
    gate_b = pre_execution_bindings["gate_b_projection_sha256"]
    private_v4 = pre_execution_bindings["gate_b_private_v4_sha256"]
    if not isinstance(gate_a, dict) or set(gate_a) != gate_roles or not isinstance(gate_b, dict) or set(gate_b) != gate_b_roles:
        raise A0XExperimentalPublicClosureError("synthetic authorization Gate A/B role bindings differ")
    if not isinstance(private_v4, dict) or set(private_v4) != {"authorization", "readiness"}:
        raise A0XExperimentalPublicClosureError("synthetic authorization private Gate B bindings differ")
    for value in (*gate_a.values(), *gate_b.values(), *private_v4.values()):
        _valid_sha(value)
    return {
        "profile": "a0x-public-authorization-extension-v1",
        "source": dict(identity["source"]),
        "pair_binding": dict(identity["pair_binding"]),
        "authorization_id": identity["authorization_id"],
        "attempt_id": identity["attempt_id"],
        "bindings": dict(pre_execution_bindings),
    }


def _validate_post_execution_bindings(
    manifest: Mapping[str, Any], documents: Mapping[str, Mapping[str, Any]], raw: Mapping[str, bytes],
) -> None:
    post = manifest.get("post_execution_bindings")
    if not isinstance(post, dict):
        raise A0XExperimentalPublicClosureError("post-execution closure bindings are missing")
    expected = {
        "authorization_extension_sha256": _sha256(raw["authorization_extension"]),
        "terminal_projection_sha256": _sha256(raw["terminal_projection"]),
        "terminal_private_raw_sha256": documents["terminal_projection"].get("source_raw_sha256"),
        "outer_postflight_projection_sha256": _sha256(raw["outer_postflight_projection"]),
        "outer_postflight_private_raw_sha256": documents["outer_postflight_projection"].get("source_raw_sha256"),
    }
    if set(post) != set(expected):
        raise A0XExperimentalPublicClosureError("post-execution closure binding shape differs")
    for key, value in expected.items():
        if post.get(key) != value:
            raise A0XExperimentalPublicClosureError(f"post-execution closure binding differs: {key}")
        _valid_sha(value)
    for role, manifest_key in (("terminal_projection", "terminal_private_raw_sha256"), ("outer_postflight_projection", "outer_postflight_private_raw_sha256")):
        if documents[role].get("source_raw_sha256") != post[manifest_key]:
            raise A0XExperimentalPublicClosureError(f"projection source hash differs from post-execution manifest: {role}")


def _validate_closed_roles(documents: Mapping[str, Mapping[str, Any]]) -> None:
    identity_fields = {"profile", "source", "pair_binding", "authorization_id", "attempt_id"}
    exact_fields = {
        "p0_dossier_projection": identity_fields | {"original_raw_sha256", "contents"},
        "public_execution_spec": identity_fields | {"requirements"},
        "gate_a_evidence": identity_fields | {"run_id", "attempt"},
        "gate_a_attestation_bundle": identity_fields | {"run_id"},
        "gate_a_trusted_root": identity_fields,
        "gate_a_transport": identity_fields | {"artifact_id"},
        "gate_b_authorization_projection": identity_fields | {"source_raw_sha256"},
        "gate_b_readiness_projection": identity_fields | {"source_raw_sha256"},
        "terminal_projection": identity_fields | {"source_raw_sha256"},
        "outer_postflight_projection": identity_fields | {"source_raw_sha256"},
        "authorization_extension": identity_fields | {"bindings"},
    }
    for role, fields in exact_fields.items():
        if set(documents[role]) != fields:
            raise A0XExperimentalPublicClosureError(f"closed synthetic document shape differs: {role}")
    for role, field in (("gate_a_evidence", "run_id"), ("gate_a_attestation_bundle", "run_id"), ("gate_a_transport", "artifact_id")):
        if not isinstance(documents[role][field], str) or not documents[role][field]:
            raise A0XExperimentalPublicClosureError(f"synthetic Gate A binding is invalid: {role}")
    if documents["gate_a_evidence"].get("attempt") != 1:
        raise A0XExperimentalPublicClosureError("synthetic Gate A attempt must be exactly one")
    for role, key in (("gate_a_evidence", "run_id"), ("gate_a_attestation_bundle", "run_id"), ("gate_a_transport", "artifact_id")):
        if not _SYNTHETIC_ID.fullmatch(documents[role][key]):
            raise A0XExperimentalPublicClosureError(f"Gate A identifier is not explicitly synthetic: {role}")
    if documents["gate_a_evidence"].get("run_id") != documents["gate_a_attestation_bundle"].get("run_id"):
        raise A0XExperimentalPublicClosureError("synthetic Gate A evidence and bundle run IDs differ")
    if not isinstance(documents["public_execution_spec"].get("requirements"), list):
        raise A0XExperimentalPublicClosureError("public execution spec requirements are invalid")
    if documents["public_execution_spec"]["requirements"] != ["synthetic-only"]:
        raise A0XExperimentalPublicClosureError("only the fixed synthetic execution spec is accepted")
    if documents["p0_dossier_projection"].get("contents") != {"public_safe": True}:
        raise A0XExperimentalPublicClosureError("only the closed synthetic-safe dossier projection is accepted")
    _valid_sha(documents["p0_dossier_projection"].get("original_raw_sha256"))


def _check_synthetic_p0_member_semantics(
    documents: Mapping[str, Mapping[str, Any]], identity: Mapping[str, Any],
) -> None:
    """Check the bounded synthetic P0 shape; raw real dossiers stay out of scope."""
    leg = identity["pair_binding"]["leg"]
    leg_docs = [documents[role] for role in ("p0_protocol", "p0_implementation", "p0_freeze")]
    identities: list[Mapping[str, Any]] = []
    for role, document in zip(("p0_protocol", "p0_implementation", "p0_freeze"), leg_docs, strict=True):
        expected_artifact = {
            "p0_protocol": "synthetic-p0-protocol",
            "p0_implementation": "synthetic-p0-implementation",
            "p0_freeze": "synthetic-p0-freeze",
        }[role]
        if set(document) != {"artifact_class", "synthetic_only", "identity"} or document.get("artifact_class") != expected_artifact or document.get("synthetic_only") is not True or not isinstance(document.get("identity"), dict):
            raise A0XExperimentalPublicClosureError("P0 leg member is not marked synthetic-only")
        member_identity = document["identity"]
        if set(member_identity) != {"leg", "protocol_id"} or not isinstance(member_identity.get("protocol_id"), str) or not member_identity["protocol_id"]:
            raise A0XExperimentalPublicClosureError("P0 leg member identity is not closed")
        if member_identity.get("leg") != leg:
            raise A0XExperimentalPublicClosureError("P0 leg member differs from closure pair")
        identities.append(member_identity)
    if identities[0] != identities[1] or identities[1] != identities[2]:
        raise A0XExperimentalPublicClosureError("P0 leg members have inconsistent shared identity")

    manifest = documents["p0_slice_manifest"]
    if set(manifest) != {"artifact_class", "synthetic_only", "implementation_source_head", "implementation_source_tree", "pair"} or manifest.get("artifact_class") != "synthetic-p0-slice-manifest" or manifest.get("synthetic_only") is not True:
        raise A0XExperimentalPublicClosureError("P0 slice manifest is not marked synthetic-only")
    if manifest.get("implementation_source_head") != identity["source"]["head"] or manifest.get("implementation_source_tree") != identity["source"]["tree"]:
        raise A0XExperimentalPublicClosureError("P0 slice manifest source differs from closure identity")
    if manifest.get("pair") != identity["pair_binding"]:
        raise A0XExperimentalPublicClosureError("P0 slice manifest pair differs from closure identity")


def _identity(value: Mapping[str, Any]) -> dict[str, Any]:
    source = value.get("source")
    pair = value.get("pair_binding")
    if not isinstance(source, dict) or set(source) != {"head", "tree"}:
        raise A0XExperimentalPublicClosureError("closure source identity is invalid")
    if not _HEAD.fullmatch(str(source.get("head", ""))) or not _HEAD.fullmatch(str(source.get("tree", ""))):
        raise A0XExperimentalPublicClosureError("closure source identity digest is invalid")
    _validate_synthetic_pair(pair)
    if not _HEAD.fullmatch(str(pair.get("revision", ""))):
        raise A0XExperimentalPublicClosureError("closure model revision is invalid")
    for key in ("authorization_id", "attempt_id"):
        if not isinstance(value.get(key), str) or not _SYNTHETIC_ID.fullmatch(value[key]):
            raise A0XExperimentalPublicClosureError(f"closure {key} is not an explicit synthetic identifier")
    _check_synthetic_identity({"source": source, "pair_binding": pair, "authorization_id": value["authorization_id"], "attempt_id": value["attempt_id"]})
    return {"source": dict(source), "pair_binding": dict(pair), "authorization_id": value["authorization_id"], "attempt_id": value["attempt_id"]}


def _validate_synthetic_pair(pair: Any) -> None:
    if not isinstance(pair, dict) or set(pair) != _PAIR_FIELDS:
        raise A0XExperimentalPublicClosureError("synthetic pair binding must have the exact closed field set")
    if any(pair.get(key) != value for key, value in _SYNTHETIC_PAIR.items()):
        raise A0XExperimentalPublicClosureError("pair binding is outside the explicit synthetic fixture values")
    if pair.get("revision") != _SYNTHETIC_PAIR["revision"]:
        raise A0XExperimentalPublicClosureError("pair binding revision is outside the explicit synthetic fixture value")


def _check_synthetic_identity(identity: Mapping[str, Any]) -> None:
    source = identity.get("source")
    if not isinstance(source, dict) or set(source) != {"head", "tree"} or not all(_HEAD.fullmatch(str(source.get(key, ""))) for key in ("head", "tree")):
        raise A0XExperimentalPublicClosureError("synthetic source identity is invalid")
    _validate_synthetic_pair(identity.get("pair_binding"))
    for key in ("authorization_id", "attempt_id"):
        if not isinstance(identity.get(key), str) or not _SYNTHETIC_ID.fullmatch(identity[key]):
            raise A0XExperimentalPublicClosureError(f"synthetic identity {key} is invalid")


def _check_document_identity(document: Mapping[str, Any], expected: Mapping[str, Any], role: str) -> None:
    if document.get("source") != expected["source"] or document.get("pair_binding") != expected["pair_binding"]:
        raise A0XExperimentalPublicClosureError(f"document identity differs: {role}")
    if document.get("authorization_id") != expected["authorization_id"] or document.get("attempt_id") != expected["attempt_id"]:
        raise A0XExperimentalPublicClosureError(f"document attempt binding differs: {role}")
    if not isinstance(document.get("profile"), str) or not document["profile"]:
        raise A0XExperimentalPublicClosureError(f"document profile is missing: {role}")


def _sha256_hex_field(value: Mapping[str, Any], *path: str) -> str:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise A0XExperimentalPublicClosureError("authorization extension is missing a private-source hash reference")
        current = current[key]
    return _valid_sha(current)


def _reject_status_promotion(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _FORBIDDEN_STATUS_VALUES and item is not _FORBIDDEN_STATUS_VALUES[key]:
                raise A0XExperimentalPublicClosureError(f"prohibited status promotion: {key}")
            _reject_status_promotion(item)
    elif isinstance(value, list):
        for item in value:
            _reject_status_promotion(item)


def _reject_private_content(raw: bytes, role: str) -> None:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise A0XExperimentalPublicClosureError(f"role is not UTF-8: {role}") from error
    lowered = text.lower()
    if any(marker.lower() in lowered for marker in _PRIVATE_MARKERS) or _ABSOLUTE_PRIVATE_PATH.search(text):
        raise A0XExperimentalPublicClosureError(f"private path or runtime mapping leaked in role: {role}")


def _canonical_json_object(raw: bytes, label: str) -> dict[str, Any]:
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise A0XExperimentalPublicClosureError(f"JSON is not canonical single-LF form: {label}")
    try:
        value = json.loads(raw[:-1].decode("utf-8"), object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise A0XExperimentalPublicClosureError(f"JSON is invalid: {label}") from error
    if not isinstance(value, dict) or _canonical_json(value) != raw:
        raise A0XExperimentalPublicClosureError(f"JSON bytes are not canonical: {label}")
    return value


def _canonical_jsonl_object(raw: bytes, label: str) -> dict[str, Any]:
    if not raw or not raw.endswith(b"\n"):
        raise A0XExperimentalPublicClosureError(f"JSONL lacks canonical final LF: {label}")
    lines = raw.splitlines(keepends=True)
    if any(not line.endswith(b"\n") or line == b"\n" for line in lines):
        raise A0XExperimentalPublicClosureError(f"JSONL contains a blank or unterminated line: {label}")
    values = [_canonical_json_object(line, f"{label} line") for line in lines]
    if len(values) != 1:
        raise A0XExperimentalPublicClosureError(f"synthetic JSONL role must have one object: {label}")
    return values[0]


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XExperimentalPublicClosureError("JSON value is not canonically serializable") from error


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts) or "\\" in value:
        raise A0XExperimentalPublicClosureError("role path is unsafe")
    return path


def _check_directory_path(root: Path) -> None:
    cursor = Path(root.anchor)
    for component in root.parts[1:]:
        cursor = cursor / component
        try:
            info = cursor.lstat()
        except OSError as error:
            raise A0XExperimentalPublicClosureError("package directory path is unavailable") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise A0XExperimentalPublicClosureError("package directory path contains a symlink or non-directory")


def _verify_exact_tree(root: Path) -> None:
    expected_files = {"closure-manifest.json", *ROLE_PATHS.values()}
    expected_dirs = {"/".join(PurePosixPath(path).parts[:index]) for path in ROLE_PATHS.values() for index in range(1, len(PurePosixPath(path).parts))}
    actual_files: set[str] = set()
    actual_dirs: set[str] = set()
    for current, directory_names, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in list(directory_names):
            full = current_path / name
            info = full.lstat()
            relative = full.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise A0XExperimentalPublicClosureError("closure contains a symlink or non-directory member")
            actual_dirs.add(relative)
        for name in filenames:
            full = current_path / name
            relative = full.relative_to(root).as_posix()
            actual_files.add(relative)
    if actual_files != expected_files or actual_dirs != expected_dirs:
        raise A0XExperimentalPublicClosureError("closure package contains missing or unallowlisted members")


def _read_independent(root: Path, relative: str) -> bytes:
    path = _safe_relative_path(relative)
    cursor = root
    for component in path.parts[:-1]:
        cursor = cursor / component
        try:
            info = cursor.lstat()
        except OSError as error:
            raise A0XExperimentalPublicClosureError(f"package role parent is unavailable: {relative}") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise A0XExperimentalPublicClosureError(f"package role parent is unsafe: {relative}")
    target = cursor / path.parts[-1]
    try:
        before = target.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise A0XExperimentalPublicClosureError(f"package role is not an independent regular file: {relative}")
        if before.st_size > _MAX_ROLE_BYTES:
            raise A0XExperimentalPublicClosureError(f"package role exceeds byte limit: {relative}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(target, flags)
    except A0XExperimentalPublicClosureError:
        raise
    except OSError as error:
        raise A0XExperimentalPublicClosureError(f"package role cannot be opened: {relative}") from error
    try:
        opened = os.fstat(descriptor)
        before_signature = (before.st_dev, before.st_ino, before.st_mode, before.st_nlink, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        opened_signature = (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_nlink, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or opened_signature != before_signature:
            raise A0XExperimentalPublicClosureError(f"package role changed during open: {relative}")
        chunks: list[bytes] = []
        total_bytes = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > _MAX_ROLE_BYTES:
                raise A0XExperimentalPublicClosureError(f"package role exceeds byte limit while reading: {relative}")
            chunks.append(chunk)
        after = os.fstat(descriptor)
        after_signature = (after.st_dev, after.st_ino, after.st_mode, after.st_nlink, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if opened_signature != after_signature or total_bytes != after.st_size:
            raise A0XExperimentalPublicClosureError(f"package role changed while reading: {relative}")
        try:
            after_path = target.lstat()
        except OSError as error:
            raise A0XExperimentalPublicClosureError(f"package role path changed while reading: {relative}") from error
        path_signature = (after_path.st_dev, after_path.st_ino, after_path.st_mode, after_path.st_nlink, after_path.st_size, after_path.st_mtime_ns, after_path.st_ctime_ns)
        if stat.S_ISLNK(after_path.st_mode) or path_signature != after_signature:
            raise A0XExperimentalPublicClosureError(f"package role path changed while reading: {relative}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _valid_sha(value: Any) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XExperimentalPublicClosureError("SHA-256 field is invalid")
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
