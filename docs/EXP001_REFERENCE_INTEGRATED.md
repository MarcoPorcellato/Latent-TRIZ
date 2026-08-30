---
type: research-specification
title: EXP-001 Reference-Integrated TRIZ Study
description: Durable preregistration for a source-aware, source-blinded, label-safe study using the public TRIZ reference layer.
status: published_exploratory_results
version: 0.3.0
last_verified: 2026-08-19
---

# EXP-001 — reference-integrated TRIZ study

This specification is the canonical execution contract for the next Latent-TRIZ
milestone. It is deliberately separate from the frozen A0-R2 protocol and does
not amend, rerun, or reinterpret any A0-R2 artifact.

## 1. Purpose and falsifiable outcome

Measure whether the already acquired SmolLM2 model can perform narrowly defined
TRIZ reference tasks under two non-poolable conditions:

1. `TRIZ-blinded-transfer`: independently authored problems contain no TRIZ
   names, source wording, canonical examples, matrix cells, or tool-map edges.
   This is the only arm that can test a rediscovery-like transfer signal.
2. `source-exposed-competence`: the same task families are paired with a cited,
   bounded reference context. This measures retrieval, interpretation, and use,
   never rediscovery.

The primary falsifiable outcome is a preregistered held-out-domain transfer
score in the blinded arm against a lexical-matched non-TRIZ control. Secondary
outcomes are source-exposed principle retrieval, direction-aware Matrix 2003
cell agreement, and supported-versus-unsupported tool-transition selection.
Every outcome is exploratory E0 until independent human labels and a later
confirmatory protocol exist.

A positive result may state only that the corresponding automated reference-task
signal exceeded its frozen control. It may not be called TRIZ rediscovery,
inventiveness, novelty, expert competence, causal reasoning, or expert-validated
TRIZ.

## 2. Verified anchors

The verified starting anchor is public `main` commit
`db4cf6d32d263f1df059f6fd376d4cb2bfd38a9c` (PR #74; verify `origin/main`
before every mutation). The prior `f60afc8d9f2803a6a988f26f6c520dd72659080a`
anchor remains the immutable A0-R2/C3 publication input, not the R3 delivery
base. The current reference layer is:

| Artifact | SHA-256 | Scientific status |
|---|---|---|
| `data/triz-reference-sources.json` | `a3bd9283b7e73ebd723bcfab8edb9599161e37a47686b6c25e652158d2158273` | metadata/provenance only |
| `data/triz-reference/principles.jsonl` | `7baa3b74f7a5ee7ca5fe9303baf64361a5cbcdfea0cb0c539e00bb74db764249` | 40 independently worded summaries, not labels |
| `data/triz-consulting-web-corpus.json` | `e397160adfc60c534d16b5cd934deddb3e3500bb8f99f7fef26a2b6d4c2eff46` | metadata-only site catalogue |
| `docs/reference/triz-reference-corpus.md` | `92429183119e463090df170f4ec29bf0f0e43ee531f47898c8071325a3b7435f` | canonical rights and epistemic boundary |

The three supplied public references remain external copyrighted material. No
PDF, screenshot, bulk matrix table, or verbatim extract may be vendored under
the repository Apache-2.0 licence. The Panitz map remains user-attributed and
not independently verified as a canonical ontology.

The SmolLM2 model identity, runtime-file receipt, feasibility receipt, and prior
C3 activation bundle remain immutable inputs. Their exact hashes must be copied
into the new protocol and execution receipt; no new model download is planned.

## 3. Status vocabulary and epistemic envelope

Use these machine-readable states: `draft`, `ready_for_review`, `frozen`,
`approval_requested`, `authorized`, `running`, `positive`, `null`, `failed`,
`non_interpretable`, `incompatible`, and `published`.

`source_exposed` means a bounded source-derived context is intentionally shown.
`TRIZ_blinded` means no source-derived lexical or structural cue is shown.
`reference_task` means agreement with a recorded source recommendation; it is
not a ground-truth claim about the quality of a proposed solution.

All results are `scientific_status: exploratory`, `expert_validated: false`,
`claim_ids: []`, and `evidence_eligible: false` unless a later human-governed
protocol explicitly changes those fields.

## 4. Scope, non-goals, and invariants

In scope:

- all 40 principle records as authoring references;
- a small, double-checked Matrix 2003 cell fixture with page/table locators;
- a small, independently transcribed Panitz tool-edge fixture with edge status;
- paired blinded/exposed variants, lexical controls, held-out domains, and
  source-family splits;
