# A0X Runtime Binding Cycle Correction Design

**Status:** approved in chat for specification; implementation pending review  
**Date:** 2026-08-29  
**Scope:** private A0X runtime packaging and its synthetic verification only

## Problem statement

The frozen A0X design requires an execution authorization to bind the exact
SHA-256 of its launch descriptor. The current private launch descriptor also
binds the exact SHA-256 of that authorization. The resulting byte-level cycle
cannot be materialized deterministically:

```text
authorization --SHA-256--> launch descriptor
      ^                         |
      +----------SHA-256--------+
```

This is a protocol-construction defect rather than a model, tokenizer, CCP, or
resource failure. The outer executor enforces the authorization-to-descriptor
edge, while the production adapter and child enforce the reverse edge. The
synthetic tests cover those components separately and therefore never prove
that one real runtime bundle can satisfy both edges simultaneously.

No material run may begin until a real bundle can be constructed, validated by
the outer executor and child, and qualified at one exact repository head.

## Goals

1. Make the private runtime bundle deterministically constructible.
2. Preserve one exact operator-approved authorization as the trust root.
3. Preserve exact descriptor, contract, CCP, Python, child-script, source-head,
   qualification-receipt, dossier, pair, timeout, and resource bindings.
4. Reject any byte drift before model construction or sealed-target access.
5. Provide one target-free, model-free preparer for all twelve A0X pairs.
6. Prove the complete construction and verification path with TDD.

## Non-goals

- No change to the A0X questions, selections, targets, statistical methods,
  dense bounds, model revisions, model cards, or scientific interpretation.
- No model or tokenizer load, target read, CCP heavy command, network access,
  result publication, or retry authorization.
- No weakening of the per-pair, one-attempt, exact-head approval boundary.
- No general refactor of A0X or unrelated cleanup.

## Considered approaches

### A. One-way authorization root with a path-only descriptor reference

The private descriptor names the pair-derived authorization path without
embedding its hash. The authorization continues to embed the descriptor's
exact hash. The child hashes its own descriptor bytes and compares them with
the authorization before exposing any material capability.

This is the selected approach. It is the smallest change, follows the existing
operator-authorization model, and keeps the complete public authorization
schema and commitment profile intact.

### B. Third runtime manifest

A third document could bind authorization and descriptor hashes. This adds a
new trust root, schema, locator, commitment, verifier, and operator-facing hash
without strengthening the existing authorization boundary. It is rejected as
unnecessary complexity.

### C. Projection hash

The descriptor could bind a domain-separated projection of the authorization
that omits the descriptor hash. This preserves a form of mutual commitment but
introduces normalization rules and a second authorization commitment that are
easy to misunderstand or implement inconsistently. It is rejected for this
milestone.

## Selected trust chain

The corrected chain is acyclic:

```text
operator approval
      |
      v
execution authorization A --SHA-256--> launch descriptor L
      |                                  |
      |                                  +--> pair-derived authorization path
      |                                  +--SHA-256--> material contract
      |                                  +--SHA-256--> child and Python
      |
      +--> dossier commitment D
      +--> exact source HEAD and qualification receipt
      +--> exact CCP, Python, child, pair, attempt, and resource envelope
```

The authorization remains the injected trust root. Its canonical commitment
and raw SHA-256 are carried into attempt claims and terminal artifacts. The
descriptor does not authorize the authorization; it only supplies the fixed
private path from which the already operator-approved authorization is read.

## Private descriptor v2

The descriptor profile changes from
`a0x-material-child-descriptor-v1` to
`a0x-material-child-descriptor-v2`.

Its `runtime_files` list is replaced by two fields with distinct semantics:

```json
{
  "authorization_reference": {
    "role": "authorization",
    "path": ".a0x-runtime/authorizations/<leg>/<model>/<run-id>.json"
  },
  "material_contract": {
    "role": "material_contract",
    "path": "experiments/a0x-six-model/material-execution-contract.json",
    "sha256": "<exact raw SHA-256>"
  }
}
```

The authorization path must equal `derive_runtime_paths(pair)` exactly. It may
not be absolute, user-selected, redirected through a symlink, or overridden at
the command line. The material contract remains byte-bound.

## Verification order

The target-free outer path must perform these checks before claiming or
launching the attempt:

1. Read and schema-validate the pair-derived execution authorization.
2. Verify its source HEAD, dossier commitment, material contract, CCP identity,
   qualification evidence, pair, attempt, and one-shot boundary.
3. Read the pair-derived descriptor and compare its raw SHA-256 with the hash
   in the authorization.
4. Validate the runtime mapping and exact CCP, Python, child, and descriptor
   bytes.
