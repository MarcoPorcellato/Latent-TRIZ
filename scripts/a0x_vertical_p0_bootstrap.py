#!/usr/bin/env python3
"""Fail-closed bootstrap for one authorized A0 / SmolLM2-360M P0 package."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


sys.dont_write_bytecode = True

PROFILE = "a0x-vertical-p0-bootstrap-v1"
SCRIPT_RELATIVE = "scripts/a0x_vertical_p0_bootstrap.py"
LEDGER_DOCUMENT_RELATIVE = (
    "docs/qualification/"
    "a0x-vertical-slice-local-review-77dcae52542d21e9bf16e4f17102abf70e68ffc3.md"
)
LEDGER_COUNT = 137
LEG = "a0"
MODEL_KEY = "smollm2_360m"
MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
MAX_PYTHON_BYTES = 512 * 1024 * 1024
REVISION = re.compile(r"^[a-f0-9]{40}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
LEDGER_LINE = re.compile(r"^([a-f0-9]{64}) ([1-9][0-9]*) (.+)$")

INVALID_ARGUMENT = "A0X_VERTICAL_P0_INVALID_ARGUMENT"
RUNTIME_UNISOLATED = "A0X_VERTICAL_P0_RUNTIME_UNISOLATED"
PYTHON_IDENTITY_MISMATCH = "A0X_VERTICAL_P0_PYTHON_IDENTITY_MISMATCH"
SOURCE_IDENTITY_MISMATCH = "A0X_VERTICAL_P0_SOURCE_IDENTITY_MISMATCH"
CHECKOUT_DIRTY = "A0X_VERTICAL_P0_CHECKOUT_DIRTY"
LAUNCHER_IDENTITY_MISMATCH = "A0X_VERTICAL_P0_LAUNCHER_IDENTITY_MISMATCH"
BOOTSTRAP_IDENTITY_MISMATCH = "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH"
BYTECODE_PRESENT = "A0X_VERTICAL_P0_BYTECODE_PRESENT"
LEDGER_MISMATCH = "A0X_VERTICAL_P0_LEDGER_MISMATCH"
OUTPUT_EXISTS = "A0X_VERTICAL_P0_OUTPUT_EXISTS"
IMPORT_FAILED = "A0X_VERTICAL_P0_IMPORT_FAILED"
INTERNAL_ERROR = "A0X_VERTICAL_P0_INTERNAL_ERROR"
PRIVATE_CLEANUP_UNCERTAIN = "A0X_VERTICAL_P0_PRIVATE_CLEANUP_UNCERTAIN"


class A0XVerticalP0BootstrapError(ValueError):
    """Raised when the P0 bootstrap cannot prove an authorization binding."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class A0XVerticalP0TerminalError(A0XVerticalP0BootstrapError):
    """Raised with a terminal receipt when private cleanup is uncertain."""

    def __init__(self, code: str, receipt: dict[str, Any]):
        super().__init__(code)
        self.receipt = receipt


@dataclass(frozen=True)
class LedgerEvidence:
    sha256: str
    count: int
    total_bytes: int
    document_sha256: str


@dataclass(frozen=True)
class BoundFile:
    relative: str
    raw: bytes
    sha256: str


