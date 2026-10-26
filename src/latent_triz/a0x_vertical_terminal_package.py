"""Fail-closed v4 terminal packages, separate from historical A0X formats.

Synthetic fixtures are never eligible for publication. Production packaging
requires a complete independently reloaded capability, not a context projection,
and preserves its exact pre-execution trust set plus the observed statistic.
"""
from __future__ import annotations

import hashlib
import json
import ctypes
import errno
import os
import re
import stat
import secrets
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

from .a0x_contract import A0XContractError, PairBinding
from .a0x_report import _atomic_publish_no_replace
from .a0x_validator import validate as validate_a0x
from .a0x_public_closure import A0XPublicClosureError, load_public_terminal_closure
from .a0x_vertical_production_adapter import VerticalProductionContext

_ROOT = Path(__file__).resolve().parents[2]
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_TERMINAL_SCHEMA = "a0x-vertical-terminal-result-v1.schema.json"
_TRUST_SCHEMA = "a0x-vertical-trust-manifest-v1.schema.json"
_MANIFEST_SCHEMA = "a0x-vertical-terminal-manifest-v1.schema.json"
_ROOT_SCHEMA = "a0x-vertical-terminal-root-v1.schema.json"
_ASSET_SCHEMA = "a0x-vertical-external-assets-locator-v1.schema.json"
_BASE_MEMBERS = frozenset({
    "publication-manifest.json", "root-receipt.json", "terminal-result.json",
    "trust-manifest.json", "report.md", "execution-authorization-v4.schema.json",
})
_ASSET_MEMBER = "external-assets-locator.json"
_PUBLIC_TRUST_SOURCES = {
    "schemas/a0x-execution-authorization-v4.schema.json": (
        "execution_authorization_schema", "execution-authorization-v4.schema.json",
    ),
}
_PUBLIC_ASSET_ROOT = "results/a0x-external-assets"
_ASSET_STATUSES = frozenset({"positive", "null", "non_interpretable"})


class A0XVerticalTerminalPackageError(ValueError):
    """A v4 terminal package cannot be built or independently verified."""


@dataclass(frozen=True)
class _ExpectedFile:
    path: str
    size: int
    sha256: str
    device: int
    inode: int

    def public_mapping(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True)
class _ExpectedAsset:
    role: str
    path: str
    size: int
    sha256: str

    def public_mapping(self) -> dict[str, Any]:
        return {"role": self.role, "repository_relative_path": self.path, "bytes": self.size, "raw_sha256": self.sha256}


@dataclass(frozen=True)
class VerticalTerminalExpectation:
    """Independent expected bindings captured from an already validated graph."""

    source_head: str
    source_tree: str
    source_ref: str
    pair_binding: Mapping[str, Any]
    vertical_package_digests: Mapping[str, str]
    qualification_context: str
    authorization_id: str
    attempt_id: str
    trust_files: tuple[_ExpectedFile, ...]
    external_assets: tuple[_ExpectedAsset, ...] = ()
    _production_capability: Any = None

    @classmethod
    def from_context(
        cls,
        context: VerticalProductionContext,
        *,
        repository_root: str | Path | None = None,
        external_assets: Mapping[str, str | Path] | None = None,
        _production_capability: Any = None,
    ) -> "VerticalTerminalExpectation":
        if not isinstance(context, VerticalProductionContext):
            raise A0XVerticalTerminalPackageError("validated vertical context is required")
        if context.qualification_context == "production" and _production_capability is not None:
            _validate_production_context_membership(context, _production_capability)
        elif context.qualification_context not in {"synthetic-target-free", "engineering_rehearsal"}:
            raise A0XVerticalTerminalPackageError(
                "production expectations require the complete parent-validated trust capability"
            )
        identities: list[_ExpectedFile] = []
        for path, identity in sorted(context.trust_file_identities.items()):
            if set(identity) != {"device", "inode", "size", "sha256"}:
                raise A0XVerticalTerminalPackageError("validated trust identity shape differs")
            identities.append(_ExpectedFile(
                path=_relative(path, "trust input"),
                size=_nonnegative_int(identity["size"], "trust size"),
                sha256=_digest(identity["sha256"], "trust digest"),
                device=_nonnegative_int(identity["device"], "trust device"),
                inode=_positive_int(identity["inode"], "trust inode"),
            ))
        if not identities:
            raise A0XVerticalTerminalPackageError("validated trust set is empty")

        assets: list[_ExpectedAsset] = []
        if external_assets:
            if set(external_assets) != {"dense", "index"}:
                raise A0XVerticalTerminalPackageError("dense and index assets must be supplied as an exact pair")
            if repository_root is None:
                raise A0XVerticalTerminalPackageError("repository root is required for external assets")
            repo = _directory(Path(repository_root), "repository root")
            pair = PairBinding.from_mapping(context.public_identity()["pair_binding"])
            for role in ("dense", "index"):
                relative = _path_to_relative(repo, Path(external_assets[role]), f"{role} asset")
                if relative != _public_asset_path(context.source_head, context.source_tree, pair, role):
                    raise A0XVerticalTerminalPackageError(f"{role} asset path is not the canonical public pair destination")
                raw, _info = _read_independent(repo, relative)
                assets.append(_ExpectedAsset(role, relative, len(raw), _sha(raw)))

        return cls(
            source_head=context.source_head,
            source_tree=context.source_tree,
            source_ref="refs/heads/main",
            pair_binding=_freeze_json(context.public_identity()["pair_binding"]),
            vertical_package_digests=MappingProxyType({
                key: _digest(context.vertical_package[key], f"vertical package {key}")
                for key in ("commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256")
            }),
            qualification_context=context.qualification_context,
            authorization_id=context.authorization_id,
            attempt_id=context.attempt_id,
            trust_files=tuple(identities),
            external_assets=tuple(assets),
            _production_capability=_production_capability,
        )

    @classmethod
    def from_production_capability(cls, capability: Any, *, material_context: VerticalProductionContext | None = None,
                                   external_assets: Mapping[str, str | Path] | None = None) -> "VerticalTerminalExpectation":
        from .a0x_vertical_production_adapter import _ValidatedProductionCapability, _PRODUCTION_CAPABILITY, load_vertical_production_capability
        if not isinstance(capability, _ValidatedProductionCapability) or capability._marker is not _PRODUCTION_CAPABILITY:
            raise A0XVerticalTerminalPackageError("complete production capability is required")
        validated = load_vertical_production_capability(capability.repository_root, capability.descriptor_path, _terminal_outputs=True)
        if validated.context != capability.context or validated.package_documents != capability.package_documents:
            raise A0XVerticalTerminalPackageError("production capability differs after material stages")
        context = validated.context if material_context is None else material_context
        return cls.from_context(context, repository_root=validated.repository_root,
            external_assets=external_assets, _production_capability=validated)

    def identity(self) -> dict[str, Any]:
        return {
            "qualified_source": {"head": self.source_head, "tree": self.source_tree, "ref": self.source_ref},
            "pair_binding": _json_mapping(self.pair_binding),
            "vertical_package_digests": dict(self.vertical_package_digests),
            "qualification_context": self.qualification_context,
            "authorization_id": self.authorization_id,
            "attempt_id": self.attempt_id,
        }


@dataclass(frozen=True)
class VerticalTerminalPackageRef:
    manifest_sha256: str
    root_receipt_sha256: str
    terminal_result_sha256: str
    member_count: int


@dataclass(frozen=True)
class VerifiedVerticalTerminalPackage:
    qualification_context: str
    scientific_outcome: str
    publication_eligible: bool
    manifest_sha256: str
    root_receipt_sha256: str
    terminal_result_sha256: str


@dataclass(frozen=True)
class PublicVerticalPackageIntegrity:
    """Public-file integrity only; never proof of private execution facts."""

    package_integrity_verified: bool
    execution_evidence_verified: bool
    publication_eligible: bool
    manifest_sha256: str
    root_receipt_sha256: str
    terminal_result_sha256: str
    public_closure_verified: bool = False
    public_closure_manifest_sha256: str | None = None


