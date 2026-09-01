# A0X Hosted Gate A — Task 11 Architecture, Security, and Supply-Chain Re-review

## Decision

**APPROVE for completion of Task 11 static qualification only.**

This re-review examined candidate commit
`3274e2381ff0f7bc6a4a5fab4c721dabf6d8b0e7`, tree
`90801d20408573297ea889c3764e56e3a25270a0`, and local candidate dossier
SHA-256
`0bda4f49cbd244b8dc0afa897b5ce74e069dda0206d480246394616d43f1fe99`.
No P0, P1, P2, or P3 finding remains in the reviewed scope.

This is not hosted qualification and does not authorize Task 12, GitHub access,
Gate B or Gate C, runtime materialization, model or tokenizer access, sealed
target access, or scientific execution. Those boundaries still require the
separate reviews and exact authorization stated in the candidate dossier.

## Closure of prior findings

The active verification-result schema
`schemas/a0x-gh-2.97.0-verification-result.schema.json` is now an
implementation trust input. Its raw SHA-256 is
`ae6b10ae31d9667a6a9c76ee219384d3c9bcb640d2098b006adc4be60be6f0d2`.
It appears in the canonical implementation path list and in both A0 and A0-R1
implementation inventories. Each freeze binds the corresponding regenerated
implementation hash: A0
`8fa41b1331d7747e1f48d31d0bd711de90ff15f02e9ccd6e4f488ea72364e961`
and A0-R1
`bbee27b5471de05f817395a65ffbe994188bac4b9f2ee6b745f6292f309f34df`.
The prior frozen-schema omission is therefore closed.

All three hosted quality lanes now explicitly select Python 3.11, assert the
observed interpreter version, and install
`requirements-schema.lock` with `--require-hashes`. The two repository and
two schema-cross-validation lanes preserve their explicit Python 3.11/3.12
selection and the same lock. The lock hash is
`0bbafebbe4fdb6028f5e8565eae397d18d6ace90e7e5e2c5b9472aa924162be7`.
The earlier mutable-preinstalled-`jsonschema` concern is closed.

The dossier now directly binds the verifier-policy fixture, material execution
contract, and shell-free verifier wrapper. It also records the semantic
no-model-receipt ruling as a local, hash-bound qualification ruling, not as
material or remote authorization.

## Security and provenance findings

The verifier reads the reviewed result schema, uses strict JSON parsing and
Draft 2020-12 validation, binds independent signer and source identities, and
refuses invalid or drifted signed-result fields. The wrapper accepts only
verifier-provided shell-free argument vectors, uses a scrubbed child
environment, and invokes Git by an absolute path. It is not executed by this
review.

Control paths are constrained below the repository root; symlink and traversal
inputs are refused. The verifier rehashes control inputs after the external
runner boundary, refuses pre-existing output, writes through an exclusive
regular temporary file, and fsyncs the result and parent directory. Tests cover
pre-run and post-run drift, output collision, invalid output, and one-shot
behavior.

The hosted workflow preserves exactly seven required lane providers:
`a0x-no-model`, `a0x-synthetic`, `documentation-audit`,
`repository-python311`, `repository-python312`,
`schema-cross-validation-python311`, and
`schema-cross-validation-python312`. Workflow permissions are empty by
default; lanes use `contents: read`, while only aggregation receives the
minimal attestation and identity permissions. Actions are full-commit pinned,
and workflow, action-manifest, lane-manifest, and requirements-lock bytes agree
with the dossier.

Current hosted Gate A and historical CCP evidence remain explicitly separated.
The current path does not reinterpret hosted identity as Gate C producer
identity. Legacy dispatch remains isolated behind the explicit historical
profile. The public dossier omits local paths, raw commands, raw logs,
credentials, and runtime locators.

## Verification performed

The following target-free checks passed on the reviewed candidate:

- focused Hosted Gate A and verifier suite: 24 tests;
- frozen no-model package verification: 11 tests;
- hosted Gate A deterministic ladder: 190 tests, 1 documented historical skip;
- schema cross-validation: 155 tracked pairs and 19 rejected mutations;
- documentation audit and `git diff --check`;
- independent recomputation of all 13 canonical dossier inputs and all 17
  regenerated artifact hashes.

No model, tokenizer, sealed target, network operation, GitHub operation, CCP,
Docker, or material runtime action occurred.

GitNexus was checked first but was not indexed for this candidate. Re-indexing
would mutate repository metadata and was outside this read-only review, so the
review used bounded source and deterministic-test inspection instead.

## Remaining boundary

Task 12 remains a separate external and material gate. A later operator must
re-establish the exact live commit, tree, ruleset, workflow outcome, and
authorization bindings before any material action. This review makes no claim
that those future conditions have been met.
