---
type: implementation-plan
title: A0X contract convergence implementation plan
status: approved-for-offline-implementation
version: 1.0.0
date: 2026-09-01
source_head: 2670dbd8008b7498c417b03a38d475cb5acd279b
source_tree: 63c9e015c30c2c4aef48730718db8129a2d630f0
scope: target-free
---

# A0X Contract Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate parallel A0X contract truths so every real frozen pair is accepted consistently from dossier generation through Hosted Gate A, Gate B preparation, Gate C execution, and terminal sealing.

**Architecture:** Keep the existing safety boundaries, but move pair identity, pair-derived paths, and lifecycle transitions into a deterministic functional core. JSON Schemas remain self-contained transport artifacts compiled from one canonical pair fragment; adapters perform I/O but may not redefine domain semantics. A target-free compatibility oracle validates the complete 12-pair boundary before any freeze, hosted qualification, or operator authorization.

**Tech Stack:** Python 3.11/3.12, standard-library `unittest`, repository JSON Schema validator, JSON Schema Draft 2020-12, deterministic canonical JSON, Git.

**Spec:** `docs/A0X_ARCHITECTURE_CONVERGENCE.md`

## Global Constraints

- Preserve public base `2670dbd8008b7498c417b03a38d475cb5acd279b`, tree `63c9e015c30c2c4aef48730718db8129a2d630f0`, as historical evidence.
- Preserve all historical receipts, result packages, authorization records, and published evidence byte-identically.
- Keep `a0x-pair-scope-v2`; this is an invariant repair, not a scientific protocol change.
- The exact canonical result path is `results/a0x/<leg>/<model_key>/<run_id>` with no trailing slash.
- Do not add external JSON Schema resolution, network access, or a new runtime dependency.
- Do not load models or tokenizers, read targets, run CCP/Docker, or cross Gate B/C.
- Every production change follows RED → GREEN → REFACTOR with the failing test observed first.
- Generated schemas remain self-contained and use local `$ref` only.
- Every new implementation source, generator, schema source, compatibility test, and operational check must be bound by the A0X implementation inventory before regeneration.
- Stop before regeneration if any pre-existing real dossier changes after parse/serialize except through the expected implementation/freeze hash cascade.
- Stop before material or remote action; publication, Hosted Gate A capture, Gate B, and Gate C require later exact authorizations.

---

### Task 1: Establish the non-tautological compatibility oracle

**Files:**
- Create: `src/latent_triz/a0x_compatibility.py`
- Create: `scripts/a0x_compatibility_check.py`
- Create: `tests/test_a0x_pair_compatibility.py`
- Modify: `scripts/repository_check.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: the 12 tracked dossier JSON files and the two production Hosted schemas.
- Produces: `check_frozen_pair_compatibility(root: Path) -> CompatibilityReport` and a zero-write CLI returning non-zero unless all expected cases pass.

- [ ] **Step 1: Write the failing real-dossier test**

```python
def test_all_real_dossiers_cross_both_hosted_boundaries(self):
    report = check_frozen_pair_compatibility(ROOT)
    self.assertEqual(24, report.expected_case_count)
    self.assertEqual(24, report.passed_case_count)
    self.assertEqual((), report.failures)
```

The test must load the tracked dossiers. It must not call `tests.a0x_test_support.pair_binding()`.

- [ ] **Step 2: Run RED and retain the exact failure**

Run:

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_pair_compatibility -v
```

Expected: FAIL with 24 `pair_binding.output_path` schema failures. A collection error, missing import, or fabricated fixture is not the required RED.

- [ ] **Step 3: Implement the reporting shell without fixing compatibility**

```python
@dataclass(frozen=True)
class CompatibilityFailure:
    dossier_path: str
    consumer_schema: str
    issue_path: str
    message: str

@dataclass(frozen=True)
class CompatibilityReport:
    expected_case_count: int
    passed_case_count: int
    failures: tuple[CompatibilityFailure, ...]
```

The oracle constructs full Gate B authorization and verification-receipt envelopes by replacing only `pair_binding` in schema-valid templates. It validates with `latent_triz.validator.validate` and sorts failures by dossier and schema.

- [ ] **Step 4: Add zero-write and exact-cardinality tests**

