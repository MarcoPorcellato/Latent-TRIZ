# A0X Hosted Gate A Design

**Status:** design approved; specification ready for operator review
**Base:** public `main` `bc9b7ad66464eced774c1bfd3123c5bc54b10384`, tree `4c1fb980fc687a4f26cf561e0c93d1a04546e491`
**Scope:** replace only A0X repository qualification with signed GitHub-hosted evidence; keep CCP as the local Gate C coordinator
**Material boundary:** this design authorizes no Gate B preparation, model or tokenizer construction, target access, Gate C execution, CCP heavy command, publication, or scientific claim

## Purpose

Remove the structural dependency between A0X Gate A and a local CCP Matrix
receipt without weakening the exact-source, fail-closed, and offline-verifiable
boundaries required before Gate B.

The current public repository correctly uses standard GitHub-hosted runners for
ordinary public CI. The A0X material path still accepts only a local CCP
qualification receipt, however. A green hosted pull-request workflow therefore
cannot open Gate B, even when it executes the required repository checks. The
result is redundant local compute and an evidence format mismatch.

The correction makes Gate A a signed hosted-source qualification. Gate C keeps
the existing exact CCP executable, admission controls, resource watchdog,
shell-free guard, and one-shot material execution. No scientific rule changes.

## Authoritative external guidance

This design follows these primary sources:

- GitHub requires a `workflow_dispatch` reference to be a branch or tag, not an
  arbitrary commit SHA. Exact-main qualification therefore uses the `push`
  event on protected `main`, not a manual dispatch presented as exact-head:
  <https://docs.github.com/en/rest/actions/workflows>.
- GitHub Artifact Attestations are available for public repositories and use
  `contents: read`, `id-token: write`, and `attestations: write` for binary or
  file provenance:
  <https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations>.
- GitHub documents offline verification using an attestation bundle and an
  imported trusted-root file:
  <https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline>.
- SLSA verification requires more than the presence of provenance. Consumers
  compare the subject digest, signature, predicate type, builder identity,
  canonical source, build type, and external parameters against frozen
  expectations:
  <https://slsa.dev/spec/v1.2/verifying-artifacts>.
- In-toto separates the authenticated envelope, subject-binding statement, and
  predicate. Consumers verify the envelope before interpreting the predicate:
  <https://github.com/in-toto/attestation/blob/main/spec/v1/envelope.md>.

The project does not claim a SLSA level. It uses GitHub's signed provenance and
the SLSA verification model as concrete integrity and expectation-checking
guidance. Implementation requires the current standard predicate URI
`https://slsa.dev/provenance/v1`. That URI is the canonical SLSA provenance v1
predicate identifier; implementation fixtures must additionally pin the exact
statement schema and verifier JSON contract accepted at freeze time. Neither
may drift to an implicit "latest" shape or be inferred from a retired SLSA
documentation URL.

## TRIZ resolution

### Ideal Final Result

Every protected `main` revision that matters to A0X automatically produces a
small signed qualification object. Gate B verifies it offline against frozen
expectations. No operator relabels a check, no local process repeats ordinary
public CI, and no hosted workflow can authorize material execution by itself.

### Functional analysis and trimming

CCP currently performs two unrelated useful functions:

1. repository qualification before Gate B;
2. local resource coordination and process containment at Gate C.

The first function duplicates free hosted CI and has caused repeated operational
delays. The second function remains necessary because model execution requires
local CPU, memory, cleanup, and one-shot coordination. The correction trims only
the first function. It does not remove or weaken CCP's Gate C function.

### Contradictions and inventive principles

