"""Offline, fail-closed verifier for A0X Hosted Gate A evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Callable, Mapping, Sequence

from jsonschema import Draft202012Validator

from latent_triz.a0x_hosted_gate_a import A0XHostedGateAError, canonical_json_bytes, parse_manifest_bytes


EXPECTATION_MISMATCH = "A0X_GATE_B_EXPECTATION_MISMATCH"
ATTESTATION_REFUSED = "A0X_GATE_B_ATTESTATION_REFUSED"
INPUT_HASH_MISMATCH = "A0X_GATE_B_INPUT_HASH_MISMATCH"
INPUT_INVALID = "A0X_GATE_B_INPUT_INVALID"
SOURCE_DRIFT = "A0X_GATE_B_SOURCE_DRIFT"
OUTPUT_EXISTS = "A0X_GATE_B_OUTPUT_EXISTS"

_INPUT_LIMITS = {
    "manifest": 32 * 1024,
    "attestation_bundle": 1024 * 1024,
    "trusted_root": 2 * 1024 * 1024,
    "transport": 16 * 1024,
}
_MAX_CONTROL_BYTES = 32 * 1024
_GH_VERSION = "gh version 2.97.0 (2026-07-31)"
_GH_SHA256 = "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"


class A0XHostedVerifierError(ValueError):
    """Stable refusal raised before Gate B can create any output."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GateBVerificationRequest:
    """Fixed paths required to verify one Gate B authorization."""

    repository_root: Path
    authorization_path: Path
    verifier_executable: Path
    verifier_policy_path: Path


VerifierRunner = Callable[[Sequence[str], Path], tuple[int, bytes, bytes]]
SourceState = tuple[str, str, bool]
SourceStateProbe = Callable[[Path], SourceState]


def validate_verification_result(
    raw: bytes,
    *,
    manifest_sha256: str,
    source_head: str,
    repository: str,
    signer_workflow: str,
    predicate_type: str,
    cert_oidc_issuer: str,
    required_ref: str,
) -> dict[str, Any]:
    """Accept only frozen gh 2.97.0/sigstore-go 1.2.2 result bytes."""
    value = _strict_json(raw)
    schema = _read_result_schema()
    if list(Draft202012Validator(schema).iter_errors(value)):
        raise A0XHostedVerifierError(ATTESTATION_REFUSED)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise A0XHostedVerifierError(ATTESTATION_REFUSED)
    result = value[0]
    verification = result["verificationResult"]
    statement = verification["statement"]
    certificate = verification["signature"]["certificate"]
    extensions = certificate["extensions"]
    expected_workflow_uri = f"https://github.com/{signer_workflow}@{required_ref}"
    expected_repository_uri = f"https://github.com/{repository}"
    expected = (
        statement["subject"][0]["digest"]["sha256"] == manifest_sha256
        and statement["predicateType"] == predicate_type
        and certificate["issuer"] == cert_oidc_issuer
        and certificate["subjectAlternativeName"] == expected_workflow_uri
        and extensions["BuildSignerURI"] == expected_workflow_uri
        and extensions["BuildSignerDigest"] == {"sha1": source_head}
        and extensions["RunnerEnvironment"] == "github-hosted"
        and extensions["SourceRepositoryURI"] == expected_repository_uri
        and extensions["SourceRepositoryDigest"] == {"sha1": source_head}
        and extensions["SourceRepositoryRef"] == required_ref
        and extensions["BuildConfigURI"] == expected_workflow_uri
        and extensions["BuildConfigDigest"] == {"sha1": source_head}
        and extensions["BuildTrigger"] == "push"
        and statement["predicate"]["buildDefinition"]["buildType"] == "https://github.com/actions/runner/github-hosted"
        and statement["predicate"]["runDetails"]["builder"]["id"] == "https://github.com/actions/runner/github-hosted"
        and statement["predicate"]["buildDefinition"]["externalParameters"] == {
            "workflow": signer_workflow, "source": source_head,
        }
    )
    if not expected:
        raise A0XHostedVerifierError(EXPECTATION_MISMATCH)
    return result


