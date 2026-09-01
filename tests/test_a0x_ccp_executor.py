"""Synthetic-only tests for the fixed A0X CCP guard adapter."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from latent_triz.a0x_ccp_executor import (
    A0XCcpExecutorError,
    GuardPreflightOutput,
    ProcessResult,
    launch_fixed_dossier,
    runtime_mapping_path,
)
from latent_triz.a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    Leg,
    PairBinding,
    canonical_commitment,
)
from latent_triz.a0x_material_contract import derive_runtime_paths
from tests.a0x_test_support import authorization_documents, pair_binding


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class _FakeProcess:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[tuple[str, ...], Path, dict[str, str], int, int]] = []

    def run(self, argv, *, cwd, env, timeout_seconds, capture_limit_bytes):
        self.calls.append((tuple(argv), cwd, dict(env), timeout_seconds, capture_limit_bytes))
        return self.result


class _FakeGuardPreflight:
    def __init__(self, *, source_head: str = "a" * 40, version: str = "commit-ci-preflight 0.1.0", outputs=None) -> None:
        self.source_head = source_head
        self.version = version
        self.outputs = outputs
        self.calls: list[tuple[Path, Path]] = []

    def produce(self, *, ccp_path: Path, repository_root: Path):
        self.calls.append((ccp_path, repository_root))
        if self.outputs is not None:
            return self.outputs
        return (
            GuardPreflightOutput("ccp_version", 0, self.version.encode()),
            GuardPreflightOutput("resource_status", 0, b'{"decision":"admit"}'),
            GuardPreflightOutput("admission_status", 0, b'{"active":false,"queue_count":0,"slot":{"state":"free"}}'),
            GuardPreflightOutput("git_source_state", 0, json.dumps({"head": self.source_head, "clean": True}, separators=(",", ":")).encode()),
            GuardPreflightOutput("docker_context", 0, b"orbstack\n"),
            GuardPreflightOutput("docker_active_count", 0, b""),
        )


class A0XCcpExecutorTests(unittest.TestCase):
    _dossier = "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"

    def _fixture(self, *, result: ProcessResult | None = None):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        pair_mapping = pair_binding(Leg.A0, "gpt2")
        pair = PairBinding.from_mapping(pair_mapping)
        dossier, authorization, _chain = authorization_documents(pair_mapping)
        source_head = "a" * 40
        runtime = derive_runtime_paths(pair, source_head=source_head)

        contract = root / "experiments/a0x-six-model/material-execution-contract.json"
        contract.parent.mkdir(parents=True)
        contract_raw = b'{"synthetic":"material-contract"}'
        contract.write_bytes(contract_raw)
        contract_hash = _sha(contract_raw)
        dossier["material_contract_raw_sha256"] = contract_hash
        authorization["material_contract_raw_sha256"] = contract_hash
        authorization["approved_dossier_commitment"] = canonical_commitment(
            dossier, APPROVAL_DOSSIER_PROFILE,
        ).as_mapping()

        child = root / "scripts/a0x_material_child.py"
        child.parent.mkdir(parents=True)
        child_raw = b"synthetic-child\n"
        child.write_bytes(child_raw)
        ccp = root / ".a0x-runtime/bin/ccp"
        ccp.parent.mkdir(parents=True)
        ccp_raw = b"synthetic-ccp\n"
        ccp.write_bytes(ccp_raw)
        python = root / ".a0x-runtime/bin/python"
        python.write_bytes(b"synthetic-python\n")
        python.chmod(0o700)

        authorization["ccp"]["sha256"] = _sha(ccp_raw)
        authorization["qualification_evidence"]["ccp"]["binary_sha256"] = _sha(ccp_raw)
        launch = authorization["guard_launch"]
        launch["ccp"]["sha256"] = _sha(ccp_raw)
        launch["python"]["sha256"] = _sha(python.read_bytes())
        launch["child_script"]["sha256"] = _sha(child_raw)
        launch["source_head"] = source_head
        self.assertEqual(runtime.launch_descriptor_path, launch["launch_descriptor"]["path"])
        descriptor = root / runtime.launch_descriptor_path
        descriptor.parent.mkdir(parents=True)
        from latent_triz.a0x_runtime_readiness import canonical_json_bytes, runtime_readiness_path
        from tests.test_a0x_runtime_bundle import _synthetic_runtime_readiness
        readiness = _synthetic_runtime_readiness(root, pair, source_head, python.resolve())
        readiness_path = root / runtime_readiness_path(pair)
        readiness_path.parent.mkdir(parents=True, exist_ok=True)
        readiness_raw = canonical_json_bytes(readiness)
        readiness_path.write_bytes(readiness_raw)
        descriptor_raw = json.dumps({
            "synthetic": "child-descriptor",
            "python": {"role": "python", "path": str(python.resolve()), "sha256": _sha(python.read_bytes())},
            "runtime_readiness": {
                "role": "readiness", "path": readiness_path.relative_to(root).as_posix(),
                "sha256": _sha(readiness_raw),
            },
        }, sort_keys=True, separators=(",", ":")).encode()
        descriptor.write_bytes(descriptor_raw)
        launch["launch_descriptor"]["sha256"] = _sha(descriptor_raw)
        qualification_receipt = {
            "schema_version": "2.0",
            "producer": {"name": "commit-ci-preflight", "version": "0.1.0+matrix-v2-legacy-v1"},
            "repository": {"repository": "MarcoPorcellato/Latent-TRIZ", "commit_sha": source_head, "dirty": False},
            "run": {"generation": 1},
            "overall_status": "PASS",
            "incomplete_reason": None,
        }
        receipt_id = "sha256:" + _sha(json.dumps(qualification_receipt, sort_keys=True, separators=(",", ":")).encode())
        qualification_raw = json.dumps({"receipt_id": receipt_id, "receipt": qualification_receipt}, sort_keys=True, separators=(",", ":")).encode()
        authorization["qualification_evidence"]["qualification_receipt_id"] = receipt_id
        authorization["qualification_evidence"]["qualification_receipt_raw_sha256"] = _sha(qualification_raw)
        qualification_path = root / runtime.qualification_receipt_path
        qualification_path.parent.mkdir(parents=True)
        qualification_path.write_bytes(qualification_raw)
        authorization_path = root / runtime.authorization_path
        authorization_path.parent.mkdir(parents=True)
        authorization_path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
        dossier_path = root / self._dossier
        dossier_path.parent.mkdir(parents=True)
        dossier_path.write_bytes(json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode())

        mapping_path = root / runtime_mapping_path(pair, source_head=source_head)
        mapping_path.parent.mkdir(parents=True)
        mapping = {
            "mapping_profile": "a0x-runtime-role-mapping-v1",
            "source_head": source_head,
            "repository_root": str(root.resolve()),
            "pair_binding": pair.as_mapping(),
            "ccp": {"role": "ccp", "path": str(ccp.resolve()), "sha256": _sha(ccp_raw)},
            "python": {"role": "python", "path": str(python.resolve()), "sha256": _sha(python.read_bytes())},
            "descriptor": {"path": runtime.launch_descriptor_path, "sha256": _sha(descriptor_raw)},
        }
        mapping_path.write_bytes(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode())
        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
        fake = _FakeProcess(result or ProcessResult(
            returncode=0, stdout_sha256=_sha(terminal), stdout_bytes=len(terminal),
            stderr_sha256=_sha(b""), stderr_bytes=0, stdout_prefix=terminal,
        ))
        return root, pair, runtime, authorization, mapping_path, fake

    def _launch(self, root: Path, fake: _FakeProcess, *, preflight: _FakeGuardPreflight | None = None):
        mapping = {("a0", "gpt2"): self._dossier}
        with patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value=mapping):
            return launch_fixed_dossier(
                repository_root=root,
                fixed_dossier=self._dossier,
                source_head_probe=lambda: "a" * 40,
                process_executor=fake,
                guard_preflight_producer=preflight or _FakeGuardPreflight(),
            )

    def test_exact_template_launches_once_with_sanitized_environment(self) -> None:
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        root = bundle.root
        pair = PairBinding.from_mapping(bundle.receipt["pair_binding"])
        runtime = derive_runtime_paths(pair, source_head=bundle.receipt["source_head"])
        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
        fake = _FakeProcess(ProcessResult(
            returncode=0,
            stdout_sha256=_sha(terminal),
            stdout_bytes=len(terminal),
            stderr_sha256=_sha(b""),
            stderr_bytes=0,
            stdout_prefix=terminal,
        ))
        preflight = _FakeGuardPreflight()
        expected_ccp_sha256 = json.loads(
            (root / "experiments/a0x-six-model/material-execution-contract.json").read_text(),
        )["ccp"]["sha256"]
        actual_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
        with patch(
            "latent_triz.a0x_ccp_executor.sha256_file",
            side_effect=lambda path: expected_ccp_sha256 if Path(path).resolve() == bundle.request.ccp_executable.resolve()
            else actual_sha256_file(path),
        ):
            result = self._launch(root, fake, preflight=preflight)
        self.assertEqual("completed", result["status"])
        self.assertEqual(pair.as_mapping(), result["pair_binding"])
        self.assertEqual(runtime.claim_path, result["claim_path"])
        self.assertTrue((root / runtime.claim_path).is_file())
        authorization_raw = (root / bundle.receipt["authorization_path"]).read_bytes()
        authorization_commitment = canonical_commitment(
            json.loads(authorization_raw), CURRENT_EXECUTION_AUTHORIZATION_PROFILE,
        ).as_mapping()
        claim = json.loads((root / runtime.claim_path).read_text())
        pre_run = json.loads((root / runtime.observation_directory / "pre-run-observation.json").read_text())
        observation = json.loads((root / result["terminal_observation_path"]).read_text())
        for document in (claim, pre_run, observation, result):
            self.assertEqual(_sha(authorization_raw), document["authorization_raw_sha256"])
            self.assertEqual(authorization_commitment, document["authorization_commitment"])
            self.assertNotIn(authorization_raw.decode("utf-8"), json.dumps(document, sort_keys=True))
        self.assertEqual("completed", observation["outer_exit_classification"])
        self.assertFalse(observation["recovery_required"])
        self.assertEqual("null", observation["child_terminal_status"])
        self.assertEqual(1, len(fake.calls))
        argv, cwd, env, timeout, capture_limit = fake.calls[0]
        self.assertEqual(root.resolve(), cwd)
        self.assertEqual(3900, timeout)
        self.assertEqual(65536, capture_limit)
        self.assertEqual({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false", "PYTHONNOUSERSITE": "1"}, env)
        self.assertEqual("guard", argv[1])
        self.assertEqual("exec", argv[2])
        self.assertIn("--timeout-seconds", argv)
        self.assertEqual("3600", argv[argv.index("--timeout-seconds") + 1])
        self.assertEqual("--launch-descriptor", argv[-2])
        self.assertEqual(runtime.launch_descriptor_path, argv[-1])
        self.assertEqual(1, len(preflight.calls))
        guard_observation = json.loads((root / runtime.observation_directory / "guard-preflight-observation.json").read_text())
        self.assertEqual(
            ["ccp_version", "resource_status", "admission_status", "git_source_state", "docker_context", "docker_active_count"],
            [row["role"] for row in guard_observation["commands"]],
        )
        self.assertNotIn("argv", json.dumps(guard_observation))
        self.assertNotIn(".commit-ci-preflight.toml", json.dumps(guard_observation))
        self.assertEqual(_sha((root / runtime.observation_directory / "guard-preflight-observation.json").read_bytes()), observation["guard_preflight_observation_raw_sha256"])

    def test_guard_preflight_denials_refuse_before_claim_or_guard(self) -> None:
        cases = {
            "resource": (1, b'{"decision":"deny"}'),
            "unknown": (1, b'{"decision":"unknown"}'),
            "dirty": (3, json.dumps({"head": "a" * 40, "clean": False}, separators=(",", ":")).encode()),
            "container": (5, b"container-id\n"),
        }
        for name, (index, raw) in cases.items():
            with self.subTest(name=name):
                root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
                baseline = list(_FakeGuardPreflight().produce(ccp_path=root / ".a0x-runtime/bin/ccp", repository_root=root))
                baseline[index] = GuardPreflightOutput(baseline[index].role, 0, raw)
                with self.assertRaisesRegex(A0XCcpExecutorError, "guard preflight"):
                    self._launch(root, fake, preflight=_FakeGuardPreflight(outputs=tuple(baseline)))
                self.assertFalse((root / runtime.claim_path).exists())
                self.assertEqual([], fake.calls)

    def test_pre_run_observation_failure_records_recovery_without_starting_guard(self) -> None:
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        fake = _FakeProcess(ProcessResult(
            returncode=0, stdout_sha256=_sha(b""), stdout_bytes=0,
            stderr_sha256=_sha(b""), stderr_bytes=0,
        ))
        runtime = derive_runtime_paths(
            PairBinding.from_mapping(bundle.receipt["pair_binding"]),
            source_head=bundle.receipt["source_head"],
        )
        expected_ccp_sha256 = json.loads(
            (bundle.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(),
        )["ccp"]["sha256"]
        actual_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
        with (
            patch(
                "latent_triz.a0x_ccp_executor.sha256_file",
                side_effect=lambda path: expected_ccp_sha256
                if Path(path).resolve() == bundle.request.ccp_executable.resolve()
                else actual_sha256_file(path),
            ),
            patch(
                "latent_triz.a0x_ccp_executor._write_pre_run_observation",
                side_effect=OSError("injected pre-run write failure"),
            ),
            patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value={("a0", "gpt2"): bundle.request.fixed_dossier}),
            self.assertRaises(A0XCcpExecutorError),
        ):
            launch_fixed_dossier(
                repository_root=bundle.root,
                fixed_dossier=bundle.request.fixed_dossier,
                source_head_probe=lambda: "a" * 40,
                process_executor=fake,
                guard_preflight_producer=_FakeGuardPreflight(),
            )
        self.assertEqual([], fake.calls)
        terminal = json.loads((bundle.root / runtime.observation_directory / "terminal-observation.json").read_text())
        self.assertEqual("launcher_internal_error", terminal["outer_exit_classification"])
        self.assertTrue(terminal["recovery_required"])
        self.assertEqual("OSError", terminal["error_type"])
        self.assertTrue((bundle.root / runtime.claim_path).is_file())

    def test_configuration_backed_preflight_roles_are_rejected_before_claim(self) -> None:
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
        outputs = list(_FakeGuardPreflight().produce(ccp_path=root / ".a0x-runtime/bin/ccp", repository_root=root))
        outputs[2] = GuardPreflightOutput("plan", 0, outputs[2].raw)
        with self.assertRaisesRegex(A0XCcpExecutorError, "fixed sequence"):
            self._launch(root, fake, preflight=_FakeGuardPreflight(outputs=tuple(outputs)))
        self.assertFalse((root / runtime.claim_path).exists())
        self.assertEqual([], fake.calls)

    def test_authorization_replacement_during_guard_preflight_refuses_before_claim(self) -> None:
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
        authorization_path = root / runtime.authorization_path

        class ReplacingPreflight(_FakeGuardPreflight):
            def produce(self, *, ccp_path: Path, repository_root: Path):
                rows = super().produce(ccp_path=ccp_path, repository_root=repository_root)
                authorization_path.write_bytes(b'{"replacement":true}')
                return rows

        with self.assertRaisesRegex(A0XCcpExecutorError, "authorization"):
            self._launch(root, fake, preflight=ReplacingPreflight())
        self.assertFalse((root / runtime.claim_path).exists())
        self.assertEqual([], fake.calls)

    def test_authorization_replacement_after_claim_seals_attempt_without_process(self) -> None:
        root, _pair, runtime, authorization, _mapping, fake = self._fixture()
        authorization_path = root / runtime.authorization_path
        authorization_raw = authorization_path.read_bytes()
        authorization_commitment = canonical_commitment(
            authorization, EXECUTION_AUTHORIZATION_PROFILE,
        ).as_mapping()
        module = __import__("latent_triz.a0x_ccp_executor", fromlist=["_write_pre_run_observation"])
        write_pre_run = module._write_pre_run_observation

        def replace_after_pre_run(*args, **kwargs):
            path = write_pre_run(*args, **kwargs)
            authorization_path.write_bytes(b'{"replacement":true}')
            return path

        with patch("latent_triz.a0x_ccp_executor._write_pre_run_observation", side_effect=replace_after_pre_run):
            with self.assertRaisesRegex(A0XCcpExecutorError, "terminal result"):
                self._launch(root, fake)
        self.assertEqual([], fake.calls)
        self.assertTrue((root / runtime.claim_path).is_file())
        claim = json.loads((root / runtime.claim_path).read_text())
        pre_run = json.loads((root / runtime.observation_directory / "pre-run-observation.json").read_text())
        terminal = json.loads((root / runtime.observation_directory / "terminal-observation.json").read_text())
        for document in (claim, pre_run, terminal):
            self.assertEqual(_sha(authorization_raw), document["authorization_raw_sha256"])
            self.assertEqual(authorization_commitment, document["authorization_commitment"])
        self.assertEqual("launcher_internal_error", terminal["outer_exit_classification"])
        self.assertTrue(terminal["recovery_required"])

    def test_material_contract_replacement_is_checked_at_both_authorization_boundaries(self) -> None:
        for timing in ("pre_claim", "post_claim"):
            with self.subTest(timing=timing):
                root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
                contract_path = root / "experiments/a0x-six-model/material-execution-contract.json"
                if timing == "pre_claim":
                    class ReplacingPreflight(_FakeGuardPreflight):
                        def produce(self, *, ccp_path: Path, repository_root: Path):
                            rows = super().produce(ccp_path=ccp_path, repository_root=repository_root)
                            contract_path.write_bytes(b'{"replacement":true}')
                            return rows

                    with self.assertRaisesRegex(A0XCcpExecutorError, "material contract"):
                        self._launch(root, fake, preflight=ReplacingPreflight())
                    self.assertFalse((root / runtime.claim_path).exists())
                else:
                    module = __import__("latent_triz.a0x_ccp_executor", fromlist=["_write_pre_run_observation"])
                    write_pre_run = module._write_pre_run_observation

                    def replace_after_pre_run(*args, **kwargs):
                        path = write_pre_run(*args, **kwargs)
                        contract_path.write_bytes(b'{"replacement":true}')
                        return path

                    with patch("latent_triz.a0x_ccp_executor._write_pre_run_observation", side_effect=replace_after_pre_run):
                        with self.assertRaisesRegex(A0XCcpExecutorError, "terminal result"):
                            self._launch(root, fake)
                    self.assertTrue((root / runtime.claim_path).is_file())
                self.assertEqual([], fake.calls)

    def test_public_guard_preflight_rejects_private_locator_and_raw_log_fields(self) -> None:
        from latent_triz.a0x_ccp_executor import _assert_public_safe_preflight

        for value in ({"path": "/private/tmp/leak"}, {"raw": "opaque log"}, {"nested": ["file:///private/tmp/leak"]}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(A0XCcpExecutorError, "leaks"):
                    _assert_public_safe_preflight(value)

    def test_production_preflight_has_only_the_six_guard_roles_and_no_config_commands(self) -> None:
        from latent_triz.a0x_ccp_executor import SubprocessGuardPreflightProducer

        responses = iter((
            b"commit-ci-preflight 0.1.0\n", b'{"decision":"admit"}',
            b'{"active":false,"queue_count":0,"slot":{"state":"free"}}',
            ("a" * 40 + "\n").encode(), b"## agent/test\n", b"orbstack\n", b"",
        ))
        calls: list[tuple[str, ...]] = []
        waits: list[int | None] = []
        class FakePopen:
            def __init__(self, raw: bytes) -> None:
                self.stdout = io.BytesIO(raw)
                self.returncode = 0
            def wait(self, timeout=None):
                waits.append(timeout)
                return self.returncode
            def kill(self):
                self.returncode = -9
        def fake_popen(argv, **_kwargs):
            calls.append(tuple(argv))
            return FakePopen(next(responses))
        with patch("latent_triz.a0x_ccp_executor.subprocess.Popen", side_effect=fake_popen):
            rows = SubprocessGuardPreflightProducer().produce(
                ccp_path=Path("/private/tmp/ccp"), repository_root=Path("/private/tmp/repository"),
            )
        self.assertEqual(
            ["ccp_version", "resource_status", "admission_status", "git_source_state", "docker_context", "docker_active_count"],
            [row.role for row in rows],
        )
        flattened = " ".join(" ".join(call) for call in calls)
        self.assertNotIn("plan", flattened)
        self.assertNotIn("doctor", flattened)
        self.assertNotIn("dry-run", flattened)
        self.assertTrue(all(value == 30 for value in waits))

    def test_production_preflight_probe_timeout_and_oversize_output_fail_closed(self) -> None:
        from latent_triz.a0x_ccp_executor import SubprocessGuardPreflightProducer

        class TimeoutPopen:
            stdout = io.BytesIO(b"")
            returncode = None
            def wait(self, timeout=None):
                if self.returncode is None:
                    raise subprocess.TimeoutExpired("synthetic", timeout)
                return self.returncode
            def kill(self):
                self.returncode = -9
        with patch("latent_triz.a0x_ccp_executor.subprocess.Popen", return_value=TimeoutPopen()):
            with self.assertRaisesRegex(A0XCcpExecutorError, "timed out"):
                SubprocessGuardPreflightProducer._run(("synthetic",), Path("/private/tmp"))

        class OversizePopen:
            stdout = io.BytesIO(b"x" * 65_537)
            returncode = 0
            def wait(self, timeout=None):
                return 0
            def kill(self):
                return None
        with patch("latent_triz.a0x_ccp_executor.subprocess.Popen", return_value=OversizePopen()):
            with self.assertRaisesRegex(A0XCcpExecutorError, "capture limit"):
                SubprocessGuardPreflightProducer._run(("synthetic",), Path("/private/tmp"))

    def test_rejects_any_path_not_in_the_frozen_twelve_set_before_claim(self) -> None:
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
        with self.assertRaisesRegex(A0XCcpExecutorError, "exact twelve"):
            launch_fixed_dossier(
                repository_root=root, fixed_dossier="experiments/a0x-six-model/approval-dossiers/a0/other.json",
                source_head_probe=lambda: "a" * 40, process_executor=fake,
            )
        self.assertFalse((root / runtime.claim_path).exists())
        self.assertEqual([], fake.calls)

    def test_hash_drift_refuses_before_attempt_claim(self) -> None:
        root, _pair, runtime, _authorization, mapping_path, fake = self._fixture()
        mapping = json.loads(mapping_path.read_text())
        mapping["ccp"]["sha256"] = "0" * 64
        mapping_path.write_text(json.dumps(mapping, sort_keys=True, separators=(",", ":")))
        with self.assertRaisesRegex(A0XCcpExecutorError, "ccp hash"):
            self._launch(root, fake)
        self.assertFalse((root / runtime.claim_path).exists())
        self.assertEqual([], fake.calls)

    def test_dossier_implementation_anchor_can_precede_the_authorization_live_head(self) -> None:
        root, _pair, _runtime, authorization, _mapping, fake = self._fixture()
        dossier_path = root / self._dossier
        dossier = json.loads(dossier_path.read_text())
        dossier["implementation_source_head"] = "b" * 40
        authorization["implementation_source_head"] = "b" * 40
        authorization["approved_dossier_commitment"] = canonical_commitment(
            dossier, APPROVAL_DOSSIER_PROFILE,
        ).as_mapping()
        source_head = authorization["source_head"]
        runtime = derive_runtime_paths(PairBinding.from_mapping(dossier["pair_binding"]), source_head=source_head)
        (root / runtime.authorization_path).write_bytes(
            json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode(),
        )
        dossier_path.write_bytes(json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode())

        result = self._launch(root, fake)
        self.assertEqual("completed", result["status"])

    def test_live_source_drift_from_execution_authorization_refuses_before_claim(self) -> None:
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
        mapping = {("a0", "gpt2"): self._dossier}
        with patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value=mapping):
            with self.assertRaisesRegex(A0XCcpExecutorError, "execution authorization"):
                launch_fixed_dossier(
                    repository_root=root,
                    fixed_dossier=self._dossier,
                    source_head_probe=lambda: "b" * 40,
                    process_executor=fake,
                    guard_preflight_producer=_FakeGuardPreflight(source_head="b" * 40),
                )
        self.assertFalse((root / runtime.claim_path).exists())
        self.assertEqual([], fake.calls)

    def test_local_qualification_receipt_missing_or_mutated_refuses_before_claim(self) -> None:
        for mutation, expected in (("missing", "unavailable"), ("raw", "raw SHA-256"), ("semantic", "semantic ID")):
            with self.subTest(mutation=mutation):
                root, _pair, runtime, authorization, _mapping, fake = self._fixture()
                receipt_path = root / runtime.qualification_receipt_path
                if mutation == "missing":
                    receipt_path.unlink()
                else:
                    envelope = json.loads(receipt_path.read_text())
                    if mutation == "raw":
                        envelope["receipt"]["overall_status"] = "FAIL"
                    else:
                        envelope["receipt_id"] = "sha256:" + "0" * 64
                        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
                        authorization["qualification_evidence"]["qualification_receipt_raw_sha256"] = _sha(raw)
                        authorization_path = root / runtime.authorization_path
                        authorization_path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
                    receipt_path.write_bytes(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode())
                with self.assertRaisesRegex(A0XCcpExecutorError, expected):
                    self._launch(root, fake)
                self.assertFalse((root / runtime.claim_path).exists())
                self.assertEqual([], fake.calls)

    def test_current_gate_a_five_file_matrix_refuses_before_claim_or_guard(self) -> None:
        """Every current hosted input is an independent local Gate-C boundary."""
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        for role in ("manifest", "attestation_bundle", "trusted_root", "transport", "verification_receipt"):
            for mutation in ("missing", "mutated", "symlink", "hardlink", "nonregular"):
                with self.subTest(role=role, mutation=mutation):
                    bundle = prepare_constructible_runtime_bundle()
                    self.addCleanup(bundle.close)
                    root = bundle.root
                    authorization = json.loads((root / bundle.receipt["authorization_path"]).read_text())
                    evidence = authorization["gate_a_evidence"]
                    binding = evidence["verification_receipt"] if role == "verification_receipt" else evidence["hosted_inputs"][role]
                    path = root / binding["path"]
                    if mutation == "missing":
                        path.unlink()
                    elif mutation == "mutated":
                        path.write_bytes(b"mutated")
                    elif mutation == "symlink":
                        target = root / "untrusted-gate-a-bytes"
                        target.write_bytes(path.read_bytes())
                        path.unlink()
                        path.symlink_to(target)
                    elif mutation == "hardlink":
                        alias = root / "untrusted-gate-a-alias"
                        os.link(path, alias)
                    else:
                        path.unlink()
                        path.mkdir()
                    fake = _FakeProcess(ProcessResult(
                        returncode=0, stdout_sha256=_sha(b""), stdout_bytes=0,
                        stderr_sha256=_sha(b""), stderr_bytes=0,
                    ))
                    pair = PairBinding.from_mapping(bundle.receipt["pair_binding"])
                    runtime = derive_runtime_paths(pair, source_head=bundle.receipt["source_head"])
                    ccp_sha256 = json.loads((root / "experiments/a0x-six-model/material-execution-contract.json").read_text())["ccp"]["sha256"]
                    actual_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
                    with (
                        patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value={("a0", "gpt2"): bundle.request.fixed_dossier}),
                        patch("latent_triz.a0x_ccp_executor.sha256_file", side_effect=lambda candidate: ccp_sha256 if Path(candidate).resolve() == bundle.request.ccp_executable.resolve() else actual_sha256_file(candidate)),
                        self.assertRaises(A0XCcpExecutorError),
                    ):
                        launch_fixed_dossier(
                            repository_root=root, fixed_dossier=bundle.request.fixed_dossier,
                            source_head_probe=lambda: "a" * 40, process_executor=fake,
                            guard_preflight_producer=_FakeGuardPreflight(),
                        )
                    self.assertFalse((root / runtime.claim_path).exists())
                    self.assertEqual([], fake.calls)

    def test_current_gate_a_replacement_during_preflight_refuses_before_claim(self) -> None:
        """The preflight-to-claim race is closed by a second five-file rehash."""
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        for role in ("manifest", "attestation_bundle", "trusted_root", "transport", "verification_receipt"):
            with self.subTest(role=role):
                bundle = prepare_constructible_runtime_bundle()
                self.addCleanup(bundle.close)
                root = bundle.root
                authorization = json.loads((root / bundle.receipt["authorization_path"]).read_text())
                evidence = authorization["gate_a_evidence"]
                binding = evidence["verification_receipt"] if role == "verification_receipt" else evidence["hosted_inputs"][role]
                path = root / binding["path"]

                class _MutatingPreflight(_FakeGuardPreflight):
                    def produce(self, *, ccp_path: Path, repository_root: Path):
                        replacement = path.with_name(path.name + ".replacement")
                        replacement.write_bytes(b"post-preflight replacement")
                        os.replace(replacement, path)
                        return super().produce(ccp_path=ccp_path, repository_root=repository_root)

                fake = _FakeProcess(ProcessResult(
                    returncode=0, stdout_sha256=_sha(b""), stdout_bytes=0,
                    stderr_sha256=_sha(b""), stderr_bytes=0,
                ))
                pair = PairBinding.from_mapping(bundle.receipt["pair_binding"])
                runtime = derive_runtime_paths(pair, source_head=bundle.receipt["source_head"])
                contract = json.loads((root / "experiments/a0x-six-model/material-execution-contract.json").read_text())
                actual_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
                with (
                    patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value={("a0", "gpt2"): bundle.request.fixed_dossier}),
                    patch("latent_triz.a0x_ccp_executor.sha256_file", side_effect=lambda candidate: contract["ccp"]["sha256"] if Path(candidate).resolve() == bundle.request.ccp_executable.resolve() else actual_sha256_file(candidate)),
                    self.assertRaisesRegex(A0XCcpExecutorError, "raw SHA-256"),
                ):
                    launch_fixed_dossier(
                        repository_root=root, fixed_dossier=bundle.request.fixed_dossier,
                        source_head_probe=lambda: "a" * 40, process_executor=fake,
                        guard_preflight_producer=_MutatingPreflight(),
                    )
                self.assertFalse((root / runtime.claim_path).exists())
                self.assertEqual([], fake.calls)

    def test_current_hosted_verifier_and_ccp_producer_bind_independently(self) -> None:
        """Hosted Gate A identity is not reinterpreted as the CCP identity."""
        from latent_triz.a0x_ccp_executor import rehash_gate_a_evidence
        from tests.test_a0x_runtime_bundle import prepare_constructible_runtime_bundle

        bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        authorization = json.loads((bundle.root / bundle.receipt["authorization_path"]).read_text())
        hosted = authorization["gate_a_evidence"]["verifier"]
        ccp = authorization["ccp"]
        self.assertEqual("github_cli_verifier", hosted["role"])
        self.assertEqual("commit-ci-preflight", ccp["executable_name"])
        self.assertNotEqual(hosted["sha256"], ccp["sha256"])
        self.assertEqual(
            {"manifest", "attestation_bundle", "trusted_root", "transport", "verification_receipt"},
            set(rehash_gate_a_evidence(
                repository_root=bundle.root,
                evidence=authorization["gate_a_evidence"],
                source_head=authorization["source_head"],
            )),
        )

    def test_runtime_role_mapping_is_distinct_for_all_twelve_pair_source_run_combinations(self) -> None:
        models = ("smollm2_360m", "qwen3_0_6b_base", "gpt2", "smollm2_135m", "gpt_neo_125m", "qwen2_5_0_5b")
        source = "a" * 40
        paths = {
            runtime_mapping_path(pair_binding(leg, model), source_head=source)
            for leg in (Leg.A0, Leg.R1) for model in models
        }
        self.assertEqual(12, len(paths))
        self.assertTrue(all(path.startswith(f".a0x-runtime/bin/{source}/") for path in paths))
        self.assertTrue(all(path.endswith("/runtime-mapping.json") for path in paths))

    def test_existing_claim_prevents_a_retry(self) -> None:
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
        self._launch(root, fake)
        with self.assertRaisesRegex(Exception, "(claim|preflight observation)"):
            self._launch(root, fake)
        self.assertEqual(1, len(fake.calls))

    def test_post_claim_source_drift_is_sealed_without_starting_a_child(self) -> None:
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture()
        samples = iter(["a" * 40, "a" * 40, "a" * 40, "b" * 40])
        mapping = {("a0", "gpt2"): self._dossier}
        with patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value=mapping):
            with self.assertRaisesRegex(A0XCcpExecutorError, "terminal result"):
                launch_fixed_dossier(
                    repository_root=root, fixed_dossier=self._dossier,
                    source_head_probe=lambda: next(samples), process_executor=fake,
                    guard_preflight_producer=_FakeGuardPreflight(),
                )
        self.assertEqual([], fake.calls)
        self.assertTrue((root / runtime.claim_path).is_file())
        observation = json.loads((root / runtime.observation_directory / "terminal-observation.json").read_text())
        self.assertEqual("launcher_internal_error", observation["outer_exit_classification"])
        self.assertTrue(observation["recovery_required"])

    def test_pre_run_observation_is_durable_before_executor_failure(self) -> None:
        class RaisingProcess:
            def run(self, *_args, **_kwargs):
                raise RuntimeError("synthetic crash")

        root, _pair, runtime, authorization, _mapping, _fake = self._fixture()
        mapping = {("a0", "gpt2"): self._dossier}
        with patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value=mapping):
            with self.assertRaisesRegex(A0XCcpExecutorError, "terminal result"):
                launch_fixed_dossier(
                    repository_root=root, fixed_dossier=self._dossier,
                    source_head_probe=lambda: "a" * 40, process_executor=RaisingProcess(),
                    guard_preflight_producer=_FakeGuardPreflight(),
                )
        pre_run = root / runtime.observation_directory / "pre-run-observation.json"
        terminal = root / runtime.observation_directory / "terminal-observation.json"
        self.assertTrue(pre_run.is_file())
        self.assertTrue(terminal.is_file())
        pre_run_value = json.loads(pre_run.read_text())
        authorization_raw = (root / runtime.authorization_path).read_bytes()
        authorization_commitment = canonical_commitment(
            authorization, EXECUTION_AUTHORIZATION_PROFILE,
        ).as_mapping()
        self.assertEqual(runtime.claim_path, pre_run_value["claim_path"])
        self.assertEqual(authorization["qualification_evidence"]["qualification_receipt_id"], pre_run_value["qualification_receipt_id"])
        self.assertEqual(authorization["qualification_evidence"]["qualification_receipt_raw_sha256"], pre_run_value["qualification_receipt_raw_sha256"])
        terminal_value = json.loads(terminal.read_text())
        for document in (pre_run_value, terminal_value):
            self.assertEqual(_sha(authorization_raw), document["authorization_raw_sha256"])
            self.assertEqual(authorization_commitment, document["authorization_commitment"])
        self.assertEqual(_sha(pre_run.read_bytes()), terminal_value["pre_run_observation_raw_sha256"])
        self.assertEqual("launcher_internal_error", terminal_value["outer_exit_classification"])

    def test_every_documented_outer_terminal_exit_is_preserved_for_recovery(self) -> None:
        expected = {
            5: "admission_rejected", 6: "resource_rejected", 70: "cleanup_or_internal",
            124: "timeout", 130: "cancelled", 42: "child_exit_42",
        }
        for code, classification in expected.items():
            with self.subTest(code=code):
                terminal = b"not-a-public-child-terminal\n"
                root, _pair, runtime, _authorization, _mapping, fake = self._fixture(result=ProcessResult(
                    returncode=code, stdout_sha256=_sha(terminal), stdout_bytes=len(terminal),
                    stderr_sha256=_sha(b""), stderr_bytes=0, stdout_prefix=terminal,
                    timed_out=code == 124,
                ))
                with self.assertRaisesRegex(A0XCcpExecutorError, classification):
                    self._launch(root, fake)
                observation = json.loads((root / runtime.observation_directory / "terminal-observation.json").read_text())
                self.assertEqual(classification, observation["outer_exit_classification"])
                self.assertTrue(observation["recovery_required"])
                self.assertTrue((root / runtime.claim_path).is_file())

    def test_success_without_a_valid_child_terminal_is_not_promoted(self) -> None:
        raw = b"unexpected output\n"
        root, _pair, runtime, _authorization, _mapping, fake = self._fixture(result=ProcessResult(
            returncode=0, stdout_sha256=_sha(raw), stdout_bytes=len(raw),
            stderr_sha256=_sha(b""), stderr_bytes=0, stdout_prefix=raw,
        ))
        with self.assertRaisesRegex(A0XCcpExecutorError, "valid child terminal"):
            self._launch(root, fake)
        observation = json.loads((root / runtime.observation_directory / "terminal-observation.json").read_text())
        self.assertEqual("completed", observation["outer_exit_classification"])
        self.assertIsNone(observation["child_terminal_status"])
        self.assertTrue(observation["recovery_required"])

    def test_streaming_capture_retains_only_the_declared_prefix(self) -> None:
        from latent_triz.a0x_ccp_executor import _StreamingCapture

        capture = _StreamingCapture(3)
        payload = b"abcdef"
        capture.drain(io.BytesIO(payload))
        self.assertEqual(6, capture.length)
        self.assertEqual(b"abc", capture.prefix)
        self.assertEqual(_sha(payload), capture.sha256)
