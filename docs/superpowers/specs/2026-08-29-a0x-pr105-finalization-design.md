# A0X PR #105 Finalization Design

## Status

Approved in chat on 2026-08-29. This specification governs only the final
integration and exact-head qualification of PR #105. It does not authorize a
CCP heavy run, model or tokenizer construction, sealed-target access, receipt
publication, push, PR mutation, or merge.

## Goal

Integrate the migrated trusted-base policy from public
`main@4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08` into A0X PR #105 without
changing any frozen scientific artifact, then produce one clean exact head that
is ready for a separately authorized CCP qualification.

## Established facts

- PR #105 head `4aee4698f5c59101b1f3292519f10ae802629bf7` already has a terminal local
  CCP `PASS`. Receipt-file SHA-256:
  `08b1a8f1c08d2ab9784c95acd3b452c218b76108744a129cd6b8df2aef52c447`.
- The hosted receipt failure predates the trusted-base migration and does not
  indicate a repository-check failure.
- Public `main` and the PR head contain the same `.commit-ci-policy-v2.toml`
  blob, object ID `8a40d48220723373156f9d99fc4e433ed1beaa70`.
- A dry integration exposes only two content conflicts:
  `docs/log.md` and `tests/test_exp002_publication_verify.py`.
- The A0X implementation-bound file set has no changes between correction
  anchor `6b8c8e3491b24fa4717b2f4faa8700b007c48892` and PR head `4aee4698...`.
  The protocol, material contract, two freezes, and twelve approval-requested
  dossiers therefore remain valid and must not be regenerated merely because
  the integration commit changes.

## Integration strategy

Use a normal merge of current public `main` into the feature branch. Do not
rebase, force-push, squash locally, or create a replacement PR. The repository
ruleset may still squash the completed pull request into `main`; the temporary
feature-branch merge commit does not weaken linear public history.

Resolve the two conflicts as follows:

1. `docs/log.md`: retain a single valid front matter block and both historical
   chronology entries in reverse chronological order.
2. `tests/test_exp002_publication_verify.py`: retain three distinct claims:
   - tracked package and locator bindings pass without reading ignored dense
     assets;
   - full verification passes against deterministic synthetic dense assets;
   - missing or mutated dense assets still fail closed.

Take the new `main` implementation of
`scripts/exp002_publication_verify.py`. Preserve the migrated policy blob
byte-for-byte.

## Scientific immutability boundary

The integration must leave byte-identical:

- `experiments/a0x-six-model/material-execution-contract.json`;
- both A0X implementation and protocol documents;
- both A0X freeze manifests;
- all twelve approval dossiers;
- `results/a0x/preexecution/a0x-no-model-verification-receipt.json`;
- every implementation-bound A0X source, schema, fixture, and test file.

The final audit compares the complete protected path set against
`4aee4698...`. Any unexpected byte difference is blocking and requires a new
design decision instead of silent regeneration.

## Verification sequence

Run all verification from a clean, isolated, no-hardlink clone of the final
candidate:

1. conflict-focused EXP-002 publication tests;
2. A0X Matrix-plan binding tests;
3. frozen-package and complete A0X aggregate tests;
4. schema cross-validation;
5. full repository check;
6. documentation audit and diff check;
7. exact protected-path byte comparison against `4aee4698...`;
8. policy/plan/producer hash ledger verification.

No Docker or CCP heavy command is part of this preparatory sequence. A failure
is corrected with TDD and the sequence restarts from the affected focused
test. The work stops after reporting the final commit, tree, policy, plan,
producer, immutable artifact hashes, and the separately reviewable exact-head
authorization envelope.

## Qualification and publication boundary

After the preparatory sequence passes, request one new authorization bound to
the final commit and tree, candidate CCP executable SHA-256
`c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`,
profile `matrix-v2-legacy-v1`, generation `1`, maximum one run, and the three
reviewed plan digests.

Only a terminal, verified exact-head PASS permits receipt publication and PR
update. Post-qualification status wording must not modify that exact head. A
small documentation-only follow-up after merge records the final receipt and
merge commit through the lightweight documentation path.

## Rejected alternatives

- Rebase or force-push: rewrites the 52-commit evidence history.
- Replacement PR: duplicates more than 31,000 added lines and breaks existing
  review and evidence links.
- Regenerate A0X freezes and dossiers after a non-bound documentation/test
  integration: changes scientific commitments without a scientific cause.
- Add another orchestration subsystem: increases the failure surface while
  existing tests already express the required invariants.

## Completion criteria

The preparatory tranche is complete only when the integrated clone is clean,
every listed verification passes, all protected A0X bytes match
`4aee4698...`, and the exact authorization envelope is reported. The overall
closure is complete only after a separately authorized CCP PASS, evidence
publication, green GitHub gates, squash merge, fresh-clone verification, and a
documentation-only final status update.
