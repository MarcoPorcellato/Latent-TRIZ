"""Presentation-only helpers for the local, read-only research observatory.

Every value read from repository documents is escaped before insertion in HTML.
No helper opens a file, makes a network request, or computes a scientific score.
"""

from __future__ import annotations

from collections import Counter
from html import escape
from typing import Iterable, Mapping


STATUS_LABELS = {
    "positive_exploratory_proxy": "Exploratory proxy +",
    "analysis_only_recovery": "Analysis-only recovery",
    "auto_proxy_signal": "AUTO proxy signal",
    "null": "Null",
    "failed": "Engineering failure",
    "unavailable": "Unavailable",
    "descriptive": "Descriptive",
    "recovered_unbound": "Recovered, unbound",
    "not_run": "Not run",
    "not_inspected": "Not inspected",
    "not_interpretable": "Not interpretable",
}

STATUS_COLORS = {
    "positive_exploratory_proxy": ("#d1fae5", "#065f46"),
    "analysis_only_recovery": ("#e0f2fe", "#075985"),
    "auto_proxy_signal": ("#ccfbf1", "#115e59"),
    "null": ("#dbeafe", "#1e40af"),
    "failed": ("#fee2e2", "#991b1b"),
    "unavailable": ("#fef3c7", "#92400e"),
    "descriptive": ("#e0e7ff", "#3730a3"),
    "recovered_unbound": ("#fce7f3", "#9d174d"),
    "not_run": ("#f1f5f9", "#475569"),
    "not_inspected": ("#f1f5f9", "#64748b"),
    "not_interpretable": ("#fecaca", "#7f1d1d"),
}

FAMILY_QUESTIONS = {
    "selected_docs": "Which research design, method, or decision does this document describe?",
    "navigation_snapshot": "Where was repository status summarized, and is that summary still current?",
    "formal_claims": "Which formal hypothesis and evidence level are registered?",
    "triz_reference": "Which expert TRIZ source is recorded for reference?",
    "study_protocol": "Which frozen protocol defines this experiment?",
    "a0": "What did the original A0 proxy study report?",
    "a0_r1": "What did the independent A0-R1 proxy study report?",
    "a0_r2_c3": "What did the C3 analysis-only recovery report?",
    "exp001_comparative": "What did this model's EXP-001 comparison report?",
    "exp002_baseline": "What did this model's EXP-002A baseline report?",
}

VIEW_TITLES = (
    "Start here",
    "Experiments × models",
    "What results mean",
    "Scientific route",
    "Decisions and lessons",
    "Explore sources",
)


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _source(path: object) -> str:
    return f'<span class="lt-source">{_e(path)}</span>' if path else ""


def _chip(status: str) -> str:
    label = STATUS_LABELS.get(status, "Not interpretable")
    safe_status = status if status in STATUS_LABELS else "not_interpretable"
    return f'<span class="lt-chip lt-{safe_status}">{_e(label)}</span>'


def snapshot_banner_html(snapshot: Mapping[str, object]) -> str:
    """Identify the local source snapshot without asserting remote publication."""
    head = str(snapshot.get("source_head") or "unavailable")
    tree = str(snapshot.get("source_tree") or "unavailable")
    digest = str(snapshot.get("snapshot_sha256") or "unavailable")
    return (
        '<div class="lt-page lt-note"><strong>Local source snapshot:</strong> '
        f'commit {_e(head[:12])} · tree {_e(tree[:12])} · catalogue {_e(digest[:12])}. '
        'Remote public publication is not verified by this app.</div>'
    )


