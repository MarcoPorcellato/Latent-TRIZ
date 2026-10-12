# A0X N3 Target-Free Schema Reconciliation Proposal

**Status: DRAFT — NOT APPROVED.** This proposal does not amend the canonical
plan, establish N3 acceptance, authorize target access, authorize regeneration,
or grant any material or remote action.

## Purpose

Resolve the conflict between the current N3 requirement to run the complete
schema cross-validation command and the A0X boundary that forbids opening
sealed targets before the authorized analysis boundary. Preserve the scientific
protocol and one-read rule while making the engineering evidence precise about
what it does and does not validate.

## Evidence bindings reviewed

- Isolated clone: `.a0x-runtime/workspaces/a0x-first-result-4f801f03`
- Source HEAD: `7dbb04d0eecd1ab7d40f4dd3a40f5253affa5367`
- Source tree: `14b75e50c23c22cd8b21a506b72fe2af3f0abd21`
- Canonical execution plan in the preserved primary checkout:
  `docs/superpowers/plans/2026-09-16-a0x-first-result-autonomous-execution.md`,
  SHA-256 `cdbfa42c1bfed6c21ab002014cfc5c4d2568ad7504b489656af4aab1c1eda54c`
- A0 protocol SHA-256:
  `42e252b21dd9f1d6b793be304bfe708d2d9324e8e08ffe1d1915e7f01b75f586`
- A0-R1 protocol SHA-256:
  `32d8bbfcbd76e38d51a2eff012c22e65bfe0c1eca4f6d0bf345f309777df4b52`
- A0 freeze SHA-256:
  `6c7e812e2603a37ef365a804797d414f9c28d366e2a1a306a22b61548f0472c0`
- A0-R1 freeze SHA-256:
  `87aaa02cc496ae2bb468a32938de1c563459a765234c201e39a9265da5d3f36d`
- Existing validator source `scripts/schema_cross_validate.py` SHA-256:
  `166df74d7a8925c30b027847f55c3b7e81efa1c6e4d85b4190cfb9f737a03aef`

These are the bytes observed for this proposal. Reverify all bindings before
any implementation, regeneration, commit, or acceptance decision.

## Current contract conflict

The canonical plan's N3 row requires the full target-free A0X suite, synthetic
contract check, schema cross-validation, documentation audit, and diff check;
it says any incomplete test is `NO-GO`. The current schema command is not
target-free: its static input table includes four actual protected target
JSONL paths. The unchanged `a0x-no-model-verify` and `a0x-synthetic-verify`
aggregates also include test paths with whole-repository copies/replays that
are not safe to run until each such path is replaced by an equivalent bounded
synthetic fixture and independently audited.

The bounded source inventory of the current validator found:

- 211 schema-definition files;
- 155 declared `(schema, instance)` pairs and 129 distinct referenced schemas;
- 4 protected target instances;
- 14 additional paths whose names suggest authorization, sealed-key, private,
  mapping, or target-key roles and whose public/safe role is unresolved;
- 137 remaining path candidates that are not yet certified public merely by
  their filenames;
- 3 existing in-memory synthetic A0X positional instances and 12 positional
  mutations.

The 4 protected instances are:

- `data/a0/procedural-targets/calibration-targets.jsonl`
- `data/a0/sealed-targets/targets.jsonl`
- `data/a0r1/targets/calibration.jsonl`
- `data/a0r1/targets/sealed.jsonl`

The 14 unresolved paths are:

- `experiments/exp001-comparative-reference/additional-model-authorization.json`
- `experiments/exp001-comparative-reference/execution-authorization.json`
- `experiments/exp001-comparative-reference/next-model-authorization.json`
- `experiments/exp001-comparative-reference/qwen-download-authorization.json`
- `experiments/exp001-reference-integrated/execution-authorization.json`
- `experiments/a0r2-independent-model/sealed-execution-approval-dossier.json`
- `results/a0r2/preexecution/smollm2-360m-f8027fd0/sealed-execution-authorization.json`
- `results/a0r2c1/preexecution/sealed-execution-authorization.json`
- `experiments/exp002-auto/combined-target-key-template.json`
- `experiments/exp002-qwen3-followup/transfer-target-key-template.json`
- `results/exp002/preexecution/sealed-key-access-template.json`
- `results/exp001-comparative/pythia-70m-e93a9faa-pythia-20260818-01/sealed-key-access.json`
- `results/exp001-comparative/qwen3-0.6b-da87bfb-qwen3-20260818-01/sealed-key-access.json`
- `results/exp001-comparative/smollm2-360m-f8027fd0-smollm2-20260818-01/sealed-key-access.json`

No protected or unresolved file was opened, hashed, stat'ed, copied, or
materialized for this audit. Path classification is conservative triage, not
content verification.

## Proposed N3 acceptance amendment

