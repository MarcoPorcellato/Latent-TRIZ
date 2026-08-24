from __future__ import annotations

import argparse
import hashlib
import json
import sys
import webbrowser
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

from .docs import load_profile, audit_docs
from .dataset_audit import DatasetAuditError, run_dataset_audit, stable_json_dumps as dataset_stable_json_dumps
from .model_preflight import ModelPreflightError, run_model_preflight, stable_json_dumps as model_stable_json_dumps
from .blinding import BlindingError, build_evaluator_bundle, write_evaluator_bundle
from .pilot import PilotError, prepare_packets, score_annotations, stable_json_dumps, write_jsonl
from .lab00 import Lab00Error, build_lab00_report
from .lab_suite import LAB00_REPORT_PATH, LabSuiteError, build_lab_suite_report
from .annotation_workbench import AnnotationWorkbenchError, serve_annotation_workbench
from .candidate_batch import CandidateBatchError, audit_candidate_batch
from .annotation_audit import AnnotationAuditError, audit_annotations
from .a0_corpus import A0CorpusError, generate_a0_corpus
from .a0_calibration import A0CalibrationError, run_a0_calibration
from .a0r1_corpus import A0R1CorpusError, generate_a0r1_corpus
from .a0r1_preoutput import A0R1PreoutputError, run_a0r1_preoutput_audits
from .a0r1_verify import A0R1VerifyError, verify_a0r1_foundation
from .a0r1_freeze import A0R1FreezeError, run_a0r1_freeze
from .a0r1_execution import A0R1ExecutionError, verify_a0r1_execution_contract
from .a0x_runner import A0XRunnerError, verify_a0x_implementation
from .validator import ValidationIssue, validate