def page_css() -> str:
    """Fixed local styles; no source-derived CSS or external fonts/assets."""
    return """
<style>
  :root { --lt-ink:#14213d; --lt-muted:#526179; --lt-edge:#d9e3ee;
          --lt-paper:#f7fafc; --lt-blue:#123a68; --lt-teal:#0f766e; }
  .lt-page { color:var(--lt-ink); font-family:Inter,ui-sans-serif,system-ui,sans-serif;
             max-width:1420px; margin:auto; padding:8px 4px 48px; }
  .lt-hero { background:linear-gradient(118deg,#102a4c 0%,#164e63 66%,#0f766e 100%);
             color:#fff; border-radius:20px; padding:30px 34px; box-shadow:0 12px 32px #102a4c24; }
  .lt-eyebrow { font-size:.72rem; font-weight:800; letter-spacing:.13em;
                 text-transform:uppercase; opacity:.88; }
  .lt-hero h1 { color:#fff; margin:8px 0 10px; font-size:clamp(1.7rem,3vw,2.7rem);
                letter-spacing:-.035em; line-height:1.1; }
  .lt-hero p { color:#edf8fa; margin:0; max-width:74ch; line-height:1.55; }
  .lt-badges { display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; }
  .lt-badge { background:#ffffff20; border:1px solid #ffffff70; border-radius:999px;
              color:#fff; font-size:.76rem; font-weight:700; padding:6px 10px; }
  .lt-section { margin-top:24px; }
  .lt-section h2 { font-size:1.5rem; color:var(--lt-ink); margin:0 0 9px; }
  .lt-kicker { color:var(--lt-teal); font-size:.73rem; font-weight:800;
               text-transform:uppercase; letter-spacing:.11em; margin-bottom:6px; }
  .lt-intro { color:var(--lt-muted); max-width:95ch; line-height:1.55; }
  .lt-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
             gap:14px; margin-top:16px; }
  .lt-card { border:1px solid var(--lt-edge); border-radius:16px; background:#fff;
             padding:18px 20px; box-shadow:0 4px 17px #14213d09; }
  .lt-card h3 { font-size:1.02rem; margin:0 0 7px; color:#123a68; }
  .lt-card p, .lt-card li { color:#334155; line-height:1.52; }
  .lt-card p { margin:4px 0 11px; }
  .lt-card ul { margin:6px 0 0; padding-left:20px; }
  .lt-note { border-left:4px solid #f59e0b; background:#fffbeb; padding:13px 16px;
             border-radius:0 11px 11px 0; color:#713f12; line-height:1.48; }
  .lt-source { display:inline-block; font:600 .73rem ui-monospace,SFMono-Regular,monospace;
               color:#365a79; background:#eaf2f8; border-radius:6px; padding:3px 6px;
               overflow-wrap:anywhere; }
  .lt-chip { display:inline-block; border-radius:999px; padding:5px 9px;
             font-size:.72rem; font-weight:800; border:1px solid currentColor; }
  .lt-positive_exploratory_proxy { color:#065f46; background:#d1fae5; }
  .lt-analysis_only_recovery { color:#075985; background:#e0f2fe; }
  .lt-auto_proxy_signal { color:#115e59; background:#ccfbf1; }
  .lt-null { color:#1e40af; background:#dbeafe; }
  .lt-failed, .lt-not_interpretable { color:#991b1b; background:#fee2e2; }
  .lt-unavailable { color:#92400e; background:#fef3c7; }
  .lt-descriptive { color:#3730a3; background:#e0e7ff; }
  .lt-recovered_unbound { color:#9d174d; background:#fce7f3; }
  .lt-not_run, .lt-not_inspected { color:#475569; background:#f1f5f9; }
  .lt-legend { display:flex; flex-wrap:wrap; gap:8px; margin:13px 0; }
  .lt-statline { display:flex; flex-wrap:wrap; gap:10px; margin:13px 0; }
  .lt-stat { background:#fff; border:1px solid var(--lt-edge); border-radius:12px;
             padding:10px 14px; min-width:130px; }
  .lt-stat strong { display:block; font-size:1.2rem; color:#123a68; }
  .lt-stat span { color:var(--lt-muted); font-size:.78rem; }
  .lt-route { display:grid; grid-template-columns:repeat(5,minmax(150px,1fr));
              gap:10px; margin:17px 0; }
  .lt-route-item { position:relative; background:#fff; border:1px solid var(--lt-edge);
                   border-top:5px solid #0f766e; border-radius:12px; padding:13px; }
  .lt-route-item strong { display:block; font-size:.93rem; color:#123a68; }
  .lt-route-item small { color:var(--lt-muted); line-height:1.4; display:block; margin-top:7px; }
  .lt-route-num { color:#0f766e; font-weight:800; font-size:.73rem; margin-bottom:5px; }
  .lt-levels { display:grid; grid-template-columns:repeat(7,minmax(75px,1fr)); gap:8px; }
  .lt-level { border-radius:10px; padding:11px 7px; text-align:center; background:#edf2f7;
              border:1px solid #cfd9e4; font-weight:800; color:#516174; }
  .lt-level.current { background:#d1fae5; color:#065f46; border-color:#0f766e; }
  .lt-timeline { margin:12px 0 0; padding:0 0 0 19px; border-left:3px solid #b5c9dc; }
  .lt-event { position:relative; margin:0 0 14px; padding:12px 16px;
              border:1px solid var(--lt-edge); border-radius:12px; background:#fff; }
  .lt-event:before { content:''; position:absolute; left:-26px; top:16px; width:11px;
                     height:11px; border-radius:50%; background:#0f766e; border:2px solid white; }
  .lt-event h3 { font-size:1rem; margin:4px 0 6px; }
  .lt-event .meta { color:var(--lt-muted); font-size:.76rem; }
  .lt-event p { color:#334155; line-height:1.46; margin:5px 0; }
  .lt-source-row { padding:13px 0; border-bottom:1px solid var(--lt-edge); }
  .lt-source-row p { margin:5px 0; color:#526179; }
  .lt-mini { font-size:.77rem; color:#64748b; }
  .lt-svg-wrap { overflow-x:auto; border:1px solid var(--lt-edge); border-radius:14px;
                 background:white; padding:8px; margin-top:15px; }
  @media(max-width:850px) { .lt-route { grid-template-columns:repeat(2,minmax(150px,1fr)); }
    .lt-hero { padding:22px; } }
  @media(max-width:450px) { .lt-route { grid-template-columns:1fr; } }
</style>
"""


