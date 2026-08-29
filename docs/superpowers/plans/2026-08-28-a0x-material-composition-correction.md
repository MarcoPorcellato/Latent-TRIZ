# A0X Material Composition Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the A0X material refusal stub with a hash-bound, shell-free, one-shot production composition that preserves the frozen A0/A0-R1 protocol and stops before material execution.

**Architecture:** A fixed outer launcher validates pair-scoped runtime inputs and invokes one exact CCP `guard exec`; a fixed child composes existing target-free activation, one-shot target reading, frozen analysis, terminal packaging, verification, and cleanup. Runtime authorization lives outside the immutable result directory, while authorization bytes and qualification evidence are embedded in the terminal package.

**Tech Stack:** Python 3.11, JSON Schema Draft 2020-12, `unittest`, existing Latent-TRIZ A0X modules, CCP shell-free `guard exec`.

**Spec:** `docs/superpowers/specs/2026-08-28-a0x-material-composition-correction-design.md`

## Global Constraints

- No CCP heavy command, Docker, model/tokenizer construction, target access, network, GitHub, or publication during this plan.
- Preserve the exact A0 and A0-R1 corpora, selections, endpoints, controls, seeds, thresholds, statistical rules, and model cards.
- Use one uniform outer timeout of 3,600 seconds, internal budget of 3,300 seconds, cleanup margin of 300 seconds, and admission timeout of 300 seconds.
- Preserve all twelve independent pair identities; never pool, rank, substitute, tune, or retry.
- Use TDD for every production change and `apply_patch` for edits.
- Preserve unrelated dirty files, stashes, model snapshots, caches, receipts, and user work.

---

### Task 1: Freeze runtime-inlet, timeout, launch, and qualification-evidence contracts

**Status:** Complete; focused contracts and schema tests are green.

**Files:**
- Create: `src/latent_triz/a0x_material_contract.py`
- Create: `schemas/a0x-guard-launch.schema.json`
- Create: `schemas/a0x-qualification-evidence.schema.json`
- Modify: `schemas/a0x-execution-authorization.schema.json`
- Modify: `schemas/a0x-authorization-dossier.schema.json`
- Modify: `src/latent_triz/a0x_contract.py`
- Modify: `tests/a0x_test_support.py`
- Create: `tests/test_a0x_material_contract.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `A0XGuardLaunch`, `TimeoutEnvelope`, `canonical_guard_commitment()`, `derive_runtime_paths()`, `validate_qualification_evidence()`.
- Consumes: existing `PairBinding`, canonical commitment helpers, model-card and CCP identity values.

- [ ] Write failing tests proving the authorization inlet is outside `results/`, is pair-derived below `.a0x-runtime/`, and a dossier cannot name any other path.
- [ ] Write failing tests for the exact timeout envelope `3600/3300/300/300` and rejection of per-model overrides, booleans, zero, negative, or unbounded values.
- [ ] Write failing tests that build the canonical shell-free argv object and mutate, one at a time, CCP path, Python path, cwd, child script, descriptor, timeout, resource label, memory limit, separator, and child argument.
- [ ] Write failing tests for qualification evidence with exact receipt ID/hash, source HEAD, producer identity, public evidence branch/path, and rejection of local paths or private fields.
- [ ] Implement the smallest pure-data contract module and schemas that pass the focused tests.
- [ ] Add `.a0x-runtime/` to `.gitignore`; assert tests never write it in the source checkout.
- [ ] Run `PYTHONPATH=src .venv/bin/python -m unittest tests.test_a0x_material_contract tests.test_a0x_contract tests.test_a0x_schemas -v` and record the terminal count.
- [ ] Run schema cross-validation and `git diff --check`.

### Task 2: Build the private child lifecycle through injected capabilities

**Status:** Complete; lifecycle and timeout-frontier tests are green.

**Files:**
- Create: `src/latent_triz/a0x_material_runtime.py`
- Create: `tests/test_a0x_material_runtime.py`
- Modify: `src/latent_triz/a0x_runner.py`
- Modify: `src/latent_triz/a0x_execution.py`
- Modify: `src/latent_triz/a0x_report.py`
- Modify: `src/latent_triz/a0x_verify.py`

**Interfaces:**
- Consumes: `A0XGuardLaunch`, existing model adapter, A0/R1 activation extractors, `OneShotTargetReader`, A0/R1 analyzers, terminal builder and verifier.
- Produces: `build_material_runtime()`, `execute_material_child()`, stage timing receipt, and first-terminal failure sealing.

- [ ] Write failing injected tests for exact A0 and R1 dispatch and prove activation receives no target path, target rows, or reader.
- [ ] Write failing ordering tests proving target-reader construction follows activation sealing and `read_jsonl_once()` occurs exactly once immediately before analysis.
- [ ] Write failing tests proving immutable activation, target-receipt, dense, and index bytes are passed unchanged to the correct analyzer.
- [ ] Write failing tests for every lifecycle frontier, including tokenizer, model, activation, target reservation/open/hash/parse/selection, analysis, package, verifier, postflight, release, and internal timeout.
- [ ] Write failing tests proving model release after success and all post-load failures; cleanup uncertainty must not erase the first terminal outcome.
- [ ] Implement the injected child lifecycle by composing existing primitives without modifying scientific modules.
- [ ] Add monotonic stage timing and the 3,300-second internal deadline; check it at every stage boundary and model-forward iteration seam.
- [ ] Run focused runtime tests plus existing activation, analysis, execution, report, and verifier tests.

### Task 3: Implement the fixed child entrypoint

**Status:** Complete; import/help remain inert and descriptor-only tests are green.

**Files:**
- Create: `scripts/a0x_material_child.py`
- Create: `tests/test_a0x_material_child.py`
- Modify: `src/latent_triz/a0x_material_runtime.py`

**Interfaces:**
- Consumes: one repository-relative launch descriptor.
- Produces: one privacy-minimized terminal JSON line and a process exit code reflecting the sealed result.

- [ ] Write failing CLI tests proving only `--launch-descriptor` is accepted and all model/leg/revision/output/target/timeout/command overrides are rejected.
- [ ] Write failing tests for descriptor bytes, source HEAD, cwd, Python executable/hash, environment allowlist, pair, runtime files, and child-script hash drift before model construction.
- [ ] Write failing tests that forbid network-enabled Hugging Face settings, generation, `trust_remote_code`, non-CPU parameters, or non-float32 parameters.
- [ ] Implement the fixed child CLI and production factory wiring behind injected seams.
- [ ] Prove importing and `--help` do not import Torch/Transformers or read model/target files.
- [ ] Run focused child tests, compile checks, and `git diff --check`.

### Task 4: Replace the outer refusal stub with a real, non-materially tested launcher

**Status:** Complete offline; no real CCP process was started.

**Files:**
- Modify: `scripts/a0x_material.py`
- Create: `src/latent_triz/a0x_ccp_executor.py`
- Modify: `tests/test_a0x_material.py`
- Create: `tests/test_a0x_ccp_executor.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: fixed dossier, derived authorization inlet, local qualification receipt/evidence, canonical guard launch, live source/hash/status probes.
- Produces: durable claim/pre-run observation and exactly one shell-free CCP guard invocation when used later under authorization.

