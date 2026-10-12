"""Target-free regressions for the exact A0X vertical P0 bootstrap."""

from __future__ import annotations

import hashlib
import builtins
import io
import importlib.util
import json
import os
import argparse
import py_compile
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unicodedata
import unittest
from dataclasses import dataclass
from contextlib import ExitStack, contextmanager
from unittest import mock
from pathlib import Path, PurePosixPath, PureWindowsPath


ROOT = Path(os.path.abspath(__file__)).parents[1]
SCRIPT_RELATIVE = Path("scripts/a0x_vertical_p0_bootstrap.py")
V2_SCRIPT_RELATIVE = Path("scripts/a0x_vertical_p0_v2.py")
V2_PREEXEC_RELATIVE = Path("scripts/a0x_vertical_p0_preexec_v2.py")
REVIEW_RELATIVE = Path(
    "docs/qualification/"
    "a0x-vertical-slice-local-review-77dcae52542d21e9bf16e4f17102abf70e68ffc3.md"
)
PROTECTED_TARGET_PATHS = frozenset({
    "data/a0/sealed-targets/targets.jsonl",
    "data/a0/procedural-targets/calibration-targets.jsonl",
    "data/a0r1/targets/calibration.jsonl",
    "data/a0r1/targets/sealed.jsonl",
})
N3_PROFILE_MANIFEST = Path("docs/qualification/a0x-target-free-schema-profile-v1-manifest.json")
N3_PROFILE_MANIFEST_SHA256 = "b88ca0db8f2c05d1e00021b2915e9c75d654b5ec7d0d3b5894ed05343f96b9cf"
MAX_FIXTURE_SOURCE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class AdmittedFixtureSource:
    relative_path: str
    raw_bytes: bytes


def _canonical_fixture_source_paths(
    relative_paths: object,
    *,
    forbidden_paths: frozenset[str] | set[str],
) -> tuple[str, ...]:
    try:
        values = tuple(relative_paths)  # type: ignore[arg-type]
    except TypeError as exc:
        raise AssertionError("fixture source paths must be an iterable of literals") from exc
    if not values:
        raise AssertionError("fixture source set must not be empty")

    canonical: list[str] = []
    for value in values:
        try:
            raw = os.fspath(value)
        except TypeError as exc:
            raise AssertionError("fixture source path is not path-like") from exc
        if not isinstance(raw, str):
            raise AssertionError("fixture source path must be text")
        if (
            not raw
            or "\\" in raw
            or "\x00" in raw
            or ":" in raw
            or any(ord(character) < 32 or ord(character) == 127 for character in raw)
            or unicodedata.normalize("NFC", raw) != raw
            or PurePosixPath(raw).is_absolute()
            or PureWindowsPath(raw).is_absolute()
        ):
            raise AssertionError(f"noncanonical fixture source path: {raw!r}")
        components = raw.split("/")
        if (
            "//" in raw
            or raw.endswith("/")
            or any(component in {"", ".", ".."} for component in components)
            or any(component.endswith((".", " ")) for component in components)
            or PurePosixPath(raw).as_posix() != raw
        ):
            raise AssertionError(f"noncanonical fixture source path: {raw!r}")
        canonical.append(raw)

    if len(set(canonical)) != len(canonical):
        raise AssertionError("fixture source set contains duplicate paths")
    forbidden_folded = {item.casefold() for item in forbidden_paths}
    forbidden = [path for path in canonical if path.casefold() in forbidden_folded]
    if forbidden:
        raise AssertionError(f"protected or excluded fixture path rejected: {forbidden[0]}")
    return tuple(sorted(canonical))


def _directory_open_flags() -> int:
    try:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise AssertionError("platform lacks required no-follow directory flags") from exc


def _file_open_flags() -> int:
    try:
        return os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise AssertionError("platform lacks required no-follow file flags") from exc