class RepositoryReader:
    """Descriptor-relative regular, single-link repository reader."""

    def __init__(self, root: Path):
        self.root = root
        self.root_fd: int | None = None

    def __enter__(self) -> "RepositoryReader":
        try:
            self.root_fd = os.open(
                self.root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
        except (AttributeError, OSError) as error:
            raise A0XVerticalP0BootstrapError(LEDGER_MISMATCH) from error
        return self

    def __exit__(self, *_arguments: object) -> None:
        if self.root_fd is not None:
            os.close(self.root_fd)
            self.root_fd = None

    def read(self, relative: str, *, code: str = LEDGER_MISMATCH) -> BoundFile:
        normalized = _safe_relative(relative, code)
        if self.root_fd is None:
            raise A0XVerticalP0BootstrapError(code)
        descriptors: list[int] = []
        try:
            current = os.dup(self.root_fd)
            descriptors.append(current)
            parts = PurePosixPath(normalized).parts
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            for part in parts[:-1]:
                child = os.open(part, flags, dir_fd=current)
                descriptors.append(child)
                current = child
            raw = _read_regular_at(current, parts[-1], MAX_BOUND_FILE_BYTES, code)
        except A0XVerticalP0BootstrapError:
            raise
        except (AttributeError, OSError) as error:
            raise A0XVerticalP0BootstrapError(code) from error
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        return BoundFile(normalized, raw, hashlib.sha256(raw).hexdigest())


def _safe_relative(relative: str, code: str) -> str:
    if not isinstance(relative, str):
        raise A0XVerticalP0BootstrapError(code)
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or path.as_posix() != relative
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise A0XVerticalP0BootstrapError(code)
    return relative


def _read_regular_at(parent_fd: int, name: str, maximum: int, code: str) -> bytes:
    try:
        first = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(first.st_mode)
            or first.st_nlink != 1
            or first.st_size < 1
            or first.st_size > maximum
        ):
            raise A0XVerticalP0BootstrapError(code)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent_fd,
        )
        try:
            checked = os.fstat(descriptor)
            if (
                not stat.S_ISREG(checked.st_mode)
                or checked.st_nlink != 1
                or (checked.st_dev, checked.st_ino, checked.st_size)
                != (first.st_dev, first.st_ino, first.st_size)
            ):
                raise A0XVerticalP0BootstrapError(code)
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            final = os.fstat(descriptor)
            if (
                len(raw) != first.st_size
                or len(raw) > maximum
                or final.st_nlink != 1
                or (final.st_dev, final.st_ino, final.st_size)
                != (first.st_dev, first.st_ino, first.st_size)
            ):
                raise A0XVerticalP0BootstrapError(code)
            return raw
        finally:
            os.close(descriptor)
    except A0XVerticalP0BootstrapError:
        raise
    except (AttributeError, OSError) as error:
        raise A0XVerticalP0BootstrapError(code) from error


def _verify_runtime_isolation() -> None:
    flags = sys.flags
    if not (
        flags.isolated == 1
        and flags.ignore_environment == 1
        and flags.no_site == 1
        and flags.no_user_site == 1
        and flags.dont_write_bytecode == 1
    ):
        raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED)


def _verify_python_identity(expected_path: str, expected_sha256: str) -> dict[str, Any]:
    if (
        not isinstance(expected_path, str)
        or not Path(expected_path).is_absolute()
        or DIGEST.fullmatch(expected_sha256) is None
    ):
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT)
    try:
        expected = Path(expected_path).resolve(strict=True)
        observed = Path(sys.executable).resolve(strict=True)
        metadata = expected.lstat()
        if (
            expected.as_posix() != expected_path
            or observed != expected
            or not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size < 1
            or metadata.st_size > MAX_PYTHON_BYTES
        ):
            raise A0XVerticalP0BootstrapError(PYTHON_IDENTITY_MISMATCH)
        raw = _read_absolute_regular(expected, MAX_PYTHON_BYTES, PYTHON_IDENTITY_MISMATCH)
    except A0XVerticalP0BootstrapError:
        raise
    except (OSError, RuntimeError) as error:
        raise A0XVerticalP0BootstrapError(PYTHON_IDENTITY_MISMATCH) from error
    observed_sha256 = hashlib.sha256(raw).hexdigest()
    if observed_sha256 != expected_sha256:
        raise A0XVerticalP0BootstrapError(PYTHON_IDENTITY_MISMATCH)
    return {
        "path": expected_path,
        "sha256": observed_sha256,
        "bytes": len(raw),
        "implementation": sys.implementation.name,
        "cache_tag": sys.implementation.cache_tag,
        "version": sys.version,
        "flags": {
            "isolated": sys.flags.isolated,
            "ignore_environment": sys.flags.ignore_environment,
            "no_site": sys.flags.no_site,
            "no_user_site": sys.flags.no_user_site,
            "dont_write_bytecode": sys.flags.dont_write_bytecode,
        },
    }