class CliError(RuntimeError):
    pass


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="latent-triz")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate JSON data against a schema")
    validate_parser.add_argument("--schema", required=True, help="Path to schema file")
    validate_parser.add_argument("data", nargs="+", help="JSON or JSONL document path(s)")

    docs_parser = subparsers.add_parser("docs-audit", help="Audit Markdown documentation against OKF profile")
    docs_parser.add_argument("--profile", required=True, help="Path to OKF TOML profile")
    docs_parser.add_argument("--root", default=".", help="Documentation root for link resolution")
    docs_parser.add_argument(
        "--as-of-date",
        required=True,
        help="Reference date for stale-date checks (YYYY-MM-DD)",
    )

    claims_parser = subparsers.add_parser("claims-audit", help="Audit claim evidence references")
    claims_parser.add_argument("--registry", required=True, help="Path to claim registry JSONL")
    claims_parser.add_argument("--root", default=".", help="Repository root for evidence references")

    pilot_prepare_parser = subparsers.add_parser("pilot-prepare", help="Prepare randomized, blinded pilot packets")
    pilot_prepare_parser.add_argument("--seed", type=int, required=True, help="Deterministic seed")
    pilot_prepare_parser.add_argument("--arms", nargs="+", required=True, help="Arm labels")
    pilot_prepare_parser.add_argument("--cases", nargs="+", required=True, help="Case JSON/JSONL file(s)")
    pilot_prepare_parser.add_argument("--output", default="-", help="Output JSONL path, '-' for stdout")
    pilot_prepare_parser.add_argument("--format", choices=["json", "jsonl"], default="jsonl")

    pilot_score_parser = subparsers.add_parser("pilot-score", help="Aggregate blinded pilot annotations")
    pilot_score_parser.add_argument("--packets", required=True, help="Packet JSON/JSONL file")
    pilot_score_parser.add_argument("--responses", required=True, help="Response JSON/JSONL file")
    pilot_score_parser.add_argument("--annotations", required=True, help="Annotation JSON/JSONL file")
    pilot_score_parser.add_argument("--dimensions", nargs="+", default=list(), help="Optional custom dimensions")
    pilot_score_parser.add_argument(
        "--minimum-distinct-raters",
        type=int,
        default=1,
        help="Minimum distinct raters required per response (confirmatory runs should use 2 or more)",
    )
    pilot_score_parser.add_argument("--output", default="-", help="Output JSON path, '-' for stdout")

    lab00_parser = subparsers.add_parser("lab00", help="Build deterministic Stage-1 non-evidence HTML report")
    lab00_parser.add_argument("--output", required=True, help="Output HTML path")
    lab00_parser.add_argument("--open", action="store_true", help="Open the report in a browser")

    lab_suite_parser = subparsers.add_parser(
        "lab-suite",
        help="Build the deterministic Lab 00-04 visual index",
    )
    lab_suite_parser.add_argument("--root", default=".", help="Repository root")
    lab_suite_parser.add_argument("--output", required=True, help="Output HTML path relative to the repository")
    lab_suite_parser.add_argument("--open", action="store_true", help="Open the dashboard in a browser")

    model_preflight_parser = subparsers.add_parser(
        "model-preflight",
        help="Check the offline EXP-001 model candidate manifest",
    )
    model_preflight_parser.add_argument("--manifest", required=True, help="Path to the model candidate manifest")
    model_preflight_parser.add_argument("--output", default="-", help="Output JSON path, '-' for stdout")

    dataset_audit_parser = subparsers.add_parser(
        "dataset-audit",
        help="Audit the EXP-001 dataset plan against cases",
    )
    dataset_audit_parser.add_argument("--plan", required=True, help="Path to the dataset plan")
    dataset_audit_parser.add_argument("--cases", required=True, help="Path to the JSONL case corpus")
    dataset_audit_parser.add_argument(
        "--mode",
        choices=["development", "freeze"],
        default="development",
        help="Development reports gaps; freeze enforces all targets",
    )
    dataset_audit_parser.add_argument("--output", default="-", help="Output JSON path, '-' for stdout")

    candidate_audit_parser = subparsers.add_parser(
        "candidate-audit",
        help="Fail closed on leakage, imbalance, provenance, or pairing defects in a candidate batch",
    )
    candidate_audit_parser.add_argument("--manifest", required=True, help="Candidate batch manifest JSON")
    candidate_audit_parser.add_argument("--cases", required=True, help="Candidate case JSONL")
    candidate_audit_parser.add_argument("--output", default="-", help="Output JSON path, '-' for stdout")

    annotation_audit_parser = subparsers.add_parser(
        "annotation-audit",
        help="Audit independent blinded annotation files for coverage, agreement, and abstentions",
    )
    annotation_audit_parser.add_argument("--cases", required=True, help="Candidate case JSONL")
    annotation_audit_parser.add_argument("--guide", required=True, help="Versioned annotation guide JSON")
    annotation_audit_parser.add_argument("--schema", required=True, help="Dataset annotation schema JSON")
    annotation_audit_parser.add_argument("--annotations", nargs="+", required=True, help="One JSONL file per rater")
    annotation_audit_parser.add_argument("--minimum-distinct-raters", type=int, default=2)
    annotation_audit_parser.add_argument("--agreement-threshold", type=float, default=0.8)
    annotation_audit_parser.add_argument("--maximum-abstention-rate", type=float, default=0.2)
    annotation_audit_parser.add_argument("--output", default="-", help="Output JSON path, '-' for stdout")

    evaluator_export_parser = subparsers.add_parser(
        "pilot-export-evaluator",
        help="Export evaluator-safe packets and a separate sealed allocation key",
    )
    evaluator_export_parser.add_argument("--packets", required=True, help="Administrative packet JSONL")
    evaluator_export_parser.add_argument("--responses", required=True, help="Blinded response JSONL")
    evaluator_export_parser.add_argument("--evaluator-output", required=True, help="Evaluator-safe JSONL output")
    evaluator_export_parser.add_argument("--key-output", required=True, help="Separate sealed allocation key output")

    annotation_parser = subparsers.add_parser(
        "annotation-workbench",
        help="Run the loopback-only blinded dataset annotation workbench",
    )
    annotation_parser.add_argument("--cases", required=True, help="Case JSONL path")
    annotation_parser.add_argument("--guide", required=True, help="Versioned annotation guide JSON path")
    annotation_parser.add_argument("--schema", required=True, help="Dataset annotation schema path")
    annotation_parser.add_argument("--output", required=True, help="Append-only annotation JSONL output")
    annotation_parser.add_argument("--rater-id", required=True, help="Pseudonymous rater identifier")
    annotation_parser.add_argument("--host", default="127.0.0.1", help="Loopback address only")
    annotation_parser.add_argument("--port", type=int, default=8765, help="Local TCP port")
    annotation_parser.add_argument("--open", action="store_true", help="Open the workbench in a browser")

    a0_corpus_parser = subparsers.add_parser(
        "a0-corpus",
        help="Generate pre-sealed A0 corpus artifacts from a protocol",
    )
    a0_corpus_parser.add_argument("--protocol", required=True, help="Path to the A0 protocol JSON file")
    a0_corpus_parser.add_argument("--output-dir", required=True, help="Output directory for generated A0 artifacts")

    a0_calibration_parser = subparsers.add_parser(
        "a0-calibrate",
        help="Run calibration-only A0 power and shortcut gates",
    )
    a0_calibration_parser.add_argument("--protocol", required=True)
    a0_calibration_parser.add_argument("--corpus-dir", required=True)
    a0_calibration_parser.add_argument("--output-dir", required=True)

    a0r1_corpus_parser = subparsers.add_parser(
        "a0r1-corpus",
        help="Generate the independent A0-R1 procedural corpus",
    )
    a0r1_corpus_parser.add_argument("--protocol", required=True)
    a0r1_corpus_parser.add_argument("--output-dir", required=True)

    a0r1_preoutput_parser = subparsers.add_parser(
        "a0r1-preoutput",
        help="Run A0-R1 independence and calibration-only shortcut audits",
    )
    a0r1_preoutput_parser.add_argument("--protocol", required=True)
    a0r1_preoutput_parser.add_argument("--candidate-corpus-dir", required=True)
    a0r1_preoutput_parser.add_argument("--source-corpus-dir", required=True)
    a0r1_preoutput_parser.add_argument("--output-dir", required=True)

    a0r1_verify_parser = subparsers.add_parser(
        "a0r1-verify",
        help="Regenerate and verify the tracked A0-R1 pre-output foundation",
    )
    a0r1_verify_parser.add_argument("--root", default=".")

    a0x_verify_parser = subparsers.add_parser(
        "a0x-synthetic-verify",
        help="Verify the no-model A0X implementation surface",
    )
    a0x_verify_parser.add_argument("--root", default=".")

    a0r1_freeze_parser = subparsers.add_parser(
        "a0r1-freeze",
        help="Prepare the A0-R1 power receipt and frozen protocol package",
    )
    a0r1_freeze_parser.add_argument("--protocol", required=True)
    a0r1_freeze_parser.add_argument("--candidate-corpus-dir", required=True)
    a0r1_freeze_parser.add_argument("--source-corpus-dir", required=True)
    a0r1_freeze_parser.add_argument("--preoutput-dir", required=True)
    a0r1_freeze_parser.add_argument("--output-dir", required=True)

    a0r1_execution_parser = subparsers.add_parser(
        "a0r1-execution-verify",
        help="Verify the frozen R1.4a implementation contract before model access",
    )
    a0r1_execution_parser.add_argument("--root", default=".")

    fingerprint_parser = subparsers.add_parser("fingerprint", help="Compute SHA-256 of a file")
    fingerprint_parser.add_argument("path", help="Path to file")

    args = parser.parse_args(argv)
    if args.command == "fingerprint":
        return _run_fingerprint(args.path)
    if args.command == "validate":
        return _run_validate(args.schema, args.data)
    if args.command == "docs-audit":
        return _run_docs_audit(args.profile, args.root, args.as_of_date)
    if args.command == "claims-audit":
        return _run_claims_audit(args.registry, args.root)
    if args.command == "pilot-prepare":
        return _run_pilot_prepare(args.cases, args.arms, args.seed, args.output, args.format)
    if args.command == "pilot-score":
        return _run_pilot_score(
            args.packets,
            args.responses,
            args.annotations,
            args.dimensions,
            args.minimum_distinct_raters,
            args.output,
        )
    if args.command == "lab00":
        return _run_lab00(args.output, args.open)
    if args.command == "lab-suite":
        return _run_lab_suite(args.root, args.output, args.open)
    if args.command == "model-preflight":
        return _run_model_preflight(args.manifest, args.output)
    if args.command == "dataset-audit":
        return _run_dataset_audit(args.plan, args.cases, args.mode, args.output)
    if args.command == "candidate-audit":
        return _run_candidate_audit(args.manifest, args.cases, args.output)
    if args.command == "annotation-audit":
        return _run_annotation_audit(
            args.cases, args.guide, args.schema, args.annotations,
            args.minimum_distinct_raters, args.agreement_threshold,
            args.maximum_abstention_rate, args.output,
        )
    if args.command == "pilot-export-evaluator":
        return _run_pilot_export_evaluator(
            args.packets,
            args.responses,
            args.evaluator_output,
            args.key_output,
        )
    if args.command == "annotation-workbench":
        try:
            serve_annotation_workbench(
                cases_path=args.cases,
                guide_path=args.guide,
                output_path=args.output,
                schema_path=args.schema,
                rater_id=args.rater_id,
                host=args.host,
                port=args.port,
                open_browser=args.open,
            )
        except (AnnotationWorkbenchError, OSError) as exc:
            _print_error(str(exc))
            return 1
        return 0
    if args.command == "a0-corpus":
        return _run_a0_corpus(args.protocol, args.output_dir)
    if args.command == "a0-calibrate":
        return _run_a0_calibration(args.protocol, args.corpus_dir, args.output_dir)
    if args.command == "a0r1-corpus":
        return _run_a0r1_corpus(args.protocol, args.output_dir)
    if args.command == "a0r1-preoutput":
        return _run_a0r1_preoutput(
            args.protocol,
            args.candidate_corpus_dir,
            args.source_corpus_dir,
            args.output_dir,
        )
    if args.command == "a0r1-verify":
        return _run_a0r1_verify(args.root)
    if args.command == "a0x-synthetic-verify":
        return _run_a0x_synthetic_verify(args.root)
    if args.command == "a0r1-freeze":
        return _run_a0r1_freeze(
            args.protocol,
            args.candidate_corpus_dir,
            args.source_corpus_dir,
            args.preoutput_dir,
            args.output_dir,
        )
    if args.command == "a0r1-execution-verify":
        return _run_a0r1_execution_verify(args.root)
    parser.error("Unknown command")
    return 1


