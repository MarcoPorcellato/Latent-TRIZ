# A0X Vertical Gate-Chain Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one protected-main A0X source support the exact target-free chain Hosted Gate A → P0 v2 → Gate B v2 → Gate C pre-material validation without self-referential commit identity.

**Architecture:** Preserve all v1 and batch behavior as historical. Add a future-only local v2 envelope under ignored `.a0x-runtime`, atomically containing the five-member package and an external commitment receipt. Gate B and Gate C consume one typed binding to the same package, source `HEAD/tree`, raw commitment, dossier, and pair.

**Tech Stack:** Python 3.11+, `unittest`, JSON Schema, Git, descriptor-relative POSIX file access, Darwin exclusive rename, existing A0X canonical JSON and validation helpers.

**Spec:** `docs/superpowers/specs/2026-09-05-a0x-vertical-gate-chain-convergence-design.md`

## Global Constraints

- Work only in the isolated clone; preserve the dirty primary checkout.
- All shell commands begin with `rtk`.
- No network, GitHub mutation, CCP, Docker, Gate B/C material execution, model load, tokenizer construction, target read, mapping-private access, scoring, publication, or retry.
- Preserve every v1 package, batch dossier, freeze, receipt, report, and published artifact byte-identically.
- New v2 code has no fallback to v1 or batch material routes.
- Keep the exact live checkout clean at one protected-main `HEAD/tree`; ignored v2 runtime files receive independent path, inode, size, and hash validation.
- Use TDD: observe each new behavior fail for the intended reason before production code.
- Use one atomic envelope: `package/` with exactly five files plus `p0-commitment.json`; publish the absent final envelope by one exclusive rename.
- Regenerate implementation-bound inventories, freezes, and dossiers only after the implementation commit.

---

### Task 1: P0 v2 atomic package and external commitment

**Files:**
- Modify: `src/latent_triz/a0x_vertical_slice.py`
- Modify: `src/latent_triz/a0x_contract.py`
- Create: `schemas/a0x-vertical-slice-manifest-v2.schema.json`
- Create: `schemas/a0x-vertical-package-commitment-v2.schema.json`
- Create: `tests/test_a0x_vertical_slice_v2.py`
- Modify: `tests/test_a0x_contract.py`
- Modify: `tests/test_a0x_schemas.py`

**Interfaces:**
- Consumes: `Leg`, `PairBinding`, v1 document builders and descriptor-relative publication primitives.
- Produces: `VerticalRuntimePackageRequest`, `VerticalPackageBinding`, `generate_vertical_runtime_package()`, `load_vertical_runtime_package()` and canonical package commitment validation.

- [ ] **Step 1: Write failing contract and package tests**

Create tests that import the missing v2 types and establish the exact envelope:

```python
request = VerticalRuntimePackageRequest(
    qualified_source_head=head,
    qualified_source_tree=tree,
    leg=Leg.A0,
    model_key="smollm2_360m",
    output_root=f".a0x-runtime/p0/v2/{head}/{tree}/a0/smollm2_360m",
    authorization_id="p0-auth-test-01",
    attempt_id="p0-attempt-test-01",
)
receipt = generate_vertical_runtime_package(root, request)
self.assertEqual(git_head(root), head)
self.assertEqual(git_tree(root), tree)
self.assertEqual(git_status(root), "")
self.assertEqual(set(envelope.iterdir()), {envelope / "package", envelope / "p0-commitment.json"})
self.assertEqual({p.name for p in package.iterdir()}, set(V2_MEMBER_NAMES))
```

Add mutations for reordered members, changed byte/size/hash, wrong source tree,
occupied envelope, symlink, hardlink, extra/missing member, v1/v2 substitution,
and ownership loss. Assert stable v2 refusal codes.

- [ ] **Step 2: Run the tests and observe RED**

Run:

```text
rtk python3 -m unittest tests.test_a0x_vertical_slice_v2 tests.test_a0x_contract tests.test_a0x_schemas -v
```

Expected: import/schema failures because v2 APIs and profiles do not exist.

- [ ] **Step 3: Implement the pure commitment contract**

Add exact constants and pure helpers:

