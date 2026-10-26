# A0X Sealed Cohort and Failure Terminal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans, inline direct-main. The operator already selected implementation plus a new GPT-6 Astra Medium reviewer. No implementation delegation.

**Goal:** reject incompatible public cohort metadata before consumption and preserve verified failure terminals without scientific promotion.

**Architecture:** strengthen the existing public selection generator/loader, then converge the existing material failure producer, child wire and parent/package consumers. Preserve historical bytes and use only temporary synthetic fixtures for verification.

**Tech Stack:** existing dependency-free Python, unittest and JSON schemas; no installation.

**Spec:** `docs/superpowers/specs/2026-10-26-a0x-sealed-cohort-terminal-design.md`.

## Global constraints

- Base HEAD `20bfdb95a795b794648d7981298a47c427715a1b`, tree `1da1cd948fc43bd05df86a14dc4c93ab4d34fdd5`; work only in the existing isolated A0X clone.
- No reopening or probing protected targets, their retained copies, models, tokenizers or private mappings. Fixtures use temporary independent data.
- No canonical derivative generation, commit, stage, network, Beads, CCP, Docker, Gate A/B/C, next attempt or publication.
- Preserve consumed claim and historical evidence. Existing frozen artifacts deliberately remain stale for this candidate until separate authorization.
- Keep limits, statistics, R1 and scientific claims unchanged. Policy is `a0x-a0-sealed-cohort-v1`, split `sealed`, 48 cases/24 families/six domains.
- Use `rtk`, `-B`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src`. Run only statically audited synthetic tests; unsafe broad discovery is excluded and must be reported, not silently claimed green.

## Review focus

- Calibration families sorting before sealed families must never enter the prospective cohort (Task 1).
- Mixed family splits, duplicate IDs or fewer than four eligible families must refuse without target access (Task 1).
- Rehashed legacy/calibration selection must refuse before permission, claim or model callbacks (Task 1).
- A sealed failure must survive real child serialization and parent/package verification without becoming null/positive (Task 2).
- Missing/mismatched packages, impossible outcome/frontier combinations and failed cleanup remain refusals (Task 2).

## Task 1: prospective public-only cohort admission

**Files:** `src/latent_triz/a0x_freeze.py`, `src/latent_triz/a0x_execution.py`, `schemas/a0x-selection-manifest.schema.json`; existing freeze/execution/preflight tests and synthetic fixture helpers, plus rehearsal fixture construction where necessary.

**Interfaces:** preserve `build_a0_selection_manifest(...)` and `load_a0_public_selection(...)`. The builder emits required policy/split bindings; loader validates them and the sealed cohort before returning `FrozenSelectionCapability`. No material capability is added.

- [x] Add mixed-split temporary fixture tests with literal expected sealed family IDs; observe intended RED.
- [x] Add loader/preclaim rejection tests, including legacy policy, malformed counts and duplicate identities; observe intended RED.
- [x] Implement split filtering/admission and required closed schema fields, updating synthetic fixtures to explicit sealed inputs without production bypasses.
- [x] Run the safe targeted tests and record GREEN. Do not regenerate the real selection manifest.

## Task 2: truthful failure production and end-to-end wire acceptance

**Files:** `src/latent_triz/a0x_vertical_production_adapter.py`, `src/latent_triz/a0x_ccp_executor.py`, `src/latent_triz/a0x_vertical_terminal_package.py`, relevant existing result schema and vertical production/material/package tests.

**Interfaces:** retain the public production entrypoints. A small pure failure-terminal helper may expose the existing failure payload construction for real tests; it grants no material authority. Reuse `_emit_terminal`, `_parse_vertical_child_terminal` and independent package verification.

- [x] Add RED regressions for a target-read failure through the real producer/serializer/parser/package path, using only a synthetic model/OS boundary and temporary target sentinels.
- [x] Add tuple/package/cleanup refusal regressions and early-failure cases; do not weaken existing scientific-success assertions.
- [x] Derive conservative frontier/diagnostic from actual verified progress; accept completed failure lifecycle only with exact package and unchanged independent postflight checks.
- [x] Keep asset capture restricted to explicitly asset-bearing scientific outcomes; do not require or publish assets merely because a failed result is sealed.
- [x] Run audited focused regressions, including the unchanged positive path, and record GREEN and any limitations.

## Task 3: review and durable handoff

- [x] Verify historical artifact/claim content bindings, without accessing target/model content. Metadata limitation: six historical failure members and the consumed claim match hashes/size/link counts but have private mode 0600 instead of recorded 0644; the cause/time is unresolved. Preserve the failed full-metadata check and do not claim complete metadata identity.
- [x] Run scoped diff checks and collect changed-file hashes, test counts and exact failures. Full discovery is not authorized unless its entire closure is proved safe.
- [x] Send the coherent verified diff and synthetic evidence to the same new Astra Medium instance; resolve findings only within this target-free scope.
- [x] Update the local implementation notebook and handoff. Stop before commit, canonical regeneration or any qualification/material gate.

## Completion record

Target-free implementation complete, uncommitted. Ninety distinct targeted tests passed (88-test focused ladder plus two supplemental temporary P0/contract methods). Astra Medium: PASS_WITH_NOTES, no blocking implementation finding. Exact evidence and remaining minor improvements are recorded in `.a0x-runtime/SEALED_COHORT_TDD_CHECKPOINT_2026-10-26.md`, the Astra report and `SEALED_COHORT_VERIFICATION_2026-10-26.json`. The metadata limitation above is not a PASS and grants no material readiness. No canonical artifact was regenerated, and the old attempt remains consumed.

Self-review: scope, signatures and profile values match the approved design; each review focus has an owning test task. The plan does not authorize a real cohort artifact or another material attempt.
