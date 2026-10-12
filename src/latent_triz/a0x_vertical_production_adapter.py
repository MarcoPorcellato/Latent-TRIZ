"""Bind one validated vertical-v4 evidence graph to an immutable context.

This module remains separate from the historical batch adapter. A pure graph
projection is not authority: production requires complete independent graph
and source revalidation. The real internal stages are shared with the isolated,
permanently evidence-ineligible engineering rehearsal.
"""
from __future__ import annotations

import re
import gc
import hashlib
import json
import os
import sys
import types
import resource
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .a0x_contract import A0XContractError, PairBinding


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_GRAPH_KEYS = frozenset({
    "descriptor", "readiness", "gate_a_evidence", "execution_inlet",
    "gate_c_authorization", "trust_file_identities",
})
_CONTEXTS = frozenset({"production", "synthetic-target-free", "engineering_rehearsal"})
_PRODUCTION_CAPABILITY = object()


class A0XVerticalProductionAdapterError(ValueError):
    """A validated vertical graph cannot be rebound without ambiguity."""


@dataclass(frozen=True)
class VerticalProductionContext:
    """Detached immutable projection of the exact validated v4 graph."""

    source_head: str
    source_tree: str
    pair_binding: Mapping[str, Any]
    vertical_package: Mapping[str, Any]
    qualification_context: str
    authorization_id: str
    attempt_id: str
    descriptor: Mapping[str, Any]
    readiness: Mapping[str, Any]
    gate_a_evidence: Mapping[str, Any]
    execution_inlet: Mapping[str, Any]
    gate_c_authorization: Mapping[str, Any]
    trust_file_identities: Mapping[str, Any]

    def public_identity(self) -> dict[str, Any]:
        """Return path-free package digests and identity fields for summaries."""
        return {
            "qualified_source": {
                "head": self.source_head,
                "tree": self.source_tree,
                "ref": "refs/heads/main",
            },
            "pair_binding": _thaw(self.pair_binding),
            "vertical_package_digests": {
                key: self.vertical_package[key]
                for key in ("commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256")
            },
            "qualification_context": self.qualification_context,
            "authorization_id": self.authorization_id,
            "attempt_id": self.attempt_id,
        }


