---
type: runbook
title: A0X Gate B operator hardening
status: preparatory
---

# A0X Gate B operator hardening

This runbook defines the target-free preparation boundaries added after the
first A0 / SmolLM2-360M Gate B recovery. It does not authorize Gate B, Gate C,
a model or tokenizer load, a target read, CCP, Docker, network access, or
publication.

The already prepared Gate B bundle remains historical evidence for its exact
source and exact bytes. These source changes do not alter or retroactively
upgrade it. Any future use of this hardening requires a new exact-head Gate A
qualification and a new pair-specific Gate B authorization.

## Why the process is split

Gate B previously combined four questions too late in the workflow:

1. Are all public bindings and paths valid before any output exists?
2. Was APFS copy-on-write actually used, without silently falling back to a
   full copy?
3. Can a Python environment be rebuilt from a complete verified offline
   wheelhouse?
4. Do the selected interpreter, packages, APIs, card and runtime files satisfy
   the frozen readiness contract?

The corrected process answers each question independently. A success at one
boundary never implies success or authorization at the next boundary.

## Boundary 1: no-write bundle preflight

Run `scripts/a0x_prepare_runtime.py --preflight` with the same pair, receipt,
CCP, Python, evidence commit, authorization ID and attempt ID that would be
used by preparation. The preflight executes the same target-free validation
and constructs all four documents in memory, but creates none of their output
paths.

Success returns `status: preflight`, relative paths and document SHA-256
values. Repeating identical inputs must produce identical JSON. Refusal exits
with code 2 and returns a stable diagnostic code plus a safe message. The
legacy invocation without `--preflight` retains the minimal
`{"status":"refused"}` response.

The diagnostic code
`A0X_QUALIFICATION_RECEIPT_PATH_NOT_SOURCE_DERIVED` identifies the exact
failure encountered during the first Gate B attempt. It means that copying the
receipt to the dossier-derived repository path is a separately authorized
preparation prerequisite; it does not authorize that copy.

## Boundary 2: APFS clonefile materialization

`latent_triz.a0x_apfs.clone_regular_file` is the only approved copy-on-write
primitive for future runtime materialization. It calls Darwin `clonefile(2)`
directly and has no ordinary-copy fallback. The caller must provide an existing
destination parent, an unoccupied destination, and explicit trusted source and
destination roots. Every caller-controlled path component below those roots is
checked for traversal and symlinks before the syscall.

Before the call it requires an independent regular source. After the call it
requires:

- unchanged source identity, size and SHA-256;
- an independent regular destination with link count one;
- a distinct inode;
- exact destination size and SHA-256.

Unsupported platforms, missing `clonefile`, symlinks, hardlinks, occupied
destinations, syscall errors and verification drift are terminal refusals for
that preparation attempt. After a syscall return, failed verification removes
only the same regular inode created by that call; it never removes a
pre-existing path or a replacement inode. If safe cleanup cannot be proven,
the path remains refused and must not be reused as evidence.

## Boundary 3: offline wheelhouse verification

`latent_triz.a0x_wheelhouse.verify_offline_wheelhouse` validates a canonical
`a0x-offline-wheelhouse-v1` manifest against an exact directory. It performs no
installation and invokes neither `pip` nor any network API.

The manifest binds Python 3.11, the complete accepted wheel-tag set, and for
every wheel its normalized distribution, version, filename, tag, size and
SHA-256. Verification rejects missing or extra entries, duplicate
distributions, filename/metadata disagreement, unaccepted tags, noncanonical
JSON, byte drift, symlinks, hardlinks and non-regular files.

No complete exact offline wheelhouse is currently proven for the accepted A0X
Python environment. Therefore this boundary is ready for a future wheelhouse;
it does not retroactively prove rebuildability of the copied environment used
by the historical recovery.

## Boundary 4: immutable preparation

Only after Boundaries 1--3 and the pair-specific authorization are satisfied
may the ordinary preparer write readiness, descriptor, authorization and local
mapping. The existing live-readiness validators then recheck independent
regular Python and model files at every material boundary and immediately
before model construction.

Preparation success still stops before Gate C. The operator must report the
raw authorization-document SHA-256 and request a separate one-shot Gate C
authorization bound to those exact bytes.

## Failure handling

- Preserve the refusal and exact input hashes.
- Do not reinterpret preflight, clonefile or wheelhouse success as scientific
  evidence.
- Do not fall back to a full copy, online resolver or implicit package install.
- Do not modify a completed bundle to repair a later mismatch.
- Correct source only with TDD, regenerate frozen inputs, requalify Gate A and
  request a fresh Gate B authorization.
