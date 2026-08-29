"""Late-bound, fixed-pair assembly for the A0X material child.

Importing this module is intentionally inert: it does not import Torch or
Transformers, enumerate a snapshot, open a sealed target, or invoke CCP.  The
child validates its private launch descriptor first; this adapter then binds
that descriptor to exactly one authorization and material contract before it
constructs the lifecycle callbacks that may be used at a separately approved
material boundary.
"""
from __future__ import annotations

import hashlib
import json
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .a0x_contract import (
    EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    Leg,
    PairBinding,
    canonical_commitment,
    strict_json_object,
)
from .a0x_material_contract import (
    CLEANUP_MARGIN_SECONDS,
    INTERNAL_BUDGET_SECONDS,
    OUTER_TIMEOUT_SECONDS,
    A0XGuardLaunch,
    derive_runtime_paths,
    validate_guard_launch_pair_binding,
)
from .a0x_material_runtime import MaterialLifecycleDependencies, run_material_lifecycle
from .a0x_runner import planned_material_dossiers


class A0XProductionAdapterError(RuntimeError):
    """The child could not bind one production attempt without ambiguity."""


@dataclass(frozen=True)
class ProductionContext:
    """Immutable pair-scoped inputs reconstructed from the private descriptor."""

    root: Path
    descriptor: Mapping[str, Any]
    descriptor_commitment: str
    source_head: str
    pair: PairBinding
    authorization: Mapping[str, Any]
    authorization_raw_sha256: str
    material_contract: Mapping[str, Any]
    material_contract_raw_sha256: str

    def lifecycle_preflight(self) -> dict[str, Any]:
        """Public-safe envelope for the injected lifecycle only.

        Absolute paths, raw command argv, caches and raw process output are
        deliberately omitted.  The production callback resolves its local
        paths from this immutable context rather than accepting user input.
        """
        return {
            "source_head": self.source_head,
            "pair_binding": self.pair.as_mapping(),
            "authorization_raw_sha256": self.authorization_raw_sha256,
            "material_contract_raw_sha256": self.material_contract_raw_sha256,
            "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
            "internal_budget_seconds": INTERNAL_BUDGET_SECONDS,
            "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
        }


@dataclass(frozen=True)
class ProductionFactories:
    """Narrow synthetic seams; no selector or model override is accepted."""

    dependency_builder: Callable[[ProductionContext], MaterialLifecycleDependencies]
    lifecycle_runner: Callable[..., Mapping[str, Any]]


