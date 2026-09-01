# A0X Hosted Gate A Capture Wrapper Recovery Design

**Status:** approved recovery of previously approved target-free scope
**Base:** `1bde09bb72ab5c4e938e1b9904f6b0a745ab3cc2`, tree `d07daf572f471b2be3973a464c44d3d826c73106`
**Boundary:** no real GitHub transport, `gh attestation verify`, Gate B/C, model, tokenizer, target, CCP, Docker, push, PR, or merge

## Purpose

Recreate the lost local implementation of the A0X Hosted Gate A capture
boundary. It bridges a later separately-authorized GitHub artifact retrieval to
the existing offline hosted verifier. It is not an attestation verifier and
cannot authorize Gate B.

## Contract

The library consumes an exact request binding repository, source head/tree,
push run and attempt `1`, artifact ID/name/archive digest/size/expiry, and
one absolute absent output root. It permits only a regular independent,
absolute GitHub CLI executable with exact frozen version and SHA-256.

Transport data remains untrusted until all metadata, archive, member, and
cross-bindings pass. The canonical artifact member
`a0x-hosted-gate-a-evidence.json` is preserved byte-identically as
`hosted-gate-a-evidence.json`. Exactly four final files are permitted:

```text
hosted-gate-a-evidence.json
hosted-gate-a-attestation.bundle.jsonl
github-trusted-root.jsonl
hosted-gate-a-transport.json
```

All other output is refusal. Existing outputs, symlinks, hardlinks,
non-directory ancestors, duplicate/extra/traversal/encrypted/nonregular ZIP
members, bad hashes/sizes, malformed values, source/run/attempt drift, and
partial publication are fail-closed.

## Architecture

`src/latent_triz/a0x_hosted_capture.py` owns pure request validation, safe
archive validation, cross-binding checks, inode-owned staging cleanup, and
atomic exclusive directory publication. `scripts/a0x_capture_hosted_gate_a.py`
is a thin explicit-argument, shell-free adapter. Every real subprocess path is
injected in tests. The production adapter exists only for a later exact real
capture authorization.

Darwin `renamex_np(..., RENAME_EXCL)` is the only no-overwrite publication
primitive. Unsupported hosts refuse; tests inject the primitive so hosted CI
tests portability without claiming Linux material capture support.

## Tests

Synthetic files/ZIPs and injected subprocess replies prove pre-transport
refusals, exact byte/metadata bindings, all rejected archive/path/link cases,
staging ownership, no final output after failure, exclusive four-file success,
and pinned-CLI revalidation before each subprocess. No fixture contains real
GitHub evidence, credentials, model data, or targets.

## Freeze and recovery boundary

After code/tests/docs are committed, trusted source/script/test/schema/fixture
paths must enter both A0X inventories. Regeneration of freezes and twelve
dossiers is target-free but now requires a new explicit authorization because
new synthetic test modules also require a trusted Makefile aggregate update.
Historical candidate artifacts from the lost clone are unavailable and must
not be reconstructed as evidence.
