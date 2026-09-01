# A0X Hosted Gate A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace A0X's local CCP repository-qualification gate with exact-main GitHub-hosted signed evidence while preserving offline Gate B verification, the unchanged local CCP Gate C coordinator, historical evidence, and every material stop boundary.

**Architecture:** A protected-main `push` workflow runs seven target-free lanes and attests one canonical manifest. Gate B validates four immutable hosted inputs with one hash-bound offline GitHub CLI invocation, writes a fifth verification receipt, and only then prepares the existing runtime documents. Gate C remains local and rehashes all five Gate A files while independently enforcing the exact CCP identity and guard envelope.

**Tech Stack:** Python 3.11/3.12, `unittest`, JSON Schema Draft 2020-12, GitHub Actions, GitHub Artifact Attestations, GitHub CLI `gh attestation verify`, Sigstore bundles, existing A0X freeze/runtime code.

**Spec:** `docs/superpowers/specs/2026-08-31-a0x-hosted-gate-a-design.md`

## Global Constraints

- Start from specification commit `636338042d4ca5bf74e56ae291897a1dc11a7689`, tree `59b4d6a1f08b00c71687a73e0d0cedbcc4b79730`, unless a reviewed integration commit is explicitly selected first.
- No task in this plan may access a model, construct a material tokenizer, read a sealed target, run scientific scoring, or invoke CCP heavy work. Only Task 12 may publish remotely, and only after a separate exact authorization.
- Preserve all historical `ccp-evidence/**` branches, CCP receipts, result packages, and A0X material artifacts byte-identical.
- New A0X dossiers accept only provider `github-hosted-attestation-v1`; historical profile `a0x-qualification-evidence-v1` remains read-only and explicit.
- Hosted Gate A has exactly seven lanes: repository and schema checks on Python 3.11 and 3.12, A0X no-model, A0X synthetic, and documentation audit.
- Workflow trigger is only `push` to `main`; `GITHUB_RUN_ATTEMPT` must equal `1`; no rerun may qualify.
- Workflow-wide permissions are `{}`. Lane jobs receive `contents: read`; only the aggregate attestation job additionally receives `id-token: write` and `attestations: write`.
- Pin external actions to these complete reviewed commits: `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (v7.0.1), `actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405` (v6.2.0), `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` (v7.0.1), and `actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d` (v4.2.1).
- The manifest, attestation bundle, trusted root, transport record, and Gate B receipt have hard ceilings of 32 KiB, 1 MiB, 2 MiB, 16 KiB, and 32 KiB respectively.
- Canonical JSON is UTF-8, sorted-key, compact, finite, duplicate-free, unknown-field-free, and terminated by one newline. Raw byte hashes are never hashes of reparsed objects.
- The Gate B authorization binds four existing input hashes, verifier identity/policy, and output path. It cannot pre-bind the not-yet-created verification receipt hash.
- Gate C requires five independent regular files with link count one and rehashes them before claim and immediately before `guard exec`.
- GitHub provenance is a source/workflow integrity fact, not proof of scientific validity, branch-protection non-bypass, or a SLSA level.
- Every shell command in this plan is issued through `rtk`. Any live network, GitHub mutation, Gate B preparation, or Gate C action remains separately authorized.

---

## File and Responsibility Map

**Create**

- `.github/workflows/a0x-hosted-gate-a.yml` — exact-main seven-lane workflow and single attested aggregate.
- `.github/a0x-hosted-gate-a-actions.json` — canonical allowlist of the four full action pins.
- `.github/a0x-hosted-gate-a-lanes.json` — canonical seven-lane IDs, interpreter, and shell-free command declarations.
- `src/latent_triz/a0x_hosted_gate_a.py` — canonical lane/manifest parsing, building, size limits, and refusal codes.
- `src/latent_triz/a0x_hosted_verifier.py` — pure offline evidence validation and injected GitHub CLI verifier boundary.
- `scripts/a0x_hosted_gate_a.py` — workflow-facing lane and aggregate CLI.
- `scripts/a0x_verify_hosted_gate_a.py` — Gate B verifier CLI; writes only one overwrite-refusing receipt.
- `schemas/a0x-hosted-gate-a-lane-receipt.schema.json` — strict lane receipt.
- `schemas/a0x-hosted-gate-a-evidence.schema.json` — strict aggregate manifest.
- `schemas/a0x-hosted-gate-a-transport.schema.json` — strict GitHub API correlation record.
- `schemas/a0x-hosted-gate-a-verifier-policy.schema.json` — exact frozen verifier policy.
- `schemas/a0x-hosted-gate-a-verification-receipt.schema.json` — strict post-verification receipt.
- `schemas/a0x-gate-b-authorization.schema.json` — four-input, one-output-path operator authorization.
- `schemas/a0x-execution-authorization-v3.schema.json` — current hosted-evidence authorization; the existing v2 schema remains the legacy verifier contract.
- `scripts/a0x_materialize_no_model_receipt.py` — deterministic, explicit, overwrite-controlled no-model receipt writer.
- `tests/test_a0x_hosted_gate_a.py` — canonical builder/parser/schema tests.
- `tests/test_a0x_hosted_gate_a_workflow.py` — workflow trigger, permission, pin, lane, and aggregate policy.
- `tests/test_a0x_hosted_verifier.py` — synthetic verifier and mutation matrix.
- `tests/fixtures/a0x/hosted-gate-a/` — inert canonical positive and signed-valid/wrong-policy adapter fixtures.
- `docs/A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md` — capture, offline verification, refusal, retention, and acceptance procedure.

**Modify**

- `requirements-schema.in` and `requirements-schema.lock` — complete hash-locked Python 3.11/3.12 schema and safe-YAML environment.
- `schemas/a0x-material-execution-contract.schema.json` and `experiments/a0x-six-model/material-execution-contract.json` — add hosted Gate A policy; keep CCP Gate C block unchanged.
- `schemas/a0x-qualification-evidence.schema.json` — explicit current hosted binding and historical CCP dispatch.
- `schemas/a0x-execution-authorization.schema.json` — preserve the historical v2 contract byte-semantically; dispatch new authorizations to the new v3 schema.
- `src/latent_triz/a0x_material_contract.py` — provider dispatch and pair-derived five-file paths.
- `src/latent_triz/a0x_contract.py` — same-source, separate-provider authorization-chain checks.
- `src/latent_triz/a0x_runtime_bundle.py` and `scripts/a0x_prepare_runtime.py` — Gate B authorization and hosted verification before bundle output.
- `src/latent_triz/a0x_ccp_executor.py`, `src/latent_triz/a0x_production_adapter.py`, and `scripts/a0x_material_child.py` — five-file Gate C rehash without GitHub/network verification.
- `src/latent_triz/a0x_report.py` and `src/latent_triz/a0x_verify.py` — package and fresh-clone provider-aware verification.
- `src/latent_triz/a0x_freeze.py` — inventory every trust-relevant implementation input.
- `scripts/a0x_contract_check.py`, `scripts/repository_check.py`, and `Makefile` — expose target-free verification targets.
- `tests/a0x_test_support.py` and existing A0X contract/runtime/executor/production/report/verify/freeze/schema tests — provider migration regressions.
- `docs/A0X_SIX_MODEL_CAMPAIGN.md`, `docs/A0X_GATE_B_OPERATOR_HARDENING.md`, `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`, `docs/CURRENT_STATUS.md`, `docs/PERSISTENT_GOAL.txt`, and `artifacts/checkpoints/A0X_RESTART_CHECKPOINT_2026-08-30.md` — current status and restart-safe operator boundary.
- Both implementation inventories, both freezes, all twelve dossiers, and `results/a0x/preexecution/a0x-no-model-verification-receipt.json` — regenerated only after the exact implementation commit.

---

### Task 1: Freeze Dependency and Workflow Input Manifests

**Files:**
- Create: `.github/a0x-hosted-gate-a-actions.json`
- Create: `.github/a0x-hosted-gate-a-lanes.json`
- Modify: `requirements-schema.in`
- Modify: `requirements-schema.lock`
- Test: `tests/test_a0x_hosted_gate_a_workflow.py`

**Interfaces:**
- Consumes: approved full action pins and seven lane definitions from the specification.
- Produces: canonical `actions-v1` and `lanes-v1` files whose raw SHA-256 values enter every hosted manifest.

- [ ] **Step 1: Write failing policy tests**

Add tests that require exact action objects and exact sorted lane IDs:

```python
ACTION_PINS = {
    "actions/attest": "508db95dd578ae2727ebd6217d5ba78e4fbda05d",
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "a309ff8b426b58ec0e2a45f0f869d46889d02405",
    "actions/upload-artifact": "043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
}