| Contradiction | Resolution |
| --- | --- |
| Avoid redundant local CI while preserving exact auditable qualification | **Segmentation**: hosted Gate A and local Gate C become independent functions. |
| Publish durable evidence without granting repository write access to test jobs | **Local quality**: only the attestation step receives `id-token: write` and `attestations: write`; no job receives `contents: write`. |
| Verify hosted provenance while Gate B remains offline | **Intermediary**: an attested canonical manifest plus imported Sigstore bundle and trusted root bridge the boundary. |
| Prevent optimistic interpretation of missing evidence | **Inversion**: verification starts at rejection and admits only a complete exact match. |
| Avoid discovering binding errors after runtime materialization | **Prior action**: freeze workflow, action SHAs, schemas, commands, repository, source, and expected lanes before the hosted run. |
| Preserve actionable failures without raw-log publication | **Feedback**: machine-readable reason codes identify the failed signature, subject, workflow, source, lane, or hash binding. |
| Let protected source produce its own qualification | **Self-service**: `push` to `main` launches the qualification automatically. |

## Gate model

The campaign keeps three non-interchangeable operator stops:

```text
A — signed hosted qualification of one exact protected-main commit
B — offline verification and preparation of one exact pair/attempt bundle
C — one local material attempt under the exact CCP guard
```

Gate A produces evidence only. It never creates a runtime bundle. Gate B
verifies Gate A and creates target-free runtime bindings only after a separate
pair-specific authorization. Gate C requires another authorization bound to the
prepared authorization bytes. No success at one gate implies the next gate.

## Hosted Gate A workflow

Create `.github/workflows/a0x-hosted-gate-a.yml` with only:

```yaml
on:
  push:
    branches: [main]
```

The workflow must not accept `pull_request`, `pull_request_target`,
`workflow_run`, `workflow_dispatch`, `repository_dispatch`, or reusable caller
inputs. A rerun is not fresh evidence and `GITHUB_RUN_ATTEMPT` must equal `1`.
Any failed, cancelled, skipped, or rerun qualification remains terminally
ineligible. A corrective source commit and a new protected-main push are needed
for a new qualification.

Workflow-wide permissions are `{}`. Check jobs receive only `contents: read`.
The final provenance job receives exactly:

```yaml
permissions:
  contents: read
  id-token: write
  attestations: write
```

No job receives `contents: write`, `actions: write`, `checks: write`,
`statuses: write`, `pull-requests: write`, `packages: write`, or repository
secrets. `artifact-metadata: write` is also excluded because the manifest is
not published to a registry. The ephemeral `GITHUB_TOKEN` still exists, but it
has only the explicitly declared job permissions. No user-configured secret is
referenced or exposed. Every external action is pinned to a complete reviewed
commit SHA. Mutable tags are forbidden in committed workflow bytes.

Concurrency is keyed by exact `${{ github.sha }}` with cancellation disabled.
One source revision cannot cancel or overwrite another revision's evidence.

### Required lanes

The exact protected-main revision runs these target-free lanes:

1. repository check on Python 3.11;
2. schema cross-validation on Python 3.11;
3. repository check on Python 3.12;
4. schema cross-validation on Python 3.12;
5. A0X frozen/no-model verification;
6. A0X synthetic verification;
7. documentation audit.

The PR-diff scientific-artifact audit is deliberately not reused: its contract
requires a pull-request changed-file set and has no valid push-main input. The
complete repository check and the dedicated A0X frozen/synthetic lanes provide
the full-tree target-free validation for Gate A. No empty or synthetic PR diff
may be invented.

Each lane checks out `${{ github.sha }}` with `persist-credentials: false`,
asserts `HEAD == GITHUB_SHA`, records `HEAD^{tree}`, and writes a small canonical
lane receipt only after its command succeeds. The compact receipt is exported
as the exact job-output key `gate_a_lane_receipt`; it is canonical compact JSON
encoded as unpadded base64url and limited to 4,096 decoded bytes. It is not
uploaded as a separate artifact. Repository lanes install from a complete
hash-locked `requirements-schema.lock` using
`python -m pip install --require-hashes -r requirements-schema.lock`.
The lock must contain hashes for every accepted distribution and transitive
dependency; a version-only lock is insufficient. No lane loads a model,
constructs a material tokenizer, reads a sealed target, downloads a model, or
performs scientific scoring.

