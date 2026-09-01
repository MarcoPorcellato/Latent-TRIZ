---
type: execution-handoff
title: A0X Hosted Gate A — Terra execution handoff
status: local-preparation
date: 2026-08-31
---

# A0X Hosted Gate A — Terra execution handoff

## Objective

Complete Tasks 6–11 of
`docs/superpowers/plans/2026-08-31-a0x-hosted-gate-a-implementation.md`
without crossing a material or remote boundary. Produce one clean, frozen,
target-free exact-head candidate and publication dossier, then stop for Sol and
operator review before Task 12.

## Verified starting state

- Isolated clone: `/private/tmp/latent-triz-pr109-postmerge-bc9b7ad-2`
- Branch: `agent/a0x-hosted-gate-a-design`
- Last implementation commit before this handoff:
  `f79d7c717a46630a2617bad64f9727c1bf4df7d1`
- Tree at that implementation commit:
  `e55e3a80130a1399c99027f802f1f77302c21aa6`
- Task 5 focused verification: 40/40 PASS
- Schema cross-validation: 155 tracked pairs agree; 19 mutations rejected by
  both validators
- Independent Task 5 security review: APPROVE, no findings
- Complete repository status: expected `NO-GO`, not a regression claim. Four
  frozen-package assertions detect stale pre-migration implementation bytes.

The final handoff-preparation commit is a docs/plan descendant of the
implementation commit above. Verify live branch, HEAD, tree, and dirty state
before acting. Stop if the code diff between the implementation commit and the
live tip contains anything outside the documented Sol preparation.

## Required reading

1. repository and global `AGENTS.md` instructions;
2. `docs/superpowers/specs/2026-08-31-a0x-hosted-gate-a-design.md`;
3. `docs/superpowers/plans/2026-08-31-a0x-hosted-gate-a-implementation.md`;
4. `docs/A0X_HOSTED_GATE_A_SOL_ARCHITECTURE_REVIEW.md`;
5. this handoff;
6. `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md` sections 35–36.

Use `orchestrate-long-running-work`, `superpowers:test-driven-development`,
`superpowers:subagent-driven-development`, and
`superpowers:verification-before-completion`. All shell commands begin with
`rtk`.

## Sol decisions already closed

Do not reopen these during Terra execution:

- current hosted evidence uses v2; current execution authorization uses v3;
- legacy CCP/v2 packages use explicit legacy loaders only;
- `implementation_source_head` and live `source_head` are distinct;
- Hosted Gate A and CCP Gate C identities are never compared;
- Gate B preserves a successfully created verification receipt if a later
  preparation stage fails, while leaving no later partial artifacts;
- one shared five-file validator defines every Gate C path/type/hash rule;
- Task 9 must end with an explicit stale-freeze `NO-GO`;
- Task 10 alone regenerates frozen bytes;
- Task 12 remains Sol/operator-owned and separately authorized.

Any required deviation is a hard stop. Record exact evidence and request Sol;
do not improvise.

## Execution order and ownership

### Task 6 — contract/profile separation

Terra owns implementation and integration. Start with RED tests. Preserve the
existing execution-authorization v2 schema, commitment prefix, fixture bytes,
and historical verification results. Add v3 and explicit profile dispatch.

Delegate to Luna after GREEN:

- enumerate every v2/v3 schema and dispatch site;
- compare historical fixture bytes before and after;
- audit that the CCP object and 3,600/3,300/300-second envelope are unchanged;
- report only concrete mismatches.

Checkpoint: focused contract/schema tests and schema cross-validation PASS.

### Task 7 — Gate B lifecycle

Terra owns files listed by Task 7. Verification receipt must precede readiness.
No current path accepts a CCP Gate A receipt or fallback.

Delegate to Luna after GREEN:

- verify lifecycle ordering from source and tests;
- audit imports/calls for model, tokenizer, target, CCP, Docker, and network
  access;
- check every post-verification failure leaves only the owned verification
  receipt and no later partial output.

Checkpoint: focused runtime-bundle/preflight tests PASS. Frozen package remains
stale and must not be regenerated.

### Task 8 — five-file Gate C boundary

Terra performs the mechanical integration under the Sol-closed shared-validator
contract. Every caller uses the same validator before claim, before guard, at
child inlet, and during package verification. No caller may invoke `gh` or
reinterpret provenance.

Delegate to Luna after GREEN:

- enumerate all validator call sites;
- audit missing/mutated/symlink/hardlink/nonregular/TOCTOU coverage for each of
  five files;
- verify separate Hosted Gate A and CCP Gate C identities in positive tests.

Checkpoint: focused Gate C tests PASS; material spies remain zero.

### Task 9 — inventory completeness

Terra exclusively owns freeze/inventory files, `Makefile`, repository-check
registration, and receipt materializer integration. Luna may only inventory
paths and distill deterministic output.

Checkpoint:

- named implementation/inventory tests PASS;
- `a0x-hosted-gate-a-verify` PASS;
- one `a0x-no-model-verify` run refuses only because tracked freeze bytes are
  stale;
- no regeneration occurs.

Any other failure is a real blocker, not the expected stale-package boundary.

### Task 10 — documentation and regeneration

Terra updates current documentation, commits the complete implementation/docs
anchor, records its exact HEAD, then performs exactly the three target-free
regeneration commands in the canonical plan. Do not use the later generated
artifact commit as `implementation_source_head`.

Delegate to Luna:

- compare implementation path sets between A0 and A0-R1;
- report exact counts and SHA-256 values for two inventories, two freezes,
  twelve dossiers, and one no-model receipt;
- verify a second regeneration produces no diff;
- audit documentation for stale values presented as current.

Checkpoint: frozen, synthetic, schema, and documentation checks PASS with zero
material access.

### Task 11 — local candidate qualification

Terra runs the complete deterministic ladder, integrates only verified fixes,
and creates the public-safe exact-head dossier. Luna performs independent
material/freeze review. A final Sol architecture/security review is still
required before Task 12; do not represent Luna review as that approval.

Checkpoint: clean exact HEAD/tree, every required local target green, two
reviews recorded, publication dossier exact, no remote mutation. Stop.

## Hard boundaries

Forbidden throughout Tasks 6–11:

- real `gh attestation verify`;
- network or GitHub API;
- push, PR, merge, ruleset, status, evidence branch, or publication mutation;
- Gate B runtime materialization;
- Gate C or any CCP heavy command;
- Docker/OrbStack;
- model load, tokenizer construction, target read, generation, inference,
  scoring, or scientific output;
- regeneration before Task 10;
- retry or adaptation after any real signed-output access.

Synthetic injected subprocess tests remain allowed. Read-only local Git and
deterministic target-free tests remain allowed.

## Resume and compaction discipline

After every task, append a short checkpoint to the existing SDD progress file
with exact commit/tree, RED and GREEN evidence, delegated review result,
expected global status, and next task. Keep at most one task in progress. Do
not copy the full plan into the checkpoint.

Before interruption, commit authorized local work, record dirty state and all
active processes, and update `docs/PERSISTENT_GOAL.txt`. A temporary clone path
alone is not durable evidence; preserve the branch and exact commit in the
repository object store. Remote publication remains separately gated.

## Completion condition for Terra

Terra stops only when Task 11 is proven or a precise deviation is recorded.
The final response must provide:

- exact HEAD and tree;
- clean/dirty state;
- test commands and counts;
- regenerated hashes and counts;
- review outcomes;
- publication dossier path and SHA-256;
- explicit statement that Task 12 and every material boundary remain pending.