If the operator accepts this proposal, revise only the N3 engineering
acceptance wording in a versioned amendment to the canonical plan. Name the new
profile `A0X target-free schema profile v1` and require a machine-readable,
closed-world coverage manifest that records every schema and instance pair
from the bound validator table, its role, disposition, reason, and evidence.

The profile must:

1. Validate all 211 schema-definition files and retain the existing validator
   checks that do not read instance files.
2. Bind the complete filesystem read closure, not only `VALIDATION_PAIRS`:
   every schema-definition path, declared instance path, direct literal
   `ROOT / path` read used for mutation construction, fixture/source file used
   to construct an instance, and every local schema-reference dependency.
   The manifest must be regenerated from reviewed source analysis and fail if
   the source's read set changes.
3. Read an instance only when its exact path is explicitly allowlisted in the
   coverage manifest as an approved public, target-free input. Do not infer
   public status from a filename, repository tracking, or an existing schema
   pair. A candidate whose role is not affirmatively established must be
   explicitly excluded from this profile; it is not an implicitly public
   input.
4. Mark the four protected target instances `deferred_protected` and
   `UNVERIFIED`; do not open, hash, copy, materialize, or validate their bytes
   before the single authorized analysis-boundary read.
5. Mark the 14 unresolved paths `excluded_sensitive_role_unverified` and fail
   closed if any is read or treated as public. This is a complete scope
   exclusion, not a claim about file contents; they stay outside the instance
   profile unless a separate role review changes the exact allowlist.
6. Include synthetic valid and invalid instances for the protected target
   schemas, retaining the current three positional examples and 12 mutations
   and adding JSON-Schema positive/negative coverage where absent. These prove
   validator behavior only, not conformance of the actual protected files.
7. Reject unknown paths, unlisted instances, duplicate pairs, missing schema
   definitions, and manifest drift. Tests must intercept prohibited reads and
   demonstrate rejection before opening the prohibited input; approved schema
   and source reads remain within the manifest-bound closure.
8. Emit a report that distinguishes `validated_public`, `validated_synthetic`,
   `deferred_protected`, and `excluded_sensitive_role_unverified`. Never label
   the result full repository schema validation or imply actual-target
   conformance.
9. Disable all network and lazy acquisition. Schema `$ref` resolution must be
   limited to the exact local, manifest-bound closure; remote or unapproved
   references fail before retrieval. Never fetch missing Git objects.
10. Preserve the frozen A0/A0-R1 protocol, target order and hashes, selection,
   uniqueness rules, one-read analysis boundary, stopping rules, and all
   historical artifacts byte-identically. Do not move A0-R1 target validation
   into A0 Gate C.
11. Require the safe target-free test ladder and docs audit to pass. Do not call
   a canonical aggregate safe until every transitive test module and child
   process has been audited for target opens, whole-root copies, lazy fetch,
   and remote/network fallback.

N3 after adoption would mean only that the amended engineering profile passed.
It would not prove actual protected-instance schema conformance. The first A0
Gate C may validate the A0 target rows from the already-authorized single read
only if the existing reviewed Gate C contract already permits that check; any
new production behavior or additional read needs separate review and
authorization. A0-R1 protected targets remain outside this A0 attempt.

## Review and authorization sequence

1. Operator decides whether to adopt this exact acceptance amendment.
2. After adoption is authorized, Luna implements the versioned plan amendment,
   closed-world manifest, target-free verifier/tests, and safe fixture
   corrections under TDD. No production Gate C changes.
3. Sol reviews scope, fixture equivalence, complete path classification,
   fail-closed behavior, and absence of indirect protected reads. Astra reviews
   only if a new critical ambiguity or trust-boundary decision appears.
4. Re-run only the approved target-free tests and record exact command/output
   evidence. Keep N3 `NO-GO` if any path is unresolved or any required test is
   incomplete.
5. After review and tests, request a separate exact authorization for the
   implementation-anchor commit. Verify the exact commit and tree.
6. Only after that anchor commit, prepare a separate exact authorization for
   derivative regeneration, binding the new committed HEAD/tree, protected
   inputs, expected outputs, and overwrite policy. Verify resulting hashes and
   tests; then request any separate packaging commit authorization.
7. Only after N3 evidence is complete, prepare the next exact Hosted Gate A
   authorization packet. Hosted Gate A, capture, P0, Gate B, Gate C, result
   publication, and GitHub mutations remain separately gated.

## Non-adoption / stop conditions

Until the operator explicitly adopts the amendment, the canonical N3
acceptance remains unchanged and N3 remains `NO-GO`. This draft is not a waiver
or a substitute for schema cross-validation. Do not run the unsafe aggregate,
read protected targets, regenerate derived artifacts, commit, access models or
tokenizers, run CCP/Docker, or perform remote mutations on the basis of this
proposal.