The two repository lanes run `python scripts/repository_check.py`; the two
schema lanes run `python scripts/schema_cross_validate.py`. Each Python 3.11
and 3.12 lane independently installs the same hash-locked schema environment.
This preserves the four-runtime-check parity of the qualification being
replaced rather than collapsing schema validation to one interpreter.

Lane receipts contain no logs, environment dump, username, local path,
container identifier, token, secret, or private target detail. The final job
decodes the bounded job outputs, validates them with trusted code from the exact
protected-main source, and refuses oversized, duplicate, missing, extra,
malformed, or non-success lanes. Only the final aggregate manifest is uploaded
as a workflow artifact. Lane identifiers are strictly sorted and each lane
receipt must independently bind the same source HEAD and tree. Command stdout
is never used as receipt content.

## Canonical qualification manifest

The final job writes one canonical UTF-8 JSON file with sorted keys, compact
separators, a trailing newline, and no duplicate or unknown fields. Its profile
is `a0x-hosted-gate-a-evidence-v1`.

Required public-safe fields:

```json
{
  "artifact_class": "a0x-hosted-gate-a-evidence",
  "evidence_profile": "a0x-hosted-gate-a-evidence-v1",
  "repository": "MarcoPorcellato/Latent-TRIZ",
  "event": "push",
  "ref": "refs/heads/main",
  "qualified_source_head": "<40-hex>",
  "qualified_source_tree": "<40-hex>",
  "workflow": {
    "path": ".github/workflows/a0x-hosted-gate-a.yml",
    "raw_sha256": "<64-hex>",
    "run_id": "<positive integer>",
    "run_attempt": 1
  },
  "inputs": {
    "requirements_schema_lock_sha256": "<64-hex>",
    "action_pin_manifest_sha256": "<64-hex>",
    "lane_manifest_sha256": "<64-hex>"
  },
  "required_lanes": [
    {"id": "repository-python311", "receipt_sha256": "<64-hex>", "status": "PASS"},
    {"id": "schema-cross-validation-python311", "receipt_sha256": "<64-hex>", "status": "PASS"},
    {"id": "repository-python312", "receipt_sha256": "<64-hex>", "status": "PASS"},
    {"id": "schema-cross-validation-python312", "receipt_sha256": "<64-hex>", "status": "PASS"},
    {"id": "a0x-no-model", "receipt_sha256": "<64-hex>", "status": "PASS"},
    {"id": "a0x-synthetic", "receipt_sha256": "<64-hex>", "status": "PASS"},
    {"id": "documentation-audit", "receipt_sha256": "<64-hex>", "status": "PASS"}
  ],
  "overall_status": "PASS"
}
```

The final job uses GitHub's standard build-provenance mode to attest exactly
this raw manifest file. A custom predicate is unnecessary: the subject is the
manifest, while GitHub's signed provenance supplies builder, repository,
workflow, event, ref, and source identity. The verifier checks both layers.

The manifest is also uploaded as a workflow artifact for transport. The
workflow artifact is not the trust root; the attestation subject digest and
signature are. The raw manifest SHA-256, uploaded archive digest, attestation
subject digest, and later Gate B verification-receipt SHA-256 are distinct and
must never be substituted for one another. The GitHub Artifacts API digest is
the digest of the uploaded artifact archive, not automatically the digest of
the JSON file inside it. Before durable capture, an expired, deleted, or
unavailable artifact is `NO-GO`. After the exact manifest, bundle, trusted
root, and transport metadata are preserved, later transport expiration does
not change those captured bytes or their signature status.

## Durable evidence package

The hosted workflow must not push an evidence branch. After a terminal PASS, a
separately authorized operator retrieves and preserves exactly:

```text
hosted-gate-a-evidence.json
hosted-gate-a-attestation.bundle.jsonl
github-trusted-root.jsonl
hosted-gate-a-transport.json
```

