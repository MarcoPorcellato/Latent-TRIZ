---
type: restart-handoff
title: A0X six-model replication preparatory checkpoint
status: sealed-gate-pending
date: 2026-08-25
---

# A0X restart handoff

This is a reboot checkpoint, not a validation receipt or material-run
authorization.

## Safe resume point

- Repository: `/Users/marco1/Documents/CODICE con VS CODE/Emergent-AI-TRIZ`
- Worktree: none; the user explicitly requested work in the existing checkout
  to avoid additional disk use.
- Branch: `agent/a0x-six-model-design`
- Last independently qualified A0X HEAD:
  `34bbb38728c841c86128a2967ae18df9aea177cc`.
- Reboot checkpoint HEAD: the local commit containing this handoff; verify its
  exact SHA live after restart because a commit cannot safely self-hash.
- Locally recorded `origin/main`: `188eb65b5e249923baddadeba52659f07fcd1609`;
  this was not refreshed from the network in the current checkpoint.
- Branch distance before the reboot checkpoint commit: 28 commits ahead of the
  locally recorded `origin/main`.
- Pull request and remote branch: not checked and not changed.

## Completed and terminally verified

- A0X Tasks 1-8 and the acyclic authorization/package-ledger corrections are
  committed through `2aab598c7b07e3046b4d22d06903071a966c7eb1`.
- Task 9 immutable package construction and fresh-copy verification are
  committed at `34bbb38728c841c86128a2967ae18df9aea177cc`.
- Fresh controller verification for Task 9:
  - `tests.test_a0x_report tests.test_a0x_verify`: 21/21 PASS;
  - Task 5-8 compatibility: 57/57 PASS with 3 expected NumPy skips;
  - `py_compile` and `git diff --check`: exit 0.
- Independent Sol review approved Task 9 after four fix rounds. It confirmed
  exact repository-root postflight verification, distinct A0/R1 protected
  trees, activation-to-asset binding, atomic no-replace publication, strict
  JSON/report checks, cap/alias defences, and fresh-copy mutation refusal.

## Task 10 closure and current Task 11 checkpoint

Task 10 is complete in the current uncommitted worktree. Its final controller
evidence is:

- 87/87 focused tests PASS;
- 184/184 aggregate tests PASS with three expected skips;
- schema cross-validation 155/19 PASS;
- `py_compile` and `git diff --check` PASS;
- independent Sol re-review `APPROVED` after closing the immediate post-claim
  CCP hash and exact Matrix runtime/receipt bindings.

Task 11 has now generated, without material access:

- `experiments/a0x-six-model/a0/{protocol,implementation}.json`;
- `experiments/a0x-six-model/r1/{protocol,implementation}.json`;
- two freeze manifests under `experiments/a0x-six-model/freeze/`;
- twelve separate `approval_requested` dossiers under
  `experiments/a0x-six-model/approval-dossiers/`;
- `docs/A0X_SIX_MODEL_CAMPAIGN.md`;
- the frozen-package TDD suite and `make a0x-no-model-verify`.

Task 11 is locally complete at `sealed_gate_pending`. Final regeneration and
the 9/9 focused gate passed; the aggregate is 193/193 with three documented
optional-NumPy skips; schema is 155/19; docs/compile/diff pass; Sol re-review
is `APPROVED`; and the exact two freeze plus twelve dossier hashes are recorded
in `docs/A0X_SIX_MODEL_CAMPAIGN.md`. No Task-12 execution is authorized. The
consolidation commit must be resolved live because this handoff cannot safely
self-record it.

## Preserved unrelated work

The following pre-existing untracked directories are outside A0X Task 10 and
must remain untouched:

- `experiments/exp002-auto-partial-recovery/`
- `results/exp002-auto-partial-recovery/`
- `tmp/`

## Active or stopped work

- Worker `/root/a0x_task10_impl`: paused, then explicitly interrupted.
- Controller test session for Task 9: terminally completed.
- Known A0X model, target, CCP, Docker, OrbStack, network, or remote process
  started by this task: none.
- Resource admission: not checked and not needed for Tasks 10-11 synthetic
  preparation.

## Exact resume sequence

1. Verify repository path, branch, exact HEAD, locally recorded base, and dirty
   paths before trusting this handoff.
2. Re-read the A0X design, implementation plan, SDD ledger, Task 10 brief, and
   Task 10 report.
3. Confirm no unexpected material runner or shared-state process is active.
4. Verify the exact freeze/dossier hashes against
   `docs/A0X_SIX_MODEL_CAMPAIGN.md`; do not regenerate unless a bound source or
   test intentionally changes.
5. Preserve `sealed_gate_pending`. Do not stage, commit, invoke CCP, or start
   Task 12 without the next explicit authorization.

## Boundaries that survive the restart

- Tasks 1-11 are preparatory only. Do not construct a real tokenizer or model,
  open a historical/sealed target, invoke CCP or a material Make target, use
  network/GitHub, or publish remotely.
- Do not execute Task 12 without a new explicit authorization bound to the
  exact dossier for one leg/model pair.
- Do not retry, tune, pool, rank, substitute models, change frozen statistics,
  or promote a general TRIZ claim.
- Preserve all A0-R2/C3, EXP-001, EXP-002/R5, and unrelated user artifacts
  byte-for-byte.
- Do not create another worktree unless the user changes the disk-space
  preference.

## Sources of truth

- Canonical design:
  `docs/superpowers/specs/2026-08-24-a0x-six-model-replication-design.md`
- Implementation plan:
  `docs/superpowers/plans/2026-08-24-a0x-six-model-replication-implementation.md`
- Local progress ledger:
  `.superpowers/sdd/2026-08-24-a0x-six-model-replication-implementation/progress.md`
- Task 10 requirements and interruption record:
  `.superpowers/sdd/2026-08-24-a0x-six-model-replication-implementation/task-10-brief.md`
  and `task-10-report.md`
