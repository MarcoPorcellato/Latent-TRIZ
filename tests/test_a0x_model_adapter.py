from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import math
import unittest
from unittest.mock import ANY

from latent_triz.a0x_model_adapter import A0XHiddenStateAdapter, A0XModelAdapterError
from latent_triz.a0x_preflight import A0XModelCard, load_registry


ROOT = Path(__file__).resolve().parents[1]


class Batch(dict):
    pass


class FakeTensor:
    def __init__(self, value):
        self.value = value
        self.shape = self._shape(value)

    @staticmethod
    def _shape(value):
        shape = []
        current = value
        while isinstance(current, list):
            shape.append(len(current))
            current = current[0] if current else None
        return tuple(shape)

    def tolist(self):
        return self.value


class FakeParam:
    def __init__(self, dtype="float32", device="cpu"):
        self.dtype = dtype
        self.device = SimpleNamespace(type=device)


class FakeTorch:
    float32 = "float32"

    @staticmethod
    def device(name):
        return name

    @staticmethod
    def inference_mode():
        return nullcontext()


class FakeTokenizer:
    is_fast = True

    def __init__(self, calls, *, offsets=True, slow=False):
        self.calls = calls
        self.offsets = offsets
        self.is_fast = not slow

    def __call__(self, text, **kwargs):
        self.calls.append("offset-probe" if kwargs.get("return_offsets_mapping") else "tokenize")
        token_count = 3
        payload = Batch(
            input_ids=FakeTensor([[1, 2, 3]]),
            attention_mask=FakeTensor([[1, 1, 1]]),
            special_tokens_mask=FakeTensor([[0, 0, 0]]),
        )
        if self.offsets:
            payload["offset_mapping"] = FakeTensor([[(0, 1), (1, 2), (2, 3)]])
        return payload


class FakeModel:
    def __init__(self, calls, *, layers, width, hidden_states=None, parameter=None):
        self.calls = calls
        self.layers = layers
        self.width = width
        self._hidden_states = hidden_states
        self._parameter = parameter or FakeParam()
        self.eval_called = False
        self.to_value = None
        self.forward_calls = []
        self.generate_calls = 0

    def to(self, value):
        self.to_value = value
        return self

    def eval(self):
        self.eval_called = True
        return self

    def parameters(self):
        return [self._parameter]

    def __call__(self, **kwargs):
        self.forward_calls.append(kwargs)
        if self._hidden_states is None:
            state = FakeTensor([[[float(index) for index in range(self.width)] for _ in range(3)]])
            hidden_states = tuple(state for _ in range(self.layers + 1))
        else:
            hidden_states = self._hidden_states
        return SimpleNamespace(hidden_states=hidden_states)

    def generate(self, *_args, **_kwargs):
        self.generate_calls += 1
        raise AssertionError("generation must never be invoked")


def registry_cards():
    return load_registry(ROOT / "experiments/a0x-six-model/model-registry.json")


