from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import types
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

_ORIGINAL_PATH_OPEN = Path.open

from latent_triz import a0r2_adapter
from latent_triz.a0r2_adapter import A0R2AdapterError, SmolLM2TransformersAdapter
from latent_triz.a0r2_activations import A0R2ActivationError, run_a0r2_activations


class _FakeTokenizer:
    is_fast = True
    name_or_path = "fake-tokenizer"

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        return_attention_mask: bool = True,
        return_offsets_mapping: bool = False,
        return_tensors: str | None = None,
    ) -> dict[str, object]:
        del add_special_tokens, return_tensors
        input_ids = [ord(ch) for ch in text]
        payload: dict[str, object] = {"input_ids": input_ids}
        if return_attention_mask:
            payload["attention_mask"] = [1] * len(input_ids)
        if return_offsets_mapping:
            payload["offset_mapping"] = [[index, index + 1] for index in range(len(input_ids))]
        return payload

    def convert_ids_to_tokens(self, ids: list[int]) -> list[str]:
        return [str(value) for value in ids]

    def get_special_tokens_mask(self, input_ids: list[int], already_has_special_tokens: bool = True) -> list[int]:  # noqa: ARG002
        del already_has_special_tokens
        return [0] * len(input_ids)


class _FakeAdapter:
    def __init__(self, hidden_state_factory) -> None:
        self.tokenizer = _FakeTokenizer()
        self.hidden_state_factory = hidden_state_factory
        self.calls: list[str] = []

    def run_prompt(self, *, prompt: str, instrumented: bool = True) -> dict[str, object]:  # noqa: ARG002
        self.calls.append(prompt)
        hidden_states = self.hidden_state_factory(len(prompt))
        return {
            "token_ids": [ord(ch) for ch in prompt],
            "offsets_mapping": [[index, index + 1] for index in range(len(prompt))],
            "attention_mask": [1] * len(prompt),
            "special_token_flags": [False] * len(prompt),
            "hidden_states": hidden_states,
        }


class _FakeTensor:
    def __init__(self, data):
        self._data = data

    def to(self, _device):
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self._data


class _FakeConfig:
    model_type = "llama"
    num_hidden_layers = 32
    hidden_size = 960
    architectures = ["LlamaForCausalLM"]


class _FakeModel:
    def __init__(self, hidden_state_factory):
        self.hidden_state_factory = hidden_state_factory

    def to(self, _device):
        return self

    def eval(self):
        return self

    def __call__(self, *, input_ids, attention_mask, output_hidden_states, use_cache, return_dict):  # noqa: ARG002
        del attention_mask, output_hidden_states, use_cache, return_dict
        values = input_ids.tolist()
        token_count = len(values[0]) if values and isinstance(values[0], list) else len(values)
        hidden_states = self.hidden_state_factory(token_count)
        return types.SimpleNamespace(hidden_states=hidden_states, logits=_FakeTensor([[0.0]]))


def _shared_hidden_states(token_count: int, *, dim: int = 960, layers: int = 33, value: float = 0.125):
    row = tuple(float(value + coordinate * 0.0001) for coordinate in range(dim))
    layer = tuple(row for _ in range(token_count))
    return tuple(tuple(layer for _ in range(layers)))


def _shared_hidden_states_with_nonfinite(token_count: int):
    rows = _shared_hidden_states(token_count)
    first_layer = [list(row) for row in rows[0]]
    for row in first_layer:
        row[0] = float("nan")
    mutable_layers = [tuple(first_layer)]
    for layer in rows[1:]:
        mutable_layers.append(layer)
    return tuple(mutable_layers)


def _guard_sealed_target_open(
    sealed_target_path: Path,
    attempted_opens: list[str],
    original_open: Callable[..., object] | None = None,
) -> Callable[..., object]:
    blocked_path = Path(os.path.abspath(sealed_target_path))
    delegate = _ORIGINAL_PATH_OPEN if original_open is None else original_open

    def tracked_open(path_obj: Path, *args: object, **kwargs: object) -> object:
        if Path(os.path.abspath(path_obj)) == blocked_path:
            attempted_opens.append(str(path_obj))
            raise PermissionError("sealed-target path access denied before opener")
        return delegate(path_obj, *args, **kwargs)

    return tracked_open


