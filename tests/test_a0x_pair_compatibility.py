from __future__ import annotations

import hashlib
import io
import json
import os
import runpy
import stat
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from latent_triz.a0x_compatibility import (
    CompatibilityOracleError,
    check_frozen_pair_compatibility,
    discover_frozen_dossier_paths,
)


ROOT = Path(__file__).resolve().parents[1]
_MODEL_KEYS = (
    "gpt2", "gpt_neo_125m", "qwen2_5_0_5b", "qwen3_0_6b_base", "smollm2_135m", "smollm2_360m",
)
_ADMITTED_PAIR_ENGINEERING_INPUTS = {
    "src/latent_triz/__init__.py": (76, "db06d3f6e4698ca55d12b13a7064e0b2d4bac9c966b5bdd930d3d3faf861d34c"),
    "src/latent_triz/a0x_compatibility.py": (7989, "1c239ad09cc3e1999fe7950659232b6da8521d67bb828d5a584b6f4d2b0e1549"),
    "src/latent_triz/a0x_pair.py": (11618, "82f1ecbfdf6f30cc5b19a311ab1cd67c1a0592ffaf27651d4bda5719f097fe19"),
    "src/latent_triz/validator.py": (15621, "7d3bec9bbfb4960f70f3b18395d7e75cc928e032a25fbec3897c88e48ebeff91"),
    "scripts/a0x_compatibility_check.py": (1403, "c89dc10de43b6b0a341963effa7e5eb854888a38be74b33f74c8aefed51e8b2e"),
    "schemas/a0x-gate-b-authorization.schema.json": (10363, "bc0f52d81a0280a8a59423eb4ab54ed63b06e4753e72ea095e78616873554874"),
    "schemas/a0x-hosted-gate-a-verification-receipt.schema.json": (9987, "bd735639a9b34fb231f0118be9dab40599b407a40a29c17f63f29f0e7c7e680e"),
}
_DOSSIERS = tuple(
    f"experiments/a0x-six-model/approval-dossiers/{leg}/{model}.json"
    for leg in ("a0", "r1") for model in _MODEL_KEYS
)
_TEMPLATES = (
    "tests/fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json",
    "tests/fixtures/a0x/hosted-gate-a/positive/verification-receipt.json",
)
_FORBIDDEN_ROOT_SENTINEL = Path("/__a0x_forbidden_root_sentinel__")
_VERIFIER_SHA256 = "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"


class _PairFixtureAdmissionError(ValueError):
    """A synthetic fixture exceeded its explicit input boundary."""


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns,
    )


def _admit_pair_fixture_inputs(
    sources: dict[str, Path], *, engineering_root: Path, forbidden_roots: tuple[Path, ...] = (),
) -> dict[str, bytes]:
    """Read the exact seven admitted blobs through pinned no-follow descriptors."""
    if set(sources) != set(_ADMITTED_PAIR_ENGINEERING_INPUTS):
        raise _PairFixtureAdmissionError("pair fixture input set is not exact")
    root_text = os.path.abspath(os.fspath(engineering_root))
    if os.fspath(engineering_root) != root_text:
        raise _PairFixtureAdmissionError("engineering root is not canonical")
    for forbidden in forbidden_roots:
        forbidden_text = os.path.abspath(os.fspath(forbidden))
        try:
            within_forbidden = os.path.commonpath((root_text, forbidden_text)) == forbidden_text
        except ValueError:
            within_forbidden = False
        if within_forbidden:
            raise _PairFixtureAdmissionError("engineering root is forbidden")

    root_parts = Path(root_text).parts
    for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS:
        source = sources[relative]
        relative_parts = PurePosixPath(relative).parts
        if not isinstance(source, Path):
            raise _PairFixtureAdmissionError("source is not a Path")
        source_text = os.fspath(source)
        parts = Path(source_text).parts
        if (
            source_text != os.path.abspath(source_text)
            or parts[:-len(relative_parts)] != root_parts
            or parts[-len(relative_parts):] != relative_parts
            or source_text != os.path.join(root_text, *relative_parts)
        ):
            raise _PairFixtureAdmissionError("source path is not the canonical admitted path")

    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    nonblock = getattr(os, "O_NONBLOCK", 0)
    if not nofollow or not directory_flag or not nonblock:
        raise _PairFixtureAdmissionError("no-follow/nonblocking admission is unavailable")
    directory_fds: list[int] = []
    file_fds: list[int] = []
    admitted: dict[str, bytes] = {}
    try:
        for relative, (expected_size, expected_hash) in _ADMITTED_PAIR_ENGINEERING_INPUTS.items():
            relative_parts = PurePosixPath(relative).parts
            parent_fd = os.open(os.sep, os.O_RDONLY | directory_flag | nofollow)
            directory_fds.append(parent_fd)
            for component in (*root_parts[1:], *relative_parts[:-1]):
                parent_fd = os.open(
                    component, os.O_RDONLY | directory_flag | nofollow, dir_fd=parent_fd,
                )
                directory_fds.append(parent_fd)
                if not stat.S_ISDIR(os.fstat(parent_fd).st_mode):
                    raise _PairFixtureAdmissionError("source ancestor is not a directory")

            descriptor = os.open(relative_parts[-1], os.O_RDONLY | nofollow | nonblock, dir_fd=parent_fd)
            file_fds.append(descriptor)
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != expected_size:
                raise _PairFixtureAdmissionError("source is not an exact single-link regular blob")
            content = bytearray()
            while len(content) <= expected_size:
                block = os.read(descriptor, min(65536, expected_size + 1 - len(content)))
                if not block:
                    break
                content.extend(block)
            after = os.fstat(descriptor)
            raw = bytes(content)
            if (
                len(raw) != expected_size
                or hashlib.sha256(raw).hexdigest() != expected_hash
                or _identity(before) != _identity(after)
            ):
                raise _PairFixtureAdmissionError("source changed or failed its admitted hash")
            pinned = os.stat(relative_parts[-1], dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISREG(pinned.st_mode) or _identity(before) != _identity(pinned):
                raise _PairFixtureAdmissionError("source path no longer identifies its admitted descriptor")
            admitted[relative] = raw
    except OSError as error:
        raise _PairFixtureAdmissionError("no-follow source admission failed") from error
    finally:
        for descriptor in reversed(file_fds):
            os.close(descriptor)
        for descriptor in reversed(directory_fds):
            os.close(descriptor)
    return admitted


def _write_owned_file(root: Path, relative: str, data: bytes) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600,
    )
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view):]
    finally:
        os.close(descriptor)