def build_vertical_terminal_package(
    *,
    repository_root: str | Path,
    destination: str | Path,
    expected: VerticalTerminalExpectation,
    terminal_result: Mapping[str, Any],
) -> VerticalTerminalPackageRef:
    """Build a canonical v4 package via atomic no-replace publication."""
    _validate_expectation_context(expected)
    repo = _directory(Path(repository_root), "repository root")
    _require_rehearsal_namespace(repo, expected)
    target = _destination(repo, Path(destination), expected)
    if os.path.lexists(target):
        raise A0XVerticalTerminalPackageError("terminal destination already exists")
    result = _validate_terminal_result(terminal_result, expected)
    trust_value = _trust_manifest(repo, expected)
    public_documents = _public_trust_documents(repo, expected)
    _verify_expected_assets(repo, expected.external_assets, expected.trust_files)
    _validate_schema(trust_value, _TRUST_SCHEMA, "trust manifest")
    report_raw = _render_report(result, expected)
    assets = [item.public_mapping() for item in expected.external_assets]
    _require_asset_policy(expected, result, assets)

    parent = target.parent
    parent_fd = _open_directory_chain(repo, parent, create=True)
    stage_name = f".{target.name}.stage-{secrets.token_hex(12)}"
    stage_fd: int | None = None
    stage_identity: tuple[int, int] | None = None
    file_identities: dict[str, tuple[int, int]] = {}
    published = False
    try:
        os.mkdir(stage_name, mode=0o700, dir_fd=parent_fd)
        stage_fd = os.open(stage_name, _directory_open_flags(), dir_fd=parent_fd)
        stage_info = os.fstat(stage_fd)
        stage_identity = (stage_info.st_dev, stage_info.st_ino)
        if not stat.S_ISDIR(stage_info.st_mode):
            raise A0XVerticalTerminalPackageError("staging object is not a directory")
        files: list[dict[str, Any]] = []
        for role, filename, raw in (
            ("terminal_result", "terminal-result.json", _canonical_json(result)),
            ("trust_manifest", "trust-manifest.json", _canonical_json(trust_value)),
            ("report", "report.md", report_raw),
        ):
            file_identities[filename] = _write_new_at(stage_fd, filename, raw)
            files.append(_file_entry(role, filename, raw))
        for filename, raw in sorted(public_documents.items()):
            file_identities[filename] = _write_new_at(stage_fd, filename, raw)
            files.append(_file_entry("public_evidence", filename, raw))
        locator = None
        if assets:
            locator = {
                "artifact_class": "a0x-vertical-external-assets-locator",
                "locator_profile": "a0x-vertical-external-assets-locator-v1",
                **expected.identity(),
                "assets": assets,
            }
            _validate_schema(locator, _ASSET_SCHEMA, "external asset locator")
            raw = _canonical_json(locator)
            file_identities[_ASSET_MEMBER] = _write_new_at(stage_fd, _ASSET_MEMBER, raw)
            files.append(_file_entry("external_assets_locator", _ASSET_MEMBER, raw))
        files.sort(key=lambda entry: entry["path"])
        manifest = {
            "artifact_class": "a0x-vertical-terminal-package",
            "manifest_profile": "a0x-vertical-terminal-manifest-v1",
            **expected.identity(),
            "terminal_status": result["scientific_outcome"],
            "files": files,
            "external_assets_locator": None if locator is None else {
                "path": _ASSET_MEMBER,
                "raw_sha256": _sha(_canonical_json(locator)),
            },
            "publication_eligible": False,
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
        }
        _validate_schema(manifest, _MANIFEST_SCHEMA, "terminal manifest")
        manifest_raw = _canonical_json(manifest)
        root = {
            "artifact_class": "a0x-vertical-terminal-root-receipt",
            "root_profile": "a0x-vertical-terminal-root-v1",
            **expected.identity(),
            "manifest_raw_sha256": _sha(manifest_raw),
            "member_paths": sorted([*_BASE_MEMBERS, *([_ASSET_MEMBER] if locator is not None else [])]),
            "publication_eligible": manifest["publication_eligible"],
            "evidence_eligible": False,
            "expert_validated": False,
            "claim_ids": [],
        }
        _validate_schema(root, _ROOT_SCHEMA, "root receipt")
        file_identities["publication-manifest.json"] = _write_new_at(stage_fd, "publication-manifest.json", manifest_raw)
        root_raw = _canonical_json(root)
        file_identities["root-receipt.json"] = _write_new_at(stage_fd, "root-receipt.json", root_raw)
        _verify_staged_members_fd(stage_fd, locator is not None, file_identities)
        _require_directory_path_identity(repo, parent, parent_fd)
        _require_named_directory_identity(parent_fd, stage_name, stage_identity)
        _atomic_rename_noreplace_at(parent_fd, stage_name, target.name)
        published = True
        _require_named_directory_identity(parent_fd, target.name, stage_identity)
        _require_directory_path_identity(repo, parent, parent_fd)
        reference = VerticalTerminalPackageRef(
            manifest_sha256=_sha(manifest_raw),
            root_receipt_sha256=_sha(root_raw),
            terminal_result_sha256=_sha(_canonical_json(result)),
            member_count=len(_BASE_MEMBERS) + int(locator is not None),
        )
        verified = verify_vertical_terminal_package(
            package_root=target,
            repository_root=repo,
            expected=expected,
            expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256,
        )
        if (
            verified.publication_eligible
            or verified.manifest_sha256 != reference.manifest_sha256
            or verified.root_receipt_sha256 != reference.root_receipt_sha256
        ):
            raise A0XVerticalTerminalPackageError("published package verification differs")
        _require_named_directory_identity(parent_fd, target.name, stage_identity)
        _require_directory_path_identity(repo, parent, parent_fd)
        return reference
    except (OSError, A0XVerticalTerminalPackageError):
        raise
    except Exception as error:
        raise A0XVerticalTerminalPackageError("terminal package construction failed") from error
    finally:
        try:
            if stage_fd is not None and not published and stage_identity is not None:
                _cleanup_owned_stage(
                    parent_fd=parent_fd,
                    stage_fd=stage_fd,
                    stage_name=stage_name,
                    stage_identity=stage_identity,
                    file_identities=file_identities,
                )
        finally:
            if stage_fd is not None:
                os.close(stage_fd)
            os.close(parent_fd)


def verify_vertical_terminal_package(
    *,
    package_root: str | Path,
    repository_root: str | Path,
    expected: VerticalTerminalExpectation,
    expected_manifest_sha256: str,
    expected_root_receipt_sha256: str,
) -> VerifiedVerticalTerminalPackage:
    """Independently verify exact membership, expected inputs, and raw hashes."""
    _validate_expectation_context(expected)
    repo = _directory(Path(repository_root), "repository root")
    _require_rehearsal_namespace(repo, expected)
    package = _directory(Path(package_root), "package root")
    expected_manifest_sha256 = _digest(expected_manifest_sha256, "expected manifest digest")
    expected_root_receipt_sha256 = _digest(expected_root_receipt_sha256, "expected root digest")
    expected_destination = repo / PairBinding.from_mapping(expected.pair_binding).output_path
    if package != expected_destination:
        raise A0XVerticalTerminalPackageError("package root differs from independent PairBinding output path")
    parent_fd = _open_directory_chain(repo, package.parent, create=False)
    package_fd: int | None = None
    try:
        _require_directory_path_identity(repo, package.parent, parent_fd)
        try:
            named = os.stat(package.name, dir_fd=parent_fd, follow_symlinks=False)
            package_fd = os.open(package.name, _directory_open_flags(), dir_fd=parent_fd)
        except OSError as error:
            raise A0XVerticalTerminalPackageError("package directory is unavailable or unsafe") from error
        pinned = os.fstat(package_fd)
        package_identity = (pinned.st_dev, pinned.st_ino)
        if not stat.S_ISDIR(pinned.st_mode) or not stat.S_ISDIR(named.st_mode) or package_identity != (named.st_dev, named.st_ino):
            raise A0XVerticalTerminalPackageError("package directory identity is not stable")

        _verify_package_membership_fd(package_fd, expected_names=None)
        manifest_raw, manifest = _read_json_at(package_fd, "publication-manifest.json", "manifest")
        root_raw, root = _read_json_at(package_fd, "root-receipt.json", "root receipt")
        terminal_raw, result = _read_json_at(package_fd, "terminal-result.json", "terminal result")
        trust_raw, trust = _read_json_at(package_fd, "trust-manifest.json", "trust manifest")
        _validate_schema(manifest, _MANIFEST_SCHEMA, "terminal manifest")
        _validate_schema(root, _ROOT_SCHEMA, "root receipt")
        _validate_schema(result, _TERMINAL_SCHEMA, "terminal result")
        _validate_schema(trust, _TRUST_SCHEMA, "trust manifest")
        if _sha(manifest_raw) != expected_manifest_sha256 or _sha(root_raw) != expected_root_receipt_sha256:
            raise A0XVerticalTerminalPackageError("external package anchors differ")
        if root.get("manifest_raw_sha256") != _sha(manifest_raw):
            raise A0XVerticalTerminalPackageError("root receipt does not bind exact manifest bytes")
        identity = expected.identity()
        for label, value in (("manifest", manifest), ("root receipt", root), ("terminal result", result), ("trust manifest", trust)):
            if any(value.get(key) != bound for key, bound in identity.items()):
                raise A0XVerticalTerminalPackageError(f"{label} identity differs from independent expectation")
        validated_result = _validate_terminal_result(result, expected)
        _verify_material_evidence(repo, expected, validated_result)
        if manifest.get("terminal_status") != validated_result["scientific_outcome"]:
            raise A0XVerticalTerminalPackageError("manifest terminal status differs")
        if manifest.get("publication_eligible") is not False or root.get("publication_eligible") is not False:
            raise A0XVerticalTerminalPackageError("terminal package cannot assert publication eligibility")
        if any(value.get("evidence_eligible") is not False or value.get("expert_validated") is not False or value.get("claim_ids") != [] for value in (manifest, root, result)):
            raise A0XVerticalTerminalPackageError("claim-promotion fields must remain closed")

        expected_trust = _trust_manifest(repo, expected)
        public_documents = _public_trust_documents(repo, expected)
        if trust != expected_trust:
            raise A0XVerticalTerminalPackageError("trust set differs from independently re-read inputs")
        expected_assets = [item.public_mapping() for item in expected.external_assets]
        _require_asset_policy(expected, validated_result, expected_assets)
        locator = None
        locator_ref = manifest.get("external_assets_locator")
        if expected_assets:
            if not isinstance(locator_ref, Mapping) or locator_ref.get("path") != _ASSET_MEMBER:
                raise A0XVerticalTerminalPackageError("external asset locator is missing")
            locator_raw, locator = _read_json_at(package_fd, _ASSET_MEMBER, "external asset locator")
            if _sha(locator_raw) != locator_ref.get("raw_sha256"):
                raise A0XVerticalTerminalPackageError("external asset locator digest differs")
            _validate_schema(locator, _ASSET_SCHEMA, "external asset locator")
            if locator.get("assets") != expected_assets or any(locator.get(key) != bound for key, bound in identity.items()):
                raise A0XVerticalTerminalPackageError("external asset locator differs from independent expectation")

        expected_files = {
            "terminal-result.json": ("terminal_result", terminal_raw),
            "trust-manifest.json": ("trust_manifest", trust_raw),
            "report.md": ("report", _render_report(validated_result, expected)),
        }
        expected_files.update({name: ("public_evidence", raw) for name, raw in public_documents.items()})
        if locator is not None:
            expected_files[_ASSET_MEMBER] = ("external_assets_locator", _canonical_json(locator))
        if manifest.get("files") != [
            _file_entry(role, path, raw)
            for path, (role, raw) in sorted(expected_files.items())
        ]:
            raise A0XVerticalTerminalPackageError("manifest member ledger differs")
        if root.get("member_paths") != sorted([*_BASE_MEMBERS, *([_ASSET_MEMBER] if locator is not None else [])]):
            raise A0XVerticalTerminalPackageError("root member set differs")
        expected_names = set(expected_files) | {"publication-manifest.json", "root-receipt.json"}
        _verify_package_membership_fd(package_fd, expected_names=expected_names)
        expected_member_bytes = {name: raw for name, (_role, raw) in expected_files.items()}
        expected_member_bytes["publication-manifest.json"] = manifest_raw
        expected_member_bytes["root-receipt.json"] = root_raw
        seen: set[tuple[int, int]] = set()
        member_identities: dict[str, tuple[int, int]] = {}
        for relative in sorted(expected_names):
            raw, inode = _read_member_at(package_fd, relative)
            if inode in seen:
                raise A0XVerticalTerminalPackageError("physical aliases and hardlinks are forbidden")
            seen.add(inode)
            expected_raw = expected_member_bytes[relative]
            if raw != expected_raw:
                role = expected_files.get(relative, ("package anchor", b""))[0]
                raise A0XVerticalTerminalPackageError(f"{role} bytes differ")
            member_identities[relative] = inode

        # Re-read mutable external inputs only after all package bytes are checked.
        if _trust_manifest(repo, expected) != trust:
            raise A0XVerticalTerminalPackageError("trust input changed during package verification")
        if expected.external_assets:
            _verify_expected_assets(repo, expected.external_assets, expected.trust_files)
        _verify_package_membership_fd(package_fd, expected_names=expected_names)
        for relative in sorted(expected_names):
            raw, identity_after = _read_member_at(package_fd, relative)
            if identity_after != member_identities[relative] or raw != expected_member_bytes[relative]:
                raise A0XVerticalTerminalPackageError("package member changed during final verification")
        current = os.stat(package.name, dir_fd=parent_fd, follow_symlinks=False)
        pinned = os.fstat(package_fd)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != package_identity or (pinned.st_dev, pinned.st_ino) != package_identity:
            raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_VERIFICATION_OWNERSHIP_LOST")
        _require_directory_path_identity(repo, package.parent, parent_fd)
        return VerifiedVerticalTerminalPackage(
            qualification_context=expected.qualification_context,
            scientific_outcome=str(validated_result["scientific_outcome"]),
            publication_eligible=False,
            manifest_sha256=_sha(manifest_raw),
            root_receipt_sha256=_sha(root_raw),
            terminal_result_sha256=_sha(terminal_raw),
        )
    finally:
        if package_fd is not None:
            os.close(package_fd)
        os.close(parent_fd)


