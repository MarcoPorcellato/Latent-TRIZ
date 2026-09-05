"""Fail-closed checks for the selector-only A0X vertical material launcher."""
from __future__ import annotations

import unittest
import importlib.util
import hashlib
import inspect
import io
import json
import os
import subprocess
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from latent_triz.a0x_ccp_executor import A0XCcpExecutorError
from latent_triz.a0x_contract import Leg, PairBinding
from latent_triz.a0x_vertical_slice import (
    A0XVerticalSliceError,
    VerticalSliceRequest,
    generate_vertical_slice,
)
from tests.a0x_test_support import pair_binding


ROOT = Path(__file__).resolve().parents[1]
HEAD = "a" * 40
VERTICAL_DOSSIER = (
    "experiments/a0x-six-model/vertical-slices/"
    f"{HEAD}/a0/smollm2_360m/approval-dossier.json"
)
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "a0x_vertical_material.py"


class _SyntheticExecutableIdentityVerifier:
    """Private-core test capability: reports actual bytes, never a production identity."""

    def verify(self, *, role, path, expected_sha256, expected_version=None):
        from latent_triz.a0x_ccp_executor import _ExecutableIdentityEvidence
        candidate = Path(path)
        metadata = candidate.lstat()
        if not os.path.isfile(candidate) or metadata.st_nlink != 1:
            raise AssertionError("synthetic role is not an independent regular file")
        return _ExecutableIdentityEvidence(
            role, candidate, hashlib.sha256(candidate.read_bytes()).hexdigest(), expected_version, synthetic=True,
        )


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("a0x_vertical_material_entrypoint", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("vertical material entrypoint cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A0XVerticalMaterialTests(unittest.TestCase):
    def test_v2_launcher_is_a_distinct_typed_entrypoint(self) -> None:
        """Future Gate C must not select the historical v1/batch launcher."""
        from latent_triz.a0x_ccp_executor import launch_vertical_runtime_package

        self.assertTrue(callable(launch_vertical_runtime_package))

    def test_public_v2_launcher_exposes_no_test_dependency_adapters(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_runtime_package

        self.assertNotIn("source_state_probe", inspect.signature(launch_vertical_runtime_package).parameters)

    def _prepared_v2_graph(self):
        """Build Task-1/2 synthetic bytes; no model, network, or runtime load."""
        from tests.test_a0x_vertical_runtime_bundle import A0XVerticalRuntimeBundleTests, HEAD as V2_HEAD, TREE as V2_TREE
        from latent_triz.a0x_runtime_bundle import prepare_vertical_runtime_bundle, sha256_file
        from tests.test_a0x_runtime_bundle import _synthetic_gate_a_verifier

        fixture = A0XVerticalRuntimeBundleTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        binding = fixture._binding()
        request = fixture._request(binding)
        expected_ccp = json.loads(
            (fixture.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(encoding="utf-8")
        )["ccp"]["sha256"]
        with (
            patch(
                "latent_triz.a0x_runtime_bundle.sha256_file",
                side_effect=lambda path: (
                    expected_ccp if Path(path).resolve() == request.ccp_executable.resolve()
                    else "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
                    if Path(path).resolve() == request.verifier_executable.resolve()
                    else sha256_file(path)
                ),
            ),
            patch("latent_triz.a0x_runtime_bundle._runtime_readiness", return_value={"artifact_class": "synthetic-readiness"}),
        ):
            prepared = prepare_vertical_runtime_bundle(
                fixture.root, request, source_state_probe=lambda: (V2_HEAD, V2_TREE, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=lambda *_args: (_ for _ in ()).throw(AssertionError("readiness reached")),
                gate_a_verifier=_synthetic_gate_a_verifier,
            )
        return fixture.root, binding, prepared, V2_HEAD, V2_TREE

    def _v4_authorization(self, root, binding, prepared, head, tree):
        """Build the complete v4 graph from real Task-2 wrapper bytes."""
        outputs = prepared["vertical_outputs"]
        references = {
            name: {"path": relative, "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest()}
            for name, relative in outputs.items()
        }
        descriptor = json.loads((root / outputs["descriptor"]).read_text())["payload"]
        inlet = json.loads((root / outputs["authorization"]).read_text())["payload"]
        mapping = json.loads((root / outputs["mapping"]).read_text())["payload"]
        guard_launch = {
            "launch_profile": "a0x-guard-launch-v2",
            "ccp": {"role": "ccp", "sha256": mapping["ccp"]["sha256"]},
            "python": {"role": "python", "sha256": mapping["python"]["sha256"]},
            "cwd_kind": "repository_root", "source_head": head,
            "child_script": descriptor["child_script"],
            "launch_descriptor": {"role": "descriptor", "path": outputs["descriptor"], "sha256": references["descriptor"]["sha256"]},
            "environment_template": descriptor["environment_template"],
            "resource": {"profile": "a0x-material", "workload_family": "latent-triz-a0x-v1", "executor": "native", "cache_state": "warm", "execution_mode": "native", "target_platform": "macos-arm64", "memory_limit_bytes": 8589934592},
            "timeouts": {"outer_timeout_seconds": 3600, "internal_budget_seconds": 3300, "cleanup_margin_seconds": 300, "admission_timeout_seconds": 300},
            "argv_template": ["{CCP}", "guard", "exec", "--admission-timeout-seconds", "300", "--timeout-seconds", "3600", "--resource-profile", "a0x-material", "--resource-workload-family", "latent-triz-a0x-v1", "--resource-executor", "native", "--resource-cache-state", "warm", "--resource-execution-mode", "native", "--resource-target-platform", "macos-arm64", "--resource-memory-limit-bytes", "8589934592", "--", "{PYTHON}", "{CHILD}", "--launch-descriptor", "{DESCRIPTOR}"],
        }
        return {
            "artifact_class": "a0x-vertical-execution-authorization",
            "commitment_profile": "a0x-execution-authorization-json-v4",
            "qualified_source": {"head": head, "tree": tree, "ref": "refs/heads/main"},
            "pair_binding": binding.pair_binding.as_mapping(),
            "vertical_package": {"envelope_path": binding.envelope_path, "package_path": binding.package_path, "commitment_path": binding.commitment_path, "commitment_raw_sha256": binding.commitment_raw_sha256, "package_commitment_sha256": binding.package_commitment_sha256, "dossier_path": binding.dossier_path, "dossier_sha256": binding.dossier_sha256},
            "gate_b_authorization": {"path": prepared["gate_b_authorization_path"], "sha256": prepared["gate_b_authorization_sha256"]},
            "gate_a_verification_receipt": {"path": prepared["verification_receipt_path"], "sha256": prepared["verification_receipt_sha256"]},
            "gate_b_outputs": references, "guard_launch": guard_launch,
            "authorization_id": "gate-c-auth-test-01", "attempt_id": "gate-c-attempt-test-01",
            "max_guard_exec_count": 1, "stop_boundary": "after_one_sealed_target_read",
        }

    def test_v2_gate_c_revalidates_package_and_every_gate_b_output_before_guard(self) -> None:
        from latent_triz.a0x_ccp_executor import (
            ProcessResult, _launch_validated_vertical_v2, vertical_execution_authorization_path,
        )

        root, binding, prepared, head, tree = self._prepared_v2_graph()
        authorization = self._v4_authorization(root, binding, prepared, head, tree)
        path = root / vertical_execution_authorization_path(binding)
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode("utf-8"))

        class Inert:
            calls = 0
            def run(self, *args, **kwargs):
                self.calls += 1
                terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
                return ProcessResult(0, hashlib.sha256(terminal).hexdigest(), len(terminal), "0" * 64, 0, stdout_prefix=terminal)

        inert = Inert()
        result = _launch_validated_vertical_v2(
            repository_root=root, package_binding=binding, execution_authorization_path=path.relative_to(root).as_posix(),
            source_state_probe=lambda: (head, tree, True), process_executor=inert,
            guard_preflight_producer=__import__("tests.test_a0x_ccp_executor", fromlist=["_FakeGuardPreflight"])._FakeGuardPreflight(version=json.loads((root / prepared["vertical_outputs"]["authorization"]).read_text())["payload"]["ccp"]["version"]),
            executable_identity_verifier=_SyntheticExecutableIdentityVerifier(),
        )
        self.assertEqual("synthetic_completed", result["status"])
        self.assertFalse(result["publication_eligible"])
        self.assertEqual(1, inert.calls)
        pre_run = root / path.parent.relative_to(root) / "observations" / "pre-run-observation.json"
        self.assertTrue(pre_run.is_file())

    def test_v2_gate_c_rechecks_all_executable_identities_after_guard(self) -> None:
        """A successful child cannot bypass the final executable-byte boundary."""
        from latent_triz.a0x_ccp_executor import (
            ProcessResult, _launch_validated_vertical_v2, vertical_execution_authorization_path,
        )

        root, binding, prepared, head, tree = self._prepared_v2_graph()
        authorization = self._v4_authorization(root, binding, prepared, head, tree)
        path = root / vertical_execution_authorization_path(binding)
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode("utf-8"))

        class CountingSynthetic(_SyntheticExecutableIdentityVerifier):
            def __init__(self):
                self.calls = []

            def verify(self, **kwargs):
                self.calls.append(kwargs["role"])
                return super().verify(**kwargs)

        class Inert:
            def run(self, *args, **kwargs):
                terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
                return ProcessResult(0, hashlib.sha256(terminal).hexdigest(), len(terminal), "0" * 64, 0, stdout_prefix=terminal)

        verifier = CountingSynthetic()
        _launch_validated_vertical_v2(
            repository_root=root, package_binding=binding,
            execution_authorization_path=path.relative_to(root).as_posix(),
            source_state_probe=lambda: (head, tree, True), process_executor=Inert(),
            guard_preflight_producer=__import__("tests.test_a0x_ccp_executor", fromlist=["_FakeGuardPreflight"])._FakeGuardPreflight(
                version=json.loads((root / prepared["vertical_outputs"]["authorization"]).read_text())["payload"]["ccp"]["version"],
            ),
            executable_identity_verifier=verifier,
        )
        self.assertEqual(
            ["child", "ccp", "python"] * 4,
            verifier.calls,
        )

    def test_v2_gate_c_refuses_raw_gate_b_auth_or_receipt_drift_after_preflight(self) -> None:
        """Both non-wrapper Gate-B raw files are re-read before the one-shot claim."""
        from latent_triz.a0x_ccp_executor import (
            ProcessResult, _launch_validated_vertical_v2, vertical_execution_authorization_path,
        )
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight

        for label, field in (("authorization", "gate_b_authorization_path"), ("receipt", "verification_receipt_path")):
            with self.subTest(raw=label):
                root, binding, prepared, head, tree = self._prepared_v2_graph()
                authorization = self._v4_authorization(root, binding, prepared, head, tree)
                path = root / vertical_execution_authorization_path(binding)
                path.parent.mkdir(parents=True)
                path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode("utf-8"))

                class MutatingPreflight:
                    def __init__(self):
                        self.delegate = _FakeGuardPreflight(
                            version=json.loads((root / prepared["vertical_outputs"]["authorization"]).read_text())["payload"]["ccp"]["version"],
                        )

                    def produce(self, **kwargs):
                        outputs = self.delegate.produce(**kwargs)
                        (root / prepared[field]).write_bytes(b"{}")
                        return outputs

                class Inert:
                    calls = 0

                    def run(self, *args, **kwargs):
                        self.calls += 1
                        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
                        return ProcessResult(0, hashlib.sha256(terminal).hexdigest(), len(terminal), "0" * 64, 0, stdout_prefix=terminal)

                inert = Inert()
                with self.assertRaises(A0XCcpExecutorError):
                    _launch_validated_vertical_v2(
                        repository_root=root, package_binding=binding,
                        execution_authorization_path=path.relative_to(root).as_posix(),
                        source_state_probe=lambda: (head, tree, True), process_executor=inert,
                        guard_preflight_producer=MutatingPreflight(),
                        executable_identity_verifier=_SyntheticExecutableIdentityVerifier(),
                    )
                self.assertEqual(0, inert.calls)

    def test_v2_gate_c_post_claim_source_drift_seals_recovery_before_guard(self) -> None:
        """A claim is consumed when the final source boundary drifts."""
        from latent_triz.a0x_ccp_executor import _launch_validated_vertical_v2, vertical_execution_authorization_path
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight

        root, binding, prepared, head, tree = self._prepared_v2_graph()
        authorization = self._v4_authorization(root, binding, prepared, head, tree)
        path = root / vertical_execution_authorization_path(binding)
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        states = iter(((head, tree, True), (head, tree, True), (head, "f" * 40, True)))
        executor = mock.Mock(side_effect=AssertionError("guard reached"))

        with self.assertRaises(A0XCcpExecutorError):
            _launch_validated_vertical_v2(
                repository_root=root, package_binding=binding,
                execution_authorization_path=path.relative_to(root).as_posix(),
                source_state_probe=lambda: next(states), process_executor=executor,
                guard_preflight_producer=_FakeGuardPreflight(
                    version=json.loads((root / prepared["vertical_outputs"]["authorization"]).read_text())["payload"]["ccp"]["version"],
                ),
                executable_identity_verifier=_SyntheticExecutableIdentityVerifier(),
            )
        executor.assert_not_called()
        self.assertTrue(path.with_name("attempt-claim.json").is_file())
        terminal = json.loads((path.parent / "observations" / "terminal-observation.json").read_text())
        self.assertTrue(terminal["recovery_required"])
        self.assertEqual("recovery_required", terminal["outer_exit_classification"])

    def test_v2_gate_c_refuses_a_terminal_prefix_with_unobserved_extra_output(self) -> None:
        """A captured prefix is not an exact terminal record when output was truncated."""
        from latent_triz.a0x_ccp_executor import (
            ProcessResult, _launch_validated_vertical_v2, vertical_execution_authorization_path,
        )
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight

        root, binding, prepared, head, tree = self._prepared_v2_graph()
        authorization = self._v4_authorization(root, binding, prepared, head, tree)
        path = root / vertical_execution_authorization_path(binding)
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'

        class TruncatedTerminal:
            def run(self, *args, **kwargs):
                return ProcessResult(
                    0, hashlib.sha256(terminal + b"x").hexdigest(), len(terminal) + 1,
                    "0" * 64, 0, stdout_prefix=terminal,
                )

        with self.assertRaises(A0XCcpExecutorError):
            _launch_validated_vertical_v2(
                repository_root=root, package_binding=binding,
                execution_authorization_path=path.relative_to(root).as_posix(),
                source_state_probe=lambda: (head, tree, True), process_executor=TruncatedTerminal(),
                guard_preflight_producer=_FakeGuardPreflight(
                    version=json.loads((root / prepared["vertical_outputs"]["authorization"]).read_text())["payload"]["ccp"]["version"],
                ),
                executable_identity_verifier=_SyntheticExecutableIdentityVerifier(),
            )

    def test_v2_gate_c_refuses_output_drift_before_guard(self) -> None:
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, _launch_validated_vertical_v2, vertical_execution_authorization_path

        root, binding, prepared, head, tree = self._prepared_v2_graph()
        authorization = self._v4_authorization(root, binding, prepared, head, tree)
        path = root / vertical_execution_authorization_path(binding)
        path.parent.mkdir(parents=True)
        path.write_bytes(json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode())
        (root / prepared["vertical_outputs"]["mapping"]).write_bytes(b"{}")
        executor = mock.Mock(side_effect=AssertionError("guard reached"))
        with self.assertRaises(A0XCcpExecutorError):
            _launch_validated_vertical_v2(
                repository_root=root, package_binding=binding, execution_authorization_path=path.relative_to(root).as_posix(),
                source_state_probe=lambda: (head, tree, True), process_executor=executor,
                guard_preflight_producer=mock.Mock(), executable_identity_verifier=_SyntheticExecutableIdentityVerifier(),
            )
        executor.assert_not_called()

    def test_v2_gate_c_refuses_dirty_or_wrong_source_before_package_or_guard(self) -> None:
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, _launch_validated_vertical_v2, vertical_execution_authorization_path

        root, binding, _prepared, head, tree = self._prepared_v2_graph()
        executor = mock.Mock(side_effect=AssertionError("guard reached"))
        for state in ((head, tree, False), ("f" * 40, tree, True), (head, "e" * 40, True)):
            with self.subTest(state=state), self.assertRaises(A0XCcpExecutorError):
                _launch_validated_vertical_v2(
                    repository_root=root, package_binding=binding,
                    execution_authorization_path=vertical_execution_authorization_path(binding),
                    source_state_probe=lambda state=state: state, process_executor=executor,
                    guard_preflight_producer=mock.Mock(), executable_identity_verifier=_SyntheticExecutableIdentityVerifier(),
                )
        executor.assert_not_called()

    def _valid_package(self):
        from tests.test_a0x_vertical_slice import _publish_at, _synthetic_repository

        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "repository"
        root.mkdir()
        _synthetic_repository(root)
        for command in (
            ("init", "-q"),
            ("config", "user.name", "A0X Test"),
            ("config", "user.email", "a0x@example.invalid"),
            ("add", "-A"),
            ("commit", "-q", "-m", "synthetic fixture"),
        ):
            subprocess.run(("/usr/bin/git", "-C", str(root), *command), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        head = subprocess.check_output(("/usr/bin/git", "-C", str(root), "rev-parse", "HEAD"), text=True).strip()
        request = VerticalSliceRequest(
            leg=Leg.A0,
            model_key="smollm2_360m",
            implementation_source_head=head,
            output_root=(
                "experiments/a0x-six-model/vertical-slices/"
                f"{head}/a0/smollm2_360m"
            ),
        )
        with patch("latent_triz.a0x_vertical_slice._darwin_publish_exclusive_at", new=_publish_at):
            generate_vertical_slice(root, request)
        return temporary, root, head, root / request.output_root

    def _assert_no_claim_or_guard(self, root: Path, fake, preflight) -> None:
        self.assertEqual([], fake.calls)
        self.assertEqual([], preflight.calls)
        self.assertEqual([], list(root.rglob("attempt-claim.json")))

    def test_selector_only_launcher_derives_the_only_dossier_path(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        with patch("latent_triz.a0x_ccp_executor.load_vertical_slice") as load:
            load.side_effect = A0XVerticalSliceError("synthetic package rejection")
            with self.assertRaises(A0XCcpExecutorError):
                launch_vertical_slice_dossier(
                    repository_root=ROOT,
                    implementation_source_head=HEAD,
                    leg="a0",
                    model_key="smollm2_360m",
                    source_head_probe=lambda: HEAD,
                )
        load.assert_called_once_with(ROOT.resolve(), VERTICAL_DOSSIER)

    def test_bad_selector_refuses_before_package_load_or_guard(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        with patch("latent_triz.a0x_ccp_executor.load_vertical_slice") as load:
            with self.assertRaises(A0XCcpExecutorError):
                launch_vertical_slice_dossier(
                    repository_root=ROOT,
                    implementation_source_head=HEAD,
                    leg="A0",
                    model_key="smollm2_360m",
                    source_head_probe=lambda: HEAD,
                )
        load.assert_not_called()

    def test_loader_rejection_starts_no_guard(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        with patch(
            "latent_triz.a0x_ccp_executor.load_vertical_slice",
            side_effect=A0XVerticalSliceError("synthetic hash/schema/source mismatch"),
        ):
            with self.assertRaises(A0XCcpExecutorError):
                launch_vertical_slice_dossier(
                    repository_root=ROOT,
                    implementation_source_head=HEAD,
                    leg="a0",
                    model_key="smollm2_360m",
                    source_head_probe=lambda: HEAD,
                )

    def test_cross_pair_dossier_refuses_before_common_material_launcher(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        expected = PairBinding.from_mapping(pair_binding(Leg.A0, "smollm2_360m"))
        dossier = {
            "implementation_source_head": HEAD,
            "pair_binding": {**expected.as_mapping(), "leg": Leg.R1.value},
        }
        package = {
            "pair": expected.as_mapping(),
            "dossier": dossier,
            "dossier_relative": VERTICAL_DOSSIER,
        }
        with (
            patch("latent_triz.a0x_ccp_executor.load_vertical_slice", return_value=package),
            patch("latent_triz.a0x_ccp_executor._launch_validated_dossier") as launcher,
        ):
            with self.assertRaises(A0XCcpExecutorError):
                launch_vertical_slice_dossier(
                    repository_root=ROOT,
                    implementation_source_head=HEAD,
                    leg="a0",
                    model_key="smollm2_360m",
                    source_head_probe=lambda: HEAD,
                )
        launcher.assert_not_called()

    def test_dossier_byte_drift_refuses_before_common_material_launcher(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        pair = pair_binding(Leg.A0, "smollm2_360m")
        dossier = {"implementation_source_head": HEAD, "pair_binding": pair}
        original = json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode()
        package = {
            "pair": pair,
            "dossier": dossier,
            "dossier_relative": VERTICAL_DOSSIER,
            "manifest": {"members": {"approval-dossier.json": {"sha256": hashlib.sha256(original).hexdigest()}}},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / VERTICAL_DOSSIER
            path.parent.mkdir(parents=True)
            path.write_bytes(b'{"replaced":true}')
            with (
                patch("latent_triz.a0x_ccp_executor.load_vertical_slice", return_value=package),
                patch("latent_triz.a0x_ccp_executor._launch_validated_dossier") as launcher,
            ):
                with self.assertRaises(A0XCcpExecutorError):
                    launch_vertical_slice_dossier(
                        repository_root=root,
                        implementation_source_head=HEAD,
                        leg="a0",
                        model_key="smollm2_360m",
                        source_head_probe=lambda: HEAD,
                    )
            launcher.assert_not_called()

    def test_valid_synthetic_package_reaches_only_injected_guard(self) -> None:
        from tests.test_a0x_ccp_executor import A0XCcpExecutorTests, _FakeGuardPreflight
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        fixture = A0XCcpExecutorTests()
        try:
            root, pair, runtime, authorization, _mapping, fake = fixture._fixture()
            source = root / fixture._dossier
            dossier = json.loads(source.read_bytes())
            dossier["implementation_source_head"] = HEAD
            authorization["implementation_source_head"] = HEAD
            from latent_triz.a0x_contract import APPROVAL_DOSSIER_PROFILE, canonical_commitment
            authorization["approved_dossier_commitment"] = canonical_commitment(
                dossier, APPROVAL_DOSSIER_PROFILE,
            ).as_mapping()
            source.write_bytes(json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode())
            (root / runtime.authorization_path).write_bytes(
                json.dumps(authorization, sort_keys=True, separators=(",", ":")).encode(),
            )
            vertical_dossier = (
                "experiments/a0x-six-model/vertical-slices/"
                f"{HEAD}/a0/{pair.model_key}/approval-dossier.json"
            )
            vertical = root / vertical_dossier
            vertical.parent.mkdir(parents=True)
            raw = source.read_bytes()
            vertical.write_bytes(raw)
            package = {
                "pair": pair.as_mapping(),
                "dossier": json.loads(raw),
                "dossier_relative": vertical_dossier,
                "manifest": {"members": {"approval-dossier.json": {"sha256": hashlib.sha256(raw).hexdigest()}}},
            }
            with patch("latent_triz.a0x_ccp_executor.load_vertical_slice", return_value=package):
                result = launch_vertical_slice_dossier(
                    repository_root=root,
                    implementation_source_head=HEAD,
                    leg="a0",
                    model_key=pair.model_key,
                    source_head_probe=lambda: HEAD,
                    process_executor=fake,
                    guard_preflight_producer=_FakeGuardPreflight(),
                )
            self.assertEqual("completed", result["status"])
            self.assertEqual(1, len(fake.calls))
        finally:
            fixture.doCleanups()

    def test_historical_launcher_refuses_derived_vertical_path(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_fixed_dossier

        with self.assertRaises(A0XCcpExecutorError):
            launch_fixed_dossier(
                repository_root=ROOT,
                fixed_dossier=VERTICAL_DOSSIER,
                source_head_probe=lambda: HEAD,
            )

    def test_cli_source_probe_has_fixed_minimal_environment(self) -> None:
        module = _load_cli_module()

        class Completed:
            returncode = 0
            stdout = (HEAD + "\n").encode()

        with patch.object(module.subprocess, "run", return_value=Completed()) as run:
            self.assertEqual(HEAD, module._source_head())
        self.assertEqual(
            {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_NO_REPLACE_OBJECTS": "1"},
            run.call_args.kwargs["env"],
        )

    def test_cli_has_no_fixed_dossier_option(self) -> None:
        module = _load_cli_module()
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                module.main(["--fixed-dossier", VERTICAL_DOSSIER])
        self.assertEqual(2, stopped.exception.code)

    def test_cli_v2_checks_external_raw_hashes_before_loading_package(self) -> None:
        module = _load_cli_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "commitment.json").write_bytes(b"{}")
            (root / "authorization.json").write_bytes(b"{}")
            with (
                patch.object(module, "ROOT", root),
                patch.object(module, "vertical_package_binding_from_commitment") as load,
                redirect_stderr(io.StringIO()),
            ):
                result = module.main([
                    "vertical-v2", "--vertical-commitment", "commitment.json",
                    "--vertical-commitment-raw-sha256", "0" * 64,
                    "--execution-authorization", "authorization.json",
                    "--execution-authorization-raw-sha256", "0" * 64,
                ])
        self.assertEqual(2, result)
        load.assert_not_called()

    def test_cli_v1_rejects_v2_only_arguments(self) -> None:
        module = _load_cli_module()
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                module.main([
                    "historical-v1", "--implementation-source-head", HEAD,
                    "--leg", "a0", "--model-key", "smollm2_360m",
                    "--execution-authorization", "forbidden.json",
                ])
        self.assertEqual(2, stopped.exception.code)

    def test_vertical_package_head_drift_between_load_and_delegation_refuses_before_claim(self) -> None:
        from tests.test_a0x_ccp_executor import A0XCcpExecutorTests, _FakeGuardPreflight
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        fixture = A0XCcpExecutorTests()
        try:
            root, pair, _runtime, _authorization, _mapping, fake = fixture._fixture()
            vertical_dossier = (
                "experiments/a0x-six-model/vertical-slices/"
                f"{HEAD}/a0/{pair.model_key}/approval-dossier.json"
            )
            dossier = json.loads((root / fixture._dossier).read_bytes())
            dossier["implementation_source_head"] = HEAD
            raw = json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode()
            path = root / vertical_dossier
            path.parent.mkdir(parents=True)
            path.write_bytes(raw)
            package = {
                "pair": pair.as_mapping(),
                "dossier": dossier,
                "dossier_relative": vertical_dossier,
                "manifest": {"members": {"approval-dossier.json": {"sha256": hashlib.sha256(raw).hexdigest()}}},
            }
            preflight = _FakeGuardPreflight()
            samples = iter((HEAD, "b" * 40))
            with patch("latent_triz.a0x_ccp_executor.load_vertical_slice", return_value=package):
                with self.assertRaisesRegex(A0XCcpExecutorError, "vertical package"):
                    launch_vertical_slice_dossier(
                        repository_root=root,
                        implementation_source_head=HEAD,
                        leg="a0",
                        model_key=pair.model_key,
                        source_head_probe=lambda: next(samples),
                        process_executor=fake,
                        guard_preflight_producer=preflight,
                    )
            self._assert_no_claim_or_guard(root, fake, preflight)
        finally:
            fixture.doCleanups()

    def test_five_file_package_mutations_refuse_before_claim_guard_or_preflight(self) -> None:
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight, _FakeProcess
        from latent_triz.a0x_ccp_executor import ProcessResult, launch_vertical_slice_dossier

        def mutate(package: Path, kind: str) -> None:
            freeze = package / "freeze.json"
            if kind == "freeze":
                freeze.write_bytes(b"{}")
            elif kind == "dossier":
                (package / "approval-dossier.json").write_bytes(b"{}")
            elif kind == "manifest":
                (package / "slice-manifest.json").write_bytes(b"{}")
            elif kind == "symlink":
                freeze.unlink()
                freeze.symlink_to("implementation.json")
            elif kind == "hardlink":
                freeze.unlink()
                os.link(package / "implementation.json", freeze)
            elif kind == "directory":
                freeze.unlink()
                freeze.mkdir()
            elif kind == "extra":
                (package / "unexpected.json").write_bytes(b"{}")
            else:
                raise AssertionError(kind)

        for kind in ("freeze", "dossier", "manifest", "symlink", "hardlink", "directory", "extra"):
            with self.subTest(kind=kind):
                temporary, root, head, package = self._valid_package()
                self.addCleanup(temporary.cleanup)
                mutate(package, kind)
                fake = _FakeProcess(ProcessResult(0, "0" * 64, 0, "0" * 64, 0))
                preflight = _FakeGuardPreflight()
                with self.assertRaises(A0XCcpExecutorError):
                    launch_vertical_slice_dossier(
                        repository_root=root,
                        implementation_source_head=head,
                        leg="a0",
                        model_key="smollm2_360m",
                        source_head_probe=lambda: head,
                        process_executor=fake,
                        guard_preflight_producer=preflight,
                    )
                self._assert_no_claim_or_guard(root, fake, preflight)

    def test_changed_head_cross_pair_and_malformed_selectors_refuse_before_package_side_effects(self) -> None:
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight, _FakeProcess
        from latent_triz.a0x_ccp_executor import ProcessResult, launch_vertical_slice_dossier

        temporary, root, head, _package = self._valid_package()
        self.addCleanup(temporary.cleanup)
        cases = (
            (head, "a0", "smollm2_360m", "b" * 40),
            (head, "r1", "smollm2_360m", head),
            (head, "a0", "gpt2", head),
            ("short", "a0", "smollm2_360m", head),
            (head, "A0", "smollm2_360m", head),
            (head, "a0", "../smollm2_360m", head),
        )
        for implementation_head, leg, model_key, observed_head in cases:
            with self.subTest(implementation_head=implementation_head, leg=leg, model_key=model_key):
                fake = _FakeProcess(ProcessResult(0, "0" * 64, 0, "0" * 64, 0))
                preflight = _FakeGuardPreflight()
                with self.assertRaises(A0XCcpExecutorError):
                    launch_vertical_slice_dossier(
                        repository_root=root,
                        implementation_source_head=implementation_head,
                        leg=leg,
                        model_key=model_key,
                        source_head_probe=lambda value=observed_head: value,
                        process_executor=fake,
                        guard_preflight_producer=preflight,
                    )
                self._assert_no_claim_or_guard(root, fake, preflight)
