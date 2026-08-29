#!/usr/bin/env python3
"""Fail-closed verification of EXP-002 publication manifests and assets."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class PublicationVerificationError(ValueError):
    """Raised when a publication package is incomplete or mutated."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationVerificationError(f"cannot read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise PublicationVerificationError("publication manifest must be an object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise PublicationVerificationError(f"cannot read external asset: {path}") from exc
    return digest.hexdigest()


def _relative_asset(root: Path, locator: Any) -> Path:
    if not isinstance(locator, str) or not locator or locator.startswith("/"):
        raise PublicationVerificationError("asset locator must be a relative repository path")
    candidate = Path(locator)
    if ".." in candidate.parts:
        raise PublicationVerificationError("asset locator escapes repository root")
    return root / candidate


_PACKAGE_FILES = (
    "execution-receipt.json", "statistical-result.json", "response-index.json",
    "sealed-key-access.json", "recovery-observation.json", "report.md",
)


def _verify_package(repo: Path, package_entry: dict[str, Any]) -> None:
    package_path = _relative_asset(repo, package_entry["package_locator"])
    if not package_path.is_dir():
        raise PublicationVerificationError(f"publication package is missing: {package_path}")
    nested_path = package_path / "publication-manifest.json"
    nested = _load(nested_path)
    if nested.get("artifact_class") != "exp002-publication-manifest" or nested.get("status") != "published":
        raise PublicationVerificationError(f"nested package manifest is not published: {package_entry['package_locator']}")
    nested_packages = nested.get("packages")
    if not isinstance(nested_packages, list) or len(nested_packages) != 1:
        raise PublicationVerificationError("nested package manifest must contain exactly one package")
    nested_entry = nested_packages[0]
    if nested_entry.get("model_id") != package_entry.get("model_id") or nested_entry.get("revision") != package_entry.get("revision") or nested_entry.get("package_locator") != package_entry.get("package_locator"):
        raise PublicationVerificationError("aggregate and nested package identity drift")
    bindings = nested.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != set(_PACKAGE_FILES):
        raise PublicationVerificationError("nested package bindings are incomplete")
    for name in _PACKAGE_FILES:
        path = package_path / name
        if not path.is_file():
            raise PublicationVerificationError(f"package artifact is missing: {name}")
        binding = bindings[name]
        if not isinstance(binding, dict) or binding.get("path") != path.relative_to(repo).as_posix() or binding.get("sha256") != _sha256(path):
            raise PublicationVerificationError(f"package artifact binding mismatch: {name}")


def _verify_tracked_bindings(
    manifest_path: str | Path, *, root: str | Path
) -> tuple[Path, dict[str, Any]]:
    repo = Path(root).resolve()
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = repo / manifest_file
    manifest = _load(manifest_file)
    schema_file = repo / "schemas/exp002-publication-manifest.schema.json"
    schema = _load(schema_file)
    errors = list(Draft202012Validator(schema).iter_errors(manifest))
    if errors:
        raise PublicationVerificationError(errors[0].message)
    for package in manifest["packages"]:
        _verify_package(repo, package)
    for asset in manifest["external_dense_assets"]:
        _relative_asset(repo, asset["locator"])
    return repo, manifest


def verify_publication_manifest_bindings(
    manifest_path: str | Path, *, root: str | Path = ROOT
) -> dict[str, Any]:
    """Verify tracked package bindings without reading external dense assets."""
    _repo, manifest = _verify_tracked_bindings(manifest_path, root=root)
    return {
        "status": "bindings_only",
        "packages": len(manifest["packages"]),
        "verified_package_bindings": len(manifest["packages"]),
        "declared_external_assets": len(manifest["external_dense_assets"]),
        "verified_external_assets": [],
        "model_access": False,
        "sealed_target_access": False,
    }


def verify_publication_manifest(manifest_path: str | Path, *, root: str | Path = ROOT) -> dict[str, Any]:
    """Verify tracked manifest and every declared external dense asset."""
    repo, manifest = _verify_tracked_bindings(manifest_path, root=root)
    verified_assets = []
    for asset in manifest["external_dense_assets"]:
        asset_path = _relative_asset(repo, asset["locator"])
        if not asset_path.is_file():
            raise PublicationVerificationError(f"external dense asset is missing: {asset_path}")
        observed = _sha256(asset_path)
        if observed != asset["sha256"]:
            raise PublicationVerificationError(f"external dense asset hash mismatch: {asset['locator']}")
        verified_assets.append(asset["locator"])
    return {"status": "pass", "packages": len(manifest["packages"]), "verified_package_bindings": len(manifest["packages"]), "verified_external_assets": verified_assets, "model_access": False, "sealed_target_access": False}


def main(argv: list[str]) -> int:
    manifest = argv[1] if len(argv) > 1 else "results/exp002/preexecution/publication-manifest.json"
    result = verify_publication_manifest(manifest)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