def _read_absolute_regular(path: Path, maximum: int, code: str) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            first = os.fstat(descriptor)
            if (
                not stat.S_ISREG(first.st_mode)
                or first.st_nlink != 1
                or first.st_size < 1
                or first.st_size > maximum
            ):
                raise A0XVerticalP0BootstrapError(code)
            raw = b""
            while len(raw) <= maximum:
                chunk = os.read(descriptor, min(1024 * 1024, maximum + 1 - len(raw)))
                if not chunk:
                    break
                raw += chunk
            final = os.fstat(descriptor)
            if (
                len(raw) != first.st_size
                or len(raw) > maximum
                or final.st_nlink != 1
                or (final.st_dev, final.st_ino, final.st_size)
                != (first.st_dev, first.st_ino, first.st_size)
            ):
                raise A0XVerticalP0BootstrapError(code)
            return raw
        finally:
            os.close(descriptor)
    except A0XVerticalP0BootstrapError:
        raise
    except (AttributeError, OSError) as error:
        raise A0XVerticalP0BootstrapError(code) from error


def _git_output(root: Path, arguments: tuple[str, ...]) -> bytes:
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    try:
        completed = subprocess.run(
            ("/usr/bin/git", "-C", str(root), *arguments),
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise A0XVerticalP0BootstrapError(SOURCE_IDENTITY_MISMATCH) from error
    if completed.returncode != 0:
        raise A0XVerticalP0BootstrapError(SOURCE_IDENTITY_MISMATCH)
    return completed.stdout


def _require_source_state(root: Path, expected_head: str, expected_tree: str) -> None:
    if REVISION.fullmatch(expected_head) is None or REVISION.fullmatch(expected_tree) is None:
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT)
    try:
        head = _git_output(root, ("rev-parse", "--verify", "HEAD^{commit}")).decode(
            "ascii", "strict",
        ).strip()
        tree = _git_output(root, ("rev-parse", "--verify", "HEAD^{tree}")).decode(
            "ascii", "strict",
        ).strip()
    except UnicodeDecodeError as error:
        raise A0XVerticalP0BootstrapError(SOURCE_IDENTITY_MISMATCH) from error
    if head != expected_head or tree != expected_tree:
        raise A0XVerticalP0BootstrapError(SOURCE_IDENTITY_MISMATCH)
    status_raw = _git_output(
        root,
        ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none"),
    )
    if status_raw:
        raise A0XVerticalP0BootstrapError(CHECKOUT_DIRTY)


def _verify_launcher(root: Path, expected_sha256: str) -> dict[str, Any]:
    if DIGEST.fullmatch(expected_sha256) is None:
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT)
    expected = root / SCRIPT_RELATIVE
    try:
        if Path(__file__).resolve(strict=True) != expected.resolve(strict=True):
            raise A0XVerticalP0BootstrapError(LAUNCHER_IDENTITY_MISMATCH)
        with RepositoryReader(root) as reader:
            launcher = reader.read(SCRIPT_RELATIVE, code=LAUNCHER_IDENTITY_MISMATCH)
    except A0XVerticalP0BootstrapError:
        raise
    except (OSError, RuntimeError) as error:
        raise A0XVerticalP0BootstrapError(LAUNCHER_IDENTITY_MISMATCH) from error
    if launcher.sha256 != expected_sha256:
        raise A0XVerticalP0BootstrapError(BOOTSTRAP_IDENTITY_MISMATCH)
    return {
        "path": SCRIPT_RELATIVE,
        "sha256": launcher.sha256,
        "bytes": len(launcher.raw),
    }


