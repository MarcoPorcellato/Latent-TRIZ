---
type: restart-handoff
title: A0X six-model replication preparatory checkpoint
status: sealed-gate-pending
date: 2026-08-25
---

# A0X restart handoff

This is a reboot checkpoint, not a validation receipt or material-run
authorization.

## Current continuation checkpoint (2026-08-25)

This section supersedes older status statements below when they conflict. The
older chronology remains in this file as historical context.

### CCP compatibility checkpoint (2026-08-26)

- The fetched official CCP `origin/main` is
  `2b4b55ce1a4be0a2b610656ae4a56a7641b29f26`. Its current operator contract
  keeps `plan`, `doctor`, `dry-run`, and `verify` outside the host-wide heavy
  slot; `run`, `benchmark`, and `guard exec` remain coordinated heavy commands.
  It also retains the prepared-entry lock throughout a standard `run` and
  revalidates the exact staging generation immediately before Docker creation.
- The reviewed compatibility implementation is local and not yet official:
  branch `agent/matrix-v2-legacy-plan-profile`, exact HEAD
  `c91915adcb8706898574c0c74d033b9ff991eefb`, tree
  `687fcaaa3643d35a66ba748409e5621d13e25dd7`.
- Its isolated candidate is
  `/private/tmp/ccp-final-review-candidate-c91915a/release/commit-ci-preflight`,
  SHA-256
  `72a3458987e18313ceacfc97d8e7902d2d5338eb8eb609320fd37ca58aedd4be`.
  The static suite completed with 394 passes and four documented ignores; an
  independent final review returned GO with no P0-P3 findings.
- A fresh non-executing `matrix-v2-legacy-v1` plan on this A0X checkout
  reproduced the trusted-base digests exactly: outer `13f4cb39...76178`,
  Python 3.11 `eff5b7d5...8562`, and Python 3.12 `7afb3e6d...994c8`.
  Candidate `doctor` identified OrbStack 29.4.0 with memory and swap controls,
  and candidate `dry-run` rendered the expected shell-free CCP self-check
  plan. No CCP `run`, installation, publication, model, tokenizer, or target
  access occurred.
- The next material gate is one explicitly authorized exact-head CCP
  qualification of the compatibility candidate. A successful qualification
  would still not authorize installation, publication, a Latent-TRIZ
  qualification, or any of the twelve scientific runs.

The `matrix-v2-legacy-v1` documentation and implementation are present only on
the candidate branch, not on the fetched public `origin/main`. The candidate is
therefore reviewed compatibility work, not an installed or released CCP
contract. Its `verify` command deliberately has no profile flag.

### No-model A0X migration closure (2026-08-26)

- Policy, material contract, schemas, runner, verifier, independent plan
  fixture, and synthetic tests are bound to the candidate identity and exact
  compatibility profile.
- The canonical generator regenerated both frozen legs and all twelve
  `approval_requested` dossiers. Its receipt reports zero model loads, zero
  tokenizer constructions, zero sealed-target content reads, zero CCP
  invocations, and zero remote mutations.
- A0X aggregate verification: 197 tests passed with three expected skips.
- Frozen package verification: 9/9 passed.
- Schema cross-validation: 155 tracked pairs agreed and 19 mutations were
  rejected by both validators.
- Documentation audit passed. The first direct host-Python repository check was
  inconclusive because that Python 3.14 environment lacks `jsonschema`; the
  deterministic rerun with the pinned project Python 3.11 environment passed
  all 1,024 tests with one expected skip and ended `repository-check: PASS`.

Current no-model artifact hashes:

| Artifact | SHA-256 |
| --- | --- |
| Material execution contract | `5b9754c5689b6f48476768c61a58afcac6b7c6e88ee289a5b16678ec26021ca4` |
| A0 freeze | `711d7df84baf2cceaea6f0567733feec24292e4ca872fc66da79ece7e7577569` |
| A0-R1 freeze | `d43a91f02089ce6a103d6afe6126076ea53e480bbe68e49abcf61f3dee0e240b` |

