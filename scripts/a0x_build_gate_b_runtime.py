#!/usr/bin/env python3
"""Plan or build exact offline prerequisites for one later A0X Gate B."""
import sys
sys.dont_write_bytecode = True

import argparse
import json
from pathlib import Path
from typing import Sequence, TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_gate_b_builder import (  # noqa: E402
    A0XGateBBuilderError,
    GateBBuildRequest,
    build_gate_b_runtime,
    plan_gate_b_runtime,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="validate and print the no-write plan")
    mode.add_argument("--build", action="store_true", help="perform one separately authorized material build")
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--wheelhouse", required=True)
    parser.add_argument("--wheelhouse-manifest", required=True)
    parser.add_argument("--wheelhouse-manifest-sha256", required=True)
    parser.add_argument("--base-python", required=True)
    parser.add_argument("--base-python-sha256", required=True)
    parser.add_argument("--base-python-version", required=True)
    parser.add_argument("--bootstrap-pip-version", required=True)
    parser.add_argument("--base-runtime-root", required=True)
    parser.add_argument("--base-runtime-manifest", required=True)
    parser.add_argument("--base-runtime-manifest-sha256", required=True)
    parser.add_argument("--model-card", required=True)
    parser.add_argument("--model-card-sha256", required=True)
    parser.add_argument("--model-source-root", required=True)
    return parser


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def main(
    argv: Sequence[str] | None = None,
    *,
    root: Path | None = None,
    stdout: TextIO | None = None,
    runner=None,
    clone_file=None,
    source_state_probe=None,
) -> int:
    arguments = _parser().parse_args(argv)
    repository = (ROOT if root is None else Path(root)).resolve(strict=True)
    stream = sys.stdout if stdout is None else stdout
    request = GateBBuildRequest(
        source_head=arguments.source_head,
        attempt_id=arguments.attempt_id,
        wheelhouse_directory=Path(arguments.wheelhouse),
        wheelhouse_manifest=Path(arguments.wheelhouse_manifest),
        wheelhouse_manifest_sha256=arguments.wheelhouse_manifest_sha256,
        base_python=Path(arguments.base_python),
        base_python_sha256=arguments.base_python_sha256,
        base_python_version=arguments.base_python_version,
        bootstrap_pip_version=arguments.bootstrap_pip_version,
        base_runtime_root=Path(arguments.base_runtime_root),
        base_runtime_manifest=Path(arguments.base_runtime_manifest),
        base_runtime_manifest_sha256=arguments.base_runtime_manifest_sha256,
        model_card=arguments.model_card,
        model_card_sha256=arguments.model_card_sha256,
        model_source_root=Path(arguments.model_source_root),
    )
    try:
        if arguments.plan:
            keywords = {}
            if runner is not None:
                keywords["runner"] = runner
            if source_state_probe is not None:
                keywords["source_state_probe"] = source_state_probe
            result = plan_gate_b_runtime(repository, request, **keywords)
        elif arguments.build:
            keywords = {}
            if runner is not None:
                keywords["runner"] = runner
            if clone_file is not None:
                keywords["clone_file"] = clone_file
            if source_state_probe is not None:
                keywords["source_state_probe"] = source_state_probe
            result = build_gate_b_runtime(repository, request, **keywords)
        else:  # pragma: no cover - argparse enforces the exclusive mode
            raise A0XGateBBuilderError("an explicit builder mode is required")
    except (A0XGateBBuilderError, OSError, ValueError):
        print(_canonical({
            "error": {"code": "A0X_GATE_B_BUILDER_REFUSED"},
            "status": "refused",
        }), file=stream)
        return 2
    print(_canonical(result), file=stream)
    return 0


if __name__ == "__main__":  # pragma: no cover - direct CLI boundary
    raise SystemExit(main())