def _open_directory_chain_without_symlinks(directory: Path) -> int:
    raw = os.fspath(directory)
    if not isinstance(raw, str) or not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise AssertionError("fixture root must be a canonical absolute path")
    flags = _directory_open_flags()
    try:
        descriptor = os.open(os.path.sep, flags)
    except OSError as exc:
        raise AssertionError("filesystem root cannot be opened without following links") from exc
    try:
        for component in raw.split(os.path.sep)[1:]:
            if not component:
                continue
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except OSError as exc:
                raise AssertionError("fixture root contains an unavailable or symlinked component") from exc
            try:
                if not stat.S_ISDIR(os.fstat(child).st_mode):
                    raise AssertionError("fixture root component is not a directory")
            except BaseException:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_regular_independent_file_from_root(root_descriptor: int, relative: str) -> bytes:
    components = relative.split("/")
    directory_flags = _directory_open_flags()
    current_directory = os.dup(root_descriptor)
    file_descriptor: int | None = None
    try:
        for component in components[:-1]:
            try:
                child = os.open(component, directory_flags, dir_fd=current_directory)
            except OSError as exc:
                raise AssertionError(f"symlinked fixture source component or unavailable ancestor: {relative}") from exc
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise AssertionError(f"fixture source ancestor is not a directory: {relative}")
            os.close(current_directory)
            current_directory = child

        try:
            file_descriptor = os.open(components[-1], _file_open_flags(), dir_fd=current_directory)
        except OSError as exc:
            raise AssertionError(f"fixture source cannot be opened without following links: {relative}") from exc
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise AssertionError(f"fixture source is not an independent regular file: {relative}")
        if before.st_size < 0 or before.st_size > MAX_FIXTURE_SOURCE_BYTES:
            raise AssertionError(f"fixture source exceeds the bounded size: {relative}")

        raw = bytearray()
        while True:
            chunk = os.read(file_descriptor, min(1024 * 1024, MAX_FIXTURE_SOURCE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > MAX_FIXTURE_SOURCE_BYTES:
                raise AssertionError(f"fixture source exceeds the bounded size: {relative}")
        after = os.fstat(file_descriptor)
        identity_before = (
            before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
            before.st_size, before.st_mtime_ns, before.st_ctime_ns,
        )
        identity_after = (
            after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
            after.st_size, after.st_mtime_ns, after.st_ctime_ns,
        )
        if identity_before != identity_after or len(raw) != before.st_size:
            raise AssertionError(f"fixture source changed while being admitted: {relative}")
        return bytes(raw)
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        os.close(current_directory)


def _read_regular_independent_file(root: Path, relative: str) -> bytes:
    forbidden_paths = globals().get("FORBIDDEN_FIXTURE_PATHS", PROTECTED_TARGET_PATHS)
    canonical = _canonical_fixture_source_paths((relative,), forbidden_paths=forbidden_paths)[0]
    root_descriptor = _open_directory_chain_without_symlinks(root)
    try:
        return _read_regular_independent_file_from_root(root_descriptor, canonical)
    finally:
        os.close(root_descriptor)


def _parse_review_ledger(review_document: bytes | str) -> tuple[list[str], list[str]]:
    if isinstance(review_document, bytes):
        try:
            text = review_document.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AssertionError("review ledger is not UTF-8") from exc
    elif isinstance(review_document, str):
        text = review_document
    else:
        raise AssertionError("review ledger must be admitted bytes or text")
    try:
        block = text.split("## Raw P0 package-input ledger", 1)[1]
        lines = block.split("```text\n", 1)[1].split("\n```", 1)[0].splitlines()
        paths = [line.split(" ", 2)[2] for line in lines]
    except (IndexError, ValueError) as exc:
        raise AssertionError("review ledger structure is invalid") from exc
    if len(paths) != 137:
        raise AssertionError(f"unexpected canonical test ledger cardinality: {len(paths)}")
    return paths, lines


def _parse_n3_excluded_sensitive_paths(raw: bytes) -> frozenset[str]:
    if hashlib.sha256(raw).hexdigest() != N3_PROFILE_MANIFEST_SHA256:
        raise AssertionError("N3 profile manifest identity mismatch")
    try:
        manifest = json.loads(raw)
        paths = manifest["instance_dispositions"]["excluded_sensitive_role_unverified"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise AssertionError("N3 profile manifest structure is invalid") from exc
    if not isinstance(paths, list) or len(paths) != 14 or any(not isinstance(path, str) for path in paths):
        raise AssertionError("N3 sensitive-path inventory is not the expected closed list")
    if len(set(paths)) != 14:
        raise AssertionError("N3 sensitive-path inventory contains duplicates")
    return frozenset(paths)


N3_PROFILE_MANIFEST_BYTES = _read_regular_independent_file(ROOT, N3_PROFILE_MANIFEST.as_posix())
N3_EXCLUDED_SENSITIVE_PATHS = _parse_n3_excluded_sensitive_paths(N3_PROFILE_MANIFEST_BYTES)


def _parse_n3_excluded_role_paths(raw: bytes) -> frozenset[str]:
    if hashlib.sha256(raw).hexdigest() != N3_PROFILE_MANIFEST_SHA256:
        raise AssertionError("N3 profile manifest identity mismatch")
    try:
        manifest = json.loads(raw)
        paths = manifest["instance_dispositions"]["excluded_role_unverified"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise AssertionError("N3 role-exclusion inventory is invalid") from exc
    if not isinstance(paths, list) or len(paths) != 137 or any(not isinstance(path, str) for path in paths):
        raise AssertionError("N3 role-exclusion inventory is not the expected closed list")
    if len(set(paths)) != 137:
        raise AssertionError("N3 role-exclusion inventory contains duplicates")
    return frozenset(paths)


N3_EXCLUDED_ROLE_PATHS = _parse_n3_excluded_role_paths(N3_PROFILE_MANIFEST_BYTES)
FORBIDDEN_FIXTURE_PATHS = PROTECTED_TARGET_PATHS | N3_EXCLUDED_SENSITIVE_PATHS | N3_EXCLUDED_ROLE_PATHS


def _load_n3_excluded_sensitive_paths(root: Path | None = None) -> frozenset[str]:
    selected_root = ROOT if root is None else root
    raw = _read_regular_independent_file(selected_root, N3_PROFILE_MANIFEST.as_posix())
    return _parse_n3_excluded_sensitive_paths(raw)


PYTHON = Path(sys.executable).resolve()
PREEXEC_SOURCE = """\
import hashlib
import hmac
import os
import stat
import sys

MAXIMUM = 64 * 1024 * 1024
CODE = "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH"

def refuse():
    print(f"a0x-vertical-p0-preexec: {CODE}", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]
expected_sha256 = sys.argv[2]
if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
    refuse()
try:
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= MAXIMUM:
        refuse()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        raw = b"".join(iter(lambda: os.read(descriptor, 1024 * 1024), b""))
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)
except (AttributeError, OSError):
    refuse()
identity = (before.st_dev, before.st_ino, before.st_size)
if identity != (opened.st_dev, opened.st_ino, opened.st_size) or identity != (final.st_dev, final.st_ino, final.st_size):
    refuse()
if len(raw) != before.st_size or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
    refuse()
sys.argv = [
    path,
    *sys.argv[3:],
    "--preexec-bootstrap-device", str(opened.st_dev),
    "--preexec-bootstrap-inode", str(opened.st_ino),
    "--preexec-bootstrap-bytes", str(opened.st_size),
]
globals_for_script = {
    "__name__": "__main__",
    "__file__": path,
    "__package__": None,
    "__cached__": None,
}
exec(compile(raw, path, "exec", dont_inherit=True, optimize=0), globals_for_script, globals_for_script)
"""


def _load_bootstrap_module():
    spec = importlib.util.spec_from_file_location(
        "a0x_vertical_p0_bootstrap_under_test", ROOT / SCRIPT_RELATIVE,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("bootstrap module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_v2_module():
    spec = importlib.util.spec_from_file_location(
        "a0x_vertical_p0_v2_under_test", ROOT / V2_SCRIPT_RELATIVE,
    )
    if spec is None or spec.loader is None:
        raise AssertionError("v2 operator module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    environment = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_AUTHOR_NAME": "A0X Test",
        "GIT_AUTHOR_EMAIL": "a0x-test@example.invalid",
        "GIT_COMMITTER_NAME": "A0X Test",
        "GIT_COMMITTER_EMAIL": "a0x-test@example.invalid",
    }
    completed = subprocess.run(
        ("/usr/bin/git", "-C", str(root), *arguments),
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        text=True,
    )
    return completed.stdout.strip()


def _ledger_paths(review_document: bytes | str | None = None) -> list[str]:
    if review_document is None:
        review_document = _read_regular_independent_file(ROOT, REVIEW_RELATIVE.as_posix())
    return _parse_review_ledger(review_document)[0]


def _repository_relative_literal(path: object) -> str | None:
    try:
        raw = os.fspath(path)
    except TypeError:
        return None
    if not isinstance(raw, str):
        return None
    candidate = raw if os.path.isabs(raw) else os.path.join(ROOT, raw)
    candidate = os.path.abspath(candidate)
    try:
        relative = os.path.relpath(candidate, os.path.abspath(ROOT))
    except ValueError:
        return None
    if relative == os.curdir or relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return None
    return relative.replace(os.sep, "/")


def _refuse_forbidden_fixture_io(path: object) -> None:
    relative = _repository_relative_literal(path)
    if relative is not None and relative.casefold() in {
        item.casefold() for item in FORBIDDEN_FIXTURE_PATHS
    }:
        raise AssertionError(f"protected or excluded fixture I/O is forbidden in this test: {relative}")


def _validate_fixture_source_set(
    root: Path,
    relative_paths: object,
    *,
    already_admitted: dict[str, bytes] | None = None,
) -> tuple[AdmittedFixtureSource, ...]:
    """Admit the complete literal set, then snapshot each safe inode through no-follow descriptors."""
    canonical = _canonical_fixture_source_paths(
        relative_paths,
        forbidden_paths=FORBIDDEN_FIXTURE_PATHS,
    )
    prior = {} if already_admitted is None else dict(already_admitted)
    if any(path not in canonical for path in prior):
        raise AssertionError("pre-admitted fixture bytes are outside the complete source set")
    if any(not isinstance(raw, bytes) for raw in prior.values()):
        raise AssertionError("pre-admitted fixture content must be immutable bytes")

    root_descriptor: int | None = None
    admitted: list[AdmittedFixtureSource] = []
    try:
        for relative in canonical:
            if relative in prior:
                raw = prior[relative]
            else:
                if root_descriptor is None:
                    root_descriptor = _open_directory_chain_without_symlinks(Path(root))
                raw = _read_regular_independent_file_from_root(root_descriptor, relative)
            admitted.append(AdmittedFixtureSource(relative_path=relative, raw_bytes=raw))
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)
    return tuple(admitted)


def _write_admitted_fixture_source(source: AdmittedFixtureSource, destination_root: Path) -> Path:
    if not isinstance(source, AdmittedFixtureSource):
        raise AssertionError("fixture copy requires an admitted byte snapshot")
    destination = Path(destination_root).joinpath(*source.relative_path.split("/"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
    except OSError as exc:
        raise AssertionError(f"fixture destination is occupied or unsafe: {source.relative_path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != 0:
            raise AssertionError(f"fixture destination is not a new independent regular file: {source.relative_path}")
        remaining = memoryview(source.raw_bytes)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise AssertionError(f"fixture snapshot write made no progress: {source.relative_path}")
            remaining = remaining[written:]
        after = os.fstat(descriptor)
        if not stat.S_ISREG(after.st_mode) or after.st_nlink != 1 or after.st_size != len(source.raw_bytes):
            raise AssertionError(f"fixture destination changed during snapshot write: {source.relative_path}")
    finally:
        os.close(descriptor)
    return destination


@contextmanager
def _target_io_guard():
    """Trap pathname reads of protected inputs while constructing test fixtures."""
    real_os_open = os.open

    def guard_first_path(function):
        def guarded(path, *args, **kwargs):
            _refuse_forbidden_fixture_io(path)
            return function(path, *args, **kwargs)
        return guarded

    def guarded_copytree(src, dst, *args, **kwargs):
        raise AssertionError("recursive directory copies are forbidden in this test")

    def guarded_os_open(path, *args, **kwargs):
        if kwargs.get("dir_fd") is not None:
            raise AssertionError("descriptor-relative source access must happen before fixture construction")
        _refuse_forbidden_fixture_io(path)
        return real_os_open(path, *args, **kwargs)

    with ExitStack() as stack:
        for target, function in (("builtins.open", builtins.open), ("io.open", io.open),
                                 ("os.open", real_os_open)):
            guarded = guarded_os_open if target == "os.open" else guard_first_path(function)
            stack.enter_context(mock.patch(target, side_effect=guarded))
        stack.enter_context(mock.patch("shutil.copytree", side_effect=guarded_copytree))
        yield


class SyntheticRepository:
    def __init__(self, parent: Path, *, cleanup_failure: bool = False, generator_failure: bool = False, reload_failure: bool = False, construction_failure: bool = False, publication_failure: bool = False):
        self.root = parent / "repository"
        self.root.mkdir()
        self.import_marker = parent / "repository-imported"
        self.malicious_marker = parent / "malicious-bytecode-executed"
        self.shadow_marker = parent / "path-shadow-executed"
        self.bootstrap_replacement_marker = parent / "bootstrap-replacement-executed"
        self.paths = _ledger_paths()
        for index, relative in enumerate(self.paths):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture-{index:03d}\n".encode("ascii"))
        self._write_repository_sources(cleanup_failure=cleanup_failure, generator_failure=generator_failure, reload_failure=reload_failure, construction_failure=construction_failure, publication_failure=publication_failure)
        package = self.root / "src/latent_triz/__init__.py"
        package.write_text("\"\"\"Synthetic package.\"\"\"\n", encoding="utf-8")
        bootstrap = self.root / SCRIPT_RELATIVE
        bootstrap.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / SCRIPT_RELATIVE, bootstrap)
        shutil.copyfile(ROOT / V2_SCRIPT_RELATIVE, self.root / V2_SCRIPT_RELATIVE)
        shutil.copyfile(ROOT / V2_PREEXEC_RELATIVE, self.root / V2_PREEXEC_RELATIVE)
        (self.root / ".gitignore").write_text(
            ".a0x-runtime/\n__pycache__/\n*.py[cod]\n", encoding="utf-8",
        )
        self._write_ledger_document(self._current_lines())
        _git(self.root, "init", "-q")
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-q", "-m", "synthetic bootstrap fixture")

    def _write_repository_sources(self, *, cleanup_failure: bool, generator_failure: bool, reload_failure: bool, construction_failure: bool, publication_failure: bool) -> None:
        contract = self.root / "src/latent_triz/a0x_contract.py"
        contract.write_text(
            textwrap.dedent(
                f"""\
                from enum import Enum
                from pathlib import Path
                Path({str(self.import_marker)!r}).write_text("imported", encoding="utf-8")
                class Leg(Enum):
                    A0 = "a0"
                """
            ),
            encoding="utf-8",
        )
        vertical = self.root / "src/latent_triz/a0x_vertical_slice.py"
        cleanup_block = ""
        if cleanup_failure:
            cleanup_block = textwrap.indent(
                textwrap.dedent(
                    """\
                    from pathlib import Path
                    import shutil
                    import sys
                    import tempfile
                    cache = Path(sys.pycache_prefix)
                    shutil.rmtree(cache)
                    replacement = Path(tempfile.mkdtemp(prefix="a0x-p0-cleanup-target-"))
                    cache.symlink_to(replacement, target_is_directory=True)
                    """
                ),
                "    ",
            )
        construction_block = "raise RuntimeError('synthetic construction failure')" if construction_failure else "pass"
        vertical.write_text(
            textwrap.dedent(
                """\
                from dataclasses import dataclass
                @dataclass(frozen=True)
                class VerticalSliceRequest:
                    leg: object
                    model_key: str
                    implementation_source_head: str
                    output_root: str
                @dataclass(frozen=True)
                class VerticalRuntimePackageRequest:
                    qualified_source_head: str
                    qualified_source_tree: str
                    leg: object
                    model_key: str
                    output_root: str
                    authorization_id: str
                    attempt_id: str
                    def __post_init__(self):
                        %s
                @dataclass(frozen=True)
                class VerticalPackageBinding:
                    envelope_path: str
                    package_path: str
                    commitment_path: str
                    commitment_raw_sha256: str
                    package_commitment_sha256: str
                    dossier_path: str
                    dossier_sha256: str
                    qualified_source_head: str
                    qualified_source_tree: str
                    leg: object
                    model_key: str
                    model_revision: str
                    pair_binding: object
                def generate_vertical_slice(root, request):
                """ % construction_block
            )
            + cleanup_block
            + textwrap.indent(
                textwrap.dedent(
                    """\
                    return {
                        "artifact_class": "synthetic-a0x-vertical-receipt",
                        "implementation_source_head": request.implementation_source_head,
                        "pair": {"leg": request.leg.value, "model_key": request.model_key},
                        "output_root": request.output_root,
                    }
                    """
                ),
                "    ",
            ),
            encoding="utf-8",
        )
        runtime_failure = "raise RuntimeError('synthetic generator failure')" if generator_failure else ""
        publication_failure_block = "raise RuntimeError('synthetic publication ownership lost')" if publication_failure else ""
        reload_body = (
            "raise RuntimeError('synthetic reload failure')" if reload_failure
            else "return {'binding': binding, 'package_commitment_sha256': binding.package_commitment_sha256, 'dossier_sha256': binding.dossier_sha256}"
        )
        with vertical.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n\ndef generate_vertical_runtime_package(root, request):\n"
                + textwrap.indent(runtime_failure or "pass", "    ") + "\n"
                + "    envelope = root / request.output_root\n"
                + "    (envelope / 'package').mkdir(parents=True, exist_ok=False)\n"
                + "    (envelope / 'package' / 'protocol.json').write_text('{}', encoding='utf-8')\n"
                + "    (envelope / 'p0-commitment.json').write_text('{}', encoding='utf-8')\n"
                + textwrap.indent(publication_failure_block or "pass", "    ") + "\n"
                + textwrap.dedent(
                    """\
                        return VerticalPackageBinding(
                            envelope_path=request.output_root,
                            package_path=request.output_root + "/package",
                            commitment_path=request.output_root + "/p0-commitment.json",
                            commitment_raw_sha256="c" * 64,
                            package_commitment_sha256="a" * 64,
                            dossier_path=request.output_root + "/package/approval-dossier.json",
                            dossier_sha256="b" * 64,
                            qualified_source_head=request.qualified_source_head,
                            qualified_source_tree=request.qualified_source_tree,
                            leg=request.leg,
                            model_key=request.model_key,
                            model_revision="f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
                            pair_binding=None,
                        )

                    def load_vertical_runtime_package(root, binding):
                    """
                )
                + textwrap.indent(reload_body, "    ") + "\n"
            )

    def _current_lines(self) -> list[str]:
        lines = []
        for relative in sorted(self.paths):
            raw = (self.root / relative).read_bytes()
            lines.append(f"{hashlib.sha256(raw).hexdigest()} {len(raw)} {relative}")
        return lines

    def _write_ledger_document(self, lines: list[str]) -> None:
        document = self.root / REVIEW_RELATIVE
        document.parent.mkdir(parents=True, exist_ok=True)
        document.write_text(
            "# Synthetic review\n\n## Raw P0 package-input ledger\n\n```text\n"
            + "\n".join(lines)
            + "\n```\n\n## Exact one-shot P0 command and stop boundary\n",
            encoding="utf-8",
        )

    def commit_all(self, message: str) -> tuple[str, str]:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", message)
        return self.identity()

    def identity(self) -> tuple[str, str]:
        return _git(self.root, "rev-parse", "HEAD"), _git(
            self.root, "rev-parse", "HEAD^{tree}",
        )

    def ledger_digest(self) -> str:
        payload = ("\n".join(self._current_lines()) + "\n").encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def command(
        self,
        *,
        head: str | None = None,
        tree: str | None = None,
        digest: str | None = None,
        bootstrap_sha256: str | None = None,
        isolated: bool = True,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        actual_head, actual_tree = self.identity()
        arguments = [str(PYTHON)]
        if isolated:
            arguments.extend(("-I", "-S", "-B"))
        expected_bootstrap = (
            _sha256(self.root / SCRIPT_RELATIVE)
            if bootstrap_sha256 is None
            else bootstrap_sha256
        )
        arguments.extend(
            (
                "-c", PREEXEC_SOURCE,
                str(self.root / SCRIPT_RELATIVE),
                expected_bootstrap,
                "--repository-root", str(self.root),
                "--expected-head", actual_head if head is None else head,
                "--expected-tree", actual_tree if tree is None else tree,
                "--expected-python", str(PYTHON),
                "--expected-python-sha256", _sha256(PYTHON),
                "--expected-ledger-sha256", self.ledger_digest() if digest is None else digest,
                "--expected-bootstrap-sha256", expected_bootstrap,
                "--expected-preexec-sha256",
                hashlib.sha256(PREEXEC_SOURCE.encode("utf-8")).hexdigest(),
            )
        )
        child_environment = dict(os.environ)
        if environment:
            child_environment.update(environment)
        return subprocess.run(
            arguments,
            cwd=self.root,
            env=child_environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def v2_command(
        self, *, head: str | None = None, tree: str | None = None,
        authorization_sha256: str | None = None, document_authorization_id: str = "p0-v2-test-auth",
        document_tree: str | None = None, expected_python_sha256: str | None = None,
        expected_ledger_sha256: str | None = None,
        expected_bootstrap_sha256: str | None = None,
        document_revision: str = "f8027fd0eaeea54caa13c31d31b9fdc459c38b49",
        target_sha256: str | None = None, direct_target: bool = False, omit_bytecode: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        actual_head, actual_tree = self.identity()
        authorization = (
            self.root / ".a0x-runtime/authorizations/p0/v2" / actual_head / actual_tree
            / "a0/smollm2_360m/p0-v2-test-attempt.json"
        )
        authorization.parent.mkdir(parents=True, exist_ok=True)
        bootstrap = self.root / V2_SCRIPT_RELATIVE
        bootstrap_metadata = bootstrap.lstat()
        python_sha256 = _sha256(PYTHON) if expected_python_sha256 is None else expected_python_sha256
        ledger_sha256 = self.ledger_digest() if expected_ledger_sha256 is None else expected_ledger_sha256
        bootstrap_sha256 = _sha256(bootstrap) if expected_bootstrap_sha256 is None else expected_bootstrap_sha256
        preexec_sha256 = _sha256(self.root / V2_PREEXEC_RELATIVE)
        authorization.write_text(
            json.dumps(
                {
                    "artifact_class": "a0x-vertical-p0-authorization",
                    "authorization_profile": "a0x-vertical-p0-authorization-v2",
                    "source": {"head": actual_head, "tree": actual_tree if document_tree is None else document_tree},
                    "pair": {
                        "leg": "a0", "model_key": "smollm2_360m",
                        "model_revision": document_revision,
                    },
                    "generator_profile": "a0x-vertical-slice-v2",
                    "authorization_id": document_authorization_id,
                    "attempt_id": "p0-v2-test-attempt",
                    "operator": {
                        "profile": "a0x-vertical-p0-bootstrap-v2",
                        "python": {"path": str(PYTHON), "sha256": python_sha256},
                        "ledger": {"sha256": ledger_sha256},
                        "bootstrap": {
                            "path": V2_SCRIPT_RELATIVE.as_posix(),
                            "sha256": bootstrap_sha256,
                            "device": bootstrap_metadata.st_dev,
                            "inode": bootstrap_metadata.st_ino,
                            "bytes": bootstrap_metadata.st_size,
                        },
                        "preexec": {"path": V2_PREEXEC_RELATIVE.as_posix(), "sha256": preexec_sha256},
                    },
                    "output": {
                        "members": [
                            "protocol.json", "implementation.json", "freeze.json",
                            "approval-dossier.json", "slice-manifest.json",
                        ],
                        "commitment": "p0-commitment.json",
                    },
                },
                sort_keys=True, separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        arguments = [
            str(PYTHON), "-I", "-S", *( () if omit_bytecode else ("-B",) ), str(self.root / V2_PREEXEC_RELATIVE),
            "--target", str(self.root / V2_SCRIPT_RELATIVE),
            "--target-sha256", (
                _sha256(self.root / V2_SCRIPT_RELATIVE) if target_sha256 is None else target_sha256
            ),
            "--self-sha256", preexec_sha256,
            "--",
            "--repository-root", str(self.root),
            "--expected-head", actual_head if head is None else head,
            "--expected-tree", actual_tree if tree is None else tree,
            "--expected-python", str(PYTHON),
            "--expected-python-sha256", python_sha256,
            "--expected-ledger-sha256", ledger_sha256,
            "--expected-bootstrap-sha256", bootstrap_sha256,
            "--expected-preexec-sha256", preexec_sha256,
            "--preexec-bootstrap-device", str(bootstrap_metadata.st_dev),
            "--preexec-bootstrap-inode", str(bootstrap_metadata.st_ino),
            "--preexec-bootstrap-bytes", str(bootstrap_metadata.st_size),
            "--authorization-document", str(authorization),
            "--authorization-document-sha256", (
                _sha256(authorization) if authorization_sha256 is None else authorization_sha256
            ),
            "--authorization-id", "p0-v2-test-auth",
            "--attempt-id", "p0-v2-test-attempt",
        ]
        if direct_target:
            separator = arguments.index("--")
            arguments = [
                str(PYTHON), "-I", "-S", "-B", str(bootstrap),
                *arguments[separator + 1:], "--preexec-launcher", str(self.root / V2_PREEXEC_RELATIVE),
            ]
        return subprocess.run(
            arguments, cwd=self.root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, check=False,
        )

    def add_conflicting_bytecode(self) -> None:
        malicious = self.root.parent / "malicious-a0x-vertical-slice.py"
        malicious.write_text(
            textwrap.dedent(
                f"""\
                from pathlib import Path
                Path({str(self.malicious_marker)!r}).write_text("executed", encoding="utf-8")
                raise RuntimeError("malicious bytecode executed")
                """
            ),
            encoding="utf-8",
        )
        cache = self.root / "src/latent_triz/__pycache__"
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / f"a0x_vertical_slice.{sys.implementation.cache_tag}.pyc"
        py_compile.compile(
            str(malicious),
            cfile=str(target),
            doraise=True,
            invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
        )


class A0XVerticalP0BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="a0x-p0-bootstrap-")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture(self, *, cleanup_failure: bool = False, generator_failure: bool = False, reload_failure: bool = False, construction_failure: bool = False, publication_failure: bool = False) -> SyntheticRepository:
        return SyntheticRepository(
            Path(self.temporary.name), cleanup_failure=cleanup_failure, generator_failure=generator_failure,
            reload_failure=reload_failure, construction_failure=construction_failure,
            publication_failure=publication_failure,
        )

    def test_n3_manifest_symlink_and_hardlink_are_rejected_before_byte_reads(self) -> None:
        module = sys.modules[__name__]
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix="a0x-manifest-admission-") as temporary:
                root = Path(temporary).resolve()
                manifest = root / N3_PROFILE_MANIFEST
                manifest.parent.mkdir(parents=True)
                sentinel = root / "sentinel.json"
                sentinel.write_bytes(b"synthetic sentinel, never a valid N3 manifest")
                if kind == "symlink":
                    manifest.symlink_to(sentinel)
                else:
                    os.link(sentinel, manifest)

                path_open_calls: list[object] = []
                real_io_open = io.open

                def record_path_open(path: object, *args: object, **kwargs: object):
                    path_open_calls.append(path)
                    return real_io_open(path, *args, **kwargs)

                with mock.patch.object(module, "ROOT", root), \
                     mock.patch.object(io, "open", side_effect=record_path_open), \
                     mock.patch.object(os, "read", wraps=os.read) as descriptor_read:
                    with self.assertRaises(AssertionError):
                        _load_n3_excluded_sensitive_paths()

                self.assertEqual([], path_open_calls, "manifest must not be read through a following pathname")
                descriptor_read.assert_not_called()

    def test_admitted_fixture_snapshot_survives_source_path_replacement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a0x-fixture-snapshot-") as temporary:
            root = (Path(temporary) / "root").resolve()
            outside = Path(temporary) / "outside.txt"
            root.mkdir()
            source = root / "source.txt"
            approved = b"approved synthetic bytes"
            replacement = b"replacement sentinel bytes"
            source.write_bytes(approved)
            outside.write_bytes(replacement)

            admitted = _validate_fixture_source_set(root, {"source.txt"})
            self.assertEqual(1, len(admitted))
            admitted_bytes = getattr(admitted[0], "raw_bytes", None)
            self.assertEqual(approved, admitted_bytes, "admission must retain bytes from the opened inode")

            source.unlink()
            source.symlink_to(outside)
            destination_root = Path(temporary) / "copy"
            _write_admitted_fixture_source(admitted[0], destination_root)
            self.assertEqual(approved, (destination_root / "source.txt").read_bytes())
            self.assertNotEqual(replacement, (destination_root / "source.txt").read_bytes())

    def test_ledger_parser_uses_admitted_snapshot_after_source_path_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a0x-ledger-snapshot-") as temporary:
            root = Path(temporary).resolve()
            review = root / REVIEW_RELATIVE
            review.parent.mkdir(parents=True)
            expected_paths = [f"fixtures/item-{index:03d}.txt" for index in range(137)]

            def document(paths: list[str]) -> bytes:
                rows = [f"{'0' * 64} 1 {path}" for path in paths]
                return (
                    "## Raw P0 package-input ledger\n\n```text\n"
                    + "\n".join(rows)
                    + "\n```\n"
                ).encode("utf-8")

            admitted_document = document(expected_paths)
            review.write_bytes(admitted_document)
            admitted = _validate_fixture_source_set(root, {REVIEW_RELATIVE.as_posix()})
            raw_bytes = getattr(admitted[0], "raw_bytes", None)
            self.assertEqual(admitted_document, raw_bytes, "ledger source must be captured during admission")

            review.write_bytes(document([f"changed/item-{index:03d}.txt" for index in range(137)]))
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("ledger path was reopened")), \
                 mock.patch.object(Path, "read_text", side_effect=AssertionError("ledger path was reopened")):
                try:
                    parsed_paths = _ledger_paths(raw_bytes)
                except TypeError as exc:
                    self.fail(f"ledger parser must consume admitted bytes, not reopen a path: {exc}")

            self.assertEqual(expected_paths, parsed_paths)

    def test_fixture_source_set_rejects_all_eighteen_forbidden_literals_before_candidate_io(self) -> None:
        excluded = sorted(N3_EXCLUDED_SENSITIVE_PATHS)
        self.assertEqual(14, len(excluded))
        forbidden = set(PROTECTED_TARGET_PATHS) | set(excluded)
        self.assertEqual(18, len(forbidden))
        with tempfile.TemporaryDirectory(prefix="a0x-fixture-deny-") as temporary:
            root = Path(temporary).resolve()
            safe = root / "safe.txt"
            safe.write_text("synthetic", encoding="utf-8")
            self.assertEqual(
                (AdmittedFixtureSource("safe.txt", b"synthetic"),),
                _validate_fixture_source_set(root, {"safe.txt"}),
            )
            for relative in forbidden:
                with self.subTest(relative=relative):
                    with mock.patch.object(os, "open", side_effect=AssertionError("candidate I/O before admission")) as opened:
                        with self.assertRaisesRegex(AssertionError, "protected or excluded fixture path rejected"):
                            _validate_fixture_source_set(root, {"safe.txt", relative})
                    opened.assert_not_called()

    def test_fixture_source_set_rejects_every_n3_role_unverified_path_before_candidate_io(self) -> None:
        try:
            manifest = json.loads(N3_PROFILE_MANIFEST_BYTES)
            excluded_paths = manifest["instance_dispositions"]["excluded_role_unverified"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self.fail(f"N3 role-exclusion inventory must be readable from the admitted manifest: {exc}")
        self.assertIsInstance(excluded_paths, list)
        self.assertEqual(137, len(excluded_paths))
        self.assertTrue(all(isinstance(path, str) for path in excluded_paths))
        self.assertEqual(len(excluded_paths), len(set(excluded_paths)))

        with tempfile.TemporaryDirectory(prefix="a0x-fixture-role-deny-") as temporary:
            root = Path(temporary).resolve()
            (root / "safe.txt").write_text("synthetic", encoding="utf-8")
            for relative in excluded_paths:
                with self.subTest(relative=relative):
                    with ExitStack() as stack:
                        guards = []

                        def refuse_io(*_args: object, **_kwargs: object) -> None:
                            raise AssertionError("candidate filesystem I/O before deny decision")

                        for owner, names in (
                            (os, ("open", "read", "fstat", "stat", "lstat", "scandir", "listdir")),
                            (Path, ("open", "read_bytes", "read_text", "stat", "lstat", "resolve", "exists", "is_file", "is_dir")),
                            (builtins, ("open",)),
                            (io, ("open",)),
                            (shutil, ("copyfile", "copy2", "copytree")),
                        ):
                            for name in names:
                                guards.append(
                                    stack.enter_context(
                                        mock.patch.object(owner, name, side_effect=refuse_io),
                                    ),
                                )
                        with self.assertRaisesRegex(
                            AssertionError,
                            "protected or excluded fixture path rejected",
                        ):
                            _validate_fixture_source_set(root, {"safe.txt", relative})
                        for guard in guards:
                            guard.assert_not_called()

    def test_fixture_source_set_rejects_absolute_traversal_and_noncanonical_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a0x-fixture-alias-") as temporary:
            root = Path(temporary).resolve()
            aliases = {
                "../outside.txt", f"{root}/absolute.txt", r"nested\\file.txt",
                "nested//file.txt", "nested/./file.txt", "./safe.txt",
                "nested/", "C:/absolute.txt",
            }
            for relative in aliases:
                with self.subTest(relative=relative):
                    with mock.patch.object(os, "open", side_effect=AssertionError("candidate I/O before admission")) as opened:
                        with self.assertRaisesRegex(AssertionError, "noncanonical fixture source path"):
                            _validate_fixture_source_set(root, {"safe.txt", relative})
                    opened.assert_not_called()

    def test_fixture_source_set_rejects_symlinked_ancestor_without_opening_destination(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a0x-fixture-symlink-") as temporary:
            root = Path(temporary) / "root"
            outside = Path(temporary) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "source.txt").write_text("synthetic", encoding="utf-8")
            (root / "alias").symlink_to(outside, target_is_directory=True)
            with mock.patch.object(os, "read", wraps=os.read) as source_read:
                with self.assertRaisesRegex(AssertionError, "symlinked fixture source component"):
                    _validate_fixture_source_set(root.resolve(), {"alias/source.txt"})
            source_read.assert_not_called()

    def test_fixture_source_set_rejects_hardlinked_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="a0x-fixture-hardlink-") as temporary:
            root = Path(temporary)
            directory = root / "directory"
            directory.mkdir()
            with self.assertRaisesRegex(AssertionError, "independent regular file"):
                _validate_fixture_source_set(root.resolve(), {"directory"})
            source = root / "source.txt"
            source.write_text("synthetic", encoding="utf-8")
            os.link(source, root / "alias.txt")
            with mock.patch.object(os, "read", wraps=os.read) as source_read:
                with self.assertRaisesRegex(AssertionError, "independent regular file"):
                    _validate_fixture_source_set(root.resolve(), {"source.txt"})
            source_read.assert_not_called()

    def test_private_pycache_uses_platform_temp_root(self) -> None:
        """The bootstrap must not assume macOS's /private/tmp on hosted Linux."""
        module = _load_bootstrap_module()
        calls: dict[str, object] = {}

        def fake_mkdtemp(**kwargs: object) -> str:
            calls.update(kwargs)
            path = Path(self.temporary.name) / "portable-pycache"
            path.mkdir()
            return str(path)

        with mock.patch.object(module.tempfile, "mkdtemp", side_effect=fake_mkdtemp):
            path = module._create_private_pycache()
        self.assertNotIn("dir", calls)
        self.assertEqual(str(path), sys.pycache_prefix)

    def test_canonical_v2_operator_entrypoint_uses_only_the_v2_generator(self) -> None:
        """RED: v2 must be a distinct operator, not an implicit v1 rewrite."""
        operator = ROOT / "scripts/a0x_vertical_p0_v2.py"
        self.assertTrue(operator.is_file())
        source = operator.read_text(encoding="utf-8")
        self.assertIn("generate_vertical_runtime_package", source)
        self.assertNotIn("generate_vertical_slice", source)

    def test_canonical_v2_operator_help_runs_in_isolated_python(self) -> None:
        """The operator must expose its bound inlet before repository imports."""
        completed = subprocess.run(
            [str(PYTHON), "-I", "-S", "-B", str(ROOT / "scripts/a0x_vertical_p0_v2.py"), "--help"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("--authorization-document", completed.stdout)
        self.assertIn("--attempt-id", completed.stdout)

    def test_canonical_v2_operator_dispatches_real_subprocess_to_v2_generator(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command()
        self.assertEqual(0, completed.returncode, completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual("a" * 64, receipt["package_commitment_sha256"])
        self.assertEqual("b" * 64, receipt["dossier_sha256"])
        self.assertEqual("f8027fd0eaeea54caa13c31d31b9fdc459c38b49", receipt["model_revision"])

    def test_contract_checker_cli_uses_temporary_synthetic_root_and_fails_closed(self) -> None:
        """The production checker must receive a disposable synthetic root, never ROOT."""
        with tempfile.TemporaryDirectory(prefix="a0x-contract-synthetic-") as temporary:
            synthetic_root = Path(temporary) / "repository"
            scripts = synthetic_root / "scripts"
            scripts.mkdir(parents=True)
            (synthetic_root / "schemas").mkdir()
            checker_source = _read_regular_independent_file(
                ROOT, "scripts/a0x_contract_check.py",
            )
            checker = scripts / "a0x_contract_check.py"
            checker.write_bytes(checker_source)
            environment = {
                "PATH": "/usr/bin:/bin",
                "LC_ALL": "C",
                "PYTHONPATH": str(ROOT / "src"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            completed = subprocess.run(
                (str(PYTHON), "-B", str(checker), "--phase", "synthetic"),
                cwd=synthetic_root,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(1, completed.returncode)
            self.assertEqual("", completed.stdout)
            self.assertIn("a0x-contract-check: A0X schemas are unavailable", completed.stderr)

    def test_contract_checker_cli_accepts_a_disposable_target_free_synthetic_root(self) -> None:
        """The production checker accepts synthetic engineering inputs without material access."""
        with tempfile.TemporaryDirectory(prefix="a0x-contract-accepted-synthetic-") as temporary:
            synthetic_root = Path(temporary) / "repository"
            scripts = synthetic_root / "scripts"
            scripts.mkdir(parents=True)
            schemas = synthetic_root / "schemas"
            schemas.mkdir()
            checker = scripts / "a0x_contract_check.py"
            checker.write_bytes(_read_regular_independent_file(ROOT, "scripts/a0x_contract_check.py"))
            for source_schema in (ROOT / "schemas").glob("a0x-*.schema.json"):
                target = schemas / source_schema.name
                target.write_bytes(_read_regular_independent_file(ROOT, source_schema.relative_to(ROOT).as_posix()))

            def write_json(relative: str, value: object) -> Path:
                path = synthetic_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
                return path

            def schema_example(schema: dict[str, object], root_schema: dict[str, object]) -> object:
                if "const" in schema:
                    return schema["const"]
                if "enum" in schema:
                    return schema["enum"][0]
                reference = schema.get("$ref")
                if isinstance(reference, str):
                    target: object = root_schema
                    for segment in reference.removeprefix("#/").split("/"):
                        target = target[segment.replace("~1", "/").replace("~0", "~")]
                    return schema_example(target, root_schema)
                kind = schema.get("type")
                if kind == "object":
                    return {
                        name: schema_example(schema["properties"][name], root_schema)
                        for name in schema.get("required", [])
                    }
                if kind == "array":
                    return [schema_example(schema["items"], root_schema)] * schema.get("minItems", 0)
                if kind == "boolean":
                    return False
                if kind == "integer":
                    return schema.get("minimum", 0)
                if kind == "string":
                    pattern = schema.get("pattern", "")
                    if "{64}" in pattern:
                        return "a" * 64
                    if "{40}" in pattern:
                        return "a" * 40
                    return "synthetic/engineering.json"
                raise AssertionError(f"unsupported public schema fixture node: {schema!r}")

            material_schema = json.loads((schemas / "a0x-material-execution-contract.schema.json").read_text())
            material_contract = schema_example(material_schema, material_schema)
            write_json("experiments/a0x-six-model/material-execution-contract.json", material_contract)

            models = (
                ("smollm2_360m", "HuggingFaceTB/SmolLM2-360M", "f8027fd0eaeea54caa13c31d31b9fdc459c38b49", "artifacts/models/smollm2-360m-f8027fd0", "llama", "LlamaForCausalLM"),
                ("qwen3_0_6b_base", "Qwen/Qwen3-0.6B-Base", "da87bfb608c14b7cf20ba1ce41287e8de496c0cd", "artifacts/models/qwen3-0.6b-base-da87bfb", "qwen3", "Qwen3ForCausalLM"),
                ("gpt2", "openai-community/gpt2", "607a30d783dfa663caf39e06633721c8d4cfcd7e", "artifacts/models/gpt2-607a30d7", "gpt2", "GPT2LMHeadModel"),
                ("smollm2_135m", "HuggingFaceTB/SmolLM2-135M", "93efa2f097d58c2a74874c7e644dbc9b0cee75a2", "artifacts/models/smollm2-135m-93efa2f0", "llama", "LlamaForCausalLM"),
                ("gpt_neo_125m", "EleutherAI/gpt-neo-125m", "21def0189f5705e2521767faed922f1f15e7d7db", "artifacts/models/gpt-neo-125m-21def018", "gpt_neo", "GPTNeoForCausalLM"),
                ("qwen2_5_0_5b", "Qwen/Qwen2.5-0.5B", "060db6499f32faf8b98477b0a26969ef7d8b9987", "artifacts/models/qwen2.5-0.5b-060db649", "qwen2", "Qwen2ForCausalLM"),
            )
            registry_cards: list[str] = []
            registry_models: list[dict[str, str]] = []
            for key, model_id, revision, runtime_root, model_type, architecture in models:
                receipt_path = f"experiments/a0x-six-model/synthetic-source/{key}-receipt.json"
                audit_path = f"experiments/a0x-six-model/synthetic-source/{key}-audit.json"
                card_path = f"experiments/a0x-six-model/synthetic-cards/{key}.json"
                fact_fields = {
                    name: name for name in (
                        "model_type", "architecture", "num_hidden_layers", "hidden_size", "vocab_size",
                        "effective_context", "final_transformer_block_tuple_index",
                    )
                }
                tokenizer_fields = {
                    name: name for name in (
                        "tokenizer_metadata_class", "expected_runtime_tokenizer_class", "fast_offsets_required",
                    )
                }
                receipt = {
                    "model_id": model_id, "revision": revision, "license_id": "synthetic-license",
                    "runtime_root": runtime_root, "runtime_files": [{"path": "config.json", "size_bytes": 1, "sha256": "b" * 64}],
                    **{name: name for name in (*fact_fields, *tokenizer_fields)},
                }
                receipt_raw = json.dumps(receipt, sort_keys=True).encode("utf-8")
                write_json(receipt_path, receipt)
                write_json(audit_path, {"synthetic_audit": True, "model_key": key})
                card = {
                    "artifact_class": "a0x-model-card", "empirical": True, "scientific_status": "exploratory",
                    "evidence_eligible": False, "expert_validated": False, "claim_ids": [], "model_key": key,
                    "model_id": model_id, "revision": revision, "license_id": "synthetic-license",
                    "architecture": architecture, "model_type": model_type, "runtime_root": runtime_root,
                    "runtime_files": [{"path": "config.json", "size_bytes": 1, "sha256": "b" * 64}],
                    "num_hidden_layers": 1, "hidden_size": 1, "vocab_size": 2, "effective_context": 2,
                    "final_transformer_block_tuple_index": 1, "tokenizer_metadata_class": "SyntheticTokenizer",
                    "expected_runtime_tokenizer_class": "SyntheticTokenizer", "fast_offsets_required": False,
                    "pad_side": None, "trust_remote_code": False, "source_receipt_path": receipt_path,
                    "source_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(), "official_audit_path": audit_path,
                    "official_audit_sha256": hashlib.sha256(json.dumps({"synthetic_audit": True, "model_key": key}, sort_keys=True).encode()).hexdigest(),
                    "config_fact_provenance": {"source_path": receipt_path, "source_sha256": hashlib.sha256(receipt_raw).hexdigest(), "field_pointers": fact_fields},
                    "tokenizer_fact_provenance": {"source_path": receipt_path, "source_sha256": hashlib.sha256(receipt_raw).hexdigest(), "field_pointers": tokenizer_fields},
                    "card_path": card_path,
                }
                write_json(card_path, card)
                registry_cards.append(f"synthetic-cards/{key}.json")
                registry_models.append({"model_id": model_id, "revision": revision, "runtime_root": runtime_root})
            source_path = "experiments/a0x-six-model/synthetic-registry-source.json"
            source_payload = {"models": registry_models}
            source_raw = json.dumps(source_payload, sort_keys=True).encode("utf-8")
            write_json(source_path, source_payload)
            write_json("experiments/a0x-six-model/model-registry.json", {
                "artifact_class": "a0x-model-registry", "registry_source_path": source_path,
                "registry_source_sha256": hashlib.sha256(source_raw).hexdigest(), "cards": registry_cards,
            })

            data_cases = []
            domains = ("agriculture", "energy", "manufacturing", "medicine", "software", "transport")
            for domain in domains:
                for family_index in range(4):
                    family = f"{domain}-synthetic-{family_index}"
                    for case_index in range(2):
                        data_cases.append({
                            "case_id": f"{family}-{case_index}", "case_content_sha256": hashlib.sha256(f"{family}-{case_index}".encode()).hexdigest(),
                            "domain": domain, "problem_family_id": family, "split": f"synthetic-{case_index}",
                        })
            cases_relative = "data/a0/cases.jsonl"
            cases_raw = "\n".join(json.dumps(case, sort_keys=True) for case in data_cases) + "\n"
            (synthetic_root / cases_relative).parent.mkdir(parents=True, exist_ok=True)
            (synthetic_root / cases_relative).write_text(cases_raw, encoding="utf-8")
            manifest_relative = "data/a0/manifest.json"
            manifest = {"neutral_domains": list(domains)}
            manifest_raw = json.dumps(manifest, sort_keys=True).encode("utf-8")
            write_json(manifest_relative, manifest)
            cases_sha = hashlib.sha256(cases_raw.encode("utf-8")).hexdigest()
            manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
            selection_binding = {"source_cases_sha256": cases_sha, "source_corpus_manifest_sha256": manifest_sha}
            selection = {
                "artifact_class": "a0x-selection-manifest", "empirical": True, "scientific_status": "exploratory",
                "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
                "selection_corpus_sha256": hashlib.sha256(json.dumps(selection_binding, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "selection_path": "experiments/a0x-six-model/a0-selection-manifest.json", "selected_case_count": 48,
                "source_cases_path": cases_relative, "source_corpus_manifest_path": manifest_relative,
                **selection_binding,
                "selection_rule": {"cases_per_family": 2, "families_per_domain": 4, "family_order": "lexicographic", "domain_order": "frozen"},
                "cases": data_cases, "target_content_reads": 0,
            }
            write_json("experiments/a0x-six-model/a0-selection-manifest.json", selection)

            for name in ("protected-a0-tree.json", "protected-a0r1-tree.json"):
                tree = {
                    "artifact_class": "a0x-protected-tree", "empirical": True, "scientific_status": "exploratory",
                    "evidence_eligible": False, "expert_validated": False, "claim_ids": [],
                    "source_base_commit": "c" * 40, "protected_paths": ["synthetic/non-target.txt"],
                    "entries": [{"entry_kind": "file", "path": "synthetic/non-target.txt", "bytes": 0,
                                 "sha256": "d" * 64, "provenance_manifest": "synthetic/non-target.txt",
                                 "provenance_manifest_sha256": "e" * 64, "verification_phase": "preflight_postflight"}],
                }
                tree["protected_tree_sha256"] = hashlib.sha256(
                    json.dumps(tree, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                write_json(f"experiments/a0x-six-model/{name}", tree)

            (synthetic_root / "src/latent_triz").mkdir(parents=True)
            (synthetic_root / "src/latent_triz/a0x_runner.py").write_text("# synthetic interface marker\n", encoding="utf-8")
            (synthetic_root / "src/latent_triz/cli.py").write_text("a0x-synthetic-verify\n", encoding="utf-8")
            (synthetic_root / "scripts/repository_check.py").write_text("# synthetic\n", encoding="utf-8")
            (synthetic_root / "scripts/a0x_material.py").write_text("# synthetic interface marker\n", encoding="utf-8")
            (synthetic_root / "tests").mkdir()
            test_modules = ("test_a0x_contract_check.py", "test_a0x_runner.py", "test_a0x_material.py")
            for module in test_modules:
                (synthetic_root / "tests" / module).write_text("# synthetic module\n", encoding="utf-8")
            material_targets = []
            target_slugs = {
                "smollm2_360m": "smollm2-360m", "qwen3_0_6b_base": "qwen3-0-6b-base", "gpt2": "gpt2",
                "smollm2_135m": "smollm2-135m", "gpt_neo_125m": "gpt-neo-125m", "qwen2_5_0_5b": "qwen2-5-0-5b",
            }
            for leg, models_for_leg in (("a0", models), ("r1", models)):
                for key, *_rest in models_for_leg:
                    material_targets.extend((
                        f"a0x-material-{leg}-{target_slugs[key]}:",
                        f"\tPYTHONPATH=$(PYTHONPATH) python3 scripts/a0x_material.py --fixed-dossier experiments/a0x-six-model/approval-dossiers/{leg}/{key}.json",
                    ))
            makefile = [*material_targets, "a0x-synthetic-verify:"]
            makefile.extend((
                "\tpython -m unittest tests.test_a0x_contract_check tests.test_a0x_runner tests.test_a0x_material",
                "\tpython -m unittest tests.test_a0x_contract_check tests.test_a0x_runner tests.test_a0x_material",
                "\tpython -m unittest tests.test_a0x_contract_check tests.test_a0x_runner tests.test_a0x_material",
            ))
            (synthetic_root / "Makefile").write_text("\n".join(makefile) + "\n", encoding="utf-8")

            command = (str(PYTHON), "-B", str(checker), "--phase", "synthetic")
            environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
            completed = subprocess.run(command, cwd=synthetic_root, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            self.assertEqual(0, completed.returncode, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual("synthetic_implementation", receipt["phase"])
            self.assertGreater(receipt["schema_count"], 0)
            self.assertEqual(6, receipt["model_card_count"])
            self.assertEqual(12, receipt["fixed_material_target_count"])
            self.assertFalse(receipt["model_loaded"])
            self.assertFalse(receipt["tokenizer_constructed"])
            self.assertEqual(0, receipt["sealed_target_content_reads"])
            self.assertFalse(receipt["ccp_invoked"])

            material_path = synthetic_root / "experiments/a0x-six-model/material-execution-contract.json"
            changed_contract = json.loads(material_path.read_text(encoding="utf-8"))
            changed_contract["offline"]["network"] = True
            material_path.write_text(json.dumps(changed_contract), encoding="utf-8")
            rejected_contract = subprocess.run(command, cwd=synthetic_root, env=environment, stdin=subprocess.DEVNULL,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            self.assertEqual(1, rejected_contract.returncode)
            self.assertEqual("", rejected_contract.stdout)
            self.assertIn("A0X material contract fails its schema", rejected_contract.stderr)

            material_path.write_text(json.dumps(material_contract, sort_keys=True), encoding="utf-8")
            selection_path = synthetic_root / "experiments/a0x-six-model/a0-selection-manifest.json"
            changed_selection = json.loads(selection_path.read_text(encoding="utf-8"))
            changed_selection["target_content_reads"] = 1
            selection_path.write_text(json.dumps(changed_selection), encoding="utf-8")
            rejected_selection = subprocess.run(command, cwd=synthetic_root, env=environment, stdin=subprocess.DEVNULL,
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            self.assertEqual(1, rejected_selection.returncode)
            self.assertEqual("", rejected_selection.stdout)
            self.assertIn("A0X selection manifest fails its schema", rejected_selection.stderr)

    def test_canonical_v2_operator_refuses_source_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(head="0" * 40)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_SOURCE_IDENTITY_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_authorization_hash_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(authorization_sha256="0" * 64)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_AUTHORIZATION_IDENTITY_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_authorization_id_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(document_authorization_id="other-auth")
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_AUTHORIZATION_BINDING_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_rehashed_authorization_tree_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(document_tree="f" * 40)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_AUTHORIZATION_BINDING_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_rehashed_authorization_model_revision_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(document_revision="0" * 40)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_AUTHORIZATION_BINDING_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_python_hash_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(expected_python_sha256="0" * 64)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_ledger_hash_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(expected_ledger_sha256="0" * 64)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_LEDGER_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_bootstrap_hash_drift_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(expected_bootstrap_sha256="0" * 64)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_BOOTSTRAP_IDENTITY_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_consumes_one_atomic_attempt_claim_before_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command()
        self.assertEqual(0, completed.returncode, completed.stderr)
        head, tree = fixture.identity()
        claim = (
            fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree
            / "a0/smollm2_360m/p0-v2-test-attempt/attempt-claim.json"
        )
        metadata = claim.lstat()
        self.assertTrue(stat.S_ISREG(metadata.st_mode))
        self.assertEqual(1, metadata.st_nlink)
        payload = json.loads(claim.read_text(encoding="utf-8"))
        self.assertEqual("a0x-vertical-p0-attempt-claim-v2", payload["artifact_class"])
        self.assertFalse(payload["retry_permitted"])
        self.assertEqual("p0-v2-test-auth", payload["authorization_id"])
        receipt = claim.with_name("terminal-receipt.json")
        terminal = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(claim.read_bytes()).hexdigest(), terminal["claim_sha256"])
        self.assertEqual({"head": head, "tree": tree}, terminal["source"])
        self.assertEqual("target_free_p0_completed", terminal["frontier"])
        self.assertEqual("p0-v2-test-auth", terminal["authorization"]["id"])

    def test_canonical_v2_operator_refuses_reused_attempt_before_import(self) -> None:
        fixture = self.fixture()
        first = fixture.v2_command()
        self.assertEqual(0, first.returncode, first.stderr)
        head, tree = fixture.identity()
        shutil.rmtree(fixture.root / f".a0x-runtime/p0/v2/{head}/{tree}/a0/smollm2_360m")
        fixture.import_marker.unlink(missing_ok=True)
        second = fixture.v2_command()
        self.assertEqual(2, second.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_ATTEMPT_ALREADY_CONSUMED", second.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_occupied_output_before_consuming_attempt(self) -> None:
        fixture = self.fixture()
        head, tree = fixture.identity()
        output = fixture.root / f".a0x-runtime/p0/v2/{head}/{tree}/a0/smollm2_360m"
        output.mkdir(parents=True)
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_OUTPUT_EXISTS", completed.stderr)
        claim = (
            fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree
            / "a0/smollm2_360m/p0-v2-test-attempt/attempt-claim.json"
        )
        self.assertFalse(claim.exists())
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_dirty_checkout_before_consuming_attempt(self) -> None:
        fixture = self.fixture()
        (fixture.root / fixture.paths[0]).write_text("uncommitted drift\n", encoding="utf-8")
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_CHECKOUT_DIRTY", completed.stderr)
        head, tree = fixture.identity()
        claim = (
            fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree
            / "a0/smollm2_360m/p0-v2-test-attempt/attempt-claim.json"
        )
        self.assertFalse(claim.exists())
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_operator_refuses_ignored_bytecode_before_consuming_attempt(self) -> None:
        fixture = self.fixture()
        fixture.add_conflicting_bytecode()
        self.assertEqual("", _git(fixture.root, "status", "--porcelain"))
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_BYTECODE_PRESENT", completed.stderr)
        self.assertFalse(fixture.malicious_marker.exists())
        self.assertFalse(fixture.import_marker.exists())

    def test_canonical_v2_preexec_refuses_replaced_operator_before_replacement_executes(self) -> None:
        fixture = self.fixture()
        operator = fixture.root / V2_SCRIPT_RELATIVE
        expected = _sha256(operator)
        operator.write_text(
            f"from pathlib import Path\nPath({str(fixture.bootstrap_replacement_marker)!r}).write_text('executed')\n",
            encoding="utf-8",
        )
        completed = fixture.v2_command(target_sha256=expected)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_PREEXEC_IDENTITY_MISMATCH", completed.stderr)
        self.assertFalse(fixture.bootstrap_replacement_marker.exists())

    def test_canonical_v2_operator_refuses_direct_target_bypass_before_claim_or_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(direct_target=True)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_PREEXEC_HANDOFF_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())
        head, tree = fixture.identity()
        claim = fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree
        self.assertFalse(claim.exists())

    def test_canonical_v2_operator_refuses_missing_bytecode_flag_before_claim_or_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.v2_command(omit_bytecode=True)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_PYTHON_IDENTITY_MISMATCH", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())
        head, tree = fixture.identity()
        self.assertFalse((fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree).exists())
        self.assertFalse((fixture.root / "src/latent_triz/__pycache__").exists())

    def test_canonical_v2_operator_preserves_terminal_receipt_after_claimed_construction_failure(self) -> None:
        fixture = self.fixture(construction_failure=True)
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE", completed.stderr)
        head, tree = fixture.identity()
        receipt = fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree / "a0/smollm2_360m/p0-v2-test-attempt/terminal-receipt.json"
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual("claimed_prepublication_failure", payload["terminal_class"])
        self.assertEqual("prepublication", payload["frontier"])
        self.assertEqual("synthetic construction failure", payload["error_code"])

    def test_canonical_v2_claim_fsync_failure_is_consumed_and_retained(self) -> None:
        fixture = self.fixture()
        head, tree = fixture.identity()
        module = _load_v2_module()
        arguments = argparse.Namespace(
            expected_head=head, expected_tree=tree, attempt_id="claim-fsync-failure",
            authorization_id="p0-v2-test-auth", authorization_document_sha256="d" * 64,
            expected_python_sha256="e" * 64, expected_ledger_sha256="f" * 64,
            expected_preexec_sha256="a" * 64,
        )
        bootstrap = {"path": V2_SCRIPT_RELATIVE.as_posix(), "sha256": "b" * 64, "device": 1, "inode": 2, "bytes": 3}
        with mock.patch.object(module.os, "fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaises(module._ConsumedClaimFailure) as raised:
                module._reserve_attempt_claim(fixture.root, arguments, bootstrap)
        claim = fixture.root / raised.exception.claim_relative
        self.assertTrue(claim.is_file())
        self.assertEqual(1, claim.stat().st_nlink)

    def test_canonical_v2_operator_preserves_postpublication_ownership_failure(self) -> None:
        fixture = self.fixture(publication_failure=True)
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        head, tree = fixture.identity()
        receipt = fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree / "a0/smollm2_360m/p0-v2-test-attempt/terminal-receipt.json"
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual("claimed_publication_failure", payload["terminal_class"])
        self.assertEqual("post_publication", payload["frontier"])
        self.assertEqual("synthetic publication ownership lost", payload["error_code"])

    def test_canonical_v2_operator_preserves_terminal_receipt_after_claimed_generator_failure(self) -> None:
        fixture = self.fixture(generator_failure=True)
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE", completed.stderr)
        head, tree = fixture.identity()
        receipt = (
            fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree
            / "a0/smollm2_360m/p0-v2-test-attempt/terminal-receipt.json"
        )
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual("claimed_prepublication_failure", payload["terminal_class"])
        self.assertEqual("prepublication", payload["frontier"])
        self.assertFalse(payload["retry_permitted"])
        self.assertTrue(payload["recovery_required"])
        self.assertEqual("synthetic generator failure", payload["error_code"])

    def test_canonical_v2_operator_preserves_terminal_receipt_after_postpublication_reload_failure(self) -> None:
        fixture = self.fixture(reload_failure=True)
        completed = fixture.v2_command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_V2_CLAIMED_TERMINAL_FAILURE", completed.stderr)
        head, tree = fixture.identity()
        receipt = (
            fixture.root / ".a0x-runtime/attempts/p0/v2" / head / tree
            / "a0/smollm2_360m/p0-v2-test-attempt/terminal-receipt.json"
        )
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual("claimed_publication_failure", payload["terminal_class"])

    def test_replaced_bootstrap_is_rejected_before_any_replacement_byte_executes(self) -> None:
        fixture = self.fixture()
        expected_sha256 = _sha256(fixture.root / SCRIPT_RELATIVE)
        (fixture.root / SCRIPT_RELATIVE).write_text(
            textwrap.dedent(
                f"""\
                from pathlib import Path
                Path({str(fixture.bootstrap_replacement_marker)!r}).write_text(
                    "executed", encoding="utf-8"
                )
                """
            ),
            encoding="utf-8",
        )
        _git(fixture.root, "update-index", "--assume-unchanged", SCRIPT_RELATIVE.as_posix())
        self.assertEqual("", _git(fixture.root, "status", "--porcelain"))

        completed = fixture.command(bootstrap_sha256=expected_sha256)

        self.assertEqual(2, completed.returncode)
        self.assertIn(
            "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH", completed.stderr,
        )
        self.assertFalse(fixture.bootstrap_replacement_marker.exists())

    def test_cleanup_failure_preserves_published_receipt_and_marks_uncertainty(self) -> None:
        fixture = self.fixture(cleanup_failure=True)

        completed = fixture.command(
            bootstrap_sha256=_sha256(fixture.root / SCRIPT_RELATIVE),
        )

        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_PRIVATE_CLEANUP_UNCERTAIN", completed.stderr)
        self.assertTrue(completed.stdout)
        receipt = json.loads(completed.stdout)
        terminal = receipt["p0_authorization_preflight"]["terminal"]
        self.assertEqual("published", terminal["package_publication"])
        self.assertEqual("uncertain", terminal["private_cleanup"])
        self.assertFalse(terminal["retry_permitted"])
        self.assertEqual(
            "shutil.rmtree", terminal["private_cleanup_error"]["operation"],
        )
        self.assertEqual(
            "symlink",
            terminal["private_cleanup_error"]["observed_object"]["object_type"],
        )
        cleanup_path = Path(terminal["private_cleanup_path"])
        cleanup_target = cleanup_path.resolve()
        cleanup_path.unlink()
        shutil.rmtree(cleanup_target)

    def test_authorities_bind_one_full_preexec_through_cleanup_trust_window(self) -> None:
        required = (
            "before pre-execution Python/bootstrap verification and process launch "
            "through terminal receipt emission and private-bootstrap cleanup"
        )
        paths = (
            ROOT / "docs/A0X_VERTICAL_SLICE.md",
            ROOT / REVIEW_RELATIVE,
            ROOT / "artifacts/checkpoints/A0X_VERTICAL_SLICE_RESTART_2026-09-02.md",
        )
        for path in paths:
            with self.subTest(path=path):
                normalized = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
                self.assertIn(required, normalized)

    def test_authorization_commands_embed_the_exact_preexec_source(self) -> None:
        prefix = "python3.13 -I -S -B -c '\n"
        suffix = "\n' /Users/marco1/.codex/worktrees/"
        expected_sha256 = hashlib.sha256(PREEXEC_SOURCE.encode("utf-8")).hexdigest()
        for path in (
            ROOT / REVIEW_RELATIVE,
            ROOT / "artifacts/checkpoints/A0X_VERTICAL_SLICE_RESTART_2026-09-02.md",
        ):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                embedded = text.split(prefix, 1)[1].split(suffix, 1)[0] + "\n"
                self.assertEqual(PREEXEC_SOURCE, embedded)
                self.assertIn(f"--expected-preexec-sha256 {expected_sha256}", text)

    def test_wrong_head_or_tree_refuses_before_repository_import(self) -> None:
        fixture = self.fixture()
        head, tree = fixture.identity()
        for wrong_head, wrong_tree in (("0" * 40, tree), (head, "f" * 40)):
            with self.subTest(head=wrong_head, tree=wrong_tree):
                fixture.import_marker.unlink(missing_ok=True)
                completed = fixture.command(head=wrong_head, tree=wrong_tree)
                self.assertEqual(2, completed.returncode)
                self.assertIn("A0X_VERTICAL_P0_SOURCE_IDENTITY_MISMATCH", completed.stderr)
                self.assertFalse(fixture.import_marker.exists())
                self.assertFalse((fixture.root / "experiments/a0x-six-model/vertical-slices").exists())

    def test_unisolated_runtime_refuses_before_repository_import(self) -> None:
        fixture = self.fixture()
        completed = fixture.command(isolated=False)
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_RUNTIME_UNISOLATED", completed.stderr)
        self.assertFalse(fixture.import_marker.exists())

    def test_path_shadow_cannot_replace_absolute_isolated_python(self) -> None:
        fixture = self.fixture()
        shadow = Path(self.temporary.name) / "shadow"
        shadow.mkdir()
        shadow_python = shadow / "python3"
        shadow_python.write_text(
            f"#!/bin/sh\nprintf executed > {fixture.shadow_marker}\nexit 99\n",
            encoding="utf-8",
        )
        shadow_python.chmod(0o755)
        completed = fixture.command(environment={"PATH": f"{shadow}:/usr/bin:/bin"})
        self.assertEqual(0, completed.returncode, completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(str(PYTHON), receipt["p0_authorization_preflight"]["python"]["path"])
        self.assertEqual(_sha256(PYTHON), receipt["p0_authorization_preflight"]["python"]["sha256"])
        self.assertFalse(fixture.shadow_marker.exists())
        self.assertTrue(fixture.import_marker.exists())

    def test_valid_conflicting_ignored_bytecode_refuses_before_source_import(self) -> None:
        fixture = self.fixture()
        fixture.add_conflicting_bytecode()
        self.assertEqual("", _git(fixture.root, "status", "--porcelain"))
        completed = fixture.command()
        self.assertEqual(2, completed.returncode)
        self.assertIn("A0X_VERTICAL_P0_BYTECODE_PRESENT", completed.stderr)
        self.assertFalse(fixture.malicious_marker.exists())
        self.assertFalse(fixture.import_marker.exists())

    def test_ledger_cardinality_type_link_and_digest_mismatch_refuse_before_import(self) -> None:
        mutations = ("cardinality", "symlink", "hardlink", "digest")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(
                prefix=f"a0x-p0-{mutation}-",
            ) as directory:
                fixture = SyntheticRepository(Path(directory))
                original_digest = fixture.ledger_digest()
                selected = fixture.root / fixture.paths[0]
                if mutation == "cardinality":
                    fixture._write_ledger_document(fixture._current_lines()[:-1])
                    head, tree = fixture.commit_all("remove ledger member")
                    completed = fixture.command(head=head, tree=tree, digest=original_digest)
                elif mutation == "symlink":
                    replacement = fixture.root / "replacement.txt"
                    replacement.write_bytes(selected.read_bytes())
                    selected.unlink()
                    selected.symlink_to(os.path.relpath(replacement, selected.parent))
                    head, tree = fixture.commit_all("replace ledger member with symlink")
                    completed = fixture.command(head=head, tree=tree, digest=original_digest)
                elif mutation == "hardlink":
                    duplicate = fixture.root / fixture.paths[1]
                    duplicate.write_bytes(selected.read_bytes())
                    fixture._write_ledger_document(fixture._current_lines())
                    fixture.commit_all("align ledger member bytes")
                    selected.unlink()
                    os.link(duplicate, selected)
                    self.assertEqual("", _git(fixture.root, "status", "--porcelain"))
                    completed = fixture.command(digest=fixture.ledger_digest())
                else:
                    selected.write_bytes(b"changed tracked input\n")
                    head, tree = fixture.commit_all("change ledger input")
                    completed = fixture.command(head=head, tree=tree, digest=original_digest)
                self.assertEqual(2, completed.returncode)
                self.assertIn("A0X_VERTICAL_P0_LEDGER_MISMATCH", completed.stderr)
                self.assertFalse(fixture.import_marker.exists())

    def test_success_receipt_binds_source_launcher_python_and_ledger(self) -> None:
        fixture = self.fixture()
        head, tree = fixture.identity()
        completed = fixture.command()
        self.assertEqual(0, completed.returncode, completed.stderr)
        receipt = json.loads(completed.stdout)
        preflight = receipt["p0_authorization_preflight"]
        self.assertEqual(head, preflight["source"]["head"])
        self.assertEqual(tree, preflight["source"]["tree"])
        self.assertEqual(137, preflight["input_ledger"]["count"])
        self.assertEqual(fixture.ledger_digest(), preflight["input_ledger"]["sha256"])
        self.assertEqual(SCRIPT_RELATIVE.as_posix(), preflight["launcher"]["path"])
        self.assertEqual(
            _sha256(fixture.root / SCRIPT_RELATIVE), preflight["launcher"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(PREEXEC_SOURCE.encode("utf-8")).hexdigest(),
            preflight["preexec_verifier"]["source_sha256"],
        )
        self.assertEqual(
            preflight["launcher"]["bytes"],
            preflight["preexec_verifier"]["bootstrap_descriptor"]["bytes"],
        )
        self.assertEqual("published", preflight["terminal"]["package_publication"])
        self.assertEqual("complete", preflight["terminal"]["private_cleanup"])
        self.assertFalse(preflight["terminal"]["retry_permitted"])
        self.assertEqual("a0", receipt["pair"]["leg"])
        self.assertEqual("smollm2_360m", receipt["pair"]["model_key"])


if __name__ == "__main__":
    unittest.main()
