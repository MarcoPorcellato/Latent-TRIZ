#!/usr/bin/env python3
"""Fail-closed fixed child entrypoint for one A0X material attempt.

No production model adapter is connected here.  This module validates a single
ignored launch descriptor and calls an injected executor only after static
identity, environment, and runtime-input checks pass.  Thus import, help, and
rejected descriptors cannot load a model or read a protected target.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_contract import (  # noqa: E402
    EXECUTION_AUTHORIZATION_PROFILE,
    A0XContractError,
    PairBinding,
    canonical_commitment,
    strict_json_object,
)
from latent_triz.a0x_material_contract import (  # noqa: E402
    A0XGuardLaunch,
    CLEANUP_MARGIN_SECONDS,
    DESCRIPTOR_PROFILE,
    INTERNAL_BUDGET_SECONDS,
    OUTER_TIMEOUT_SECONDS,
    authorization_reference,
    material_contract_binding,
    validate_qualification_evidence,
)
from latent_triz.a0x_runtime_readiness import (  # noqa: E402
    A0XRuntimeReadinessError,
    runtime_readiness_path,
    validate_runtime_readiness,
)
from latent_triz.validator import validate  # noqa: E402


_REVISION = re.compile(r"^[a-f0-9]{40}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_ENVIRONMENT = (
    "HF_HUB_OFFLINE=1", "TRANSFORMERS_OFFLINE=1", "HF_DATASETS_OFFLINE=1",
    "TOKENIZERS_PARALLELISM=false", "PYTHONNOUSERSITE=1",
)
_EXECUTION = {
    "network": "offline", "generation": "forbidden", "trust_remote_code": False,
    "device": "cpu", "dtype": "float32", "outer_timeout_seconds": OUTER_TIMEOUT_SECONDS,
    "internal_budget_seconds": INTERNAL_BUDGET_SECONDS, "cleanup_margin_seconds": CLEANUP_MARGIN_SECONDS,
}
_TERMINAL_STATUSES = frozenset({"positive", "null", "non_interpretable", "incompatible", "failed"})
_GIT_REF = re.compile(r"^refs/heads/[A-Za-z0-9][A-Za-z0-9._/-]*$")
_GIT_SMALL_FILE_BYTES = 1_048_576
_GIT_PACKED_REFS_BYTES = 16 * 1_048_576


class A0XMaterialChildError(RuntimeError):
    """A static launch descriptor check did not remain fail-closed."""


def run_child(
    argv: Sequence[str] | None = None,
    *,
    root: Path = ROOT,
    execute_descriptor: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    production_executor_factory: Callable[..., Callable[[Mapping[str, Any]], Mapping[str, Any]] | None] | None = None,
    source_head_probe: Callable[[], str] | None = None,
    environment: Mapping[str, str] | None = None,
    cwd: Path | None = None,
    child_script_path: Path | None = None,
    python_executable: Path | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Validate one fixed descriptor before invoking an injected executor."""
    stream = stdout if stdout is not None else sys.stdout
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv in (["--help"], ["-h"]):
        print("usage: a0x_material_child.py --launch-descriptor <repository-relative-runtime-path>", file=stream)
        return 0
    try:
        descriptor_path = _parse_launch_descriptor_argument(raw_argv)
        descriptor, descriptor_raw = _read_descriptor(Path(root), descriptor_path)
        effective_probe = source_head_probe or (lambda: _default_source_head_probe(Path(root)))
        _validate_descriptor(
            descriptor,
            root=Path(root),
            source_head_probe=effective_probe,
            environment=os.environ if environment is None else environment,
            cwd=Path.cwd() if cwd is None else Path(cwd),
            child_script_path=Path(__file__) if child_script_path is None else Path(child_script_path),
            python_executable=Path(sys.executable) if python_executable is None else Path(python_executable),
            descriptor_raw_sha256=hashlib.sha256(descriptor_raw).hexdigest(),
        )
    except (A0XMaterialChildError, A0XContractError, OSError, ValueError, TypeError):
        _emit_terminal(stream, exit_class="refused")
        return 2
    if execute_descriptor is None:
        factory = production_executor_factory or _production_executor_factory
        try:
            execute_descriptor = factory(root=Path(root), descriptor=descriptor)
        except Exception:
            execute_descriptor = None
    if execute_descriptor is None:
        _emit_terminal(stream, exit_class="runtime_unavailable")
        return 3
    try:
        outcome = execute_descriptor(descriptor)
        status = _terminal_status(outcome)
    except Exception:
        _emit_terminal(stream, exit_class="executor_failed")
        return 4
    _emit_terminal(stream, exit_class="completed", terminal_status=status)
    return 0


