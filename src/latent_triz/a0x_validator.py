from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:.*$")
_DATETIME_Z_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
_DATETIME_OFFSET_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+\-]\d{2}:\d{2}$")

_SUPPORTED_SCHEMA_KEYWORDS = frozenset(
    {
        "$comment", "$defs", "$id", "$ref", "$schema", "additionalProperties",
        "allOf", "const", "contains", "default", "deprecated", "description",
        "else", "enum", "examples", "exclusiveMaximum", "exclusiveMinimum",
        "format", "if", "items", "maxItems", "maximum", "minItems", "minLength",
        "minProperties", "minimum", "pattern", "prefixItems", "properties", "readOnly", "required",
        "then", "title", "type", "uniqueItems", "writeOnly",
    }
)
_SUPPORTED_FORMATS = frozenset({"date", "date-time", "uri"})


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


def validate(instance: Any, schema: Dict[str, Any]) -> List[ValidationIssue]:
    issues = _check_schema(schema)
    if issues:
        return issues
    _validate(instance, schema, path="root", issues=issues, root_schema=schema, ref_stack=())
    return issues


def _validate(
    instance: Any,
    schema: Any,
    path: str,
    issues: List[ValidationIssue],
    *,
    root_schema: Dict[str, Any],
    ref_stack: Sequence[str],
) -> None:
    if schema is True:
        return
    if schema is False:
        issues.append(ValidationIssue(path, "Boolean schema rejects every value"))
        return
    if not isinstance(schema, dict):
        issues.append(ValidationIssue(path, "Schema node must be an object or boolean"))
        return

    reference = schema.get("$ref")
    if isinstance(reference, str):
        if reference in ref_stack:
            issues.append(ValidationIssue(path, f"Cyclic local reference {reference!r}"))
            return
        target = _resolve_local_ref(root_schema, reference)
        if target is None:
            issues.append(ValidationIssue(path, f"Unresolvable local reference {reference!r}"))
            return
        _validate(
            instance,
            target,
            path,
            issues,
            root_schema=root_schema,
            ref_stack=(*ref_stack, reference),
        )

    _validate_type(instance, schema.get("type"), path, issues)

    _validate_const(instance, schema, path, issues)
    _validate_enum(instance, schema, path, issues)
    _validate_pattern(instance, schema, path, issues)
    _validate_range(instance, schema, path, issues)
    _validate_format(instance, schema, path, issues)
    _validate_strings(instance, schema, path, issues)
    _validate_arrays(instance, schema, path, issues, root_schema=root_schema, ref_stack=ref_stack)
    _validate_objects(instance, schema, path, issues, root_schema=root_schema, ref_stack=ref_stack)
    _validate_all_of(instance, schema, path, issues, root_schema=root_schema, ref_stack=ref_stack)
    _validate_condition(instance, schema, path, issues, root_schema=root_schema, ref_stack=ref_stack)


def _check_schema(schema: Any) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if not isinstance(schema, (dict, bool)):
        return [ValidationIssue("schema", "Root schema must be an object or boolean")]
    if isinstance(schema, bool):
        return issues
    _check_schema_node(schema, schema, "schema", issues, ())
    return issues


def _check_schema_node(
    schema: Any,
    root_schema: Dict[str, Any],
    path: str,
    issues: List[ValidationIssue],
    ref_stack: Sequence[str],
) -> None:
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        issues.append(ValidationIssue(path, "Schema node must be an object or boolean"))
        return

    for keyword in sorted(set(schema) - _SUPPORTED_SCHEMA_KEYWORDS):
        issues.append(ValidationIssue(path, f"Unsupported schema keyword {keyword!r}"))

    schema_format = schema.get("format")
    if schema_format is not None and schema_format not in _SUPPORTED_FORMATS:
        issues.append(ValidationIssue(path, f"Unsupported schema format {schema_format!r}"))

    reference = schema.get("$ref")
    if reference is not None:
        if not isinstance(reference, str) or not reference.startswith("#/"):
            issues.append(ValidationIssue(path, "$ref must be a local JSON Pointer beginning with '#/'"))
        elif reference in ref_stack:
            issues.append(ValidationIssue(path, f"Cyclic local reference {reference!r}"))
        else:
            target = _resolve_local_ref(root_schema, reference)
            if target is None:
                issues.append(ValidationIssue(path, f"Unresolvable local reference {reference!r}"))
            else:
                _check_schema_node(target, root_schema, f"{path}.$ref", issues, (*ref_stack, reference))

    for mapping_name in ("properties", "$defs"):
        mapping = schema.get(mapping_name)
        if mapping is None:
            continue
        if not isinstance(mapping, dict):
            issues.append(ValidationIssue(f"{path}.{mapping_name}", f"{mapping_name} must be an object"))
            continue
        for name, child in mapping.items():
            _check_schema_node(child, root_schema, f"{path}.{mapping_name}.{name}", issues, ref_stack)

    for child_name in ("items", "contains", "if", "then", "else"):
        if child_name in schema:
            _check_schema_node(schema[child_name], root_schema, f"{path}.{child_name}", issues, ref_stack)

    prefix_items = schema.get("prefixItems")
    if prefix_items is not None:
        if not isinstance(prefix_items, list):
            issues.append(ValidationIssue(f"{path}.prefixItems", "prefixItems must be an array"))
        else:
            for index, child in enumerate(prefix_items):
                _check_schema_node(child, root_schema, f"{path}.prefixItems[{index}]", issues, ref_stack)

    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        _check_schema_node(additional, root_schema, f"{path}.additionalProperties", issues, ref_stack)
    elif additional is not None and not isinstance(additional, bool):
        issues.append(ValidationIssue(f"{path}.additionalProperties", "additionalProperties must be a schema or boolean"))

    all_of = schema.get("allOf")
    if all_of is not None:
        if not isinstance(all_of, list) or not all_of:
            issues.append(ValidationIssue(f"{path}.allOf", "allOf must be a non-empty array"))
        else:
            for index, child in enumerate(all_of):
                _check_schema_node(child, root_schema, f"{path}.allOf[{index}]", issues, ref_stack)


