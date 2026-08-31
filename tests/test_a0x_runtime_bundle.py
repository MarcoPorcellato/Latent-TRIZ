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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from latent_triz.a0x_contract import PairBinding
from latent_triz.a0x_material_contract import derive_runtime_paths
from tests.a0x_test_support import authorization_documents, pair_binding


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
    fixture_root = Path(__file__).parent / "fixtures/a0x/hosted-gate-a/positive"
    gate = json.loads((fixture_root / "gate-b-authorization.json").read_text(encoding="utf-8"))
    gate["source_head"] = source_head
    gate["source_tree"] = "b" * 40
    gate["source_sha"] = source_head
    gate["pair_binding"] = pair.as_mapping()
    evidence_base = f".a0x-runtime/gate-a/evidence/{source_head}"
    fixture_names = {
        "manifest": "hosted-gate-a-evidence.json",
        "attestation_bundle": "hosted-gate-a-attestation.bundle.jsonl",
        "trusted_root": "github-trusted-root.jsonl",
        "transport": "hosted-gate-a-transport.json",
    }
    for name, filename in fixture_names.items():
        path = root / f"{evidence_base}/{filename}"
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (fixture_root / "transport.json").read_bytes() if name == "transport" else f"synthetic-{name}".encode()
        path.write_bytes(raw)
        gate["hosted_inputs"][name] = {"path": f"{evidence_base}/{filename}", "sha256": hashlib.sha256(raw).hexdigest()}
    gate["verification_receipt_path"] = (
        f".a0x-runtime/gate-b-verifications/{source_head}/a0/gpt2/"
        "a0x-auth-a0-gpt2-attempt-01/gate-a-verification-receipt.json"
    )
    policy_path = root / "gate-b/verifier-policy.json"
    policy_path.parent.mkdir(parents=True)
    policy_raw = (fixture_root / "verifier-policy.json").read_bytes()
    policy_path.write_bytes(policy_raw)
    gate["verifier"]["policy_raw_sha256"] = hashlib.sha256(policy_raw).hexdigest()
    gate_path = root / "gate-b/gate-b-authorization.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_bytes(json.dumps(gate, sort_keys=True, separators=(",", ":")).encode())
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
    verifier_path = root / "bin/gh"
    verifier_path.write_bytes(b"synthetic verifier")
    verifier_path.chmod(0o700)
    return temporary, root, RuntimePreparationRequest(
        fixed_dossier=fixed_dossier,
        gate_b_authorization=gate_path,
        verifier_executable=verifier_path,
        verifier_policy=policy_path,
        ccp_executable=ccp_path,
        python_executable=python_path,
        authorization_id="a0x-auth-a0-gpt2-attempt-01",
        attempt_id="a0x-a0-gpt2-attempt-01",
    )


