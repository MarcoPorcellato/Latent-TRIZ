# Research Observatory (optional)

This Marimo app is a read-only map of selected public Latent-TRIZ records. It
helps newcomers find experiments, model coverage, decisions, source documents,
and the boundary between exploratory observations and scientific claims. It is
not a result verifier, live GitHub monitor, experiment runner, or evidence for
either Latent TRIZ hypothesis.

The six views are **Start here**, **Experiments × models**, **What results
mean**, **Scientific route**, **Decisions and lessons**, and **Explore sources**.
The current source inventory binds 66 repository files from the public base
commit recorded in `source-inventory.json`; the matrix contains 35 cells from
five distinct campaign layers. Unpublished local result material is deliberately
excluded. Missing, null, failed, and not-interpretable are different states.
The A0-R2-C3 cell is analysis-only recovery, not a third model-run proxy signal.
Known stale navigation documents are shown as source warnings. Source labels
are citations, not links; use the source selector to preview their local bytes.
The registered claims remain governed by `data/claims.jsonl` and
`docs/EVIDENCE_LADDER.md`, not by this app.

The opening view separates the weak pretrained-model hypothesis from the
strong controlled-emergence hypothesis. Scientific route explains the
cumulative E0–E6 obligations without treating its five research questions as
completed milestones. Explore sources shows a short, searchable synopsis for
each of the 66 admitted files instead of a repeated question by file family.
These synopses are derived from the locally hash-inventoried source bytes and
their fixed source roles; they are navigation aids, not new scientific claims.
If a source is missing, its synopsis does not infer an outcome.

## Run locally

From `scripts/research_observatory` in a fresh clone:

```bash
uv run --locked marimo check --strict app.py
uv run --locked marimo run app.py --host 127.0.0.1 --token --headless
```

The first `uv run` may download the pinned optional packages in `uv.lock`; it
does not load models or run experiments. Keep the token private, open the local
URL it prints, and stop the owned process when finished. The app performs no
network requests. It reads only its explicit source inventory and fails closed
if a source is untracked, modified, missing, too large, symlinked, hardlinked,
or no longer matches its recorded SHA-256. The supported source-reading
platform must provide `O_DIRECTORY` and `O_NOFOLLOW`.

The app is optional. The existing `make lab` Lab Suite remains the maintained
one-command laboratory surface and the canonical documents and verifiers
remain authoritative.

## Publication and interpretation

- `source-inventory.json` is a candidate public-source review packet, not
  proof of permission or scientific validity. Review licensing, content, and
  exact hashes before publishing this tool.
- The app shows a local source commit, tree, and catalogue hash. This is not
  proof that its checkout is the current public GitHub `main`.
- Source previews are bounded and escaped. A file changed after snapshot load
  is refused instead of appearing under the old hash.
- Filters never relabel a known outcome as “not inspected.” A nonmatching
  recorded cell is shown as “Filtered out.” Campaigns are not pooled.
- The scientific route shows dependencies, including expert construct
  validation and a single-operator causal gate before composition. It does not
  assert that any stage has been completed.
- The current claim reader only interprets E0 entries. A future E1–E6 claim
  remains uninterpretable here until the canonical proof obligations and this
  derived view are reviewed together.
- The decision view initially covers nine indexed ADRs, not all subsequent
  engineering or research choices. Its categories are a reviewed editorial
  index, not labels inferred from incidental words in the ADR body.

No public live service or GitHub Pages export is included. Such deployment
would require separate review of every rendered or bundled input.
