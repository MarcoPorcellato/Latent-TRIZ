"""Fail-closed, target-free Hosted Gate A capture transaction library."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import io
import os
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Any, Callable, Mapping
import zipfile

from latent_triz.a0x_hosted_gate_a import A0XHostedGateAError, canonical_json_bytes, parse_manifest_bytes

CAPTURE_INVALID = "A0X_HOSTED_CAPTURE_INVALID"
ARCHIVE_INVALID = "A0X_HOSTED_CAPTURE_ARCHIVE_INVALID"
BINDING_MISMATCH = "A0X_HOSTED_CAPTURE_BINDING_MISMATCH"
OUTPUT_EXISTS = "A0X_HOSTED_CAPTURE_OUTPUT_EXISTS"
PUBLICATION_UNSUPPORTED = "A0X_HOSTED_CAPTURE_PUBLICATION_UNSUPPORTED"
PUBLICATION_FAILED = "A0X_HOSTED_CAPTURE_PUBLICATION_FAILED"
PIN_INVALID = "A0X_HOSTED_CAPTURE_PIN_INVALID"
REPOSITORY = "MarcoPorcellato/Latent-TRIZ"
ARTIFACT_NAME = "a0x-hosted-gate-a-evidence"
MANIFEST_NAME = "a0x-hosted-gate-a-evidence.json"
FINAL_NAMES = ("hosted-gate-a-evidence.json", "hosted-gate-a-attestation.bundle.jsonl", "github-trusted-root.jsonl", "hosted-gate-a-transport.json")
GH_VERSION = "gh version 2.97.0 (2026-07-31)"
GH_SHA256 = "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
MAX_MANIFEST_BYTES, MAX_BUNDLE_BYTES, MAX_TRUSTED_ROOT_BYTES, MAX_TRANSPORT_BYTES, MAX_ARCHIVE_BYTES = 32 * 1024, 1024 * 1024, 2 * 1024 * 1024, 16 * 1024, 8 * 1024 * 1024
_REVISION, _SHA256, _TIMESTAMP = re.compile(r"^[a-f0-9]{40}$"), re.compile(r"^[a-f0-9]{64}$"), re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z$")

class A0XHostedCaptureError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

def _positive(value: object) -> bool:
    return type(value) is int and 1 <= value <= 9_007_199_254_740_991

def _revision(value: object) -> bool:
    return isinstance(value, str) and _REVISION.fullmatch(value) is not None

def _sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None

def _timestamp(value: object) -> bool:
    return isinstance(value, str) and _TIMESTAMP.fullmatch(value) is not None

def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class CaptureRequest:
    repository: str; source_head: str; source_tree: str; run_id: int; run_attempt: int; artifact_id: int; artifact_name: str; archive_sha256: str; archive_size_bytes: int; manifest_sha256: str; expires_at: str; output_root: Path

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CaptureRequest":
        keys = {"repository", "source_head", "source_tree", "run_id", "run_attempt", "artifact_id", "artifact_name", "archive_sha256", "archive_size_bytes", "manifest_sha256", "expires_at", "output_root"}
        if not isinstance(value, Mapping) or set(value) != keys:
            raise A0XHostedCaptureError(CAPTURE_INVALID)
        try:
            result = cls(**{key: (Path(value[key]) if key == "output_root" else value[key]) for key in keys})
        except (TypeError, ValueError) as error:
            raise A0XHostedCaptureError(CAPTURE_INVALID) from error
        result.validate()
        return result

    def validate(self) -> None:
        if not (self.repository == REPOSITORY and _revision(self.source_head) and _revision(self.source_tree) and _positive(self.run_id) and self.run_attempt == 1 and _positive(self.artifact_id) and self.artifact_name == ARTIFACT_NAME and _sha256(self.archive_sha256) and _positive(self.archive_size_bytes) and self.archive_size_bytes <= MAX_ARCHIVE_BYTES and _sha256(self.manifest_sha256) and _timestamp(self.expires_at) and self.output_root.is_absolute()):
            raise A0XHostedCaptureError(CAPTURE_INVALID)

@dataclass(frozen=True)
class CaptureTransport:
    artifact_id: int; run_id: int; run_attempt: int; head_sha: str; archive_digest: str; archive_size_bytes: int; created_at: str; expires_at: str; captured_at: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CaptureTransport":
        keys = {"artifact_id", "run_id", "run_attempt", "head_sha", "archive_digest", "archive_size_bytes", "created_at", "expires_at", "captured_at"}
        if not isinstance(value, Mapping) or set(value) != keys:
            raise A0XHostedCaptureError(CAPTURE_INVALID)
        result = cls(**{key: value[key] for key in keys})
        result.validate()
        return result

    def validate(self) -> None:
        if not (_positive(self.artifact_id) and _positive(self.run_id) and self.run_attempt == 1 and _revision(self.head_sha) and isinstance(self.archive_digest, str) and self.archive_digest.startswith("sha256:") and _sha256(self.archive_digest[7:]) and _positive(self.archive_size_bytes) and self.archive_size_bytes <= MAX_ARCHIVE_BYTES and all(_timestamp(v) for v in (self.created_at, self.expires_at, self.captured_at))):
            raise A0XHostedCaptureError(CAPTURE_INVALID)

    def as_document(self) -> bytes:
        raw = canonical_json_bytes({"artifact_class":"a0x-hosted-gate-a-transport", "transport_profile":"a0x-hosted-gate-a-transport-v1", "repository":REPOSITORY, "artifact_id":self.artifact_id, "run_id":self.run_id, "run_attempt":self.run_attempt, "head_sha":self.head_sha, "archive_digest":self.archive_digest, "archive_size_bytes":self.archive_size_bytes, "created_at":self.created_at, "expires_at":self.expires_at, "captured_at":self.captured_at})
        if len(raw) > MAX_TRANSPORT_BYTES: raise A0XHostedCaptureError(CAPTURE_INVALID)
        return raw

@dataclass(frozen=True)
class PinnedGitHubCLI:
    path: Path
    raw_sha256: str
    @classmethod
    def from_path(cls, path: Path) -> "PinnedGitHubCLI":
        path = Path(path)
        if not path.is_absolute(): raise A0XHostedCaptureError(PIN_INVALID)
        raw = _read_regular(path, PIN_INVALID)
        if _sha(raw) != GH_SHA256: raise A0XHostedCaptureError(PIN_INVALID)
        return cls(path.resolve(strict=True), GH_SHA256)

def revalidate_pinned_cli(pinned: PinnedGitHubCLI, path: Path, version_output: bytes) -> None:
    if not isinstance(pinned, PinnedGitHubCLI) or Path(path) != pinned.path or version_output != (GH_VERSION + "\n").encode() or _sha(_read_regular(pinned.path, PIN_INVALID)) != pinned.raw_sha256:
        raise A0XHostedCaptureError(PIN_INVALID)

Publisher = Callable[[Path, Path], None]

def capture_hosted_gate_a(request: CaptureRequest, transport: CaptureTransport, archive_path: Path, attestation_bundle: bytes, trusted_root: bytes, *, publish: Publisher | None = None) -> Path:
    if not isinstance(request, CaptureRequest) or not isinstance(transport, CaptureTransport): raise A0XHostedCaptureError(CAPTURE_INVALID)
    request.validate(); transport.validate()
    if not (transport.artifact_id == request.artifact_id and transport.run_id == request.run_id and transport.run_attempt == request.run_attempt and transport.head_sha == request.source_head and transport.archive_digest == "sha256:" + request.archive_sha256 and transport.archive_size_bytes == request.archive_size_bytes and transport.expires_at == request.expires_at): raise A0XHostedCaptureError(BINDING_MISMATCH)
    destination = request.output_root
    if os.path.lexists(destination): raise A0XHostedCaptureError(OUTPUT_EXISTS)
    try: meta = destination.parent.lstat()
    except OSError as error: raise A0XHostedCaptureError(CAPTURE_INVALID) from error
    if stat.S_ISLNK(meta.st_mode) or not stat.S_ISDIR(meta.st_mode): raise A0XHostedCaptureError(CAPTURE_INVALID)
    archive = _read_regular(Path(archive_path), ARCHIVE_INVALID)
    if len(archive) != request.archive_size_bytes or _sha(archive) != request.archive_sha256: raise A0XHostedCaptureError(ARCHIVE_INVALID)
    manifest = _extract_manifest(archive)
    if _sha(manifest) != request.manifest_sha256: raise A0XHostedCaptureError(BINDING_MISMATCH)
    try: parsed = parse_manifest_bytes(manifest)
    except A0XHostedGateAError as error: raise A0XHostedCaptureError(ARCHIVE_INVALID) from error
    if not (parsed["repository"] == request.repository and parsed["qualified_source_head"] == request.source_head and parsed["qualified_source_tree"] == request.source_tree and parsed["workflow"]["run_id"] == request.run_id and parsed["workflow"]["run_attempt"] == request.run_attempt): raise A0XHostedCaptureError(BINDING_MISMATCH)
    if not isinstance(attestation_bundle, bytes) or not attestation_bundle or len(attestation_bundle) > MAX_BUNDLE_BYTES or not isinstance(trusted_root, bytes) or not trusted_root or len(trusted_root) > MAX_TRUSTED_ROOT_BYTES: raise A0XHostedCaptureError(CAPTURE_INVALID)
    stage = Path(tempfile.mkdtemp(prefix=".a0x-hosted-capture-", dir=destination.parent))
    try:
        for name, raw in zip(FINAL_NAMES, (manifest, attestation_bundle, trusted_root, transport.as_document()), strict=True):
            with (stage / name).open("xb") as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        _assert_stage(stage)
        (publish or _darwin_publish_exclusive)(stage, destination)
    except A0XHostedCaptureError:
        _cleanup(stage); raise
    except Exception as error:
        _cleanup(stage); raise A0XHostedCaptureError(PUBLICATION_FAILED) from error
    if os.path.lexists(stage) or destination.is_symlink(): raise A0XHostedCaptureError(PUBLICATION_FAILED)
    _assert_stage(destination)
    return destination

def _extract_manifest(archive: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            members = z.infolist()
            if len(members) != 1: raise A0XHostedCaptureError(ARCHIVE_INVALID)
            member = members[0]; mode = member.external_attr >> 16
            if member.filename != MANIFEST_NAME or member.is_dir() or member.flag_bits & 1 or stat.S_IFMT(mode) != stat.S_IFREG or member.file_size > MAX_MANIFEST_BYTES: raise A0XHostedCaptureError(ARCHIVE_INVALID)
            raw = z.read(member)
            if len(raw) != member.file_size or len(raw) > MAX_MANIFEST_BYTES: raise A0XHostedCaptureError(ARCHIVE_INVALID)
            return raw
    except A0XHostedCaptureError: raise
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as error: raise A0XHostedCaptureError(ARCHIVE_INVALID) from error

def _read_regular(path: Path, code: str) -> bytes:
    try: first = path.lstat()
    except OSError as error: raise A0XHostedCaptureError(code) from error
    if stat.S_ISLNK(first.st_mode) or not stat.S_ISREG(first.st_mode) or first.st_nlink != 1: raise A0XHostedCaptureError(code)
    try: raw = path.read_bytes(); second = path.lstat()
    except OSError as error: raise A0XHostedCaptureError(code) from error
    if stat.S_ISLNK(second.st_mode) or not stat.S_ISREG(second.st_mode) or second.st_nlink != 1: raise A0XHostedCaptureError(code)
    return raw

def _assert_stage(path: Path) -> None:
    try: entries = list(path.iterdir())
    except OSError as error: raise A0XHostedCaptureError(PUBLICATION_FAILED) from error
    if {entry.name for entry in entries} != set(FINAL_NAMES): raise A0XHostedCaptureError(PUBLICATION_FAILED)
    for entry in entries: _read_regular(entry, PUBLICATION_FAILED)

def _cleanup(stage: Path) -> None:
    try:
        if stage.is_dir() and not stage.is_symlink(): shutil.rmtree(stage, ignore_errors=True)
    except OSError: pass

def _darwin_publish_exclusive(stage: Path, destination: Path) -> None:
    if sys.platform != "darwin": raise A0XHostedCaptureError(PUBLICATION_UNSUPPORTED)
    try:
        fn = ctypes.CDLL(None, use_errno=True).renamex_np; fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]; fn.restype = ctypes.c_int
        result = fn(os.fsencode(stage), os.fsencode(destination), 4)
    except (AttributeError, OSError) as error: raise A0XHostedCaptureError(PUBLICATION_UNSUPPORTED) from error
    if result:
        if ctypes.get_errno() == errno.EEXIST: raise A0XHostedCaptureError(OUTPUT_EXISTS)
        raise A0XHostedCaptureError(PUBLICATION_FAILED)

__all__ = ["ARCHIVE_INVALID", "A0XHostedCaptureError", "BINDING_MISMATCH", "CAPTURE_INVALID", "CaptureRequest", "CaptureTransport", "FINAL_NAMES", "GH_SHA256", "GH_VERSION", "OUTPUT_EXISTS", "PIN_INVALID", "PinnedGitHubCLI", "PUBLICATION_FAILED", "PUBLICATION_UNSUPPORTED", "capture_hosted_gate_a", "revalidate_pinned_cli"]
