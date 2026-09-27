# Research Observatory GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the existing six-view Research Observatory as a verified, accessible GitHub Pages snapshot without changing the canonical evidence process.

**Architecture:** A Python build-time exporter validates the existing public source inventory and emits one bounded JSON document. Dependency-free HTML/CSS/JavaScript renders that document on GitHub Pages. A read-only pull-request build and a separately privileged `main` deployment use pinned GitHub Actions.

**Tech Stack:** Python 3.11 and existing Observatory modules; the repository's hash-locked `requirements-schema.lock` for YAML workflow tests; vanilla JavaScript with Node 22 built-in tests; GitHub Actions and Pages.

**Spec:** `docs/superpowers/specs/2026-09-27-research-observatory-github-pages-design.md`

## Global Constraints

- Work in a clean isolated clone; preserve the dirty primary checkout and historical research artifacts.
- No models, tokenizers, sealed targets, private mappings, scoring, CCP, Docker, external browser scripts, analytics, or GitHub API polling.
- Keep the local Marimo app optional and unchanged. The website is a derived snapshot, not evidence or a live monitor; issue #119 tracks self-updating behavior.
- Export only reviewed public fields from `source-inventory.json`; v1 exports **zero raw source excerpts or previews**. Every admitted source path must have an exact-path-bound, reviewed, authored two-sentence editorial synopsis; no generic fallback. The TRIZ corpus is citation-only. No third-party PDFs or provider text. Preserve all 11 statuses in `observatory_views.STATUS_LABELS`, distinct campaigns, E0-only claim interpretation, and null/failure/missing boundaries.
- Bind the export to a clean, complete Git HEAD/tree, inventory-file SHA-256, and separate path/hash catalogue digest. Unknown inputs fail closed.
- Generate the disposable site directory outside the Git checkout so the build itself cannot make source provenance dirty.
- Pull-request jobs have `contents: read` only and no secrets or deploy token. `main` deployment is a dependent job with `pages: write`, `id-token: write`, and `github-pages` environment. Pin every action to a reviewed full commit.
- Never claim the Pages URL is live until a deployed HTTPS visit verifies it. Run `rtk` at the start of every shell command.

## Review Focus

1. Historical inventory base differs from build HEAD: display both accurately, reject missing Git identity, never label inventory base as current `main` (Task 1 tests).
2. A newly introduced status or claim level: reject unknown status and render future claim content as unverified, never silently classify it as positive (Tasks 1–2 tests).
3. Catalogue path lacks a reviewed synopsis, or a source record contains a hostile description, markup, control characters, or malicious URL: reject missing/extra/duplicate synopsis coverage, ignore source-derived descriptions, render authored synopsis text only, and construct GitHub links from admitted paths plus exact commit (Tasks 1–2 tests).
4. Missing data file, failed build, or stale browser cache: show a visible error/staleness state; do not show an empty success dashboard or deploy failed output (Tasks 2–3 tests).
5. Fork pull request changing build code: run without secrets/deploy permission, and never execute a privileged `pull_request_target` build (Task 3 workflow test).

## File structure

- `scripts/research_observatory/site_export.py`: strict source identity, public-field admission, canonical JSON, source-integrity checks without excerpt export, output-directory writing.
- `scripts/research_observatory/site_synopses.py`: complete path-bound authored synopsis catalogue; fail closed on missing, extra, duplicate, or empty entries.
- `scripts/research_observatory/test_site_export.py`: export contract and refusal tests using disposable synthetic Git repositories.
- `scripts/research_observatory/site/index.html`, `site/style.css`, `site/app.mjs`: dependency-free six-view browser UI; `site/app.mjs` exports pure selectors/render-model helpers for Node tests.
- `scripts/research_observatory/site/test_app.mjs`: Node built-in tests for status/filter/navigation/escaping/link semantics.
- `scripts/research_observatory/test_site_build.py`: end-to-end build/oracle/artifact audit tests.
- `.github/workflows/research-observatory-pages.yml` and `tests/test_research_observatory_pages_workflow.py`: unprivileged PR build, main-only deployment, and workflow-policy assertions.
- `README.md` and `scripts/research_observatory/README.md`: snapshot/Marimo distinction and verified public link only after deployment.

### Task 1: Strict public data export

