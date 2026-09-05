"""Target-free pair-scoped A0X package construction and validation."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    Leg,
    PairBinding,
    V2_MEMBER_NAMES,
    build_vertical_package_commitment,
    compute_dense_bound,
    derive_pair_output_path,
    validate_vertical_package_commitment,
)
from .a0x_freeze import (
    _COMMON,
    _IMPLEMENTATION_PATHS,
    _LEG_SOURCES,
    _copy_fields,
)
from .validator import validate


GENERATOR_PROFILE = "a0x-vertical-slice-v1"
REPOSITORY = "MarcoPorcellato/Latent-TRIZ"
PACKAGE_SCOPE = "one_leg_model_pair_not_campaign_wide_regeneration"
INVALID_REQUEST = "A0X_VERTICAL_SLICE_INVALID_REQUEST"
OUTPUT_EXISTS = "A0X_VERTICAL_SLICE_OUTPUT_EXISTS"
PUBLICATION_FAILED = "A0X_VERTICAL_SLICE_PUBLICATION_FAILED"
PUBLICATION_OWNERSHIP_LOST = "A0X_VERTICAL_SLICE_PUBLICATION_OWNERSHIP_LOST"
PUBLICATION_UNSUPPORTED = "A0X_VERTICAL_SLICE_PUBLICATION_UNSUPPORTED"
VALIDATION_FAILED = "A0X_VERTICAL_SLICE_VALIDATION_FAILED"
V2_INVALID_REQUEST = "A0X_VERTICAL_RUNTIME_PACKAGE_V2_INVALID_REQUEST"
V2_OUTPUT_EXISTS = "A0X_VERTICAL_RUNTIME_PACKAGE_V2_OUTPUT_EXISTS"
V2_PUBLICATION_FAILED = "A0X_VERTICAL_RUNTIME_PACKAGE_V2_PUBLICATION_FAILED"
V2_PUBLICATION_OWNERSHIP_LOST = "A0X_VERTICAL_RUNTIME_PACKAGE_V2_PUBLICATION_OWNERSHIP_LOST"
V2_VALIDATION_FAILED = "A0X_VERTICAL_RUNTIME_PACKAGE_V2_VALIDATION_FAILED"
V2_GENERATOR_PROFILE = "a0x-vertical-slice-v2"
RENAME_EXCL = 0x00000004
RENAME_NOFOLLOW_ANY = 0x00000010

_REVISION = re.compile(r"^[a-f0-9]{40}$")
_MODEL_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DOSSIER_PATH = re.compile(
    r"^experiments/a0x-six-model/vertical-slices/"
    r"([a-f0-9]{40})/(a0|r1)/([A-Za-z0-9][A-Za-z0-9._-]{0,127})/"
    r"approval-dossier\.json$"
)
_MEMBER_NAMES = (
    "protocol.json",
    "implementation.json",
    "freeze.json",
    "approval-dossier.json",
    "slice-manifest.json",
)
_NON_MANIFEST_NAMES = _MEMBER_NAMES[:-1]
_MAX_DOCUMENT_BYTES = 32 * 1024 * 1024


class A0XVerticalSliceError(ValueError):
    """Raised when pair selection, package publication, or validation refuses."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class VerticalSliceRequest:
    leg: Leg
    model_key: str
    implementation_source_head: str
    output_root: str


@dataclass(frozen=True)
class VerticalRuntimePackageRequest:
    qualified_source_head: str
    qualified_source_tree: str
    leg: Leg
    model_key: str
    output_root: str
    authorization_id: str
    attempt_id: str


@dataclass(frozen=True)
class VerticalPackageBinding:
    envelope_path: str
    package_path: str
    commitment_path: str
    commitment_raw_sha256: str
    package_commitment_sha256: str
    dossier_path: str
    dossier_sha256: str
    qualified_source_head: str
    qualified_source_tree: str
    leg: Leg
    model_key: str
    model_revision: str
    pair_binding: PairBinding


@dataclass
class _PackageParent:
    descriptors: tuple[int, ...]
    chain: tuple[tuple[int, str, tuple[int, int]], ...]
    fd: int
    destination_name: str


@dataclass
class _PublicationTransaction:
    parent: _PackageParent
    stage_name: str
    stage_fd: int
    stage_identity: tuple[int, int]
    state: str = "staged"


@dataclass(frozen=True)
class _BoundFile:
    relative: str
    raw: bytes
    sha256: str

    def as_binding(self) -> dict[str, Any]:
        return {"path": self.relative, "bytes": len(self.raw), "sha256": self.sha256}


@dataclass(frozen=True)
class _V2StageSnapshot:
    package_identity: tuple[int, int]
    member_identities: Mapping[str, tuple[int, int, int]]
    commitment_identity: tuple[int, int, int]
    members: Mapping[str, tuple[bytes, str]]
    commitment: tuple[bytes, str]


class _RepositoryReader:
    """Single-read, descriptor-relative access to repository prerequisites."""

    def __init__(self, repository: Path):
        self.repository = repository
        self.root_fd: int | None = None
        self.cache: dict[str, _BoundFile] = {}

    def __enter__(self) -> "_RepositoryReader":
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            self.root_fd = os.open(self.repository, flags)
        except OSError as error:
            raise A0XVerticalSliceError(VALIDATION_FAILED) from error
        return self

    def __exit__(self, *_args: object) -> None:
        if self.root_fd is not None:
            os.close(self.root_fd)
            self.root_fd = None

    def read(self, relative: str) -> _BoundFile:
        normalized = _safe_prerequisite_relative(relative)
        cached = self.cache.get(normalized)
        if cached is not None:
            return cached
        if self.root_fd is None:
            raise A0XVerticalSliceError(VALIDATION_FAILED)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptors: list[int] = []
        try:
            current = os.dup(self.root_fd)
            descriptors.append(current)
            parts = PurePosixPath(normalized).parts
            for part in parts[:-1]:
                child = os.open(part, flags, dir_fd=current)
                descriptors.append(child)
                current = child
            raw = _read_regular_at(current, parts[-1], _MAX_DOCUMENT_BYTES, VALIDATION_FAILED)
        except A0XVerticalSliceError:
            raise
        except OSError as error:
            raise A0XVerticalSliceError(VALIDATION_FAILED) from error
        finally:
            _close_descriptors(tuple(descriptors))
        binding = _BoundFile(normalized, raw, _sha256(raw))
        self.cache[normalized] = binding
        _after_prerequisite_read(normalized, raw)
        return binding

    def object(self, relative: str) -> dict[str, Any]:
        return _parse_json_object(self.read(relative).raw)


def _before_publish(transaction: _PublicationTransaction) -> None:
    """Test seam immediately before exclusive publication."""


def _after_publish(transaction: _PublicationTransaction) -> None:
    """Test seam immediately after exclusive publication."""


def _before_owned_rmdir(transaction: _PublicationTransaction, name: str) -> None:
    """Test seam immediately before removing an owned stage directory."""


def _after_prerequisite_read(relative: str, raw: bytes) -> None:
    """Test seam after prerequisite bytes and digest become immutable inputs."""


