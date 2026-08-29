# A0X PR #105 Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate public `main@4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08` into A0X PR #105 without changing frozen scientific bytes, then stop at one exact clean commit ready for a separately authorized CCP qualification.

**Architecture:** Perform a normal merge in an isolated no-hardlink clone, combine the two independently TDD-qualified EXP-002 verification surfaces, and preserve the A0X protected set byte-for-byte. Verification is layered from conflict-focused tests through the complete repository suite and an exact Git object comparison against `4aee4698f5c59101b1f3292519f10ae802629bf7`.

**Tech Stack:** Git, Python 3.11/3.12-compatible `unittest`, JSON Schema, repository documentation audit, CCP Matrix V2 policy and plan fixtures.

**Spec:** `docs/superpowers/specs/2026-08-29-a0x-pr105-finalization-design.md`

## Global Constraints

- Preserve the dirty primary checkout and all unrelated user work.
- Work only in a clean, isolated, no-hardlink clone under `/private/tmp`.
- All shell commands begin with `rtk`.
- Do not invoke CCP `run`, `benchmark`, or `guard exec`; do not use Docker.
- Do not load models or tokenizers and do not read sealed targets.
- Do not push, publish a receipt, mutate PR #105, or merge remotely.
- Keep `.commit-ci-policy-v2.toml` byte-identical to public `main` object `8a40d48220723373156f9d99fc4e433ed1beaa70`.
- Keep the complete A0X protected path set byte-identical to `4aee4698f5c59101b1f3292519f10ae802629bf7`.
- Stop after reporting the final HEAD, tree, verification evidence, and exact CCP authorization envelope.

---

### Task 1: Capture the immutable integration baseline

**Files:**
- Read: `experiments/a0x-six-model/**`
- Read: `results/a0x/preexecution/a0x-no-model-verification-receipt.json`
- Read: `src/latent_triz/a0x_*.py`
- Read: `scripts/a0x_*.py`
- Read: `schemas/a0x-*.json`
- Read: `tests/test_a0x_*.py`
- Read: `tests/fixtures/a0x/**`

**Interfaces:**
- Consumes: Git object tree at `4aee4698f5c59101b1f3292519f10ae802629bf7`.
- Produces: an exact protected-path list and blob-ID map used by Task 4.

- [ ] **Step 1: Verify repository identities and clean state**

Run:

```bash
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git rev-parse HEAD^{tree}
rtk git rev-parse origin/main
rtk git rev-parse origin/main^{tree}
```

Expected: clean branch based on the PR head plus the approved specification commit; `origin/main` equals `4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08`.

- [ ] **Step 2: Capture the protected path list from the freeze implementation**

Run:

```bash
rtk rg -n "_IMPLEMENTATION_PATHS|_LEG_SOURCES" src/latent_triz/a0x_freeze.py
rtk git diff --name-only 6b8c8e3491b24fa4717b2f4faa8700b007c48892..4aee4698f5c59101b1f3292519f10ae802629bf7 -- 'schemas/a0x-*' 'scripts/a0x_*' 'src/latent_triz/a0x_*' 'tests/a0x_test_support.py' 'tests/test_a0x_*' 'tests/fixtures/a0x'
```

Expected: the second command prints no paths.

- [ ] **Step 3: Record immutable blob IDs for the complete protected set**

Run:

```bash
rtk git ls-tree -r 4aee4698f5c59101b1f3292519f10ae802629bf7 -- experiments/a0x-six-model results/a0x/preexecution/a0x-no-model-verification-receipt.json schemas scripts src/latent_triz tests
```

Retain only `schemas/a0x-*`, `scripts/a0x_*`, `src/latent_triz/a0x_*`,
`tests/a0x_test_support.py`, `tests/test_a0x_*`, `tests/fixtures/a0x/**`, the
complete `experiments/a0x-six-model/**` tree, and the no-model receipt when
reviewing the output. Expected: every protected path resolves to exactly one
blob; Task 4 uses an exact Git diff over the same path patterns.

### Task 2: Integrate public main and resolve the two conflicts

**Files:**
- Modify: `docs/log.md`
- Modify: `tests/test_exp002_publication_verify.py`
- Adopt from main: `scripts/exp002_publication_verify.py`
- Adopt from main: `docs/qualification/a0x-legacy-policy-migration-dossier.json`
- Adopt from main: `tests/test_ccp_a0x_policy_migration.py` (operational CCP policy-migration test; deliberately outside the reserved A0X frozen-test namespace)
- Preserve: `.commit-ci-policy-v2.toml`

**Interfaces:**
- Consumes: Task 1 baseline and
  `origin/main@4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08`.
