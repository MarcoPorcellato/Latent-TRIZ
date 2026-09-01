"""Capability-based, one-shot A0X sealed-target analysis boundary.

The target path is deliberately confined to :class:`OneShotTargetReader`.
Activation code receives neither this reader nor a target path.  This module is
safe to exercise only with synthetic fixtures until a later, separately
authorized material runner supplies a sealed target capability.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from .a0x_contract import (
    APPROVAL_DOSSIER_PROFILE,
    EXECUTION_AUTHORIZATION_PROFILE,
    Commitment,
    Leg,
    LegFreezeBinding,
    PairBinding,
)


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SELECTION_DOMAIN = "a0x-public-selection-capability-v1"
_A0_SELECTION_PATH = Path("experiments/a0x-six-model/a0-selection-manifest.json")
_R1_MANIFEST_PATH = Path("data/a0r1/manifest.json")
_R1_CASES_PATH = Path("data/a0r1/cases.jsonl")
_COMMON = {
    "empirical": True,
    "scientific_status": "exploratory",
    "evidence_eligible": False,
    "expert_validated": False,
    "claim_ids": [],
}


class A0XExecutionError(RuntimeError):
    """Raised when the one-shot analysis boundary cannot stay fail-closed."""


def validate_authorization_chain(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize one exact, caller-supplied approval commitment chain."""
    try:
        if not isinstance(value, Mapping) or set(value) != {
            "dossier_commitment", "authorization_commitment",
        }:
            raise ValueError("authorization chain fields are not exact")
        dossier = Commitment.from_mapping(_mapping(value, "dossier_commitment"))
        authorization = Commitment.from_mapping(_mapping(value, "authorization_commitment"))
        if dossier.profile != APPROVAL_DOSSIER_PROFILE:
            raise ValueError("dossier commitment profile is invalid")
        if authorization.profile != EXECUTION_AUTHORIZATION_PROFILE:
            raise ValueError("authorization commitment profile is invalid")
    except (TypeError, ValueError) as error:
        raise A0XExecutionError("authorization chain is invalid") from error
    return {
        "dossier_commitment": dossier.as_mapping(),
        "authorization_commitment": authorization.as_mapping(),
    }


class AttemptState(StrEnum):
    PREFLIGHT = "preflight"
    ACTIVATION = "activation"
    ANALYSIS = "analysis"
    SEALED = "sealed"


class AttemptEvent(StrEnum):
    ACTIVATION_STARTED = "activation_started"
    TARGET_RESERVED = "target_reserved"
    ANALYSIS_STARTED = "analysis_started"
    TERMINAL_SELECTED = "terminal_selected"


_ATTEMPT_TRANSITIONS = {
    (AttemptState.PREFLIGHT, AttemptEvent.ACTIVATION_STARTED): AttemptState.ACTIVATION,
    (AttemptState.ACTIVATION, AttemptEvent.TARGET_RESERVED): AttemptState.ANALYSIS,
    (AttemptState.ANALYSIS, AttemptEvent.ANALYSIS_STARTED): AttemptState.ANALYSIS,
    (AttemptState.PREFLIGHT, AttemptEvent.TERMINAL_SELECTED): AttemptState.SEALED,
    (AttemptState.ACTIVATION, AttemptEvent.TERMINAL_SELECTED): AttemptState.SEALED,
    (AttemptState.ANALYSIS, AttemptEvent.TERMINAL_SELECTED): AttemptState.SEALED,
}


def reduce_attempt(state: AttemptState, event: AttemptEvent) -> AttemptState:
    """Apply one legal lifecycle event without performing I/O."""
    if not isinstance(state, AttemptState) or not isinstance(event, AttemptEvent):
        raise A0XExecutionError("A0X attempt transition requires state and event enums")
    try:
        return _ATTEMPT_TRANSITIONS[state, event]
    except KeyError as error:
        raise A0XExecutionError(
            f"illegal A0X attempt transition: {state.value} / {event.value}",
        ) from error