def generate_vertical_slice(root: str | Path, request: VerticalSliceRequest) -> dict[str, Any]:
    """Build and atomically publish one target-free leg/model package.

    The operation reads frozen public metadata and source bindings only. It has
    no model, tokenizer, sealed-target, CCP, Docker, or network capability.
    """

    repository = _repository_root(root)
    destination_relative = _validate_request(request)
    source_tree = _git_tree_for_head(repository, request.implementation_source_head)
    _require_checkout_state(repository, request.implementation_source_head, source_tree, frozenset())
    with _RepositoryReader(repository) as prerequisites:
        documents, pair = _build_documents(
            prerequisites, request, source_tree, destination_relative,
        )
        encoded = {name: _canonical_json_bytes(value) for name, value in documents.items()}
        _validate_built_documents(prerequisites, documents, encoded, destination_relative)

    parent = _open_package_parent(repository, destination_relative, create=True)
    transaction: _PublicationTransaction | None = None
    try:
        _revalidate_chain(parent)
        if _exists_at(parent.fd, parent.destination_name):
            raise A0XVerticalSliceError(OUTPUT_EXISTS)
        transaction = _create_stage(parent)
        expected = {name: (raw, _sha256(raw)) for name, raw in encoded.items()}
        for name in _MEMBER_NAMES:
            _write_member_at(transaction.stage_fd, name, expected[name][0])
        _assert_stage(transaction.stage_fd, expected)
        os.fsync(transaction.stage_fd)
        os.fsync(parent.fd)
        _before_publish(transaction)
        _revalidate_chain(parent)
        _assert_owned_stage(transaction)
        if _exists_at(parent.fd, parent.destination_name):
            raise A0XVerticalSliceError(OUTPUT_EXISTS)
        allowed_stage = frozenset(
            f"{destination_relative.parent.as_posix()}/{transaction.stage_name}/{name}"
            for name in _MEMBER_NAMES
        )
        _require_checkout_state(
            repository,
            request.implementation_source_head,
            source_tree,
            allowed_stage,
        )
        try:
            _darwin_publish_exclusive_at(parent.fd, transaction.stage_name, parent.destination_name)
        except FileExistsError as error:
            raise A0XVerticalSliceError(OUTPUT_EXISTS) from error
        transaction.state = "published"
        _after_publish(transaction)
        _assert_published_chain(transaction)
        _assert_published(transaction)
        _assert_stage(transaction.stage_fd, expected)
        _assert_published_chain(transaction)
        os.fsync(parent.fd)
        transaction.state = "committed"
    except A0XVerticalSliceError as error:
        _cleanup_after_failure(transaction, error)
    except Exception as error:
        wrapped = A0XVerticalSliceError(PUBLICATION_FAILED)
        _cleanup_after_failure(transaction, wrapped, cause=error)
    finally:
        if transaction is not None:
            os.close(transaction.stage_fd)
        _close_parent(parent)

    written = [
        {
            "path": f"{destination_relative.as_posix()}/{name}",
            "sha256": _sha256(encoded[name]),
        }
        for name in _MEMBER_NAMES
    ]
    return {
        "artifact_class": "a0x-vertical-slice-generation-receipt",
        "generator_profile": GENERATOR_PROFILE,
        "repository": REPOSITORY,
        "implementation_source_head": request.implementation_source_head,
        "implementation_source_tree": source_tree,
        "pair": pair,
        "written": written,
        "sealed_target_content_reads": 0,
        "model_loads": 0,
        "tokenizer_constructions": 0,
        "ccp_invocations": 0,
        "network_operations": 0,
        "remote_mutations": 0,
    }


def load_vertical_slice(root: str | Path, dossier_relative: str) -> dict[str, Any]:
    """Load and validate one exact pair-scoped dossier package read-only."""

    repository = _repository_root(root)
    if not isinstance(dossier_relative, str):
        raise A0XVerticalSliceError(INVALID_REQUEST)
    match = _DOSSIER_PATH.fullmatch(dossier_relative)
    if match is None or PurePosixPath(dossier_relative).as_posix() != dossier_relative:
        raise A0XVerticalSliceError(INVALID_REQUEST)
    head, leg_value, model_key = match.groups()
    package_relative = PurePosixPath(dossier_relative).parent
    expected_tree = _git_tree_for_head(repository, head)
    allowed_package = frozenset(
        f"{package_relative.as_posix()}/{name}" for name in _MEMBER_NAMES
    )
    _require_checkout_state(repository, head, expected_tree, allowed_package)
    parent = _open_package_parent(repository, package_relative, create=False, package_is_parent=True)
    try:
        _revalidate_chain(parent)
        raw = _read_exact_package(parent.fd)
        _revalidate_chain(parent)
    finally:
        _close_parent(parent)

    try:
        documents = {name: _parse_json_object(value) for name, value in raw.items()}
    except Exception as error:
        raise A0XVerticalSliceError(VALIDATION_FAILED) from error
    if any(raw[name] != _canonical_json_bytes(documents[name]) for name in _MEMBER_NAMES):
        raise A0XVerticalSliceError(VALIDATION_FAILED)

    protocol = documents["protocol.json"]
    implementation = documents["implementation.json"]
    freeze = documents["freeze.json"]
    dossier = documents["approval-dossier.json"]
    manifest = documents["slice-manifest.json"]
    expected_members = {
        name: {
            "path": f"{package_relative.as_posix()}/{name}",
            "sha256": _sha256(raw[name]),
        }
        for name in _NON_MANIFEST_NAMES
    }
    with _RepositoryReader(repository) as prerequisites:
        _validate_schema(prerequisites, manifest, "a0x-vertical-slice-manifest.schema.json")
        _validate_schema(prerequisites, protocol, "a0x-protocol.schema.json")
        _validate_schema(prerequisites, implementation, "a0x-implementation.schema.json")
        _validate_schema(prerequisites, freeze, "a0x-freeze-manifest.schema.json")
        _validate_schema(prerequisites, dossier, "a0x-authorization-dossier.schema.json")

        expected_relative = _package_relative(head, Leg(leg_value), model_key)
        if package_relative != expected_relative:
            raise A0XVerticalSliceError(VALIDATION_FAILED)
        cards = _model_cards_by_key(prerequisites)
        card = cards.get(model_key)
        if card is None:
            raise A0XVerticalSliceError(VALIDATION_FAILED)
        expected_pair = _pair_binding(Leg(leg_value), card, _sha256(raw["freeze.json"]))
        if (
            manifest.get("artifact_class") != "a0x-vertical-slice-manifest"
            or manifest.get("generator_profile") != GENERATOR_PROFILE
            or manifest.get("repository") != REPOSITORY
            or manifest.get("implementation_source_head") != head
            or manifest.get("implementation_source_tree") != expected_tree
            or manifest.get("package_scope") != PACKAGE_SCOPE
            or manifest.get("pair") != expected_pair
            or manifest.get("members") != expected_members
            or dossier.get("pair_binding") != expected_pair
            or dossier.get("implementation_source_head") != head
            or freeze.get("protocol_sha256") != _sha256(raw["protocol.json"])
            or freeze.get("implementation_sha256") != _sha256(raw["implementation.json"])
            or protocol.get("identity") != freeze.get("identity")
            or implementation.get("identity") != freeze.get("identity")
        ):
            raise A0XVerticalSliceError(VALIDATION_FAILED)
        material = prerequisites.read("experiments/a0x-six-model/material-execution-contract.json")
        if dossier.get("material_contract_raw_sha256") != material.sha256:
            raise A0XVerticalSliceError(VALIDATION_FAILED)
        _validate_selected_sources(prerequisites, Leg(leg_value), protocol, implementation)
    _require_checkout_state(repository, head, expected_tree, allowed_package)
    return {
        "manifest": manifest,
        "protocol": protocol,
        "implementation": implementation,
        "freeze": freeze,
        "dossier": dossier,
        "pair": expected_pair,
        "dossier_relative": dossier_relative,
    }


def _validate_request(request: VerticalSliceRequest) -> PurePosixPath:
    if (
        not isinstance(request, VerticalSliceRequest)
        or not isinstance(request.leg, Leg)
        or not isinstance(request.model_key, str)
        or _MODEL_KEY.fullmatch(request.model_key) is None
        or not isinstance(request.implementation_source_head, str)
        or _REVISION.fullmatch(request.implementation_source_head) is None
        or not isinstance(request.output_root, str)
    ):
        raise A0XVerticalSliceError(INVALID_REQUEST)
    expected = _package_relative(
        request.implementation_source_head, request.leg, request.model_key,
    )
    if request.output_root != expected.as_posix() or PurePosixPath(request.output_root) != expected:
        raise A0XVerticalSliceError(INVALID_REQUEST)
    return expected


