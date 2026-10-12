"""Versioned public closure bindings for A0X production packages.

This module checks byte and identity consistency only. It does not authenticate
who approved a run, how documents were derived, Gate A attestation, runtime
execution, or publication eligibility. Callers must independently obtain every
``public_role_bytes`` value and every private input digest from the exact
validated files at their own filesystem boundary. Filesystem loaders detect
ordinary replacement and refuse symlinks, hardlinks, and non-regular members,
but assume no untrusted concurrent same-user mutator and do not claim
race-proof isolation from one.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .a0x_validator import validate as validate_schema
from .a0x_contract import validate_vertical_package_commitment


PROFILE = "a0x-public-authorization-extension-v1"
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "a0x-public-authorization-extension-v1.schema.json"
_MANIFEST_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "a0x-public-closure-manifest-v1.schema.json"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_HEAD = re.compile(r"^[a-f0-9]{40}$")
PRE_EXECUTION_PUBLIC_ROLES = (
    "p0_commitment", "p0_protocol", "p0_implementation", "p0_freeze",
    "p0_slice_manifest", "public_dossier", "execution_spec", "gate_a_evidence",
    "gate_a_attestation_bundle", "gate_a_trusted_root", "gate_a_transport",
    "gate_b_authorization_projection", "gate_b_readiness_projection",
)
PRE_EXECUTION_PUBLIC_ROLE_PATHS = {
    "p0_commitment": "p0/commitment.json",
    "p0_protocol": "p0/protocol.json",
    "p0_implementation": "p0/implementation.json",
    "p0_freeze": "p0/freeze.json",
    "p0_slice_manifest": "p0/slice-manifest.json",
    "public_dossier": "public/dossier.json",
    "execution_spec": "public/execution-spec.json",
    "gate_a_evidence": "gate-a/evidence.json",
    "gate_a_attestation_bundle": "gate-a/attestation.bundle.jsonl",
    "gate_a_trusted_root": "gate-a/trusted-root.jsonl",
    "gate_a_transport": "gate-a/transport.json",
    "gate_b_authorization_projection": "gate-b/authorization-projection.json",
    "gate_b_readiness_projection": "gate-b/readiness-projection.json",
}
PRE_EXECUTION_EXTENSION_PATH = "authorization/extension-v1.json"
TERMINAL_CLOSURE_MANIFEST_PATH = "manifest.json"
TERMINAL_CLOSURE_ROLE_PATHS = {
    **PRE_EXECUTION_PUBLIC_ROLE_PATHS,
    "terminal_projection": "terminal/terminal-projection.json",
    "outer_postflight_projection": "terminal/outer-postflight-projection.json",
}
TERMINAL_PROJECTION_PATH = TERMINAL_CLOSURE_ROLE_PATHS["terminal_projection"]
OUTER_POSTFLIGHT_PROJECTION_PATH = TERMINAL_CLOSURE_ROLE_PATHS["outer_postflight_projection"]
PRIVATE_PRE_EXECUTION_INPUTS = (
    "p0_dossier_raw", "gate_b_authorization_v4", "gate_b_readiness_v4",
)
CLAIMS = {
    "document_bindings_consistent": True,
    "derivation_authenticated": False,
    "operator_approval_authenticated": False,
    "authorization_verified": False,
    "publication_eligible": False,
}
_MAX_ROLE_BYTES = 8 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_PRIVATE_MARKERS = (b".a0x-runtime", b"runtime_authorization_path", b"runtime-mapping.json")
_PRIVATE_ABSOLUTE_PATH = re.compile(rb"/(?:Users|private/(?:tmp|var)|var/folders)/", re.IGNORECASE)


class A0XPublicClosureError(ValueError):
    """Public closure is malformed, inconsistent, untrusted, or out of scope."""


@dataclass(frozen=True)
class PreExecutionBindingStatus:
    document_bindings_consistent: bool
    derivation_authenticated: bool
    operator_approval_authenticated: bool
    authorization_verified: bool
    publication_eligible: bool
    extension_sha256: str
    public_role_count: int


@dataclass(frozen=True)
class TerminalClosureStatus:
    document_bindings_consistent: bool
    derivation_authenticated: bool
    operator_approval_authenticated: bool
    authorization_verified: bool
    publication_eligible: bool
    private_originals_verified: bool
    manifest_sha256: str
    terminal_outcome: str


def validate_pre_execution_extension(
    extension_raw: bytes,
    *,
    public_role_bytes: Mapping[str, bytes],
    private_input_sha256: Mapping[str, str],
    expected_identity: Mapping[str, Any],
) -> PreExecutionBindingStatus:
    """Validate the acyclic pre-run extension against independently read inputs.

    The caller is responsible for reading the raw private v4/P0 members and
    public role files using its own exact path, regular-file and link-count
    rules. Digests supplied in ``private_input_sha256`` are observations, not
    self-authenticating evidence. No post-run, terminal or child-output hash
    is accepted in this extension.
    """
    if not isinstance(extension_raw, bytes) or not extension_raw or len(extension_raw) > _MAX_ROLE_BYTES:
        raise A0XPublicClosureError("authorization extension bytes are invalid")
    if not isinstance(public_role_bytes, Mapping) or set(public_role_bytes) != set(PRE_EXECUTION_PUBLIC_ROLES):
        raise A0XPublicClosureError("pre-execution public role inventory differs")
    if not isinstance(private_input_sha256, Mapping) or set(private_input_sha256) != set(PRIVATE_PRE_EXECUTION_INPUTS):
        raise A0XPublicClosureError("pre-execution private input inventory differs")
    if not isinstance(expected_identity, Mapping) or set(expected_identity) != {
        "qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256",
    }:
        raise A0XPublicClosureError("independent expected identity shape differs")

    total = 0
    public_hashes: dict[str, str] = {}
    for role in PRE_EXECUTION_PUBLIC_ROLES:
        raw = public_role_bytes[role]
        if not isinstance(raw, bytes) or not raw or len(raw) > _MAX_ROLE_BYTES:
            raise A0XPublicClosureError(f"public role bytes are invalid: {role}")
        total += len(raw)
        if any(marker in raw for marker in _PRIVATE_MARKERS) or _PRIVATE_ABSOLUTE_PATH.search(raw):
            raise A0XPublicClosureError(f"public role contains a known private-path marker: {role}")
        public_hashes[role] = hashlib.sha256(raw).hexdigest()
    if total > _MAX_TOTAL_BYTES:
        raise A0XPublicClosureError("pre-execution public role bytes exceed total limit")
    private_hashes = {role: _digest(private_input_sha256[role], role) for role in PRIVATE_PRE_EXECUTION_INPUTS}

    value = _canonical_object(extension_raw, "authorization extension")
    _validate_schema(value)
    if value["profile"] != PROFILE or value["artifact_class"] != "a0x-public-authorization-extension":
        raise A0XPublicClosureError("production verifier rejects non-production or experimental profiles")
    identity = {key: value[key] for key in expected_identity}
    if identity != dict(expected_identity):
        raise A0XPublicClosureError("extension identity differs from independently validated private graph")
    source = identity["qualified_source"]
    if not isinstance(source, Mapping) or set(source) != {"head", "tree", "ref"}:
        raise A0XPublicClosureError("qualified source shape differs")
    if not _HEAD.fullmatch(str(source["head"])) or not _HEAD.fullmatch(str(source["tree"])) or source["ref"] != "refs/heads/main":
        raise A0XPublicClosureError("qualified source identity is invalid")
    if not isinstance(identity["pair_binding"], Mapping):
        raise A0XPublicClosureError("pair binding is invalid")
    if not isinstance(identity["authorization_id"], str) or not identity["authorization_id"] or not isinstance(identity["attempt_id"], str) or not identity["attempt_id"]:
        raise A0XPublicClosureError("authorization or attempt identity is invalid")
    _digest(identity["p0_package_commitment_sha256"], "P0 package commitment")

    bindings = value["bindings"]
    if bindings != {"public_role_sha256": public_hashes, "private_input_sha256": private_hashes}:
        raise A0XPublicClosureError("pre-execution raw input hash bindings differ")
    _validate_pre_execution_role_semantics(public_role_bytes, private_hashes, identity)
    if value["claims"] != CLAIMS:
        raise A0XPublicClosureError("claim statuses exceed the closure contract")
    return PreExecutionBindingStatus(
        document_bindings_consistent=True,
        derivation_authenticated=False,
        operator_approval_authenticated=False,
        authorization_verified=False,
        publication_eligible=False,
        extension_sha256=hashlib.sha256(extension_raw).hexdigest(),
        public_role_count=len(public_hashes),
    )


def _validate_pre_execution_role_semantics(
    role_bytes: Mapping[str, bytes], private_hashes: Mapping[str, str], identity: Mapping[str, Any],
) -> None:
    try:
        commitment = validate_vertical_package_commitment(_canonical_object(role_bytes["p0_commitment"], "P0 commitment"))
    except (KeyError, TypeError, ValueError) as error:
        raise A0XPublicClosureError("public P0 v2 commitment is invalid") from error
    if (
        commitment.get("qualified_source") != identity["qualified_source"]
        or commitment.get("pair_binding") != identity["pair_binding"]
        or commitment.get("package_commitment_sha256") != identity["p0_package_commitment_sha256"]
    ):
        raise A0XPublicClosureError("P0 v2 commitment source, pair, or digest differs from pre-execution identity")
    expected_members = {
        "p0_protocol": "protocol.json",
        "p0_implementation": "implementation.json",
        "p0_freeze": "freeze.json",
        "p0_dossier_raw": "approval-dossier.json",
        "p0_slice_manifest": "slice-manifest.json",
    }
    members = {member["name"]: member for member in commitment["members"]}
    if set(members) != set(expected_members.values()):
        raise A0XPublicClosureError("P0 v2 member inventory differs")
    for role, member_name in expected_members.items():
        member = members[member_name]
        if role == "p0_dossier_raw":
            if private_hashes[role] != member["sha256"]:
                raise A0XPublicClosureError(f"P0 member differs from v2 commitment: {member_name}")
            continue
        raw = role_bytes[role]
        if hashlib.sha256(raw).hexdigest() != member["sha256"] or len(raw) != member["size"]:
            raise A0XPublicClosureError(f"P0 member differs from v2 commitment: {member_name}")

    identity_fields = {
        "qualified_source": identity["qualified_source"],
        "pair_binding": identity["pair_binding"],
        "authorization_id": identity["authorization_id"],
        "attempt_id": identity["attempt_id"],
    }
    dossier = _canonical_object(role_bytes["public_dossier"], "public dossier projection")
    _exact_fields(dossier, {
        "artifact_class", "profile", "qualified_source", "pair_binding",
        "authorization_id", "attempt_id", "original_raw_sha256",
    }, "public dossier projection")
    if (
        dossier.get("artifact_class") != "a0x-public-dossier-projection"
        or dossier.get("profile") != "a0x-public-dossier-projection-v1"
        or any(dossier.get(key) != expected for key, expected in identity_fields.items())
        or dossier.get("original_raw_sha256") != private_hashes["p0_dossier_raw"]
    ):
        raise A0XPublicClosureError("public dossier projection differs from exact P0 dossier or identity")
    execution_spec = _canonical_object(role_bytes["execution_spec"], "public execution specification")
    _exact_fields(execution_spec, {
        "artifact_class", "profile", "qualified_source", "pair_binding",
        "authorization_id", "attempt_id", "protocol_sha256",
    }, "public execution specification")
    if (
        execution_spec.get("artifact_class") != "a0x-public-execution-specification"
        or execution_spec.get("profile") != "a0x-public-execution-spec-v1"
        or any(execution_spec.get(key) != expected for key, expected in identity_fields.items())
        or _digest(execution_spec.get("protocol_sha256"), "execution specification protocol")
        != hashlib.sha256(role_bytes["p0_protocol"]).hexdigest()
    ):
        raise A0XPublicClosureError("public execution specification identity or protocol binding differs")
    for role, expected_hash in (
        ("gate_b_authorization_projection", private_hashes["gate_b_authorization_v4"]),
        ("gate_b_readiness_projection", private_hashes["gate_b_readiness_v4"]),
    ):
        projection = _canonical_object(role_bytes[role], role)
        _exact_fields(projection, {
            "artifact_class", "profile", "qualified_source", "pair_binding",
            "authorization_id", "attempt_id", "source_raw_sha256",
        }, role)
        expected_artifact_class, expected_profile = {
            "gate_b_authorization_projection": (
                "a0x-public-gate-b-authorization-projection",
                "a0x-public-gate-b-authorization-projection-v1",
            ),
            "gate_b_readiness_projection": (
                "a0x-public-gate-b-readiness-projection",
                "a0x-public-gate-b-readiness-projection-v1",
            ),
        }[role]
        if (
            projection.get("artifact_class") != expected_artifact_class
            or projection.get("profile") != expected_profile
            or any(projection.get(key) != expected for key, expected in identity_fields.items())
            or projection.get("source_raw_sha256") != expected_hash
        ):
            raise A0XPublicClosureError(f"public Gate B projection is not bound to private input: {role}")
    gate_a = _canonical_object(role_bytes["gate_a_evidence"], "Gate A evidence projection")
    _exact_fields(gate_a, {
        "artifact_class", "profile", "qualified_source", "pair_binding",
        "authorization_id", "attempt_id",
    }, "Gate A evidence projection")
    if gate_a.get("artifact_class") != "a0x-public-gate-a-evidence" or gate_a.get("profile") != "a0x-public-gate-a-evidence-v1":
        raise A0XPublicClosureError("Gate A evidence projection profile differs")
    if any(gate_a.get(key) != expected for key, expected in identity_fields.items()):
        raise A0XPublicClosureError("Gate A evidence projection identity differs")


def _exact_fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise A0XPublicClosureError(f"{label} has unknown or missing fields")


def pre_execution_closure_relative_path(expected_identity: Mapping[str, Any]) -> str:
    """Return the only accepted pair-scoped public closure directory."""
    if not isinstance(expected_identity, Mapping) or set(expected_identity) != {
        "qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256",
    }:
        raise A0XPublicClosureError("independent expected identity shape differs")
    source = expected_identity["qualified_source"]
    pair = expected_identity["pair_binding"]
    if not isinstance(source, Mapping) or set(source) != {"head", "tree", "ref"}:
        raise A0XPublicClosureError("qualified source shape differs")
    if not _HEAD.fullmatch(str(source.get("head", ""))) or not _HEAD.fullmatch(str(source.get("tree", ""))) or source.get("ref") != "refs/heads/main":
        raise A0XPublicClosureError("qualified source identity is invalid")
    if not isinstance(pair, Mapping) or pair.get("leg") not in {"a0", "r1"} or not isinstance(pair.get("model_key"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", pair["model_key"]):
        raise A0XPublicClosureError("pair identity is invalid")
    return (
        "experiments/a0x-six-model/vertical-slices/"
        f"{source['head']}/{pair['leg']}/{pair['model_key']}/public-closure/v1"
    )


def load_pre_execution_public_closure(
    repository_root: str | os.PathLike[str],
    *,
    expected_identity: Mapping[str, Any],
    private_input_sha256: Mapping[str, str],
) -> PreExecutionBindingStatus:
    """Read the exact public role tree as independent regular files, then bind it.

    All directory components under the resolved repository and every member
    must be non-symlink objects; member files must have link count one and
    unique inodes. The role tree is closed: extra or missing files refuse.
    This narrow marker scan catches only named private-path forms and is not a
    general secret or privacy detector.
    """
    repository = os.path.realpath(os.fspath(repository_root))
    if not os.path.isdir(repository) or os.path.islink(os.fspath(repository_root)):
        raise A0XPublicClosureError("repository root is unavailable or symlinked")
    relative = pre_execution_closure_relative_path(expected_identity)
    root = os.path.join(repository, *relative.split("/"))
    _require_nonsymlink_directory_chain(repository, root)
    expected_paths = {**PRE_EXECUTION_PUBLIC_ROLE_PATHS, "authorization_extension": PRE_EXECUTION_EXTENSION_PATH}
    expected_files = set(expected_paths.values())
    observed_files: set[str] = set()
    observed_directories: set[str] = {"."}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        rel_dir = os.path.relpath(current, root)
        if rel_dir != ".":
            observed_directories.add(rel_dir.replace(os.sep, "/"))
        for name in directories:
            path = os.path.join(current, name)
            if os.path.islink(path) or not stat.S_ISDIR(os.lstat(path).st_mode):
                raise A0XPublicClosureError("public closure contains a symlink or non-directory")
        for name in files:
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path):
                raise A0XPublicClosureError("public closure contains a symlink member")
            observed_files.add(rel)
    expected_directories = {"."}
    for relative_file in expected_files:
        parent = os.path.dirname(relative_file)
        while parent:
            expected_directories.add(parent)
            parent = os.path.dirname(parent)
    if observed_files != expected_files or observed_directories != expected_directories:
        raise A0XPublicClosureError("public closure role tree membership differs")
    role_bytes: dict[str, bytes] = {}
    inodes: set[tuple[int, int]] = set()
    for role, relative_file in expected_paths.items():
        path = os.path.join(root, *relative_file.split("/"))
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
            )
            with os.fdopen(descriptor, "rb") as stream:
                before = os.fstat(stream.fileno())
                named = os.stat(path, follow_symlinks=False)
                if not stat.S_ISREG(before.st_mode) or not stat.S_ISREG(named.st_mode) or before.st_nlink != 1 or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino):
                    raise A0XPublicClosureError("public closure member is not an independent regular file")
                inode = (before.st_dev, before.st_ino)
                if inode in inodes:
                    raise A0XPublicClosureError("public closure contains an aliased file inode")
                inodes.add(inode)
                raw = stream.read(_MAX_ROLE_BYTES + 1)
                after = os.fstat(stream.fileno())
                if len(raw) != before.st_size or len(raw) == 0 or len(raw) > _MAX_ROLE_BYTES or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                    raise A0XPublicClosureError("public closure member changed or exceeded its limit")
                role_bytes[role] = raw
        except OSError as error:
            raise A0XPublicClosureError("public closure member cannot be read safely") from error
    extension = role_bytes.pop("authorization_extension")
    return validate_pre_execution_extension(
        extension,
        public_role_bytes=role_bytes,
        private_input_sha256=private_input_sha256,
        expected_identity=expected_identity,
    )


def load_public_terminal_closure(
    repository_root: str | os.PathLike[str],
    *,
    expected_identity: Mapping[str, Any],
    expected_manifest_sha256: str,
) -> TerminalClosureStatus:
    """Load and verify the complete public closure at its canonical pair path.

    This is the production filesystem entrypoint. The manifest is part of the
    closed tree; all files must be independent regular files. Private original
    bytes are deliberately unavailable here and are never claimed verified.
    The manifest digest must come from an independent caller anchor; an
    adjacent self-hash is not treated as proof of identity.
    """
    repository = os.path.realpath(os.fspath(repository_root))
    if not os.path.isdir(repository) or os.path.islink(os.fspath(repository_root)):
        raise A0XPublicClosureError("repository root is unavailable or symlinked")
    relative = pre_execution_closure_relative_path(expected_identity)
    expected_manifest_sha256 = _digest(expected_manifest_sha256, "expected public closure manifest")
    root = os.path.join(repository, *relative.split("/"))
    _require_nonsymlink_directory_chain(repository, root)

    expected_paths = {
        **TERMINAL_CLOSURE_ROLE_PATHS,
        "authorization_extension": PRE_EXECUTION_EXTENSION_PATH,
    }
    expected_files = set(expected_paths.values()) | {TERMINAL_CLOSURE_MANIFEST_PATH}
    expected_directories = {"."}
    for relative_file in expected_files:
        parent = os.path.dirname(relative_file)
        while parent:
            expected_directories.add(parent)
            parent = os.path.dirname(parent)
    observed_files: set[str] = set()
    observed_directories: set[str] = {"."}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        rel_dir = os.path.relpath(current, root)
        if rel_dir != ".":
            observed_directories.add(rel_dir.replace(os.sep, "/"))
        for name in directories:
            path = os.path.join(current, name)
            if os.path.islink(path) or not stat.S_ISDIR(os.lstat(path).st_mode):
                raise A0XPublicClosureError("public terminal closure contains a symlink or non-directory")
        for name in files:
            path = os.path.join(current, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if os.path.islink(path):
                raise A0XPublicClosureError("public terminal closure contains a symlink member")
            observed_files.add(rel)
    if observed_files != expected_files or observed_directories != expected_directories:
        raise A0XPublicClosureError("public terminal closure membership differs")

    directory_identities = _directory_identity_snapshot(root, expected_directories)

    raw_by_path: dict[str, bytes] = {}
    identities: set[tuple[int, int]] = set()
    for relative_file in sorted(expected_files):
        path = os.path.join(root, *relative_file.split("/"))
        raw, identity = _read_independent_regular_file(path, label=relative_file)
        if identity in identities:
            raise A0XPublicClosureError("public terminal closure contains aliased file inodes")
        identities.add(identity)
        raw_by_path[relative_file] = raw
    if sum(map(len, raw_by_path.values())) > _MAX_TOTAL_BYTES:
        raise A0XPublicClosureError("public terminal closure exceeds total byte limit")
    if _directory_identity_snapshot(root, expected_directories) != directory_identities:
        raise A0XPublicClosureError("public terminal closure directory identity changed during verification")
    _require_nonsymlink_directory_chain(repository, root)
    role_bytes = {role: raw_by_path[path] for role, path in expected_paths.items()}
    extension_raw = role_bytes.pop("authorization_extension")
    manifest_raw = raw_by_path[TERMINAL_CLOSURE_MANIFEST_PATH]
    if hashlib.sha256(manifest_raw).hexdigest() != expected_manifest_sha256:
        raise A0XPublicClosureError("public terminal closure manifest differs from independent anchor")
    return verify_public_terminal_closure(
        manifest_raw,
        pre_execution_extension_raw=extension_raw,
        terminal_projection_raw=role_bytes.pop("terminal_projection"),
        outer_postflight_projection_raw=role_bytes.pop("outer_postflight_projection"),
        public_role_bytes=role_bytes,
        expected_identity=expected_identity,
    )


def verify_public_terminal_closure(
    manifest_raw: bytes,
    *,
    pre_execution_extension_raw: bytes,
    terminal_projection_raw: bytes,
    outer_postflight_projection_raw: bytes,
    public_role_bytes: Mapping[str, bytes],
    expected_identity: Mapping[str, Any],
) -> TerminalClosureStatus:
    """Verify the public document graph, not omitted private originals.

    ``private_original_sha256`` values are carried as integrity references only.
    Since this public verifier does not possess those private bytes, it always
    reports ``private_originals_verified=False``. Callers must independently
    read canonical public role files and pass their exact bytes.
    """
    manifest = _canonical_object(manifest_raw, "public closure manifest")
    try:
        schema = json.loads(_MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise A0XPublicClosureError("public closure manifest schema unavailable") from error
    if validate_schema(manifest, schema):
        raise A0XPublicClosureError("public closure manifest schema invalid")
    if manifest.get("profile") != "a0x-public-closure-manifest-v1":
        raise A0XPublicClosureError("production verifier rejects experimental closure profiles")
    if not isinstance(expected_identity, Mapping) or set(expected_identity) != {
        "qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256",
    }:
        raise A0XPublicClosureError("independent expected identity shape differs")
    for key in ("qualified_source", "pair_binding", "authorization_id", "attempt_id", "p0_package_commitment_sha256"):
        if manifest[key] != expected_identity[key]:
            raise A0XPublicClosureError(f"terminal closure identity differs: {key}")
    extension = _canonical_object(pre_execution_extension_raw, "authorization extension")
    if extension.get("profile") != PROFILE or extension.get("artifact_class") != "a0x-public-authorization-extension":
        raise A0XPublicClosureError("terminal verifier rejects synthetic or experimental authorization")
    if (
        extension.get("qualified_source") != expected_identity["qualified_source"]
        or extension.get("pair_binding") != expected_identity["pair_binding"]
        or extension.get("authorization_id") != expected_identity["authorization_id"]
        or extension.get("attempt_id") != expected_identity["attempt_id"]
        or extension.get("p0_package_commitment_sha256") != expected_identity["p0_package_commitment_sha256"]
    ):
        raise A0XPublicClosureError("pre-execution extension identity differs from terminal closure")
    try:
        pre_execution_status = validate_pre_execution_extension(
            pre_execution_extension_raw,
            public_role_bytes=public_role_bytes,
            private_input_sha256=extension["bindings"]["private_input_sha256"],
            expected_identity=expected_identity,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise A0XPublicClosureError("public pre-execution role graph is invalid") from error
    terminal_projection = _canonical_object(terminal_projection_raw, "terminal projection")
    outer_projection = _canonical_object(outer_postflight_projection_raw, "outer postflight projection")
    identity_fields = {
        "qualified_source": expected_identity["qualified_source"],
        "pair_binding": expected_identity["pair_binding"],
        "authorization_id": expected_identity["authorization_id"],
        "attempt_id": expected_identity["attempt_id"],
    }
    _exact_fields(terminal_projection, {
        "artifact_class", "profile", "schema_version", *identity_fields.keys(),
        "original_raw_sha256", "terminal_outcome", "completion_classification", "execution_assertions_only",
    }, "terminal projection")
    if (
        terminal_projection.get("artifact_class") != "a0x-public-terminal-projection"
        or terminal_projection.get("profile") != "a0x-public-terminal-projection-v1"
        or type(terminal_projection.get("schema_version")) is not int
        or terminal_projection.get("schema_version") != 1
        or terminal_projection.get("terminal_outcome") not in {"positive", "null", "non_interpretable", "incompatible", "failed", "recovery_required"}
        or terminal_projection.get("completion_classification") not in {"completed", "failed", "recovery_required"}
        or terminal_projection.get("execution_assertions_only") is not True
        or any(terminal_projection.get(key) != value for key, value in identity_fields.items())
    ):
        raise A0XPublicClosureError("terminal projection fields or values exceed the closed contract")
    expected_completion = {
        "positive": "completed", "null": "completed", "non_interpretable": "completed",
        "incompatible": "failed", "failed": "failed", "recovery_required": "recovery_required",
    }[terminal_projection["terminal_outcome"]]
    if terminal_projection["completion_classification"] != expected_completion:
        raise A0XPublicClosureError("terminal outcome and completion classification are inconsistent")
    _digest(terminal_projection.get("original_raw_sha256"), "terminal original")
    _exact_fields(outer_projection, {
        "artifact_class", "profile", "schema_version", *identity_fields.keys(),
        "original_raw_sha256", "admission_inactive", "runtime_clean", "cleanup_status",
    }, "outer postflight projection")
    if (
        outer_projection.get("artifact_class") != "a0x-public-outer-postflight-projection"
        or outer_projection.get("profile") != "a0x-public-outer-postflight-projection-v1"
        or type(outer_projection.get("schema_version")) is not int
        or outer_projection.get("schema_version") != 1
        or not isinstance(outer_projection.get("admission_inactive"), bool)
        or not isinstance(outer_projection.get("runtime_clean"), bool)
        or outer_projection.get("cleanup_status") not in {"complete", "uncertain", "failed"}
        or any(outer_projection.get(key) != value for key, value in identity_fields.items())
    ):
        raise A0XPublicClosureError("outer postflight projection fields or values exceed the closed contract")
    _digest(outer_projection.get("original_raw_sha256"), "outer postflight original")
    private_original_sha256 = manifest.get("private_original_sha256")
    if not isinstance(private_original_sha256, Mapping) or set(private_original_sha256) != {"terminal_original", "outer_postflight_original"}:
        raise A0XPublicClosureError("private original hash inventory differs")
    expected_hashes = {
        "pre_execution_extension_sha256": hashlib.sha256(pre_execution_extension_raw).hexdigest(),
        "terminal_projection_sha256": hashlib.sha256(terminal_projection_raw).hexdigest(),
        "outer_postflight_projection_sha256": hashlib.sha256(outer_postflight_projection_raw).hexdigest(),
        "private_original_sha256": {
            key: _digest(private_original_sha256[key], key)
            for key in ("terminal_original", "outer_postflight_original")
        },
    }
    if any(manifest.get(key) != value for key, value in expected_hashes.items()):
        raise A0XPublicClosureError("terminal or postflight bytes differ from the post-execution closure")
    if (
        terminal_projection.get("original_raw_sha256") != expected_hashes["private_original_sha256"]["terminal_original"]
        or outer_projection.get("original_raw_sha256") != expected_hashes["private_original_sha256"]["outer_postflight_original"]
    ):
        raise A0XPublicClosureError("private original digest references differ from public projections")
    if manifest.get("claims") != CLAIMS:
        raise A0XPublicClosureError("terminal closure claims exceed the contract")
    return TerminalClosureStatus(
        document_bindings_consistent=pre_execution_status.document_bindings_consistent,
        derivation_authenticated=False,
        operator_approval_authenticated=False,
        authorization_verified=False,
        publication_eligible=False,
        private_originals_verified=False,
        manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
        terminal_outcome=terminal_projection["terminal_outcome"],
    )


def _read_independent_regular_file(path: str, *, label: str) -> tuple[bytes, tuple[int, int]]:
    """Read bounded bytes without blocking on FIFOs or following symlinks."""
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        before = os.fstat(descriptor)
        named = os.stat(path, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(named.st_mode)
            or before.st_nlink != 1
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise A0XPublicClosureError(f"public closure member is not an independent regular file: {label}")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = None
            raw = stream.read(_MAX_ROLE_BYTES + 1)
            after = os.fstat(stream.fileno())
        named_after = os.stat(path, follow_symlinks=False)
        if (
            not raw
            or len(raw) > _MAX_ROLE_BYTES
            or len(raw) != before.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or after.st_nlink != 1
            or (after.st_dev, after.st_ino) != (named_after.st_dev, named_after.st_ino)
        ):
            raise A0XPublicClosureError(f"public closure member changed or exceeded its limit: {label}")
        return raw, (before.st_dev, before.st_ino)
    except OSError as error:
        raise A0XPublicClosureError(f"public closure member cannot be read safely: {label}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _directory_identity_snapshot(root: str, relatives: set[str]) -> dict[str, tuple[int, int]]:
    snapshot: dict[str, tuple[int, int]] = {}
    for relative in sorted(relatives):
        path = root if relative == "." else os.path.join(root, *relative.split("/"))
        try:
            info = os.lstat(path)
        except OSError as error:
            raise A0XPublicClosureError("public closure directory became unavailable") from error
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise A0XPublicClosureError("public closure directory changed type")
        snapshot[relative] = (info.st_dev, info.st_ino)
    return snapshot


def _require_nonsymlink_directory_chain(repository: str, destination: str) -> None:
    relative = os.path.relpath(destination, repository)
    if relative == "." or relative.startswith("..") or os.path.isabs(relative):
        raise A0XPublicClosureError("public closure path escaped repository")
    current = repository
    for component in relative.split(os.sep):
        current = os.path.join(current, component)
        try:
            info = os.lstat(current)
        except OSError as error:
            raise A0XPublicClosureError("public closure directory is unavailable") from error
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise A0XPublicClosureError("public closure directory component is unsafe")


def _validate_schema(value: Mapping[str, Any]) -> None:
    try:
        schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise A0XPublicClosureError("public authorization extension schema unavailable") from error
    if validate_schema(dict(value), schema):
        raise A0XPublicClosureError("public authorization extension schema invalid")


def _canonical_object(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise A0XPublicClosureError(f"{label} is not canonical JSON") from error
    if not isinstance(value, dict) or canonical != raw:
        raise A0XPublicClosureError(f"{label} is not canonical JSON object bytes")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XPublicClosureError(f"{label} digest is invalid")
    return value