def bind_validated_vertical_graph(
    graph: Mapping[str, Any], *, qualification_context: str,
) -> VerticalProductionContext:
    """Recheck cross-bindings and freeze a child-validated v4 graph.

    Filesystem/schema/hash verification must already have happened in the
    material child.  This pure second boundary checks the data crossing into
    adapter dispatch and refuses legacy shapes rather than translating them.
    It is not a trust-manifest authority by itself: a future production
    dispatcher must first establish exact expected trust membership and
    identities independently. Production obtains that proof separately before
    calling the real material stages.
    """
    if not isinstance(graph, Mapping) or set(graph) != _GRAPH_KEYS:
        raise A0XVerticalProductionAdapterError("vertical graph shape is unsupported")
    descriptor = _object(graph, "descriptor")
    readiness = _object(graph, "readiness")
    evidence = _object(graph, "gate_a_evidence")
    inlet = _object(graph, "execution_inlet")
    authorization = _object(graph, "gate_c_authorization")
    trust = _object(graph, "trust_file_identities")

    source = _object(descriptor, "qualified_source")
    if (
        set(source) != {"head", "tree", "ref"}
        or not _REVISION.fullmatch(_string(source, "head"))
        or not _REVISION.fullmatch(_string(source, "tree"))
        or source.get("ref") != "refs/heads/main"
    ):
        raise A0XVerticalProductionAdapterError("vertical source binding is invalid")
    try:
        pair = PairBinding.from_mapping(_object(descriptor, "pair_binding"))
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XVerticalProductionAdapterError("vertical pair binding is invalid") from error
    pair_value = pair.as_mapping()
    package = _object(descriptor, "vertical_package")
    if (
        set(package) != {
            "envelope_path", "package_path", "commitment_path", "commitment_raw_sha256",
            "package_commitment_sha256", "dossier_path", "dossier_sha256",
        }
        or any(not _SHA256.fullmatch(_string(package, key)) for key in (
            "commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256",
        ))
    ):
        raise A0XVerticalProductionAdapterError("vertical package binding is invalid")
    context = qualification_context
    if context not in _CONTEXTS:
        raise A0XVerticalProductionAdapterError("vertical qualification context is unsupported")
    auth_id = _identifier(authorization, "authorization_id")
    attempt_id = _identifier(authorization, "attempt_id")

    if readiness.get("source_head") != source["head"] or readiness.get("pair_binding") != pair_value:
        raise A0XVerticalProductionAdapterError("vertical readiness binding differs")
    if (
        evidence.get("source_head") != source["head"]
        or evidence.get("source_tree") != source["tree"]
        or evidence.get("pair_binding") != pair_value
    ):
        raise A0XVerticalProductionAdapterError("vertical Hosted Gate A binding differs")

    if (
        descriptor.get("descriptor_profile") != "a0x-vertical-launch-descriptor-v2"
        or authorization.get("artifact_class") != "a0x-vertical-execution-authorization"
        or authorization.get("commitment_profile") != "a0x-execution-authorization-json-v4"
        or authorization.get("qualified_source") != source
        or authorization.get("pair_binding") != pair_value
        or authorization.get("vertical_package") != package
        or authorization.get("qualification_context") != context
        or inlet.get("authorization_id") != descriptor.get("authorization_id")
        or inlet.get("attempt_id") != descriptor.get("attempt_id")
        or authorization.get("max_guard_exec_count") != 1
        or authorization.get("stop_boundary") != "after_one_sealed_target_read"
        or inlet.get("qualified_source") != source
        or inlet.get("pair_binding") != pair_value
        or inlet.get("vertical_package") != package
        or inlet.get("artifact_class") != "a0x-vertical-gate-b-execution-inlet"
        or inlet.get("inlet_profile") != "a0x-vertical-gate-b-execution-inlet-v2"
    ):
        raise A0XVerticalProductionAdapterError("vertical v4 authorization cross-binding differs")

    _validate_trust_identities(trust)
    frozen = _freeze(graph)
    return VerticalProductionContext(
        source_head=source["head"],
        source_tree=source["tree"],
        pair_binding=frozen["descriptor"]["pair_binding"],
        vertical_package=frozen["descriptor"]["vertical_package"],
        qualification_context=context,
        authorization_id=auth_id,
        attempt_id=attempt_id,
        descriptor=frozen["descriptor"],
        readiness=frozen["readiness"],
        gate_a_evidence=frozen["gate_a_evidence"],
        execution_inlet=frozen["execution_inlet"],
        gate_c_authorization=frozen["gate_c_authorization"],
        trust_file_identities=frozen["trust_file_identities"],
    )


def _dispatch_synthetic_target_free(
    graph: Mapping[str, Any], executor: Callable[[VerticalProductionContext], Any],
) -> Any:
    """Private adapter test seam; never used by the public child entrypoint."""
    context = bind_validated_vertical_graph(graph, qualification_context="synthetic-target-free")
    if context.qualification_context != "synthetic-target-free" or not callable(executor):
        raise A0XVerticalProductionAdapterError("synthetic dispatch is not eligible")
    return executor(context)


@dataclass(frozen=True)
class _ValidatedProductionCapability:
    """A complete, freshly reloaded graph; a context projection is not this proof."""

    repository_root: Path
    descriptor_path: str
    context: VerticalProductionContext
    package_documents: Mapping[str, Any]
    _marker: object
    _terminal_outputs: bool = False


