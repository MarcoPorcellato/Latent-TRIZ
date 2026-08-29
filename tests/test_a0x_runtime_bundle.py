from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

from latent_triz.a0x_contract import PairBinding
from latent_triz.a0x_material_contract import derive_runtime_paths
from tests.a0x_test_support import authorization_documents, pair_binding, qualification_receipt


@dataclass
class ConstructibleRuntimeBundle:
    """One prepared Task-2 bundle shared unchanged by every static boundary."""

    temporary: tempfile.TemporaryDirectory[str]
    root: Path
    request: Any
    receipt: dict[str, Any]

    def close(self) -> None:
        self.temporary.cleanup()


def _runtime_preparation_fixture() -> tuple[tempfile.TemporaryDirectory[str], Path, Any]:
    from latent_triz.a0x_runtime_bundle import RuntimePreparationRequest

    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    pair = PairBinding.from_mapping(pair_binding())
    source_head = "a" * 40
    paths = derive_runtime_paths(pair, source_head=source_head)
    contract = json.loads(
        (Path(__file__).parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text(
            encoding="utf-8",
        ),
    )
    contract_path = root / "experiments/a0x-six-model/material-execution-contract.json"
    contract_path.parent.mkdir(parents=True)
    contract_path.write_bytes(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode())
    dossier, _authorization, _chain = authorization_documents(pair.as_mapping())
    dossier["implementation_source_head"] = source_head
    dossier["material_contract_raw_sha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    dossier["runtime_authorization_path"] = paths.authorization_path
    fixed_dossier = "experiments/a0x-six-model/approval-dossiers/a0/gpt2.json"
    dossier_path = root / fixed_dossier
    dossier_path.parent.mkdir(parents=True)
    dossier_path.write_bytes(json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode())
    receipt_path = root / paths.qualification_receipt_path
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_bytes(qualification_receipt(source_head))
    child_path = root / "scripts/a0x_material_child.py"
    child_path.parent.mkdir(parents=True)
    child_path.write_bytes(b"synthetic child")
    ccp_path = root / "bin/commit-ci-preflight"
    ccp_path.parent.mkdir(parents=True)
    ccp_path.write_bytes(b"synthetic ccp")
    ccp_path.chmod(0o700)
    python_path = root / "bin/python"
    python_path.write_bytes(b"synthetic python")
    python_path.chmod(0o700)
    return temporary, root, RuntimePreparationRequest(
        fixed_dossier=fixed_dossier,
        qualification_receipt=receipt_path,
        ccp_executable=ccp_path,
        python_executable=python_path,
        public_evidence_commit="e" * 40,
        authorization_id="a0x-auth-a0-gpt2-attempt-01",
        attempt_id="a0x-a0-gpt2-attempt-01",
    )


@contextmanager
def _synthetic_ccp_hash(request: Any):
    """Keep the inert executable target-free while preserving the frozen CCP identity."""
    from latent_triz import a0x_runtime_bundle

    expected = json.loads(
        (Path(__file__).parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text(
            encoding="utf-8",
        ),
    )["ccp"]["sha256"]
    actual = a0x_runtime_bundle.sha256_file
    ccp = request.ccp_executable.resolve()
    with patch(
        "latent_triz.a0x_runtime_bundle.sha256_file",
        side_effect=lambda path: expected if Path(path).resolve() == ccp else actual(path),
    ):
        yield


def prepare_constructible_runtime_bundle() -> ConstructibleRuntimeBundle:
    """Prepare one v2 bundle without a model, target, process, or CCP invocation."""
    from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle

    temporary, root, request = _runtime_preparation_fixture()
    with (
        _synthetic_ccp_hash(request),
        patch(
            "latent_triz.a0x_runtime_bundle.planned_material_dossiers",
            return_value={("a0", "gpt2"): request.fixed_dossier},
        ),
    ):
        receipt = prepare_runtime_bundle(
            root,
            request,
            source_state_probe=lambda: ("a" * 40, True),
            ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
        )
    return ConstructibleRuntimeBundle(temporary=temporary, root=root, request=request, receipt=receipt)


class A0XRuntimeBundleTests(unittest.TestCase):
    @staticmethod
    def _cli_module():
        path = Path(__file__).parents[1] / "scripts/a0x_prepare_runtime.py"
        specification = importlib.util.spec_from_file_location("a0x_prepare_runtime_test", path)
        if specification is None or specification.loader is None:
            raise AssertionError("runtime preparation CLI is unavailable")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module

    def _fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, object]:
        return _runtime_preparation_fixture()

    @contextmanager
    def _synthetic_ccp_hash(self, request):
        with _synthetic_ccp_hash(request):
            yield

    @contextmanager
    def _without_model_modules(self):
        """Make target-free import/execution assertions independent of suite history."""
        missing = object()
        saved = {name: sys.modules.get(name, missing) for name in ("torch", "transformers")}
        for name in saved:
            sys.modules.pop(name, None)
        try:
            yield
            self.assertNotIn("torch", sys.modules)
            self.assertNotIn("transformers", sys.modules)
        finally:
            for name, module in saved.items():
                sys.modules.pop(name, None)
                if module is not missing:
                    sys.modules[name] = module

    def test_prepares_one_acyclic_bundle_in_dependency_order(self) -> None:
        from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}):
            receipt = prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )
        descriptor = root / receipt["descriptor_path"]
        authorization = root / receipt["authorization_path"]
        mapping = root / receipt["mapping_path"]
        self.assertTrue(descriptor.is_file())
        self.assertTrue(authorization.is_file())
        self.assertTrue(mapping.is_file())
        descriptor_document = json.loads(descriptor.read_text(encoding="utf-8"))
        authorization_document = json.loads(authorization.read_text(encoding="utf-8"))
        mapping_document = json.loads(mapping.read_text(encoding="utf-8"))
        self.assertNotIn("authorization", descriptor_document)
        descriptor_sha256 = hashlib.sha256(descriptor.read_bytes()).hexdigest()
        self.assertEqual(descriptor_sha256, authorization_document["guard_launch"]["launch_descriptor"]["sha256"])
        self.assertEqual(receipt["descriptor_path"], mapping_document["descriptor"]["path"])
        self.assertEqual(descriptor_sha256, mapping_document["descriptor"]["sha256"])

    def test_one_constructible_bundle_crosses_all_static_boundaries(self) -> None:
        """One Task-2 bundle, unchanged, is accepted by every static boundary."""
        from latent_triz.a0x_ccp_executor import ProcessResult, launch_fixed_dossier
        from latent_triz.a0x_production_adapter import ProductionFactories, build_production_executor
        from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight, _FakeProcess
        from tests.test_a0x_material_child import load_child_module

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        with self._synthetic_ccp_hash(request), patch(
            "latent_triz.a0x_runtime_bundle.planned_material_dossiers",
            return_value={("a0", "gpt2"): request.fixed_dossier},
        ):
            receipt = prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )

        descriptor_path = root / receipt["descriptor_path"]
        authorization_path = root / receipt["authorization_path"]
        contract_path = root / "experiments/a0x-six-model/material-execution-contract.json"
        descriptor_raw = descriptor_path.read_bytes()
        authorization_raw = authorization_path.read_bytes()
        contract_raw = contract_path.read_bytes()
        descriptor = json.loads(descriptor_raw)
        expected = {
            "source_head": receipt["source_head"],
            "pair_binding": receipt["pair_binding"],
            "authorization_raw_sha256": hashlib.sha256(authorization_raw).hexdigest(),
            "descriptor_raw_sha256": hashlib.sha256(descriptor_raw).hexdigest(),
            "material_contract_raw_sha256": hashlib.sha256(contract_raw).hexdigest(),
        }

        child_received: list[dict[str, object]] = []
        child_contexts: list[object] = []
        def child_production_factory(*, root, descriptor):
            child_received.append(dict(descriptor))
            return build_production_executor(
                root=root,
                descriptor=descriptor,
                factories=ProductionFactories(
                    dependency_builder=lambda context: child_contexts.append(context) or object(),
                    lifecycle_runner=lambda **_kwargs: {"terminal_outcome": {"status": "null"}},
                ),
            )

        child_code = load_child_module().run_child(
            ["--launch-descriptor", receipt["descriptor_path"]],
            root=root,
            production_executor_factory=child_production_factory,
            source_head_probe=lambda: expected["source_head"],
            environment={
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
                "TOKENIZERS_PARALLELISM": "false", "PYTHONNOUSERSITE": "1",
            },
            cwd=root,
            child_script_path=root / "scripts/a0x_material_child.py",
            python_executable=request.python_executable,
            stdout=io.StringIO(),
        )
        self.assertEqual(0, child_code)
        self.assertEqual([descriptor], child_received)
        self.assertEqual(1, len(child_contexts))
        child_context = child_contexts[0]
        self.assertEqual(expected["source_head"], child_context.source_head)
        self.assertEqual(expected["pair_binding"], child_context.pair.as_mapping())
        self.assertEqual(expected["authorization_raw_sha256"], child_context.authorization_raw_sha256)
        self.assertEqual(expected["descriptor_raw_sha256"], child_context.descriptor_commitment)
        self.assertEqual(expected["material_contract_raw_sha256"], child_context.material_contract_raw_sha256)

        production_contexts: list[object] = []
        production = build_production_executor(
            root=root,
            descriptor=descriptor,
            factories=ProductionFactories(
                dependency_builder=lambda context: production_contexts.append(context) or object(),
                lifecycle_runner=lambda **_kwargs: {"terminal_outcome": {"status": "null"}},
            ),
        )
        self.assertEqual({"status": "null"}, production(descriptor))
        self.assertEqual(1, len(production_contexts))
        production_context = production_contexts[0]
        self.assertEqual(expected["source_head"], production_context.source_head)
        self.assertEqual(expected["pair_binding"], production_context.pair.as_mapping())
        self.assertEqual(expected["authorization_raw_sha256"], production_context.authorization_raw_sha256)
        self.assertEqual(expected["descriptor_raw_sha256"], production_context.descriptor_commitment)
        self.assertEqual(expected["material_contract_raw_sha256"], production_context.material_contract_raw_sha256)

        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
        outer_process = _FakeProcess(ProcessResult(
            returncode=0,
            stdout_sha256=hashlib.sha256(terminal).hexdigest(),
            stdout_bytes=len(terminal),
            stderr_sha256=hashlib.sha256(b"").hexdigest(),
            stderr_bytes=0,
            stdout_prefix=terminal,
        ))
        ccp_sha256 = json.loads(contract_raw)["ccp"]["sha256"]
        executor_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
        ccp_module = __import__("latent_triz.a0x_ccp_executor", fromlist=["_validate_authorization"])
        real_validate_authorization = ccp_module._validate_authorization
        real_validate_file_hash = ccp_module._validate_file_hash
        outer_contract_hashes: list[str] = []
        outer_descriptor_hashes: list[tuple[str, str]] = []

        def validate_authorization_spy(**kwargs):
            launch = real_validate_authorization(**kwargs)
            outer_contract_hashes.append(kwargs["authorization"]["material_contract_raw_sha256"])
            return launch

        def validate_file_hash_spy(path, expected_hash, label):
            result = real_validate_file_hash(path, expected_hash, label)
            if label == "launch descriptor":
                outer_descriptor_hashes.append((
                    expected_hash,
                    hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                ))
            return result

        with (
            patch(
                "latent_triz.a0x_ccp_executor.planned_material_dossiers",
                return_value={("a0", "gpt2"): request.fixed_dossier},
            ),
            patch(
                "latent_triz.a0x_ccp_executor.sha256_file",
                side_effect=lambda path: ccp_sha256 if Path(path).resolve() == request.ccp_executable.resolve()
                else executor_sha256_file(path),
            ),
            patch("latent_triz.a0x_ccp_executor._validate_authorization", side_effect=validate_authorization_spy),
            patch("latent_triz.a0x_ccp_executor._validate_file_hash", side_effect=validate_file_hash_spy),
        ):
            outer = launch_fixed_dossier(
                repository_root=root,
                fixed_dossier=request.fixed_dossier,
                source_head_probe=lambda: expected["source_head"],
                process_executor=outer_process,
                guard_preflight_producer=_FakeGuardPreflight(),
            )
        self.assertEqual(expected["source_head"], outer["source_head"])
        self.assertEqual(expected["pair_binding"], outer["pair_binding"])
        self.assertTrue((root / outer["claim_path"]).is_file())
        runtime = derive_runtime_paths(expected["pair_binding"], source_head=expected["source_head"])
        pre_run = json.loads((root / runtime.observation_directory / "pre-run-observation.json").read_text())
        self.assertEqual(expected["authorization_raw_sha256"], pre_run["authorization_raw_sha256"])
        self.assertTrue(outer_descriptor_hashes)
        self.assertTrue(all(pair == (expected["descriptor_raw_sha256"], expected["descriptor_raw_sha256"])
                            for pair in outer_descriptor_hashes))
        self.assertEqual([expected["material_contract_raw_sha256"]], outer_contract_hashes)

    def test_tamper_matrix_refuses_before_process_or_lifecycle_seams(self) -> None:
        """Every independently prepared bundle fails closed for one altered binding."""
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, ProcessResult, launch_fixed_dossier
        from latent_triz.a0x_production_adapter import (
            A0XProductionAdapterError,
            ProductionFactories,
            build_production_executor,
        )
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight, _FakeProcess
        from tests.test_a0x_material_child import load_child_module

        def rewrite(path: Path, document: dict[str, object]) -> None:
            path.write_bytes(json.dumps(document, sort_keys=True, separators=(",", ":")).encode())

        def mutate_authorization_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            (bundle.root / bundle.receipt["authorization_path"]).write_bytes(b"{}")

        def mutate_descriptor_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            (bundle.root / bundle.receipt["descriptor_path"]).write_bytes(b"{}")

        def mutate_authorization_descriptor_hash(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["authorization_path"]
            document = json.loads(path.read_text())
            document["guard_launch"]["launch_descriptor"]["sha256"] = "0" * 64
            rewrite(path, document)

        def mutate_descriptor_authorization_path(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["descriptor_path"]
            document = json.loads(path.read_text())
            document["authorization_reference"]["path"] = ".a0x-runtime/authorizations/a0/gpt2/other.json"
            rewrite(path, document)

        def mutate_contract_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            (bundle.root / "experiments/a0x-six-model/material-execution-contract.json").write_bytes(b"{}")

        def mutate_mapping_descriptor_path(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["mapping_path"]
            document = json.loads(path.read_text())
            document["descriptor"]["path"] = ".a0x-runtime/launches/a0/gpt2/other.json"
            rewrite(path, document)

        def mutate_mapping_descriptor_hash(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["mapping_path"]
            document = json.loads(path.read_text())
            document["descriptor"]["sha256"] = "0" * 64
            rewrite(path, document)

        def mutate_receipt_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / derive_runtime_paths(bundle.receipt["pair_binding"], source_head=bundle.receipt["source_head"]).qualification_receipt_path
            path.write_bytes(b"{}")

        def mutate_receipt_id(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["authorization_path"]
            document = json.loads(path.read_text())
            document["qualification_evidence"]["qualification_receipt_id"] = "sha256:" + "0" * 64
            rewrite(path, document)

        def mutate_receipt_source(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / derive_runtime_paths(bundle.receipt["pair_binding"], source_head=bundle.receipt["source_head"]).qualification_receipt_path
            document = json.loads(path.read_text())
            document["receipt"]["repository"]["commit_sha"] = "b" * 40
            rewrite(path, document)

        def mutate_receipt_generation(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / derive_runtime_paths(bundle.receipt["pair_binding"], source_head=bundle.receipt["source_head"]).qualification_receipt_path
            document = json.loads(path.read_text())
            document["receipt"]["run"]["generation"] = 2
            rewrite(path, document)

        def mutate_ccp_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            bundle.request.ccp_executable.write_bytes(b"tampered ccp")

        def mutate_python_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            bundle.request.python_executable.write_bytes(b"tampered python")

        def mutate_child_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            (bundle.root / "scripts/a0x_material_child.py").write_bytes(b"tampered child")

        def mutate_source_head(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["descriptor_path"]
            document = json.loads(path.read_text())
            document["source_head"] = "b" * 40
            rewrite(path, document)

        def mutate_pair(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["descriptor_path"]
            document = json.loads(path.read_text())
            document["pair_binding"]["leg"] = "r1"
            rewrite(path, document)

        cases = {
            "authorization_bytes": mutate_authorization_bytes,
            "descriptor_bytes": mutate_descriptor_bytes,
            "authorization_descriptor_hash": mutate_authorization_descriptor_hash,
            "descriptor_authorization_path": mutate_descriptor_authorization_path,
            "contract_bytes": mutate_contract_bytes,
            "mapping_descriptor_path": mutate_mapping_descriptor_path,
            "mapping_descriptor_hash": mutate_mapping_descriptor_hash,
            "qualification_receipt_bytes": mutate_receipt_bytes,
            "qualification_receipt_id": mutate_receipt_id,
            "qualification_receipt_source": mutate_receipt_source,
            "qualification_receipt_generation": mutate_receipt_generation,
            "ccp_bytes": mutate_ccp_bytes,
            "python_bytes": mutate_python_bytes,
            "child_bytes": mutate_child_bytes,
            "source_head": mutate_source_head,
            "pair": mutate_pair,
        }
        child_checked = {
            "authorization_bytes", "descriptor_bytes", "authorization_descriptor_hash",
            "descriptor_authorization_path", "contract_bytes", "python_bytes", "child_bytes",
            "source_head", "pair",
        }
        production_checked = {
            "authorization_bytes", "descriptor_bytes", "authorization_descriptor_hash",
            "descriptor_authorization_path", "contract_bytes", "source_head", "pair",
        }
        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
        for name, mutate in cases.items():
            with self.subTest(name=name):
                bundle = prepare_constructible_runtime_bundle()
                self.addCleanup(bundle.close)
                mutate(bundle)
                descriptor_path = bundle.root / bundle.receipt["descriptor_path"]
                try:
                    descriptor = json.loads(descriptor_path.read_text())
                except json.JSONDecodeError:
                    descriptor = {"invalid": True}

                if name in child_checked:
                    child_called: list[object] = []
                    child_code = load_child_module().run_child(
                        ["--launch-descriptor", bundle.receipt["descriptor_path"]],
                        root=bundle.root,
                        execute_descriptor=lambda value: child_called.append(value) or {"status": "null"},
                        source_head_probe=lambda: "a" * 40,
                        environment={
                            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1",
                            "TOKENIZERS_PARALLELISM": "false", "PYTHONNOUSERSITE": "1",
                        },
                        cwd=bundle.root,
                        child_script_path=bundle.root / "scripts/a0x_material_child.py",
                        python_executable=bundle.request.python_executable,
                        stdout=io.StringIO(),
                    )
                    self.assertEqual(2, child_code)
                    self.assertEqual([], child_called)

                lifecycle_called: list[object] = []
                if name in production_checked:
                    with self.assertRaises(A0XProductionAdapterError):
                        build_production_executor(
                            root=bundle.root,
                            descriptor=descriptor,
                            factories=ProductionFactories(
                                dependency_builder=lambda _context: lifecycle_called.append("dependency") or object(),
                                lifecycle_runner=lambda **_kwargs: lifecycle_called.append("lifecycle") or {"terminal_outcome": {"status": "null"}},
                            ),
                        )
                    self.assertEqual([], lifecycle_called)

                outer_process = _FakeProcess(ProcessResult(
                    returncode=0,
                    stdout_sha256=hashlib.sha256(terminal).hexdigest(),
                    stdout_bytes=len(terminal),
                    stderr_sha256=hashlib.sha256(b"").hexdigest(),
                    stderr_bytes=0,
                    stdout_prefix=terminal,
                ))
                ccp_sha256 = json.loads(
                    (bundle.root / "experiments/a0x-six-model/material-execution-contract.json").read_text(),
                ).get("ccp", {}).get("sha256", "0" * 64)
                executor_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
                with (
                    patch(
                        "latent_triz.a0x_ccp_executor.planned_material_dossiers",
                        return_value={("a0", "gpt2"): bundle.request.fixed_dossier},
                    ),
                    patch(
                        "latent_triz.a0x_ccp_executor.sha256_file",
                        side_effect=lambda path: ccp_sha256 if (
                            Path(path).resolve() == bundle.request.ccp_executable.resolve()
                            and Path(path).read_bytes() == b"synthetic ccp"
                        )
                        else executor_sha256_file(path),
                    ),
                    self.assertRaises(A0XCcpExecutorError),
                ):
                    launch_fixed_dossier(
                        repository_root=bundle.root,
                        fixed_dossier=bundle.request.fixed_dossier,
                        source_head_probe=lambda: "a" * 40,
                        process_executor=outer_process,
                        guard_preflight_producer=_FakeGuardPreflight(),
                    )
                self.assertEqual([], outer_process.calls)

    def test_output_and_runtime_occupancy_refuse_without_a_process(self) -> None:
        from latent_triz.a0x_ccp_executor import A0XCcpExecutorError, ProcessResult, launch_fixed_dossier
        from dataclasses import replace
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle
        from tests.test_a0x_ccp_executor import _FakeGuardPreflight, _FakeProcess

        bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        with self._synthetic_ccp_hash(bundle.request), patch(
            "latent_triz.a0x_runtime_bundle.planned_material_dossiers",
            return_value={("a0", "gpt2"): bundle.request.fixed_dossier},
        ), self.assertRaises(A0XRuntimeBundleError):
            prepare_runtime_bundle(
                bundle.root,
                bundle.request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )

        for field in ("authorization_id", "attempt_id"):
            with self.subTest(field=field), self._synthetic_ccp_hash(bundle.request), patch(
                "latent_triz.a0x_runtime_bundle.planned_material_dossiers",
                return_value={("a0", "gpt2"): bundle.request.fixed_dossier},
            ), self.assertRaises(A0XRuntimeBundleError):
                prepare_runtime_bundle(
                    bundle.root,
                    replace(bundle.request, **{field: "invalid identifier"}),
                    source_state_probe=lambda: ("a" * 40, True),
                    ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                )

        paths = derive_runtime_paths(bundle.receipt["pair_binding"], source_head=bundle.receipt["source_head"])
        claim = bundle.root / paths.claim_path
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.write_bytes(b"occupied")
        terminal = b'{"artifact_class":"a0x-material-child-terminal","exit_class":"completed","terminal_status":"null"}\n'
        process = _FakeProcess(ProcessResult(
            returncode=0,
            stdout_sha256=hashlib.sha256(terminal).hexdigest(), stdout_bytes=len(terminal),
            stderr_sha256=hashlib.sha256(b"").hexdigest(), stderr_bytes=0, stdout_prefix=terminal,
        ))
        ccp_sha256 = json.loads((bundle.root / "experiments/a0x-six-model/material-execution-contract.json").read_text())["ccp"]["sha256"]
        executor_sha256_file = __import__("latent_triz.a0x_ccp_executor", fromlist=["sha256_file"]).sha256_file
        with (
            patch("latent_triz.a0x_ccp_executor.planned_material_dossiers", return_value={("a0", "gpt2"): bundle.request.fixed_dossier}),
            patch(
                "latent_triz.a0x_ccp_executor.sha256_file",
                side_effect=lambda path: ccp_sha256 if (
                    Path(path).resolve() == bundle.request.ccp_executable.resolve()
                    and Path(path).read_bytes() == b"synthetic ccp"
                )
                else executor_sha256_file(path),
            ),
            self.assertRaises(A0XCcpExecutorError),
        ):
            launch_fixed_dossier(
                repository_root=bundle.root,
                fixed_dossier=bundle.request.fixed_dossier,
                source_head_probe=lambda: "a" * 40,
                process_executor=process,
                guard_preflight_producer=_FakeGuardPreflight(),
            )
        self.assertEqual([], process.calls)

    def test_second_preparation_refuses_without_changing_first_bundle_bytes(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        patch_target = "latent_triz.a0x_runtime_bundle.planned_material_dossiers"
        with self._synthetic_ccp_hash(request), patch(patch_target, return_value={("a0", "gpt2"): request.fixed_dossier}):
            receipt = prepare_runtime_bundle(root, request, source_state_probe=lambda: ("a" * 40, True), ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0")
            first_bytes = {name: (root / receipt[f"{name}_path"]).read_bytes() for name in ("descriptor", "authorization", "mapping")}
            with self.assertRaises(A0XRuntimeBundleError):
                prepare_runtime_bundle(root, request, source_state_probe=lambda: ("a" * 40, True), ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0")
        self.assertEqual(first_bytes, {name: (root / receipt[f"{name}_path"]).read_bytes() for name in first_bytes})

    def test_preparation_never_reaches_material_or_process_seams(self) -> None:
        from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        patch_target = "latent_triz.a0x_runtime_bundle.planned_material_dossiers"
        with (
            self._without_model_modules(),
            self._synthetic_ccp_hash(request),
            patch(patch_target, return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch("subprocess.run", side_effect=AssertionError("subprocess.run reached")) as process_run,
            patch("subprocess.Popen", side_effect=AssertionError("subprocess.Popen reached")) as process_open,
            patch("latent_triz.a0x_ccp_executor.launch_fixed_dossier", side_effect=AssertionError("guard launch reached")) as launch,
            patch("latent_triz.a0x_execution.OneShotTargetReader", side_effect=AssertionError("target reader reached")) as target_reader,
            patch("latent_triz.a0x_model_adapter.A0XHiddenStateAdapter", side_effect=AssertionError("model adapter reached")) as model_adapter,
            patch("latent_triz.a0x_production_adapter._default_dependencies", side_effect=AssertionError("model factory reached")) as model_factory,
        ):
            receipt = prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )
        self.assertEqual("prepared", receipt["status"])
        process_run.assert_not_called()
        process_open.assert_not_called()
        launch.assert_not_called()
        target_reader.assert_not_called()
        model_adapter.assert_not_called()
        model_factory.assert_not_called()

    def test_any_pair_scoped_occupancy_refuses_before_bundle_or_material_access(self) -> None:
        from latent_triz.a0x_ccp_executor import runtime_mapping_path
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        categories = (
            "descriptor", "authorization", "mapping", "claim", "observation", "material_workspace", "result_output",
        )
        for category in categories:
            with self.subTest(category=category):
                temporary, root, request = self._fixture()
                self.addCleanup(temporary.cleanup)
                dossier = json.loads((root / request.fixed_dossier).read_text(encoding="utf-8"))
                pair = PairBinding.from_mapping(dossier["pair_binding"])
                runtime = derive_runtime_paths(pair, source_head="a" * 40)
                relative = {
                    "descriptor": runtime.launch_descriptor_path,
                    "authorization": runtime.authorization_path,
                    "mapping": runtime_mapping_path(pair, source_head="a" * 40),
                    "claim": runtime.claim_path,
                    "observation": runtime.observation_directory,
                    "material_workspace": f".a0x-runtime/material/{pair.leg.value}/{pair.model_key}/{pair.run_id}",
                    "result_output": pair.output_path,
                }[category]
                occupied = root / relative
                if category in {"observation", "material_workspace", "result_output"}:
                    occupied.mkdir(parents=True)
                    original = None
                else:
                    occupied.parent.mkdir(parents=True, exist_ok=True)
                    occupied.write_bytes(b"occupied")
                    original = occupied.read_bytes()
                with (
                    self._synthetic_ccp_hash(request),
                    patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
                    patch("subprocess.run", side_effect=AssertionError("subprocess.run reached")) as process_run,
                    patch("subprocess.Popen", side_effect=AssertionError("subprocess.Popen reached")) as process_open,
                    patch("latent_triz.a0x_ccp_executor.launch_fixed_dossier", side_effect=AssertionError("guard launch reached")) as launch,
                    patch("latent_triz.a0x_execution.OneShotTargetReader", side_effect=AssertionError("target reader reached")) as target_reader,
                    patch("latent_triz.a0x_production_adapter._default_dependencies", side_effect=AssertionError("model factory reached")) as model_factory,
                ):
                    with self.assertRaises(A0XRuntimeBundleError):
                        prepare_runtime_bundle(
                            root,
                            request,
                            source_state_probe=lambda: ("a" * 40, True),
                            ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                        )
                self.assertTrue(os.path.lexists(occupied))
                if original is not None:
                    self.assertEqual(original, occupied.read_bytes())
                for bundle_path in (
                    runtime.launch_descriptor_path,
                    runtime.authorization_path,
                    runtime_mapping_path(pair, source_head="a" * 40),
                ):
                    candidate = root / bundle_path
                    if candidate != occupied:
                        self.assertFalse(os.path.lexists(candidate))
                process_run.assert_not_called()
                process_open.assert_not_called()
                launch.assert_not_called()
                target_reader.assert_not_called()
                model_factory.assert_not_called()

    def test_dirty_source_refuses_before_any_runtime_output(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(A0XRuntimeBundleError, "clean checkout"):
            prepare_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, False),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
            )
        self.assertFalse((root / ".a0x-runtime/launches").exists())
        self.assertFalse((root / ".a0x-runtime/authorizations").exists())
        self.assertFalse((root / ".a0x-runtime/bin").exists())

    def test_cli_prepares_sorted_public_receipt_from_shell_free_probes(self) -> None:
        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        cli = self._cli_module()
        output = io.StringIO()

        class Result:
            def __init__(self, stdout: str) -> None:
                self.returncode = 0
                self.stdout = stdout

        def probe(argv, **_kwargs):
            if argv == ["git", "rev-parse", "HEAD"]:
                return Result("a" * 40 + "\n")
            if argv == ["git", "status", "--porcelain", "--untracked-files=all"]:
                return Result("")
            if argv == [str(request.ccp_executable.resolve()), "--version"]:
                return Result("commit-ci-preflight 0.1.0\n")
            raise AssertionError(f"unexpected probe argv: {argv}")

        argv = [
            "--fixed-dossier", request.fixed_dossier,
            "--qualification-receipt", str(request.qualification_receipt),
            "--ccp", str(request.ccp_executable),
            "--python", str(request.python_executable),
            "--public-evidence-commit", request.public_evidence_commit,
            "--authorization-id", request.authorization_id,
            "--attempt-id", request.attempt_id,
        ]
        with (
            self._synthetic_ccp_hash(request),
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch.object(cli.subprocess, "run", side_effect=probe),
        ):
            code = cli.main(argv, root=root, stdout=output)
        self.assertEqual(0, code)
        receipt = json.loads(output.getvalue())
        self.assertEqual("prepared", receipt["status"])
        self.assertEqual(sorted(receipt), list(receipt))

    def test_malformed_contract_refuses_before_creating_any_runtime_document(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        contract_path = root / "experiments/a0x-six-model/material-execution-contract.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        del contract["offline"]
        contract_path.write_bytes(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode())
        dossier_path = root / request.fixed_dossier
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        dossier["material_contract_raw_sha256"] = hashlib.sha256(contract_path.read_bytes()).hexdigest()
        dossier_path.write_bytes(json.dumps(dossier, sort_keys=True, separators=(",", ":")).encode())
        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}):
            with self.assertRaises(A0XRuntimeBundleError):
                prepare_runtime_bundle(
                    root,
                    request,
                    source_state_probe=lambda: ("a" * 40, True),
                    ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                )
        self.assertFalse((root / ".a0x-runtime/launches").exists())
        self.assertFalse((root / ".a0x-runtime/authorizations").exists())
        self.assertFalse((root / ".a0x-runtime/bin").exists())

    def test_cli_malformed_qualification_receipt_returns_refusal_code_two(self) -> None:
        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        request.qualification_receipt.write_bytes(b"{not-json")
        cli = self._cli_module()
        output = io.StringIO()

        class Result:
            def __init__(self, stdout: str) -> None:
                self.returncode = 0
                self.stdout = stdout

        def probe(argv, **_kwargs):
            if argv == ["git", "rev-parse", "HEAD"]:
                return Result("a" * 40 + "\n")
            if argv == ["git", "status", "--porcelain", "--untracked-files=all"]:
                return Result("")
            if argv == [str(request.ccp_executable.resolve()), "--version"]:
                return Result("commit-ci-preflight 0.1.0\n")
            raise AssertionError(f"unexpected probe argv: {argv}")

        argv = [
            "--fixed-dossier", request.fixed_dossier,
            "--qualification-receipt", str(request.qualification_receipt),
            "--ccp", str(request.ccp_executable),
            "--python", str(request.python_executable),
            "--public-evidence-commit", request.public_evidence_commit,
            "--authorization-id", request.authorization_id,
            "--attempt-id", request.attempt_id,
        ]
        with (
            self._synthetic_ccp_hash(request),
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch.object(cli.subprocess, "run", side_effect=probe),
        ):
            code = cli.main(argv, root=root, stdout=output)
        self.assertEqual(2, code)
        self.assertEqual({"status": "refused"}, json.loads(output.getvalue()))
