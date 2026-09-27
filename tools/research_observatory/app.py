"""Local, read-only Marimo observatory for public Latent-TRIZ research records."""

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="full")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo
    import observatory_data as catalog
    import observatory_views as views

    repo_root = catalog.resolve_repository_root(Path(__file__))
    snapshot = catalog.load_observatory(repo_root, strict_public=True)
    return catalog, mo, repo_root, snapshot, views


@app.cell
def _(mo, snapshot, views):
    mo.vstack([
        mo.Html(views.page_css()),
        mo.Html(views.snapshot_banner_html(snapshot)),
        mo.Html(views.hero_html(snapshot["claims"], snapshot["warnings"])),
    ])
    return


@app.cell
def _(mo, snapshot, views):
    view = mo.ui.radio(
        options=list(views.VIEW_TITLES),
        value=views.VIEW_TITLES[0],
        inline=True,
        label="Choose a view",
    )
    campaign_filter = mo.ui.dropdown(
        options=["All", *snapshot["campaign_names"]], value="All",
        label="Campaign", searchable=True,
    )
    model_filter = mo.ui.dropdown(
        options=["All", *snapshot["model_names"]], value="All",
        label="Model", searchable=True,
    )
    status_filter = mo.ui.dropdown(
        options=["All", *views.STATUS_LABELS], value="All", label="Recorded state",
    )
    result_campaign = mo.ui.dropdown(
        options=list(snapshot["campaign_names"]),
        value=snapshot["campaign_names"][0], label="Study to inspect",
        searchable=True,
    )
    stage_selector = mo.ui.dropdown(
        options=[stage[0] for stage in views.ROUTE_STAGES],
        value=views.ROUTE_STAGES[0][0], label="Explore a research stage",
    )
    decision_categories = sorted({item["category"] for item in snapshot["decisions"]})
    decision_filter = mo.ui.dropdown(
        options=["All", *decision_categories], value="All", label="Decision category",
    )
    source_search = mo.ui.text(
        value="", placeholder="Search path or source family",
        label="Find a source", full_width=True,
    )
    source_options = [item["path"] for item in snapshot["sources"]]
    source_selector = mo.ui.dropdown(
        options=source_options, value=source_options[0],
        label="Preview one allowlisted source", searchable=True,
    )
    mo.vstack([view])
    return (
        campaign_filter, decision_filter, model_filter, result_campaign,
        source_search, source_selector, stage_selector, status_filter, view,
    )


@app.cell
def _(catalog, mo, result_campaign, snapshot, views):
    cited_paths = views.result_source_paths(
        snapshot["observations"], result_campaign.value, set(catalog.SOURCE_FAMILIES)
    )
    result_source_selector = mo.ui.dropdown(
        options=cited_paths or ["No admitted source for this study"],
        value=cited_paths[0] if cited_paths else "No admitted source for this study",
        label="Inspect a cited source from this study", searchable=True,
    )
    return result_source_selector,


@app.cell
def _(campaign_filter, mo, model_filter, snapshot, status_filter, views):
    visible_observations = [
        item for item in snapshot["observations"]
        if (campaign_filter.value == "All" or item["campaign"] == campaign_filter.value)
        and (model_filter.value == "All" or item["model"] == model_filter.value)
        and (status_filter.value == "All" or item["status"] == status_filter.value)
    ]
    visible_models = [
        model for model in snapshot["model_names"]
        if model_filter.value == "All" or model == model_filter.value
    ]
    visible_campaigns = [
        campaign for campaign in snapshot["campaign_names"]
        if campaign_filter.value == "All" or campaign == campaign_filter.value
    ]
    matrix_table = mo.ui.table(
        data=views.matrix_rows(
            snapshot["observations"], visible_models, visible_campaigns,
            status_filter=status_filter.value,
        ),
        selection=None, style_cell=views.matrix_status_style,
        show_download=False, show_search=False, show_column_summaries=False,
        show_data_types=False, pagination=False, max_height=550,
        label="Categorical experiment and model coverage matrix",
    )
    return matrix_table, visible_campaigns, visible_models, visible_observations


@app.cell
def _(
    campaign_filter, catalog, decision_filter, matrix_table, mo, model_filter,
    repo_root, result_campaign, result_source_selector, snapshot, source_search, source_selector,
    stage_selector, status_filter, view, views, visible_campaigns,
    visible_models, visible_observations,
):
    if view.value == "Start here":
        page = mo.vstack([
            mo.Html(views.overview_html(snapshot)),
            mo.Html(views.guided_questions_html()),
            mo.Html(views.source_warnings_html(snapshot["warnings"])),
        ])
    elif view.value == "Experiments × models":
        selected_record = None
        if campaign_filter.value != "All" and model_filter.value != "All":
            selected_record = next(
                (item for item in snapshot["observations"]
                 if item["model"] == model_filter.value
                 and item["campaign"] == campaign_filter.value),
                {"model": model_filter.value, "campaign": campaign_filter.value,
                 "status": "not_inspected", "scope": "No allowlisted package was inspected",
                 "notes": "This is a coverage gap, not a null result.", "source_paths": []},
            )
            if status_filter.value != "All" and selected_record["status"] != status_filter.value:
                selected_record = None
        page = mo.vstack([
            mo.hstack([campaign_filter, model_filter, status_filter], widths="equal"),
            mo.Html(views.coverage_summary_html(visible_observations)),
            matrix_table,
            mo.Html(views.matrix_detail_html(selected_record, snapshot["sources"])),
        ])
    elif view.value == "What results mean":
        campaign_records = [
            item for item in snapshot["observations"]
            if item["campaign"] == result_campaign.value
        ]
        cited_source = next(
            (item for item in snapshot["sources"] if item["path"] == result_source_selector.value), None
        )
        cited_preview = (
            catalog.read_allowed_preview(
                repo_root, result_source_selector.value,
                expected_sha256=cited_source["sha256"],
            )
            if cited_source is not None and cited_source["sha256"] is not None else ""
        )
        page = mo.vstack([
            result_campaign,
            mo.Html(views.results_header_html(result_campaign.value, campaign_records)),
            mo.Html(views.result_cards_html(campaign_records, snapshot["sources"])),
            result_source_selector,
            mo.Html(views.source_preview_html(result_source_selector.value, cited_preview)),
        ])
    elif view.value == "Scientific route":
        page = mo.vstack([
            stage_selector,
            mo.Html(views.route_html(stage_selector.value, snapshot["claims"])),
        ])
    elif view.value == "Decisions and lessons":
        page = mo.vstack([
            decision_filter,
            mo.Html(views.timeline_html(snapshot["decisions"], decision_filter.value)),
        ])
    else:
        selected_source = next(
            item for item in snapshot["sources"] if item["path"] == source_selector.value
        )
        preview = (
            catalog.read_allowed_preview(
                repo_root, source_selector.value,
                expected_sha256=selected_source["sha256"],
            )
            if selected_source["sha256"] is not None else ""
        )
        page = mo.vstack([
            source_search,
            mo.Html(views.source_list_html(snapshot["sources"], source_search.value)),
            source_selector,
            mo.Html(views.source_preview_html(source_selector.value, preview)),
        ])
    page
    return


if __name__ == "__main__":
    app.run()
