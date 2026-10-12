from __future__ import annotations

import copy
import builtins
from contextlib import ExitStack, contextmanager
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.a0x_contract import (  # noqa: E402
    A0XContractError,
    Leg,
    assert_leg_freeze_binding,
    build_leg_freeze_binding,
    sha256_file,
)
from latent_triz.a0x_freeze import (  # noqa: E402
    A0XFreezeError,
    freeze_a0x_campaign,
    verify_batch_pre_regeneration_ledger,
    verify_frozen_legs,
)
from latent_triz.a0x_runner import (  # noqa: E402
    A0XRunnerError,
    frozen_pair_dossiers,
    verify_a0x_dossier_inventory,
    verify_a0x_no_model,
)
from latent_triz.validator import validate  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "experiments/a0x-six-model"
CANONICAL_PUBLIC_REPOSITORY = "MarcoPorcellato/Latent-TRIZ"
_PROTECTED_TARGET_PATHS = frozenset({
    "data/a0/sealed-targets/targets.jsonl",
    "data/a0/procedural-targets/calibration-targets.jsonl",
    "data/a0r1/targets/calibration.jsonl",
    "data/a0r1/targets/sealed.jsonl",
})


def _refuse_protected_target_io(path: object) -> None:
    try:
        candidate = Path(os.fspath(path))
    except TypeError:
        return
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if candidate.absolute() in {ROOT / relative for relative in _PROTECTED_TARGET_PATHS}:
        raise AssertionError(f"protected target I/O is forbidden in this test: {candidate}")


@contextmanager
def _target_io_guard():
    """Trap direct file opens and copy sources for the real protected inputs."""
    real_copytree = shutil.copytree

    def guard_first_path(function):
        def guarded(path, *args, **kwargs):
            _refuse_protected_target_io(path)
            return function(path, *args, **kwargs)
        return guarded

    def guarded_copytree(src, dst, *args, **kwargs):
        source = Path(src)
        if source.absolute() == ROOT:
            raise AssertionError("whole-repository copy is forbidden in this test")
        for relative in _PROTECTED_TARGET_PATHS:
            if (source / relative).exists():
                raise AssertionError(f"copytree source contains protected target: {source / relative}")
        return real_copytree(src, dst, *args, **kwargs)

    with ExitStack() as stack:
        for target, function in (("builtins.open", builtins.open), ("io.open", io.open),
                                 ("os.open", os.open), ("shutil.copyfile", shutil.copyfile)):
            stack.enter_context(patch(target, side_effect=guard_first_path(function)))
        stack.enter_context(patch("shutil.copytree", side_effect=guarded_copytree))
        yield


def _copy_frozen_verification_fixture(source_root: Path, destination: Path) -> None:
    """Copy only frozen verification inputs; never clone unrelated repository data."""
    campaign = source_root / "experiments/a0x-six-model"
    implementation = json.loads((campaign / "a0/implementation.json").read_text(encoding="utf-8"))
    paths = set(implementation["implementation_paths"])
    paths.update({
        "experiments/a0-automated-weak-proxy/protocol.json",
        "experiments/a0-automated-weak-proxy/implementation.json",
        "experiments/a0r1-independent-proxy/protocol.json",
        "experiments/a0r1-independent-proxy/implementation.json",
        "experiments/a0x-six-model/protected-a0-tree.json",
        "experiments/a0x-six-model/protected-a0r1-tree.json",
        "experiments/a0x-six-model/a0-selection-manifest.json",
        "data/a0r1/manifest.json",
        "experiments/a0x-six-model/a0/protocol.json",
        "experiments/a0x-six-model/a0/implementation.json",
        "experiments/a0x-six-model/r1/protocol.json",
        "experiments/a0x-six-model/r1/implementation.json",
        "experiments/a0x-six-model/freeze/a0-freeze.json",
        "experiments/a0x-six-model/freeze/r1-freeze.json",
        "schemas/a0x-protocol.schema.json",
        "schemas/a0x-implementation.schema.json",
        "schemas/a0x-freeze-manifest.schema.json",
    })
    assert paths.isdisjoint(_PROTECTED_TARGET_PATHS), "fixture input set must exclude all protected targets"
    for relative in sorted(paths):
        _refuse_protected_target_io(source_root / relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / relative, target)
    _refresh_frozen_fixture_inventory(destination)