LANES = (
    "a0x-no-model",
    "a0x-synthetic",
    "documentation-audit",
    "repository-python311",
    "repository-python312",
    "schema-cross-validation-python311",
    "schema-cross-validation-python312",
)
```

Assert `requirements-schema.in` pins `jsonschema` and `PyYAML==6.0.3`; `requirements-schema.lock` contains `--hash=sha256:` for every named and transitive requirement and can be installed with `--require-hashes` on both supported interpreters. Workflow tests must use a strict `yaml.SafeLoader`, reject duplicate keys, and never execute Python-specific YAML tags.

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `rtk python3 -m unittest tests.test_a0x_hosted_gate_a_workflow -v`

Expected: FAIL because the manifests are absent and the lock is version-only.

- [ ] **Step 3: Create canonical manifests and regenerate the hash lock**

Use compact sorted JSON with one trailing newline. Each lane record has exactly `id`, `python`, and `argv`; non-Python lanes use `python: null`. Generate the lock from `requirements-schema.in` with hashes for all resolved distributions, then inspect that Python 3.11 and 3.12 on `ubuntu-latest` share compatible versions.

Run during implementation under an explicitly authorized dependency-resolution network boundary:

```bash
rtk python3 -m venv /private/tmp/latent-triz-gate-a-lock-venv
rtk /private/tmp/latent-triz-gate-a-lock-venv/bin/python -m pip install --disable-pip-version-check 'pip-tools==7.5.2'
rtk /private/tmp/latent-triz-gate-a-lock-venv/bin/python -m piptools compile --generate-hashes --resolver=backtracking --output-file=requirements-schema.lock requirements-schema.in
```

- [ ] **Step 4: Prove deterministic bytes and hash-enforced installation**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_hosted_gate_a_workflow -v
rtk python3 -m pip install --dry-run --require-hashes -r requirements-schema.lock
```

Expected: PASS; deleting one hash or changing one lane/action pin makes the focused test fail.

- [ ] **Step 5: Commit**

```bash
rtk git add .github/a0x-hosted-gate-a-actions.json .github/a0x-hosted-gate-a-lanes.json requirements-schema.in requirements-schema.lock tests/test_a0x_hosted_gate_a_workflow.py
rtk git commit -m "build: freeze hosted Gate A inputs"
```

### Task 2: Implement Canonical Lane and Manifest Contracts

**Files:**
- Create: `schemas/a0x-hosted-gate-a-lane-receipt.schema.json`
- Create: `schemas/a0x-hosted-gate-a-evidence.schema.json`
- Create: `src/latent_triz/a0x_hosted_gate_a.py`
- Create: `scripts/a0x_hosted_gate_a.py`
- Create: `tests/test_a0x_hosted_gate_a.py`
- Modify: `tests/test_a0x_schemas.py`

**Interfaces:**
- Consumes: raw action/lane manifests from Task 1.
- Produces: `canonical_json_bytes(value) -> bytes`, `build_lane_receipt(lane_id, source_head, source_tree, command, status) -> bytes`, `decode_lane_output(encoded) -> dict`, and `build_manifest(repository, source, workflow, inputs, lanes) -> bytes`.

- [ ] **Step 1: Write failing canonical-contract tests**

Test the public interface with complete concrete inputs:

```python
lane_raw = build_lane_receipt(
    lane_id="repository-python311",
    source_head="a" * 40,
    source_tree="b" * 40,
    command=("python", "scripts/repository_check.py"),
    status="PASS",
)
lane = decode_lane_output(base64url_without_padding(lane_raw))
manifest_raw = build_manifest(
    repository="MarcoPorcellato/Latent-TRIZ",
    source_head="a" * 40,
    source_tree="b" * 40,
    workflow_sha256="c" * 64,
    run_id=123,
    run_attempt=1,
    requirements_lock_sha256="d" * 64,
    action_manifest_sha256="e" * 64,
    lane_manifest_sha256="f" * 64,
    encoded_lane_outputs=seven_encoded_lane_outputs,
)
assert lane["status"] == "PASS"
assert manifest_raw.endswith(b"\n")
```

