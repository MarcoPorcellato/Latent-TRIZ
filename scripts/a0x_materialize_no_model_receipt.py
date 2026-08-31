#!/usr/bin/env python3
"""Materialize the one canonical target-free A0X no-model receipt safely."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import sys
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from latent_triz.a0x_runner import verify_a0x_no_model  # noqa: E402


CANONICAL_OUTPUT = "results/a0x/preexecution/a0x-no-model-verification-receipt.json"


class A0XNoModelReceiptError(ValueError):
    """Raised when the target-free receipt cannot be safely materialized."""


ReceiptBuilder = Callable[[Path], Mapping[str, Any]]


def _canonical_receipt_bytes(value: Mapping[str, Any]) -> bytes:
    """Encode standard finite JSON values in the project's canonical receipt form."""
    def validate(item: Any) -> None:
        if item is None or type(item) in (bool, str, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) in (list, tuple):
            for child in item:
                validate(child)
            return
        if isinstance(item, Mapping):
            for key, child in item.items():
                if type(key) is not str:
                    raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_CHECK_FAILED")
                validate(child)
            return
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_CHECK_FAILED")

    validate(value)
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True)
    parser.add_argument("--replace-existing", action="store_true")
    return parser


def _regular_unlinked(path: Path) -> os.stat_result | None:
    """Return safe output metadata, or reject every extant unsafe object."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID")
    return metadata


def _safe_repository(root_argument: Path) -> Path:
    """Reject a missing, linked, or non-directory caller-controlled repository root."""
    try:
        metadata = root_argument.lstat()
    except OSError as error:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_ROOT_INVALID") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_ROOT_INVALID")
    return root_argument.resolve()


def _canonical_output(root: Path, raw_output: str) -> Path:
    """Accept exactly one repository-relative output path, never an alias."""
    if raw_output != CANONICAL_OUTPUT:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID")
    output = root / CANONICAL_OUTPUT
    if output.relative_to(root).as_posix() != CANONICAL_OUTPUT:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID")
    return output


def _safe_parent(root: Path, output: Path, *, create: bool) -> Path:
    """Verify or create only regular directory ancestors beneath the trusted root."""
    parent = root
    for part in Path(CANONICAL_OUTPUT).parent.parts:
        candidate = parent / part
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            if not create:
                parent = candidate
                continue
            try:
                candidate.mkdir(mode=0o700)
            except FileExistsError:
                pass
            except OSError as error:
                raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID") from error
            try:
                metadata = candidate.lstat()
            except OSError as error:
                raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID") from error
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID")
        parent = candidate
    if parent != output.parent:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID")
    return parent


def _write_atomically(root: Path, output: Path, raw: bytes, *, replace_existing: bool) -> None:
    """Use an exclusive fsynced temporary regular file and one atomic replacement."""
    parent = _safe_parent(root, output, create=True)
    _regular_unlinked(output)
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    directory = os.open(parent, flags)
    temporary_name = f".{output.name}.{uuid.uuid4().hex}.tmp"
    temporary_created = False
    try:
        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            create_flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary_name, create_flags, 0o600, dir_fd=directory)
        temporary_created = True
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_metadata = os.stat(temporary_name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(temporary_metadata.st_mode) or temporary_metadata.st_nlink != 1:
            raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_INVALID")
        existing = _regular_unlinked(output)
        if existing is not None and not replace_existing:
            raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_EXISTS")
        os.replace(temporary_name, output.name, src_dir_fd=directory, dst_dir_fd=directory)
        temporary_created = False
        os.fsync(directory)
    except OSError as error:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_WRITE_FAILED") from error
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=directory)
            except FileNotFoundError:
                pass
        os.close(directory)


def materialize_no_model_receipt(
    root_argument: Path,
    raw_output: str,
    *,
    replace_existing: bool,
    receipt_builder: ReceiptBuilder = verify_a0x_no_model,
) -> bytes:
    """Build before writing, then atomically materialize the canonical receipt only."""
    root = _safe_repository(root_argument)
    output = _canonical_output(root, raw_output)
    _safe_parent(root, output, create=False)
    existing = _regular_unlinked(output)
    if existing is not None and not replace_existing:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_OUTPUT_EXISTS")
    try:
        receipt = receipt_builder(root)
    except Exception as error:
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_CHECK_FAILED") from error
    if not isinstance(receipt, Mapping):
        raise A0XNoModelReceiptError("A0X_NO_MODEL_RECEIPT_CHECK_FAILED")
    raw = _canonical_receipt_bytes(dict(receipt))
    _write_atomically(root, output, raw, replace_existing=replace_existing)
    return raw


def main(
    argv: list[str] | None = None,
    *,
    receipt_builder: ReceiptBuilder = verify_a0x_no_model,
    stderr: TextIO | None = None,
) -> int:
    args = _parser().parse_args(argv)
    stream = sys.stderr if stderr is None else stderr
    try:
        materialize_no_model_receipt(
            args.root,
            args.output,
            replace_existing=args.replace_existing,
            receipt_builder=receipt_builder,
        )
    except A0XNoModelReceiptError as error:
        print(error, file=stream)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