```python
VERTICAL_PACKAGE_COMMITMENT_PROFILE = "a0x-vertical-package-commitment-v2"
V2_MEMBER_NAMES = (
    "protocol.json", "implementation.json", "freeze.json",
    "approval-dossier.json", "slice-manifest.json",
)

def build_vertical_package_commitment(
    *, qualified_source: Mapping[str, str], pair: PairBinding,
    members: Sequence[Mapping[str, object]], generator: Mapping[str, str],
    authorization_id: str, attempt_id: str,
) -> dict[str, object]:
    projection = {
        "profile": VERTICAL_PACKAGE_COMMITMENT_PROFILE,
        "qualified_source": dict(qualified_source),
        "pair_binding": pair.as_mapping(),
        "members": [dict(member) for member in members],
        "generator": dict(generator),
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
    }
    projection["package_commitment_sha256"] = domain_sha256(projection)
    return validate_vertical_package_commitment(projection)

def validate_vertical_package_commitment(value: Mapping[str, object]) -> dict[str, object]:
    document = strict_json_object(canonical_json_bytes(value))
    names = tuple(member["name"] for member in document["members"])
    if names != V2_MEMBER_NAMES:
        raise A0XContractError("vertical package member order is invalid")
    return document
```

Require exact keys, fixed member order, lowercase hashes, canonical source
`refs/heads/main`, exact pair projection, generator identity, authorization ID,
attempt ID, and a domain-separated `package_commitment_sha256`. The document
must not contain its own raw hash.

- [ ] **Step 4: Implement atomic envelope generation and loading**

Add the spec dataclasses with these mandatory binding fields:

```python
@dataclass(frozen=True)
class VerticalPackageBinding:
    envelope_path: str
    package_path: str
    commitment_path: str
    commitment_raw_sha256: str
    package_commitment_sha256: str
    dossier_path: str
    dossier_sha256: str
    qualified_source_head: str
    qualified_source_tree: str
    leg: Leg
    model_key: str
    model_revision: str
    pair_binding: PairBinding
```

Build `package/` and `p0-commitment.json` in one private sibling stage, fsync
every file and both directories, then rename the whole envelope exclusively.
Load descriptor-relatively; require exact entries, regular files, `st_nlink ==
1`, canonical bytes, unchanged inode/size/hash, and a recomputed commitment.
Leave v1 functions unchanged.

- [ ] **Step 5: Run focused tests GREEN and commit**

```text
rtk python3 -m unittest tests.test_a0x_vertical_slice_v2 tests.test_a0x_vertical_slice tests.test_a0x_contract tests.test_a0x_schemas -v
rtk git add src/latent_triz/a0x_vertical_slice.py src/latent_triz/a0x_contract.py schemas/a0x-vertical-slice-manifest-v2.schema.json schemas/a0x-vertical-package-commitment-v2.schema.json tests/test_a0x_vertical_slice_v2.py tests/test_a0x_contract.py tests/test_a0x_schemas.py
rtk git commit -m "feat: add A0X vertical runtime package v2"
```

Expected: all focused tests PASS; only named files enter the commit.

### Task 2: Vertical-only Gate B binding

**Files:**
- Modify: `src/latent_triz/a0x_runtime_bundle.py`
- Modify: `src/latent_triz/a0x_gate_contract.py`
- Modify: `scripts/a0x_prepare_runtime.py`
- Create: `schemas/a0x-gate-b-authorization-v2.schema.json`
- Create: `tests/test_a0x_vertical_runtime_bundle.py`
- Modify: `tests/test_a0x_runtime_bundle.py`

**Interfaces:**
- Consumes: Task 1 `VerticalPackageBinding` and `load_vertical_runtime_package()`.
- Produces: `VerticalRuntimePreparationRequest`, `preflight_vertical_runtime_bundle()` and `prepare_vertical_runtime_bundle()`.

- [ ] **Step 1: Write failing Gate B tests**

Use the real Task 1 package with injected hosted verifier/readiness probes:

```python
request = VerticalRuntimePreparationRequest(
    package_binding=binding,
    gate_b_authorization=authorization_path,
    verifier_executable=verifier,
    verifier_policy=policy,
    ccp_executable=ccp,
    python_executable=python,
    authorization_id="gate-b-auth-test-01",
    attempt_id="gate-b-attempt-test-01",
)
result = preflight_vertical_runtime_bundle(root, request, **inert_dependencies)
self.assertEqual(result["qualified_source"], {"head": head, "tree": tree})
self.assertEqual(result["package_commitment_sha256"], binding.package_commitment_sha256)
self.assertEqual(result["dossier_sha256"], binding.dossier_sha256)
```

Prove batch/v1 substitution, changed commitment/dossier/pair/source/tree,
Hosted Gate A mismatch, dirty checkout, occupied output, and missing typed
binding refuse before verifier or readiness counters increment.

- [ ] **Step 2: Run and observe RED**

```text
rtk python3 -m unittest tests.test_a0x_vertical_runtime_bundle -v
```

Expected: imports fail because the v2 Gate B entry points do not exist.

- [ ] **Step 3: Implement the v2 Gate B entry points**

Keep `RuntimePreparationRequest` and batch functions historical. Add:

```python
@dataclass(frozen=True)
class VerticalRuntimePreparationRequest:
    package_binding: VerticalPackageBinding
    gate_b_authorization: Path
    verifier_executable: Path
    verifier_policy: Path
    ccp_executable: Path
    python_executable: Path
    authorization_id: str
    attempt_id: str

def preflight_vertical_runtime_bundle(
    root: Path, request: VerticalRuntimePreparationRequest, **probes: object,
) -> dict[str, object]:
    return _build_vertical_runtime_bundle(root, request, write_outputs=False, **probes)

def prepare_vertical_runtime_bundle(
    root: Path, request: VerticalRuntimePreparationRequest, **probes: object,
) -> dict[str, object]:
    return _build_vertical_runtime_bundle(root, request, write_outputs=True, **probes)
```

Validate the package before shared bundle construction. Every v2 output binds
the exact source head/tree, raw commitment hash, package commitment, dossier
path/hash, and pair. The v2 authorization schema rejects v1/batch profiles.
Refactor shared document construction only after each version-specific
selector has passed.

- [ ] **Step 4: Add an explicit CLI mode**

Add mutually exclusive `--fixed-dossier` and `--vertical-commitment` modes.
The v2 path derives all remaining package paths from the commitment document;
no arbitrary dossier path is accepted. `--preflight` remains no-write.

- [ ] **Step 5: Run focused tests GREEN and commit**

```text
rtk python3 -m unittest tests.test_a0x_vertical_runtime_bundle tests.test_a0x_runtime_bundle -v
rtk git add src/latent_triz/a0x_runtime_bundle.py src/latent_triz/a0x_gate_contract.py scripts/a0x_prepare_runtime.py schemas/a0x-gate-b-authorization-v2.schema.json tests/test_a0x_vertical_runtime_bundle.py tests/test_a0x_runtime_bundle.py
rtk git commit -m "feat: bind Gate B to vertical package v2"
```

### Task 3: Vertical-only Gate C pre-material validation

**Files:**
- Modify: `src/latent_triz/a0x_ccp_executor.py`
- Modify: `src/latent_triz/a0x_runner.py`
- Modify: `src/latent_triz/a0x_material_contract.py`
- Modify: `scripts/a0x_vertical_material.py`
- Create: `schemas/a0x-execution-authorization-v4.schema.json`
- Modify: `tests/test_a0x_ccp_executor.py`
- Modify: `tests/test_a0x_vertical_material.py`

**Interfaces:**
- Consumes: Task 1 package binding and Task 2 Gate B output bindings.
- Produces: `launch_vertical_runtime_package()` and v2 execution authorization validation.

- [ ] **Step 1: Write failing Gate C tests**

```python
result = launch_vertical_runtime_package(
    repository_root=root,
    package_binding=binding,
    source_state_probe=lambda: (head, tree, True),
    process_executor=inert_executor,
    guard_preflight_producer=inert_preflight,
)
self.assertEqual(inert_executor.calls, 1)
```

Add refusal tests for changed package after Gate B, wrong head/tree, dirty
source, wrong pair/revision, changed Gate B output hash, v1/batch substitution,
and more than one guard attempt. Each refusal must occur before guard count
changes.

- [ ] **Step 2: Run and observe RED**

```text
rtk python3 -m unittest tests.test_a0x_ccp_executor tests.test_a0x_vertical_material -v
```