def hero_html(claims: Iterable[Mapping[str, object]], warnings: Iterable[str]) -> str:
    claims = list(claims)
    e0 = sum(item.get("evidence_level") == "E0" for item in claims)
    warning_count = len(list(warnings))
    return (
        '<div class="lt-page"><header class="lt-hero">'
        '<div class="lt-eyebrow">Latent-TRIZ · local research guide</div>'
        '<h1>See the whole investigation</h1>'
        '<p>Explore the hypotheses, model studies, decisions and open evidence '
        'gates through their recorded sources. Each view is a local snapshot.</p>'
        '<div class="lt-badges">'
        '<span class="lt-badge">Read-only pilot</span>'
        '<span class="lt-badge">Local checkout · not live GitHub</span>'
        f'<span class="lt-badge">Formal claims: {e0}/{len(claims)} at E0</span>'
        f'<span class="lt-badge">Source warnings: {warning_count}</span>'
        '</div></header></div>'
    )


def overview_html(data: Mapping[str, object]) -> str:
    claims = list(data["claims"])
    observations = list(data["observations"])
    by_status = Counter(item["status"] for item in observations)
    exp1_null = sum(
        item["campaign"] == "EXP-001 comparative" and item["status"] == "null"
        for item in observations
    )
    early_proxy = all(
        any(item["campaign"] == campaign and item["status"] == "positive_exploratory_proxy"
            for item in observations)
        for campaign in ("A0", "A0-R1")
    )
    c3_recovery = any(
        item["campaign"] == "A0-R2-C3" and item["status"] == "analysis_only_recovery"
        for item in observations
    )
    early_text = (
        "A0 and A0-R1 report positive automated-proxy signals; C3 is an "
        "analysis-only recovery. These remain exploratory observations."
        if early_proxy and c3_recovery else
        "Early proxy-package status is incomplete in this local catalogue; "
        "inspect the individual source records before drawing a conclusion."
    )
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Start here</div>'
        '<h2>What is being tested?</h2>'
        '<p class="lt-intro">The weak hypothesis asks whether a language model '
        'has a transferable internal representation of an inventive operation. '
        'The strong hypothesis asks whether a model trained without TRIZ source '
        'language develops a comparable operator. Both require tests beyond '
        'recognizing words or reusing known examples.</p>'
        '<div class="lt-grid">'
        '<div class="lt-card"><h3>Observed so far</h3><p>' + _e(early_text) + '</p>'
        f'<p><strong>{exp1_null} separate model packages in EXP-001</strong> '
        'are recorded as null under their frozen protocol.</p>'
        + _source("results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json") + ' '
        + _source("results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json") + ' '
        + _source("results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/publication-manifest.json")
        + '</div>'
        '<div class="lt-card"><h3>What remains open</h3><p>Independent TRIZ '
        'expert construct validation, cross-domain controls, causal intervention '
        'and replication remain scientific gates. A proxy signal does not '
        'establish a general TRIZ mechanism.</p>'
        + _source("docs/EVIDENCE_LADDER.md") + '</div>'
        '<div class="lt-card"><h3>How to read this observatory</h3><p>The '
        'matrix shows what happened to each model in each distinct study. '
        'The results view explains one study at a time. The source explorer '
        'shows where each statement comes from.</p>'
        + _source("data/claims.jsonl") + '</div></div>'
        '<div class="lt-statline">'
        f'<div class="lt-stat"><strong>{len(claims)}</strong><span>registered formal claims</span></div>'
        f'<div class="lt-stat"><strong>{by_status.get("positive_exploratory_proxy", 0)}</strong><span>exploratory proxy cells</span></div>'
        f'<div class="lt-stat"><strong>{by_status.get("analysis_only_recovery", 0)}</strong><span>analysis-only recovery cells</span></div>'
        f'<div class="lt-stat"><strong>{by_status.get("auto_proxy_signal", 0)}</strong><span>AUTO proxy signal cells</span></div>'
        f'<div class="lt-stat"><strong>{by_status.get("null", 0)}</strong><span>null cells across distinct studies</span></div>'
        '</div><div class="lt-note">Cell counts describe the local catalog, '
        'not pooled evidence or a measure of the probability that a hypothesis is true. '
        'The source pages may be older than this checkout.</div></div>'
    )