- [ ] Write failing tests proving fixed-dossier-only dispatch, exact twelve-target bijection, and no selectable model/leg/output/target/timeout/command surface.
- [ ] Write failing tests that use a fake process executor to verify exact argv tokens and cwd without invoking CCP.
- [ ] Write failing drift/race tests for dossier, authorization, qualification receipt, CCP/Python/child hashes, source HEAD, config/policy, output occupancy, claim, and launch descriptor.
- [ ] Write failing tests for outer guard exit `5`, `6`, `70`, `124`, `130`, and ordinary child exits; every invoked guard consumes the attempt and emits recovery evidence without retry.
- [ ] Implement the subprocess boundary using `subprocess.run` with an argv list, `shell=False`, exact cwd/environment, bounded capture, and no fallback.
- [ ] Keep Make targets fixed and exclude them from repository CI workflows.
- [ ] Run focused launcher/executor tests and prove no real CCP process was started.

### Task 5: Bind qualification evidence and runtime authorization into terminal packages

**Status:** Complete; public-safety and mutation tests are green.

**Files:**
- Modify: `src/latent_triz/a0x_report.py`
- Modify: `src/latent_triz/a0x_verify.py`
- Modify: `schemas/a0x-publication-manifest.schema.json`
- Modify: `schemas/a0x-terminal-result.schema.json`
- Modify: `tests/test_a0x_report.py`
- Modify: `tests/test_a0x_verify.py`

**Interfaces:**
- Consumes: byte-exact authorization inlet, validated qualification evidence, terminal receipts, external dense/index assets.
- Produces: self-contained package plus immutable external/evidence locators verifiable from a fresh clone.

- [ ] Write failing tests that compare embedded authorization bytes with the inlet and continue to verify after the inlet is absent.
- [ ] Write failing tests for missing/mutated qualification evidence, receipt locator, receipt ID/hash, evidence branch/commit, producer identity, and source HEAD.
- [ ] Write failing tests for missing/mutated dense/index assets and cross-leg/model/run substitutions.
- [ ] Implement new package roles and verifier bindings without copying dense data or raw private logs into the package.
- [ ] Prove package schemas reject pooling, ranking, general-claim, raw-log, local-path, or secret-bearing fields.
- [ ] Run report/verifier/schema focused gates.

