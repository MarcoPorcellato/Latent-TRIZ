---
type: operator-runbook
title: A0X Hosted Gate A evidence capture and offline verification
status: target-free-preparation
date: 2026-08-31
---

# A0X Hosted Gate A operator runbook

This runbook describes the post-implementation operator sequence. It is not an
authorization to capture evidence, publish anything, prepare Gate B, run Gate
C, load a model or tokenizer, read a target, use CCP heavy work, use Docker, or
contact GitHub. Each listed external step needs its own separate authorization
bound to the exact source and files involved.

## Current vertical-chain consumer — 2026-09-05

Hosted Gate A qualifies a protected-main source `HEAD/tree`; it does not create
or attest a P0 package. After a separately authorized capture of the four
hosted inputs, only P0 v2 may create an ignored atomic package envelope. The
current consumer chain is `Hosted Gate A -> capture -> P0 v2 -> Gate B v2 ->
Gate C v2 -> verification`. P0 v2, Gate B v2, and Gate C v2 each bind the same
source identity and external package commitment.

Historical CCP/Matrix Gate A evidence, tracked v1 vertical packages, and
earlier batch artifacts retain their original historical meanings. They cannot
substitute for a new Hosted Gate A run or for a v2 package. This text grants no
capture, network, GitHub CLI, P0, Gate B, Gate C, model, tokenizer, target,
CCP, Docker, or publication authority.

## Capture-wrapper recovery checkpoint — 2026-09-02

The target-free capture library and shell-free adapter are restored locally.
Both wrapper test modules are part of the A0X synthetic aggregate, and the
request/transport schemas, library, adapter, and both tests are trusted
implementation inputs for both leg inventories. No real CLI runner is enabled:
the production entry point refuses until a separately authorized capture
qualifies its exact pinned CLI help and output shapes.

Tracked inventories, freezes, twelve dossiers, and the no-model receipt predate
these trusted inputs. They are deliberately stale and cannot authorize any
next step. One new explicit target-free authorization must name the exact
implementation head, one regeneration, both inventories and freezes, all
twelve dossiers, the no-model receipt, full deterministic suite, independent
review, and local closure. It grants no hosted capture, network, GitHub CLI,
publication, Gate B/C, CCP, Docker, model, tokenizer, target, or material work.

## Scope and non-interchangeable gates

Gate A is a signed, GitHub-hosted qualification of one protected `main` commit.
Gate B is an offline, pair-specific verification and runtime preparation step.
Gate C is the one local CCP-guarded material attempt. A Gate A result never
creates a runtime bundle; Gate B never starts Gate C; and a successful Gate C
cannot retroactively validate Gate A.

The seven required Hosted Gate A lanes are, exactly once each:

1. `repository-python311`;
2. `schema-cross-validation-python311`;
3. `repository-python312`;
4. `schema-cross-validation-python312`;
5. `a0x-no-model`;
6. `a0x-synthetic`;
7. `documentation-audit`.

The workflow is a protected-`main` push-only acceptance surface. Its run
attempt must be `1`: there is **no rerun** qualification path. A failed,
cancelled, skipped, missing, duplicate, or rerun lane is `NO-GO`. The first
real post-merge hosted Gate A run is an acceptance test of the actual GitHub
attestation and GitHub CLI result shapes; it is not an occasion to adapt the
parser, change policy, or fall back to a CCP Gate A receipt.

CCP remains required only for the independent local **CCP Gate C** coordinator
and material envelope. New hosted dossiers reject CCP Gate A substitution.
Historical CCP receipt branches and packages are **Historical evidence** only;
they retain their original meaning and bytes.

## Capture set and limits

After a terminal Hosted Gate A PASS, an independently authorized capture stores
these exact regular files:

```text
hosted-gate-a-evidence.json
hosted-gate-a-attestation.bundle.jsonl
github-trusted-root.jsonl
hosted-gate-a-transport.json
```