5. Perform the fresh guard preflight and create the immutable attempt claim.
6. Recheck all bound bytes and launch one shell-free `guard exec`.

The child must then:

1. Read only the fixed descriptor argument.
2. Validate descriptor profile v2, source HEAD, pair, environment, execution
   envelope, child, and Python.
3. Read the authorization from its pair-derived path and the contract from its
   fixed repository path.
4. Validate the authorization and contract semantics and raw contract hash.
5. Hash the descriptor bytes it received and require equality with
   `authorization.guard_launch.launch_descriptor.sha256`.
6. Only after all checks pass, assemble the production dependencies. Model
   construction and target access remain behind their existing lifecycle
   gates.

## Deterministic runtime preparer

A new target-free preparer will build one private pair bundle in this order:

1. Verify the clean exact source HEAD and fixed dossier.
2. Verify the material contract, qualification receipt, CCP executable, Python
   executable, and child script.
3. Create descriptor v2 without an authorization content hash.
4. Compute the descriptor raw SHA-256.
5. Create the execution authorization containing that descriptor hash and the
   operator-supplied authorization ID and attempt ID.
6. Create the private runtime-role mapping bound to the same descriptor hash.
7. Run target-free validation through the real outer and child validators.
8. Report the exact authorization, descriptor, mapping, receipt, dossier, and
   contract hashes, then stop before `guard exec`.

The preparer must be idempotent only while no private bundle exists. Existing
authorization, descriptor, mapping, claim, observation, workspace, or output
paths cause a fail-closed refusal; it never overwrites or offers a retry.

Materialization of an authorization whose status is `authorized` requires an
explicit operator instruction naming the exact pair and attempt. The preparer
does not itself grant permission to run. A separate later authorization must
bind the resulting raw authorization SHA-256 and the exact qualified source
HEAD before the argument-free material target may run.

## TDD and regression coverage

Implementation starts with failing tests that demonstrate:

1. The current v1 bundle cannot be materialized because of the reciprocal raw
   hashes.
2. A descriptor-v2 bundle can be constructed in one deterministic pass.
3. The same real bundle passes the outer executor's static validation and the
   child's pre-material validation with injected inert dependencies.
4. Descriptor drift is rejected by both outer and child validation.
5. Authorization drift is rejected before and after guard review.
6. Contract, mapping, qualification receipt, CCP, Python, child, source HEAD,
   pair, attempt ID, output occupancy, and path drift remain fail-closed.
7. A second preparation attempt refuses to overwrite the first bundle.
8. No target, model, tokenizer, Docker, network, or CCP heavy command is
   reached by preparation or tests.

The earlier component fixtures must be replaced or supplemented by one
constructible end-to-end runtime-bundle fixture. Synthetic placeholder hashes
may remain only in tests that do not claim bundle constructibility.

## Expected code and documentation surface

The implementation is expected to remain limited to:

- `src/latent_triz/a0x_material_contract.py`
- `src/latent_triz/a0x_ccp_executor.py`
- `src/latent_triz/a0x_production_adapter.py`
- `scripts/a0x_material_child.py`
- one small runtime-preparation module and CLI
- focused A0X tests and shared test support
- the A0X campaign specification, problem/solution register, and persistent
  checkpoint
- regenerated A0X contract, implementation, freeze, dossier, and no-model
  receipt artifacts only where their existing hash graph requires it

The public execution-authorization profile remains
`a0x-execution-authorization-json-v2`. If implementation proves that its schema
must change, work stops for a revised design rather than silently introducing
v3.

## Qualification and material stop boundaries

After implementation and full target-free verification:

1. Commit the correction locally in the isolated clone.
2. Regenerate and report all changed hash-bound artifacts.
3. Stop for exact-head CCP qualification authorization.
4. After a terminal positive qualification receipt, publish only under a
   separate explicit authorization.
5. Materialize one SmolLM2-360M A0 runtime bundle and report its exact hashes.
6. Stop for the final one-shot material authorization bound to that exact
   authorization SHA-256.

No existing model or target authorization is reusable after the source HEAD
changes. No failed or consumed material attempt may be retried without a new
authorization.

## Acceptance criteria

The correction is ready for exact-head qualification only when:

- one real runtime bundle is constructible without a hash fixed point;
- all new tests were observed failing before implementation and then pass;
- the focused A0X suite, full repository suite, schema cross-validation, and
  documentation audit pass without material access;
- an independent review finds no weakened binding or new selector;
- all regenerated hashes and the exact local HEAD are recorded;
- the primary worktree and every historical receipt, result, model, target,
  cache, and authorization remain untouched.