class SealedTargetGuardMetadataTests(unittest.TestCase):
    def test_guard_blocks_lexical_alias_without_metadata_and_allows_public_input(self):
        with tempfile.TemporaryDirectory() as directory:
            blocked = Path(directory) / "sentinel.jsonl"
            attempted = []
            delegated = []
            sentinel = object()

            def opener(path, *_args, **_kwargs):
                delegated.append(path)
                return sentinel

            with (
                patch.object(Path, "resolve", side_effect=AssertionError("resolve forbidden")),
                patch.object(Path, "stat", side_effect=AssertionError("stat forbidden")),
                patch.object(Path, "lstat", side_effect=AssertionError("lstat forbidden")),
                patch.object(os, "readlink", side_effect=AssertionError("readlink forbidden")),
            ):
                guard = _guard_sealed_target_open(blocked, attempted, original_open=opener)
                with self.assertRaisesRegex(PermissionError, "before opener"):
                    guard(blocked, "rb")
                with self.assertRaisesRegex(PermissionError, "before opener"):
                    guard(Path(directory) / "unused" / ".." / "sentinel.jsonl", "rb")
                allowed = Path(directory) / "public.json"
                self.assertIs(sentinel, guard(allowed, "rb"))
            self.assertEqual(2, len(attempted))
            self.assertEqual([allowed], delegated)