def _write_json(root: Path, relative: str, value: object) -> None:
    _write_owned_file(root, relative, json.dumps(value, sort_keys=True).encode("utf-8"))


def _replace_json(root: Path, relative: str, value: object) -> None:
    path = root / relative
    payload = json.dumps(value, sort_keys=True).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0))
    try:
        view = memoryview(payload)
        while view:
            view = view[os.write(descriptor, view):]
    finally:
        os.close(descriptor)


def _pair_binding(leg: str, model: str, run_id: str) -> dict[str, object]:
    a0 = leg == "a0"
    vectors = 48 * (50 if a0 else 4)
    dense = vectors * 768 * 4
    index_bytes, payload_bytes, cap = (
        (6_291_456, 2_097_152, 33_554_432) if a0 else (1_048_576, 524_288, 4_194_304)
    )
    return {
        "binding_profile": "a0x-pair-scope-v2", "leg": leg,
        "leg_freeze_sha256": ("a" if a0 else "b") * 64,
        "model_key": model, "model_id": f"synthetic-{model}", "revision": "c" * 40,
        "run_id": run_id, "output_path": f"results/a0x/{leg}/{model}/{run_id}",
        "dense_bound": {
            "leg": leg, "cases": 48, "view_site_count": 10 if a0 else 2,
            "endpoint_count": 5 if a0 else 2, "hidden_width": 768, "scalar_bytes": 4,
            "vector_count": vectors, "dense_bytes": dense, "dense_copy_count": 2,
            "atomic_dense_bytes": dense * 2, "index_copy_count": 2,
            "index_reservation_bytes": index_bytes, "payload_allowance_bytes": payload_bytes,
            "total_bytes": dense * 2 + index_bytes + payload_bytes, "cap_bytes": cap,
        },
    }


def _hosted_inputs() -> dict[str, object]:
    evidence = ".a0x-runtime/gate-a/evidence/" + "d" * 40
    return {
        "manifest": {"path": f"{evidence}/hosted-gate-a-evidence.json", "sha256": "e" * 64},
        "attestation_bundle": {"path": f"{evidence}/hosted-gate-a-attestation.bundle.jsonl", "sha256": "e" * 64},
        "trusted_root": {"path": f"{evidence}/github-trusted-root.jsonl", "sha256": "e" * 64},
        "transport": {"path": f"{evidence}/hosted-gate-a-transport.json", "sha256": "e" * 64},
    }