def legend_html() -> str:
    return '<div class="lt-legend">' + ''.join(_chip(key) for key in STATUS_LABELS) + '</div>'


def matrix_rows(
    observations: Iterable[Mapping[str, object]],
    models: Iterable[str],
    campaigns: Iterable[str],
    *,
    status_filter: str = "All",
) -> list[dict[str, str]]:
    selected = {(item["model"], item["campaign"]): item for item in observations}
    def cell(model: str, campaign: str) -> str:
        item = selected.get((model, campaign))
        if item is None:
            return STATUS_LABELS["not_inspected"]
        status = str(item.get("status", "not_interpretable"))
        if status == "not_inspected":
            return STATUS_LABELS["not_inspected"]
        if status_filter != "All" and status != status_filter:
            return "Filtered out"
        return STATUS_LABELS.get(status, STATUS_LABELS["not_interpretable"])
    return [
        {"Model": model, **{
            campaign: cell(model, campaign)
            for campaign in campaigns
        }}
        for model in models
    ]


def matrix_status_style(_row: str, column: str, value: object) -> dict[str, str]:
    if column == "Model":
        return {"fontWeight": "700", "color": "#123a68"}
    if value == "Filtered out":
        return {"backgroundColor": "#f8fafc", "color": "#64748b"}
    reverse = {v: k for k, v in STATUS_LABELS.items()}
    status = reverse.get(str(value), "not_interpretable")
    background, foreground = STATUS_COLORS[status]
    return {"backgroundColor": background, "color": foreground, "fontWeight": "700"}


def source_scope_html(record: Mapping[str, object], sources: Iterable[Mapping[str, object]]) -> str:
    lookup = {str(item.get("path")): item for item in sources}
    paths = record.get("source_paths") or [record.get("source", "")]
    scopes = {str(lookup[path].get("source_scope", "")) for path in paths if path in lookup}
    states = {str(lookup[path].get("vcs_state", "")) for path in paths if path in lookup}
    if "untracked" in states:
        return '<p class="lt-note"><strong>Local untracked source; public publication is unverified.</strong></p>'
    if "tracked_modified" in states:
        return '<p class="lt-note"><strong>Locally modified source; this view may differ from GitHub.</strong></p>'
    if any("historical" in scope for scope in scopes):
        return '<p class="lt-mini">Historical source; verify current applicability.</p>'
    return ""


def matrix_detail_html(record: Mapping[str, object] | None,
                       sources: Iterable[Mapping[str, object]] = ()) -> str:
    if record is None:
        return (
            '<div class="lt-card"><h3>Inspect one pair</h3><p>Choose one '
            'campaign and one model in the filters above. Its outcome, scope '
            'and source will appear here. The recorded-state filter may hide it.</p></div>'
        )
    source_paths = record.get("source_paths") or [record.get("source", "")]
    source_chips = ''.join(_source(path) + ' ' for path in source_paths if path)
    return (
        '<div class="lt-card"><div class="lt-kicker">Selected record</div>'
        f'<h3>{_e(record.get("model", "?"))} · {_e(record.get("campaign", "?"))}</h3>'
        f'<p>{_chip(str(record.get("status", "not_interpretable")))}</p>'
        f'<p><strong>Scope:</strong> {_e(record.get("scope", "Not stated"))}</p>'
        f'<p>{_e(record.get("notes", ""))}</p>'
        + source_scope_html(record, sources) + f'<div>{source_chips}</div></div>'
    )


