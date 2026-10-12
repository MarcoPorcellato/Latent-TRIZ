#!/usr/bin/env python3
"""Canonical operator inlet for one A0X vertical P0 v2 package."""

from __future__ import annotations

import argparse
import dataclasses
import enum
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import secrets
from pathlib import Path


PROFILE = "a0x-vertical-p0-bootstrap-v2"
SCRIPT_RELATIVE = "scripts/a0x_vertical_p0_v2.py"
PREEXEC_RELATIVE = "scripts/a0x_vertical_p0_preexec_v2.py"
_PREEXEC_HANDOFF = "__a0x_vertical_p0_v2_preexec_handoff__"
LEDGER_DOCUMENT_RELATIVE = (
    "docs/qualification/"
    "a0x-vertical-slice-local-review-77dcae52542d21e9bf16e4f17102abf70e68ffc3.md"
)
LEDGER_COUNT = 137
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_LEDGER_LINE = re.compile(r"^([a-f0-9]{64}) ([1-9][0-9]*) (.+)$")
_MAX_PYTHON_BYTES = 256 * 1024 * 1024
_MAX_BOUND_FILE_BYTES = 64 * 1024 * 1024
_GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
}


class _ConsumedClaimFailure(ValueError):
    def __init__(self, claim_relative: str) -> None:
        super().__init__("A0X_VERTICAL_P0_V2_ATTEMPT_CLAIM_FAILED")
        self.claim_relative = claim_relative


