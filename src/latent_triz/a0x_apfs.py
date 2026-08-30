"""Fail-closed APFS clonefile boundary for A0X runtime preparation."""
from __future__ import annotations

import ctypes
import hashlib
import os
import stat
import sys
from pathlib import Path
from typing import Callable


class A0XClonefileError(RuntimeError):
    """An APFS copy-on-write materialization could not be proven exact."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bind_to_trusted_root(path: Path, root: Path, *, include_leaf: bool) -> None:
    """Reject traversal and symlinks in every caller-controlled component."""
    path_absolute = path.absolute()
    root_absolute = root.absolute()
    if not path.is_absolute() or not root.is_absolute():
        raise A0XClonefileError("clonefile paths and trusted roots must be absolute")
    if root_absolute.is_symlink() or not root_absolute.is_dir():
        raise A0XClonefileError("clonefile trusted root is unavailable")
    try:
        relative = path_absolute.relative_to(root_absolute)
    except ValueError as error:
        raise A0XClonefileError("clonefile path escapes its trusted root") from error
    current = root_absolute
    parts = relative.parts if include_leaf else relative.parts[:-1]
    for part in parts:
        current = current / part
        if os.path.lexists(current) and current.is_symlink():
            raise A0XClonefileError("clonefile path contains a symlink")
    resolved_root = root_absolute.resolve(strict=True)
    existing = path_absolute if include_leaf else path_absolute.parent
    try:
        resolved_existing = existing.resolve(strict=True)
    except OSError as error:
        raise A0XClonefileError("clonefile path is unavailable") from error
    if not resolved_existing.is_relative_to(resolved_root):
        raise A0XClonefileError("clonefile path escapes its trusted root")


def _independent_regular(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise A0XClonefileError(f"{label} is unavailable") from error
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_nlink != 1:
        raise A0XClonefileError(f"{label} is not an independent regular file")
    return metadata


def _darwin_clonefile(source: Path, destination: Path) -> None:
    """Invoke Darwin clonefile(2) without a shell or full-copy fallback."""
    try:
        library = ctypes.CDLL(None, use_errno=True)
        clonefile = library.clonefile
    except (AttributeError, OSError) as error:
        raise A0XClonefileError("Darwin clonefile is unavailable") from error
    clonefile.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)
    clonefile.restype = ctypes.c_int
    if clonefile(os.fsencode(source), os.fsencode(destination), 0) != 0:
        error_number = ctypes.get_errno()
        raise A0XClonefileError("Darwin clonefile refused") from OSError(error_number, os.strerror(error_number))


def _remove_created_file(path: Path, created: os.stat_result | None) -> None:
    """Remove only the same regular inode created by this operation."""
    if created is None or not stat.S_ISREG(created.st_mode):
        return
    try:
        current = path.lstat()
        if (
            stat.S_ISREG(current.st_mode)
            and not path.is_symlink()
            and current.st_dev == created.st_dev
            and current.st_ino == created.st_ino
        ):
            path.unlink()
    except OSError:
        return


def clone_regular_file(
    source: Path,
    destination: Path,
    *,
    source_root: Path,
    destination_root: Path,
    platform: str | None = None,
    clone_call: Callable[[Path, Path], None] | None = None,
) -> dict[str, object]:
    """Clone one file and prove exact bytes plus independent regular-file state.

    There is deliberately no ordinary-copy fallback. Callers must prepare the
    destination parent and must treat any refusal as terminal for that attempt.
    """
    source_path = Path(source)
    destination_path = Path(destination)
    if (sys.platform if platform is None else platform) != "darwin":
        raise A0XClonefileError("APFS clonefile materialization requires macOS")
    _bind_to_trusted_root(source_path, Path(source_root), include_leaf=True)
    _bind_to_trusted_root(destination_path, Path(destination_root), include_leaf=False)
    source_metadata = _independent_regular(source_path, "clonefile source")
    try:
        source_resolved = source_path.resolve(strict=True)
    except OSError as error:
        raise A0XClonefileError("clonefile source is unavailable") from error
    destination_parent = destination_path.parent
    if not destination_parent.is_dir() or destination_parent.is_symlink():
        raise A0XClonefileError("clonefile destination parent is not an existing regular directory")
    if os.path.lexists(destination_path):
        raise A0XClonefileError("clonefile destination is already occupied")

    source_digest = _sha256(source_resolved)
    source_size = source_metadata.st_size
    operation = _darwin_clonefile if clone_call is None else clone_call
    created: os.stat_result | None = None
    try:
        operation(source_resolved, destination_path)
        created = destination_path.lstat()
    except A0XClonefileError:
        if os.path.lexists(destination_path):
            try:
                created = destination_path.lstat()
            except OSError:
                created = None
        _remove_created_file(destination_path, created)
        raise
    except OSError as error:
        if os.path.lexists(destination_path):
            try:
                created = destination_path.lstat()
            except OSError:
                created = None
        _remove_created_file(destination_path, created)
        raise A0XClonefileError("Darwin clonefile refused") from error
    try:
        destination_metadata = _independent_regular(destination_path, "clonefile destination")
        current_source = _independent_regular(source_resolved, "clonefile source")
        source_unchanged = (
            current_source.st_dev == source_metadata.st_dev
            and current_source.st_ino == source_metadata.st_ino
            and current_source.st_size == source_metadata.st_size
            and current_source.st_mtime_ns == source_metadata.st_mtime_ns
            and _sha256(source_resolved) == source_digest
        )
        destination_exact = (
            destination_metadata.st_ino != current_source.st_ino
            and destination_metadata.st_size == source_size
            and _sha256(destination_path) == source_digest
        )
        if not source_unchanged or not destination_exact:
            raise A0XClonefileError("clonefile post-operation verification failed")
    except (A0XClonefileError, OSError) as error:
        _remove_created_file(destination_path, created)
        if isinstance(error, A0XClonefileError):
            raise
        raise A0XClonefileError("clonefile post-operation verification failed") from error
    return {
        "operation": "clonefile",
        "sha256": source_digest,
        "size_bytes": source_size,
    }


__all__ = ["A0XClonefileError", "clone_regular_file"]