def _repository_root(root: str | Path) -> Path:
    try:
        repository = Path(root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError) as error:
        raise A0XVerticalSliceError(INVALID_REQUEST) from error
    if not repository.is_dir():
        raise A0XVerticalSliceError(INVALID_REQUEST)
    return repository


def _package_relative(head: str, leg: Leg, model_key: str) -> PurePosixPath:
    return PurePosixPath(
        "experiments", "a0x-six-model", "vertical-slices", head, leg.value, model_key,
    )


def _build_documents(
    prerequisites: _RepositoryReader,
    request: VerticalSliceRequest,
    source_tree: str,
    package_relative: PurePosixPath,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    try:
        cards = _model_cards_by_key(prerequisites)
        card = cards.get(request.model_key)
        if card is None:
            raise A0XVerticalSliceError(INVALID_REQUEST)
        spec = _LEG_SOURCES[request.leg]
        identity = _leg_identity_from_prerequisites(prerequisites, request.leg, spec)
        source_protocol_path = str(spec["protocol"])
        source_implementation_path = str(spec["implementation"])
        source_protocol_file = prerequisites.read(source_protocol_path)
        source_implementation_file = prerequisites.read(source_implementation_path)
        source_protocol = _parse_json_object(source_protocol_file.raw)
        source_implementation = _parse_json_object(source_implementation_file.raw)
        protocol = {
            **_COMMON,
            "artifact_class": "a0x-leg-protocol",
            "identity": identity,
            "protocol_status": "frozen",
            "endpoint_indices": [0, 2, 4, 6] if request.leg is Leg.A0 else [6],
            "descriptive_final_block_endpoint": {
                "model_card_index_field": "final_transformer_block_tuple_index",
                "required_equal_model_card_field": "num_hidden_layers",
                "role": "descriptive_sensitivity",
                "rescues_primary": False,
            },
            "source_protocol_path": source_protocol_path,
            "source_protocol_raw_sha256": source_protocol_file.sha256,
            "inherited_rules": _copy_fields(
                source_protocol, spec["protocol_fields"], f"{request.leg.value} protocol",
            ),
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
        }
        implementation = {
            **_COMMON,
            "artifact_class": "a0x-leg-implementation",
            "identity": identity,
            "implementation_status": "frozen_before_model_output",
            "source_implementation_path": source_implementation_path,
            "source_implementation_raw_sha256": source_implementation_file.sha256,
            "inherited_rules": _copy_fields(
                source_implementation,
                spec["implementation_fields"],
                f"{request.leg.value} implementation",
            ),
            "sealed_targets_accessed": False,
            "model_output_accessed": False,
            "implementation_paths": list(_IMPLEMENTATION_PATHS),
            "implementation_files": [
                prerequisites.read(relative).as_binding() for relative in _IMPLEMENTATION_PATHS
            ],
        }
        protocol_raw = _canonical_json_bytes(protocol)
        implementation_raw = _canonical_json_bytes(implementation)
        freeze = {
            **_COMMON,
            "artifact_class": "a0x-leg-freeze-manifest",
            "identity": identity,
            "protocol_sha256": _sha256(protocol_raw),
            "implementation_sha256": _sha256(implementation_raw),
            "freeze_status": "frozen",
        }
        freeze_raw = _canonical_json_bytes(freeze)
        pair = _pair_binding(request.leg, card, _sha256(freeze_raw))
        dossier = {
            **_COMMON,
            "artifact_class": "a0x-authorization-dossier",
            "commitment_profile": APPROVAL_DOSSIER_PROFILE,
            "pair_binding": pair,
            "dossier_status": "approval_requested",
            "implementation_source_head": request.implementation_source_head,
            "material_contract_path": "experiments/a0x-six-model/material-execution-contract.json",
            "material_contract_raw_sha256": prerequisites.read(
                "experiments/a0x-six-model/material-execution-contract.json"
            ).sha256,
            "runtime_authorization_path": (
                f".a0x-runtime/authorizations/{request.leg.value}/{request.model_key}/"
                f"{pair['run_id']}.json"
            ),
        }
        members_raw = {
            "protocol.json": protocol_raw,
            "implementation.json": implementation_raw,
            "freeze.json": freeze_raw,
            "approval-dossier.json": _canonical_json_bytes(dossier),
        }
        manifest = {
            "artifact_class": "a0x-vertical-slice-manifest",
            "generator_profile": GENERATOR_PROFILE,
            "repository": REPOSITORY,
            "implementation_source_head": request.implementation_source_head,
            "implementation_source_tree": source_tree,
            "package_scope": PACKAGE_SCOPE,
            "pair": pair,
            "members": {
                name: {
                    "path": f"{package_relative.as_posix()}/{name}",
                    "sha256": _sha256(raw),
                }
                for name, raw in members_raw.items()
            },
        }
        return {
            "protocol.json": protocol,
            "implementation.json": implementation,
            "freeze.json": freeze,
            "approval-dossier.json": dossier,
            "slice-manifest.json": manifest,
        }, pair
    except A0XVerticalSliceError:
        raise
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise A0XVerticalSliceError(INVALID_REQUEST) from error


def _leg_identity_from_prerequisites(
    prerequisites: _RepositoryReader,
    leg: Leg,
    spec: Mapping[str, Any],
) -> dict[str, str]:
    tree = prerequisites.object(str(spec["protected_tree"]))
    protected_sha = tree.get("protected_tree_sha256")
    if not isinstance(protected_sha, str) or re.fullmatch(r"[a-f0-9]{64}", protected_sha) is None:
        raise A0XVerticalSliceError(VALIDATION_FAILED)
    selection = prerequisites.read(str(spec["selection"]))
    return {
        "leg": leg.value,
        "protocol_id": f"a0x-{leg.value}-six-model-v1",
        "protected_tree_sha256": protected_sha,
        "selection_corpus_sha256": selection.sha256,
        "source_base_commit": "188eb65b5e249923baddadeba52659f07fcd1609",
    }


def _model_cards_by_key(prerequisites: _RepositoryReader) -> dict[str, dict[str, Any]]:
    registry = prerequisites.object("experiments/a0x-six-model/model-registry.json")
    declared = registry.get("cards")
    if (
        not isinstance(declared, list)
        or len(declared) != 6
        or len(set(value for value in declared if isinstance(value, str))) != 6
        or not all(isinstance(value, str) for value in declared)
    ):
        raise A0XVerticalSliceError(INVALID_REQUEST)
    by_key: dict[str, dict[str, Any]] = {}
    for relative in declared:
        card_relative = f"experiments/a0x-six-model/{_safe_prerequisite_relative(relative)}"
        card = prerequisites.object(card_relative)
        key = card.get("model_key")
        if (
            not isinstance(key, str)
            or _MODEL_KEY.fullmatch(key) is None
            or key in by_key
            or PurePosixPath(relative).stem != key
            or card.get("card_path") != card_relative
            or not isinstance(card.get("model_id"), str)
            or not card["model_id"]
            or not isinstance(card.get("revision"), str)
            or _REVISION.fullmatch(card["revision"]) is None
            or not isinstance(card.get("hidden_size"), int)
            or isinstance(card.get("hidden_size"), bool)
            or card["hidden_size"] < 1
        ):
            raise A0XVerticalSliceError(INVALID_REQUEST)
        by_key[key] = card
    if len(by_key) != len(declared):
        raise A0XVerticalSliceError(INVALID_REQUEST)
    return by_key


def _pair_binding(leg: Leg, card: Mapping[str, Any], freeze_sha256: str) -> dict[str, Any]:
    model_key = str(card["model_key"])
    revision = str(card["revision"])
    run_id = f"a0x-{leg.value}-{model_key}-{revision[:8]}-attempt-01"
    return PairBinding(
        binding_profile="a0x-pair-scope-v2",
        leg=leg,
        leg_freeze_sha256=freeze_sha256,
        model_key=model_key,
        model_id=str(card["model_id"]),
        revision=revision,
        run_id=run_id,
        output_path=derive_pair_output_path(leg, model_key, run_id),
        dense_bound=compute_dense_bound(leg, cases=48, hidden_width=int(card["hidden_size"])),
    ).as_mapping()


def _validate_built_documents(
    prerequisites: _RepositoryReader,
    documents: Mapping[str, Mapping[str, Any]],
    encoded: Mapping[str, bytes],
    package_relative: PurePosixPath,
) -> None:
    if set(documents) != set(_MEMBER_NAMES) or set(encoded) != set(_MEMBER_NAMES):
        raise A0XVerticalSliceError(VALIDATION_FAILED)
    for name, schema_name in (
        ("protocol.json", "a0x-protocol.schema.json"),
        ("implementation.json", "a0x-implementation.schema.json"),
        ("freeze.json", "a0x-freeze-manifest.schema.json"),
        ("approval-dossier.json", "a0x-authorization-dossier.schema.json"),
        ("slice-manifest.json", "a0x-vertical-slice-manifest.schema.json"),
    ):
        _validate_schema(prerequisites, documents[name], schema_name)
    manifest = documents["slice-manifest.json"]
    expected_members = {
        name: {
            "path": f"{package_relative.as_posix()}/{name}",
            "sha256": _sha256(encoded[name]),
        }
        for name in _NON_MANIFEST_NAMES
    }
    if manifest.get("members") != expected_members:
        raise A0XVerticalSliceError(VALIDATION_FAILED)


def _validate_schema(
    prerequisites: _RepositoryReader,
    value: Mapping[str, Any],
    schema_name: str,
) -> None:
    schema = prerequisites.object(f"schemas/{schema_name}")
    issues = validate(dict(value), schema)
    if issues:
        raise A0XVerticalSliceError(VALIDATION_FAILED)


def _validate_selected_sources(
    prerequisites: _RepositoryReader,
    leg: Leg,
    protocol: Mapping[str, Any],
    implementation: Mapping[str, Any],
) -> None:
    spec = _LEG_SOURCES[leg]
    try:
        source_protocol_file = prerequisites.read(str(spec["protocol"]))
        source_implementation_file = prerequisites.read(str(spec["implementation"]))
        source_protocol = _parse_json_object(source_protocol_file.raw)
        source_implementation = _parse_json_object(source_implementation_file.raw)
        if (
            protocol.get("identity") != _leg_identity_from_prerequisites(prerequisites, leg, spec)
            or protocol.get("source_protocol_path") != spec["protocol"]
            or protocol.get("source_protocol_raw_sha256") != source_protocol_file.sha256
            or protocol.get("inherited_rules")
            != _copy_fields(source_protocol, spec["protocol_fields"], f"{leg.value} protocol")
            or implementation.get("source_implementation_path") != spec["implementation"]
            or implementation.get("source_implementation_raw_sha256") != source_implementation_file.sha256
            or implementation.get("inherited_rules")
            != _copy_fields(
                source_implementation, spec["implementation_fields"], f"{leg.value} implementation",
            )
            or implementation.get("implementation_paths") != list(_IMPLEMENTATION_PATHS)
            or implementation.get("implementation_files")
            != [prerequisites.read(relative).as_binding() for relative in _IMPLEMENTATION_PATHS]
        ):
            raise A0XVerticalSliceError(VALIDATION_FAILED)
    except A0XVerticalSliceError:
        raise
    except (KeyError, OSError, TypeError, ValueError) as error:
        raise A0XVerticalSliceError(VALIDATION_FAILED) from error


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XVerticalSliceError(VALIDATION_FAILED) from error


def _safe_prerequisite_relative(relative: str) -> str:
    if not isinstance(relative, str):
        raise A0XVerticalSliceError(VALIDATION_FAILED)
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or path.as_posix() != relative
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise A0XVerticalSliceError(VALIDATION_FAILED)
    return relative


def _parse_json_object(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or raw.startswith(b"\xef\xbb\xbf"):
        raise A0XVerticalSliceError(VALIDATION_FAILED)

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise A0XVerticalSliceError(VALIDATION_FAILED) from error
    if not isinstance(value, dict):
        raise A0XVerticalSliceError(VALIDATION_FAILED)
    return value


def _git_tree_for_head(repository: Path, head: str) -> str:
    if _REVISION.fullmatch(head) is None:
        raise A0XVerticalSliceError(INVALID_REQUEST)
    try:
        environment = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
        common = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "check": False,
            "timeout": 10,
            "env": environment,
        }
        commit = subprocess.run(
            ["/usr/bin/git", "-C", os.fspath(repository), "rev-parse", "--verify", f"{head}^{{commit}}"],
            **common,
        )
        completed = subprocess.run(
            ["/usr/bin/git", "-C", os.fspath(repository), "rev-parse", "--verify", f"{head}^{{tree}}"],
            **common,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise A0XVerticalSliceError(INVALID_REQUEST) from error
    resolved_commit = (
        commit.stdout.decode("ascii", errors="strict").strip() if commit.returncode == 0 else ""
    )
    value = completed.stdout.decode("ascii", errors="strict").strip() if completed.returncode == 0 else ""
    if resolved_commit != head:
        raise A0XVerticalSliceError(INVALID_REQUEST)
    if _REVISION.fullmatch(value) is None:
        raise A0XVerticalSliceError(INVALID_REQUEST)
    return value


def _checkout_state(
    repository: Path,
    allowed_untracked: frozenset[str],
) -> tuple[str, str, bool]:
    """Return exact checkout identity and whether only owned output is dirty."""

    try:
        head_raw = _git_output(repository, ("rev-parse", "--verify", "HEAD^{commit}"))
        tree_raw = _git_output(repository, ("rev-parse", "--verify", "HEAD^{tree}"))
        status_raw = _git_output(
            repository,
            ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"),
        )
        head = head_raw.decode("ascii").strip()
        tree = tree_raw.decode("ascii").strip()
        records = tuple(
            value.decode("utf-8") for value in status_raw.split(b"\0") if value
        )
    except (UnicodeDecodeError, OSError, subprocess.SubprocessError) as error:
        raise A0XVerticalSliceError(INVALID_REQUEST) from error
    allowed_records = {f"?? {relative}" for relative in allowed_untracked}
    clean = all(record in allowed_records for record in records)
    return head, tree, clean


def _require_checkout_state(
    repository: Path,
    expected_head: str,
    expected_tree: str,
    allowed_untracked: frozenset[str],
) -> None:
    observed_head, observed_tree, clean = _checkout_state(repository, allowed_untracked)
    if observed_head != expected_head or observed_tree != expected_tree or not clean:
        raise A0XVerticalSliceError(INVALID_REQUEST)


def _git_output(repository: Path, arguments: tuple[str, ...]) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    try:
        completed = subprocess.run(
            ["/usr/bin/git", "-C", os.fspath(repository), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise A0XVerticalSliceError(INVALID_REQUEST) from error
    if completed.returncode != 0:
        raise A0XVerticalSliceError(INVALID_REQUEST)
    return completed.stdout


def _open_package_parent(
    repository: Path,
    relative: PurePosixPath,
    *,
    create: bool,
    package_is_parent: bool = False,
) -> _PackageParent:
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise A0XVerticalSliceError(INVALID_REQUEST)
    if not all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")):
        raise A0XVerticalSliceError(PUBLICATION_UNSUPPORTED)
    if not package_is_parent:
        return _open_destination_parent(
            repository,
            PurePosixPath(*relative.parts[:-1]),
            relative.name,
            create=create,
        )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptors: list[int] = []
    chain: list[tuple[int, str, tuple[int, int]]] = []
    try:
        current = os.open(repository, flags)
        descriptors.append(current)
        for part in relative.parts:
            try:
                child = os.open(part, flags, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o755, dir_fd=current)
                os.fsync(current)
                child = os.open(part, flags, dir_fd=current)
            descriptors.append(child)
            identity = _fd_identity(child)
            chain.append((current, part, identity))
            current = child
        return _PackageParent(tuple(descriptors), tuple(chain), current, relative.name)
    except A0XVerticalSliceError:
        _close_descriptors(tuple(descriptors))
        raise
    except (AttributeError, OSError) as error:
        _close_descriptors(tuple(descriptors))
        code = INVALID_REQUEST if not create else PUBLICATION_FAILED
        raise A0XVerticalSliceError(code) from error


def _open_destination_parent(
    repository: Path, parent_relative: PurePosixPath, destination_name: str, *, create: bool,
) -> _PackageParent:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptors: list[int] = []
    chain: list[tuple[int, str, tuple[int, int]]] = []
    try:
        current = os.open(repository, flags)
        descriptors.append(current)
        for part in parent_relative.parts:
            try:
                child = os.open(part, flags, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o755, dir_fd=current)
                os.fsync(current)
                child = os.open(part, flags, dir_fd=current)
            descriptors.append(child)
            chain.append((current, part, _fd_identity(child)))
            current = child
        return _PackageParent(tuple(descriptors), tuple(chain), current, destination_name)
    except A0XVerticalSliceError:
        _close_descriptors(tuple(descriptors))
        raise
    except (AttributeError, OSError) as error:
        _close_descriptors(tuple(descriptors))
        code = INVALID_REQUEST if not create else PUBLICATION_FAILED
        raise A0XVerticalSliceError(code) from error


def _create_stage(parent: _PackageParent) -> _PublicationTransaction:
    stage_name = ".a0x-vertical-slice-" + secrets.token_hex(16)
    try:
        os.mkdir(stage_name, 0o700, dir_fd=parent.fd)
        created = os.stat(stage_name, dir_fd=parent.fd, follow_symlinks=False)
        if not stat.S_ISDIR(created.st_mode):
            raise A0XVerticalSliceError(PUBLICATION_FAILED)
        stage_fd = os.open(
            stage_name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent.fd,
        )
        os.fchmod(stage_fd, 0o700)
        identity = _fd_identity(stage_fd)
        if identity != (created.st_dev, created.st_ino):
            os.close(stage_fd)
            raise A0XVerticalSliceError(PUBLICATION_FAILED)
        return _PublicationTransaction(parent, stage_name, stage_fd, identity)
    except A0XVerticalSliceError:
        if "created" in locals():
            try:
                current = os.stat(stage_name, dir_fd=parent.fd, follow_symlinks=False)
                if (
                    stat.S_ISDIR(current.st_mode)
                    and (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino)
                ):
                    os.rmdir(stage_name, dir_fd=parent.fd)
            except OSError:
                pass
        raise
    except OSError as error:
        if "created" in locals():
            try:
                current = os.stat(stage_name, dir_fd=parent.fd, follow_symlinks=False)
                if (
                    stat.S_ISDIR(current.st_mode)
                    and (current.st_dev, current.st_ino) == (created.st_dev, created.st_ino)
                ):
                    os.rmdir(stage_name, dir_fd=parent.fd)
            except OSError:
                pass
        raise A0XVerticalSliceError(PUBLICATION_FAILED) from error


def _write_member_at(stage_fd: int, name: str, raw: bytes) -> None:
    descriptor = os.open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
        dir_fd=stage_fd,
    )
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise OSError(errno.EIO, "short write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _assert_stage(stage_fd: int, expected: Mapping[str, tuple[bytes, str]]) -> None:
    try:
        names = set(os.listdir(stage_fd))
        if names != set(_MEMBER_NAMES) or set(expected) != set(_MEMBER_NAMES):
            raise A0XVerticalSliceError(PUBLICATION_FAILED)
        for name in _MEMBER_NAMES:
            raw, digest = expected[name]
            observed = _read_regular_at(stage_fd, name, len(raw), PUBLICATION_FAILED)
            if observed != raw or _sha256(observed) != digest:
                raise A0XVerticalSliceError(PUBLICATION_FAILED)
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(PUBLICATION_FAILED) from error


def _read_exact_package(package_fd: int) -> dict[str, bytes]:
    try:
        if set(os.listdir(package_fd)) != set(_MEMBER_NAMES):
            raise A0XVerticalSliceError(VALIDATION_FAILED)
        return {
            name: _read_regular_at(package_fd, name, _MAX_DOCUMENT_BYTES, VALIDATION_FAILED)
            for name in _MEMBER_NAMES
        }
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(VALIDATION_FAILED) from error


def _read_regular_at(parent_fd: int, name: str, maximum: int, code: str) -> bytes:
    try:
        first = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(first.st_mode)
            or first.st_nlink != 1
            or first.st_size < 1
            or first.st_size > maximum
        ):
            raise A0XVerticalSliceError(code)
        descriptor = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd,
        )
        try:
            checked = os.fstat(descriptor)
            if (
                not stat.S_ISREG(checked.st_mode)
                or checked.st_nlink != 1
                or (checked.st_dev, checked.st_ino, checked.st_size)
                != (first.st_dev, first.st_ino, first.st_size)
            ):
                raise A0XVerticalSliceError(code)
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            final = os.fstat(descriptor)
            if (
                len(raw) != first.st_size
                or len(raw) > maximum
                or final.st_nlink != 1
                or (final.st_dev, final.st_ino, final.st_size)
                != (first.st_dev, first.st_ino, first.st_size)
            ):
                raise A0XVerticalSliceError(code)
            return raw
        finally:
            os.close(descriptor)
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(code) from error


def _revalidate_chain(parent: _PackageParent) -> None:
    try:
        for descriptor, name, identity in parent.chain:
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or (metadata.st_dev, metadata.st_ino) != identity
            ):
                raise A0XVerticalSliceError(PUBLICATION_FAILED)
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(PUBLICATION_FAILED) from error


def _fd_identity(descriptor: int) -> tuple[int, int]:
    metadata = os.fstat(descriptor)
    return metadata.st_dev, metadata.st_ino


def _exists_at(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False
    except OSError as error:
        raise A0XVerticalSliceError(PUBLICATION_FAILED) from error


def _assert_owned_stage(transaction: _PublicationTransaction) -> None:
    try:
        metadata = os.stat(
            transaction.stage_name, dir_fd=transaction.parent.fd, follow_symlinks=False,
        )
    except OSError as error:
        raise A0XVerticalSliceError(PUBLICATION_FAILED) from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != transaction.stage_identity
    ):
        raise A0XVerticalSliceError(PUBLICATION_FAILED)


def _assert_published(transaction: _PublicationTransaction) -> None:
    if _exists_at(transaction.parent.fd, transaction.stage_name):
        raise A0XVerticalSliceError(PUBLICATION_FAILED)
    try:
        metadata = os.stat(
            transaction.parent.destination_name,
            dir_fd=transaction.parent.fd,
            follow_symlinks=False,
        )
    except FileNotFoundError as error:
        raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST) from error
    except OSError as error:
        raise A0XVerticalSliceError(PUBLICATION_FAILED) from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != transaction.stage_identity
    ):
        transaction.state = "ownership_lost"
        raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)


