"""Injected, fail-closed lifecycle for one A0X material pair.

The coordinator intentionally knows nothing about model libraries, tokenizer
files, CCP, network clients, or sealed-target paths. A later material adapter
must supply those narrow capabilities. This layer only enforces the order,
one-read boundary, immutable first terminal outcome, and the fixed 3,300-second
internal deadline that leaves 300 seconds for sealing and cleanup inside the
3,600-second outer guard envelope.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from time import monotonic as _monotonic
from typing import Any, Callable, Mapping

from .a0x_contract import Leg, PairBinding
from .a0x_execution import AttemptEvent, AttemptState, reduce_attempt
from .a0x_material_contract import INTERNAL_BUDGET_SECONDS


class A0XMaterialRuntimeError(RuntimeError):
    """Raised when an injected lifecycle cannot remain fail-closed."""


class InternalDeadlineExceeded(A0XMaterialRuntimeError):
    """The material phase exhausted its fixed internal budget."""

    def __init__(self, stage: str, elapsed_nanoseconds: int) -> None:
        super().__init__(f"A0X internal deadline exhausted at {stage}")
        self.stage = stage
        self.elapsed_nanoseconds = elapsed_nanoseconds


@dataclass(frozen=True)
class MaterialLifecycleDependencies:
    """Capabilities in the only permitted material lifecycle order.

    No callback receives a sealed-target reader until ``target_read``. The
    activation and analysis callbacks receive ``check_deadline`` so a real
    adapter can call it around every forward iteration without importing a
    clock or a hidden global.
    """

    static_preflight: Callable[[Mapping[str, Any], Callable[[str], None]], Any]
    model_identity: Callable[[Callable[[str], None]], Any]
    tokenizer_factory: Callable[[Callable[[str], None]], Any]
    model_factory: Callable[[Any, Any, Callable[[str], None]], Any]
    activation_by_leg: Mapping[Leg, Callable[[Any, Callable[[str], None]], Any]]
    activation_sealer: Callable[[Any, Callable[[str], None]], Any]
    target_reader_factory: Callable[[Any, Callable[[str], None]], Any]
    target_read: Callable[[Any, Callable[[str], None]], Any]
    target_read_evidence: Callable[[Any], Mapping[str, Any]]
    analysis_by_leg: Mapping[Leg, Callable[[Any, Callable[[str], None]], Any]]
    terminal_sealer: Callable[[Any, AttemptState, Callable[[str], None]], Mapping[str, Any]]
    package_builder: Callable[[Mapping[str, Any], Callable[[str], None]], Path]
    package_verifier: Callable[[Path, Callable[[str], None]], None]
    protected_tree_postflight: Callable[[Path, Callable[[str], None]], None]
    failure_sealer: Callable[[AttemptState, str, BaseException, PairBinding], Mapping[str, Any]]
    release_model: Callable[[Any, Callable[[str], None]], None]


class _Deadline:
    def __init__(self, *, started_at: object, monotonic: Callable[[], object]) -> None:
        self._started_at = _clock_nanoseconds(started_at)
        self._deadline = self._started_at + INTERNAL_BUDGET_SECONDS * 1_000_000_000
        self._monotonic = monotonic
        self._last_observed = self._started_at

    def observe(self) -> int:
        observed = _clock_nanoseconds(self._monotonic())
        if observed < self._last_observed:
            raise A0XMaterialRuntimeError("material lifecycle monotonic clock moved backwards")
        self._last_observed = observed
        return observed - self._started_at

    def check(self, stage: str) -> int:
        elapsed_nanoseconds = self.observe()
        if self._last_observed >= self._deadline:
            raise InternalDeadlineExceeded(stage, elapsed_nanoseconds)
        return elapsed_nanoseconds


def run_material_lifecycle(
    *, pair: PairBinding, preflight_context: Mapping[str, Any],
    dependencies: MaterialLifecycleDependencies,
    monotonic: Callable[[], object] = _monotonic,
) -> dict[str, Any]:
    """Run one injected A0X pair, preserving the first terminal outcome.

    The return value is terminal even if cleanup or verification fails after a
    terminal result has already been sealed. It never retries and records an
    attempted target read at the only callable boundary that can access one.
    """
    if not isinstance(pair, PairBinding):
        raise A0XMaterialRuntimeError("material lifecycle requires a frozen pair binding")
    if not isinstance(preflight_context, Mapping):
        raise A0XMaterialRuntimeError("material lifecycle preflight context is invalid")
    deadline = _Deadline(started_at=monotonic(), monotonic=monotonic)
    model: Any | None = None
    model_release_attempted = False
    target_content_reads = 0
    target_read_evidence: Mapping[str, Any] | None = None
    terminal_outcome: Mapping[str, Any] | None = None
    package_path: Path | None = None
    attempt_state = AttemptState.PREFLIGHT
    stage = "static_preflight"
    stage_timings: list[dict[str, int | str]] = []

    def cleanup_check(_stage: str) -> None:
        """Deliberately no-op inside the outer guard cleanup margin."""

    def record_timing(*, name: str, phase: str, started: int, finished: int) -> None:
        if finished < started:
            raise A0XMaterialRuntimeError("material lifecycle stage timing moved backwards")
        stage_timings.append({
            "stage": name,
            "phase": phase,
            "started_elapsed_nanoseconds": started,
            "finished_elapsed_nanoseconds": finished,
            "elapsed_nanoseconds": finished - started,
        })

    def invoke(name: str, callback: Callable[..., Any], *args: Any) -> Any:
        nonlocal stage
        stage = name
        started = deadline.check(name)
        try:
            result = callback(*args, deadline.check)
        except InternalDeadlineExceeded as error:
            record_timing(name=name, phase="scientific", started=started, finished=error.elapsed_nanoseconds)
            raise
        except A0XMaterialRuntimeError:
            raise
        except BaseException:
            record_timing(name=name, phase="scientific", started=started, finished=deadline.observe())
            raise
        try:
            finished = deadline.check(name)
        except InternalDeadlineExceeded as error:
            record_timing(name=name, phase="scientific", started=started, finished=error.elapsed_nanoseconds)
            raise
        record_timing(name=name, phase="scientific", started=started, finished=finished)
        return result

    def cleanup_invoke(name: str, callback: Callable[..., Any], *args: Any) -> Any:
        """Run a post-terminal action under the outer guard cleanup margin."""
        nonlocal stage
        stage = name
        started = deadline.observe()
        try:
            result = callback(*args, cleanup_check)
        except BaseException:
            record_timing(name=name, phase="cleanup", started=started, finished=deadline.observe())
            raise
        record_timing(name=name, phase="cleanup", started=started, finished=deadline.observe())
        return result

    def release() -> BaseException | None:
        nonlocal model, model_release_attempted
        if model is None or model_release_attempted:
            return None
        model_release_attempted = True
        try:
            # Cleanup may use the final 300-second guard margin. It must run
            # even if the internal analysis budget just elapsed.
            cleanup_invoke("model_release", dependencies.release_model, model)
        except BaseException as error:
            return error
        finally:
            model = None
        return None

    def cleanup_terminal(
        *, lifecycle_status: str, terminal: Mapping[str, Any], sealed_from_state: AttemptState,
    ) -> dict[str, Any]:
        """Use the reserved outer-guard margin after a terminal is selected.

        The internal deadline is an analysis budget, not a permission to skip
        sealing or cleanup. Every callback here receives a no-op deadline seam
        so it cannot accidentally turn an already selected terminal outcome
        into a second internal-deadline failure.
        """
        nonlocal package_path, stage
        post_terminal_failure: dict[str, str] | None = None
        try:
            package_path = cleanup_invoke("terminal_package", dependencies.package_builder, terminal)
            if not isinstance(package_path, Path):
                raise A0XMaterialRuntimeError("terminal package builder did not return a path")
        except BaseException as error:
            post_terminal_failure = {"stage": stage, "error_type": type(error).__name__}
            package_path = None
        if package_path is not None:
            for name, callback in (
                ("independent_package_verification", dependencies.package_verifier),
                ("protected_tree_postflight", dependencies.protected_tree_postflight),
            ):
                try:
                    cleanup_invoke(name, callback, package_path)
                except BaseException as error:
                    if post_terminal_failure is None:
                        post_terminal_failure = {"stage": stage, "error_type": type(error).__name__}
        stage = "model_release"
        cleanup_error = release()
        if cleanup_error is not None and post_terminal_failure is None:
            post_terminal_failure = {"stage": stage, "error_type": type(cleanup_error).__name__}
        final_status = "post_terminal_failure" if lifecycle_status == "completed" and post_terminal_failure else lifecycle_status
        return _result(
            pair=pair, lifecycle_status=final_status, terminal_outcome=terminal,
            package_path=package_path, target_content_reads=target_content_reads,
            target_read_evidence=target_read_evidence,
            post_terminal_failure=post_terminal_failure, stage_timings=stage_timings,
            attempt_state=AttemptState.SEALED, sealed_from_state=sealed_from_state,
        )

    def first_failure(error: BaseException) -> dict[str, Any]:
        nonlocal terminal_outcome, attempt_state
        if terminal_outcome is None:
            failed_stage = stage
            try:
                sealed = cleanup_invoke(
                    "failure_seal",
                    lambda _check: dependencies.failure_sealer(attempt_state, failed_stage, error, pair),
                )
            except BaseException as sealing_error:
                # Release a just-constructed model even when evidence sealing
                # itself failed.  A rejected clock sample is a pre-evidence
                # invariant violation, so it must remain observable as such
                # rather than being relabelled as a sealing error.
                cleanup_error = release()
                if (
                    isinstance(error, A0XMaterialRuntimeError)
                    and "monotonic clock" in str(error)
                    and cleanup_error is None
                ):
                    raise error
                if cleanup_error is not None:
                    raise A0XMaterialRuntimeError(
                        "could not seal first terminal lifecycle outcome and model cleanup failed"
                    ) from sealing_error
                raise A0XMaterialRuntimeError(
                    "could not seal first terminal lifecycle outcome after model cleanup"
                ) from sealing_error
            if not isinstance(sealed, Mapping):
                cleanup_error = release()
                if cleanup_error is not None:
                    raise A0XMaterialRuntimeError(
                        "failure sealer returned an invalid terminal mapping and model cleanup failed"
                    )
                raise A0XMaterialRuntimeError(
                    "failure sealer did not return a terminal mapping after model cleanup"
                )
            terminal_outcome = dict(sealed)
            if isinstance(error, InternalDeadlineExceeded):
                # A full analysis budget is an inconclusive measurement, not a
                # generic software failure. This classification remains fixed
                # whether the one permitted target read has happened or not.
                terminal_outcome.update({
                    "status": "non_interpretable",
                    "termination": {
                        "reason": "internal_deadline",
                        "stage": error.stage,
                        "target_content_reads": target_content_reads,
                    },
                })
            lifecycle_status = "sealed_failure"
        else:
            lifecycle_status = "post_terminal_failure"
        sealed_from_state = attempt_state
        attempt_state = reduce_attempt(attempt_state, AttemptEvent.TERMINAL_SELECTED)
        return cleanup_terminal(
            lifecycle_status=lifecycle_status, terminal=terminal_outcome,
            sealed_from_state=sealed_from_state,
        )

    try:
        invoke("static_preflight", dependencies.static_preflight, preflight_context)
        identity = invoke("model_identity", dependencies.model_identity)
        tokenizer = invoke("tokenizer_construction", dependencies.tokenizer_factory)
        # Store the returned model before the post-construction deadline check,
        # so a just-expired budget cannot skip its required release attempt.
        stage = "model_construction"
        model_started = deadline.check(stage)
        try:
            model = dependencies.model_factory(tokenizer, identity, deadline.check)
        except InternalDeadlineExceeded as error:
            record_timing(name=stage, phase="scientific", started=model_started, finished=error.elapsed_nanoseconds)
            raise
        except A0XMaterialRuntimeError:
            raise
        except BaseException:
            record_timing(name=stage, phase="scientific", started=model_started, finished=deadline.observe())
            raise
        try:
            model_finished = deadline.check(stage)
        except InternalDeadlineExceeded as error:
            record_timing(name=stage, phase="scientific", started=model_started, finished=error.elapsed_nanoseconds)
            raise
        record_timing(name=stage, phase="scientific", started=model_started, finished=model_finished)
        attempt_state = reduce_attempt(attempt_state, AttemptEvent.ACTIVATION_STARTED)
        activation = invoke(
            "activation", _leg_callback(dependencies.activation_by_leg, pair.leg, "activation"), model,
        )
        sealed_activation = invoke("activation_sealing", dependencies.activation_sealer, activation)
        reader = invoke("reader_construction", dependencies.target_reader_factory, sealed_activation)
        attempt_state = reduce_attempt(attempt_state, AttemptEvent.TARGET_RESERVED)
        stage = "target_read"
        target_started = deadline.check(stage)
        try:
            target = dependencies.target_read(reader, deadline.check)
        except InternalDeadlineExceeded as error:
            target_read_evidence = _target_read_evidence(dependencies, reader)
            target_content_reads = target_read_evidence["content_reads"]
            record_timing(name=stage, phase="scientific", started=target_started, finished=error.elapsed_nanoseconds)
            raise
        except A0XMaterialRuntimeError:
            # This exception type can still be raised after the reader opened
            # content. Its class must not bypass the reader-owned evidence
            # probe or turn a single permitted read into a false zero-read
            # receipt.
            target_read_evidence = _target_read_evidence(dependencies, reader)
            target_content_reads = target_read_evidence["content_reads"]
            raise
        except BaseException:
            target_read_evidence = _target_read_evidence(dependencies, reader)
            target_content_reads = target_read_evidence["content_reads"]
            record_timing(name=stage, phase="scientific", started=target_started, finished=deadline.observe())
            raise
        target_read_evidence = _target_read_evidence(dependencies, reader)
        target_content_reads = target_read_evidence["content_reads"]
        if target_read_evidence["status"] != "pass" or target_content_reads != 1:
            record_timing(name=stage, phase="scientific", started=target_started, finished=deadline.observe())
            raise A0XMaterialRuntimeError("successful target boundary evidence is not one passing content read")
        try:
            target_finished = deadline.check(stage)
        except InternalDeadlineExceeded as error:
            record_timing(name=stage, phase="scientific", started=target_started, finished=error.elapsed_nanoseconds)
            raise
        record_timing(name=stage, phase="scientific", started=target_started, finished=target_finished)
        attempt_state = reduce_attempt(attempt_state, AttemptEvent.ANALYSIS_STARTED)
        analysis = invoke(
            "frozen_analysis", _leg_callback(dependencies.analysis_by_leg, pair.leg, "analysis"), target,
        )
        # Analysis ends at the 3,300 second deadline. Once it has returned and
        # the last boundary check passed, terminal sealing is cleanup work
        # covered by the final 300 seconds of the outer guard.
        terminal = cleanup_invoke("terminal_seal", dependencies.terminal_sealer, analysis, attempt_state)
        if not isinstance(terminal, Mapping):
            raise A0XMaterialRuntimeError("terminal sealer did not return a terminal mapping")
        terminal_outcome = dict(terminal)
        sealed_from_state = attempt_state
        attempt_state = reduce_attempt(attempt_state, AttemptEvent.TERMINAL_SELECTED)
        return cleanup_terminal(
            lifecycle_status="completed", terminal=terminal_outcome,
            sealed_from_state=sealed_from_state,
        )
    except BaseException as error:
        return first_failure(error)


def _result(
    *, pair: PairBinding, lifecycle_status: str, terminal_outcome: Mapping[str, Any] | None,
    package_path: Path | None, target_content_reads: int,
    target_read_evidence: Mapping[str, Any] | None,
    post_terminal_failure: Mapping[str, str] | None,
    stage_timings: list[Mapping[str, int | str]],
    attempt_state: AttemptState,
    sealed_from_state: AttemptState,
) -> dict[str, Any]:
    if terminal_outcome is None:
        raise A0XMaterialRuntimeError("material lifecycle ended without a terminal outcome")
    return {
        "pair_binding": pair.as_mapping(),
        "lifecycle_status": lifecycle_status,
        "terminal_outcome": dict(terminal_outcome),
        "package_path": None if package_path is None else str(package_path),
        "target_content_reads": target_content_reads,
        "target_read_evidence": None if target_read_evidence is None else dict(target_read_evidence),
        "post_terminal_failure": None if post_terminal_failure is None else dict(post_terminal_failure),
        "stage_timings": [dict(item) for item in stage_timings],
        "attempt_state": attempt_state.value,
        "sealed_from_state": sealed_from_state.value,
    }


def _target_read_evidence(
    dependencies: MaterialLifecycleDependencies, reader: Any,
) -> dict[str, Any]:
    """Accept only the reader-owned, public-safe terminal boundary evidence."""
    evidence = dependencies.target_read_evidence(reader)
    if not isinstance(evidence, Mapping) or set(evidence) != {
        "receipt", "status", "content_reads", "raw_sha256",
    }:
        raise A0XMaterialRuntimeError("target reader evidence has an invalid public shape")
    receipt = evidence["receipt"]
    status = evidence["status"]
    reads = evidence["content_reads"]
    raw_sha256 = evidence["raw_sha256"]
    if (
        not isinstance(receipt, str)
        or not receipt.startswith("sha256:")
        or len(receipt) != 71
        or not isinstance(raw_sha256, str)
        or len(raw_sha256) != 64
        or any(character not in "0123456789abcdef" for character in receipt[7:] + raw_sha256)
    ):
        raise A0XMaterialRuntimeError("target reader evidence receipt identity is invalid")
    if status not in {
        "pass", "reservation_failed", "open_failed", "hash_mismatch", "parse_failed",
        "selection_mismatch",
    }:
        raise A0XMaterialRuntimeError("target reader evidence status is invalid")
    if not isinstance(reads, int) or isinstance(reads, bool) or reads not in {0, 1}:
        raise A0XMaterialRuntimeError("target reader evidence must report zero or one content read")
    if status == "pass" and reads != 1:
        raise A0XMaterialRuntimeError("passing target reader evidence must report exactly one content read")
    return {
        "receipt": receipt,
        "status": status,
        "content_reads": reads,
        "raw_sha256": raw_sha256,
    }


def _leg_callback(
    callbacks: Mapping[Leg, Callable[[Any, Callable[[str], None]], Any]], leg: Leg, label: str,
) -> Callable[[Any, Callable[[str], None]], Any]:
    """Require two distinct explicit callbacks before any material dispatch."""
    if set(callbacks) != {Leg.A0, Leg.R1}:
        raise A0XMaterialRuntimeError(f"{label} dispatch must bind exactly A0 and R1")
    a0, r1 = callbacks[Leg.A0], callbacks[Leg.R1]
    if not callable(a0) or not callable(r1) or a0 is r1:
        raise A0XMaterialRuntimeError(f"{label} dispatch must use distinct callable legs")
    return callbacks[leg]


def _clock_nanoseconds(value: object) -> int:
    """Normalize one finite, real clock sample to an integer evidence unit."""
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise A0XMaterialRuntimeError("material lifecycle clock sample is not a finite real value")
    scaled = float(value) * 1_000_000_000
    if not math.isfinite(scaled):
        raise A0XMaterialRuntimeError("material lifecycle clock sample cannot be represented as nanoseconds")
    return round(scaled)


__all__ = [
    "A0XMaterialRuntimeError",
    "InternalDeadlineExceeded",
    "MaterialLifecycleDependencies",
    "run_material_lifecycle",
]