def config_for(card, **overrides):
    values = {
        "model_type": card.model_type,
        "architectures": [card.architecture],
        "num_hidden_layers": card.num_hidden_layers,
        "hidden_size": card.hidden_size,
        "vocab_size": card.vocab_size,
        "max_position_embeddings": card.effective_context,
        "n_positions": card.effective_context,
        "n_ctx": card.effective_context,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def tokenizer_for(card, calls, **kwargs):
    token_type = type(card.expected_runtime_tokenizer_class, (FakeTokenizer,), {})
    return token_type(calls, **kwargs)


def load_synthetic(card: A0XModelCard, *, config=None, tokenizer=None, model=None):
    calls = []
    config = config or config_for(card)
    tokenizer = tokenizer or tokenizer_for(card, calls)
    model = model or FakeModel(calls, layers=card.num_hidden_layers, width=card.hidden_size)

    def config_factory(_root, **kwargs):
        calls.append("config")
        assert kwargs == {"local_files_only": True, "trust_remote_code": False}
        return config

    def tokenizer_factory(_root, **kwargs):
        calls.append("tokenizer")
        assert kwargs == {"local_files_only": True, "trust_remote_code": False, "use_fast": True}
        return tokenizer

    def model_factory(_root, **kwargs):
        calls.append("model")
        assert kwargs == {
            "local_files_only": True,
            "trust_remote_code": False,
            "torch_dtype": FakeTorch.float32,
        }
        return model

    adapter = A0XHiddenStateAdapter.load(
        f"/synthetic/{card.model_key}", card=card,
        config_factory=config_factory, tokenizer_factory=tokenizer_factory,
        model_factory=model_factory, torch_module=FakeTorch,
    )
    return adapter, calls, tokenizer, model


class A0XHiddenStateAdapterTests(unittest.TestCase):
    def test_all_six_cards_load_in_required_order_with_only_synthetic_factories(self):
        observed = []
        for card in registry_cards():
            with self.subTest(model_key=card.model_key):
                adapter, calls, _tokenizer, model = load_synthetic(card)
                self.assertEqual(calls, ["config", "tokenizer", "offset-probe", "model"])
                self.assertTrue(adapter.model_loaded)
                self.assertEqual(adapter.card, card)
                self.assertTrue(model.eval_called)
                self.assertEqual(model.to_value, "cpu")
                self.assertEqual(model.generate_calls, 0)
                observed.append((card.model_type, card.hidden_size, card.num_hidden_layers))
        self.assertEqual(
            observed,
            [("llama", 960, 32), ("qwen3", 1024, 28), ("gpt2", 768, 12),
             ("llama", 576, 30), ("gpt_neo", 768, 12), ("qwen2", 896, 24)],
        )

    def test_forward_preserves_embedding_and_final_block_with_exact_kwargs(self):
        card = next(card for card in registry_cards() if card.model_key == "gpt2")
        adapter, _calls, _tokenizer, model = load_synthetic(card)

        payload = adapter.forward_hidden("Analysis anchor: x")

        self.assertEqual(len(payload.hidden_states), 13)
        self.assertEqual(payload.final_block_tuple_index, 12)
        self.assertEqual(payload.hidden_states[6].shape, (1, 3, 768))
        self.assertEqual(payload.input_ids, (1, 2, 3))
        self.assertEqual(payload.attention_mask, (1, 1, 1))
        self.assertEqual(payload.offsets, ((0, 1), (1, 2), (2, 3)))
        self.assertEqual(payload.special_tokens_mask, (0, 0, 0))
        self.assertEqual(
            model.forward_calls,
            [{
                "input_ids": ANY,
                "attention_mask": ANY,
                "output_hidden_states": True,
                "output_attentions": False,
                "use_cache": False,
                "return_dict": True,
            }],
        )
        self.assertEqual(model.generate_calls, 0)

    def test_rejects_config_fact_drift_before_model_factory(self):
        card = next(card for card in registry_cards() if card.model_key == "qwen3_0_6b_base")
        for field, wrong in {
            "model_type": "qwen2", "architectures": ["Qwen2ForCausalLM"],
            "num_hidden_layers": 27, "hidden_size": 1023,
            "vocab_size": 1, "max_position_embeddings": 1,
        }.items():
            with self.subTest(field=field):
                values = {field: wrong}
                calls = []
                config = config_for(card, **values)
                tokenizer = tokenizer_for(card, calls)
                with self.assertRaises(A0XModelAdapterError):
                    load_synthetic(card, config=config, tokenizer=tokenizer)
                self.assertNotIn("model", calls)

    def test_rejects_tokenizer_contract_drift_before_model_factory(self):
        card = next(card for card in registry_cards() if card.model_key == "gpt_neo_125m")
        variants = (
            FakeTokenizer([], offsets=True),
            tokenizer_for(card, [], slow=True),
            tokenizer_for(card, [], offsets=False),
        )
        for tokenizer in variants:
            with self.subTest(tokenizer_type=type(tokenizer).__name__, fast=tokenizer.is_fast, offsets=tokenizer.offsets):
                calls = tokenizer.calls
                with self.assertRaises(A0XModelAdapterError):
                    load_synthetic(card, tokenizer=tokenizer)
                self.assertNotIn("model", calls)

    def test_rejects_non_cpu_float32_parameters(self):
        card = next(card for card in registry_cards() if card.model_key == "smollm2_135m")
        for parameter in (FakeParam(dtype="float16"), FakeParam(device="cuda")):
            with self.subTest(parameter=(parameter.dtype, parameter.device.type)):
                model = FakeModel([], layers=card.num_hidden_layers, width=card.hidden_size, parameter=parameter)
                with self.assertRaises(A0XModelAdapterError):
                    load_synthetic(card, model=model)

    def test_rejects_invalid_hidden_state_shapes_values_and_tuple_length(self):
        card = next(card for card in registry_cards() if card.model_key == "qwen2_5_0_5b")
        valid = FakeTensor([[[0.0 for _ in range(card.hidden_size)] for _ in range(3)]])
        invalids = (
            tuple(FakeTensor([[0.0] * card.hidden_size for _ in range(3)]) for _ in range(card.num_hidden_layers + 1)),
            tuple(FakeTensor([[[0.0 for _ in range(card.hidden_size)] for _ in range(3)]] * 2) for _ in range(card.num_hidden_layers + 1)),
            tuple(FakeTensor([[[float("nan")] + [0.0] * (card.hidden_size - 1) for _ in range(3)]]) for _ in range(card.num_hidden_layers + 1)),
            tuple(valid for _ in range(card.num_hidden_layers)),
        )
        for hidden_states in invalids:
            with self.subTest(shape=getattr(hidden_states[0], "shape", None), length=len(hidden_states)):
                model = FakeModel([], layers=card.num_hidden_layers, width=card.hidden_size, hidden_states=hidden_states)
                adapter, _calls, _tokenizer, _model = load_synthetic(card, model=model)
                with self.assertRaises(A0XModelAdapterError):
                    adapter.forward_hidden("Analysis anchor: x")


if __name__ == "__main__":
    unittest.main()