def _assert_published_chain(transaction: _PublicationTransaction) -> None:
    try:
        _revalidate_chain(transaction.parent)
    except A0XVerticalSliceError as error:
        transaction.state = "ownership_lost"
        raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST) from error


def _cleanup_after_failure(
    transaction: _PublicationTransaction | None,
    original: A0XVerticalSliceError,
    *,
    cause: Exception | None = None,
) -> None:
    try:
        _cleanup_transaction(transaction)
    except A0XVerticalSliceError as cleanup_error:
        if cleanup_error.code == PUBLICATION_OWNERSHIP_LOST:
            raise cleanup_error from (cause or original)
        raise original from (cause or cleanup_error)
    raise original from cause


def _cleanup_transaction(transaction: _PublicationTransaction | None) -> None:
    if transaction is None:
        return
    if transaction.state == "ownership_lost":
        raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)
    owned_name: str | None = None
    for name in (transaction.stage_name, transaction.parent.destination_name):
        try:
            metadata = os.stat(name, dir_fd=transaction.parent.fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError as error:
            raise A0XVerticalSliceError(PUBLICATION_FAILED) from error
        if (metadata.st_dev, metadata.st_ino) == transaction.stage_identity:
            if not stat.S_ISDIR(metadata.st_mode) or owned_name is not None:
                raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)
            owned_name = name
    if owned_name is None:
        raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)
    try:
        names = set(os.listdir(transaction.stage_fd))
        if not names.issubset(set(_MEMBER_NAMES)):
            raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)
        for name in names:
            metadata = os.stat(name, dir_fd=transaction.stage_fd, follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)
            os.unlink(name, dir_fd=transaction.stage_fd)
        _before_owned_rmdir(transaction, owned_name)
        metadata = os.stat(owned_name, dir_fd=transaction.parent.fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != transaction.stage_identity
        ):
            raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST)
        os.rmdir(owned_name, dir_fd=transaction.parent.fd)
        os.fsync(transaction.parent.fd)
    except A0XVerticalSliceError:
        raise
    except (FileNotFoundError, OSError) as error:
        raise A0XVerticalSliceError(PUBLICATION_OWNERSHIP_LOST) from error