def _preexec_evidence(
    arguments: argparse.Namespace,
    launcher_identity: dict[str, Any],
) -> dict[str, Any]:
    if DIGEST.fullmatch(arguments.expected_preexec_sha256) is None:
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT)
    values = (
        arguments.preexec_bootstrap_device,
        arguments.preexec_bootstrap_inode,
        arguments.preexec_bootstrap_bytes,
    )
    if any(re.fullmatch(r"[0-9]+", value) is None for value in values):
        raise A0XVerticalP0BootstrapError(BOOTSTRAP_IDENTITY_MISMATCH)
    device, inode, byte_count = (int(value) for value in values)
    if inode < 1 or byte_count != launcher_identity["bytes"]:
        raise A0XVerticalP0BootstrapError(BOOTSTRAP_IDENTITY_MISMATCH)
    return {
        "profile": "authorization-bound-inline-python-c-v1",
        "source_sha256": arguments.expected_preexec_sha256,
        "bootstrap_descriptor": {
            "device": device,
            "inode": inode,
            "bytes": byte_count,
        },
    }


def _parse_ledger(raw: bytes) -> list[tuple[str, int, str]]:
    try:
        text = raw.decode("utf-8", "strict")
        section = text.split("## Raw P0 package-input ledger", 1)
        if len(section) != 2:
            raise ValueError("ledger section missing")
        block = section[1].split("```text\n", 1)
        if len(block) != 2:
            raise ValueError("ledger fence missing")
        fenced = block[1].split("\n```", 1)
        if len(fenced) != 2:
            raise ValueError("ledger fence unterminated")
        lines = fenced[0].splitlines()
        if len(lines) != LEDGER_COUNT:
            raise ValueError("ledger cardinality differs")
        parsed: list[tuple[str, int, str]] = []
        for line in lines:
            match = LEDGER_LINE.fullmatch(line)
            if match is None:
                raise ValueError("ledger line malformed")
            digest, size, relative = match.groups()
            parsed.append((digest, int(size), _safe_relative(relative, LEDGER_MISMATCH)))
        paths = [relative for _digest, _size, relative in parsed]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("ledger paths are not unique and sorted")
        return parsed
    except (UnicodeDecodeError, ValueError) as error:
        raise A0XVerticalP0BootstrapError(LEDGER_MISMATCH) from error


def _verify_ledger(root: Path, expected_sha256: str) -> LedgerEvidence:
    if DIGEST.fullmatch(expected_sha256) is None:
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT)
    with RepositoryReader(root) as reader:
        document = reader.read(LEDGER_DOCUMENT_RELATIVE)
        declared = _parse_ledger(document.raw)
        actual_lines: list[str] = []
        total_bytes = 0
        for declared_sha256, declared_bytes, relative in declared:
            binding = reader.read(relative)
            if binding.sha256 != declared_sha256 or len(binding.raw) != declared_bytes:
                raise A0XVerticalP0BootstrapError(LEDGER_MISMATCH)
            actual_lines.append(f"{binding.sha256} {len(binding.raw)} {relative}")
            total_bytes += len(binding.raw)
    payload = ("\n".join(actual_lines) + "\n").encode("utf-8")
    observed_sha256 = hashlib.sha256(payload).hexdigest()
    if observed_sha256 != expected_sha256:
        raise A0XVerticalP0BootstrapError(LEDGER_MISMATCH)
    return LedgerEvidence(
        sha256=observed_sha256,
        count=len(actual_lines),
        total_bytes=total_bytes,
        document_sha256=document.sha256,
    )


def _reject_repository_bytecode(root: Path) -> None:
    source_root = root / "src"
    try:
        for directory, names, files in os.walk(source_root, topdown=True, followlinks=False):
            directory_path = Path(directory)
            for name in tuple(names):
                path = directory_path / name
                metadata = path.lstat()
                if name == "__pycache__" or stat.S_ISLNK(metadata.st_mode):
                    raise A0XVerticalP0BootstrapError(BYTECODE_PRESENT)
            for name in files:
                if name.endswith((".pyc", ".pyo", ".so", ".dylib")):
                    raise A0XVerticalP0BootstrapError(BYTECODE_PRESENT)
    except A0XVerticalP0BootstrapError:
        raise
    except OSError as error:
        raise A0XVerticalP0BootstrapError(BYTECODE_PRESENT) from error


