# A0X Material Composition Correction Design

**Status:** approved for offline implementation on 2026-08-28
**Scope:** A0X infrastructure only; frozen A0 and A0-R1 science is unchanged
**Material boundary:** no CCP heavy command, Docker, model or tokenizer construction, sealed-target access, network access, or remote publication is authorized by this design

## Purpose

Make each of the twelve frozen A0X leg/model pairs executable as one real,
shell-free, independently authorized local process while preserving the
scientific protocol, the one-shot target boundary, pair isolation, output caps,
and fail-closed terminal evidence.

The existing A0X statistical, activation, target-reader, package, and verifier
modules remain authoritative. The correction adds only the missing production
composition and fixes integration contradictions discovered after Task 11.

## Evidence behind the correction

The live audit found four gaps:

1. `scripts/a0x_material.py` is still an intentional refusal stub.
2. Each dossier places its future authorization below the pair output path,
   while the runner correctly requires that output path not exist before the
   attempt. A real authorization would therefore block its own run.
3. `guard_exec_argv_commitment` binds only an opaque digest. No canonical argv
   preimage is available for recomputation immediately before execution.
4. A package binds a qualification-receipt hash but lacks a public-safe
   qualification-evidence locator sufficient for a fresh-clone verifier to
   obtain and validate the exact receipt.

The six declared runtime snapshots are present below `artifacts/models/`, with
an aggregate footprint of 4,283,111,958 bytes. The intended runtime is the
repository `.venv` resolved to CPython 3.11.13; its resolved executable and
installed package manifest must be hash-bound before material use.

Historical comparable runs completed in approximately 312--950 seconds. Since
an outer timeout consumes the one authorized guard even when the scientific
work is otherwise healthy, the approved A0X envelope is increased uniformly
from 1,800 to 3,600 seconds.

## Non-negotiable scientific invariants

- Exactly two legs and six exact model/revision pairs: twelve independent
  attempts.
- No pooling, ranking, rescue of a primary endpoint, or cross-model claim.
- A0 keeps tuple indices `0`, `2`, `4`, and `6` as primary endpoints; its final
  transformer block remains descriptive only.
- A0-R1 keeps tuple index `6` as its sole primary endpoint; its final block
  remains descriptive only.
- Corpus, case selection, shortcut controls, seeds, permutation budgets,
  thresholds, analysis rules, and model cards are unchanged.
- CPU float32 only, no generation, no network, and `trust_remote_code=false`.
- At most one target-content open per pair, performed only after target-free
  activation sealing at the analysis boundary.
- Each pair has one immutable attempt claim and one terminal outcome. A timeout,
  cancellation, pressure stop, incompatibility, null, positive, or failure is
  preserved; no implicit retry exists.

## Runtime inlet and immutable outputs

Material authorizations and launch descriptors are runtime inputs, not result
artifacts. They live below the Git-ignored namespace:

```text
.a0x-runtime/
  authorizations/<leg>/<model-key>/<run-id>.json
  qualification/<source-head>/receipt.json
  launches/<leg>/<model-key>/<run-id>.json
  claims/<leg>/<model-key>/<run-id>.json
  observations/<leg>/<model-key>/<run-id>/
```

Every path is derived from the frozen pair binding; users cannot select a
model, leg, revision, output, target, timeout, or command on the CLI. The final
package embeds the authorization bytes as `execution-authorization.json` and a
public-safe qualification-evidence record. The ephemeral inlet is neither a
publication dependency nor part of the immutable result path.

Pair outputs remain:

```text
results/a0x/<leg>/<model-key>/<run-id>/
```

Dense/index assets remain pair-scoped external assets named by immutable hashes;
the package contains their locator, sizes, and hashes.

## Canonical guard launch

The execution authorization carries a public-safe `a0x-guard-launch-v2`
object containing:

- logical CCP and Python roles with exact SHA-256 values, never host-local
  absolute paths;
- `cwd_kind: repository_root` rather than a machine-specific cwd;
- the repository-relative child-script path and SHA-256;
- the pair-derived launch-descriptor role and path;
- a complete shell-free argv template whose only substitutions are the fixed
  tokens `{CCP}`, `{PYTHON}`, `{CHILD}`, and `{DESCRIPTOR}`;
- a bounded, non-secret environment template;
- resource and timeout fields.

The ignored launch descriptor contains the local token-to-path mapping. Before
claiming the attempt, the launcher verifies every resolved file hash, proves
that normalizing the resolved argv reproduces the authorized template, and
constructs a sanitized environment from the authorized template. The local
resolved argv commitment is retained only in the private observation. The
public package embeds the public-safe authorization bytes and never publishes
usernames, host-local paths, inherited environment values, container IDs, or
raw logs.

The canonical public commitment is the SHA-256 of UTF-8 canonical JSON using
sorted keys and compact separators. It is recomputed from the authorization
immediately before the durable claim and again immediately before `guard
exec`. The resolved command is normalized back to the same template at both
boundaries. Any unknown token, extra environment key, hash mismatch, argument
change, or normalization difference fails before the child.

Qualification evidence binds the CCP receipt's semantic `receipt_id` and the
SHA-256 of its serialized bytes as two independent values. A fresh verifier
must recover the receipt, validate the internal ID, and hash the raw bytes;
neither value is derived from or substituted for the other.

The approved guard argv uses the exact CCP grammar:

