from __future__ import annotations

import base64
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_hosted_gate_a import (
    A0XHostedGateAError,
    LANE_INVALID,
    LANE_OVERSIZED,
    LANE_SET_MISMATCH,
    MANIFEST_NONCANONICAL,
    SOURCE_MISMATCH,
    build_lane_receipt,
    build_manifest,
    canonical_json_bytes,
    decode_lane_output,
    parse_manifest_bytes,
)


LANE_IDS = (
    "a0x-no-model",
    "a0x-synthetic",
    "documentation-audit",
    "repository-python311",
    "repository-python312",
    "schema-cross-validation-python311",
    "schema-cross-validation-python312",
)
COMMANDS = {
    "a0x-no-model": ("make", "a0x-no-model-verify"),
    "a0x-synthetic": ("make", "a0x-synthetic-verify"),
    "documentation-audit": ("make", "docs-audit"),
    "repository-python311": ("python", "scripts/repository_check.py"),
    "repository-python312": ("python", "scripts/repository_check.py"),
    "schema-cross-validation-python311": ("python", "scripts/schema_cross_validate.py"),
    "schema-cross-validation-python312": ("python", "scripts/schema_cross_validate.py"),
}
HEAD = "a" * 40
TREE = "b" * 40


def encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def lane_outputs(*, head: str = HEAD, tree: str = TREE) -> list[str]:
    return [
        encode(build_lane_receipt(lane, head, tree, COMMANDS[lane], "PASS"))
        for lane in LANE_IDS
    ]


class A0XHostedGateATests(unittest.TestCase):
    def build_manifest(self, outputs: list[str] | None = None) -> bytes:
        return build_manifest(
            repository="MarcoPorcellato/Latent-TRIZ",
            source_head=HEAD,
            source_tree=TREE,
            workflow_sha256="c" * 64,
            run_id=123,
            run_attempt=1,
            requirements_lock_sha256="d" * 64,
            action_manifest_sha256="e" * 64,
            lane_manifest_sha256="f" * 64,
            encoded_lane_outputs=lane_outputs() if outputs is None else outputs,
        )

    def test_lane_and_manifest_are_canonical_and_byte_identical(self) -> None:
        raw = build_lane_receipt(
            "repository-python311", HEAD, TREE,
            ("python", "scripts/repository_check.py"), "PASS",
        )
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(raw, canonical_json_bytes(json.loads(raw)))
        self.assertEqual("PASS", decode_lane_output(encode(raw))["status"])

        manifest = self.build_manifest()
        self.assertTrue(manifest.endswith(b"\n"))
        self.assertEqual(manifest, self.build_manifest())
        decoded = parse_manifest_bytes(manifest)
        self.assertEqual(list(LANE_IDS), [lane["id"] for lane in decoded["required_lanes"]])
        self.assertEqual(
            [hashlib.sha256(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))).hexdigest() for value in lane_outputs()],
            [lane["receipt_sha256"] for lane in decoded["required_lanes"]],
        )

    def test_lane_decoder_rejects_noncanonical_and_encoded_mutations(self) -> None:
        raw = build_lane_receipt("repository-python311", HEAD, TREE, COMMANDS["repository-python311"], "PASS")
        invalid = (
            (encode(raw) + "=", LANE_INVALID),
            ("!" + encode(raw)[1:], LANE_INVALID),
            (encode(raw[:-1] + b" "), MANIFEST_NONCANONICAL),
            (encode(b'{"lane_id":"repository-python311","lane_id":"repository-python311"}\n'), LANE_INVALID),
            (encode(raw.replace(b'"status":"PASS"', b'"status":"FAIL"')), LANE_INVALID),
        )
        for encoded, code in invalid:
            with self.subTest(encoded=encoded[:24]):
                with self.assertRaisesRegex(A0XHostedGateAError, code):
                    decode_lane_output(encoded)

    def test_lane_decoder_enforces_4096_byte_limit(self) -> None:
        oversized = encode(b"x" * 4097)
        with self.assertRaisesRegex(A0XHostedGateAError, LANE_OVERSIZED):
            decode_lane_output(oversized)

    def test_manifest_rejects_exact_lane_set_and_source_mismatches(self) -> None:
        outputs = lane_outputs()
        with self.assertRaisesRegex(A0XHostedGateAError, LANE_SET_MISMATCH):
            self.build_manifest(outputs[:-1])
        with self.assertRaisesRegex(A0XHostedGateAError, LANE_SET_MISMATCH):
            self.build_manifest([outputs[1], outputs[0], *outputs[2:]])

        mismatched = lane_outputs(head="c" * 40)
        with self.assertRaisesRegex(A0XHostedGateAError, SOURCE_MISMATCH):
            self.build_manifest(mismatched)

    def test_manifest_parser_rejects_unknown_fields_noncanonical_numbers_and_booleans(self) -> None:
        raw = self.build_manifest()
        document = json.loads(raw)
        document["unexpected"] = "no"
        with self.assertRaisesRegex(A0XHostedGateAError, MANIFEST_NONCANONICAL):
            parse_manifest_bytes(canonical_json_bytes(document))

        noncanonical = raw.replace(b'"run_id":123', b'"run_id":123.0')
        with self.assertRaisesRegex(A0XHostedGateAError, MANIFEST_NONCANONICAL):
            parse_manifest_bytes(noncanonical)
        boolean = raw.replace(b'"run_attempt":1', b'"run_attempt":true')
        with self.assertRaisesRegex(A0XHostedGateAError, MANIFEST_NONCANONICAL):
            parse_manifest_bytes(boolean)
        nan = raw.replace(b'"run_id":123', b'"run_id":NaN')
        with self.assertRaisesRegex(A0XHostedGateAError, MANIFEST_NONCANONICAL):
            parse_manifest_bytes(nan)
        with self.assertRaisesRegex(A0XHostedGateAError, MANIFEST_NONCANONICAL):
            canonical_json_bytes({"value": math.nan})

    def test_cli_has_only_lane_and_aggregate_and_never_writes_partial_output(self) -> None:
        script = ROOT / "scripts/a0x_hosted_gate_a.py"
        help_result = subprocess.run(
            [sys.executable, str(script), "--help"], cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertIn("{lane,aggregate}", help_result.stdout)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "github-output"
            bad = subprocess.run(
                [sys.executable, str(script), "lane", "--lane-id", "unknown", "--source-head", HEAD,
                 "--source-tree", TREE, "--github-output", str(output), "--", "echo", "bad"],
                cwd=ROOT, text=True, capture_output=True,
            )
            self.assertNotEqual(0, bad.returncode)
            self.assertFalse(output.exists())