def load_vertical_production_capability(repository_root: Path, descriptor_path: str, *, _terminal_outputs: bool = False) -> _ValidatedProductionCapability:
    """Re-run the real child graph validator and the complete six-member P0 loader.

    This is used independently by child and parent. It creates no model and
    opens no calibration or sealed target. The planned environment is checked
    against the frozen descriptor; actual child environment is checked by the
    operational child before calling this loader.
    """
    from .a0x_vertical_terminal_package import _read_independent
    from .a0x_vertical_slice import VerticalPackageBinding, load_vertical_runtime_package, vertical_terminal_output_paths, vertical_public_pre_execution_paths, _checkout_state

    root = Path(repository_root).absolute()
    raw, _info = _read_independent(root, "scripts/a0x_vertical_material_child.py")
    module = types.ModuleType("_a0x_graph_admission")
    module.__file__ = str(root / "scripts/a0x_vertical_material_child.py")
    # Consume the admitted source bytes, not a second path-based import.
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    descriptor_raw, _info = _read_independent(root, descriptor_path)
    descriptor = json.loads(descriptor_raw)["payload"]
    pair = PairBinding.from_mapping(descriptor["pair_binding"])
    source = descriptor["qualified_source"]
    allowed = vertical_terminal_output_paths(pair, source["head"], source["tree"]) if _terminal_outputs else frozenset()
    allowed |= vertical_public_pre_execution_paths(pair, source["head"], source["tree"])
    graph = module._validate_graph(
        root, descriptor_path, source_state_probe=lambda: _checkout_state(root, allowed),
        environment=dict(item.split("=", 1) for item in module._ENVIRONMENT),
        cwd=root, child_script_path=root / "scripts/a0x_vertical_material_child.py",
        expected_context="production",
    )
    context = bind_validated_vertical_graph(graph, qualification_context="production")
    pair = PairBinding.from_mapping(_thaw(context.pair_binding))
    package = _thaw(context.vertical_package)
    binding = VerticalPackageBinding(
        **package, qualified_source_head=context.source_head, qualified_source_tree=context.source_tree,
        leg=pair.leg, model_key=pair.model_key, model_revision=pair.revision, pair_binding=pair,
    )
    loaded = load_vertical_runtime_package(root, binding, allow_terminal_outputs=_terminal_outputs, allow_public_pre_execution=True)
    return _ValidatedProductionCapability(root, descriptor_path, context, _freeze(loaded["documents"]), _PRODUCTION_CAPABILITY, _terminal_outputs)


def _require_production_capability(value: Any) -> _ValidatedProductionCapability:
    if not isinstance(value, _ValidatedProductionCapability) or value._marker is not _PRODUCTION_CAPABILITY:
        raise A0XVerticalProductionAdapterError("complete validated production capability is required")
    fresh = load_vertical_production_capability(value.repository_root, value.descriptor_path, _terminal_outputs=value._terminal_outputs)
    if (
        fresh.context != value.context
        or fresh.package_documents != value.package_documents
    ):
        raise A0XVerticalProductionAdapterError("validated production capability drifted")
    return value


@dataclass(frozen=True)
class _MaterialInputs:
    """Private adapter inputs: public selection, calibration and one-shot target."""

    repository_root: Path
    output_root: Path
    snapshot_root: Path
    card: Any
    freeze: Any
    cases: tuple[Mapping[str, Any], ...]
    selection: Any
    protocol_path: Path
    calibration_cases_path: Path
    calibration_targets_path: Path
    sealed_targets_path: Path
    sealed_targets_sha256: str
    authorization_chain: Mapping[str, Any]
    revalidate: Callable[[], None]
    protected_postflight: Callable[[], None]


