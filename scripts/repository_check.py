#!/usr/bin/env python3
"""Run the complete dependency-free repository gate without requiring Make."""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.cli import _run_validate


PYTHON = sys.executable
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))


def _ensure_writable_tempdir() -> str:
    """Select the container's writable shared-memory tmpdir when needed.

    CCP mounts the checkout read-only and some runtimes also expose no writable
    ``/tmp``.  The repository tests intentionally use ``tempfile`` for
    isolated fixtures, so fail-closed qualification must provide a writable
    temporary location without relaxing the checkout mount.  Normal hosts keep
    Python's default selection unchanged; the fallback is used only when the
    default lookup is unavailable.
    """

    candidates = ["/dev/shm"]
    try:
        candidates.append(tempfile.gettempdir())
    except FileNotFoundError:
        pass
    candidates.append("/tmp")

    for candidate in dict.fromkeys(candidates):
        if not os.path.isdir(candidate):
            continue
        try:
            descriptor, probe = tempfile.mkstemp(prefix="latent-triz-", dir=candidate)
            os.close(descriptor)
            os.unlink(probe)
        except OSError:
            continue
        tempfile.tempdir = candidate
        ENV["TMPDIR"] = candidate
        return candidate

    raise RuntimeError("no writable temporary directory available for repository checks")


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, env=ENV, check=True)


def validate(schema: str, data: str) -> None:
    if _run_validate(schema, (data,)) != 0:
        raise RuntimeError(f"schema validation failed: {schema} -> {data}")