The installed stable executable remains SHA-256
`b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c`;
it does not match the newly frozen material contract. Consequently no A0X
material command is runnable yet, even if host admission is free.

### Exact local and remote anchors

- Repository: `/Users/marco1/Documents/CODICE con VS CODE/Emergent-AI-TRIZ`.
- Branch: `agent/a0x-six-model-design`.
- Exact local HEAD: `34b52c42ef08cfe7043dde53f300154cc01d22f9`.
- Exact local tree: `3f09362de6094db68560628492d14d0029057e1b`.
- Locally recorded and GitHub-verified PR base: public `main`
  `188eb65b5e249923baddadeba52659f07fcd1609`.
- Branch distance: 32 commits ahead and 0 behind that base.
- The checkout preserves these unrelated, pre-existing untracked paths:
  `experiments/exp002-auto-partial-recovery/`,
  `results/exp002-auto-partial-recovery/`, and `tmp/`. They must remain
  untouched.

### Published review state

- Public source branch: `agent/a0x-six-model-design` at the exact HEAD above.
- Public evidence branch:
  `ccp-evidence/34b52c42ef08cfe7043dde53f300154cc01d22f9`,
  evidence commit `b6a7d8cfa1a575f0a5ed379337b2d93093d9dfac`.
- Pull request: [#105](https://github.com/MarcoPorcellato/Latent-TRIZ/pull/105),
  ready, open, and `BLOCKED`, with exact head and base unchanged when checked
  live on 2026-08-25.
- Terminal hosted results: trusted-path classification `PASS`, scientific
  artifact audit `PASS`, documentation audit expected `SKIPPED`, exact-head
  CCP receipt `FAIL`, aggregate publication `FAIL`, and
  `merge-policy/gate` `FAIL`.
- No merge, retry, force-push, receipt rewrite, or ruleset change is authorized
  by this checkpoint.

### Exact local qualification evidence

The one authorized Matrix V2 qualification for this HEAD ran in the isolated
clone `/private/tmp/latent-triz-a0x-qualification-34b52c42` and completed all
four checks successfully with the then-installed producer:

- producer source commit:
  `3fccc197e5055a2759ee7afe51b91133938ec904`;
- producer tree: `9e478c1489a9926772e8ab8bea21bd57470494b6`;
- executable: `/Users/marco1/.cargo/bin/commit-ci-preflight`;
- executable SHA-256:
  `b8d26013800c99ba806506a0539a9ddc781bfab52f95c8f1dbdff1b65c2fcd4c`;
- generation: `1`, with no retry;
- receipt ID:
  `sha256:fb04d84e2cfe93482021f40b0b7abff08faa44a2c362757019b70f0897835361`;
- receipt file SHA-256:
  `8a838aa82cb8e45451a25fa4b7db8c64df141e18f257336320aa90a6f7770761`;
- observed outer digest:
  `25b35b942a6ff9b6237ebed7cefbdbc96b968bbe8954a38b606942f36b8df4b2`;
- Python 3.11 digest:
  `b3d8beef1542566d9d925bfee77d2244995dc74adcd879128ef65e82ed1d354b`;
- Python 3.12 digest:
  `d446c4ca0602c09eee61c796ad2972f58ab0eebe84a39f928fd90aac5bfb535c`.

This receipt is valid local evidence for the exact recorded producer and plan,
but it does not satisfy the current trusted-base GitHub policy.

### Hosted failure diagnosis

The trusted `pull_request_target` workflow still builds CCP source commit
`044697dee9a0d678d30a4847d62ddf9b4970505b` and expects the trusted-base
digests:

- outer: `13f4cb39b7e1a8ed31cae64502cc8e4d80d040230d3fb410a6afc3bad3b76178`;
- Python 3.11:
  `eff5b7d55bb0220890dbfb050bb68a1e0fbba8f9a30a69e2f66085354fcc8562`;
- Python 3.12:
  `7afb3e6dd435d9d5a317e4d9d85e80527431044312bbe299e9a70b6ba9e994c8`.

The hosted verifier accepted receipt integrity and rejected only the outer and
runtime policy/config digest bindings. This is a producer-plan compatibility
failure, not a scientific failure and not permission to reinterpret or alter
the receipt.

### Historical producer investigation

An offline isolated build from the exact trusted workflow producer was
completed without a CCP run:

- source commit: `044697dee9a0d678d30a4847d62ddf9b4970505b`;
- source tree: `5220164edf17831ce0c42dae1c14300ed1045015`;
- candidate path:
  `/private/tmp/ccp-candidate-044697dee/target/release/commit-ci-preflight`;
- candidate SHA-256:
  `71d64cdbb1bb509bb459aebd6c53e06d819150de42be4fe3715c35bd73426af7`;
- version: `commit-ci-preflight 0.1.0`;
- offline release build `PASS`;
- static Matrix, plan, verification, and CLI tests: 20/20 `PASS`;
- the single authorized read-only plan reproduced all three trusted-base
  digests exactly.

That candidate must not run against the current shared coordinator. Its legacy
admission implementation rejects the modern `quarantine` and `leases`
directories and lacks the current lease/heartbeat protocol. The current root
was inspected read-only: `tickets/` and `leases/` were empty, while
`quarantine/` contained preserved historical recovery evidence. Manual
deletion, relocation, alternate admission roots, nested guards, fabricated
receipts, or coordinator bypasses are not acceptable solutions. A fresh
admission status could not be reproved inside the sandbox because locking
`queue.lock` requires the narrow runtime permission; this remains unproven, not
a denial or a pass.

### Resume decision

Do not run either producer yet. The preferred next design is a reviewed CCP
compatibility mechanism that keeps the modern admission coordinator while
reproducing the historical plan algorithm deterministically. It must derive
the historical digests from canonical inputs rather than hard-code expected
hashes, preserve receipt integrity and provenance, pass TDD and independent
review, and be separately qualified before any new Latent-TRIZ run. A second
exact-head run, evidence publication, PR update, or merge each requires new
explicit authorization.

### Static-analysis evaluation checkpoint

The read-only tooling study requested at this pause is documented in
`docs/reference/static-analysis-tooling.md` and linked from the maintained
documentation portals. It recommends a staged, no-autofix first wave built
around Ruff, mypy, Bandit, actionlint, zizmor, and ShellCheck, while keeping
dependency freshness and optional diagnostics separate. No tool was installed,
configured, downloaded, or added to CCP. The documentation audit and
`git diff --check` passed after the local documentation edits.

These checkpoint/documentation edits remain intentionally uncommitted because
committing would change PR #105's exact head and invalidate the current
head-bound publication state. Review and commit them only in a separately
authorized documentation or recovery change.

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

Task 11 is locally complete at `sealed_gate_pending`. The Matrix V2 correction
is committed at `0114cdc0f14344a9bceb1f442128c55195e69a71`. Its one authorized
exact-head CCP qualification terminated `FAIL`, without timeout: both schema
checks passed, while both repository checks exposed that
`test_exp002_publication_verify.py` depended on seven ignored external dense
assets unavailable in the isolated clone. Receipt ID
`sha256:6e462b9c9bcb0389d886b2b2f56d386e8b4cbdc7ebf3865e8c6478ed47fc1352`,
file SHA-256
`763c845ef4065945a4057149997f44c652dd2cfccdf590795bdaa5b9da430835`.
The production verifier remains fail-closed. The local test correction uses
seven deterministic synthetic assets and preserves missing/mutated negative
coverage. No retry, Task-12 execution, model, tokenizer, or target access is
authorized. Consolidate and verify the correction, then request a new
exact-head CCP authorization.

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