def verify_public_vertical_terminal_package(
    *,
    package_root: str | Path,
    evidence_root: str | Path,
    expected_manifest_sha256: str,
    expected_root_receipt_sha256: str,
    expected_public_closure_manifest_sha256: str | None = None,
) -> PublicVerticalPackageIntegrity:
    """Verify a public package using only its closure and declared assets.

    The result is deliberately limited to package-byte integrity. Production
    packages additionally require a caller-supplied independent pin for the
    complete public closure manifest; the closure outcome must agree with this
    terminal package. Synthetic packages remain integrity-only and cannot
    consume that production anchor. This verifier cannot prove private
    execution history and never returns eligibility or scientific-evidence
    claims. Callers must exclude untrusted concurrent same-user writers during
    verification.
    """
    root_path = _directory(Path(evidence_root), "public evidence root")
    package = _directory(Path(package_root), "public package root")
    expected_manifest_sha256 = _digest(expected_manifest_sha256, "expected manifest digest")
    expected_root_receipt_sha256 = _digest(expected_root_receipt_sha256, "expected root digest")
    parent_fd = _open_directory_chain(root_path, package.parent, create=False)
    package_fd: int | None = None
    try:
        _require_directory_path_identity(root_path, package.parent, parent_fd)
        try:
            named = os.stat(package.name, dir_fd=parent_fd, follow_symlinks=False)
            package_fd = os.open(package.name, _directory_open_flags(), dir_fd=parent_fd)
        except OSError as error:
            raise A0XVerticalTerminalPackageError("public package directory is unavailable or unsafe") from error
        pinned = os.fstat(package_fd)
        package_identity = (pinned.st_dev, pinned.st_ino)
        if not stat.S_ISDIR(pinned.st_mode) or not stat.S_ISDIR(named.st_mode) or package_identity != (named.st_dev, named.st_ino):
            raise A0XVerticalTerminalPackageError("public package directory identity is unstable")

        manifest_raw, manifest = _read_json_at(package_fd, "publication-manifest.json", "manifest")
        root_raw, root_receipt = _read_json_at(package_fd, "root-receipt.json", "root receipt")
        terminal_raw, result = _read_json_at(package_fd, "terminal-result.json", "terminal result")
        trust_raw, trust = _read_json_at(package_fd, "trust-manifest.json", "trust manifest")
        _validate_schema(manifest, _MANIFEST_SCHEMA, "terminal manifest")
        _validate_schema(root_receipt, _ROOT_SCHEMA, "root receipt")
        _validate_schema(result, _TERMINAL_SCHEMA, "terminal result")
        _validate_schema(trust, _TRUST_SCHEMA, "trust manifest")
        if _sha(manifest_raw) != expected_manifest_sha256 or _sha(root_raw) != expected_root_receipt_sha256:
            raise A0XVerticalTerminalPackageError("external public package anchors differ")
        if root_receipt.get("manifest_raw_sha256") != _sha(manifest_raw):
            raise A0XVerticalTerminalPackageError("root receipt does not bind exact manifest bytes")

        identity = {
            key: manifest.get(key)
            for key in (
                "qualified_source", "pair_binding", "vertical_package_digests",
                "qualification_context", "authorization_id", "attempt_id",
            )
        }
        source = identity["qualified_source"]
        pair_value = identity["pair_binding"]
        package_digests = identity["vertical_package_digests"]
        if identity["qualification_context"] not in {"production", "synthetic-target-free"}:
            raise A0XVerticalTerminalPackageError("public verifier rejects an unknown qualification context")
        if not isinstance(source, Mapping) or not isinstance(pair_value, Mapping) or not isinstance(package_digests, Mapping):
            raise A0XVerticalTerminalPackageError("public package identity is malformed")
        pair = PairBinding.from_mapping(pair_value)
        expected_package = root_path / pair.output_path
        if package != expected_package:
            raise A0XVerticalTerminalPackageError("public package path differs from pair output binding")
        expectation = VerticalTerminalExpectation(
            source_head=str(source.get("head")),
            source_tree=str(source.get("tree")),
            source_ref=str(source.get("ref")),
            pair_binding=_freeze_json(pair_value),
            vertical_package_digests=MappingProxyType({key: _digest(package_digests.get(key), f"package {key}") for key in (
                "commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256",
            )}),
            qualification_context=str(identity["qualification_context"]),
            authorization_id=str(identity["authorization_id"]),
            attempt_id=str(identity["attempt_id"]),
            trust_files=(),
            external_assets=(),
        )
        for label, value in (("manifest", manifest), ("root receipt", root_receipt), ("terminal result", result), ("trust manifest", trust)):
            if any(value.get(key) != bound for key, bound in identity.items()):
                raise A0XVerticalTerminalPackageError(f"public {label} identity differs")
        if root_receipt.get("publication_eligible") is not False or manifest.get("publication_eligible") is not False:
            raise A0XVerticalTerminalPackageError("public package cannot assert publication eligibility")
        validated_result = _validate_terminal_result(result, expectation)
        if manifest.get("terminal_status") != validated_result["scientific_outcome"]:
            raise A0XVerticalTerminalPackageError("public terminal status differs")
        if any(value.get("evidence_eligible") is not False or value.get("expert_validated") is not False or value.get("claim_ids") != [] for value in (manifest, root_receipt, result)):
            raise A0XVerticalTerminalPackageError("public claim-promotion fields are not closed")
        if trust.get("private_execution_inputs_excluded") is not True:
            raise A0XVerticalTerminalPackageError("public trust closure does not exclude private execution inputs")
        trust_files = trust.get("files")
        if not isinstance(trust_files, list) or len(trust_files) != len(_PUBLIC_TRUST_SOURCES):
            raise A0XVerticalTerminalPackageError("public trust role set is incomplete or extended")
        public_documents: dict[str, bytes] = {}
        for source_path, (role, filename) in _PUBLIC_TRUST_SOURCES.items():
            candidates = [item for item in trust_files if isinstance(item, Mapping) and item.get("role") == role]
            if len(candidates) != 1 or candidates[0].get("path") != filename:
                raise A0XVerticalTerminalPackageError("public trust role/path allowlist differs")
            raw, _inode = _read_member_at(package_fd, filename)
            if len(raw) != candidates[0].get("size") or _sha(raw) != candidates[0].get("raw_sha256"):
                raise A0XVerticalTerminalPackageError("public trust document bytes differ from closure")
            public_documents[filename] = raw

        expected_assets: tuple[_ExpectedAsset, ...] = ()
        locator = None
        locator_ref = manifest.get("external_assets_locator")
        locator_raw: bytes | None = None
        if locator_ref is not None:
            if not isinstance(locator_ref, Mapping) or locator_ref.get("path") != _ASSET_MEMBER:
                raise A0XVerticalTerminalPackageError("public external asset locator reference is invalid")
            locator_raw, locator = _read_json_at(package_fd, _ASSET_MEMBER, "external asset locator")
            if _sha(locator_raw) != locator_ref.get("raw_sha256"):
                raise A0XVerticalTerminalPackageError("public external asset locator digest differs")
            _validate_schema(locator, _ASSET_SCHEMA, "external asset locator")
            if any(locator.get(key) != bound for key, bound in identity.items()):
                raise A0XVerticalTerminalPackageError("public external asset locator identity differs")
            raw_assets = locator.get("assets")
            if not isinstance(raw_assets, list) or [item.get("role") for item in raw_assets if isinstance(item, Mapping)] != ["dense", "index"]:
                raise A0XVerticalTerminalPackageError("public asset role set is incomplete or extended")
            parsed_assets: list[_ExpectedAsset] = []
            for item in raw_assets:
                if not isinstance(item, Mapping) or set(item) != {"role", "repository_relative_path", "bytes", "raw_sha256"}:
                    raise A0XVerticalTerminalPackageError("public asset entry shape differs")
                role = str(item["role"])
                path = _relative(str(item["repository_relative_path"]), "public asset path")
                if path != _public_asset_path(expectation.source_head, expectation.source_tree, pair, role):
                    raise A0XVerticalTerminalPackageError("public asset path is not pair-derived")
                parsed_assets.append(_ExpectedAsset(role, path, _nonnegative_int(item["bytes"], "public asset size"), _digest(item["raw_sha256"], "public asset digest")))
            expected_assets = tuple(parsed_assets)
            _verify_expected_assets(root_path, expected_assets, ())
        elif validated_result["scientific_outcome"] in _ASSET_STATUSES:
            raise A0XVerticalTerminalPackageError("public scientific terminal lacks declared external assets")
        _require_asset_policy(expectation, validated_result, [asset.public_mapping() for asset in expected_assets])

        expected_files = {
            "terminal-result.json": ("terminal_result", terminal_raw),
            "trust-manifest.json": ("trust_manifest", trust_raw),
            "report.md": ("report", _render_report(validated_result, expectation)),
            **{name: ("public_evidence", raw) for name, raw in public_documents.items()},
        }
        if locator_raw is not None:
            expected_files[_ASSET_MEMBER] = ("external_assets_locator", locator_raw)
        if manifest.get("files") != [_file_entry(role, name, raw) for name, (role, raw) in sorted(expected_files.items())]:
            raise A0XVerticalTerminalPackageError("public package file ledger differs")
        expected_names = set(expected_files) | {"publication-manifest.json", "root-receipt.json"}
        if root_receipt.get("member_paths") != sorted(expected_names):
            raise A0XVerticalTerminalPackageError("public package member set differs")
        _verify_package_membership_fd(package_fd, expected_names=expected_names)
        expected_raws = {name: raw for name, (_role, raw) in expected_files.items()}
        expected_raws.update({"publication-manifest.json": manifest_raw, "root-receipt.json": root_raw})
        identities: dict[str, tuple[int, int]] = {}
        seen: set[tuple[int, int]] = set()
        for name in sorted(expected_names):
            raw, inode = _read_member_at(package_fd, name)
            if inode in seen or raw != expected_raws[name]:
                raise A0XVerticalTerminalPackageError("public package member differs or aliases another member")
            seen.add(inode)
            identities[name] = inode
            if b".a0x-runtime" in raw or b"runtime-mapping.json" in raw:
                raise A0XVerticalTerminalPackageError("public package contains a private runtime path marker")
        if expected_assets:
            _verify_expected_assets(root_path, expected_assets, ())
        _verify_package_membership_fd(package_fd, expected_names=expected_names)
        for name in sorted(expected_names):
            raw, inode = _read_member_at(package_fd, name)
            if inode != identities[name] or raw != expected_raws[name]:
                raise A0XVerticalTerminalPackageError("public package member changed during verification")
        current = os.stat(package.name, dir_fd=parent_fd, follow_symlinks=False)
        pinned = os.fstat(package_fd)
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != package_identity or (pinned.st_dev, pinned.st_ino) != package_identity:
            raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_VERIFICATION_OWNERSHIP_LOST")
        public_closure_verified = False
        closure_manifest_sha256: str | None = None
        if identity["qualification_context"] == "production":
            if expected_public_closure_manifest_sha256 is None:
                raise A0XVerticalTerminalPackageError("production package requires an independently pinned public closure manifest")
            try:
                closure = load_public_terminal_closure(
                    root_path,
                    expected_identity={
                        "qualified_source": identity["qualified_source"],
                        "pair_binding": identity["pair_binding"],
                        "authorization_id": identity["authorization_id"],
                        "attempt_id": identity["attempt_id"],
                        "p0_package_commitment_sha256": package_digests["package_commitment_sha256"],
                    },
                    expected_manifest_sha256=expected_public_closure_manifest_sha256,
                )
            except (A0XPublicClosureError, KeyError, TypeError, ValueError) as error:
                raise A0XVerticalTerminalPackageError("production public closure is invalid or unanchored") from error
            if closure.terminal_outcome != validated_result["scientific_outcome"]:
                raise A0XVerticalTerminalPackageError("public terminal closure outcome differs from terminal package")
            public_closure_verified = True
            closure_manifest_sha256 = closure.manifest_sha256
        elif expected_public_closure_manifest_sha256 is not None:
            raise A0XVerticalTerminalPackageError("synthetic package cannot consume a production closure anchor")
        _require_directory_path_identity(root_path, package.parent, parent_fd)
        return PublicVerticalPackageIntegrity(
            package_integrity_verified=True,
            execution_evidence_verified=False,
            publication_eligible=False,
            manifest_sha256=_sha(manifest_raw),
            root_receipt_sha256=_sha(root_raw),
            terminal_result_sha256=_sha(terminal_raw),
            public_closure_verified=public_closure_verified,
            public_closure_manifest_sha256=closure_manifest_sha256,
        )
    finally:
        if package_fd is not None:
            os.close(package_fd)
        os.close(parent_fd)


