# A0X Pair-Scoped Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a target-free, atomic, pair-scoped A0X package generator and
consumer path so the campaign can qualify one leg-model pair at a time.

**Architecture:** Keep the existing batch `freeze_a0x_campaign()` and its
twelve-dossier verifier historical and byte-compatible. Add an independent
`a0x-vertical-slice-v1` package under a source-head-qualified namespace. A
separate validator is the only path by which the future material executor can
accept its generated dossier.

**Tech Stack:** Python standard library, existing strict JSON/schema validator,
macOS `renameatx_np` exclusive publication seam, `unittest`.

**Spec:** `docs/A0X_VERTICAL_SLICE.md`

## Global Constraints

- Preserve every batch freeze and batch dossier byte-identically; do not modify
  `freeze_a0x_campaign()` semantics or the twelve-dossier inventory.
- New package selector is exactly one `Leg` and one registry model key.
- Generated package has exactly `protocol.json`, `implementation.json`,
  `freeze.json`, `approval-dossier.json`, and `slice-manifest.json`.
- Publicly exposed or user-supplied paths remain repository-relative, regular,
  non-symlink, non-hardlink, canonical, and fail-closed.
- Stage all five files under a private absent directory and publish with one
  exclusive no-overwrite rename; unsupported platform or primitive is refusal.
- No real GitHub/CLI network, Gate A/B/C, CCP/Docker, runtime installation,
  model/tokenizer/target access, scoring, push, PR, or merge.
- Do not regenerate tracked batch inventory, batch freezes, twelve dossiers, or
  no-model receipt. A later exact-head authorization is required for any real
  pair package generation.

---

### Task 1: Define pair-scoped document and publication primitives

**Files:**
- Create: `src/latent_triz/a0x_vertical_slice.py`
- Create: `schemas/a0x-vertical-slice-manifest.schema.json`
- Create: `tests/test_a0x_vertical_slice.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class VerticalSliceRequest:
    leg: Leg
    model_key: str
    implementation_source_head: str
    output_root: str

def generate_vertical_slice(root: str | Path, request: VerticalSliceRequest) -> dict[str, Any]: ...
def load_vertical_slice(root: str | Path, dossier_relative: str) -> dict[str, Any]: ...
```

`generate_vertical_slice` writes only under
`experiments/a0x-six-model/vertical-slices/<head>/<leg>/<model-key>/`. Its
receipt contains the five relative paths, their SHA-256 values, selected pair,
exact source head/tree, and zero-material counters. `load_vertical_slice`
validates the parent namespace, all five exact names, the manifest schema and
cross-hashes, the existing authorization-dossier schema, selected registry
card, and dossier/freeze/source-head bindings.

- [ ] **Step 1: Write failing document tests**

```python
def test_pair_package_contains_only_one_selected_leg_and_model(self):
    receipt = generate_vertical_slice(ROOT, request("a0", "smollm2_360m"))
    self.assertEqual(5, len(receipt["written"]))
    self.assertEqual("a0", receipt["pair"]["leg"])
    self.assertEqual("smollm2_360m", receipt["pair"]["model_key"])

def test_selector_rejects_unknown_model_or_noncanonical_head(self):
    with self.assertRaises(A0XVerticalSliceError):
        generate_vertical_slice(ROOT, request("a0", "unknown"))
```

- [ ] **Step 2: Run the new test module to prove RED**

Run: `rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_a0x_vertical_slice -v`

Expected: FAIL because `a0x_vertical_slice` and the manifest schema do not yet
exist.

- [ ] **Step 3: Implement canonical builders and strict selector validation**

Use `_LEG_SOURCES`, `_load_model_cards`, `_leg_identity`, `_file_binding`,
`PairBinding`, `compute_dense_bound`, and `APPROVAL_DOSSIER_PROFILE` as
read-only inputs. Copy the selected leg's protocol/implementation values by
value into the new namespace, bind their raw hashes into `freeze.json`, then
build one dossier. Reject a non-40-hex head, any missing/duplicate registry
model key, a selector that disagrees with card metadata, and a non-absent output
root. The manifest's `members` map is exactly the four non-manifest files; it
does not self-hash.

- [ ] **Step 4: Implement private-stage exclusive publication**