- one bounded SmolLM2 run that processes both strata in one guarded invocation;
- immutable receipts, statistics, reports, limitations, and public publication.

Out of scope:

- changing A0-R2 prompts, targets, thresholds, model identity, or claims;
- treating a principle, matrix recommendation, or Panitz edge as universal
  ground truth;
- claiming that source exposure demonstrates latent rediscovery;
- human or LLM judging in the automated run;
- downloading a new model, accepting new terms, or publishing third-party PDFs;
- pooling blinded transfer with source-exposed retrieval in one score.

Invariants:

- source registry and existing A0-R2 bytes remain byte-for-byte unchanged;
- every item has source ID, locator, derivation method, exposure mode, domain,
  family, lexical-overlap score, canonical-example proximity, and rights state;
- source-derived recommendations and independent human labels are separate
  fields and are never silently substituted;
- the primary endpoint, controls, stopping rule, and multiplicity are frozen
  before any model output;
- sensitivity analyses cannot rescue a failed primary;
- missing, stale, mismatched, or uncertain receipts fail closed;
- positive, null, failed, non-interpretable, and incompatible packages are all
  published.

## 5. Ordered milestones

### R3.0 — no-model source and protocol readiness

Create `experiments/exp001-reference-integrated/` with a strict protocol,
item, source-exposure, matrix-cell, tool-edge, and publication schema. Validate
the existing registry, exactly 40 principles, exactly 18 web resources, rights
flags, hashes, and no-local-path policy. Do not download sources, load a model,
open sealed targets, or alter A0-R2.

**Exit evidence:** schema cross-validation, source/hash audit, rights audit,
clean worktree, and a reviewable protocol diff.

**Current status (2026-08-18):** the target-free protocol, implementation
binding, freeze manifest, and approval-request dossier are frozen and published
on PR #75. Exact-head no-model qualification and operator approval remain
separate gates. This status authorizes neither a model load nor sealed-target
access.

The current no-model source verifier is committed at `6316cd6`. It verifies
the four immutable reference hashes, forty ordered principle records, eighteen
web-resource records, fixture schemas, safe paths, paired non-poolable strata,
Matrix double-check agreement, and Panitz non-selection controls without
importing an ML runtime. It is evidence of preparation only, not a study
freeze or a model qualification.

### R3.1 — independent fixture construction and contamination audit

Build independent paraphrases and domains from the reference summaries without
copying canonical examples. Encode a sparse matrix fixture only after two
independent visual checks against Matrix 2003. Encode only clearly supported
Panitz edges and mark uncertain or unsupported transitions explicitly. Add
near-neighbour principles, swapped matrix directions, unsupported edges,
abstentions, lexical-matched non-TRIZ controls, and canonical-example proximity
audits.

The fixture must be split by source family, problem family, and held-out domain
before any model output. The blinded and exposed variants must share the same
underlying task identity but remain separately addressable and separately
scored.

**Exit evidence:** frozen fixture manifest, independent derivation receipts,
lexical-overlap report, source-family/domain split report, matrix double-check
receipt, tool-edge status receipt, and synthetic power/permutation calibration.

**Checkpoint (2026-08-18):** `b1ab0d6` adds 24 public target-free primary
units across six domains, two families per domain, and two replicates per
family. Correct-answer positions are rotated semantically in the future sealed
key and are not stored in public fixtures. `2e7c510` adds synthetic-tested
teacher-forced scoring that rejects tensor, prefix, architecture, or generation
contract drift. Matrix and Panitz secondary fixtures are now execution-ready,
source-family separated, and bound by the public freeze manifest; R3.1 is
verified complete without model or target access.

**Operational decision pending freeze:** preserve the 72-record primary
inventory unchanged and add 13 separately scored secondary records: nine
Matrix 2003 checks (three verified cells × forward, reversed-direction and
non-recommendation controls) plus four Panitz edge checks. The combined single
model invocation will therefore score 85 records × four teacher-forced labels.
Secondary outcomes are descriptive, source-family separated and cannot alter
the primary terminal classification. The target-free fixture inventory is now
bound by the R3 implementation freeze; sealed target values remain absent.

### R3.2 — statistical and implementation freeze

Freeze one primary: blinded held-out-domain transfer versus the lexical-matched
control, using family-grouped leave-one-domain-out evaluation. Freeze distinct
secondary endpoints for exposed principle retrieval, Matrix 2003 exact-cell
agreement, and tool-edge selection/abstention. Declare the exact score,
permutation/bootstrap scheme, seed, multiplicity correction, confidence
intervals, minimum family/domain support, and terminal classification before
model access. Reuse existing kernels only after a compatibility review; do not
inherit A0 thresholds by assumption.