Positive tests assert byte-identical output, seven sorted lanes, trailing newline, and a 4,096-byte decoded lane ceiling. Negative tests reject duplicate keys, unknown fields, noncanonical bytes, unsorted/duplicate/extra/missing lanes, non-PASS status, wrong source/tree, invalid base64url padding, oversized inputs, booleans used as integers, and NaN.

- [ ] **Step 2: Run tests and confirm RED**

Run: `rtk python3 -m unittest tests.test_a0x_hosted_gate_a tests.test_a0x_schemas -v`

Expected: FAIL because schemas and module do not exist.

- [ ] **Step 3: Add strict schemas and minimal pure implementation**

Use stable error codes on `A0XHostedGateAError`, including:

```python
LANE_INVALID = "A0X_GATE_A_LANE_INVALID"
LANE_OVERSIZED = "A0X_GATE_A_LANE_OVERSIZED"
LANE_SET_MISMATCH = "A0X_GATE_A_LANE_SET_MISMATCH"
SOURCE_MISMATCH = "A0X_GATE_A_SOURCE_MISMATCH"
MANIFEST_NONCANONICAL = "A0X_GATE_A_MANIFEST_NONCANONICAL"
```

The workflow CLI has only `lane` and `aggregate` subcommands. It never imports model/runtime modules and writes a lane output to the requested GitHub output file only after successful validation.

- [ ] **Step 4: Run focused and schema tests**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_hosted_gate_a tests.test_a0x_schemas -v
rtk python3 scripts/schema_cross_validate.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add schemas/a0x-hosted-gate-a-lane-receipt.schema.json schemas/a0x-hosted-gate-a-evidence.schema.json src/latent_triz/a0x_hosted_gate_a.py scripts/a0x_hosted_gate_a.py tests/test_a0x_hosted_gate_a.py tests/test_a0x_schemas.py
rtk git commit -m "feat: add canonical hosted Gate A manifest"
```

### Task 3: Add the Exact-Main Hosted Workflow

**Files:**
- Create: `.github/workflows/a0x-hosted-gate-a.yml`
- Modify: `tests/test_a0x_hosted_gate_a_workflow.py`
- Modify: `scripts/repository_check.py`

**Interfaces:**
- Consumes: Task 1 manifests and Task 2 CLI.
- Produces: one artifact named `a0x-hosted-gate-a-${GITHUB_SHA}` and one GitHub provenance attestation whose subject is the raw manifest.

- [ ] **Step 1: Expand static workflow tests and confirm RED**

Tests must parse YAML as data with the hash-locked `PyYAML==6.0.3` strict `SafeLoader`; regex-only checks are insufficient. The loader rejects duplicate mapping keys and all Python-specific tags. Require:

```yaml
on:
  push:
    branches: [main]
permissions: {}
concurrency:
  group: a0x-gate-a-${{ github.sha }}
  cancel-in-progress: false
```

Reject every other trigger, mutable `uses:`, secrets reference, write permission, self-hosted runner, PR checkout, lane omission, aggregate duplication, and `continue-on-error`. Require `persist-credentials: false`, explicit Python version, `--require-hashes`, `GITHUB_RUN_ATTEMPT == 1`, and `if: always()` on the unique aggregate so missing lane outputs are rejected rather than skipped.

Each Python lane also asserts the observed `sys.version_info[:2]` equals its declared `(3, 11)` or `(3, 12)` value before dependency installation; a successful setup action alone is insufficient evidence of interpreter identity.

- [ ] **Step 2: Implement seven lanes and the aggregate job**

Each Python lane runs one of these exact commands after hash-locked install:

```text
python scripts/repository_check.py
python scripts/schema_cross_validate.py
```

Other lanes run:

```text
make a0x-no-model-verify
make a0x-synthetic-verify
make docs-audit
```

The aggregate decodes seven `gate_a_lane_receipt` outputs, builds the manifest, uploads only that file with `if-no-files-found: error`, and invokes pinned `actions/attest` in default provenance mode using `subject-path`.

- [ ] **Step 3: Add workflow policy to the repository check**

Register `tests.test_a0x_hosted_gate_a_workflow` in the repository-check suite so a pull request cannot change workflow bytes without exercising the static policy.

- [ ] **Step 4: Run focused and complete repository checks**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_hosted_gate_a_workflow -v
rtk python3 scripts/repository_check.py
```

Expected: PASS; no workflow execution occurs locally.

- [ ] **Step 5: Commit**

```bash
rtk git add .github/workflows/a0x-hosted-gate-a.yml tests/test_a0x_hosted_gate_a_workflow.py scripts/repository_check.py
rtk git commit -m "ci: attest exact-main A0X qualification"
```

### Task 4: Implement Strict Transport, Policy, Authorization, and Receipt Schemas

**Files:**
- Create: `schemas/a0x-hosted-gate-a-transport.schema.json`
- Create: `schemas/a0x-hosted-gate-a-verifier-policy.schema.json`
- Create: `schemas/a0x-hosted-gate-a-verification-receipt.schema.json`
- Create: `schemas/a0x-gate-b-authorization.schema.json`
- Create: `tests/fixtures/a0x/hosted-gate-a/positive/`
- Modify: `tests/test_a0x_schemas.py`
- Modify: `tests/a0x_test_support.py`

**Interfaces:**
- Consumes: canonical manifest profile from Task 2.
- Produces: exact Gate B authorization containing four input file bindings plus verifier and output path, but no verification-receipt hash.

- [ ] **Step 1: Write failing schema tests**

The Gate B authorization must have this exact top-level shape:

```python
{
    "artifact_class": "a0x-gate-b-authorization",
    "authorization_profile": "a0x-gate-b-authorization-v1",
    "authorization_status": "authorized",
    "repository": "MarcoPorcellato/Latent-TRIZ",
    "source_head": REVISION,
    "source_tree": REVISION,
    "pair_binding": PAIR,
    "hosted_inputs": {
        "manifest": {"path": PATH, "sha256": SHA256},
        "attestation_bundle": {"path": PATH, "sha256": SHA256},
        "trusted_root": {"path": PATH, "sha256": SHA256},
        "transport": {"path": PATH, "sha256": SHA256},
    },
    "verifier": {
        "role": "github_cli_verifier",
        "version": "gh version 2.97.0 (2026-07-31)",
        "sha256": "6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c",
        "policy_raw_sha256": SHA256,
    },
    "verification_receipt_path": PATH,
    "max_verification_count": 1,
    "stop_boundary": "after_gate_b_runtime_bundle",
    "authorization_id": IDENTIFIER,
}
```