def _validate_terminal_result(value: Mapping[str, Any], expected: VerticalTerminalExpectation) -> dict[str, Any]:
    result = _json_mapping(value)
    _validate_schema(result, _TERMINAL_SCHEMA, "terminal result")
    identity = expected.identity()
    if any(result.get(key) != bound for key, bound in identity.items()):
        raise A0XVerticalTerminalPackageError("terminal result identity differs from expectation")
    try:
        if PairBinding.from_mapping(result["pair_binding"]).as_mapping() != PairBinding.from_mapping(expected.pair_binding).as_mapping():
            raise ValueError("pair binding differs")
    except (KeyError, TypeError, ValueError, A0XContractError) as error:
        raise A0XVerticalTerminalPackageError("terminal pair binding is invalid") from error
    if result["reached_frontier"] not in {"validated_graph", "model_identity", "model_loaded", "analysis", "sealed"}:
        raise A0XVerticalTerminalPackageError("terminal frontier is unsupported")
    if expected.qualification_context == "synthetic-target-free" and result["reached_frontier"] != "validated_graph":
        raise A0XVerticalTerminalPackageError("synthetic terminal cannot claim material frontier")
    if result["reached_frontier"] == "sealed" and expected.qualification_context not in {"production", "engineering_rehearsal"}:
        raise A0XVerticalTerminalPackageError("only production context can claim sealed frontier")
    outcome = result["scientific_outcome"]
    if expected.qualification_context in {"production", "engineering_rehearsal"} and outcome is None:
        raise A0XVerticalTerminalPackageError("material package must retain an explicit terminal outcome")
    if outcome in {"positive", "null", "non_interpretable"}:
        if result["reached_frontier"] != "sealed":
            raise A0XVerticalTerminalPackageError("scientific outcomes require the sealed analysis frontier")
        if expected.qualification_context not in {"production", "engineering_rehearsal"}:
            raise A0XVerticalTerminalPackageError("synthetic packages cannot claim a scientific outcome")
    payload = result.get("result_payload")
    if not isinstance(payload, Mapping):
        raise A0XVerticalTerminalPackageError("terminal result payload is not an object")
    if outcome in {"positive", "null"}:
        if set(payload) != {"statistical_result_sha256"}:
            raise A0XVerticalTerminalPackageError("scientific outcome requires an exact statistical result digest")
        _digest(payload["statistical_result_sha256"], "statistical result digest")
        observed = [item for item in expected.trust_files if item.path == _material_evidence_paths(expected)["statistic"]]
        if len(observed) != 1 or payload["statistical_result_sha256"] != observed[0].sha256:
            raise A0XVerticalTerminalPackageError("terminal statistical digest differs from independently observed bytes")
    else:
        if set(payload) != {"diagnostic_code"} or payload["diagnostic_code"] not in {
            "SYNTHETIC_FIXTURE", "MODEL_INCOMPATIBLE", "PREFLIGHT_FAILED", "TARGET_READ_FAILED",
            "ANALYSIS_FAILED", "CLEANUP_UNCERTAIN", "OUTER_EXECUTION_FAILED",
        }:
            raise A0XVerticalTerminalPackageError("terminal diagnostic payload is not allowlisted")
    return result