Test that repeated runs are identical, no repository file changes, six models exist in each leg, and missing/extra/duplicate dossiers fail closed.

- [ ] **Step 5: Prepare repository integration without enabling a red gate**

Prepare the `a0x-compatibility-check` target and repository-check call, but do
not commit or publish a repository state in which the new required gate is
known to fail. Do not maintain a second implementation.

- [ ] **Step 6: Preserve RED evidence without committing a broken checkpoint**

Record the exact command, test count, and 24 schema failures in the task
checkpoint. Keep the RED changes local until Task 3 makes the compatibility
oracle green; no versioned commit may knowingly require a failing gate.

---

### Task 2: Make pair identity and output derivation canonical

**Files:**
- Create: `src/latent_triz/a0x_pair.py`
- Modify: `src/latent_triz/a0x_contract.py`
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `src/latent_triz/a0x_runner.py`
- Modify: `tests/a0x_test_support.py`
- Modify: `tests/test_a0x_contract.py`
- Modify: `tests/test_a0x_freeze.py`

**Interfaces:**
- Produces: `derive_pair_output_path(leg: Leg | str, model_key: str, run_id: str) -> str`.
- Produces: `PairBinding.from_mapping()` that rejects any `output_path` unequal to the derived value.
- Preserves: imports from `latent_triz.a0x_contract` through explicit re-exports during migration.

- [ ] **Step 1: Write focused failing invariant tests**

```python
def test_pair_rejects_model_root_output(self):
    value = real_pair_mapping()
    value["output_path"] = f"results/a0x/{value['leg']}/{value['model_key']}/"
    with self.assertRaisesRegex(A0XContractError, "derived output path"):
        PairBinding.from_mapping(value)

def test_pair_rejects_wrong_run_output(self):
    value = real_pair_mapping()
    value["output_path"] += "-different"
    with self.assertRaisesRegex(A0XContractError, "derived output path"):
        PairBinding.from_mapping(value)
```

Also cover wrong leg/model segment, traversal, unsafe segment, trailing slash, and all 12 tracked dossiers.

- [ ] **Step 2: Run RED**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_contract.A0XContractTests.test_pair_rejects_model_root_output -v
```

Expected: FAIL because current `PairBinding` accepts a safe model-root path.

- [ ] **Step 3: Implement the pure pair core**

```python
PAIR_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

def derive_pair_output_path(leg: Leg | str, model_key: str, run_id: str) -> str:
    parsed_leg = Leg(leg)
    for label, value in (("model key", model_key), ("run id", run_id)):
        if not isinstance(value, str) or not PAIR_SEGMENT.fullmatch(value):
            raise A0XContractError(f"{label} is not a safe pair segment")
    return f"results/a0x/{parsed_leg.value}/{model_key}/{run_id}"
```

After constructing a `PairBinding`, require exact equality with this function. Keep dense-bound and registered-model validation unchanged.

- [ ] **Step 4: Remove independent output derivations**

Make `a0x_freeze.py`, `a0x_runner.py`, and `tests/a0x_test_support.py` call `derive_pair_output_path`. Search for independent `results/a0x/` formatting and justify every remaining literal.

- [ ] **Step 5: Prove all 12 real dossiers remain semantically identical**

Parse and reserialize every dossier pair; compare canonical JSON bytes of `pair_binding` before and after. Any difference is a stop condition.

- [ ] **Step 6: Run focused GREEN**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_contract tests.test_a0x_freeze tests.test_a0x_pair_compatibility -v
```

The compatibility test still fails at schemas, while pair-core tests pass.

- [ ] **Step 7: Keep the pair-core GREEN local until contract convergence**

Record the focused GREEN result. Do not commit yet: the new repository
compatibility gate remains intentionally RED until Task 3 compiles the schema
projections.

---

### Task 3: Compile self-contained pair schemas from one source

**Files:**
- Create: `schemas/a0x-pair-binding.fragment.json`
- Create: `schemas/a0x-pair-projections.json`
- Create: `src/latent_triz/a0x_schema_projection.py`
- Create: `scripts/a0x_compile_pair_schemas.py`
- Create: `tests/test_a0x_schema_projection.py`
- Modify: all A0X schemas registered in `a0x-pair-projections.json`