@dataclass(frozen=True)
class FrozenSelectionCapability:
    """Validated public selection identity, with no sealed-target capability.

    The loader opens only a public selection source, computes its byte hash,
    and derives the immutable ordered 48-case identity.  A reader revalidates
    the attestation before it reserves a receipt or can open a target.
    """

    leg: Leg
    leg_freeze_sha256: str
    source_path: str
    source_sha256: str
    ordered_case_ids_sha256: str
    expected_case_ids: tuple[str, ...]
    require_file_exact: bool
    _attestation_sha256: str


def load_a0_public_selection(
    *, repository_root: str | Path, leg_freeze: LegFreezeBinding,
) -> FrozenSelectionCapability:
    """Load the sole canonical A0 selection manifest before target access."""
    return _load_a0_public_selection(Path(repository_root), leg_freeze)


def load_r1_public_selection(
    *, repository_root: str | Path, leg_freeze: LegFreezeBinding,
) -> FrozenSelectionCapability:
    """Load the canonical frozen R1 public corpus before target access."""
    return _load_r1_public_selection(Path(repository_root), leg_freeze)


@dataclass(frozen=True)
class TargetReadReceipt:
    """Immutable evidence of exactly one attempted target-content open."""

    pair_binding: Mapping[str, Any]
    authorization_chain: Mapping[str, Any]
    selection_corpus_sha256: str
    activation_receipt_sha256: str
    dense_sha256: str
    index_sha256: str
    content_reads: int
    status: str
    observed_sha256: str | None

    def as_mapping(self) -> dict[str, Any]:
        return {
            "artifact_class": "a0x-target-read-receipt",
            **_COMMON,
            "pair_binding": dict(self.pair_binding),
            "authorization_chain": dict(self.authorization_chain),
            "selection_corpus_sha256": self.selection_corpus_sha256,
            "activation_receipt_sha256": self.activation_receipt_sha256,
            "dense_sha256": self.dense_sha256,
            "index_sha256": self.index_sha256,
            "content_reads": self.content_reads,
            "status": self.status,
            "observed_sha256": self.observed_sha256,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TargetReadReceipt":
        try:
            if value.get("artifact_class") != "a0x-target-read-receipt":
                raise ValueError("wrong artifact class")
            pair = PairBinding.from_mapping(_mapping(value, "pair_binding")).as_mapping()
            chain = validate_authorization_chain(_mapping(value, "authorization_chain"))
            selection = _sha(value, "selection_corpus_sha256")
            activation = _sha(value, "activation_receipt_sha256")
            dense = _sha(value, "dense_sha256")
            index = _sha(value, "index_sha256")
            reads = value["content_reads"]
            if reads not in (0, 1) or isinstance(reads, bool):
                raise ValueError("content reads must be zero or one")
            status = value["status"]
            if status not in {"pass", "read_failed", "hash_mismatch", "parse_failed", "selection_mismatch"}:
                raise ValueError("unknown target read status")
            observed = value.get("observed_sha256")
            if observed is not None and (not isinstance(observed, str) or not _SHA256.fullmatch(observed)):
                raise ValueError("invalid observed hash")
            if reads == 0 and (status != "read_failed" or observed is not None):
                raise ValueError("zero reads must record a failed open")
            if reads == 1 and status != "read_failed" and observed is None:
                raise ValueError("successful hash/parse must record observed hash")
            return cls(pair, chain, selection, activation, dense, index, reads, status, observed)
        except (KeyError, TypeError, ValueError) as error:
            raise A0XExecutionError("persisted target-read receipt is invalid") from error


class OneShotTargetReader:
    """The sole capability allowed to open the sealed target exactly once.

    Construction atomically reserves the receipt name before any target open.
    A process crash after reservation can therefore leave an empty/incomplete
    receipt file; that file is fail-closed recovery evidence and must never be
    overwritten or treated as a completed read receipt.
    """

    def __init__(
        self,
        *,
        path: str | Path,
        expected_sha256: str,
        receipt_path: str | Path,
        pair_binding: Mapping[str, Any],
        selection: FrozenSelectionCapability,
        activation_receipt_sha256: str,
        dense_sha256: str,
        index_sha256: str,
        authorization_chain: Mapping[str, Any],
    ) -> None:
        self._path = Path(path)
        self._expected_sha256 = _required_sha(expected_sha256, "expected sealed target")
        try:
            parsed_pair = PairBinding.from_mapping(pair_binding)
        except Exception as error:
            raise A0XExecutionError("sealed target pair binding is invalid") from error
        _validate_selection_capability(selection, pair_binding=parsed_pair)
        self._expected_case_ids = selection.expected_case_ids
        self._require_file_exact = selection.require_file_exact
        self._activation_receipt_sha256 = _required_sha(activation_receipt_sha256, "sealed activation")
        self._dense_sha256 = _required_sha(dense_sha256, "sealed activation")
        self._index_sha256 = _required_sha(index_sha256, "sealed activation")
        self._authorization_chain = validate_authorization_chain(authorization_chain)
        self._receipt_path = Path(receipt_path)
        try:
            self._receipt_reservation = self._receipt_path.open("xb")
        except FileExistsError as error:
            raise A0XExecutionError("target-read receipt already exists; incomplete reservation is fail-closed") from error
        except OSError as error:
            raise A0XExecutionError("target-read receipt reservation could not be acquired") from error
        self._pair_binding = parsed_pair.as_mapping()
        self._selection_corpus_sha256 = selection.source_sha256
        self._consumed = False

    def read_jsonl_once(self) -> tuple[list[dict[str, object]], TargetReadReceipt]:
        """Read, hash, parse, select, and receipt the target through one open."""
        if self._consumed:
            raise A0XExecutionError("target reader already consumed")
        self._consumed = True
        status = "read_failed"
        content_reads = 0
        observed_sha256: str | None = None
        parsed: list[dict[str, object]] | None = None
        try:
            try:
                with self._path.open("rb") as stream:
                    content_reads = 1
                    payload = stream.read()
            except OSError as error:
                raise A0XExecutionError("sealed target read failed") from error
            observed_sha256 = hashlib.sha256(payload).hexdigest()
            if observed_sha256 != self._expected_sha256:
                status = "hash_mismatch"
                raise A0XExecutionError("sealed target hash mismatch")
            try:
                parsed = _parse_jsonl(payload)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
                status = "parse_failed"
                raise A0XExecutionError("sealed target parse failed") from error
            try:
                rows = self._select_and_validate(parsed)
            except A0XExecutionError:
                status = "selection_mismatch"
                raise
            status = "pass"
        finally:
            receipt = self._persist_receipt(
                content_reads=content_reads,
                status=status,
                observed_sha256=observed_sha256,
            )
        if parsed is None:  # pragma: no cover - retained for static totality
            raise A0XExecutionError("sealed target did not produce rows")
        return rows, receipt

    def _select_and_validate(self, parsed: list[dict[str, object]]) -> list[dict[str, object]]:
        ids = [_case_id(row) for row in parsed]
        expected = self._expected_case_ids
        if self._require_file_exact:
            if tuple(ids) != expected or len(ids) != len(set(ids)):
                raise A0XExecutionError("sealed target selection mismatch")
            return list(parsed)
        rows_by_id: dict[str, dict[str, object]] = {}
        for case_id, row in zip(ids, parsed, strict=True):
            if case_id in expected:
                if case_id in rows_by_id:
                    raise A0XExecutionError("sealed target selection mismatch")
                rows_by_id[case_id] = row
        if tuple(rows_by_id) and any(case_id not in rows_by_id for case_id in expected):
            raise A0XExecutionError("sealed target selection mismatch")
        if len(rows_by_id) != len(expected):
            raise A0XExecutionError("sealed target selection mismatch")
        return [rows_by_id[case_id] for case_id in expected]

    def _persist_receipt(
        self, *, content_reads: int, status: str, observed_sha256: str | None,
    ) -> TargetReadReceipt:
        receipt = TargetReadReceipt(
            pair_binding=self._pair_binding,
            authorization_chain=self._authorization_chain,
            selection_corpus_sha256=self._selection_corpus_sha256,
            activation_receipt_sha256=self._activation_receipt_sha256,
            dense_sha256=self._dense_sha256,
            index_sha256=self._index_sha256,
            content_reads=content_reads,
            status=status,
            observed_sha256=observed_sha256,
        )
        _validate_artifact("a0x-target-read-receipt.schema.json", receipt.as_mapping())
        try:
            self._receipt_reservation.write(json.dumps(
                receipt.as_mapping(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            ).encode("utf-8") + b"\n")
            self._receipt_reservation.flush()
            self._receipt_reservation.close()
        except OSError as error:
            raise A0XExecutionError("target-read receipt could not be persisted") from error
        return receipt


def advance_attempt(state: AttemptState | str) -> AttemptState:
    """Compatibility wrapper for the canonical linear lifecycle path."""
    try:
        current = AttemptState(state)
    except ValueError as error:
        raise A0XExecutionError("unknown A0X attempt state") from error
    try:
        event = {
            AttemptState.PREFLIGHT: AttemptEvent.ACTIVATION_STARTED,
            AttemptState.ACTIVATION: AttemptEvent.TARGET_RESERVED,
            AttemptState.ANALYSIS: AttemptEvent.TERMINAL_SELECTED,
        }[current]
    except KeyError as error:
        raise A0XExecutionError("sealed A0X attempt cannot be retried") from error
    return reduce_attempt(current, event)


def seal_terminal_attempt(
    *,
    state: AttemptState | str,
    status: str,
    target_receipt_path: str | Path | None = None,
    statistical_result: Mapping[str, Any] | None = None,
    pair_binding: Mapping[str, Any] | None = None,
    authorization_chain: Mapping[str, Any] | None = None,
    terminal_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build the first terminal envelope from a persisted read receipt.

    Pre-analysis failures are necessarily zero-read.  At analysis, a persisted
    receipt is mandatory; direct counters are rejected so an error cannot be
    rewritten into a result.  Callers must then use :func:`advance_attempt` to
    move the returned terminal outcome to the immutable ``SEALED`` state.
    """
    try:
        current = AttemptState(state)
    except ValueError as error:
        raise A0XExecutionError("unknown A0X attempt state") from error
    reduce_attempt(current, AttemptEvent.TERMINAL_SELECTED)
    if status not in {"positive", "null", "non_interpretable", "incompatible", "failed"}:
        raise A0XExecutionError("unknown A0X terminal status")
    if not isinstance(pair_binding, Mapping):
        raise A0XExecutionError("terminal pair binding is required")
    try:
        required_pair = PairBinding.from_mapping(pair_binding).as_mapping()
    except Exception as error:
        raise A0XExecutionError("terminal pair binding is invalid") from error
    try:
        required_chain = validate_authorization_chain(authorization_chain)
    except Exception as error:
        raise A0XExecutionError("terminal authorization chain is required and invalid") from error
    if terminal_path is None:
        raise A0XExecutionError("terminal path is required")
    destination = Path(terminal_path)
    if destination.exists():
        raise A0XExecutionError("terminal artifact already exists")

    target_receipt_sha256: str | None = None
    if current in {AttemptState.PREFLIGHT, AttemptState.ACTIVATION}:
        if target_receipt_path is not None:
            raise A0XExecutionError("pre-analysis terminal outcome must have zero target reads")
        if status not in {"incompatible", "failed"}:
            raise A0XExecutionError("pre-analysis attempt must be incompatible or failed")
        reads = 0
    else:
        if target_receipt_path is None:
            raise A0XExecutionError("analysis terminal outcome requires persisted target-read receipt")
        receipt = _read_persisted_receipt(target_receipt_path)
        reads = receipt.content_reads
        if required_pair != receipt.pair_binding:
            raise A0XExecutionError("terminal pair binding differs from target-read receipt")
        if required_chain != receipt.authorization_chain:
            raise A0XExecutionError("terminal authorization chain differs from target-read receipt")
        target_receipt_sha256 = _sha256_file(Path(target_receipt_path))
        if status in {"positive", "null", "non_interpretable"} and (receipt.status != "pass" or reads != 1):
            raise A0XExecutionError("result terminal outcome requires one passing target read")
        if receipt.status != "pass" and statistical_result is not None:
            raise A0XExecutionError("read error cannot carry a statistical result")

    if status in {"failed", "incompatible"}:
        if statistical_result is not None:
            raise A0XExecutionError("failed or incompatible terminal outcome cannot carry a statistical result")
        statistic: Mapping[str, Any] | None = None
    elif status in {"positive", "null"}:
        if statistical_result is None:
            raise A0XExecutionError("positive or null terminal outcome requires a statistical result")
        _validate_statistical_result(
            statistical_result, status=status, pair_binding=required_pair, authorization_chain=required_chain,
        )
        statistic = dict(statistical_result)
    else:
        if statistical_result is not None:
            raise A0XExecutionError("non-interpretable terminal outcome cannot carry a statistical result")
        statistic = None

    terminal: dict[str, Any] = {
        "artifact_class": "a0x-terminal-result",
        **_COMMON,
        "status": status,
        "sealed_from_state": current.value,
        "analysis_target_content_reads": reads,
        "target_read_receipt_sha256": target_receipt_sha256,
        "statistical_result": statistic,
        "pair_binding": required_pair,
        "authorization_chain": required_chain,
    }
    _validate_artifact("a0x-terminal-result.schema.json", terminal)
    _persist_exclusive(destination, terminal, label="terminal artifact")
    return terminal


def _parse_jsonl(payload: bytes) -> list[dict[str, object]]:
    text = payload.decode("utf-8")
    rows: list[dict[str, object]] = []
    for line in text.splitlines():
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("JSONL target rows must be objects")
        rows.append(value)
    return rows


def _read_persisted_receipt(path: str | Path) -> TargetReadReceipt:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XExecutionError("persisted target-read receipt is unavailable") from error
    if not isinstance(value, Mapping):
        raise A0XExecutionError("persisted target-read receipt is invalid")
    return TargetReadReceipt.from_mapping(value)


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise ValueError(f"{key} must be an object")
    return item


def _sha(value: Mapping[str, Any], key: str) -> str:
    return _required_sha(value[key], key)


def _required_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XExecutionError(f"{label} hash is not sealed")
    return value


def _load_a0_public_selection(
    repository_root: Path, leg_freeze: LegFreezeBinding,
) -> FrozenSelectionCapability:
    _validate_leg_freeze(leg_freeze, expected_leg=Leg.A0)
    source = repository_root / _A0_SELECTION_PATH
    payload, value = _read_public_json(source, label="public A0 selection source")
    source_sha256 = hashlib.sha256(payload).hexdigest()
    _require_freeze_source_hash(leg_freeze, source_sha256)
    _validate_artifact("a0x-selection-manifest.schema.json", value)
    if value.get("artifact_class") != "a0x-selection-manifest" or value.get("target_content_reads") != 0:
        raise A0XExecutionError("public A0 selection source is not target-free")
    return _selection_capability(
        leg_freeze=leg_freeze,
        source_path=_A0_SELECTION_PATH,
        source_sha256=source_sha256,
        case_ids=_selection_case_ids(value),
        require_file_exact=False,
    )


def _load_r1_public_selection(
    repository_root: Path, leg_freeze: LegFreezeBinding,
) -> FrozenSelectionCapability:
    _validate_leg_freeze(leg_freeze, expected_leg=Leg.R1)
    manifest_path = repository_root / _R1_MANIFEST_PATH
    manifest_payload, manifest = _read_public_json(manifest_path, label="public R1 corpus manifest")
    manifest_sha256 = hashlib.sha256(manifest_payload).hexdigest()
    _require_freeze_source_hash(leg_freeze, manifest_sha256)
    _validate_r1_manifest(manifest)

    cases_path = repository_root / _R1_CASES_PATH
    try:
        cases_payload = cases_path.read_bytes()
    except OSError as error:
        raise A0XExecutionError("public R1 cases source is unavailable") from error
    actual_cases_sha256 = hashlib.sha256(cases_payload).hexdigest()
    if actual_cases_sha256 != manifest["cases_sha256"]:
        raise A0XExecutionError("public R1 cases hash differs from frozen manifest")
    case_ids = _public_r1_case_ids(cases_payload)
    manifest_ids = _case_ids(tuple(manifest["case_ids"]))
    if case_ids != manifest_ids:
        raise A0XExecutionError("public R1 cases differ from frozen manifest order")
    return _selection_capability(
        leg_freeze=leg_freeze,
        source_path=_R1_MANIFEST_PATH,
        source_sha256=manifest_sha256,
        case_ids=case_ids,
        require_file_exact=True,
    )


def _read_public_json(path: Path, *, label: str) -> tuple[bytes, Mapping[str, Any]]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, json.JSONDecodeError) as error:
        raise A0XExecutionError(f"{label} is unavailable") from error
    if not isinstance(value, Mapping):
        raise A0XExecutionError(f"{label} must be an object")
    return payload, value


def _validate_leg_freeze(leg_freeze: object, *, expected_leg: Leg) -> None:
    if not isinstance(leg_freeze, LegFreezeBinding):
        raise A0XExecutionError("validated leg freeze binding is required")
    if leg_freeze.leg is not expected_leg:
        raise A0XExecutionError("leg freeze binding has the wrong leg")
    if not isinstance(leg_freeze.protocol_id, str) or not leg_freeze.protocol_id:
        raise A0XExecutionError("leg freeze binding protocol is invalid")
    for value, label in (
        (leg_freeze.protocol_sha256, "leg freeze protocol"),
        (leg_freeze.implementation_sha256, "leg freeze implementation"),
        (leg_freeze.leg_freeze_sha256, "leg freeze"),
        (leg_freeze.protected_tree_sha256, "leg freeze protected tree"),
        (leg_freeze.selection_corpus_sha256, "leg freeze selection"),
    ):
        _required_sha(value, label)


def _require_freeze_source_hash(leg_freeze: LegFreezeBinding, actual_sha256: str) -> None:
    if actual_sha256 != leg_freeze.selection_corpus_sha256:
        raise A0XExecutionError("public selection source hash differs from leg freeze")


def _validate_r1_manifest(value: Mapping[str, Any]) -> None:
    required = {"artifact_class", "cases_path", "cases_sha256", "case_count", "case_ids"}
    if set(value) != required:
        raise A0XExecutionError("public R1 corpus manifest has an invalid frozen format")
    if (
        value.get("artifact_class") != "a0r1-public-corpus-manifest"
        or value.get("cases_path") != _R1_CASES_PATH.as_posix()
        or not isinstance(value.get("cases_sha256"), str)
        or not _SHA256.fullmatch(value["cases_sha256"])
        or value.get("case_count") != 48
        or not isinstance(value.get("case_ids"), list)
    ):
        raise A0XExecutionError("public R1 corpus manifest has an invalid frozen format")
    _case_ids(tuple(value["case_ids"]))


def _public_r1_case_ids(payload: bytes) -> tuple[str, ...]:
    try:
        rows = _parse_jsonl(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise A0XExecutionError("public R1 cases source is invalid") from error
    return _case_ids(tuple(_case_id(row) for row in rows))


def _selection_capability(
    *, leg_freeze: LegFreezeBinding, source_path: Path, source_sha256: str,
    case_ids: tuple[str, ...], require_file_exact: bool,
) -> FrozenSelectionCapability:
    ordered_case_ids_sha256 = _selection_identity_sha256(leg_freeze.leg, case_ids)
    return FrozenSelectionCapability(
        leg=leg_freeze.leg,
        leg_freeze_sha256=leg_freeze.leg_freeze_sha256,
        source_path=source_path.as_posix(),
        source_sha256=source_sha256,
        ordered_case_ids_sha256=ordered_case_ids_sha256,
        expected_case_ids=case_ids,
        require_file_exact=require_file_exact,
        _attestation_sha256=_selection_attestation(
            leg_freeze.leg, leg_freeze.leg_freeze_sha256, source_path.as_posix(),
            source_sha256, ordered_case_ids_sha256, require_file_exact,
        ),
    )


def _selection_case_ids(value: Mapping[str, Any]) -> tuple[str, ...]:
    rows = value.get("cases")
    if not isinstance(rows, list):
        raise A0XExecutionError("public selection source is missing cases")
    try:
        ids = tuple(row["case_id"] for row in rows if isinstance(row, Mapping))
    except (KeyError, TypeError) as error:
        raise A0XExecutionError("public selection source is missing case IDs") from error
    return _case_ids(ids)


def _validate_selection_capability(selection: object, *, pair_binding: PairBinding) -> None:
    if not isinstance(selection, FrozenSelectionCapability):
        raise A0XExecutionError("validated public selection capability is required")
    ids = _case_ids(selection.expected_case_ids)
    if selection.leg is not pair_binding.leg:
        raise A0XExecutionError("public selection leg differs from target pair")
    if selection.leg_freeze_sha256 != pair_binding.leg_freeze_sha256:
        raise A0XExecutionError("public selection leg freeze differs from target pair")
    if selection.require_file_exact is not (selection.leg is Leg.R1):
        raise A0XExecutionError("public selection exact-file mode differs from leg")
    expected_path = _A0_SELECTION_PATH if selection.leg is Leg.A0 else _R1_MANIFEST_PATH
    if selection.source_path != expected_path.as_posix():
        raise A0XExecutionError("public selection source path is not canonical")
    freeze = _required_sha(selection.leg_freeze_sha256, "public selection leg freeze")
    source = _required_sha(selection.source_sha256, "public selection source")
    identity = _required_sha(selection.ordered_case_ids_sha256, "public selection identity")
    if identity != _selection_identity_sha256(selection.leg, ids):
        raise A0XExecutionError("public selection case identity is not immutable")
    expected_attestation = _selection_attestation(
        selection.leg, freeze, selection.source_path, source, identity, selection.require_file_exact,
    )
    if selection._attestation_sha256 != expected_attestation:
        raise A0XExecutionError("public selection capability is not validated")


def _selection_identity_sha256(leg: Leg, ids: tuple[str, ...]) -> str:
    encoded = json.dumps({"leg": leg.value, "case_ids": ids}, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selection_attestation(
    leg: Leg, leg_freeze_sha256: str, source_path: str, source_sha256: str,
    identity_sha256: str, require_file_exact: bool,
) -> str:
    encoded = (
        f"{_SELECTION_DOMAIN}|{leg.value}|{leg_freeze_sha256}|{source_path}|"
        f"{source_sha256}|{identity_sha256}|{require_file_exact}"
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _case_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) != 48 or any(not isinstance(value, str) or not value for value in values):
        raise A0XExecutionError("sealed target selection must contain exactly 48 unique case IDs")
    if len(set(values)) != 48:
        raise A0XExecutionError("sealed target selection must contain exactly 48 unique case IDs")
    return values


def _case_id(row: Mapping[str, object]) -> str:
    value = row.get("case_id")
    if not isinstance(value, str) or not value:
        raise A0XExecutionError("sealed target selection mismatch")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_artifact(schema_name: str, artifact: Mapping[str, Any]) -> None:
    from .validator import validate

    schema_path = Path(__file__).resolve().parents[2] / "schemas" / schema_name
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise A0XExecutionError(f"strict schema {schema_name} is unavailable") from error
    issues = validate(dict(artifact), schema)
    if issues:
        raise A0XExecutionError(f"strict schema {schema_name} rejected produced artifact: {issues[0].message}")


def _validate_statistical_result(
    value: Mapping[str, Any], *, status: str, pair_binding: Mapping[str, Any],
    authorization_chain: Mapping[str, Any],
) -> None:
    if not isinstance(value, Mapping):
        raise A0XExecutionError("statistical result is invalid")
    if value.get("status") != status:
        raise A0XExecutionError("terminal status differs from statistical result status")
    try:
        statistic_pair = PairBinding.from_mapping(_mapping(value, "pair_binding")).as_mapping()
    except Exception as error:
        raise A0XExecutionError("statistical result pair binding is invalid") from error
    if statistic_pair != pair_binding:
        raise A0XExecutionError("terminal pair binding differs from statistical result pair binding")
    if validate_authorization_chain(_mapping(value, "authorization_chain")) != authorization_chain:
        raise A0XExecutionError("terminal authorization chain differs from statistical result authorization chain")
    _validate_artifact("a0x-statistical-result.schema.json", value)
    primary = _mapping(value, "primary")
    outcome = _mapping(value, "outcome_rule")
    try:
        terminal_pair = PairBinding.from_mapping(pair_binding)
        reported_p_value = float(value["p_value"])
        p_value = float(primary["max_statistic_p"])
        margin = float(value["macro_f1_margin_over_surface"])
        successes = int(primary["observed_max_family_successes"] if terminal_pair.leg is Leg.A0 else primary["family_successes"])
    except (KeyError, TypeError, ValueError) as error:
        raise A0XExecutionError("statistical result predicate fields are invalid") from error
    if reported_p_value != p_value:
        raise A0XExecutionError("statistical result p_value differs from primary max-statistic p_value")
    if terminal_pair.leg is Leg.A0:
        positive = p_value <= 0.05 and margin >= 0.10 and successes >= 19
    else:
        directions = value.get("domain_direction_successes")
        if not isinstance(directions, Mapping) or len(directions) != 6:
            raise A0XExecutionError("R1 domain direction evidence must contain exactly six canonical domains")
        try:
            direction_count = int(value["domain_direction_success_count"])
            recomputed_count = sum(float(item) > 0.0 for item in directions.values())
        except (KeyError, TypeError, ValueError) as error:
            raise A0XExecutionError("R1 domain direction fields are invalid") from error
        if direction_count != recomputed_count:
            raise A0XExecutionError("R1 domain direction count differs from direction evidence")
        positive = p_value <= 0.05 and margin >= 0.10 and successes >= 17 and direction_count >= 4
    if (status == "positive") != positive or outcome.get("passed") != positive:
        raise A0XExecutionError("statistical result status violates the frozen positive predicate")


def _persist_exclusive(destination: Path, artifact: Mapping[str, Any], *, label: str) -> None:
    encoded = json.dumps(dict(artifact), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    try:
        with destination.open("xb") as stream:
            stream.write(encoded)
    except FileExistsError as error:
        raise A0XExecutionError(f"{label} already exists") from error
    except OSError as error:
        raise A0XExecutionError(f"{label} could not be persisted") from error


__all__ = [
    "A0XExecutionError",
    "AttemptEvent",
    "AttemptState",
    "FrozenSelectionCapability",
    "OneShotTargetReader",
    "TargetReadReceipt",
    "advance_attempt",
    "load_a0_public_selection",
    "load_r1_public_selection",
    "seal_terminal_attempt",
    "reduce_attempt",
    "validate_authorization_chain",
]