def _json_shape(value: object) -> object:
    """Convert the validated production binding to a canonical JSON-safe receipt value."""
    if dataclasses.is_dataclass(value):
        return {field.name: _json_shape(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return _json_shape(value.value)
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _json_shape(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_shape(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError("A0X_VERTICAL_P0_V2_COMPLETION_BINDING_MISMATCH")


def _claim_relative(head: str, tree: str, attempt_id: str) -> str:
    if not attempt_id or "/" in attempt_id or attempt_id in {".", ".."}:
        raise ValueError("A0X_VERTICAL_P0_V2_INVALID_ATTEMPT_ID")
    return (
        f".a0x-runtime/attempts/p0/v2/{head}/{tree}/a0/smollm2_360m/"
        f"{attempt_id}/attempt-claim.json"
    )


def _package_relative(head: str, tree: str) -> str:
    return f".a0x-runtime/p0/v2/{head}/{tree}/a0/smollm2_360m"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-python", required=True)
    parser.add_argument("--expected-python-sha256", required=True)
    parser.add_argument("--expected-ledger-sha256", required=True)
    parser.add_argument("--ledger-profile", choices=("historical-v1", "current-source-inventory-v1"), default="historical-v1")
    parser.add_argument("--expected-bootstrap-sha256", required=True)
    parser.add_argument("--expected-preexec-sha256", required=True)
    parser.add_argument("--preexec-launcher", required=True)
    parser.add_argument("--preexec-bootstrap-device", required=True)
    parser.add_argument("--preexec-bootstrap-inode", required=True)
    parser.add_argument("--preexec-bootstrap-bytes", required=True)
    parser.add_argument("--authorization-document", required=True)
    parser.add_argument("--authorization-document-sha256", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    return parser


def _require_source_identity(root: Path, head: str, tree: str) -> None:
    if _REVISION.fullmatch(head) is None or _REVISION.fullmatch(tree) is None:
        raise ValueError("A0X_VERTICAL_P0_V2_SOURCE_IDENTITY_MISMATCH")
    observed: list[str] = []
    for expression in ("HEAD", "HEAD^{tree}"):
        completed = subprocess.run(
            ("/usr/bin/git", "-C", str(root), "rev-parse", "--verify", expression),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, check=False, env=_GIT_ENV,
        )
        if completed.returncode != 0:
            raise ValueError("A0X_VERTICAL_P0_V2_SOURCE_IDENTITY_MISMATCH")
        observed.append(completed.stdout.strip())
    if tuple(observed) != (head, tree):
        raise ValueError("A0X_VERTICAL_P0_V2_SOURCE_IDENTITY_MISMATCH")


def _require_clean_checkout(root: Path) -> None:
    completed = subprocess.run(
        (
            "/usr/bin/git", "-C", str(root), "status", "--porcelain=v1", "-z",
            "--untracked-files=all", "--ignore-submodules=none",
        ),
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        check=False,
        env=_GIT_ENV,
    )
    if completed.returncode != 0:
        raise ValueError("A0X_VERTICAL_P0_V2_SOURCE_IDENTITY_MISMATCH")
    if completed.stdout:
        raise ValueError("A0X_VERTICAL_P0_V2_CHECKOUT_DIRTY")


def _read_regular_at(parent_fd: int, name: str, maximum: int, code: str) -> bytes:
    """Read one descriptor-relative, regular, independent file exactly once."""
    try:
        first = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(first.st_mode)
            or first.st_nlink != 1
            or not 0 < first.st_size <= maximum
        ):
            raise ValueError(code)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino, opened.st_size)
                != (first.st_dev, first.st_ino, first.st_size)
            ):
                raise ValueError(code)
            chunks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            final = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except ValueError:
        raise
    except (AttributeError, OSError) as error:
        raise ValueError(code) from error
    if (
        len(raw) != first.st_size
        or final.st_nlink != 1
        or (final.st_dev, final.st_ino, final.st_size)
        != (first.st_dev, first.st_ino, first.st_size)
    ):
        raise ValueError(code)
    return raw


def _safe_relative(value: str, code: str) -> tuple[str, ...]:
    parts = tuple(value.split("/")) if isinstance(value, str) else ()
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(code)
    return parts


def _read_regular_relative(root: Path, relative: str, maximum: int, code: str) -> bytes:
    """Open every caller-controlled path component without following links."""
    parts = _safe_relative(relative, code)
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            descriptors.append(current)
        return _read_regular_at(current, parts[-1], maximum, code)
    except ValueError:
        raise
    except (AttributeError, OSError) as error:
        raise ValueError(code) from error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _reserve_attempt_claim(root: Path, arguments: argparse.Namespace, bootstrap: dict[str, int | str]) -> str:
    """Create the irreversible P0 claim through descriptor-relative O_EXCL."""
    relative = _claim_relative(arguments.expected_head, arguments.expected_tree, arguments.attempt_id)
    parts = _safe_relative(relative, "A0X_VERTICAL_P0_V2_ATTEMPT_CLAIM_FAILED")
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(current)
        for part in parts[:-1]:
            try:
                os.mkdir(part, 0o700, dir_fd=current)
            except FileExistsError:
                pass
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            descriptors.append(current)
        parent = os.fstat(current)
        payload = {
            "artifact_class": "a0x-vertical-p0-attempt-claim-v2",
            "profile": PROFILE,
            "source": {"head": arguments.expected_head, "tree": arguments.expected_tree},
            "pair": {
                "leg": "a0", "model_key": "smollm2_360m",
                "model_revision": "f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
            },
            "authorization_id": arguments.authorization_id,
            "attempt_id": arguments.attempt_id,
            "authorization_document_sha256": arguments.authorization_document_sha256,
            "python_sha256": arguments.expected_python_sha256,
            "ledger_sha256": arguments.expected_ledger_sha256,
            "bootstrap": bootstrap,
            "preexec_sha256": arguments.expected_preexec_sha256,
            "claim_parent": {"device": parent.st_dev, "inode": parent.st_ino},
            "retry_permitted": False,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        created = False
        try:
            descriptor = os.open(parts[-1], flags, 0o600, dir_fd=current)
            created = True
        except FileExistsError as error:
            raise ValueError("A0X_VERTICAL_P0_V2_ATTEMPT_ALREADY_CONSUMED") from error
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(current)
        except OSError as error:
            if created:
                raise _ConsumedClaimFailure(relative) from error
            raise ValueError("A0X_VERTICAL_P0_V2_ATTEMPT_CLAIM_FAILED") from error
    except ValueError:
        raise
    except (AttributeError, OSError) as error:
        raise ValueError("A0X_VERTICAL_P0_V2_ATTEMPT_CLAIM_FAILED") from error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
    return relative


def _write_terminal_receipt(
    root: Path, claim_relative: str, terminal_class: str, *, arguments: argparse.Namespace,
    error_code: str | None = None, verification: dict[str, object] | None = None,
) -> None:
    """Seal a terminal P0 outcome beside its irreversible claim exactly once."""
    parts = _safe_relative(claim_relative, "A0X_VERTICAL_P0_V2_TERMINAL_RECEIPT_FAILED")
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            descriptors.append(current)
        try:
            claim_raw = _read_regular_at(current, parts[-1], _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_TERMINAL_RECEIPT_FAILED")
            claim_sha256: str | None = hashlib.sha256(claim_raw).hexdigest()
        except ValueError:
            claim_sha256 = None
        frontiers = {
            "claimed_preload_failure": "preload",
            "claimed_prepublication_failure": "prepublication",
            "claimed_publication_failure": "post_publication",
            "target_free_p0_completed": "target_free_p0_completed",
        }
        if terminal_class not in frontiers:
            raise ValueError("A0X_VERTICAL_P0_V2_TERMINAL_RECEIPT_FAILED")
        payload: dict[str, object] = {
            "artifact_class": "a0x-vertical-p0-terminal-receipt-v2",
            "claim_path": claim_relative,
            "claim_sha256": claim_sha256,
            "terminal_class": terminal_class,
            "retry_permitted": False,
            "recovery_required": terminal_class != "target_free_p0_completed",
            "frontier": frontiers[terminal_class],
            "source": {"head": arguments.expected_head, "tree": arguments.expected_tree},
            "pair": {
                "leg": "a0", "model_key": "smollm2_360m",
                "model_revision": "f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
            },
            "authorization": {
                "id": arguments.authorization_id,
                "sha256": arguments.authorization_document_sha256,
            },
            "input_identities": {
                "python_sha256": arguments.expected_python_sha256,
                "ledger_sha256": arguments.expected_ledger_sha256,
                "bootstrap_sha256": arguments.expected_bootstrap_sha256,
                "preexec_sha256": arguments.expected_preexec_sha256,
            },
        }
        if error_code is not None:
            payload["error_code"] = error_code
        if verification is not None:
            payload["verification"] = verification
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        descriptor = os.open(
            "terminal-receipt.json",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=current,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(current)
        except OSError as error:
            raise ValueError("A0X_VERTICAL_P0_V2_TERMINAL_RECEIPT_FAILED") from error
    except (AttributeError, FileExistsError, OSError) as error:
        raise ValueError("A0X_VERTICAL_P0_V2_TERMINAL_RECEIPT_FAILED") from error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _require_python_identity(path_text: str, expected_sha256: str) -> None:
    """Bind this isolated process to one independently-owned Python binary."""
    if _DIGEST.fullmatch(expected_sha256) is None:
        raise ValueError("A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH")
    try:
        expected = Path(path_text)
        expected_metadata = expected.lstat()
        runtime = Path(sys.executable)
        runtime_metadata = runtime.lstat()
        if (
            not stat.S_ISREG(expected_metadata.st_mode)
            or expected_metadata.st_nlink != 1
            or not stat.S_ISREG(runtime_metadata.st_mode)
            or runtime_metadata.st_nlink != 1
            or (expected_metadata.st_dev, expected_metadata.st_ino)
            != (runtime_metadata.st_dev, runtime_metadata.st_ino)
            or not 0 < expected_metadata.st_size <= _MAX_PYTHON_BYTES
            or not sys.flags.isolated
            or not sys.flags.ignore_environment
            or not sys.flags.no_site
            or not sys.flags.no_user_site
            or not sys.flags.dont_write_bytecode
        ):
            raise ValueError("A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH")
        parent = os.open(expected.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            raw = _read_regular_at(parent, expected.name, _MAX_PYTHON_BYTES, "A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH")
        finally:
            os.close(parent)
        final_metadata = expected.lstat()
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        if isinstance(error, ValueError):
            raise
        raise ValueError("A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH") from error
    if (
        (expected_metadata.st_dev, expected_metadata.st_ino, expected_metadata.st_size)
        != (final_metadata.st_dev, final_metadata.st_ino, final_metadata.st_size)
        or hashlib.sha256(raw).hexdigest() != expected_sha256
    ):
        raise ValueError("A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH")


def _require_ledger(root: Path, expected_sha256: str) -> None:
    if _DIGEST.fullmatch(expected_sha256) is None:
        raise ValueError("A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")
    _require_historical_ledger(root, expected_sha256)


def _current_ledger_path(head: str, tree: str) -> str:
    if not _REVISION.fullmatch(head) or not _REVISION.fullmatch(tree):
        raise ValueError("A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")
    return f".a0x-runtime/p0-input-ledger/v1/{head}/{tree}/input-ledger.json"


def _current_ledger_bytes(root: Path, head: str, tree: str) -> bytes:
    """Declare today's source closure without rewriting the historical ledger."""
    code = "A0X_VERTICAL_P0_V2_LEDGER_MISMATCH"
    document = _read_regular_relative(root, LEDGER_DOCUMENT_RELATIVE, _MAX_BOUND_FILE_BYTES, code).decode("utf-8")
    block = document.split("## Raw P0 package-input ledger", 1)[1].split("```text\n", 1)[1].split("\n```", 1)[0]
    paths = set()
    for line in block.splitlines():
        match = _LEDGER_LINE.fullmatch(line)
        if match is None:
            raise ValueError(code)
        paths.add(match[3])
    if len(paths) != LEDGER_COUNT:
        raise ValueError(code)
    inventory_path = "experiments/a0x-six-model/a0/implementation.json"
    inventory_raw = _read_regular_relative(root, inventory_path, _MAX_BOUND_FILE_BYTES, code)
    inventory = json.loads(inventory_raw)
    paths.update(item["path"] for item in inventory["implementation_files"])
    paths.update({inventory_path, LEDGER_DOCUMENT_RELATIVE, "src/latent_triz/__init__.py",
        "experiments/a0x-six-model/model-registry.json", "experiments/a0x-six-model/material-execution-contract.json",
        "experiments/a0x-six-model/protected-a0-tree.json", "experiments/a0x-six-model/a0-selection-manifest.json",
        "experiments/a0-automated-weak-proxy/protocol.json", "experiments/a0-automated-weak-proxy/implementation.json"})
    registry = json.loads(_read_regular_relative(root, "experiments/a0x-six-model/model-registry.json", _MAX_BOUND_FILE_BYTES, code))
    paths.update("experiments/a0x-six-model/" + item for item in registry["cards"])
    if len(paths) > 512:
        raise ValueError(code)
    # Admit the complete set lexically before probing any member. No corpus,
    # target, private mapping, runtime, weights or historical result is a member.
    for relative in paths:
        _safe_relative(relative, code)
        first = Path(relative).parts[0]
        if first not in {"src", "tests", "schemas", "scripts", "docs", ".github", "experiments", "Makefile", "requirements-schema.in", "requirements-schema.lock", "requirements-lab01.lock"}:
            raise ValueError(code)
        if first == "experiments" and not (relative.startswith("experiments/a0x-six-model/") or relative in {
            "experiments/a0-automated-weak-proxy/protocol.json", "experiments/a0-automated-weak-proxy/implementation.json"}):
            raise ValueError(code)
        if relative.startswith("experiments/a0x-six-model/") and ("authorization" in relative or "approval-dossiers" in relative):
            raise ValueError(code)
    entries = []
    for relative in sorted(paths):
        raw = _read_regular_relative(root, relative, _MAX_BOUND_FILE_BYTES, code)
        entries.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    # A stale implementation inventory may not be papered over by a new ledger.
    observed = {entry["path"]: entry for entry in entries}
    if any(observed.get(item["path"]) != item for item in inventory["implementation_files"]):
        raise ValueError(code)
    payload = {"artifact_class": "a0x-current-p0-input-ledger", "profile": "current-source-inventory-v1",
        "source": {"head": head, "tree": tree}, "inventory_raw_sha256": hashlib.sha256(inventory_raw).hexdigest(), "entries": entries}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _require_current_ledger(root: Path, expected_sha256: str, head: str, tree: str) -> None:
    raw = _read_regular_relative(root, _current_ledger_path(head, tree), _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")
    if not _DIGEST.fullmatch(expected_sha256) or hashlib.sha256(raw).hexdigest() != expected_sha256 or raw != _current_ledger_bytes(root, head, tree):
        raise ValueError("A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")


def prepare_current_ledger(root: Path, head: str, tree: str) -> dict[str, object]:
    """One bounded source-inventory declaration, published without replacement."""
    _require_source_identity(root, head, tree)
    _require_clean_checkout(root)
    raw = _current_ledger_bytes(root, head, tree)
    relative = _current_ledger_path(head, tree)
    parts = Path(relative).parts
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    stage = ".input-ledger-" + secrets.token_hex(12)
    created = False
    identity = None
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, 0o700, dir_fd=directory)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
        created = True
        with os.fdopen(fd, "wb") as stream:
            info = os.fstat(stream.fileno())
            identity = (info.st_dev, info.st_ino)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _require_source_identity(root, head, tree)
        _require_clean_checkout(root)
        source = root / "src"
        sys.path.insert(0, str(source))
        from latent_triz.a0x_vertical_slice import _darwin_publish_exclusive_at
        _darwin_publish_exclusive_at(directory, stage, parts[-1])
        created = False
        os.fsync(directory)
    finally:
        if created:
            try:
                info = os.stat(stage, dir_fd=directory, follow_symlinks=False)
                if (info.st_dev, info.st_ino) == identity:
                    os.unlink(stage, dir_fd=directory)
            except FileNotFoundError:
                pass
        os.close(directory)
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "profile": "current-source-inventory-v1"}


def _require_historical_ledger(root: Path, expected_sha256: str) -> None:
    try:
        document = _read_regular_relative(root, LEDGER_DOCUMENT_RELATIVE, _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")
        text = document.decode("utf-8", "strict")
        block = text.split("## Raw P0 package-input ledger", 1)[1].split("```text\n", 1)[1].split("\n```", 1)[0]
        parsed: list[tuple[str, int, str]] = []
        for line in block.splitlines():
            match = _LEDGER_LINE.fullmatch(line)
            if match is None:
                raise ValueError("malformed ledger")
            digest, size, relative = match.groups()
            _safe_relative(relative, "A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")
            parsed.append((digest, int(size), relative))
        if len(parsed) != LEDGER_COUNT or [entry[2] for entry in parsed] != sorted(entry[2] for entry in parsed):
            raise ValueError("invalid ledger")
        lines: list[str] = []
        for declared_digest, declared_size, relative in parsed:
            raw = _read_regular_relative(root, relative, _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")
            digest = hashlib.sha256(raw).hexdigest()
            if digest != declared_digest or len(raw) != declared_size:
                raise ValueError("ledger drift")
            lines.append(f"{digest} {len(raw)} {relative}")
    except (IndexError, UnicodeDecodeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error) == "A0X_VERTICAL_P0_V2_LEDGER_MISMATCH":
            raise
        raise ValueError("A0X_VERTICAL_P0_V2_LEDGER_MISMATCH") from error
    if hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest() != expected_sha256:
        raise ValueError("A0X_VERTICAL_P0_V2_LEDGER_MISMATCH")


def _require_bootstrap_identity(root: Path, arguments: argparse.Namespace) -> dict[str, int | str]:
    if _DIGEST.fullmatch(arguments.expected_bootstrap_sha256) is None or _DIGEST.fullmatch(arguments.expected_preexec_sha256) is None:
        raise ValueError("A0X_VERTICAL_P0_V2_BOOTSTRAP_IDENTITY_MISMATCH")
    try:
        script = root / SCRIPT_RELATIVE
        expected = script.lstat()
        actual = Path(__file__).lstat()
        if (
            not stat.S_ISREG(expected.st_mode)
            or expected.st_nlink != 1
            or (expected.st_dev, expected.st_ino, expected.st_size)
            != (actual.st_dev, actual.st_ino, actual.st_size)
        ):
            raise ValueError("identity")
        raw = _read_regular_relative(root, SCRIPT_RELATIVE, _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_BOOTSTRAP_IDENTITY_MISMATCH")
        values = tuple(int(value) for value in (
            arguments.preexec_bootstrap_device,
            arguments.preexec_bootstrap_inode,
            arguments.preexec_bootstrap_bytes,
        ))
    except (OSError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error) == "A0X_VERTICAL_P0_V2_BOOTSTRAP_IDENTITY_MISMATCH":
            raise
        raise ValueError("A0X_VERTICAL_P0_V2_BOOTSTRAP_IDENTITY_MISMATCH") from error
    if (
        hashlib.sha256(raw).hexdigest() != arguments.expected_bootstrap_sha256
        or values != (expected.st_dev, expected.st_ino, expected.st_size)
    ):
        raise ValueError("A0X_VERTICAL_P0_V2_BOOTSTRAP_IDENTITY_MISMATCH")
    return {"path": SCRIPT_RELATIVE, "sha256": arguments.expected_bootstrap_sha256, "device": values[0], "inode": values[1], "bytes": values[2]}


def _require_preexec_launcher(root: Path, arguments: argparse.Namespace) -> dict[str, str]:
    if _DIGEST.fullmatch(arguments.expected_preexec_sha256) is None:
        raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
    try:
        expected = root / PREEXEC_RELATIVE
        supplied = Path(arguments.preexec_launcher)
        if supplied.resolve(strict=True) != expected.resolve(strict=True):
            raise ValueError("path mismatch")
        raw = _read_regular_relative(
            root, PREEXEC_RELATIVE, _MAX_BOUND_FILE_BYTES,
            "A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH",
        )
    except (OSError, RuntimeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error) == "A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH":
            raise
        raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH") from error
    if hashlib.sha256(raw).hexdigest() != arguments.expected_preexec_sha256:
        raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
    return {"path": PREEXEC_RELATIVE, "sha256": arguments.expected_preexec_sha256}


def _require_preexec_handoff(root: Path, arguments: argparse.Namespace, bootstrap: dict[str, int | str]) -> None:
    """Reject direct target execution: only the byte-verifying launcher may enter P0."""
    marker = globals().get(_PREEXEC_HANDOFF)
    expected = {
        "launcher_path": str(root / PREEXEC_RELATIVE),
        "launcher_sha256": arguments.expected_preexec_sha256,
        "target_path": str(root / SCRIPT_RELATIVE),
        "target_sha256": arguments.expected_bootstrap_sha256,
        "target_device": bootstrap["device"],
        "target_inode": bootstrap["inode"],
        "target_bytes": bootstrap["bytes"],
    }
    if not isinstance(marker, dict) or marker != expected:
        raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_HANDOFF_MISMATCH")


def _publication_frontier(root: Path, head: str, tree: str) -> str:
    """Classify failure by durable descriptor-relative publication evidence only."""
    relative = _package_relative(head, tree)
    parts = _safe_relative(relative, "A0X_VERTICAL_P0_V2_PUBLICATION_FRONTIER_FAILED")
    descriptors: list[int] = []
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(current)
        for part in parts:
            current = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            descriptors.append(current)
        package = os.open("package", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
        try:
            _read_regular_at(current, "p0-commitment.json", _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_PUBLICATION_FRONTIER_FAILED")
            _read_regular_at(package, "protocol.json", _MAX_BOUND_FILE_BYTES, "A0X_VERTICAL_P0_V2_PUBLICATION_FRONTIER_FAILED")
        finally:
            os.close(package)
    except (AttributeError, OSError, ValueError):
        return "claimed_prepublication_failure"
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
    return "claimed_publication_failure"


def _require_output_absent(root: Path, head: str, tree: str) -> None:
    if os.path.lexists(root / _package_relative(head, tree)):
        raise ValueError("A0X_VERTICAL_P0_V2_OUTPUT_EXISTS")


def _reject_repository_bytecode(root: Path) -> None:
    """Keep ignored pyc/native artifacts outside the trusted source import path."""
    source = root / "src"
    try:
        for directory, names, files in os.walk(source, topdown=True, followlinks=False):
            for name in names:
                metadata = (Path(directory) / name).lstat()
                if name == "__pycache__" or stat.S_ISLNK(metadata.st_mode):
                    raise ValueError("A0X_VERTICAL_P0_V2_BYTECODE_PRESENT")
            for name in files:
                if name.endswith((".pyc", ".pyo", ".so", ".dylib")):
                    raise ValueError("A0X_VERTICAL_P0_V2_BYTECODE_PRESENT")
    except ValueError:
        raise
    except OSError as error:
        raise ValueError("A0X_VERTICAL_P0_V2_BYTECODE_PRESENT") from error


def _require_authorization_identity(
    root: Path, path_text: str, expected_sha256: str, *, head: str, tree: str,
    authorization_id: str, attempt_id: str, bootstrap: dict[str, int | str], preexec: dict[str, str], arguments: argparse.Namespace,
) -> None:
    if _DIGEST.fullmatch(expected_sha256) is None:
        raise ValueError("A0X_VERTICAL_P0_V2_AUTHORIZATION_IDENTITY_MISMATCH")
    relative = (
        f".a0x-runtime/authorizations/p0/v2/{head}/{tree}/a0/smollm2_360m/"
        f"{attempt_id}.json"
    )
    try:
        expected_path = root / relative
        supplied_path = Path(path_text)
        supplied_metadata = supplied_path.lstat()
        if (
            not stat.S_ISREG(supplied_metadata.st_mode)
            or supplied_metadata.st_nlink != 1
            or supplied_path.resolve(strict=True) != expected_path.resolve(strict=True)
        ):
            raise ValueError("A0X_VERTICAL_P0_V2_AUTHORIZATION_IDENTITY_MISMATCH")
        raw = _read_regular_relative(
            root, relative, _MAX_BOUND_FILE_BYTES,
            "A0X_VERTICAL_P0_V2_AUTHORIZATION_IDENTITY_MISMATCH",
        )
    except (OSError, RuntimeError, TypeError) as error:
        raise ValueError("A0X_VERTICAL_P0_V2_AUTHORIZATION_IDENTITY_MISMATCH") from error
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("A0X_VERTICAL_P0_V2_AUTHORIZATION_IDENTITY_MISMATCH")
    try:
        value = json.loads(raw.decode("utf-8"))
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("A0X_VERTICAL_P0_V2_AUTHORIZATION_BINDING_MISMATCH") from error
    expected = {
        "artifact_class": "a0x-vertical-p0-authorization",
        "authorization_profile": "a0x-vertical-p0-authorization-v2",
        "source": {"head": head, "tree": tree},
        "pair": {
            "leg": "a0", "model_key": "smollm2_360m",
            "model_revision": "f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
        },
        "generator_profile": "a0x-vertical-slice-v2",
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "operator": {
            "profile": PROFILE,
            "python": {
                "path": arguments.expected_python,
                "sha256": arguments.expected_python_sha256,
            },
            "ledger": ({"sha256": arguments.expected_ledger_sha256} if arguments.ledger_profile == "historical-v1" else {
                "profile": "current-source-inventory-v1", "path": _current_ledger_path(head, tree), "sha256": arguments.expected_ledger_sha256}),
            "bootstrap": bootstrap,
            "preexec": preexec,
        },
        "output": {
            "members": [
                "protocol.json", "implementation.json", "freeze.json",
                "approval-dossier.json", "slice-manifest.json",
            ],
            "commitment": "p0-commitment.json",
        },
    }
    if raw != canonical or value != expected:
        raise ValueError("A0X_VERTICAL_P0_V2_AUTHORIZATION_BINDING_MISMATCH")


def _run(arguments: argparse.Namespace) -> dict[str, object]:
    root = Path(arguments.repository_root).resolve(strict=True)
    source = root / "src"
    if not source.is_dir():
        raise ValueError("A0X_VERTICAL_P0_V2_INVALID_REPOSITORY")
    _require_source_identity(root, arguments.expected_head, arguments.expected_tree)
    _require_clean_checkout(root)
    _require_python_identity(arguments.expected_python, arguments.expected_python_sha256)
    if arguments.ledger_profile == "historical-v1":
        _require_ledger(root, arguments.expected_ledger_sha256)
    else:
        _require_current_ledger(root, arguments.expected_ledger_sha256, arguments.expected_head, arguments.expected_tree)
    bootstrap = _require_bootstrap_identity(root, arguments)
    preexec = _require_preexec_launcher(root, arguments)
    _require_preexec_handoff(root, arguments, bootstrap)
    _require_authorization_identity(
        root, arguments.authorization_document, arguments.authorization_document_sha256,
        head=arguments.expected_head, tree=arguments.expected_tree,
        authorization_id=arguments.authorization_id, attempt_id=arguments.attempt_id,
        bootstrap=bootstrap, preexec=preexec, arguments=arguments,
    )
    _require_output_absent(root, arguments.expected_head, arguments.expected_tree)
    _reject_repository_bytecode(root)
    try:
        claim_relative = _reserve_attempt_claim(root, arguments, bootstrap)
    except _ConsumedClaimFailure as error:
        _write_terminal_receipt(
            root, error.claim_relative, "claimed_preload_failure", arguments=arguments,
            error_code="A0X_VERTICAL_P0_V2_ATTEMPT_CLAIM_FAILED",
        )
        raise ValueError("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE") from error
    try:
        sys.path.insert(0, str(source))
        from latent_triz.a0x_contract import Leg
        from latent_triz.a0x_vertical_slice import (
            VerticalRuntimePackageRequest,
            generate_vertical_runtime_package,
            load_vertical_runtime_package,
        )
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as error:
        _write_terminal_receipt(
            root, claim_relative, "claimed_preload_failure", arguments=arguments,
            error_code=str(error),
        )
        raise ValueError("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE") from error
    output_root = _package_relative(arguments.expected_head, arguments.expected_tree)
    try:
        request = VerticalRuntimePackageRequest(
            qualified_source_head=arguments.expected_head,
            qualified_source_tree=arguments.expected_tree,
            leg=Leg.A0,
            model_key="smollm2_360m",
            output_root=output_root,
            authorization_id=arguments.authorization_id,
            attempt_id=arguments.attempt_id,
        )
        result = generate_vertical_runtime_package(root, request)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        _write_terminal_receipt(
            root, claim_relative, _publication_frontier(root, arguments.expected_head, arguments.expected_tree), arguments=arguments,
            error_code=str(error),
        )
        raise ValueError("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE") from error
    try:
        reloaded = load_vertical_runtime_package(root, result)
        if not isinstance(reloaded, dict) or reloaded.get("binding") != result:
            raise ValueError("reloaded P0 binding differs")
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as error:
        _write_terminal_receipt(
            root, claim_relative, "claimed_publication_failure", arguments=arguments,
            error_code=str(error),
        )
        raise ValueError("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE") from error
    binding = _json_shape(result) if dataclasses.is_dataclass(result) else None
    commitment_sha256 = reloaded.get("package_commitment_sha256") if isinstance(reloaded, dict) else None
    dossier_sha256 = reloaded.get("dossier_sha256") if isinstance(reloaded, dict) else None
    if (
        not isinstance(binding, dict)
        or not isinstance(commitment_sha256, str) or _DIGEST.fullmatch(commitment_sha256) is None
        or not isinstance(dossier_sha256, str) or _DIGEST.fullmatch(dossier_sha256) is None
        or binding.get("package_commitment_sha256") != commitment_sha256
        or binding.get("dossier_sha256") != dossier_sha256
    ):
        _write_terminal_receipt(
            root, claim_relative, "claimed_publication_failure", arguments=arguments,
            error_code="A0X_VERTICAL_P0_V2_COMPLETION_BINDING_MISMATCH",
        )
        raise ValueError("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE")
    verification = {
        "binding": binding,
        "package_commitment_sha256": commitment_sha256,
        "dossier_sha256": dossier_sha256,
    }
    _write_terminal_receipt(
        root, claim_relative, "target_free_p0_completed", arguments=arguments,
        verification=verification,
    )
    if dataclasses.is_dataclass(result):
        return binding
    if isinstance(result, dict):
        return result
    raise ValueError("A0X_VERTICAL_P0_V2_INVALID_RESULT")


def main(argv: list[str] | None = None) -> int:
    selected = list(sys.argv[1:] if argv is None else argv)
    if selected[:1] == ["--prepare-current-ledger"]:
        parser = argparse.ArgumentParser(description="Prepare one target-free current P0 input ledger")
        parser.add_argument("--repository-root", required=True)
        parser.add_argument("--expected-head", required=True)
        parser.add_argument("--expected-tree", required=True)
        arguments = parser.parse_args(selected[1:])
        try:
            result = prepare_current_ledger(Path(arguments.repository_root).resolve(strict=True), arguments.expected_head, arguments.expected_tree)
        except (OSError, ValueError, RuntimeError) as error:
            print(str(error), file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    arguments = _parser().parse_args(argv)
    try:
        receipt = _run(arguments)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI boundary
    raise SystemExit(main())