**Interfaces:**
- Produces: `compile_pair_projections(root: Path) -> dict[str, bytes]`.
- Produces: CLI modes `--write` and `--check`; default must be `--check`.
- Consumes: canonical PairBinding field metadata from `a0x_pair.py` plus
  explicit consumer overlays only.
- Treats: `schemas/a0x-pair-binding.fragment.json` as deterministic generated
  output, never as a second hand-edited contract source.

- [ ] **Step 1: Write RED tests for projection drift**

```python
def test_every_pair_definition_is_registered(self):
    self.assertEqual(discovered_pair_definitions(ROOT), registered_pair_definitions(ROOT))

def test_tracked_schemas_equal_compiled_bytes(self):
    for relative, expected in compile_pair_projections(ROOT).items():
        self.assertEqual(expected, (ROOT / relative).read_bytes(), relative)
```

Also assert no external `$ref`, network URI fetch, unregistered override, or implicit default overlay.
The baseline discovery must report exactly 20 PairBinding definitions across
the 33 A0X schemas recorded by the architecture audit. The registry must equal
the discovered path-and-definition-name set exactly. A cardinality change is a
stop condition requiring an explained specification update; it must not be
silently absorbed by adding entries.

- [ ] **Step 2: Run RED**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_schema_projection -v
```

Expected: FAIL because the fragment, registry, and compiler do not exist.

- [ ] **Step 3: Define the canonical fragment**

The generator projects the nine exact PairBinding fields from the pure pair
core and emits this lexical path pattern:

```json
{
  "output_path": {
    "type": "string",
    "pattern": "^results/a0x/(?:a0|r1)/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
  }
}
```

Document that cross-field equality remains the responsibility of `PairBinding`; JSON Schema supplies lexical transport validation.

Add mutation parity tests proving that every field required by the semantic
parser is represented by the generated fragment and that no fragment-only
field or independent default can be introduced.

- [ ] **Step 4: Implement deterministic local projection**

The registry identifies each schema and local definition name (`pair`, `a0_pair`, `any_pair`, or `result_pair`) plus explicit overlays. Compile canonical JSON with sorted keys and a trailing newline. Do not resolve external references.

- [ ] **Step 5: Migrate the two blocking Hosted schemas first**

Run:

```bash
rtk env PYTHONPATH=src:. python3 scripts/a0x_compile_pair_schemas.py --write --only a0x-gate-b-authorization.schema.json --only a0x-hosted-gate-a-verification-receipt.schema.json
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_pair_compatibility -v
```

Expected: 24/24 PASS.

- [ ] **Step 6: Migrate remaining registered pair definitions**

Compile all registered schemas. Run every existing schema-positive artifact and mutation test before accepting the generated bytes. Consumer-specific leg/dense constraints must remain explicit overlays.

- [ ] **Step 7: Prove both validators agree**

Run repository custom validation and pinned `jsonschema` cross-validation over every generated schema, all tracked real dossier projections, and existing mutation corpus.

- [ ] **Step 8: Enable the now-green repository compatibility gate**

Enable the prepared Make target and repository-check call. Run both entry
points and prove they share the same API and return `24/24 PASS`.

- [ ] **Step 9: Commit the first fully green convergence checkpoint**

```bash
rtk git add Makefile scripts/a0x_compatibility_check.py scripts/a0x_compile_pair_schemas.py scripts/repository_check.py schemas src/latent_triz/a0x_compatibility.py src/latent_triz/a0x_contract.py src/latent_triz/a0x_freeze.py src/latent_triz/a0x_pair.py src/latent_triz/a0x_runner.py src/latent_triz/a0x_schema_projection.py tests/a0x_test_support.py tests/test_a0x_contract.py tests/test_a0x_freeze.py tests/test_a0x_pair_compatibility.py tests/test_a0x_schema_projection.py
rtk git commit -m "refactor: converge A0X pair contracts"
```

---

### Task 4: Replace surrogate Hosted fixtures with semantic projections

**Files:**
- Create: `src/latent_triz/a0x_gate_contract.py`
- Modify: `src/latent_triz/a0x_hosted_verifier.py`
- Modify: `src/latent_triz/a0x_runtime_bundle.py`
- Modify: `tests/a0x_test_support.py`
- Modify: `tests/fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json`
- Modify: `tests/fixtures/a0x/hosted-gate-a/positive/verification-receipt.json`
- Modify: `tests/test_a0x_hosted_verifier.py`
- Modify: `tests/test_a0x_runtime_bundle.py`

**Interfaces:**
- Produces: pure builders for Gate B authorization and verification receipt.
- Requires: both schema validation and `PairBinding.from_mapping()` at the Hosted verifier boundary.

- [ ] **Step 1: Write RED semantic-boundary tests**

```python
def test_hosted_verifier_rejects_schema_valid_semantically_invalid_pair_before_runner(self):
    authorization = valid_authorization_from_real_dossier()
    authorization["pair_binding"]["output_path"] = "results/a0x/a0/gpt2/"
    with self.assertRaisesRegex(A0XHostedVerifierError, "pair binding"):
        verify(...)
    self.assertEqual(0, runner.calls)
