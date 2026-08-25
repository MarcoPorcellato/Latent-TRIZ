"""The material entrypoint has no selectable execution surface."""
from __future__ import annotations

import unittest
import hashlib
from contextlib import redirect_stderr
from io import StringIO
import json
import os
import threading
from pathlib import Path
from tempfile import TemporaryDirectory


def _guarded_fixture(root: Path, *, leg_name: str = "a0") -> dict[str, object]:
    from latent_triz.a0x_contract import Leg
    from tests.a0x_test_support import authorization_documents, pair_binding
    from tests.test_a0x_runner import matrix_receipt_envelope

    repository = Path(__file__).resolve().parents[1]
    raw = (repository / "experiments/a0x-six-model/material-execution-contract.json").read_bytes()
    contract = json.loads(raw)
    leg = Leg(leg_name)
    pair = pair_binding(leg)
    dossier, authorization, _chain = authorization_documents(pair)
    qualification = json.dumps(matrix_receipt_envelope(), sort_keys=True, separators=(",", ":")).encode()
    material_contract_raw_sha256 = hashlib.sha256(raw).hexdigest()
    dossier["material_contract_raw_sha256"] = material_contract_raw_sha256
    authorization.update({
        "material_contract_raw_sha256": material_contract_raw_sha256,
        "source_head": "a" * 40,
        "qualification_receipt_raw_sha256": hashlib.sha256(qualification).hexdigest(),
        "ccp": {name: contract["ccp"][name] for name in ("path", "source_commit", "qualified_source_tree", "sha256", "version")},
    })
    from latent_triz.a0x_contract import APPROVAL_DOSSIER_PROFILE, canonical_commitment
    authorization["approved_dossier_commitment"] = canonical_commitment(
        dossier, APPROVAL_DOSSIER_PROFILE,
    ).as_mapping()
    (root / ".commit-ci-preflight.toml").write_bytes((repository / ".commit-ci-preflight.toml").read_bytes())
    (root / ".commit-ci-policy-v2.toml").write_bytes((repository / ".commit-ci-policy-v2.toml").read_bytes())
    dossier_path, authorization_path = root / "dossier.json", root / "authorization.json"
    dossier_path.write_text(json.dumps(dossier), encoding="utf-8")
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    return {
        "raw": raw, "contract": contract, "pair": pair, "dossier": dossier,
        "authorization": authorization, "qualification": qualification,
        "dossier_path": dossier_path, "authorization_path": authorization_path,
        "claim_path": root / "claim.json",
    }


