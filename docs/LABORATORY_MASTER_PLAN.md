---
type: master-plan
title: Laboratory Master Plan
description: Canonical evolution ledger and gated route from the verified laboratory foundation to falsifiable, reproducible Latent TRIZ experiments.
status: canonical
last_verified: 2026-08-20
---

# Laboratory Master Plan

This is the canonical long-form plan for Latent TRIZ. It records the verified
repository evolution, the current scientific bottleneck, the dependency-ordered
delivery sequence, and the proof required to close each milestone. The shorter
[Roadmap](./ROADMAP.md) remains the public overview.

This plan is operational metadata. It is not evidence for the Latent TRIZ
Hypothesis.

Long-running Codex work should use [the persistent execution goal](./PERSISTENT_GOAL.txt)
as a short pointer to this plan rather than duplicating its milestones.

For the compact public snapshot of the verified checkpoint, see
[Current Laboratory Status](./CURRENT_STATUS.md).

The construct-validity and falsification contract is maintained separately in
[Weak and Strong Latent TRIZ Hypotheses](./HYPOTHESES_AND_FALSIFICATION.md).
It is normative for new WLT/SLT work and does not rewrite historical packages.

## Status vocabulary

- **Verified:** supported by a tracked artifact, exact commit, merged pull
  request, or terminal validation receipt.
- **In delivery:** saved implementation exists but the milestone has not passed
  its complete qualification and merge gate.
- **Blocked by human work:** software may be ready, but a real independent human
  activity is still required.
- **Planned:** ordered work with an explicit predecessor and exit gate.
- **Deferred:** intentionally excluded until a stronger predecessor result
  justifies it.

## Verified planning anchor

| Item | Verified state | Authoritative anchor |
|---|---|---|
| Public repository | `MarcoPorcellato/Latent-TRIZ` | GitHub repository and tracked `LICENSE` / `NOTICE` |
| Protected `main` | `0123ce467408becbf127b66da1fcd4166bbbd431` | public exact head after PR #98; verify again before the next mutation |
| Required merge context | strict `merge-policy/gate` | active GitHub ruleset and `.github/expected-main-ruleset.json` |
| Completed automated milestone | A0-R Tier R1 same-model replication | PR 41, run `a0r1-v1.0.0-e93a9faa-r1` |
| Current authentic-TRIZ milestone | H1 v1.2 collection packet | public packet is `ready_for_collection`; closure is blocked by three independent human TRIZ experts |
| Claim state | all registered claims remain E0 | `data/claims.jsonl` |
| First dataset attempt | rejected for scientific freeze | retained Wave 1 surface-audit artifacts |
| Comparative reference tranche | seven terminal `null` packages | PRs #77, #96, and #97; public main `0123ce4`; exploratory and claim-free |

The implementation checkpoint for the latest comparative tranche is now the
public `main` head above. The exact-head receipt branches and merged pull
requests are recorded in the chronology and the comparative study. It is not a
protected-main scientific claim: every result remains exploratory and must be
read together with its protocol, receipt, and external-asset verifier.

The checkout used for unrelated local work is not an authoritative integration
base. Delivery uses an isolated worktree created from an exact verified commit.

### EXP-002 Qwen3 follow-up implementation checkpoint (2026-08-20)

The new branch `exp002-qwen3-followup` publishes the implementation of
[`EXP002_QWEN3_FOLLOWUP_RESEARCH_PLAN.md`](./EXP002_QWEN3_FOLLOWUP_RESEARCH_PLAN.md)
through implementation checkpoint `e47937c`. Its frozen seven-model dossier was executed once
per exact snapshot under the current CCP `origin/main` binary. The EXP-002A
baseline packages are all terminal `null`, exploratory, non-pooled, and claim
free; each records CPU float32, no network/generation, and one target read at
the analysis boundary. The aggregate manifest is
`results/exp002/preexecution/publication-manifest.json`. The remaining
label-permutation/tokenizer, direct TRIZ/source-familiarity, and independent
blinded-transfer stages remain pending and cannot be inferred from this
baseline.

The no-model tranche also freezes the EXP-002B answer-key gate (three
pseudonymous reviewers plus an explicit disagreement policy), the locator-only
source-familiarity boundary, deterministic EXP-002C power calibration, and the
target-free corpus schema/validator, label-free candidate runner, and the
`not_ready` sealed transfer target-key contract. The public corpus template remains empty
until independent authoring, source-proximity review, and held-out/sealed-novel
splits are complete; these gates do not authorize model or sealed-target
access. Separate `approval_requested` dossiers for EXP-002B and EXP-002C bind
the seven exact models and fixed resource envelope while remaining unapproved;
incomplete prerequisites are explicitly marked pending.

### EXP-002-AUTO pre-expert checkpoint (2026-08-20)

[`EXP002_AUTO_PREEXPERT_CAMPAIGN.md`](./EXP002_AUTO_PREEXPERT_CAMPAIGN.md)
is a separate, fully automated exploratory programme. Its frozen no-model
tranche defines tokenizer audit, 24-record cyclic/label-free response-surface
controls, 178 factual automatic items, 160 source-familiarity formulations,
an eight-domain procedural proxy, and the full 24-permutation schedule for
each of the seven already registered model snapshots. Public fixtures contain
no expected answer; factual and procedural labels remain one combined,
unmaterialized key outside the public tree. The approval dossier is explicitly
`approval_requested`, so this checkpoint authorizes neither model/tokenizer
construction nor target access. It is designed to diagnose surface sensitivity
such as Qwen3's balanced labels, not to replace expert TRIZ validation or make
a general TRIZ claim.

## Evidence boundary

The following may qualify engineering, documentation, or readiness, but never
count as evidence for the hypothesis:

- smoke tests and synthetic fixtures;
- dashboards and visualizations;
- source inspection without a completed run;
- generator intent labels;
- incomplete or unblinded human judgments;
- model-backed instrumentation without the experimental controls;
- exploratory results presented outside their registered evidence class.

A scientific result requires frozen inputs, canonical labels, an exact model
revision, an immutable run record, the applicable controls, a terminal artifact
audit, and an explicit link to the claim registry. Null and failed results are
published under the same standard.

## Strategic improvement decisions from the external hypothesis review

The accompanying review is a planning input, not new scientific evidence. It
does, however, sharpen the order in which the repository should spend effort.
The following decisions are now normative for future work:

1. **Construct validity before scale.** The immediate bottleneck is H1, not a
   larger model or a broader principle inventory. Three independent qualified
   TRIZ experts must validate the blinded operator cases before any automated
   proxy is described as a Weak Latent TRIZ result.