```

Add a dense-bound mutation that currently passes the Hosted schema but fails `DenseBound.from_mapping()`.

- [ ] **Step 2: Run RED and confirm runner reachability**

Expected: the path case fails at schema, while the dense-bound case currently reaches later orchestration or fails without the stable semantic-boundary code. Record exact behavior.

- [ ] **Step 3: Add pure builders**

Builders accept a validated `PairBinding` and typed/hash-validated inputs. They return mappings only; they perform no filesystem, GitHub, subprocess, clock, model, or target action.

- [ ] **Step 4: Enforce semantic parsing in the Hosted verifier**

Immediately after schema parsing:

```python
try:
    pair = PairBinding.from_mapping(authorization["pair_binding"])
except A0XContractError as error:
    raise A0XHostedVerifierError(INPUT_INVALID) from error
```

Build the receipt from `pair.as_mapping()`, not unvalidated input bytes.

- [ ] **Step 5: Regenerate positive fixtures from a real-shaped pair**

Use a canonical production builder and a semantically valid dense bound. Checked-in fixture bytes are snapshots of builder output, and a snapshot test fails if either drifts independently.

- [ ] **Step 6: Run focused GREEN**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_hosted_verifier tests.test_a0x_runtime_bundle tests.test_a0x_pair_compatibility -v
```

- [ ] **Step 7: Commit**

```bash
rtk git add src/latent_triz/a0x_gate_contract.py src/latent_triz/a0x_hosted_verifier.py src/latent_triz/a0x_runtime_bundle.py tests/a0x_test_support.py tests/fixtures/a0x/hosted-gate-a/positive tests/test_a0x_hosted_verifier.py tests/test_a0x_runtime_bundle.py
rtk git commit -m "fix: bind Hosted Gate A to semantic pair identity"
```

---

### Task 5: Converge the execution state machine

**Files:**
- Modify: `src/latent_triz/a0x_execution.py`
- Modify: `src/latent_triz/a0x_runner.py`
- Modify: `src/latent_triz/a0x_production_adapter.py`
- Modify: `src/latent_triz/a0x_material_runtime.py`
- Modify: `tests/test_a0x_execution.py`
- Modify: `tests/test_a0x_runner.py`
- Modify: `tests/test_a0x_production_adapter.py`
- Modify: `tests/test_a0x_material_runtime.py`

**Interfaces:**
- Produces: one reducer that maps state/event to the next state or terminal sealing state.
- Removes: independent string-to-state inference in runner and adapter.

- [ ] **Step 1: Write the transition-table RED tests**

Cover:

```text
PREFLIGHT -> ACTIVATION -> ANALYSIS -> SEALED
```

Reject reverse transitions, skipped stages, transition from `SEALED`, double target read, double seal, positive/null without valid target receipt, and pre-analysis failure with non-zero reads.

- [ ] **Step 2: Run RED**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_execution -v
```

At least one test must prove that current runner/adapter stage mapping bypasses the tested `advance_attempt()` behavior.

- [ ] **Step 3: Implement the minimal reducer**

```python
class AttemptEvent(StrEnum):
    ACTIVATION_STARTED = "activation_started"
    TARGET_RESERVED = "target_reserved"
    ANALYSIS_STARTED = "analysis_started"
    TERMINAL_SELECTED = "terminal_selected"