Create a private sibling staging directory with mode `0700`, write each member
with `O_CREAT|O_EXCL|O_NOFOLLOW`, fsync each file and directory, re-read exact
bytes/hashes, then publish the directory only through a private Darwin
`renameatx_np(parent_fd, stage, parent_fd, destination,
RENAME_EXCL|RENAME_NOFOLLOW_ANY)` seam. Hold the parent directory descriptor;
reject unsupported host/primitive, destination existence, link/path drift, or
post-publication ownership loss. On any pre-publication failure remove only the
held owned staging inode. Never fall back to `Path.rename`, `os.replace`, or a
full-copy path.

- [ ] **Step 5: Add negative and mutation tests**

Cover occupied destination; output-root traversal; symlink/hardlink/nonregular
member; duplicate/extra/missing member; wrong model revision; wrong freeze hash;
manifest hash mutation; staging write failure; `EEXIST`; primitive absence;
no-op publisher; post-publish ownership loss; and byte-determinism in two fresh
temporary roots. Assert the historical `approval-dossiers/` and `freeze/`
trees are byte-identical before and after every case.

- [ ] **Step 6: Run focused tests and commit**

Run: `rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_a0x_vertical_slice tests.test_a0x_freeze tests.test_a0x_schemas -v`

Expected: PASS with zero model/tokenizer/target/CCP/network use.

```bash
rtk git add src/latent_triz/a0x_vertical_slice.py schemas/a0x-vertical-slice-manifest.schema.json tests/test_a0x_vertical_slice.py
rtk git commit -m "feat(a0x): add pair-scoped vertical package"
```

### Task 2: Add a fixed pair-scoped material consumer

**Files:**
- Create: `scripts/a0x_vertical_material.py`
- Modify: `src/latent_triz/a0x_ccp_executor.py`
- Modify: `src/latent_triz/a0x_runner.py`
- Create: `tests/test_a0x_vertical_material.py`
- Modify: `tests/test_a0x_ccp_executor.py`

**Interfaces:**

```python
def vertical_slice_dossier_path(
    implementation_source_head: str, leg: Leg, model_key: str,
) -> str: ...

def launch_vertical_slice_dossier(
    *, repository_root: Path, implementation_source_head: str,
    leg: str, model_key: str, source_head_probe: Callable[[], str],
) -> dict[str, Any]: ...
```

The CLI accepts `--implementation-source-head`, `--leg`, and `--model-key`;
it does not accept an arbitrary dossier path. The executor derives the only
allowed path, calls `load_vertical_slice`, requires current source head equals
the package head, then delegates to the existing one-shot material state
machine. The legacy `launch_fixed_dossier()` remains restricted to the exact
historical twelve paths.

- [ ] **Step 1: Write failing consumer tests**

```python
def test_vertical_launcher_derives_not_accepts_dossier_path(self):
    with self.assertRaises(A0XCcpExecutorError):
        launch_vertical_slice_dossier(
            repository_root=self.root, implementation_source_head=HEAD,
            leg="a0", model_key="smollm2_360m", source_head_probe=lambda: HEAD,
        )

def test_batch_launcher_still_refuses_vertical_path(self):
    with self.assertRaises(A0XCcpExecutorError):
        launch_fixed_dossier(repository_root=self.root, fixed_dossier=VERTICAL_DOSSIER, source_head_probe=lambda: HEAD)
```

The first test uses a synthetic valid pair package and spies on the child guard;
assert no guard starts for source/head/hash/schema mismatch.

- [ ] **Step 2: Run target tests to prove RED**

Run: `rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_a0x_vertical_material tests.test_a0x_ccp_executor -v`

Expected: FAIL because no pair-scoped consumer exists.

- [ ] **Step 3: Implement derived-path launcher and shell-free CLI**

Derive the path from the three selectors; reject a current source mismatch,
manifest/dossier inconsistency, unselected pair, stale package, missing regular
file, or any arbitrary path injection before reserving a claim or invoking a
guard. Reuse the existing `launch_fixed_dossier` internals only after a common
validated-dossier object has been established; do not weaken the historical
twelve-path assertion. The CLI has fixed minimal environment and no shell.

- [ ] **Step 4: Add mutation and no-material regressions**

Prove cross-model and cross-leg substitution, changed source head, changed
freeze/dossier/manifest bytes, symlink/hardlink paths, extra manifest members,
and malformed selector all refuse with zero guard calls and zero model/tokenizer
or sealed-target access.

- [ ] **Step 5: Run focused consumer suites and commit**

Run: `rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_a0x_vertical_material tests.test_a0x_ccp_executor tests.test_a0x_runner tests.test_a0x_contract -v`

Expected: PASS; no CCP invocation occurs because all guard calls are injected.