2. **Causality before breadth.** Once H1 and an out-of-sample direction exist,
   the next material study is one validated operator in Lab 06. Steering,
   ablation, dose-response, opposite-sign, norm-matched random, unrelated,
   fluency, and capability controls have priority over testing all forty
   principles or adding more model families.
3. **Controls are part of the construct.** Every new dataset must challenge
   lexical, length, template, source, near-neighbour, cosmetic, generic-action,
   Matrix-direction, unsupported-tool-edge, abstention, random-label, and
   extreme-domain shortcuts. A control that fails is a readiness failure, not
   an invitation to tune the primary.
4. **Keep retrieval separate from rediscovery.** The public TRIZ corpus may
   improve source-exposed competence tasks, but only the source-blinded arm can
   test transfer. Their records, statistics, claims, and publication summaries
   remain physically and analytically non-poolable.
5. **Treat Strong Latent TRIZ as a separate emergence question.** Track B must
   use a from-scratch, no-TRIZ-term corpus with frozen checkpoints and
   independent seeds. Track A outputs may not choose its data, checkpoint, or
   hyperparameters. It may be prepared in parallel, but it cannot replace H1 or
   causal evidence.
6. **Use scale only after a stable signal.** Independent model-family
   replication and additional principles are justified after the single
   operator contract and controls are stable. Composition and contradiction
   tasks come after the first causal gate; they cannot rescue a failed
   single-operator result. GPT-2 and SmolLM2-135M are now completed
   architecture/scale controls under a separate one-run authorization; their
   terminal null packages do not broaden the evidence claim.
7. **Make the lab usable without weakening it.** A no-model quickstart should
   reproduce a synthetic result in under thirty minutes, expose the evidence
   profile and published nulls, and route all material execution through CCP
   and explicit approval. Infrastructure work that does not unlock a listed
   evidence gate is deferred.

### Additional-model execution checkpoint (2026-08-19)

The separate dossier
`experiments/exp001-comparative-reference/additional-model-selection.json`
and schema `schemas/exp001-additional-model-selection.schema.json` freeze two
complementary candidates without consulting prior scores: GPT-2 as an
architecture-diversity control and SmolLM2-135M as a same-family scale control
against SmolLM2-360M. Both snapshots were acquired under the exact allowlists,
their SHA-256 receipts were verified, and the official tokenizer contracts are
recorded in `docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md`. One local CPU float32
run per model completed under CCP: GPT-2 `null` (316.68 s, 2,121,891,840 B
peak RSS, p=0.3125) and SmolLM2-135M `null` (341.66 s, 2,520,023,040 B peak
RSS, p=0.5). Each opened sealed targets exactly once. Scores remain separate,
all claim IDs are empty, and the existing comparative packages remain
immutable.

This ordering prevents the repository from confusing a positive automated
proxy with the construct itself, and prevents infrastructure expansion from
outpacing the human and causal evidence needed to test the hypothesis.

### Next complementary-model selection checkpoint (2026-08-19)

The no-download dossier
`experiments/exp001-comparative-reference/next-model-selection.json` freezes
`EleutherAI/gpt-neo-125m@21def0189f5705e2521767faed922f1f15e7d7db` (MIT,
`gpt_neo`, 125M) and `Qwen/Qwen2.5-0.5B@060db6499f32faf8b98477b0a26969ef7d8b9987`
(Apache-2.0, `qwen2`, 0.5B) without consulting any prior score. They are
complementary controls for architecture and within-provider scale, not pooled
replications. The exact source/config/tokenizer links, rejected alternatives,
and fail-closed boundaries are documented in the dossier and schema. The
metadata-only request
`experiments/exp001-comparative-reference/next-model-authorization.json`
now binds the official revision-tree allowlists: GPT-Neo has eight runtime
files totalling 529,444,041 bytes under a 1 GiB ceiling; Qwen2.5 has seven
runtime files totalling 999,586,188 bytes under a 1.5 GiB ceiling. Hub blob/LFS
identifiers and canonical metadata hashes are recorded. The operator approval
for the exact two IDs/revisions is now recorded in the request; acquisition and
each material run remain separately observable, one-shot gates. The prior
GPT-2/SmolLM2-135M approval was not reused.

#### Official documentation audit checkpoint (2026-08-19)

`docs/EXP001_MODEL_OFFICIAL_DOC_AUDIT.md` records a read-only review of the
official Hugging Face model pages and Transformers documentation for both
snapshots. It freezes the implementation safeguards that are easy to miss in
generic documentation: GPT-Neo's published defaults are not the exact 125M
checkpoint, GPT-Neo requires right padding if padding is ever introduced, and
Qwen2.5's tokenizer maximum (131,072) is larger than the model context
(32,768). The audit also binds the no-generation/base-model prompt boundary,
the fast-tokenizer rule for any future offsets, and the deliberate CPU
float32 override. This checkpoint is metadata-only: it does not authorize
acquisition, model load, feasibility, sealed-target access, or a retry.

## Evolution ledger

### Phase A — hypothesis, governance, and public laboratory foundation