**Files:** Create `scripts/research_observatory/site_export.py`, `scripts/research_observatory/site_synopses.py`, and `scripts/research_observatory/test_site_export.py`.

**Interfaces:** Consume `observatory_data.load_observatory(repo_root, strict_public=True)`, source-integrity verification, `site_synopses.SOURCE_SYNOPSES`, `observatory_views.STATUS_LABELS`, and `source-inventory.json`. Produce `build_public_payload(repo_root: Path, *, expected_head: str, generated_at: str) -> dict[str, object]` and `write_public_payload(payload: Mapping[str, object], destination: Path) -> Path`.

- [ ] Write tests named `test_rejects_missing_or_mismatched_git_identity`, `test_rejects_dirty_or_mutated_inventory`, `test_rejects_unknown_status_and_future_claim_promotion`, `test_exports_only_reviewed_fields_and_source_specific_synopses`, and `test_records_distinct_inventory_and_catalogue_digests`. Use synthetic repositories and assert exact accepted keys, all 11 status values, zero `preview`/excerpt fields, exact two-sentence synopsis coverage for every catalogue path, no raw source/provider text, and no absolute local paths. Also prove stale `summary`/`description` fields from source metadata cannot override the authored catalogue.
- [ ] Run `rtk python3 -m unittest scripts.research_observatory.test_site_export -v`; confirm the new tests fail for missing implementation, not bad fixtures.
- [ ] Implement the two interfaces. Require full 40-hex `expected_head`, exact `HEAD`, valid 40-hex tree, clean checkout, regular single-link inventory and sources, exact inventory entry hashes, explicit record-field allowlists, and complete exact-path synopsis catalogue validation. Verify source bytes/hashes without exporting excerpts. Build-source identity and historical inventory base are separate fields. Reject an unknown schema/status; never convert it to a positive label. Write canonical UTF-8 JSON to a new regular file without overwrite.
- [ ] Re-run the targeted tests and existing `rtk python3 -m unittest scripts.research_observatory.test_observatory_data -v`; expect PASS.
- [ ] Commit only this task's exporter and tests.

### Task 2: Six-view static browser

**Files:** Create `scripts/research_observatory/site/index.html`, `site/style.css`, `site/app.mjs`, and `site/test_app.mjs`.

**Interfaces:** Consume `research-observatory-site-v1` from Task 1. Export pure `selectMatrix(records, filters)`, `selectSources(sources, query)`, `sourceUrl(head, path)`, and `renderViewModel(payload, view, filters)` from `app.mjs`; browser startup fetches only same-origin `site-data.json`.

- [ ] Write Node tests for all six view models, every current status, campaign/model/status filters, result-to-source links, route stages, decision categories, source synopsis search/selection, unknown-status refusal, and malicious synopsis/path input. Use a tiny injected fake DOM to assert synopsis content enters through `textContent`/`createTextNode`, not `innerHTML`; URLs contain only admitted paths and the exact HEAD.
- [ ] Run `rtk node --test scripts/research_observatory/site/test_app.mjs`; confirm expected missing-implementation failure.
- [ ] Implement accessible navigation, explicit weak/strong hypothesis panels, E0–E6 legend, matrix/result/route/decision/source views, two-line authored per-source synopses, a visible snapshot timestamp and not-live notice, and visible data-load failure. Use relative site assets so `/Latent-TRIZ/` and local preview both work. No external fonts, scripts, analytics, tokens, or automatic GitHub API requests.
- [ ] Run targeted Node tests and `rtk node --check scripts/research_observatory/site/app.mjs`; expect PASS. Commit browser files only.

### Task 3: Hermetic build and parity audit

**Files:** Create `scripts/research_observatory/test_site_build.py`; extend `site_export.py` with `build_site(repo_root: Path, destination: Path, *, expected_head: str, generated_at: str) -> Path` and a `python -m scripts.research_observatory.site_export` CLI.

**Interfaces:** Consume Task 1 payload and Task 2 static assets; produce exactly `index.html`, `style.css`, `app.mjs`, and `site-data.json` under a new destination directory.