class _SyntheticCcp:
    def __init__(self, fixture: dict[str, object], *, review_hook=None, review_barrier=None, drift_hash_at: int | None = None, guard_exit: int = 0):
        self.fixture = fixture
        self.review_hook = review_hook
        self.review_barrier = review_barrier
        self.drift_hash_at = drift_hash_at
        self.guard_exit = guard_exit
        self.hash_calls = 0
        self.guard_calls = 0
        self.trace: list[str] = []
        self._guard_lock = threading.Lock()

    def sha256(self, _path):
        self.hash_calls += 1
        self.trace.append("hash")
        if self.drift_hash_at == self.hash_calls:
            return "0" * 64
        return self.fixture["contract"]["ccp"]["sha256"]

    def review_dry_run(self, _trace):
        self.trace.append("review")
        if self.review_hook is not None:
            self.review_hook()
        if self.review_barrier is not None:
            self.review_barrier.wait(timeout=5)
        return True

    def execute(self, command):
        from tests.test_a0x_runner import matrix_doctor_envelope, matrix_dry_run_envelope, matrix_plan_envelope

        argv = tuple(command)
        labels = {
            ("admission", "status", "--json"): "admission status --json",
            ("resource", "status", "--json"): "resource status --json",
            ("plan", "--config", ".commit-ci-preflight.toml", "--json"): "plan --json",
            ("doctor", "--config", ".commit-ci-preflight.toml", "--json"): "doctor --json",
            ("dry-run", "--config", ".commit-ci-preflight.toml", "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--json"): "dry-run --json",
        }
        command = labels.get(argv)
        if command is None:
            raise AssertionError(f"unexpected synthetic argv: {argv}")
        self.trace.append(command)
        if command == "admission status --json":
            value = {"active": False, "queue_count": 0, "process_visibility_note": "No process visible in the local shell does not prove global inactivity.", "queue_lock": {"acquired_at_unix_seconds": None, "heartbeat_at_unix_seconds": None, "kind": "queue_lock", "lease_state": "not_applicable", "owner_run_id": None, "state": "free"}, "schema_version": "2.0", "slot": {"acquired_at_unix_seconds": None, "heartbeat_at_unix_seconds": None, "kind": "slot_lock", "lease_state": "not_applicable", "owner_run_id": None, "state": "free"}, "ticket_ids": []}
        elif command == "resource status --json":
            value = {"available_percent": 50, "capability": "supported_enforced", "compressor_occupied_bytes": 0, "consecutive_soft_samples": 0, "decision": "admit", "platform": "macos", "policy_version": "macos-v4", "reclaimable_uncompressed_bytes": 1, "schema_version": "1.0", "swap_total_bytes": 1, "swap_used_bytes": 0, "total_memory_bytes": 1}
        elif command == "plan --json":
            value = matrix_plan_envelope()
        elif command == "doctor --json":
            value = matrix_doctor_envelope()
        elif command == "dry-run --json":
            value = matrix_dry_run_envelope()
        else:
            raise AssertionError(f"unexpected synthetic command: {command}")
        return 0, json.dumps(value, separators=(",", ":")).encode()

    def guard_exec(self, argv_commitment, callback):
        with self._guard_lock:
            self.guard_calls += 1
        self.trace.append("guard-enter")
        if argv_commitment != self.fixture["authorization"]["guard_exec_argv_commitment"]:
            raise AssertionError("guard commitment differs")
        child = None
        if self.guard_exit == 0:
            self.in_guard = True
            try:
                child = callback()
            finally:
                self.in_guard = False
        self.trace.append("guard-exit")
        return self.guard_exit, b"synthetic-child-output", child


def _dependencies(root: Path, events: list[str], *, fail_stage: str | None = None, interrupt_stage: str | None = None, captured_preflight: list[dict[str, object]] | None = None):
    from latent_triz.a0x_runner import A0XRunnerDependencies

    def stage(name: str, value=None):
        events.append(name)
        if name == interrupt_stage:
            raise KeyboardInterrupt(name)
        if name == fail_stage:
            raise RuntimeError(name)
        return object() if value is None else value

    def static_preflight(context):
        stage("static_preflight")
        if captured_preflight is not None:
            captured_preflight.append({
                "ccp_observation_path": "pre-run-observation.json",
                "ccp_observation_raw_sha256": context["ccp_observation_raw_sha256"],
            })

    def failure_sealer(name, _error, _pair, _chain):
        events.append("failure_sealer")
        package = root / "failed-package.json"
        package.write_text(json.dumps({"status": "failed", "sealed_stage": name}), encoding="utf-8")
        return {"status": "failed", "sealed_stage": name, "package_path": str(package)}

    return A0XRunnerDependencies(
        static_preflight=static_preflight,
        tokenizer_factory=lambda: stage("tokenizer_construction"),
        model_factory=lambda _tokenizer: stage("model_construction"),
        activation=lambda model: stage("activation", model),
        activation_sealer=lambda activation: stage("activation_sealing", activation),
        target_capability_factory=lambda activation: stage("sealed_target_capability", activation),
        analysis=lambda target: stage("frozen_analysis", target),
        package_builder=lambda _analysis: stage("terminal_package", root / "package"),
        package_verifier=lambda _package: stage("independent_package_verification", None),
        protected_tree_postflight=lambda _package: stage("protected_tree_postflight", None),
        failure_sealer=failure_sealer,
        release_model=lambda _model: stage("model_release", None),
    )