Bind the exact SmolLM2 revision, prior integrity/feasibility receipts, code
hashes, fixture hashes, runtime limits, and no-claim envelope. Synthetic
adapters/vectors must cover both strata and every terminal class.

**Exit evidence:** frozen protocol, code/fixture hash manifest, mutation tests,
synthetic statistics tests, exact-head CCP qualification, and a separate
operator approval dossier.

**Checkpoint (2026-08-18):** the public freeze at `f1cc72b` binds the strict
terminal receipt, response index, statistical-result, publication-manifest,
freeze-manifest, and approval-request dossier to the frozen protocol and exact
SmolLM2 receipts. They preserve the exploratory/no-claim envelope and are not
an operator authorization or model result.

### R3.3 — one guarded model run

After explicit approval of the frozen dossier, check CCP `resource status
--json` and `admission status --json`; proceed only with `decision=admit`,
`active=false`, and `queue_count=0`. Run SmolLM2 locally in one CPU float32
invocation, offline and without generation unless the frozen protocol requires
structured output. Use the already acquired snapshot only. Apply a conservative
30-minute wall-time, 8 GiB peak-RSS, and 128 MiB new-dense-output ceiling unless
the approved dossier freezes stricter limits.

No tuning, model substitution, protocol change, post-output retry, or sealed
target access outside the declared analysis boundary is permitted. If any
runtime or tokenizer mismatch occurs, publish `incompatible` or `failed` and
stop.

**Checkpoint (2026-08-18):** exact-head CCP qualification passed on
`8bd99a68c07f8c666ec77e0f7d009703ac4551cf` for Python 3.11 and 3.12
(repository and schema checks). With the separately recorded operator
authorization, one guarded SmolLM2 run completed exactly once. The terminal
package is `results/exp001-r3/smollm2-r3-20260818-01/`, with status `null`,
one sealed-target read, 299.054 seconds wall time, and peak RSS
2,824,798,208 bytes. No retry occurred; the result remains exploratory and
claim-free. The secondary Matrix 2003 and Panitz strata were executed but are
reported descriptive-only/not reported by the frozen primary statistic.

**Exit evidence:** exact runtime receipt, access receipt, activation/response
index, terminal statistical result, recovery observation, and immutable logs.

### R3.4 — publication and fresh-clone verification

At the time R3.4 was executed, the publication contract required a dedicated
branch and PR plus an exact-head CCP receipt on
`ccp-evidence/<exact-head>`. That historical package merged only after its CCP,
scientific-artifact, trusted-path, documentation, and aggregate gates were
terminally green. The current public-repository gate instead uses hosted
Repository check jobs; the historical receipt remains immutable evidence. The
manifest must name the external dense asset and SHA-256;
the fresh-clone verifier must pass with that asset and fail closed when it is
missing or mutated.

**Exit evidence:** merged main commit, PR and receipt links, fresh-clone pass,
fresh-clone missing/mutation rejection, final report, and updated chronology.

**Current status (2026-08-18):** R3.4 package publication is complete. PR #75
merged the immutable package into `main` at
`4cc1c6d862bffc9558b47a5cadd838a2ee22c465`; the exact-head CCP receipt is
public on `ccp-evidence/48a354eaa2f06e0e6eabf016c42a7387a1ab1b65`. Fresh-clone
verification passed when the declared external response-score asset was
provided and rejected both a missing and a mutated asset. The score asset is
intentionally external/local: its locator and SHA-256 are public, while its
contents require a separate explicit publication authorization. This boundary
does not alter the terminal result or permit a scientific claim.
### Historical comparative extension — three-model terminal evidence (2026-08-18)

The separately frozen comparative dossier applied the same 85-record
TRIZ-reference inventory, blinded/source-exposed separation, six held-out
domains, and exact teacher-forced analysis independently to all three
authorized model families. Each run passed the live CCP gate (`Admit`, inactive,
empty queue), ran once on local CPU float32 with network and generation
disabled, read the sealed target exactly once at the analysis boundary, and
stayed within the approved 1,800-second / 8-GiB / 128-MiB limits.