def _run_fingerprint(path: str) -> int:
    file_path = Path(path)
    try:
        hash_obj = hashlib.sha256()
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(65536), b""):
                hash_obj.update(chunk)
        print(hash_obj.hexdigest())
        return 0
    except (OSError, IOError) as exc:
        _print_error(f"{path}: cannot read file: {exc}")
        return 1


def _load_schema(path: str) -> dict:
    schema_path = Path(path)
    try:
        with schema_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        _raise_cli_error(f"schema not found: {path}")
    except json.JSONDecodeError as exc:
        _raise_cli_error(f"invalid schema JSON in {path}: {exc}")
    except OSError as exc:
        _raise_cli_error(f"unable to read schema {path}: {exc}")


def _run_validate(schema_path: str, data_paths: Iterable[str]) -> int:
    try:
        schema = _load_schema(schema_path)
    except CliError as exc:
        _print_error(f"schema: {exc}")
        return 1

    had_errors = False

    for data_path in data_paths:
        path = Path(data_path)
        if path.suffix.lower() in {".jsonl", ".ndjson"}:
            if not _validate_jsonl(path, schema):
                had_errors = True
        else:
            if not _validate_json(path, schema):
                had_errors = True

    return 1 if had_errors else 0


def _validate_json(path: Path, schema: dict) -> bool:
    if not path.is_file():
        _print_error(f"{path.as_posix()}:0:0: data file not found")
        return False
    try:
        data = _read_json(path)
    except CliError as exc:
        _print_error(f"{path.as_posix()}:0:0: invalid JSON: {exc}")
        return False
    issues = validate(data, schema)
    if issues:
        for issue in issues:
            print(_fmt_issue(path.as_posix(), None, issue), file=sys.stderr)
        return False
    return True