Expected: missing v2 launcher/profile failures.

- [ ] **Step 3: Implement v2 Gate C validation**

Add a distinct entry point:

```python
def launch_vertical_runtime_package(
    *, repository_root: str | Path,
    package_binding: VerticalPackageBinding,
    source_state_probe: Callable[[], tuple[str, str, bool]],
    process_executor: ProcessExecutor | None = None,
    guard_preflight_producer: GuardPreflightProducer | None = None,
) -> dict[str, object]:
    return _launch_validated_vertical_v2(
        repository_root=repository_root,
        package_binding=package_binding,
        source_state_probe=source_state_probe,
        process_executor=process_executor,
        guard_preflight_producer=guard_preflight_producer,
    )
```

Reload the package and commitment, require clean exact source `HEAD/tree`, and
verify Gate B authorization plus every readiness/descriptor/authorization/
mapping hash before claim or guard. Keep the v1 launcher unchanged and never
dispatch v2 through its optional legacy arguments.

- [ ] **Step 4: Update the vertical CLI and schema**

Require the derived commitment path and exact raw SHA-256. Remove future v2
meaning from `--implementation-source-head`; retain that flag only for the
explicit historical v1 path. Add v4 schema/profile rather than changing v3
semantics.

- [ ] **Step 5: Run focused tests GREEN and commit**

```text
rtk python3 -m unittest tests.test_a0x_ccp_executor tests.test_a0x_vertical_material tests.test_a0x_material_contract -v
rtk git add src/latent_triz/a0x_ccp_executor.py src/latent_triz/a0x_runner.py src/latent_triz/a0x_material_contract.py scripts/a0x_vertical_material.py schemas/a0x-execution-authorization-v4.schema.json tests/test_a0x_ccp_executor.py tests/test_a0x_vertical_material.py
rtk git commit -m "feat: validate vertical package v2 at Gate C"
```

### Task 4: Real-Git full-chain proof and mutation matrix

**Files:**
- Create: `tests/test_a0x_vertical_gate_chain_v2.py`
- Modify: Task 1–3 production files only for defects exposed by this test.

**Interfaces:**
- Consumes: all v2 interfaces from Tasks 1–3.
- Produces: one non-mocked Git/source/package chain proof with injected external capabilities only.

- [ ] **Step 1: Write the full-chain test and observe RED**

Create a disposable repository with a real commit `H/T`, generated `.gitignore`,
the required tracked fixtures, and the production modules copied from the
candidate. Run real P0 generation/loading, real Gate B static document
construction, and real Gate C pre-material validation. Inject only the hosted
verifier, readiness producer, version probe, and inert guard.

```python
self.assertEqual(head_after, head_before)
self.assertEqual(tree_after, tree_before)
self.assertEqual(status_after, "")
self.assertEqual(capabilities, {
    "guard": 1, "model": 0, "tokenizer": 0, "target": 0,
    "network": 0, "ccp": 0, "docker": 0,
})
```

Run:

```text
rtk python3 -m unittest tests.test_a0x_vertical_gate_chain_v2 -v
```

Expected: the first missing cross-boundary binding or validation mismatch
fails before the inert guard.

- [ ] **Step 2: Apply minimal fixes and reach GREEN**

Fix only defects demonstrated by the real chain. Do not add alternate selectors
or fallback routes.

- [ ] **Step 3: Complete the mutation matrix**

Subtests mutate member bytes/order/type/link count, commitment, dossier, pair,
source, hosted evidence, Gate B outputs, and the package between Gate B/C.
Assert verifier/readiness/guard counters remain zero for every pre-boundary
refusal.

- [ ] **Step 4: Run focused and synthetic aggregates, then commit**

```text
rtk python3 -m unittest tests.test_a0x_vertical_gate_chain_v2 -v
rtk make a0x-synthetic-verify
rtk git add tests/test_a0x_vertical_gate_chain_v2.py src/latent_triz/a0x_vertical_slice.py src/latent_triz/a0x_runtime_bundle.py src/latent_triz/a0x_ccp_executor.py
rtk git commit -m "test: prove A0X vertical gate chain v2"
```