def _validate_expectation_context(expected: VerticalTerminalExpectation) -> None:
    if not isinstance(expected, VerticalTerminalExpectation):
        raise A0XVerticalTerminalPackageError("terminal expectation is not a supported value")
    if expected.qualification_context == "production":
        from .a0x_vertical_production_adapter import _require_production_capability
        try:
            capability = _require_production_capability(expected._production_capability)
            from dataclasses import replace
            context = replace(capability.context, trust_file_identities=MappingProxyType({
                item.path: MappingProxyType({"device": item.device, "inode": item.inode, "size": item.size, "sha256": item.sha256})
                for item in expected.trust_files
            }))
            _validate_production_context_membership(context, capability)
            if expected.identity() != context.public_identity():
                raise A0XVerticalTerminalPackageError("production terminal identity differs from parent capability")
        except (ValueError, TypeError) as error:
            raise A0XVerticalTerminalPackageError("complete production trust capability is invalid") from error
    elif expected.qualification_context not in {"synthetic-target-free", "engineering_rehearsal"}:
        raise A0XVerticalTerminalPackageError(
            "production packaging requires the complete parent-validated trust capability"
        )


def _validate_production_context_membership(context: VerticalProductionContext, capability: Any) -> None:
    """Only the complete pre-execution set plus the exact five measured receipts."""
    from .a0x_vertical_production_adapter import _require_production_capability
    from dataclasses import replace
    validated = _require_production_capability(capability)
    if replace(context, trust_file_identities=validated.context.trust_file_identities) != validated.context:
        raise A0XVerticalTerminalPackageError("production context differs from independent capability")
    original = validated.context.trust_file_identities
    observed = context.trust_file_identities
    if any(observed.get(path) != identity for path, identity in original.items()):
        raise A0XVerticalTerminalPackageError("production trust membership was removed or replaced")
    pair = PairBinding.from_mapping(context.public_identity()["pair_binding"])
    base = f".a0x-runtime/gate-c/v2/{context.source_head}/{context.source_tree}/a0/{pair.model_key}/{pair.run_id}/material/"
    admitted = {base + name for name in _MATERIAL_EVIDENCE_MEMBERS.values()}
    extra = set(observed) - set(original)
    if extra not in (set(), admitted):
        raise A0XVerticalTerminalPackageError("unadmitted production terminal trust input")
    for path in extra:
        raw, info = _read_independent(validated.repository_root, path)
        if observed[path] != {"device": info.st_dev, "inode": info.st_ino, "size": len(raw), "sha256": _sha(raw)}:
            raise A0XVerticalTerminalPackageError("material evidence identity differs from observed bytes")


_MATERIAL_EVIDENCE_MEMBERS = {"calibration":"calibration-result.json", "activation":"activation/activation-receipt.json",
    "target":"target-read-receipt.json", "statistic":"statistical-result.json", "analysis_seal":"analysis-terminal-result.json"}


def _material_evidence_paths(expected: Any) -> dict[str, str]:
    pair = PairBinding.from_mapping(expected.pair_binding)
    base = (f".a0x-runtime/gate-c/v2/{expected.source_head}/{expected.source_tree}/a0/{pair.model_key}/{pair.run_id}/material/"
        if expected.qualification_context == "production" else ".a0x-runtime/engineering/material/")
    return {role: base + name for role, name in _MATERIAL_EVIDENCE_MEMBERS.items()}


def capture_material_evidence(repository_root: Path, context: VerticalProductionContext) -> VerticalProductionContext:
    """Capture only produced receipts, never model inputs or original targets."""
    from dataclasses import replace
    trust = {key: dict(value) for key, value in context.trust_file_identities.items()}
    for path in _material_evidence_paths(context).values():
        raw, info = _read_independent(repository_root, path)
        trust[path] = {"device":info.st_dev,"inode":info.st_ino,"size":len(raw),"sha256":_sha(raw)}
    return replace(context, trust_file_identities=_freeze_json(trust))


def _verify_material_evidence(repository_root: Path, expected: VerticalTerminalExpectation, result: Mapping[str, Any]) -> None:
    """Verify retained schemas, calibration, one-shot links and the frozen predicate.

    These checks prove consistency of source-qualified observations, not human
    consent or independent truth of a compromised runtime. No targets reopen.
    """
    if result["scientific_outcome"] not in _ASSET_STATUSES:
        return
    paths = _material_evidence_paths(expected)
    by_path = {item.path:item for item in expected.trust_files}
    raw_values, values = {}, {}
    for role, path in paths.items():
        item = by_path.get(path)
        if item is None:
            raise A0XVerticalTerminalPackageError("required retained material evidence is missing")
        raw, info = _read_independent(repository_root,path)
        if (len(raw),_sha(raw),info.st_dev,info.st_ino)!=(item.size,item.sha256,item.device,item.inode):
            raise A0XVerticalTerminalPackageError("retained material evidence drifted")
        try:
            value=json.loads(raw.decode("utf-8"),object_pairs_hook=_no_duplicates,parse_constant=_reject_nonfinite)
            if not isinstance(value,dict) or raw not in (_canonical_json(value),_canonical_json(value)+b"\n"):
                raise ValueError("noncanonical material evidence")
        except (UnicodeDecodeError,ValueError,TypeError) as error:
            raise A0XVerticalTerminalPackageError("retained evidence JSON is invalid") from error
        raw_values[role],values[role]=raw,value
    activation,target,statistic,seal=(values[name] for name in ("activation","target","statistic","analysis_seal"))
    for name,document in (("a0x-activation-receipt.schema.json",activation),("a0x-target-read-receipt.schema.json",target),
                          ("a0x-statistical-result.schema.json",statistic),("a0x-terminal-result.schema.json",seal)):
        _validate_schema(document,name,"private material evidence")
        if document.get("pair_binding")!=_json_mapping(expected.pair_binding):
            raise A0XVerticalTerminalPackageError("material evidence pair differs")
    chain=target["authorization_chain"]
    if any(document.get("authorization_chain")!=chain for document in (activation,statistic,seal)):
        raise A0XVerticalTerminalPackageError("material authorization chains differ")
    if expected.qualification_context=="production":
        from .a0x_contract import APPROVAL_DOSSIER_PROFILE, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE, canonical_commitment
        capability=expected._production_capability
        approved_chain={"dossier_commitment":{"profile":APPROVAL_DOSSIER_PROFILE,"commitment_sha256":canonical_commitment(
            _plain_json(capability.package_documents["approval-dossier.json"]),APPROVAL_DOSSIER_PROFILE).commitment_sha256},
            "authorization_commitment":{"profile":VERTICAL_EXECUTION_AUTHORIZATION_PROFILE,"commitment_sha256":canonical_commitment(
                _plain_json(capability.context.gate_c_authorization),VERTICAL_EXECUTION_AUTHORIZATION_PROFILE).commitment_sha256}}
        if chain!=approved_chain:
            raise A0XVerticalTerminalPackageError("observed material chain differs from independent authority")
        selected_raw,_info=_read_independent(repository_root,"experiments/a0x-six-model/a0-selection-manifest.json")
        selected=json.loads(selected_raw)
        tree_raw,_info=_read_independent(repository_root,"experiments/a0x-six-model/protected-a0-tree.json")
        entries=json.loads(tree_raw)["entries"]
        sealed=[item for item in entries if item.get("entry_kind")=="sealed_target"]
        # The receiver and frozen leg bind the raw selection manifest. Its
        # source-corpus provenance is a separate hash, checked independently.
        if len(sealed)!=1 or target.get("observed_sha256")!=sealed[0]["sha256"] or target.get("selection_corpus_sha256")!=_sha(selected_raw):
            raise A0XVerticalTerminalPackageError("one-shot receipt differs from independent target or selection declarations")
    outcome=result["scientific_outcome"]
    if statistic.get("status")!=outcome or seal.get("status")!=outcome:
        raise A0XVerticalTerminalPackageError("observed statistic or seal outcome differs")
    if activation.get("activation_status")!="completed" or activation.get("activation_target_content_reads")!=0:
        raise A0XVerticalTerminalPackageError("activation was not sealed before target access")
    if target.get("status")!="pass" or type(target.get("content_reads")) is not int or target["content_reads"]!=1:
        raise A0XVerticalTerminalPackageError("target read was not exactly one successful observation")
    if seal.get("analysis_target_content_reads")!=1 or seal.get("target_read_receipt_sha256")!=_sha(raw_values["target"]):
        raise A0XVerticalTerminalPackageError("analysis seal does not bind the one-shot receipt")
    if target.get("activation_receipt_sha256")!=_sha(raw_values["activation"]):
        raise A0XVerticalTerminalPackageError("target receipt does not bind activation")
    assets={item.role:item for item in expected.external_assets}
    if set(assets)!={"dense","index"}:
        raise A0XVerticalTerminalPackageError("sealed evidence lacks both observed assets")
    for role in assets:
        if target.get(role+"_sha256")!=assets[role].sha256 or activation[role]["sha256"]!=assets[role].sha256 or activation[role]["bytes"]!=assets[role].size:
            raise A0XVerticalTerminalPackageError("material receipts do not bind actual assets")
    cal=values["calibration"]
    _validate_calibration_evidence(cal,expected,outcome)
    if outcome in {"positive","null"}:
        if seal.get("statistical_result")!=statistic or result["result_payload"]["statistical_result_sha256"]!=_sha(raw_values["statistic"]):
            raise A0XVerticalTerminalPackageError("sealed statistic bytes or embedded result differ")
        from .a0x_execution import _validate_statistical_result, A0XExecutionError
        try:
            _validate_statistical_result(statistic,status=outcome,pair_binding=_json_mapping(expected.pair_binding),authorization_chain=chain)
        except (ValueError,A0XExecutionError) as error:
            raise A0XVerticalTerminalPackageError("frozen statistical predicate rejected evidence") from error