- [ ] Write tests `test_build_matches_local_observatory_oracle`, `test_refuses_occupied_or_linked_destination`, and `test_bundle_excludes_private_and_external_assets`. Compare claims, 35 matrix cells, 66 sources, warnings, and route labels to the local oracle at the candidate HEAD; verify deterministic bytes with fixed `generated_at` and scan all output files.
- [ ] Run `rtk python3 -m unittest scripts.research_observatory.test_site_build -v`; confirm expected failure before code.
- [ ] Implement the build CLI and atomic output staging. Refuse unexpected output members, symlinks/hardlinks, oversized JSON, private paths, prohibited file classes, and external assets. Do not copy source documents or PDFs. On failure leave no partial public directory.
- [ ] Run targeted Python and Node tests, then build from a fresh clean clone outside the repository; verify four output members and the exact source binding. Commit build code/tests.

### Task 4: Least-privilege Pages workflow

**Files:** Create `.github/workflows/research-observatory-pages.yml` and `tests/test_research_observatory_pages_workflow.py`.

**Interfaces:** Consume Task 3 CLI. Build on pull requests and `main` push; upload only the four-member site artifact after tests. Deploy only from `main`, after build success, in the `github-pages` environment.

- [ ] Write tests that parse workflow YAML with the existing `PyYAML==6.0.3` from `requirements-schema.lock` and assert `permissions: {}` by default, `contents: read` in build, no secrets or `pull_request_target`, main-only deploy with `pages: write` and `id-token: write`, dependency on build, exact-HEAD checkout, and immutable action references.
- [ ] Run `rtk python3 -m unittest tests.test_research_observatory_pages_workflow -v`; confirm expected missing-workflow failure.
- [ ] Implement workflow with repository-pinned checkout `3d3c42e5aac5ba805825da76410c181273ba90b1`; pinned `actions/setup-python` `a309ff8b426b58ec0e2a45f0f869d46889d02405`; pinned `actions/setup-node` `49933ea5288caeca8642d1e84afbd3f7d6820020`; pinned `actions/configure-pages` `983d7736d9b0ae728b81ab479565c72886d7745b`; pinned `actions/upload-pages-artifact` `7b1f4a764d45c48632c6b24a0339c27f5614fb0b`; pinned `actions/deploy-pages` `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e`. Configure Python 3.11 and Node 22; install only existing hash-locked `requirements-schema.lock` for workflow-policy tests, no npm packages; disable credential persistence. Run tests on PR, but upload/deploy the Pages artifact only on `main`. Reverify these upstream SHAs before publication.
- [ ] Run workflow-policy tests and repository checks; expect PASS. Commit workflow/tests.

### Task 5: Documentation, review, and public verification

**Files:** Modify `README.md` and `scripts/research_observatory/README.md` only after the deployed URL is verified; create a short release/operation note under `docs/qualification/` with exact commit, site-data SHA-256, workflow run, Pages URL, freshness boundary, and browser checks.

**Interfaces:** Consume verified Task 1–4 output and hosted checks. Do not change canonical results, claims, model artifacts, or evidence gates.

- [ ] Run full deterministic Python/Node checks and `rtk git diff --check` from the exact candidate; inspect the four-member site directory and compare with the local Observatory oracle. Request independent Sol code and security reviews before publication; repair any blocking finding.
- [ ] In a real browser, visit all six views and exercise every interaction named in the spec. Record desktop and representative mobile viewport results, full keyboard-only operation/focus visibility, and inspect the browser accessibility tree for exposed names, roles, and states. This does not require or claim a full screen-reader/assistive-technology or usability validation. A blocked or unavailable mobile/keyboard/browser accessibility-tree check is `INCONCLUSIVE`, not PASS; leave the relevant release gate open and do not claim full accessibility.
- [ ] Push a single reviewed branch, open a PR, and observe existing required checks plus the new site build. Do not merge while any gate is pending or failing.
- [ ] After PR gates pass, configure Pages source as GitHub Actions before merging, if not already configured. This is an external repository setting and must be observed/verified, not assumed from workflow code. Recheck exact head/base and required gates, merge, then verify the merge-triggered HTTPS deployment, source commit, and `site-data.json` hash. Only then add the live link to README and Observatory docs in a follow-up reviewed PR. If Pages configuration or deployment fails, keep documents honest and report the precise external gate.

## Handoff

The user asked to delegate as much safe bounded work as possible to GPT-6 Luna. Use Luna workers with exclusive file ownership for Tasks 1–4, integrate centrally, and request Sol review for the public-data and deployment trust boundaries. Keep a single writer for each file group. No task review or model opinion substitutes for tests, GitHub gates, or explicit external authorization.