def _close_parent(parent: _PackageParent) -> None:
    _close_descriptors(parent.descriptors)


def _close_descriptors(descriptors: tuple[int, ...]) -> None:
    for descriptor in reversed(tuple(dict.fromkeys(descriptors))):
        try:
            os.close(descriptor)
        except OSError:
            pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _darwin_publish_exclusive_at(parent_fd: int, stage_name: str, destination_name: str) -> None:
    if sys.platform != "darwin":
        raise A0XVerticalSliceError(PUBLICATION_UNSUPPORTED)
    try:
        function = ctypes.CDLL(None, use_errno=True).renameatx_np
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(
            parent_fd,
            os.fsencode(stage_name),
            parent_fd,
            os.fsencode(destination_name),
            RENAME_EXCL | RENAME_NOFOLLOW_ANY,
        )
    except (AttributeError, OSError) as error:
        raise A0XVerticalSliceError(PUBLICATION_UNSUPPORTED) from error
    if result:
        current_errno = ctypes.get_errno()
        if current_errno == errno.EEXIST:
            raise A0XVerticalSliceError(OUTPUT_EXISTS)
        raise A0XVerticalSliceError(PUBLICATION_FAILED)


def generate_vertical_runtime_package(
    root: str | Path, request: VerticalRuntimePackageRequest,
) -> VerticalPackageBinding:
    """Publish one v2 P0 envelope without changing tracked source bytes."""
    repository = _repository_root(root)
    envelope_relative = _validate_v2_request(request)
    observed_tree = _git_tree_for_head(repository, request.qualified_source_head)
    if observed_tree != request.qualified_source_tree:
        raise A0XVerticalSliceError(V2_INVALID_REQUEST)
    _require_v2_checkout(repository, request.qualified_source_head, request.qualified_source_tree)
    legacy_request = VerticalSliceRequest(
        leg=request.leg,
        model_key=request.model_key,
        implementation_source_head=request.qualified_source_head,
        output_root=_package_relative(
            request.qualified_source_head, request.leg, request.model_key,
        ).as_posix(),
    )
    with _RepositoryReader(repository) as prerequisites:
        documents, pair_mapping = _build_documents(
            prerequisites, legacy_request, request.qualified_source_tree, envelope_relative / "package",
        )
        pair = PairBinding.from_mapping(pair_mapping)
        preliminary = {
            name: _canonical_json_bytes(documents[name]) for name in V2_MEMBER_NAMES[:-1]
        }
        manifest = {
            "artifact_class": "a0x-vertical-slice-manifest-v2",
            "generator_profile": V2_GENERATOR_PROFILE,
            "repository": REPOSITORY,
            "qualified_source": {
                "head": request.qualified_source_head,
                "tree": request.qualified_source_tree,
                "ref": "refs/heads/main",
            },
            "pair_binding": pair.as_mapping(),
            "members": [
                {"name": name, "size": len(preliminary[name]), "sha256": _sha256(preliminary[name])}
                for name in V2_MEMBER_NAMES[:-1]
            ],
        }
        documents["slice-manifest.json"] = manifest
        encoded = {name: _canonical_json_bytes(documents[name]) for name in V2_MEMBER_NAMES}
        _validate_v2_documents(prerequisites, documents, encoded, request, pair)

    members = [
        {"name": name, "size": len(encoded[name]), "sha256": _sha256(encoded[name])}
        for name in V2_MEMBER_NAMES
    ]
    commitment = build_vertical_package_commitment(
        qualified_source={
            "head": request.qualified_source_head,
            "tree": request.qualified_source_tree,
            "ref": "refs/heads/main",
        },
        pair=pair,
        members=members,
        generator={"profile": V2_GENERATOR_PROFILE, "repository": REPOSITORY},
        authorization_id=request.authorization_id,
        attempt_id=request.attempt_id,
    )
    commitment_raw = _canonical_json_bytes(commitment)
    _publish_v2_envelope(repository, envelope_relative, encoded, commitment_raw, request)
    package_relative = envelope_relative / "package"
    dossier_relative = package_relative / "approval-dossier.json"
    return VerticalPackageBinding(
        envelope_path=envelope_relative.as_posix(),
        package_path=package_relative.as_posix(),
        commitment_path=(envelope_relative / "p0-commitment.json").as_posix(),
        commitment_raw_sha256=_sha256(commitment_raw),
        package_commitment_sha256=str(commitment["package_commitment_sha256"]),
        dossier_path=dossier_relative.as_posix(),
        dossier_sha256=_sha256(encoded["approval-dossier.json"]),
        qualified_source_head=request.qualified_source_head,
        qualified_source_tree=request.qualified_source_tree,
        leg=request.leg,
        model_key=request.model_key,
        model_revision=pair.revision,
        pair_binding=pair,
    )


