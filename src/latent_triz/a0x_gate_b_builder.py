"""Fail-closed offline prerequisite builder for A0X Gate B.

The builder creates neither a Gate B verification receipt nor any scientific
artifact. It prepares only an exact Python environment and an exact model-card
snapshot for a later, separately authorized runtime-bundle preparation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .a0x_apfs import clone_regular_file
from .a0x_wheelhouse import A0XWheelhouseError, verify_offline_wheelhouse


PROFILE = "a0x-gate-b-offline-build-v1"
EXPECTED_DISTRIBUTION_COUNT = 39
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]+$")
_PYTHON_PROBE = (
    "import json,sys;"
    "print(json.dumps({'python_major_minor':list(sys.version_info[:2]),"
    "'python_version':'.'.join(str(x) for x in sys.version_info[:3])},"
    "sort_keys=True,separators=(',',':')))"
)
_DISTRIBUTION_PROBE = (
    "import importlib.metadata as m,importlib.util as u,json,re,sys;"
    "ds=sorted((re.sub(r'[-_.]+','-',d.metadata['Name']).lower(),d.version) "
    "for d in m.distributions());"
    "print(json.dumps({'distributions':ds,'pip_importable':u.find_spec('pip') is not None,"
    "'python_major_minor':list(sys.version_info[:2]),"
    "'python_version':'.'.join(str(x) for x in sys.version_info[:3]),"
    "'sys_executable':sys.executable},sort_keys=True,separators=(',',':')))"
)

Runner = Callable[[Sequence[str], Path], tuple[int, bytes, bytes]]
CloneFile = Callable[..., Mapping[str, object]]
SourceStateProbe = Callable[[Path], tuple[str, bool]]


class A0XGateBBuilderError(RuntimeError):
    """The offline Gate B prerequisite build could not be proven exact."""


@dataclass(frozen=True)
class GateBBuildRequest:
    """Exact operator-selected inputs for one future prerequisite build."""

    source_head: str
    attempt_id: str
    wheelhouse_directory: Path
    wheelhouse_manifest: Path
    wheelhouse_manifest_sha256: str
    base_python: Path
    base_python_sha256: str
    base_python_version: str
    bootstrap_pip_version: str
    model_card: str
    model_card_sha256: str
    model_source_root: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise A0XGateBBuilderError("builder value is not canonical JSON") from error


def _independent_regular(path: Path, label: str, *, executable: bool = False) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise A0XGateBBuilderError(f"{label} is unavailable") from error
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_nlink != 1:
        raise A0XGateBBuilderError(f"{label} is not an independent regular file")
    if executable and not os.access(path, os.X_OK):
        raise A0XGateBBuilderError(f"{label} is not executable")
    return metadata


def _absolute_directory(path: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute() or candidate.is_symlink() or not candidate.is_dir():
        raise A0XGateBBuilderError(f"{label} is unavailable")
    try:
        return candidate.resolve(strict=True)
    except OSError as error:
        raise A0XGateBBuilderError(f"{label} is unavailable") from error


def _repository_file(root: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise A0XGateBBuilderError(f"{label} path is invalid")
    path = root / candidate
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError as error:
        raise A0XGateBBuilderError(f"{label} is unavailable") from error
    if not resolved_parent.is_relative_to(root):
        raise A0XGateBBuilderError(f"{label} escapes the repository")
    _independent_regular(path, label)
    return path


def _default_runner(argv: Sequence[str], cwd: Path) -> tuple[int, bytes, bytes]:
    try:
        result = subprocess.run(
            list(argv), cwd=str(cwd), shell=False, check=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise A0XGateBBuilderError("builder child process could not start") from error
    return result.returncode, result.stdout, result.stderr


def _default_source_state(root: Path) -> tuple[str, bool]:
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC"}

    def probe(arguments: Sequence[str]) -> bytes:
        try:
            result = subprocess.run(
                ["/usr/bin/git", *arguments], cwd=str(root), shell=False, check=False,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=environment, timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise A0XGateBBuilderError("source-state probe refused") from error
        if result.returncode != 0:
            raise A0XGateBBuilderError("source-state probe refused")
        return result.stdout

    try:
        head = probe(("rev-parse", "HEAD")).decode("ascii").strip()
        status = probe(("status", "--porcelain", "--untracked-files=all"))
    except UnicodeDecodeError as error:
        raise A0XGateBBuilderError("source-state probe returned invalid text") from error
    return head, status == b""


def _validate_source_state(root: Path, expected_head: str, probe: SourceStateProbe) -> None:
    try:
        state = probe(root)
    except A0XGateBBuilderError:
        raise
    except Exception as error:
        raise A0XGateBBuilderError("source-state probe refused") from error
    if state != (expected_head, True):
        raise A0XGateBBuilderError("source state differs from the clean exact build request")


def _run_checked(runner: Runner, argv: Sequence[str], cwd: Path, label: str) -> bytes:
    try:
        returncode, stdout, _stderr = runner(tuple(str(item) for item in argv), cwd)
    except A0XGateBBuilderError:
        raise
    except Exception as error:
        raise A0XGateBBuilderError(f"{label} probe refused") from error
    if returncode != 0 or not isinstance(stdout, bytes):
        raise A0XGateBBuilderError(f"{label} probe refused")
    return stdout


def _normalize_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _probe_python(
    python: Path,
    expected_version: str,
    expected_pip_version: str,
    root: Path,
    runner: Runner,
) -> None:
    raw = _run_checked(runner, (str(python), "-I", "-c", _PYTHON_PROBE), root, "Python")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise A0XGateBBuilderError("Python probe returned invalid JSON") from error
    if value != {"python_major_minor": [3, 11], "python_version": expected_version}:
        raise A0XGateBBuilderError("Python version differs from the build request")
    pip_raw = _run_checked(
        runner, (str(python), "-I", "-m", "pip", "--version"), root, "bootstrap pip",
    )
    try:
        pip_text = pip_raw.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise A0XGateBBuilderError("bootstrap pip probe returned invalid text") from error
    match = re.fullmatch(r"pip ([^ ]+) .+\(python 3\.11\)", pip_text)
    if match is None or match.group(1) != expected_pip_version:
        raise A0XGateBBuilderError("bootstrap pip version differs from the build request")


def _manifest_records(manifest_raw: bytes) -> tuple[list[dict[str, Any]], bytes]:
    try:
        manifest = json.loads(manifest_raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise A0XGateBBuilderError("wheelhouse manifest is invalid") from error
    wheels = manifest.get("wheels") if isinstance(manifest, dict) else None
    if not isinstance(wheels, list) or len(wheels) != EXPECTED_DISTRIBUTION_COUNT:
        raise A0XGateBBuilderError("wheelhouse must contain exactly 39 distributions")
    records: list[dict[str, Any]] = []
    requirements: list[str] = []
    for item in wheels:
        if not isinstance(item, dict):
            raise A0XGateBBuilderError("wheelhouse distribution record is invalid")
        distribution = item.get("distribution")
        version = item.get("version")
        digest = item.get("sha256")
        if (
            not isinstance(distribution, str) or not distribution
            or not isinstance(version, str) or not version
            or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
        ):
            raise A0XGateBBuilderError("wheelhouse distribution record is invalid")
        records.append({"distribution": distribution, "version": version, "sha256": digest})
        requirements.append(f"{distribution}=={version} --hash=sha256:{digest}\n")
    return records, "".join(requirements).encode("utf-8")


def _model_card(root: Path, request: GateBBuildRequest) -> tuple[Path, bytes, dict[str, Any]]:
    path = _repository_file(root, request.model_card, "model card")
    raw = path.read_bytes()
    if _sha256(path) != request.model_card_sha256:
        raise A0XGateBBuilderError("model card bytes differ from the build request")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise A0XGateBBuilderError("model card is invalid JSON") from error
    if not isinstance(value, dict) or _canonical(value) != raw:
        raise A0XGateBBuilderError("model card is not canonical JSON")
    runtime_root = value.get("runtime_root")
    runtime_files = value.get("runtime_files")
    if not isinstance(runtime_root, str) or not runtime_root or not isinstance(runtime_files, list) or not runtime_files:
        raise A0XGateBBuilderError("model card runtime declaration is invalid")
    return path, raw, value


def _runtime_file_records(source_root: Path, card: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    expected: set[str] = set()
    for item in card["runtime_files"]:
        if not isinstance(item, dict) or set(item) != {"path", "size_bytes", "sha256"}:
            raise A0XGateBBuilderError("model-card runtime record is invalid")
        relative = item.get("path")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        relative_path = Path(relative) if isinstance(relative, str) else Path()
        if (
            not isinstance(relative, str) or not relative or relative_path.is_absolute()
            or ".." in relative_path.parts or relative_path.as_posix() != relative
            or not isinstance(size, int) or isinstance(size, bool) or size < 0
            or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
            or relative in expected
        ):
            raise A0XGateBBuilderError("model-card runtime record is invalid")
        expected.add(relative)
        source = source_root / relative_path
        metadata = _independent_regular(source, "model snapshot source")
        if metadata.st_size != size or _sha256(source) != digest:
            raise A0XGateBBuilderError("model snapshot bytes differ from the model card")
        records.append({"path": relative, "size_bytes": size, "sha256": digest})
    actual: set[str] = set()
    for path in source_root.rglob("*"):
        relative = path.relative_to(source_root).as_posix()
        metadata = path.lstat()
        if path.is_symlink():
            raise A0XGateBBuilderError("model snapshot contains a symlink")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise A0XGateBBuilderError("model snapshot contains a non-independent file")
        actual.add(relative)
    if actual != expected:
        raise A0XGateBBuilderError("model snapshot differs from the model-card allowlist")
    return records


def _runtime_destination(root: Path, runtime_root: Any) -> Path:
    if not isinstance(runtime_root, str):
        raise A0XGateBBuilderError("model runtime root is invalid")
    relative = Path(runtime_root)
    if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != runtime_root:
        raise A0XGateBBuilderError("model runtime root is invalid")
    destination = root / relative
    existing = destination.parent
    while not os.path.lexists(existing):
        if existing == existing.parent:
            raise A0XGateBBuilderError("model runtime destination parent is unavailable")
        existing = existing.parent
    if existing.is_symlink() or not existing.is_dir():
        raise A0XGateBBuilderError("model runtime destination parent is unavailable")
    try:
        resolved_existing = existing.resolve(strict=True)
    except OSError as error:
        raise A0XGateBBuilderError("model runtime destination parent is unavailable") from error
    if not resolved_existing.is_relative_to(root):
        raise A0XGateBBuilderError("model runtime destination escapes the repository")
    if os.path.lexists(destination):
        raise A0XGateBBuilderError("model runtime destination is occupied")
    return destination


def plan_gate_b_runtime(
    root: Path,
    request: GateBBuildRequest,
    *,
    runner: Runner = _default_runner,
    source_state_probe: SourceStateProbe = _default_source_state,
) -> dict[str, Any]:
    """Validate exact inputs and return a no-write shell-free build plan."""
    repository = _absolute_directory(Path(root), "repository")
    if _REVISION.fullmatch(request.source_head) is None:
        raise A0XGateBBuilderError("source HEAD is invalid")
    if _IDENTIFIER.fullmatch(request.attempt_id) is None:
        raise A0XGateBBuilderError("attempt ID is invalid")
    for digest, label in (
        (request.wheelhouse_manifest_sha256, "wheelhouse manifest SHA-256"),
        (request.base_python_sha256, "base Python SHA-256"),
        (request.model_card_sha256, "model card SHA-256"),
    ):
        if _SHA256.fullmatch(digest) is None:
            raise A0XGateBBuilderError(f"{label} is invalid")
    _validate_source_state(repository, request.source_head, source_state_probe)

    manifest_path = Path(request.wheelhouse_manifest)
    _independent_regular(manifest_path, "wheelhouse manifest")
    manifest_raw = manifest_path.read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != request.wheelhouse_manifest_sha256:
        raise A0XGateBBuilderError("wheelhouse manifest bytes differ from the build request")
    records, requirements_raw = _manifest_records(manifest_raw)
    wheelhouse = _absolute_directory(Path(request.wheelhouse_directory), "wheelhouse")
    try:
        wheelhouse_evidence = verify_offline_wheelhouse(wheelhouse, manifest_raw)
    except A0XWheelhouseError as error:
        raise A0XGateBBuilderError("wheelhouse verification refused") from error

    python = Path(request.base_python)
    _independent_regular(python, "base Python", executable=True)
    if _sha256(python) != request.base_python_sha256:
        raise A0XGateBBuilderError("base Python bytes differ from the build request")
    _probe_python(
        python, request.base_python_version, request.bootstrap_pip_version, repository, runner,
    )

    _card_path, card_raw, card = _model_card(repository, request)
    model_source = _absolute_directory(Path(request.model_source_root), "model snapshot source")
    runtime_records = _runtime_file_records(model_source, card)
    model_destination = _runtime_destination(repository, card.get("runtime_root"))

    attempt_root = repository / ".a0x-runtime/gate-b-builds" / request.attempt_id
    if os.path.lexists(attempt_root):
        raise A0XGateBBuilderError("attempt destination is occupied")
    environment = attempt_root / "environment"
    environment_python = environment / "bin/python3"
    requirements = attempt_root / "requirements-wheelhouse.txt"
    receipt = attempt_root / "build-receipt.json"
    commands = {
        "venv": [str(python), "-I", "-m", "venv", "--copies", str(environment)],
        "install": [
            str(environment_python), "-I", "-m", "pip", "--isolated",
            "--disable-pip-version-check", "install", "--no-index", "--find-links",
            str(wheelhouse), "--require-hashes", "--no-deps", "-r", str(requirements),
        ],
        "remove_bootstrap_pip": [
            str(environment_python), "-I", "-m", "pip", "--isolated",
            "--disable-pip-version-check", "uninstall", "--yes", "pip",
        ],
    }
    return {
        "profile": PROFILE,
        "status": "planned",
        "source_head": request.source_head,
        "attempt_id": request.attempt_id,
        "wheelhouse": {
            **wheelhouse_evidence,
            "directory": str(wheelhouse),
            "manifest_path": str(manifest_path),
            "distribution_count": len(records),
            "distributions": records,
        },
        "python": {
            "base_path": str(python),
            "base_sha256": request.base_python_sha256,
            "version": request.base_python_version,
            "bootstrap_pip_version": request.bootstrap_pip_version,
            "environment_path": str(environment),
            "environment_python_path": str(environment_python),
        },
        "model": {
            "card_path": request.model_card,
            "card_sha256": hashlib.sha256(card_raw).hexdigest(),
            "source_root": str(model_source),
            "destination_root": str(model_destination),
            "runtime_files": runtime_records,
        },
        "attempt_root": str(attempt_root),
        "requirements_path": str(requirements),
        "requirements_sha256": hashlib.sha256(requirements_raw).hexdigest(),
        "requirements_bytes": requirements_raw.decode("utf-8"),
        "receipt_path": str(receipt),
        "commands": commands,
    }


def _mkdirs_below(root: Path, destination: Path) -> None:
    try:
        relative = destination.relative_to(root)
    except ValueError as error:
        raise A0XGateBBuilderError("builder output escapes the repository") from error
    current = root
    for part in relative.parts:
        current = current / part
        if os.path.lexists(current):
            if current.is_symlink() or not current.is_dir():
                raise A0XGateBBuilderError("builder output path is occupied")
            continue
        try:
            current.mkdir()
        except OSError as error:
            raise A0XGateBBuilderError("builder output directory creation refused") from error


def _verify_existing_directory_below(root: Path, destination: Path, label: str) -> None:
    try:
        relative = destination.relative_to(root)
    except ValueError as error:
        raise A0XGateBBuilderError(f"{label} escapes the repository") from error
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except OSError as error:
            raise A0XGateBBuilderError(f"{label} is unavailable") from error
        if current.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            raise A0XGateBBuilderError(f"{label} contains a symlink or non-directory")


def _exclusive_write(path: Path, raw: bytes, label: str) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        raise A0XGateBBuilderError(f"{label} exclusive write refused") from error


def _validate_environment_probe(raw: bytes, plan: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError) as error:
        raise A0XGateBBuilderError("installed-distribution probe returned invalid JSON") from error
    if not isinstance(value, dict) or set(value) != {
        "distributions", "pip_importable", "python_major_minor", "python_version", "sys_executable",
    }:
        raise A0XGateBBuilderError("installed-distribution probe shape is invalid")
    distributions = value.get("distributions")
    if not isinstance(distributions, list):
        raise A0XGateBBuilderError("installed distribution set is invalid")
    normalized: dict[str, str] = {}
    for item in distributions:
        if (
            not isinstance(item, list) or len(item) != 2
            or not isinstance(item[0], str) or not isinstance(item[1], str)
            or item[0] in normalized
        ):
            raise A0XGateBBuilderError("installed distribution set is invalid")
        normalized[item[0]] = item[1]
    expected = {
        _normalize_distribution(item["distribution"]): item["version"]
        for item in plan["wheelhouse"]["distributions"]
    }
    if normalized != expected or len(distributions) != EXPECTED_DISTRIBUTION_COUNT:
        raise A0XGateBBuilderError("installed distribution set differs from the 39 locked distributions")
    if value.get("pip_importable") is not False:
        raise A0XGateBBuilderError("bootstrap pip remains in the final environment")
    python = plan["python"]
    if (
        value.get("python_major_minor") != [3, 11]
        or value.get("python_version") != python["version"]
        or value.get("sys_executable") != python["environment_python_path"]
    ):
        raise A0XGateBBuilderError("built Python identity differs from the plan")
    return {**value, "distributions": normalized}


def _probe_environment(plan: Mapping[str, Any], root: Path, runner: Runner) -> dict[str, Any]:
    raw = _run_checked(
        runner,
        (plan["python"]["environment_python_path"], "-I", "-c", _DISTRIBUTION_PROBE),
        root,
        "installed distribution",
    )
    return _validate_environment_probe(raw, plan)


def _revalidate_build_inputs(root: Path, request: GateBBuildRequest, plan: Mapping[str, Any]) -> None:
    manifest = Path(request.wheelhouse_manifest)
    _independent_regular(manifest, "wheelhouse manifest")
    manifest_raw = manifest.read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != request.wheelhouse_manifest_sha256:
        raise A0XGateBBuilderError("wheelhouse manifest drifted during the build")
    try:
        evidence = verify_offline_wheelhouse(Path(request.wheelhouse_directory), manifest_raw)
    except A0XWheelhouseError as error:
        raise A0XGateBBuilderError("wheelhouse drifted during the build") from error
    if evidence["manifest_sha256"] != plan["wheelhouse"]["manifest_sha256"]:
        raise A0XGateBBuilderError("wheelhouse drifted during the build")
    python = Path(request.base_python)
    _independent_regular(python, "base Python", executable=True)
    if _sha256(python) != request.base_python_sha256:
        raise A0XGateBBuilderError("base Python drifted during the build")
    _path, raw, card = _model_card(root, request)
    if hashlib.sha256(raw).hexdigest() != plan["model"]["card_sha256"]:
        raise A0XGateBBuilderError("model card drifted during the build")
    source_root = _absolute_directory(Path(request.model_source_root), "model snapshot source")
    if str(source_root) != plan["model"]["source_root"]:
        raise A0XGateBBuilderError("model snapshot source drifted during the build")
    records = _runtime_file_records(source_root, card)
    if records != plan["model"]["runtime_files"]:
        raise A0XGateBBuilderError("model snapshot drifted during the build")


def _verify_materialized_model(root: Path, plan: Mapping[str, Any]) -> None:
    destination_root = Path(plan["model"]["destination_root"])
    _verify_existing_directory_below(root, destination_root, "materialized model output path")
    expected = {item["path"]: item for item in plan["model"]["runtime_files"]}
    actual: set[str] = set()
    for path in destination_root.rglob("*"):
        relative = path.relative_to(destination_root).as_posix()
        metadata = path.lstat()
        if path.is_symlink():
            raise A0XGateBBuilderError("materialized model contains a symlink")
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise A0XGateBBuilderError("materialized model contains a non-independent file")
        actual.add(relative)
        item = expected.get(relative)
        if item is None or metadata.st_size != item["size_bytes"] or _sha256(path) != item["sha256"]:
            raise A0XGateBBuilderError("materialized model bytes differ from the model card")
    if actual != set(expected):
        raise A0XGateBBuilderError("materialized model differs from the model-card allowlist")


def build_gate_b_runtime(
    root: Path,
    request: GateBBuildRequest,
    *,
    runner: Runner = _default_runner,
    clone_file: CloneFile = clone_regular_file,
    source_state_probe: SourceStateProbe = _default_source_state,
) -> dict[str, Any]:
    """Build one local prerequisite bundle from already verified offline inputs.

    This is a material operation and requires a separate exact authorization.
    It is exposed here for future use but is exercised only with synthetic
    fixtures by the repository tests.
    """
    repository = _absolute_directory(Path(root), "repository")
    plan = plan_gate_b_runtime(
        repository, request, runner=runner, source_state_probe=source_state_probe,
    )
    attempt_root = Path(plan["attempt_root"])
    attempt_parent = attempt_root.parent
    _mkdirs_below(repository, attempt_parent)
    try:
        attempt_root.mkdir()
    except OSError as error:
        raise A0XGateBBuilderError("attempt destination is occupied") from error
    requirements_path = Path(plan["requirements_path"])
    requirements_raw = plan["requirements_bytes"].encode("utf-8")
    _exclusive_write(requirements_path, requirements_raw, "hash-locked requirements")

    _run_checked(runner, plan["commands"]["venv"], repository, "venv --copies")
    environment_python = Path(plan["python"]["environment_python_path"])
    _independent_regular(environment_python, "built Python", executable=True)
    if _sha256(environment_python) != request.base_python_sha256:
        raise A0XGateBBuilderError("venv --copies did not preserve the exact Python bytes")
    _run_checked(runner, plan["commands"]["install"], repository, "offline pip install")
    _run_checked(
        runner, plan["commands"]["remove_bootstrap_pip"], repository, "bootstrap pip removal",
    )
    _verify_existing_directory_below(repository, attempt_root, "attempt output path")
    _verify_existing_directory_below(
        repository, Path(plan["python"]["environment_path"]), "environment output path",
    )
    installed = _probe_environment(plan, repository, runner)

    _revalidate_build_inputs(repository, request, plan)
    model_destination = Path(plan["model"]["destination_root"])
    _mkdirs_below(repository, model_destination.parent)
    try:
        model_destination.mkdir()
    except OSError as error:
        raise A0XGateBBuilderError("model runtime destination is occupied") from error
    clone_evidence: list[dict[str, Any]] = []
    source_root = Path(plan["model"]["source_root"])
    for item in plan["model"]["runtime_files"]:
        source = source_root / item["path"]
        destination = model_destination / item["path"]
        _mkdirs_below(model_destination, destination.parent)
        try:
            evidence = dict(clone_file(
                source,
                destination,
                source_root=source_root,
                destination_root=model_destination,
            ))
        except A0XGateBBuilderError:
            raise
        except Exception as error:
            raise A0XGateBBuilderError("APFS model materialization refused") from error
        if (
            evidence.get("operation") != "clonefile"
            or evidence.get("sha256") != item["sha256"]
            or evidence.get("size_bytes") != item["size_bytes"]
        ):
            raise A0XGateBBuilderError("APFS clone evidence differs from the model card")
        clone_evidence.append({
            "path": item["path"],
            "operation": "clonefile",
            "sha256": item["sha256"],
            "size_bytes": item["size_bytes"],
        })

    _revalidate_build_inputs(repository, request, plan)
    _validate_source_state(repository, request.source_head, source_state_probe)
    _independent_regular(environment_python, "built Python", executable=True)
    if _sha256(environment_python) != request.base_python_sha256:
        raise A0XGateBBuilderError("built Python drifted before receipt sealing")
    installed = _probe_environment(plan, repository, runner)
    _verify_materialized_model(repository, plan)
    _verify_existing_directory_below(repository, attempt_root, "attempt output path")
    _independent_regular(requirements_path, "hash-locked requirements")
    if _sha256(requirements_path) != plan["requirements_sha256"]:
        raise A0XGateBBuilderError("hash-locked requirements drifted before receipt sealing")
    receipt: dict[str, Any] = {
        "profile": PROFILE,
        "status": "built",
        "scientific_evidence": False,
        "source_head": request.source_head,
        "attempt_id": request.attempt_id,
        "wheelhouse": {
            "manifest_sha256": plan["wheelhouse"]["manifest_sha256"],
            "requirements_sha256": plan["requirements_sha256"],
            "distribution_count": len(installed["distributions"]),
            "distributions": installed["distributions"],
        },
        "python": {
            "base_sha256": request.base_python_sha256,
            "version": request.base_python_version,
            "bootstrap_pip_version": request.bootstrap_pip_version,
            "bootstrap_pip_retained": False,
            "environment_path": plan["python"]["environment_path"],
            "executable_path": plan["python"]["environment_python_path"],
            "executable_sha256": _sha256(environment_python),
            "distribution_count": len(installed["distributions"]),
        },
        "model": {
            "card_path": request.model_card,
            "card_sha256": plan["model"]["card_sha256"],
            "destination_root": plan["model"]["destination_root"],
            "runtime_file_count": len(clone_evidence),
            "runtime_files": clone_evidence,
        },
        "commands": plan["commands"],
        "sealed_target_reads": 0,
        "model_loads": 0,
        "tokenizer_constructions": 0,
        "network_accesses": 0,
        "gate_b_documents_written": 0,
        "gate_c_executions": 0,
    }
    receipt_path = Path(plan["receipt_path"])
    receipt_raw = _canonical(receipt)
    _exclusive_write(receipt_path, receipt_raw, "build receipt")
    if receipt_path.read_bytes() != receipt_raw:
        raise A0XGateBBuilderError("build receipt post-write verification failed")
    return receipt


__all__ = [
    "A0XGateBBuilderError",
    "EXPECTED_DISTRIBUTION_COUNT",
    "GateBBuildRequest",
    "PROFILE",
    "build_gate_b_runtime",
    "plan_gate_b_runtime",
]
