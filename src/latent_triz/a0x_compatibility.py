"""Target-free compatibility checks for frozen A0X pair bindings."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from latent_triz.a0x_pair import A0XContractError, PairBinding
from latent_triz.validator import validate


_DOSSIER_DIRECTORY = Path("experiments/a0x-six-model/approval-dossiers")
_HOSTED_CONSUMERS = (
    (
        "schemas/a0x-gate-b-authorization.schema.json",
        "tests/fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json",
    ),
    (
        "schemas/a0x-hosted-gate-a-verification-receipt.schema.json",
        "tests/fixtures/a0x/hosted-gate-a/positive/verification-receipt.json",
    ),
)
_MODEL_KEYS = (
    "gpt2",
    "gpt_neo_125m",
    "qwen2_5_0_5b",
    "qwen3_0_6b_base",
    "smollm2_135m",
    "smollm2_360m",
)
_EXPECTED_DOSSIER_PATHS = tuple(
    _DOSSIER_DIRECTORY / leg / f"{model_key}.json"
    for leg in ("a0", "r1")
    for model_key in _MODEL_KEYS
)


class CompatibilityOracleError(ValueError):
    """Raised when frozen dossier inventory is not the exact tracked matrix."""


@dataclass(frozen=True)
class CompatibilityFailure:
    dossier_path: str
    leg: str
    model_key: str
    run_id: str
    consumer: str
    pointer: str
    reason: str


@dataclass(frozen=True)
class CompatibilityReport:
    expected_case_count: int
    passed_case_count: int
    failures: tuple[CompatibilityFailure, ...]


def discover_frozen_dossier_paths(root: Path) -> tuple[Path, ...]:
    """Return the exact twelve tracked dossier paths or fail closed."""
    repository = Path(root)
    expected = {repository / relative for relative in _EXPECTED_DOSSIER_PATHS}
    dossier_root = repository / _DOSSIER_DIRECTORY
    actual = set(dossier_root.glob("**/*.json")) if dossier_root.is_dir() else set()
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append("missing tracked approval dossiers: " + ", ".join(_relative(repository, path) for path in missing))
        if unexpected:
            details.append("unexpected approval dossiers: " + ", ".join(_relative(repository, path) for path in unexpected))
        raise CompatibilityOracleError("; ".join(details))
    return tuple(repository / relative for relative in _EXPECTED_DOSSIER_PATHS)


def check_frozen_pair_compatibility(root: Path) -> CompatibilityReport:
    """Validate each real frozen pair against both hosted consumer schemas."""
    repository = Path(root)
    dossier_paths = discover_frozen_dossier_paths(repository)
    dossiers = tuple(_load_dossier(repository, path) for path in dossier_paths)
    _validate_dossier_coordinates(repository, dossiers)
    consumers = tuple(_load_consumer(repository, schema_path, template_path) for schema_path, template_path in _HOSTED_CONSUMERS)

    failures: list[CompatibilityFailure] = []
    passed_case_count = 0
    for dossier_path, dossier in dossiers:
        raw_pair = dossier["pair_binding"]
        leg, model_key, run_id = _pair_coordinates(raw_pair)
        try:
            pair_binding = PairBinding.from_dossier(dossier).as_mapping()
        except A0XContractError as error:
            failures.extend(
                CompatibilityFailure(
                    dossier_path=_relative(repository, dossier_path),
                    leg=leg,
                    model_key=model_key,
                    run_id=run_id,
                    consumer=consumer_schema,
                    pointer="pair_binding",
                    reason=str(error),
                )
                for consumer_schema, _schema, _template in consumers
            )
            continue
        for consumer_schema, schema, template in consumers:
            envelope = copy.deepcopy(template)
            envelope["pair_binding"] = pair_binding
            issues = validate(envelope, schema)
            if not issues:
                passed_case_count += 1
                continue
            failures.extend(
                CompatibilityFailure(
                    dossier_path=_relative(repository, dossier_path),
                    leg=leg,
                    model_key=model_key,
                    run_id=run_id,
                    consumer=consumer_schema,
                    pointer=issue.path.removeprefix("root."),
                    reason=issue.message,
                )
                for issue in issues
            )

    return CompatibilityReport(
        expected_case_count=len(dossiers) * len(consumers),
        passed_case_count=passed_case_count,
        failures=tuple(sorted(failures, key=lambda failure: (
            failure.dossier_path,
            failure.consumer,
            failure.pointer,
            failure.reason,
        ))),
    )


def _load_dossier(root: Path, path: Path) -> tuple[Path, Mapping[str, Any]]:
    value = _load_json(root, path, "approval dossier")
    pair_binding = value.get("pair_binding")
    if not isinstance(pair_binding, Mapping):
        raise CompatibilityOracleError(f"approval dossier lacks object pair_binding: {_relative(root, path)}")
    return path, value


def _validate_dossier_coordinates(root: Path, dossiers: tuple[tuple[Path, Mapping[str, Any]], ...]) -> None:
    seen: dict[tuple[str, str], Path] = {}
    mismatches: list[Path] = []
    for path, dossier in dossiers:
        pair_binding = dossier["pair_binding"]
        relative = path.relative_to(root)
        expected_leg, expected_model_key = relative.parts[-2], path.stem
        leg = pair_binding.get("leg")
        model_key = pair_binding.get("model_key")
        if not isinstance(leg, str) or not isinstance(model_key, str):
            raise CompatibilityOracleError(f"approval dossier lacks pair coordinate: {_relative(root, path)}")
        coordinate = (leg, model_key)
        prior = seen.get(coordinate)
        if prior is not None:
            raise CompatibilityOracleError(
                "duplicate pair coordinate "
                f"{leg}/{model_key}: {_relative(root, prior)}, {_relative(root, path)}"
            )
        seen[coordinate] = path
        if coordinate != (expected_leg, expected_model_key):
            mismatches.append(path)
    if mismatches:
        raise CompatibilityOracleError(
            "approval dossier pair coordinate disagrees with tracked path: "
            + ", ".join(_relative(root, path) for path in mismatches)
        )


def _pair_coordinates(pair_binding: Mapping[str, Any]) -> tuple[str, str, str]:
    """Extract diagnostic coordinates without creating alternate semantics."""
    coordinates = tuple(
        value if isinstance(value, str) else "<invalid>"
        for value in (
            pair_binding.get("leg"), pair_binding.get("model_key"), pair_binding.get("run_id"),
        )
    )
    return coordinates[0], coordinates[1], coordinates[2]


def _load_consumer(root: Path, schema_path: str, template_path: str) -> tuple[str, Mapping[str, Any], Mapping[str, Any]]:
    schema = _load_json(root, root / schema_path, "consumer schema")
    template = _load_json(root, root / template_path, "consumer template")
    if not isinstance(template.get("pair_binding"), Mapping):
        raise CompatibilityOracleError(f"consumer template lacks object pair_binding: {template_path}")
    return schema_path, schema, template


def _load_json(root: Path, path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CompatibilityOracleError(f"cannot read {label}: {_relative(root, path)}") from error
    if not isinstance(value, Mapping):
        raise CompatibilityOracleError(f"{label} is not an object: {_relative(root, path)}")
    return value


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()