def _validate_calibration_evidence(cal: Mapping[str,Any],expected: VerticalTerminalExpectation,outcome: str) -> None:
    from .a0_shortcuts import production_mechanics_recipe, _DEFAULT_A0_CONTROLS, _V2_REQUIRED_FIELDS, _v2_sentinel
    from fractions import Fraction
    recipe=production_mechanics_recipe()
    pair=PairBinding.from_mapping(expected.pair_binding)
    if pair.model_id!=recipe["method_selection"]["model"] or pair.revision!=recipe["method_selection"]["revision"] or pair.leg.value!="a0":
        raise A0XVerticalTerminalPackageError("calibration method scope differs from the observed pair")
    fields={"artifact_class","claim_ids","controls","duplicate_coverage","empirical","evaluated_integrity_scopes",
        "evidence_eligible","expert_validated","human_consent_verified","mechanical_evidence_contract","mechanical_evidence_sha256",
        "mechanical_evidence_validation","mechanical_freeze_independently_verified","method_proposal_sha256","method_selection",
        "primary_analysis_recalibrated","primary_scientific_success","production_binding_status","production_mechanics_profile",
        "production_recipe_sha256","scientific_status","status","input_hashes"}
    constants={"artifact_class":"a0-shortcut-audit-prospective","claim_ids":[],"empirical":False,"evidence_eligible":False,
        "expert_validated":False,"human_consent_verified":False,"mechanical_freeze_independently_verified":False,
        "primary_analysis_recalibrated":False,"primary_scientific_success":False,"scientific_status":"exploratory",
        "production_binding_status":"validated_against_source_recipe","production_mechanics_profile":recipe["schema"],
        "production_recipe_sha256":_sha(_canonical_json(recipe)),"method_proposal_sha256":recipe["method_proposal_sha256"],
        "method_selection":recipe["method_selection"],"mechanical_evidence_validation":"validated",
        "duplicate_coverage":"exact-normalized-only; no near-duplicate, paraphrase or semantic screening"}
    properties={key:{"const":value,**({"type":"boolean"} if type(value) is bool else {})} for key,value in constants.items()}
    properties.update({key:{"type":"object"} for key in ("controls","mechanical_evidence_contract","input_hashes")})
    properties.update({"evaluated_integrity_scopes":{"type":"array"},"mechanical_evidence_sha256":{"type":"string","pattern":"^[a-f0-9]{64}$"},
        "status":{"enum":["PASS","NON_INTERPRETABLE"]}})
    schema={"type":"object","additionalProperties":False,"required":sorted(fields),"properties":properties}
    if validate_a0x(dict(cal),schema):
        raise A0XVerticalTerminalPackageError("production calibration evidence schema or recipe differs")
    controls=cal.get("controls")
    if not isinstance(controls,dict) or set(controls)!=set(_DEFAULT_A0_CONTROLS):
        raise A0XVerticalTerminalPackageError("production calibration control registry differs")
    def fraction(value):
        if not isinstance(value,dict) or set(value)!={"numerator","denominator","display"} or type(value["numerator"]) is not int or type(value["denominator"]) is not int or value["denominator"]<=0:
            raise A0XVerticalTerminalPackageError("calibration rational metric schema differs")
        measured=Fraction(value["numerator"],value["denominator"])
        if float(measured)!=value["display"]:
            raise A0XVerticalTerminalPackageError("calibration rational and display differ")
        return measured
    for name,control in controls.items():
        expected_fields=({"status","reason","issues","coverage"} if name=="duplicate_and_near_duplicate_detection" else
            {"status","reason","issues"} if name=="family_leakage_detection" else {"status","reason","evaluations"})
        if not isinstance(control,dict) or set(control)!=expected_fields or control.get("status") not in {"PASS","NON_INTERPRETABLE"}:
            raise A0XVerticalTerminalPackageError("required calibration control is failed, absent or unevaluable")
        if "issues" in control:
            if not isinstance(control["issues"],list) or control["status"]!=("NON_INTERPRETABLE" if control["issues"] else "PASS"):
                raise A0XVerticalTerminalPackageError("integrity control contradicts observed issues")
            if "coverage" in control and control["coverage"]!=constants["duplicate_coverage"]:
                raise A0XVerticalTerminalPackageError("duplicate coverage differs from the approved exact-only scope")
        if "evaluations" in control:
            evaluations=control["evaluations"]
            views=recipe["control_views"][name]
            replicas=[f"replica-{index:02d}" for index in range(len(recipe["replica_seeds"]))] if name.startswith("random_") else [None]
            planned={(view,replica) for view in views for replica in replicas}
            if not isinstance(evaluations,list) or len(evaluations)!=len(planned):
                raise A0XVerticalTerminalPackageError("required calibration evaluation coverage differs")
            observed=set()
            for item in evaluations:
                if not isinstance(item,dict) or set(item)!={"domains","f1","paired_margin","reason","replica","status","units","view"}:
                    raise A0XVerticalTerminalPackageError("calibration evaluation schema differs")
                if item["status"] not in {"PASS","NON_INTERPRETABLE"}:
                    raise A0XVerticalTerminalPackageError("calibration evaluation is unevaluable")
                if not isinstance(item["domains"],dict) or set(item["domains"])!=set(recipe["domains"]):
                    raise A0XVerticalTerminalPackageError("calibration evaluation domain support differs")
                metrics=[(fraction(item["f1"]),fraction(item["paired_margin"]))] if name=="random_partition_controls" else [
                    (fraction(value["f1"]),fraction(value["paired_margin"])) for value in item["domains"].values()]
                measured_status="NON_INTERPRETABLE" if any(_v2_sentinel(*metric) for metric in metrics) else "PASS"
                if item["status"]!=measured_status:
                    raise A0XVerticalTerminalPackageError("calibration sentinel contradicts observed rational metrics")
                observed.add((item["view"],item["replica"]))
            if observed!=planned or control["status"]!=("PASS" if all(item["status"]=="PASS" for item in evaluations) else "NON_INTERPRETABLE"):
                raise A0XVerticalTerminalPackageError("calibration control contradicts its complete evaluations")
    measured="PASS" if all(item["status"]=="PASS" for item in controls.values()) else "NON_INTERPRETABLE"
    if cal["status"]!=measured or (outcome in {"positive","null"} and measured!="PASS"):
        raise A0XVerticalTerminalPackageError("scientific outcome contradicts measured calibration gate")
    mechanical=cal["mechanical_evidence_contract"]
    if not isinstance(mechanical,dict) or set(mechanical)!=_V2_REQUIRED_FIELDS|{"production_recipe_sha256"} or _sha(_canonical_json(mechanical))!=cal["mechanical_evidence_sha256"]:
        raise A0XVerticalTerminalPackageError("mechanical evidence digest differs")
    for key in ("production_recipe_sha256","classes","views","control_views","payload_stages","boundaries"):
        expected_value=cal["production_recipe_sha256"] if key=="production_recipe_sha256" else recipe[key]
        if mechanical.get(key)!=expected_value:
            raise A0XVerticalTerminalPackageError("mechanical declaration differs from frozen source recipe")
    if any(mechanical.get(key)!=recipe[key] for key in ("randomizer","algorithm","numerics","tie_break","payload_encoding","normalization")):
        raise A0XVerticalTerminalPackageError("mechanical algorithm or normalization differs")
    if mechanical.get("schema")!="a0x-shortcut-mechanics-production-evaluation-v1" or mechanical.get("replicas")!=[
        {"id":f"replica-{index:02d}","seed":seed} for index,seed in enumerate(recipe["replica_seeds"])]:
        raise A0XVerticalTerminalPackageError("mechanical schema or predetermined replicas differ")
    hashes=cal["input_hashes"]
    if not isinstance(hashes,dict) or set(hashes)!={"protocol","cases","targets"}:
        raise A0XVerticalTerminalPackageError("calibration input hash roles differ")
    for digest in hashes.values(): _digest(digest,"calibration input digest")
    if expected.qualification_context=="production":
        capability=expected._production_capability
        root=capability.repository_root
        selected_raw,_info=_read_independent(root,"experiments/a0x-six-model/a0-selection-manifest.json")
        selected=json.loads(selected_raw)
        manifest_raw,_info=_read_independent(root,selected["source_corpus_manifest_path"])
        if _sha(manifest_raw)!=selected["source_corpus_manifest_sha256"]:
            raise A0XVerticalTerminalPackageError("independent public corpus declaration differs")
        corpus=json.loads(manifest_raw)
        expected_hashes={"protocol":capability.package_documents["protocol.json"]["source_protocol_raw_sha256"],
            "cases":selected["source_cases_sha256"],"targets":corpus["files"]["calibration_targets_jsonl"]["sha256"]}
        if hashes!=expected_hashes or mechanical.get("python_version")!=capability.context.readiness["python"]["version"] or mechanical.get("unicode_version")!="14.0.0":
            raise A0XVerticalTerminalPackageError("calibration inputs or runtime differ from independent declarations")


