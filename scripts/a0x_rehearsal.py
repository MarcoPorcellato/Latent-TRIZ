#!/usr/bin/env python3
"""Real A0 components with independent synthetic inputs and an ignored output root.
Real Gate A/P0/B approvals are replaced only by explicitly synthetic bindings.
Uses the real loader, activation, D1–D7 consumer, analysis, packager and verifier.
No production corpus, protected targets, generation or scientific eligibility.
Production Gate C readiness is reported separately, never inferred from success.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT))
MODEL_KEY = "smollm2_360m"
MODEL_ID = "HuggingFaceTB/SmolLM2-360M"
REVISION = "f8027fd0eaeea54caa13c31d31b9fdc459c38b49"
DOMAINS = ("agriculture", "energy", "manufacturing", "medicine", "software", "transport")
COMMON = {"empirical": True, "scientific_status": "exploratory", "evidence_eligible": False,
          "expert_validated": False, "claim_ids": []}


class RehearsalError(RuntimeError):
    """A synthetic engineering rehearsal cannot satisfy its bounded contract."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def validate_output_root(repository_root: Path, output_root: Path) -> Path:
    root = Path(repository_root).resolve(strict=True)
    output = Path(output_root)
    if not output.is_absolute() or ".." in output.parts:
        raise RehearsalError("output must be in the owned rehearsal namespace")
    try:
        relative = output.relative_to(root)
    except ValueError as error:
        raise RehearsalError("output must be in the owned rehearsal namespace") from error
    if len(relative.parts) != 3 or relative.parts[:2] != (".a0x-runtime", "rehearsal") or not relative.parts[2].isdigit():
        raise RehearsalError("output must be in the owned rehearsal namespace")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise RehearsalError("rehearsal namespace has a symlink")
    if os.path.lexists(output):
        raise RehearsalError("rehearsal attempt is occupied")
    return output