def run_vertical_production(capability: Any) -> dict[str, Any]:
    """Dispatch the real A0 stages only after complete independent admission."""
    capability = _require_production_capability(capability)
    from .a0x_contract import Leg, build_leg_freeze_binding, canonical_commitment, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE, APPROVAL_DOSSIER_PROFILE
    from .a0x_execution import load_a0_public_selection
    from .a0x_runtime_readiness import validate_runtime_readiness_live
    from .a0x_preflight import load_model_card
    from .a0x_vertical_terminal_package import _read_independent

    context, root = capability.context, capability.repository_root
    pair = PairBinding.from_mapping(_thaw(context.pair_binding))
    if pair.leg is not Leg.A0 or pair.model_key != "smollm2_360m" or pair.revision != "f8027fd0eaeea54caa13c31d31b9fdc459c38b49":
        raise A0XVerticalProductionAdapterError("only the approved first A0 pair can dispatch")
    if sys.version_info[:2] != (3, 11):
        raise A0XVerticalProductionAdapterError("material child is not Python 3.11")
    package = context.vertical_package["package_path"]
    freeze = build_leg_freeze_binding(root / package / "protocol.json", root / package / "implementation.json", root / package / "freeze.json")
    if freeze.leg_freeze_sha256 != pair.leg_freeze_sha256:
        raise A0XVerticalProductionAdapterError("production pair freeze differs")
    selection = load_a0_public_selection(repository_root=root, leg_freeze=freeze)
    selection_raw, _info = _read_independent(root, "experiments/a0x-six-model/a0-selection-manifest.json")
    selected = json.loads(selection_raw)
    cases_raw, _info = _read_independent(root, selected["source_cases_path"])
    if hashlib.sha256(cases_raw).hexdigest() != selected["source_cases_sha256"]:
        raise A0XVerticalProductionAdapterError("public cases differ from the frozen selection")
    all_cases = [json.loads(line) for line in cases_raw.splitlines() if line.strip()]
    by_id = {row["case_id"]: row for row in all_cases}
    if len(by_id) != len(all_cases):
        raise A0XVerticalProductionAdapterError("public case IDs are duplicated")
    cases = tuple(by_id[identity] for identity in selection.expected_case_ids)
    protocol = capability.package_documents["protocol.json"]
    protocol_path = root / protocol["source_protocol_path"]
    protocol_raw, _info = _read_independent(root, protocol["source_protocol_path"])
    if hashlib.sha256(protocol_raw).hexdigest() != protocol["source_protocol_raw_sha256"]:
        raise A0XVerticalProductionAdapterError("frozen source protocol differs")
    tree_raw, _info = _read_independent(root, "experiments/a0x-six-model/protected-a0-tree.json")
    from .a0x_freeze import _tree_sha256
    declaration = json.loads(tree_raw)
    if _tree_sha256(declaration) != freeze.protected_tree_sha256:
        raise A0XVerticalProductionAdapterError("protected-tree declaration differs")
    targets = {entry["path"]: entry for entry in declaration["entries"] if entry.get("entry_kind") == "sealed_target"}
    calibration_path = "data/a0/procedural-targets/calibration-targets.jsonl"
    sealed_path = "data/a0/sealed-targets/targets.jsonl"
    if set(targets) != {sealed_path}:
        raise A0XVerticalProductionAdapterError("A0 protected target declarations differ")
    manifest_raw, _info = _read_independent(root, selected["source_corpus_manifest_path"])
    if hashlib.sha256(manifest_raw).hexdigest() != selected["source_corpus_manifest_sha256"]:
        raise A0XVerticalProductionAdapterError("public corpus manifest differs from selection")
    calibration_declaration = json.loads(manifest_raw)["files"]["calibration_targets_jsonl"]
    if calibration_declaration.get("path") != "procedural-targets/calibration-targets.jsonl":
        raise A0XVerticalProductionAdapterError("calibration declaration is not the fixed A0 role")
    # This read occurs only in the authorized material dispatcher, never in its
    # pure graph/capability constructor. The consumer checks the same binding.
    calibration_raw, _info = _read_independent(root, calibration_path)
    if hashlib.sha256(calibration_raw).hexdigest() != calibration_declaration["sha256"] or len(calibration_raw) != calibration_declaration["size"]:
        raise A0XVerticalProductionAdapterError("calibration targets differ from the frozen declaration")
    card = load_model_card(root / context.readiness["model_runtime"]["card_path"])
    output = root / ".a0x-runtime/gate-c/v2" / context.source_head / context.source_tree / "a0" / pair.model_key / pair.run_id / "material"
    if os.path.lexists(output):
        raise A0XVerticalProductionAdapterError("material attempt namespace is occupied")
    output.mkdir(parents=True, mode=0o700)
    # Captured hash-bound calibration bytes are consumed once from an owned
    # copy; the protected source is not reopened by the consumer.
    calibration_copy = output / "calibration-targets.jsonl"
    _write_material_file(calibration_copy, calibration_raw)
    chain = {
        "dossier_commitment": {"profile": APPROVAL_DOSSIER_PROFILE, "commitment_sha256": canonical_commitment(_thaw(capability.package_documents["approval-dossier.json"]), APPROVAL_DOSSIER_PROFILE).commitment_sha256},
        "authorization_commitment": {"profile": VERTICAL_EXECUTION_AUTHORIZATION_PROFILE, "commitment_sha256": canonical_commitment(_thaw(context.gate_c_authorization), VERTICAL_EXECUTION_AUTHORIZATION_PROFILE).commitment_sha256},
    }

    def revalidate() -> None:
        _require_production_capability(capability)
        validate_runtime_readiness_live(_thaw(context.readiness), repository_root=root, source_head=context.source_head,
            pair=pair, python_path=context.readiness["python"]["path"])
        if os.path.abspath(sys.executable) != context.readiness["python"]["path"]:
            raise A0XVerticalProductionAdapterError("running Python differs from Gate B")

    # Postflight proves target path ownership/metadata, not target contents;
    # permission restoration/reprotection is owned by the authorized operator.
    protected_identities = {path: (os.lstat(root / path).st_dev, os.lstat(root / path).st_ino, os.lstat(root / path).st_size) for path in (sealed_path, calibration_path)}
    def postflight() -> None:
        for path, identity in protected_identities.items():
            info = os.lstat(root / path)
            import stat
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (info.st_dev, info.st_ino, info.st_size) != identity:
                raise A0XVerticalProductionAdapterError("protected target identity drifted")
    inputs = _MaterialInputs(root, output, root / card.runtime_root, card, freeze, cases, selection,
        protocol_path, root / selected["source_cases_path"], calibration_copy, root / sealed_path,
        targets[sealed_path]["sha256"], chain, revalidate, postflight)
    return _run_a0_material_stages(context, inputs, production_capability=capability)