Assert the authorization rejects a fifth input, a pre-bound receipt hash, local/private strings, unsafe paths, or an output outside the pair/source-derived runtime inlet.

The raw authorization SHA-256 is computed by the consumer and later bound into the execution authorization; the authorization object does not contain a self-referential copy of its own hash.

- [ ] **Step 2: Run schema tests and confirm RED**

Run: `rtk python3 -m unittest tests.test_a0x_schemas -v`

Expected: FAIL because the schemas are absent.

- [ ] **Step 3: Implement closed schemas and positive inert fixtures**

Every schema uses `additionalProperties: false`, bounded strings, full lowercase hashes, exact profile constants, and Draft 2020-12. The transport schema requires `artifact_id`, `run_id`, `run_attempt`, `head_sha`, `archive_digest`, `archive_size_bytes`, `created_at`, `expires_at`, and `captured_at`.

- [ ] **Step 4: Cross-validate and mutate each fixture**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_schemas -v
rtk python3 scripts/schema_cross_validate.py
```

Expected: PASS; each unknown/missing/wrong-typed field mutation is rejected.

- [ ] **Step 5: Commit**

```bash
rtk git add schemas/a0x-hosted-gate-a-transport.schema.json schemas/a0x-hosted-gate-a-verifier-policy.schema.json schemas/a0x-hosted-gate-a-verification-receipt.schema.json schemas/a0x-gate-b-authorization.schema.json tests/fixtures/a0x/hosted-gate-a tests/test_a0x_schemas.py tests/a0x_test_support.py
rtk git commit -m "feat: define offline hosted evidence schemas"
```

### Task 5: Implement the Offline GitHub Attestation Verifier

**Files:**
- Create: `src/latent_triz/a0x_hosted_verifier.py`
- Create: `scripts/a0x_verify_hosted_gate_a.py`
- Create: `tests/test_a0x_hosted_verifier.py`
- Modify: `src/latent_triz/a0x_hosted_gate_a.py`

**Interfaces:**
- Consumes: `GateBVerificationRequest`, four independent files, exact verifier bytes/version, and one injected shell-free runner.
- Produces: `verify_hosted_gate_a(request, runner) -> bytes`, canonical `a0x-hosted-gate-a-verification-receipt-v1`, or no output plus stable refusal code.

- [ ] **Step 1: Write the synthetic verifier mutation matrix**

Exercise these exact request and runner interfaces in tests before implementation:

```python
@dataclass(frozen=True)
class GateBVerificationRequest:
    repository_root: Path
    authorization_path: Path
    verifier_executable: Path
    verifier_policy_path: Path

VerifierRunner = Callable[[Sequence[str], Path], tuple[int, bytes, bytes]]
SourceState = tuple[str, str, bool]
SourceStateProbe = Callable[[Path], SourceState]