def _strict_json(raw: bytes) -> Any:
    if not isinstance(raw, bytes) or raw.startswith(b"\xef\xbb\xbf"):
        raise A0XHostedVerifierError(ATTESTATION_REFUSED)
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_number, parse_constant=_reject_number,
        )
    except (UnicodeDecodeError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise A0XHostedVerifierError(ATTESTATION_REFUSED) from error


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate key")
        value[key] = item
    return value


def _reject_number(value: str) -> None:
    raise ValueError(f"unexpected JSON number {value!r}")


def _read_result_schema() -> Mapping[str, Any]:
    path = Path(__file__).resolve().parents[2] / "schemas/a0x-gh-2.97.0-verification-result.schema.json"
    return _strict_json(path.read_bytes())


def verify_hosted_gate_a(
    request: GateBVerificationRequest,
    runner: VerifierRunner,
    source_state_probe: SourceStateProbe,
    clock: Callable[[], str] | None = None,
) -> bytes:
    """Verify one exact hosted Gate A evidence packet without network access."""
    root = Path(request.repository_root).resolve(strict=True)
    authorization_path = _controlled_path(root, request.authorization_path)
    policy_path = _controlled_path(root, request.verifier_policy_path)
    _require_independent(Path(request.verifier_executable), None)
    executable = Path(request.verifier_executable).resolve(strict=True)
    _require_independent(authorization_path, _MAX_CONTROL_BYTES)
    _require_independent(policy_path, _MAX_CONTROL_BYTES)
    _require_independent(executable, None)
    authorization_raw = authorization_path.read_bytes()
    authorization = _load_schema_object(authorization_raw, "a0x-gate-b-authorization.schema.json")
    policy_raw = policy_path.read_bytes()
    policy = _load_schema_object(policy_raw, "a0x-hosted-gate-a-verifier-policy.schema.json")
    _validate_authorization(authorization, policy, policy_raw, executable)
    timestamp = (clock or _utc_timestamp)()
    current_time = _parse_timestamp(timestamp)
    inputs = _resolve_inputs(root, authorization)
    for name, path in inputs.items():
        _require_independent(path, _INPUT_LIMITS[name])
    raw_inputs = {name: path.read_bytes() for name, path in inputs.items()}
    for name, raw in raw_inputs.items():
        if _sha256(raw) != authorization["hosted_inputs"][name]["sha256"]:
            raise A0XHostedVerifierError(INPUT_HASH_MISMATCH)
    try:
        manifest = parse_manifest_bytes(raw_inputs["manifest"])
    except A0XHostedGateAError as error:
        raise A0XHostedVerifierError(INPUT_INVALID) from error
    transport = _load_schema_object(raw_inputs["transport"], "a0x-hosted-gate-a-transport.schema.json")
    _validate_manifest_and_transport(manifest, transport, authorization, root, current_time)
    expected_state = (authorization["source_head"], authorization["source_tree"], True)
    if source_state_probe(root) != expected_state:
        raise A0XHostedVerifierError(SOURCE_DRIFT)
    output_path = _resolve_relative(root, authorization["verification_receipt_path"])
    _require_safe_output_parent(root, output_path)
    if os.path.lexists(output_path):
        raise A0XHostedVerifierError(OUTPUT_EXISTS)
    argv = _verification_argv(executable, inputs, policy, authorization["source_head"])
    return_code, stdout, _stderr = runner(argv, root)
    if type(return_code) is not int or return_code != 0:
        raise A0XHostedVerifierError(ATTESTATION_REFUSED)
    validate_verification_result(
        stdout,
        manifest_sha256=_sha256(raw_inputs["manifest"]),
        source_head=authorization["source_head"], repository=policy["repository"],
        signer_workflow=policy["signer_workflow"], predicate_type=policy["predicate_type"],
        cert_oidc_issuer=policy["cert_oidc_issuer"], required_ref=policy["required_ref"],
    )
    if source_state_probe(root) != expected_state:
        raise A0XHostedVerifierError(SOURCE_DRIFT)
    for name, path in inputs.items():
        _require_independent(path, _INPUT_LIMITS[name])
        if _sha256(path.read_bytes()) != authorization["hosted_inputs"][name]["sha256"]:
            raise A0XHostedVerifierError(INPUT_HASH_MISMATCH)
    _require_independent(executable, None)
    if _sha256(executable.read_bytes()) != _GH_SHA256:
        raise A0XHostedVerifierError(INPUT_HASH_MISMATCH)
    receipt = {
        "artifact_class": "a0x-hosted-gate-a-verification-receipt",
        "receipt_profile": "a0x-hosted-gate-a-verification-receipt-v1",
        "verification_status": "verified",
        "repository": authorization["repository"],
        "qualified_source_head": authorization["source_head"],
        "qualified_source_tree": authorization["source_tree"],
        "pair_binding": authorization["pair_binding"],
        "authorization_raw_sha256": _sha256(authorization_raw),
        "hosted_inputs": authorization["hosted_inputs"],
        "verifier": authorization["verifier"],
        "verified_at": timestamp,
    }
    raw_receipt = canonical_json_bytes(receipt)
    if len(raw_receipt) > _MAX_CONTROL_BYTES:
        raise A0XHostedVerifierError(INPUT_INVALID)
    _load_schema_object(raw_receipt, "a0x-hosted-gate-a-verification-receipt.schema.json")
    _exclusive_write(output_path, raw_receipt)
    return raw_receipt


def _controlled_path(root: Path, candidate: Path) -> Path:
    path = Path(candidate)
    _require_independent(path, _MAX_CONTROL_BYTES)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise A0XHostedVerifierError(INPUT_INVALID) from error
    return resolved


def _resolve_relative(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise A0XHostedVerifierError(INPUT_INVALID)
    candidate = root / value
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise A0XHostedVerifierError(INPUT_INVALID) from error
    return candidate


def _require_independent(path: Path, limit: int | None) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise A0XHostedVerifierError(INPUT_INVALID) from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise A0XHostedVerifierError(INPUT_INVALID)
    if limit is not None and metadata.st_size > limit:
        raise A0XHostedVerifierError(INPUT_INVALID)


def _require_safe_output_parent(root: Path, path: Path) -> None:
    current = root
    for part in path.relative_to(root).parent.parts:
        current /= part
        if os.path.lexists(current) and stat.S_ISLNK(current.lstat().st_mode):
            raise A0XHostedVerifierError(INPUT_INVALID)


def _resolve_inputs(root: Path, authorization: Mapping[str, Any]) -> dict[str, Path]:
    hosted = authorization.get("hosted_inputs")
    if not isinstance(hosted, Mapping) or set(hosted) != set(_INPUT_LIMITS):
        raise A0XHostedVerifierError(INPUT_INVALID)
    result: dict[str, Path] = {}
    for name in _INPUT_LIMITS:
        binding = hosted[name]
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise A0XHostedVerifierError(INPUT_INVALID)
        result[name] = _resolve_relative(root, binding["path"])
    return result


def _validate_authorization(authorization: Mapping[str, Any], policy: Mapping[str, Any], policy_raw: bytes, executable: Path) -> None:
    verifier = authorization.get("verifier")
    expected_verifier = {
        "role": "github_cli_verifier", "version": _GH_VERSION,
        "sha256": _GH_SHA256, "policy_raw_sha256": _sha256(policy_raw),
    }
    if authorization.get("repository") != policy.get("repository") or verifier != expected_verifier:
        raise A0XHostedVerifierError(EXPECTATION_MISMATCH)
    if _sha256(executable.read_bytes()) != _GH_SHA256:
        raise A0XHostedVerifierError(INPUT_HASH_MISMATCH)


def _validate_manifest_and_transport(
    manifest: Mapping[str, Any], transport: Mapping[str, Any], authorization: Mapping[str, Any], root: Path,
    current_time: datetime,
) -> None:
    if (
        manifest["repository"] != authorization["repository"]
        or manifest["qualified_source_head"] != authorization["source_head"]
        or manifest["qualified_source_tree"] != authorization["source_tree"]
        or transport["repository"] != authorization["repository"]
        or transport["head_sha"] != authorization["source_head"]
        or transport["run_id"] != manifest["workflow"]["run_id"]
        or transport["run_attempt"] != 1
    ):
        raise A0XHostedVerifierError(EXPECTATION_MISMATCH)
    workflow = root / manifest["workflow"]["path"]
    _require_independent(workflow, None)
    if _sha256(workflow.read_bytes()) != manifest["workflow"]["raw_sha256"]:
        raise A0XHostedVerifierError(INPUT_HASH_MISMATCH)
    expires_at = _parse_timestamp(transport["expires_at"])
    if expires_at < current_time:
        raise A0XHostedVerifierError(ATTESTATION_REFUSED)


def _verification_argv(executable: Path, inputs: Mapping[str, Path], policy: Mapping[str, Any], source_head: str) -> tuple[str, ...]:
    return (
        str(executable), "attestation", "verify", str(inputs["manifest"]),
        "--bundle", str(inputs["attestation_bundle"]), "--custom-trusted-root", str(inputs["trusted_root"]),
        "--repo", policy["repository"], "--signer-workflow", policy["signer_workflow"],
        "--signer-digest", source_head, "--source-digest", source_head,
        "--source-ref", policy["required_ref"], "--cert-oidc-issuer", policy["cert_oidc_issuer"],
        "--predicate-type", policy["predicate_type"], "--deny-self-hosted-runners", "--format", "json",
    )


def _load_schema_object(raw: bytes, schema_name: str) -> dict[str, Any]:
    value = _strict_json(raw)
    if not isinstance(value, dict):
        raise A0XHostedVerifierError(INPUT_INVALID)
    schema = _strict_json((Path(__file__).resolve().parents[2] / "schemas" / schema_name).read_bytes())
    if list(Draft202012Validator(schema).iter_errors(value)):
        raise A0XHostedVerifierError(INPUT_INVALID)
    return value


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise A0XHostedVerifierError(INPUT_INVALID)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise A0XHostedVerifierError(INPUT_INVALID) from error


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _exclusive_write(path: Path, raw: bytes) -> None:
    if os.path.lexists(path):
        raise A0XHostedVerifierError(OUTPUT_EXISTS)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except FileExistsError as error:
        raise A0XHostedVerifierError(OUTPUT_EXISTS) from error
    except OSError as error:
        raise A0XHostedVerifierError(INPUT_INVALID) from error


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