def coverage_summary_html(observations: Iterable[Mapping[str, object]]) -> str:
    items = list(observations)
    counts = Counter(str(item["status"]) for item in items)
    segments = ''.join(
        f'<div class="lt-stat"><strong>{counts.get(status, 0)}</strong>'
        f'<span>{_e(label)}</span></div>'
        for status, label in STATUS_LABELS.items()
        if counts.get(status, 0)
    )
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Coverage</div>'
        '<h2>Which model was tested where?</h2>'
        '<p class="lt-intro">Choose a campaign and model in the filters to inspect their recorded '
        'state. The matrix preserves gaps, unavailable runs and terminal '
        'results as different categories. Filters change the visible denominator.</p>'
        f'<div class="lt-statline">{segments}</div>{legend_html()}</div>'
    )


def categorical_bar_svg(observations: Iterable[Mapping[str, object]], campaign: str) -> str:
    """Small descriptive status chart for one campaign; no cross-study pooling."""
    items = [item for item in observations if item["campaign"] == campaign]
    counts = Counter(str(item["status"]) for item in items)
    count = len(items)
    width, bar_x, bar_w = 850, 180, 620
    rows = []
    cursor = 45
    for status in STATUS_LABELS:
        n = counts.get(status, 0)
        if not n:
            continue
        bg, fg = STATUS_COLORS[status]
        fill_w = max(3, bar_w * n / max(count, 1))
        rows.append(
            f'<text x="12" y="{cursor + 18}" font-size="14" fill="#263b55">'
            f'{_e(STATUS_LABELS[status])}</text>'
            f'<rect x="{bar_x}" y="{cursor}" width="{bar_w}" height="28" '
            'rx="6" fill="#edf2f7"/>'
            f'<rect x="{bar_x}" y="{cursor}" width="{fill_w:.1f}" height="28" '
            f'rx="6" fill="{bg}" stroke="{fg}"/>'
            f'<text x="{bar_x + bar_w + 10}" y="{cursor + 19}" font-size="14" '
            f'fill="{fg}" font-weight="700">{n}</text>'
        )
        cursor += 42
    if not rows:
        return '<p>No inspected categorical outcomes in this campaign.</p>'
    return (
        '<div class="lt-svg-wrap">'
        f'<svg viewBox="0 0 {width} {cursor + 6}" role="img" '
        f'aria-label="Outcome categories for {_e(campaign)}, {count} visible records" '
        'style="width:100%;min-width:650px;max-height:420px">'
        + ''.join(rows) + '</svg></div>'
    )


def results_header_html(campaign: str, observations: Iterable[Mapping[str, object]]) -> str:
    items = [item for item in observations if item["campaign"] == campaign]
    inspected = sum(item["status"] not in {"not_inspected", "not_run"} for item in items)
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Results</div>'
        f'<h2>{_e(campaign)}</h2><p class="lt-intro">{len(items)} model cells, '
        f'{inspected} with an inspected status in this protocol or analysis layer. '
        'The figure shows categorical states, including missing coverage; '
        'it does not combine experiments or evaluate a general TRIZ claim.</p>'
        + categorical_bar_svg(items, campaign) + '</div>'
    )


def result_source_paths(
    records: Iterable[Mapping[str, object]], campaign: str, allowed_paths: set[str]
) -> list[str]:
    """Offer only cited, admitted sources for the selected study."""
    return sorted({
        path
        for item in records if item.get("campaign") == campaign
        for path in item.get("source_paths", [])
        if isinstance(path, str) and path in allowed_paths
    })


ROUTE_STAGES = (
    ("Decodability", "Can a frozen probe read the proposed operation from a representation?",
     "Held-out labels, layer controls and lexical controls.", "docs/HYPOTHESES_AND_FALSIFICATION.md"),
    ("Geometry", "Are the relevant directions or subspaces stable and interpretable?",
     "Across cases, layers and matched negative directions.", "docs/LAB05.md"),
    ("Generalization", "Does the same relationship transfer to new problems and domains?",
     "Held-out families, sources, domains and formulations.", "docs/HYPOTHESES_AND_FALSIFICATION.md"),
    ("Causality", "Does a controlled intervention change the selected operation?",
     "Steering, ablation, dose, opposite-sign and capability-preservation tests.", "docs/LAB06.md"),
    ("Compositionality", "Can two operations combine predictably?",
     "Two-operation and contradiction tasks only after the single-operator causal gate passes.", "docs/HYPOTHESES_AND_FALSIFICATION.md"),
)