request = GateBVerificationRequest(
    repository_root=root,
    authorization_path=root / ".a0x-runtime/gate-b-authorizations/a0/smollm2_360m/a0x-a0-smollm2_360m-f8027fd0-attempt-01.json",
    verifier_executable=root / ".a0x-runtime/bin/gh",
    verifier_policy_path=root / ".a0x-runtime/gate-a/verifier-policy.json",
)
receipt_raw = verify_hosted_gate_a(
    request,
    runner=synthetic_verifier_runner,
    source_state_probe=synthetic_source_state_probe,
)
assert receipt_raw.endswith(b"\n")
```

Cover every spec mutation: same tree/wrong HEAD; wrong tree/repository/event/ref/workflow/hash; rerun; missing/duplicate/extra/failed lane; wrong subject/signer/issuer/builder/predicate/source; independently wrong-but-valid signer digest and source digest; valid signature with wrong policy values; changed manifest/bundle/root/transport; expired-only or unavailable artifact; symlink/hardlink/nonregular input; oversized file; output collision; source mutation between the two probes; input mutation after initial hash; and verifier nonzero/malformed JSON. Assert both the stable refusal code and absence of receipt/readiness/descriptor/authorization/mapping output.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `rtk python3 -m unittest tests.test_a0x_hosted_verifier -v`

Expected: FAIL because the verifier module is absent.

- [ ] **Step 3: Implement the pure fail-closed sequence**

Use this exact order:

1. validate authorization and pair-derived paths;
2. `lstat` all inputs and verifier; require regular, non-symlink, `st_nlink == 1`;
3. enforce byte ceilings before reads/parsing;
4. hash all raw inputs and verifier against authorization;
5. strictly parse transport, policy, and manifest;
6. require local exact `HEAD`, tree, and clean state from the injected source-state probe;
7. execute one shell-free `gh attestation verify` argv with `--bundle`, `--custom-trusted-root`, `--repo`, `--signer-workflow`, `--signer-digest`, `--source-digest`, `--source-ref`, `--cert-oidc-issuer`, `--predicate-type`, `--deny-self-hosted-runners`, and `--format json`; bind `--signer-digest` to the expected `job_workflow_sha` certificate claim and `--source-digest` to the expected `sha` source-repository claim. For this non-reusable, same-repository exact-main workflow both expected claim values are the source HEAD, but they remain separate policy fields. The raw workflow-file SHA-256 is independently bound and verified through `workflow.raw_sha256` in the manifest;
8. validate structured result, subject digest, certificate identity/issuer, verified timestamp/transparency evidence, builder, source/ref, and predicate;
9. rerun the injected source-state probe and require the same exact HEAD/tree/clean tuple;
10. rehash all inputs and verifier;
11. write one receipt with exclusive-create semantics, then fsync file and parent.

If implementation later introduces a reusable workflow, hard stop: `job_workflow_sha` may diverge from the source HEAD, so the policy, specification, fixtures, and frozen package require reviewed revision rather than permissive adaptation.

Use stable codes such as `A0X_GATE_B_INPUT_HASH_MISMATCH`, `A0X_GATE_B_ATTESTATION_REFUSED`, `A0X_GATE_B_EXPECTATION_MISMATCH`, `A0X_GATE_B_SOURCE_DRIFT`, and `A0X_GATE_B_OUTPUT_EXISTS`.

- [ ] **Step 4: Verify installed CLI help without executing material work**

Run read-only:

```bash
rtk shasum -a 256 /opt/homebrew/bin/gh
rtk /opt/homebrew/bin/gh --version
rtk /opt/homebrew/bin/gh attestation verify --help
```

Expected: exact version/hash, every frozen flag, and the documented semantics of
`--signer-digest`, `--source-digest`, and `--predicate-type`. Any flag presence,
meaning, accepted format, default, version, or output-shape mismatch is a hard
stop for reviewed contract revision; implementation must not adapt
permissively.

- [ ] **Step 5: Run the focused suite**

Run: `rtk python3 -m unittest tests.test_a0x_hosted_verifier -v`

Expected: PASS with only synthetic runner fixtures; no network or GitHub CLI verification occurs.

- [ ] **Step 6: Commit**

```bash
rtk git add src/latent_triz/a0x_hosted_gate_a.py src/latent_triz/a0x_hosted_verifier.py scripts/a0x_verify_hosted_gate_a.py tests/test_a0x_hosted_verifier.py
rtk git commit -m "feat: verify hosted Gate A evidence offline"
```

## Sol architecture closure for Tasks 6–12

The following rulings are frozen before lower-cost execution. Terra may
implement them with TDD and delegate bounded read-only or mechanical checks to
Luna. Neither model may reinterpret these decisions or weaken a refusal to
make an intermediate suite green.

1. `implementation_source_head` and `source_head` are intentionally different
   identities. The former is the committed pre-regeneration implementation
   anchor stored in the twelve approval dossiers. The latter is the clean live
   repository commit attested by Hosted Gate A and later repeated in the Gate B
   authorization and Gate C guard. A squash merge may change `source_head`
   without invalidating `implementation_source_head`; tree equality never
   substitutes for either commit identity.
2. Current evidence dispatch is profile-first. Current dossiers accept only
   `a0x-gate-a-evidence-binding-v2` and execution authorization
   `a0x-execution-authorization-json-v3`. Historical packages accept only their
   existing v1/v2 profiles through explicitly named legacy loaders. No
   structural `oneOf`, missing discriminator, or exception fallback may select
   a legacy parser for a current document.
3. Hosted Gate A and CCP Gate C remain independent trust domains. Hosted
   verifier identity is compared only with the frozen Hosted Gate A policy.
   The existing `ccp` object, guard identity, timeout envelope, and one-shot
   count remain byte-semantic Gate C requirements. Both domains bind the same
   `source_head`, but their producer identities are never compared.
4. Gate B has one acyclic ownership sequence: four authorized hosted inputs,
   one exclusively created verification receipt, then readiness, descriptor,
   execution authorization, and local mapping. A verifier refusal creates
   nothing. If verification succeeds but a later preparation step fails, the
   owned verification receipt is preserved as evidence of the consumed
   verification attempt; no readiness, descriptor, execution authorization, or
   mapping may survive partially. Pre-existing files are never removed or
   overwritten.
5. One shared, pure five-file validator owns Gate C byte and path semantics.
   It requires repository-controlled relative paths, safe ancestors,
   independent regular files with link count one, exact raw SHA-256 values, and
   exact source/pair bindings. Every Gate C inlet calls that same validator;
   consumers must not reimplement a weaker subset.
6. Tasks 6, 7, and 8 are sequential integration checkpoints. Task 9 may make
   implementation and inventory tests green, but the old frozen package must
   remain an explicit expected `NO-GO` until Task 10 regenerates it. No result
   before Task 10 may be described as a full repository PASS.
7. Task 10 records one pre-regeneration implementation anchor, regenerates both
   inventories, both freezes, twelve dossiers, and the no-model receipt from
   that anchor, then commits generated bytes. The later candidate HEAD is a
   packaging/publication commit, not a replacement for the stored
   `implementation_source_head`.
8. Task 12 remains an operator/Sol boundary. Push, PR, squash merge, exact-main
   hosted acceptance, evidence capture, offline verification, evidence
   publication, and any correction after a real output-shape mismatch require
   their named authorization. A failed, skipped, cancelled, or rerun hosted
   acceptance is terminal for that attempt.

Cost-aware ownership after these rulings: Terra implements Tasks 6–10 in
order; Luna performs bounded fixture/schema inventories, mutation-coverage
audits, deterministic test execution, hash/count distillation, and the
material-boundary review. Terra integrates all findings and completes Task 11
locally. Sol is required again only for the final security/architecture review
of the exact Task 11 candidate and for Task 12 external decisions.

### Task 6: Separate Hosted Gate A from CCP Gate C in Public Contracts

**Files:**
- Modify: `experiments/a0x-six-model/material-execution-contract.json`
- Modify: `schemas/a0x-material-execution-contract.schema.json`
- Modify: `schemas/a0x-qualification-evidence.schema.json`
- Preserve: `schemas/a0x-execution-authorization.schema.json`
- Create: `schemas/a0x-execution-authorization-v3.schema.json`
- Modify: `src/latent_triz/a0x_material_contract.py`
- Modify: `src/latent_triz/a0x_contract.py`
- Modify: `tests/test_a0x_material_contract.py`
- Modify: `tests/test_a0x_contract.py`

**Interfaces:**
- Consumes: verified hosted receipt from Task 5 and unchanged CCP block.
- Produces: `validate_gate_a_evidence(value, *, historical=False) -> dict`, current hosted profile `a0x-gate-a-evidence-binding-v2`, current execution profile `a0x-execution-authorization-json-v3`, and explicit legacy-v2 loaders/schema mapping.

- [ ] **Step 1: Write failing provider-separation tests**

Require the current binding to contain provider, exact source HEAD/tree, four input file bindings, the fifth verification-receipt binding, and verifier identity. Assert:

- current hosted evidence cannot accept a CCP receipt;
- legacy CCP evidence cannot satisfy a current dossier;
- hosted verifier identity is never compared with Gate C CCP identity;
- exact source HEAD must match both Gate A and Gate C authorization;
- Gate C CCP identity remains mandatory and unchanged;
- same tree with different HEAD is rejected.
- current v3 authorizations use a new commitment prefix and v3 schema;
- historical v2 authorizations still select the original schema and commitment prefix and verify byte-identically from frozen historical packages.

- [ ] **Step 2: Run contract tests and confirm RED**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_material_contract tests.test_a0x_contract -v
```

Expected: FAIL on the existing mandatory Gate-A/CCP identity coupling.

- [ ] **Step 3: Add hosted `gate_a` policy and explicit dispatch**