def load_vertical_runtime_package(
    root: str | Path, binding: VerticalPackageBinding,
) -> dict[str, Any]:
    """Descriptor-relatively reload and fully validate one v2 P0 envelope."""
    repository = _repository_root(root)
    _validate_v2_binding(binding)
    envelope_relative = PurePosixPath(binding.envelope_path)
    _require_v2_checkout(repository, binding.qualified_source_head, binding.qualified_source_tree)
    parent = _open_package_parent(repository, envelope_relative, create=False, package_is_parent=True)
    package_fd: int | None = None
    try:
        _revalidate_chain(parent)
        if set(os.listdir(parent.fd)) != {"package", "p0-commitment.json"}:
            raise A0XVerticalSliceError(V2_VALIDATION_FAILED)
        package_fd = os.open(
            "package", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent.fd,
        )
        if set(os.listdir(package_fd)) != set(V2_MEMBER_NAMES):
            raise A0XVerticalSliceError(V2_VALIDATION_FAILED)
        raw = {
            name: _read_regular_at(package_fd, name, _MAX_DOCUMENT_BYTES, V2_VALIDATION_FAILED)
            for name in V2_MEMBER_NAMES
        }
        commitment_raw = _read_regular_at(
            parent.fd, "p0-commitment.json", _MAX_DOCUMENT_BYTES, V2_VALIDATION_FAILED,
        )
        _revalidate_chain(parent)
    except A0XVerticalSliceError as error:
        if error.code == V2_VALIDATION_FAILED:
            raise
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED) from error
    except OSError as error:
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED) from error
    finally:
        if package_fd is not None:
            os.close(package_fd)
        _close_parent(parent)
    try:
        documents = {name: _parse_json_object(raw[name]) for name in V2_MEMBER_NAMES}
        commitment = _parse_json_object(commitment_raw)
        if any(raw[name] != _canonical_json_bytes(documents[name]) for name in V2_MEMBER_NAMES):
            raise ValueError("noncanonical member")
        if commitment_raw != _canonical_json_bytes(commitment):
            raise ValueError("noncanonical commitment")
        commitment = validate_vertical_package_commitment(commitment)
        pair = PairBinding.from_mapping(documents["slice-manifest.json"]["pair_binding"])
        request = VerticalRuntimePackageRequest(
            qualified_source_head=binding.qualified_source_head,
            qualified_source_tree=binding.qualified_source_tree,
            leg=binding.leg,
            model_key=binding.model_key,
            output_root=binding.envelope_path,
            authorization_id=str(commitment["authorization_id"]),
            attempt_id=str(commitment["attempt_id"]),
        )
        _validate_v2_loaded_documents(documents, raw, commitment, request, pair, binding)
    except (A0XVerticalSliceError, ValueError, KeyError, TypeError) as error:
        if isinstance(error, A0XVerticalSliceError) and error.code == V2_VALIDATION_FAILED:
            raise
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED) from error
    _require_v2_checkout(repository, binding.qualified_source_head, binding.qualified_source_tree)
    return {
        "binding": binding,
        "package_commitment_sha256": binding.package_commitment_sha256,
        "dossier_sha256": binding.dossier_sha256,
        "commitment": commitment,
        "documents": documents,
    }


