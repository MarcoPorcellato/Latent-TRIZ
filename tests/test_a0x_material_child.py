from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tests.a0x_test_support import artifact, authorization_documents, pair_binding
from latent_triz.a0x_contract import Leg

ROOT = Path(__file__).resolve().parents[1]
CHILD = ROOT / "scripts" / "a0x_material_child.py"
_DEFAULT_EXECUTOR = object()


def load_child_module():
    spec = importlib.util.spec_from_file_location("a0x_material_child", CHILD)
    if spec is None or spec.loader is None:
        raise AssertionError("A0X material child module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class A0XMaterialChildTests(unittest.TestCase):
    def test_child_entrypoint_exposes_an_injected_executor_seam(self) -> None:
        self.assertTrue(CHILD.is_file(), "the fixed child entrypoint must exist")
        module = load_child_module()
        self.assertTrue(callable(module.run_child))

    def _fixture(self) -> tuple[Path, dict[str, object], Path, Path]:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        git = root / ".git"
        (git / "refs" / "heads").mkdir(parents=True)
        (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
        (git / "refs" / "heads" / "main").write_text("a" * 40 + "\n", encoding="ascii")
        child = root / "scripts" / "a0x_material_child.py"
        child.parent.mkdir(parents=True)
        child.write_bytes(b"synthetic-child\n")
        python = root / ".a0x-runtime" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"synthetic-python\n")
        authorization = root / ".a0x-runtime" / "authorizations" / "a0" / "gpt2" / "a0x-a0-gpt2-run-1.json"
        authorization.parent.mkdir(parents=True)
        pair = pair_binding(Leg.A0, "gpt2")
        contract = root / "experiments" / "a0x-six-model" / "material-execution-contract.json"
        contract.parent.mkdir(parents=True)
        material_contract = self._v2_material_contract()
        contract.write_bytes(json.dumps(material_contract, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        _dossier, authorization_document, _chain = authorization_documents(pair)
        contract_ccp = material_contract["ccp"]
        authorization_document["ccp"] = {
            "executable_name": "commit-ci-preflight",
            "source_commit": contract_ccp["source_commit"],
            "qualified_source_tree": contract_ccp["source_tree"],
            "sha256": contract_ccp["sha256"],
            "version": contract_ccp["version"],
        }
        authorization_document["guard_launch"]["ccp"]["sha256"] = contract_ccp["sha256"]
        authorization_document["qualification_evidence"]["ccp"] = {
            "executable_name": "commit-ci-preflight",
            "source_commit": contract_ccp["source_commit"],
            "qualified_source_tree": contract_ccp["source_tree"],
            "binary_sha256": contract_ccp["sha256"],
            "version": contract_ccp["version"],
        }
        authorization_document["material_contract_raw_sha256"] = hashlib.sha256(contract.read_bytes()).hexdigest()
        authorization_document["guard_launch"]["child_script"]["sha256"] = hashlib.sha256(child.read_bytes()).hexdigest()
        authorization_document["guard_launch"]["python"]["sha256"] = hashlib.sha256(python.read_bytes()).hexdigest()
        authorization.write_bytes(json.dumps(authorization_document, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        descriptor = {
            "descriptor_profile": "a0x-material-child-descriptor-v1",
            "source_head": "a" * 40,
            "cwd_kind": "repository_root",
            "pair_binding": pair,
            "child_script": {
                "role": "child",
                "path": "scripts/a0x_material_child.py",
                "sha256": hashlib.sha256(child.read_bytes()).hexdigest(),
            },
            "python": {
                "role": "python",
                "path": str(python.resolve()),
                "sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
            },
            "environment_template": [
                "HF_HUB_OFFLINE=1",
                "TRANSFORMERS_OFFLINE=1",
                "HF_DATASETS_OFFLINE=1",
                "TOKENIZERS_PARALLELISM=false",
                "PYTHONNOUSERSITE=1",
            ],
            "runtime_files": [
                {
                    "role": "authorization",
                    "path": ".a0x-runtime/authorizations/a0/gpt2/a0x-a0-gpt2-run-1.json",
                    "sha256": hashlib.sha256(authorization.read_bytes()).hexdigest(),
                },
                {
                    "role": "material_contract",
                    "path": "experiments/a0x-six-model/material-execution-contract.json",
                    "sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
                },
            ],
            "execution": {
                "network": "offline",
                "generation": "forbidden",
                "trust_remote_code": False,
                "device": "cpu",
                "dtype": "float32",
                "outer_timeout_seconds": 3600,
                "internal_budget_seconds": 3300,
                "cleanup_margin_seconds": 300,
            },
        }
        launch = root / ".a0x-runtime" / "launches" / "a0" / "gpt2" / "a0x-a0-gpt2-run-1.json"
        launch.parent.mkdir(parents=True)
        launch.write_bytes(json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return root, descriptor, child, python

    @staticmethod
    def _v2_material_contract() -> dict[str, object]:
        """Build a schema-valid public-safe V2 contract for child TDD.

        The synthetic authorization remains intentionally private.  The
        contract itself has no executable path, cache path, raw argv, or
        environment values, matching the public V2 boundary.
        """
        schema = json.loads(
            (ROOT / "schemas" / "a0x-material-execution-contract.schema.json").read_text(encoding="utf-8")
        )
        ccp = schema["$defs"]["ccp"]["properties"]
        plan = schema["$defs"]["plan_binding"]["properties"]
        return {
            "artifact_class": "a0x-material-execution-contract",
            "contract_version": schema["properties"]["contract_version"]["const"],
            "repository": "MarcoPorcellato/Latent-TRIZ",
            "ccp": {
                "producer_role": ccp["producer_role"]["const"],
                "source_commit": ccp["source_commit"]["const"],
                "source_tree": ccp["source_tree"]["const"],
                "sha256": ccp["sha256"]["const"],
                "version": ccp["version"]["const"],
                "qualification_status": ccp["qualification_status"]["const"],
                "command_roles": ccp["command_roles"]["const"],
                "hash_before_command": ccp["hash_before_command"]["const"],
                "matrix_plan_profile": ccp["matrix_plan_profile"]["const"],
                "matrix_config_binding": {"locator": "repository/.commit-ci-preflight.toml", "raw_sha256": "1" * 64},
                "matrix_policy_binding": {"locator": "repository/.commit-ci-policy-v2.toml", "raw_sha256": "2" * 64},
                "location_roles": ccp["location_roles"]["const"],
                "matrix_plan_binding": {
                    name: plan[name]["const"] for name in (
                        "plan_output_sha256", "outer_digest", "python311_digest", "python312_digest",
                    )
                },
            },
            "offline": {"network": False, "generation": False, "local_cpu_float32": True},
            "max_run_count": 1,
            "stop_boundaries": ["before_model_load", "after_first_terminal_outcome", "after_one_sealed_target_read"],
        }

    @staticmethod
    def _environment() -> dict[str, str]:
        return {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_DATASETS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONNOUSERSITE": "1",
        }

    def _run(self, *, root: Path, child: Path, python: Path, argv: list[str], executor=_DEFAULT_EXECUTOR,
             production_executor_factory=None, source_head_probe=None, environment=None, cwd=None) -> tuple[int, dict[str, object], list[dict[str, object]]]:
        module = load_child_module()
        stream = io.StringIO()
        received: list[dict[str, object]] = []
        if executor is _DEFAULT_EXECUTOR:
            def executor(value):
                received.append(dict(value))
                return {"status": "null"}
        code = module.run_child(
            argv,
            root=root,
            execute_descriptor=executor,
            production_executor_factory=production_executor_factory,
            source_head_probe=source_head_probe or (lambda: "a" * 40),
            environment=self._environment() if environment is None else environment,
            cwd=root if cwd is None else cwd,
            child_script_path=child,
            python_executable=python,
            stdout=stream,
        )
        line = stream.getvalue()
        self.assertTrue(line.endswith("\n"))
        self.assertEqual(1, len(line.splitlines()))
        return code, json.loads(line), received

    def test_only_fixed_launch_descriptor_argument_is_accepted(self) -> None:
        root, _descriptor, child, python = self._fixture()
        forbidden = (
            ["--model", "gpt2"], ["--leg", "a0"], ["--revision", "a" * 40],
            ["--output", "results/"], ["--target", "data/private"],
            ["--timeout", "3600"], ["--command", "python"],
            ["--launch-descriptor", "other.json"],
        )
        for argv in forbidden:
            with self.subTest(argv=argv):
                code, terminal, received = self._run(root=root, child=child, python=python, argv=list(argv))
                self.assertEqual(2, code)
                self.assertEqual("refused", terminal["exit_class"])
                self.assertEqual([], received)

    def test_valid_descriptor_is_verified_before_injected_executor(self) -> None:
        root, descriptor, child, python = self._fixture()
        code, terminal, received = self._run(
            root=root,
            child=child,
            python=python,
            argv=["--launch-descriptor", ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json"],
        )
        self.assertEqual(0, code)
        self.assertEqual("completed", terminal["exit_class"])
        self.assertEqual("null", terminal["terminal_status"])
        self.assertEqual([descriptor], received)

    def test_descriptor_drift_refuses_before_executor(self) -> None:
        root, descriptor, child, python = self._fixture()
        launch = root / ".a0x-runtime" / "launches" / "a0" / "gpt2" / "a0x-a0-gpt2-run-1.json"
        mutations = {
            "source_head": lambda value: value.__setitem__("source_head", "b" * 40),
            "cwd_kind": lambda value: value.__setitem__("cwd_kind", "host_path"),
            "child_hash": lambda value: value["child_script"].__setitem__("sha256", "0" * 64),
            "python_role": lambda value: value["python"].__setitem__("role", "other"),
            "python_hash": lambda value: value["python"].__setitem__("sha256", "0" * 64),
            "environment": lambda value: value["environment_template"].pop(),
            "runtime_hash": lambda value: value["runtime_files"][0].__setitem__("sha256", "0" * 64),
            "network": lambda value: value["execution"].__setitem__("network", "enabled"),
            "generation": lambda value: value["execution"].__setitem__("generation", "allowed"),
            "trust_remote_code": lambda value: value["execution"].__setitem__("trust_remote_code", True),
            "device": lambda value: value["execution"].__setitem__("device", "cuda"),
            "dtype": lambda value: value["execution"].__setitem__("dtype", "float16"),
            "deadline": lambda value: value["execution"].__setitem__("internal_budget_seconds", 3299),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = copy.deepcopy(descriptor)
                mutate(candidate)
                launch.write_bytes(json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode("utf-8"))
                code, terminal, received = self._run(
                    root=root, child=child, python=python,
                    argv=["--launch-descriptor", ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json"],
                )
                self.assertEqual(2, code)
                self.assertEqual("refused", terminal["exit_class"])
                self.assertEqual([], received)

    def test_import_and_help_do_not_import_model_libraries_or_touch_fixture_files(self) -> None:
        root, _descriptor, child, python = self._fixture()
        before_child = child.read_bytes()
        before_python = python.read_bytes()
        probe = "\n".join(
            (
                "import importlib.util",
                "import io",
                "import pathlib",
                "import sys",
                f"script = pathlib.Path({str(CHILD)!r})",
                "spec = importlib.util.spec_from_file_location('a0x_material_child_probe', script)",
                "assert spec is not None and spec.loader is not None",
                "module = importlib.util.module_from_spec(spec)",
                "spec.loader.exec_module(module)",
                "assert 'torch' not in sys.modules",
                "assert 'transformers' not in sys.modules",
                "stream = io.StringIO()",
                "assert module.run_child(['--help'], stdout=stream) == 0",
                "assert '--launch-descriptor' in stream.getvalue()",
            )
        )
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(before_child, child.read_bytes())
        self.assertEqual(before_python, python.read_bytes())

    def test_missing_production_executor_is_terminal_and_does_not_construct_material_runtime(self) -> None:
        root, _descriptor, child, python = self._fixture()
        code, terminal, received = self._run(
            root=root,
            child=child,
            python=python,
            argv=["--launch-descriptor", ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json"],
            executor=None,
            production_executor_factory=lambda **_kwargs: None,
        )
        self.assertEqual(3, code)
        self.assertEqual("runtime_unavailable", terminal["exit_class"])
        self.assertEqual([], received)

    def test_default_factory_binds_the_production_adapter_after_static_checks(self) -> None:
        root, descriptor, _child, _python = self._fixture()
        module = load_child_module()
        executor = module._production_executor_factory(root=root, descriptor=descriptor)
        self.assertTrue(callable(executor))

    def test_default_source_head_probe_and_production_factory_reach_executor_after_static_checks(self) -> None:
        root, descriptor, child, python = self._fixture()
        module = load_child_module()
        received: list[dict[str, object]] = []
        stream = io.StringIO()
        code = module.run_child(
            ["--launch-descriptor", ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json"],
            root=root,
            source_head_probe=None,
            production_executor_factory=lambda **_kwargs: lambda value: received.append(dict(value)) or {"status": "null"},
            environment=self._environment(), cwd=root,
            child_script_path=child, python_executable=python, stdout=stream,
        )
        self.assertEqual(0, code)
        self.assertEqual(descriptor, received[0])
        self.assertEqual(
            {"artifact_class": "a0x-material-child-terminal", "exit_class": "completed", "terminal_status": "null"},
            json.loads(stream.getvalue()),
        )

    def test_default_head_reader_is_pure_python_and_supports_gitdir_packed_refs(self) -> None:
        module = load_child_module()
        self.assertNotIn("subprocess", module.__dict__)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = root / "metadata"
            metadata.mkdir()
            (root / ".git").write_text(f"gitdir: {metadata}\n", encoding="utf-8")
            (metadata / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (metadata / "packed-refs").write_text(
                "# pack-refs with: peeled fully-peeled\n" + "b" * 40 + " refs/heads/main\n",
                encoding="ascii",
            )
            self.assertEqual("b" * 40, module._default_source_head_probe(root))

    def test_default_head_reader_rejects_symbolic_or_ambiguous_refs(self) -> None:
        module = load_child_module()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            git = root / ".git"
            (git / "refs" / "heads").mkdir(parents=True)
            (git / "HEAD").write_text("ref: refs/tags/v1\n", encoding="ascii")
            self.assertEqual("", module._default_source_head_probe(root))
            (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git / "refs" / "heads" / "main").write_text("ref: refs/heads/other\n", encoding="ascii")
            self.assertEqual("", module._default_source_head_probe(root))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            git = root / ".git"
            git.mkdir()
            (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git / "packed-refs").write_text(
                "c" * 40 + " refs/heads/main\n" + "d" * 40 + " refs/heads/main\n",
                encoding="ascii",
            )
            self.assertEqual("", module._default_source_head_probe(root))

    def test_default_head_reader_refuses_oversized_metadata_without_full_read(self) -> None:
        module = load_child_module()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            git = root / ".git"
            git.mkdir()
            (git / "HEAD").write_bytes(b"x" * (module._GIT_SMALL_FILE_BYTES + 1))
            with patch.object(Path, "read_bytes", side_effect=AssertionError("oversized HEAD must not be fully read")):
                self.assertEqual("", module._default_source_head_probe(root))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            git = root / ".git"
            git.mkdir()
            (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git / "packed-refs").write_bytes(b"x" * (module._GIT_PACKED_REFS_BYTES + 1))
            original_read_bytes = Path.read_bytes

            def forbid_packed_read(path: Path) -> bytes:
                if path.name == "packed-refs":
                    raise AssertionError("oversized packed refs must not be fully read")
                return original_read_bytes(path)

            with patch.object(Path, "read_bytes", forbid_packed_read):
                self.assertEqual("", module._default_source_head_probe(root))

    def test_malformed_but_rehashed_runtime_authorization_or_contract_refuses_before_executor(self) -> None:
        root, descriptor, child, python = self._fixture()
        authorization_path = root / ".a0x-runtime" / "authorizations" / "a0" / "gpt2" / "a0x-a0-gpt2-run-1.json"
        contract_path = root / "experiments" / "a0x-six-model" / "material-execution-contract.json"
        launch = root / ".a0x-runtime" / "launches" / "a0" / "gpt2" / "a0x-a0-gpt2-run-1.json"
        for name, path, mutate in (
            ("authorization", authorization_path, lambda value: value.__setitem__("max_guard_exec_count", 2)),
            ("contract", contract_path, lambda value: value["offline"].__setitem__("network", True)),
        ):
            with self.subTest(name=name):
                candidate = json.loads(path.read_text(encoding="utf-8"))
                mutate(candidate)
                path.write_bytes(json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode("utf-8"))
                rewritten = copy.deepcopy(descriptor)
                rewritten["runtime_files"][0 if name == "authorization" else 1]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                launch.write_bytes(json.dumps(rewritten, sort_keys=True, separators=(",", ":")).encode("utf-8"))
                code, terminal, received = self._run(
                    root=root, child=child, python=python,
                    argv=["--launch-descriptor", ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json"],
                )
                self.assertEqual(2, code)
                self.assertEqual("refused", terminal["exit_class"])
                self.assertEqual([], received)

    def test_keyboard_interrupt_from_executor_is_not_swallowed(self) -> None:
        root, _descriptor, child, python = self._fixture()
        module = load_child_module()
        with self.assertRaises(KeyboardInterrupt):
            module.run_child(
                ["--launch-descriptor", ".a0x-runtime/launches/a0/gpt2/a0x-a0-gpt2-run-1.json"],
                root=root,
                execute_descriptor=lambda _value: (_ for _ in ()).throw(KeyboardInterrupt()),
                source_head_probe=lambda: "a" * 40,
                environment=self._environment(), cwd=root,
                child_script_path=child, python_executable=python, stdout=io.StringIO(),
            )


if __name__ == "__main__":
    unittest.main()
