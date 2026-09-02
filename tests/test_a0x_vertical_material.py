"""Fail-closed checks for the selector-only A0X vertical material launcher."""
from __future__ import annotations

import unittest
import importlib.util
import hashlib
import io
import json
import os
import subprocess
import tempfile
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from latent_triz.a0x_ccp_executor import A0XCcpExecutorError
from latent_triz.a0x_contract import Leg, PairBinding
from latent_triz.a0x_vertical_slice import (
    A0XVerticalSliceError,
    VerticalSliceRequest,
    generate_vertical_slice,
)
from tests.a0x_test_support import pair_binding


HEAD = "a" * 40
VERTICAL_DOSSIER = (
    "experiments/a0x-six-model/vertical-slices/"
    f"{HEAD}/a0/smollm2_360m/approval-dossier.json"
)
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "a0x_vertical_material.py"


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("a0x_vertical_material_entrypoint", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("vertical material entrypoint cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A0XVerticalMaterialTests(unittest.TestCase):
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
                    repository_root=Path("/private/tmp"),
                    implementation_source_head=HEAD,
                    leg="a0",
                    model_key="smollm2_360m",
                    source_head_probe=lambda: HEAD,
                )
        load.assert_called_once_with(Path("/private/tmp").resolve(), VERTICAL_DOSSIER)

    def test_bad_selector_refuses_before_package_load_or_guard(self) -> None:
        from latent_triz.a0x_ccp_executor import launch_vertical_slice_dossier

        with patch("latent_triz.a0x_ccp_executor.load_vertical_slice") as load:
            with self.assertRaises(A0XCcpExecutorError):
                launch_vertical_slice_dossier(
                    repository_root=Path("/private/tmp"),
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
                    repository_root=Path("/private/tmp"),
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
                    repository_root=Path("/private/tmp"),
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
                repository_root=Path("/private/tmp"),
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