def _synthetic_runtime_readiness(root: Path, pair: PairBinding, source_head: str, python_path: Path):
    """Return closed target-free metadata for the inert runtime fixture."""
    from latent_triz.a0x_contract import sha256_file
    from latent_triz.a0x_runtime_readiness import EXPECTED_API_SYMBOLS, EXPECTED_PACKAGES

    runtime_root = "artifacts/models/gpt2-synthetic"
    runtime = root / runtime_root
    runtime.mkdir(parents=True, exist_ok=True)
    config = {
        "architectures": ["GPT2LMHeadModel"],
        "model_type": "gpt2",
        "n_embd": 768,
        "n_layer": 12,
        "n_positions": 1024,
        "vocab_size": 50257,
    }

    config_raw = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    (runtime / "config.json").write_bytes(config_raw)
    runtime_files = [{
        "path": "config.json",
        "sha256": hashlib.sha256(config_raw).hexdigest(),
        "size_bytes": len(config_raw),
    }]

    source_receipt_path = "results/synthetic/gpt2-runtime-receipt.json"
    source_receipt = root / source_receipt_path
    source_receipt.parent.mkdir(parents=True, exist_ok=True)
    source_receipt.write_bytes(json.dumps({
        "license_id": "MIT",
        "model_id": pair.model_id,
        "revision": pair.revision,
        "runtime_files": runtime_files,
        "runtime_root": runtime_root,
    }, sort_keys=True, separators=(",", ":")).encode())
    audit_path = "docs/synthetic-gpt2-audit.md"
    audit = root / audit_path
    audit.parent.mkdir(parents=True, exist_ok=True)
    pointers = {
        "architecture": "architecture-pointer",
        "effective_context": "context-pointer",
        "expected_runtime_tokenizer_class": "runtime-tokenizer-pointer",
        "fast_offsets_required": "fast-offsets-pointer",
        "final_transformer_block_tuple_index": "final-block-pointer",
        "hidden_size": "hidden-size-pointer",
        "model_type": "model-type-pointer",
        "num_hidden_layers": "layer-count-pointer",
        "tokenizer_metadata_class": "metadata-tokenizer-pointer",
        "vocab_size": "vocab-pointer",
    }
    audit.write_text("\n".join(sorted(pointers.values())) + "\n", encoding="utf-8")

    card_path = "experiments/a0x-six-model/model-cards/gpt2.json"
    card_file = root / card_path
    card_file.parent.mkdir(parents=True, exist_ok=True)
    card = json.loads((Path(__file__).parents[1] / card_path).read_text(encoding="utf-8"))
    audit_sha256 = sha256_file(audit)
    card.update({
        "revision": pair.revision,
        "runtime_root": runtime_root,
        "runtime_files": runtime_files,
        "source_receipt_path": source_receipt_path,
        "source_receipt_sha256": sha256_file(source_receipt),
        "official_audit_path": audit_path,
        "official_audit_sha256": audit_sha256,
        "config_fact_provenance": {
            "source_path": audit_path,
            "source_sha256": audit_sha256,
            "field_pointers": {key: pointers[key] for key in (
                "model_type", "architecture", "num_hidden_layers", "hidden_size",
                "vocab_size", "effective_context", "final_transformer_block_tuple_index",
            )},
        },
        "tokenizer_fact_provenance": {
            "source_path": audit_path,
            "source_sha256": audit_sha256,
            "field_pointers": {key: pointers[key] for key in (
                "tokenizer_metadata_class", "expected_runtime_tokenizer_class",
                "fast_offsets_required",
            )},
        },
        "card_path": card_path,
    })
    card_file.write_bytes(json.dumps(card, sort_keys=True, separators=(",", ":")).encode())
    runtime_commitment = hashlib.sha256(
        json.dumps(runtime_files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return {
        "artifact_class": "a0x-runtime-readiness",
        "readiness_profile": "a0x-runtime-readiness-v1",
        "source_head": source_head,
        "pair_binding": pair.as_mapping(),
        "python": {
            "path": str(python_path),
            "sha256": sha256_file(python_path),
            "version": "3.11.13",
            "major_minor": [3, 11],
            "environment_root": str(python_path.parent.parent),
            "base_prefix": "/synthetic/base-python",
            "packages": dict(EXPECTED_PACKAGES),
            "api_symbols": dict(EXPECTED_API_SYMBOLS),
        },
        "model_runtime": {
            "model_key": pair.model_key,
            "model_id": pair.model_id,
            "revision": pair.revision,
            "card_path": card_path,
            "card_sha256": sha256_file(card_file),
            "runtime_root": runtime_root,
            "runtime_file_count": 1,
            "runtime_total_bytes": len(config_raw),
            "runtime_files_commitment_sha256": runtime_commitment,
        },
    }


def _synthetic_gate_a_verifier(request) -> bytes:
    """Minimal callback: writes one schema-valid receipt, no process or network."""
    authorization_raw = request.authorization_path.read_bytes()
    authorization = json.loads(authorization_raw)
    receipt = {
        "artifact_class": "a0x-hosted-gate-a-verification-receipt",
        "receipt_profile": "a0x-hosted-gate-a-verification-receipt-v1",
        "verification_status": "verified",
        "repository": authorization["repository"],
        "qualified_source_head": authorization["source_head"],
        "qualified_source_tree": authorization["source_tree"],
        "pair_binding": authorization["pair_binding"],
        "authorization_raw_sha256": hashlib.sha256(authorization_raw).hexdigest(),
        "hosted_inputs": authorization["hosted_inputs"],
        "verifier": authorization["verifier"],
        "verified_at": "2026-08-31T00:00:00Z",
    }
    raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    output = request.repository_root / authorization["verification_receipt_path"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return raw


@contextmanager
def _synthetic_ccp_hash(request: Any):
    """Keep inert test binaries independent of the temporary mount policy."""
    from latent_triz import a0x_runtime_bundle

    expected = json.loads(
        (Path(__file__).parents[1] / "experiments/a0x-six-model/material-execution-contract.json").read_text(
            encoding="utf-8",
        ),
    )["ccp"]["sha256"]
    actual = a0x_runtime_bundle.sha256_file
    ccp = request.ccp_executable.resolve()
    python = request.python_executable.resolve()
    verifier = request.verifier_executable.resolve()
    actual_access = os.access

    def synthetic_access(path: os.PathLike[str] | str, mode: int) -> bool:
        resolved = Path(path).resolve()
        if mode & os.X_OK and resolved in {ccp, python, verifier}:
            return True
        return actual_access(path, mode)

    with (
        patch(
            "latent_triz.a0x_runtime_bundle.sha256_file",
            side_effect=lambda path: (
                expected if Path(path).resolve() == ccp
                else "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
                if Path(path).resolve() == verifier else actual(path)
            ),
        ),
        patch("latent_triz.a0x_runtime_bundle.os.access", side_effect=synthetic_access),
        patch("latent_triz.a0x_runtime_bundle._required_gate_a_verifier", side_effect=_synthetic_gate_a_verifier),
    ):
        yield


def prepare_constructible_runtime_bundle() -> ConstructibleRuntimeBundle:
    """Prepare one Gate B bundle without model, target, process, or CCP invocation."""
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
            runtime_readiness_probe=_synthetic_runtime_readiness,
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

    def test_constructible_fixture_is_independent_of_temp_mount_exec_policy(self) -> None:
        """Synthetic executables remain inert on a writable ``noexec`` temp mount."""
        with patch("latent_triz.a0x_runtime_bundle.os.access", return_value=False):
            bundle = prepare_constructible_runtime_bundle()
        self.addCleanup(bundle.close)
        self.assertEqual("prepared", bundle.receipt["status"])

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
                runtime_readiness_probe=_synthetic_runtime_readiness,
            )
        readiness = root / receipt["readiness_path"]
        descriptor = root / receipt["descriptor_path"]
        authorization = root / receipt["authorization_path"]
        mapping = root / receipt["mapping_path"]
        self.assertTrue(readiness.is_file())
        self.assertTrue(descriptor.is_file())
        self.assertTrue(authorization.is_file())
        self.assertTrue(mapping.is_file())
        descriptor_document = json.loads(descriptor.read_text(encoding="utf-8"))
        authorization_document = json.loads(authorization.read_text(encoding="utf-8"))
        mapping_document = json.loads(mapping.read_text(encoding="utf-8"))
        self.assertNotIn("authorization", descriptor_document)
        self.assertEqual(receipt["readiness_path"], descriptor_document["runtime_readiness"]["path"])
        self.assertEqual(
            hashlib.sha256(readiness.read_bytes()).hexdigest(),
            descriptor_document["runtime_readiness"]["sha256"],
        )
        descriptor_sha256 = hashlib.sha256(descriptor.read_bytes()).hexdigest()
        self.assertEqual(descriptor_sha256, authorization_document["guard_launch"]["launch_descriptor"]["sha256"])
        self.assertEqual(receipt["descriptor_path"], mapping_document["descriptor"]["path"])
        self.assertEqual(descriptor_sha256, mapping_document["descriptor"]["sha256"])

    def test_current_preparation_request_requires_gate_b_verifier_inputs(self) -> None:
        """Removing Gate B inputs would let current preparation bypass verification."""
        from latent_triz.a0x_runtime_bundle import RuntimePreparationRequest

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        request = RuntimePreparationRequest(
            fixed_dossier="experiments/a0x-six-model/approval-dossiers/a0/gpt2.json",
            gate_b_authorization=root / "gate-b-authorization.json",
            verifier_executable=root / "gh",
            verifier_policy=root / "verifier-policy.json",
            ccp_executable=root / "commit-ci-preflight",
            python_executable=root / "python",
            authorization_id="a0x-auth-a0-gpt2-attempt-01",
            attempt_id="a0x-a0-gpt2-attempt-01",
        )
        self.assertEqual(root / "gate-b-authorization.json", request.gate_b_authorization)

    def test_gate_b_verifies_before_readiness_and_binds_five_hashes(self) -> None:
        from latent_triz.a0x_runtime_bundle import prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        events: list[str] = []

        def verifier(value):
            events.append("verification")
            return _synthetic_gate_a_verifier(value)

        def readiness(*args):
            self.assertEqual(["verification"], events)
            return _synthetic_runtime_readiness(*args)

        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}):
            receipt = prepare_runtime_bundle(
                root, request, source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=readiness, gate_a_verifier=verifier,
            )
        authorization = json.loads((root / receipt["authorization_path"]).read_text())
        evidence = authorization["gate_a_evidence"]
        self.assertEqual(4, len(evidence["hosted_inputs"]))
        self.assertEqual(
            hashlib.sha256((root / evidence["verification_receipt"]["path"]).read_bytes()).hexdigest(),
            evidence["verification_receipt"]["sha256"],
        )
        verified = json.loads((root / evidence["verification_receipt"]["path"]).read_text())
        self.assertEqual(hashlib.sha256(request.gate_b_authorization.read_bytes()).hexdigest(), verified["authorization_raw_sha256"])
        self.assertEqual(
            hashlib.sha256(request.gate_b_authorization.read_bytes()).hexdigest(),
            evidence["gate_b_authorization_raw_sha256"],
        )

    def test_gate_b_refusal_creates_no_receipt_or_runtime_documents(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}), self.assertRaisesRegex(A0XRuntimeBundleError, "verification refused"):
            prepare_runtime_bundle(
                root, request, source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=Mock(side_effect=AssertionError("readiness reached")),
                gate_a_verifier=Mock(side_effect=ValueError("refused")),
            )
        gate = json.loads(request.gate_b_authorization.read_text())
        self.assertFalse((root / gate["verification_receipt_path"]).exists())
        self.assertFalse((root / ".a0x-runtime/launches").exists())

    def test_static_preflight_never_consumes_gate_b_receipt_or_readiness(self) -> None:
        """Preflight must not spend the one-shot verifier or create future bytes."""
        from latent_triz.a0x_runtime_bundle import preflight_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        verifier = Mock(side_effect=AssertionError("verifier reached"))
        readiness = Mock(side_effect=AssertionError("readiness reached"))
        gate = json.loads(request.gate_b_authorization.read_text())
        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}):
            first = preflight_runtime_bundle(
                root, request, source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=readiness, gate_a_verifier=verifier,
            )
            second = preflight_runtime_bundle(
                root, request, source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=readiness, gate_a_verifier=verifier,
            )
        self.assertEqual(first, second)
        verifier.assert_not_called()
        readiness.assert_not_called()
        self.assertFalse(os.path.lexists(root / gate["verification_receipt_path"]))
        for key in ("readiness_path", "descriptor_path", "authorization_path", "mapping_path"):
            self.assertFalse(os.path.lexists(root / first[key]))

    def test_post_verification_drift_preserves_only_owned_receipt(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        gate = json.loads(request.gate_b_authorization.read_text())

        def drifted_readiness(*args):
            (root / gate["hosted_inputs"]["manifest"]["path"]).write_bytes(b"drift")
            return _synthetic_runtime_readiness(*args)

        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}), self.assertRaisesRegex(A0XRuntimeBundleError, "hosted input bytes"):
            prepare_runtime_bundle(
                root, request, source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=drifted_readiness, gate_a_verifier=_synthetic_gate_a_verifier,
            )
        self.assertTrue((root / gate["verification_receipt_path"]).is_file())
        self.assertFalse((root / derive_runtime_paths(PairBinding.from_mapping(gate["pair_binding"])).launch_descriptor_path).exists())

    def test_runtime_write_failure_removes_only_new_runtime_outputs(self) -> None:
        from latent_triz import a0x_runtime_bundle
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        gate = json.loads(request.gate_b_authorization.read_text())
        real_write = a0x_runtime_bundle._exclusive_write
        writes = 0

        def fail_after_two(path, raw):
            nonlocal writes
            writes += 1
            if writes == 3:
                raise OSError("synthetic write failure")
            return real_write(path, raw)

        with self._synthetic_ccp_hash(request), patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}), patch("latent_triz.a0x_runtime_bundle._exclusive_write", side_effect=fail_after_two), self.assertRaises(OSError):
            prepare_runtime_bundle(
                root, request, source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=_synthetic_runtime_readiness, gate_a_verifier=_synthetic_gate_a_verifier,
            )
        runtime = derive_runtime_paths(PairBinding.from_mapping(gate["pair_binding"]), source_head="a" * 40)
        self.assertTrue((root / gate["verification_receipt_path"]).is_file())
        for path in (runtime.launch_descriptor_path, runtime.authorization_path):
            self.assertFalse((root / path).exists())

    @unittest.skip("Gate C v3 execution acceptance is outside Gate B preparation")
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
                runtime_readiness_probe=_synthetic_runtime_readiness,
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

        def mutate_readiness_bytes(bundle: ConstructibleRuntimeBundle) -> None:
            (bundle.root / bundle.receipt["readiness_path"]).write_bytes(b"{}")

        def mutate_descriptor_readiness_hash(bundle: ConstructibleRuntimeBundle) -> None:
            path = bundle.root / bundle.receipt["descriptor_path"]
            document = json.loads(path.read_text())
            document["runtime_readiness"]["sha256"] = "0" * 64
            rewrite(path, document)

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
            "readiness_bytes": mutate_readiness_bytes,
            "descriptor_readiness_hash": mutate_descriptor_readiness_hash,
            "authorization_descriptor_hash": mutate_authorization_descriptor_hash,
            "descriptor_authorization_path": mutate_descriptor_authorization_path,
            "contract_bytes": mutate_contract_bytes,
            "mapping_descriptor_path": mutate_mapping_descriptor_path,
            "mapping_descriptor_hash": mutate_mapping_descriptor_hash,
            "ccp_bytes": mutate_ccp_bytes,
            "python_bytes": mutate_python_bytes,
            "child_bytes": mutate_child_bytes,
            "source_head": mutate_source_head,
            "pair": mutate_pair,
        }
        child_checked = {
            "authorization_bytes", "descriptor_bytes", "readiness_bytes",
            "descriptor_readiness_hash", "authorization_descriptor_hash",
            "descriptor_authorization_path", "contract_bytes", "python_bytes", "child_bytes",
            "source_head", "pair",
        }
        production_checked = {
            "authorization_bytes", "descriptor_bytes", "readiness_bytes",
            "descriptor_readiness_hash", "authorization_descriptor_hash",
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
                runtime_readiness_probe=_synthetic_runtime_readiness,
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
                    runtime_readiness_probe=_synthetic_runtime_readiness,
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
            receipt = prepare_runtime_bundle(root, request, source_state_probe=lambda: ("a" * 40, True), ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0", runtime_readiness_probe=_synthetic_runtime_readiness)
            first_bytes = {name: (root / receipt[f"{name}_path"]).read_bytes() for name in ("readiness", "descriptor", "authorization", "mapping")}
            with self.assertRaises(A0XRuntimeBundleError):
                prepare_runtime_bundle(root, request, source_state_probe=lambda: ("a" * 40, True), ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0", runtime_readiness_probe=_synthetic_runtime_readiness)
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
                runtime_readiness_probe=_synthetic_runtime_readiness,
            )
        self.assertEqual("prepared", receipt["status"])
        process_run.assert_not_called()
        process_open.assert_not_called()
        launch.assert_not_called()
        target_reader.assert_not_called()
        model_adapter.assert_not_called()
        model_factory.assert_not_called()

    def test_preflight_is_deterministic_and_writes_no_runtime_bundle(self) -> None:
        from latent_triz.a0x_runtime_bundle import preflight_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        patch_target = "latent_triz.a0x_runtime_bundle.planned_material_dossiers"
        with (
            self._synthetic_ccp_hash(request),
            patch(patch_target, return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch(
                "latent_triz.a0x_runtime_bundle._write_and_verify_bundle",
                side_effect=AssertionError("runtime bundle write reached"),
            ) as writer,
        ):
            first = preflight_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=_synthetic_runtime_readiness,
            )
            second = preflight_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=lambda _path: "commit-ci-preflight 0.1.0",
                runtime_readiness_probe=_synthetic_runtime_readiness,
            )
        self.assertEqual(first, second)
        self.assertEqual("preflight", first["status"])
        self.assertEqual("a" * 40, first["source_head"])
        self.assertEqual(request.authorization_id, first["authorization_id"])
        self.assertEqual(request.attempt_id, first["attempt_id"])
        writer.assert_not_called()
        for key in ("readiness_path", "descriptor_path", "authorization_path", "mapping_path"):
            self.assertFalse(os.path.lexists(root / first[key]))

    def test_preflight_refuses_occupied_pair_path_before_runtime_probes(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, preflight_runtime_bundle

        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        dossier = json.loads((root / request.fixed_dossier).read_text(encoding="utf-8"))
        pair = PairBinding.from_mapping(dossier["pair_binding"])
        occupied = root / derive_runtime_paths(pair).claim_path
        occupied.parent.mkdir(parents=True, exist_ok=True)
        occupied.write_bytes(b"preserve")
        version_probe = Mock(side_effect=AssertionError("CCP version probe reached"))
        readiness_probe = Mock(side_effect=AssertionError("readiness probe reached"))
        with (
            self._synthetic_ccp_hash(request),
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            self.assertRaisesRegex(A0XRuntimeBundleError, "occupied"),
        ):
            preflight_runtime_bundle(
                root,
                request,
                source_state_probe=lambda: ("a" * 40, True),
                ccp_version_probe=version_probe,
                runtime_readiness_probe=readiness_probe,
            )
        self.assertEqual(b"preserve", occupied.read_bytes())
        version_probe.assert_not_called()
        readiness_probe.assert_not_called()

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
                version_probe = Mock(side_effect=AssertionError("CCP version probe reached"))
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
                            ccp_version_probe=version_probe,
                            runtime_readiness_probe=_synthetic_runtime_readiness,
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
                version_probe.assert_not_called()
                launch.assert_not_called()
                target_reader.assert_not_called()
                model_factory.assert_not_called()

    def test_symlink_occupancy_refuses_before_ccp_version_or_material_access(self) -> None:
        from latent_triz.a0x_runtime_bundle import A0XRuntimeBundleError, prepare_runtime_bundle

        for category in ("destination", "parent"):
            with self.subTest(category=category):
                temporary, root, request = self._fixture()
                self.addCleanup(temporary.cleanup)
                dossier = json.loads((root / request.fixed_dossier).read_text(encoding="utf-8"))
                pair = PairBinding.from_mapping(dossier["pair_binding"])
                runtime = derive_runtime_paths(pair, source_head="a" * 40)
                link_target = root / f"{category}-link-target"
                link_target.mkdir()
                marker = link_target / "preserved"
                marker.write_bytes(b"preserved")
                if category == "destination":
                    occupied = root / runtime.claim_path
                    occupied.parent.mkdir(parents=True, exist_ok=True)
                    occupied.symlink_to(marker)
                    parent_link = None
                else:
                    parent_link = root / f".a0x-runtime/material/{pair.leg.value}/{pair.model_key}"
                    parent_link.parent.mkdir(parents=True, exist_ok=True)
                    parent_link.symlink_to(link_target, target_is_directory=True)
                    occupied = parent_link / pair.run_id
                version_probe = Mock(side_effect=AssertionError("CCP version probe reached"))
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
                            ccp_version_probe=version_probe,
                            runtime_readiness_probe=_synthetic_runtime_readiness,
                        )
                self.assertEqual(b"preserved", marker.read_bytes())
                if category == "destination":
                    self.assertTrue(occupied.is_symlink())
                    self.assertEqual(marker.resolve(), occupied.resolve())
                else:
                    self.assertIsNotNone(parent_link)
                    self.assertTrue(parent_link.is_symlink())
                    self.assertFalse(os.path.lexists(occupied))
                    self.assertFalse((link_target / pair.run_id).exists())
                version_probe.assert_not_called()
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
                runtime_readiness_probe=_synthetic_runtime_readiness,
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
            if len(argv) == 4 and argv[:3] == [str(request.python_executable.resolve()), "-I", "-c"]:
                return Result("{}\n")
            raise AssertionError(f"unexpected probe argv: {argv}")

        argv = [
            "--fixed-dossier", request.fixed_dossier,
            "--gate-b-authorization", str(request.gate_b_authorization),
            "--verifier", str(request.verifier_executable),
            "--verifier-policy", str(request.verifier_policy),
            "--ccp", str(request.ccp_executable),
            "--python", str(request.python_executable),
            "--authorization-id", request.authorization_id,
            "--attempt-id", request.attempt_id,
        ]
        with (
            self._synthetic_ccp_hash(request),
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch.object(
                cli, "build_runtime_readiness",
                side_effect=lambda **kwargs: _synthetic_runtime_readiness(
                    kwargs["repository_root"], kwargs["pair"],
                    kwargs["source_head"], kwargs["python_path"],
                ),
            ),
            patch.object(cli.subprocess, "run", side_effect=probe),
        ):
            code = cli.main(
                argv, root=root, stdout=output, gate_a_verifier=_synthetic_gate_a_verifier,
            )
        self.assertEqual(0, code)
        receipt = json.loads(output.getvalue())
        self.assertEqual("prepared", receipt["status"])
        self.assertEqual(sorted(receipt), list(receipt))

    def test_cli_preflight_emits_sorted_summary_without_writing_bundle(self) -> None:
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
            if len(argv) == 4 and argv[:3] == [str(request.python_executable.resolve()), "-I", "-c"]:
                return Result("{}\n")
            raise AssertionError(f"unexpected probe argv: {argv}")

        argv = [
            "--preflight",
            "--fixed-dossier", request.fixed_dossier,
            "--gate-b-authorization", str(request.gate_b_authorization),
            "--verifier", str(request.verifier_executable),
            "--verifier-policy", str(request.verifier_policy),
            "--ccp", str(request.ccp_executable),
            "--python", str(request.python_executable),
            "--authorization-id", request.authorization_id,
            "--attempt-id", request.attempt_id,
        ]
        verifier = Mock(side_effect=AssertionError("verifier reached"))
        with (
            self._synthetic_ccp_hash(request),
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch.object(
                cli, "build_runtime_readiness",
                side_effect=AssertionError("readiness reached"),
            ) as readiness,
            patch.object(cli.subprocess, "run", side_effect=probe),
        ):
            code = cli.main(argv, root=root, stdout=output, gate_a_verifier=verifier)
        self.assertEqual(0, code)
        receipt = json.loads(output.getvalue())
        self.assertEqual("preflight", receipt["status"])
        self.assertEqual(sorted(receipt), list(receipt))
        verifier.assert_not_called()
        readiness.assert_not_called()
        gate = json.loads(request.gate_b_authorization.read_text())
        self.assertFalse(os.path.lexists(root / gate["verification_receipt_path"]))
        for key in ("readiness_path", "descriptor_path", "authorization_path", "mapping_path"):
            self.assertFalse(os.path.lexists(root / receipt[key]))

    @unittest.skip("historical qualification-receipt CLI contract retired by Gate B authorization")
    def test_cli_preflight_wrong_receipt_path_reports_stable_safe_error(self) -> None:
        temporary, root, request = self._fixture()
        self.addCleanup(temporary.cleanup)
        cli = self._cli_module()
        output = io.StringIO()
        alternate = root / "alternate-receipt.json"
        alternate.write_bytes(request.qualification_receipt.read_bytes())
        request = replace(request, qualification_receipt=alternate)

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
            "--preflight",
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
        self.assertEqual(
            {
                "error": {
                    "code": "A0X_QUALIFICATION_RECEIPT_PATH_NOT_SOURCE_DERIVED",
                    "message": "qualification receipt path is not source-derived",
                },
                "status": "refused",
            },
            json.loads(output.getvalue()),
        )

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
                    runtime_readiness_probe=_synthetic_runtime_readiness,
                )
        self.assertFalse((root / ".a0x-runtime/launches").exists())
        self.assertFalse((root / ".a0x-runtime/authorizations").exists())
        self.assertFalse((root / ".a0x-runtime/bin").exists())

    def test_cli_gate_b_verifier_refusal_returns_code_two(self) -> None:
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
            "--gate-b-authorization", str(request.gate_b_authorization),
            "--verifier", str(request.verifier_executable),
            "--verifier-policy", str(request.verifier_policy),
            "--ccp", str(request.ccp_executable),
            "--python", str(request.python_executable),
            "--authorization-id", request.authorization_id,
            "--attempt-id", request.attempt_id,
        ]
        with (
            self._synthetic_ccp_hash(request),
            patch("latent_triz.a0x_runtime_bundle.planned_material_dossiers", return_value={("a0", "gpt2"): request.fixed_dossier}),
            patch.object(cli.subprocess, "run", side_effect=probe),
        ):
            code = cli.main(
                argv, root=root, stdout=output,
                gate_a_verifier=Mock(side_effect=ValueError("refused")),
            )
        self.assertEqual(2, code)
        self.assertEqual({"status": "refused"}, json.loads(output.getvalue()))