### Task 5: Inventory, derived artifacts, and canonical documentation

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: implementation inventories, protected trees, freezes, twelve dossiers, and no-model receipt selected by the existing generator.
- Modify: `docs/A0X_VERTICAL_SLICE.md`
- Modify: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify: `docs/A0X_GATE_B_OPERATOR_HARDENING.md`
- Modify: `docs/A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md`
- Modify: `docs/CURRENT_STATUS.md`
- Modify: `docs/PERSISTENT_GOAL.txt`
- Modify: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`

**Interfaces:**
- Consumes: stable Tasks 1–4 implementation commit.
- Produces: current inventory/freeze/dossier bindings and one canonical operator route.

- [ ] **Step 1: Record historical protected-path hashes**

Hash all existing v1 vertical packages, historical receipts, result reports,
and batch artifacts before regeneration. The allowlist distinguishes generated
current artifacts from protected historical evidence.

- [ ] **Step 2: Add every new v2 implementation path to the inventory**

Update `_IMPLEMENTATION_PATHS` with the exact new schemas, source files,
scripts, and tests. Run the stale-freeze check and require its expected NO-GO
before regeneration.

- [ ] **Step 3: Regenerate target-free derived artifacts**

```text
rtk python3 -m latent_triz.a0x_freeze --root . --write-protected-trees --write-a0-selection
rtk python3 -m latent_triz.a0x_freeze --root . --freeze-all --prepare-dossiers --implementation-source-head "$(rtk git rev-parse HEAD)"
```

Confirm exactly two freezes and twelve dossiers. Do not generate a live P0 v2
runtime package.

- [ ] **Step 4: Reconcile documentation**

Declare one current route:

```text
Hosted Gate A -> capture -> P0 v2 -> Gate B v2 -> Gate C v2 -> verification
```

Label CCP/Matrix Gate A, batch dossiers, and tracked v1 packages historical.
Record the defect, correction, residual same-user mutation assumption, exact
implementation source head, and next authorization boundary.

- [ ] **Step 5: Verify protected historical bytes and commit**

```text
rtk make a0x-no-model-verify
rtk make docs-audit
rtk git diff --check
rtk git add src/latent_triz/a0x_freeze.py experiments docs schemas tests scripts src
rtk git commit -m "docs: bind A0X vertical gate chain v2"
```

Reject the commit if any historical protected byte changed.

### Task 6: Complete target-free verification and independent review

**Files:**
- Create: `.superpowers/sdd/2026-09-05-a0x-vertical-gate-chain-convergence/progress.md` (ignored execution ledger)
- Update: `artifacts/checkpoints/` only if the repository's current checkpoint convention requires a tracked restart record.

**Interfaces:**
- Consumes: all implementation and generated artifacts.
- Produces: exact local closure evidence and the next remote/material stop boundary.

- [ ] **Step 1: Run the complete deterministic ladder**

```text
rtk python3 -m unittest tests.test_a0x_vertical_slice_v2 tests.test_a0x_vertical_runtime_bundle tests.test_a0x_vertical_gate_chain_v2 tests.test_a0x_runtime_bundle tests.test_a0x_vertical_material tests.test_a0x_ccp_executor -v
rtk make a0x-no-model-verify
rtk make a0x-synthetic-verify
rtk python3 scripts/schema_cross_validate.py
rtk python3 scripts/repository_check.py
rtk python3 -m unittest -v
rtk make docs-audit
rtk git diff --check
```

- [ ] **Step 2: Verify exact closure facts**

Require a clean checkout, record complete HEAD/tree, and hash the spec, plan,
new schemas, implementation inventories, freezes, dossiers, and checkpoint.
Recompute the historical protected manifest and require byte equality.

- [ ] **Step 3: Obtain independent reviews**

Luna reviews mutation coverage and documentation consistency. Sol reviews
source/package identity, same-user mutation handling, atomic publication, and
Gate B/C authorization boundaries. Address findings with focused TDD and
repeat the affected verification.

- [ ] **Step 4: Stop before remote or material work**

Report exact local HEAD/tree, commits, hashes, test counts, reviews, and dirty
state. Request separate authorization for push/PR. Even after merge, Hosted
Gate A capture, P0 v2, Gate B, and Gate C each require later exact
authorizations.
