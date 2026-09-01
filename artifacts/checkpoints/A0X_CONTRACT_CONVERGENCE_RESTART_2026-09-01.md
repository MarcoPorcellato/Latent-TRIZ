---
type: restart-checkpoint
title: A0X contract convergence restart checkpoint
status: local-reviewed-non-qualified
version: 1.0.0
date: 2026-09-01
branch: agent/a0x-contract-convergence
code_head: 092a06aee5d4e50055ed454f22c988057566cf03
code_tree: 379b7eac4eeb50ea73ff269673f7b0207fe0f33e
source_base: 2670dbd8008b7498c417b03a38d475cb5acd279b
scope: target-free
---

# A0X contract convergence restart checkpoint

## Purpose

This checkpoint preserves the first useful, independently reviewed A0X
architecture-convergence boundary before a Mac restart. It records completed
Tasks 1–4, remaining work, exact source identities, evidence, review rulings,
and safe recovery instructions.

This is a **local engineering checkpoint**, not a scientific result, Hosted
Gate A qualification, Gate B authorization, Gate C execution approval, CCP
receipt, publication candidate, or merge candidate.

## Durable recovery identity

- Durable repository:
  `/Users/marco1/Documents/CODICE con VS CODE/Emergent-AI-TRIZ`
- Durable local ref:
  `refs/heads/agent/a0x-contract-convergence`
- Reviewed code commit:
  `092a06aee5d4e50055ed454f22c988057566cf03`
- Reviewed code tree:
  `379b7eac4eeb50ea73ff269673f7b0207fe0f33e`
- Historical source base:
  `2670dbd8008b7498c417b03a38d475cb5acd279b`
- Historical source tree:
  `63c9e015c30c2c4aef48730718db8129a2d630f0`

The durable branch was imported into the primary repository without switching
its dirty checkout or changing any user file. The primary checkout remains on
`agent/a0x-six-model-design`; its pre-existing work must be preserved.

## Canonical specification and plan

- Specification:
  `docs/A0X_ARCHITECTURE_CONVERGENCE.md`
  - SHA-256:
    `1f834e501fba2ff4e10652846b80ae8b49de4729028c149c720a1a5ec339675c`
- Implementation plan:
  `docs/superpowers/plans/2026-09-01-a0x-contract-convergence.md`
  - SHA-256:
    `5396b95a5cba1f1baa5fd2f3bfda2fc61ff3ad1bbf4fd4d119dabc2a669e41fc`

The specification is authoritative. The plan argues from it. Recorded rulings
below resolve live dependencies discovered during implementation.

## Completed work

### Task 1 — real-dossier compatibility oracle

- Established the real target-free matrix: twelve tracked dossiers by two
  production Hosted schemas.
- Initial evidence was `0/24 PASS`; every failure was the stale
  `pair_binding.output_path` schema grammar.
- Added deterministic, fail-closed inventory and failure reporting.
- Closed a review finding where the nominal zero-write CLI could create
  `__pycache__`; the shipped entrypoint now prevents bytecode writes before
  project imports.
- Permanent tests require the future `24/24 PASS`; temporary `0/24` evidence is
  recorded in reports, not encoded as a passing expectation.

### Task 2 — canonical pair semantics

- `PairBinding` remains the only public pair-scope implementation.
- Added one exact derivation:
  `results/a0x/<leg>/<model_key>/<run_id>`.
- Parser rejects model-root, wrong-run, wrong-leg, wrong-model, trailing-slash,
  traversal, and unsafe-segment paths.
- All twelve tracked dossier pair mappings parse and reserialize byte-identically.
- Freeze, runner, and synthetic helpers no longer derive pair output paths
  independently.

### Task 3 — compiled schema projections

- Audited exact baseline: 33 A0X schemas and 20 PairBinding definitions.
- Registry equality is exact; 18 consumer schemas plus one canonical fragment
  produce 19 deterministic generated outputs.
- Multi-definition schemas are loaded once and all definitions are updated in
  one in-memory document.
- Generated writes are directory-descriptor anchored, reject path escape,
  symlink/nonregular targets and ancestor replacement, and use fsynced atomic
  replacement.
- Custom and pinned validators exercise literal semantic and per-schema
  mutation corpora, including nested terminal results.
- Results:
  - compiler: `19/19 PASS`;
  - compatibility oracle: `24/24 PASS`;
  - cross-validation: 155 tracked pairs agree, 19 mutations rejected.