def reduce_attempt(state: AttemptState, event: AttemptEvent) -> AttemptState:
    ...
```

Keep status validation in the same functional core. The reducer performs no I/O.

- [ ] **Step 4: Make production orchestration consume the reducer**

Runner and production adapter carry `AttemptState`, never infer it independently from arbitrary strings. `sealed_from_state`, target-read count, lifecycle status, and package status are validated from the same transition record.

- [ ] **Step 5: Delete replaced mappings**

Remove the independent mapping at `a0x_production_adapter.py` and any runner-local transition table after parity tests pass. Do not remove one-shot reader, overwrite refusal, terminal recovery, or cleanup controls.

- [ ] **Step 6: Run focused GREEN**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_execution tests.test_a0x_runner tests.test_a0x_production_adapter tests.test_a0x_material_runtime -v
```

- [ ] **Step 7: Commit**

```bash
rtk git add src/latent_triz/a0x_execution.py src/latent_triz/a0x_runner.py src/latent_triz/a0x_production_adapter.py src/latent_triz/a0x_material_runtime.py tests/test_a0x_execution.py tests/test_a0x_runner.py tests/test_a0x_production_adapter.py tests/test_a0x_material_runtime.py
rtk git commit -m "refactor: make A0X lifecycle state executable"
```

---

### Task 6: Enforce architecture and documentation fitness functions

**Files:**
- Create: `tests/test_a0x_architecture.py`
- Modify: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`
- Modify: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify: `docs/CURRENT_STATUS.md`
- Modify: `docs/PERSISTENT_GOAL.txt`
- Modify: `docs/A0X_RESTART_HANDOFF.md`

**Interfaces:**
- Produces: mechanical rules preventing new parallel truths.
- Preserves: historical sections, hashes, and prior outcomes.

- [ ] **Step 1: Write RED architecture tests**

Tests require:

- every PairBinding schema projection is registered;
- no production or test helper independently formats `results/a0x/`;
- Hosted positive fixtures equal builder output;
- runner and adapter use the canonical reducer;
- the pair-domain module imports no I/O adapter;
- `a0x_contract` and `a0x_material_contract` no longer form a domain-level cycle;
- repository verification invokes the compatibility oracle.

- [ ] **Step 2: Run RED**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_architecture -v
```

- [ ] **Step 3: Remove the contract/material cycle without broad rewriting**

Move only pair-domain types and helpers to `a0x_pair.py`; keep compatibility re-exports. Move guard-launch cross-object checks to the adapter-side module that owns them. Do not split large modules solely to reduce line counts.

- [ ] **Step 4: Consolidate current documentation**

`docs/A0X_SIX_MODEL_CAMPAIGN.md` remains the canonical current scientific lifecycle. `docs/CURRENT_STATUS.md` and `docs/PERSISTENT_GOAL.txt` contain short pointers and the latest exact checkpoint only. Mark prior restart/handoff status blocks historical; do not rewrite their original hashes.

- [ ] **Step 5: Record engineering-log entry 39 and the corrective architecture**

Document the 24/24 failure, schema-only verifier gap, semantic fixture invalidity, duplicated state machine, canonical sources, and proof required before the next Gate A/B action.