def main() -> int:
    _ensure_writable_tempdir()
    run(PYTHON, "scripts/a0x_contract_check.py", "--phase", "synthetic")
    run(PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")

    validation_pairs = (
        ("schemas/case.schema.json", "tests/fixtures/case_valid.json"),
        ("schemas/study.schema.json", "experiments/000-template/manifest.json"),
        ("schemas/study.schema.json", "experiments/001-stage1-pilot/manifest.json"),
        ("schemas/run.schema.json", "experiments/000-template/run.json"),
        ("schemas/dataset-registry.schema.json", "data/registry.json"),
        ("schemas/claim.schema.json", "data/claims.jsonl"),
        ("schemas/case.schema.json", "tests/fixtures/case_valid.jsonl"),
        ("schemas/case.schema.json", "data/pilot/cases.jsonl"),
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
        ("schemas/representation-record.schema.json", "data/pilot/representations.jsonl"),
        ("schemas/lab05-config.schema.json", "experiments/lab05-candidate-directions/config.json"),
        ("schemas/lab05-result.schema.json", "results/lab05/candidate-directions/summary.json"),
        ("schemas/a0-protocol.schema.json", "experiments/a0-automated-weak-proxy/protocol.json"),
        ("schemas/a0r1-protocol.schema.json", "experiments/a0r1-independent-proxy/protocol.json"),
        ("schemas/a0r1-corpus-manifest.schema.json", "data/a0r1/manifest.json"),
        ("schemas/a0-case.schema.json", "data/a0r1/cases.jsonl"),
        ("schemas/a0-procedural-target.schema.json", "data/a0r1/targets/calibration.jsonl"),
        ("schemas/a0-procedural-target.schema.json", "data/a0r1/targets/sealed.jsonl"),
        ("schemas/a0r1-independence-audit.schema.json", "results/a0r1/preoutput/independence.json"),
        ("schemas/a0-shortcut-audit.schema.json", "results/a0r1/preoutput/shortcuts.json"),
        ("schemas/a0r1-preoutput-summary.schema.json", "results/a0r1/preoutput/summary.json"),
        ("schemas/a0r1-preoutput-manifest.schema.json", "results/a0r1/preoutput/preoutput-manifest.json"),
        ("schemas/a0r1-power.schema.json", "results/a0r1/freeze/power.json"),
        ("schemas/a0r1-freeze-manifest.schema.json", "results/a0r1/freeze/freeze-manifest.json"),
        ("schemas/a0r1-implementation.schema.json", "experiments/a0r1-independent-proxy/implementation.json"),
        ("schemas/a0r1-protocol.schema.json", "results/a0r1/freeze/protocol-planned.json"),
        ("schemas/a0r1-protocol.schema.json", "results/a0r1/freeze/protocol-frozen.json"),
        ("schemas/a0r1-activation-receipt.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/activation-receipt.json"),
        ("schemas/a0r1-statistical-result.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/statistical-result.json"),
        ("schemas/a0r1-recovery-receipt.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/recovery-receipt.json"),
        ("schemas/a0r1-publication-manifest.schema.json", "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json"),
        ("schemas/a0r2-acquisition-contract.schema.json", "experiments/a0r2-independent-model/acquisition-contract.json"),
        ("schemas/a0r2-acquisition-receipt.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/integrity-receipt.json"),
        ("schemas/a0r2-study-protocol.schema.json", "experiments/a0r2-independent-model/study-protocol.json"),
        ("schemas/a0r2-sealed-execution-approval-dossier.schema.json", "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json"),
        ("schemas/a0r2-sealed-execution-authorization.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json"),
        ("schemas/a0r2-implementation.schema.json", "experiments/a0r2-independent-model/implementation.json"),
        ("schemas/a0r2-feasibility-contract.schema.json", "experiments/a0r2-independent-model/feasibility-contract.json"),
        ("schemas/a0r2-feasibility-receipt.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/feasibility-receipt.json"),
        ("schemas/a0r2-feasibility-guard-observation.schema.json", "results/a0r2/preexecution/smollm2-360m-f8027fd0/guard-observation.json"),
        ("schemas/a0r2c1-correction-contract.schema.json", "experiments/a0r2c1-tokenizer-correction/contract.json"),
        ("schemas/a0r2c1-tokenizer-compatibility.schema.json", "results/a0r2c1/preexecution/tokenizer-compatibility.json"),
        ("schemas/a0r2c1-sealed-execution-authorization.schema.json", "results/a0r2c1/preexecution/sealed-execution-authorization.json"),
        ("schemas/a0r2c2-correction-contract.schema.json", "experiments/a0r2c2-shape-correction/contract.json"),
        ("schemas/a0r2c3-analysis-contract.schema.json", "experiments/a0r2c3-analysis-only-recovery/contract.json"),
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
        ("schemas/a0-corpus-manifest.schema.json", "data/a0/manifest.json"),
        ("schemas/a0-case.schema.json", "data/a0/cases.jsonl"),
        ("schemas/a0-procedural-target.schema.json", "data/a0/procedural-targets/calibration-targets.jsonl"),
        ("schemas/a0-procedural-target.schema.json", "data/a0/sealed-targets/targets.jsonl"),
        ("schemas/a0-power-calibration.schema.json", "results/a0/calibration/power.json"),
        ("schemas/a0-shortcut-audit.schema.json", "results/a0/calibration/shortcuts.json"),
        ("schemas/a0-calibration-summary.schema.json", "results/a0/calibration/summary.json"),
        ("schemas/a0-freeze-manifest.schema.json", "results/a0/calibration/freeze-manifest.json"),
    )
    for schema, data in validation_pairs:
        validate(schema, data)

    run(PYTHON, "-m", "latent_triz.cli", "claims-audit", "--registry", "data/claims.jsonl", "--root", ".")
    run(
        PYTHON,
        "-m",
        "latent_triz.cli",
        "docs-audit",
        "--profile",
        "docs/okf-profile.toml",
        "--root",
        ".",
        "--as-of-date",
        date.today().isoformat(),
    )

    json_files = (
        "schemas/case.schema.json",
        "schemas/study.schema.json",
        "schemas/run.schema.json",
        "schemas/dataset-registry.schema.json",
        "schemas/claim.schema.json",
        "schemas/pilot-packet.schema.json",
        "schemas/pilot-response.schema.json",
        "schemas/pilot-annotation.schema.json",
        "schemas/pilot-summary.schema.json",
        "schemas/dataset-plan.schema.json",
        "schemas/model-candidate.schema.json",
        "schemas/evaluator-packet.schema.json",
        "schemas/allocation-key.schema.json",
        "schemas/lab01-manifest.schema.json",
        "schemas/lab01-model-receipt.schema.json",
        "schemas/lab01-run.schema.json",
        "schemas/dataset-annotation.schema.json",
        "schemas/annotation-guide.schema.json",
        "schemas/candidate-batch.schema.json",
        "schemas/blinded-annotation-audit.schema.json",
        "schemas/dataset-snapshot.schema.json",
        "schemas/lab03-config.schema.json",
        "schemas/lab03-result.schema.json",
        "schemas/lab04-config.schema.json",
        "schemas/lab04-result.schema.json",
        "schemas/representation-record.schema.json",
        "schemas/lab05-config.schema.json",
        "schemas/lab05-result.schema.json",
        "schemas/a0-protocol.schema.json",
        "schemas/a0r1-protocol.schema.json",
        "schemas/a0r1-corpus-manifest.schema.json",
        "schemas/a0r1-independence-audit.schema.json",
        "schemas/a0r1-preoutput-summary.schema.json",
        "schemas/a0r1-preoutput-manifest.schema.json",
        "schemas/a0r1-power.schema.json",
        "schemas/a0r1-freeze-manifest.schema.json",
        "schemas/a0r1-implementation.schema.json",
        "schemas/a0r1-activation-receipt.schema.json",
        "schemas/a0r1-statistical-result.schema.json",
        "schemas/a0r1-run-failure.schema.json",
        "schemas/a0r1-recovery-receipt.schema.json",
        "schemas/a0r1-publication-manifest.schema.json",
        "schemas/a0r2-acquisition-contract.schema.json",
        "schemas/a0r2-acquisition-receipt.schema.json",
        "schemas/a0r2-feasibility-contract.schema.json",
        "schemas/a0r2-feasibility-receipt.schema.json",
        "schemas/a0r2-feasibility-guard-observation.schema.json",
        "schemas/a0r2-study-protocol.schema.json",
        "schemas/a0r2-sealed-execution-approval-dossier.schema.json",
        "schemas/a0r2-sealed-execution-authorization.schema.json",
        "schemas/a0r2-implementation.schema.json",
        "schemas/a0r2c1-correction-contract.schema.json",
        "schemas/a0r2c1-sealed-execution-authorization.schema.json",
        "schemas/a0r2c1-tokenizer-compatibility.schema.json",
        "schemas/a0r2c2-correction-contract.schema.json",
        "schemas/a0r2c2-sealed-execution-authorization.schema.json",
        "schemas/a0r2c3-analysis-contract.schema.json",
        "schemas/a0r2c3-analysis-authorization.schema.json",
        "schemas/triz-reference-registry.schema.json",
        "data/triz-reference-sources.json",
        "schemas/triz-principle-reference.schema.json",
        "schemas/triz-web-corpus.schema.json",
        "data/triz-consulting-web-corpus.json",
        "schemas/a0r2-activation-receipt.schema.json",
        "schemas/a0r2-statistical-result.schema.json",
        "schemas/a0r2-run-failure.schema.json",
        "schemas/a0r2-publication-manifest.schema.json",
        "schemas/a0-corpus-manifest.schema.json",
        "schemas/a0-case.schema.json",
        "schemas/a0-procedural-target.schema.json",
        "schemas/a0-power-calibration.schema.json",
        "schemas/a0-shortcut-audit.schema.json",
        "schemas/a0-calibration-summary.schema.json",
        "schemas/a0-freeze-manifest.schema.json",
        "experiments/lab03-behavioral-baselines/config.json",
        "experiments/lab04-decodability/config.json",
        "experiments/lab05-candidate-directions/config.json",
        "experiments/a0r1-independent-proxy/protocol.json",
        "data/a0r1/manifest.json",
        "results/a0r1/preoutput/independence.json",
        "results/a0r1/preoutput/shortcuts.json",
        "results/a0r1/preoutput/summary.json",
        "results/a0r1/preoutput/preoutput-manifest.json",
        "results/a0r1/freeze/power.json",
        "results/a0r1/freeze/freeze-manifest.json",
        "experiments/a0r1-independent-proxy/implementation.json",
        "results/a0r1/freeze/protocol-planned.json",
        "results/a0r1/freeze/protocol-frozen.json",
        "experiments/a0r2-independent-model/acquisition-contract.json",
        "results/a0r2/preexecution/smollm2-360m-f8027fd0/integrity-receipt.json",
        "experiments/a0r2-independent-model/study-protocol.json",
        "experiments/a0r2-independent-model/sealed-execution-approval-dossier.json",
        "results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json",
        "experiments/a0r2-independent-model/implementation.json",
        "experiments/a0r2c1-tokenizer-correction/contract.json",
        "results/a0r2c1/preexecution/tokenizer-compatibility.json",
        "results/a0r2c1/preexecution/sealed-execution-authorization.json",
        "experiments/a0r2c2-shape-correction/contract.json",
        "experiments/a0r2c3-analysis-only-recovery/contract.json",
    )
    for path in json_files:
        json.loads((ROOT / path).read_text(encoding="utf-8"))

    run(PYTHON, "-m", "latent_triz.cli", "a0r1-verify", "--root", ".")

    run(
        PYTHON, "-m", "latent_triz.cli", "candidate-audit",
        "--manifest", "data/candidates/wave1-manifest.json",
        "--cases", "data/candidates/wave1-model-generated.jsonl",
    )

    with tempfile.TemporaryDirectory() as directory:
        a0_output = Path(directory) / "data" / "a0"
        run(
            PYTHON,
            "-m",
            "latent_triz.cli",
            "a0-corpus",
            "--protocol",
            "experiments/a0-automated-weak-proxy/protocol.json",
            "--output-dir",
            str(a0_output),
        )
        manifest_path = a0_output / "manifest.json"
        cases_path = a0_output / "cases.jsonl"
        calibration_targets_path = a0_output / "procedural-targets/calibration-targets.jsonl"
        sealed_targets_path = a0_output / "sealed-targets/targets.jsonl"
        validate("schemas/a0-corpus-manifest.schema.json", str(manifest_path))
        validate("schemas/a0-case.schema.json", str(cases_path))
        validate("schemas/a0-procedural-target.schema.json", str(calibration_targets_path))
        validate("schemas/a0-procedural-target.schema.json", str(sealed_targets_path))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["empirical"] is not True:
            raise RuntimeError("A0 manifest must be empirical")
        if manifest["scientific_status"] != "exploratory":
            raise RuntimeError("A0 manifest scientific_status must be exploratory")
        if manifest["evidence_eligible"] is not False:
            raise RuntimeError("A0 manifest evidence_eligible must be false")
        if manifest["expert_validated"] is not False:
            raise RuntimeError("A0 manifest expert_validated must be false")
        if manifest["claim_ids"] != []:
            raise RuntimeError("A0 manifest claim_ids must be empty")
        if manifest["counts"]["families"] != 96:
            raise RuntimeError("A0 manifest family count changed")
        if manifest["counts"]["total_cases"] != 192:
            raise RuntimeError("A0 manifest total case count changed")
        if manifest["counts"]["total_targets"] != 192:
            raise RuntimeError("A0 manifest total target count changed")
        if manifest["family_integrity"]["paired_records_by_family"] is not True:
            raise RuntimeError("A0 family integrity paired_records_by_family must be true")
        if manifest["family_integrity"]["uniform_split_by_family"] is not True:
            raise RuntimeError("A0 family integrity uniform_split_by_family must be true")
        if manifest["counts"]["sealed_cases"] < 1 or manifest["counts"]["calibration_cases"] < 1:
            raise RuntimeError("A0 manifest missing required split cases")
        for key, suffix in {
            "cases_jsonl": "cases.jsonl",
            "calibration_targets_jsonl": "procedural-targets/calibration-targets.jsonl",
            "sealed_targets_jsonl": "sealed-targets/targets.jsonl",
        }.items():
            path = a0_output / manifest["files"][key]["path"]
            if not path.is_file():
                raise RuntimeError(f"A0 manifest references missing {path}")
            expected = manifest["files"][key]["sha256"]
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
            if observed != expected:
                raise RuntimeError(f"A0 manifest file hash mismatch for {suffix}")
            if path.stat().st_size != manifest["files"][key]["size"]:
                raise RuntimeError(f"A0 manifest file size mismatch for {suffix}")

        for relative in (
            "manifest.json",
            "cases.jsonl",
            "procedural-targets/calibration-targets.jsonl",
            "sealed-targets/targets.jsonl",
        ):
            if (a0_output / relative).read_bytes() != (ROOT / "data/a0" / relative).read_bytes():
                raise RuntimeError(f"tracked A0 corpus artifact is not deterministic: {relative}")

        calibration_output = Path(directory) / "results" / "a0" / "calibration"
        run(
            PYTHON,
            "-m",
            "latent_triz.cli",
            "a0-calibrate",
            "--protocol",
            "experiments/a0-automated-weak-proxy/protocol.json",
            "--corpus-dir",
            str(a0_output),
            "--output-dir",
            str(calibration_output),
        )
        for relative in ("power.json", "shortcuts.json", "summary.json", "freeze-manifest.json"):
            if (calibration_output / relative).read_bytes() != (ROOT / "results/a0/calibration" / relative).read_bytes():
                raise RuntimeError(f"tracked A0 calibration artifact is not deterministic: {relative}")

    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        packets = temporary / "packets.jsonl"
        summary = temporary / "summary.json"
        evaluator_packets = temporary / "evaluator-packets.jsonl"
        allocation_key = temporary / "sealed-allocation-key.json"
        run(
            PYTHON,
            "-m",
            "latent_triz.cli",
            "pilot-prepare",
            "--seed",
            "20260812",
            "--arms",
            "control",
            "treatment",
            "--cases",
            "data/pilot/cases.jsonl",
            "--output",
            str(packets),
            "--format",
            "jsonl",
        )
        if packets.read_bytes() != (ROOT / "data/pilot/packets.jsonl").read_bytes():
            raise RuntimeError("Stage 1 packets differ from the frozen expected artifact")

        run(
            PYTHON,
            "-m",
            "latent_triz.cli",
            "pilot-score",
            "--packets",
            "data/pilot/packets.jsonl",
            "--responses",
            "data/pilot/responses.jsonl",
            "--annotations",
            "data/pilot/annotations.jsonl",
            "--output",
            str(summary),
        )
        if summary.read_bytes() != (ROOT / "data/pilot/summary.json").read_bytes():
            raise RuntimeError("Stage 1 summary differs from the frozen expected artifact")

        run(
            PYTHON,
            "-m",
            "latent_triz.cli",
            "pilot-export-evaluator",
            "--packets",
            "data/pilot/packets.jsonl",
            "--responses",
            "data/pilot/responses.jsonl",
            "--evaluator-output",
            str(evaluator_packets),
            "--key-output",
            str(allocation_key),
        )
        evaluator_text = evaluator_packets.read_text(encoding="utf-8")
        for forbidden in ('"arms_by_blind"', '"control"', '"treatment"'):
            if forbidden in evaluator_text:
                raise RuntimeError(f"Evaluator export leaks allocation marker: {forbidden}")
        validate("schemas/evaluator-packet.schema.json", str(evaluator_packets))
        validate("schemas/allocation-key.schema.json", str(allocation_key))

    pilot_pairs = (
        ("schemas/pilot-packet.schema.json", "data/pilot/packets.jsonl"),
        ("schemas/pilot-response.schema.json", "data/pilot/responses.jsonl"),
        ("schemas/pilot-annotation.schema.json", "data/pilot/annotations.jsonl"),
        ("schemas/pilot-summary.schema.json", "data/pilot/summary.json"),
    )
    for schema, data in pilot_pairs:
        validate(schema, data)

    lab01_root = ROOT / "results/lab01/model-anatomy"
    parity = json.loads((lab01_root / "parity_report.json").read_text(encoding="utf-8"))
    if parity.get("status") != "pass":
        raise RuntimeError("Lab 01 parity report is not PASS")
    artifact_names = {
        "model_receipt": "model_receipt.json",
        "environment": "environment.json",
        "run": "run.json",
        "prompt": "prompt.json",
        "tokens": "tokens.json",
        "layer_summary": "layer_summary.jsonl",
        "topk_logits": "topk_logits.jsonl",
        "report_html": "report.html",
    }
    for key, filename in artifact_names.items():
        expected = parity.get("artifact_hashes", {}).get(key)
        actual = hashlib.sha256((lab01_root / filename).read_bytes()).hexdigest()
        if expected != actual:
            raise RuntimeError(f"Lab 01 artifact hash mismatch: {filename}")

    lab02_root = ROOT / "results/lab02/dataset-anatomy"
    lab02_summary = json.loads((lab02_root / "summary.json").read_text(encoding="utf-8"))
    if lab02_summary.get("evidence_eligible") is not False or lab02_summary.get("claim_ids") != []:
        raise RuntimeError("Lab 02 evidence boundary is invalid")
    if lab02_summary.get("status") != "fail":
        raise RuntimeError("Lab 02 smoke fixture must preserve the documented not-ready result")
    for key, filename in {
        "dataset_audit_report": "dataset_audit.json",
        "snapshot_verification_report": "snapshot_manifest.json",
    }.items():
        expected = lab02_summary.get("hashes", {}).get(key)
        actual = hashlib.sha256((lab02_root / filename).read_bytes()).hexdigest()
        if expected != actual:
            raise RuntimeError(f"Lab 02 artifact hash mismatch: {filename}")

    lab03_root = ROOT / "results/lab03/behavioral-baselines"
    lab03_summary = json.loads((lab03_root / "summary.json").read_text(encoding="utf-8"))
    if lab03_summary.get("evidence_eligible") is not False or lab03_summary.get("claim_ids") != []:
        raise RuntimeError("Lab 03 evidence boundary is invalid")
    if lab03_summary.get("empirical") is not False or lab03_summary.get("status") != "fail":
        raise RuntimeError("Lab 03 smoke fixture must remain non-empirical and not ready")
    if lab03_summary.get("interpretation") != "diagnostic_only_not_scientifically_interpretable":
        raise RuntimeError("Lab 03 smoke metrics are not clearly marked diagnostic-only")
    expected_gate_status = {
        "B1": "fail",
        "B2": "fail",
        "B3": "pass",
        "B4": "fail",
        "B5": "pass",
        "B6": "fail",
        "B7": "fail",
        "B8": "pass",
    }
    observed_gate_status = {row.get("gate"): row.get("status") for row in lab03_summary.get("gates", [])}
    if observed_gate_status != expected_gate_status:
        raise RuntimeError(f"Lab 03 gate state changed: {observed_gate_status}")
    for key, path in {
        "baseline_jsonl": lab03_root / "baseline_result.json",
        "report_html": lab03_root / "report.html",
        "cases_hash": ROOT / "data/pilot/cases.jsonl",
        "snapshot_hash": ROOT / "results/lab02/dataset-anatomy/snapshot_manifest.json",
        "config_hash": ROOT / "experiments/lab03-behavioral-baselines/config.json",
    }.items():
        expected = lab03_summary.get("hashes", {}).get(key)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected != actual:
            raise RuntimeError(f"Lab 03 artifact hash mismatch: {path.name}")

    lab04_root = ROOT / "results/lab04/decodability"
    lab04_summary_path = lab04_root / "summary.json"
    if lab04_summary_path.exists():
        run(
            PYTHON,
            "-m",
            "latent_triz.cli",
            "validate",
            "--schema",
            "schemas/lab04-result.schema.json",
            str(lab04_summary_path),
        )
        lab04_summary = json.loads(lab04_summary_path.read_text(encoding="utf-8"))
        if lab04_summary.get("empirical") is not False:
            raise RuntimeError("Lab 04 fixture is unexpectedly empirical")
        if lab04_summary.get("evidence_eligible") is not False:
            raise RuntimeError("Lab 04 evidence eligibility is incorrectly true")
        if lab04_summary.get("claim_ids") != []:
            raise RuntimeError("Lab 04 claim ids are not empty")
        if lab04_summary.get("interpretation") != "diagnostic_only_not_scientifically_interpretable":
            raise RuntimeError("Lab 04 interpretation is not diagnostic-only")
        if lab04_summary.get("status") != "fail":
            raise RuntimeError("Lab 04 smoke fixture must remain non-ready")

        for key, path in {
            "probe_result_json": lab04_root / "probe_result.json",
            "report_html": lab04_root / "report.html",
            "cases_jsonl": ROOT / "data/pilot/cases.jsonl",
            "representations_jsonl": ROOT / "data/pilot/representations.jsonl",
            "config_json": ROOT / "experiments/lab04-decodability/config.json",
        }.items():
            if not path.exists():
                continue
            expected = lab04_summary.get("hashes", {}).get(key)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected and expected != actual:
                raise RuntimeError(f"Lab 04 artifact hash mismatch: {path.name}")

    lab05_root = ROOT / "results/lab05/candidate-directions"
    lab05_summary_path = lab05_root / "summary.json"
    lab05_summary = json.loads(lab05_summary_path.read_text(encoding="utf-8"))
    if lab05_summary.get("status") != "fail":
        raise RuntimeError("Lab 05 current fixture must remain fail-closed")
    if lab05_summary.get("empirical") is not False or lab05_summary.get("evidence_eligible") is not False:
        raise RuntimeError("Lab 05 evidence classification boundary is invalid")
    if lab05_summary.get("claim_ids") != []:
        raise RuntimeError("Lab 05 claim ids are not empty")
    boundary = lab05_summary.get("publication_boundary", {})
    if any(boundary.get(field) is not False for field in (
        "dense_vectors_published", "interventions_executed", "steering_claim_allowed", "causal_claim_allowed"
    )):
        raise RuntimeError("Lab 05 publication boundary is invalid")
    expected_gates = {
        "D1": "fail", "D2": "pass", "D3": "fail", "D4": "fail",
        "D5": "fail", "D6": "fail", "D7": "fail", "D8": "pass",
    }
    observed_gates = {row.get("gate"): row.get("status") for row in lab05_summary.get("gates", [])}
    if observed_gates != expected_gates:
        raise RuntimeError(f"Lab 05 gate state changed: {observed_gates}")
    for key, path in {
        "cases_jsonl": ROOT / "data/pilot/cases.jsonl",
        "representations_jsonl": ROOT / "data/pilot/representations.jsonl",
        "config_json": ROOT / "experiments/lab05-candidate-directions/config.json",
        "predecessor_lab04_summary": ROOT / "results/lab04/decodability/summary.json",
        "direction_result_json": lab05_root / "direction_result.json",
        "report_html": lab05_root / "report.html",
    }.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if lab05_summary.get("hashes", {}).get(key) != actual:
            raise RuntimeError(f"Lab 05 artifact hash mismatch: {path.name}")
    canonical_lab05 = dict(lab05_summary)
    canonical_lab05["hashes"] = dict(lab05_summary["hashes"])
    declared_summary_hash = canonical_lab05["hashes"]["summary_json"]
    canonical_lab05["hashes"]["summary_json"] = ""
    canonical_text = json.dumps(canonical_lab05, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    if hashlib.sha256(canonical_text.encode("utf-8")).hexdigest() != declared_summary_hash:
        raise RuntimeError("Lab 05 canonical summary hash mismatch")

    with tempfile.TemporaryDirectory() as directory:
        suite_root = Path(directory) / "repository"
        suite_inputs = (
            "results/lab01/model-anatomy/parity_report.json",
            "results/lab01/model-anatomy/report.html",
            "results/lab02/dataset-anatomy/summary.json",
            "results/lab02/dataset-anatomy/report.html",
            "results/lab03/behavioral-baselines/summary.json",
            "results/lab03/behavioral-baselines/report.html",
            "results/lab04/decodability/summary.json",
            "results/lab04/decodability/report.html",
            "results/lab05/candidate-directions/summary.json",
            "results/lab05/candidate-directions/report.html",
        )
        for relative in suite_inputs:
            destination = suite_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        lab_suite_output = suite_root / "artifacts/lab/index.html"
        command = (
            PYTHON, "-m", "latent_triz.cli", "lab-suite",
            "--root", str(suite_root), "--output", "artifacts/lab/index.html",
        )
        run(*command)
        first_lab_suite = lab_suite_output.read_bytes()
        run(*command)
        if lab_suite_output.read_bytes() != first_lab_suite:
            raise RuntimeError("Lab Suite dashboard is not byte-stable")

    run(
        PYTHON,
        "-m",
        "latent_triz.cli",
        "model-preflight",
        "--manifest",
        "experiments/001-stage1-pilot/model-candidates.jsonl",
    )
    run(
        PYTHON,
        "-m",
        "latent_triz.cli",
        "dataset-audit",
        "--plan",
        "experiments/001-stage1-pilot/dataset-plan.json",
        "--cases",
        "data/pilot/cases.jsonl",
        "--mode",
        "development",
    )

    print("repository-check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
