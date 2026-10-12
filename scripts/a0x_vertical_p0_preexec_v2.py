#!/usr/bin/env python3
"""Verified-byte launcher for the canonical A0X vertical P0 v2 operator."""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
from pathlib import Path


MAX_BYTES = 64 * 1024 * 1024


def _read_regular(path: Path) -> bytes:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or not 0 < metadata.st_size <= MAX_BYTES:
        raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino, opened.st_size) != (metadata.st_dev, metadata.st_ino, metadata.st_size):
            raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
        chunks: list[bytes] = []
        remaining = MAX_BYTES + 1
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
    if (
        len(raw) != metadata.st_size
        or final.st_nlink != 1
        or (final.st_dev, final.st_ino, final.st_size)
        != (metadata.st_dev, metadata.st_ino, metadata.st_size)
    ):
        raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--target-sha256", required=True)
    parser.add_argument("--self-sha256", required=True)
    parser.add_argument("operator_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    if not arguments.operator_arguments or arguments.operator_arguments[0] != "--":
        print("A0X_VERTICAL_P0_V2_PREEXEC_ARGUMENT_MISMATCH", file=sys.stderr)
        return 2
    try:
        launcher = Path(__file__).resolve(strict=True)
        if hashlib.sha256(_read_regular(launcher)).hexdigest() != arguments.self_sha256:
            raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
        target = Path(arguments.target).resolve(strict=True)
        raw = _read_regular(target)
        if hashlib.sha256(raw).hexdigest() != arguments.target_sha256:
            raise ValueError("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH")
        launcher_metadata = launcher.lstat()
        target_metadata = target.lstat()
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    sys.argv = [str(target), *arguments.operator_arguments[1:], "--preexec-launcher", str(launcher)]
    namespace = {
        "__name__": "__main__", "__file__": str(target), "__package__": None, "__cached__": None,
        "__a0x_vertical_p0_v2_preexec_handoff__": {
            "launcher_path": str(launcher), "launcher_sha256": arguments.self_sha256,
            "target_path": str(target), "target_sha256": arguments.target_sha256,
            "target_device": target_metadata.st_dev, "target_inode": target_metadata.st_ino,
            "target_bytes": target_metadata.st_size,
        },
    }
    exec(compile(raw, str(target), "exec", dont_inherit=True, optimize=0), namespace, namespace)
    return 0


if __name__ == "__main__":  # pragma: no cover - subprocess boundary
    raise SystemExit(main())