They are four hosted inputs. Offline Gate B creates the fifth verification
receipt, `gate-a-verification-receipt.json`, only after all four inputs verify.
The hard caps are 32 KiB for the manifest, 1 MiB for the attestation bundle,
2 MiB for the trusted root, 16 KiB for transport metadata, and 32 KiB for the
fifth verification receipt. Oversize, missing, nonregular, symlinked,
hardlinked, noncanonical, duplicate, or hash-mismatched data is `NO-GO` before
parsing or output.

Capture validates the artifact archive digest and the raw manifest hash. The
transport record is correlation data, not an authenticity root. Public-safe
fields are only artifact/run/attempt identifiers, exact source head, archive
digest and size, timestamps, frozen workflow/policy identifiers, hashes, and
refusal code. Do not publish raw logs, local paths, usernames, commands,
environment values, secrets, container identifiers, or private runtime data.

Capture must occur before artifact expiry. A deleted, expired, or unavailable
artifact is `NO-GO`; a run URL, check name, branch status, archive digest, or
tree match is not a substitute for signed provenance. Once the exact four files
are retained, later transport expiration does not change their bytes or their
recorded verification outcome.

The signed bundle is verified against its captured trusted-root snapshot. The
snapshot should be refreshed when importing new signed material. Offline
verification cannot discover **revocations published after that snapshot**;
record that limitation rather than claiming live revocation coverage.

## Offline Gate B verifier

The pair-specific authorization binds the raw hashes of the four hosted inputs,
the frozen GitHub CLI identity and verifier policy, and only the intended
verification-receipt output path. It does not pre-bind the receipt hash.

The operational boundary uses a shell-free invocation of the hash-bound GitHub
CLI adapter with these required flags:

```text
gh attestation verify <subject>
  --repo MarcoPorcellato/Latent-TRIZ
  --bundle hosted-gate-a-attestation.bundle.jsonl
  --custom-trusted-root github-trusted-root.jsonl
  --signer-workflow MarcoPorcellato/Latent-TRIZ/.github/workflows/a0x-hosted-gate-a.yml
  --signer-digest <qualified-source-head>
  --source-digest <qualified-source-head>
  --source-ref refs/heads/main
  --cert-oidc-issuer https://token.actions.githubusercontent.com
  --predicate-type https://slsa.dev/provenance/v1
  --deny-self-hosted-runners
  --format json
```

The project wrapper supplies the exact frozen executable, timeout, environment,
and canonical input/output paths. The displayed command is explanatory: do not
paste a hand-built command or resolve an unpinned CLI. Verification refuses on
any signature, certificate, timestamp, subject, source, workflow, event, ref,
builder, predicate, lane, raw-hash, path, object, link-count, JSON, or policy
mismatch. A refusal writes no receipt. A successful exclusive receipt is kept
if a later Gate B preparation stage fails; no readiness, descriptor,
authorization, or mapping partial may remain.

The attestation proves a signed workflow invocation for an exact source; it
does not prove absence of administrative branch-protection bypasses, reviews,
or a SLSA level. At capture, separately inspect and record the active `main`
ruleset, required PR route, force-push/deletion controls, and bypass actors as
GitHub governance observations, not signed facts.

## Retention, publication, and restart

The evidence branch is durable distribution, not an authenticity root. A
separate authorization may publish the four exact bytes only on
`hosted-evidence/<qualified-source-head>` after a dedicated no-force-push and
no-deletion rule exists. If that rule is unavailable, stop and request a new
authorization that records the durability limitation. Capture authorization,
publication authorization, Gate B authorization, and Gate C authorization are
all separate.

On restart, preserve existing artifacts and receipts byte-identically; record
the exact source head/tree, four raw input hashes, policy/verifier identity,
authorization ID, current stage, and refusal/expiry status. Revalidate objects,
paths, link counts, raw hashes, and authorization before resuming the next
unconsumed boundary. Never rerun a consumed hosted attempt, overwrite a receipt,
or reinterpret a historical CCP Gate A result as hosted evidence.