```text
commit-ci-preflight guard exec
  --admission-timeout-seconds 300
  --timeout-seconds 3600
  --resource-profile a0x-material
  --resource-workload-family latent-triz-a0x-v1
  --resource-executor native
  --resource-cache-state warm
  --resource-execution-mode native
  --resource-target-platform macos-arm64
  --resource-memory-limit-bytes 8589934592
  --
  {PYTHON}
  {CHILD}
  --launch-descriptor
  {DESCRIPTOR}
```

No shell syntax and no managed-cache pin flags are allowed. The runtime uses
private pair-scoped writable paths rather than manually pinning or altering CCP
cache state.

## Timeout design

- Outer CCP child timeout: exactly `3,600` seconds for every pair.
- Internal scientific budget: exactly `3,300` monotonic seconds.
- Reserved terminal/cleanup margin: `300` seconds.
- Admission wait: `300` seconds and distinct from child execution.

The child checks the internal deadline at every stage boundary and around every
model-forward iteration. Crossing it seals a `non_interpretable` timeout before
the outer guard deadline when possible. The outer `124` remains authoritative
if the child cannot seal in time. Resource watchdog, 8 GiB RSS ceiling, dense
caps, and cancellation rules remain independent and fail closed.

The timeout is an execution envelope, not an endpoint. It is identical across
all models and legs, so it does not introduce model-specific treatment.

## Component boundaries

### `a0x_material_contract.py`

Parses and validates the runtime inlet, canonical launch object, interpreter
manifest, qualification evidence, pair-derived paths, and timeout constants.
It performs no subprocess, model, target, or network action.

### `a0x_material_runtime.py`

Owns the private child lifecycle. It composes existing primitives in this
order:

```text
static preflight
model identity receipt
tokenizer and CPU-float32 model construction
target-free A0 or R1 activation
activation sealing
one-shot target-reader construction
exactly one target read
frozen A0 or R1 analysis
terminal sealing
package build and independent verification
protected-tree postflight
model release
```

The module accepts injected factories in synthetic tests. Production factories
are reachable only from the fixed child entrypoint.

### `scripts/a0x_material_child.py`

Accepts only `--launch-descriptor`. It verifies descriptor bytes, cwd, source
HEAD, pair, runtime, environment, and deadline before constructing a tokenizer
or model. It never invokes CCP.

### `scripts/a0x_material.py`

Accepts only one of the twelve fixed dossier paths. It validates the dossier,
authorization inlet, qualification evidence, exact CCP/Python/script hashes,
repository state, and canonical guard argv; writes the durable claim and
pre-run observation; then invokes exactly one real CCP `guard exec`.

## Qualification evidence

An `a0x-qualification-evidence-v1` record binds:

- qualification receipt ID and raw SHA-256;
- qualified Latent-TRIZ source HEAD and generation;
- exact CCP source commit, tree, path, version, and binary SHA-256;
- immutable public evidence branch and `.ccp/receipt.json` path;
- evidence commit, when published;
- zero raw logs, local usernames, container IDs, environment values, or secrets.

Before material use the local raw receipt must be validated as an authentic
Matrix V2 PASS and must hash to the evidence record. Publication verification
from a fresh clone must obtain the exact public evidence object and repeat the
same check. Missing or mutated evidence fails closed.

## Terminal behavior

The first terminal scientific outcome is authoritative. Cleanup failure is
recorded without rewriting that scientific outcome, except when the outer CCP
contract reports timeout, pressure, cancellation, internal failure, or cleanup
uncertainty; in that case the outer classification bounds the claim.

Before model construction, failure evidence records zero model loads and zero
target reads. After model construction but before target-reader construction,
failure evidence records model cleanup status and zero target reads. After the
reader reservation, its immutable receipt is retained even if open, hash,
parse, selection, or analysis fails.

No stage removes a claim, receipt reservation, staging residue, or terminal
package in order to make a retry possible.

## TDD and verification

Synthetic tests must prove:

- authorization/output separation and byte-identical package embedding;
- canonical argv recomputation and rejection of every mutated token;
- exact timeout values and rejection of model-specific overrides;
- exact CCP, Python, child-script, descriptor, source-HEAD, and environment
  bindings;
- correct A0/R1 dispatch without target capability during activation;
- one target read after activation and before analysis;
- timeout sealing at the internal boundary and authoritative outer `124`;
- model release after success and every post-load failure;
- immutable qualification-evidence and external-asset verification;
- cross-leg/model/run substitution rejection;
- all twelve dossiers remain independent and no pooling field is accepted;
- no synthetic test imports material model weights or opens protected targets.

The final offline gate includes focused tests, every A0X test, schema
cross-validation, compilation, documentation checks, diff checks, deterministic
regeneration in a disposable copy, and independent architecture/science review.

## Regeneration and stop boundary

Adding the production composition changes infrastructure members of both leg
freezes. After tests pass, regenerate:

1. the material execution contract;
2. A0 and A0-R1 implementation manifests;
3. both protected/freeze manifests;
4. all twelve approval dossiers;
5. the no-model verification receipt;
6. the documented hash ledger.

Regeneration must keep all dossiers at `approval_requested` and must report zero
model, tokenizer, target, CCP, Docker, network, and remote access.

Stop after reporting the exact hashes and independent review. A later exact
authorization is required for CCP candidate qualification, installation,
Latent-TRIZ qualification, and each material pair.