| Model | Terminal state | Exact two-sided p | Mean domain delta | Bootstrap 95% CI | Positive domains | Wall/RSS |
|---|---:|---:|---:|---|---:|---|
| Pythia 70M | `null` | 0.6875 | +0.0545 | [-0.1485, +0.2956] | 3/6 | 312.4 s / 1.92 GiB |
| SmolLM2 360M | `null` | 0.65625 | -0.0247 | [-0.1095, +0.0602] | 2/6 | 365.4 s / 2.90 GiB |
| Qwen3 0.6B | `null` | 0.0625 | +0.9323 | [+0.5353, +1.2063] | 5/6 | 948.8 s / 4.66 GiB |

All three publication verifiers pass and all receipts record one target read,
`claim_ids=[]`, `evidence_eligible=false`, and `expert_validated=false`.
Qwen3 is an exploratory near-signal, not a positive result: it misses the
preregistered `p<=0.05` threshold and has one slightly negative domain
(`agriculture`, -0.0043), so the frozen terminal classifier correctly remains
`null`. The results do not establish latent TRIZ rediscovery or any general
TRIZ claim. Dense response assets remain external and are bound by the
published SHA-256 locators in each execution receipt.

The immutable packages are:

- `results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/`
- `results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/`
- `results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/`

This extension closes the automated three-model evidence tranche. Human TRIZ
review remains a separate next step; no post-hoc tuning, pooling, model
substitution, or retry is permitted.

### Historical additional model extension — two-model no-download selection (2026-08-19)

The three-model tranche above remains immutable. It is not amended, rerun, or
pooled with the following separately frozen proposal. This proposal widens the
future comparison to five model runs only after a new approval, acquisition,
integrity, feasibility, and one-run dossier has been completed.

| Candidate | Exact revision | Role | License | Declared runtime bytes |
|---|---|---|---|---:|
| GPT-2 (`openai-community/gpt2`) | `607a30d783dfa663caf39e06633721c8d4cfcd7e` | architecture-diversity control | MIT | 550,959,861 |
| SmolLM2-135M (`HuggingFaceTB/SmolLM2-135M`) | `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` | same-family scale control | Apache-2.0 | 272,437,465 |