```bash
rtk git add scripts/a0x_vertical_material.py src/latent_triz/a0x_ccp_executor.py src/latent_triz/a0x_runner.py tests/test_a0x_vertical_material.py tests/test_a0x_ccp_executor.py
rtk git commit -m "feat(a0x): bind vertical material launcher"
```

### Task 3: Bind the trusted surface and document operational sequence

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `tests/test_a0x_freeze.py`
- Modify: `src/latent_triz/a0x_schema_projection.py`
- Modify: `tests/test_a0x_schema_projection.py`
- Modify: `Makefile`
- Modify: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify: `docs/A0X_GATE_B_OPERATOR_HARDENING.md`
- Modify: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`
- Modify: `docs/PERSISTENT_GOAL.txt`

- [ ] **Step 1: Write failing inventory and aggregate tests**

Require the vertical library, CLI, test module, and manifest schema in
`_IMPLEMENTATION_PATHS`; require the new test module exactly once in
`a0x-synthetic-verify`; require `A0X_SCHEMA_COUNT` to equal the actual schema
set and include `a0x-vertical-slice-manifest.schema.json`.

- [ ] **Step 2: Implement only the required registrations**

Keep batch generation and its 12-dossier tests unchanged. Add a no-material
`a0x-vertical-slice-verify` Make target for the vertical tests and add a
selector-derived `a0x-vertical-material-a0-smollm2-360m` target that invokes
the new CLI with a computed current `HEAD`; it is a future launcher, not an
authorized execution command.

- [ ] **Step 3: Update canonical documentation**

Mark all old batch generated artifacts historical/stale. Link
`docs/A0X_VERTICAL_SLICE.md`; state P0 package generation, Gate A, Gate B,
Gate C, result verification, and publication as distinct authorization gates.
Document that A0-R1 begins only after the A0 terminal report and no scientific
rule may change between legs.

- [ ] **Step 4: Run target-free validation without generation**

Run:

```bash
rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_a0x_vertical_slice tests.test_a0x_vertical_material tests.test_a0x_freeze tests.test_a0x_schema_projection -v
rtk make a0x-vertical-slice-verify
rtk make a0x-synthetic-verify
rtk git diff --check
```

Expected: synthetic checks pass except for the explicitly stale batch
freeze/package check. Do not run `a0x-no-model-verify` as a PASS and do not
write freeze/dossier artifacts.

- [ ] **Step 5: Commit and record regeneration boundary**

```bash
rtk git add src/latent_triz/a0x_freeze.py tests/test_a0x_freeze.py src/latent_triz/a0x_schema_projection.py tests/test_a0x_schema_projection.py Makefile docs/A0X_SIX_MODEL_CAMPAIGN.md docs/A0X_GATE_B_OPERATOR_HARDENING.md docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md docs/PERSISTENT_GOAL.txt
rtk git commit -m "docs(a0x): stage vertical SmolLM2 slice"
```

### Task 4: Review and request the first pair-package authorization

**Files:**
- Create: `docs/qualification/a0x-vertical-slice-local-review-<head>.md`
- Create: `artifacts/checkpoints/A0X_VERTICAL_SLICE_RESTART_<date>.md`

- [ ] **Step 1: Perform independent target-free review**

Verify exact clean HEAD/tree, source diff, schema validation, selector tests,
batch-artifact byte identity, zero-material spies, and docs boundaries. Record
only local evidence; do not create any generated pair package.

- [ ] **Step 2: Commit the checkpoint and review**

```bash
rtk git add docs/qualification artifacts/checkpoints
rtk git commit -m "docs(a0x): checkpoint vertical slice readiness"
```

- [ ] **Step 3: Stop for exact authorization**

Report the exact clean HEAD/tree, the raw source/schema/test hashes that become
package inputs, and the command that will generate only
`A0 / smollm2_360m`. Request a separate authorization for exactly one
target-free P0 generation. Do not run it, push, create a PR, or start Gate A,
Gate B, or Gate C.

## Plan self-review

- Spec coverage: Tasks 1–2 implement pair-scoped atomic package and derived
  consumer; Task 3 binds code/docs; Task 4 creates a restartable exact-head
  approval boundary.
- Historical isolation: every task preserves batch APIs/paths and tests their
  byte identity.
- Security: Task 1 owns exclusive staging; Task 2 disallows arbitrary dossier
  paths; Task 3 verifies registration and documentation.
- No placeholders: all generator, consumer, test, validation, and stop actions
  have named files and commands.