def _validate_v2_request(request: VerticalRuntimePackageRequest) -> PurePosixPath:
    if (
        not isinstance(request, VerticalRuntimePackageRequest)
        or not isinstance(request.leg, Leg)
        or not isinstance(request.model_key, str)
        or _MODEL_KEY.fullmatch(request.model_key) is None
        or not isinstance(request.qualified_source_head, str)
        or _REVISION.fullmatch(request.qualified_source_head) is None
        or not isinstance(request.qualified_source_tree, str)
        or _REVISION.fullmatch(request.qualified_source_tree) is None
        or not isinstance(request.authorization_id, str) or not request.authorization_id
        or not isinstance(request.attempt_id, str) or not request.attempt_id
        or not isinstance(request.output_root, str)
    ):
        raise A0XVerticalSliceError(V2_INVALID_REQUEST)
    expected = _v2_envelope_relative(
        request.qualified_source_head, request.qualified_source_tree, request.leg, request.model_key,
    )
    if request.output_root != expected.as_posix() or PurePosixPath(request.output_root) != expected:
        raise A0XVerticalSliceError(V2_INVALID_REQUEST)
    return expected


def _v2_envelope_relative(head: str, tree: str, leg: Leg, model_key: str) -> PurePosixPath:
    return PurePosixPath(".a0x-runtime", "p0", "v2", head, tree, leg.value, model_key)


def _require_v2_checkout(repository: Path, head: str, tree: str) -> None:
    try:
        _require_checkout_state(repository, head, tree, frozenset())
    except A0XVerticalSliceError as error:
        raise A0XVerticalSliceError(V2_INVALID_REQUEST) from error


def _validate_v2_documents(
    prerequisites: _RepositoryReader,
    documents: Mapping[str, Mapping[str, Any]],
    encoded: Mapping[str, bytes],
    request: VerticalRuntimePackageRequest,
    pair: PairBinding,
) -> None:
    if set(documents) != set(V2_MEMBER_NAMES) or set(encoded) != set(V2_MEMBER_NAMES):
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED)
    for name, schema in (
        ("protocol.json", "a0x-protocol.schema.json"),
        ("implementation.json", "a0x-implementation.schema.json"),
        ("freeze.json", "a0x-freeze-manifest.schema.json"),
        ("approval-dossier.json", "a0x-authorization-dossier.schema.json"),
        ("slice-manifest.json", "a0x-vertical-slice-manifest-v2.schema.json"),
    ):
        _validate_schema(prerequisites, documents[name], schema)
    manifest = documents["slice-manifest.json"]
    if (
        manifest.get("qualified_source")
        != {"head": request.qualified_source_head, "tree": request.qualified_source_tree, "ref": "refs/heads/main"}
        or manifest.get("pair_binding") != pair.as_mapping()
        or manifest.get("members")
        != [
            {"name": name, "size": len(encoded[name]), "sha256": _sha256(encoded[name])}
            for name in V2_MEMBER_NAMES[:-1]
        ]
    ):
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED)


def _publish_v2_envelope(
    repository: Path,
    envelope_relative: PurePosixPath,
    encoded: Mapping[str, bytes],
    commitment_raw: bytes,
    request: VerticalRuntimePackageRequest,
) -> None:
    parent = _open_package_parent(repository, envelope_relative, create=True)
    transaction: _PublicationTransaction | None = None
    package_fd: int | None = None
    snapshot: _V2StageSnapshot | None = None
    try:
        _revalidate_chain(parent)
        if _exists_at(parent.fd, parent.destination_name):
            raise A0XVerticalSliceError(V2_OUTPUT_EXISTS)
        transaction = _create_stage(parent)
        os.mkdir("package", 0o700, dir_fd=transaction.stage_fd)
        package_fd = os.open(
            "package", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=transaction.stage_fd,
        )
        for name in V2_MEMBER_NAMES:
            _write_member_at(package_fd, name, encoded[name])
        _write_member_at(transaction.stage_fd, "p0-commitment.json", commitment_raw)
        snapshot = _capture_v2_stage(transaction, package_fd, encoded, commitment_raw)
        _assert_v2_stage(transaction, package_fd, snapshot)
        os.fsync(package_fd)
        os.fsync(transaction.stage_fd)
        os.fsync(parent.fd)
        _before_publish(transaction)
        _revalidate_chain(parent)
        _assert_owned_stage(transaction)
        _assert_v2_stage(transaction, package_fd, snapshot)
        if _exists_at(parent.fd, parent.destination_name):
            raise A0XVerticalSliceError(V2_OUTPUT_EXISTS)
        _require_v2_checkout(repository, request.qualified_source_head, request.qualified_source_tree)
        _darwin_publish_exclusive_at(parent.fd, transaction.stage_name, parent.destination_name)
        transaction.state = "published"
        _after_publish(transaction)
        _assert_published(transaction)
        _assert_published_chain(transaction)
        os.fsync(parent.fd)
    except A0XVerticalSliceError as error:
        _cleanup_v2_stage(transaction, package_fd, snapshot)
        if error.code in {V2_OUTPUT_EXISTS, V2_INVALID_REQUEST}:
            raise
        if error.code == PUBLICATION_OWNERSHIP_LOST:
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST) from error
        raise A0XVerticalSliceError(V2_PUBLICATION_FAILED) from error
    except (OSError, ValueError) as error:
        _cleanup_v2_stage(transaction, package_fd, snapshot)
        raise A0XVerticalSliceError(V2_PUBLICATION_FAILED) from error
    finally:
        if package_fd is not None:
            os.close(package_fd)
        if transaction is not None:
            os.close(transaction.stage_fd)
        _close_parent(parent)


