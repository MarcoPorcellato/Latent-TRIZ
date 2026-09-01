# A0X Hosted Gate A Capture Wrapper Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Recreate a target-free fail-closed Hosted Gate A capture wrapper in a durable clone.

**Architecture:** Pure capture module plus thin injected CLI adapter; existing verifier remains separate.

**Tech Stack:** Python standard library, existing canonical JSON/schema helpers, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-01-a0x-hosted-gate-a-capture-wrapper-recovery-design.md`

## Global Constraints

- No real network/GitHub/attestation verification/Gate B/C/material runtime/CCP/Docker/model/tokenizer/target/push/PR/merge.
- TDD red then green. Synthetic inputs and injected subprocesses only.
- Every refusal is fail-closed and leaves no canonical partial output.
- No freeze or dossier regeneration unless separately re-authorized after Makefile correction.

### Task 1: Restore request, archive, and transaction library

**Files:**
- Create: `src/latent_triz/a0x_hosted_capture.py`
- Create: `tests/test_a0x_hosted_capture.py`
- Create: `schemas/a0x-hosted-gate-a-capture-request.schema.json`
- Create: `schemas/a0x-hosted-gate-a-capture-transport.schema.json`

- [ ] Write red synthetic tests for pinned CLI, strict request metadata, safe ZIP, cross-binding, and transaction refusal.
- [ ] Implement smallest fail-closed module; run focused tests green.
- [ ] Add mutation regressions for every binding and fault path; commit.

### Task 2: Restore shell-free operational wrapper

**Files:**
- Create: `scripts/a0x_capture_hosted_gate_a.py`
- Create: `tests/test_a0x_capture_hosted_gate_a.py`

- [ ] Write red injected-subprocess tests for explicit args and per-call CLI revalidation.
- [ ] Implement no-shell wrapper, fixed transport operations, and unsupported-host refusal seam.
- [ ] Run focused suites green; commit.

### Task 3: Integrate trusted surface and prepare next authorization

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `tests/test_a0x_freeze.py`
- Modify: `Makefile`
- Modify: A0X operator/campaign/problem/persistent-goal docs

- [ ] Add red inventory and aggregate tests.
- [ ] Add all wrapper paths to inventory and both new modules to synthetic aggregate.
- [ ] Run no-model deterministic ladder without regeneration.
- [ ] Stop and request explicit authorization for one new target-free regeneration, twelve dossiers, full suite, review, and local closure.