def _synthetic_envelopes(binding: dict[str, object], leg: str, model: str, run_id: str) -> tuple[dict[str, object], dict[str, object]]:
    revision = "1" * 40
    hosted = _hosted_inputs()
    verifier = {
        "role": "github_cli_verifier", "version": "gh version 2.97.0 (2026-07-31)",
        "sha256": _VERIFIER_SHA256, "policy_raw_sha256": "f" * 64,
    }
    authorization = {
        "artifact_class": "a0x-gate-b-authorization",
        "authorization_profile": "a0x-gate-b-authorization-v1", "authorization_status": "authorized",
        "repository": "MarcoPorcellato/Latent-TRIZ", "source_head": revision, "source_tree": revision,
        "job_workflow_sha": revision, "source_sha": revision, "pair_binding": binding,
        "hosted_inputs": hosted, "verifier": verifier,
        "verification_receipt_path": (
            f".a0x-runtime/gate-b-verifications/{revision}/{leg}/{model}/{run_id}/gate-a-verification-receipt.json"
        ),
        "max_verification_count": 1, "stop_boundary": "after_gate_b_runtime_bundle",
        "authorization_id": f"synthetic-auth-{leg}-{model}",
    }
    receipt = {
        "artifact_class": "a0x-hosted-gate-a-verification-receipt",
        "receipt_profile": "a0x-hosted-gate-a-verification-receipt-v1",
        "verification_status": "verified", "repository": "MarcoPorcellato/Latent-TRIZ",
        "qualified_source_head": revision, "qualified_source_tree": revision,
        "pair_binding": binding, "authorization_raw_sha256": "a" * 64,
        "hosted_inputs": hosted, "verifier": verifier, "verified_at": "2026-10-05T00:00:00Z",
    }
    return authorization, receipt