- Produces: a conflict-free merge tree with all three EXP-002 verification claims.

- [ ] **Step 1: Merge without rewriting history**

Run:

```bash
rtk git merge --no-ff origin/main
```

Expected: merge pauses with conflicts only in `docs/log.md` and `tests/test_exp002_publication_verify.py`.

- [ ] **Step 2: Resolve the test conflict by retaining all independent claims**

The final class must retain the three existing PR #105 tests unchanged and add
the exact tracked-binding test below. The imports must include both the module
and the two existing public names:

```python
import exp002_publication_verify as publication_verify  # noqa: E402
from exp002_publication_verify import (  # noqa: E402
    PublicationVerificationError,
    verify_publication_manifest,
)

def test_published_manifest_tracked_bindings_are_source_snapshot_safe(self):
    result = publication_verify.verify_publication_manifest_bindings(
        "results/exp002/preexecution/publication-manifest.json", root=ROOT
    )
    self.assertEqual(result["status"], "bindings_only")
    self.assertEqual(result["packages"], 7)
    self.assertEqual(result["declared_external_assets"], 7)
    self.assertEqual(result["verified_external_assets"], [])
```

Do not alter these existing method bodies:
`test_complete_seven_package_manifest_passes_without_local_asset_dependency`,
`test_missing_and_mutated_external_assets_fail_closed`, and
`test_missing_or_mutated_package_binding_fails_closed`.

- [ ] **Step 3: Resolve the chronology conflict**

Keep one front matter block with `last_verified: 2026-08-29`, then place the `2026-08-29 — A0X Matrix V2 policy bootstrap` entry before the preserved `2026-08-25 — CCP current workflow and A0X diagnostic correction` entry. Remove every conflict marker.

- [ ] **Step 4: Verify the policy and adopted implementation blobs**

Run:

```bash
rtk git hash-object .commit-ci-policy-v2.toml
rtk git diff --check
rtk rg -n '^(<<<<<<<|=======|>>>>>>>)' docs/log.md tests/test_exp002_publication_verify.py
```

Expected: policy object `8a40d48220723373156f9d99fc4e433ed1beaa70`, clean diff, and no conflict markers.

- [ ] **Step 5: Run the conflict-focused tests**

Run:

```bash
rtk env PYTHONPATH=src python3 -m unittest tests.test_exp002_publication_verify tests.test_ccp_a0x_policy_migration -v
```

Expected: all tests PASS. The two behavioral surfaces were independently developed test-first; integration adds no new production behavior.

- [ ] **Step 6: Commit the resolved merge**

Run:

```bash
rtk git add docs/log.md tests/test_exp002_publication_verify.py scripts/exp002_publication_verify.py docs/qualification/a0x-legacy-policy-migration-dossier.json tests/test_ccp_a0x_policy_migration.py .commit-ci-policy-v2.toml
rtk git commit -m "merge: integrate A0X trusted-base migration"
```

Expected: one local merge commit; no push.

### Task 3: Reconcile canonical operational documentation

