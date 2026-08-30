"""Target-free runtime readiness evidence for one exact A0X pair.

The readiness boundary may inspect executable metadata, installed package
metadata, public model-card evidence, and the already acquired runtime-file
allowlist. It never constructs a tokenizer or model and never reads a sealed
target.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .a0x_contract import PairBinding, sha256_file
from .a0x_preflight import (
    A0XModelCard,
    A0XPreflightError,
    load_model_card,
    load_registry,
    verify_card_sources,
    verify_snapshot_files,
)


READINESS_PROFILE = "a0x-runtime-readiness-v1"
EXPECTED_PYTHON_MAJOR_MINOR = (3, 11)
EXPECTED_PACKAGES = {
    "numpy": "2.4.6",
    "safetensors": "0.8.0",
    "tokenizers": "0.22.2",
    "torch": "2.13.0",
    "transformers": "5.15.0",
}
EXPECTED_API_SYMBOLS = {
    "torch.float32": True,
    "transformers.AutoConfig": True,
    "transformers.AutoModelForCausalLM": True,
    "transformers.AutoTokenizer": True,
}
_REVISION = re.compile(r"^[a-f0-9]{40}$")


class A0XRuntimeReadinessError(ValueError):
    """Readiness evidence is absent, unsafe, or inconsistent."""


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    """Return the one permitted no-newline encoding for a readiness object."""
    try:
        return json.dumps(
            dict(value), sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XRuntimeReadinessError("runtime readiness is not canonical JSON") from error


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def runtime_readiness_path(pair: PairBinding) -> str:
    """Derive a private path without adding a new public runtime-path kind."""
    return (
        f".a0x-runtime/launches/{pair.leg.value}/{pair.model_key}/"
        f"{pair.run_id}.readiness.json"
    )


def build_runtime_readiness(
    *,
    repository_root: str | Path,
    source_head: str,
    pair: PairBinding,
    python_path: str | Path,
    environment_root: str | Path,
    python_probe: Mapping[str, Any],
    registry_loader: Callable[[str | Path], Sequence[A0XModelCard]] = load_registry,
    card_source_verifier: Callable[[str | Path, A0XModelCard], None] = verify_card_sources,
    snapshot_verifier: Callable[[str | Path, A0XModelCard], A0XModelCard] = verify_snapshot_files,
) -> dict[str, Any]:
    """Build one exact readiness object from target-free observations."""
    root = Path(repository_root).resolve(strict=True)
    if not _REVISION.fullmatch(source_head):
        raise A0XRuntimeReadinessError("runtime readiness source HEAD is invalid")
    environment = Path(environment_root).absolute()
    if not environment.is_dir():
        raise A0XRuntimeReadinessError("Python environment root is unavailable")
    candidate = _regular_environment_executable(python_path, environment)
    probe = _validate_python_probe(python_probe, candidate, environment)
    card = _select_card(root, pair, registry_loader)
    model_runtime = _model_runtime_binding(
        root, card,
        card_source_verifier=card_source_verifier,
        snapshot_verifier=snapshot_verifier,
    )
    return {
        "artifact_class": "a0x-runtime-readiness",
        "readiness_profile": READINESS_PROFILE,
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "python": {
            "path": str(candidate),
            "sha256": sha256_file(candidate),
            "version": probe["python_version"],
            "major_minor": list(EXPECTED_PYTHON_MAJOR_MINOR),
            "environment_root": str(environment),
            "base_prefix": probe["sys_base_prefix"],
            "packages": dict(EXPECTED_PACKAGES),
            "api_symbols": dict(EXPECTED_API_SYMBOLS),
        },
        "model_runtime": model_runtime,
    }


def validate_runtime_readiness(
    value: Mapping[str, Any], *, source_head: str, pair: PairBinding,
    python_path: Path | None = None,
) -> dict[str, Any]:
    """Validate the closed readiness shape without reopening runtime assets."""
    expected_top = {
        "artifact_class", "readiness_profile", "source_head", "pair_binding",
        "python", "model_runtime",
    }
    if not isinstance(value, Mapping) or set(value) != expected_top:
        raise A0XRuntimeReadinessError("runtime readiness shape is invalid")
    if (
        value.get("artifact_class") != "a0x-runtime-readiness"
        or value.get("readiness_profile") != READINESS_PROFILE
        or value.get("source_head") != source_head
        or value.get("pair_binding") != pair.as_mapping()
    ):
        raise A0XRuntimeReadinessError("runtime readiness source or pair binding differs")
    python = value.get("python")
    if not isinstance(python, Mapping) or set(python) != {
        "path", "sha256", "version", "major_minor", "environment_root",
        "base_prefix", "packages", "api_symbols",
    }:
        raise A0XRuntimeReadinessError("runtime readiness Python binding is invalid")
    if (
        python.get("major_minor") != list(EXPECTED_PYTHON_MAJOR_MINOR)
        or python.get("packages") != EXPECTED_PACKAGES
        or python.get("api_symbols") != EXPECTED_API_SYMBOLS
        or not isinstance(python.get("version"), str)
        or not python["version"].startswith("3.11.")
        or not isinstance(python.get("sha256"), str)
        or not re.fullmatch(r"[a-f0-9]{64}", python["sha256"])
    ):
        raise A0XRuntimeReadinessError("runtime readiness Python contract differs")
    if python_path is not None and (
        python.get("path") != str(python_path) or sha256_file(python_path) != python.get("sha256")
    ):
        raise A0XRuntimeReadinessError("runtime readiness Python bytes differ")
    model = value.get("model_runtime")
    expected_model = {
        "model_key", "model_id", "revision", "card_path", "card_sha256",
        "runtime_root", "runtime_file_count", "runtime_total_bytes",
        "runtime_files_commitment_sha256",
    }
    if not isinstance(model, Mapping) or set(model) != expected_model:
        raise A0XRuntimeReadinessError("runtime readiness model binding is invalid")
    if (
        model.get("model_key") != pair.model_key
        or model.get("model_id") != pair.model_id
        or model.get("revision") != pair.revision
        or not isinstance(model.get("runtime_file_count"), int)
        or model["runtime_file_count"] < 1
        or not isinstance(model.get("runtime_total_bytes"), int)
        or model["runtime_total_bytes"] < 1
    ):
        raise A0XRuntimeReadinessError("runtime readiness model identity differs")
    for field in ("card_sha256", "runtime_files_commitment_sha256"):
        if not isinstance(model.get(field), str) or not re.fullmatch(r"[a-f0-9]{64}", model[field]):
            raise A0XRuntimeReadinessError("runtime readiness model digest is invalid")
    return dict(value)


def validate_runtime_readiness_live(
    value: Mapping[str, Any], *, repository_root: str | Path, source_head: str,
    pair: PairBinding, python_path: str | Path,
    card_loader: Callable[[str | Path], A0XModelCard] = load_model_card,
    card_source_verifier: Callable[[str | Path, A0XModelCard], None] = verify_card_sources,
    snapshot_verifier: Callable[[str | Path, A0XModelCard], A0XModelCard] = verify_snapshot_files,
) -> dict[str, Any]:
    """Reopen all public runtime bytes and re-enforce independent-file facts."""
    validated = validate_runtime_readiness(
        value, source_head=source_head, pair=pair,
    )
    python = validated["python"]
    environment_raw = python.get("environment_root")
    if not isinstance(environment_raw, str) or not Path(environment_raw).is_absolute():
        raise A0XRuntimeReadinessError("runtime readiness environment root is invalid")
    environment = Path(environment_raw).absolute()
    candidate = _regular_environment_executable(python_path, environment)
    if str(candidate) != python.get("path") or sha256_file(candidate) != python.get("sha256"):
        raise A0XRuntimeReadinessError("runtime readiness Python bytes differ")
    root = Path(repository_root).resolve(strict=True)
    model = validated["model_runtime"]
    card_path = model.get("card_path")
    if not isinstance(card_path, str):
        raise A0XRuntimeReadinessError("runtime readiness card path is invalid")
    try:
        card = card_loader(root / card_path)
    except (A0XPreflightError, OSError, ValueError) as error:
        raise A0XRuntimeReadinessError("runtime readiness card is unavailable") from error
    if (
        card.model_key != pair.model_key
        or card.model_id != pair.model_id
        or card.revision != pair.revision
        or card.card_path != card_path
    ):
        raise A0XRuntimeReadinessError("runtime readiness card identity differs")
    observed_model = _model_runtime_binding(
        root, card,
        card_source_verifier=card_source_verifier,
        snapshot_verifier=snapshot_verifier,
    )
    if observed_model != model:
        raise A0XRuntimeReadinessError("runtime readiness model bytes differ")
    return validated


def _regular_environment_executable(path: str | Path, environment: Path) -> Path:
    candidate = Path(path).absolute()
    try:
        candidate.relative_to(environment)
    except ValueError as error:
        raise A0XRuntimeReadinessError("Python is outside the declared environment") from error
    current = candidate
    while True:
        if current.is_symlink():
            raise A0XRuntimeReadinessError("Python path has a symlink component")
        if current == environment:
            break
        parent = current.parent
        if parent == current:
            raise A0XRuntimeReadinessError("Python environment ancestry is invalid")
        current = parent
    try:
        info = candidate.stat()
    except OSError as error:
        raise A0XRuntimeReadinessError("Python executable is unavailable") from error
    if not candidate.is_file() or info.st_nlink != 1 or not (info.st_mode & 0o111):
        raise A0XRuntimeReadinessError("Python must be an independent regular executable")
    return candidate


def _validate_python_probe(
    value: Mapping[str, Any], candidate: Path, environment: Path,
) -> dict[str, Any]:
    expected = {
        "sys_executable", "python_version", "python_major_minor", "sys_prefix",
        "sys_base_prefix", "packages", "api_symbols",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise A0XRuntimeReadinessError("Python readiness probe shape is invalid")
    if (
        value.get("sys_executable") != str(candidate)
        or value.get("python_major_minor") != list(EXPECTED_PYTHON_MAJOR_MINOR)
        or not isinstance(value.get("python_version"), str)
        or not value["python_version"].startswith("3.11.")
        or value.get("sys_prefix") != str(environment)
        or value.get("sys_base_prefix") == value.get("sys_prefix")
        or value.get("packages") != EXPECTED_PACKAGES
        or value.get("api_symbols") != EXPECTED_API_SYMBOLS
    ):
        raise A0XRuntimeReadinessError("Python readiness probe does not match the exact environment")
    return dict(value)


def _select_card(
    root: Path, pair: PairBinding,
    registry_loader: Callable[[str | Path], Sequence[A0XModelCard]],
) -> A0XModelCard:
    try:
        cards = registry_loader(root / "experiments/a0x-six-model/model-registry.json")
    except (A0XPreflightError, OSError, ValueError) as error:
        raise A0XRuntimeReadinessError("model registry is unavailable") from error
    selected = [
        card for card in cards
        if card.model_key == pair.model_key
        and card.model_id == pair.model_id
        and card.revision == pair.revision
    ]
    if len(selected) != 1:
        raise A0XRuntimeReadinessError("pair does not select exactly one runtime card")
    return selected[0]


def _model_runtime_binding(
    root: Path,
    card: A0XModelCard,
    *,
    card_source_verifier: Callable[[str | Path, A0XModelCard], None],
    snapshot_verifier: Callable[[str | Path, A0XModelCard], A0XModelCard],
) -> dict[str, Any]:
    try:
        card_source_verifier(root, card)
        snapshot_verifier(root / card.runtime_root, card)
    except (A0XPreflightError, OSError, ValueError) as error:
        raise A0XRuntimeReadinessError("pair runtime snapshot is not ready") from error
    snapshot = root / card.runtime_root
    for runtime_file in card.runtime_files:
        path = snapshot / runtime_file.path
        try:
            info = path.stat()
        except OSError as error:
            raise A0XRuntimeReadinessError("pair runtime file is unavailable") from error
        if path.is_symlink() or not path.is_file() or info.st_nlink != 1:
            raise A0XRuntimeReadinessError("pair runtime file must be an independent regular file")
    runtime_files = [
        {"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes}
        for item in card.runtime_files
    ]
    runtime_commitment = hashlib.sha256(
        json.dumps(runtime_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "model_key": card.model_key,
        "model_id": card.model_id,
        "revision": card.revision,
        "card_path": card.card_path,
        "card_sha256": sha256_file(root / card.card_path),
        "runtime_root": card.runtime_root,
        "runtime_file_count": len(runtime_files),
        "runtime_total_bytes": sum(item["size_bytes"] for item in runtime_files),
        "runtime_files_commitment_sha256": runtime_commitment,
    }


__all__ = [
    "A0XRuntimeReadinessError", "EXPECTED_API_SYMBOLS", "EXPECTED_PACKAGES",
    "READINESS_PROFILE", "build_runtime_readiness", "canonical_json_bytes",
    "canonical_json_sha256", "runtime_readiness_path", "validate_runtime_readiness",
    "validate_runtime_readiness_live",
]
