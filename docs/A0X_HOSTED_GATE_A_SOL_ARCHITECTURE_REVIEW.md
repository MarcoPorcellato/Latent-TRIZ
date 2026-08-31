---
type: architecture-review
title: A0X Hosted Gate A — Sol architecture and security review
status: approved-for-local-terra-execution
date: 2026-08-31
---

# A0X Hosted Gate A — Sol architecture and security review

## Decision

Tasks 6–11 may proceed locally under the canonical specification, plan, and
Terra handoff. The review authorizes no external or material action. Task 12,
Gate B, Gate C, model or tokenizer access, target access, CCP heavy work, and
scientific execution remain outside this decision.

## Reviewed trust boundaries

The review covered:

- dispatch between current Hosted Gate A profiles and historical CCP packages;
- separation of hosted provenance from the existing CCP Gate C identity;
- the four hosted inputs and exclusively created fifth verification receipt;
- path, object type, link count, raw hash, source, and pair binding for all five
  files at every Gate C inlet;
- regeneration order for implementation inventories, freezes, dossiers, and
  the no-model receipt;
- commit identities before regeneration, after packaging, and after a future
  squash merge;
- failure ownership, partial-output cleanup, overwrite refusal, TOCTOU
  resistance, and terminal no-rerun behavior;
- absence of model, tokenizer, target, Docker, CCP heavy, and real network
  access from Tasks 6–11.

## Frozen rulings

1. Current documents use `a0x-gate-a-evidence-binding-v2` and
   `a0x-execution-authorization-json-v3`. Historical profiles are accepted only
   through explicit legacy loaders.
2. Hosted Gate A and CCP Gate C are independent producer domains. They share
   the exact `source_head`; their producer identities are never equated.
3. Gate B owns an acyclic creation sequence. A verifier refusal creates no
   output. A later preparation failure preserves only the successfully created
   verification receipt and removes no pre-existing file.
4. A shared pure validator owns all five-file Gate C semantics. Individual
   consumers may not implement reduced checks.
5. `implementation_source_head` records the reviewed pre-regeneration
   implementation anchor. `source_head` records the later exact source accepted
   by Hosted Gate A and Gate B/C. Tree equality substitutes for neither.
6. Task 9 must leave the old frozen package in an explicit expected `NO-GO`.
   Task 10 alone performs regeneration.
7. Any real hosted failure, cancellation, skip, or rerun is terminal for that
   attempt. Publication and material continuation require new exact
   authorization.

## Residual risks and required evidence

The current implementation checkpoint has not yet integrated Tasks 6–10, so
the complete frozen package correctly remains stale. Terra must use TDD and
preserve that failure until Task 10. Luna reviews are supporting evidence only;
they do not replace integration verification or the final Sol review.

Before Task 12, Sol must re-review the clean Task 11 exact HEAD and tree. That
review must confirm current schemas and dispatch, every shared-validator call
site, deterministic regeneration, public-safe dossier contents, test evidence,
and zero unauthorized material or remote access. A changed architecture or
unplanned trust input is a stop condition, not an implementation detail.

## Execution handoff

Terra follows `docs/A0X_HOSTED_GATE_A_TERRA_HANDOFF.md` and Tasks 6–11 in
`docs/superpowers/plans/2026-08-31-a0x-hosted-gate-a-implementation.md`.
Terra delegates bounded inventories, fixture comparisons, mutation audits,
deterministic test execution, and hash/count distillation to Luna. Terra retains
implementation and integration ownership. The Task 11 candidate then returns
to Sol and the operator; it must not proceed directly to Task 12.
