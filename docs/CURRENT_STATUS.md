---
type: status-report
title: Current Laboratory Status
description: Public, receipt-backed snapshot of the Latent-TRIZ laboratory and its evidence boundary.
status: canonical
last_verified: 2026-08-31
---

# Current laboratory status

This page is the short, public status snapshot for the Latent-TRIZ laboratory.
The long-form history remains in the [Laboratory Master Plan](./LABORATORY_MASTER_PLAN.md)
and the event-by-event chronology remains in [`docs/log.md`](./log.md).

## Public checkpoint

- **Public main:** `d2a475f58db668a2ce0a4ec48082189422b19eab`
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

### A0X Hosted Gate A implementation boundary (current local checkpoint)

Tasks 1–9 of the Hosted Gate A migration are locally complete. Task 9 ended
with the deliberate stale-freeze `NO-GO`; Task 10 is the only regeneration
boundary. The seven hosted lanes are `repository-python311`,
`schema-cross-validation-python311`, `repository-python312`,
`schema-cross-validation-python312`, `a0x-no-model`, `a0x-synthetic`, and
`documentation-audit`.

Current Gate A binds four hosted inputs—manifest, attestation bundle, trusted
root, and transport—with caps 32 KiB, 1 MiB, 2 MiB, and 16 KiB. Gate B may
create the fifth verification receipt, capped at 32 KiB, only after offline
verification. There is no rerun and no CCP Gate A fallback. CCP Gate C remains
a separate local coordinator. All old CCP Gate A receipts are **Historical
evidence**, not current hosted qualification.

The first real post-merge hosted Gate A run is acceptance only. Capture,
publication, Gate B, and Gate C each require separate authorization; the
trusted-root snapshot cannot expose revocations published after that snapshot.
The state remains `sealed_gate_pending`. No real GitHub CLI verification,
network capture, Gate B runtime bundle, Gate C execution, model, tokenizer,
target read, CCP heavy command, push, PR, merge, or evidence publication is
authorized by this checkpoint.

### Historical A0X hosted-integration boundary

Public `main` `d2a475f58db668a2ce0a4ec48082189422b19eab` now installs the
pinned schema oracle for GitHub-hosted Python 3.11 and 3.12 repository checks.
PR #110 reached that bootstrap state through a one-time CCP-backed
administrative bridge after its hosted run failed on the missing dependency;
that bridge is not a hosted PASS. PR #109 is being reconstructed against this
main without rewriting history. Its A0X Gate B hardening remains anchored at
implementation commit `74d6bc048e656f3ced2d4bc6db4b0492dfd16359` and
generated binding commit `50cf959e7a9b50d68ee58a11ac063e6681761abe`.
The historical A0/A0-R1 freeze SHA-256 values in that package are
`7b4920328414ae93eda793b00770ca1dae080656bf62600b233e8c1afd6448ff` and
`9713376406522581cec9c32cc71f0e4c215066e47fe875e4c332ee49ff8b00e1`.

Target-free verification passed: focused hardening 97/97, frozen 11/11,
synthetic 293/293, schema cross-validation 155 agreements with 19 rejected
mutations, and the complete repository suite 1,125 tests with 11 documented
skips. The integration ancestry commit is
`7ac5a6065d78974f52a86816b019184f8f147bd7`; its merge tree stayed
byte-identical to the prior PR head. The next permitted actions are fresh local
target-free verification, a non-forced PR #109 update, and new GitHub-hosted
gates. Merge remains separate. Gate B/C, model/tokenizer access, target reads,
and scientific execution remain unauthorized; the state is
`sealed_gate_pending`.

### Historical A0X pre-material readiness boundary

Exact source `68f8bfe75a883054118246101485f71a56a5e82e` passed Gate A; the
receipt-file SHA-256 is
`3f75c665115c00fd18df1a5fb403f6dd5e410b5d5cdb12c78eada39effb1810e`
and its evidence commit is `fc46c39421ae85713f473ef49a1270beab3aefe6`.
A target-free audit before Gate B nevertheless found two unproven material
prerequisites: the available venv launcher resolved to a package-incomplete
base Python, and the isolated clone lacked the pair-specific model snapshot.
The local readiness correction binds an independent Python 3.11 executable,
exact package/API facts, and independent regular snapshot files before a
runtime descriptor can be created. It also closes tokenizer-padding and
post-claim observation-write gaps. Because these are frozen implementation
changes, the prior Gate A evidence becomes historical for the corrected HEAD.
Deterministic regeneration and full target-free review are complete. The next
stop is a new explicit Gate A authorization; no Gate B or C action is
authorized.

The implementation anchor is `7e1afaba83def501a2641a036c10aae1b98be7b0`.
Regenerated A0 and A0-R1 freeze SHA-256 values are
`6fc72f35c1c2ae0e069164cef34eeb865712f2728555596c1bf3363603541e53` and
`f9c80dc071944e3f2c5e8e531a84ae670a9480f1e0c65e51847d1ec66ff75c54`.
The corrected implementation revalidates regular-file type, link count, bytes,
card, source receipts, and the full model binding again at every final material
boundary, including once more immediately before model construction. Final
target-free verification passed: frozen 11/11, synthetic 278/278, schema 155
agreements with 19 rejected mutations, and repository 1,110 tests with one
documented skip. Final independent Luna security, freeze/package, and
documentation reviews all returned `APPROVE` before the local package commit.