def _validate_v2_binding(binding: VerticalPackageBinding) -> None:
    if not isinstance(binding, VerticalPackageBinding):
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED)
    envelope = _v2_envelope_relative(
        binding.qualified_source_head, binding.qualified_source_tree, binding.leg, binding.model_key,
    )
    package = envelope / "package"
    if (
        binding.envelope_path != envelope.as_posix()
        or binding.package_path != package.as_posix()
        or binding.commitment_path != (envelope / "p0-commitment.json").as_posix()
        or binding.dossier_path != (package / "approval-dossier.json").as_posix()
        or _REVISION.fullmatch(binding.qualified_source_head) is None
        or _REVISION.fullmatch(binding.qualified_source_tree) is None
        or _MODEL_KEY.fullmatch(binding.model_key) is None
        or _REVISION.fullmatch(binding.model_revision) is None
        or not isinstance(binding.pair_binding, PairBinding)
        or binding.pair_binding != PairBinding.from_mapping(binding.pair_binding.as_mapping())
        or binding.pair_binding.leg is not binding.leg
        or binding.pair_binding.model_key != binding.model_key
        or binding.pair_binding.revision != binding.model_revision
        or _sha256_pattern_invalid(binding.commitment_raw_sha256)
        or _sha256_pattern_invalid(binding.package_commitment_sha256)
        or _sha256_pattern_invalid(binding.dossier_sha256)
    ):
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED)


def _sha256_pattern_invalid(value: object) -> bool:
    return not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{64}", value) is None


def _capture_v2_stage(
    transaction: _PublicationTransaction,
    package_fd: int,
    encoded: Mapping[str, bytes],
    commitment_raw: bytes,
) -> _V2StageSnapshot:
    members = {name: (encoded[name], _sha256(encoded[name])) for name in V2_MEMBER_NAMES}
    commitment = (commitment_raw, _sha256(commitment_raw))
    try:
        package = os.stat("package", dir_fd=transaction.stage_fd, follow_symlinks=False)
        if not stat.S_ISDIR(package.st_mode) or (package.st_dev, package.st_ino) != _fd_identity(package_fd):
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        member_identities = {
            name: _v2_stage_file_identity(package_fd, name, members[name][0]) for name in V2_MEMBER_NAMES
        }
        commitment_identity = _v2_stage_file_identity(transaction.stage_fd, "p0-commitment.json", commitment_raw)
        return _V2StageSnapshot(
            package_identity=(package.st_dev, package.st_ino),
            member_identities=member_identities,
            commitment_identity=commitment_identity,
            members=members,
            commitment=commitment,
        )
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST) from error


def _v2_stage_file_identity(parent_fd: int, name: str, expected_raw: bytes) -> tuple[int, int, int]:
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
    raw = _read_regular_at(parent_fd, name, len(expected_raw), V2_PUBLICATION_OWNERSHIP_LOST)
    if raw != expected_raw:
        raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
    return metadata.st_dev, metadata.st_ino, metadata.st_size


def _assert_v2_stage(
    transaction: _PublicationTransaction,
    package_fd: int,
    snapshot: _V2StageSnapshot,
) -> None:
    try:
        if set(os.listdir(transaction.stage_fd)) != {"package", "p0-commitment.json"}:
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        package = os.stat("package", dir_fd=transaction.stage_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(package.st_mode)
            or (package.st_dev, package.st_ino) != snapshot.package_identity
            or _fd_identity(package_fd) != snapshot.package_identity
            or set(os.listdir(package_fd)) != set(V2_MEMBER_NAMES)
        ):
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        for name, (expected_raw, expected_hash) in snapshot.members.items():
            identity = _v2_stage_file_identity(package_fd, name, expected_raw)
            if identity != snapshot.member_identities[name] or _sha256(expected_raw) != expected_hash:
                raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        commitment_identity = _v2_stage_file_identity(
            transaction.stage_fd, "p0-commitment.json", snapshot.commitment[0],
        )
        if (
            commitment_identity != snapshot.commitment_identity
            or _sha256(snapshot.commitment[0]) != snapshot.commitment[1]
        ):
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST) from error


def _cleanup_v2_stage(
    transaction: _PublicationTransaction | None,
    package_fd: int | None,
    snapshot: _V2StageSnapshot | None,
) -> None:
    """Remove only an unchanged unpublished v2 staging inode."""
    if transaction is None or transaction.state != "staged":
        return
    if package_fd is None or snapshot is None:
        raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
    try:
        metadata = os.stat(transaction.stage_name, dir_fd=transaction.parent.fd, follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != transaction.stage_identity:
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        _assert_v2_stage(transaction, package_fd, snapshot)
        for name in V2_MEMBER_NAMES:
            if _v2_stage_file_identity(package_fd, name, snapshot.members[name][0]) != snapshot.member_identities[name]:
                raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
            os.unlink(name, dir_fd=package_fd)
        os.rmdir("package", dir_fd=transaction.stage_fd)
        if _v2_stage_file_identity(
            transaction.stage_fd, "p0-commitment.json", snapshot.commitment[0],
        ) != snapshot.commitment_identity:
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        os.unlink("p0-commitment.json", dir_fd=transaction.stage_fd)
        metadata = os.stat(transaction.stage_name, dir_fd=transaction.parent.fd, follow_symlinks=False)
        if (metadata.st_dev, metadata.st_ino) != transaction.stage_identity:
            raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST)
        os.rmdir(transaction.stage_name, dir_fd=transaction.parent.fd)
        os.fsync(transaction.parent.fd)
    except A0XVerticalSliceError:
        raise
    except OSError as error:
        raise A0XVerticalSliceError(V2_PUBLICATION_OWNERSHIP_LOST) from error


def _validate_v2_loaded_documents(
    documents: Mapping[str, dict[str, Any]], raw: Mapping[str, bytes], commitment: Mapping[str, object],
    request: VerticalRuntimePackageRequest, pair: PairBinding, binding: VerticalPackageBinding,
) -> None:
    expected_source = {
        "head": request.qualified_source_head, "tree": request.qualified_source_tree, "ref": "refs/heads/main",
    }
    members = [
        {"name": name, "size": len(raw[name]), "sha256": _sha256(raw[name])}
        for name in V2_MEMBER_NAMES
    ]
    manifest = documents["slice-manifest.json"]
    if (
        commitment.get("qualified_source") != expected_source
        or commitment.get("pair_binding") != pair.as_mapping()
        or pair != binding.pair_binding
        or commitment.get("members") != members
        or manifest.get("qualified_source") != expected_source
        or manifest.get("pair_binding") != pair.as_mapping()
        or manifest.get("members") != members[:-1]
        or documents["approval-dossier.json"].get("pair_binding") != pair.as_mapping()
        or documents["approval-dossier.json"].get("implementation_source_head") != request.qualified_source_head
        or _sha256(raw["approval-dossier.json"]) != binding.dossier_sha256
        or _sha256(_canonical_json_bytes(dict(commitment))) != binding.commitment_raw_sha256
        or commitment.get("package_commitment_sha256") != binding.package_commitment_sha256
    ):
        raise A0XVerticalSliceError(V2_VALIDATION_FAILED)


__all__ = [
    "A0XVerticalSliceError",
    "GENERATOR_PROFILE",
    "INVALID_REQUEST",
    "OUTPUT_EXISTS",
    "PUBLICATION_FAILED",
    "PUBLICATION_OWNERSHIP_LOST",
    "PUBLICATION_UNSUPPORTED",
    "VALIDATION_FAILED",
    "V2_GENERATOR_PROFILE",
    "V2_INVALID_REQUEST",
    "V2_OUTPUT_EXISTS",
    "V2_PUBLICATION_FAILED",
    "V2_PUBLICATION_OWNERSHIP_LOST",
    "V2_VALIDATION_FAILED",
    "VerticalPackageBinding",
    "VerticalRuntimePackageRequest",
    "VerticalSliceRequest",
    "generate_vertical_runtime_package",
    "generate_vertical_slice",
    "load_vertical_runtime_package",
    "load_vertical_slice",
]