| Delivery | What became usable | Scientific boundary |
|---|---|---|
| PRs [#1](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/1)–[#3](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/3) | article framing, research protocol, official repository structure, Apache-2.0 governance, E0–E6 evidence discipline, Matryca-Knowledge documentation bundle | hypothesis registered; no empirical support |
| PR [#11](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/11) | one-command Lab 00 visual process smoke | synthetic and presentation-only |
| PRs [#12](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/12)–[#13](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/13) | provisional model strategy, offline model and dataset preflight, stronger evidence integrity | selection remained provisional and no-download |

### Phase B — runnable Lab 01–05 instrumentation

| Delivery | What became usable | Scientific boundary |
|---|---|---|
| PR [#14](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/14) | exact-revision real-model Lab 01 anatomy and numerical parity | instrumentation evidence only |
| PRs [#15](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/15)–[#19](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/19) | Lab 02 dataset anatomy, Lab 03 surface controls, Lab 04 decodability fixture, Lab 05 candidate directions, and the one-command Lab Suite | maintained fixtures and readiness gates, not TRIZ evidence |
| PR [#24](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/24) | domain-blocked max-statistic inference, nested alpha reselection, p-resolution refusal, and NumPy backend | empirical-scale method enabled; tracked fixture remained non-empirical |
| PR [#25](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/25) | hash-verified Safetensors bridge from real residual activations to Lab 04 | two-case Pythia smoke remained engineering-only |

### Phase C — annotation and the first dataset falsification gate

| Delivery | What became usable | Scientific boundary |
|---|---|---|
| PRs [#21](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/21)–[#23](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/23) | blinded workbench, balanced Wave 1 candidate batch, and retained multi-rater audit | candidate and collection infrastructure only |
| PR [#26](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/26) | annotation ontology v1.1 with cryptographic case, batch, guide, and session binding | independent collection had not started |
| PR [#27](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/27) | field-specific lexical and provenance surface audit | Wave 1 correctly rejected; negative readiness result, not hypothesis evidence |

Wave 1 exposed strong superficial shortcuts, including label prediction from the
problem alone and perfect prediction from some solution views. It must not be
edited until it passes the audit. Its permanent role is a known-leaky
calibration corpus and regression fixture.

### Phase D — fail-closed integrity and stable cost-aware governance

| Delivery | What became usable | Scientific boundary |
|---|---|---|
| PR [#28](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/28) | local `$ref` / `$defs`, `allOf`, exclusive bounds, unsupported-keyword failure, Draft 2020-12 cross-validation, mutation tests, disagreement-safe freeze, and `constraints` cue scanning | closed the two reported P0 fail-open paths; did not change a claim |
| PR [#29](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/29) | one stable path- and risk-aware `merge-policy/gate`, pre-merge Python 3.11/3.12 where applicable, exact-head CCP and artifact audit for scientific/governance changes, scheduled ruleset drift audit | qualification policy only |

### Phase E — human-label route in delivery

The v1.2 H1 route is now **software-ready but blocked by human work**. The
public packet contains six blinded cases, deterministic allocation, a reviewed
guide, a strict raw-annotation schema, a fail-closed packet audit, and a
synthetic-only validation receipt at exact head `10d249a…`. The audit reports
`ready_for_collection`, `non_empirical: true`, `expert_validated: false`, and
`evidence_eligible: false`.

The next required artifact is not another implementation PR: it is one
immutable raw file from each of three independent qualified TRIZ experts,
followed by agreement, abstention, disagreement, adjudication, and keep/amend
receipts. The old v1.1 `data/pilot/*` files remain synthetic calibration and
must not be reclassified. Until the human package closes, Wave 2 canonical
labels, WLT claims, and Lab 06 remain gated.

### Phase F — completed automated A0 exploration

| Delivery | What became usable | Scientific boundary |
|---|---|---|
| PR [#31](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/31) | pre-sealed deterministic corpus foundation | procedural targets only; no model result |
| PR [#38](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/38) | A0-R R1.3 calibration and protocol freeze | exact power receipt, freeze manifest, and protocol lock; no model or sealed-output access |
| PR [#39](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/39) | A0-R R1.4a implementation binding and deterministic pre-output tests | exact runtime/input/code/statistical contract; no model or sealed-target access |
| PR [#40](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/40) | A0-R R1.4b guarded runner and failure receipts | exact-head qualified harness; model and sealed-target access remained blocked until merge |
| PR [#41](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/41) | one-time R1 sealed execution, transparent clerical recovery, and immutable publication package | positive exploratory same-model replication; E0, evidence-ineligible, and not expert-validated |
| PR [#42](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/42) | R1 publication closeout | documentation-only closeout; no empirical claim changes |
| PR [#32](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/32) | calibrated and frozen A0 protocol `v1.0.3` | freeze and controls, not evidence by themselves |
| PR [#33](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/33) | hosted repository lane allowed to complete | CI policy correction only |
| PR [#34](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/34) | exact-model activations, sealed analysis, immutable result package, `make a0`, HTML report, schemas, and receipts | positive exploratory proxy result; not expert-validated TRIZ evidence and not claim-eligible |

The sealed A0 result is `positive` under its frozen automated-proxy rule:
maximum statistic p = 0.005, 24/24 paired-family successes, maximum primary
macro-F1 = 0.687364, problem-only surface macro-F1 = 0.499130, and margin =
0.188234. The strongest preregistered combination was layer 6 at the mean
transformation span. Energy and transport remained at 0.5 accuracy in that
combination, the corpus is procedural, and only one small model revision was
tested. Those limits are part of the result, not optional caveats.

### Phase G — cost-aware receipt routing (verified complete)

CCP PR [#37](https://github.com/MarcoPorcellato/commit-ci-preflight/pull/37)
merged at `044697dee9a0d678d30a4847d62ddf9b4970505b`, adding v2 multi-runtime
receipts with exact per-runtime configuration and digest binding. Latent-TRIZ
PR [#51](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/51) merged at
`39ad1965e82f5aa2f4671e38708e401774f176ec`; exact source head
`e249c4b42795b27d27d78a0b5c3526a38e7809de` was qualified by receipt branch
`ccp-evidence/e249c4b42795b27d27d78a0b5c3526a38e7809de` (evidence commit
`e4fb6c183483cedd12d9306c29938d1bdedae966`) and terminal run `31934684914` (Python 3.11 2m44; CCP 42s).
PR [#50](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/50) merged at
`e6a634d52fcd153d6c78224fabb8df4713b18415`, publishing immutable public GHCR
verification images for Python 3.11 and 3.12; policy references use only their
digests. PR [#53](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/53)
merged at `64892dd227f7256fe0dae204e501b2867ef4f905`, adding the trusted CCP
v2 verifier bridge. The initial matrix PR
[#54](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/54), at head
`c6874fdaa11aeebee079579b0a323146818be8fa`, was closed without merge because
its v2 receipt could not yet be evaluated against the base's v1-only policy
route. PR [#55](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/55) then
merged the fail-closed v1/v2 policy selector at
`28b6c5d309eb5e640c34945e598b3a1e8425d979`. PR
[#56](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/56) then qualified
the rebased matrix head `c913ea5b89bc6feb261560ebfd80bb5bc2d23080` with a fresh
v2 receipt and merged at `1457e2c4e5e6affba75266fc0b62e7375f8e16fa`.
Post-merge PR [#57](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/57),
head `f5dbd54c20eca05cc7cc4c5e03b3dc3cce243092`, merged at
`9ef86ec22a46422eb586fbe29085cc0b05672ea8` after run `31949031711` created
no hosted Python candidate job. Compared with pre-migration run `31948392224`,
run wall time fell from 237 to 71 seconds and summed successful-job intervals
fell from 473 to 56 seconds. GitHub reported zero billable milliseconds for
both public-repository samples, so this proves reduced hosted execution, not a
monetary saving. No R2 boundary changed.

### Phase H — expert TRIZ reference corpus foundation

The laboratory now has a rights-aware reference layer for three supplied
expert artifacts and a curated catalog of the official public resources at
TRIZ Consulting Group: Robert Adunka's forty-principle teaching set, the
Mann-Dewulf-Zlotin-Zusman Matrix 2003, Gregor Panitz's TRIZ tools relationship
map, method and training indexes, practitioner tools, and application examples.
The public repository tracks exact artifact hashes where local files were
supplied, source metadata, page locators, authority status, rights status, and
independently written principle summaries. It does not vendor third-party PDFs
or treat expert recommendations as automatic ground truth.

This phase improves construct coverage and future question design but does not
change any A0-R2 evidence. The frozen R2.3 run remains byte- and rule-bound to
its preregistration. The new corpus is reserved for a separately frozen
R3/EXP-001 design with non-poolable `TRIZ-blinded` and `source-exposed` strata,
source-family splits, lexical controls, negative controls, and independent
labels.

**Exit evidence:** strict source, web-corpus, and principle schemas; exact
three-file hash receipts; forty ordered page-bound principle records; a curated
official-site inventory; fail-closed rights and R2 exclusion tests; maintained
reference documentation; repository qualification; reviewed PR and terminal
merge gates.

## Current bottlenecks

The laboratory now has one empirical automated-proxy result, while the authentic
TRIZ route still lacks expert-validated constructs and canonical labels. The
two routes must remain separate:

```text
annotation contract integrity
        -> permanent Wave 1 negative control
        -> label-free paired Wave 2
        -> independent canonical labels
        -> empirical artifact contract
        -> real multi-view activations
        -> held-out-domain EXP-001-R
```

The automated route may challenge A0 through a new preregistered replication,
but it cannot unblock or replace any node in the authentic route:

```text
A0 published result
        -> independent procedural-corpus replication (R1 published)
        -> independent model-family replication
        -> robustness conclusion for automated proxies only
```

## Ordered delivery plan

### Parallel Phase A0 — automated weak-hypothesis exploration

A0 may run before the human H1 gate because its targets are assigned by frozen
procedural transformations rather than expert judgment. It remains independent
from Wave 2 and cannot validate the TRIZ construct or promote a claim. Its
complete freeze, corpus, controls, activation, analysis, publication, and
completion contract is defined in
[A0 Automated Weak Hypothesis Exploration](./A0_AUTOMATED_WEAK_HYPOTHESIS.md).

The A0 protocol was merged and frozen before model output. PR 34 then passed the
scientific artifact audit, exact-head CCP receipt verification, Python 3.11 and
3.12 repository checks, the trusted aggregate gate, and exact-head squash merge.
The tracked package includes the exact-revision activation receipt, statistical
result, representation index, publication manifest, and HTML report. Dense
vectors remain external and hash-addressed.

**Current status — verified complete:** protocol `v1.0.3` is immutable and run
`a0-v1.0.3-e93a9faa` is published on `main` at PR 34's merge commit.

- deterministic design selected by power calibration:
  4 problem families/domain, 24 problem families total (48 paired cases), 199 permutations, critical=19,
  MDE 0.333212784429589
- v1.0.1 pre-freeze prototype was rejected and redesigned pre-freeze as token-matched
  unique role pairs
- exact Pythia activations and the sealed automated-proxy result are published
- all registered claims remain E0 and H1/Wave 2 remain independent

### Parallel Phase A0-R — automated replication and robustness

A0-R is the next fully automated milestone. It is a new preregistered experiment,
not a mutable continuation of the observed A0 protocol. Its canonical contract
is [A0 Replication and Robustness](./A0_REPLICATION_AND_ROBUSTNESS.md).

**Dependency:** A0 is terminally published and its inputs and results remain
byte-stable.

**Outcome:** challenge the A0 signal on an independently generated procedural
corpus, first with the already cached exact model revision and then, only with
explicit acquisition approval, with an independent model family.

**Exit evidence:** pre-output protocol freeze, independent case/template hashes,
the full shortcut suite, exact-model receipts, a terminal positive/null/failed/
non-interpretable result, one-command verification, artifact audit, exact-head
qualification, and immutable publication.

**Claim impact:** none. A successful A0-R strengthens only the robustness of the
automated proxy observation; it does not validate Segmentation or Inversion as
TRIZ constructs.

**Current status — verified complete:** R1.2 has a deterministic
independent 48-family / 96-case corpus, physically separate calibration and
sealed targets, a zero-violation comparison against the published A0 corpus,
14/14 passing shortcut controls, strict schemas, and byte-for-byte one-command
verification. R1.3 has frozen the protocol with a separately hashed power
receipt and freeze manifest. R1.4a and R1.4b are merged and verified. The
single sealed R1 run is complete with a positive exploratory fixed-primary
result: 23/24 family successes, macro-F1 0.624348 versus 0.499130 for the
problem-only surface baseline, margin 0.125217, six domain-direction successes,
and permutation p = 0.002. PR 41 completed R1.5 at
`05ba15a28442260c32951413c9128f0179573198`: the immutable package preserves
the raw schema-invalid output, the clerically recovered result, and a receipt
proving that exactly 54 domain labels changed while metric values did not. The
declared dense asset, one-command verifier, exact-head repository check, and
all seven hosted checks passed. Published A0 remained byte-stable, all claims
remain E0, and H1 and Wave 2 were untouched. The next automated milestone is
R2, gated by explicit approval of its exact model acquisition, license or
terms, disk budget, and material RAM/runtime use. The subsequent authorized
checkpoint produced a verified SmolLM2 acquisition dossier: nine runtime files,
727,058,433 bytes total,
integrity verified, no model load, and no sealed execution. The operator then
authorized one bounded CPU feasibility test. PR 44 merged its contract before
the first load. The schema-valid payload reports runtime compatibility, 2.37
GiB peak RSS, and 3.81 seconds total time; the outer guard separately remains
`cleanup_uncertain` after exit 70 despite a clean post-run observation. No rerun
is permitted, and sealed execution remains gated.

PR 46 then merged the R2.1 publication and receipt branch at
`1f35ba353e792aa263db7449216e3172d0306798` after exact head
`5f9c21db944f25fd1dac4a550911c85e86471e35` and public receipt publication.
R2.1 is now verified complete. The SmolLM2 R2.2 implementation is public and
verified complete as a fully automated, local/offline, synthetic tranche: 192 forwards, 1920 vectors, the
final-block primary, descriptive layers, views, and sites, fixed primary
thresholds, strict single target read, failure publication, and
descriptive-only cross-model concordance and resource-envelope refusal. Fifty-five focused synthetic tests
currently pass, the execution contract verifies 11 code files and 9 runtime
files without model load, and no real model load or sealed-target access
occurred. The implementation was locally qualified before publication, then
opened as PR 47. Its first hosted run exposed a fail-closed configuration-digest
bootstrap conflict rather than a receipt-integrity defect. PR 48 migrated only
the trusted digest at `afd4b56ae84a944dc4cd60486caabce9b9452f75`; PR 49 then
activated only the 180-second timeout at
`85180041717f336de554300dda109731b48c6b95`. Both prerequisite PRs used
base-policy exact-head receipts and terminal green gates. PR 47 subsequently
passed its refreshed exact-head receipt and hosted gates and merged at
`fa1e254ec373092278b1ab63f05504545e295b67`. R2.3 still requires separate
explicit approval.

The R2.3 approval-request checkpoint has one canonical human-readable
dossier and a strict machine-readable counterpart. They bind the exact
SmolLM2 snapshot and receipts, the frozen R1/R2 inputs, conservative resource
ceilings, one material attempt, one analysis-boundary target read, all terminal
publication classes, and the no-claim boundary. The original dossier remains
historical `approval_requested`. A later technical target-file hash read outside
the analysis boundary was treated conservatively as consuming its one-read
scope, despite retaining or emitting no target content. The replacement
operator authorization must be recorded separately, bind the exact frozen
protocol and corrected implementation, and be verified by the runner before
any model import or target discovery.

The sole R2.4 attempt subsequently reached a terminal pre-analysis failure:
the locally loaded SmolLM2 adapter rejected the tokenizer return type before
activation extraction. The sealed target file was not accessed. This is a
published `failed` outcome, not a null result or evidence for any TRIZ claim;
the one-run authorization forbids a retry, tuning, model substitution, or
post-hoc protocol adjustment.

R2.3–R2.5 are closed at public `main` commit
`1112bc31e388c5c6857ecfd96542466cf613ea52`: the exact immutable failure package
and its fresh-clone, local CCP, and hosted-gate evidence are published. This
milestone supplies no comparative signal and authorizes no retry. A future R3
or corrective effort starts from a separate preregistration and approval gate.

### A0-R2-C1 — corrective SmolLM2 result path

The immutable A0-R2 failure is preserved. A separate C1 tranche corrects only
the tokenizer container contract (`dict` to `collections.abc.Mapping`) and
adds the realistic regression coverage missing from feasibility and synthetic
qualification. A tokenizer-only local receipt already confirms the exact
runtime returns aligned IDs, offsets, and attention values in a valid
`BatchEncoding`; it loaded no model and accessed no sealed target.

The C1 contract merged and exact-head qualification passed. The authorized C1
execution then loaded SmolLM2 but failed before analysis because the shared
activation normalizer treated the rank-three Llama hidden-state tensor as a
rank-two token matrix. The sealed targets were not accessed; no signal estimate
exists. The C1 terminal package is therefore published as `failed`, and its
authorization is consumed. Any C2 attempt requires a separately preregistered
shape-normalization correction, full synthetic/runtime qualification, and a
new explicit one-attempt authorization. All frozen scientific inputs,
statistics, thresholds, model identity, resource ceilings, no-tuning rule, and
single target-read boundary remain unchanged.

### A0-R2-C2 — singleton-batch shape correction

C2 was the only allowed continuation of C1: it was a separately preregistered,
namespaced correction that removes a singleton batch dimension from Llama
hidden-state layers only after strict shape validation. It was not a C1 retry.
The C2 contract bound the C1 terminal package and retained all frozen
scientific inputs and resource limits. Its one guarded material attempt
successfully produced the activation bundle but terminated with
`A0R2AnalysisError` at the data stage. The terminal package is `failed`; no
statistical inference or claim is available, and any further run requires a
separate preregistration and explicit authorization.

### A0-R2-C3 — analysis-only metadata recovery

The C2 failure is now reproducibly attributable to the missing per-row
`dtype` metadata required by the analyzer. The canonical
[SmolLM2 runtime contract](./reference/smollm2-runtime-contract.md) now binds
the official tokenizer and hidden-state API facts to synthetic and
pre-analysis export checks for future versioned writers. C3 may not rerun
SmolLM2: it is an analysis-only correction that preserves the exact C2
activation receipt, index, and dense-asset hash and can add `float32` only in
memory under an exact-index binding. It must keep the original byte-bound R2
modules unchanged and use separately namespaced C3 recovery/publication code.
C3.0 synthetic qualification and C3.1 corrective isolation are complete. The
explicit authorization was recorded against the immutable contract, and the one
analysis-only run completed after a fresh CCP `Admit`/empty-queue check. It opened
the sealed targets once at the analysis boundary, loaded no model, and produced
the terminal positive exploratory package at
`results/a0r2/a0r2c3-analysis-only-v1.0.0-f8027fd0-r1/`. The primary p-value is
`0.001000`, the macro-F1 margin over surface is `0.147686`, all `24` families
passed, and `6` held-out domain directions succeeded. This remains automated E0
evidence with no claim IDs and no general TRIZ claim. Fresh-clone verification
and exact-head publication remain the final gates. See
[A0-R2-C3 analysis-only metadata recovery](./A0R2C3_ANALYSIS_ONLY_RECOVERY.md).

### PR 30 — annotation ontology v1.2 implementation

**Outcome**

- independent Segmentation and Inversion presence/essentiality scores;
- global contradiction-resolution and feasibility scores;
- mandatory named alternative for `Other`;
- null scores for `Cannot determine`;
- visible definitions, positive examples, near misses, adjacent-principle
  confusions, and decision rule;
- complete form reset after every successful save;
- a versioned cognitive-pilot protocol, without fabricated human results.

**Exit evidence**

- guide, annotation, audit-result, and cognitive-pilot schemas validate with the
  local validator and pinned `jsonschema`;
- focused workbench and audit tests cover every v1.2 branch;
- synthetic v1.1 fixtures are explicitly migrated without being reclassified as
  empirical;
- full repository, docs, Python 3.11, and schema cross-validation gates pass;
- exact-head CCP receipt, `merge-policy/gate`, ruleset re-read, and zero unresolved
  review threads are terminally green.

**Claim impact:** none; all claims stay E0.

**Residual risk:** a software-complete protocol is not a validated human guide.

### Human gate H1 — three-expert cognitive pilot

This is **blocked by real human work**, not by code. The operational handoff is
[H1_COGNITIVE_PILOT.md](./H1_COGNITIVE_PILOT.md). Three independent TRIZ
experts must evaluate the six frozen pilot cases, explain ambiguities, and
produce a versioned keep-or-amend decision. Synthetic or model-generated
responses cannot substitute for this gate. Wave 2 collection cannot start until
H1 closes, although software and archival work may continue.

### Milestone W1 — preserve Wave 1 as a permanent calibration corpus

**Outcome**

- no case text is changed;
- machine-readable `calibration_only`, `freeze_eligible: false`, and
  `known_shortcut_corpus: true` status;
- retained negative report and regression tests that must continue detecting
  the known shortcuts;
- a pre-freeze Candidate Surface Audit contract separated from post-freeze
  Lab 03 so no frozen Lab 02 snapshot is required circularly.

**Exit evidence:** artifact hashes remain stable, the expected-negative audit
passes as a regression, and no EXP-001 manifest can select Wave 1.

**Claim impact:** none; the negative result qualifies the method, not the
hypothesis.

### Milestone W2 — label-free paired Wave 2 contract

**Outcome**

- same base problem, constraints, improvement, and worsening consequence with
  counterfactual Segmentation and Inversion solution variants;
- label-free cases with separate generator draft targets;
- `problem_family_id`, solution-variant, source, generator, template, license,
  and relationship provenance;
- grouped splits that keep every problem family together;
- a sealed later set that is not used to tune Wave 2 or the audits.

**Exit evidence:** problem-only baselines remain near chance; no family crosses
split boundaries; provenance diversity, duplicate, cue, pair, and surface gates
pass under rules fixed before generation.

**Claim impact:** none; a valid candidate corpus is not a result.

### Milestone C1 — canonical human-label pipeline

**Dependency:** H1 closed and Wave 2 contract frozen.

**Outcome**

- immutable raw per-rater files;
- additive adjudication and exclusion ledgers;
- separate canonical labels and a Both/Other/Cannot-determine challenge set;
- Labs 03–05 consume explicit canonical labels and never generator intent;
- case content, targets, labels, relationships, splits, and representations are
  physically separate.

**Exit evidence:** blinded coverage and agreement gates pass; every canonical
label is traceable to raw ratings and adjudication; no mixed ontology revision
or hidden label fallback is possible.

**Claim impact:** none; independently labelled data becomes eligible for a
future frozen study.

### Milestone E1 — empirical envelope v2 and immutable run substrate

**Outcome**

- typed `fixture`, `instrumentation`, `exploratory`, `confirmatory`, and
  `replication` modes without rewriting historical v1 fixtures;
- fail-closed prohibition on empirical input being downgraded to non-empirical
  output;
- planning artifacts separated from evidence artifacts so an E0 claim may have
  a preregistration without pretending to have a result;
- separate recognition, pre-output selection, and causal-control claim branches;
- immutable run directories, atomic publication, real execution receipts, and
  compact summaries pointing to detailed results;
- one shared verified representation store for later Lab 04–06 consumers.

**Exit evidence:** schema mutations reject epistemic downgrades and overwrites;
interrupted writes cannot create valid partial runs; legacy fixtures remain
byte-stable.

**Claim impact:** claim structure becomes more precise; evidence levels do not
change.

### Milestone I1 — published multi-view Pythia instrumentation bundle

**Outcome**

- `problem_only`, transformation, and completed-solution views;
- stable sentinel, span-mean, and boundary token sites;
- complete tokenizer, model, case, license, and execution provenance;
- versioned index and summary in Git, with the verified Safetensors container as
  a release or archival asset rather than a dense Git payload.

**Exit evidence:** hashes, shapes, dtypes, token sites, residual parity, atomic
publish, and fresh-clone verification pass.

**Claim impact:** none; this remains a published engineering smoke.

### Milestone F1 — current model feasibility and statistical calibration

**Outcome**

- live verification of model terms, availability, exact revisions, disk, RAM,
  latency, tokenizer behavior, interpretability resources, and redistribution
  constraints before selecting a primary and replication model;
- simulation calibration for false-positive rate, known signal, domain-only
  confounding, lexical-only confounding, and minimum detectable effect;
- a sample size and permutation budget justified by the calibration rather than
  inherited from a smoke fixture;
- operator-signature and competing-taxonomy controls that distinguish TRIZ
  alignment from generic action or lexical categories.

**Exit evidence:** receipted no-download preflight precedes any authorized
acquisition; any download or material hardware use receives explicit approval;
the preregistration records the chosen model, dataset, views, sites, groups,
controls, sample size, and stopping rules.

**Claim impact:** none; feasibility and preregistration are planning artifacts.

### Milestone R1 — first authentic EXP-001-R exploratory recognition run

**Dependencies:** PR 30, milestones W1–F1, and H1 are closed; Wave 2 and canonical labels are
frozen; Candidate Surface Audit passes.

**Outcome**

- real exact-revision activations;
- multi-view and multi-site recognition analysis;
- grouped leave-one-domain-out evaluation;
- shared grouped permutations with nested selection and the calibrated budget;
- lexical, provenance, matched-negative, random-partition, adjacent-principle,
  and generic-transformation controls;
- a reproducible public bundle whether the result is positive, null, or failed.

**Exit evidence:** immutable dataset, canonical-label, model, environment, code,
run, and result receipts link end to end; rerun instructions work from a fresh
clone plus declared external assets; the result is marked `empirical: true`,
`scientific_status: exploratory`, and `evidence_eligible: false` unless a later
confirmatory contract explicitly changes that boundary.

**Claim impact:** the run may inform a future recognition-specific claim, but it
does not by itself establish pre-output selection, causal use, or the Strong
Latent TRIZ Hypothesis. Null results are published without reinterpretation.

## Construct-validity and causal transition plan

The next scientific tranche follows the formal contract in
[HYPOTHESES_AND_FALSIFICATION.md](./HYPOTHESES_AND_FALSIFICATION.md). The
the seven comparative null packages are retained as a robustness constraint;
they do not authorize a rerun or a post-hoc threshold change.

The execution order is intentionally front-loaded toward evidence quality:
`H1 -> strengthened controls -> held-out recognition -> one-principle
causality -> composition/contradictions -> independent model replication ->
Track B emergence`. Track B can be prepared with no-model artifacts in
parallel, but no Track A result may select its corpus or checkpoint. Adding
principles, models, or mechanistic tooling before the causal predecessor is
deferred unless it closes a named control or reproducibility gate.

### CV1 — H1 expert construct pilot

**Dependency:** annotation ontology v1.2 and the frozen blinded workbench.

Three independent TRIZ experts rate a small blinded pilot for Segmentation,
Inversion, adjacent principles, contradiction resolution, feasibility, and
abstention. Raw ratings, adjudication, exclusions, and canonical labels remain
separate. The model results are not shown to raters.

**Exit evidence:** exact guide/case/session hashes, independent rater receipts,
agreement statistic and confidence interval, disagreement ledger, adjudication
record, and a keep/amend decision. Synthetic or model-generated ratings cannot
close H1.

### CV2 — strengthened negative-control corpus

Add lexical- and length-matched generic transformations, near-neighbour
principles, cosmetic counterfactuals, Matrix direction swaps, unsupported
Panitz edges, abstention cases, random-label/direction controls, and extreme
domain shifts (for example mechanical, organisational, biological, and
software cases). Freeze family and source splits before any model output.
Keep source-blinded transfer and source-exposed competence physically and
statistically separate; a source-exposed success can never rescue a blinded
failure.

**Exit evidence:** contamination, shortcut, split, power, and abstention
receipts; all controls pass or are explicitly published as readiness failures.

**No-model checkpoint (2026-08-18):** the machine-bound protocol is now
`experiments/cv2-negative-controls/protocol.json`, with a strict schema and
cross-validator registration. It freezes eleven control families, grouped
family/source/domain splits, non-poolable blinded/exposed strata, all required
readiness receipts, and all terminal classes. This is preparation only; no
control targets or model outputs exist.

### CV3 — one-principle causal pilot

**Dependency:** CV1 agreement gate and an out-of-sample decodability direction.

Select one operator by the frozen expert and data criteria, never by inspecting
the causal outcome. Prepare a separate Lab 06 contract for steering, ablation,
dose-response, opposite-sign and norm-matched controls, plus capability
preservation. Do not run it until the exact dossier and resource gate are
approved.

**Exit evidence:** immutable intervention parameters, activation and behavior
receipts, positive/null/failed/non-interpretable result, and a report that does
not promote a TRIZ claim.

This gate has priority over broad forty-principle coverage and over additional
model-family runs. The selected operator must be chosen from the frozen human
and held-out data rules before the intervention outcome is visible.

**No-model checkpoint (2026-08-18):**
`experiments/lab06-causal-intervention/dossier.json` and
`docs/LAB06_DOSSIER.md` define the single-pilot arms and approval boundary.
The dossier remains `blocked_by_h1`; its operator is deliberately unset and
all model, target, training, and run authorization flags are false.

### CV4 — contradiction and composition pilot

**Dependency:** CV3 passes its causal integrity gate.

Test technical/physical contradictions and two-operator compositions separately
from single-operator recognition. Include Matrix direction, random-composition,
single-operator, and abstention controls. A composition result cannot rescue a
failed single-operator primary.

### CV5 — Track B controlled emergence

Track B remains a separate preregistered route. Train a small model from scratch
on provenance-audited problem-solution data with no TRIZ terms, sources,
canonical examples, matrix cells, or Panitz edges. Freeze data, checkpoints,
seeds, matched shuffled-solution controls, generic-transformation controls, and
held-out domains before inspecting emergence. Pretrained-model results cannot
select the Track B corpus or checkpoint.

**Exit evidence:** training and data receipts, checkpoint schedule, independent
seed replication, held-out decodability, causal controls, capability checks, and
every terminal outcome published under the E0-E6 envelope.

**No-model checkpoint (2026-08-18):** the independent preparation contract is
now machine-bound in `experiments/track-b-emergence/protocol.json` and
`freeze-manifest.json`, with strict schemas and cross-validator mutation tests.
It freezes the no-TRIZ-term boundary, held-out domain/operator codes, three
independent run seeds, contamination/shortcut/random/generic controls, and
the terminal publication classes. The protocol is `planned` and
`no_model_ready`; it authorizes no corpus access, training, model load, target
access, CCP, or claim promotion.

### CV6 — contributor path and release hygiene

Add a small no-model quickstart that reaches a synthetic result in under thirty
minutes, while keeping model/target execution behind CCP and explicit approval.
Publish a claim/evidence profile for every scientific package and preserve dense
assets externally with immutable locators and hashes.

The quickstart must also show one published positive exploratory package and
one published null or failed package, explain why neither proves the construct,
and expose the exact command that performs the fail-closed artifact audit.

### CV7 — independent replication after causal stability

Only after CV3 passes its integrity and capability gates, replicate the frozen
single-operator contract on an independent model family, dataset, implementation,
or team. The replication must be selected before observing its outcome and must
retain the same controls and terminal publication classes. A replication null
is evidence against robustness of the frozen proxy, not a license to retune the
primary.

## Work after the first authentic recognition run

Proceed only when the predecessor result justifies the next cost:

1. close H1 with three independent experts and freeze the canonical operator
   ontology before treating any proxy as construct evidence;
2. construct Lab 05 directions on training domains and evaluate them on held-out
   domains with split-half, bootstrap, permutation, orthogonal, random, and
   opposite-sign controls;
3. start Lab 06 only after an out-of-sample direction exists, then test dose
   response, ablation, bidirectionality, and capability preservation;
4. separate pre-output selection from recognition by annotating what the model
   actually generates after problem-only activations are captured;
5. replicate across an independent model family, dataset, implementation, or
   team before E5;
6. examine intermediate training checkpoints only after the primary recognition
   contract is stable;
7. reserve controlled training and E6 for a separately preregistered Track B;
8. publish versioned releases, tutorials, role-specific onboarding, issue
   milestones, Discussions, and archival assets as first-class reproducibility
   surfaces.

## Deferred until justified

- empirical Lab 05 before held-out-domain recognition;
- Lab 06 steering or causal claims before an out-of-sample direction;
- SAE, Jacobian, sparse-feature, or broad localization work before a stable
  target effect exists;
- expanding beyond Segmentation and Inversion before the two-operator contract
  works;
- using Wave 2 to redesign its own audits;
- promoting a claim from a smoke, dashboard, plot, source check, or partial run.

## Cost- and token-aware execution policy

1. Use deterministic discovery, parsers, targeted tests, and exact Git evidence
   before any LLM task.
2. Give documentation, mechanical migrations, bounded tests, and isolated audits
   to the cheapest suitable worker; provide only the necessary excerpts.
3. Reserve the primary model for architecture, integration, scientific and
   statistical judgment, security, release qualification, and merge decisions.
4. Never depend on an interactive local model-serving application. Do not repeat broad repository discovery when the master
   plan, exact checkpoint, or a recent receipt already answers the question.
5. Run the narrowest relevant validation first. Use the path-aware remote gate,
   and require exact-head CCP for scientific, governance, workflow, dependency,
   or otherwise high-risk changes.
6. Keep one isolated worktree and one owner per file group. Workers do not commit,
   push, merge, or revert other work.
7. At each milestone report: result, terminal validation evidence, claim changes,
   residual risks, and the next dependency.

Cost reduction never weakens an evidence gate. `RUNNING`, partial tests, source
inspection, or a receipt for another commit are not a pass.

## A0X six-model A0/A0-R1 replication tranche

### Pre-material readiness correction — 2026-08-30

Gate A passed for exact source `68f8bfe75a883054118246101485f71a56a5e82e`,
but a separate target-free Gate-B inventory correctly found that repository
qualification did not prove a runnable pair-specific Python environment or
snapshot. The correction freezes a readiness receipt binding a regular Python
3.11 venv executable, exact packages/APIs, and independent regular runtime
files before descriptor construction. It also enforces declared tokenizer
padding and terminal recovery for the first post-claim observation write.
After deterministic regeneration and independent review, obtain a new Gate A;
then Gate B may separately materialize only the selected pair's runtime. Gate C
remains the later one-shot scientific authorization. Do not reuse the earlier
receipt for corrected bytes.

A0X is the bounded model-family replication route for the six exact snapshots
that were acquired after the original Pythia work. It is not an alternative to
the human H1 gate and does not pool outcomes across models or legs.

The preparatory dependency chain is:

```text
historical A0 and A0-R1 rules
        -> protected trees and public selection identities
        -> exact source/test implementation bindings
        -> one freeze per leg
        -> six approval-requested dossiers per leg
        -> no-model qualification and independent review
        -> separate exact-head qualification and approval for one pair
        -> first terminal outcome and immutable publication
```

Tasks 10 and 11 have completed offline implementation, final no-model
qualification, and independent review. The two frozen legs and twelve
pair-isolated dossiers are recorded with exact hashes. The TDD-corrected
producer at
commit `27adf8d0820b3cd96f9c5e149de9b580ae41f639`, tree
`d8e0364d1313fde0898a44517ae6d233d9e10763`, executable SHA-256
`c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`
has passed one exact Matrix qualification with all five checks terminally
green. Its source and receipt are durably preserved on dedicated public
branches, and CCP PR #70 is merged as
`1a2e081cd3912b0fd63a7226a4564f1d85a51eb8` with the exact qualified tree. It
is not installed, but A0X now deliberately binds that exact identity.
Correction anchor `6b8c8e3491b24fa4717b2f4faa8700b007c48892`
regenerated the complete package deterministically in the active checkout;
the frozen verifier independently repeated its byte-determinism checks in
disposable source copies before this correction. A later single exact-head
attempt at `32e03b5…` preserved terminal `FAIL`: both schema checks passed and
both repository checks reached their approximately 300-second configured
timeouts. Correct V2 verification established receipt integrity `PASS` and
policy status `FAIL`, because the attempt used default `current-v2` rather than
the frozen `matrix-v2-legacy-v1` profile. TDD now sets the repository checks to
3,600 seconds, leaves schema checks at 300 seconds, requires the legacy profile
on every operator target, and verifies against the V2 policy. No retry has
occurred. Fresh no-material verification passed 10 frozen-package tests, 248
A0X tests, 155 schema agreements with 19 rejected mutations, and 1,075
repository tests with one documented skip. Independent review returned
`APPROVE` with no P0--P3 findings. The next gate is a local package commit,
followed by a separately authorized Latent-TRIZ exact-head
qualification. Task 12 is not authorized. The authoritative operator-facing contract is
[`A0X_SIX_MODEL_CAMPAIGN.md`](./A0X_SIX_MODEL_CAMPAIGN.md).

A second authorized qualification at `fb9484a…` then ended terminal `FAIL`
without timeout or cancellation: schema passed, but both repository checks
returned exit 1 because the Matrix binding test invoked `make -n` inside lean
verification images that deliberately remove build-only `make`. A clean host
run passed all 1,075 tests, and a no-`make` environment reproduced the five
missing-executable errors. The dependency-free correction now parses the
Makefile with Python and requires one exact, non-empty recipe for all five
Matrix operator targets, preserving the legacy-profile and V2-policy checks.
The attempt is consumed and was not retried. Fresh verification passed the
no-`make` regression 3/3, frozen package 10/10, A0X aggregate 248/248, schema
cross-validation 155 agreements with 19 rejected mutations, repository suite
1,075 tests with one documented skip, documentation audit, and diff check.
Independent Luna review returned `APPROVE` with no P0--P3 findings. Only the
local package commit remains before another exact-head authorization.

A0X acceptance criteria are:

- inherited corpus, split, control, statistic, threshold, and endpoint rules
  are copied by value while historical model identity is not misrepresented;
- six exact cards form a complete two-leg by six-model Cartesian product;
- every dossier binds one and only one leg/model pair, dense cap, output path,
  material contract, and future authorization path;
- the verifier rejects cross-leg, cross-model, wrong-freeze, source/test drift,
  cap overflow, and Make-target mapping drift;
- no-model qualification proves zero model loads, tokenizer constructions,
  sealed-target reads, CCP invocations, and remote mutations;
- each later material pair has a new exact authorization and publishes its
  first terminal outcome without retry, tuning, substitution, or pooling;
- interpretation remains E0 exploratory and does not promote a general TRIZ,
  causal, or training-data claim.

## Improvement-tranche checklist

- [x] Preserve A0/R1 positives, seven-model comparative nulls, and the R3
  reference-integrated package as immutable E0 exploratory records.
- [x] Publish explicit Weak/Strong definitions, falsification rules, evidence
  axes, and the no-claim boundary.
- [x] Prepare and mechanically audit the v1.2 H1 packet without fabricating
  human judgments.
- [ ] Collect three independent expert sessions and publish agreement,
  abstention, disagreement, adjudication, and keep/amend receipts.
- [ ] Freeze the stronger control corpus and grouped source/domain splits before
  any new model output.
- [ ] Demonstrate one out-of-sample operator direction and qualify the Lab 06
  causal dossier before composition or broad model scaling.
- [x] Prepare the Track B no-TRIZ-term from-scratch protocol independently of
  Track A selection decisions (no-model contract only; training remains gated).
- [x] Publish the sub-thirty-minute no-model contributor quickstart and a
  positive/null evidence-profile walkthrough entry point (`make
  no-model-quickstart`); the walkthrough remains readiness-only.
- [x] Freeze and validate the separate no-download dossier for GPT-2 and
  SmolLM2-135M without conditioning on prior model scores.
- [ ] Acquire, integrity-verify, feasibility-test, and execute the two new
  candidates under separate exact approvals and one-run limits.
- [x] Freeze the A0X two-leg, six-model no-material contract and prepare twelve
  separate `approval_requested` dossiers.
- [x] Qualify and independently review the complete A0X no-model package, then
  stop before any Task-12 material execution.

The unchecked items are genuine prerequisites, not missing documentation. A
future run may not be called WLT or SLT evidence while any applicable item is
open.

## Release and completion definition

The laboratory is not complete merely because all modules exist. Completion
requires a new contributor to be able to:

- clone the public Apache-2.0 repository;
- launch the visual laboratory with one command;
- reproduce at least one complete empirical path using declared assets;
- inspect its frozen inputs, controls, receipts, result, and limitations;
- understand the E0–E6 claim boundary and find published null results;
- contribute through documented researcher, developer, statistician, or TRIZ
  specialist paths without private assistance.

Update this file whenever a milestone status, exact anchor, dependency, or exit
gate changes. Never rewrite a delivered negative result into a success.