The first three files are immutable cryptographic inputs. The fourth is a
canonical correlation record captured from the GitHub API. It records
`artifact_id`, `run_id`, `run_attempt`, `head_sha`, archive digest, size,
`created_at`, `expires_at`, and `captured_at`; it is never an authenticity root.
Capture verifies the archive digest and internal raw manifest hash before the
four bytesets are accepted. No file contains raw logs or host-local identifiers.

`hosted-gate-a-transport.json` is validated before archive or manifest
acceptance by `schemas/a0x-hosted-gate-a-transport.schema.json`. The strict
schema uses `additionalProperties: false`, bounded strings, exact integer and
timestamp types, and the canonical fields `artifact_id`, `run_id`,
`run_attempt`, `head_sha`, `archive_digest`, `archive_size_bytes`, `created_at`,
`expires_at`, and `captured_at`.

Hard size ceilings are part of the provider contract: 32 KiB for the manifest,
1 MiB for the attestation bundle, 2 MiB for the trusted root, 16 KiB for
transport metadata, and 32 KiB for the later Gate B verification receipt.
Excess bytes fail before parsing or output.

A separate authorization may publish those exact bytes only on
`hosted-evidence/<qualified-source-head>`. The branch is durable distribution,
not the authenticity root. A dedicated ruleset preventing force-push and
deletion of `hosted-evidence/**` is required before first publication. If the
platform cannot provide that rule, publication requires a new explicit
authorization that records the missing durability control as a limitation.

## Offline verification at Gate B

Gate B accepts a provider-neutral `gate_a_evidence` input. The current CCP
receipt format remains valid only for explicitly historical packages. New A0X
dossiers require provider `github-hosted-attestation-v1` and reject a CCP
receipt substituted into the new profile.

The current verifier candidate observed during design is GitHub CLI
`2.97.0 (2026-07-31)`, executable SHA-256
`6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c`.
The public contract binds this as role `github_cli_verifier`, not as a
host-local absolute path. Before implementation freeze, these bytes and CLI
help must be reverified; any difference requires an explicit contract update.

The frozen verifier policy is:

```json
{
  "profile": "a0x-hosted-gate-a-verifier-v1",
  "repository": "MarcoPorcellato/Latent-TRIZ",
  "signer_workflow": "MarcoPorcellato/Latent-TRIZ/.github/workflows/a0x-hosted-gate-a.yml",
  "predicate_type": "https://slsa.dev/provenance/v1",
  "cert_oidc_issuer": "https://token.actions.githubusercontent.com",
  "required_event": "push",
  "required_ref": "refs/heads/main",
  "deny_self_hosted_runners": true,
  "require_verified_timestamp": true
}
```

The shell-free verification argv includes `--repo`, `--bundle`,
`--custom-trusted-root`, `--signer-workflow`, `--signer-digest`,
`--source-digest`, `--source-ref`, `--cert-oidc-issuer`,
`--predicate-type`, `--deny-self-hosted-runners`, and `--format json`.
Both digest arguments are derived from the exact qualified source HEAD. The
JSON result must contain the expected certificate identity, issuer, at least
one verified transparency/timestamp record, standard predicate type, source
digest, source ref, and subject digest. Run IDs and job IDs are correlation
facts only; they never establish authenticity.

The Gate B pair authorization binds the raw SHA-256 values of the four hosted
input files, the exact verifier identity and policy, and only the intended
output path for `gate-a-verification-receipt.json`. It cannot pre-bind the hash
of an output that does not yet exist.

Before writing readiness, descriptor, execution authorization, or local
mapping, Gate B:

1. requires the four input files to be independent regular files with link
   count one;
2. checks every raw SHA-256 against the pair authorization;
3. invokes one exact, hash-bound GitHub CLI verifier with the frozen shell-free
   argv, network disabled, the supplied attestation bundle, and supplied trusted
   root;
4. requires the expected repository and signer workflow;
5. checks the authenticated subject digest against the raw manifest;
6. checks the standard provenance predicate type and builder expectations;
7. strictly parses the manifest and lane receipts;
8. requires exact local `HEAD == qualified_source_head` and exact local tree;
9. requires event `push`, ref `refs/heads/main`, run attempt `1`, the frozen
   workflow hash, and every required lane exactly once with `PASS`;