The material contract `gate_a` block freezes provider, workflow path, event/ref, seven lane IDs, four size ceilings, verifier role/version/hash, policy hash, predicate URI, issuer, self-hosted denial, verified-timestamp requirement, and action/lane manifest hashes. Leave the complete `ccp` object byte-semantically unchanged except for the outer material-contract hash caused by adding `gate_a`.

Replace ambiguous `oneOf` acceptance with an explicit `evidence_profile` dispatch in Python. Add a new `a0x-execution-authorization-json-v3` constant, schema mapping, and commitment prefix. Keep the existing v2 constant, schema file, mapping, and prefix unchanged behind an explicit legacy loader. Schemas may use `oneOf` only when the discriminating profile constants are mutually exclusive and tests prove current dossiers reject the legacy branch. Verify representative historical packages byte-for-byte before and after migration.

- [ ] **Step 4: Run provider and schema tests**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_material_contract tests.test_a0x_contract tests.test_a0x_schemas -v
rtk python3 scripts/schema_cross_validate.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add experiments/a0x-six-model/material-execution-contract.json schemas/a0x-material-execution-contract.schema.json schemas/a0x-qualification-evidence.schema.json schemas/a0x-execution-authorization-v3.schema.json src/latent_triz/a0x_material_contract.py src/latent_triz/a0x_contract.py tests/test_a0x_material_contract.py tests/test_a0x_contract.py
rtk git commit -m "refactor: separate Gate A and Gate C identities"
```

### Task 7: Integrate Offline Verification into Gate B Bundle Preparation

**Files:**
- Modify: `src/latent_triz/a0x_runtime_bundle.py`
- Modify: `scripts/a0x_prepare_runtime.py`
- Modify: `src/latent_triz/a0x_preflight.py`
- Modify: `tests/test_a0x_runtime_bundle.py`
- Modify: `tests/test_a0x_preflight.py`

**Interfaces:**
- Consumes: fixed dossier, Gate B authorization file, verifier executable/policy, Python runtime, and Task 5 verifier callback.
- Produces: verification receipt first, then readiness, descriptor, execution authorization, and local mapping; all five Gate A hashes enter execution authorization.

- [ ] **Step 1: Write failing Gate B lifecycle tests**

Replace the request interface with:

```python
@dataclass(frozen=True)
class RuntimePreparationRequest:
    fixed_dossier: str
    gate_b_authorization: Path
    verifier_executable: Path
    verifier_policy: Path
    ccp_executable: Path
    python_executable: Path
    authorization_id: str
    attempt_id: str
```

Assert that verification occurs before `runtime_readiness_probe`; any verifier refusal produces no output. Assert the output receipt is hashed only after creation, then all five hashes plus the Gate B authorization raw hash are embedded in execution authorization. Mutate each file between verification and output and require refusal/cleanup without overwriting pre-existing files.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_runtime_bundle tests.test_a0x_preflight -v
```

Expected: FAIL because the request still requires a local CCP qualification receipt.

- [ ] **Step 3: Implement one acyclic Gate B chain**

The new chain is:

```text
four authorized hosted inputs
  -> gate-a-verification-receipt.json
  -> readiness
  -> descriptor
  -> execution authorization
  -> local mapping
```

The CLI requires `--gate-b-authorization`, `--verifier`, and `--verifier-policy`; remove current-only `--qualification-receipt` and `--public-evidence-commit`. Keep a separate explicitly named historical verification entrypoint for old packages, never as current bundle preparation fallback.

- [ ] **Step 4: Prove no-material and overwrite refusal**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_runtime_bundle tests.test_a0x_preflight -v
rtk make a0x-no-model-verify
```

Expected: PASS; spies prove no model, tokenizer, target, network, Docker, or CCP invocation.

- [ ] **Step 5: Commit**

```bash
rtk git add src/latent_triz/a0x_runtime_bundle.py scripts/a0x_prepare_runtime.py src/latent_triz/a0x_preflight.py tests/test_a0x_runtime_bundle.py tests/test_a0x_preflight.py
rtk git commit -m "feat: require offline hosted evidence at Gate B"
```

### Task 8: Enforce the Five-File Boundary at Gate C and Package Verification

**Files:**
- Modify: `src/latent_triz/a0x_ccp_executor.py`
- Modify: `src/latent_triz/a0x_production_adapter.py`
- Modify: `scripts/a0x_material_child.py`
- Modify: `src/latent_triz/a0x_report.py`
- Modify: `src/latent_triz/a0x_verify.py`
- Modify: `tests/test_a0x_ccp_executor.py`
- Modify: `tests/test_a0x_production_adapter.py`
- Modify: `tests/test_a0x_material_child.py`
- Modify: `tests/test_a0x_report.py`
- Modify: `tests/test_a0x_verify.py`

**Interfaces:**
- Consumes: execution authorization containing five Gate A bindings plus independent CCP Gate C identity.
- Produces: `rehash_gate_a_evidence(paths, binding) -> None` called before claim, immediately before guard, at child inlet, and during fresh-clone package verification.

- [ ] **Step 1: Write failing boundary and TOCTOU tests**

For each of the five files, test missing, mutated, symlink, hardlink, nonregular, and replacement between first and second validation. Assert no claim, guard invocation, model factory, target loader, or output on failure. Add a positive test where hosted verifier identity differs from CCP identity and both independently match their contracts.

- [ ] **Step 2: Run focused tests and confirm RED**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_ccp_executor tests.test_a0x_production_adapter tests.test_a0x_material_child tests.test_a0x_report tests.test_a0x_verify -v
```

Expected: FAIL because current code reparses a local CCP qualification receipt.

- [ ] **Step 3: Replace current receipt semantics with five-file rehashing**

Gate C must not invoke `gh`, access a network, reinterpret provenance, or compare hosted and CCP producers. Package verification validates the stored Gate B receipt and raw five-file commitments. Historical package verification remains behind an explicit legacy loader and unchanged profile.

