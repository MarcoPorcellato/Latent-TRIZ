# Research Observatory GitHub Pages Design

## Purpose and boundary

Publish the existing six-view Research Observatory as an accessible project website. A visitor should be able to understand the two hypotheses, browse the model/campaign matrix, interpret outcomes and evidence levels, follow the scientific route, inspect decisions, and find source documents without installing Python or running Marimo. The website is a derived, read-only navigation aid. Repository documents, schemas, result manifests, receipts, and verifiers remain authoritative.

This first release is a verified **curated snapshot**, not a live GitHub monitor. It must state its source commit and generation time and must not claim to show changes that have not been admitted to the source inventory. Automatic near-real-time refresh is separate follow-up work in [issue #119](https://github.com/MarcoPorcellato/Latent-TRIZ/issues/119).

## Chosen approach and alternatives

Generate a small static HTML/CSS/JavaScript site from the existing deterministic Observatory loader at build time. The generator verifies every admitted source before emitting a bounded, versioned public data document. Browser code renders the six views and handles filters and source selection without contacting GitHub or executing Python. The local Marimo app remains available and unchanged.

Ordinary Marimo HTML export would lose the required interactions. Marimo WebAssembly could retain Python interactions but would require porting the current Git/POSIX source-verification path into a browser-compatible data layer and add a larger runtime. Those are valid later options, not dependencies of the first public release.

## Components and interfaces

1. **Admission and export.** A standard-library Python builder calls the existing `load_observatory` path against the checked-out repository and its explicit `source-inventory.json`. It rejects missing, modified, untracked, oversized, symlinked, or hardlinked sources. It also independently requires a clean checkout and complete, valid Git HEAD/tree matching the exact selected source; a missing identity is a build failure even if the existing loader returns null. The inventory's historical `source_base_head`/`source_base_tree` are recorded separately from the build commit and reviewed when changed, not silently presented as current `main`. A separate public-export allowlist selects only the fields required by the six views. The builder emits a canonical `research-observatory-site-v1` data document with build-source HEAD/tree, raw inventory-file SHA-256, catalogue digest, generation timestamp, source paths, source hashes, status classifications, warnings, and path-bound editorial synopses. **Version 1 exports no source excerpts or previews.** Each admitted source path has exactly one reviewed, authored two-sentence synopsis; catalogue changes require explicit synopsis review, with no generic fallback. The inventory-file hash and the loader's path/hash catalogue digest are different fields. It must never include full third-party PDFs, copied provider text, private mappings, sealed targets, raw model assets, or unreviewed local results.
2. **Static viewer.** Reviewed HTML/CSS/JavaScript renders the six existing views, with distinct weak and strong hypotheses, an E0–E6 legend, searchable two-line source synopses, matrix filters, and direct links to the exact GitHub source commit. Render untrusted source-derived strings as text, never as HTML, script, style, or URL code. Relative asset paths must work under `/Latent-TRIZ/` and during local preview.
3. **Publication workflow.** A GitHub Actions workflow builds and tests the site on pull requests with `contents: read`, no repository secrets, no `pull_request_target`, and no deployment permission. On `main`, a successful build uploads only the verified site directory; a dependent deployment job uses `pages: write` and `id-token: write` in the `github-pages` environment. Actions are pinned to reviewed immutable commits. The workflow does not run models, scoring, or CCP.
4. **Documentation.** Root README and Observatory documentation link to the public site once its deployment is verified. They distinguish the local Marimo pilot, the static public snapshot, canonical research evidence, and the later self-updating goal. A failed deployment is not represented as a live site.

## Data and claim rules

- The 66-file inventory at the design baseline is a candidate review packet, not permission to redistribute source contents. Version 1 exports zero raw source excerpts/previews. The site uses exact-path-bound editorial synopses written for navigation; they are not quotations, extracted source text, experimental findings, or substitutes for linked documents. Review each synopsis for accuracy and privacy before deployment. Link to public files rather than bundling documents. The TRIZ consulting corpus contributes citation metadata only; no provider text or third-party PDF is copied into the artifact.
- Preserve parity with every current `STATUS_LABELS` value: `positive_exploratory_proxy`, `analysis_only_recovery`, `auto_proxy_signal`, `null`, `failed`, `unavailable`, `descriptive`, `recovered_unbound`, `not_run`, `not_inspected`, and `not_interpretable`. Unknown states fail closed. Do not pool campaign layers or promote a general TRIZ, causal, or training-data claim.
- Interpret formal claims only at levels supported by the existing local reader. Unknown or future claim schemas fail closed rather than receiving an optimistic label. Website timestamps and hashes establish snapshot identity, not scientific validity.
- Display source HEAD, tree, inventory digest, build time, and an explicit snapshot-not-live notice. If an admitted file drifts, the build fails before an artifact is uploaded; the prior deployed site remains visibly dated.

## Failure handling and security

- Build and deployment are separate jobs. Deployment depends on successful deterministic checks. No preview of untrusted pull-request code has deploy credentials.
- Generated output is confined to one disposable directory. Reject unexpected output paths, links, oversized documents, malformed JSON, unsupported statuses, and non-canonical or missing source references. No private filesystem path or token appears in HTML, JavaScript, data, logs, or artifacts.
- Browser code performs no automatic network requests beyond loading the same-origin site files. No external fonts, analytics, scripts, browser tokens, or GitHub API polling. Source links open public GitHub pages only after a user action.
- GitHub Pages must be configured to publish from GitHub Actions after the PR build passes and before merge/deployment. The first deployment and public URL require live HTTPS verification of the deployed source commit and `site-data.json` binding; until then, documents must not state that the site is available.

## Verification and release criteria

- Unit and mutation tests prove inventory/hash refusal, absent or malformed Git identity rejection, public-field allowlisting, parity for every current status and refusal of unknown statuses, HTML escaping/text-only rendering, URL construction, subpath loading, missing/changed source rejection, and deterministic output apart from the recorded build timestamp.
- Build the site from a fresh clone at the exact candidate HEAD. Compare its claims, matrix cells, source count, warnings, and route labels with the tested local Observatory oracle. Inspect the generated artifact for private paths, secrets, prohibited file families, external requests, and third-party PDFs.
- Exercise all six views and each interaction class in a real browser: campaign/model/status filters, result-to-source navigation, route-stage selection, decision-category selection, source selection and synopsis search. Check at representative mobile widths and complete keyboard-only operation/focus visibility. Inspect the browser accessibility tree for exposed names, roles, and states. Record browser, viewport, interaction coverage, inspection method, and observed result. This is label/accessibility-tree inspection, not a full screen-reader or usability validation; an inconclusive mobile or keyboard pass remains an open release gate.
- Review the final diff and trust-boundary changes independently. Open a pull request; merge only after existing required GitHub gates and the new site build are terminally green. Configure Pages and verify the deployed URL, contents, source binding, and HTTPS before linking it from the README.

## Out of scope

No scientific rerun, model or tokenizer load, sealed-target access, private mapping, claim promotion, API polling, custom domain, analytics, or general-purpose content management system. Issue #119 covers the later measured-freshness, self-updating version.

## Baseline and official platform references

At design time, public `main` is `b604a3d62a2da5e2bfd54a9b08c5179664ad7cc2`; the clean isolated clone is `$ISOLATED_TEMP_ROOT/latent-triz-observatory-verify/repository`. The local Observatory is documented in `scripts/research_observatory/README.md` and is not yet a public Pages export.

- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Configure a Pages publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub Actions security guidance](https://docs.github.com/en/actions/how-tos/secure-your-work)