10. writes `gate-a-verification-receipt.json` once, or writes nothing and
    returns a stable refusal code.

Only after that receipt exists may the descriptor and execution authorization
bind its newly computed raw SHA-256 together with the four input hashes. Gate C
requires all five independent files and rehashes them before claim and before
`guard exec`.

The trusted-root snapshot is refreshed when importing new signed material, as
GitHub recommends. Its hash and capture time are evidence facts. Offline
verification cannot discover revocations published after that snapshot; this
limitation must remain explicit.

Missing, expired-only, malformed, unsigned, duplicate, unknown, stale,
mismatched, untrusted, rerun, or unverifiable evidence is `NO-GO`. Tree equality
never authorizes a different commit. A branch status, check name, run URL, or
artifact digest without valid provenance never opens Gate B.

The first real post-merge hosted Gate A run is also a non-material acceptance
test for the actual GitHub attestation and GitHub CLI JSON shapes. It must pass
the frozen policy without adaptation. Any unexpected certificate, predicate,
builder, signer, source, or timestamp shape stops the migration for a reviewed
specification correction; it does not authorize permissive parsing.

## Repository-governance boundary

The attestation proves a hosted workflow invocation for a signed subject and
exact source identity. It does not cryptographically prove that no privileged
actor bypassed branch protection when creating the push. At evidence capture,
the operator rechecks the active `main` ruleset, required pull-request path,
force-push/deletion controls, and bypass actors and records those observations
in transport metadata. They remain GitHub governance facts, not signed
attestation claims. Gate B must not claim cryptographic proof of reviews,
ruleset compliance, or absence of administrative bypass.

Gate A trusts the reviewed protected-main workflow and test implementation to
derive lane receipts correctly. The attestation proves which workflow produced
the manifest; it does not independently prove the semantic correctness of
workflow-controlled predicate fields or test code. Stronger builder isolation
through a centrally controlled reusable workflow is future hardening, not a
claim of this migration.

## Separation from Gate C

The material contract gains an explicit `gate_a` provider block. The existing
`ccp` block remains mandatory and unchanged for Gate C.

```text
Gate A hosted evidence -> proves exact protected source and target-free checks
Gate C CCP identity    -> proves exact local coordinator and execution envelope
```

Both bind the same source HEAD. They are not required to have the same producer
identity because they serve different functions. Gate C continues to rehash
the four Gate A evidence files and the verification receipt before claim and
before `guard exec`; it does not use network and does not reinterpret the
hosted run.

## Compatibility and frozen-state migration

### Commit identities and regeneration order

Two commit identities remain deliberately distinct. Each regenerated dossier
stores `implementation_source_head`, the reviewed commit whose implementation
bytes were used to produce both inventories and freezes. The later Gate B
authorization stores `source_head`, the clean exact-main commit authenticated
by Hosted Gate A and used by Gate C. A packaging commit or squash merge may
therefore advance `source_head` while the dossier continues to identify its
earlier implementation anchor. Neither identity may be replaced by tree
equality, and neither field may be silently rewritten after evidence capture.

Gate B authorization is created only after the exact-main hosted run and its
four inputs have been captured. It binds that final `source_head`, source tree,
all four raw inputs, and the newly created verification receipt. Approval
dossiers do not predict a future squash SHA and do not authorize Gate B by
themselves. This ordering avoids a self-referential commit cycle.

- Historical CCP receipts, evidence branches, and packages remain byte-identical
  and retain their historical interpretation.
- The existing CCP qualification parser remains available only to verify those
  historical profiles.
- Current A0X dossiers move to the hosted Gate A provider and cannot silently
  fall back to CCP qualification.
- New workflow, manifest builder, schema, verifier, workflow tests, provider
  dispatcher, strict transport schema, hash-locked `requirements-schema.lock`,
  and material-boundary tests enter both A0 and A0-R1 implementation
  inventories.