def route_html(selected_stage: str, claims: Iterable[Mapping[str, object]]) -> str:
    claims = list(claims)
    nodes = ''.join(
        '<div class="lt-route-item">'
        f'<div class="lt-route-num">STEP {index}</div><strong>{_e(title)}</strong>'
        f'<small>{_e(question)}</small></div>'
        for index, (title, question, _controls, _source_path) in enumerate(ROUTE_STAGES, 1)
    )
    chosen = next((item for item in ROUTE_STAGES if item[0] == selected_stage), ROUTE_STAGES[0])
    e0 = sum(item.get("evidence_level") == "E0" for item in claims)
    levels = ''.join(
        f'<div class="lt-level{" current" if i == 0 else ""}">E{i}</div>' for i in range(7)
    )
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Scientific route</div>'
        '<h2>Five questions and their prerequisites</h2>'
        '<p class="lt-intro">This route organizes research questions, not completed milestones. '
        'Expert validation of the TRIZ construct and labels remains a separate prerequisite; '
        'composition follows a passing single-operator causal gate. The formal '
        'E0–E6 claim ladder below is a separate, cumulative evidence policy.</p>'
        f'<div class="lt-route">{nodes}</div>'
        '<div class="lt-card"><h3>' + _e(chosen[0]) + '</h3>'
        '<p><strong>Question:</strong> ' + _e(chosen[1]) + '</p>'
        '<p><strong>Required checks:</strong> ' + _e(chosen[2]) + '</p>'
        '<p><strong>Current boundary:</strong> this local catalogue contains no '
        'completed, claim-linked proof of this stage.</p>'
        + _source(chosen[3]) + '</div>'
        '<div class="lt-section"><div class="lt-kicker">Formal claims</div>'
        f'<h2>{e0} of {len(claims)} registered claims remain E0</h2>'
        f'<div class="lt-levels">{levels}</div>'
        '<p class="lt-mini">Levels are cumulative proof obligations, not a '
        'generic maturity score. A result package does not change a claim level '
        'until the claim registry links and qualifies it.</p>'
        + _source("data/claims.jsonl") + ' ' + _source("docs/EVIDENCE_LADDER.md")
        + '</div></div>'
    )


def timeline_html(decisions: Iterable[Mapping[str, object]], category: str = "All") -> str:
    items = [item for item in decisions if category == "All" or item.get("category") == category]
    cards = ''.join(
        '<article class="lt-event">'
        f'<div class="meta">{_e(item.get("declared_date") or "Undated in source")}'
        f' · {_e(item.get("category", "Decision"))} · {_e(item.get("id", ""))}</div>'
        f'<h3>{_e(item.get("title", "Untitled"))}</h3>'
        f'<p>{_e(item.get("notes", ""))}</p>'
        + _source(item.get("source", "")) + '</article>'
        for item in items
    )
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Decisions and lessons</div>'
        '<h2>Why did the laboratory take this route?</h2>'
        '<p class="lt-intro">This is a curated, incomplete timeline. Dates are '
        'shown only when stated in the source; file order is not a date.</p>'
        f'<div class="lt-statline"><div class="lt-stat"><strong>{len(items)}</strong>'
        f'<span>visible entries</span></div></div><div class="lt-timeline">{cards}</div></div>'
    )