def _validate_jsonl(path: Path, schema: dict) -> bool:
    ok = True
    try:
        file = path.open("r", encoding="utf-8")
    except OSError as exc:
        _print_error(f"{path.as_posix()}:0:0: cannot open JSONL file: {exc}")
        return False

    with file:
        for index, line in enumerate(file, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(
                    _fmt_parse_error(path.as_posix(), index, exc),
                    file=sys.stderr,
                )
                ok = False
                continue
            issues = validate(data, schema)
            if issues:
                ok = False
                for issue in issues:
                    print(_fmt_issue(path.as_posix(), index, issue), file=sys.stderr)
    return ok


def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        _raise_cli_error(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        _raise_cli_error(str(exc))
    except OSError as exc:
        _raise_cli_error(str(exc))


def _print_error(message: str) -> None:
    print(f"latent-triz: {message}", file=sys.stderr)


def _raise_cli_error(message: str) -> None:
    raise CliError(message)


def _fmt_issue(path: str, record: Optional[int], issue: ValidationIssue) -> str:
    if record is None:
        return f"{path}:0:{issue.path}: {issue.message}"
    return f"{path}:{record}:{issue.path}: {issue.message}"


def _fmt_parse_error(path: str, record: int, exc: Exception) -> str:
    return f"{path}:{record}:0: invalid JSON: {exc}"


def _run_docs_audit(profile_path: str, root: str, as_of_date: str) -> int:
    try:
        as_of = date.fromisoformat(as_of_date)
    except ValueError as exc:
        _print_error(f"invalid --as-of-date: {exc}")
        return 1

    try:
        profile = load_profile(profile_path)
    except ValueError as exc:
        _print_error(f"invalid profile {profile_path}: {exc}")
        return 1

    issues = audit_docs(profile, Path(root), as_of)
    if issues:
        for issue in issues:
            print(f"{issue.file}:{issue.line}:{issue.code}: {issue.message}", file=sys.stderr)
        return 1
    return 0


def _run_claims_audit(registry_path: str, root: str) -> int:
    registry = Path(registry_path)
    repo_root = Path(root).resolve()
    reference_fields = (
        "preregistrations",
        "dataset_snapshots",
        "experiments",
        "results",
        "replications",
    )
    profile_requirements = {
        "E0": (),
        "E1": ("behavioral_effect",),
        "E2": ("behavioral_effect", "lexical_controls", "cross_domain", "decodable"),
        "E3": (
            "behavioral_effect",
            "lexical_controls",
            "cross_domain",
            "decodable",
            "positive_causal_intervention",
            "dose_response",
            "capability_preserved",
        ),
        "E4": (
            "behavioral_effect",
            "lexical_controls",
            "cross_domain",
            "decodable",
            "positive_causal_intervention",
            "dose_response",
            "capability_preserved",
            "negative_causal_intervention",
        ),
        "E5": (
            "behavioral_effect",
            "lexical_controls",
            "cross_domain",
            "decodable",
            "positive_causal_intervention",
            "dose_response",
            "capability_preserved",
            "negative_causal_intervention",
            "independent_replication",
            "cross_model_replication",
        ),
        "E6": (
            "behavioral_effect",
            "lexical_controls",
            "cross_domain",
            "decodable",
            "positive_causal_intervention",
            "dose_response",
            "capability_preserved",
            "negative_causal_intervention",
            "independent_replication",
            "cross_model_replication",
            "controlled_training",
        ),
    }
    ok = True

    try:
        lines = registry.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        _print_error(f"{registry_path}: cannot read claim registry: {exc}")
        return 1

    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            claim = json.loads(raw)
        except json.JSONDecodeError as exc:
            _print_error(f"{registry_path}:{line_number}: invalid JSON: {exc}")
            ok = False
            continue

        claim_id = claim.get("claim_id", "unknown") if isinstance(claim, dict) else "unknown"
        if not isinstance(claim, dict):
            _print_error(f"{registry_path}:{line_number}: claim must be an object")
            ok = False
            continue

        for field in reference_fields:
            references = claim.get(field, [])
            if not isinstance(references, list):
                continue
            for reference in references:
                if not isinstance(reference, str):
                    continue
                target = (repo_root / reference).resolve()
                try:
                    target.relative_to(repo_root)
                except ValueError:
                    _print_error(
                        f"{registry_path}:{line_number}:{claim_id}:{field}: reference escapes repository: {reference}"
                    )
                    ok = False
                    continue
                if not target.is_file():
                    _print_error(
                        f"{registry_path}:{line_number}:{claim_id}:{field}: evidence file not found: {reference}"
                    )
                    ok = False

        evidence_level = claim.get("evidence_level")
        evidence_profile = claim.get("evidence_profile")

        if not isinstance(evidence_level, str):
            _print_error(f"{registry_path}:{line_number}:{claim_id}: evidence_level must be a string")
            ok = False
            continue

        required_axes = profile_requirements.get(evidence_level)
        if required_axes is None:
            _print_error(f"{registry_path}:{line_number}:{claim_id}: unsupported evidence_level: {evidence_level}")
            ok = False
            continue

        if not isinstance(evidence_profile, dict):
            _print_error(
                f"{registry_path}:{line_number}:{claim_id}: evidence_profile must be an object for evidence_level {evidence_level}"
            )
            ok = False
            continue

        missing_axis = [axis for axis in required_axes if evidence_profile.get(axis) is not True]
        if missing_axis:
            _print_error(
                f"{registry_path}:{line_number}:{claim_id}: evidence_profile incompatible with evidence_level {evidence_level}; "
                f"missing true axes: {', '.join(missing_axis)}"
            )
            ok = False

    return 0 if ok else 1


def _run_pilot_prepare(case_files: List[str], arms: List[str], seed: int, output: str, output_format: str) -> int:
    try:
        packets = prepare_packets(case_files, arms, seed)
    except PilotError as exc:
        _print_error(f"invalid pilot input: {exc}")
        return 1

    if output == "-":
        if output_format == "jsonl":
            for packet in packets:
                print(stable_json_dumps(packet))
        else:
            print(stable_json_dumps(packets))
        return 0

    if output_format == "jsonl":
        try:
            write_jsonl(output, packets)
            return 0
        except OSError as exc:
            _print_error(f"unable to write packets: {exc}")
            return 1
    try:
        Path(output).write_text(stable_json_dumps(packets) + "\n", encoding="utf-8")
    except OSError as exc:
        _print_error(f"unable to write packets: {exc}")
        return 1
    return 0


def _run_pilot_score(
    packets: str,
    responses: str,
    annotations: str,
    dimensions: List[str],
    minimum_distinct_raters: int,
    output: str,
) -> int:
    try:
        summary = score_annotations(
            packets,
            responses,
            annotations,
            dimensions or None,
            minimum_distinct_raters=minimum_distinct_raters,
        )
    except PilotError as exc:
        _print_error(f"invalid pilot scoring: {exc}")
        return 1

    if output == "-":
        print(stable_json_dumps(summary))
        return 0

    try:
        Path(output).write_text(stable_json_dumps(summary) + "\n", encoding="utf-8")
    except OSError as exc:
        _print_error(f"unable to write summary: {exc}")
        return 1
    return 0


def _run_lab00(output: str, open_report: bool) -> int:
    try:
        report_path = build_lab00_report(output_path=Path(output))
    except Lab00Error as exc:
        _print_error(f"lab00: {exc}")
        return 1
    resolved = Path(report_path).resolve()
    print(f"lab00: rendered {resolved}")
    if open_report:
        webbrowser.open(resolved.as_uri())
    return 0


def _run_lab_suite(root: str, output: str, open_report: bool) -> int:
    repo_root = Path(root).resolve()
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    try:
        build_lab00_report(output_path=repo_root / LAB00_REPORT_PATH)
        report_path = build_lab_suite_report(repo_root=repo_root, output_path=output_path)
    except (Lab00Error, LabSuiteError, OSError) as exc:
        _print_error(f"lab-suite: {exc}")
        return 1
    print(f"lab-suite: rendered {report_path}")
    if open_report:
        webbrowser.open(report_path.as_uri())
    return 0


def _run_model_preflight(manifest: str, output: str) -> int:
    try:
        report = run_model_preflight(manifest)
    except ModelPreflightError as exc:
        _print_error(str(exc))
        return 1
    write_result = _write_json_output(report, output, model_stable_json_dumps)
    if write_result != 0:
        return write_result
    return 0 if report.get("manifest_valid") is True else 1


def _run_dataset_audit(plan: str, cases: str, mode: str, output: str) -> int:
    try:
        report = run_dataset_audit(plan, cases, mode=mode)
    except DatasetAuditError as exc:
        _print_error(str(exc))
        return 1
    write_result = _write_json_output(report, output, dataset_stable_json_dumps)
    if write_result != 0:
        return write_result
    if report.get("structural_ok") is not True:
        return 1
    if mode == "freeze" and report.get("freeze_ready") is not True:
        return 1
    return 0


def _run_candidate_audit(manifest: str, cases: str, output: str) -> int:
    try:
        report = audit_candidate_batch(manifest, cases)
    except CandidateBatchError as exc:
        _print_error(str(exc))
        return 1
    write_result = _write_json_output(report, output, dataset_stable_json_dumps)
    if write_result != 0:
        return write_result
    return 0 if report["ready_for_blinded_review"] is True else 1


def _run_annotation_audit(
    cases: str,
    guide: str,
    schema: str,
    annotations: list[str],
    minimum_distinct_raters: int,
    agreement_threshold: float,
    maximum_abstention_rate: float,
    output: str,
) -> int:
    try:
        report = audit_annotations(
            cases_path=cases,
            guide_path=guide,
            annotation_schema_path=schema,
            annotation_paths=annotations,
            minimum_distinct_raters=minimum_distinct_raters,
            agreement_threshold=agreement_threshold,
            maximum_abstention_rate=maximum_abstention_rate,
        )
    except AnnotationAuditError as exc:
        _print_error(str(exc))
        return 1
    write_result = _write_json_output(report, output, dataset_stable_json_dumps)
    if write_result != 0:
        return write_result
    return 0 if report["ready_for_freeze"] is True else 1


def _run_pilot_export_evaluator(
    packets: str,
    responses: str,
    evaluator_output: str,
    key_output: str,
) -> int:
    try:
        evaluator_packets, allocation_key = build_evaluator_bundle(packets, responses)
        write_evaluator_bundle(evaluator_packets, allocation_key, evaluator_output, key_output)
    except (BlindingError, OSError) as exc:
        _print_error(str(exc))
        return 1
    print(f"evaluator packets: {evaluator_output}")
    print(f"sealed allocation key: {key_output}")
    return 0


def _run_a0_corpus(protocol: str, output_dir: str) -> int:
    try:
        manifest = generate_a0_corpus(protocol, output_dir)
    except (A0CorpusError, OSError) as exc:
        _print_error(f"a0-corpus: {exc}")
        return 1
    print(stable_json_dumps(manifest))
    return 0


def _run_a0_calibration(protocol: str, corpus_dir: str, output_dir: str) -> int:
    try:
        summary = run_a0_calibration(protocol, corpus_dir, output_dir)
    except (A0CalibrationError, OSError, ValueError) as exc:
        _print_error(f"a0-calibrate: {exc}")
        return 1
    print(stable_json_dumps(summary))
    return 0 if summary["status"] == "pass" else 1


def _run_a0r1_corpus(protocol: str, output_dir: str) -> int:
    try:
        manifest = generate_a0r1_corpus(protocol, output_dir)
    except (A0R1CorpusError, OSError) as exc:
        _print_error(f"a0r1-corpus: {exc}")
        return 1
    print(stable_json_dumps(manifest))
    return 0


def _run_a0r1_preoutput(
    protocol: str,
    candidate_corpus_dir: str,
    source_corpus_dir: str,
    output_dir: str,
) -> int:
    try:
        summary = run_a0r1_preoutput_audits(
            protocol,
            candidate_corpus_dir,
            source_corpus_dir,
            output_dir,
        )
    except (A0R1PreoutputError, OSError, ValueError) as exc:
        _print_error(f"a0r1-preoutput: {exc}")
        return 1
    print(stable_json_dumps(summary))
    return 0 if summary["status"] == "pass" else 1


def _run_a0r1_verify(root: str) -> int:
    try:
        summary = verify_a0r1_foundation(root)
    except (A0R1VerifyError, OSError, ValueError) as exc:
        _print_error(f"a0r1-verify: {exc}")
        return 1


def _run_a0x_synthetic_verify(root: str) -> int:
    try:
        print(json.dumps(verify_a0x_implementation(root), sort_keys=True))
        return 0
    except A0XRunnerError as exc:
        _print_error(str(exc))
        return 1
    print(stable_json_dumps(summary))
    return 0


def _run_a0r1_freeze(
    protocol: str,
    candidate_corpus_dir: str,
    source_corpus_dir: str,
    preoutput_dir: str,
    output_dir: str,
) -> int:
    try:
        summary = run_a0r1_freeze(
            protocol,
            candidate_corpus_dir,
            source_corpus_dir,
            preoutput_dir,
            output_dir,
        )
    except (A0R1FreezeError, OSError, ValueError) as exc:
        _print_error(f"a0r1-freeze: {exc}")
        return 1
    print(stable_json_dumps(summary))
    return 0 if summary["status"] == "frozen" else 1


def _run_a0r1_execution_verify(root: str) -> int:
    try:
        summary = verify_a0r1_execution_contract(root)
    except (A0R1ExecutionError, OSError, ValueError) as exc:
        _print_error(f"a0r1-execution-verify: {exc}")
        return 1
    print(stable_json_dumps(summary))
    return 0


def _write_json_output(payload: dict, output: str, dumper) -> int:
    rendered = dumper(payload)
    if output == "-":
        print(rendered, end="")
        return 0
    try:
        Path(output).write_text(rendered, encoding="utf-8")
    except OSError as exc:
        _print_error(f"cannot write {output}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