def _write_material_file(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _material_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _run_a0_material_stages(context: VerticalProductionContext, inputs: _MaterialInputs, *, production_capability: Any = None) -> dict[str, Any]:
    """Shared real calibration/loader/extraction/analysis/sealing/package path."""
    from .a0x_contract import Leg
    from .a0_calibration import run_production_shortcut_calibration
    from .a0_shortcuts import production_mechanics_recipe
    from .a0x_execution import OneShotTargetReader, TargetReadReceipt, seal_terminal_attempt, AttemptState
    from .a0x_material_runtime import MaterialLifecycleDependencies, run_material_lifecycle
    from .a0x_model_adapter import A0XHiddenStateAdapter
    from .a0x_a0_activations import extract_a0x_a0
    from .a0x_a0_analysis import analyze_a0x_a0
    from .a0x_production_adapter import _a0_activation_selection_manifest
    from .a0x_vertical_terminal_package import VerticalTerminalExpectation, build_vertical_terminal_package, verify_vertical_terminal_package, capture_material_evidence

    if context.qualification_context == "production":
        _require_production_capability(production_capability)
        if production_capability.context != context or production_capability.repository_root != inputs.repository_root:
            raise A0XVerticalProductionAdapterError("production material inputs differ from their capability")
    elif context.qualification_context == "engineering_rehearsal":
        parts = inputs.repository_root.parts
        if len(parts) < 4 or parts[-4:-2] != (".a0x-runtime", "rehearsal") or not parts[-2].isdigit() or parts[-1] != "synthetic-repository":
            raise A0XVerticalProductionAdapterError("engineering material requires the ignored rehearsal root")
    else:
        raise A0XVerticalProductionAdapterError("target-free context cannot authorize material execution")
    pair = PairBinding.from_mapping(_thaw(context.pair_binding))
    if pair.leg is not Leg.A0:
        raise A0XVerticalProductionAdapterError("shared first-result stages are A0 only")
    state: dict[str, Any] = {}
    output, chain = inputs.output_root, _thaw(inputs.authorization_chain)
    def write(name: str, value: Mapping[str, Any]) -> Path:
        path = output / name
        _write_material_file(path, _material_json(value) + b"\n")
        return path
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def preflight(_context, check):
        inputs.revalidate()
        check("calibration-before-real-consumer")
        state["calibration"] = run_production_shortcut_calibration(inputs.protocol_path, inputs.calibration_cases_path,
            inputs.calibration_targets_path, production_mechanics_recipe())
        write("calibration-result.json", state["calibration"])
        if state["calibration"]["status"] not in {"PASS", "NON_INTERPRETABLE"}:
            raise A0XVerticalProductionAdapterError("required calibration controls are failed or unevaluable")
        check("calibration-after-real-consumer")
    def load(_tokenizer, _identity, check):
        inputs.revalidate()  # Immediately before tokenizer and weights are loaded.
        check("real-model-before-load")
        import torch
        torch.set_num_threads(1)
        return A0XHiddenStateAdapter.load(model_root=inputs.snapshot_root, card=inputs.card)
    class DeadlineAdapter:
        def __init__(self, model, check):
            self.model, self.check = model, check
        def __getattr__(self, name):
            return getattr(self.model, name)
        def forward_hidden(self, text):
            self.check("forward-before")
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform != "darwin":
                rss *= 1024
            if rss > 8 * 1024**3:
                raise A0XVerticalProductionAdapterError("material RSS exceeds the fixed 8 GiB limit")
            result = self.model.forward_hidden(text)
            self.check("forward-after")
            return result
    def activate(model, check):
        result = extract_a0x_a0(adapter=DeadlineAdapter(model, check), cases=inputs.cases,
            selection=_a0_activation_selection_manifest(inputs.selection, freeze=inputs.freeze, pair=pair),
            pair_binding=pair.as_mapping(), authorization_chain=chain, output_dir=output / "activation", created_at="2026-10-12T00:00:00Z")
        state["activation"] = result
        return result
    def reader_factory(artifacts, _check):
        return OneShotTargetReader(path=inputs.sealed_targets_path, expected_sha256=inputs.sealed_targets_sha256,
            receipt_path=output / "target-read-receipt.json", pair_binding=pair.as_mapping(), selection=inputs.selection,
            activation_receipt_sha256=digest(artifacts.receipt_path), dense_sha256=digest(artifacts.dense_path),
            index_sha256=digest(artifacts.index_path), authorization_chain=chain)
    def read(reader, _check):
        rows, receipt = reader.read_jsonl_once()
        state["target_receipt"] = receipt
        return rows
    def target_evidence(_reader):
        receipt = state.get("target_receipt")
        path = output / "target-read-receipt.json"
        if receipt is None:
            receipt = TargetReadReceipt.from_mapping(json.loads(path.read_bytes()))
        raw_sha = digest(path)
        return {"receipt": "sha256:" + raw_sha, "raw_sha256": raw_sha, "status": {"read_failed": "open_failed"}.get(receipt.status, receipt.status), "content_reads": receipt.content_reads}
    def analyze(rows, _check):
        artifacts = state["activation"]
        calibration = state["calibration"]
        status = {"PASS": "pass"}.get(calibration["status"], "failed")
        result = analyze_a0x_a0(pair_binding=pair.as_mapping(), target_rows=rows,
            target_read_receipt_bytes=(output / "target-read-receipt.json").read_bytes(),
            activation_receipt_bytes=artifacts.receipt_path.read_bytes(), dense_asset_bytes=artifacts.dense_path.read_bytes(),
            index_bytes=artifacts.index_path.read_bytes(), shortcut_result={"status": status}, authorization_chain=chain)
        state["statistic"] = result
        write("statistical-result.json", result)
        return result
    def seal(result, attempt_state, _check):
        seal_terminal_attempt(state=attempt_state, status=result["status"],
            target_receipt_path=output / "target-read-receipt.json", statistical_result=result if result["status"] in {"positive", "null"} else None,
            pair_binding=pair.as_mapping(), authorization_chain=chain, terminal_path=output / "analysis-terminal-result.json")
        payload = {"statistical_result_sha256": digest(output / "statistical-result.json")} if result["status"] in {"positive", "null"} else {"diagnostic_code": "ANALYSIS_FAILED"}
        return {"artifact_class": "a0x-vertical-terminal-result", "terminal_profile": "a0x-vertical-terminal-result-v1",
            **context.public_identity(), "reached_frontier": "sealed", "scientific_outcome": result["status"],
            "evidence_eligible": False, "expert_validated": False, "claim_ids": [], "result_payload": payload}
    def failure(attempt_state, stage, error, _pair):
        write("material-failure.json", {"stage": stage, "error_type": type(error).__name__, "error": str(error)[:300], "sealed_from_state": attempt_state.value})
        return {"artifact_class": "a0x-vertical-terminal-result", "terminal_profile": "a0x-vertical-terminal-result-v1",
            **context.public_identity(), "reached_frontier": "validated_graph", "scientific_outcome": "failed",
            "evidence_eligible": False, "expert_validated": False, "claim_ids": [], "result_payload": {"diagnostic_code": "MODEL_INCOMPATIBLE" if stage == "model_construction" else "PREFLIGHT_FAILED"}}
    def package(terminal, _check):
        assets = None
        material_context = context
        artifacts = state.get("activation")
        if terminal["reached_frontier"] == "sealed" and artifacts is not None:
            base = inputs.repository_root / "results/a0x-external-assets" / context.source_head / context.source_tree / "a0" / pair.model_key / pair.run_id
            assets = {"dense": base / "dense-output.bin", "index": base / "representation-index.json"}
            for role, source in (("dense", artifacts.dense_path), ("index", artifacts.index_path)):
                _write_material_file(assets[role], source.read_bytes())
            material_context = capture_material_evidence(inputs.repository_root, context)
        expectation = (VerticalTerminalExpectation.from_production_capability(production_capability, material_context=material_context, external_assets=assets)
            if context.qualification_context == "production" else VerticalTerminalExpectation.from_context(material_context, repository_root=inputs.repository_root, external_assets=assets))
        destination = inputs.repository_root / pair.output_path
        reference = build_vertical_terminal_package(repository_root=inputs.repository_root, destination=destination, expected=expectation, terminal_result=terminal)
        state.update(expectation=expectation, reference=reference)
        return destination
    def verify(path, _check):
        reference = state["reference"]
        state["verified"] = verify_vertical_terminal_package(package_root=path, repository_root=inputs.repository_root,
            expected=state["expectation"], expected_manifest_sha256=reference.manifest_sha256, expected_root_receipt_sha256=reference.root_receipt_sha256)
    def release(model, _check):
        model.model, model.tokenizer = None, None
        gc.collect()
    def refuse_r1(_value, _check):
        raise A0XVerticalProductionAdapterError("R1 is outside the approved first-result route")
    dependencies = MaterialLifecycleDependencies(static_preflight=preflight,
        model_identity=lambda _check: inputs.card, tokenizer_factory=lambda _check: inputs.card, model_factory=load,
        activation_by_leg={Leg.A0: activate, Leg.R1: refuse_r1}, activation_sealer=lambda value, _check: value,
        target_reader_factory=reader_factory, target_read=read, target_read_evidence=target_evidence,
        analysis_by_leg={Leg.A0: analyze, Leg.R1: refuse_r1}, terminal_sealer=seal, package_builder=package, package_verifier=verify,
        protected_tree_postflight=lambda _path, _check: inputs.protected_postflight(), failure_sealer=failure, release_model=release)
    result = run_material_lifecycle(pair=pair, preflight_context=context.public_identity(), dependencies=dependencies)
    result["calibration_status"] = state.get("calibration", {}).get("status")
    result["package_verified"] = "verified" in state
    result["publication_eligible"] = False
    write("material-lifecycle-result.json", result)
    return result


def _validate_trust_identities(value: Mapping[str, Any]) -> None:
    if not value:
        raise A0XVerticalProductionAdapterError("vertical trust identity set is empty")
    for path, raw_identity in value.items():
        if not isinstance(path, str) or path != PurePosixPath(path).as_posix() or PurePosixPath(path).is_absolute() or any(part in {"", ".", ".."} for part in PurePosixPath(path).parts):
            raise A0XVerticalProductionAdapterError("vertical trust identity path is unsafe")
        if not isinstance(raw_identity, Mapping) or set(raw_identity) != {"device", "inode", "size", "sha256"}:
            raise A0XVerticalProductionAdapterError("vertical trust identity shape is invalid")
        if any(not isinstance(raw_identity[key], int) or isinstance(raw_identity[key], bool) or raw_identity[key] < 0 for key in ("device", "inode", "size")) or raw_identity["inode"] == 0:
            raise A0XVerticalProductionAdapterError("vertical trust inode identity is invalid")
        if not isinstance(raw_identity.get("sha256"), str) or not _SHA256.fullmatch(raw_identity["sha256"]):
            raise A0XVerticalProductionAdapterError("vertical trust digest is invalid")


def _object(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise A0XVerticalProductionAdapterError(f"{key} is not an object")
    return value


def _string(parent: Mapping[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str):
        raise A0XVerticalProductionAdapterError(f"{key} is not a string")
    return value


def _identifier(parent: Mapping[str, Any], key: str) -> str:
    value = _string(parent, key)
    if not _IDENTIFIER.fullmatch(value):
        raise A0XVerticalProductionAdapterError(f"{key} is invalid")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(member) for key, member in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(member) for member in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise A0XVerticalProductionAdapterError("vertical graph is not JSON-shaped")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(member) for key, member in value.items()}
    if isinstance(value, tuple):
        return [_thaw(member) for member in value]
    return value
