#!/usr/bin/env python3
"""Bounded A0X schema audit that never opens repository instance inputs.

This profile validates the exact schema/source closure recorded by its manifest.
It is not the repository-wide cross-validator and makes no claim about real
protected targets or the 155 legacy instance declarations.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
import os
import stat
import sys
import threading
import types
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


PROFILE = "a0x-target-free-schema-profile-v1"
# Keep proposal provenance and the A0X implementation anchor distinct. The
# eventual candidate HEAD/tree belongs in the external checkpoint, not in an
# artifact committed by that candidate.
PROPOSAL_PROVENANCE_HEAD = "7dbb04d0eecd1ab7d40f4dd3a40f5253affa5367"
PROPOSAL_PROVENANCE_TREE = "14b75e50c23c22cd8b21a506b72fe2af3f0abd21"
IMPLEMENTATION_ANCHOR_HEAD = "01bf0bbb2d4bd09fdf28f7863c364bf1c3c71fce"
IMPLEMENTATION_ANCHOR_TREE = "d52408d84d7d061f9db31d37f5290be78396e617"
PROPOSAL_PATH = "docs/qualification/A0X_N3_TARGET_FREE_SCHEMA_RECONCILIATION_PROPOSAL_2026-09-29.md"
PROPOSAL_SHA256 = "687e716e7eac35c328553637bab034f67844689e7b99425813cab641710d7f2a"
CANONICAL_PLAN_SHA256 = "cdbfa42c1bfed6c21ab002014cfc5c4d2568ad7504b489656af4aab1c1eda54c"
PLAN_COPY_OBSERVED_SHA256 = "73dc41e2c3eb6b8b51b2de143f861a3de86674ebaccb84bab069fdb1595ed331"
LEGACY_SCRIPT = "scripts/schema_cross_validate.py"
FRAGMENT_PATH = "schemas/a0x-pair-binding.fragment.json"
REGISTRY_PATH = "schemas/a0x-pair-projections.json"
PROJECTION_SOURCE = "src/latent_triz/a0x_schema_projection.py"
PAIR_SOURCE = "src/latent_triz/a0x_pair.py"
PACKAGE_INIT = "src/latent_triz/__init__.py"
PROTECTED = (
    "data/a0/procedural-targets/calibration-targets.jsonl",
    "data/a0/sealed-targets/targets.jsonl",
    "data/a0r1/targets/calibration.jsonl",
    "data/a0r1/targets/sealed.jsonl",
)
SENSITIVE = (
    "experiments/exp001-comparative-reference/additional-model-authorization.json",
    "experiments/exp001-comparative-reference/execution-authorization.json",
    "experiments/exp001-comparative-reference/next-model-authorization.json",
    "experiments/exp001-comparative-reference/qwen-download-authorization.json",
    "experiments/exp001-reference-integrated/execution-authorization.json",
    "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json",
    "results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json",
    "results/a0r2c1/preexecution/sealed-execution-authorization.json",
    "experiments/exp002-auto/combined-target-key-template.json",
    "experiments/exp002-qwen3-followup/transfer-target-key-template.json",
    "results/exp002/preexecution/sealed-key-access-template.json",
    "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/sealed-key-access.json",
    "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/sealed-key-access.json",
    "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/sealed-key-access.json",
)
MANIFEST_RELATIVE = "docs/qualification/a0x-target-free-schema-profile-v1-manifest.json"
EXPECTED_SOURCE_HASHES = {
    "docs/superpowers/plans/2026-09-16-a0x-first-result-autonomous-execution.md": PLAN_COPY_OBSERVED_SHA256,
    LEGACY_SCRIPT: "166df74d7a8925c30b027847f55c3b7e81efa1c6e4d85b4190cfb9f737a03aef",
    "src/latent_triz/validator.py": "7d3bec9bbfb4960f70f3b18395d7e75cc928e032a25fbec3897c88e48ebeff91",
    "src/latent_triz/a0x_validator.py": "b17a2be5b9c658b489c068a58ca9c6ed5b4db5e6e4c6462151d46a8275ca4772",
    PROJECTION_SOURCE: "2e803e7152bef7d538c317d35c4d28712fd03dda637d7a0ff00dbb97b2ba852f",
    PAIR_SOURCE: "82f1ecbfdf6f30cc5b19a311ab1cd67c1a0592ffaf27651d4bda5719f097fe19",
    PACKAGE_INIT: "db06d3f6e4698ca55d12b13a7064e0b2d4bac9c966b5bdd930d3d3faf861d34c",
    PROPOSAL_PATH: PROPOSAL_SHA256,
    FRAGMENT_PATH: "66acfe46458da4a7ccd4f1fa57e2c3e97d0610a5f497f0be6f42660c3d59cbea",
    REGISTRY_PATH: "d63f2f1a792d8aa9740ddf12e3740cea08f480cbaa77ecda03e7eca6a0ae2d2e",
}


class ProfileError(ValueError):
    """An exact source, manifest, role, or schema-profile check failed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _safe_relative(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return False
    path = PurePosixPath(value)
    return not any(part in ("", ".", "..") for part in value.split("/")) and path.as_posix() == value


def _lstat_regular_independent(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ProfileError(f"cannot inspect admitted {label}") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ProfileError(f"{label} is not an independent regular file")
    return info


def _directory_open_flags() -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        raise ProfileError("descriptor-safe directory flags are unavailable")
    return os.O_RDONLY | nofollow | directory


def _open_root_directory(root: Path) -> int:
    flags = _directory_open_flags()
    descriptors: list[int] = []
    try:
        current = os.open("/", flags)
        descriptors.append(current)
        for component in Path(os.path.abspath(root)).parts[1:]:
            current = os.open(component, flags, dir_fd=current)
            descriptors.append(current)
        return os.dup(current)
    except OSError as exc:
        raise ProfileError("cannot open repository root without following links") from exc
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _open_relative_directory(parent: int, relative: str) -> int:
    if not _safe_relative(relative):
        raise ProfileError("unsafe relative directory path")
    flags = _directory_open_flags()
    current = os.dup(parent)
    try:
        for component in relative.split("/"):
            next_fd = os.open(component, flags, dir_fd=current)
            os.close(current)
            current = next_fd
        return current
    except OSError as exc:
        os.close(current)
        raise ProfileError("cannot open admitted directory without following links") from exc


def _read_bytes(root: Path, relative: str, expected_hash: str | None = None) -> bytes:
    if not _safe_relative(relative):
        raise ProfileError("unsafe relative path")
    flags = _directory_open_flags()
    opened: list[int] = []
    try:
        descriptor = _open_root_directory(Path(root))
        opened.append(descriptor)
        for component in relative.split("/")[:-1]:
            descriptor = _open_relative_directory(descriptor, component)
            opened.append(descriptor)
        leaf_flags = os.O_RDONLY | os.O_NOFOLLOW
        leaf = os.open(relative.split("/")[-1], leaf_flags, dir_fd=descriptor)
        opened.append(leaf)
        before = os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ProfileError(f"{relative} is not an independent regular file")
        chunks = []
        while True:
            chunk = os.read(leaf, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(leaf)
        stable_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        stable_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if stable_before != stable_after or after.st_nlink != 1 or not stat.S_ISREG(after.st_mode):
            raise ProfileError(f"{relative} changed during descriptor-bound read")
        data = b"".join(chunks)
    except ProfileError:
        raise
    except OSError as exc:
        raise ProfileError(f"cannot read admitted file: {relative}") from exc
    finally:
        for descriptor in reversed(opened):
            try:
                os.close(descriptor)
            except OSError:
                pass
    digest = hashlib.sha256(data).hexdigest()
    if expected_hash is not None and digest != expected_hash:
        raise ProfileError(f"bound file hash drift: {relative}")
    return data


def _json_bytes(data: bytes, label: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProfileError(f"duplicate JSON key in {label}")
            result[key] = value
        return result

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"invalid UTF-8 JSON: {label}") from exc


def _literal_assignment(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    raise ProfileError(f"source literal missing: {name}")


def _root_literals(tree: ast.Module) -> list[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                and isinstance(node.left, ast.Name) and node.left.id == "ROOT"
                and isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)):
            found.add(node.right.value)
    return sorted(found)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ProfileError(f"source function missing: {name}")


def _positional_contract(tree: ast.Module) -> tuple[list[Any], list[str]]:
    """Execute only two AST-extracted pure fixture constructors, never main()."""
    module = ast.Module(body=[_function(tree, "_a0x_positional_pairs"), _function(tree, "_a0x_positional_mutations")], type_ignores=[])
    wrapper = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
              ast.ImportFrom(module="copy", names=[ast.alias(name="deepcopy")], level=0),
              ast.ImportFrom(module="typing", names=[ast.alias(name="Iterable")], level=0), *module.body],
        type_ignores=[],
    )
    namespace: dict[str, Any] = {}
    exec(compile(ast.fix_missing_locations(wrapper), LEGACY_SCRIPT, "exec"), namespace, namespace)
    pairs = namespace["_a0x_positional_pairs"]()
    labels: list[str] = []
    for _, instance in pairs:
        labels.extend(name for name, _ in namespace["_a0x_positional_mutations"](instance))
    if len(pairs) != 3 or len(labels) != 12:
        raise ProfileError("legacy positional examples/mutations cardinality drift")
    return list(pairs), labels


def _pointer(document: Any, reference: str) -> Any:
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise ProfileError("external, empty, or unsupported schema reference")
    current = document
    for raw in reference[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise ProfileError(f"unresolved local schema reference: {reference}")
    return current


def _refs(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                if not isinstance(child, str):
                    raise ProfileError("non-string schema reference")
                result.append(child)
            result.extend(_refs(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(_refs(child))
    return result


def _inventory_schema_files(root: Path, expected_rows: Any = None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    root_fd = _open_root_directory(root)
    try:
        schemas_fd = _open_relative_directory(root_fd, "schemas")
    finally:
        os.close(root_fd)
    try:
        names = sorted(entry.name for entry in os.scandir(schemas_fd) if entry.name.endswith(".json"))
    except (OSError, ProfileError) as exc:
        raise ProfileError("cannot enumerate bound schemas directory") from exc
    finally:
        os.close(schemas_fd)
    actual_paths = [f"schemas/{name}" for name in names]
    if expected_rows is not None:
        if (not isinstance(expected_rows, list)
                or any(not isinstance(row, list) or len(row) != 3 for row in expected_rows)
                or [row[0] for row in expected_rows] != actual_paths):
            raise ProfileError("schema directory differs from closed-world manifest before file reads")
    files: list[dict[str, str]] = []
    docs: dict[str, Any] = {}
    for name in names:
        rel = f"schemas/{name}"
        role = ("projection_registry" if rel == REGISTRY_PATH else
                "schema_fragment" if rel == FRAGMENT_PATH else
                "draft_2020_12_schema" if name.endswith(".schema.json") else "unsupported")
        if role == "unsupported":
            raise ProfileError(f"unclassified schema-directory JSON file: {rel}")
        if expected_rows is not None:
            expected = expected_rows[len(files)]
            if expected[1] != role or not isinstance(expected[2], str):
                raise ProfileError("schema role/hash row differs from closed-world manifest")
            raw = _read_bytes(root, rel, expected[2])
        else:
            raw = _read_bytes(root, rel)
        digest = hashlib.sha256(raw).hexdigest()
        files.append({"path": rel, "role": role, "sha256": digest})
        docs[rel] = _json_bytes(raw, rel)
    counts = {
        "draft_2020_12_schema": sum(row["role"] == "draft_2020_12_schema" for row in files),
        "schema_fragment": sum(row["role"] == "schema_fragment" for row in files),
        "projection_registry": sum(row["role"] == "projection_registry" for row in files),
    }
    if len(files) != 211 or counts != {"draft_2020_12_schema": 209, "schema_fragment": 1, "projection_registry": 1}:
        raise ProfileError(f"schema classification/cardinality drift: {counts}")
    return files, docs


def _registry_contract(root: Path, docs: dict[str, Any]) -> tuple[int, int, list[dict[str, str]]]:
    # Execute only source bytes already verified against the closed manifest.
    sys.dont_write_bytecode = True
    bound = _import_bound_latent_modules(root, ("latent_triz.a0x_pair", "latent_triz.a0x_schema_projection"))
    pair_module = bound["latent_triz.a0x_pair"]
    projection_module = bound["latent_triz.a0x_schema_projection"]
    PAIR_BINDING_FIELD_METADATA = pair_module.PAIR_BINDING_FIELD_METADATA
    A0X_PAIR_DEFINITION_COUNT = projection_module.A0X_PAIR_DEFINITION_COUNT
    _is_pair_definition = projection_module._is_pair_definition
    _merge_overlay = projection_module._merge_overlay
    canonical_pair_fragment = projection_module.canonical_pair_fragment

    fragment = docs[FRAGMENT_PATH]
    canonical = canonical_pair_fragment()
    if fragment != canonical:
        raise ProfileError("pair fragment differs from its hash-bound canonical generator")
    registry = docs[REGISTRY_PATH]
    if not isinstance(registry, dict) or set(registry) != {"profile", "projections"} or registry["profile"] != "a0x-pair-projections-v1":
        raise ProfileError("projection registry contract mismatch")
    rows = registry["projections"]
    if not isinstance(rows, list) or len(rows) != A0X_PAIR_DEFINITION_COUNT or len(rows) != 28:
        raise ProfileError("projection registry must contain exactly 28 rows")
    seen: set[tuple[str, str]] = set()
    overlay_references: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "definition", "overlay"}:
            raise ProfileError("projection registry row fields are not closed")
        path, definition, overlay = row["path"], row["definition"], row["overlay"]
        if path not in docs or path in (REGISTRY_PATH, FRAGMENT_PATH) or not path.endswith(".schema.json"):
            raise ProfileError("projection row points outside admitted bound schema documents")
        if not isinstance(definition, str) or not definition:
            raise ProfileError("projection definition name invalid")
        key = (path, definition)
        if key in seen:
            raise ProfileError("duplicate projection registration")
        seen.add(key)
        base = docs[path]
        defs = base.get("$defs") if isinstance(base, dict) else None
        if not isinstance(defs, dict) or definition not in defs:
            raise ProfileError("projection target definition absent")
        projected = _merge_overlay(canonical, overlay)
        if projected != defs[definition]:
            raise ProfileError(f"projection semantics differ from bound schema target: {path}:{definition}")
        for ref in _refs(overlay):
            _pointer(base, ref)
            overlay_references.append({"source": f"{REGISTRY_PATH}:{path}:{definition}",
                                       "reference": ref, "target_schema": path})

    discovered: set[tuple[str, str]] = set()
    for path, document in docs.items():
        if not path.endswith(".schema.json") or path == "schemas/a0x-public-closure-manifest-v1.schema.json":
            continue
        definitions = document.get("$defs", {}) if isinstance(document, dict) else {}
        if not isinstance(definitions, dict):
            raise ProfileError(f"schema $defs is not an object: {path}")
        for name, definition in definitions.items():
            if _is_pair_definition(definition):
                discovered.add((path, name))
    if discovered != seen:
        raise ProfileError("registered projections differ from in-memory discovered pair definitions")
    # Ensure imported metadata was actually represented by the generated fragment.
    if canonical["properties"] != PAIR_BINDING_FIELD_METADATA:
        raise ProfileError("pair metadata source differs from canonical fragment")
    return len(rows), len(discovered), sorted(overlay_references, key=lambda row: (row["source"], row["reference"]))


def _validate_document_refs(docs: dict[str, Any]) -> list[dict[str, str]]:
    inventory: list[dict[str, str]] = []
    for path, document in docs.items():
        if path in (REGISTRY_PATH, FRAGMENT_PATH):
            continue
        if not isinstance(document, dict) or document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise ProfileError(f"schema document has no exact Draft 2020-12 declaration: {path}")
        Draft202012Validator.check_schema(document)
        for reference in _refs(document):
            _pointer(document, reference)
            inventory.append({"source": path, "reference": reference, "target_schema": path})
    return sorted(inventory, key=lambda row: (row["source"], row["reference"]))


def _hash_for(root: Path, relative: str, expected: str | None = None) -> str:
    data = _read_bytes(root, relative, expected)
    return hashlib.sha256(data).hexdigest()


_BOUND_MODULE_PATHS = {
    "latent_triz.a0x_pair": PAIR_SOURCE,
    "latent_triz.a0x_schema_projection": PROJECTION_SOURCE,
    "latent_triz.a0x_validator": "src/latent_triz/a0x_validator.py",
    "latent_triz.validator": "src/latent_triz/validator.py",
}
_BOUND_IMPORT_LOCK = threading.RLock()
_ACTIVE_BOUND_CONTEXT: "_BoundExecutionContext | None" = None


class _BoundExecutionContext:
    """One invocation's source-hash-verified, filesystem-isolated modules."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root_identity = os.path.abspath(self.root)
        self.modules: dict[str, types.ModuleType] = {}
        self.hashes: dict[str, str] = {}

    def ensure_intact(self) -> None:
        for name, module in self.modules.items():
            if sys.modules.get(name) is not module:
                raise ProfileError(f"bound import namespace replaced during profile invocation: {name}")
        unexpected = sorted(name for name in sys.modules
                            if (name == "latent_triz" or name.startswith("latent_triz."))
                            and name not in self.modules)
        if unexpected:
            raise ProfileError("unowned latent_triz module appeared during profile invocation: "
                               + ", ".join(unexpected))

    def load(self, names: tuple[str, ...]) -> dict[str, types.ModuleType]:
        if any(name not in _BOUND_MODULE_PATHS for name in names):
            raise ProfileError("module request exceeds exact in-memory source closure")
        self.ensure_intact()
        if "latent_triz" not in self.modules:
            raw = _read_bytes(self.root, PACKAGE_INIT, EXPECTED_SOURCE_HASHES[PACKAGE_INIT])
            package = types.ModuleType("latent_triz")
            package.__file__ = f"<bound:{PACKAGE_INIT}>"
            package.__package__ = "latent_triz"
            package.__path__ = []
            self.modules["latent_triz"] = package
            self.hashes["latent_triz"] = hashlib.sha256(raw).hexdigest()
            sys.modules["latent_triz"] = package
            try:
                exec(compile(raw, package.__file__, "exec"), package.__dict__)
            except BaseException:
                raise
            self.ensure_intact()
        result: dict[str, types.ModuleType] = {}
        for name in names:
            if name == "latent_triz.a0x_schema_projection" and "latent_triz.a0x_pair" not in self.modules:
                self.load(("latent_triz.a0x_pair",))
            relative = _BOUND_MODULE_PATHS[name]
            module = self.modules.get(name)
            if module is None:
                raw = _read_bytes(self.root, relative, EXPECTED_SOURCE_HASHES[relative])
                module = types.ModuleType(name)
                module.__file__ = f"<bound:{relative}>"
                module.__package__ = "latent_triz"
                self.modules[name] = module
                self.hashes[name] = hashlib.sha256(raw).hexdigest()
                sys.modules[name] = module
                setattr(self.modules["latent_triz"], name.rsplit(".", 1)[1], module)
                try:
                    exec(compile(raw, module.__file__, "exec"), module.__dict__)
                except BaseException:
                    raise
                self.ensure_intact()
            elif sys.modules.get(name) is not module:
                raise ProfileError(f"bound module replaced during profile invocation: {name}")
            result[name] = module
        self.ensure_intact()
        return result

    def cleanup(self) -> list[str]:
        replacements = []
        for name, module in reversed(tuple(self.modules.items())):
            current = sys.modules.get(name)
            if current is module:
                del sys.modules[name]
            elif current is not None:
                replacements.append(name)
        return replacements


@contextmanager
def _verified_source_execution(root: Path):
    """Reject every preloaded namespace, then isolate exact in-memory modules."""
    global _ACTIVE_BOUND_CONTEXT
    root_identity = os.path.abspath(root)
    active = _ACTIVE_BOUND_CONTEXT
    if active is not None:
        if active.root_identity != root_identity:
            raise ProfileError("nested profile invocation changed repository root")
        active.ensure_intact()
        yield active
        active.ensure_intact()
        return
    with _BOUND_IMPORT_LOCK:
        collisions = sorted(name for name in sys.modules
                            if name == "latent_triz" or name.startswith("latent_triz."))
        if collisions:
            raise ProfileError("preloaded latent_triz namespace rejected before source reads")
        context = _BoundExecutionContext(Path(root))
        _ACTIVE_BOUND_CONTEXT = context
        failure: BaseException | None = None
        try:
            yield context
            context.ensure_intact()
        except BaseException as exc:
            failure = exc
            raise
        finally:
            replacements = context.cleanup()
            _ACTIVE_BOUND_CONTEXT = None
            if replacements:
                message = "bound import namespace replacement detected: " + ", ".join(replacements)
                if failure is not None:
                    raise ProfileError(message) from failure
                raise ProfileError(message)


def _import_bound_latent_modules(root: Path, names: tuple[str, ...]) -> dict[str, types.ModuleType]:
    """Load from the active invocation only; never trust mutable module markers."""
    context = _ACTIVE_BOUND_CONTEXT
    if context is None or context.root_identity != os.path.abspath(root):
        raise ProfileError("bound modules require an active profile invocation")
    return context.load(names)


def _build_manifest_in_context(root: Path) -> dict[str, Any]:
    """Build exact profile manifest without reading any legacy instance path."""
    schema_files, docs = _inventory_schema_files(root)
    schema_paths = {row["path"] for row in schema_files if row["role"] == "draft_2020_12_schema"}
    for rel, expected in EXPECTED_SOURCE_HASHES.items():
        _read_bytes(root, rel, expected)
    legacy_raw = _read_bytes(root, LEGACY_SCRIPT, EXPECTED_SOURCE_HASHES[LEGACY_SCRIPT])
    tree = ast.parse(legacy_raw.decode("utf-8"), filename=LEGACY_SCRIPT)
    pair_tuple = _literal_assignment(tree, "VALIDATION_PAIRS")
    if not isinstance(pair_tuple, tuple) or len(pair_tuple) != 155:
        raise ProfileError("legacy validation pair count drift")
    pair_rows: list[dict[str, str]] = []
    for schema, instance in pair_tuple:
        if schema not in schema_paths or not _safe_relative(instance):
            raise ProfileError("legacy pair outside safe manifest closure")
        role = ("deferred_protected/UNVERIFIED" if instance in PROTECTED else
                "excluded_sensitive_role_unverified" if instance in SENSITIVE else
                "excluded_role_unverified")
        if instance in PROTECTED:
            disposition = "deferred_protected"
            reason = "Protected target role is deliberately not opened or attested in this profile."
            evidence = "adopted_proposal:protected-target-list; path-classification-only"
        elif instance in SENSITIVE:
            disposition = "excluded_sensitive_role_unverified"
            reason = "Sensitive authorization or mapping role is unresolved and excluded from reads."
            evidence = "adopted_proposal:sensitive-path-list; path-classification-only"
        else:
            disposition = "excluded_role_unverified"
            reason = "No independent public-role evidence is available; public validation is not claimed."
            evidence = "adopted_proposal:public-coverage-zero; path-classification-only"
        pair_rows.append({"schema": schema, "instance": instance, "role": role,
                          "disposition": disposition, "reason": reason, "evidence": evidence})
    if len(set((row["schema"], row["instance"]) for row in pair_rows)) != 155:
        raise ProfileError("legacy pair duplication")
    raw_literals = _root_literals(tree)
    schema_hashes = {row["path"]: row["sha256"] for row in schema_files
                     if row["role"] == "draft_2020_12_schema"}
    literals = [_direct_literal_row(path, schema_hashes) for path in raw_literals]
    positional, mutation_labels = _positional_contract(tree)
    schema_references = _validate_document_refs(docs)
    projection_count, discovered_count, projection_references = _registry_contract(root, docs)
    references = sorted(schema_references + projection_references,
                        key=lambda row: (row["source"], row["reference"], row["target_schema"]))
    source_hashes = dict(EXPECTED_SOURCE_HASHES)
    source_hashes["scripts/a0x_target_free_schema_profile.py"] = _hash_for(root, "scripts/a0x_target_free_schema_profile.py")
    source_hashes["tests/test_a0x_target_free_schema_profile.py"] = _hash_for(root, "tests/test_a0x_target_free_schema_profile.py")
    # Bind plan authority separately: its canonical bytes live in the preserved primary checkout.
    return {
        "profile": PROFILE,
        "proposal_provenance": {
            "source_head": PROPOSAL_PROVENANCE_HEAD,
            "source_tree": PROPOSAL_PROVENANCE_TREE,
            "document_path": PROPOSAL_PATH,
            "document_sha256": PROPOSAL_SHA256,
        },
        "implementation_anchor": {
            "head": IMPLEMENTATION_ANCHOR_HEAD,
            "tree": IMPLEMENTATION_ANCHOR_TREE,
        },
        "canonical_plan_authority_sha256": CANONICAL_PLAN_SHA256,
        "isolated_plan_copy_sha256_observed": PLAN_COPY_OBSERVED_SHA256,
        "schema_counts": {"schema_related_json_files": 211, "draft_2020_12_schema_documents": 209,
                          "schema_fragment": 1, "projection_registry": 1},
        "schema_files": [[row["path"], row["role"], row["sha256"]] for row in schema_files],
        "source_files": [[rel, digest] for rel, digest in sorted(source_hashes.items())],
        "legacy_pairs": pair_rows,
        "legacy_pair_count": len(pair_rows),
        "legacy_pairs_sha256": hashlib.sha256(_canonical(pair_rows)).hexdigest(),
        "direct_root_read_literals": literals,
        "direct_root_read_literals_sha256": hashlib.sha256(_canonical(literals)).hexdigest(),
        "positional_examples": {"count": 3, "sha256": hashlib.sha256(_canonical(positional)).hexdigest()},
        "positional_mutations": {"count": 12, "labels": mutation_labels},
        "local_references": {"count": len(references),
                              "sha256": hashlib.sha256(_canonical(references)).hexdigest(),
                              "entries": [[row["source"], row["reference"], row["target_schema"]] for row in references],
                              "schema_document_reference_count": len(schema_references),
                              "projection_count": projection_count,
                              "discovered_pair_definition_count": discovered_count,
                              "resolution": "document-local JSON Pointer; projection overlays against bound target schema"},
        "instance_dispositions": {
            "validated_public": [],
            "validated_public_count": 0,
            "deferred_protected": [[path, "UNVERIFIED"] for path in PROTECTED],
            "excluded_sensitive_role_unverified": list(SENSITIVE),
            "excluded_role_unverified": sorted({row["instance"] for row in pair_rows}
                - set(PROTECTED) - set(SENSITIVE)),
        },
        "validated_synthetic": {"source_count": 2, "schema_count": 4, "case_count": 17,
                                "valid_case_count": 4, "invalid_case_count": 13,
                                "source_roles": ["legacy_positional_fixture_constructors", "profile_procedural_fixture"],
                                "schema_paths": sorted({schema for schema, _ in positional}
                                    | {"schemas/a0-procedural-target.schema.json"}),
                                "valid_cases": {"protected_schema": 1, "legacy_positional": 3},
                                "invalid_cases": {"protected_schema": 1, "legacy_mutations": 12},
                                "all_cases_in_memory": True},
        "execution_boundary": {"network": False, "lazy_fetch": False, "external_refs": False,
                               "subprocess": False, "real_target_conformance_verified": False,
                               "full_repository_schema_validation": False},
    }


def _direct_literal_row(path: str, schema_hashes: dict[str, str]) -> dict[str, Any]:
    if path in schema_hashes:
        return {"path": path, "role": "schema_definition", "disposition": "validated_schema_definition",
                "reason": "Exact literal is a Draft 2020-12 schema input validated from the closed-world schema inventory; this is not an instance-read authorization.",
                "evidence": "schema_files:closed_world_path_role_hash",
                "schema_binding": {"path": path, "sha256": schema_hashes[path]}}
    if path == "schemas":
        role, disposition = "schema_directory_selector", "bounded_to_manifest_schema_files"
        reason, evidence = "Directory enumeration is checked against the exact 211-row manifest.", "schema_files:closed_world_path_role_hash"
    elif path == "src":
        role, disposition = "source_directory_selector", "bounded_to_manifest_source_files"
        reason, evidence = "Import roots are not searched; only hash-bound in-memory modules execute.", "source_files:closed_world_path_hash"
    elif path in SENSITIVE:
        role, disposition = "sensitive_input", "excluded_sensitive_role_unverified"
        reason, evidence = "Sensitive authorization/mapping literal is inventoried but never opened.", "adopted_proposal:sensitive-path-list"
    elif path.startswith("schemas/") and path.endswith(".schema.json"):
        role, disposition = "unresolved_schema_candidate", "excluded_role_unverified"
        reason, evidence = "Schema-like path is absent from the exact manifest schema inventory.", "schema_files:closed_world_membership-required"
    else:
        role, disposition = "instance_input", "excluded_role_unverified"
        reason, evidence = "Legacy fixture/input literal is inventoried but not admitted as public.", "adopted_proposal:public-coverage-zero"
    return {"path": path, "role": role, "disposition": disposition,
            "reason": reason, "evidence": evidence}


def build_manifest(root: Path) -> dict[str, Any]:
    with _verified_source_execution(Path(root)):
        return _build_manifest_in_context(Path(root))


def load_profile_manifest(root: Path, path: Path) -> dict[str, Any]:
    root = Path(root)
    try:
        relative = Path(path).relative_to(root).as_posix()
    except ValueError as exc:
        raise ProfileError("manifest path is outside repository") from exc
    if relative != MANIFEST_RELATIVE:
        raise ProfileError("unexpected manifest path")
    raw = _read_bytes(root, relative)
    value = _json_bytes(raw, relative)
    if not isinstance(value, dict):
        raise ProfileError("manifest root must be object")
    return value


def read_instance(root: Path, manifest: dict[str, Any], relative: str) -> Any:
    """Read only exact `validated_public` entries; current profile has none."""
    if not isinstance(relative, str) or relative in PROTECTED or relative in SENSITIVE:
        raise ProfileError("instance role is protected or excluded")
    public = manifest.get("instance_dispositions", {}).get("validated_public", [])
    rows = [row for row in public if isinstance(row, dict) and row.get("path") == relative]
    if len(rows) != 1 or not _safe_relative(relative):
        raise ProfileError("instance path is not explicitly allowlisted as public")
    if manifest != build_manifest(Path(root)):
        raise ProfileError("instance profile manifest drift")
    digest = rows[0].get("sha256")
    if not isinstance(digest, str):
        raise ProfileError("public instance has no bound digest")
    return _json_bytes(_read_bytes(Path(root), relative, digest), relative)


def _synthetic_coverage(root: Path, docs: dict[str, Any]) -> dict[str, Any]:
    schema_path = "schemas/a0-procedural-target.schema.json"
    schema = docs[schema_path]
    sys.dont_write_bytecode = True
    bound = _import_bound_latent_modules(root, ("latent_triz.a0x_validator", "latent_triz.validator"))
    validate_a0x = bound["latent_triz.a0x_validator"].validate
    validate_minimal = bound["latent_triz.validator"].validate

    good = {
        "target_record_id": "synthetic-target-01", "case_id": "synthetic-case-01",
        "problem_family_id": "synthetic-family-01", "solution_variant_id": "variant_a",
        "operator_proxy_family": "segmentation_like", "generator_rule": "synthetic-rule-01",
        "split": "calibration", "provenance": {"seed": 1, "template_id": "synthetic-template-01",
            "generator_id": "synthetic-generator-01", "license": "Apache-2.0"},
        "target_content_sha256": "a" * 64, "case_content_sha256": "b" * 64,
    }
    bad = {**good, "split": "unapproved"}
    validator = Draft202012Validator(schema)
    if list(validator.iter_errors(good)) or validate_a0x(good, schema) or validate_minimal(good, schema):
        raise ProfileError("synthetic valid target-schema instance rejected")
    if not list(validator.iter_errors(bad)) or not validate_a0x(bad, schema) or not validate_minimal(bad, schema):
        raise ProfileError("synthetic invalid target-schema instance was not rejected by all validators")
    return {schema_path: {"valid_instance_accepted": True, "invalid_instance_rejected": True,
                          "fixture_source": "in_memory_synthetic"}}


def _legacy_positional_coverage(root: Path, docs: dict[str, Any]) -> tuple[int, int]:
    """Validate only AST-extracted in-memory positional examples and mutations."""
    raw = _read_bytes(root, LEGACY_SCRIPT, EXPECTED_SOURCE_HASHES[LEGACY_SCRIPT])
    tree = ast.parse(raw.decode("utf-8"), filename=LEGACY_SCRIPT)
    examples, labels = _positional_contract(tree)
    sys.dont_write_bytecode = True
    validate_a0x = _import_bound_latent_modules(root, ("latent_triz.a0x_validator",))["latent_triz.a0x_validator"].validate

    rejected = 0
    for schema_path, instance in examples:
        schema = docs.get(schema_path)
        if schema is None:
            raise ProfileError("legacy positional schema is outside the bound schema closure")
        reference = Draft202012Validator(schema)
        if list(reference.iter_errors(instance)) or validate_a0x(instance, schema):
            raise ProfileError(f"bound synthetic positional example rejected: {schema_path}")
        for _name, mutation in _pure_mutations(tree, instance):
            if not list(reference.iter_errors(mutation)) or not validate_a0x(mutation, schema):
                raise ProfileError(f"bound synthetic positional mutation accepted: {schema_path}")
            rejected += 1
    if len(examples) != 3 or rejected != 12 or len(labels) != 12:
        raise ProfileError("positional example/mutation coverage changed")
    return len(examples), rejected


def _pure_mutations(tree: ast.Module, instance: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    wrapper = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
              ast.ImportFrom(module="copy", names=[ast.alias(name="deepcopy")], level=0),
              ast.ImportFrom(module="typing", names=[ast.alias(name="Iterable")], level=0),
              _function(tree, "_a0x_positional_mutations")],
        type_ignores=[],
    )
    namespace: dict[str, Any] = {}
    exec(compile(ast.fix_missing_locations(wrapper), LEGACY_SCRIPT, "exec"), namespace, namespace)
    return list(namespace["_a0x_positional_mutations"](instance))


def _run_profile_in_context(root: Path, manifest_path: Path | None = None,
                            manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root)
    if manifest is None:
        if manifest_path is None:
            manifest_path = root / MANIFEST_RELATIVE
        manifest = load_profile_manifest(root, manifest_path)
    # Compare directory enumeration and every declared path/role/hash before opening a schema.
    schema_files, docs = _inventory_schema_files(root, manifest.get("schema_files"))
    expected = build_manifest(root)
    if manifest != expected:
        raise ProfileError("profile manifest drift or non-canonical inventory")
    schema_document_count = 0
    fragment_count = registry_count = 0
    for row in schema_files:
        if row["role"] == "draft_2020_12_schema":
            schema_document_count += 1
        elif row["role"] == "schema_fragment":
            fragment_count += 1
        elif row["role"] == "projection_registry":
            registry_count += 1
    coverage = _synthetic_coverage(root, docs)
    positional_valid, positional_invalid = _legacy_positional_coverage(root, docs)
    disposition = expected["instance_dispositions"]
    return {
        "profile": PROFILE,
        "schema_file_count": len(schema_files),
        "schema_definition_count": schema_document_count,
        "schema_fragment_count": fragment_count,
        "schema_registry_count": registry_count,
        "legacy_pair_count": expected["legacy_pair_count"],
        "positional_example_count": expected["positional_examples"]["count"],
        "positional_mutation_count": expected["positional_mutations"]["count"],
        "positional_validated_count": positional_valid,
        "positional_mutation_rejected_count": positional_invalid,
        "validated_public_count": disposition["validated_public_count"],
        "deferred_protected_count": len(disposition["deferred_protected"]),
        "excluded_sensitive_count": len(disposition["excluded_sensitive_role_unverified"]),
        "excluded_role_unverified_count": len(disposition["excluded_role_unverified"]),
        "validated_synthetic": expected["validated_synthetic"],
        "protected_schema_synthetic_coverage": coverage,
        "local_schema_reference_count": expected["local_references"]["count"],
        "projection_count": expected["local_references"]["projection_count"],
        "real_target_conformance_verified": False,
        "full_repository_schema_validation": False,
        "network_enabled": False,
        "lazy_fetch_enabled": False,
        "external_refs_enabled": False,
    }


def run_profile(root: Path, manifest_path: Path | None = None,
                manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    with _verified_source_execution(Path(root)):
        return _run_profile_in_context(Path(root), manifest_path, manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--print-manifest", action="store_true", help="print canonical manifest to stdout; write no files")
    args = parser.parse_args(argv)
    try:
        if args.print_manifest:
            print(json.dumps(build_manifest(args.root), ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        else:
            print(json.dumps(run_profile(args.root), ensure_ascii=False, indent=2, sort_keys=True))
    except ProfileError as exc:
        print(f"NO-GO: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
