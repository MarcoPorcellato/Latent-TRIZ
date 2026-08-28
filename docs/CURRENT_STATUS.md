---
type: status-report
title: Current Laboratory Status
description: Public, receipt-backed snapshot of the Latent-TRIZ laboratory and its evidence boundary.
status: canonical
last_verified: 2026-08-25
---

# Current laboratory status

This page is the short, public status snapshot for the Latent-TRIZ laboratory.
The long-form history remains in the [Laboratory Master Plan](./LABORATORY_MASTER_PLAN.md)
and the event-by-event chronology remains in [`docs/log.md`](./log.md).

## Public checkpoint

- **Public main:** `0123ce467408becbf127b66da1fcd4166bbbd431`
- **Repository:** [MarcoPorcellato/Latent-TRIZ](https://github.com/MarcoPorcellato/Latent-TRIZ)
- **Scientific posture:** exploratory, reproducible, and claim-free
- **Registered claims:** all remain `E0`; `data/claims.jsonl` is unchanged
- **Model execution policy:** exact revision, offline/local-only, one-shot, receipt-backed, and CCP-gated

The repository contains immutable positive automated-proxy packages from A0/R1
and immutable null packages from the reference-integrated and comparative
studies. None is expert-validated TRIZ evidence, causal evidence, or evidence
for the Strong Latent TRIZ Hypothesis.

## What is delivered

### Laboratory and governance

- Apache-2.0 repository with attribution in [`NOTICE`](../NOTICE).
- Maintained documentation bundle, decision records, evidence ladder, claim
  registry, and fail-closed JSON-schema validation.
- Local visual Lab Suite for Lab 00–05; it renders and verifies tracked reports
  without downloading or rerunning models.
- CCP exact-head receipts for material execution and lightweight documentation
  qualification for docs-only changes.
- Public dense response assets remain external to Git where the manifest says so;
  every package records a locator and SHA-256.

### TRIZ reference corpus

The public corpus contains provenance and bounded, independently authored
derivatives for:

- all 40 Inventive Principles;
- a sparse, double-checked Matrix 2003 fixture with direction-aware cells; and
- a rights-aware fixture of the Panitz TRIZ-tool relationships.

The original public PDFs and bulk tables are not redistributed. The corpus is
used in two explicitly separate strata: `TRIZ-blinded-transfer` and
`source-exposed-competence`. The exposed arm measures reference use, never
latent rediscovery, and the strata are not pooled.

### EXP-002 Qwen3 follow-up — EXP-002A baseline published

Branch [`exp002-qwen3-followup`](https://github.com/MarcoPorcellato/Latent-TRIZ/tree/exp002-qwen3-followup)
has the frozen no-model tranche at implementation checkpoint `e47937c`, with
the guarded EXP-002A baseline. The seven exact snapshots were each loaded once
under the exact `commit-ci-preflight` `origin/main` binary, CPU float32,
local-only, no generation, and one sealed-target read at analysis. Every
terminal outcome is `null`; no claim is promoted. The aggregate manifest is
`results/exp002/preexecution/publication-manifest.json`. Label-permutation and
tokenizer diagnostics, direct TRIZ knowledge/source-familiarity scoring, and
the independently authored EXP-002C corpus remain separate pending stages. The
no-model tranche now includes the three-reviewer answer-key gate, direct-question
and label-free candidate runners, a fail-closed EXP-002C corpus
validator/template, locator-only source-familiarity fixture, deterministic power
calibration, and the `not_ready` sealed transfer target-key contract; neither
authorizes a model load
or sealed-target read. Separate EXP-002B and EXP-002C approval-requested
dossiers are present but intentionally unapproved, with incomplete
prerequisites represented as pending.

## Published model-backed record

The following seven model runs used the same frozen comparative reference-task
contract. Each was authorized separately, executed once under CCP on local CPU
float32, used no network or generation, read sealed targets once at the analysis
boundary, and published its terminal state. Results are independent and are not
pooled into a new statistic.

| Model | Terminal | Primary p | Mean domain delta | Wall time | Peak RSS | Package |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| EleutherAI/pythia-70m-deduped | `null` | 0.6875 | +0.0545 | 312.4 s | 1.92 GiB | [`results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01`](../results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/) |
| HuggingFaceTB/SmolLM2-360M | `null` | 0.65625 | -0.0247 | 365.4 s | 2.90 GiB | [`results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01`](../results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/) |
| Qwen/Qwen3-0.6B-Base | `null` | 0.0625 | +0.9323 | 948.8 s | 4.66 GiB | [`results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01`](../results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/) |
| openai-community/gpt2 | `null` | 0.3125 | +0.0264 | 316.7 s | 1.98 GiB | [`results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01`](../results/exp001-comparative/gpt2-607a30d7-gpt2-20260819-01/) |
| HuggingFaceTB/SmolLM2-135M | `null` | 0.5000 | +0.0420 | 341.7 s | 2.35 GiB | [`results/exp001-comparative/smollm2-135m-93efa2f0-smollm2-135m-20260819-01`](../results/exp001-comparative/smollm2-135m-93efa2f0-smollm2-135m-20260819-01/) |
| EleutherAI/gpt-neo-125m | `null` | 0.6875 | +0.0155 | 323.9 s | 1.73 GiB | [`results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01`](../results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01/) |
| Qwen/Qwen2.5-0.5B | `null` | 0.96875 | -0.0059 | 935.3 s | 4.54 GiB | [`results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01`](../results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01/) |

The separately registered SmolLM2 R3 reference-integrated package is also
terminal `null`; it is a distinct source-aware study and is not pooled with the
seven-model comparative record.

### Interpretation

The record does **not** show a robust, frozen-protocol signal across the tested
model families. Qwen3 is a descriptive near-threshold case (`p=0.0625`), but it
is correctly classified `null` because the preregistered threshold and
held-out-domain rule were not both satisfied. These outcomes do not falsify the
construct-level hypothesis: expert validation, stronger controls, and causal
tests remain open gates.

## Reproducibility and integrity

Start with the no-model path:

```bash
make check
make lab-render
```

To inspect published experiments, use the [EXP-001 comparative study](./EXP001_COMPARATIVE_REFERENCE_STUDY.md),
the [official model documentation audit](./EXP001_MODEL_OFFICIAL_DOC_AUDIT.md),
and the [results contract](../results/README.md). A fresh clone must reject a
missing or mutated external dense asset; it must never silently substitute an
asset or recompute a scientific result.

## Next evidence gate

The A0X six-model campaign is now at its frozen no-model checkpoint. Two
independent legs preserve the historical A0 and A0-R1 rules, and twelve
single-pair dossiers cover six exact model snapshots without pooling. Every
dossier remains `approval_requested`; none authorizes material access. The
complete local no-model qualification and independent architecture/science
review now pass, and the exact freeze/dossier hashes are recorded. A0X is
stopped at `sealed_gate_pending`: the consolidation commit is the next source
anchor, no CCP exact-head qualification exists, and no pair is authorized for
material execution. The preflight for `2af9a159...` correctly stopped before
`doctor`, `dry-run`, and `run` when a stale Matrix V2 digest was detected. The
offline correction now has a non-tautological real-plan fixture and regenerated
freeze/dossier hashes; it does not reuse the obsolete qualification
authorization. See [A0X six-model campaign](./A0X_SIX_MODEL_CAMPAIGN.md).

The later CCP compatibility producer has now completed its own exact
qualification after a TDD fixture-path correction. Qualified source commit
`faf587890e4f899803f027660bc66452623f405e`, tree
`4615028176f3d594fbce0554f5e5edecfb802af1`, and executable SHA-256
`7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8`
passed all five Matrix checks; receipt ID
`sha256:65ff7b62fa949b549c87c1d599e76d67ebfa3edb3cc15d0cfae3972fdde236d9`.
This qualifies that exact local producer only. It is not installed or
published, and the current A0X contract still binds its superseded predecessor.
The remaining preparatory gate is therefore durable CCP integration followed by
zero-access regeneration and a new Latent-TRIZ exact-head qualification.

The next scientific priority is human construct validation: three independent
TRIZ experts, blinded cases, agreement and abstention receipts, and an explicit
keep/amend decision. After that gate, the priority is one preregistered causal
pilot with lexical, source, Matrix-direction, unsupported-edge, random-label,
and capability-preservation controls. Additional model scaling is deferred
until those gates are stable.

See the [Roadmap](./ROADMAP.md) for the short sequence, the [Laboratory Master
Plan](./LABORATORY_MASTER_PLAN.md) for dependencies and exit evidence, and the
[Hypotheses and Falsification](./HYPOTHESES_AND_FALSIFICATION.md) contract for
the normative interpretation rules.
The current installed CCP producer is the separately qualified build from
source commit `3fccc197e5055a2759ee7afe51b91133938ec904`, tree
`9e478c1489a9926772e8ab8bea21bd57470494b6`, executable SHA-256
`b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c`.
Admission remains host-wide and manual lock/lease quarantine is unsupported.
This installed producer identity does not authorize an A0X run: a fresh live
Admit/inactive/queue-zero gate, exact-head qualification, and separate
hash-bound pair authorization are still required.

The single authorized A0X exact-head qualification of
`0114cdc0f14344a9bceb1f442128c55195e69a71` reached a terminal `FAIL` without
timeout. Both schema checks passed; both repository checks failed because
`tests/test_exp002_publication_verify.py` required seven ignored external dense
assets to exist in the fresh isolated checkout. The terminal receipt ID is
`sha256:6e462b9c9bcb0389d886b2b2f56d386e8b4cbdc7ebf3865e8c6478ed47fc1352`
(file SHA-256
`763c845ef4065945a4057149997f44c652dd2cfccdf590795bdaa5b9da430835`).
The production verifier remains fail-closed. The local corrective change makes
the positive test materialize seven deterministic synthetic assets and keeps
explicit missing/mutated-asset failures. This correction requires a new clean
commit and new exact-head authorization before any CCP retry.