def _run_fixture(root: Path, fixture: dict[str, object], executor: _SyntheticCcp, dependencies, **overrides):
    from latent_triz.a0x_runner import run_a0x_guarded_pair

    arguments = {
        "root": root,
        "dossier_path": fixture["dossier_path"],
        "authorization_path": fixture["authorization_path"],
        "material_contract_raw": fixture["raw"],
        "executor": executor,
        "source_head": "a" * 40,
        "dependencies": dependencies,
        "attempt_claim_path": fixture["claim_path"],
        "source_head_probe": lambda: "a" * 40,
        "qualification_receipt_probe": lambda: fixture["qualification"],
    }
    arguments.update(overrides)
    return run_a0x_guarded_pair(**arguments)


class A0XMaterialEntrypointTests(unittest.TestCase):
    def test_mismatched_dossier_material_hash_refuses_before_ccp(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            fixture["dossier"]["material_contract_raw_sha256"] = "0" * 64
            Path(fixture["dossier_path"]).write_text(json.dumps(fixture["dossier"]), encoding="utf-8")
            executor = _SyntheticCcp(fixture)
            with self.assertRaisesRegex(A0XRunnerError, "one raw hash"):
                _run_fixture(root, fixture, executor, _dependencies(root, []))
            self.assertEqual(0, executor.guard_calls)

    def test_guarded_dispatch_preserves_explicit_a0_and_r1_pair_identity(self) -> None:
        for leg_name in ("a0", "r1"):
            with self.subTest(leg=leg_name), TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = _guarded_fixture(root, leg_name=leg_name)
                executor = _SyntheticCcp(fixture)
                result = _run_fixture(root, fixture, executor, _dependencies(root, executor.trace))
                self.assertEqual("completed", result["status"])
                self.assertEqual(leg_name, result["pair_binding"]["leg"])
                self.assertEqual(1, executor.guard_calls)
                self.assertLess(executor.trace.index("guard-enter"), executor.trace.index("static_preflight"))
                self.assertLess(executor.trace.index("static_preflight"), executor.trace.index("guard-exit"))
                run_record = result["ccp_observation"]["run_record"]
                self.assertEqual(fixture["authorization"]["guard_exec_argv_commitment"], run_record["state"]["argv_commitment"])
                self.assertEqual("completed", run_record["state"]["guard_exit_classification"])
                self.assertEqual("completed", run_record["state"]["child_exit_classification"])
                self.assertEqual("completed", run_record["state"]["lifecycle_status"])
                self.assertEqual([str(root / "package")], run_record["state"]["terminal_links"])

    def test_live_source_head_probe_is_mandatory_before_a_claim(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            executor = _SyntheticCcp(fixture)
            with self.assertRaisesRegex(A0XRunnerError, "source HEAD probe"):
                _run_fixture(root, fixture, executor, _dependencies(root, []), source_head_probe=None)
            self.assertFalse(Path(fixture["claim_path"]).exists())
            self.assertEqual(0, executor.guard_calls)

    def test_private_lifecycle_refuses_direct_invocation_outside_guard_exec(self) -> None:
        from latent_triz.a0x_execution import validate_authorization_chain
        from latent_triz.a0x_runner import A0XRunnerError, _authorization_chain, _run_injected_lifecycle

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            dossier = fixture["dossier"]
            authorization = fixture["authorization"]
            chain = validate_authorization_chain(_authorization_chain(dossier, authorization))
            with self.assertRaisesRegex(A0XRunnerError, "guard exec"):
                _run_injected_lifecycle(
                    pair=__import__("latent_triz.a0x_contract", fromlist=["PairBinding"]).PairBinding.from_mapping(fixture["pair"]),
                    chain=chain,
                    dependencies=_dependencies(root, []),
                    attempt_claim_path=root / "direct-claim.json",
                    dossier=dossier,
                    authorization=authorization,
                    pre_run_context={"ccp_observation_path": "pre-run-observation.json", "ccp_observation_raw_sha256": "0" * 64},
                )
            self.assertFalse((root / "direct-claim.json").exists())

    def test_every_lifecycle_stage_is_the_first_sealed_failure_including_model_release(self) -> None:
        stages = (
            "static_preflight", "tokenizer_construction", "model_construction",
            "activation", "activation_sealing", "sealed_target_capability",
            "frozen_analysis", "terminal_package", "independent_package_verification",
            "protected_tree_postflight", "model_release",
        )
        for failed_stage in stages:
            with self.subTest(stage=failed_stage), TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = _guarded_fixture(root)
                events: list[str] = []
                executor = _SyntheticCcp(fixture)
                result = _run_fixture(
                    root, fixture, executor,
                    _dependencies(root, events, fail_stage=failed_stage),
                )
                self.assertEqual("failed", result["status"])
                self.assertEqual(failed_stage, result["sealed_stage"])
                self.assertEqual(1, events.count("failure_sealer"))
                self.assertEqual(1, executor.guard_calls)
                self.assertTrue(Path(fixture["claim_path"]).is_file())

    def test_keyboard_interrupt_is_sealed_consumes_claim_and_cannot_retry(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            events: list[str] = []
            executor = _SyntheticCcp(fixture)
            dependencies = _dependencies(root, events, interrupt_stage="activation")
            with self.assertRaises(KeyboardInterrupt):
                _run_fixture(root, fixture, executor, dependencies)
            self.assertEqual(1, events.count("failure_sealer"))
            self.assertTrue((root / "failed-package.json").is_file())
            self.assertTrue(Path(fixture["claim_path"]).is_file())
            with self.assertRaisesRegex(A0XRunnerError, "already exists"):
                _run_fixture(root, fixture, executor, dependencies)
            self.assertEqual(1, executor.guard_calls)

    def test_abrupt_guard_terminal_classes_consume_claim_without_fabricating_a_package_or_retry(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError

        classifications = {124: "timeout", 130: "cancelled", 70: "cleanup_or_internal", 9: "child_failed"}
        for exit_code, classification in classifications.items():
            with self.subTest(exit_code=exit_code), TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = _guarded_fixture(root)
                executor = _SyntheticCcp(fixture, guard_exit=exit_code)
                with self.assertRaisesRegex(A0XRunnerError, classification):
                    _run_fixture(root, fixture, executor, _dependencies(root, []))
                claim = Path(fixture["claim_path"])
                self.assertTrue(claim.is_file())
                self.assertFalse((root / "package").exists())
                recovery = json.loads((root / "guard-recovery-observation.json").read_text(encoding="utf-8"))
                self.assertEqual(classification, recovery["guard_exit_classification"])
                self.assertFalse(recovery["retry_permitted"])
                with self.assertRaisesRegex(A0XRunnerError, "already exists"):
                    _run_fixture(root, fixture, executor, _dependencies(root, []))
                self.assertEqual(1, executor.guard_calls)

    def test_concurrent_durable_claim_race_has_exactly_one_guard_winner(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            barrier = threading.Barrier(2)
            executor = _SyntheticCcp(fixture, review_barrier=barrier)
            outcomes: list[tuple[str, object]] = []
            lock = threading.Lock()

            def compete() -> None:
                try:
                    value = _run_fixture(root, fixture, executor, _dependencies(root, []))
                except BaseException as error:
                    value = error
                    kind = "error"
                else:
                    kind = "result"
                with lock:
                    outcomes.append((kind, value))

            threads = [threading.Thread(target=compete), threading.Thread(target=compete)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(["error", "result"], sorted(kind for kind, _value in outcomes))
            self.assertEqual(1, executor.guard_calls)
            claim = Path(fixture["claim_path"])
            self.assertTrue(claim.is_file())
            immutable = claim.read_bytes()
            self.assertGreater(len(immutable), 0)
            self.assertEqual(immutable, claim.read_bytes())

    def test_post_review_drift_refuses_before_guard_for_every_hash_bound_input(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError

        drift_cases = ("authorization", "source_head", "matrix_config", "matrix_policy", "qualification_receipt", "output_file", "output_symlink")
        for drift in drift_cases:
            with self.subTest(drift=drift), TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = _guarded_fixture(root)

                def review_hook() -> None:
                    if drift == "authorization":
                        Path(fixture["authorization_path"]).write_bytes(Path(fixture["authorization_path"]).read_bytes() + b"\n")
                    elif drift == "matrix_config":
                        (root / ".commit-ci-preflight.toml").write_bytes(b"drift")
                    elif drift == "matrix_policy":
                        (root / ".commit-ci-policy-v2.toml").write_bytes(b"drift")
                    elif drift in {"output_file", "output_symlink"}:
                        output = root / str(fixture["pair"]["output_path"])
                        output.parent.mkdir(parents=True, exist_ok=True)
                        if drift == "output_file":
                            output.write_bytes(b"occupied")
                        else:
                            os.symlink(root / "elsewhere", output)

                executor = _SyntheticCcp(fixture, review_hook=review_hook)
                overrides = {}
                if drift == "source_head":
                    overrides["source_head_probe"] = lambda: "b" * 40
                if drift == "qualification_receipt":
                    overrides["qualification_receipt_probe"] = lambda: fixture["qualification"] + b"\n"
                with self.assertRaises(A0XRunnerError):
                    _run_fixture(root, fixture, executor, _dependencies(root, []), **overrides)
                self.assertEqual(0, executor.guard_calls)

    def test_executable_drift_immediately_before_guard_consumes_claim_without_child(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            executor = _SyntheticCcp(fixture, drift_hash_at=6)
            with self.assertRaisesRegex(A0XRunnerError, "hash drift"):
                _run_fixture(root, fixture, executor, _dependencies(root, []))
            self.assertEqual(0, executor.guard_calls)
            self.assertTrue(Path(fixture["claim_path"]).is_file())

    def test_pre_guard_bytes_bind_child_preflight_and_task9_final_observation(self) -> None:
        from dataclasses import replace
        from latent_triz.a0x_contract import PairBinding
        from latent_triz.a0x_execution import validate_authorization_chain
        from latent_triz.a0x_preflight import A0XModelCard, RuntimeFile, _verify_ccp_observation, verify_static_preflight
        from latent_triz.a0x_runner import _authorization_chain
        from latent_triz.a0x_verify import A0XVerificationError, _ccp_preflight_link

        with TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = _guarded_fixture(root)
            preflight_receipts: list[dict[str, object]] = []
            dependencies = _dependencies(root, [], captured_preflight=preflight_receipts)
            pair = PairBinding.from_mapping(fixture["pair"])
            chain = validate_authorization_chain(_authorization_chain(fixture["dossier"], fixture["authorization"]))
            snapshot = root / "synthetic-snapshot"
            snapshot.mkdir()
            config = {
                "model_type": "gpt2", "architectures": ["GPT2LMHeadModel"], "n_layer": 12,
                "n_embd": 1024, "vocab_size": 50257, "n_positions": 1024,
            }
            config_raw = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
            (snapshot / "config.json").write_bytes(config_raw)
            card = A0XModelCard(
                model_key=pair.model_key, model_id=pair.model_id, revision=pair.revision,
                license_id="MIT", architecture="GPT2LMHeadModel", model_type="gpt2",
                runtime_root="synthetic", runtime_files=(RuntimeFile("config.json", len(config_raw), hashlib.sha256(config_raw).hexdigest()),),
                num_hidden_layers=12, hidden_size=1024, vocab_size=50257, effective_context=1024,
                final_transformer_block_tuple_index=12, tokenizer_metadata_class=None,
                expected_runtime_tokenizer_class="GPT2TokenizerFast", fast_offsets_required=True,
                pad_side=None, trust_remote_code=False, source_receipt_path="synthetic", source_receipt_sha256="0" * 64,
                official_audit_path="synthetic", official_audit_sha256="0" * 64,
                config_fact_provenance={}, tokenizer_fact_provenance={}, card_path="synthetic",
            )

            def production_preflight(context) -> None:
                self.assertEqual("pre-run-observation.json", context["ccp_observation_path"])
                raw = (root / context["ccp_observation_path"]).read_bytes()
                observation = json.loads(raw)
                receipt = verify_static_preflight(
                    card=card, snapshot_root=snapshot, expected_origin="a" * 40, observed_origin="a" * 40,
                    output_dir=root / "real-static-preflight-output", environment={"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                    pair_binding=pair, protected_trees=((root / "protected-a", {}), (root / "protected-b", {})),
                    protected_tree_verifier=lambda *_args, **_kwargs: None, dossier_path=fixture["dossier_path"],
                    expected_dossier_raw_sha256=hashlib.sha256(Path(fixture["dossier_path"]).read_bytes()).hexdigest(),
                    authorization_path=fixture["authorization_path"],
                    expected_authorization_raw_sha256=hashlib.sha256(Path(fixture["authorization_path"]).read_bytes()).hexdigest(),
                    ccp_observation=observation, authorization_chain=chain,
                    material_contract_raw_sha256=hashlib.sha256(fixture["raw"]).hexdigest(),
                    ccp_observation_path=context["ccp_observation_path"], ccp_observation_raw_sha256=context["ccp_observation_raw_sha256"],
                )
                preflight_receipts.append(receipt)

            result = _run_fixture(
                root, fixture, _SyntheticCcp(fixture),
                replace(dependencies, static_preflight=production_preflight),
            )
            self.assertEqual("completed", result["status"])
            observation = result["ccp_observation"]
            self.assertEqual(
                observation,
                json.loads(Path(result["ccp_observation_path"]).read_text(encoding="utf-8")),
            )
            persisted = (root / "pre-run-observation.json").read_bytes()
            self.assertEqual(hashlib.sha256(persisted).hexdigest(), observation["pre_run_observation_sha256"])
            self.assertEqual(json.loads(persisted), observation["pre_run_observation"])
            self.assertEqual(observation["pre_run_observation_sha256"], preflight_receipts[0]["ccp_observation_raw_sha256"])
            _ccp_preflight_link({"ccp_observation": observation, "preflight_receipt": preflight_receipts[0]}, {})
            changed = json.loads(json.dumps(observation))
            changed["pre_run_observation"]["run_count"] = 1
            with self.assertRaises(A0XVerificationError):
                _ccp_preflight_link({"ccp_observation": changed, "preflight_receipt": preflight_receipts[0]}, {})
            changed = json.loads(json.dumps(observation))
            changed["run_record"]["state"]["argv_commitment"] = "0" * 64
            with self.assertRaisesRegex(A0XVerificationError, "guard commitment"):
                _ccp_preflight_link({"ccp_observation": changed, "preflight_receipt": preflight_receipts[0]}, {})
            changed = json.loads(json.dumps(observation))
            changed["pre_run_observation"]["ccp_trace"][4]["argv"][7] = "/mutated-cache"
            changed_raw = json.dumps(changed["pre_run_observation"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            changed["pre_run_observation_sha256"] = hashlib.sha256(changed_raw).hexdigest()
            with self.assertRaisesRegex(A0XVerificationError, "argv"):
                _ccp_preflight_link({"ccp_observation": changed, "preflight_receipt": {"ccp_observation_path": "pre-run-observation.json", "ccp_observation_raw_sha256": hashlib.sha256(changed_raw).hexdigest()}}, {})
            changed = json.loads(json.dumps(observation))
            changed["policy_raw_sha256"] = "0" * 64
            with self.assertRaisesRegex(A0XVerificationError, "projection"):
                _ccp_preflight_link({"ccp_observation": changed, "preflight_receipt": preflight_receipts[0]}, {})
            malformed_mutations = (
                lambda value: value.pop("policy_raw_sha256"),
                lambda value: value.__setitem__("unexpected", True),
                lambda value: value["admission"]["slot"].__setitem__("kind", "queue_lock"),
            )
            for mutate in malformed_mutations:
                self_consistent_but_malformed = json.loads(json.dumps(observation))
                mutate(self_consistent_but_malformed["pre_run_observation"])
                malformed_raw = json.dumps(self_consistent_but_malformed["pre_run_observation"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
                self_consistent_but_malformed["pre_run_observation_sha256"] = hashlib.sha256(malformed_raw).hexdigest()
                malformed_receipt = {
                    "ccp_observation_path": "pre-run-observation.json",
                    "ccp_observation_raw_sha256": hashlib.sha256(malformed_raw).hexdigest(),
                }
                with self.assertRaisesRegex(A0XVerificationError, "shape"):
                    _ccp_preflight_link({"ccp_observation": self_consistent_but_malformed, "preflight_receipt": malformed_receipt}, {})

    def test_material_entrypoint_rejects_cli_model_or_leg_override(self) -> None:
        from scripts.a0x_material import main

        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                main(["--model", "gpt2"])

    def test_material_entrypoint_fails_closed_when_planned_dossier_is_absent(self) -> None:
        from scripts.a0x_material import main

        with redirect_stderr(StringIO()):
            self.assertNotEqual(0, main(["--fixed-dossier", "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"]))

    def test_attempt_claim_is_durable_exclusive_and_never_reused(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, reserve_attempt_claim
        from tests.a0x_test_support import artifact

        with TemporaryDirectory() as directory:
            claim = Path(directory) / "attempt.json"
            payload = artifact("a0x-attempt-claim.schema.json")
            reserve_attempt_claim(claim, payload)
            self.assertTrue(claim.is_file())
            with self.assertRaisesRegex(A0XRunnerError, "attempt claim already exists"):
                reserve_attempt_claim(claim, payload)

    def test_attempt_claim_rejects_a_symlinked_parent(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerError, reserve_attempt_claim
        from tests.a0x_test_support import artifact

        with TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external"
            external.mkdir()
            os.symlink(external, root / "linked")
            with self.assertRaisesRegex(A0XRunnerError, "symlink"):
                reserve_attempt_claim(root / "linked" / "attempt.json", artifact("a0x-attempt-claim.schema.json"))

    def test_guarded_coordinator_claims_before_its_single_run_and_refuses_busy_state(self) -> None:
        from latent_triz.a0x_runner import A0XRunnerDependencies, A0XRunnerError, run_a0x_guarded_pair

        contract = json.loads((Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text())

        from tests.a0x_test_support import authorization_documents, pair_binding
        from tests.test_a0x_runner import matrix_doctor_envelope, matrix_dry_run_envelope, matrix_plan_envelope, matrix_receipt_envelope
        pair = pair_binding()
        dossier, authorization, _chain = authorization_documents(pair)
        raw = (Path(__file__).resolve().parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_bytes()
        dossier["material_contract_raw_sha256"] = hashlib.sha256(raw).hexdigest()
        authorization["material_contract_raw_sha256"] = hashlib.sha256(raw).hexdigest()
        authorization["source_head"] = "a" * 40
        qualification = json.dumps(matrix_receipt_envelope(), sort_keys=True, separators=(",", ":")).encode()
        authorization["qualification_receipt_raw_sha256"] = hashlib.sha256(qualification).hexdigest()
        authorization["ccp"] = {name: contract["ccp"][name] for name in ("path", "source_commit", "qualified_source_tree", "sha256", "version")}
        from latent_triz.a0x_contract import APPROVAL_DOSSIER_PROFILE, canonical_commitment
        authorization["approved_dossier_commitment"] = canonical_commitment(
            dossier, APPROVAL_DOSSIER_PROFILE,
        ).as_mapping()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = Path(__file__).resolve().parents[1]
            (root / ".commit-ci-preflight.toml").write_bytes((repository / ".commit-ci-preflight.toml").read_bytes())
            (root / ".commit-ci-policy-v2.toml").write_bytes((repository / ".commit-ci-policy-v2.toml").read_bytes())
            dossier_path, authorization_path = root / "dossier.json", root / "authorization.json"
            dossier_path.write_text(json.dumps(dossier), encoding="utf-8")
            authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
            trace: list[str] = []
            test_case = self
            class FakeCcp:
                def sha256(self, path): trace.append("hash"); return contract["ccp"]["sha256"]
                def review_dry_run(self, _trace): trace.append("review"); return True
                def execute(self, command):
                    command = tuple(command)
                    labels = {
                        ("admission", "status", "--json"): "admission status --json",
                        ("resource", "status", "--json"): "resource status --json",
                        ("plan", "--config", ".commit-ci-preflight.toml", "--json"): "plan --json",
                        ("doctor", "--config", ".commit-ci-preflight.toml", "--json"): "doctor --json",
                        ("dry-run", "--config", ".commit-ci-preflight.toml", "--repository", ".", "--cache-dir", "/Users/marco1/Library/Caches/commit-ci-preflight-build-v1", "--json"): "dry-run --json",
                    }
                    command = labels.get(command, "unknown")
                    trace.append(command)
                    if command == "admission status --json":
                        return 0, b'{"active":false,"queue_count":0,"process_visibility_note":"No process visible in the local shell does not prove global inactivity.","queue_lock":{"acquired_at_unix_seconds":null,"heartbeat_at_unix_seconds":null,"kind":"queue_lock","lease_state":"not_applicable","owner_run_id":null,"state":"free"},"schema_version":"2.0","slot":{"acquired_at_unix_seconds":null,"heartbeat_at_unix_seconds":null,"kind":"slot_lock","lease_state":"not_applicable","owner_run_id":null,"state":"free"},"ticket_ids":[]}'
                    if command == "resource status --json":
                        return 0, b'{"available_percent":50,"capability":"supported_enforced","compressor_occupied_bytes":0,"consecutive_soft_samples":0,"decision":"admit","platform":"macos","policy_version":"macos-v4","reclaimable_uncompressed_bytes":1,"schema_version":"1.0","swap_total_bytes":1,"swap_used_bytes":0,"total_memory_bytes":1}'
                    if command == "plan --json":
                        return 0, json.dumps(matrix_plan_envelope(), separators=(",", ":")).encode()
                    if command == "doctor --json": return 0, json.dumps(matrix_doctor_envelope(), separators=(",", ":")).encode()
                    if command == "dry-run --json": return 0, json.dumps(matrix_dry_run_envelope(), separators=(",", ":")).encode()
                    return 0, b""
                def guard_exec(self, argv_commitment, callback):
                    trace.append("run-enter")
                    test_case.assertEqual(authorization["guard_exec_argv_commitment"], argv_commitment)
                    child = callback()
                    trace.append("run-exit")
                    return 0, b"synthetic-child-output", child
            dependencies = A0XRunnerDependencies(
                static_preflight=lambda _context: trace.append("lifecycle"), tokenizer_factory=lambda: object(), model_factory=lambda _x: object(), activation=lambda x: x, activation_sealer=lambda x: x, target_capability_factory=lambda x: x, analysis=lambda x: x, package_builder=lambda _x: root / "package", package_verifier=lambda _x: None, protected_tree_postflight=lambda _x: None, failure_sealer=lambda *_x: {"status":"failed"}, release_model=lambda _x: None,
            )
            result = run_a0x_guarded_pair(root=root, dossier_path=dossier_path, authorization_path=authorization_path, material_contract_raw=raw, executor=FakeCcp(), source_head="a" * 40, dependencies=dependencies, attempt_claim_path=root / "claim.json", source_head_probe=lambda: "a" * 40, qualification_receipt_probe=lambda: qualification)
            self.assertEqual("completed", result["status"])
            self.assertLess(trace.index("review"), trace.index("run-enter"))
            self.assertGreater(trace.index("lifecycle"), trace.index("run-enter"))
            self.assertTrue((root / "claim.json").is_file())
            class Busy(FakeCcp):
                def execute(self, command):
                    if tuple(command) == ("admission", "status", "--json"):
                        return 0, b'{"active":true}'
                    return super().execute(command)
            with self.assertRaises(A0XRunnerError):
                run_a0x_guarded_pair(root=root, dossier_path=dossier_path, authorization_path=authorization_path, material_contract_raw=raw, executor=Busy(), source_head="a" * 40, dependencies=dependencies, attempt_claim_path=root / "other.json", qualification_receipt_probe=lambda: qualification)

    def test_fixed_make_targets_are_bijective_and_excluded_from_synthetic_workflows(self) -> None:
        from latent_triz.a0x_runner import planned_material_dossiers

        root = Path(__file__).resolve().parents[1]
        makefile = (root / "Makefile").read_text(encoding="utf-8")
        mappings = planned_material_dossiers()
        self.assertEqual(12, len(mappings))
        self.assertEqual(12, len(set(mappings.values())))
        for (leg, model), dossier in mappings.items():
            target = f"a0x-material-{leg}-{model}:"
            self.assertEqual(1, makefile.count(target))
            self.assertIn(f"--fixed-dossier {dossier}", makefile)
        self.assertNotIn("a0x-material-", (root / "scripts/repository_check.py").read_text(encoding="utf-8"))