def _synthetic_oracle_root(root: Path, *, engineering_root: Path = ROOT) -> Path:
    sources = {relative: engineering_root / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
    admitted = _admit_pair_fixture_inputs(
        sources, engineering_root=engineering_root, forbidden_roots=(_FORBIDDEN_ROOT_SENTINEL,),
    )
    for relative, data in admitted.items():
        _write_owned_file(root, relative, data)
    first_binding = None
    for leg in ("a0", "r1"):
        for model in _MODEL_KEYS:
            run_id = f"synthetic-{leg}-{model}"
            binding = _pair_binding(leg, model, run_id)
            if first_binding is None:
                first_binding = binding
            _write_json(root, f"experiments/a0x-six-model/approval-dossiers/{leg}/{model}.json", {"pair_binding": binding})
    assert first_binding is not None
    authorization, receipt = _synthetic_envelopes(first_binding, "a0", _MODEL_KEYS[0], f"synthetic-a0-{_MODEL_KEYS[0]}")
    _write_json(root, _TEMPLATES[0], authorization)
    _write_json(root, _TEMPLATES[1], receipt)
    return root


def _snapshot(root: Path) -> tuple[tuple[str, str], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()
    )


def _run_synthetic_cli(root: Path) -> tuple[int, str]:
    script = root / "scripts/a0x_compatibility_check.py"
    previous_path = sys.path[:]
    previous_bytecode = sys.dont_write_bytecode
    try:
        sys.path.insert(0, str(root / "src"))
        sys.dont_write_bytecode = True
        output = io.StringIO()
        with patch("sys.stdout", output):
            namespace = runpy.run_path(str(script), run_name="a0x_synthetic_pair_cli")
            status = namespace["main"](["--root", str(root)])
        return status, output.getvalue()
    finally:
        sys.path[:] = previous_path
        sys.dont_write_bytecode = previous_bytecode


class A0XPairFixtureAdmissionTests(unittest.TestCase):
    def test_incomplete_input_set_is_rejected_before_any_filesystem_probe(self) -> None:
        with (
            patch("builtins.open", side_effect=AssertionError("unexpected open")) as builtin_open,
            patch("io.open", side_effect=AssertionError("unexpected io.open")) as io_open,
            patch("os.open", side_effect=AssertionError("unexpected os.open")) as os_open,
            patch("os.stat", side_effect=AssertionError("unexpected stat")) as os_stat,
            patch("os.lstat", side_effect=AssertionError("unexpected lstat")) as os_lstat,
        ):
            with self.assertRaisesRegex(_PairFixtureAdmissionError, "input set is not exact"):
                _admit_pair_fixture_inputs({}, engineering_root=ROOT)
        for probe in (builtin_open, io_open, os_open, os_stat, os_lstat):
            probe.assert_not_called()

    def test_forbidden_root_sentinel_is_rejected_before_any_filesystem_probe(self) -> None:
        sources = {relative: _FORBIDDEN_ROOT_SENTINEL / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
        with (
            patch("builtins.open", side_effect=AssertionError("unexpected open")) as builtin_open,
            patch("io.open", side_effect=AssertionError("unexpected io.open")) as io_open,
            patch("os.open", side_effect=AssertionError("unexpected os.open")) as os_open,
            patch("os.stat", side_effect=AssertionError("unexpected stat")) as os_stat,
            patch("os.lstat", side_effect=AssertionError("unexpected lstat")) as os_lstat,
        ):
            with self.assertRaisesRegex(_PairFixtureAdmissionError, "forbidden"):
                _admit_pair_fixture_inputs(
                    sources, engineering_root=_FORBIDDEN_ROOT_SENTINEL,
                    forbidden_roots=(_FORBIDDEN_ROOT_SENTINEL,),
                )
        for probe in (builtin_open, io_open, os_open, os_stat, os_lstat):
            probe.assert_not_called()

    def test_complete_inputs_are_admitted_only_from_nofollow_single_link_regular_files(self) -> None:
        sources = {relative: ROOT / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
        stats = []
        real_fstat = os.fstat
        def observe(fd):
            result = real_fstat(fd)
            stats.append(result)
            return result
        with patch("os.open", wraps=os.open) as opens, patch("os.fstat", side_effect=observe):
            admitted = _admit_pair_fixture_inputs(sources, engineering_root=ROOT)
        self.assertEqual(set(_ADMITTED_PAIR_ENGINEERING_INPUTS), set(admitted))
        self.assertTrue(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NONBLOCK"))
        leaves = [call for call in opens.call_args_list if not call.args[1] & os.O_DIRECTORY]
        dirs = [call for call in opens.call_args_list if call.args[1] & os.O_DIRECTORY]
        self.assertEqual(7, len(leaves))
        self.assertGreater(len(dirs), 0)
        for call in opens.call_args_list:
            self.assertTrue(call.args[1] & os.O_NOFOLLOW)
        regular = [item for item in stats if stat.S_ISREG(item.st_mode)]
        self.assertGreaterEqual(len(regular), 14)
        for item in regular:
            self.assertEqual(1, item.st_nlink)
        for relative, data in admitted.items():
            size, digest = _ADMITTED_PAIR_ENGINEERING_INPUTS[relative]
            self.assertEqual(size, len(data))
            self.assertEqual(digest, hashlib.sha256(data).hexdigest())

    def test_noncanonical_source_path_is_rejected_before_any_filesystem_probe(self) -> None:
        sources = {relative: ROOT / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
        relative = next(iter(sources))
        sources[relative] = ROOT / ".." / ROOT.name / relative
        with patch("os.open", side_effect=AssertionError("unexpected open")) as opened:
            with self.assertRaisesRegex(_PairFixtureAdmissionError, "canonical"):
                _admit_pair_fixture_inputs(sources, engineering_root=ROOT)
        opened.assert_not_called()

    def test_valid_key_cannot_map_to_a_different_source_before_probe(self) -> None:
        sources = {relative: ROOT / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
        relative = "src/latent_triz/validator.py"
        sources[relative] = ROOT / "src/latent_triz/a0x_pair.py"
        with patch("os.open", side_effect=AssertionError("unexpected open")) as opened:
            with self.assertRaisesRegex(_PairFixtureAdmissionError, "canonical"):
                _admit_pair_fixture_inputs(sources, engineering_root=ROOT)
        opened.assert_not_called()

    def test_leaf_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _synthetic_oracle_root(Path(directory))
            leaf = root / "src/latent_triz/validator.py"
            leaf.unlink()
            leaf.symlink_to(root / "src/latent_triz/a0x_pair.py")
            sources = {relative: root / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
            with self.assertRaises(_PairFixtureAdmissionError):
                _admit_pair_fixture_inputs(sources, engineering_root=root)

    def test_ancestor_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _synthetic_oracle_root(Path(directory))
            package = root / "src/latent_triz"
            moved = root / "detached-package"
            package.rename(moved)
            package.symlink_to(moved, target_is_directory=True)
            sources = {relative: root / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
            with self.assertRaises(_PairFixtureAdmissionError):
                _admit_pair_fixture_inputs(sources, engineering_root=root)

    def test_hardlinked_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _synthetic_oracle_root(Path(directory))
            os.link(root / "src/latent_triz/validator.py", root / "hardlink-sentinel")
            sources = {relative: root / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
            with self.assertRaisesRegex(_PairFixtureAdmissionError, "single-link"):
                _admit_pair_fixture_inputs(sources, engineering_root=root)

    def test_fifo_input_is_rejected_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _synthetic_oracle_root(Path(directory))
            leaf = root / "src/latent_triz/validator.py"
            leaf.unlink()
            os.mkfifo(leaf)
            sources = {relative: root / relative for relative in _ADMITTED_PAIR_ENGINEERING_INPUTS}
            with self.assertRaisesRegex(_PairFixtureAdmissionError, "single-link regular"):
                _admit_pair_fixture_inputs(sources, engineering_root=root)


class A0XPairCompatibilityTests(unittest.TestCase):
    def _root(self, directory: str) -> Path:
        return _synthetic_oracle_root(Path(directory))

    def test_all_synthetic_dossiers_cross_both_hosted_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = check_frozen_pair_compatibility(self._root(directory))
        self.assertEqual(24, report.expected_case_count)
        self.assertEqual(24, report.passed_case_count)
        self.assertEqual((), report.failures)

    def test_synthetic_oracle_is_repeatable_and_leaves_inputs_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            before = _snapshot(root)
            first = check_frozen_pair_compatibility(root)
            second = check_frozen_pair_compatibility(root)
            after = _snapshot(root)
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_exactly_six_synthetic_models_exist_for_each_leg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = discover_frozen_dossier_paths(self._root(directory))
        self.assertEqual(12, len(paths))
        by_leg = {leg: [path for path in paths if f"/{leg}/" in path.as_posix()] for leg in ("a0", "r1")}
        self.assertEqual(6, len(by_leg["a0"]))
        self.assertEqual(6, len(by_leg["r1"]))

    def test_missing_extra_and_duplicate_synthetic_dossiers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            (root / _DOSSIERS[0]).unlink()
            with self.assertRaisesRegex(CompatibilityOracleError, "missing"):
                check_frozen_pair_compatibility(root)
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            _write_json(root, "experiments/a0x-six-model/approval-dossiers/a0/unexpected.json", {"pair_binding": {}})
            with self.assertRaisesRegex(CompatibilityOracleError, "unexpected"):
                check_frozen_pair_compatibility(root)
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            path = root / _DOSSIERS[0]
            value = json.loads(path.read_text(encoding="utf-8"))
            value["pair_binding"]["model_key"] = _MODEL_KEYS[1]
            _replace_json(root, _DOSSIERS[0], value)
            with self.assertRaisesRegex(CompatibilityOracleError, "duplicate"):
                check_frozen_pair_compatibility(root)

    def test_synthetic_cli_rejects_malformed_dossier_without_bytecode_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            path = root / _DOSSIERS[0]
            value = json.loads(path.read_text(encoding="utf-8"))
            value["pair_binding"]["output_path"] = "not-a-results-path"
            _replace_json(root, _DOSSIERS[0], value)
            before = _snapshot(root)
            status, stdout = _run_synthetic_cli(root)
            after = _snapshot(root)
            self.assertEqual(1, status)
            self.assertIn("failures", stdout)
            self.assertEqual(before, after)
            self.assertFalse((root / "src/latent_triz/__pycache__").exists())

    def test_synthetic_run_id_drift_fails_oracle_with_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            path = root / _DOSSIERS[0]
            value = json.loads(path.read_text(encoding="utf-8"))
            value["pair_binding"]["run_id"] = "schema-valid-different-run"
            _replace_json(root, _DOSSIERS[0], value)
            report = check_frozen_pair_compatibility(root)
            status, stdout = _run_synthetic_cli(root)
        self.assertEqual(24, report.expected_case_count)
        self.assertEqual(22, report.passed_case_count)
        self.assertEqual(2, len(report.failures))
        for failure in report.failures:
            self.assertEqual("a0", failure.leg)
            self.assertEqual(_MODEL_KEYS[0], failure.model_key)
            self.assertEqual("schema-valid-different-run", failure.run_id)
            self.assertIn("schemas/a0x-", failure.consumer)
            self.assertEqual("pair_binding", failure.pointer)
            self.assertIn("derived output path", failure.reason)
        self.assertEqual(1, status)
        self.assertIn("reason=pair binding output path differs from derived output path", stdout)

    def test_synthetic_cli_exit_code_matches_synthetic_oracle_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            report = check_frozen_pair_compatibility(root)
            status, stdout = _run_synthetic_cli(root)
        self.assertEqual(0 if report.passed_case_count == report.expected_case_count else 1, status)
        self.assertIn(
            f"{report.expected_case_count} expected; {report.passed_case_count} passed; {len(report.failures)} failures",
            stdout,
        )


if __name__ == "__main__":
    unittest.main()
