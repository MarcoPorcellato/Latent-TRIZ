#!/usr/bin/env python3
"""Compile self-contained A0X PairBinding schema projections offline."""

from __future__ import annotations

import argparse
import os
from pathlib import PurePosixPath
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from latent_triz.a0x_schema_projection import ProjectionError, compile_pair_projections


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_TEMPORARY_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--only", action="append", default=[])
    arguments = parser.parse_args(argv)
    root_descriptor: int | None = None
    schemas_descriptor: int | None = None
    try:
        outputs = compile_pair_projections(arguments.root)
        selected = _select(outputs, arguments.only)
        basenames = {relative: _output_basename(relative) for relative in selected}
        root_descriptor, schemas_descriptor = _open_projection_directories(arguments.root)
        for basename in basenames.values():
            _target_mode(schemas_descriptor, basename)

        if arguments.write:
            _before_directory_write()
            for relative, payload in selected.items():
                _revalidate_visible_schemas(arguments.root, root_descriptor, schemas_descriptor)
                mode = _target_mode(schemas_descriptor, basenames[relative])
                _atomic_write(schemas_descriptor, basenames[relative], payload, mode)
                _revalidate_visible_schemas(arguments.root, root_descriptor, schemas_descriptor)
            print(f"a0x-compile-pair-schemas: wrote {len(selected)} file(s)")
            return 0

        drift: list[str] = []
        for relative, payload in selected.items():
            try:
                current = _read_target(schemas_descriptor, basenames[relative])
            except FileNotFoundError:
                drift.append(relative)
                continue
            if current != payload:
                drift.append(relative)
        if drift:
            print("a0x-compile-pair-schemas: FAIL: generated projection drift: " + ", ".join(drift))
            return 1
        print(f"a0x-compile-pair-schemas: PASS: {len(selected)} file(s) match")
        return 0
    except (OSError, ProjectionError) as error:
        print(f"a0x-compile-pair-schemas: FAIL: safe write failed: {error}", file=sys.stderr)
        return 2
    finally:
        if schemas_descriptor is not None:
            os.close(schemas_descriptor)
        if root_descriptor is not None:
            os.close(root_descriptor)


def _select(outputs: dict[str, bytes], requested: list[str]) -> dict[str, bytes]:
    if not requested:
        return outputs
    requested_paths = {f"schemas/{name}" if not name.startswith("schemas/") else name for name in requested}
    unknown = requested_paths - set(outputs)
    if unknown:
        raise ProjectionError("unknown registered projection: " + ", ".join(sorted(unknown)))
    selected = {relative: payload for relative, payload in outputs.items() if relative in requested_paths}
    selected.setdefault("schemas/a0x-pair-binding.fragment.json", outputs["schemas/a0x-pair-binding.fragment.json"])
    return selected


def _output_basename(relative: str) -> str:
    """Accept only a direct generated schemas child, never a caller path."""
    candidate = PurePosixPath(relative)
    if (
        candidate.is_absolute()
        or len(candidate.parts) != 2
        or candidate.parts[0] != "schemas"
        or not candidate.name.startswith("a0x-")
        or not candidate.name.endswith(".json")
    ):
        raise ProjectionError("projection output path is not a direct A0X schemas child")
    return candidate.name


def _open_projection_directories(root_value: Path) -> tuple[int, int]:
    """Open exact root and schemas directories without following either component."""
    root = Path(root_value)
    root_descriptor = os.open(root, _DIRECTORY_FLAGS)
    try:
        schemas_descriptor = os.open("schemas", _DIRECTORY_FLAGS, dir_fd=root_descriptor)
    except BaseException:
        os.close(root_descriptor)
        raise
    try:
        _revalidate_visible_schemas(root, root_descriptor, schemas_descriptor)
    except BaseException:
        os.close(schemas_descriptor)
        os.close(root_descriptor)
        raise
    return root_descriptor, schemas_descriptor


def _revalidate_visible_schemas(root: Path, root_descriptor: int, schemas_descriptor: int) -> None:
    """Refuse if caller-visible root/schemas no longer identify owned descriptors."""
    root_metadata = os.stat(root, follow_symlinks=False)
    descriptor_root_metadata = os.fstat(root_descriptor)
    if (
        not stat.S_ISDIR(root_metadata.st_mode)
        or (root_metadata.st_dev, root_metadata.st_ino)
        != (descriptor_root_metadata.st_dev, descriptor_root_metadata.st_ino)
    ):
        raise ProjectionError("projection root changed during write")
    schemas_metadata = os.stat("schemas", dir_fd=root_descriptor, follow_symlinks=False)
    descriptor_schemas_metadata = os.fstat(schemas_descriptor)
    if (
        not stat.S_ISDIR(schemas_metadata.st_mode)
        or (schemas_metadata.st_dev, schemas_metadata.st_ino)
        != (descriptor_schemas_metadata.st_dev, descriptor_schemas_metadata.st_ino)
    ):
        raise ProjectionError("projection schemas directory changed during write")


def _target_mode(schemas_descriptor: int, basename: str) -> int:
    """Inspect a direct child without following its final component."""
    try:
        metadata = os.stat(basename, dir_fd=schemas_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return 0o644
    if stat.S_ISLNK(metadata.st_mode):
        raise ProjectionError("projection output target must not be a symlink")
    if not stat.S_ISREG(metadata.st_mode):
        raise ProjectionError("projection output target must be a regular file")
    return stat.S_IMODE(metadata.st_mode)


def _read_target(schemas_descriptor: int, basename: str) -> bytes:
    """Read a checked output through owned schemas descriptor only."""
    descriptor = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=schemas_descriptor)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ProjectionError("projection output target must be a regular file")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            return stream.read()
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _atomic_write(schemas_descriptor: int, basename: str, payload: bytes, mode: int) -> None:
    """Atomically replace a direct child through an owned schemas descriptor."""
    temporary, descriptor = _create_temporary(schemas_descriptor, basename)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(payload)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        os.replace(
            temporary,
            basename,
            src_dir_fd=schemas_descriptor,
            dst_dir_fd=schemas_descriptor,
        )
        os.fsync(schemas_descriptor)
    finally:
        try:
            os.unlink(temporary, dir_fd=schemas_descriptor)
        except FileNotFoundError:
            pass
        if descriptor is not None:
            os.close(descriptor)


def _create_temporary(schemas_descriptor: int, basename: str) -> tuple[str, int]:
    """Reserve a direct-child temporary name without inspecting caller paths."""
    for sequence in range(100):
        temporary = f".{basename}.a0x-projection-{os.getpid()}-{sequence}"
        try:
            descriptor = os.open(temporary, _TEMPORARY_FLAGS, 0o600, dir_fd=schemas_descriptor)
        except FileExistsError:
            continue
        return temporary, descriptor
    raise OSError("could not reserve projection temporary file")


def _before_directory_write() -> None:
    """Narrow test seam for replacement-race regression coverage."""


if __name__ == "__main__":
    raise SystemExit(main())
