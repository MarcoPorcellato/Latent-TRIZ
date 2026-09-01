# A0X Offline Gate B Runtime Builder Implementation Plan

> **For Codex:** Execute inline with the TDD and verification-before-completion skills. The user has approved this design and only the target-free implementation tranche. Do not perform a real build.

**Goal:** Implement a fail-closed, reproducible Python 3.11 and APFS snapshot prerequisite builder for later A0X Gate B use.

**Architecture:** A focused library owns static validation, deterministic
no-execution planning, complete base-runtime and wheelhouse APFS binding,
shell-free execution only from owned paths, exact post-install verification,
model clonefile materialization, and a local receipt. A thin CLI requires an
explicit plan or build mode. Existing Hosted Gate A and runtime-bundle modules
remain unchanged authorities.

**Tech Stack:** Python 3.11 standard library, `venv`, `pip`, existing A0X wheelhouse/APFS/model-card contracts, `unittest`.

---

### Task 1: Freeze the approved architecture

**Files:**
- Create: `docs/superpowers/specs/2026-09-01-a0x-offline-gate-b-builder-design.md`
- Create: `docs/superpowers/plans/2026-09-01-a0x-offline-gate-b-builder-implementation.md`

1. Record boundaries, commands, failure model, and non-authorizations.
2. Verify that the design produces prerequisites only.

### Task 2: Implement deterministic planning with TDD

**Files:**
- Create: `tests/test_a0x_gate_b_builder.py`
- Create: `src/latent_triz/a0x_gate_b_builder.py`

1. Write failing tests for wheelhouse and base-runtime manifest hashes,
   39-distribution cardinality, hash-locked requirements, exact command
   construction, path confinement, no-execution/no-write planning, and explicit
   CLI mode selection.
2. Run the focused test and confirm RED because the module is absent.
3. Implement only strict parsing, plan records, and canonical requirements generation.
4. Run the focused test and confirm GREEN.

### Task 3: Implement execution boundaries with TDD

**Files:**
- Modify: `tests/test_a0x_gate_b_builder.py`
- Modify: `src/latent_triz/a0x_gate_b_builder.py`

1. Add failing tests for shell-free runner calls, APFS-bound Python and wheels,
   exact installed distributions, APFS model allowlist materialization, final
   bound-input revalidation, exclusive receipt creation, and fail-closed errors.
2. Confirm RED on the missing behavior.
3. Implement the minimal execution path with injected runner and clone callback.
4. Confirm GREEN, then run adjacent APFS and wheelhouse suites.

### Task 4: Add the CLI with TDD

**Files:**
- Create: `scripts/a0x_build_gate_b_runtime.py`
- Create: `tests/test_a0x_gate_b_builder_cli.py`

1. Add failing tests proving `--plan` produces canonical JSON and never executes a child or clone operation.
2. Implement a thin CLI around the library.
3. Confirm GREEN and stable refusal output.

### Task 5: Bind and document the trusted surface

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `tests/test_a0x_freeze.py`
- Modify: `tests/test_a0x_frozen_package.py`
- Modify: `docs/A0X_GATE_B_OPERATOR_HARDENING.md`
- Modify: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify: `docs/A0X_PROBLEM_SOLUTION_REGISTER.md` if present

1. Add the builder library, CLI, and tests to the frozen implementation inventory.
2. Add inventory regressions.
3. Document the builder boundary, the verified local wheelhouse status without promoting it to public evidence, and the separately authorized material procedure.
4. Run documentation and focused frozen-package tests.

### Task 6: Regenerate target-free bindings

**Files:**
- Modify generated A0X A0/R1 implementation inventories, freezes, and twelve dossiers.

1. Commit implementation and documentation so `implementation_source_head` can be exact.
2. Run the canonical protected-tree/selection and freeze/dossier regeneration commands without model or target access.
3. Commit only regenerated target-free bindings.
4. Record every new SHA-256.

### Task 7: Verify and stop

1. Run focused builder, APFS, wheelhouse, frozen-package, no-model, synthetic, schema, documentation, and complete repository suites.
2. Inspect the full diff and exact Git state.
3. Commit the final target-free state locally.
4. Report exact HEAD, tree, tests, and regenerated hashes.
5. Stop. Do not create a real environment or model snapshot; do not run Gate B/C or publish.