def source_list_html(sources: Iterable[Mapping[str, object]], query: str = "") -> str:
    source_list = list(sources)
    needle = query.strip().casefold()
    selected = [
        item for item in source_list
        if not needle or needle in (
            str(item.get("path", "")) + " " + str(item.get("family", "")) + " "
            + FAMILY_QUESTIONS.get(str(item.get("family", "")), "")
        ).casefold()
    ]
    cards = ''.join(
        '<div class="lt-source-row">'
        + _source(item.get("path", ""))
        + f'<p><strong>Question:</strong> {_e(FAMILY_QUESTIONS.get(str(item.get("family", "")), "What does this source record?"))}</p>'
        + f'<p>Family: {_e(item.get("family", "unknown"))} · '
        f'Declared date: {_e(item.get("declared_date") or "not stated")} · '
        f'Freshness: {_e(item.get("freshness") or "unknown")} · '
        f'Git: {_e(item.get("vcs_state") or "unknown")}</p>'
        f'<p class="lt-mini">Scope: {_e(item.get("source_scope") or "not stated")}</p>'
        f'<p class="lt-mini">Local SHA-256: {_e(item.get("sha256", ""))}</p>'
        + (
            '<p class="lt-mini">Warnings: '
            + _e("; ".join(map(str, item.get("stale_markers", []) + item.get("conflict_markers", []))))
            + '</p>'
            if item.get("stale_markers") or item.get("conflict_markers") else ''
        )
        + '</div>'
        for item in selected
    )
    if not cards:
        cards = '<div class="lt-note">No allowlisted source matches this search.</div>'
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Explore sources</div>'
        '<h2>A map of the documents</h2>'
        '<p class="lt-intro">This catalogue contains selected public, local '
        'files. A local hash identifies bytes, while each document’s date and '
        'scope determine how to read it.</p>'
        f'<div class="lt-statline"><div class="lt-stat"><strong>{len(selected)}</strong>'
        f'<span>visible of {len(source_list)} allowlisted sources</span></div></div>{cards}</div>'
    )


def guided_questions_html() -> str:
    return (
        '<div class="lt-page lt-section"><div class="lt-kicker">Guided tour</div>'
        '<h2>Five questions to try</h2><div class="lt-grid">'
        '<div class="lt-card"><h3>1 · Proxy or claim?</h3><p>Find the A0/R1 '
        'outcomes, then inspect the formal claims in Scientific route.</p></div>'
        '<div class="lt-card"><h3>2 · What is missing?</h3><p>Use the '
        'experiment matrix and its explicit not-run and unavailable states.</p></div>'
        '<div class="lt-card"><h3>3 · Why Qwen3 null?</h3><p>Inspect its '
        'EXP-001 cell and the corresponding report.</p></div>'
        '<div class="lt-card"><h3>4 · Beyond E0?</h3><p>Read the Evidence '
        'Ladder beside the five-stage route.</p></div>'
        '<div class="lt-card"><h3>5 · Why this next step?</h3><p>Filter '
        'the decision timeline, then use Explore sources → Preview one allowlisted '
        'source to inspect a cited roadmap or hypothesis document.</p></div></div></div>'
    )


def result_cards_html(records: Iterable[Mapping[str, object]],
                      sources: Iterable[Mapping[str, object]] = ()) -> str:
    records = list(records)
    if not records:
        return '<div class="lt-note">No allowlisted result in this selection.</div>'
    cards = ''.join(
        '<article class="lt-card">'
        f'<h3>{_e(item.get("model", "?"))}</h3>'
        f'<p>{_chip(str(item.get("status", "not_interpretable")))}</p>'
        f'<p>{_e(item.get("notes", ""))}</p>'
        f'<p class="lt-mini">Scope: {_e(item.get("scope", "not stated"))}</p>'
        + source_scope_html(item, sources)
        + ''.join(
            _source(path) + ' ' for path in
            (item.get("source_paths") or [item.get("source", "")]) if path
        )
        + '</article>'
        for item in records
    )
    return f'<div class="lt-page lt-section"><div class="lt-grid">{cards}</div></div>'


def source_preview_html(path: str, text: str) -> str:
    return (
        '<div class="lt-page lt-section"><div class="lt-card">'
        f'<h3>Source preview · {_e(path)}</h3>'
        '<p class="lt-mini">First bounded excerpt from this allowlisted local '
        'file. Review the full file for its complete scope.</p>'
        '<pre style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:320px;'
        'overflow:auto;background:#f7fafc;padding:14px;border-radius:9px">'
        f'{_e(text)}</pre></div></div>'
    )


def source_warnings_html(warnings: Iterable[str]) -> str:
    warnings = list(warnings)
    if not warnings:
        return ''
    rendered = ''.join(f'<li>{_e(warning)}</li>' for warning in warnings)
    return (
        '<div class="lt-page lt-section"><div class="lt-note">'
        '<strong>Source freshness and coverage warnings</strong>'
        f'<ul>{rendered}</ul></div></div>'
    )