def _require_rehearsal_namespace(repo: Path, expected: VerticalTerminalExpectation) -> None:
    if expected.qualification_context != "engineering_rehearsal":
        return
    parts = repo.parts
    if (
        len(parts) < 4 or parts[-4:-2] != (".a0x-runtime", "rehearsal")
        or not parts[-2].isdigit() or parts[-1] != "synthetic-repository"
    ):
        raise A0XVerticalTerminalPackageError("engineering package requires the owned rehearsal namespace")


def _trust_manifest(repository_root: Path, expected: VerticalTerminalExpectation) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    public_roles: set[str] = set()
    for item in expected.trust_files:
        raw, info = _read_independent(repository_root, item.path)
        if len(raw) != item.size or _sha(raw) != item.sha256 or (info.st_dev, info.st_ino) != (item.device, item.inode):
            raise A0XVerticalTerminalPackageError("trust input differs from validated identity")
        _assert_unique_inode_info(info, seen)
        public = _PUBLIC_TRUST_SOURCES.get(item.path)
        if public is not None:
            role, package_path = public
            public_roles.add(role)
            entries.append({"role": role, "path": package_path, "size": len(raw), "raw_sha256": _sha(raw)})
    required_roles = {role for role, _path in _PUBLIC_TRUST_SOURCES.values()}
    if public_roles != required_roles:
        raise A0XVerticalTerminalPackageError("public trust closure lacks an allowlisted source document")
    return {
        "artifact_class": "a0x-vertical-trust-manifest",
        "trust_profile": "a0x-vertical-trust-manifest-v1",
        **expected.identity(),
        "files": sorted(entries, key=lambda entry: entry["role"]),
        "private_execution_inputs_excluded": True,
    }


def _public_trust_documents(repository_root: Path, expected: VerticalTerminalExpectation) -> dict[str, bytes]:
    by_path = {item.path: item for item in expected.trust_files}
    result: dict[str, bytes] = {}
    for source, (_role, package_path) in _PUBLIC_TRUST_SOURCES.items():
        identity = by_path.get(source)
        if identity is None:
            raise A0XVerticalTerminalPackageError("public trust source is absent from validated identity set")
        raw, info = _read_independent(repository_root, source)
        if len(raw) != identity.size or _sha(raw) != identity.sha256 or (info.st_dev, info.st_ino) != (identity.device, identity.inode):
            raise A0XVerticalTerminalPackageError("public trust source differs from validated identity")
        result[package_path] = raw
    return result


def _require_asset_policy(expected: VerticalTerminalExpectation, result: Mapping[str, Any], assets: list[dict[str, Any]]) -> None:
    roles = [item["role"] for item in assets]
    if assets and roles != ["dense", "index"]:
        raise A0XVerticalTerminalPackageError("external assets must be the ordered dense/index pair")
    if expected.qualification_context in {"production", "engineering_rehearsal"} and result["scientific_outcome"] in _ASSET_STATUSES and roles != ["dense", "index"]:
        raise A0XVerticalTerminalPackageError("production scientific terminal requires dense and index assets")


def _public_asset_path(source_head: str, source_tree: str, pair: PairBinding, role: str) -> str:
    if role not in {"dense", "index"}:
        raise A0XVerticalTerminalPackageError("external asset role is unsupported")
    filename = "dense-output.bin" if role == "dense" else "representation-index.json"
    return (
        f"{_PUBLIC_ASSET_ROOT}/{source_head}/{source_tree}/"
        f"{pair.leg.value}/{pair.model_key}/{pair.run_id}/{filename}"
    )