### Task 4 — Hosted semantic builders and fixtures

- Added pure typed Gate B authorization and Hosted verification-receipt
  builders.
- Hosted verifier semantic-parses PairBinding immediately after schema
  validation and before runner-adjacent work.
- Receipt pair data comes from the validated object, never unchecked input.
- Builders reject divergent source identities, absolute/traversal/wrong-kind
  hosted paths, and source-head path mismatch.
- Runtime-bundle tests use the production receipt builder and prove that a
  schema-valid but semantically invalid dense binding reaches zero callbacks.
- Positive fixtures are canonical builder snapshots and cross-bind exact bytes:
  - authorization SHA-256:
    `8a14fb8bca982778c8759bd5c534cb14c159b0e845fb26dfb250e4d9eafa9334`;
  - verification receipt SHA-256:
    `48189bbbbbb3af80cdf13275d46086a934c0e5256416baf48afbf8654b5f8208`.
- Focused Tasks 1–4 and preflight: 103 PASS, 1 historical skip.
- Independent Task 4 re-review: APPROVE; no P0–P3 finding remained.

## Live rulings

1. Pair scope is the concept; `PairBinding` is the sole public implementation.
   A second `PairScope` type would recreate parallel truth.
2. All 20 discovered A0X pair definitions converge now through one generated
   projection, with explicit consumer overlays.
3. Known RED states were not committed. Tasks 1–4 formed the first useful code
   checkpoint because generated schemas correctly rejected the two legacy
   Hosted fixtures until Task 4 replaced them from production builders.
4. Task 3 safe writes use raw directory descriptors; pre-write path checks
   alone were insufficient because of ancestor replacement races.
5. The current checkpoint may be committed despite stale frozen bindings only
   as a non-qualified restart checkpoint. Task 7 owns binding and Task 8 owns
   target-free regeneration.

## Known remaining gate

The complete repository gate is not yet green because frozen implementation
inventories still describe the pre-convergence source. Latest full result:

- 1203 tests;
- 3 failures;
- 1 error;
- 12 skips;
- all four non-green outcomes are stale frozen-package/binding consequences;
- no Task 1–4 functional or semantic failure remains.

Representative refusal: current `src/latent_triz/a0x_contract.py` size/hash no
longer matches the old A0/R1 implementation inventories. This is expected and
must not be bypassed, relabelled, or repaired by manual artifact edits.

## Exact next work

Resume at **Task 5** in the canonical plan:

1. create a fresh isolated clone from the durable local branch, without
   hardlinks and without switching the dirty primary checkout;
2. verify exact checkpoint HEAD/tree and clean state;
3. recreate the SDD ledger from this file and the canonical plan;
4. implement the one lifecycle reducer with TDD and independent review;
5. complete Task 6 architecture/documentation fitness functions;
6. complete Task 7 inventory binding and record the exact clean implementation
   anchor;
7. only then perform Task 8 target-free regeneration, deterministic double
   check, hash ledger, and independent reviews.

Stop before network, GitHub mutation, CCP heavy, Docker, Hosted evidence
capture, Gate B/C material work, model or tokenizer construction/load, target
access, push, PR, merge, or publication without a new exact authorization.

## Recovery procedure after reboot

Do not switch branches in the dirty primary checkout. From a new Codex task:

1. read this checkpoint, the canonical specification, and the canonical plan;
2. verify the durable ref resolves to the checkpoint commit recorded by the
   final checkpoint report;
3. create a new isolated local clone under `/private/tmp`, explicitly without
   hardlinks, from the durable repository and select the durable branch;
4. verify `HEAD`, tree, branch, and clean state before edits;
5. resume at Task 5; do not repeat Tasks 1–4.

The old `/private/tmp/latent-triz-pr111-fresh.NkvGN3` clone is expendable after
the durable ref and this checkpoint commit are verified. Do not delete it as
part of restart preparation.

## Resume prompt

> Resume A0X contract convergence from
> `artifacts/checkpoints/A0X_CONTRACT_CONVERGENCE_RESTART_2026-09-01.md` and
> durable local branch `agent/a0x-contract-convergence`. Verify the exact branch
> HEAD/tree and dirty primary checkout live, create a no-hardlink isolated clone,
> preserve all existing work, recreate the SDD ledger, and continue at Task 5
> of `docs/superpowers/plans/2026-09-01-a0x-contract-convergence.md`. Do not
> repeat Tasks 1–4. Stop before any remote or material boundary not explicitly
> authorized.

