"""Reviewed, authored summaries for the public Observatory source catalogue.

These summaries describe each allowlisted file's role; they are not extracted
source text, experimental findings, or a substitute for the linked document.
TRIZ-reference entries intentionally remain citation-only.
"""

from __future__ import annotations

from collections.abc import Mapping


# Each value is two short authored sentences. Exact path coverage makes source
# catalogue changes an explicit editorial review instead of a generic fallback.
SOURCE_SYNOPSES: dict[str, tuple[str, str]] = {
    "docs/ARTICLE.md": (
        "Introduces the Latent-TRIZ research question and its public experimental framing.",
        "Use it for the project’s motivation and scope, not as a result report.",
    ),
    "docs/HYPOTHESES_AND_FALSIFICATION.md": (
        "Defines the weak and strong Latent-TRIZ hypotheses and their competing explanations.",
        "Lists observations that could weaken or falsify each claim.",
    ),
    "docs/EVIDENCE_LADDER.md": (
        "Explains the E0–E6 levels used to describe increasing evidence strength.",
        "Sets limits on what permits a claim to move between levels.",
    ),
    "docs/LABORATORY_MASTER_PLAN.md": (
        "Maps the laboratory’s research tracks, controls, and planned milestones.",
        "Use it to see how exploratory signals remain separate from stronger claims.",
    ),
    "docs/ROADMAP.md": (
        "Summarizes delivered foundations and the intended next research stages.",
        "It is a planning view; current status should be checked in the linked records.",
    ),
    "docs/LAB_SUITE.md": (
        "Introduces the local visual suite for browsing laboratory structures and outputs.",
        "Describes its views and how to run the suite without treating it as evidence.",
    ),
    "docs/LAB01.md": (
        "Specifies Lab 01’s model-anatomy questions and receipt-derived states.",
        "Separates runtime compatibility evidence from behavioral conclusions.",
    ),
    "docs/LAB02.md": (
        "Specifies Lab 02’s dataset-anatomy inventory, checks, and gates.",
        "Focuses on what the experimental records contain before outcome analysis.",
    ),
    "docs/LAB03.md": (
        "Defines Lab 03 behavioral baselines and the comparisons they support.",
        "Keeps baseline observations distinct from latent-mechanism evidence.",
    ),
    "docs/LAB04.md": (
        "Defines Lab 04 probes for whether candidate transformations are decodable.",
        "States the controls and boundaries needed before interpreting a probe result.",
    ),
    "docs/LAB05.md": (
        "Defines Lab 05’s candidate latent directions and control design.",
        "Treats directions as candidates until independent tests support them.",
    ),
    "docs/LAB06.md": (
        "Sets readiness conditions for Lab 06 causal intervention experiments.",
        "Covers intervention arms and prerequisites before any causal interpretation.",
    ),
    "docs/decisions/index.md": (
        "Indexes the laboratory’s numbered architecture and research decisions.",
        "Use it to locate the rationale and status recorded in each decision file.",
    ),
    "docs/decisions/0001-official-lab-foundation.md": (
        "Records the decision establishing the official public research laboratory.",
        "Explains the initial scope, governance, and evidence-preservation rationale.",
    ),
    "docs/decisions/0002-stage1-blinded-pilot.md": (
        "Records the blinded two-arm pilot design and its separation of test stages.",
        "Documents why response-surface leakage controls matter to interpretation.",
    ),
    "docs/decisions/0003-exp-001-model-selection.md": (
        "Records the model-selection rationale for the EXP-001 comparison.",
        "Defines the chosen comparison scope rather than a general model ranking.",
    ),
    "docs/decisions/0004-lab01-model-anatomy.md": (
        "Records Lab 01’s model-anatomy scope and evidence contract.",
        "Clarifies which model facts are inventory evidence and which remain unknown.",
    ),
    "docs/decisions/0005-lab02-dataset-anatomy.md": (
        "Records Lab 02’s dataset-anatomy scope and inventory decisions.",
        "Explains the checks used to make later comparisons interpretable.",
    ),
    "docs/decisions/0006-lab03-behavioral-baselines.md": (
        "Records the decision to establish behavioral baselines in Lab 03.",
        "Sets the intended comparison boundaries before latent probing.",
    ),
    "docs/decisions/0007-lab04-decodability.md": (
        "Records Lab 04’s decodability question and probe-design rationale.",
        "Separates successful decoding from evidence of mechanism or causality.",
    ),
    "docs/decisions/0008-local-visual-laboratory-suite.md": (
        "Records the decision to provide a local visual browser for lab artifacts.",
        "Explains its role as navigation and inspection, not a new evidence source.",
    ),
    "docs/decisions/0009-lab05-candidate-directions.md": (
        "Records Lab 05’s method for nominating candidate representation directions.",
        "Keeps nomination separate from validation and any later intervention claim.",
    ),
    "docs/README.md": (
        "Provides a human-oriented map of the project documentation and topics.",
        "Use it to choose the canonical source for a question before reading details.",
    ),
    "docs/CURRENT_STATUS.md": (
        "Summarizes the documented laboratory checkpoint and active work boundaries.",
        "Check its linked exact records because status changes as new work is merged.",
    ),
    "results/README.md": (
        "Maps the published result families and their report locations.",
        "Explains how to read package-specific outcomes without pooling them.",
    ),
    "data/claims.jsonl": (
        "Contains the structured registry of research claims and their evidence states.",
        "Each row should be read with its scope, falsifier, and linked evidence fields.",
    ),
    "schemas/claim.schema.json": (
        "Defines the machine-readable shape and allowed fields for claim records.",
        "It validates record structure; it does not validate scientific truth.",
    ),
    "data/triz-reference-sources.json": (
        "Lists citation metadata for selected public TRIZ reference materials.",
        "Third-party text is not reproduced here; follow citations to the source owner.",
    ),
    "data/triz-consulting-web-corpus.json": (
        "Indexes selected public TRIZ Consulting pages and source metadata.",
        "Use it as a citation map, not as permission to redistribute source content.",
    ),
    "experiments/a0-automated-weak-proxy/protocol.json": (
        "Freezes the A0 automated weak-proxy question, procedure, and limits.",
        "Its protocol defines a narrow proxy signal, not a general TRIZ test.",
    ),
    "experiments/a0r1-independent-proxy/protocol.json": (
        "Freezes the independent-proxy design used for A0-R1.",
        "Read its controls and scope alongside the separately published result.",
    ),
    "experiments/a0r2-independent-model/study-protocol.json": (
        "Specifies the A0-R2 study protocol and the independent-model comparison.",
        "The protocol’s constraints govern how its associated analysis can be read.",
    ),
    "results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json": (
        "Binds the published A0 report to its versioned package and provenance.",
        "Use this manifest to verify the exact artifact and its declared scope.",
    ),
    "results/a0/a0-v1.0.3-e93a9faa/report.html": (
        "Reports the published A0 automated weak-proxy outcome and limitations.",
        "Interpret it only under the frozen A0 protocol and package binding.",
    ),
    "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json": (
        "Binds the A0-R1 report to its versioned package and provenance.",
        "Use it to check which exact report and scope the publication identifies.",
    ),
    "results/a0r1/a0r1-v1.0.0-e93a9faa-r1/report.md": (
        "Reports A0-R1’s independent-proxy outcome and stated limitations.",
        "It supports only the package-scoped interpretation recorded in the report.",
    ),
    "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/publication-manifest.json": (
        "Binds the A0-R2-C3 analysis-only report to its published package.",
        "The record identifies provenance and scope, not a new model execution.",
    ),
    "results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/report.md": (
        "Reports the A0-R2-C3 analysis-only recovery and its evidence boundaries.",
        "Read it as analysis of the named package, not as an additional run.",
    ),
    "results/exp001-comparative/smollm2-135m-93efa2f0-smollm2-135m-20260819-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for SmolLM2-135M to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/smollm2-135m-93efa2f0-smollm2-135m-20260819-01/report.md": (
        "Reports the EXP-001 comparative observation for SmolLM2-135M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for GPT-2 to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/report.md": (
        "Reports the EXP-001 comparative observation for GPT-2.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for GPT-Neo-125M to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01/report.md": (
        "Reports the EXP-001 comparative observation for GPT-Neo-125M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for Pythia-70M to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/report.md": (
        "Reports the EXP-001 comparative observation for Pythia-70M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for Qwen3-0.6B-Base to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/report.md": (
        "Reports the EXP-001 comparative observation for Qwen3-0.6B-Base.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for Qwen2.5-0.5B to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01/report.md": (
        "Reports the EXP-001 comparative observation for Qwen2.5-0.5B.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/publication-manifest.json": (
        "Binds the EXP-001 comparative record for SmolLM2-360M to its package.",
        "It identifies provenance for this model-specific comparison artifact.",
    ),
    "results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/report.md": (
        "Reports the EXP-001 comparative observation for SmolLM2-360M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/huggingfacetb-smollm2-135m/exp002-smollm2-135m-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for SmolLM2-135M to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/huggingfacetb-smollm2-135m/exp002-smollm2-135m-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for SmolLM2-135M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/eleutherai-pythia-70m-deduped/exp002-pythia-70m-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for Pythia-70M to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/eleutherai-pythia-70m-deduped/exp002-pythia-70m-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for Pythia-70M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/openai-community-gpt2/exp002-gpt2-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for GPT-2 to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/openai-community-gpt2/exp002-gpt2-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for GPT-2.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/eleutherai-gpt-neo-125m/exp002-gpt-neo-125m-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for GPT-Neo-125M to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/eleutherai-gpt-neo-125m/exp002-gpt-neo-125m-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for GPT-Neo-125M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/huggingfacetb-smollm2-360m/exp002-smollm2-360m-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for SmolLM2-360M to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/huggingfacetb-smollm2-360m/exp002-smollm2-360m-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for SmolLM2-360M.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/qwen-qwen2-5-0-5b/exp002-qwen2-5-0-5b-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for Qwen2.5-0.5B to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/qwen-qwen2-5-0-5b/exp002-qwen2-5-0-5b-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for Qwen2.5-0.5B.",
        "Its result and caveats apply only to this named model and package.",
    ),
    "results/exp002/qwen-qwen3-0-6b-base/exp002-qwen3-0-6b-exp002a-20260820-01/publication-manifest.json": (
        "Binds the EXP-002A baseline record for Qwen3-0.6B-Base to its package.",
        "It identifies provenance for this model-specific baseline artifact.",
    ),
    "results/exp002/qwen-qwen3-0-6b-base/exp002-qwen3-0-6b-exp002a-20260820-01/report.md": (
        "Reports the EXP-002A baseline observation for Qwen3-0.6B-Base.",
        "Its result and caveats apply only to this named model and package.",
    ),
}


def validate_synopsis_catalogue(
    expected_paths: Mapping[str, object],
    synopses: Mapping[str, tuple[str, str]] | None = None,
) -> None:
    """Require exact allowlist coverage and distinct bounded editorial entries."""
    candidate = SOURCE_SYNOPSES if synopses is None else synopses
    if not isinstance(expected_paths, Mapping) or not isinstance(candidate, Mapping):
        raise PermissionError("Public source synopsis catalogue is malformed")
    if set(candidate) != set(expected_paths):
        raise PermissionError("Public source synopsis coverage differs from allowlist")
    seen: set[tuple[str, str]] = set()
    for path, parts in candidate.items():
        if (not isinstance(path, str) or not isinstance(parts, tuple) or len(parts) != 2
                or any(not isinstance(part, str) or not part.strip() or len(part) > 180 for part in parts)):
            raise PermissionError("Public source synopsis must contain two bounded sentences")
        normalized = tuple(" ".join(part.split()).casefold() for part in parts)
        if normalized in seen:
            raise PermissionError("Public source synopsis must be distinct per file")
        seen.add(normalized)


def source_synopsis(path: str, expected_paths: Mapping[str, object]) -> str:
    """Return the authored two-sentence summary for one allowlisted source."""
    validate_synopsis_catalogue(expected_paths)
    if path not in expected_paths:
        raise PermissionError("Public source synopsis path is not allowlisted")
    try:
        first, second = SOURCE_SYNOPSES[path]
    except KeyError as exc:
        raise PermissionError("Public source synopsis is unavailable") from exc
    return f"{first} {second}"
