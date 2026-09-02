"""Compile offline, self-contained A0X PairBinding schema projections."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from latent_triz.a0x_pair import PAIR_BINDING_FIELD_METADATA


A0X_SCHEMA_COUNT = 35
A0X_PAIR_DEFINITION_COUNT = 20
_REGISTRY_PATH = Path("schemas/a0x-pair-projections.json")
_FRAGMENT_PATH = Path("schemas/a0x-pair-binding.fragment.json")
_PAIR_FIELDS = frozenset(PAIR_BINDING_FIELD_METADATA)


class ProjectionError(ValueError):
    """Raised when pair projection inventory or registry is not exact."""


def canonical_pair_fragment() -> dict[str, Any]:
    """Return generated PairBinding schema; equality remains semantic-parser work."""
    return {
        "additionalProperties": False,
        "properties": copy.deepcopy(PAIR_BINDING_FIELD_METADATA),
        "required": sorted(_PAIR_FIELDS),
        "type": "object",
    }


def discovered_pair_definitions(root: Path) -> frozenset[tuple[str, str]]:
    """Discover only complete PairBinding definitions in exact A0X inventory."""
    repository = Path(root)
    paths = sorted((repository / "schemas").glob("a0x-*.schema.json"))
    if len(paths) != A0X_SCHEMA_COUNT:
        raise ProjectionError(
            f"A0X schema cardinality drift: expected {A0X_SCHEMA_COUNT}, found {len(paths)}"
        )
    definitions: set[tuple[str, str]] = set()
    for path in paths:
        document = _load_json(path)
        raw_definitions = document.get("$defs", {})
        if not isinstance(raw_definitions, dict):
            raise ProjectionError(f"A0X schema $defs is not an object: {path}")
        for name, definition in raw_definitions.items():
            if _is_pair_definition(definition):
                definitions.add((path.relative_to(repository).as_posix(), name))
    if len(definitions) != A0X_PAIR_DEFINITION_COUNT:
        raise ProjectionError(
            "PairBinding definition cardinality drift: "
            f"expected {A0X_PAIR_DEFINITION_COUNT}, found {len(definitions)}"
        )
    return frozenset(definitions)


def registered_pair_definitions(root: Path) -> frozenset[tuple[str, str]]:
    """Return exact path/name registry, rejecting implicit or malformed overlays."""
    registry = _load_json(Path(root) / _REGISTRY_PATH)
    if set(registry) != {"profile", "projections"}:
        raise ProjectionError("pair projection registry fields are not exact")
    if registry["profile"] != "a0x-pair-projections-v1":
        raise ProjectionError("pair projection registry profile is not supported")
    projections = registry["projections"]
    if not isinstance(projections, list) or len(projections) != A0X_PAIR_DEFINITION_COUNT:
        raise ProjectionError("pair projection registry cardinality drift")
    entries: set[tuple[str, str]] = set()
    for projection in projections:
        if not isinstance(projection, dict) or set(projection) != {"definition", "overlay", "path"}:
            raise ProjectionError("pair projection registry entry fields are not exact")
        path, definition, overlay = projection["path"], projection["definition"], projection["overlay"]
        if not isinstance(path, str) or not path.startswith("schemas/a0x-") or not path.endswith(".schema.json"):
            raise ProjectionError("pair projection registry path is not an A0X schema")
        if not isinstance(definition, str) or not definition:
            raise ProjectionError("pair projection registry definition is invalid")
        _validate_overlay(overlay)
        entry = (path, definition)
        if entry in entries:
            raise ProjectionError(f"duplicate pair projection registry entry: {path}:{definition}")
        entries.add(entry)
    return frozenset(entries)


def compile_pair_projections(root: Path) -> dict[str, bytes]:
    """Compile generated fragment plus all registered self-contained schemas."""
    repository = Path(root)
    discovered = discovered_pair_definitions(repository)
    registered = registered_pair_definitions(repository)
    if discovered != registered:
        missing = sorted(discovered - registered)
        unexpected = sorted(registered - discovered)
        raise ProjectionError(f"pair projection registry mismatch: missing={missing}; unexpected={unexpected}")

    registry = _load_json(repository / _REGISTRY_PATH)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for projection in registry["projections"]:
        grouped.setdefault(projection["path"], []).append(projection)

    outputs = {_FRAGMENT_PATH.as_posix(): _canonical_bytes(canonical_pair_fragment())}
    for relative, projections in grouped.items():
        document = _load_json(repository / relative)
        definitions = _definitions(document)
        for projection in projections:
            definition_name = projection["definition"]
            if definition_name not in definitions:
                raise ProjectionError(f"registered pair definition is absent: {relative}:{definition_name}")
            definitions[definition_name] = _merge_overlay(canonical_pair_fragment(), projection["overlay"])
        outputs[relative] = _canonical_bytes(document)
    return outputs


def _definitions(document: Mapping[str, Any]) -> dict[str, Any]:
    definitions = document.get("$defs")
    if not isinstance(definitions, dict):
        raise ProjectionError("A0X schema does not contain object $defs")
    return definitions


def _is_pair_definition(definition: Any) -> bool:
    if not isinstance(definition, dict):
        return False
    properties = definition.get("properties")
    required = definition.get("required")
    return (
        definition.get("type") == "object"
        and definition.get("additionalProperties") is False
        and isinstance(properties, dict)
        and set(properties) == _PAIR_FIELDS
        and isinstance(required, list)
        and set(required) == _PAIR_FIELDS
    )


def _validate_overlay(overlay: Any) -> None:
    if not isinstance(overlay, dict) or set(overlay) - {"allOf", "properties"}:
        raise ProjectionError("pair projection overlay is not explicit and local")
    properties = overlay.get("properties", {})
    if not isinstance(properties, dict) or set(properties) - _PAIR_FIELDS:
        raise ProjectionError("pair projection overlay changes unregistered fields")
    all_of = overlay.get("allOf", [])
    if not isinstance(all_of, list) or not all(isinstance(value, dict) for value in all_of):
        raise ProjectionError("pair projection allOf overlay is invalid")
    if any(_contains_default(value) for value in properties.values()) or any(_contains_default(value) for value in all_of):
        raise ProjectionError("pair projection overlay cannot introduce a default")
    if any(not _has_only_local_refs(value) for value in (*properties.values(), *all_of)):
        raise ProjectionError("pair projection overlay contains an external reference")


def _merge_overlay(fragment: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    _validate_overlay(overlay)
    projected = copy.deepcopy(fragment)
    for name, override in overlay.get("properties", {}).items():
        if not isinstance(override, dict):
            raise ProjectionError("pair projection field overlay must be an object")
        projected["properties"][name] = _deep_merge(projected["properties"][name], override)
    if "allOf" in overlay:
        projected["allOf"] = copy.deepcopy(overlay["allOf"])
    return projected


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _contains_default(value: Any) -> bool:
    if isinstance(value, dict):
        return "default" in value or any(_contains_default(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_default(child) for child in value)
    return False


def _has_only_local_refs(value: Any) -> bool:
    if isinstance(value, dict):
        reference = value.get("$ref")
        if reference is not None and (not isinstance(reference, str) or not reference.startswith("#/")):
            return False
        return all(_has_only_local_refs(child) for child in value.values())
    if isinstance(value, list):
        return all(_has_only_local_refs(child) for child in value)
    return True


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProjectionError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise ProjectionError(f"JSON document is not an object: {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