def _create_private_pycache() -> Path:
    try:
        # Use the platform's managed temporary root; hosted Linux has no
        # macOS-specific /private/tmp namespace.
        path = Path(tempfile.mkdtemp(prefix="a0x-p0-pycache-"))
        path.chmod(0o700)
        metadata = path.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or any(path.iterdir())
        ):
            raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED)
        sys.pycache_prefix = str(path)
        return path
    except A0XVerticalP0BootstrapError:
        raise
    except OSError as error:
        raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED) from error


def _terminal_receipt(
    receipt: dict[str, Any] | None,
    preflight: dict[str, Any],
    *,
    package_publication: str,
    private_cleanup: str,
    pycache: Path | None = None,
    cleanup_error: OSError | None = None,
) -> dict[str, Any]:
    terminal_receipt = (
        receipt
        if receipt is not None
        else {"artifact_class": "a0x-vertical-p0-terminal-receipt"}
    )
    terminal: dict[str, Any] = {
        "package_publication": package_publication,
        "private_cleanup": private_cleanup,
        "retry_permitted": False,
    }
    if pycache is not None:
        terminal["private_cleanup_path"] = str(pycache)
    if cleanup_error is not None and pycache is not None:
        observation: dict[str, Any] | None = None
        try:
            metadata = pycache.lstat()
            observation = {
                "device": metadata.st_dev,
                "inode": metadata.st_ino,
                "mode": stat.S_IMODE(metadata.st_mode),
                "link_count": metadata.st_nlink,
                "object_type": (
                    "symlink"
                    if stat.S_ISLNK(metadata.st_mode)
                    else "directory"
                    if stat.S_ISDIR(metadata.st_mode)
                    else "other"
                ),
            }
        except OSError:
            pass
        terminal["private_cleanup_error"] = {
            "operation": "shutil.rmtree",
            "errno": cleanup_error.errno,
            "observed_object": observation,
        }
    preflight["terminal"] = terminal
    terminal_receipt["p0_authorization_preflight"] = preflight
    return terminal_receipt


def _prepare_source_import(root: Path) -> None:
    source_root = (root / "src").resolve(strict=True)
    for entry in sys.path:
        if not entry:
            raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED)
        try:
            candidate = Path(entry).resolve(strict=False)
        except (OSError, RuntimeError) as error:
            raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED) from error
        if candidate == root or root in candidate.parents:
            raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED)
    if any(name == "latent_triz" or name.startswith("latent_triz.") for name in sys.modules):
        raise A0XVerticalP0BootstrapError(RUNTIME_UNISOLATED)
    sys.path.insert(0, str(source_root))
    importlib.invalidate_caches()