### Task 6: Regenerate all hash-bound A0X artifacts without material access

**Status:** Complete from implementation anchor
`3dc40aa104358a83855cd59a40df30319131ea1e`.

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `scripts/a0x_freeze.py`
- Modify: `experiments/a0x-six-model/material-execution-contract.json`
- Modify: `experiments/a0x-six-model/a0/implementation.json`
- Modify: `experiments/a0x-six-model/r1/implementation.json`
- Modify: `experiments/a0x-six-model/a0/freeze-manifest.json`
- Modify: `experiments/a0x-six-model/r1/freeze-manifest.json`
- Modify: `experiments/a0x-six-model/approval-dossiers/a0/*.json`
- Modify: `experiments/a0x-six-model/approval-dossiers/r1/*.json`
- Modify: `results/a0x/preexecution/a0x-no-model-verification-receipt.json`
- Modify: `tests/test_a0x_freeze.py`
- Modify: `tests/test_a0x_frozen_package.py`

**Interfaces:**
- Consumes: reviewed production composition source, schemas, timeout envelope, interpreter manifest, selected CCP candidate identity.
- Produces: deterministic material contract, two freezes, twelve `approval_requested` dossiers, and a zero-access verification receipt.

- [ ] Add failing tests requiring every new production/schema/test file in both implementation manifests and freezes.
- [ ] Add failing tests requiring exactly twelve runtime-inlet paths, guard launch templates, uniform timeout values, and no authorization grant.
- [ ] Update the deterministic generator; regeneration must run only in a disposable copy and leave source inputs byte-identical.
- [ ] Regenerate the source artifacts once, then reproduce them byte-identically in a second disposable copy.
- [ ] Verify all dossiers remain `approval_requested` and report zero model/tokenizer/target/CCP/Docker/network/remote access.
- [ ] Record complete SHA-256 values for material contract, two freezes, twelve dossiers, no-model receipt, guard schema, qualification schema, child, launcher, and runtime module.

### Task 7: Document every discovered problem, correction, and remaining gate

**Status:** Complete locally; publication remains unauthorized.

**Files:**
- Create: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`
- Modify: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify: `docs/A0X_RESTART_HANDOFF.md`
- Modify: `docs/PERSISTENT_GOAL.txt`
- Modify: `docs/README.md`
- Modify: `.superpowers/sdd/2026-08-24-a0x-six-model-replication-implementation/progress.md`
- Create: `.superpowers/sdd/2026-08-28-a0x-material-composition-correction/progress.md`

**Interfaces:**
- Consumes: exact task evidence, hashes, tests, reviews, and access counters.
- Produces: a durable restart checkpoint and auditable problem/solution chronology.

- [ ] Document the refusal stub, authorization/output collision, opaque argv hash, qualification-evidence gap, stale CCP producer, incompatible candidate timeout, ignored-file audit false negative, timeout rationale, and exact fixes.
- [ ] For each problem record symptom, root cause, affected evidence, correction, regression test, residual risk, and current status.
- [ ] Update canonical state to the new hashes and `sealed_gate_pending`; explicitly state that material execution remains unauthorized.
- [ ] Run documentation policy checks, link checks available offline, placeholder scan, and `git diff --check`.

### Task 8: Complete the offline aggregate and independent review

**Status:** Complete offline. Aggregate gates are green, the independent review
returned APPROVE, and the exact hash ledger is recorded. CCP qualification and
all material execution remain separate future gates.

**Files:**
- Modify only files required to fix review findings within Tasks 1--7.
- Create: `.superpowers/sdd/2026-08-28-a0x-material-composition-correction/final-review.md`

**Interfaces:**
- Consumes: complete offline candidate from Tasks 1--7.
- Produces: terminal no-material verification evidence and exact hash ledger for the next approval.

- [ ] Run every focused test from Tasks 1--7.
- [ ] Run the complete A0X aggregate with both the minimal and full local Python environments, recording expected dependency skips separately.
- [ ] Run schema cross-validation, repository check without model/target access, compilation, docs checks, and diff checks.
- [ ] Independently review architecture, security, scientific invariants, timeout behavior, one-shot semantics, package recoverability, and fresh-clone fail-closed verification.
- [ ] Correct every Important or higher finding with a new red/green regression and rerun affected aggregate gates.
- [ ] Verify through instrumentation that the whole tranche performed zero CCP heavy commands, Docker actions, model/tokenizer constructions, target reads, network access, and remote mutations.
- [ ] Stop and report exact hashes and the next required authorization. Do not start CCP qualification or material execution.