def synthetic_inputs() -> tuple[list[dict], list[dict]]:
    cases, targets = [], []
    for family in range(24):
        domain = DOMAINS[family // 4]
        for variant in range(2):
            identity = f"engineering-case-{family:02d}-{variant}"
            public = {
                "case_id": identity, "problem_family_id": f"engineering-family-{family:02d}",
                "domain": domain, "split": "engineering", "solution_variant_id": str(variant),
                "problem": f"An independent synthetic device {family} must deliver a stable flow.",
                "constraints": ["Keep the fixture bounded"], "initial_state": "A synthetic flow is uneven.",
                "desired_improvement": "Make delivery steady", "worsening_consequence": "Avoid added waste",
                "transformation": "Adjust the mechanism in a controlled way.",
                "solution": f"Use the independently assigned fixture configuration {variant}.",
                "resulting_state": "The fixture reaches a stable synthetic state.",
            }
            cases.append(public)
            targets.append({
                key: public[key] for key in ("case_id", "problem_family_id", "domain", "split")
            } | {"operator_proxy_family": ("inversion_like", "segmentation_like")[variant]})
    return cases, targets


def _calibration(output: Path) -> dict:
    # This already-independent fixture exercises the actual prospective consumer;
    # its mechanical contract is engineering input, not production adoption.
    from tests.test_a0_prospective_d1_d7_synthetic import fixture, mechanics, SELECTION
    from latent_triz.a0_calibration import run_a0_calibration

    cases, targets, protocol = fixture()
    corpus = output / "calibration/corpus"
    protocol_path = output / "calibration/protocol.json"
    protocol_raw = canonical(protocol)
    write_new(protocol_path, protocol_raw)
    files = {}
    for name, rows, role in (("cases.jsonl", cases, "cases_jsonl"),
                             ("calibration-targets.jsonl", targets, "calibration_targets_jsonl")):
        raw = b"".join(canonical(row) + b"\n" for row in rows)
        write_new(corpus / name, raw)
        files[role] = {"path": name, "sha256": sha(raw), "size": len(raw)}
    files["sealed_targets_jsonl"] = {"path": "absent-synthetic-sealed.jsonl", "sha256": "0" * 64, "size": 0}
    write_new(corpus / "manifest.json", canonical({
        **COMMON, "protocol_id": protocol["protocol_id"], "protocol_hash": sha(protocol_raw), "files": files,
    }))
    return run_a0_calibration(protocol_path, corpus, output / "calibration/result",
                              method_selection=SELECTION, mechanical_evidence=mechanics(cases))


def _memory_available_bytes() -> int:
    if sys.platform != "darwin":
        raise RehearsalError("real rehearsal currently requires the authorized macOS host")
    result = subprocess.run(["/usr/bin/memory_pressure", "-Q"], check=True, capture_output=True, text=True)
    import re
    total = re.search(r"The system has (\d+) \(", result.stdout)
    free = re.search(r"System-wide memory free percentage: (\d+)%", result.stdout)
    if total is None or free is None:
        raise RehearsalError("native memory availability is inconclusive")
    return int(total[1]) * int(free[1]) // 100


def _synthetic_context(root: Path, pair, source_head: str, source_tree: str,
                       package_hash: str, attempt: str, statistic_raw: bytes):
    from latent_triz.a0x_vertical_production_adapter import bind_validated_vertical_graph

    public_schema = "schemas/a0x-execution-authorization-v4.schema.json"
    path = root / public_schema
    info = path.stat()
    statistic_path = root / ".a0x-runtime/engineering/statistical-result.json"
    write_new(statistic_path, statistic_raw)
    statistic_info = statistic_path.stat()
    source = {"head": source_head, "tree": source_tree, "ref": "refs/heads/main"}
    package = {
        "envelope_path": ".a0x-runtime/synthetic/p0", "package_path": ".a0x-runtime/synthetic/p0/package",
        "commitment_path": ".a0x-runtime/synthetic/p0/commitment.json",
        "commitment_raw_sha256": package_hash, "package_commitment_sha256": package_hash,
        "dossier_path": ".a0x-runtime/synthetic/p0/package/dossier.json", "dossier_sha256": package_hash,
    }
    common = {"qualified_source": source, "pair_binding": pair.as_mapping(), "vertical_package": package,
              "authorization_id": f"engineering-auth-{attempt}", "attempt_id": f"engineering-{attempt}"}
    graph = {
        "descriptor": {**common, "descriptor_profile": "a0x-vertical-launch-descriptor-v2"},
        "readiness": {"source_head": source_head, "pair_binding": pair.as_mapping()},
        "gate_a_evidence": {"source_head": source_head, "source_tree": source_tree, "pair_binding": pair.as_mapping()},
        "execution_inlet": {**common, "artifact_class": "a0x-vertical-gate-b-execution-inlet",
                            "inlet_profile": "a0x-vertical-gate-b-execution-inlet-v2"},
        "gate_c_authorization": {**common, "artifact_class": "a0x-vertical-execution-authorization",
            "commitment_profile": "a0x-execution-authorization-json-v4", "qualification_context": "engineering_rehearsal",
            "max_guard_exec_count": 1, "stop_boundary": "after_one_sealed_target_read"},
        "trust_file_identities": {public_schema: {
            "device": info.st_dev, "inode": info.st_ino, "size": info.st_size, "sha256": sha(path.read_bytes()),
        }, statistic_path.relative_to(root).as_posix(): {
            "device": statistic_info.st_dev, "inode": statistic_info.st_ino,
            "size": len(statistic_raw), "sha256": sha(statistic_raw),
        }},
    }
    return bind_validated_vertical_graph(graph, qualification_context="engineering_rehearsal")


def run_rehearsal(*, repository_root: Path, snapshot_root: Path, output_root: Path) -> dict:
    output = validate_output_root(repository_root, output_root)
    from latent_triz.a0x_contract import (APPROVAL_DOSSIER_PROFILE, VERTICAL_EXECUTION_AUTHORIZATION_PROFILE,
        Leg, LegFreezeBinding, PairBinding, compute_dense_bound, derive_pair_output_path)
    from latent_triz.a0x_preflight import load_model_card, verify_snapshot_files, verify_card_sources
    from latent_triz.a0x_production_adapter import _a0_activation_selection_manifest
    from latent_triz.a0x_execution import (load_a0_public_selection, OneShotTargetReader,
                                           seal_terminal_attempt, AttemptState)
    from latent_triz.a0x_model_adapter import A0XHiddenStateAdapter
    from latent_triz.a0x_a0_activations import extract_a0x_a0
    from latent_triz.a0x_a0_analysis import analyze_a0x_a0
    from latent_triz.a0x_vertical_terminal_package import (VerticalTerminalExpectation,
        build_vertical_terminal_package, verify_vertical_terminal_package)

    root = Path(repository_root).resolve(strict=True)
    card = load_model_card(root / "experiments/a0x-six-model/model-cards/smollm2_360m.json")
    if card.model_id != MODEL_ID or card.revision != REVISION:
        raise RehearsalError("rehearsal model identity drifted")
    verify_card_sources(root, card)
    verify_snapshot_files(snapshot_root, card)
    available = _memory_available_bytes()
    if available < 4 * 1024**3:
        raise RehearsalError("less than 4 GiB native reported memory is available")
    output.mkdir(parents=True, mode=0o700)
    started = time.monotonic()
    calibration = _calibration(output)
    shortcut_status = {"PASS": "pass"}.get(calibration["status"])
    if shortcut_status is None:
        raise RehearsalError("independent synthetic calibration did not pass")
    synthetic_root = output / "synthetic-repository"
    cases, targets = synthetic_inputs()
    cases_raw = b"".join(canonical(row) + b"\n" for row in cases)
    manifest_raw = canonical({"artifact_class": "engineering-source", "evidence_eligible": False})
    write_new(synthetic_root / "fixture/cases.jsonl", cases_raw)
    write_new(synthetic_root / "fixture/manifest.json", manifest_raw)
    selection = {
        "artifact_class": "a0x-selection-manifest", **COMMON,
        "selection_corpus_sha256": sha(cases_raw),
        "selection_path": "experiments/a0x-six-model/a0-selection-manifest.json",
        "selected_case_count": 48, "source_cases_path": "fixture/cases.jsonl",
        "source_corpus_manifest_path": "fixture/manifest.json", "source_cases_sha256": sha(cases_raw),
        "source_corpus_manifest_sha256": sha(manifest_raw),
        "selection_rule": {"cases_per_family": 2, "families_per_domain": 4,
                           "family_order": "lexicographic", "domain_order": "frozen"},
        "cases": [{key: row[key] for key in ("case_id", "problem_family_id", "domain", "split")} |
                  {"case_content_sha256": sha(canonical(row))} for row in cases], "target_content_reads": 0,
    }
    selection_raw = canonical(selection)
    write_new(synthetic_root / "experiments/a0x-six-model/a0-selection-manifest.json", selection_raw)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
    fixture_sha = sha(canonical({"cases": cases, "targets": targets}))
    freeze = LegFreezeBinding(Leg.A0, "engineering-rehearsal", fixture_sha, fixture_sha,
                              fixture_sha, fixture_sha, sha(selection_raw), head)
    attempt = output.name
    run_id = f"engineering-rehearsal-{attempt}"
    pair = PairBinding(binding_profile="a0x-pair-scope-v2", leg=Leg.A0,
        leg_freeze_sha256=freeze.leg_freeze_sha256, model_key=MODEL_KEY, model_id=MODEL_ID,
        revision=REVISION, run_id=run_id, output_path=derive_pair_output_path(Leg.A0, MODEL_KEY, run_id),
        dense_bound=compute_dense_bound(Leg.A0, cases=48, hidden_width=card.hidden_size))
    chain = {
        "dossier_commitment": {"profile": APPROVAL_DOSSIER_PROFILE, "commitment_sha256": fixture_sha},
        "authorization_commitment": {"profile": VERTICAL_EXECUTION_AUTHORIZATION_PROFILE, "commitment_sha256": fixture_sha},
    }
    capability = load_a0_public_selection(repository_root=synthetic_root, leg_freeze=freeze)
    activation_selection = _a0_activation_selection_manifest(capability, freeze=freeze, pair=pair)
    available = _memory_available_bytes()
    if available < 4 * 1024**3:
        raise RehearsalError("memory gate failed immediately before model load")
    adapter = None
    try:
        import torch
        torch.set_num_threads(1)
        adapter = A0XHiddenStateAdapter.load(model_root=snapshot_root, card=card)
        artifacts = extract_a0x_a0(adapter=adapter, cases=cases, selection=activation_selection,
            pair_binding=pair.as_mapping(), authorization_chain=chain,
            output_dir=output / "activation", created_at="2026-10-12T00:00:00Z")
        target_path = output / "synthetic-targets.jsonl"
        target_raw = b"".join(canonical(row) + b"\n" for row in targets)
        write_new(target_path, target_raw)
        reader = OneShotTargetReader(path=target_path, expected_sha256=sha(target_raw),
            receipt_path=output / "target-read-receipt.json", pair_binding=pair.as_mapping(), selection=capability,
            activation_receipt_sha256=sha(artifacts.receipt_path.read_bytes()),
            dense_sha256=sha(artifacts.dense_path.read_bytes()), index_sha256=sha(artifacts.index_path.read_bytes()),
            authorization_chain=chain)
        rows, _receipt = reader.read_jsonl_once()
        result = analyze_a0x_a0(pair_binding=pair.as_mapping(), target_rows=rows,
            target_read_receipt_bytes=(output / "target-read-receipt.json").read_bytes(),
            activation_receipt_bytes=artifacts.receipt_path.read_bytes(), dense_asset_bytes=artifacts.dense_path.read_bytes(),
            index_bytes=artifacts.index_path.read_bytes(), shortcut_result={"status": shortcut_status},
            authorization_chain=chain)
        write_new(output / "statistical-result.json", canonical(result) + b"\n")
        seal_terminal_attempt(state=AttemptState.ANALYSIS, status=result["status"],
            target_receipt_path=output / "target-read-receipt.json", statistical_result=result,
            pair_binding=pair.as_mapping(), authorization_chain=chain,
            terminal_path=output / "analysis-terminal-result.json")
        schema_relative = "schemas/a0x-execution-authorization-v4.schema.json"
        write_new(synthetic_root / schema_relative, (root / schema_relative).read_bytes())
        context = _synthetic_context(synthetic_root, pair, head, tree, fixture_sha, attempt,
                                     (output / "statistical-result.json").read_bytes())
        asset_base = synthetic_root / "results/a0x-external-assets" / head / tree / "a0" / MODEL_KEY / run_id
        asset_base.mkdir(parents=True)
        assets = {"dense": asset_base / "dense-output.bin", "index": asset_base / "representation-index.json"}
        shutil.copyfile(artifacts.dense_path, assets["dense"])
        shutil.copyfile(artifacts.index_path, assets["index"])
        expectation = VerticalTerminalExpectation.from_context(context, repository_root=synthetic_root, external_assets=assets)
        terminal = {"artifact_class": "a0x-vertical-terminal-result", "terminal_profile": "a0x-vertical-terminal-result-v1",
            **context.public_identity(), "reached_frontier": "sealed", "scientific_outcome": result["status"],
            "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
            "result_payload": {"statistical_result_sha256": sha((output / "statistical-result.json").read_bytes())}}
        package = synthetic_root / pair.output_path
        reference = build_vertical_terminal_package(repository_root=synthetic_root, destination=package,
            expected=expectation, terminal_result=terminal)
        verified = verify_vertical_terminal_package(package_root=package, repository_root=synthetic_root,
            expected=expectation, expected_manifest_sha256=reference.manifest_sha256,
            expected_root_receipt_sha256=reference.root_receipt_sha256)
        if verified.publication_eligible:
            raise RehearsalError("engineering rehearsal cannot become publication eligible")
    finally:
        if adapter is not None:
            adapter.model = None
            adapter.tokenizer = None
        gc.collect()
    elapsed = time.monotonic() - started
    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        peak_rss *= 1024
    report = {
        "artifact_class": "engineering_rehearsal", "evidence_eligible": False, "publication_eligible": False,
        "production_gate_c_ready": False, "source_head": head, "source_tree": tree,
        "downstream_chain_profile": VERTICAL_EXECUTION_AUTHORIZATION_PROFILE,
        "source_worktree_dirty": subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src", "scripts", "tests", "schemas", "Makefile"], cwd=root).returncode != 0,
        "model_id": MODEL_ID, "revision": REVISION, "synthetic_cases": 48, "synthetic_families": 24,
        "calibration_status": calibration["status"], "analysis_status": result["status"],
        "package_verified": True, "wall_seconds": elapsed, "peak_rss_bytes": peak_rss,
        "budget_pass": elapsed <= 1650 and peak_rss <= 8 * 1024**3,
        "limitations": ["All inputs are synthetic; never scientific evidence.",
                        "Production v4 dispatcher and mechanical freeze remain unqualified."],
    }
    write_new(output / "rehearsal-result.json", canonical(report) + b"\n")
    if not report["budget_pass"]:
        raise RehearsalError("rehearsal exceeds its engineering resource envelope")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_rehearsal(repository_root=ROOT, snapshot_root=args.snapshot_root, output_root=args.output_root)
    except Exception as error:
        print(json.dumps({"artifact_class": "engineering_rehearsal", "status": "failed",
                          "evidence_eligible": False, "error_type": type(error).__name__, "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
