"""Pure Gate B and Hosted Gate A document projections from a canonical pair."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .a0x_contract import PairBinding


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z$")

_REPOSITORY = "MarcoPorcellato/Latent-TRIZ"
_VERIFIER_SHA256 = "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c"
_VERIFIER_VERSION = "gh version 2.97.0 (2026-07-31)"


class A0XGateContractError(ValueError):
    """A pure Gate B/Hosted receipt projection input is not contract-valid."""


@dataclass(frozen=True)
class HashBoundPath:
    """One repository-relative input whose bytes are fixed by SHA-256."""

    path: str
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path:
            raise A0XGateContractError("hash-bound path is invalid")
        _require_sha256(self.sha256, "hash-bound path SHA-256")

    def as_mapping(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}


@dataclass(frozen=True)
class HostedInputBindings:
    """Typed byte bindings for Hosted Gate A evidence inputs."""

    manifest: HashBoundPath
    attestation_bundle: HashBoundPath
    trusted_root: HashBoundPath
    transport: HashBoundPath

    def __post_init__(self) -> None:
        for value in (self.manifest, self.attestation_bundle, self.trusted_root, self.transport):
            if not isinstance(value, HashBoundPath):
                raise A0XGateContractError("hosted input binding is invalid")

    def as_mapping(self) -> dict[str, dict[str, str]]:
        return {
            "manifest": self.manifest.as_mapping(),
            "attestation_bundle": self.attestation_bundle.as_mapping(),
            "trusted_root": self.trusted_root.as_mapping(),
            "transport": self.transport.as_mapping(),
        }

    def require_source_head(self, source_head: str) -> None:
        """Reject every noncanonical hosted input path for one source identity."""
        expected = {
            "manifest": f".a0x-runtime/gate-a/evidence/{source_head}/hosted-gate-a-evidence.json",
            "attestation_bundle": f".a0x-runtime/gate-a/evidence/{source_head}/hosted-gate-a-attestation.bundle.jsonl",
            "trusted_root": f".a0x-runtime/gate-a/evidence/{source_head}/github-trusted-root.jsonl",
            "transport": f".a0x-runtime/gate-a/evidence/{source_head}/hosted-gate-a-transport.json",
        }
        for name, required_path in expected.items():
            if getattr(self, name).path != required_path:
                raise A0XGateContractError(f"hosted {name} path is invalid")


@dataclass(frozen=True)
class VerifierIdentity:
    """Fixed verifier identity plus policy-byte binding."""

    policy_raw_sha256: str

    def __post_init__(self) -> None:
        _require_sha256(self.policy_raw_sha256, "verifier policy SHA-256")

    def as_mapping(self) -> dict[str, str]:
        return {
            "role": "github_cli_verifier",
            "version": _VERIFIER_VERSION,
            "sha256": _VERIFIER_SHA256,
            "policy_raw_sha256": self.policy_raw_sha256,
        }


@dataclass(frozen=True)
class GateBAuthorizationInputs:
    """Typed immutable values required to project one Gate B authorization."""

    authorization_id: str
    source_head: str
    source_tree: str
    source_sha: str
    job_workflow_sha: str
    hosted_inputs: HostedInputBindings
    verifier: VerifierIdentity

    def __post_init__(self) -> None:
        _require_identifier(self.authorization_id, "authorization id")
        for label, value in (
            ("source head", self.source_head),
            ("source tree", self.source_tree),
            ("source SHA", self.source_sha),
            ("job workflow SHA", self.job_workflow_sha),
        ):
            _require_revision(value, label)
        if not isinstance(self.hosted_inputs, HostedInputBindings) or not isinstance(self.verifier, VerifierIdentity):
            raise A0XGateContractError("Gate B authorization inputs are invalid")
        if self.source_sha != self.source_head or self.job_workflow_sha != self.source_head:
            raise A0XGateContractError("Gate B source identities must match")
        self.hosted_inputs.require_source_head(self.source_head)


@dataclass(frozen=True)
class VerificationReceiptInputs:
    """Typed immutable values required to project one verified Hosted receipt."""

    source_head: str
    source_tree: str
    authorization_raw_sha256: str
    hosted_inputs: HostedInputBindings
    verifier: VerifierIdentity
    verified_at: str

    def __post_init__(self) -> None:
        _require_revision(self.source_head, "source head")
        _require_revision(self.source_tree, "source tree")
        _require_sha256(self.authorization_raw_sha256, "authorization raw SHA-256")
        if not isinstance(self.hosted_inputs, HostedInputBindings) or not isinstance(self.verifier, VerifierIdentity):
            raise A0XGateContractError("verification receipt inputs are invalid")
        self.hosted_inputs.require_source_head(self.source_head)
        if not isinstance(self.verified_at, str) or not _TIMESTAMP.fullmatch(self.verified_at):
            raise A0XGateContractError("verified timestamp is invalid")


def build_gate_b_authorization(pair: PairBinding, inputs: GateBAuthorizationInputs) -> dict[str, Any]:
    """Return Gate B authorization mapping from validated pure inputs only."""
    pair = _validated_pair(pair)
    if not isinstance(inputs, GateBAuthorizationInputs):
        raise A0XGateContractError("Gate B authorization inputs are invalid")
    return {
        "artifact_class": "a0x-gate-b-authorization",
        "authorization_profile": "a0x-gate-b-authorization-v1",
        "authorization_status": "authorized",
        "repository": _REPOSITORY,
        "source_head": inputs.source_head,
        "source_tree": inputs.source_tree,
        "job_workflow_sha": inputs.job_workflow_sha,
        "source_sha": inputs.source_sha,
        "pair_binding": pair.as_mapping(),
        "hosted_inputs": inputs.hosted_inputs.as_mapping(),
        "verifier": inputs.verifier.as_mapping(),
        "verification_receipt_path": (
            f".a0x-runtime/gate-b-verifications/{inputs.source_head}/{pair.leg.value}/"
            f"{pair.model_key}/{pair.run_id}/gate-a-verification-receipt.json"
        ),
        "max_verification_count": 1,
        "stop_boundary": "after_gate_b_runtime_bundle",
        "authorization_id": inputs.authorization_id,
    }


def build_verification_receipt(pair: PairBinding, inputs: VerificationReceiptInputs) -> dict[str, Any]:
    """Return verified Hosted receipt mapping from validated pure inputs only."""
    pair = _validated_pair(pair)
    if not isinstance(inputs, VerificationReceiptInputs):
        raise A0XGateContractError("verification receipt inputs are invalid")
    return {
        "artifact_class": "a0x-hosted-gate-a-verification-receipt",
        "receipt_profile": "a0x-hosted-gate-a-verification-receipt-v1",
        "verification_status": "verified",
        "repository": _REPOSITORY,
        "qualified_source_head": inputs.source_head,
        "qualified_source_tree": inputs.source_tree,
        "pair_binding": pair.as_mapping(),
        "authorization_raw_sha256": inputs.authorization_raw_sha256,
        "hosted_inputs": inputs.hosted_inputs.as_mapping(),
        "verifier": inputs.verifier.as_mapping(),
        "verified_at": inputs.verified_at,
    }


def _validated_pair(pair: PairBinding) -> PairBinding:
    if not isinstance(pair, PairBinding):
        raise A0XGateContractError("pair binding must be a validated PairBinding")
    return PairBinding.from_mapping(pair.as_mapping())


def _require_sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise A0XGateContractError(f"{label} is invalid")


def _require_revision(value: object, label: str) -> None:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise A0XGateContractError(f"{label} is invalid")


def _require_identifier(value: object, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise A0XGateContractError(f"{label} is invalid")
