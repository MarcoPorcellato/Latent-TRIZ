#!/usr/bin/env python3
"""Launch one selector-derived A0X vertical dossier through the CCP guard."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_ccp_executor import (
    A0XCcpExecutorError,
    launch_vertical_runtime_package,
    launch_vertical_slice_dossier,
)
from latent_triz.a0x_runtime_bundle import vertical_package_binding_from_commitment


def _source_head() -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=str(ROOT), check=False,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env={
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
        },
    )
    if completed.returncode != 0:
        raise A0XCcpExecutorError("repository source HEAD is unavailable")
    return completed.stdout.decode("ascii", "strict").strip()


def _source_state() -> tuple[str, str, bool]:
    """Read the future v2 source identity; this remains target-free."""
    base = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_NO_REPLACE_OBJECTS": "1"}
    commands = (("rev-parse", "HEAD"), ("write-tree",), ("status", "--short"))
    outputs: list[bytes] = []
    for command in commands:
        completed = subprocess.run(("git", *command), cwd=str(ROOT), check=False, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=base)
        if completed.returncode != 0:
            raise A0XCcpExecutorError("repository source state is unavailable")
        outputs.append(completed.stdout)
    return (
        outputs[0].decode("ascii", "strict").strip(),
        outputs[1].decode("ascii", "strict").strip(),
        outputs[2] == b"",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--implementation-source-head")
    selector.add_argument("--vertical-commitment")
    parser.add_argument("--leg", required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--execution-authorization")
    args = parser.parse_args(argv)
    try:
        if args.vertical_commitment is not None:
            if args.execution_authorization is None:
                raise A0XCcpExecutorError("v2 vertical Gate C requires an execution authorization path")
            binding = vertical_package_binding_from_commitment(ROOT, args.vertical_commitment)
            if args.leg != binding.leg.value or args.model_key != binding.model_key:
                raise A0XCcpExecutorError("v2 vertical selector differs from package binding")
            result = launch_vertical_runtime_package(
                repository_root=ROOT, package_binding=binding,
                execution_authorization_path=args.execution_authorization,
                source_state_probe=_source_state,
            )
        else:
            result = launch_vertical_slice_dossier(
                repository_root=ROOT,
                implementation_source_head=args.implementation_source_head,
                leg=args.leg,
                model_key=args.model_key,
                source_head_probe=_source_head,
            )
    except A0XCcpExecutorError as error:
        print(f"a0x-vertical-material: {error}", file=sys.stderr)
        return 2
    print(result.get("terminal_observation_path", result["status"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