def _refresh_frozen_fixture_inventory(repository: Path) -> None:
    """Make a scoped fixture internally consistent with its copied current inputs."""
    for leg in ("a0", "r1"):
        implementation_path = repository / f"experiments/a0x-six-model/{leg}/implementation.json"
        implementation = json.loads(implementation_path.read_text(encoding="utf-8"))
        for row in implementation["implementation_files"]:
            path = repository / row["path"]
            row["bytes"] = path.stat().st_size
            row["sha256"] = sha256_file(path)
        implementation_path.write_text(
            json.dumps(implementation, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        freeze_path = repository / f"experiments/a0x-six-model/freeze/{leg}-freeze.json"
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        freeze["implementation_sha256"] = sha256_file(implementation_path)
        freeze_path.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _prepare_historical_parent_for_hosted_replay(
    parent_head: str,
    parent_tree: str,
) -> None:
    """Require the exact historical parent in the local object database; never fetch."""
    environment = _isolated_local_git_environment()
    available = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{parent_head}^{{commit}}"],
        check=False,
        capture_output=True,
        env=environment,
    )
    if available.returncode != 0:
        raise AssertionError("historical parent is unavailable locally; network access is forbidden")
    observed = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", f"{parent_head}^{{tree}}"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if observed.returncode != 0 or observed.stdout.strip() != parent_tree:
        raise AssertionError("local historical parent tree differs")


def _isolated_local_git_environment() -> dict[str, str]:
    """Prevent ambient Git routing/object variables and prohibit remote protocols."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "file:local",
    })
    return environment


@contextmanager
def _offline_local_git_commands():
    """Run real local Git plumbing with lazy fetch disabled and record commands."""
    environment = _isolated_local_git_environment()
    commands: list[list[str]] = []
    real_run = subprocess.run

    def run_local_only(argv, *args, **kwargs):
        command = list(argv) if not isinstance(argv, str) else argv.split()
        if command and command[0] == "git":
            if "fetch" in command or "clone" in command or "pull" in command:
                raise AssertionError(f"network-capable Git command is forbidden: {command}")
            commands.append(command)
            kwargs["env"] = environment
        return real_run(argv, *args, **kwargs)

    with patch.dict(os.environ, environment, clear=True), patch(
        "subprocess.run", side_effect=run_local_only,
    ):
        yield commands


def _copy_public_ledger_fixture(destination: Path, ledger_source: Path) -> tuple[Path, Path]:
    """Copy only the public ledger to a disposable repository outside ROOT."""
    repository = destination.absolute()
    if repository.resolve(strict=False).is_relative_to(ROOT.resolve()):
        raise AssertionError("fixture directory must be outside repository root")
    if repository.exists() or repository.is_symlink():
        raise AssertionError("fixture directory must not already exist")
    ledger_path = repository / "docs/qualification" / ledger_source.name
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_bytes(ledger_source.read_bytes())
    return repository, ledger_path

A0_PROTOCOL_FIELDS = (
    "corpus_generation",
    "calibration_families_per_domain",
    "sealed_families_per_domain",
    "paired_syntax_templates",
    "neutral_domains",
    "target_families",
    "splits",
    "predeclared_calibration_rule",
    "frozen_analysis",
    "views",
    "token_sites",
    "preregistered_layers",
    "shortcut_evaluation",
    "outcome_rules",
    "shortcuts",
    "runtime",
)
R1_PROTOCOL_FIELDS = (
    "protocol_type",
    "independence_audit",
    "runtime",
    "primary_endpoint",
    "sensitivity_endpoints",
    "shortcut_evaluation",
    "thresholds",
    "calibration",
    "outcome_rules",
    "outcome_classes",
)


def load(relative: str) -> dict[str, object]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{relative} is not an object")
    return value


class A0XFrozenPackageTests(unittest.TestCase):
    def test_implementation_inventory_is_sorted_unique_and_regular(self) -> None:
        from latent_triz import a0x_freeze

        paths = a0x_freeze._IMPLEMENTATION_PATHS
        self.assertEqual(tuple(sorted(paths)), paths)
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn("src/latent_triz/a0x_vertical_production_adapter.py", paths)
        self.assertIn("src/latent_triz/a0x_vertical_terminal_package.py", paths)
        self.assertIn("tests/test_a0x_vertical_terminal_package.py", paths)
        self.assertIn("schemas/a0x-vertical-terminal-manifest-v1.schema.json", paths)
        for relative in paths:
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(1, path.stat().st_nlink)

    def test_frozen_protocols_copy_scientific_rules_by_value(self) -> None:
        for leg, source_path, fields, endpoints in (
            ("a0", "experiments/a0-automated-weak-proxy/protocol.json", A0_PROTOCOL_FIELDS, [0, 2, 4, 6]),
            ("r1", "experiments/a0r1-independent-proxy/protocol.json", R1_PROTOCOL_FIELDS, [6]),
        ):
            with self.subTest(leg=leg):
                source = load(source_path)
                protocol = load(f"experiments/a0x-six-model/{leg}/protocol.json")
                self.assertEqual({field: source[field] for field in fields}, protocol["inherited_rules"])
                self.assertEqual(endpoints, protocol["endpoint_indices"])
                self.assertEqual({
                    "model_card_index_field": "final_transformer_block_tuple_index",
                    "required_equal_model_card_field": "num_hidden_layers",
                    "role": "descriptive_sensitivity",
                    "rescues_primary": False,
                }, protocol["descriptive_final_block_endpoint"])
                self.assertEqual(f"a0x-{leg}-six-model-v1", protocol["identity"]["protocol_id"])
                self.assertEqual(source_path, protocol["source_protocol_path"])
                self.assertEqual(sha256_file(ROOT / source_path), protocol["source_protocol_raw_sha256"])
                self.assertFalse(protocol["sealed_targets_accessed"])
                self.assertFalse(protocol["model_output_accessed"])

    def test_implementations_bind_every_declared_source_and_test_file(self) -> None:
        for leg in ("a0", "r1"):
            with self.subTest(leg=leg):
                implementation = load(f"experiments/a0x-six-model/{leg}/implementation.json")
                paths = implementation["implementation_paths"]
                bindings = implementation["implementation_files"]
                self.assertEqual(paths, [row["path"] for row in bindings])
                self.assertIn("tests/test_a0x_frozen_package.py", paths)
                self.assertIn("src/latent_triz/a0x_runner.py", paths)
                self.assertTrue({
                    "scripts/a0x_build_gate_b_runtime.py",
                    "scripts/a0x_prepare_runtime.py",
                    "src/latent_triz/a0x_apfs.py",
                    "src/latent_triz/a0x_gate_b_builder.py",
                    "src/latent_triz/a0x_runtime_bundle.py",
                    "src/latent_triz/a0x_runtime_readiness.py",
                    "src/latent_triz/a0x_wheelhouse.py",
                    "tests/test_a0x_apfs.py",
                    "tests/test_a0x_gate_b_builder.py",
                    "tests/test_a0x_runtime_bundle.py",
                    "tests/test_a0x_runtime_readiness.py",
                    "tests/test_a0x_wheelhouse.py",
                    "schemas/a0x-execution-authorization-v4.schema.json",
                    "schemas/a0x-gate-b-authorization-v2.schema.json",
                    "schemas/a0x-hosted-gate-a-verification-receipt-synthetic-target-free-v1.schema.json",
                    "schemas/a0x-vertical-gate-a-evidence-binding-v1.schema.json",
                    "schemas/a0x-vertical-gate-b-output-v2.schema.json",
                    "schemas/a0x-vertical-package-commitment-v2.schema.json",
                    "schemas/a0x-vertical-slice-manifest-v2.schema.json",
                    "scripts/schema_cross_validate.py",
                    "src/latent_triz/a0x_validator.py",
                    "src/latent_triz/validator.py",
                    "tests/test_a0x_validator.py",
                    "tests/test_a0x_vertical_gate_chain_v2.py",
                    "tests/test_a0x_vertical_runtime_bundle.py",
                    "tests/test_a0x_vertical_slice_v2.py",
                    "docs/qualification/a0x-batch-pre-regeneration-ledger-ab047833.json",
                    "docs/qualification/a0x-vertical-chain-historical-protection.json",
                }.issubset(paths))
                for row in bindings:
                    with self.subTest(leg=leg, path=row["path"]):
                        path = ROOT / row["path"]
                        self.assertEqual(path.stat().st_size, row["bytes"])
                        self.assertEqual(sha256_file(path), row["sha256"])

    def test_implementation_inventory_rejects_a_nonfinal_binding_mutation(self) -> None:
        """Catch an assertion loop that checks only the last row using a scoped snapshot."""
        for leg in ("a0", "r1"):
            with self.subTest(leg=leg), tempfile.TemporaryDirectory() as directory, _target_io_guard():
                for relative in _PROTECTED_TARGET_PATHS:
                    with self.subTest(leg=leg, protected_path=relative):
                        with self.assertRaisesRegex(AssertionError, "protected target I/O is forbidden"):
                            _refuse_protected_target_io(ROOT / relative)
                clone = Path(directory) / "repository"
                clone.mkdir()
                _copy_frozen_verification_fixture(ROOT, clone)
                implementation_path = clone / f"experiments/a0x-six-model/{leg}/implementation.json"
                implementation = json.loads(implementation_path.read_text(encoding="utf-8"))
                from latent_triz import a0x_freeze
                with patch.object(a0x_freeze, "_IMPLEMENTATION_PATHS", tuple(implementation["implementation_paths"])):
                    verify_frozen_legs(clone)
                rows = implementation["implementation_files"]
                self.assertGreater(len(rows), 1)
                nonfinal = rows[0]
                nonfinal["sha256"] = "0" * 64
                implementation_path.write_text(json.dumps(implementation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                with self.assertRaises(A0XFreezeError) as raised:
                    with patch.object(a0x_freeze, "_IMPLEMENTATION_PATHS", tuple(implementation["implementation_paths"])):
                        a0x_freeze.verify_frozen_legs(clone)
                self.assertEqual(f"{leg} source/test hash binding drifted", str(raised.exception))

    def test_target_io_guard_intercepts_protected_open_and_copy_before_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory, _target_io_guard():
            for index, relative in enumerate(sorted(_PROTECTED_TARGET_PATHS)):
                source = ROOT / relative
                destination = Path(directory) / f"copy-{index}.bin"
                with self.subTest(path=relative):
                    with self.assertRaisesRegex(AssertionError, "protected target I/O is forbidden"):
                        open(source, "rb")
                    with self.assertRaisesRegex(AssertionError, "protected target I/O is forbidden"):
                        shutil.copyfile(source, destination)
                    self.assertFalse(destination.exists())
            with self.assertRaisesRegex(AssertionError, "whole-repository copy is forbidden"):
                shutil.copytree(ROOT, Path(directory) / "whole-repository")

    def test_batch_pre_regeneration_ledger_replays_exact_parent_blobs(self) -> None:
        """Keep the one historical batch snapshot auditable without making it active input."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        verified = self._replay_historical_ledger_if_local(
            "d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d",
            "54c59868802af381f57f830102a01be54410e718",
            ledger,
        )
        self.assertEqual("d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d", verified["parent_head"])
        self.assertEqual("54c59868802af381f57f830102a01be54410e718", verified["parent_tree"])
        self.assertEqual(17, verified["entry_count"])
        self.assertEqual(
            "a0x-batch-pre-regeneration-ledger-v1",
            verified["profile"],
        )

    def test_current_batch_pre_regeneration_ledger_replays_exact_parent_blobs(self) -> None:
        """Keep Task 5 generated artifacts auditable before Task 6 replaces them."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-ab047833.json"
        verified = self._replay_historical_ledger_if_local(
            "ab0478331c5bfa9d6b3cb983d5e4550e68f53aa9",
            "ff90ef65cd1ca1c58be620c5241621db5091fa77",
            ledger,
        )
        self.assertEqual("ab0478331c5bfa9d6b3cb983d5e4550e68f53aa9", verified["parent_head"])
        self.assertEqual("ff90ef65cd1ca1c58be620c5241621db5091fa77", verified["parent_tree"])
        self.assertEqual(17, verified["entry_count"])
        self.assertEqual("a0x-batch-pre-regeneration-ledger-v2", verified["profile"])

    def _replay_historical_ledger_if_local(
        self, parent_head: str, parent_tree: str, ledger: Path,
    ) -> dict[str, object]:
        """Verify exact parent blobs offline; missing history fails, never fetches."""
        with _offline_local_git_commands() as commands:
            _prepare_historical_parent_for_hosted_replay(parent_head, parent_tree)
            verified = verify_batch_pre_regeneration_ledger(ROOT, ledger)
        self.assertTrue(commands)
        self.assertTrue(all("fetch" not in command and "clone" not in command and "pull" not in command for command in commands))
        return verified

    def test_historical_ledger_replay_does_not_skip_unavailable_history(self) -> None:
        """Unavailable required history must remain a test failure, not a skip."""
        unavailable_errors = (
            AssertionError("historical parent is unavailable locally; network access is forbidden"),
            A0XFreezeError("historical parent is unavailable"),
            A0XFreezeError("historical Git object is unavailable"),
        )
        for error in unavailable_errors:
            with self.subTest(error=str(error)):
                with (
                    patch(
                        "tests.test_a0x_frozen_package._prepare_historical_parent_for_hosted_replay",
                        side_effect=error,
                    ),
                    patch.object(self, "skipTest", side_effect=AssertionError("skipTest was called")),
                    self.assertRaisesRegex(type(error), str(error)),
                ):
                    self._replay_historical_ledger_if_local(
                        "synthetic-parent", "synthetic-tree", Path("synthetic-ledger.json"),
                    )

    def test_batch_pre_regeneration_ledger_refuses_missing_parent(self) -> None:
        """Historical verification fails when an isolated local repo lacks the parent."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        with tempfile.TemporaryDirectory() as directory, _target_io_guard():
            environment = _isolated_local_git_environment()
            shallow = Path(directory) / "shallow"
            shallow.mkdir()
            completed = subprocess.run(
                ["git", "-C", str(shallow), "init", "--quiet"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            copied = shallow / ledger.relative_to(ROOT)
            copied.parent.mkdir(parents=True, exist_ok=True)
            _refuse_protected_target_io(ledger)
            copied.write_bytes(ledger.read_bytes())
            parent = "d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d"
            absent = subprocess.run(
                ["git", "-C", str(shallow), "cat-file", "-e", f"{parent}^{{commit}}"],
                check=False, capture_output=True, env=environment,
            )
            self.assertNotEqual(0, absent.returncode, "test fixture unexpectedly has historical parent")
            with patch.dict(os.environ, environment, clear=True):
                with self.assertRaisesRegex(A0XFreezeError, "historical parent is unavailable"):
                    verify_batch_pre_regeneration_ledger(shallow, copied)

    def test_historical_parent_preparation_never_fetches_in_hosted_ci_environment(self) -> None:
        """Even canonical-CI environment variables never enable a Git fetch."""
        unavailable = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"")
        calls = []

        def offline_git_only(argv, **kwargs):
            calls.append(argv)
            self.assertNotIn("fetch", argv)
            return unavailable

        with (
            patch.dict(
                os.environ,
                {**_isolated_local_git_environment(), "GITHUB_ACTIONS": "true",
                 "GITHUB_REPOSITORY": CANONICAL_PUBLIC_REPOSITORY},
                clear=True,
            ),
            patch("tests.test_a0x_frozen_package.subprocess.run", side_effect=offline_git_only),
            self.assertRaisesRegex(AssertionError, "historical parent is unavailable locally"),
        ):
            _prepare_historical_parent_for_hosted_replay(
                "d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d",
                "54c59868802af381f57f830102a01be54410e718",
            )
        self.assertEqual(1, len(calls))
        self.assertIn("cat-file", calls[0])

    def test_historical_parent_preparation_verifies_local_tree_without_network(self) -> None:
        unavailable = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"")
        correct_commit = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
        wrong_tree = subprocess.CompletedProcess(args=[], returncode=0, stdout="0" * 40 + "\n", stderr="")
        calls = []

        def local_git_only(argv, **kwargs):
            calls.append(argv)
            self.assertNotIn("fetch", argv)
            if "cat-file" in argv and "-e" in argv:
                return correct_commit
            if "rev-parse" in argv:
                return wrong_tree
            return unavailable

        with (
            patch.dict(
                os.environ,
                {**_isolated_local_git_environment(), "GITHUB_ACTIONS": "true",
                 "GITHUB_REPOSITORY": CANONICAL_PUBLIC_REPOSITORY},
                clear=True,
            ),
            patch(
                "tests.test_a0x_frozen_package.subprocess.run",
                side_effect=local_git_only,
            ),
            self.assertRaisesRegex(AssertionError, "local historical parent tree differs"),
        ):
            _prepare_historical_parent_for_hosted_replay(
                "d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d",
                "54c59868802af381f57f830102a01be54410e718",
            )
        self.assertEqual(2, len(calls))
        self.assertTrue(any("cat-file" in argv for argv in calls))
        self.assertTrue(any("rev-parse" in argv for argv in calls))

    def test_public_symlink_fixture_writer_refuses_repository_root(self) -> None:
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        destination = ROOT / ".a0x-test-fixture-must-not-be-created"
        with self.assertRaisesRegex(AssertionError, "fixture directory must be outside repository root"):
            _copy_public_ledger_fixture(destination, ledger)
        self.assertFalse(destination.exists())

    def test_batch_pre_regeneration_ledger_refuses_symlink_before_resolution(self) -> None:
        """A symlink must not be resolved into an accepted historical ledger."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        with tempfile.TemporaryDirectory() as directory:
            fixture_root, fixture_ledger = _copy_public_ledger_fixture(Path(directory) / "repo", ledger)
            self.assertFalse(fixture_root.is_relative_to(ROOT))
            alias = fixture_root / "ledger-alias.json"
            alias.symlink_to(fixture_ledger)
            with self.assertRaisesRegex(A0XFreezeError, "symlink|independent regular file"):
                verify_batch_pre_regeneration_ledger(fixture_root, alias)

    def test_batch_pre_regeneration_ledger_refuses_parent_symlink_before_resolution(self) -> None:
        """A symlinked parent must not normalize into an accepted ledger path."""
        ledger = ROOT / "docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json"
        with tempfile.TemporaryDirectory() as directory:
            fixture_root, fixture_ledger = _copy_public_ledger_fixture(Path(directory) / "repo", ledger)
            self.assertFalse(fixture_root.is_relative_to(ROOT))
            parent = fixture_ledger.parent
            real = parent / "real"
            real.mkdir()
            copied = real / "ledger.json"
            copied.write_bytes(fixture_ledger.read_bytes())
            alias = parent / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(A0XFreezeError, "symlink"):
                verify_batch_pre_regeneration_ledger(fixture_root, alias / "ledger.json")

    def test_historical_vertical_evidence_manifest_remains_byte_identical(self) -> None:
        manifest = load("docs/qualification/a0x-vertical-chain-historical-protection.json")
        self.assertEqual("a0x-vertical-chain-historical-protection-v1", manifest["profile"])
        self.assertEqual("2026-09-05", manifest["recorded_on"])
        protected = manifest["protected_files"]
        self.assertEqual(7, len(protected))
        self.assertEqual(sorted(item["path"] for item in protected), [item["path"] for item in protected])
        for item in protected:
            with self.subTest(path=item["path"]):
                path = ROOT / item["path"]
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(1, path.stat().st_nlink)
                self.assertEqual(item["bytes"], path.stat().st_size)
                self.assertEqual(item["sha256"], sha256_file(path))

    def test_protocol_implementation_and_freeze_do_not_self_hash(self) -> None:
        forbidden_by_kind = {
            "protocol.json": {"protocol_sha256", "leg_freeze_sha256"},
            "implementation.json": {"implementation_sha256", "leg_freeze_sha256"},
            "freeze.json": {"leg_freeze_sha256"},
        }
        for leg in ("a0", "r1"):
            paths = {
                "protocol.json": CAMPAIGN / leg / "protocol.json",
                "implementation.json": CAMPAIGN / leg / "implementation.json",
                "freeze.json": CAMPAIGN / "freeze" / f"{leg}-freeze.json",
            }
            for kind, path in paths.items():
                with self.subTest(leg=leg, kind=kind):
                    value = json.loads(path.read_text(encoding="utf-8"))
                    self.assertTrue(forbidden_by_kind[kind].isdisjoint(value))

    def test_freeze_bindings_match_exact_components_and_leg_sources(self) -> None:
        selection_raw_sha = sha256_file(CAMPAIGN / "a0-selection-manifest.json")
        r1_manifest_raw_sha = sha256_file(ROOT / "data/a0r1/manifest.json")
        expected_selection = {Leg.A0: selection_raw_sha, Leg.R1: r1_manifest_raw_sha}
        expected_tree = {
            Leg.A0: load("experiments/a0x-six-model/protected-a0-tree.json")["protected_tree_sha256"],
            Leg.R1: load("experiments/a0x-six-model/protected-a0r1-tree.json")["protected_tree_sha256"],
        }
        for leg in (Leg.A0, Leg.R1):
            binding = build_leg_freeze_binding(
                CAMPAIGN / leg.value / "protocol.json",
                CAMPAIGN / leg.value / "implementation.json",
                CAMPAIGN / "freeze" / f"{leg.value}-freeze.json",
            )
            self.assertEqual(expected_selection[leg], binding.selection_corpus_sha256)
            self.assertEqual(expected_tree[leg], binding.protected_tree_sha256)

    def test_twelve_dossiers_are_one_pair_each_and_share_only_their_leg_freeze(self) -> None:
        expected = frozen_pair_dossiers()
        self.assertEqual(12, len(expected))
        cards = load("experiments/a0x-six-model/model-registry.json")["cards"]
        self.assertEqual(6, len(cards))
        schema = load("schemas/a0x-authorization-dossier.schema.json")
        by_leg: dict[Leg, list[dict[str, object]]] = {Leg.A0: [], Leg.R1: []}
        for (leg_name, model_key), relative in expected.items():
            dossier = load(relative)
            self.assertEqual([], validate(dossier, schema))
            self.assertEqual("approval_requested", dossier["dossier_status"])
            pair = dossier["pair_binding"]
            self.assertEqual(leg_name, pair["leg"])
            self.assertEqual(model_key, pair["model_key"])
            self.assertNotIn("authorization_status", dossier)
            by_leg[Leg(leg_name)].append(dossier)
        for leg, dossiers in by_leg.items():
            binding = build_leg_freeze_binding(
                CAMPAIGN / leg.value / "protocol.json",
                CAMPAIGN / leg.value / "implementation.json",
                CAMPAIGN / "freeze" / f"{leg.value}-freeze.json",
            )
            self.assertEqual(1, len({item["pair_binding"]["leg_freeze_sha256"] for item in dossiers}))
            assert_leg_freeze_binding(binding, dossiers)

    def test_wrong_leg_or_freeze_hash_is_rejected(self) -> None:
        dossier = load("experiments/a0x-six-model/approval-dossiers/a0/gpt2.json")
        binding = build_leg_freeze_binding(
            CAMPAIGN / "a0/protocol.json",
            CAMPAIGN / "a0/implementation.json",
            CAMPAIGN / "freeze/a0-freeze.json",
        )
        wrong_leg = copy.deepcopy(dossier)
        wrong_leg["pair_binding"]["leg"] = "r1"
        with self.assertRaises(A0XContractError):
            assert_leg_freeze_binding(binding, [wrong_leg])
        wrong_hash = copy.deepcopy(dossier)
        wrong_hash["pair_binding"]["leg_freeze_sha256"] = "0" * 64
        with self.assertRaises(A0XContractError):
            assert_leg_freeze_binding(binding, [wrong_hash])

    def test_dossier_inventory_rejects_any_extra_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in frozen_pair_dossiers().values():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
            verify_a0x_dossier_inventory(root)
            extra = root / "experiments/a0x-six-model/approval-dossiers/pooled.json"
            extra.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(A0XRunnerError, "inventory"):
                verify_a0x_dossier_inventory(root)

    def test_freeze_generation_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first_directory, tempfile.TemporaryDirectory() as second_directory:
            first = Path(first_directory)
            second = Path(second_directory)
            receipt = freeze_a0x_campaign(
                ROOT,
                prepare_dossiers=True,
                output_root=first,
                implementation_source_head="f" * 40,
            )
            freeze_a0x_campaign(
                ROOT,
                prepare_dossiers=True,
                output_root=second,
                implementation_source_head="f" * 40,
            )
            generated = {
                path.relative_to(first): path.read_bytes()
                for path in sorted((first / "experiments/a0x-six-model").glob("**/*.json"))
            }
            repeated = {
                path.relative_to(second): path.read_bytes()
                for path in sorted((second / "experiments/a0x-six-model").glob("**/*.json"))
            }
            dossier_schema = json.loads(
                (ROOT / "schemas/a0x-authorization-dossier.schema.json").read_text(encoding="utf-8"),
            )
            dossiers = sorted((first / "experiments/a0x-six-model/approval-dossiers").glob("**/*.json"))
            self.assertEqual(12, len(dossiers))
            for dossier_path in dossiers:
                dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
                self.assertEqual("f" * 40, dossier["implementation_source_head"])
                self.assertEqual([], validate(dossier, dossier_schema))
        self.assertEqual(generated, repeated)
        self.assertEqual(12, receipt["dossier_count"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertEqual(0, receipt["model_loads"])
        self.assertEqual(0, receipt["ccp_invocations"])

    def test_regeneration_is_byte_identical_for_same_implementation_head(self) -> None:
        """The committed implementation anchor regenerates the tracked package byte-for-byte."""
        current_implementation_head = json.loads((
            CAMPAIGN / "approval-dossiers/a0/gpt2.json"
        ).read_text(encoding="utf-8"))["implementation_source_head"]
        with tempfile.TemporaryDirectory() as directory:
            generated_root = Path(directory)
            freeze_a0x_campaign(
                ROOT,
                prepare_dossiers=True,
                implementation_source_head=current_implementation_head,
                output_root=generated_root,
            )
            tracked_paths = [
                CAMPAIGN / leg / filename
                for leg in ("a0", "r1")
                for filename in ("protocol.json", "implementation.json")
            ] + [
                CAMPAIGN / "freeze" / f"{leg}-freeze.json"
                for leg in ("a0", "r1")
            ] + [
                ROOT / relative for relative in frozen_pair_dossiers().values()
            ]
            tracked = {
                path.relative_to(ROOT): path.read_bytes() for path in sorted(tracked_paths)
            }
            regenerated = {
                path.relative_to(generated_root): path.read_bytes()
                for path in sorted((generated_root / "experiments/a0x-six-model").glob("**/*.json"))
            }
        self.assertEqual(tracked, regenerated)

    def test_freeze_generator_requires_an_explicit_implementation_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TypeError, "implementation_source_head"):
                freeze_a0x_campaign(ROOT, prepare_dossiers=True, output_root=Path(directory))

    def test_no_model_verifier_is_a_strict_frozen_phase_superset(self) -> None:
        receipt = verify_a0x_no_model(ROOT)
        self.assertEqual("frozen_no_model", receipt["phase"])
        self.assertEqual(2, receipt["frozen_leg_count"])
        self.assertEqual(12, receipt["approval_requested_dossier_count"])
        self.assertFalse(receipt["model_loaded"])
        self.assertFalse(receipt["tokenizer_constructed"])
        self.assertEqual(0, receipt["sealed_target_content_reads"])
        self.assertFalse(receipt["ccp_invoked"])
        self.assertFalse(receipt["remote_mutations"])

    def test_tracked_no_model_receipt_matches_canonical_recomputation(self) -> None:
        """The tracked receipt is an exact canonical projection, not merely valid JSON."""
        from scripts.a0x_materialize_no_model_receipt import _canonical_receipt_bytes

        tracked = ROOT / "results/a0x/preexecution/a0x-no-model-verification-receipt.json"
        self.assertEqual(_canonical_receipt_bytes(verify_a0x_no_model(ROOT)), tracked.read_bytes())


if __name__ == "__main__":
    unittest.main()