def _render_report(result: Mapping[str, Any], expected: VerticalTerminalExpectation) -> bytes:
    pair = PairBinding.from_mapping(expected.pair_binding)
    outcome = result["scientific_outcome"]
    lines = [
        "# A0X vertical terminal package",
        "",
        f"- Source commit: `{expected.source_head}`",
        f"- Source tree: `{expected.source_tree}`",
        f"- Pair: `{pair.leg.value} / {pair.model_key}`",
        f"- Model revision: `{pair.revision}`",
        f"- Outcome: `{outcome}`",
        f"- Qualification context: `{expected.qualification_context}`",
        f"- Evidence eligible: `{str(result['evidence_eligible']).lower()}`",
        f"- Expert validated: `{str(result['expert_validated']).lower()}`",
        "- Claim IDs: none",
        "",
        "This automated proxy result makes no general TRIZ, causal, mechanism, emergence, or training-data claim.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _validate_schema(value: Mapping[str, Any], name: str, label: str) -> None:
    try:
        schema = json.loads((_ROOT / "schemas" / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XVerticalTerminalPackageError(f"{label} schema is unavailable") from error
    issues = validate_a0x(dict(value), schema)
    if issues:
        raise A0XVerticalTerminalPackageError(f"{label} schema rejected input: {issues[0].message}")


def _destination(root: Path, destination: Path, expected: VerticalTerminalExpectation) -> Path:
    relative = expected.pair_binding.get("output_path")
    if not isinstance(relative, str):
        raise A0XVerticalTerminalPackageError("pair output path is invalid")
    wanted = root / relative
    if destination.is_absolute() != wanted.is_absolute() or destination.absolute() != wanted.absolute():
        raise A0XVerticalTerminalPackageError("destination differs from independent PairBinding")
    return wanted


def _directory_open_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def _open_directory_chain(root: Path, parent: Path, *, create: bool) -> int:
    try:
        relative = parent.absolute().relative_to(root.absolute())
    except ValueError as error:
        raise A0XVerticalTerminalPackageError("destination escapes repository root") from error
    descriptor = os.open(root, _directory_open_flags())
    try:
        for part in relative.parts:
            try:
                child = os.open(part, _directory_open_flags(), dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                child = os.open(part, _directory_open_flags(), dir_fd=descriptor)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise A0XVerticalTerminalPackageError("destination ancestor is not a directory")
            os.close(descriptor)
            descriptor = child
        result = descriptor
        descriptor = -1
        return result
    except OSError as error:
        raise A0XVerticalTerminalPackageError("destination directory chain is unavailable or unsafe") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _require_directory_path_identity(root: Path, parent: Path, pinned_fd: int) -> None:
    current_fd = _open_directory_chain(root, parent, create=False)
    try:
        pinned, current = os.fstat(pinned_fd), os.fstat(current_fd)
        if (pinned.st_dev, pinned.st_ino) != (current.st_dev, current.st_ino):
            raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_PUBLICATION_OWNERSHIP_LOST")
    finally:
        os.close(current_fd)


def _require_named_directory_identity(parent_fd: int, name: str, identity: tuple[int, int]) -> None:
    try:
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_PUBLICATION_OWNERSHIP_LOST") from error
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity:
        raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_PUBLICATION_OWNERSHIP_LOST")


def _atomic_rename_noreplace_at(parent_fd: int, source: str, destination: str) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        if os.uname().sysname == "Darwin":
            function = libc.renameatx_np
            flags = 0x00000004  # RENAME_EXCL
        elif os.uname().sysname == "Linux":
            function = libc.renameat2
            flags = 1  # RENAME_NOREPLACE
        else:
            raise A0XVerticalTerminalPackageError("atomic no-replace publication is unsupported")
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(parent_fd, os.fsencode(source), parent_fd, os.fsencode(destination), flags)
    except AttributeError as error:
        raise A0XVerticalTerminalPackageError("atomic descriptor-relative no-replace publication is unavailable") from error
    if result != 0:
        number = ctypes.get_errno()
        if number == errno.EEXIST:
            raise A0XVerticalTerminalPackageError("terminal destination already exists")
        raise A0XVerticalTerminalPackageError(f"atomic descriptor-relative publication failed (errno={number})")


def _write_new_at(directory_fd: int, name: str, raw: bytes) -> tuple[int, int]:
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600, dir_fd=directory_fd)
    owned_identity: tuple[int, int] | None = None
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != len(raw):
            raise A0XVerticalTerminalPackageError("staged member is not independent and complete")
        owned_identity = (info.st_dev, info.st_ino)
        return owned_identity
    except BaseException:
        # Remove only the file inode created by this open descriptor.
        info = os.fstat(descriptor)
        try:
            named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISREG(named.st_mode) and named.st_nlink == 1 and (named.st_dev, named.st_ino) == (info.st_dev, info.st_ino):
                os.unlink(name, dir_fd=directory_fd)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def _read_member_at(directory_fd: int, name: str) -> tuple[bytes, tuple[int, int]]:
    descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=directory_fd)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 64 * 1024 * 1024:
            raise A0XVerticalTerminalPackageError("staged member is not an independent regular file")
        data = bytearray()
        while len(data) <= before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_nlink) != (after.st_dev, after.st_ino, after.st_size, after.st_nlink) or len(data) != after.st_size:
            raise A0XVerticalTerminalPackageError("staged member changed while reading")
        return bytes(data), (after.st_dev, after.st_ino)
    finally:
        os.close(descriptor)


def _read_json_at(directory_fd: int, name: str, label: str) -> tuple[bytes, dict[str, Any]]:
    raw, _identity = _read_member_at(directory_fd, name)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_reject_nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise A0XVerticalTerminalPackageError(f"{label} is not strict UTF-8 JSON") from error
    if not isinstance(value, dict) or _canonical_json(value) != raw:
        raise A0XVerticalTerminalPackageError(f"{label} is not canonical JSON")
    return raw, value


def _verify_package_membership_fd(directory_fd: int, *, expected_names: set[str] | None) -> None:
    try:
        names = set(os.listdir(directory_fd))
        for name in names:
            info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise A0XVerticalTerminalPackageError("package contains symlink, non-regular, or hardlinked member")
    except OSError as error:
        raise A0XVerticalTerminalPackageError("package membership is unavailable") from error
    if expected_names is not None and names != expected_names:
        raise A0XVerticalTerminalPackageError("package directory membership differs")


def _verify_staged_members_fd(directory_fd: int, has_assets: bool, identities: Mapping[str, tuple[int, int]]) -> None:
    expected = set(_BASE_MEMBERS) | ({_ASSET_MEMBER} if has_assets else set())
    if set(os.listdir(directory_fd)) != expected or set(identities) != expected:
        raise A0XVerticalTerminalPackageError("staged package membership differs")
    for name, identity in identities.items():
        raw, observed = _read_member_at(directory_fd, name)
        if observed != identity or not raw:
            raise A0XVerticalTerminalPackageError("staged member ownership or bytes are invalid")


def _cleanup_owned_stage(
    *, parent_fd: int, stage_fd: int, stage_name: str, stage_identity: tuple[int, int],
    file_identities: Mapping[str, tuple[int, int]],
) -> None:
    _require_named_directory_identity(parent_fd, stage_name, stage_identity)
    contents = set(os.listdir(stage_fd))
    if contents != set(file_identities):
        raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_PUBLICATION_OWNERSHIP_LOST")
    for name, identity in file_identities.items():
        try:
            info = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
        except OSError as error:
            raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_PUBLICATION_OWNERSHIP_LOST") from error
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (info.st_dev, info.st_ino) != identity:
            raise A0XVerticalTerminalPackageError("A0X_VERTICAL_TERMINAL_PUBLICATION_OWNERSHIP_LOST")
    for name in file_identities:
        os.unlink(name, dir_fd=stage_fd)
    _require_named_directory_identity(parent_fd, stage_name, stage_identity)
    os.rmdir(stage_name, dir_fd=parent_fd)


def _directory(path: Path, label: str) -> Path:
    try:
        info = path.lstat()
    except OSError as error:
        raise A0XVerticalTerminalPackageError(f"{label} is unavailable") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise A0XVerticalTerminalPackageError(f"{label} is not a real directory")
    _reject_symlink_components(path, label)
    return path.resolve(strict=True)


def _reject_symlink_components(path: Path, label: str) -> None:
    absolute = path.absolute()
    cursor = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        cursor = cursor / part
        try:
            info = cursor.lstat()
        except OSError as error:
            raise A0XVerticalTerminalPackageError(f"{label} path component is unavailable") from error
        if stat.S_ISLNK(info.st_mode):
            raise A0XVerticalTerminalPackageError(f"{label} path contains a symlink component")


def _read_independent(root: Path, relative: str) -> tuple[bytes, os.stat_result]:
    parts = _safe_parts(relative)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(root, flags)
        try:
            for part in parts[:-1]:
                child_fd = os.open(part, flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = child_fd
            descriptor = os.open(parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=directory_fd)
            try:
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                    raise A0XVerticalTerminalPackageError("input must be an independent regular file")
                data = bytearray()
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > 64 * 1024 * 1024:
                        raise A0XVerticalTerminalPackageError("input exceeds 64 MiB limit")
                after = os.fstat(descriptor)
                if (before.st_dev, before.st_ino, before.st_size, before.st_nlink) != (after.st_dev, after.st_ino, after.st_size, after.st_nlink) or len(data) != after.st_size:
                    raise A0XVerticalTerminalPackageError("input identity changed while reading")
                return bytes(data), after
            finally:
                os.close(descriptor)
        finally:
            os.close(directory_fd)
    except A0XVerticalTerminalPackageError:
        raise
    except OSError as error:
        raise A0XVerticalTerminalPackageError("input path is unavailable or contains a symlink") from error


def _verify_expected_assets(
    repository_root: Path,
    assets: tuple[_ExpectedAsset, ...],
    trust_files: tuple[_ExpectedFile, ...],
) -> None:
    seen: set[tuple[int, int]] = set()
    trust_inodes = {(item.device, item.inode) for item in trust_files}
    for item in assets:
        raw, info = _read_independent(repository_root, item.path)
        if len(raw) != item.size or _sha(raw) != item.sha256:
            raise A0XVerticalTerminalPackageError("external asset bytes differ")
        if (info.st_dev, info.st_ino) in trust_inodes:
            raise A0XVerticalTerminalPackageError("external asset aliases trust input")
        _assert_unique_inode_info(info, seen)


def _safe_parts(relative: str) -> tuple[str, ...]:
    path = PurePosixPath(relative)
    if not isinstance(relative, str) or relative != path.as_posix() or path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise A0XVerticalTerminalPackageError("path is not canonical repository-relative form")
    return path.parts


def _safe_file(root: Path, relative: str, label: str) -> Path:
    parts = _safe_parts(relative)
    cursor = root
    for part in parts:
        cursor = cursor / part
        try:
            info = cursor.lstat()
        except OSError as error:
            raise A0XVerticalTerminalPackageError(f"{label} is missing") from error
        if stat.S_ISLNK(info.st_mode):
            raise A0XVerticalTerminalPackageError(f"{label} has a symlink component")
    if not stat.S_ISREG(cursor.lstat().st_mode) or cursor.lstat().st_nlink != 1:
        raise A0XVerticalTerminalPackageError(f"{label} is not an independent regular file")
    return cursor


def _read_json(root: Path, relative: str, label: str) -> tuple[bytes, dict[str, Any]]:
    raw, _ = _read_independent(root, relative)
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_reject_nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise A0XVerticalTerminalPackageError(f"{label} is not strict UTF-8 JSON") from error
    if not isinstance(value, dict) or _canonical_json(value) != raw:
        raise A0XVerticalTerminalPackageError(f"{label} is not canonical JSON")
    return raw, value


def _membership(root: Path) -> set[str]:
    actual: set[str] = set()
    for path in root.rglob("*"):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise A0XVerticalTerminalPackageError("package contains symlink or non-regular member")
        if info.st_nlink != 1:
            raise A0XVerticalTerminalPackageError("package member is hardlinked")
        actual.add(path.relative_to(root).as_posix())
    return actual


def _assert_unique_inode(path: Path, seen: set[tuple[int, int]]) -> None:
    info = path.lstat()
    _assert_unique_inode_info(info, seen)


def _assert_unique_inode_info(info: os.stat_result, seen: set[tuple[int, int]]) -> None:
    key = (info.st_dev, info.st_ino)
    if info.st_nlink != 1 or key in seen:
        raise A0XVerticalTerminalPackageError("physical aliases and hardlinks are forbidden")
    seen.add(key)


def _path_to_relative(root: Path, path: Path, label: str) -> str:
    try:
        relative = path.absolute().relative_to(root.absolute()).as_posix()
    except ValueError as error:
        raise A0XVerticalTerminalPackageError(f"{label} escapes repository root") from error
    _safe_parts(relative)
    return relative


def _file_entry(role: str, path: str, raw: bytes) -> dict[str, Any]:
    return {"role": role, "path": path, "bytes": len(raw), "raw_sha256": _sha(raw)}


def _write_new(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != len(raw):
            raise A0XVerticalTerminalPackageError("staged member is not independent and complete")
    finally:
        os.close(descriptor)


def _verify_staged_members(stage: Path, has_assets: bool) -> None:
    expected = set(_BASE_MEMBERS) | ({_ASSET_MEMBER} if has_assets else set())
    if _membership(stage) != expected:
        raise A0XVerticalTerminalPackageError("staged package membership differs")


def _json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise A0XVerticalTerminalPackageError("expected JSON object")
    try:
        raw = _canonical_json(_plain_json(value))
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_reject_nonfinite)
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise A0XVerticalTerminalPackageError("value is not JSON-shaped") from error
    if not isinstance(parsed, dict):
        raise A0XVerticalTerminalPackageError("expected JSON object")
    return parsed


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(member) for key, member in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(member) for member in value)
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    raise A0XVerticalTerminalPackageError("expectation contains non-JSON data")


def _plain_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_json(member) for key, member in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(member) for member in value]
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> Any:
    raise ValueError(f"non-finite number {value}")


def _reject_private_or_pooling_fields(value: Any) -> None:
    forbidden = {"argv", "environment", "container_id", "username", "raw_log", "raw_logs", "local_path", "resolved_path", "aggregate", "ranking", "combined_p"}
    if isinstance(value, Mapping):
        if forbidden.intersection(value):
            raise A0XVerticalTerminalPackageError("result payload contains host detail or pooling field")
        for member in value.values():
            _reject_private_or_pooling_fields(member)
    elif isinstance(value, (list, tuple)):
        for member in value:
            _reject_private_or_pooling_fields(member)
    elif value is None or isinstance(value, (str, int, bool, float)):
        if isinstance(value, float) and not (float("-inf") < value < float("inf")):
            raise A0XVerticalTerminalPackageError("non-finite scientific number")
    else:
        raise A0XVerticalTerminalPackageError("result payload is not JSON-shaped")


def _relative(value: str, label: str) -> str:
    _safe_parts(value)
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XVerticalTerminalPackageError(f"{label} is invalid")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise A0XVerticalTerminalPackageError(f"{label} is invalid")
    return value


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise A0XVerticalTerminalPackageError(f"{label} is invalid")
    return result


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "A0XVerticalTerminalPackageError", "VerticalTerminalExpectation",
    "VerticalTerminalPackageRef", "VerifiedVerticalTerminalPackage",
    "PublicVerticalPackageIntegrity", "build_vertical_terminal_package",
    "verify_vertical_terminal_package", "verify_public_vertical_terminal_package",
]