- After the exact implementation commit, regenerate target-free both
  implementation inventories, both freezes, all twelve dossiers, and the
  no-model receipt.
- Regeneration changes no corpus, endpoint, target, statistical rule, model
  revision, timeout, dense cap, or scientific claim.

## TDD and mutation requirements

Every behavior change starts with a failing test. The minimum negative matrix
must reject:

- source head mismatch even when the tree matches;
- tree mismatch;
- wrong repository, event, ref, workflow path, or workflow hash;
- `workflow_dispatch`, PR, `pull_request_target`, `workflow_run`, or rerun
  evidence;
- missing, duplicate, extra, skipped, cancelled, or failed lane;
- mutable action references, unexpected permissions, secrets, or PR checkout;
- mutated manifest, lane receipt, attestation bundle, trusted root, or
  verification receipt;
- wrong subject digest, signer workflow, builder, predicate type, or source;
- a valid signature and internally consistent predicate whose source, workflow,
  lane, event, or ref violates the frozen expectations;
- unknown manifest fields or noncanonical JSON;
- v1 CCP evidence accepted by a hosted-only dossier;
- hosted Gate A identity incorrectly compared with the Gate C CCP binary;
- absent or changed Gate C CCP identity;
- omitted trusted implementation input in either freeze inventory;
- any attempted output before offline verification passes.

Workflow tests also require one uniquely named final aggregate job. Skipped
individual jobs or GitHub's UI treatment of a skipped check cannot qualify the
run: the aggregate requires every canonical lane receipt and emits no manifest
otherwise. Its unique check identity is a Gate A requirement distinct from the
pull-request ruleset's `merge-policy/gate`. Because Gate A runs after the
protected-main push, its aggregate cannot be a prerequisite for the same push;
Gate B instead fails closed unless the aggregate produced the exact signed
manifest and durable evidence package.

Positive fixtures use only synthetic signed-verifier adapters. They never load
a model, construct a material tokenizer, read a target, invoke CCP, use Docker,
or contact a network service.

## Validation ladder

Before publication:

1. focused hosted-qualification schema and verifier tests;
2. workflow policy tests and mutation matrix;
3. provider-separation and material-boundary tests;
4. A0X frozen-package verification;
5. `a0x-no-model-verify`;
6. `a0x-synthetic-verify`;
7. schema cross-validation;
8. documentation audit;
9. complete repository check;
10. independent security and scientific-boundary review.

After a separately authorized push and merge, the new `push main` workflow must
finish once on the exact squash-merge commit. Its manifest and attestation then
undergo online capture and offline verification. A failure, cancellation, skip,
rerun, missing bundle, signature error, or expectation mismatch stops the
campaign. No manual success status or CCP Gate A fallback is permitted.

## Publication sequence and explicit stops

1. Approve this specification.
2. Write and approve the TDD implementation plan.
3. Implement target-free on an isolated branch.
4. Regenerate frozen bindings and dossiers.
5. Qualify locally without material access.
6. Separately authorize branch push and PR.
7. Merge only after hosted PR gates pass.
8. Observe the exact-main hosted Gate A run.
9. Separately authorize capture and publication of immutable hosted evidence.
10. Verify from a fresh clone and offline evidence set.
11. Stop for a new exact pair-specific Gate B authorization.

This specification grants none of steps 3--11 by itself.

## Completion criteria

The migration is complete only when:

- Gate A no longer needs a local CCP `run`;
- exact protected-main source has signed, expectation-checked provenance;
- durable evidence is independently verifiable offline;
- Gate B refuses every incomplete or mismatched evidence case before output;
- Gate C still requires the exact CCP coordinator and unchanged material
  envelope;
- historical evidence is preserved without relabeling;
- both freezes and all twelve dossiers bind the new implementation;
- local, hosted, fresh-clone, and offline verification are terminally green;
- no model, tokenizer, target, scientific result, or general TRIZ claim is
  accessed or promoted during migration.