class A0R2ActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.sealed_target_path = self.root / "data/a0r1/targets/sealed.jsonl"
        self.sealed_open_attempts: list[str] = []
        self._sealed_open_patch = patch.object(
            Path,
            "open",
            _guard_sealed_target_open(self.sealed_target_path, self.sealed_open_attempts),
        )
        self._sealed_open_patch.start()
        self.addCleanup(self._sealed_open_patch.stop)
        self.protocol_path = self.root / "experiments/a0r2-independent-model/study-protocol.json"
        self.protocol = json.loads(self.protocol_path.read_text(encoding="utf-8"))
        self.independence = json.loads((self.root / "results/a0r1/preoutput/independence.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.assertEqual([], self.sealed_open_attempts)

    def _write_protocol_copy(self, tmpdir: Path, mutator=None) -> Path:
        payload = json.loads(self.protocol_path.read_text(encoding="utf-8"))
        if mutator is not None:
            mutator(payload)
        path = tmpdir / "protocol.json"
        path.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def _run_activation(self, *, tmpdir: Path, adapter_factory) -> tuple[object, _FakeAdapter]:
        output = tmpdir / "activation"
        fake_adapter = _FakeAdapter(adapter_factory)
        artifacts = run_a0r2_activations(
            protocol_path=self.protocol_path,
            model_root=tmpdir / "model",
            output_dir=output,
            created_at="2026-08-15T12:00:00Z",
            adapter_factory=lambda **kwargs: fake_adapter,
        )
        return artifacts, fake_adapter

    def _create_model_root(self, tmpdir: Path) -> Path:
        model_root = tmpdir / "model"
        model_root.mkdir(parents=True)
        for filename in a0r2_adapter.A0R2_REQUIRED_FILES:
            (model_root / filename).write_text(filename, encoding="utf-8")
        return model_root

    def test_sealed_target_open_guard_denies_before_delegating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            synthetic_target = Path(directory) / "sealed.jsonl"
            attempted_opens: list[str] = []
            delegated_opens: list[str] = []

            def fake_open(path_obj: Path, *_args: object, **_kwargs: object) -> object:
                delegated_opens.append(str(path_obj))
                return object()

            guarded_open = _guard_sealed_target_open(
                synthetic_target,
                attempted_opens,
                original_open=fake_open,
            )
            with self.assertRaisesRegex(PermissionError, "sealed-target path access denied"):
                guarded_open(synthetic_target, "rb")

            self.assertEqual([str(synthetic_target)], attempted_opens)
            self.assertEqual([], delegated_opens)

    def test_activation_flow_hits_expected_counts_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            output = tmpdir / "activation"

            fake_adapter = _FakeAdapter(_shared_hidden_states)
            artifacts = run_a0r2_activations(
                protocol_path=self.protocol_path,
                model_root=tmpdir / "model",
                output_dir=output,
                created_at="2026-08-15T12:00:00Z",
                adapter_factory=lambda **kwargs: fake_adapter,
            )

            self.assertEqual(192, len(fake_adapter.calls))
            self.assertTrue(artifacts.dense_path.is_file())
            self.assertTrue(artifacts.index_path.is_file())
            self.assertTrue(artifacts.summary_path.is_file())
            self.assertTrue(artifacts.receipt_path.is_file())
            self.assertEqual([], self.sealed_open_attempts)

            dense_payload = json.loads(artifacts.dense_path.read_text(encoding="utf-8"))
            index_rows = [
                json.loads(line)
                for line in artifacts.index_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            summary_payload = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
            receipt_payload = json.loads(artifacts.receipt_path.read_text(encoding="utf-8"))

            self.assertEqual(1920, len(dense_payload))
            self.assertTrue(all(len(row) == 960 for row in dense_payload.values()))
            self.assertEqual(1920, len(index_rows))
            self.assertEqual(48, summary_payload["case_count"])
            self.assertEqual(192, summary_payload["forward_passes"])
            self.assertEqual(1920, summary_payload["vector_count"])
            self.assertEqual([0, 11, 21, 32], summary_payload["tuple_indices"])
            self.assertEqual(
                self.independence["partitions"]["candidate_split_values"]["sealed"],
                summary_payload["case_ids"],
            )
            self.assertEqual("pass", receipt_payload["status"])
            self.assertTrue(receipt_payload["access"]["model_output_accessed"])
            self.assertFalse(receipt_payload["access"]["sealed_targets_accessed"])
            self.assertTrue(receipt_payload["activation"]["output_content_retained"])
            self.assertEqual(32, receipt_payload["activation"]["tuple_index"])
            self.assertEqual(
                hashlib.sha256(self.protocol_path.read_bytes()).hexdigest(),
                receipt_payload["input_hashes"]["protocol_sha256"],
            )
            self.assertEqual(1920, receipt_payload["output_bundle"]["records"])
            self.assertEqual(960, receipt_payload["output_bundle"]["hidden_size"])
            self.assertEqual(
                hashlib.sha256(artifacts.summary_path.read_bytes()).hexdigest(),
                receipt_payload["output_bundle"]["artifact_hashes"]["summary_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(artifacts.index_path.read_bytes()).hexdigest(),
                receipt_payload["output_bundle"]["artifact_hashes"]["index_sha256"],
            )
            self.assertEqual(
                hashlib.sha256(artifacts.dense_path.read_bytes()).hexdigest(),
                receipt_payload["output_bundle"]["artifact_hashes"]["dense_sha256"],
            )
            self.assertEqual(40, len(receipt_payload["output_bundle"]["exact_head"]))

    def test_activation_hashes_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            first_output = tmpdir / "first"
            second_output = tmpdir / "second"
            fake_adapter = _FakeAdapter(_shared_hidden_states)

            first = run_a0r2_activations(
                protocol_path=self.protocol_path,
                model_root=tmpdir / "model",
                output_dir=first_output,
                created_at="2026-08-15T12:00:00Z",
                adapter_factory=lambda **kwargs: fake_adapter,
            )
            fake_adapter = _FakeAdapter(_shared_hidden_states)
            second = run_a0r2_activations(
                protocol_path=self.protocol_path,
                model_root=tmpdir / "model",
                output_dir=second_output,
                created_at="2026-08-15T12:00:00Z",
                adapter_factory=lambda **kwargs: fake_adapter,
            )

            self.assertEqual(
                hashlib.sha256(first.dense_path.read_bytes()).hexdigest(),
                hashlib.sha256(second.dense_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                hashlib.sha256(first.index_path.read_bytes()).hexdigest(),
                hashlib.sha256(second.index_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                hashlib.sha256(first.summary_path.read_bytes()).hexdigest(),
                hashlib.sha256(second.summary_path.read_bytes()).hexdigest(),
            )

    def test_activation_rejects_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            drifted = self._write_protocol_copy(tmpdir, lambda payload: payload["inputs"].__setitem__("cases_sha256", "0" * 64))
            with self.assertRaisesRegex(A0R2ActivationError, "protocol validation failed"):
                run_a0r2_activations(
                    protocol_path=drifted,
                    model_root=tmpdir / "model",
                    output_dir=tmpdir / "activation",
                    created_at="2026-08-15T12:00:00Z",
                    adapter_factory=lambda **kwargs: _FakeAdapter(_shared_hidden_states),
                )

    def test_activation_rejects_hidden_state_count_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            with self.assertRaisesRegex(A0R2ActivationError, "hidden_states count mismatch"):
                run_a0r2_activations(
                    protocol_path=self.protocol_path,
                    model_root=tmpdir / "model",
                    output_dir=tmpdir / "activation",
                    created_at="2026-08-15T12:00:00Z",
                    adapter_factory=lambda **kwargs: _FakeAdapter(lambda token_count: tuple(tuple(tuple(0.0 for _ in range(960)) for _ in range(token_count)) for _ in range(32))),
                )

    def test_activation_rejects_hidden_size_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            with self.assertRaisesRegex(A0R2ActivationError, "hidden-size mismatch"):
                run_a0r2_activations(
                    protocol_path=self.protocol_path,
                    model_root=tmpdir / "model",
                    output_dir=tmpdir / "activation",
                    created_at="2026-08-15T12:00:00Z",
                    adapter_factory=lambda **kwargs: _FakeAdapter(lambda token_count: tuple(tuple(tuple(0.0 for _ in range(959)) for _ in range(token_count)) for _ in range(33))),
                )

    def test_activation_rejects_non_finite_vectors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            with self.assertRaisesRegex(A0R2ActivationError, "non-finite activation detected"):
                run_a0r2_activations(
                    protocol_path=self.protocol_path,
                    model_root=tmpdir / "model",
                    output_dir=tmpdir / "activation",
                    created_at="2026-08-15T12:00:00Z",
                    adapter_factory=lambda **kwargs: _FakeAdapter(_shared_hidden_states_with_nonfinite),
                )

    def test_activation_refuses_output_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            self._create_model_root(tmpdir)
            output = tmpdir / "activation"
            output.mkdir(parents=True)
            with self.assertRaisesRegex(A0R2ActivationError, "refusing to overwrite"):
                run_a0r2_activations(
                    protocol_path=self.protocol_path,
                    model_root=tmpdir / "model",
                    output_dir=output,
                    created_at="2026-08-15T12:00:00Z",
                    adapter_factory=lambda **kwargs: _FakeAdapter(_shared_hidden_states),
                )

    def test_adapter_verifies_runtime_files_before_loading_and_runs_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmpdir = Path(directory)
            model_root = self._create_model_root(tmpdir)
            order: list[str] = []

            fake_torch = types.SimpleNamespace()
            fake_torch.float32 = "float32"

            def tensor(data):
                return _FakeTensor(data)

            def device(name: str):
                return name

            class _InferenceMode:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            fake_torch.tensor = tensor
            fake_torch.device = device
            fake_torch.inference_mode = lambda: _InferenceMode()

            def build_runtime_file_receipts(_model_root):
                order.append("receipts")
                return [types.SimpleNamespace(name=name, size=1, sha256="0" * 64) for name in a0r2_adapter.A0R2_REQUIRED_FILES]

            class _FakeAutoConfig:
                @staticmethod
                def from_pretrained(*args, **kwargs):
                    del args, kwargs
                    order.append("config")
                    return _FakeConfig()

            class _FakeAutoTokenizer:
                @staticmethod
                def from_pretrained(*args, **kwargs):
                    del args, kwargs
                    order.append("tokenizer")
                    return _FakeTokenizer()

            class _FakeAutoModelForCausalLM:
                @staticmethod
                def from_pretrained(*args, **kwargs):
                    del args, kwargs
                    order.append("model")
                    return _FakeModel(_shared_hidden_states)

            fake_transformers = types.SimpleNamespace(
                AutoConfig=_FakeAutoConfig,
                AutoTokenizer=_FakeAutoTokenizer,
                AutoModelForCausalLM=_FakeAutoModelForCausalLM,
            )

            with patch.dict(sys.modules, {"torch": fake_torch, "transformers": fake_transformers}):
                with patch.object(a0r2_adapter, "build_runtime_file_receipts", side_effect=build_runtime_file_receipts):
                    adapter = SmolLM2TransformersAdapter(model_root)

            self.assertEqual(["receipts", "config", "tokenizer", "model"], order)
            self.assertIs(adapter.torch, fake_torch)
            self.assertEqual(9, len(adapter.runtime_file_receipts))

            result = adapter.run_prompt(prompt="ABC")
            self.assertEqual([65, 66, 67], result["token_ids"])
            self.assertEqual(33, len(result["hidden_states"]))
            self.assertTrue(result["model_output_accessed"])
            self.assertFalse(result["model_output_retained"])


if __name__ == "__main__":
    unittest.main()