def _parse_launch_descriptor_argument(argv: Sequence[str]) -> str:
    if len(argv) != 2 or argv[0] != "--launch-descriptor" or not isinstance(argv[1], str):
        raise A0XMaterialChildError("only one launch descriptor argument is accepted")
    path = Path(argv[1])
    if (
        not argv[1].endswith(".json") or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)
        or len(path.parts) < 5 or path.parts[:2] != (".a0x-runtime", "launches")
    ):
        raise A0XMaterialChildError("launch descriptor path is outside the runtime inlet")
    return path.as_posix()


def _read_descriptor(root: Path, relative_path: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = _repository_file(root, relative_path).read_bytes()
        return strict_json_object(raw), raw
    except (A0XContractError, OSError) as error:
        raise A0XMaterialChildError("launch descriptor bytes are unavailable or non-strict") from error


def _validate_descriptor(
    descriptor: Mapping[str, Any], *, root: Path, source_head_probe: Callable[[], str] | None,
    environment: Mapping[str, str], cwd: Path, child_script_path: Path, python_executable: Path,
    descriptor_raw_sha256: str,
) -> None:
    expected_keys = {
        "descriptor_profile", "source_head", "cwd_kind", "pair_binding", "child_script",
        "python", "runtime_readiness", "environment_template", "authorization_reference",
        "material_contract", "execution",
    }
    if not isinstance(descriptor, Mapping) or set(descriptor) != expected_keys:
        raise A0XMaterialChildError("launch descriptor shape is unsupported")
    if descriptor.get("descriptor_profile") != DESCRIPTOR_PROFILE:
        raise A0XMaterialChildError("launch descriptor profile is unsupported")
    source_head = descriptor.get("source_head")
    if not isinstance(source_head, str) or not _REVISION.fullmatch(source_head) or source_head_probe is None or source_head_probe() != source_head:
        raise A0XMaterialChildError("launch descriptor source head drifted")
    resolved_root = root.resolve(strict=True)
    if descriptor.get("cwd_kind") != "repository_root" or cwd.resolve(strict=True) != resolved_root:
        raise A0XMaterialChildError("launch descriptor cwd is invalid")
    try:
        pair = PairBinding.from_mapping(descriptor["pair_binding"])
    except (A0XContractError, KeyError, TypeError, ValueError) as error:
        raise A0XMaterialChildError("launch descriptor pair binding is invalid") from error
    _validate_child_script(descriptor.get("child_script"), root=resolved_root, current=child_script_path)
    _validate_python(descriptor.get("python"), current=python_executable)
    _validate_environment(descriptor.get("environment_template"), environment)
    runtime_documents = _validate_runtime_documents(descriptor, root=resolved_root, pair=pair)
    _validate_authorization_contract_chain(
        descriptor, pair=pair, runtime_documents=runtime_documents, descriptor_raw_sha256=descriptor_raw_sha256,
    )
    if not isinstance(descriptor.get("execution"), Mapping) or dict(descriptor["execution"]) != _EXECUTION:
        raise A0XMaterialChildError("launch descriptor execution envelope is invalid")


def _validate_child_script(value: Any, *, root: Path, current: Path) -> None:
    if not isinstance(value, Mapping) or set(value) != {"role", "path", "sha256"} or value.get("role") != "child" or value.get("path") != "scripts/a0x_material_child.py":
        raise A0XMaterialChildError("launch descriptor child script is invalid")
    expected = _sha256(value.get("sha256"))
    bound = _repository_file(root, "scripts/a0x_material_child.py")
    if current.resolve(strict=True) != bound.resolve(strict=True) or _file_sha256(bound) != expected:
        raise A0XMaterialChildError("child script bytes drifted")


def _validate_python(value: Any, *, current: Path) -> None:
    if not isinstance(value, Mapping) or set(value) != {"role", "path", "sha256"} or value.get("role") != "python":
        raise A0XMaterialChildError("launch descriptor Python role is invalid")
    path = value.get("path")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise A0XMaterialChildError("launch descriptor Python path is invalid")
    try:
        bound = Path(path).resolve(strict=True)
        actual = current.resolve(strict=True)
    except OSError as error:
        raise A0XMaterialChildError("bound Python executable is unavailable") from error
    if actual != bound or _file_sha256(bound) != _sha256(value.get("sha256")):
        raise A0XMaterialChildError("Python executable bytes drifted")


def _validate_environment(value: Any, environment: Mapping[str, str]) -> None:
    if not isinstance(value, list) or tuple(value) != _ENVIRONMENT:
        raise A0XMaterialChildError("launch descriptor environment template is invalid")
    expected = dict(item.split("=", 1) for item in _ENVIRONMENT)
    if not isinstance(environment, Mapping) or dict(environment) != expected:
        raise A0XMaterialChildError("child environment differs from the frozen template")


def _validate_runtime_documents(
    descriptor: Mapping[str, Any], *, root: Path, pair: PairBinding,
) -> dict[str, bytes]:
    try:
        readiness_binding = descriptor.get("runtime_readiness")
        if (
            not isinstance(readiness_binding, Mapping)
            or set(readiness_binding) != {"role", "path", "sha256"}
            or readiness_binding.get("role") != "readiness"
            or readiness_binding.get("path") != runtime_readiness_path(pair)
        ):
            raise A0XRuntimeReadinessError("runtime readiness binding is invalid")
        readiness_raw = _repository_file(root, str(readiness_binding["path"])).read_bytes()
        if hashlib.sha256(readiness_raw).hexdigest() != _sha256(readiness_binding.get("sha256")):
            raise A0XRuntimeReadinessError("runtime readiness bytes drifted")
        readiness = strict_json_object(readiness_raw)
        validate_runtime_readiness(
            readiness, source_head=str(descriptor["source_head"]), pair=pair,
            python_path=Path(str(descriptor["python"]["path"])),
        )
        authorization_path = authorization_reference(descriptor.get("authorization_reference"), pair)
        contract_path, contract_sha256 = material_contract_binding(descriptor.get("material_contract"))
        authorization_raw = _repository_file(root, authorization_path).read_bytes()
        contract_raw = _repository_file(root, contract_path).read_bytes()
    except (A0XContractError, A0XRuntimeReadinessError, OSError, TypeError, ValueError) as error:
        raise A0XMaterialChildError("launch descriptor runtime documents are invalid") from error
    if hashlib.sha256(contract_raw).hexdigest() != contract_sha256:
        raise A0XMaterialChildError("launch descriptor material contract bytes drifted")
    return {
        "runtime_readiness": readiness_raw,
        "authorization": authorization_raw,
        "material_contract": contract_raw,
    }


def _validate_authorization_contract_chain(
    descriptor: Mapping[str, Any], *, pair: PairBinding, runtime_documents: Mapping[str, bytes],
    descriptor_raw_sha256: str,
) -> None:
    """Validate real authorization/contract semantics, not only their hashes."""
    try:
        authorization_raw = runtime_documents["authorization"]
        contract_raw = runtime_documents["material_contract"]
        authorization = strict_json_object(authorization_raw)
        contract = strict_json_object(contract_raw)
        canonical_commitment(authorization, EXECUTION_AUTHORIZATION_PROFILE)
        schema = json.loads((ROOT / "schemas" / "a0x-material-execution-contract.schema.json").read_text(encoding="utf-8"))
        if validate(contract, schema):
            raise A0XMaterialChildError("material contract schema is invalid")
        if authorization.get("source_head") != descriptor["source_head"]:
            raise A0XMaterialChildError("authorization source head drifted")
        if PairBinding.from_mapping(authorization["pair_binding"]).as_mapping() != pair.as_mapping():
            raise A0XMaterialChildError("authorization pair binding drifted")
        expected_inlet = f".a0x-runtime/authorizations/{pair.leg.value}/{pair.model_key}/{pair.run_id}.json"
        if authorization.get("authorization_inlet_path") != expected_inlet:
            raise A0XMaterialChildError("authorization inlet drifted")
        if authorization.get("material_contract_raw_sha256") != hashlib.sha256(contract_raw).hexdigest():
            raise A0XMaterialChildError("authorization contract hash drifted")
        launch = A0XGuardLaunch.from_mapping(authorization["guard_launch"])
        if launch.launch_descriptor_sha256 != descriptor_raw_sha256:
            raise A0XMaterialChildError("authorization does not bind the current launch descriptor")
        if (
            launch.source_head != descriptor["source_head"]
            or launch.child_script_sha256 != descriptor["child_script"]["sha256"]
            or launch.python_sha256 != descriptor["python"]["sha256"]
        ):
            raise A0XMaterialChildError("authorization launch binding drifted")
        evidence = validate_qualification_evidence(authorization["qualification_evidence"])
        authorization_ccp = authorization["ccp"]
        contract_ccp = contract["ccp"]
        identity_fields = (
            ("source_commit", "source_commit"),
            ("qualified_source_tree", "source_tree"),
            ("sha256", "sha256"),
            ("version", "version"),
        )
        if any(authorization_ccp.get(authorization_field) != contract_ccp.get(contract_field)
               for authorization_field, contract_field in identity_fields):
            raise A0XMaterialChildError("authorization CCP identity drifted")
        if evidence["qualified_source_head"] != descriptor["source_head"]:
            raise A0XMaterialChildError("qualification source head drifted")
    except (A0XContractError, KeyError, OSError, TypeError, ValueError) as error:
        raise A0XMaterialChildError("authorization or material contract is invalid") from error


def _default_source_head_probe(root: Path) -> str:
    """Read exact local HEAD with bounded filesystem reads only.

    Git worktree indirection is supported, but a symbolic reference may point
    only directly below ``refs/heads``.  We do not follow ref chains, symlinks,
    or ambiguous packed-reference entries.
    """
    try:
        metadata = _git_metadata_directory(root)
        head = _read_git_text(metadata / "HEAD", _GIT_SMALL_FILE_BYTES)
        if _REVISION.fullmatch(head):
            return head
        if not head.startswith("ref: "):
            return ""
        reference = head.removeprefix("ref: ")
        if not _safe_head_reference(reference):
            return ""
        loose = metadata / reference
        if loose.exists():
            return _read_git_revision(loose)
        return _packed_ref_revision(metadata / "packed-refs", reference)
    except (OSError, ValueError):
        return ""


def _git_metadata_directory(root: Path) -> Path:
    git = root.resolve(strict=True) / ".git"
    if git.is_symlink():
        raise ValueError("git metadata symlink is unsupported")
    if git.is_dir():
        return git
    content = _read_git_text(git, _GIT_SMALL_FILE_BYTES)
    if not content.startswith("gitdir: "):
        raise ValueError("gitdir indirection is malformed")
    location = content.removeprefix("gitdir: ")
    if not location or "\x00" in location or "\n" in location:
        raise ValueError("gitdir indirection is unsafe")
    target = Path(location)
    if not target.is_absolute():
        target = git.parent / target
    target = target.resolve(strict=True)
    if target.is_symlink() or not target.is_dir():
        raise ValueError("gitdir target is unavailable")
    return target


def _read_git_text(path: Path, maximum_bytes: int) -> str:
    raw = _read_bounded_git_file(path, maximum_bytes)
    if len(raw) > maximum_bytes or b"\x00" in raw:
        raise ValueError("git metadata file exceeds bounded syntax")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("git metadata must be ASCII") from error
    if text.endswith("\n"):
        text = text[:-1]
    if "\n" in text or "\r" in text:
        raise ValueError("git metadata has multiple records")
    return text


def _safe_head_reference(reference: str) -> bool:
    return bool(
        _GIT_REF.fullmatch(reference)
        and all(segment not in {"", ".", ".."} for segment in Path(reference).parts)
    )


def _read_git_revision(path: Path) -> str:
    try:
        revision = _read_git_text(path, _GIT_SMALL_FILE_BYTES)
    except (OSError, ValueError):
        return ""
    return revision if _REVISION.fullmatch(revision) else ""


def _packed_ref_revision(path: Path, reference: str) -> str:
    try:
        raw = _read_bounded_git_file(path, _GIT_PACKED_REFS_BYTES)
        text = raw.decode("ascii")
    except (OSError, UnicodeDecodeError, ValueError):
        return ""
    if len(raw) > _GIT_PACKED_REFS_BYTES or b"\x00" in raw:
        return ""
    matches: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith(("#", "^")):
            continue
        parts = line.split(" ")
        if len(parts) != 2:
            return ""
        revision, packed_reference = parts
        if packed_reference == reference:
            if not _REVISION.fullmatch(revision):
                return ""
            matches.append(revision)
    return matches[0] if len(matches) == 1 else ""


def _read_bounded_git_file(path: Path, maximum_bytes: int) -> bytes:
    """Read one regular Git metadata file without trusting a stale size check."""
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError("git metadata file is unavailable") from error
    if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode) or before.st_size > maximum_bytes:
        raise ValueError("git metadata file is unavailable or oversized")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                or opened.st_size > maximum_bytes
            ):
                raise ValueError("git metadata identity changed before bounded read")
            raw = handle.read(maximum_bytes + 1)
            after = os.fstat(handle.fileno())
    except OSError as error:
        raise ValueError("git metadata file is unavailable") from error
    if (
        len(raw) > maximum_bytes
        or after.st_size > maximum_bytes
        or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
    ):
        raise ValueError("git metadata identity changed during bounded read")
    try:
        observed = path.lstat()
    except OSError as error:
        raise ValueError("git metadata file changed after bounded read") from error
    if (
        not stat.S_ISREG(observed.st_mode)
        or stat.S_ISLNK(observed.st_mode)
        or (observed.st_dev, observed.st_ino) != (before.st_dev, before.st_ino)
        or observed.st_size > maximum_bytes
    ):
        raise ValueError("git metadata identity changed after bounded read")
    return raw