def build_production_executor(
    *, root: str | Path, descriptor: Mapping[str, Any],
    factories: ProductionFactories | None = None,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Return the one callable bound to this exact descriptor and pair.

    The returned callable has no model/leg/revision/path parameters.  Passing
    a second descriptor is allowed only when it is byte-for-byte equivalent in
    canonical JSON terms; this lets the child hand its already validated object
    through without creating a selector inlet.
    """
    context = _bind_context(root=Path(root), descriptor=descriptor)
    resolved = factories or ProductionFactories(
        dependency_builder=_default_dependencies,
        lifecycle_runner=run_material_lifecycle,
    )

    def execute(received_descriptor: Mapping[str, Any]) -> Mapping[str, Any]:
        if _descriptor_commitment(received_descriptor) != context.descriptor_commitment:
            raise A0XProductionAdapterError("production executor descriptor differs from its fixed binding")
        dependencies = resolved.dependency_builder(context)
        if factories is None and not isinstance(dependencies, MaterialLifecycleDependencies):
            raise A0XProductionAdapterError("production dependency builder did not return a lifecycle contract")
        outcome = resolved.lifecycle_runner(
            pair=context.pair,
            preflight_context=context.lifecycle_preflight(),
            dependencies=dependencies,
        )
        if not isinstance(outcome, Mapping):
            raise A0XProductionAdapterError("production lifecycle did not return a terminal mapping")
        terminal = outcome.get("terminal_outcome")
        if not isinstance(terminal, Mapping) or terminal.get("status") not in {
            "positive", "null", "non_interpretable", "incompatible", "failed",
        }:
            raise A0XProductionAdapterError("production lifecycle did not preserve a terminal result")
        return {"status": str(terminal["status"])}

    return execute


def _bind_context(*, root: Path, descriptor: Mapping[str, Any]) -> ProductionContext:
    """Re-derive one pair from descriptor, authorization, and contract bytes."""
    repository = root.resolve(strict=True)
    descriptor_mapping = _descriptor_mapping(descriptor)
    descriptor_commitment = _descriptor_commitment(descriptor_mapping)
    source_head = descriptor_mapping["source_head"]
    try:
        pair = PairBinding.from_mapping(descriptor_mapping["pair_binding"])
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XProductionAdapterError("production descriptor pair binding is invalid") from error
    runtime_documents = _bound_runtime_documents(repository, descriptor_mapping, pair)
    try:
        authorization = strict_json_object(runtime_documents["authorization"][0])
        contract = strict_json_object(runtime_documents["material_contract"][0])
        canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE)
        auth_pair = PairBinding.from_mapping(authorization["pair_binding"])
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XProductionAdapterError("production authorization is invalid") from error
    if auth_pair.as_mapping() != pair.as_mapping() or authorization.get("source_head") != source_head:
        raise A0XProductionAdapterError("production authorization does not bind the descriptor pair")
    if contract.get("artifact_class") != "a0x-material-execution-contract":
        raise A0XProductionAdapterError("production material contract profile is invalid")
    contract_raw_sha256 = runtime_documents["material_contract"][1]
    if authorization.get("material_contract_raw_sha256") != contract_raw_sha256:
        raise A0XProductionAdapterError("production authorization material contract hash differs")
    try:
        launch = A0XGuardLaunch.from_mapping(authorization["guard_launch"])
        validate_guard_launch_pair_binding(pair, launch)
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XProductionAdapterError("production guard launch is invalid") from error
    if (
        launch.source_head != source_head
        or launch.timeouts.outer_timeout_seconds != OUTER_TIMEOUT_SECONDS
        or launch.timeouts.internal_budget_seconds != INTERNAL_BUDGET_SECONDS
        or launch.timeouts.cleanup_margin_seconds != CLEANUP_MARGIN_SECONDS
    ):
        raise A0XProductionAdapterError("production timeout envelope differs from the fixed A0X profile")
    authorization_raw_sha256 = runtime_documents["authorization"][1]
    return ProductionContext(
        root=repository,
        descriptor=descriptor_mapping,
        descriptor_commitment=descriptor_commitment,
        source_head=source_head,
        pair=pair,
        authorization=authorization,
        authorization_raw_sha256=authorization_raw_sha256,
        material_contract=contract,
        material_contract_raw_sha256=contract_raw_sha256,
    )


def _descriptor_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "descriptor_profile", "source_head", "cwd_kind", "pair_binding", "child_script", "python",
        "environment_template", "runtime_files", "execution",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise A0XProductionAdapterError("production descriptor shape is unsupported")
    if value.get("descriptor_profile") != "a0x-material-child-descriptor-v1":
        raise A0XProductionAdapterError("production descriptor profile is unsupported")
    source_head = value.get("source_head")
    if not isinstance(source_head, str) or len(source_head) != 40 or any(c not in "0123456789abcdef" for c in source_head):
        raise A0XProductionAdapterError("production descriptor source head is invalid")
    if value.get("cwd_kind") != "repository_root":
        raise A0XProductionAdapterError("production descriptor cwd kind is invalid")
    execution = value.get("execution")
    expected_execution = {
        "network": "offline", "generation": "forbidden", "trust_remote_code": False,
        "device": "cpu", "dtype": "float32", "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
        "internal_budget_seconds": INTERNAL_BUDGET_SECONDS,
        "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
    }
    if not isinstance(execution, Mapping) or dict(execution) != expected_execution:
        raise A0XProductionAdapterError("production descriptor execution envelope is invalid")
    return dict(value)


def _descriptor_commitment(value: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise A0XProductionAdapterError("production descriptor is not canonical JSON") from error


def _bound_runtime_documents(
    root: Path, descriptor: Mapping[str, Any], pair: PairBinding,
) -> dict[str, tuple[bytes, str]]:
    expected_paths = {
        "authorization": derive_runtime_paths(pair).authorization_path,
        "material_contract": "experiments/a0x-six-model/material-execution-contract.json",
    }
    files = descriptor.get("runtime_files")
    if not isinstance(files, list) or len(files) != 2:
        raise A0XProductionAdapterError("production descriptor runtime documents are incomplete")
    bound: dict[str, tuple[bytes, str]] = {}
    for entry in files:
        if not isinstance(entry, Mapping) or set(entry) != {"role", "path", "sha256"}:
            raise A0XProductionAdapterError("production descriptor runtime document is invalid")
        role, relative, expected_sha = entry.get("role"), entry.get("path"), entry.get("sha256")
        if role not in expected_paths or relative != expected_paths[role] or role in bound:
            raise A0XProductionAdapterError("production descriptor runtime document role is invalid")
        if not isinstance(expected_sha, str) or len(expected_sha) != 64 or any(c not in "0123456789abcdef" for c in expected_sha):
            raise A0XProductionAdapterError("production descriptor runtime document hash is invalid")
        raw = _read_repository_file(root, str(relative))
        observed = hashlib.sha256(raw).hexdigest()
        if observed != expected_sha:
            raise A0XProductionAdapterError("production descriptor runtime document bytes drifted")
        bound[str(role)] = (raw, observed)
    if set(bound) != set(expected_paths):
        raise A0XProductionAdapterError("production descriptor runtime document set is invalid")
    return bound


def _read_repository_file(root: Path, relative: str) -> bytes:
    path = Path(relative)
    if path.is_absolute() or not relative or any(part in {"", ".", ".."} for part in path.parts):
        raise A0XProductionAdapterError("production runtime path is unsafe")
    candidate = root / path
    current = candidate
    while current != root:
        if current.is_symlink():
            raise A0XProductionAdapterError("production runtime path uses a symlink")
        current = current.parent
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise A0XProductionAdapterError("production runtime document is unavailable") from error
    if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.is_symlink():
        raise A0XProductionAdapterError("production runtime document is unsafe")
    return resolved.read_bytes()


def _default_dependencies(context: ProductionContext) -> MaterialLifecycleDependencies:
    """Assemble lazy real callbacks without constructing material resources.

    Imports happen here rather than at module import.  The model adapter is
    still only loaded from inside the ``model_factory`` callback, after the
    static, frozen pair binding and output preflight have succeeded.
    """
    from .a0x_a0_activations import extract_a0x_a0
    from .a0x_a0_analysis import analyze_a0x_a0
    from .a0x_execution import (
        AttemptState,
        OneShotTargetReader,
        TargetReadReceipt,
        load_a0_public_selection,
        load_r1_public_selection,
        seal_terminal_attempt,
    )
    from .a0x_freeze import verify_frozen_legs, verify_protected_tree
    from .a0x_model_adapter import A0XHiddenStateAdapter
    from .a0x_preflight import (
        load_registry,
        verify_card_sources,
        verify_snapshot_files,
        verify_static_endpoint_availability,
        verify_static_preflight,
    )
    from .a0x_report import build_terminal_package
    from .a0x_r1_activations import extract_a0x_r1
    from .a0x_r1_analysis import analyze_a0x_r1
    from .a0x_verify import verify_a0x_package

    state: dict[str, Any] = {
        "card": None, "freeze": None, "selection": None, "activation": None,
        "target_receipt": None, "preflight_receipt": None, "model_identity_receipt": None,
        "ccp_observation_path": None, "qualification_receipt_path": None,
        "protected_trees": None, "statistical_result_path": None,
    }
    chain = _authorization_chain(context.authorization)
    workspace = context.root / ".a0x-runtime" / "material" / context.pair.leg.value / context.pair.model_key / context.pair.run_id

    def static_preflight(_preflight: Mapping[str, Any], _check: Callable[[str], None]) -> None:
        # Reserve this pair's private workspace before any later failure can be
        # confused with a safe retry. It is distinct from the frozen output.
        if workspace.exists() or workspace.is_symlink():
            raise A0XProductionAdapterError("pair runtime workspace already exists; retry is forbidden")
        workspace.mkdir(parents=True, exist_ok=False)
        freezes = verify_frozen_legs(context.root)
        freeze = freezes[context.pair.leg]
        if freeze.leg_freeze_sha256 != context.pair.leg_freeze_sha256:
            raise A0XProductionAdapterError("pair leg freeze differs from the verified frozen leg")
        cards = load_registry(context.root / "experiments/a0x-six-model/model-registry.json")
        selected = [card for card in cards if card.model_key == context.pair.model_key]
        if len(selected) != 1 or selected[0].model_id != context.pair.model_id or selected[0].revision != context.pair.revision:
            raise A0XProductionAdapterError("pair model identity does not select exactly one registered card")
        card = selected[0]
        verify_card_sources(context.root, card)
        verify_snapshot_files(context.root / card.runtime_root, card)
        verify_static_endpoint_availability(card=card, leg=context.pair.leg)
        runtime_paths = derive_runtime_paths(context.pair, source_head=context.source_head)
        expected_observation = {
            "profile": "a0x-guard-preflight-observation-v1",
            "path": runtime_paths.observation_directory + "guard-preflight-observation.json",
        }
        if context.authorization.get("guard_preflight_observation") != expected_observation:
            raise A0XProductionAdapterError("authorization guard-preflight observation binding differs")
        observation_path = context.root / expected_observation["path"]
        observation_raw = _read_repository_file(context.root, expected_observation["path"])
        observation = strict_json_object(observation_raw)
        qualification_relative = runtime_paths.qualification_receipt_path
        if qualification_relative is None:
            raise A0XProductionAdapterError("pair-derived qualification receipt path is unavailable")
        qualification_path = context.root / qualification_relative
        qualification_raw = _read_repository_file(context.root, qualification_relative)
        _validate_local_qualification_receipt(
            qualification_raw, evidence=context.authorization["qualification_evidence"],
            source_head=context.source_head,
        )
        protected_trees = {
            "a0": strict_json_object(_read_repository_file(context.root, "experiments/a0x-six-model/protected-a0-tree.json")),
            "r1": strict_json_object(_read_repository_file(context.root, "experiments/a0x-six-model/protected-a0r1-tree.json")),
        }
        preflight_receipt = verify_static_preflight(
            card=card, snapshot_root=context.root / card.runtime_root,
            expected_origin=context.source_head, observed_origin=context.source_head,
            output_dir=workspace / "preflight", environment=_offline_environment(context.descriptor),
            pair_binding=context.pair,
            protected_trees=((context.root, protected_trees["a0"]), (context.root, protected_trees["r1"])),
            protected_tree_verifier=verify_protected_tree,
            dossier_path=context.root / _dossier_relative(context.pair),
            expected_dossier_raw_sha256=_sha256_file(context.root / _dossier_relative(context.pair)),
            authorization_path=context.root / derive_runtime_paths(context.pair).authorization_path,
            expected_authorization_raw_sha256=context.authorization_raw_sha256,
            ccp_observation=observation, authorization_chain=chain,
            material_contract_raw_sha256=context.material_contract_raw_sha256,
            ccp_observation_path="ccp-observation.json",
            ccp_observation_raw_sha256=hashlib.sha256(observation_raw).hexdigest(),
        )
        _write_json_exclusive(workspace / "preflight-receipt.json", preflight_receipt)
        state.update(
            card=card, freeze=freeze, preflight_receipt=preflight_receipt,
            ccp_observation_path=observation_path, qualification_receipt_path=qualification_path,
            protected_trees=protected_trees,
        )

    def model_identity(_check: Callable[[str], None]) -> Any:
        card = state.get("card")
        if card is None:
            raise A0XProductionAdapterError("model identity was requested before static preflight")
        receipt = {
            "artifact_class": "a0x-model-identity-receipt",
            "empirical": True, "scientific_status": "exploratory",
            "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
            "pair_binding": context.pair.as_mapping(), "identity_status": "verified",
            "authorization_chain": chain,
        }
        _write_json_exclusive(workspace / "model-identity-receipt.json", receipt)
        state["model_identity_receipt"] = receipt
        return card

    def tokenizer_factory(_check: Callable[[str], None]) -> Any:
        # The adapter's public loader performs its tokenizer offset probe and
        # model construction together.  This value is only the already bound
        # card passed to that loader; it is not a user-selectable tokenizer.
        card = state.get("card")
        if card is None:
            raise A0XProductionAdapterError("tokenizer preparation was requested before static preflight")
        return card

    def model_factory(card: Any, identity: Any, _check: Callable[[str], None]) -> Any:
        if card is not identity or card is not state.get("card"):
            raise A0XProductionAdapterError("model construction identity drifted")
        return A0XHiddenStateAdapter.load(context.root / card.runtime_root, card=card)

    def activation_for(leg: Leg) -> Callable[[Any, Callable[[str], None]], Any]:
        def activation(adapter: Any, check: Callable[[str], None]) -> Any:
            if leg is not context.pair.leg:
                raise A0XProductionAdapterError("activation callback leg differs from the bound pair")
            freeze = state.get("freeze")
            if freeze is None:
                raise A0XProductionAdapterError("activation was requested before static preflight")
            selection = (
                load_a0_public_selection(repository_root=context.root, leg_freeze=freeze)
                if leg is Leg.A0 else load_r1_public_selection(repository_root=context.root, leg_freeze=freeze)
            )
            cases = _public_cases(context.root, leg)
            check("activation-before-extraction")
            extractor = extract_a0x_a0 if leg is Leg.A0 else extract_a0x_r1
            artifacts = extractor(
                adapter=adapter, cases=cases, selection={"case_ids": list(selection.expected_case_ids)},
                pair_binding=context.pair.as_mapping(), authorization_chain=chain,
                output_dir=workspace / "activation", created_at="2026-08-28T00:00:00Z",
            )
            check("activation-after-extraction")
            state.update(selection=selection, activation=artifacts)
            return artifacts
        return activation

    def activation_sealer(artifacts: Any, _check: Callable[[str], None]) -> Any:
        if artifacts is not state.get("activation"):
            raise A0XProductionAdapterError("activation sealing artifact drifted")
        return artifacts

    def target_reader_factory(artifacts: Any, _check: Callable[[str], None]) -> Any:
        if artifacts is not state.get("activation"):
            raise A0XProductionAdapterError("target reader activation binding drifted")
        selection = state.get("selection")
        if selection is None:
            raise A0XProductionAdapterError("target reader selection capability is unavailable")
        target_path, target_sha = _sealed_target_declaration(context.root, context.pair.leg)
        return OneShotTargetReader(
            path=context.root / target_path, expected_sha256=target_sha,
            receipt_path=workspace / "target-read-receipt.json", pair_binding=context.pair.as_mapping(),
            selection=selection, activation_receipt_sha256=_sha256_file(artifacts.receipt_path),
            dense_sha256=_sha256_file(artifacts.dense_path), index_sha256=_sha256_file(artifacts.index_path),
            authorization_chain=chain,
        )

    def target_read(reader: Any, check: Callable[[str], None]) -> Any:
        check("target-read-before-open")
        rows, receipt = reader.read_jsonl_once()
        state["target_receipt"] = receipt
        check("target-read-after-open")
        return rows

    def target_read_evidence(_reader: Any) -> Mapping[str, Any]:
        receipt = state.get("target_receipt")
        if not isinstance(receipt, TargetReadReceipt):
            raw_path = workspace / "target-read-receipt.json"
            if not raw_path.is_file():
                return {"receipt": "sha256:" + "0" * 64, "status": "reservation_failed", "content_reads": 0, "raw_sha256": "0" * 64}
            raw = raw_path.read_bytes()
            receipt = TargetReadReceipt.from_mapping(strict_json_object(raw))
        status = {"read_failed": "open_failed"}.get(receipt.status, receipt.status)
        return {
            "receipt": "sha256:" + _sha256_file(workspace / "target-read-receipt.json"),
            "status": status,
            "content_reads": receipt.content_reads,
            "raw_sha256": _sha256_file(workspace / "target-read-receipt.json"),
        }

    def analysis_for(leg: Leg) -> Callable[[Any, Callable[[str], None]], Any]:
        def analysis(rows: Any, check: Callable[[str], None]) -> Any:
            if leg is not context.pair.leg:
                raise A0XProductionAdapterError("analysis callback leg differs from the bound pair")
            artifacts = state.get("activation")
            if artifacts is None:
                raise A0XProductionAdapterError("analysis activation artifacts are unavailable")
            check("analysis-before-frozen-statistic")
            analyzer = analyze_a0x_a0 if leg is Leg.A0 else analyze_a0x_r1
            result = analyzer(
                pair_binding=context.pair.as_mapping(), target_rows=rows,
                target_read_receipt_bytes=(workspace / "target-read-receipt.json").read_bytes(),
                activation_receipt_bytes=artifacts.receipt_path.read_bytes(),
                dense_asset_bytes=artifacts.dense_path.read_bytes(), index_bytes=artifacts.index_path.read_bytes(),
                shortcut_result={"status": "pass"}, authorization_chain=chain,
            )
            if isinstance(result, Mapping) and result.get("status") in {"positive", "null"}:
                statistic_path = workspace / "statistical-result.json"
                _write_json_exclusive(statistic_path, result)
                state["statistical_result_path"] = statistic_path
            check("analysis-after-frozen-statistic")
            return result
        return analysis

    def terminal_sealer(result: Any, _check: Callable[[str], None]) -> Mapping[str, Any]:
        status = result.get("status") if isinstance(result, Mapping) else None
        if status not in {"positive", "null", "non_interpretable"}:
            raise A0XProductionAdapterError("frozen analysis returned no terminal status")
        return seal_terminal_attempt(
            state=AttemptState.ANALYSIS, status=status,
            target_receipt_path=workspace / "target-read-receipt.json", statistical_result=result if status in {"positive", "null"} else None,
            pair_binding=context.pair.as_mapping(), authorization_chain=chain,
            terminal_path=workspace / "terminal-result.json",
        )

    def failure_sealer(stage: str, _error: BaseException, _pair: PairBinding) -> Mapping[str, Any]:
        if stage in {"static_preflight", "model_identity", "tokenizer_construction", "model_construction"}:
            state_for_stage, target_receipt_path = AttemptState.PREFLIGHT, None
        elif stage in {"target_read", "frozen_analysis"} and (workspace / "target-read-receipt.json").is_file():
            state_for_stage, target_receipt_path = AttemptState.ANALYSIS, workspace / "target-read-receipt.json"
        else:
            state_for_stage, target_receipt_path = AttemptState.ACTIVATION, None
        return seal_terminal_attempt(
            state=state_for_stage, status="failed", pair_binding=context.pair.as_mapping(), authorization_chain=chain,
            target_receipt_path=target_receipt_path, terminal_path=workspace / "terminal-result.json",
        )

    def package_builder(terminal: Mapping[str, Any], _check: Callable[[str], None]) -> Path:
        freeze = state.get("freeze")
        observation_path = state.get("ccp_observation_path")
        protected_trees = state.get("protected_trees")
        if freeze is None or not isinstance(observation_path, Path) or not isinstance(protected_trees, Mapping):
            raise A0XProductionAdapterError("terminal package inputs were not statically bound")
        terminal_path = workspace / "terminal-result.json"
        if not terminal_path.is_file() or terminal != strict_json_object(terminal_path.read_bytes()):
            raise A0XProductionAdapterError("terminal package result differs from the sealed terminal artifact")
        artifacts: dict[str, Path] = {"ccp_observation": observation_path}
        state_name = terminal.get("sealed_from_state")
        if state_name in {AttemptState.ACTIVATION.value, AttemptState.ANALYSIS.value}:
            artifacts["model_identity_receipt"] = workspace / "model-identity-receipt.json"
            artifacts["preflight_receipt"] = workspace / "preflight-receipt.json"
        activation = state.get("activation")
        external_assets: dict[str, Path] = {}
        if activation is not None:
            artifacts["activation_receipt"] = activation.receipt_path
            external_assets = {"dense": activation.dense_path, "index": activation.index_path}
        if state_name == AttemptState.ANALYSIS.value:
            artifacts["target_read_receipt"] = workspace / "target-read-receipt.json"
            statistic = state.get("statistical_result_path")
            if terminal.get("status") in {"positive", "null"}:
                if not isinstance(statistic, Path):
                    raise A0XProductionAdapterError("completed analysis lacks its sealed statistical result")
                artifacts["statistical_result"] = statistic
        return build_terminal_package(
            destination=context.root / context.pair.output_path, repository_root=context.root,
            leg_freeze=freeze, dossier_path=context.root / _dossier_relative(context.pair),
            authorization_path=context.root / derive_runtime_paths(context.pair).authorization_path,
            terminal_result_path=terminal_path, artifacts=artifacts, external_assets=external_assets,
            protected_trees=protected_trees, protected_tree_verifier=verify_protected_tree,
        )

    def package_verifier(package_path: Path, _check: Callable[[str], None]) -> None:
        freeze = state.get("freeze")
        protected_trees = state.get("protected_trees")
        qualification_path = state.get("qualification_receipt_path")
        if freeze is None or not isinstance(protected_trees, Mapping) or not isinstance(qualification_path, Path):
            raise A0XProductionAdapterError("package verification inputs were not statically bound")
        root_receipt = package_path / "output-occupancy-receipt.json"
        verify_a0x_package(
            package_root=package_path, repository_root=context.root, leg_freeze=freeze,
            dossier_path=context.root / _dossier_relative(context.pair),
            authorization_path=context.root / derive_runtime_paths(context.pair).authorization_path,
            expected_root_receipt_sha256=_sha256_file(root_receipt), root_receipt_path=root_receipt,
            protected_trees=protected_trees, protected_tree_verifier=verify_protected_tree,
            qualification_receipt_loader=lambda _evidence: qualification_path.read_bytes(),
        )

    def protected_tree_postflight(_package_path: Path, _check: Callable[[str], None]) -> None:
        protected_trees = state.get("protected_trees")
        if not isinstance(protected_trees, Mapping):
            raise A0XProductionAdapterError("protected-tree postflight inputs were not statically bound")
        for tree in protected_trees.values():
            verify_protected_tree(context.root, tree, phase="postflight")

    return MaterialLifecycleDependencies(
        static_preflight=static_preflight,
        model_identity=model_identity,
        tokenizer_factory=tokenizer_factory,
        model_factory=model_factory,
        activation_by_leg={Leg.A0: activation_for(Leg.A0), Leg.R1: activation_for(Leg.R1)},
        activation_sealer=activation_sealer,
        target_reader_factory=target_reader_factory,
        target_read=target_read,
        target_read_evidence=target_read_evidence,
        analysis_by_leg={Leg.A0: analysis_for(Leg.A0), Leg.R1: analysis_for(Leg.R1)},
        terminal_sealer=terminal_sealer,
        package_builder=package_builder,
        package_verifier=package_verifier,
        protected_tree_postflight=protected_tree_postflight,
        failure_sealer=failure_sealer,
        release_model=_release_model_references,
    )


def _authorization_chain(authorization: Mapping[str, Any]) -> dict[str, Any]:
    approved = authorization.get("approved_dossier_commitment")
    try:
        authorization_commitment = canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE).as_mapping()
    except A0XContractError as error:
        raise A0XProductionAdapterError("authorization commitment is invalid") from error
    if not isinstance(approved, Mapping):
        raise A0XProductionAdapterError("authorization dossier commitment is unavailable")
    return {"dossier_commitment": dict(approved), "authorization_commitment": authorization_commitment}


def _public_cases(root: Path, leg: Leg) -> list[dict[str, Any]]:
    relative = "data/a0/cases.jsonl" if leg is Leg.A0 else "data/a0r1/cases.jsonl"
    raw = _read_repository_file(root, relative)
    try:
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise A0XProductionAdapterError("public activation cases are invalid") from error
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise A0XProductionAdapterError("public activation cases are invalid")
    return rows


def _sealed_target_declaration(root: Path, leg: Leg) -> tuple[str, str]:
    manifest = "experiments/a0x-six-model/protected-a0-tree.json" if leg is Leg.A0 else "experiments/a0x-six-model/protected-a0r1-tree.json"
    try:
        tree = strict_json_object(_read_repository_file(root, manifest))
        matches = [entry for entry in tree["entries"] if isinstance(entry, Mapping) and entry.get("entry_kind") == "sealed_target"]
    except (A0XContractError, KeyError, TypeError) as error:
        raise A0XProductionAdapterError("sealed target declaration is invalid") from error
    if len(matches) != 1:
        raise A0XProductionAdapterError("sealed target declaration is ambiguous")
    path, digest = matches[0].get("path"), matches[0].get("sha256")
    if not isinstance(path, str) or not isinstance(digest, str) or len(digest) != 64:
        raise A0XProductionAdapterError("sealed target declaration is invalid")
    return path, digest


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dossier_relative(pair: PairBinding) -> str:
    try:
        return planned_material_dossiers()[(pair.leg.value, pair.model_key)]
    except KeyError as error:
        raise A0XProductionAdapterError("pair has no frozen approval dossier") from error


def _offline_environment(descriptor: Mapping[str, Any]) -> dict[str, str]:
    template = descriptor.get("environment_template")
    if not isinstance(template, list):
        raise A0XProductionAdapterError("production descriptor environment template is invalid")
    try:
        environment = dict(str(item).split("=", 1) for item in template)
    except ValueError as error:
        raise A0XProductionAdapterError("production descriptor environment template is invalid") from error
    if len(environment) != len(template):
        raise A0XProductionAdapterError("production descriptor environment template repeats a variable")
    return environment


def _write_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise A0XProductionAdapterError("production evidence artifact already exists; retry is forbidden")
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
    except OSError as error:
        raise A0XProductionAdapterError("production evidence artifact could not be sealed") from error


def _validate_local_qualification_receipt(
    raw: bytes, *, evidence: object, source_head: str,
) -> None:
    """Bind the private local receipt to public evidence without raw-log use."""
    if not isinstance(evidence, Mapping):
        raise A0XProductionAdapterError("qualification evidence is unavailable")
    if hashlib.sha256(raw).hexdigest() != evidence.get("qualification_receipt_raw_sha256"):
        raise A0XProductionAdapterError("local qualification receipt raw SHA-256 differs")
    try:
        envelope = strict_json_object(raw)
    except A0XContractError as error:
        raise A0XProductionAdapterError("local qualification receipt is invalid") from error
    if set(envelope) != {"receipt_id", "receipt"} or not isinstance(envelope.get("receipt"), Mapping):
        raise A0XProductionAdapterError("local qualification receipt envelope is invalid")
    receipt = envelope["receipt"]
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    receipt_id = "sha256:" + hashlib.sha256(canonical).hexdigest()
    if envelope.get("receipt_id") != receipt_id or evidence.get("qualification_receipt_id") != receipt_id:
        raise A0XProductionAdapterError("local qualification receipt semantic ID differs")
    ccp = evidence.get("ccp")
    if not isinstance(ccp, Mapping):
        raise A0XProductionAdapterError("local qualification receipt CCP identity is invalid")
    expected_version = str(ccp.get("version", "")).removeprefix("commit-ci-preflight ") + "+matrix-v2-legacy-v1"
    repository, run = receipt.get("repository"), receipt.get("run")
    if (
        receipt.get("schema_version") != "2.0" or receipt.get("overall_status") != "PASS"
        or receipt.get("incomplete_reason") is not None
        or receipt.get("producer") != {"name": "commit-ci-preflight", "version": expected_version}
        or not isinstance(repository, Mapping) or repository.get("commit_sha") != source_head
        or repository.get("dirty") is not False or not isinstance(run, Mapping)
        or run.get("generation") != evidence.get("generation")
    ):
        raise A0XProductionAdapterError("local qualification receipt CCP/source/generation binding differs")


def _release_model_references(adapter: Any, check: Callable[[str], None]) -> None:
    """Drop all adapter-owned references and collect without importing Torch."""
    check("model-release-before-clear")
    for name in ("model", "tokenizer", "torch"):
        if hasattr(adapter, name):
            setattr(adapter, name, None)
    if hasattr(adapter, "model_loaded"):
        setattr(adapter, "model_loaded", False)
    gc.collect()
    check("model-release-after-clear")


__all__ = [
    "A0XProductionAdapterError", "ProductionContext", "ProductionFactories",
    "build_production_executor",
]