- [ ] **Step 4: Run focused and synthetic suites**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_ccp_executor tests.test_a0x_production_adapter tests.test_a0x_material_child tests.test_a0x_report tests.test_a0x_verify -v
rtk make a0x-synthetic-verify
```

Expected: PASS with no heavy command or material access.

- [ ] **Step 5: Commit**

```bash
rtk git add src/latent_triz/a0x_ccp_executor.py src/latent_triz/a0x_production_adapter.py scripts/a0x_material_child.py src/latent_triz/a0x_report.py src/latent_triz/a0x_verify.py tests/test_a0x_ccp_executor.py tests/test_a0x_production_adapter.py tests/test_a0x_material_child.py tests/test_a0x_report.py tests/test_a0x_verify.py
rtk git commit -m "feat: bind five hosted evidence files at Gate C"
```

### Task 9: Bind Every New Trust Input into Both Frozen Implementations

**Files:**
- Modify: `src/latent_triz/a0x_freeze.py`
- Modify: `scripts/a0x_contract_check.py`
- Create: `scripts/a0x_materialize_no_model_receipt.py`
- Modify: `scripts/repository_check.py`
- Modify: `Makefile`
- Modify: `tests/test_a0x_freeze.py`
- Modify: `tests/test_a0x_frozen_package.py`
- Modify: `tests/test_a0x_runner.py`
- Modify: `tests/test_ccp_a0x_policy_migration.py`

**Interfaces:**
- Consumes: all trusted files created in Tasks 1-8.
- Produces: exact implementation inventories that fail if any workflow, schema, policy manifest, verifier, CLI, or boundary test is omitted.

- [ ] **Step 1: Write failing inventory completeness tests**

Require these path families in `_IMPLEMENTATION_PATHS`: the workflow, action/lane manifests, input and hash lock, seven new schemas including execution-authorization v3, two new modules, three new scripts including the receipt materializer, three new test files, and hosted fixtures. Assert both A0 and A0-R1 inventories contain identical implementation path sets and raw hashes.

- [ ] **Step 2: Run inventory tests and confirm RED**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_freeze tests.test_a0x_frozen_package tests.test_a0x_runner tests.test_ccp_a0x_policy_migration -v
```

Expected: FAIL with omitted hosted Gate A paths.

- [ ] **Step 3: Extend target-free repository targets**

Add `a0x-hosted-gate-a-verify` to `Makefile` and the repository check. It runs only schemas, canonical builder, workflow policy, verifier synthetic tests, provider separation, and material-boundary tests. It must not call the real GitHub CLI verifier or any material path.

Implement `scripts/a0x_materialize_no_model_receipt.py` as the sole receipt writer. It computes deterministic canonical bytes from the target-free checker, accepts only the canonical repository-relative output, refuses symlinks, hardlinks, and nonregular files, requires explicit `--replace-existing` for replacement, writes through an exclusive temporary regular file, fsyncs, atomically replaces, and fsyncs the parent. Tests prove deterministic bytes, no write without the flag, no partial output on failure, and no model, runtime, target, network, Docker, or CCP access.

- [ ] **Step 4: Prove implementation completeness and explicit stale-package refusal**

Run:

```bash
rtk python3 -m unittest \
  tests.test_a0x_freeze.A0XFreezeTests.test_hosted_gate_a_paths_are_bound_in_both_implementation_inventories \
  tests.test_a0x_freeze.A0XFreezeTests.test_a0_and_r1_implementation_path_sets_are_identical \
  tests.test_a0x_runner.A0XRunnerPublicSurfaceTests.test_hosted_gate_a_target_is_target_free \
  tests.test_a0x_runner.A0XRunnerPublicSurfaceTests.test_no_model_receipt_materializer_is_deterministic_and_overwrite_refusing -v
rtk make a0x-hosted-gate-a-verify
```

Expected: the named implementation/inventory tests and hosted target PASS.
Then run `rtk make a0x-no-model-verify` once and require a fail-closed stale
implementation/freeze binding error. Record that exact expected `NO-GO`; do not
regenerate or weaken the verifier in Task 9. Task 10 is the only step that may
make the frozen and no-model package green.

- [ ] **Step 5: Commit**

```bash
rtk git add src/latent_triz/a0x_freeze.py scripts/a0x_contract_check.py scripts/a0x_materialize_no_model_receipt.py scripts/repository_check.py Makefile tests/test_a0x_freeze.py tests/test_a0x_frozen_package.py tests/test_a0x_runner.py tests/test_ccp_a0x_policy_migration.py
rtk git commit -m "test: bind hosted Gate A into A0X freeze"
```

### Task 10: Document the Operator Contract and Regenerate Target-Free Bindings

