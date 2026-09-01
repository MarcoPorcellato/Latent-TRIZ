from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class A0XGateBBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source_head = "a" * 40
        self.attempt_id = "a0x-a0-smollm2-360m-synthetic-attempt-01"

        self.base_python = self.root / "external/python3.11"
        self.base_python.parent.mkdir()
        self.base_python.write_bytes(b"synthetic python 3.11")
        self.base_python.chmod(0o700)

        self.wheelhouse = self.root / "external/wheelhouse"
        self.wheelhouse.mkdir()
        wheels: list[dict[str, object]] = []
        for index in range(39):
            distribution = f"package-{index:02d}"
            filename = f"package_{index:02d}-1.0-py3-none-any.whl"
            raw = f"synthetic wheel {index}".encode()
            (self.wheelhouse / filename).write_bytes(raw)
            wheels.append({
                "distribution": distribution,
                "version": "1.0",
                "filename": filename,
                "tag": "py3-none-any",
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
        self.manifest_raw = _canonical({
            "profile": "a0x-offline-wheelhouse-v1",
            "python_major_minor": [3, 11],
            "accepted_tags": ["py3-none-any"],
            "wheels": wheels,
        })
        self.manifest = self.root / "external/wheelhouse.manifest.json"
        self.manifest.write_bytes(self.manifest_raw)

        self.model_source = self.root / "external/model"
        self.model_source.mkdir()
        runtime_files: list[dict[str, object]] = []
        for filename, raw in (("config.json", b"{}"), ("model.safetensors", b"synthetic weights")):
            (self.model_source / filename).write_bytes(raw)
            runtime_files.append({
                "path": filename,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
        self.model_card = self.root / "experiments/a0x-six-model/model-cards/synthetic.json"
        self.model_card.parent.mkdir(parents=True)
        self.model_card_raw = _canonical({
            "artifact_class": "a0x-model-card",
            "model_key": "synthetic",
            "model_id": "example/synthetic",
            "revision": "b" * 40,
            "runtime_root": "artifacts/models/synthetic-bbbbbbbb",
            "runtime_files": runtime_files,
        })
        self.model_card.write_bytes(self.model_card_raw)

    def _request(self, **changes: object):
        from latent_triz.a0x_gate_b_builder import GateBBuildRequest

        values: dict[str, object] = {
            "source_head": self.source_head,
            "attempt_id": self.attempt_id,
            "wheelhouse_directory": self.wheelhouse,
            "wheelhouse_manifest": self.manifest,
            "wheelhouse_manifest_sha256": hashlib.sha256(self.manifest_raw).hexdigest(),
            "base_python": self.base_python,
            "base_python_sha256": hashlib.sha256(self.base_python.read_bytes()).hexdigest(),
            "base_python_version": "3.11.13",
            "bootstrap_pip_version": "25.2",
            "model_card": self.model_card.relative_to(self.root).as_posix(),
            "model_card_sha256": hashlib.sha256(self.model_card_raw).hexdigest(),
            "model_source_root": self.model_source,
        }
        values.update(changes)
        return GateBBuildRequest(**values)

    @staticmethod
    def _cli_module():
        path = Path(__file__).parents[1] / "scripts/a0x_build_gate_b_runtime.py"
        specification = importlib.util.spec_from_file_location("a0x_build_gate_b_runtime_test", path)
        if specification is None or specification.loader is None:
            raise AssertionError("Gate B builder CLI is unavailable")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module

    def _cli_arguments(self) -> list[str]:
        return [
            "--plan",
            "--source-head", self.source_head,
            "--attempt-id", self.attempt_id,
            "--wheelhouse", str(self.wheelhouse),
            "--wheelhouse-manifest", str(self.manifest),
            "--wheelhouse-manifest-sha256", hashlib.sha256(self.manifest_raw).hexdigest(),
            "--base-python", str(self.base_python),
            "--base-python-sha256", hashlib.sha256(self.base_python.read_bytes()).hexdigest(),
            "--base-python-version", "3.11.13",
            "--bootstrap-pip-version", "25.2",
            "--model-card", self.model_card.relative_to(self.root).as_posix(),
            "--model-card-sha256", hashlib.sha256(self.model_card_raw).hexdigest(),
            "--model-source-root", str(self.model_source),
        ]

    @staticmethod
    def _planning_runner(argv: Sequence[str], _cwd: Path) -> tuple[int, bytes, bytes]:
        if tuple(argv[-2:]) == ("-m", "pip"):
            raise AssertionError("incomplete pip command")
        if "--version" in argv:
            return 0, b"pip 25.2 from synthetic (python 3.11)\n", b""
        return 0, b'{"python_major_minor":[3,11],"python_version":"3.11.13"}\n', b""

    def _source_state(self, _root: Path) -> tuple[str, bool]:
        return self.source_head, True

    def test_plan_binds_exact_wheelhouse_python_model_and_commands_without_writes(self) -> None:
        from latent_triz.a0x_gate_b_builder import plan_gate_b_runtime

        plan = plan_gate_b_runtime(
            self.root, self._request(), runner=self._planning_runner,
            source_state_probe=self._source_state,
        )

        repository = self.root.resolve()
        attempt_root = repository / f".a0x-runtime/gate-b-builds/{self.attempt_id}"
        environment = attempt_root / "environment"
        requirements = attempt_root / "requirements-wheelhouse.txt"
        self.assertEqual("planned", plan["status"])
        self.assertEqual(39, plan["wheelhouse"]["distribution_count"])
        self.assertEqual(hashlib.sha256(self.manifest_raw).hexdigest(), plan["wheelhouse"]["manifest_sha256"])
        self.assertEqual(hashlib.sha256(self.model_card_raw).hexdigest(), plan["model"]["card_sha256"])
        self.assertEqual(
            [str(self.base_python), "-I", "-m", "venv", "--copies", str(environment)],
            plan["commands"]["venv"],
        )
        self.assertEqual(
            [
                str(environment / "bin/python3"), "-I", "-m", "pip", "--isolated",
                "--disable-pip-version-check", "install", "--no-index", "--find-links",
                str(self.wheelhouse.resolve()), "--require-hashes", "--no-deps", "-r", str(requirements),
            ],
            plan["commands"]["install"],
        )
        self.assertEqual(
            [
                str(environment / "bin/python3"), "-I", "-m", "pip", "--isolated",
                "--disable-pip-version-check", "uninstall", "--yes", "pip",
            ],
            plan["commands"]["remove_bootstrap_pip"],
        )
        requirements_raw = plan["requirements_bytes"].encode()
        self.assertEqual(39, len(requirements_raw.strip().splitlines()))
        self.assertIn(b"package-00==1.0 --hash=sha256:", requirements_raw)
        self.assertFalse(attempt_root.exists())
        self.assertFalse((self.root / "artifacts/models/synthetic-bbbbbbbb").exists())

    def test_plan_refuses_hash_cardinality_and_destination_drift_before_writes(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, plan_gate_b_runtime

        cases = (
            self._request(wheelhouse_manifest_sha256="0" * 64),
            self._request(model_card_sha256="0" * 64),
            self._request(base_python_sha256="0" * 64),
        )
        for request in cases:
            with self.subTest(request=request), self.assertRaises(A0XGateBBuilderError):
                plan_gate_b_runtime(
                    self.root, request, runner=self._planning_runner,
                    source_state_probe=self._source_state,
                )

        (self.root / f".a0x-runtime/gate-b-builds/{self.attempt_id}").mkdir(parents=True)
        with self.assertRaisesRegex(A0XGateBBuilderError, "occupied"):
            plan_gate_b_runtime(
                self.root, self._request(), runner=self._planning_runner,
                source_state_probe=self._source_state,
            )
        (self.root / ".a0x-runtime").rename(self.root / ".a0x-runtime-occupied-test")

        manifest = json.loads(self.manifest_raw)
        manifest["wheels"].pop()
        self.manifest_raw = _canonical(manifest)
        self.manifest.write_bytes(self.manifest_raw)
        with self.assertRaisesRegex(A0XGateBBuilderError, "39"):
            plan_gate_b_runtime(
                self.root,
                self._request(wheelhouse_manifest_sha256=hashlib.sha256(self.manifest_raw).hexdigest()),
                runner=self._planning_runner,
                source_state_probe=self._source_state,
            )

    def test_plan_refuses_probe_mismatch_and_never_builds(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, plan_gate_b_runtime

        calls: list[tuple[str, ...]] = []

        def wrong_version(argv: Sequence[str], _cwd: Path) -> tuple[int, bytes, bytes]:
            calls.append(tuple(argv))
            return 0, b'{"python_major_minor":[3,12],"python_version":"3.12.0"}\n', b""

        with self.assertRaisesRegex(A0XGateBBuilderError, "Python"):
            plan_gate_b_runtime(
                self.root, self._request(), runner=wrong_version,
                source_state_probe=self._source_state,
            )
        self.assertEqual(1, len(calls))
        self.assertFalse((self.root / ".a0x-runtime").exists())

    def test_plan_refuses_dirty_or_different_source_before_external_probe(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, plan_gate_b_runtime

        for observed in (("c" * 40, True), (self.source_head, False)):
            with self.subTest(observed=observed), self.assertRaisesRegex(A0XGateBBuilderError, "source"):
                plan_gate_b_runtime(
                    self.root,
                    self._request(),
                    runner=lambda *_args: self.fail("external probe reached"),
                    source_state_probe=lambda _root, value=observed: value,
                )

    def _build_runner(
        self,
        *,
        extra_distribution: bool = False,
        duplicate_distribution: bool = False,
        fail_install: bool = False,
        mutate_source_after_install: bool = False,
        replace_source_with_symlink: bool = False,
        replace_attempt_with_symlink: bool = False,
    ):
        calls: list[tuple[str, ...]] = []
        expected = {f"package-{index:02d}": "1.0" for index in range(39)}

        def runner(argv: Sequence[str], _cwd: Path) -> tuple[int, bytes, bytes]:
            call = tuple(argv)
            calls.append(call)
            if call[-1] == "--version":
                return 0, b"pip 25.2 from synthetic (python 3.11)\n", b""
            if "venv" in call:
                environment = Path(call[-1])
                python = environment / "bin/python3"
                python.parent.mkdir(parents=True)
                python.write_bytes(self.base_python.read_bytes())
                python.chmod(0o700)
                return 0, b"", b""
            if "install" in call:
                if fail_install:
                    return 1, b"", b"synthetic install failure"
                if mutate_source_after_install:
                    (self.model_source / "config.json").write_bytes(b"drift")
                if replace_source_with_symlink:
                    original = self.model_source.with_name("model-original")
                    self.model_source.rename(original)
                    self.model_source.symlink_to(original, target_is_directory=True)
                return 0, b"", b""
            if "uninstall" in call:
                if replace_attempt_with_symlink:
                    attempt = self.root / f".a0x-runtime/gate-b-builds/{self.attempt_id}"
                    original = attempt.with_name(f"{self.attempt_id}-original")
                    attempt.rename(original)
                    attempt.symlink_to(original, target_is_directory=True)
                return 0, b"", b""
            if call[-2] == "-c" and "distributions" in call[-1]:
                distributions = sorted(expected.items())
                if extra_distribution:
                    distributions.append(["pip", "25.2"])
                if duplicate_distribution:
                    distributions.append(["package-00", "1.0"])
                return 0, _canonical({
                    "distributions": distributions,
                    "pip_importable": False,
                    "python_major_minor": [3, 11],
                    "python_version": "3.11.13",
                    "sys_executable": call[0],
                }) + b"\n", b""
            return 0, b'{"python_major_minor":[3,11],"python_version":"3.11.13"}\n', b""

        return calls, runner

    def test_build_executes_exact_offline_flow_and_clones_only_allowlisted_files(self) -> None:
        from latent_triz.a0x_gate_b_builder import build_gate_b_runtime

        calls, runner = self._build_runner()
        clone_calls: list[tuple[Path, Path]] = []

        def clone_file(source: Path, destination: Path, **_kwargs: object) -> dict[str, object]:
            clone_calls.append((source, destination))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            return {
                "operation": "clonefile",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "size_bytes": source.stat().st_size,
            }

        receipt = build_gate_b_runtime(
            self.root, self._request(), runner=runner, clone_file=clone_file,
            source_state_probe=self._source_state,
        )

        repository = self.root.resolve()
        attempt_root = repository / f".a0x-runtime/gate-b-builds/{self.attempt_id}"
        receipt_path = attempt_root / "build-receipt.json"
        self.assertEqual("built", receipt["status"])
        self.assertEqual(39, receipt["python"]["distribution_count"])
        self.assertEqual(2, receipt["model"]["runtime_file_count"])
        self.assertEqual(_canonical(receipt), receipt_path.read_bytes())
        self.assertEqual(
            ["config.json", "model.safetensors"],
            [destination.name for _source, destination in clone_calls],
        )
        self.assertEqual(1, (attempt_root / "environment/bin/python3").stat().st_nlink)
        self.assertEqual(39, len((attempt_root / "requirements-wheelhouse.txt").read_text().strip().splitlines()))
        self.assertGreaterEqual(len(calls), 7)
        self.assertTrue(all(isinstance(call, tuple) for call in calls))

    def test_build_refuses_unexpected_distribution_without_receipt(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, build_gate_b_runtime

        _calls, runner = self._build_runner(extra_distribution=True)
        with self.assertRaisesRegex(A0XGateBBuilderError, "distribution"):
            build_gate_b_runtime(
                self.root,
                self._request(),
                runner=runner,
                clone_file=lambda *_args, **_kwargs: self.fail("clone reached"),
                source_state_probe=self._source_state,
            )
        receipt = self.root / f".a0x-runtime/gate-b-builds/{self.attempt_id}/build-receipt.json"
        self.assertFalse(receipt.exists())

    def test_build_refuses_duplicate_distribution_without_receipt(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, build_gate_b_runtime

        _calls, runner = self._build_runner(duplicate_distribution=True)
        with self.assertRaisesRegex(A0XGateBBuilderError, "distribution"):
            build_gate_b_runtime(
                self.root,
                self._request(),
                runner=runner,
                clone_file=lambda *_args, **_kwargs: self.fail("clone reached"),
                source_state_probe=self._source_state,
            )

    def test_build_refuses_child_failure_and_source_drift_without_receipt(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, build_gate_b_runtime

        for case in ("install", "source-drift"):
            with self.subTest(case=case):
                if (self.root / ".a0x-runtime").exists():
                    os.rename(self.root / ".a0x-runtime", self.root / f".a0x-runtime-{case}")
                model_destination = self.root / "artifacts/models/synthetic-bbbbbbbb"
                if model_destination.exists():
                    os.rename(model_destination, model_destination.with_name(f"{model_destination.name}-{case}"))
                (self.model_source / "config.json").write_bytes(b"{}")
                _calls, runner = self._build_runner(
                    fail_install=case == "install",
                    mutate_source_after_install=case == "source-drift",
                )
                with self.assertRaises(A0XGateBBuilderError):
                    build_gate_b_runtime(
                        self.root,
                        self._request(),
                        runner=runner,
                        clone_file=lambda *_args, **_kwargs: self.fail("clone reached"),
                        source_state_probe=self._source_state,
                    )
                receipt = self.root / f".a0x-runtime/gate-b-builds/{self.attempt_id}/build-receipt.json"
                self.assertFalse(receipt.exists())

    def test_build_refuses_source_root_or_attempt_root_symlink_swap(self) -> None:
        from latent_triz.a0x_gate_b_builder import A0XGateBBuilderError, build_gate_b_runtime

        for case in ("source", "attempt"):
            with self.subTest(case=case):
                if (self.root / ".a0x-runtime").exists() or (self.root / ".a0x-runtime").is_symlink():
                    os.rename(self.root / ".a0x-runtime", self.root / f".a0x-runtime-{case}")
                if self.model_source.is_symlink():
                    self.model_source.unlink()
                    self.model_source = self.model_source.with_name("model-original")
                model_destination = self.root / "artifacts/models/synthetic-bbbbbbbb"
                if model_destination.exists() or model_destination.is_symlink():
                    model_destination.rename(model_destination.with_name(f"{model_destination.name}-{case}"))
                clone_reached: list[bool] = []
                _calls, runner = self._build_runner(
                    replace_source_with_symlink=case == "source",
                    replace_attempt_with_symlink=case == "attempt",
                )
                with self.assertRaisesRegex(A0XGateBBuilderError, "source|output path"):
                    build_gate_b_runtime(
                        self.root,
                        self._request(),
                        runner=runner,
                        clone_file=lambda *_args, **_kwargs: clone_reached.append(True) or {},
                        source_state_probe=self._source_state,
                    )
                self.assertEqual([], clone_reached)

    def test_cli_plan_is_canonical_and_never_reaches_material_builder(self) -> None:
        module = self._cli_module()
        stream = io.StringIO()
        code = module.main(
            self._cli_arguments(),
            root=self.root,
            stdout=stream,
            runner=self._planning_runner,
            clone_file=lambda *_args, **_kwargs: self.fail("clone reached"),
            source_state_probe=self._source_state,
        )
        self.assertEqual(0, code)
        raw = stream.getvalue().encode().rstrip(b"\n")
        value = json.loads(raw)
        self.assertEqual("planned", value["status"])
        self.assertEqual(_canonical(value), raw)
        self.assertFalse((self.root / ".a0x-runtime").exists())

    def test_cli_refusal_is_stable_and_creates_no_output(self) -> None:
        module = self._cli_module()
        arguments = self._cli_arguments()
        index = arguments.index("--wheelhouse-manifest-sha256") + 1
        arguments[index] = "0" * 64
        stream = io.StringIO()
        code = module.main(
            arguments,
            root=self.root,
            stdout=stream,
            runner=self._planning_runner,
            clone_file=lambda *_args, **_kwargs: self.fail("clone reached"),
            source_state_probe=self._source_state,
        )
        self.assertEqual(2, code)
        self.assertEqual(
            {"error": {"code": "A0X_GATE_B_BUILDER_REFUSED"}, "status": "refused"},
            json.loads(stream.getvalue()),
        )
        self.assertFalse((self.root / ".a0x-runtime").exists())


if __name__ == "__main__":
    unittest.main()
