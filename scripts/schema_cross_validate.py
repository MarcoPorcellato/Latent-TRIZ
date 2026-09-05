#!/usr/bin/env python3
"""Cross-check tracked schemas and instances with the reference validator."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_validator import validate as validate_a0x  # noqa: E402
from latent_triz.validator import validate as validate_minimal  # noqa: E402


VALIDATION_PAIRS = (
    ("schemas/case.schema.json", "tests/fixtures/case_valid.json"),
    ("schemas/study.schema.json", "experiments/000-template/manifest.json"),
    ("schemas/study.schema.json", "experiments/001-stage1-pilot/manifest.json"),
    ("schemas/run.schema.json", "experiments/000-template/run.json"),
    ("schemas/dataset-registry.schema.json", "data/registry.json"),
    ("schemas/claim.schema.json", "data/claims.jsonl"),
    ("schemas/dataset-plan.schema.json", "experiments/001-stage1-pilot/dataset-plan.json"),
    ("schemas/model-candidate.schema.json", "experiments/001-stage1-pilot/model-candidates.jsonl"),
    ("schemas/lab01-manifest.schema.json", "experiments/lab01-model-anatomy/manifest.json"),
    ("schemas/lab01-model-receipt.schema.json", "results/lab01/model-anatomy/model_receipt.json"),
    ("schemas/lab01-run.schema.json", "results/lab01/model-anatomy/run.json"),
    ("schemas/dataset-annotation.schema.json", "data/pilot/dataset-annotations.jsonl"),
    ("schemas/annotation-guide.schema.json", "experiments/001-stage1-pilot/annotation-guide.json"),
    ("schemas/candidate-batch.schema.json", "data/candidates/wave1-manifest.json"),
    ("schemas/case.schema.json", "data/candidates/wave1-model-generated.jsonl"),
    ("schemas/dataset-snapshot.schema.json", "results/lab02/dataset-anatomy/snapshot_manifest.json"),
    ("schemas/lab03-config.schema.json", "experiments/lab03-behavioral-baselines/config.json"),
    ("schemas/lab03-config.schema.json", "experiments/wave1-surface-audit/config.json"),
    ("schemas/lab03-result.schema.json", "results/lab03/behavioral-baselines/summary.json"),
    ("schemas/lab03-result.schema.json", "results/wave1/surface-audit/summary.json"),
    ("schemas/lab04-config.schema.json", "experiments/lab04-decodability/config.json"),
    ("schemas/lab04-result.schema.json", "results/lab04/decodability/summary.json"),
    ("schemas/representation-record.schema.json", "data/pilot/representations.jsonl"),
    ("schemas/lab05-config.schema.json", "experiments/lab05-candidate-directions/config.json"),
    ("schemas/lab05-result.schema.json", "results/lab05/candidate-directions/summary.json"),
    ("schemas/cv2-negative-control.schema.json", "experiments/cv2-negative-controls/protocol.json"),
    ("schemas/lab06-dossier.schema.json", "experiments/lab06-causal-intervention/dossier.json"),
    ("schemas/track-b-protocol.schema.json", "experiments/track-b-emergence/protocol.json"),
    ("schemas/track-b-freeze-manifest.schema.json", "experiments/track-b-emergence/freeze-manifest.json"),
    ("schemas/a0-protocol.schema.json", "experiments/a0-automated-weak-proxy/protocol.json"),
    ("schemas/a0r1-protocol.schema.json", "experiments/a0r1-independent-proxy/protocol.json"),
    ("schemas/a0r1-corpus-manifest.schema.json", "data/a0r1/manifest.json"),
    ("schemas/a0-case.schema.json", "data/a0r1/cases.jsonl"),
    ("schemas/a0-procedural-target.schema.json", "data/a0r1/targets/calibration.jsonl"),
    ("schemas/a0-procedural-target.schema.json", "data/a0r1/targets/sealed.jsonl"),
    ("schemas/a0r1-independence-audit.schema.json", "results/a0r1/preoutput/independence.json"),
    ("schemas/a0-shortcut-audit.schema.json", "results/a0r1/preoutput/shortcuts.json"),
    ("schemas/a0r1-preoutput-summary.schema.json", "results/a0r1/preoutput/summary.json"),
    ("schemas/a0r1-implementation.schema.json", "experiments/a0r1-independent-proxy/implementation.json"),
    ("schemas/a0r1-preoutput-manifest.schema.json", "results/a0r1/preoutput/preoutput-manifest.json"),
    ("schemas/a0r1-power.schema.json", "results/a0r1/freeze/power.json"),
    ("schemas/a0r1-freeze-manifest.schema.json", "results/a0r1/freeze/freeze-manifest.json"),
    ("schemas/a0r1-protocol.schema.json", "results/a0r1/freeze/protocol-planned.json"),
    ("schemas/a0r1-protocol.schema.json", "results/a0r1/freeze/protocol-frozen.json"),
    ("schemas/a0r1-activation-receipt.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/activation-receipt.json"),
    ("schemas/a0r1-statistical-result.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/statistical-result.json"),
    ("schemas/a0r1-recovery-receipt.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/recovery-receipt.json"),
    ("schemas/a0r1-publication-manifest.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json"),
    ("schemas/a0r2-acquisition-contract.schema.json", "experiments/a0r2-independent-model/acquisition-contract.json"),
    ("schemas/a0r2-acquisition-receipt.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/integrity-receipt.json"),
    ("schemas/a0r2-feasibility-contract.schema.json", "experiments/a0r2-independent-model/feasibility-contract.json"),
    ("schemas/a0r2-study-protocol.schema.json", "experiments/a0r2-independent-model/study-protocol.json"),
    ("schemas/a0r2-sealed-execution-approval-dossier.schema.json", "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json"),
    ("schemas/a0r2-sealed-execution-authorization.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json"),
    ("schemas/a0r2-implementation.schema.json", "experiments/a0r2-independent-model/implementation.json"),
    ("schemas/a0r2-feasibility-receipt.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/feasibility-receipt.json"),
    ("schemas/a0r2-feasibility-guard-observation.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/guard-observation.json"),
    ("schemas/a0r2c1-correction-contract.schema.json", "experiments/a0r2c1-tokenizer-correction/contract.json"),
    ("schemas/a0r2c1-tokenizer-compatibility.schema.json", "results/a0r2c1/preexecution/tokenizer-compatibility.json"),
    ("schemas/a0r2c1-sealed-execution-authorization.schema.json", "results/a0r2c1/preexecution/sealed-execution-authorization.json"),
    ("schemas/a0r2c2-correction-contract.schema.json", "experiments/a0r2c2-shape-correction/contract.json"),
    ("schemas/a0r2c3-analysis-contract.schema.json", "experiments/a0r2c3-analysis-only-recovery/contract.json"),
    ("schemas/a0-corpus-manifest.schema.json", "data/a0/manifest.json"),
    ("schemas/a0-case.schema.json", "data/a0/cases.jsonl"),
    ("schemas/a0-procedural-target.schema.json", "data/a0/procedural-targets/calibration-targets.jsonl"),
    ("schemas/a0-procedural-target.schema.json", "data/a0/sealed-targets/targets.jsonl"),
    ("schemas/a0-power-calibration.schema.json", "results/a0/calibration/power.json"),
    ("schemas/a0-shortcut-audit.schema.json", "results/a0/calibration/shortcuts.json"),
    ("schemas/a0-calibration-summary.schema.json", "results/a0/calibration/summary.json"),
    ("schemas/a0-freeze-manifest.schema.json", "results/a0/calibration/freeze-manifest.json"),
    ("schemas/a0-activation-receipt.schema.json", "results/a0/a0-v1.0.3-e93a9faa/activation-receipt.json"),
    ("schemas/a0-statistical-result.schema.json", "results/a0/a0-v1.0.3-e93a9faa/statistical-result.json"),
    ("schemas/a0-publication-manifest.schema.json", "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json"),
    ("schemas/triz-reference-registry.schema.json", "data/triz-reference-sources.json"),
    ("schemas/triz-principle-reference.schema.json", "data/triz-reference/principles.jsonl"),
    ("schemas/exp001-r3-protocol.schema.json", "experiments/exp001-reference-integrated/protocol.json"),
    ("schemas/exp001-r3-implementation.schema.json", "experiments/exp001-reference-integrated/implementation.json"),
    ("schemas/exp001-r3-execution-authorization.schema.json", "experiments/exp001-reference-integrated/execution-authorization.json"),
    ("schemas/exp001-r3-freeze-manifest.schema.json", "results/exp001-r3/freeze-manifest.json"),
    ("schemas/exp001-r3-matrix-cell.schema.json", "experiments/exp001-reference-integrated/fixtures/matrix-cells.jsonl"),
    ("schemas/exp001-r3-tool-edge.schema.json", "experiments/exp001-reference-integrated/fixtures/tool-edges.jsonl"),
    ("schemas/exp001-r3-item.schema.json", "experiments/exp001-reference-integrated/fixtures/items.jsonl"),
    ("schemas/exp001-r3-source-exposure.schema.json", "experiments/exp001-reference-integrated/fixtures/source-exposures.jsonl"),
    ("schemas/exp001-r3-control-plan.schema.json", "experiments/exp001-reference-integrated/fixtures/control-plan.json"),
    ("schemas/exp001-r3-option-set.schema.json", "experiments/exp001-reference-integrated/fixtures/option-sets.jsonl"),
    ("schemas/exp001-r3-split-receipt.schema.json", "experiments/exp001-reference-integrated/fixtures/split-receipt.json"),
    ("schemas/exp001-r3-analysis-plan.schema.json", "experiments/exp001-reference-integrated/analysis-plan.json"),
    ("schemas/exp001-r3-primary-unit.schema.json", "experiments/exp001-reference-integrated/fixtures/primary-units.jsonl"),
    ("schemas/exp001-comparative-model-registry.schema.json", "experiments/exp001-comparative-reference/model-registry.json"),
    ("schemas/exp001-additional-model-selection.schema.json", "experiments/exp001-comparative-reference/additional-model-selection.json"),
    ("schemas/exp001-next-model-selection.schema.json", "experiments/exp001-comparative-reference/next-model-selection.json"),
    ("schemas/exp001-next-model-authorization.schema.json", "experiments/exp001-comparative-reference/next-model-authorization.json"),
    ("schemas/exp001-additional-model-authorization.schema.json", "experiments/exp001-comparative-reference/additional-model-authorization.json"),
    ("schemas/exp001-comparative-protocol.schema.json", "experiments/exp001-comparative-reference/protocol.json"),
    ("schemas/exp001-comparative-analysis-plan.schema.json", "experiments/exp001-comparative-reference/analysis-plan.json"),
    ("schemas/exp001-comparative-qwen-acquisition.schema.json", "experiments/exp001-comparative-reference/qwen-acquisition-dossier.json"),
    ("schemas/exp001-comparative-qwen-download-authorization.schema.json", "experiments/exp001-comparative-reference/qwen-download-authorization.json"),
    ("schemas/exp001-comparative-qwen-integrity-receipt.schema.json", "results/exp001-comparative/preexecution/qwen-integrity-receipt.json"),
    ("schemas/exp001-comparative-execution-authorization.schema.json", "experiments/exp001-comparative-reference/execution-authorization.json"),
    ("schemas/exp001-comparative-source-audit.schema.json", "results/exp001-comparative/preexecution/source-audit.json"),
    ("schemas/exp001-comparative-execution-receipt.schema.json", "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/execution-receipt.json"),
    ("schemas/exp001-comparative-statistical-result.schema.json", "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/statistical-result.json"),
    ("schemas/exp001-comparative-response-index.schema.json", "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/response-index.json"),
    ("schemas/exp001-comparative-sealed-key-access.schema.json", "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/sealed-key-access.json"),
    ("schemas/exp001-comparative-recovery-observation.schema.json", "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/recovery-observation.json"),
    ("schemas/exp001-comparative-publication-manifest.schema.json", "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/publication-manifest.json"),
    ("schemas/exp001-comparative-execution-receipt.schema.json", "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/execution-receipt.json"),
    ("schemas/exp001-comparative-statistical-result.schema.json", "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/statistical-result.json"),
    ("schemas/exp001-comparative-response-index.schema.json", "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/response-index.json"),
    ("schemas/exp001-comparative-sealed-key-access.schema.json", "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/sealed-key-access.json"),
    ("schemas/exp001-comparative-recovery-observation.schema.json", "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/recovery-observation.json"),
    ("schemas/exp001-comparative-publication-manifest.schema.json", "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/publication-manifest.json"),
    ("schemas/exp001-comparative-execution-receipt.schema.json", "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/execution-receipt.json"),
    ("schemas/exp001-comparative-statistical-result.schema.json", "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/statistical-result.json"),
    ("schemas/exp001-comparative-response-index.schema.json", "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/response-index.json"),
    ("schemas/exp001-comparative-sealed-key-access.schema.json", "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/sealed-key-access.json"),
    ("schemas/exp001-comparative-recovery-observation.schema.json", "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/recovery-observation.json"),
    ("schemas/exp001-comparative-publication-manifest.schema.json", "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/publication-manifest.json"),
    ("schemas/triz-web-corpus.schema.json", "data/triz-consulting-web-corpus.json"),
    ("schemas/exp002-followup-protocol.schema.json", "experiments/exp002-qwen3-followup/protocol.json"),
    ("schemas/exp002-question-bank-manifest.schema.json", "experiments/exp002-qwen3-followup/question-bank-manifest.json"),
    ("schemas/exp002-tokenizer-audit-plan.schema.json", "experiments/exp002-qwen3-followup/tokenizer-audit-plan.json"),
    ("schemas/exp002-tokenizer-audit-receipt.schema.json", "results/exp002/preexecution/tokenizer-audit.json"),
    ("schemas/exp002-label-surface-diagnostic.schema.json", "results/exp002/preexecution/label-surface-diagnostic.json"),
    ("schemas/exp002-response-surface-plan.schema.json", "experiments/exp002-qwen3-followup/response-surface-plan.json"),
    ("schemas/exp002-transfer-corpus-plan.schema.json", "experiments/exp002-qwen3-followup/transfer-corpus-plan.json"),
    ("schemas/exp002-approval-dossier.schema.json", "experiments/exp002-qwen3-followup/approval-dossier.json"),
    ("schemas/exp002-publication-manifest.schema.json", "results/exp002/preexecution/publication-manifest.json"),
    ("schemas/exp002-analysis-contract.schema.json", "experiments/exp002-qwen3-followup/analysis-contract.json"),
    ("schemas/exp002-source-familiarity-plan.schema.json", "experiments/exp002-qwen3-followup/source-familiarity-plan.json"),
    ("schemas/exp002-source-proximity-manifest.schema.json", "experiments/exp002-qwen3-followup/source-proximity-manifest.json"),
    ("schemas/exp002-transfer-corpus.schema.json", "experiments/exp002-qwen3-followup/transfer-corpus-template.json"),
    ("schemas/exp002-transfer-target-key.schema.json", "experiments/exp002-qwen3-followup/transfer-target-key-template.json"),
    ("schemas/exp002-study-approval-dossier.schema.json", "experiments/exp002-qwen3-followup/exp002b-approval-dossier.json"),
    ("schemas/exp002-study-approval-dossier.schema.json", "experiments/exp002-qwen3-followup/exp002c-approval-dossier.json"),
    ("schemas/exp002-interpretation-matrix.schema.json", "results/exp002/preexecution/interpretation-matrix.json"),
    ("schemas/exp002-expert-review-collection.schema.json", "experiments/exp002-qwen3-followup/expert-review-collection.json"),
    ("schemas/exp002-source-familiarity-fixture.schema.json", "experiments/exp002-qwen3-followup/source-familiarity-fixture.json"),
    ("schemas/exp002-power-calibration.schema.json", "results/exp002/preexecution/power-calibration.json"),
    ("schemas/exp002-direct-answer-key.schema.json", "results/exp002/preexecution/direct-answer-key-template.json"),
    ("schemas/exp002-execution-receipt.schema.json", "results/exp002/preexecution/execution-receipt-template.json"),
    ("schemas/exp002-statistical-result.schema.json", "results/exp002/preexecution/statistical-result-template.json"),
    ("schemas/exp002-response-index.schema.json", "results/exp002/preexecution/response-index-template.json"),
    ("schemas/exp002-sealed-key-access.schema.json", "results/exp002/preexecution/sealed-key-access-template.json"),
    ("schemas/exp002-recovery-observation.schema.json", "results/exp002/preexecution/recovery-observation-template.json"),
    ("schemas/exp002-followup-result.schema.json", "results/exp002/preexecution/synthetic-terminal-results.jsonl"),
    ("schemas/exp002-auto-protocol.schema.json", "experiments/exp002-auto/protocol.json"),
    ("schemas/exp002-auto-public-record.schema.json", "experiments/exp002-auto/factual-public.jsonl"),
    ("schemas/exp002-auto-public-record.schema.json", "experiments/exp002-auto/formulation-public.jsonl"),
    ("schemas/exp002-auto-public-record.schema.json", "experiments/exp002-auto/procedural-public.jsonl"),
    ("schemas/exp002-auto-combined-target-key.schema.json", "experiments/exp002-auto/combined-target-key-template.json"),
    ("schemas/exp002-auto-schedule.schema.json", "experiments/exp002-auto/schedule.json"),
    ("schemas/exp002-auto-approval-dossier.schema.json", "experiments/exp002-auto/approval-dossier.json"),
    ("schemas/exp002-auto-execution-receipt.schema.json", "results/exp002-auto/preexecution/execution-receipt-template.json"),
    ("schemas/exp002-auto-publication-manifest.schema.json", "results/exp002-auto/preexecution/publication-manifest.json"),
)


def _lab04_mutations(instance: Any) -> Iterable[tuple[str, Any]]:
    short_hash = deepcopy(instance)
    short_hash["hashes"]["cases_jsonl"] = "a" * 63
    yield "sha256_63_characters", short_hash

    missing_predecessor_hash = deepcopy(instance)
    missing_predecessor_hash["predecessors"]["lab01"].pop("summary_sha256")
    yield "predecessor_missing_summary_sha256", missing_predecessor_hash

    zero_alpha = deepcopy(instance)
    zero_alpha["random_control"]["max_statistic"]["configured_alpha"] = 0
    yield "exclusive_minimum_zero", zero_alpha

    mismatched_solver = deepcopy(instance)
    mismatched_solver["config"].update(
        numeric_backend="numpy",
        numeric_solver="pure_python_normal_equations_reference",
        numeric_library_version="2.4.3",
    )
    yield "numpy_backend_python_solver", mismatched_solver


def _cv2_lab06_mutations(cv2: Any, lab06: Any) -> Iterable[tuple[str, Any]]:
    missing_cv2_control = deepcopy(cv2)
    missing_cv2_control["control_families"] = missing_cv2_control["control_families"][:-1]
    yield "cv2_missing_control_family", ("schemas/cv2-negative-control.schema.json", missing_cv2_control)

    authorized_lab06 = deepcopy(lab06)
    authorized_lab06["approval_boundary"]["run_authorized"] = True
    yield "lab06_premature_authorization", ("schemas/lab06-dossier.schema.json", authorized_lab06)


def _track_b_mutations(protocol: Any, manifest: Any) -> Iterable[tuple[str, Any]]:
    target_access = deepcopy(protocol)
    target_access["scope_boundary"]["target_access_permitted"] = True
    yield "track_b_target_access_permitted", ("schemas/track-b-protocol.schema.json", target_access)

    ccp_access = deepcopy(protocol)
    ccp_access["scope_boundary"]["ccp_permitted"] = True
    yield "track_b_ccp_permitted", ("schemas/track-b-protocol.schema.json", ccp_access)

    missing_control = deepcopy(protocol)
    missing_control["control_families"] = missing_control["control_families"][:-1]
    yield "track_b_missing_required_control", ("schemas/track-b-protocol.schema.json", missing_control)

    model_loaded = deepcopy(manifest)
    model_loaded["access_receipt"]["model_loaded"] = True
    yield "track_b_model_loaded", ("schemas/track-b-freeze-manifest.schema.json", model_loaded)


def _additional_model_mutations(selection: Any) -> Iterable[tuple[str, Any]]:
    extra_candidate = deepcopy(selection)
    extra_candidate["candidates"].append(deepcopy(extra_candidate["candidates"][0]))
    yield "additional_model_extra_candidate", ("schemas/exp001-additional-model-selection.schema.json", extra_candidate)

    prior_result_selection = deepcopy(selection)
    prior_result_selection["selection_observed_prior_result"] = True
    yield "additional_model_observed_prior_result", ("schemas/exp001-additional-model-selection.schema.json", prior_result_selection)

    downloaded_candidate = deepcopy(selection)
    downloaded_candidate["candidates"][0]["acquisition_status"] = "integrity_verified"
    yield "additional_model_premature_download", ("schemas/exp001-additional-model-selection.schema.json", downloaded_candidate)


def _additional_authorization_mutations(authorization: Any) -> Iterable[tuple[str, Any]]:
    missing_approval = deepcopy(authorization)
    missing_approval["operator_approval"]["granted"] = False
    yield "additional_authorization_missing_approval", ("schemas/exp001-additional-model-authorization.schema.json", missing_approval)

    unknown_model = deepcopy(authorization)
    unknown_model["candidates"][0]["model_id"] = "unknown/model"
    yield "additional_authorization_unknown_model", ("schemas/exp001-additional-model-authorization.schema.json", unknown_model)

    network_enabled = deepcopy(authorization)
    network_enabled["execution"]["network"] = True
    yield "additional_authorization_network_enabled", ("schemas/exp001-additional-model-authorization.schema.json", network_enabled)


def _next_model_authorization_mutations(authorization: Any) -> Iterable[tuple[str, Any]]:
    revoked = deepcopy(authorization)
    revoked["candidates"][0]["permissions"]["download"] = False
    yield "next_authorization_permission_revoked", ("schemas/exp001-next-model-authorization.schema.json", revoked)

    unknown = deepcopy(authorization)
    unknown["candidates"][0]["model_id"] = "unknown/model"
    yield "next_authorization_unknown_model", ("schemas/exp001-next-model-authorization.schema.json", unknown)

    approval = deepcopy(authorization)
    approval["operator_approval"]["operator_id"] = "other"
    yield "next_authorization_operator_mismatch", ("schemas/exp001-next-model-authorization.schema.json", approval)


def _instances(path: Path) -> Iterable[tuple[int, Any]]:
    if path.suffix == ".jsonl":
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                yield line_number, json.loads(line)
        return
    yield 1, json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    for schema_path in sorted((ROOT / "schemas").glob("*.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:
            errors.append(f"{schema_path.relative_to(ROOT)}: invalid Draft 2020-12 schema: {exc}")

    for schema_name, instance_name in VALIDATION_PAIRS:
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        for line_number, instance in _instances(ROOT / instance_name):
            minimal_errors = validate_minimal(instance, schema)
            reference_errors = list(reference.iter_errors(instance))
            if minimal_errors or reference_errors:
                errors.append(
                    f"{instance_name}:{line_number}: minimal={len(minimal_errors)} "
                    f"reference={len(reference_errors)}"
                )

    lab04_schema = json.loads((ROOT / "schemas/lab04-result.schema.json").read_text(encoding="utf-8"))
    lab04_result = json.loads((ROOT / "results/lab04/decodability/summary.json").read_text(encoding="utf-8"))
    lab04_reference = Draft202012Validator(lab04_schema)
    for mutation_name, mutation in _lab04_mutations(lab04_result):
        minimal_rejects = bool(validate_minimal(mutation, lab04_schema))
        reference_rejects = bool(list(lab04_reference.iter_errors(mutation)))
        if not minimal_rejects or not reference_rejects:
            errors.append(
                f"mutation {mutation_name}: minimal_rejects={minimal_rejects} "
                f"reference_rejects={reference_rejects}"
            )

    cv2_instance = json.loads((ROOT / "experiments/cv2-negative-controls/protocol.json").read_text(encoding="utf-8"))
    lab06_instance = json.loads((ROOT / "experiments/lab06-causal-intervention/dossier.json").read_text(encoding="utf-8"))
    for mutation_name, (schema_name, mutation) in _cv2_lab06_mutations(cv2_instance, lab06_instance):
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        minimal_rejects = bool(validate_minimal(mutation, schema))
        reference_rejects = bool(list(reference.iter_errors(mutation)))
        if not minimal_rejects or not reference_rejects:
            errors.append(
                f"mutation {mutation_name}: minimal_rejects={minimal_rejects} "
                f"reference_rejects={reference_rejects}"
            )

    track_b_protocol = json.loads((ROOT / "experiments/track-b-emergence/protocol.json").read_text(encoding="utf-8"))
    track_b_manifest = json.loads((ROOT / "experiments/track-b-emergence/freeze-manifest.json").read_text(encoding="utf-8"))
    for mutation_name, (schema_name, mutation) in _track_b_mutations(track_b_protocol, track_b_manifest):
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        minimal_rejects = bool(validate_minimal(mutation, schema))
        reference_rejects = bool(list(reference.iter_errors(mutation)))
        if not minimal_rejects or not reference_rejects:
            errors.append(
                f"mutation {mutation_name}: minimal_rejects={minimal_rejects} "
                f"reference_rejects={reference_rejects}"
            )

    additional_selection = json.loads((ROOT / "experiments/exp001-comparative-reference/additional-model-selection.json").read_text(encoding="utf-8"))
    for mutation_name, (schema_name, mutation) in _additional_model_mutations(additional_selection):
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        minimal_rejects = bool(validate_minimal(mutation, schema))
        reference_rejects = bool(list(reference.iter_errors(mutation)))
        if not minimal_rejects or not reference_rejects:
            errors.append(
                f"mutation {mutation_name}: minimal_rejects={minimal_rejects} "
                f"reference_rejects={reference_rejects}"
            )

    additional_authorization = json.loads((ROOT / "experiments/exp001-comparative-reference/additional-model-authorization.json").read_text(encoding="utf-8"))
    for mutation_name, (schema_name, mutation) in _additional_authorization_mutations(additional_authorization):
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        minimal_rejects = bool(validate_minimal(mutation, schema))
        reference_rejects = bool(list(reference.iter_errors(mutation)))
        if not minimal_rejects or not reference_rejects:
            errors.append(
                f"mutation {mutation_name}: minimal_rejects={minimal_rejects} "
                f"reference_rejects={reference_rejects}"
            )

    next_authorization = json.loads((ROOT / "experiments/exp001-comparative-reference/next-model-authorization.json").read_text(encoding="utf-8"))
    for mutation_name, (schema_name, mutation) in _next_model_authorization_mutations(next_authorization):
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        minimal_rejects = bool(validate_minimal(mutation, schema))
        reference_rejects = bool(list(reference.iter_errors(mutation)))
        if not minimal_rejects or not reference_rejects:
            errors.append(
                f"mutation {mutation_name}: minimal_rejects={minimal_rejects} "
                f"reference_rejects={reference_rejects}"
            )

    a0x_pairs = _a0x_positional_pairs()
    for schema_name, instance in a0x_pairs:
        schema = json.loads((ROOT / schema_name).read_text(encoding="utf-8"))
        reference = Draft202012Validator(schema)
        a0x_errors = validate_a0x(instance, schema)
        reference_errors = list(reference.iter_errors(instance))
        if a0x_errors or reference_errors:
            errors.append(
                f"A0X positional {schema_name}: a0x={len(a0x_errors)} reference={len(reference_errors)}"
            )
        for mutation_name, mutation in _a0x_positional_mutations(instance):
            rejected = mutation
            a0x_rejects = bool(validate_a0x(rejected, schema))
            reference_rejects = bool(list(reference.iter_errors(rejected)))
            if not a0x_rejects or not reference_rejects:
                errors.append(
                    f"A0X positional mutation {schema_name}:{mutation_name}: "
                    f"a0x_rejects={a0x_rejects} reference_rejects={reference_rejects}"
                )

    if errors:
        for error in errors:
            print(f"schema-cross-validate: {error}", file=sys.stderr)
        return 1
    print(
        f"schema-cross-validate: {len(VALIDATION_PAIRS)} legacy tracked pairs agree; "
        "19 legacy mutations rejected by both validators; "
        f"{len(a0x_pairs)} A0X positional pairs agree; "
        f"{len(a0x_pairs) * 4} A0X positional mutations rejected by both validators"
    )
    return 0


def _a0x_positional_pairs() -> tuple[tuple[str, dict[str, Any]], ...]:
    source = {"head": "a" * 40, "tree": "b" * 40, "ref": "refs/heads/main"}
    names = ("protocol.json", "implementation.json", "freeze.json", "approval-dossier.json", "slice-manifest.json")
    members = [{"name": name, "size": index + 1, "sha256": "c" * 64} for index, name in enumerate(names)]
    lanes = (
        "a0x-no-model", "a0x-synthetic", "documentation-audit", "repository-python311",
        "repository-python312", "schema-cross-validation-python311", "schema-cross-validation-python312",
    )
    return (
        ("schemas/a0x-hosted-gate-a-evidence.schema.json", {
            "artifact_class": "a0x-hosted-gate-a-evidence", "evidence_profile": "a0x-hosted-gate-a-evidence-v1",
            "repository": "MarcoPorcellato/Latent-TRIZ", "event": "push", "ref": "refs/heads/main",
            "qualified_source_head": "a" * 40, "qualified_source_tree": "b" * 40,
            "workflow": {"path": ".github/workflows/a0x-hosted-gate-a.yml", "raw_sha256": "c" * 64, "run_id": 1, "run_attempt": 1},
            "inputs": {"requirements_schema_lock_sha256": "c" * 64, "action_pin_manifest_sha256": "c" * 64, "lane_manifest_sha256": "c" * 64},
            "required_lanes": [{"id": lane, "receipt_sha256": "c" * 64, "status": "PASS"} for lane in lanes], "overall_status": "PASS",
        }),
        ("schemas/a0x-vertical-slice-manifest-v2.schema.json", {
            "artifact_class": "a0x-vertical-slice-manifest-v2", "generator_profile": "a0x-vertical-slice-v2",
            "repository": "MarcoPorcellato/Latent-TRIZ", "qualified_source": source, "pair_binding": {"one": "pair"}, "members": members[:-1],
        }),
        ("schemas/a0x-vertical-package-commitment-v2.schema.json", {
            "profile": "a0x-vertical-package-commitment-v2", "qualified_source": source, "pair_binding": {"one": "pair"}, "members": members,
            "generator": {"profile": "a0x-vertical-slice-v2", "repository": "MarcoPorcellato/Latent-TRIZ"}, "authorization_id": "p0-auth-test-01", "attempt_id": "p0-attempt-test-01", "package_commitment_sha256": "d" * 64,
        }),
    )


def _a0x_positional_mutations(instance: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    key = "required_lanes" if "required_lanes" in instance else "members"
    for name, mutate in (
        ("order", lambda rows: rows.reverse()),
        ("duplicate-identity", lambda rows: rows.__setitem__(1, deepcopy(rows[0]))),
        ("missing-final", lambda rows: rows.pop()),
        ("extra-item", lambda rows: rows.append(deepcopy(rows[-1]))),
    ):
        rejected = deepcopy(instance)
        mutate(rejected[key])
        yield name, rejected


if __name__ == "__main__":
    raise SystemExit(main())