def _output_relative(expected_head: str) -> str:
    return (
        "experiments/a0x-six-model/vertical-slices/"
        f"{expected_head}/{LEG}/{MODEL_KEY}"
    )


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    try:
        root = Path(arguments.repository_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError) as error:
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT) from error
    if not root.is_dir():
        raise A0XVerticalP0BootstrapError(INVALID_ARGUMENT)

    _verify_runtime_isolation()
    python_identity = _verify_python_identity(
        arguments.expected_python, arguments.expected_python_sha256,
    )
    _require_source_state(root, arguments.expected_head, arguments.expected_tree)
    launcher_identity = _verify_launcher(root, arguments.expected_bootstrap_sha256)
    preexec_evidence = _preexec_evidence(arguments, launcher_identity)
    _reject_repository_bytecode(root)
    ledger = _verify_ledger(root, arguments.expected_ledger_sha256)
    output_relative = _output_relative(arguments.expected_head)
    if (root / output_relative).exists():
        raise A0XVerticalP0BootstrapError(OUTPUT_EXISTS)

    preflight = {
        "profile": PROFILE,
        "source": {"head": arguments.expected_head, "tree": arguments.expected_tree},
        "python": python_identity,
        "preexec_verifier": preexec_evidence,
        "launcher": launcher_identity,
        "input_ledger": {
            "path": LEDGER_DOCUMENT_RELATIVE,
            "document_sha256": ledger.document_sha256,
            "sha256": ledger.sha256,
            "count": ledger.count,
            "total_bytes": ledger.total_bytes,
        },
        "pair": {"leg": LEG, "model_key": MODEL_KEY},
        "maximum_generation_count": 1,
        "repository_bytecode_loaded": False,
    }
    pycache = _create_private_pycache()
    receipt: dict[str, Any] | None = None
    publication_state = "not_started"
    try:
        _require_source_state(root, arguments.expected_head, arguments.expected_tree)
        _reject_repository_bytecode(root)
        _prepare_source_import(root)
        try:
            from latent_triz.a0x_contract import Leg
            from latent_triz.a0x_vertical_slice import (
                VerticalSliceRequest,
                generate_vertical_slice,
            )
        except (ImportError, OSError, RuntimeError) as error:
            raise A0XVerticalP0BootstrapError(IMPORT_FAILED) from error
        request = VerticalSliceRequest(
            leg=Leg.A0,
            model_key=MODEL_KEY,
            implementation_source_head=arguments.expected_head,
            output_root=output_relative,
        )
        publication_state = "uncertain"
        receipt = generate_vertical_slice(root, request)
        publication_state = "published"
        if not isinstance(receipt, dict) or "p0_authorization_preflight" in receipt:
            raise A0XVerticalP0BootstrapError(INTERNAL_ERROR)
        observed_head = _git_output(
            root, ("rev-parse", "--verify", "HEAD^{commit}"),
        ).decode("ascii", "strict").strip()
        observed_tree = _git_output(
            root, ("rev-parse", "--verify", "HEAD^{tree}"),
        ).decode("ascii", "strict").strip()
        if observed_head != arguments.expected_head or observed_tree != arguments.expected_tree:
            raise A0XVerticalP0BootstrapError(SOURCE_IDENTITY_MISMATCH)
        preflight["source"] = {"head": observed_head, "tree": observed_tree}
    except BaseException:
        sys.pycache_prefix = None
        try:
            shutil.rmtree(pycache)
        except OSError as cleanup_error:
            terminal_receipt = _terminal_receipt(
                receipt,
                preflight,
                package_publication=publication_state,
                private_cleanup="uncertain",
                pycache=pycache,
                cleanup_error=cleanup_error,
            )
            raise A0XVerticalP0TerminalError(
                PRIVATE_CLEANUP_UNCERTAIN, terminal_receipt,
            ) from cleanup_error
        raise
    sys.pycache_prefix = None
    try:
        shutil.rmtree(pycache)
    except OSError as cleanup_error:
        terminal_receipt = _terminal_receipt(
            receipt,
            preflight,
            package_publication=publication_state,
            private_cleanup="uncertain",
            pycache=pycache,
            cleanup_error=cleanup_error,
        )
        raise A0XVerticalP0TerminalError(
            PRIVATE_CLEANUP_UNCERTAIN, terminal_receipt,
        ) from cleanup_error
    return _terminal_receipt(
        receipt,
        preflight,
        package_publication=publication_state,
        private_cleanup="complete",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-python", required=True)
    parser.add_argument("--expected-python-sha256", required=True)
    parser.add_argument("--expected-ledger-sha256", required=True)
    parser.add_argument("--expected-bootstrap-sha256", required=True)
    parser.add_argument("--expected-preexec-sha256", required=True)
    parser.add_argument("--preexec-bootstrap-device", required=True)
    parser.add_argument("--preexec-bootstrap-inode", required=True)
    parser.add_argument("--preexec-bootstrap-bytes", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        receipt = run(arguments)
    except A0XVerticalP0TerminalError as error:
        print(
            json.dumps(
                error.receipt,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ),
        )
        print(f"a0x-vertical-p0: {error.code}", file=sys.stderr)
        return 2
    except A0XVerticalP0BootstrapError as error:
        print(f"a0x-vertical-p0: {error.code}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        print(f"a0x-vertical-p0: {INTERNAL_ERROR}", file=sys.stderr)
        return 2
    print(
        json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
