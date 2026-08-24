"""Fail-closed orchestration seam for one A0X leg/model pair.

The module deliberately has no model-library, subprocess, network, or target
path dependency.  Task 11 supplies exact, hash-bound dossiers before a later
material wrapper can provide the remaining injected stages.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from latent_triz.validator import validate

from .a0x_contract import A0XContractError, Leg, PairBinding, assert_authorization_chain, compute_dense_bound, strict_json_object
from .a0x_execution import AttemptState, seal_terminal_attempt, validate_authorization_chain
from .a0x_freeze import A0XFreezeError, verify_a0_selection_manifest, verify_protected_tree
from .a0x_preflight import load_registry, verify_card_sources


class A0XRunnerError(RuntimeError):
    """Raised when an A0X pair cannot stay one-shot and fail-closed."""


_SCHEMA_PREFIX = "a0x-"
_MATERIAL_DOSSIERS = {
    ("a0", "smollm2-360m"): "experiments/a0x-six-model/dossiers/a0/smollm2_360m.json",
    ("a0", "qwen3-0-6b-base"): "experiments/a0x-six-model/dossiers/a0/qwen3_0_6b_base.json",
    ("a0", "gpt2"): "experiments/a0x-six-model/dossiers/a0/gpt2.json",
    ("a0", "smollm2-135m"): "experiments/a0x-six-model/dossiers/a0/smollm2_135m.json",
    ("a0", "gpt-neo-125m"): "experiments/a0x-six-model/dossiers/a0/gpt_neo_125m.json",
    ("a0", "qwen2-5-0-5b"): "experiments/a0x-six-model/dossiers/a0/qwen2_5_0_5b.json",
    ("r1", "smollm2-360m"): "experiments/a0x-six-model/dossiers/r1/smollm2_360m.json",
    ("r1", "qwen3-0-6b-base"): "experiments/a0x-six-model/dossiers/r1/qwen3_0_6b_base.json",
    ("r1", "gpt2"): "experiments/a0x-six-model/dossiers/r1/gpt2.json",
    ("r1", "smollm2-135m"): "experiments/a0x-six-model/dossiers/r1/smollm2_135m.json",
    ("r1", "gpt-neo-125m"): "experiments/a0x-six-model/dossiers/r1/gpt_neo_125m.json",
    ("r1", "qwen2-5-0-5b"): "experiments/a0x-six-model/dossiers/r1/qwen2_5_0_5b.json",
}


def planned_material_dossiers() -> dict[tuple[str, str], str]:
    """Return the fixed Task-11 dossier locations without opening them."""
    return dict(_MATERIAL_DOSSIERS)


def run_a0x_pair(
    *, root: str | Path, dossier_path: str | Path, authorization_path: str | Path,
    adapter_factory: Callable[[], Any],
) -> dict[str, Any]:
    """Seal the first terminal outcome for exactly one dossier-bound pair.

    This preparatory implementation reaches only the pre-model construction
    seam.  It validates the exact authorization chain, reserves the frozen
    output location, and persists a terminal failure if construction fails.
    No selection capability or target reader is constructed here; Task 11 must
    add the remaining hash-bound material stages before this function is used
    for an authorized execution.
    """
    repository = Path(root).resolve()
    if not repository.is_dir() or repository.is_symlink():
        raise A0XRunnerError("repository root is unavailable")
    dossier = _read_json_document(Path(dossier_path), "dossier")
    authorization = _read_json_document(Path(authorization_path), "authorization")
    try:
        assert_authorization_chain(dossier, authorization, [
            {"pair_binding": dossier["pair_binding"], "authorization_chain": _authorization_chain(dossier, authorization)},
        ])
        pair = PairBinding.from_mapping(dossier["pair_binding"])
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XRunnerError("dossier and authorization chain are invalid") from error
    output = _repository_output(repository, pair)
    terminal_path = output / "terminal-result.json"
    if terminal_path.exists():
        raise A0XRunnerError("terminal attempt already exists")
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise A0XRunnerError("pair output is not empty")
    else:
        output.mkdir(parents=True, exist_ok=False)

    chain = _authorization_chain(dossier, authorization)
    try:
        # This call is the deliberate tokenizer/model-construction seam.  It is
        # adapter injected so synthetic tests never import a model runtime.
        adapter = adapter_factory()
        del adapter
        raise A0XRunnerError("material activation stage is not configured")
    except A0XRunnerError as error:
        terminal = _seal_failure(pair, chain, terminal_path, error)
    except Exception as error:
        terminal = _seal_failure(pair, chain, terminal_path, error)
    return terminal


def verify_a0x_implementation(root: str | Path) -> dict[str, Any]:
    """Validate the no-model A0X implementation surface, without inference."""
    repository = Path(root).resolve()
    if not repository.is_dir() or repository.is_symlink():
        raise A0XRunnerError("repository root is unavailable")
    schema_paths = sorted((repository / "schemas").glob(f"{_SCHEMA_PREFIX}*.schema.json"))
    if not schema_paths:
        raise A0XRunnerError("A0X schemas are unavailable")
    for path in schema_paths:
        _read_schema(path)
    cards = load_registry(repository / "experiments/a0x-six-model/model-registry.json")
    if len(cards) != 6:
        raise A0XRunnerError("A0X model registry must contain exactly six cards")
    for card in cards:
        verify_card_sources(repository, card)
        for leg in (Leg.A0, Leg.R1):
            bound = compute_dense_bound(
                leg,
                cases=48,
                hidden_width=card.hidden_size,
            )
            if bound.total_bytes > bound.cap_bytes:
                raise A0XRunnerError("A0X frozen cap calculation is invalid")
    _validate_selection_manifest(repository)
    _validate_protected_tree(repository, "protected-a0-tree.json")
    _validate_protected_tree(repository, "protected-a0r1-tree.json")
    _validate_fixed_surface(repository)
    return {
        "artifact_class": "a0x-synthetic-implementation-receipt",
        "phase": "synthetic_implementation",
        "schema_count": len(schema_paths),
        "model_card_count": len(cards),
        "fixed_material_target_count": len(_MATERIAL_DOSSIERS),
        "protocol_and_dossier_frozen": False,
        "model_loaded": False,
        "tokenizer_constructed": False,
        "sealed_target_content_reads": 0,
        "ccp_invoked": False,
    }


def _seal_failure(pair: PairBinding, chain: Mapping[str, Any], terminal_path: Path, error: Exception) -> dict[str, Any]:
    try:
        return seal_terminal_attempt(
            state=AttemptState.ACTIVATION, status="failed", pair_binding=pair.as_mapping(),
            authorization_chain=chain, terminal_path=terminal_path,
        )
    except Exception as sealing_error:
        raise A0XRunnerError("could not seal first terminal attempt") from sealing_error


def _authorization_chain(dossier: Mapping[str, Any], authorization: Mapping[str, Any]) -> dict[str, Any]:
    from .a0x_contract import APPROVAL_DOSSIER_PROFILE, EXECUTION_AUTHORIZATION_PROFILE, canonical_commitment

    chain = {
        "dossier_commitment": canonical_commitment(dossier, APPROVAL_DOSSIER_PROFILE).as_mapping(),
        "authorization_commitment": canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE).as_mapping(),
    }
    return validate_authorization_chain(chain)


def _repository_output(repository: Path, pair: PairBinding) -> Path:
    relative = Path(pair.output_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise A0XRunnerError("pair output path is unsafe")
    output = repository / relative
    if not output.resolve().is_relative_to(repository):
        raise A0XRunnerError("pair output path escapes repository")
    return output


def _read_json_document(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = strict_json_object(raw)
    except (OSError, A0XContractError) as error:
        raise A0XRunnerError(f"{label} is unavailable or malformed") from error
    return value


def _validate_selection_manifest(repository: Path) -> None:
    path = repository / "experiments/a0x-six-model/a0-selection-manifest.json"
    value = _read_json_document(path, "A0X selection manifest")
    if validate(value, _read_schema(repository / "schemas/a0x-selection-manifest.schema.json")):
        raise A0XRunnerError("A0X selection manifest fails its schema")
    if value.get("target_content_reads") != 0:
        raise A0XRunnerError("synthetic verification cannot contain target reads")
    try:
        verify_a0_selection_manifest(
            value,
            cases_path=repository / "data/a0/cases.jsonl",
            corpus_manifest_path=repository / "data/a0/manifest.json",
        )
    except A0XFreezeError as error:
        raise A0XRunnerError("A0X selection manifest binding drifted") from error


def _validate_protected_tree(repository: Path, filename: str) -> None:
    path = repository / "experiments/a0x-six-model" / filename
    value = _read_json_document(path, "A0X protected tree")
    if validate(value, _read_schema(repository / "schemas/a0x-protected-tree.schema.json")):
        raise A0XRunnerError("A0X protected tree fails its schema")
    try:
        verify_protected_tree(repository, value, phase="preflight")
    except A0XFreezeError as error:
        raise A0XRunnerError("A0X protected tree binding drifted") from error


def _validate_fixed_surface(repository: Path) -> None:
    required = (
        "src/latent_triz/a0x_runner.py", "scripts/a0x_contract_check.py", "scripts/a0x_material.py",
        "tests/test_a0x_runner.py", "tests/test_a0x_contract_check.py", "tests/test_a0x_material.py",
    )
    for relative in required:
        if not (repository / relative).is_file():
            raise A0XRunnerError(f"A0X synthetic interface is missing: {relative}")
    makefile = (repository / "Makefile").read_text(encoding="utf-8")
    for target, dossier in _MATERIAL_DOSSIERS.items():
        label = f"a0x-material-{target[0]}-{target[1]}"
        if label not in makefile or dossier not in makefile:
            raise A0XRunnerError("fixed A0X material target mapping is incomplete")
    if "a0x-material-" in (repository / "scripts/repository_check.py").read_text(encoding="utf-8"):
        raise A0XRunnerError("repository check must not invoke A0X material targets")


def _read_schema(path: Path) -> dict[str, Any]:
    """Schemas are JSON Schema documents and may contain numeric literals."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XRunnerError("A0X schema is unavailable or malformed") from error
    if not isinstance(value, dict):
        raise A0XRunnerError("A0X schema must be an object")
    return value


__all__ = ["A0XRunnerError", "planned_material_dossiers", "run_a0x_pair", "verify_a0x_implementation"]
