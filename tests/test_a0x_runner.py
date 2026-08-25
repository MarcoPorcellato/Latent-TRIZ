"""Public A0X runner tests: only the guarded API may reach a lifecycle."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest


_RUNTIME_IMAGES = {
    "python311": "ghcr.io/marcoporcellato/latent-triz-verify@sha256:25de19baba5938c80de18c930342ccdcdf3c6759051196c3c713bd3e434d2f0e",
    "python312": "ghcr.io/marcoporcellato/latent-triz-verify@sha256:e984457d591121c52517027f49bb55371f68075caace763b8859db136e434dd0",
}


def _canonical_receipt_id(receipt: dict[str, object]) -> str:
    raw = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _runtime_receipt(*, runtime_id: str, configuration_digest: str, check_ids: list[str], source_head: str, generation: int) -> dict[str, object]:
    image = _RUNTIME_IMAGES[runtime_id]
    image_digest = image.rsplit("@", 1)[1]
    receipt = {
        "schema_version": "1.0",
        "producer": {"name": "commit-ci-preflight", "version": "0.1.0"},
        "repository": {"repository": "MarcoPorcellato/Latent-TRIZ", "commit_sha": source_head, "dirty": False},
        "run": {"run_id": f"matrix-{runtime_id}", "generation": generation, "started_at_utc": "2026-08-24T12:00:00Z", "finished_at_utc": "2026-08-24T12:00:01Z"},
        "platform": {"host_os": "macos", "host_arch": "aarch64", "runtime_kind": "docker_compatible", "runtime_version": "synthetic", "image_reference": image, "image_digest": image_digest},
        "configuration_digest": configuration_digest,
        "checks": [{"id": check_id, "required": True, "argv": ["python", "scripts/repository_check.py" if check_id.startswith("repository-check-") else "scripts/schema_cross_validate.py"], "working_directory": ".", "status": "PASS", "exit_code": 0, "duration_ms": 1, "timed_out": False, "cancelled": False, "output_digest": "sha256:" + "c" * 64, "incomplete_reason": None} for check_id in check_ids],
        "overall_status": "PASS",
        "incomplete_reason": None,
        "redaction_policy_version": "1.0",
    }
    return {"receipt_id": _canonical_receipt_id(receipt), "receipt": receipt}


def _resign_matrix_receipt(envelope: dict[str, object]) -> None:
    for group in envelope["receipt"]["runtime_receipts"]:
        nested = group["receipt"]
        nested["receipt_id"] = _canonical_receipt_id(nested["receipt"])
    envelope["receipt_id"] = _canonical_receipt_id(envelope["receipt"])


def matrix_receipt_envelope(*, source_head: str = "a" * 40, generation: int = 7) -> dict[str, object]:
    """A complete synthetic MatrixReceiptEnvelopeV2, never a CCP result."""
    contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
    binding = contract["ccp"]["matrix_plan_binding"]
    receipt = {
        "schema_version": "2.0",
        "producer": {"name": "commit-ci-preflight", "version": "0.1.0"},
        "repository": {"repository": "MarcoPorcellato/Latent-TRIZ", "commit_sha": source_head, "dirty": False},
        "run": {"run_id": "matrix-synthetic", "generation": generation, "started_at_utc": "2026-08-24T12:00:00Z", "finished_at_utc": "2026-08-24T12:00:02Z"},
        "configuration_digest": binding["outer_digest"],
        "runtime_receipts": [
            {"runtime_id": "python311", "receipt": _runtime_receipt(runtime_id="python311", configuration_digest=binding["python311_digest"], check_ids=["repository-check-py311", "schema-cross-validate-py311"], source_head=source_head, generation=generation)},
            {"runtime_id": "python312", "receipt": _runtime_receipt(runtime_id="python312", configuration_digest=binding["python312_digest"], check_ids=["repository-check-py312", "schema-cross-validate-py312"], source_head=source_head, generation=generation)},
        ],
        "overall_status": "PASS",
        "incomplete_reason": None,
        "redaction_policy_version": "1.0",
    }
    return {"receipt_id": _canonical_receipt_id(receipt), "receipt": receipt}


def matrix_plan_envelope() -> dict[str, object]:
    contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
    binding = contract["ccp"]["matrix_plan_binding"]
    check_sets = {
        "python311": ["repository-check-py311", "schema-cross-validate-py311"],
        "python312": ["repository-check-py312", "schema-cross-validate-py312"],
    }
    runtimes = []
    for runtime_id, check_ids in check_sets.items():
        runtimes.append({
            "id": runtime_id,
            "configuration_digest": binding[f"{runtime_id}_digest"],
            "runtime": {"kind": "docker_compatible", "image": _RUNTIME_IMAGES[runtime_id], "cpu_count": 1, "memory_mib": 1024, "pids_limit": 256, "network": False},
            "checks": [{"id": check_id, "required": True, "argv": ["python", "scripts/repository_check.py" if check_id.startswith("repository-check-") else "scripts/schema_cross_validate.py"], "working_directory": ".", "timeout_seconds": 300, "depends_on": [], "artifacts": []} for check_id in check_ids],
        })
    return {"plan_digest": binding["outer_digest"], "plan": {"schema_version": "2.0", "project": "MarcoPorcellato/Latent-TRIZ", "receipt": {"output": ".ccp/receipt.json", "freshness_seconds": 3600}, "environment": {"inherit": [], "fixed": [], "runtime_internal": [], "remote_secret_only": []}, "caches": [], "runtimes": runtimes}}


def v1_doctor_envelope(*, omit_capabilities: bool = False) -> dict[str, object]:
    """Mirror RuntimeProbe exactly; only its two serde-optional fields may omit."""
    value: dict[str, object] = {
        "runtime": "docker_compatible",
        "flavor": "orb_stack",
        "server_version": "synthetic-1.0",
        "operating_system": "OrbStack",
        "os_type": "linux",
        "containment": "process_group",
        "graceful_stop": "process_group_signal",
    }
    if not omit_capabilities:
        value.update(memory_limit_supported=True, swap_limit_supported=True)
    return value


def v1_dry_run_envelope(*, runtime_id: str = "python311") -> dict[str, object]:
    contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
    repository = "/private/tmp/a0x-synthetic-repository"
    binding = contract["ccp"]["matrix_plan_binding"]
    check_ids = {
        "python311": ("repository-check-py311", "schema-cross-validate-py311"),
        "python312": ("repository-check-py312", "schema-cross-validate-py312"),
    }[runtime_id]
    return {
        "schema_version": "1.0",
        "plan_digest": binding[f"{runtime_id}_digest"],
        "runtime": "docker_compatible",
        "program": "docker",
        "checks": [
            {
                "id": check_id,
                "program": "docker",
                "argv": [
                    "run", "--rm", "--init", "--read-only", "--network", "none",
                    "--cpus", "1", "--memory", "1024m", "--pids-limit", "256",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
                    "--env", "TMPDIR=/tmp", "--mount",
                    f"type=bind,src={repository},dst=/workspace,readonly",
                    "--workdir", "/workspace", _RUNTIME_IMAGES[runtime_id],
                    "python", "scripts/repository_check.py" if check_id.startswith("repository-check") else "scripts/schema_cross_validate.py",
                ],
                "depends_on": [],
            }
            for check_id in check_ids
        ],
        "workspace": {
            "schema_version": "1.0",
            "repository": repository,
            "run_root": "/private/tmp/a0x-synthetic-cache/workspaces/" + binding[f"{runtime_id}_digest"].removeprefix("sha256:"),
            "mounts": [{
                "source": repository,
                "target": "/workspace",
                "access": "read_only",
                "purpose": "repository",
            }],
        },
        "workspace_mount_policy": "explicit_bindings",
        "executed": False,
    }


def matrix_doctor_envelope() -> dict[str, object]:
    contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
    binding = contract["ccp"]["matrix_plan_binding"]
    return {
        "schema_version": "2.0",
        "plan_digest": binding["outer_digest"],
        "runtimes": [
            {
                "runtime_id": runtime_id,
                "configuration_digest": binding[f"{runtime_id}_digest"],
                "probe": v1_doctor_envelope(),
            }
            for runtime_id in ("python311", "python312")
        ],
    }


def matrix_dry_run_envelope() -> dict[str, object]:
    contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
    binding = contract["ccp"]["matrix_plan_binding"]
    repository = "/private/tmp/a0x-synthetic-repository"
    checks = {
        "python311": ("repository-check-py311", "schema-cross-validate-py311"),
        "python312": ("repository-check-py312", "schema-cross-validate-py312"),
    }
    runtimes = []
    for runtime_id in ("python311", "python312"):
        digest = binding[f"{runtime_id}_digest"]
        runtimes.append({
            "runtime_id": runtime_id,
            "configuration_digest": digest,
            "dry_run": v1_dry_run_envelope(runtime_id=runtime_id),
        })
    return {"schema_version": "2.0", "plan_digest": binding["outer_digest"], "runtimes": runtimes}


class A0XRunnerPublicSurfaceTests(unittest.TestCase):
    def test_single_matrix_config_owns_all_preflight_and_run_vectors(self) -> None:
        from latent_triz.a0x_runner import _ccp_argvs

        path = __import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json"
        contract = json.loads(path.read_text())
        config = ".commit-ci-preflight.toml"
        expected = (
            ("admission status --json", ("admission", "status", "--json")),
            ("resource status --json", ("resource", "status", "--json")),
            ("plan --json", ("plan", "--config", config, "--json")),
            ("doctor --json", ("doctor", "--config", config, "--json")),
            ("dry-run --json", ("dry-run", "--config", config, "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--json")),
            ("run --generation <authorized-u64> --json", ("run", "--config", config, "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--generation", "7", "--json")),
        )
        self.assertEqual(expected, _ccp_argvs(contract, generation=7))

    def test_matrix_doctor_and_dry_run_bind_both_runtime_envelopes(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, _validate_ccp_response

        contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        _validate_ccp_response("doctor --json", matrix_doctor_envelope(), contract["ccp"])
        _validate_ccp_response("dry-run --json", matrix_dry_run_envelope(), contract["ccp"])
        for command, baseline, mutate in (
            ("doctor --json", matrix_doctor_envelope(), lambda value: value["runtimes"].reverse()),
            ("doctor --json", matrix_doctor_envelope(), lambda value: value["runtimes"][0].__setitem__("configuration_digest", "sha256:" + "0" * 64)),
            ("dry-run --json", matrix_dry_run_envelope(), lambda value: value["runtimes"][1]["dry_run"].__setitem__("executed", True)),
            ("dry-run --json", matrix_dry_run_envelope(), lambda value: value["runtimes"].pop()),
        ):
            changed = copy.deepcopy(baseline)
            mutate(changed)
            with self.subTest(command=command), self.assertRaises(A0XRunnerError):
                _validate_ccp_response(command, changed, contract["ccp"])

    def test_matrix_doctor_rejects_invalid_nested_runtime_probe(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, _validate_ccp_response

        contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        baseline = matrix_doctor_envelope()
        baseline["runtimes"][0]["probe"] = v1_doctor_envelope(omit_capabilities=True)
        baseline["runtimes"][1]["probe"]["memory_limit_supported"] = False
        _validate_ccp_response("doctor --json", baseline, contract["ccp"])
        mutations = (
            lambda value: value.pop("server_version"),
            lambda value: value.__setitem__("unexpected", True),
            lambda value: value.__setitem__("runtime", "host"),
            lambda value: value.__setitem__("server_version", None),
            lambda value: value.__setitem__("os_type", "darwin"),
            lambda value: value.__setitem__("containment", "job_object"),
            lambda value: value.__setitem__("memory_limit_supported", "false"),
        )
        for mutate in mutations:
            changed = matrix_doctor_envelope()
            mutate(changed["runtimes"][0]["probe"])
            with self.subTest(changed=changed), self.assertRaises(A0XRunnerError):
                _validate_ccp_response("doctor --json", changed, contract["ccp"])

    def test_matrix_dry_run_rejects_invalid_nested_runtime_plan(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, _validate_ccp_response

        contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        _validate_ccp_response("dry-run --json", matrix_dry_run_envelope(), contract["ccp"])
        mutations = (
            lambda value: value.__setitem__("checks", []),
            lambda value: value["checks"][0].pop("depends_on"),
            lambda value: value["checks"][0].__setitem__("program", "sh"),
            lambda value: value["checks"][0].__setitem__("argv", []),
            lambda value: value.__setitem__("workspace", {}),
            lambda value: value["workspace"]["mounts"][0].__setitem__("access", "read_write"),
            lambda value: value["workspace"]["mounts"][0].__setitem__("purpose", "cache"),
            lambda value: value.__setitem__("workspace_mount_policy", "read_only"),
            lambda value: value["checks"][1]["argv"].__setitem__(-1, "scripts/repository_check.py"),
            lambda value: value["checks"][0]["argv"].__setitem__(-3, _RUNTIME_IMAGES["python312"]),
            lambda value: value["checks"][0]["argv"].__setitem__(value["checks"][0]["argv"].index("--memory") + 1, "256m"),
            lambda value: value["checks"][0]["argv"].__setitem__(value["checks"][0]["argv"].index("--pids-limit") + 1, "64"),
            lambda value: value["checks"][0]["argv"].__setitem__(-2, "python3"),
            lambda value: value["checks"][0]["argv"].insert(1, "--privileged"),
            lambda value: value["checks"][0]["argv"].__setitem__(value["checks"][0]["argv"].index("--network") + 1, "host"),
            lambda value: value["checks"][0]["argv"].__setitem__(slice(value["checks"][0]["argv"].index("--workdir"), value["checks"][0]["argv"].index("--workdir")), ["--mount", "type=bind,src=/private/tmp/extra,dst=/extra"]),
        )
        for mutate in mutations:
            changed = matrix_dry_run_envelope()
            mutate(changed["runtimes"][0]["dry_run"])
            with self.subTest(changed=changed), self.assertRaises(A0XRunnerError):
                _validate_ccp_response("dry-run --json", changed, contract["ccp"])

    def test_qualification_authorization_owns_positive_generation_and_execution_authorization_does_not(self) -> None:
        from latent_triz.a0x_contract import QUALIFICATION_AUTHORIZATION_PROFILE, canonical_commitment
        from latent_triz.a0x_runner import A0XRunnerError, validate_qualification_authorization

        contract_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json"
        raw = contract_path.read_bytes()
        contract = json.loads(raw)
        authorization = {
            "artifact_class": "a0x-qualification-authorization", "claim_ids": [],
            "commitment_profile": QUALIFICATION_AUTHORIZATION_PROFILE, "qualification_status": "authorized",
            "empirical": True, "evidence_eligible": False, "expert_validated": False, "scientific_status": "exploratory",
            "repository": "MarcoPorcellato/Latent-TRIZ", "source_head": "a" * 40,
            "material_contract_raw_sha256": hashlib.sha256(raw).hexdigest(),
            "ccp": {name: contract["ccp"][name] for name in ("path", "source_commit", "qualified_source_tree", "sha256", "version")},
            "generation": 7, "max_qualification_run_count": 1,
            "stop_boundary": "after_repository_qualification_receipt",
            "authorization_id": "synthetic-qualification",
        }
        self.assertEqual(7, validate_qualification_authorization(authorization, material_contract_raw=raw, source_head="a" * 40, contract=contract)["generation"])
        self.assertEqual(QUALIFICATION_AUTHORIZATION_PROFILE, canonical_commitment(authorization, QUALIFICATION_AUTHORIZATION_PROFILE).profile)
        authorization["generation"] = 0
        with self.assertRaises(A0XRunnerError):
            validate_qualification_authorization(authorization, material_contract_raw=raw, source_head="a" * 40, contract=contract)

    def test_per_pair_authorization_rejects_qualification_generation_and_run_limit(self) -> None:
        from latent_triz.a0x_contract import A0XContractError, EXECUTION_AUTHORIZATION_PROFILE, canonical_commitment
        from tests.a0x_test_support import authorization_documents, pair_binding

        _dossier, authorization, _chain = authorization_documents(pair_binding())
        authorization["generation"] = 7
        with self.assertRaises(A0XContractError):
            canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE)

    def test_repository_qualification_requires_authorized_generation_and_canonical_matrix_receipt(self) -> None:
        from latent_triz.a0x_runner import run_a0x_repository_qualification
        from pathlib import Path
        from tempfile import TemporaryDirectory

        contract_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json"
        raw = contract_path.read_bytes()
        contract = json.loads(raw)
        authorization = {
            "artifact_class": "a0x-qualification-authorization", "claim_ids": [], "commitment_profile": "a0x-qualification-authorization-json-v1", "qualification_status": "authorized", "empirical": True, "evidence_eligible": False, "expert_validated": False, "scientific_status": "exploratory", "repository": "MarcoPorcellato/Latent-TRIZ", "source_head": "a" * 40, "material_contract_raw_sha256": hashlib.sha256(raw).hexdigest(), "ccp": {name: contract["ccp"][name] for name in ("path", "source_commit", "qualified_source_tree", "sha256", "version")}, "generation": 7, "max_qualification_run_count": 1, "stop_boundary": "after_repository_qualification_receipt", "authorization_id": "synthetic-qualification",
        }
        test_case = self
        class FakeCcp:
            def __init__(self):
                self.calls = []
            def sha256(self, _path): return contract["ccp"]["sha256"]
            def review_dry_run(self, _trace): return True
            def execute(self, command):
                command = tuple(command)
                self.calls.append(command)
                expected = {
                    ("admission", "status", "--json"): b'{"active":false,"queue_count":0,"process_visibility_note":"No process visible in the local shell does not prove global inactivity.","queue_lock":{"acquired_at_unix_seconds":null,"heartbeat_at_unix_seconds":null,"kind":"queue_lock","lease_state":"not_applicable","owner_run_id":null,"state":"free"},"schema_version":"2.0","slot":{"acquired_at_unix_seconds":null,"heartbeat_at_unix_seconds":null,"kind":"slot_lock","lease_state":"not_applicable","owner_run_id":null,"state":"free"},"ticket_ids":[]}',
                    ("resource", "status", "--json"): b'{"available_percent":50,"capability":"supported_enforced","compressor_occupied_bytes":0,"consecutive_soft_samples":0,"decision":"admit","platform":"macos","policy_version":"macos-v4","reclaimable_uncompressed_bytes":1,"schema_version":"1.0","swap_total_bytes":1,"swap_used_bytes":0,"total_memory_bytes":1}',
                }
                if command in expected:
                    return 0, expected[command]
                if command == ("plan", "--config", ".commit-ci-preflight.toml", "--json"):
                    return 0, json.dumps(matrix_plan_envelope(), separators=(",", ":")).encode()
                if command == ("doctor", "--config", ".commit-ci-preflight.toml", "--json"):
                    return 0, json.dumps(matrix_doctor_envelope(), separators=(",", ":")).encode()
                if command == ("dry-run", "--config", ".commit-ci-preflight.toml", "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--json"):
                    return 0, json.dumps(matrix_dry_run_envelope(), separators=(",", ":")).encode()
                test_case.assertEqual(("run", "--config", ".commit-ci-preflight.toml", "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--generation", "7", "--json"), command)
                return 0, json.dumps(matrix_receipt_envelope(), sort_keys=True, separators=(",", ":")).encode()
        source = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".commit-ci-preflight.toml").write_bytes((source / ".commit-ci-preflight.toml").read_bytes())
            (root / ".commit-ci-policy-v2.toml").write_bytes((source / ".commit-ci-policy-v2.toml").read_bytes())
            authorization_path = root / "qualification-authorization.json"
            authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
            executor = FakeCcp()
            result = run_a0x_repository_qualification(
                material_contract_raw=raw, authorization_path=authorization_path,
                expected_authorization_raw_sha256=hashlib.sha256(authorization_path.read_bytes()).hexdigest(),
                qualification_claim_path=root / "qualification-claim.json",
                repository_root=root, source_head_probe=lambda: "a" * 40,
                executor=executor, source_head="a" * 40,
            )
            self.assertEqual(7, result["generation"])
            self.assertEqual("sha256:", result["receipt_id"][:7])
            self.assertTrue((root / "qualification-claim.json").is_file())
            self.assertEqual(6, len(executor.calls))
            before_second_use = list(executor.calls)
            with self.assertRaisesRegex(Exception, "claim already exists"):
                run_a0x_repository_qualification(
                    material_contract_raw=raw, authorization_path=authorization_path,
                    expected_authorization_raw_sha256=hashlib.sha256(authorization_path.read_bytes()).hexdigest(),
                    qualification_claim_path=root / "qualification-claim.json",
                    repository_root=root, source_head_probe=lambda: "a" * 40,
                    executor=executor, source_head="a" * 40,
                )
            self.assertEqual(before_second_use, executor.calls)

            class DriftAfterClaim(FakeCcp):
                def __init__(self):
                    super().__init__()
                    self.hash_calls = 0

                def sha256(self, _path):
                    self.hash_calls += 1
                    if self.hash_calls == 7:
                        return "0" * 64
                    return contract["ccp"]["sha256"]

            drift_executor = DriftAfterClaim()
            drift_claim = root / "qualification-drift-claim.json"
            with self.assertRaisesRegex(Exception, "hash drift"):
                run_a0x_repository_qualification(
                    material_contract_raw=raw, authorization_path=authorization_path,
                    expected_authorization_raw_sha256=hashlib.sha256(authorization_path.read_bytes()).hexdigest(),
                    qualification_claim_path=drift_claim,
                    repository_root=root, source_head_probe=lambda: "a" * 40,
                    executor=drift_executor, source_head="a" * 40,
                )
            self.assertTrue(drift_claim.is_file())
            self.assertEqual(5, len(drift_executor.calls))

    def test_every_frozen_ccp_argument_is_contract_bound(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, _validate_material_contract

        path = __import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json"
        baseline = json.loads(path.read_text())
        _validate_material_contract(baseline)
        for command_index, command in enumerate(baseline["ccp"]["commands"]):
            for argument_index, _argument in enumerate(command):
                changed = copy.deepcopy(baseline)
                changed["ccp"]["commands"][command_index][argument_index] = "__mutated__"
                with self.subTest(command=command_index, argument=argument_index), self.assertRaises(A0XRunnerError):
                    _validate_material_contract(changed)

    def test_material_contract_rejects_each_offline_and_stop_boundary_mutation(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, _validate_material_contract

        path = __import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json"
        baseline = json.loads(path.read_text())
        mutations = (
            lambda value: value["offline"].__setitem__("network", True),
            lambda value: value["offline"].__setitem__("generation", True),
            lambda value: value["offline"].__setitem__("local_cpu_float32", False),
            lambda value: value["stop_boundaries"].__setitem__(0, "after_model_load"),
            lambda value: value["stop_boundaries"].pop(),
        )
        for mutate in mutations:
            changed = copy.deepcopy(baseline)
            mutate(changed)
            with self.assertRaises(A0XRunnerError):
                _validate_material_contract(changed)

    def test_matrix_receipt_requires_complete_canonical_envelope_source_generation_and_runtime_digests(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, validate_matrix_qualification_receipt

        contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        envelope = matrix_receipt_envelope()
        raw = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        validated = validate_matrix_qualification_receipt(raw, contract=contract, source_head="a" * 40, generation=7)
        self.assertEqual(envelope["receipt_id"], validated["receipt_id"])

        for mutation in (
            lambda value: value.__setitem__("receipt_id", "sha256:" + "0" * 64),
            lambda value: value["receipt"]["run"].__setitem__("generation", 0),
            lambda value: value["receipt"]["repository"].__setitem__("commit_sha", "b" * 40),
            lambda value: value["receipt"]["runtime_receipts"][0]["receipt"]["receipt"].__setitem__("configuration_digest", "sha256:" + "0" * 64),
            lambda value: value["receipt"]["runtime_receipts"][0]["receipt"]["receipt"]["run"].__setitem__("started_at_utc", 0),
            lambda value: value.__setitem__("status", "pass"),
        ):
            changed = copy.deepcopy(envelope)
            mutation(changed)
            with self.assertRaises(A0XRunnerError):
                validate_matrix_qualification_receipt(json.dumps(changed, sort_keys=True, separators=(",", ":")).encode(), contract=contract, source_head="a" * 40, generation=7)

        for mutate in (
            lambda value: value["receipt"]["runtime_receipts"][0]["receipt"]["receipt"]["platform"].__setitem__("image_reference", _RUNTIME_IMAGES["python312"]),
            lambda value: value["receipt"]["runtime_receipts"][0]["receipt"]["receipt"]["checks"][1].__setitem__("argv", ["python", "scripts/repository_check.py"]),
            lambda value: value["receipt"]["runtime_receipts"][1]["receipt"]["receipt"]["checks"][0].__setitem__("working_directory", "subdir"),
        ):
            changed = matrix_receipt_envelope()
            mutate(changed)
            _resign_matrix_receipt(changed)
            with self.assertRaises(A0XRunnerError):
                validate_matrix_qualification_receipt(json.dumps(changed, sort_keys=True, separators=(",", ":")).encode(), contract=contract, source_head="a" * 40, generation=7)

    def test_matrix_plan_rejects_shallow_or_declared_digest_substitution(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, _validate_ccp_response

        contract = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        shallow = {"plan_digest": contract["ccp"]["matrix_plan_binding"]["outer_digest"], "plan": {"schema_version": "2.0", "project": "MarcoPorcellato/Latent-TRIZ", "receipt": {}, "environment": {}, "caches": [], "runtimes": [{"id": "python311", "configuration_digest": contract["ccp"]["matrix_plan_binding"]["python311_digest"], "runtime": {}, "checks": []}, {"id": "python312", "configuration_digest": contract["ccp"]["matrix_plan_binding"]["python312_digest"], "runtime": {}, "checks": []}]}}
        with self.assertRaisesRegex(A0XRunnerError, "plan"):
            _validate_ccp_response("plan --json", shallow, contract["ccp"])
        wrong_check = matrix_plan_envelope()
        wrong_check["plan"]["runtimes"][0]["checks"][1]["argv"] = ["python", "scripts/repository_check.py"]
        with self.assertRaisesRegex(A0XRunnerError, "check"):
            _validate_ccp_response("plan --json", wrong_check, contract["ccp"])
        for mutate in (
            lambda value: value["plan"]["runtimes"][0]["runtime"].__setitem__("image", _RUNTIME_IMAGES["python312"]),
            lambda value: value["plan"]["runtimes"][0]["runtime"].__setitem__("memory_mib", 256),
            lambda value: value["plan"]["runtimes"][1]["runtime"].__setitem__("pids_limit", 64),
        ):
            changed = matrix_plan_envelope()
            mutate(changed)
            with self.assertRaises(A0XRunnerError):
                _validate_ccp_response("plan --json", changed, contract["ccp"])
    def test_claim_free_pair_runner_is_not_public(self) -> None:
        import latent_triz.a0x_runner as runner
        self.assertNotIn("run_a0x_pair", runner.__all__)
        self.assertFalse(hasattr(runner, "run_a0x_pair"))

    def test_claim_rejects_incomplete_payload_before_writing(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from latent_triz.a0x_runner import A0XRunnerError, reserve_attempt_claim
        with TemporaryDirectory() as directory:
            claim = Path(directory) / "claim.json"
            with self.assertRaisesRegex(A0XRunnerError, "invalid"):
                reserve_attempt_claim(claim, {"attempt_id": "incomplete"})
            self.assertFalse(claim.exists())

    def test_matrix_configuration_bindings_validate_without_a_second_probe_file(self) -> None:
        from pathlib import Path
        from latent_triz.a0x_runner import _validate_policy_binding
        import json
        root = Path(__file__).resolve().parents[1]
        contract = json.loads((root / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        _validate_policy_binding(root, contract)

    def test_matrix_configuration_drift_is_fail_closed(self) -> None:
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from latent_triz.a0x_runner import _validate_policy_binding
        source = Path(__file__).resolve().parents[1]
        contract = json.loads((source / "experiments/a0x-six-model/material-execution-contract.json").read_text())
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (".commit-ci-preflight.toml", ".commit-ci-policy-v2.toml"):
                (root / name).write_bytes((source / name).read_bytes())
            _validate_policy_binding(root, contract)
            (root / ".commit-ci-preflight.toml").write_bytes(b"drift")
            from latent_triz.a0x_runner import A0XRunnerError
            with self.assertRaisesRegex(A0XRunnerError, "drifted"):
                _validate_policy_binding(root, contract)