- [ ] **Step 6: Run GREEN and documentation audit**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_architecture -v
rtk make docs-audit
```

- [ ] **Step 7: Commit**

```bash
rtk git add tests/test_a0x_architecture.py docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md docs/A0X_SIX_MODEL_CAMPAIGN.md docs/CURRENT_STATUS.md docs/PERSISTENT_GOAL.txt docs/A0X_RESTART_HANDOFF.md
rtk git commit -m "docs: establish A0X contract convergence rules"
```

---

### Task 7: Bind the correction into the frozen implementation

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `tests/test_a0x_freeze.py`
- Modify: `tests/test_a0x_frozen_package.py`

**Interfaces:**
- Consumes: every new or changed implementation file from Tasks 1–6.
- Produces: an implementation inventory that detects omission before regeneration.

- [ ] **Step 1: Write RED inventory tests**

Require exact inclusion of:

```text
src/latent_triz/a0x_pair.py
src/latent_triz/a0x_compatibility.py
src/latent_triz/a0x_gate_contract.py
src/latent_triz/a0x_schema_projection.py
scripts/a0x_compatibility_check.py
scripts/a0x_compile_pair_schemas.py
schemas/a0x-pair-binding.fragment.json
schemas/a0x-pair-projections.json
tests/test_a0x_pair_compatibility.py
tests/test_a0x_schema_projection.py
tests/test_a0x_architecture.py
```

- [ ] **Step 2: Run RED**

```bash
rtk env PYTHONPATH=src:. python3 -m unittest tests.test_a0x_freeze tests.test_a0x_frozen_package -v
```

Expected: stale implementation inventory, not a model/runtime error.

- [ ] **Step 3: Update the inventory source only**

Do not regenerate in this task. Assert stable sorted paths, uniqueness, existence, regular-file type, and absence of symlinks/hardlinks where the existing contract requires it.

- [ ] **Step 4: Commit the pre-regeneration implementation anchor**

```bash
rtk git add src/latent_triz/a0x_freeze.py tests/test_a0x_freeze.py tests/test_a0x_frozen_package.py
rtk git commit -m "chore: bind A0X convergence implementation"
```

Record exact HEAD/tree. This commit is the only allowed `implementation_source_head` for Task 8.

---

### Task 8: Regenerate target-free artifacts and prove closure

**Files:**
- Modify: `experiments/a0x-six-model/protected-a0-tree.json`
- Modify: `experiments/a0x-six-model/protected-a0r1-tree.json`
- Modify: `experiments/a0x-six-model/a0/implementation.json`
- Modify: `experiments/a0x-six-model/r1/implementation.json`
- Modify: `experiments/a0x-six-model/freeze/a0-freeze.json`
- Modify: `experiments/a0x-six-model/freeze/r1-freeze.json`
- Modify: 12 files under `experiments/a0x-six-model/approval-dossiers/`
- Modify: `results/a0x/preexecution/a0x-no-model-verification-receipt.json`
- Modify: canonical status/checkpoint documentation only where hashes change.

**Interfaces:**
- Consumes: exact clean implementation anchor from Task 7.
- Produces: two freezes, twelve approval-request dossiers, one no-model receipt, and an exact hash ledger.

- [ ] **Step 1: Verify the pre-regeneration stop boundary**

Run all focused tests and confirm the expected stale-freeze `NO-GO`. Any other failure blocks regeneration.

- [ ] **Step 2: Regenerate protected trees and selection**

```bash
rtk env PYTHONPATH=src:. python3 -m latent_triz.a0x_freeze --root . --write-protected-trees --write-a0-selection
```

- [ ] **Step 3: Regenerate freezes and dossiers from a recorded literal HEAD**

First run:

```bash
rtk git rev-parse HEAD
rtk git status --short --branch
```

Record the complete 40-character Task 7 HEAD in the checkpoint and copy that
literal value into the next command. Do not use an abbreviated hash, a branch
name, `HEAD`, or command substitution in the recorded regeneration argv.

```bash
rtk env PYTHONPATH=src:. python3 -m latent_triz.a0x_freeze --root . --freeze-all --prepare-dossiers --implementation-source-head TASK7_EXACT_40_CHARACTER_HEAD
```

`TASK7_EXACT_40_CHARACTER_HEAD` is an execution-plan token: replace it once
with the exact value printed and recorded immediately above before running the
command. Preserve the resulting literal argv in the task checkpoint.

Expected: exactly two freezes and twelve `approval_requested` dossiers; zero model loads, tokenizer construction, target reads, CCP, Docker, or network.

- [ ] **Step 4: Materialize the no-model receipt through the existing target-free tool**

Run exactly:

```bash
rtk env PYTHONPATH=src:. python3 scripts/a0x_materialize_no_model_receipt.py --root . --output results/a0x/preexecution/a0x-no-model-verification-receipt.json --replace-existing
```

The `--replace-existing` authority is limited to this future-facing canonical
receipt after the exact Task 7 anchor and target-free regeneration. Refuse any
other output path or pre-existing historical artifact.

- [ ] **Step 5: Run the complete deterministic ladder**

```bash
rtk env PYTHONPATH=src:. python3 scripts/a0x_compile_pair_schemas.py --check
rtk env PYTHONPATH=src:. python3 scripts/a0x_compatibility_check.py
rtk make a0x-no-model-verify
rtk make a0x-synthetic-verify
rtk make schema-cross-validate
rtk python3 scripts/repository_check.py
rtk make docs-audit
rtk git diff --check
```

- [ ] **Step 6: Run independent reviews**

One Terra review covers architecture, security boundaries, state semantics, and regeneration. One Luna review covers exact inventory, 24-case oracle, fixture provenance, schema projection parity, hash ledger, and documentation status. Findings P0–P2 block closure; P3 must be explicitly dispositioned.

- [ ] **Step 7: Commit regenerated closure**

```bash
rtk git add experiments/a0x-six-model/a0-selection-manifest.json experiments/a0x-six-model/protected-a0-tree.json experiments/a0x-six-model/protected-a0r1-tree.json experiments/a0x-six-model/a0/implementation.json experiments/a0x-six-model/r1/implementation.json experiments/a0x-six-model/freeze/a0-freeze.json experiments/a0x-six-model/freeze/r1-freeze.json experiments/a0x-six-model/approval-dossiers/a0/gpt2.json experiments/a0x-six-model/approval-dossiers/a0/gpt_neo_125m.json experiments/a0x-six-model/approval-dossiers/a0/qwen2_5_0_5b.json experiments/a0x-six-model/approval-dossiers/a0/qwen3_0_6b_base.json experiments/a0x-six-model/approval-dossiers/a0/smollm2_135m.json experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json experiments/a0x-six-model/approval-dossiers/r1/gpt2.json experiments/a0x-six-model/approval-dossiers/r1/gpt_neo_125m.json experiments/a0x-six-model/approval-dossiers/r1/qwen2_5_0_5b.json experiments/a0x-six-model/approval-dossiers/r1/qwen3_0_6b_base.json experiments/a0x-six-model/approval-dossiers/r1/smollm2_135m.json experiments/a0x-six-model/approval-dossiers/r1/smollm2_360m.json results/a0x/preexecution/a0x-no-model-verification-receipt.json docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md docs/A0X_SIX_MODEL_CAMPAIGN.md docs/A0X_RESTART_HANDOFF.md docs/CURRENT_STATUS.md docs/PERSISTENT_GOAL.txt
rtk git diff --cached --name-only
rtk git commit -m "chore: regenerate converged A0X contracts"
```

The cached-path list must equal the explicit allowlist above. If any additional
path appears, unstage only that path, investigate, and stop if it is not an
authorized future-facing artifact. Never stage a directory-wide `docs/`,
`results/`, or repository glob.

- [ ] **Step 8: Record final evidence and stop**

Report exact HEAD, tree, changed paths, two freeze SHA-256 values, twelve dossier SHA-256 values, no-model receipt SHA-256, compatibility result `24/24`, suite totals, review verdicts, and clean/dirty state.

Stop before network, GitHub publication, Hosted Gate A capture, Gate B/C, model/tokenizer construction, or target access.

---

## Plan self-review

- **Spec coverage:** root cause, canonical pair semantics, compiled schemas, real fixtures, Hosted semantic validation, state convergence, architecture fitness functions, documentation consolidation, frozen binding, regeneration, independent review, and stop boundary each have a task.
- **Plan-token scan:** no `TBD`, `TODO`, deferred handler, or unspecified test
  step remains. The single `TASK7_EXACT_40_CHARACTER_HEAD` token is defined by
  an immediately preceding read-only command and must become a recorded literal
  before execution.
- **Type consistency:** `derive_pair_output_path`, `compile_pair_projections`, `check_frozen_pair_compatibility`, `PairBinding`, `AttemptState`, `AttemptEvent`, and `reduce_attempt` have one spelling and one owner throughout.
- **Safety:** no step authorizes model, tokenizer, target, CCP, Docker, network, push, PR, merge, or publication.
- **Scientific boundary:** the plan changes engineering contracts only; it does not modify endpoints, statistics, target selection, model revisions, or claim language.