def _resolve_local_ref(root_schema: Dict[str, Any], reference: str) -> Any | None:
    if not reference.startswith("#/"):
        return None
    current: Any = root_schema
    for raw_token in reference[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            return None
        current = current[token]
    return current


def _validate_const(instance: Any, schema: Dict[str, Any], path: str, issues: List[ValidationIssue]) -> None:
    if "const" in schema and instance != schema["const"]:
        issues.append(ValidationIssue(path, f"Value {instance!r} does not equal constant {schema['const']!r}"))


def _validate_type(instance: Any, expected_type: Any, path: str, issues: List[ValidationIssue]) -> None:
    if expected_type is None:
        return

    types = expected_type if isinstance(expected_type, list) else [expected_type]
    ok = False
    for typ in types:
        if typ == "null" and instance is None:
            ok = True
        elif typ == "object" and isinstance(instance, dict):
            ok = True
        elif typ == "array" and isinstance(instance, list):
            ok = True
        elif typ == "string" and isinstance(instance, str):
            ok = True
        elif typ == "boolean" and isinstance(instance, bool):
            ok = True
        elif typ == "integer" and isinstance(instance, int) and not isinstance(instance, bool):
            ok = True
        elif typ == "number" and isinstance(instance, (int, float)) and not isinstance(instance, bool):
            ok = True

    if not ok:
        issues.append(ValidationIssue(path, f"Expected type {expected_type!r}"))


def _validate_enum(instance: Any, schema: Dict[str, Any], path: str, issues: List[ValidationIssue]) -> None:
    if "enum" not in schema:
        return
    if instance not in schema["enum"]:
        issues.append(ValidationIssue(path, f"Value {instance!r} not in enum {schema['enum']!r}"))


def _validate_pattern(instance: Any, schema: Dict[str, Any], path: str, issues: List[ValidationIssue]) -> None:
    if "pattern" not in schema:
        return
    if not isinstance(instance, str):
        return
    pattern = schema["pattern"]
    if not re.search(pattern, instance):
        issues.append(ValidationIssue(path, f"String does not match pattern {pattern!r}"))


def _validate_range(instance: Any, schema: Dict[str, Any], path: str, issues: List[ValidationIssue]) -> None:
    if not isinstance(instance, (int, float)) or isinstance(instance, bool):
        return
    if "minimum" in schema and instance < schema["minimum"]:
        issues.append(ValidationIssue(path, f"Value {instance} is below minimum {schema['minimum']}"))
    if "maximum" in schema and instance > schema["maximum"]:
        issues.append(ValidationIssue(path, f"Value {instance} is above maximum {schema['maximum']}"))
    if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
        issues.append(ValidationIssue(path, f"Value {instance} is not above exclusiveMinimum {schema['exclusiveMinimum']}"))
    if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
        issues.append(ValidationIssue(path, f"Value {instance} is not below exclusiveMaximum {schema['exclusiveMaximum']}"))


def _validate_format(instance: Any, schema: Dict[str, Any], path: str, issues: List[ValidationIssue]) -> None:
    if "format" not in schema or not isinstance(instance, str):
        return

    if schema["format"] == "date":
        if not _DATE_PATTERN.fullmatch(instance):
            issues.append(ValidationIssue(path, f"Expected date format yyyy-mm-dd: {instance!r}"))
            return
        try:
            datetime.date.fromisoformat(instance)
        except ValueError:
            issues.append(ValidationIssue(path, f"Invalid date: {instance!r}"))
        return

    if schema["format"] == "uri":
        if not _URI_SCHEME_PATTERN.match(instance):
            issues.append(ValidationIssue(path, f"Expected URI format: {instance!r}"))
        return

    if schema["format"] == "date-time":
        if not (_DATETIME_Z_PATTERN.fullmatch(instance) or _DATETIME_OFFSET_PATTERN.fullmatch(instance)):
            issues.append(ValidationIssue(path, f"Expected date-time ISO-8601 with UTC timezone: {instance!r}"))
            return

        normalized = instance
        if instance.endswith("Z"):
            normalized = instance[:-1] + "+00:00"
        try:
            dt = datetime.datetime.fromisoformat(normalized)
        except ValueError:
            issues.append(ValidationIssue(path, f"Invalid date-time: {instance!r}"))
            return
        if dt.tzinfo is None or dt.utcoffset() != datetime.timedelta(0):
            issues.append(ValidationIssue(path, f"Expected UTC date-time: {instance!r}"))

def _validate_strings(instance: Any, schema: Dict[str, Any], path: str, issues: List[ValidationIssue]) -> None:
    if not isinstance(instance, str):
        return
    if "minLength" in schema and len(instance) < schema["minLength"]:
        issues.append(ValidationIssue(path, f"String shorter than minimum length {schema['minLength']}"))


def _validate_arrays(
    instance: Any,
    schema: Dict[str, Any],
    path: str,
    issues: List[ValidationIssue],
    *,
    root_schema: Dict[str, Any],
    ref_stack: Sequence[str],
) -> None:
    if not isinstance(instance, list):
        return
    if "minItems" in schema and len(instance) < schema["minItems"]:
        issues.append(ValidationIssue(path, f"Array has fewer than minItems {schema['minItems']}"))
    if "maxItems" in schema and len(instance) > schema["maxItems"]:
        issues.append(ValidationIssue(path, f"Array has more than maxItems {schema['maxItems']}"))
    if schema.get("uniqueItems") is True:
        for index, item in enumerate(instance):
            if any(item == previous for previous in instance[:index]):
                issues.append(ValidationIssue(f"{path}[{index}]", "Array items must be unique"))

    prefix_items = schema.get("prefixItems")
    if isinstance(prefix_items, list):
        for index, item in enumerate(instance):
            if index < len(prefix_items):
                _validate(item, prefix_items[index], f"{path}[{index}]", issues, root_schema=root_schema, ref_stack=ref_stack)
            elif schema.get("items") is False:
                issues.append(ValidationIssue(f"{path}[{index}]", "Additional array item not allowed"))
            elif "items" in schema:
                _validate(item, schema["items"], f"{path}[{index}]", issues, root_schema=root_schema, ref_stack=ref_stack)
    elif "items" in schema:
        for index, item in enumerate(instance):
            _validate(item, schema["items"], f"{path}[{index}]", issues, root_schema=root_schema, ref_stack=ref_stack)

    if "contains" in schema and not any(
        _matches(item, schema["contains"], root_schema=root_schema, ref_stack=ref_stack)
        for item in instance
    ):
        issues.append(ValidationIssue(path, "Array does not contain an item matching contains"))


def _validate_objects(
    instance: Any,
    schema: Dict[str, Any],
    path: str,
    issues: List[ValidationIssue],
    *,
    root_schema: Dict[str, Any],
    ref_stack: Sequence[str],
) -> None:
    if not isinstance(instance, dict):
        return

    if "required" in schema:
        for required in schema["required"]:
            if required not in instance:
                issues.append(ValidationIssue(f"{path}.{required}", f"Missing required property {required!r}"))
    if "minProperties" in schema and len(instance) < schema["minProperties"]:
        issues.append(ValidationIssue(path, f"Object has fewer than minProperties {schema['minProperties']}"))

    properties = schema.get("properties", {})
    for key, value in instance.items():
        sub_path = f"{path}.{key}"
        if isinstance(properties, dict) and key in properties:
            _validate(value, properties[key], sub_path, issues, root_schema=root_schema, ref_stack=ref_stack)
        elif schema.get("additionalProperties") is False:
            issues.append(ValidationIssue(sub_path, f"Additional property not allowed: {key!r}"))
        elif isinstance(schema.get("additionalProperties"), dict):
            _validate(
                value,
                schema["additionalProperties"],
                sub_path,
                issues,
                root_schema=root_schema,
                ref_stack=ref_stack,
            )


def _validate_all_of(
    instance: Any,
    schema: Dict[str, Any],
    path: str,
    issues: List[ValidationIssue],
    *,
    root_schema: Dict[str, Any],
    ref_stack: Sequence[str],
) -> None:
    for child in schema.get("allOf", []):
        _validate(instance, child, path, issues, root_schema=root_schema, ref_stack=ref_stack)


def _validate_condition(
    instance: Any,
    schema: Dict[str, Any],
    path: str,
    issues: List[ValidationIssue],
    *,
    root_schema: Dict[str, Any],
    ref_stack: Sequence[str],
) -> None:
    condition = schema.get("if")
    if not isinstance(condition, dict):
        return

    branch = schema.get("then") if _matches(instance, condition, root_schema=root_schema, ref_stack=ref_stack) else schema.get("else")
    if isinstance(branch, (dict, bool)):
        _validate(instance, branch, path, issues, root_schema=root_schema, ref_stack=ref_stack)


def _matches(instance: Any, schema: Any, *, root_schema: Dict[str, Any], ref_stack: Sequence[str]) -> bool:
    candidate_issues: List[ValidationIssue] = []
    _validate(instance, schema, "root", candidate_issues, root_schema=root_schema, ref_stack=ref_stack)
    return not candidate_issues