### A0X final integration boundary

The local exact-head qualification of
`4aee4698f5c59101b1f3292519f10ae802629bf7` passed, with receipt-file
SHA-256 `08b1a8f1c08d2ab9784c95acd3b452c218b76108744a129cd6b8df2aef52c447`.
It is historical after the policy-only prerequisite advanced public main to
`4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08`: an integrated source commit
requires its own receipt. The only permitted preparatory work is to merge that
trusted base, retain source-snapshot and full-asset verification separately,
and prove the complete A0X protected set remains byte-identical. No model,
target, tokenizer, CCP heavy command, publication, or scientific retry is
authorized until a new exact-head CCP authorization is granted.

The historical detail below remains evidence, but this continuation statement
governs the current gate.

The A0X six-model campaign is now at its frozen no-model checkpoint. Two
independent legs preserve the historical A0 and A0-R1 rules, and twelve
single-pair dossiers cover six exact model snapshots without pooling. Every
dossier remains `approval_requested`; none authorizes material access. The
complete local no-model qualification and independent architecture/science
review now pass, and the exact freeze/dossier hashes are recorded. A0X is
stopped at `sealed_gate_pending`: correction anchor
`6b8c8e3491b24fa4717b2f4faa8700b007c48892` deterministically regenerated the
two freezes and twelve dossiers, but no Latent-TRIZ exact-head qualification
exists and no pair is authorized for material execution. The correction
removes an unintended test-only dependency on `make`. Fresh no-material
verification passed: no-`make` regression 3/3, frozen package 10/10, A0X
aggregate 248/248, schema cross-validation 155 agreements with 19 rejected
mutations, repository suite 1,075 tests with one documented skip,
documentation audit, and diff check. Independent Luna review returned
`APPROVE` with no P0--P3 findings. The local package commit is the remaining
local gate. See
[A0X six-model campaign](./A0X_SIX_MODEL_CAMPAIGN.md).

The later CCP compatibility producer has now completed its own exact
qualification after a TDD fixture-path correction. Qualified source commit
`27adf8d0820b3cd96f9c5e149de9b580ae41f639`, tree
`d8e0364d1313fde0898a44517ae6d233d9e10763`, and executable SHA-256
`c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`
passed all five Matrix checks; receipt ID
`sha256:21d5cf99a9d142b879b37ef8bb2f50573e45fd569a2259fa863a50fe6be08e85`.
This qualifies that exact producer only. It remains uninstalled, but its exact
source and receipt are durably published on dedicated branches and CCP PR #70
is merged as `1a2e081cd3912b0fd63a7226a4564f1d85a51eb8`, with the exact qualified
tree. A0X now deliberately binds this producer; its material contract is
SHA-256
`b56b860a4f4673f675035e0c76aa1b79e75b37ace9c441b2d1e36076d35c3fc8`.

The later single authorized exact-head attempt at
`32e03b5ef34bb1d8f778877514601994df9c3898` ended terminal `FAIL`: both schema
checks passed, while both repository checks reached their approximately
300-second configured timeouts. Receipt ID
`sha256:bbe9173bfe489e34071f71ce6822df26126f1026d939e1693245fd47daa864d9`;
receipt-file SHA-256
`63a920e8cd97310a857be8465924311389edeb61746945c9219f4c85e2500e01`.
Correct V2 verification proved receipt integrity `PASS` and policy status
`FAIL`; the run had used the default `current-v2` plan instead of the frozen
`matrix-v2-legacy-v1` profile. No retry occurred. The TDD correction gives the
two repository checks 3,600 seconds, retains 300 seconds for schema checks,
pins every operator target to the legacy profile, and uses the V2 verification
policy. After the final package commit, the remaining
preparatory gate is a new exact-head authorization bound to that commit and
the corrected plan digests.

The subsequent one authorized attempt at
`fb9484a89549fbbbfc5395932954b2d9565d91d6` ended terminal `FAIL` without
timeout or cancellation. Both schema checks passed; both repository checks
returned exit 1. Receipt ID
`sha256:f5348d82568ba98c6003132534b3a202631f04c42972b965251adaa2ca367dde`;
receipt-file SHA-256
`5bb2e49da31381e4c22858556e4c54f373ee69dfcea8f578e050efb6268e4232`.
V2 verification reported integrity `PASS` and policy `FAIL`. A clean host run
passed 1,075 tests, and the Matrix module reproduced five missing-`make`
errors in the lean runtime environment. The verification images remove
build-only `make`, so the corrected test now parses and compares the five
operator recipes using only Python while retaining exact profile, policy,
generation, receipt, and expected-commit assertions. This attempt is consumed;
no retry or scientific access followed.

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
