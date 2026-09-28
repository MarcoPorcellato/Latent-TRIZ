"""Bind one validated vertical-v4 evidence graph to an immutable context.

This module is deliberately separate from the historical production adapter:
it performs no v2/v3 conversion and creates no model, tokenizer, target, or
publication capability.  The only dispatch helper is a private synthetic
test seam; production activation remains owned by the parent executor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .a0x_contract import A0XContractError, PairBinding


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_REVISION = re.compile(r"^[a-f0-9]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_GRAPH_KEYS = frozenset({
    "descriptor", "readiness", "gate_a_evidence", "execution_inlet",
    "gate_c_authorization", "trust_file_identities",
})
_CONTEXTS = frozenset({"production", "synthetic-target-free"})


class A0XVerticalProductionAdapterError(ValueError):
    """A validated vertical graph cannot be rebound without ambiguity."""


@dataclass(frozen=True)
class VerticalProductionContext:
    """Detached immutable projection of the exact validated v4 graph."""

    source_head: str
    source_tree: str
    pair_binding: Mapping[str, Any]
    vertical_package: Mapping[str, Any]
    qualification_context: str
    authorization_id: str
    attempt_id: str
    descriptor: Mapping[str, Any]
    readiness: Mapping[str, Any]
    gate_a_evidence: Mapping[str, Any]
    execution_inlet: Mapping[str, Any]
    gate_c_authorization: Mapping[str, Any]
    trust_file_identities: Mapping[str, Any]

    def public_identity(self) -> dict[str, Any]:
        """Return path-free package digests and identity fields for summaries."""
        return {
            "qualified_source": {
                "head": self.source_head,
                "tree": self.source_tree,
                "ref": "refs/heads/main",
            },
            "pair_binding": _thaw(self.pair_binding),
            "vertical_package_digests": {
                key: self.vertical_package[key]
                for key in ("commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256")
            },
            "qualification_context": self.qualification_context,
            "authorization_id": self.authorization_id,
            "attempt_id": self.attempt_id,
        }


def bind_validated_vertical_graph(
    graph: Mapping[str, Any], *, qualification_context: str,
) -> VerticalProductionContext:
    """Recheck cross-bindings and freeze a child-validated v4 graph.

    Filesystem/schema/hash verification must already have happened in the
    material child.  This pure second boundary checks the data crossing into
    adapter dispatch and refuses legacy shapes rather than translating them.
    It is not a trust-manifest authority by itself: a future production
    dispatcher must first establish exact expected trust membership and
    identities independently.  The current public child remains disabled
    after this projection and reports ``runtime_unavailable``.
    """
    if not isinstance(graph, Mapping) or set(graph) != _GRAPH_KEYS:
        raise A0XVerticalProductionAdapterError("vertical graph shape is unsupported")
    descriptor = _object(graph, "descriptor")
    readiness = _object(graph, "readiness")
    evidence = _object(graph, "gate_a_evidence")
    inlet = _object(graph, "execution_inlet")
    authorization = _object(graph, "gate_c_authorization")
    trust = _object(graph, "trust_file_identities")

    source = _object(descriptor, "qualified_source")
    if (
        set(source) != {"head", "tree", "ref"}
        or not _REVISION.fullmatch(_string(source, "head"))
        or not _REVISION.fullmatch(_string(source, "tree"))
        or source.get("ref") != "refs/heads/main"
    ):
        raise A0XVerticalProductionAdapterError("vertical source binding is invalid")
    try:
        pair = PairBinding.from_mapping(_object(descriptor, "pair_binding"))
    except (A0XContractError, TypeError, ValueError) as error:
        raise A0XVerticalProductionAdapterError("vertical pair binding is invalid") from error
    pair_value = pair.as_mapping()
    package = _object(descriptor, "vertical_package")
    if (
        set(package) != {
            "envelope_path", "package_path", "commitment_path", "commitment_raw_sha256",
            "package_commitment_sha256", "dossier_path", "dossier_sha256",
        }
        or any(not _SHA256.fullmatch(_string(package, key)) for key in (
            "commitment_raw_sha256", "package_commitment_sha256", "dossier_sha256",
        ))
    ):
        raise A0XVerticalProductionAdapterError("vertical package binding is invalid")
    context = qualification_context
    if context not in _CONTEXTS:
        raise A0XVerticalProductionAdapterError("vertical qualification context is unsupported")
    auth_id = _identifier(authorization, "authorization_id")
    attempt_id = _identifier(authorization, "attempt_id")

    if readiness.get("source_head") != source["head"] or readiness.get("pair_binding") != pair_value:
        raise A0XVerticalProductionAdapterError("vertical readiness binding differs")
    if (
        evidence.get("source_head") != source["head"]
        or evidence.get("source_tree") != source["tree"]
        or evidence.get("pair_binding") != pair_value
    ):
        raise A0XVerticalProductionAdapterError("vertical Hosted Gate A binding differs")

    if (
        descriptor.get("descriptor_profile") != "a0x-vertical-launch-descriptor-v2"
        or authorization.get("artifact_class") != "a0x-vertical-execution-authorization"
        or authorization.get("commitment_profile") != "a0x-execution-authorization-json-v4"
        or authorization.get("qualified_source") != source
        or authorization.get("pair_binding") != pair_value
        or authorization.get("vertical_package") != package
        or authorization.get("qualification_context") != context
        or inlet.get("authorization_id") != descriptor.get("authorization_id")
        or inlet.get("attempt_id") != descriptor.get("attempt_id")
        or authorization.get("max_guard_exec_count") != 1
        or authorization.get("stop_boundary") != "after_one_sealed_target_read"
        or inlet.get("qualified_source") != source
        or inlet.get("pair_binding") != pair_value
        or inlet.get("vertical_package") != package
        or inlet.get("artifact_class") != "a0x-vertical-gate-b-execution-inlet"
        or inlet.get("inlet_profile") != "a0x-vertical-gate-b-execution-inlet-v2"
    ):
        raise A0XVerticalProductionAdapterError("vertical v4 authorization cross-binding differs")

    _validate_trust_identities(trust)
    frozen = _freeze(graph)
    return VerticalProductionContext(
        source_head=source["head"],
        source_tree=source["tree"],
        pair_binding=frozen["descriptor"]["pair_binding"],
        vertical_package=frozen["descriptor"]["vertical_package"],
        qualification_context=context,
        authorization_id=auth_id,
        attempt_id=attempt_id,
        descriptor=frozen["descriptor"],
        readiness=frozen["readiness"],
        gate_a_evidence=frozen["gate_a_evidence"],
        execution_inlet=frozen["execution_inlet"],
        gate_c_authorization=frozen["gate_c_authorization"],
        trust_file_identities=frozen["trust_file_identities"],
    )


def _dispatch_synthetic_target_free(
    graph: Mapping[str, Any], executor: Callable[[VerticalProductionContext], Any],
) -> Any:
    """Private adapter test seam; never used by the public child entrypoint."""
    context = bind_validated_vertical_graph(graph, qualification_context="synthetic-target-free")
    if context.qualification_context != "synthetic-target-free" or not callable(executor):
        raise A0XVerticalProductionAdapterError("synthetic dispatch is not eligible")
    return executor(context)


def _validate_trust_identities(value: Mapping[str, Any]) -> None:
    if not value:
        raise A0XVerticalProductionAdapterError("vertical trust identity set is empty")
    for path, raw_identity in value.items():
        if not isinstance(path, str) or path != PurePosixPath(path).as_posix() or PurePosixPath(path).is_absolute() or any(part in {"", ".", ".."} for part in PurePosixPath(path).parts):
            raise A0XVerticalProductionAdapterError("vertical trust identity path is unsafe")
        if not isinstance(raw_identity, Mapping) or set(raw_identity) != {"device", "inode", "size", "sha256"}:
            raise A0XVerticalProductionAdapterError("vertical trust identity shape is invalid")
        if any(not isinstance(raw_identity[key], int) or isinstance(raw_identity[key], bool) or raw_identity[key] < 0 for key in ("device", "inode", "size")) or raw_identity["inode"] == 0:
            raise A0XVerticalProductionAdapterError("vertical trust inode identity is invalid")
        if not isinstance(raw_identity.get("sha256"), str) or not _SHA256.fullmatch(raw_identity["sha256"]):
            raise A0XVerticalProductionAdapterError("vertical trust digest is invalid")


def _object(parent: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise A0XVerticalProductionAdapterError(f"{key} is not an object")
    return value


def _string(parent: Mapping[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str):
        raise A0XVerticalProductionAdapterError(f"{key} is not a string")
    return value


def _identifier(parent: Mapping[str, Any], key: str) -> str:
    value = _string(parent, key)
    if not _IDENTIFIER.fullmatch(value):
        raise A0XVerticalProductionAdapterError(f"{key} is invalid")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(member) for key, member in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(member) for member in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise A0XVerticalProductionAdapterError("vertical graph is not JSON-shaped")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(member) for key, member in value.items()}
    if isinstance(value, tuple):
        return [_thaw(member) for member in value]
    return value
