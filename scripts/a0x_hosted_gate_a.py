#!/usr/bin/env python3
"""Emit canonical A0X Hosted Gate A lane receipts or aggregate manifests."""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_hosted_gate_a import A0XHostedGateAError, build_lane_receipt, build_manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="subcommand", required=True)
    lane = subcommands.add_parser("lane")
    lane.add_argument("--lane-id", required=True)
    lane.add_argument("--source-head", required=True)
    lane.add_argument("--source-tree", required=True)
    lane.add_argument("--github-output", required=True, type=Path)
    lane.add_argument("command", nargs=argparse.REMAINDER)
    aggregate = subcommands.add_parser("aggregate")
    aggregate.add_argument("--repository", required=True)
    aggregate.add_argument("--source-head", required=True)
    aggregate.add_argument("--source-tree", required=True)
    aggregate.add_argument("--workflow-sha256", required=True)
    aggregate.add_argument("--run-id", required=True, type=int)
    aggregate.add_argument("--run-attempt", required=True, type=int)
    aggregate.add_argument("--requirements-lock-sha256", required=True)
    aggregate.add_argument("--action-manifest-sha256", required=True)
    aggregate.add_argument("--lane-manifest-sha256", required=True)
    aggregate.add_argument("--lane-output", action="append", default=[])
    aggregate.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.subcommand == "lane":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            raw = build_lane_receipt(args.lane_id, args.source_head, args.source_tree, command, "PASS")
            encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
            with args.github_output.open("ab") as output:
                output.write(f"gate_a_lane_receipt={encoded}\n".encode("ascii"))
            return 0
        raw = build_manifest(
            repository=args.repository, source_head=args.source_head, source_tree=args.source_tree,
            workflow_sha256=args.workflow_sha256, run_id=args.run_id, run_attempt=args.run_attempt,
            requirements_lock_sha256=args.requirements_lock_sha256,
            action_manifest_sha256=args.action_manifest_sha256,
            lane_manifest_sha256=args.lane_manifest_sha256, encoded_lane_outputs=args.lane_output,
        )
        args.output.write_bytes(raw)
        return 0
    except A0XHostedGateAError as error:
        print(error.code, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
