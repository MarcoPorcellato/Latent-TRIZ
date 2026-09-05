#!/usr/bin/env python3
"""Prepare one A0X runtime bundle without invoking a material workload."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence, TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_runtime_bundle import (  # noqa: E402
    A0XRuntimeBundleError,
    RuntimePreparationRequest,
    VerticalRuntimePreparationRequest,
    preflight_runtime_bundle,
    preflight_vertical_runtime_bundle,
    prepare_runtime_bundle,
    prepare_vertical_runtime_bundle,
    vertical_package_binding_from_commitment,
)
from latent_triz.a0x_hosted_verifier import GateBVerificationRequest, verify_hosted_gate_a  # noqa: E402
from latent_triz.a0x_runtime_readiness import build_runtime_readiness  # noqa: E402


_PYTHON_METADATA_PROGRAM = r'''import importlib.metadata as m
import json
import sys
import torch
import transformers
names=("numpy","safetensors","tokenizers","torch","transformers")
value={
 "sys_executable":sys.executable,
 "python_version":".".join(str(item) for item in sys.version_info[:3]),
 "python_major_minor":list(sys.version_info[:2]),
 "sys_prefix":sys.prefix,
 "sys_base_prefix":sys.base_prefix,
 "packages":{name:m.version(name) for name in names},
 "api_symbols":{
  "torch.float32":hasattr(torch,"float32"),
  "transformers.AutoConfig":hasattr(transformers,"AutoConfig"),
  "transformers.AutoModelForCausalLM":hasattr(transformers,"AutoModelForCausalLM"),
  "transformers.AutoTokenizer":hasattr(transformers,"AutoTokenizer"),
 },
}
print(json.dumps(value,sort_keys=True,separators=(",",":")))'''


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate and construct the bundle in memory without writing runtime documents",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixed-dossier")
    mode.add_argument("--vertical-commitment")
    parser.add_argument("--gate-b-authorization", required=True)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--verifier-policy", required=True)
    parser.add_argument("--ccp", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    return parser


def _probe(argv: Sequence[str], root: Path) -> str:
    result = subprocess.run(
        list(argv), cwd=str(root), shell=False, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise A0XRuntimeBundleError("runtime preparation probe refused")
    return result.stdout


def main(
    argv: Sequence[str] | None = None,
    *,
    root: Path | None = None,
    stdout: TextIO | None = None,
    gate_a_verifier=None,
) -> int:
    """Run the shell-free readiness probes and emit one sorted public receipt."""
    arguments = _parser().parse_args(argv)
    repository = (ROOT if root is None else Path(root)).resolve(strict=True)
    stream = sys.stdout if stdout is None else stdout
    if arguments.fixed_dossier is not None:
        request = RuntimePreparationRequest(
            fixed_dossier=arguments.fixed_dossier,
            gate_b_authorization=Path(arguments.gate_b_authorization),
            verifier_executable=Path(arguments.verifier),
            verifier_policy=Path(arguments.verifier_policy),
            ccp_executable=Path(arguments.ccp),
            python_executable=Path(arguments.python),
            authorization_id=arguments.authorization_id,
            attempt_id=arguments.attempt_id,
        )
    else:
        request = VerticalRuntimePreparationRequest(
            package_binding=vertical_package_binding_from_commitment(repository, arguments.vertical_commitment),
            gate_b_authorization=Path(arguments.gate_b_authorization),
            verifier_executable=Path(arguments.verifier),
            verifier_policy=Path(arguments.verifier_policy),
            ccp_executable=Path(arguments.ccp),
            python_executable=Path(arguments.python),
            authorization_id=arguments.authorization_id,
            attempt_id=arguments.attempt_id,
        )

    def source_state_probe() -> tuple[str, bool]:
        head = _probe(("git", "rev-parse", "HEAD"), repository).strip()
        status = _probe(("git", "status", "--porcelain", "--untracked-files=all"), repository)
        return head, status == ""

    def vertical_source_state_probe() -> tuple[str, str, bool]:
        head, clean = source_state_probe()
        tree = _probe(("git", "rev-parse", "HEAD^{tree}"), repository).strip()
        return head, tree, clean

    def ccp_version_probe(path: Path) -> str:
        return _probe((str(path), "--version"), repository).strip()

    def runtime_readiness_probe(root: Path, pair, source_head: str, python_path: Path):
        raw = _probe((str(python_path), "-I", "-c", _PYTHON_METADATA_PROGRAM), repository)
        try:
            python_metadata = json.loads(raw)
        except json.JSONDecodeError as error:
            raise A0XRuntimeBundleError("Python readiness probe returned invalid JSON") from error
        return build_runtime_readiness(
            repository_root=root,
            source_head=source_head,
            pair=pair,
            python_path=python_path,
            environment_root=python_path.parent.parent,
            python_probe=python_metadata,
        )

    def default_gate_a_verifier(request: GateBVerificationRequest) -> bytes:
        def runner(argv, cwd):
            result = subprocess.run(
                list(argv), cwd=str(cwd), shell=False, check=False,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            return result.returncode, result.stdout, result.stderr

        def verifier_source_state(probe_root: Path) -> tuple[str, str, bool]:
            head = _probe(("git", "rev-parse", "HEAD"), probe_root).strip()
            tree = _probe(("git", "rev-parse", "HEAD^{tree}"), probe_root).strip()
            clean = _probe(("git", "status", "--porcelain", "--untracked-files=all"), probe_root) == ""
            return head, tree, clean

        return verify_hosted_gate_a(request, runner=runner, source_state_probe=verifier_source_state)

    try:
        if isinstance(request, VerticalRuntimePreparationRequest):
            operation = preflight_vertical_runtime_bundle if arguments.preflight else prepare_vertical_runtime_bundle
            receipt = operation(
                repository, request, source_state_probe=vertical_source_state_probe,
                ccp_version_probe=ccp_version_probe, runtime_readiness_probe=runtime_readiness_probe,
                gate_a_verifier=default_gate_a_verifier if gate_a_verifier is None else gate_a_verifier,
            )
        else:
            operation = preflight_runtime_bundle if arguments.preflight else prepare_runtime_bundle
            receipt = operation(
                repository, request, source_state_probe=source_state_probe,
                ccp_version_probe=ccp_version_probe, runtime_readiness_probe=runtime_readiness_probe,
                gate_a_verifier=default_gate_a_verifier if gate_a_verifier is None else gate_a_verifier,
            )
    except (A0XRuntimeBundleError, OSError, ValueError, subprocess.SubprocessError) as error:
        refusal: dict[str, object] = {"status": "refused"}
        if arguments.preflight:
            if isinstance(error, A0XRuntimeBundleError):
                code = error.code
                message = str(error)
            else:
                code = "A0X_RUNTIME_BUNDLE_REFUSED"
                message = "runtime bundle preflight refused"
            refusal["error"] = {"code": code, "message": message}
        print(json.dumps(refusal, sort_keys=True, separators=(",", ":")), file=stream)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")), file=stream)
    return 0


if __name__ == "__main__":  # pragma: no cover - direct CLI boundary
    raise SystemExit(main())