def _production_executor_factory(
    *, root: Path, descriptor: Mapping[str, Any],
) -> Callable[[Mapping[str, Any]], Mapping[str, Any]] | None:
    """Resolve a later adapter only after static launch validation succeeds."""
    try:
        from latent_triz.a0x_production_adapter import build_production_executor
    except ImportError:
        return None
    executor = build_production_executor(root=root, descriptor=descriptor)
    return executor if callable(executor) else None


def _repository_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise A0XMaterialChildError("repository-relative path is unsafe")
    resolved_root = root.resolve(strict=True)
    candidate = resolved_root / path
    current = candidate
    while current != resolved_root:
        if current.is_symlink():
            raise A0XMaterialChildError("runtime path uses a symlink")
        current = current.parent
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise A0XMaterialChildError("bound runtime file is unavailable") from error
    if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
        raise A0XMaterialChildError("bound runtime file is unsafe")
    return resolved


def _sha256(value: Any) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XMaterialChildError("launch descriptor SHA-256 is invalid")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _terminal_status(value: Any) -> str:
    if not isinstance(value, Mapping) or set(value) != {"status"} or value.get("status") not in _TERMINAL_STATUSES:
        raise A0XMaterialChildError("injected executor terminal outcome is invalid")
    return str(value["status"])


def _emit_terminal(stream: TextIO, *, exit_class: str, terminal_status: str | None = None) -> None:
    terminal: dict[str, str] = {"artifact_class": "a0x-material-child-terminal", "exit_class": exit_class}
    if terminal_status is not None:
        terminal["terminal_status"] = terminal_status
    print(json.dumps(terminal, sort_keys=True, separators=(",", ":"), ensure_ascii=False), file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    return run_child(argv)


if __name__ == "__main__":
    raise SystemExit(main())