**Files:**
- Create: `docs/A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md`
- Modify: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify: `docs/A0X_GATE_B_OPERATOR_HARDENING.md`
- Modify: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`
- Modify: `docs/CURRENT_STATUS.md`
- Modify: `docs/PERSISTENT_GOAL.txt`
- Modify: `artifacts/checkpoints/A0X_RESTART_CHECKPOINT_2026-08-30.md`
- Regenerate: both implementation inventories, both freezes, twelve dossiers, and no-model receipt.

**Interfaces:**
- Consumes: exact implementation commit from Tasks 1-9.
- Produces: operator-readable stop sequence and hash-bound target-free frozen package.

- [ ] **Step 1: Write failing documentation/status tests**

Extend docs audit or focused tests to require: seven hosted lanes; four hosted inputs plus fifth receipt; 32 KiB/1 MiB/2 MiB/16 KiB/32 KiB caps; no rerun; no CCP Gate A fallback; retained CCP Gate C; historical evidence label; first hosted run as acceptance; trusted-root revocation limitation; and separate authorization before capture, publication, Gate B, or Gate C.

- [ ] **Step 2: Update canonical documentation**

The runbook must include exact capture filenames, public-safe fields, offline verifier argv flags, refusal meanings, retention/expiry behavior, governance limitation, and restart procedure. Mark all pre-migration CCP Gate A hashes historical rather than rewriting them as hosted evidence.

- [ ] **Step 3: Commit implementation and docs before regeneration**

```bash
rtk git add docs/A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md docs/A0X_SIX_MODEL_CAMPAIGN.md docs/A0X_GATE_B_OPERATOR_HARDENING.md docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md docs/CURRENT_STATUS.md docs/PERSISTENT_GOAL.txt artifacts/checkpoints/A0X_RESTART_CHECKPOINT_2026-08-30.md
rtk git commit -m "docs: define hosted Gate A operations"
rtk git rev-parse HEAD
```

Record the complete implementation HEAD; use it unchanged in both regeneration commands.
This value becomes `implementation_source_head`. Later regeneration and
qualification commits may advance the candidate HEAD. They must not rewrite
the stored implementation anchor or pre-bind the future squash-merge SHA.

- [ ] **Step 4: Regenerate without material access**

```bash
rtk env PYTHONPATH=src python3 -m latent_triz.a0x_freeze --root . --write-protected-trees --write-a0-selection
rtk env PYTHONPATH=src python3 -m latent_triz.a0x_freeze --root . --freeze-all --prepare-dossiers --implementation-source-head "$(rtk git rev-parse HEAD)"
rtk env PYTHONPATH=src python3 scripts/a0x_materialize_no_model_receipt.py --root . --output results/a0x/preexecution/a0x-no-model-verification-receipt.json --replace-existing
```

Expected: exactly two implementation inventories, two freezes, twelve dossiers, and one deterministically materialized no-model receipt updated; no model/runtime/target path read.

- [ ] **Step 5: Verify regeneration determinism**

Run:

```bash
rtk python3 -m unittest tests.test_a0x_frozen_package.A0XFrozenPackageTests.test_regeneration_is_byte_identical_for_same_implementation_head -v
rtk make a0x-no-model-verify
rtk make a0x-synthetic-verify
```

Expected: PASS and a clean second regeneration diff.

- [ ] **Step 6: Commit regenerated artifacts**

```bash
rtk git add experiments/a0x-six-model results/a0x/preexecution/a0x-no-model-verification-receipt.json
rtk git commit -m "chore: freeze hosted Gate A package"
```

### Task 11: Complete Local Verification and Independent Review

**Files:**
- Review: all files changed by Tasks 1-10.
- Update if required by verified findings only: `docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md`

**Interfaces:**
- Consumes: frozen exact-head candidate.
- Produces: local target-free qualification evidence and exact publication dossier; no remote mutation.

- [ ] **Step 1: Run the complete deterministic ladder**

```bash
rtk python3 -m unittest tests.test_a0x_hosted_gate_a tests.test_a0x_hosted_gate_a_workflow tests.test_a0x_hosted_verifier -v
rtk make a0x-hosted-gate-a-verify
rtk make a0x-no-model-verify
rtk make a0x-synthetic-verify
rtk make schema-cross-validate
rtk make docs-audit
rtk python3 scripts/repository_check.py
rtk git diff --check
```

Expected: every command PASS.

- [ ] **Step 2: Prove absence of material and network surfaces**

Run the synthetic spies and static import/call audit. Require zero references from workflow, manifest builder, verifier tests, or Gate B preflight to model factories, tokenizer constructors, sealed-target loaders, CCP `run`, CCP `guard exec`, Docker, or network clients except the real GitHub CLI adapter isolated behind the non-executed Gate B boundary.

- [ ] **Step 3: Request two independent reviews**

One reviewer checks architecture/security/supply chain; another checks scientific/material boundaries and freeze completeness. Both receive exact HEAD/tree and are read-only. Resolve concrete findings with TDD and rerun the complete ladder.

- [ ] **Step 4: Produce the exact publication dossier**

Record candidate HEAD/tree, spec/plan hashes, workflow/action/lane/lock hashes, verifier policy/hash, test counts, regenerated artifact hashes, dirty state, and explicit stop boundary. Do not include local paths, usernames, raw logs, secrets, or container IDs.

- [ ] **Step 5: Commit only verified corrections and dossier**

```bash
rtk git add docs/qualification docs/A0X_ENGINEERING_PROBLEM_SOLUTION_LOG.md
rtk git commit -m "docs: qualify hosted Gate A candidate"
rtk git status --short --branch
```

Expected: clean candidate. Stop for exact-head publication authorization.

### Task 12: Publish, Accept the First Hosted Run, and Stop Before Gate B

**Files:**
- Remote: implementation branch and pull request.
- Capture after separate authorization: four exact hosted evidence files.
- Verify: clean fresh clone.

**Interfaces:**
- Consumes: separately authorized exact-head candidate and GitHub ruleset.
- Produces: one exact-main signed Gate A evidence package verified offline; no Gate B runtime bundle.

- [ ] **Step 1: Reverify remote bindings before mutation**

Read live `origin/main`, open PRs, ruleset, required checks, candidate HEAD/tree, and worktree cleanliness. Stop on drift; do not rebase or regenerate silently.

- [ ] **Step 2: Push and merge only under exact authorization**

Push non-forced, open the PR, await all hosted PR gates, resolve conversations, and squash merge only if head/base/ruleset remain bound. No CCP Gate A receipt or manual success bridge is permitted.

- [ ] **Step 3: Observe one exact-main Gate A run**

Require event `push`, ref `refs/heads/main`, exact squash-merge SHA, run attempt `1`, seven successful lane receipts, one successful aggregate, and one attestation. Failure, cancellation, skip, or rerun is terminal `NO-GO` and requires a reviewed source correction plus new authorization.

- [ ] **Step 4: Capture four immutable inputs under separate authorization**

Capture exactly:

```text
hosted-gate-a-evidence.json
hosted-gate-a-attestation.bundle.jsonl
github-trusted-root.jsonl
hosted-gate-a-transport.json
```

Verify raw manifest SHA-256, GitHub archive digest, attestation subject digest, and transport metadata as four distinct concepts. Before publication, create or verify a dedicated `hosted-evidence/**` no-force-push/no-delete ruleset.

- [ ] **Step 5: Verify from a fresh clone and offline inputs**

Run the exact hash-bound GitHub CLI verifier with network unavailable and the captured bundle/root. Require the frozen manifest/schema/policy and exact source/tree. Demonstrate fail-closed refusal for one missing file and one byte mutation.

- [ ] **Step 6: Record acceptance and stop**

Publish only separately authorized exact bytes and public-safe receipt. Update status to `gate_a_hosted_verified; gate_b_authorization_pending`. Do not prepare runtime files, load a model/tokenizer, read targets, invoke CCP heavy work, or execute science without a new pair-specific Gate B authorization.

---

## Final Self-Review Checklist

- [ ] Every specification section maps to at least one task.
- [ ] Current hosted and historical CCP evidence profiles cannot substitute for one another.
- [ ] All seven lanes are present in policy, workflow, manifest, tests, and freeze.
- [ ] Four hosted inputs precede receipt creation; all five are bound afterward.
- [ ] Workflow, action pins, lock, schemas, verifier, fixtures, and boundary tests enter both inventories.
- [ ] Gate C CCP identity and 3,600/3,300/300-second execution envelope remain unchanged.
- [ ] No task before separately authorized publication/capture performs remote mutation.
- [ ] No task authorizes Gate B/C, model, tokenizer, target, or scientific access by implication.
