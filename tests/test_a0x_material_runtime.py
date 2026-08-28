"""Synthetic TDD coverage for the A0X material lifecycle coordinator.

This suite deliberately never creates a model, tokenizer, sealed-target file,
or CCP process.  Every stage is an injected callable and the fake clock makes
the 3,300-second internal budget deterministic.
"""
from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from latent_triz.a0x_contract import Leg, PairBinding
from tests.a0x_test_support import pair_binding


class _Clock:
    def __init__(self, *values: float) -> None:
        self._values = list(values)
        self._last = values[-1] if values else 0.0

    def __call__(self) -> float:
        if self._values:
            self._last = self._values.pop(0)
        return self._last


class A0XMaterialRuntimeTests(unittest.TestCase):
    def _pair(self, leg: Leg = Leg.A0) -> PairBinding:
        return PairBinding.from_mapping(pair_binding(leg, "gpt2"))

    def _dependencies(self, events: list[str], *, fail: str | None = None):
        from latent_triz.a0x_material_runtime import MaterialLifecycleDependencies

        def stage(name: str, value=object()):
            events.append(name)
            if name == fail:
                raise RuntimeError(name)
            return value

        def activation(leg_name: str):
            def callback(model, check_deadline):
                stage("activation", model)
                # The production adapter will invoke this seam around each
                # forward iteration. The synthetic lifecycle proves that no
                # reader, target, or path is passed to this callback.
                self.assertNotIsInstance(model, dict)
                check_deadline("activation-forward-1")
                check_deadline("activation-forward-2")
                return {"sealed_target_capability": False}
            return callback

        def analysis(leg_name: str):
            def callback(target, check_deadline):
                stage("frozen_analysis", target)
                check_deadline(f"analysis-{leg_name}")
                return {"analysis": "frozen"}
            return callback

        def target_evidence(reader):
            return {
                "receipt": "sha256:" + "b" * 64,
                "status": "pass",
                "content_reads": reader["reads"],
                "raw_sha256": "a" * 64,
            }

        def target_read(reader, check_deadline):
            stage("target_read", reader)
            check_deadline("target-read")
            reader["reads"] += 1
            return {"frozen_rows": ["synthetic"]}

        def failure_sealer(stage_name, error, _pair):
            events.append("failure_sealer")
            return {
                "status": "failed",
                "sealed_stage": stage_name,
                "error_type": type(error).__name__,
                "package_path": "/synthetic/failed-package",
            }

        return MaterialLifecycleDependencies(
            static_preflight=lambda _context, _check: stage("static_preflight", None),
            model_identity=lambda _check: stage("model_identity", {"identity": "synthetic"}),
            tokenizer_factory=lambda _check: stage("tokenizer_construction", object()),
            model_factory=lambda _tokenizer, _identity, _check: stage("model_construction", object()),
            activation_by_leg={Leg.A0: activation("a0"), Leg.R1: activation("r1")},
            activation_sealer=lambda _activation, _check: stage("activation_sealing", {"activation": "sealed"}),
            target_reader_factory=lambda _sealed, _check: stage("reader_construction", {"reads": 0}),
            target_read=target_read,
            target_read_evidence=target_evidence,
            analysis_by_leg={Leg.A0: analysis("a0"), Leg.R1: analysis("r1")},
            terminal_sealer=lambda _analysis, _check: stage("terminal_seal", {"status": "null"}),
            package_builder=lambda _terminal, _check: stage("terminal_package", Path("/synthetic/package")),
            package_verifier=lambda _package, _check: stage("independent_package_verification", None),
            protected_tree_postflight=lambda _package, _check: stage("protected_tree_postflight", None),
            failure_sealer=failure_sealer,
            release_model=lambda _model, _check: stage("model_release", None),
        )

    def _run(self, *, pair: PairBinding, dependencies, clock: _Clock | None = None):
        from latent_triz.a0x_material_runtime import run_material_lifecycle

        return run_material_lifecycle(
            pair=pair,
            preflight_context={"pair": pair.run_id},
            dependencies=dependencies,
            monotonic=clock or _Clock(*range(100)),
        )

    def test_lifecycle_has_one_ordered_target_boundary_and_release(self) -> None:
        events: list[str] = []
        result = self._run(pair=self._pair(), dependencies=self._dependencies(events))

        self.assertEqual("completed", result["lifecycle_status"])
        self.assertEqual("null", result["terminal_outcome"]["status"])
        self.assertEqual(
            [
                "static_preflight", "model_identity", "tokenizer_construction",
                "model_construction", "activation", "activation_sealing",
                "reader_construction", "target_read", "frozen_analysis",
                "terminal_seal", "terminal_package",
                "independent_package_verification", "protected_tree_postflight",
                "model_release",
            ],
            events,
        )
        self.assertEqual(1, result["target_content_reads"])
        self.assertEqual(
            [
                "static_preflight", "model_identity", "tokenizer_construction",
                "model_construction", "activation", "activation_sealing",
                "reader_construction", "target_read", "frozen_analysis",
                "terminal_seal", "terminal_package",
                "independent_package_verification", "protected_tree_postflight",
                "model_release",
            ],
            [entry["stage"] for entry in result["stage_timings"]],
        )

    def test_each_pre_terminal_failure_frontier_is_sealed_once(self) -> None:
        frontiers = (
            "static_preflight", "model_identity", "tokenizer_construction",
            "model_construction", "activation", "activation_sealing",
            "reader_construction", "target_read", "frozen_analysis", "terminal_seal",
        )
        for frontier in frontiers:
            with self.subTest(frontier=frontier):
                events: list[str] = []
                result = self._run(
                    pair=self._pair(), dependencies=self._dependencies(events, fail=frontier),
                )
                self.assertEqual("sealed_failure", result["lifecycle_status"])
                self.assertEqual(frontier, result["terminal_outcome"]["sealed_stage"])
                self.assertEqual(1, events.count("failure_sealer"))
                expected_release = 1 if frontier not in {
                    "static_preflight", "model_identity", "tokenizer_construction", "model_construction",
                } else 0
                self.assertEqual(expected_release, events.count("model_release"))
                expected_reads = 1 if frontier in {"frozen_analysis", "terminal_seal"} else 0
                self.assertEqual(expected_reads, result["target_content_reads"])

    def test_post_terminal_failure_preserves_first_terminal_outcome(self) -> None:
        for frontier in (
            "terminal_package", "independent_package_verification", "protected_tree_postflight", "model_release",
        ):
            with self.subTest(frontier=frontier):
                events: list[str] = []
                result = self._run(
                    pair=self._pair(), dependencies=self._dependencies(events, fail=frontier),
                )
                self.assertEqual("post_terminal_failure", result["lifecycle_status"])
                self.assertEqual({"status": "null"}, result["terminal_outcome"])
                self.assertEqual(frontier, result["post_terminal_failure"]["stage"])
                self.assertNotIn("failure_sealer", events)
                self.assertEqual(1, result["target_content_reads"])

    def test_timeout_before_target_is_one_sealed_zero_read_failure(self) -> None:
        events: list[str] = []
        # Initial clock read establishes 0.  The pre-target boundary sees the
        # internal deadline exactly at 3300 seconds.
        result = self._run(
            pair=self._pair(), dependencies=self._dependencies(events),
            clock=_Clock(0.0, *([0.0] * 11), 3_300.0),
        )
        self.assertEqual("sealed_failure", result["lifecycle_status"])
        self.assertEqual(0, result["target_content_reads"])
        self.assertEqual("activation", result["terminal_outcome"]["sealed_stage"])
        self.assertEqual("non_interpretable", result["terminal_outcome"]["status"])
        self.assertEqual("InternalDeadlineExceeded", result["terminal_outcome"]["error_type"])
        self.assertEqual(
            {"reason": "internal_deadline", "stage": "activation", "target_content_reads": 0},
            result["terminal_outcome"]["termination"],
        )
        self.assertNotIn("reader_construction", events)

    def test_timeout_after_target_preserves_one_read_and_never_retries(self) -> None:
        events: list[str] = []
        # The target read completes, then the next analysis boundary reaches
        # the exact deadline.
        result = self._run(
            pair=self._pair(), dependencies=self._dependencies(events),
            clock=_Clock(0.0, *([0.0] * 19), 3_300.0),
        )
        self.assertEqual("sealed_failure", result["lifecycle_status"])
        self.assertEqual(1, result["target_content_reads"])
        self.assertEqual("frozen_analysis", result["terminal_outcome"]["sealed_stage"])
        self.assertEqual("non_interpretable", result["terminal_outcome"]["status"])
        self.assertEqual(1, result["terminal_outcome"]["termination"]["target_content_reads"])
        self.assertEqual(1, events.count("target_read"))

    def test_target_read_failure_before_or_after_open_reports_counter_without_retry(self) -> None:
        from latent_triz.a0x_material_runtime import A0XMaterialRuntimeError

        for opened, error_type in (
            (False, RuntimeError), (True, RuntimeError), (False, A0XMaterialRuntimeError), (True, A0XMaterialRuntimeError),
        ):
            with self.subTest(opened=opened, error_type=error_type.__name__):
                events: list[str] = []
                dependencies = self._dependencies(events)

                def target_read(reader, _check):
                    events.append("target_read")
                    if opened:
                        reader["reads"] += 1
                    raise error_type("synthetic target boundary failure")

                result = self._run(
                    pair=self._pair(), dependencies=replace(dependencies, target_read=target_read),
                )
                self.assertEqual("sealed_failure", result["lifecycle_status"])
                self.assertEqual(int(opened), result["target_content_reads"])
                self.assertEqual(1, events.count("target_read"))

    def test_reader_owned_failure_evidence_covers_reservation_open_hash_parse_and_selection(self) -> None:
        cases = (
            ("reservation_failed", 0),
            ("open_failed", 0),
            ("hash_mismatch", 1),
            ("parse_failed", 1),
            ("selection_mismatch", 1),
        )
        for status, reads in cases:
            with self.subTest(status=status):
                events: list[str] = []
                dependencies = self._dependencies(events)

                def target_read(reader, _check):
                    events.append("target_read")
                    reader["reads"] = reads
                    raise RuntimeError(status)

                def evidence(reader):
                    return {
                        "receipt": "sha256:" + "c" * 64,
                        "status": status,
                        "content_reads": reader["reads"],
                        "raw_sha256": "d" * 64,
                    }

                result = self._run(
                    pair=self._pair(),
                    dependencies=replace(
                        dependencies,
                        target_read=target_read,
                        target_read_evidence=evidence,
                    ),
                )
                self.assertEqual(reads, result["target_content_reads"])
                self.assertEqual(status, result["target_read_evidence"]["status"])
                self.assertEqual(
                    {"receipt", "status", "content_reads", "raw_sha256"},
                    set(result["target_read_evidence"]),
                )

    def test_monotonic_evidence_is_integer_nanoseconds_and_rejects_invalid_samples(self) -> None:
        events: list[str] = []
        result = self._run(pair=self._pair(), dependencies=self._dependencies(events))
        for timing in result["stage_timings"]:
            self.assertTrue(all(
                isinstance(timing[key], int)
                for key in (
                    "started_elapsed_nanoseconds",
                    "finished_elapsed_nanoseconds",
                    "elapsed_nanoseconds",
                )
            ))
            self.assertGreaterEqual(timing["elapsed_nanoseconds"], 0)

        from latent_triz.a0x_material_runtime import A0XMaterialRuntimeError
        for invalid in (float("nan"), float("inf"), float("-inf"), True):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(A0XMaterialRuntimeError, "finite real"):
                self._run(
                    pair=self._pair(), dependencies=self._dependencies([]), clock=_Clock(invalid),
                )
        with self.assertRaisesRegex(A0XMaterialRuntimeError, "moved backwards"):
            self._run(
                pair=self._pair(), dependencies=self._dependencies([]), clock=_Clock(0.0, 1.0, 0.0),
            )

    def test_leg_keyed_dispatch_selects_distinct_a0_and_r1_callbacks(self) -> None:
        selected: list[str] = []

        def run_leg(leg: Leg) -> None:
            events: list[str] = []
            dependencies = self._dependencies(events)

            def activation(label: str):
                def callback(model, check):
                    selected.append(f"activation:{label}")
                    self.assertNotIsInstance(model, dict)
                    check(f"activation:{label}")
                    return {"activation": label}
                return callback

            def analysis(label: str):
                def callback(target, check):
                    selected.append(f"analysis:{label}")
                    self.assertIsInstance(target, dict)
                    check(f"analysis:{label}")
                    return {"analysis": label}
                return callback

            dispatched = replace(
                dependencies,
                activation_by_leg={Leg.A0: activation("a0"), Leg.R1: activation("r1")},
                analysis_by_leg={Leg.A0: analysis("a0"), Leg.R1: analysis("r1")},
            )
            self._run(pair=self._pair(leg), dependencies=dispatched)

        run_leg(Leg.A0)
        run_leg(Leg.R1)
        self.assertEqual(
            ["activation:a0", "analysis:a0", "activation:r1", "analysis:r1"], selected,
        )

    def test_runner_preserves_terminal_outcome_when_terminal_package_fails(self) -> None:
        from latent_triz.a0x_runner import (
            A0XRunnerDependencies,
            _GUARD_EXEC_ACTIVE,
            _run_injected_lifecycle,
        )
        from tests.a0x_test_support import authorization_documents

        events: list[str] = []
        dossier, authorization, chain = authorization_documents(self._pair().as_mapping())
        material = replace(
            self._dependencies(events),
            package_builder=lambda _terminal, _check: (_ for _ in ()).throw(RuntimeError("package")),
        )
        legacy = A0XRunnerDependencies(
            static_preflight=lambda _context: None,
            tokenizer_factory=lambda: object(),
            model_factory=lambda _tokenizer: object(),
            activation=lambda model: model,
            activation_sealer=lambda activation: activation,
            target_capability_factory=lambda activation: activation,
            analysis=lambda target: target,
            package_builder=lambda _analysis: Path("/unused"),
            package_verifier=lambda _package: None,
            protected_tree_postflight=lambda _package: None,
            failure_sealer=lambda *_args: {"status": "failed"},
            release_model=lambda _model: None,
            material_lifecycle=material,
            monotonic=_Clock(*range(100)),
        )
        token = _GUARD_EXEC_ACTIVE.set(True)
        try:
            result = _run_injected_lifecycle(
                pair=self._pair(), chain=chain, dependencies=legacy,
                attempt_claim_path=Path("/unused-claim"), dossier=dossier,
                authorization=authorization, claim_reserved=True, pre_run_context={"synthetic": True},
            )
        finally:
            _GUARD_EXEC_ACTIVE.reset(token)
        self.assertTrue(result["recovery_required"])
        self.assertEqual("null", result["terminal_outcome"]["status"])
        self.assertEqual("terminal_package", result["material_lifecycle"]["post_terminal_failure"]["stage"])
        self.assertIsNone(result["package_path"])

    def test_deadline_after_model_construction_releases_the_stored_model_once(self) -> None:
        events: list[str] = []
        result = self._run(
            pair=self._pair(), dependencies=self._dependencies(events),
            clock=_Clock(0.0, *([0.0] * 7), 3_300.0),
        )
        self.assertEqual("sealed_failure", result["lifecycle_status"])
        self.assertEqual("model_construction", result["terminal_outcome"]["termination"]["stage"])
        self.assertEqual(1, events.count("model_release"))
        self.assertEqual(0, result["target_content_reads"])

    def test_failure_sealer_exception_releases_model_before_propagating(self) -> None:
        from latent_triz.a0x_material_runtime import A0XMaterialRuntimeError

        events: list[str] = []
        dependencies = self._dependencies(events, fail="activation")

        def broken_failure_sealer(*_args):
            events.append("failure_sealer")
            raise RuntimeError("synthetic seal failure")

        with self.assertRaisesRegex(A0XMaterialRuntimeError, "after model cleanup"):
            self._run(
                pair=self._pair(),
                dependencies=replace(dependencies, failure_sealer=broken_failure_sealer),
            )
        self.assertEqual(1, events.count("model_release"))

    def test_analysis_timeout_still_runs_reserved_cleanup_without_deadline_checks(self) -> None:
        events: list[str] = []
        cleanup_checks: list[str] = []
        dependencies = self._dependencies(events)

        def cleanup_stage(name: str, value=None):
            def callback(*args):
                check = args[-1]
                check(name)
                cleanup_checks.append(name)
                events.append(name)
                return value
            return callback

        dependencies = replace(
            dependencies,
            package_builder=cleanup_stage("terminal_package", Path("/synthetic/package")),
            package_verifier=cleanup_stage("independent_package_verification"),
            protected_tree_postflight=cleanup_stage("protected_tree_postflight"),
            release_model=cleanup_stage("model_release"),
        )
        # The analysis callback returns, but the boundary check immediately
        # after it reaches the 3,300-second scientific budget. Packaging and
        # cleanup must still run under the 300-second outer-guard margin.
        result = self._run(
            pair=self._pair(), dependencies=dependencies,
            clock=_Clock(0.0, *([0.0] * 20), 3_300.0),
        )
        self.assertEqual("sealed_failure", result["lifecycle_status"])
        self.assertEqual("non_interpretable", result["terminal_outcome"]["status"])
        self.assertEqual("analysis-a0", result["terminal_outcome"]["termination"]["stage"])
        self.assertEqual(1, result["target_content_reads"])
        self.assertEqual(
            ["terminal_package", "independent_package_verification", "protected_tree_postflight", "model_release"],
            events[-4:],
        )
        self.assertEqual(events[-4:], cleanup_checks)

    def test_a0_and_r1_lifecycles_remain_pair_isolated(self) -> None:
        observations: list[tuple[str, str]] = []

        def dependencies_for(pair: PairBinding):
            events: list[str] = []
            dependencies = self._dependencies(events)
            original = dependencies.static_preflight
            return replace(
                dependencies,
                static_preflight=lambda context, check: (
                    observations.append((pair.leg.value, context["pair"])), original(context, check)
                )[1],
            )

        a0, r1 = self._pair(Leg.A0), self._pair(Leg.R1)
        self._run(pair=a0, dependencies=dependencies_for(a0))
        self._run(pair=r1, dependencies=dependencies_for(r1))
        self.assertEqual(
            [("a0", a0.run_id), ("r1", r1.run_id)], observations,
        )
