"""Strict local-only hidden-state adapter for the frozen A0X model cards.

The adapter is deliberately inert until a later material execution boundary
supplies concrete local factories.  Its public contract makes no attempt to
discover, download, generate from, or otherwise select a model.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Callable

from .a0x_preflight import A0XModelCard


class A0XModelAdapterError(RuntimeError):
    """Raised when a loaded model violates the frozen A0X runtime contract."""


@dataclass(frozen=True)
class HiddenPayload:
    input_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]
    offsets: tuple[tuple[int, int], ...]
    special_tokens_mask: tuple[int, ...]
    hidden_states: tuple[object, ...]
    final_block_tuple_index: int


_OFFSET_PROBE = "A0X offset probe."
_LOCAL_FACTORIES = {"local_files_only": True, "trust_remote_code": False}


def _plain(value: Any, name: str) -> Any:
    """Return a dependency-free nested representation of a tensor-like value."""
    try:
        detach = getattr(value, "detach", None)
        if callable(detach):
            value = detach()
        cpu = getattr(value, "cpu", None)
        if callable(cpu):
            value = cpu()
        tolist = getattr(value, "tolist", None)
        if callable(tolist):
            return tolist()
    except Exception as error:
        raise A0XModelAdapterError(f"could not normalize {name}") from error
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise A0XModelAdapterError(f"{name} must be a sequence")
    return value


def _one_batch(value: Any, name: str) -> Sequence[Any]:
    batches = _sequence(_plain(value, name), name)
    if len(batches) != 1:
        raise A0XModelAdapterError(f"{name} must have batch size one")
    return _sequence(batches[0], name)


def _integer_tuple(value: Any, name: str) -> tuple[int, ...]:
    row = _one_batch(value, name)
    if not row:
        raise A0XModelAdapterError(f"{name} must not be empty")
    result: list[int] = []
    for item in row:
        if not isinstance(item, int) or isinstance(item, bool):
            raise A0XModelAdapterError(f"{name} must contain integers")
        result.append(item)
    return tuple(result)


def _offset_tuple(value: Any) -> tuple[tuple[int, int], ...]:
    row = _one_batch(value, "offset_mapping")
    if not row:
        raise A0XModelAdapterError("offset_mapping must not be empty")
    offsets: list[tuple[int, int]] = []
    for item in row:
        pair = _sequence(item, "offset_mapping entry")
        if len(pair) != 2 or any(not isinstance(part, int) or isinstance(part, bool) for part in pair):
            raise A0XModelAdapterError("offset_mapping entries must be integer start/end pairs")
        offsets.append((pair[0], pair[1]))
    return tuple(offsets)


def _shape(value: Any) -> tuple[int, ...]:
    plain = _plain(value, "hidden state")

    def nested_shape(current: Any) -> tuple[int, ...]:
        if not isinstance(current, Sequence) or isinstance(current, (str, bytes, bytearray)):
            return ()
        if not current:
            return (0,)
        child_shapes = tuple(nested_shape(child) for child in current)
        if any(shape != child_shapes[0] for shape in child_shapes[1:]):
            raise A0XModelAdapterError("hidden state must have a rectangular shape")
        return (len(current), *child_shapes[0])

    return nested_shape(plain)


def _finite_hidden_state(value: Any, *, token_count: int, width: int) -> None:
    if _shape(value) != (1, token_count, width):
        raise A0XModelAdapterError("hidden state must have shape [1, token_count, hidden_size]")
    plain = _plain(value, "hidden state")
    try:
        values = (
            float(number)
            for batch in _sequence(plain, "hidden state")
            for row in _sequence(batch, "hidden state")
            for number in _sequence(row, "hidden state")
        )
        if not all(math.isfinite(number) for number in values):
            raise A0XModelAdapterError("hidden state values must be finite")
    except A0XModelAdapterError:
        raise
    except (TypeError, ValueError) as error:
        raise A0XModelAdapterError("hidden state values must be numeric") from error


def _config_integer(config: Any, *, generic: str, aliases: tuple[str, ...], expected: int, name: str) -> None:
    observed = getattr(config, generic, None)
    if observed is None:
        for alias in aliases:
            observed = getattr(config, alias, None)
            if observed is not None:
                break
    if not isinstance(observed, int) or isinstance(observed, bool) or observed != expected:
        raise A0XModelAdapterError(f"unexpected {name}")


def _validate_config(config: Any, card: A0XModelCard) -> None:
    if getattr(config, "model_type", None) != card.model_type:
        raise A0XModelAdapterError("unexpected model_type")
    architectures = getattr(config, "architectures", None)
    if architectures != [card.architecture]:
        raise A0XModelAdapterError("unexpected model architecture")
    _config_integer(
        config, generic="num_hidden_layers", aliases=("n_layer",),
        expected=card.num_hidden_layers, name="num_hidden_layers",
    )
    _config_integer(
        config, generic="hidden_size", aliases=("n_embd",),
        expected=card.hidden_size, name="hidden_size",
    )
    _config_integer(config, generic="vocab_size", aliases=(), expected=card.vocab_size, name="vocab_size")
    _config_integer(
        config, generic="max_position_embeddings", aliases=("n_positions", "n_ctx"),
        expected=card.effective_context, name="effective_context",
    )
    if card.final_transformer_block_tuple_index != card.num_hidden_layers:
        raise A0XModelAdapterError("final transformer block tuple index is inconsistent")


def _validate_runtime_model(model: Any, torch_module: Any) -> None:
    parameters = getattr(model, "parameters", None)
    if not callable(parameters):
        raise A0XModelAdapterError("loaded model parameters are unavailable")
    try:
        observed = list(parameters())
    except Exception as error:
        raise A0XModelAdapterError("could not inspect loaded model parameters") from error
    if not observed:
        raise A0XModelAdapterError("loaded model has no parameters")
    for parameter in observed:
        if getattr(getattr(parameter, "device", None), "type", None) != "cpu":
            raise A0XModelAdapterError("model parameter is not on CPU")
        if getattr(parameter, "dtype", None) != torch_module.float32:
            raise A0XModelAdapterError("model parameter is not float32")


def _outputs_hidden_states(outputs: Any) -> tuple[object, ...]:
    found = outputs.get("hidden_states") if isinstance(outputs, Mapping) else getattr(outputs, "hidden_states", None)
    if not isinstance(found, tuple):
        raise A0XModelAdapterError("model output hidden_states must be a tuple")
    return found


class A0XHiddenStateAdapter:
    """Loads a card-bound local causal LM and extracts its full hidden tuple."""

    def __init__(self, *, tokenizer: Any, model: Any, torch_module: Any, card: A0XModelCard) -> None:
        self.tokenizer = tokenizer
        self.model = model
        self.torch = torch_module
        self.card = card
        self.model_loaded = True

    @classmethod
    def load(
        cls,
        model_root: str | Path,
        *,
        card: A0XModelCard,
        config_factory: Callable[..., Any] | None = None,
        tokenizer_factory: Callable[..., Any] | None = None,
        model_factory: Callable[..., Any] | None = None,
        torch_module: Any | None = None,
    ) -> "A0XHiddenStateAdapter":
        """Construct the model only after all config/tokenizer checks succeed."""
        if not isinstance(model_root, (str, Path)) or not str(model_root) or "://" in str(model_root):
            raise A0XModelAdapterError("model_root must be a non-empty local path")
        if card.trust_remote_code is not False:
            raise A0XModelAdapterError("model card must forbid trust_remote_code")
        if torch_module is None or any(factory is None for factory in (config_factory, tokenizer_factory, model_factory)):
            try:
                import torch
                from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
            except Exception as error:  # pragma: no cover - material dependency boundary
                raise A0XModelAdapterError(f"torch/transformers unavailable: {error}") from error
            torch_module = torch if torch_module is None else torch_module
            config_factory = config_factory or AutoConfig.from_pretrained
            tokenizer_factory = tokenizer_factory or AutoTokenizer.from_pretrained
            model_factory = model_factory or AutoModelForCausalLM.from_pretrained
        root = str(Path(model_root).resolve())
        try:
            config = config_factory(root, **_LOCAL_FACTORIES)
            _validate_config(config, card)
            tokenizer = tokenizer_factory(root, use_fast=True, **_LOCAL_FACTORIES)
            if type(tokenizer).__name__ != card.expected_runtime_tokenizer_class:
                raise A0XModelAdapterError("unexpected runtime tokenizer class")
            if not bool(getattr(tokenizer, "is_fast", False)):
                raise A0XModelAdapterError("fast tokenizer required")
            probe = tokenizer(
                _OFFSET_PROBE, add_special_tokens=True, return_attention_mask=True,
                return_offsets_mapping=True, return_special_tokens_mask=True, return_tensors="pt",
            )
            if not isinstance(probe, Mapping):
                raise A0XModelAdapterError("tokenizer offset probe must return a mapping")
            _offset_tuple(probe.get("offset_mapping"))
            model = model_factory(root, torch_dtype=torch_module.float32, **_LOCAL_FACTORIES)
        except A0XModelAdapterError:
            raise
        except Exception as error:
            raise A0XModelAdapterError(f"local model load failed: {error}") from error
        to_device = getattr(model, "to", None)
        if not callable(to_device):
            raise A0XModelAdapterError("loaded model cannot move to CPU")
        to_device(torch_module.device("cpu"))
        evaluate = getattr(model, "eval", None)
        if not callable(evaluate):
            raise A0XModelAdapterError("loaded model cannot enter evaluation mode")
        evaluate()
        _validate_runtime_model(model, torch_module)
        return cls(tokenizer=tokenizer, model=model, torch_module=torch_module, card=card)

    def tokenize_with_offsets(self, text: str) -> tuple[Mapping[str, Any], tuple[int, ...], tuple[int, ...], tuple[tuple[int, int], ...], tuple[int, ...]]:
        if not isinstance(text, str) or not text:
            raise A0XModelAdapterError("text must be a non-empty string")
        try:
            encoded = self.tokenizer(
                text, add_special_tokens=True, return_attention_mask=True,
                return_offsets_mapping=True, return_special_tokens_mask=True, return_tensors="pt",
            )
        except Exception as error:
            raise A0XModelAdapterError(f"tokenizer failed: {error}") from error
        if not isinstance(encoded, Mapping):
            raise A0XModelAdapterError("tokenizer output must implement Mapping")
        try:
            input_ids = _integer_tuple(encoded["input_ids"], "input_ids")
            attention_mask = _integer_tuple(encoded["attention_mask"], "attention_mask")
            offsets = _offset_tuple(encoded["offset_mapping"])
            special_tokens_mask = _integer_tuple(encoded["special_tokens_mask"], "special_tokens_mask")
        except KeyError as error:
            raise A0XModelAdapterError(f"tokenizer output misses {error.args[0]}") from error
        if not (len(input_ids) == len(attention_mask) == len(offsets) == len(special_tokens_mask)):
            raise A0XModelAdapterError("tokenizer fields must have one common token count")
        return encoded, input_ids, attention_mask, offsets, special_tokens_mask

    def forward_hidden(self, text: str) -> HiddenPayload:
        encoded, input_ids, attention_mask, offsets, special_tokens_mask = self.tokenize_with_offsets(text)
        inference_mode = getattr(self.torch, "inference_mode", None) or getattr(self.torch, "no_grad", None)
        try:
            with (inference_mode() if callable(inference_mode) else nullcontext()):
                outputs = self.model(
                    input_ids=encoded["input_ids"], attention_mask=encoded["attention_mask"],
                    output_hidden_states=True, output_attentions=False, use_cache=False, return_dict=True,
                )
        except Exception as error:
            raise A0XModelAdapterError(f"model forward failed: {error}") from error
        hidden_states = _outputs_hidden_states(outputs)
        if len(hidden_states) != self.card.num_hidden_layers + 1:
            raise A0XModelAdapterError("hidden state tuple must include embedding plus every transformer block")
        for state in hidden_states:
            _finite_hidden_state(state, token_count=len(input_ids), width=self.card.hidden_size)
        return HiddenPayload(
            input_ids=input_ids,
            attention_mask=attention_mask,
            offsets=offsets,
            special_tokens_mask=special_tokens_mask,
            hidden_states=hidden_states,
            final_block_tuple_index=self.card.final_transformer_block_tuple_index,
        )


__all__ = ["A0XHiddenStateAdapter", "A0XModelAdapterError", "HiddenPayload"]