The exact source pages are [GPT-2 model card](https://huggingface.co/openai-community/gpt2),
[GPT-2 frozen tree](https://huggingface.co/openai-community/gpt2/tree/607a30d783dfa663caf39e06633721c8d4cfcd7e),
[GPT-2 config](https://huggingface.co/openai-community/gpt2/blob/607a30d783dfa663caf39e06633721c8d4cfcd7e/config.json),
[SmolLM2-135M model card](https://huggingface.co/HuggingFaceTB/SmolLM2-135M),
[SmolLM2-135M frozen tree](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/tree/93efa2f097d58c2a74874c7e644dbc9b0cee75a2),
and [SmolLM2-135M config](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/blob/93efa2f097d58c2a74874c7e644dbc9b0cee75a2/config.json).

The source-backed runtime/tokenizer contract and the pre-access failure
analysis are maintained in [`docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md`](EXP001_ADDITIONAL_MODEL_RUNTIME.md).
In particular, SmolLM2-135M is a Llama architecture whose pinned tokenizer
metadata declares `GPT2Tokenizer`; architecture tags must never be used as a
tokenizer-class shortcut.

Selection was made without consulting any prior model score. GPT-2 supplies a
provider, decoder-family, tokenizer, and training-corpus contrast to Pythia,
SmolLM2, and Qwen3. SmolLM2-135M is deliberately not an independent family:
it is a within-family scale control for the already tested SmolLM2-360M. The
five-model plan therefore increases architectural and scale variation without
pretending that all five observations are independent replications.

The machine-readable dossier is
`experiments/exp001-comparative-reference/additional-model-selection.json`,
validated by `schemas/exp001-additional-model-selection.schema.json`, with the
operator authorization and integrity receipts under
`experiments/exp001-comparative-reference/additional-model-authorization.json`
and `results/exp001-comparative/preexecution/`. One authorized run completed
for each model, with no generation, no network, one sealed-target read per
model, and terminal status `null` for both. GPT-2 completed in 316.68 s at
2,121,891,840 B peak RSS; SmolLM2-135M completed in 341.66 s at
2,520,023,040 B. The primary p-values were 0.3125 and 0.5 respectively; both
packages are exploratory nulls and remain non-pooled. The earlier R3 package at main
`4cc1c6d862bffc9558b47a5cadd838a2ee22c465` remains immutable; this extension
does not reopen it.

### Historical complementary-model dossier — two no-download candidates (2026-08-19)

The five-model record above remains historical terminal evidence. A separate
no-download dossier names two further candidates so the next comparison adds a
GPT-Neo architecture control and a Qwen2/Qwen3 within-provider control without
pooling them with prior scores:

| Candidate | Exact revision | Role | License | Architecture | Estimated runtime bytes |
|---|---|---|---|---|---:|
| `EleutherAI/gpt-neo-125m` | `21def0189f5705e2521767faed922f1f15e7d7db` | architecture-family control | MIT | `GPTNeoForCausalLM`, 12 layers, hidden 768 | 540,000,000 |
| `Qwen/Qwen2.5-0.5B` | `060db6499f32faf8b98477b0a26969ef7d8b9987` | provider/scale control | Apache-2.0 | `Qwen2ForCausalLM`, 24 layers, hidden 896 | 1,100,000,000 |

The exact source-backed records are in
`experiments/exp001-comparative-reference/next-model-selection.json`, validated
by `schemas/exp001-next-model-selection.schema.json`. GPT-Neo is a public MIT
causal model with a self-contained GPT-2-compatible fast tokenizer and a
documented Pile lineage; it adds a `gpt_neo` architecture distinct from the
existing GPT-NeoX Pythia. Qwen2.5 is public Apache-2.0, uses
`Qwen2ForCausalLM` with a 32,768-token context and a complete tokenizer/runtime
tree; it is explicitly a within-provider control against tested Qwen3, not an
independent provider replication. Exact file sizes, SHA-256 receipts, runtime
compatibility, and CPU feasibility remain unknown until separately approved
acquisition.

OpenELM-270M and Mamba2-130M were rejected for this immediate tranche despite
their small size: the official OpenELM snapshot requires remote code and Apple
AMLR research-only terms, while the official Mamba2 snapshot exposes no
self-contained tokenizer contract. These are documented re-evaluation options,
not substitutions. No candidate is downloaded, loaded, or allowed to read
sealed targets by this dossier.

### Additional-model acquisition checkpoint (2026-08-19)

The operator subsequently authorized the exact two candidates and the
allowlisted runtime downloads. Both snapshots are now integrity-verified,
without model load, generation, dense output, or sealed-target access:

| Model | Receipt | Total bytes | Model SHA-256 |
|---|---|---:|---|
| `EleutherAI/gpt-neo-125m@21def0189f5705e2521767faed922f1f15e7d7db` | `results/exp001-comparative/preexecution/gpt-neo-125m-integrity-receipt.json` | 529,444,041 | `52738cbfb54e25a232598242f60ef19ee193d36090b98fe649b10c02724b3521` |
| `Qwen/Qwen2.5-0.5B@060db6499f32faf8b98477b0a26969ef7d8b9987` | `results/exp001-comparative/preexecution/qwen2.5-0.5b-integrity-receipt.json` | 999,586,188 | `88c142557820ccad55bb59756bfcfcf891de9cc6202816bd346445188a0ed342` |

The receipts bind the exact allowlists, authorization digest, and explicit
negative access flags. They do not authorize a pooled analysis: after this
checkpoint, each model still receives exactly one sequential CPU-float32 run
under CCP `Admit` with inactive admission and an empty queue, using the frozen
protocol and the declared 1,800-second, 8-GiB RSS, and 128-MiB dense-output
ceilings. A terminal `null`, `failed`, or `non_interpretable` package is
publishable; no retry is permitted after model or target access.

### Additional-model execution checkpoint (2026-08-19)

Both authorized one-shot runs completed from merged public `main`, under CCP
`Admit` with inactive admission and an empty queue. They remain independent,
non-pooled exploratory controls:

| Model | Terminal | Primary p | Mean domain delta | Wall s | Peak RSS B | Dense B | Target reads |
|---|---|---:|---:|---:|---:|---:|---:|
| `EleutherAI/gpt-neo-125m` | `null` | 0.6875 | +0.01553 | 323.899 | 1,858,076,672 | 20,599 | 1 |
| `Qwen/Qwen2.5-0.5B` | `null` | 0.96875 | -0.00587 | 935.267 | 4,876,828,672 | 20,699 | 1 |

The immutable packages are under
`results/exp001-comparative/gpt-neo-125m-21def018-gpt-neo-125m-20260819-01/`
and
`results/exp001-comparative/qwen2.5-0.5b-060db649-qwen2.5-0.5b-20260819-01/`.
Each package passed the comparative publication verifier, binds an external
dense response asset by SHA-256, records `claim_ids: []`, and states no
general TRIZ claim. No rerun or tuning is permitted for either model.

### Final comparative closeout (2026-08-19)

The two complementary controls completed their authorized one-shot runs and
were merged through PRs #96 and #97. GPT-Neo 125M is `null` (`p=0.6875`,
323.899 s, peak RSS 1,858,076,672 B); Qwen2.5 0.5B is `null` (`p=0.96875`,
935.267 s, peak RSS 4,876,828,672 B). Both packages passed their publication
verifier and fresh-clone checks, including rejection of missing and mutated
external dense assets. The public documentation/result closeout is merged in
PR #98 at `0123ce467408becbf127b66da1fcd4166bbbd431`.

Together with the historical Pythia, SmolLM2, Qwen3, GPT-2, and SmolLM2-135M
packages, the comparative record now contains seven independent terminal
`null` packages. They remain non-pooled, exploratory, and claim-free. No
additional run is authorized by this specification.

## 6. Required deliverables

- `experiments/exp001-reference-integrated/protocol.json` and freeze manifest;
- strict schemas for items, exposure, matrix cells, tool edges, execution,
  statistical result, and publication manifest;
- principle, matrix, and tool fixtures with source locators and rights flags;
- lexical/split/contamination/power receipts;
- SmolLM2 execution, access, response/activation, statistical, report, and
  recovery receipts;
- external dense locator and hash, immutable publication manifest, limitations,
  and fresh-clone verifier evidence;
- public PR, exact-head CCP evidence branch, merge commit, and chronology entry.
- separate additional-model selection, authorization, integrity, and execution
packages for GPT-2 and SmolLM2-135M, including the official tokenizer
contract and public locator/hash bindings for local-only dense assets.

## 7. Delegation and cost policy

Use deterministic tools first. Delegate the largest independent safe share to
GPT-5.6 Luna: source inventory, hash/schema audits, mechanical fixture checks,
synthetic test execution, and log distillation. GPT-5.6 Terra should orchestrate
milestones, integrate Luna outputs, and own protocol architecture, scientific
interpretation, security, CCP qualification, release, and merge decisions.
Do not delegate sealed-target access, model selection, statistical endpoints,
approval boundaries, or claim language.

## 8. Approval and recovery boundaries

No-model preparation needs no new external approval beyond normal repository
delivery. Before any model load, generation, material hardware use, or sealed
target read, request one explicit approval bound to the exact frozen protocol,
model revision, files, resource ceiling, one-run rule, access mode, and
publication duties. Preserve all prior A0-R2/C3 receipts and do not retry a
consumed run under this specification.

At interruption, record branch, exact HEAD, base, dirty state, worker status,
CCP resource/admission, completed gates, unproven gates, external hashes, and
the exact resume command in a restart handoff. Never treat a temporary path as
the checkpoint.

## 9. Completion checklist

- [x] R3.0 schemas and no-model source audit pass.
- [x] R3.1 fixtures, rights, contamination, source-family, and domain audits pass.
- [x] R3.2 primary/statistics/code hashes are frozen before model output.
- [x] Exact model/runtime/CCP approval dossier is recorded.
- [x] Exactly one guarded run completes for each authorized model.
- [x] Blinded, exposed, matrix, and tool endpoints remain non-pooled.
- [x] Every terminal result and limitation is published with claim IDs empty.
- [x] Exact-head receipt and local CCP gates are terminally green.
- [x] Publication verifiers pass with declared external assets and reject missing or mutated assets.
- [x] Main, chronology, persistent goal, and this specification agree on status.
- [x] Additional-model selection is frozen without prior-score conditioning;
  both snapshots are integrity-verified and their official tokenizer contracts
  are documented.
- [x] Exact GPT-2 and SmolLM2-135M one-run publication dossier is approved,
  executed once per model, independently verified, and published as terminal
  null outcomes.
- [x] GPT-Neo and Qwen2.5 exact snapshots are acquired from the authorized
  revisions and integrity-verified without model or target access.
- [x] One CCP-guarded GPT-Neo run and one CCP-guarded Qwen2.5 run are complete,
  with immutable terminal packages and publication-verifier PASS.
- [x] Qwen2.5 terminal package publication/merge and fresh-clone verification
  (including missing/mutated external-asset rejection) are complete. PR #97
  merged at `a081e612feca348b28253ee0cc9e67c24b45ed3a`; the GPT-Neo companion
  PR #96 merged at `74926e15fe06a6e41ef1aa0d96e731b70636531a`.