**Files:**
- Modify: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`
- Modify: `docs/A0X_RESTART_HANDOFF.md`
- Modify: `docs/CURRENT_STATUS.md`
- Modify: `docs/PERSISTENT_GOAL.txt`

**Interfaces:**
- Consumes: the merged source state from Task 2 and historical receipt
  `08b1a8f1c08d2ab9784c95acd3b452c218b76108744a129cd6b8df2aef52c447`.
- Produces: prequalification-accurate status wording without claiming a receipt for the new head.

- [ ] **Step 1: Add the missing causal records**

Append three entries to the engineering log:

1. source-snapshot tests must distinguish tracked bindings from external asset verification;
2. hosted verification uses trusted-base policy, so the candidate policy cannot self-authorize;
3. a base integration changes the source head and consumes the old receipt only as historical evidence, while scientific artifacts remain unchanged when no protected path changes.

Each entry must contain symptom, root cause, consequence, correction, regression evidence, and status.

- [ ] **Step 2: Replace stale current-gate wording**

State consistently in all four files:

- `4aee4698f5c59101b1f3292519f10ae802629bf7` passed local exact-head qualification;
- its receipt is historical after the base integration;
- PR #106 migrated public `main` to `4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08`;
- scientific artifacts remain byte-identical;
- the sole remaining preparatory gate is one separately authorized CCP qualification of the final integrated exact head.

Do not claim that the final integrated head has passed CCP.

- [ ] **Step 3: Run documentation verification**

Run:

```bash
rtk env PYTHONPATH=src python3 -m latent_triz.cli docs-audit --profile docs/okf-profile.toml --root . --as-of-date 2026-08-29
rtk git diff --check
```

Expected: PASS and no whitespace errors.

- [ ] **Step 4: Commit the documentation reconciliation**

Run:

```bash
rtk git add docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md docs/A0X_RESTART_HANDOFF.md docs/CURRENT_STATUS.md docs/PERSISTENT_GOAL.txt
rtk git commit -m "docs(a0x): record finalization boundary"
```

Expected: one local documentation commit; no push.

### Task 4: Prove scientific immutability and repository correctness

**Files:**
- Test: `tests/test_exp002_publication_verify.py`
- Test: `tests/test_a0x_matrix_plan_binding.py`
- Test: all A0X tests and repository checks
- Compare: Task 1 protected path set

**Interfaces:**
- Consumes: final candidate from Task 3 and baseline from Task 1.
- Produces: complete no-material verification evidence and a final clean commit/tree.

- [ ] **Step 1: Recreate a fresh no-hardlink clone of the final candidate**

Use `rtk git clone --no-local --no-hardlinks` from the isolated source repository into a new explicit `/private/tmp` path, then detach at the final candidate commit.

Expected: clean checkout and exact commit match.

- [ ] **Step 2: Run focused Matrix and frozen-package tests**

Run:

```bash
rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_matrix_plan_binding tests.test_a0x_frozen_package -v
```

Expected: PASS.

- [ ] **Step 3: Run the complete A0X aggregate**

Run the exact module list used by `make a0x-synthetic-verify`, but invoke Python directly so verification does not depend on `make` being installed.

Expected: all A0X tests PASS with only already documented optional-NumPy skips.

- [ ] **Step 4: Run schema cross-validation and full repository check**

Run:

```bash
rtk env PYTHONPATH=src python3 scripts/schema_cross_validate.py
rtk env PYTHONPATH=src python3 scripts/repository_check.py
```

Expected: schema agreement/mutation audit PASS and full repository PASS.

- [ ] **Step 5: Run documentation and Git audits**

Run:

```bash
rtk env PYTHONPATH=src python3 -m latent_triz.cli docs-audit --profile docs/okf-profile.toml --root . --as-of-date 2026-08-29
rtk git diff --check
rtk git status --short --branch
```

Expected: documentation PASS, no diff errors, clean checkout.

- [ ] **Step 6: Compare the complete protected blob map**

Run:

```bash
rtk git diff --exit-code 4aee4698f5c59101b1f3292519f10ae802629bf7 HEAD -- experiments/a0x-six-model results/a0x/preexecution/a0x-no-model-verification-receipt.json 'schemas/a0x-*' 'scripts/a0x_*' 'src/latent_triz/a0x_*' tests/a0x_test_support.py 'tests/test_a0x_*' tests/fixtures/a0x
```

Expected: zero protected-path differences. Any difference is a hard stop; do not regenerate artifacts.

- [ ] **Step 7: Verify policy, plan fixture, and producer bindings**

Run:

```bash
rtk shasum -a 256 /Users/marco1/.cargo/bin/commit-ci-preflight.candidate-27adf8d0820b3cd96f9c5e149de9b580ae41f639-c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4
rtk git hash-object .commit-ci-policy-v2.toml
rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_matrix_plan_binding -v
```

Expected: producer SHA-256 `c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`, policy object `8a40d48220723373156f9d99fc4e433ed1beaa70`, and Matrix binding PASS.

### Task 5: Produce the exact authorization handoff

**Files:**
- Read: final Git commit and tree
- Read: `.commit-ci-preflight.toml`
- Read: `.commit-ci-policy-v2.toml`
- Read: `experiments/a0x-six-model/material-execution-contract.json`

**Interfaces:**
- Consumes: Task 4 terminal verification evidence.
- Produces: one user-facing exact-head CCP authorization envelope; no execution.

- [ ] **Step 1: Report final immutable identifiers**

Report:

- repository clone path;
- final commit and tree;
- clean status;
- CCP executable path and complete SHA-256;
- source commit/tree of the CCP producer;
- Matrix profile `matrix-v2-legacy-v1`;
- outer and per-runtime plan digests;
- configuration and policy hashes;
- material contract, two freeze, twelve dossier, and no-model receipt hashes;
- complete verification counts and durations where available.

- [ ] **Step 2: Draft the single-run authorization text**

Bind one generation-1 CCP exact-head run to the final clone, commit, tree,
producer, profile, plan digests, and maximum one run. Require fresh
`resource status`, `admission status`, `plan`, `doctor`, and `dry-run` evidence
and stop on any mismatch.

- [ ] **Step 3: Stop**

Do not invoke CCP, Docker, publish evidence, push, update PR #105, or merge.
