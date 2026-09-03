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

## Pair-scoped sequence

[A0X pair-scoped vertical slice](A0X_VERTICAL_SLICE.md) is the operational
authority for the first `A0 / smollm2_360m` package. P0 package generation,
hosted Gate A, offline Gate B, local Gate C, target-free result verification,
and publication require separate exact authorizations. None authorizes a later
gate. The historical batch freezes, twelve dossiers, and no-model receipt are
stale and must not be reused as current pair-package evidence.

A0-R1 starts only after the A0 terminal report and its own authorization. The
frozen scientific inputs and rules must not change between the two legs.

## Hosted Gate A prerequisite (current)

For current A0X dossiers, Gate A is the signed GitHub-hosted provider, not a
CCP receipt. It has seven target-free lanes: `repository-python311`,
`schema-cross-validation-python311`, `repository-python312`,
`schema-cross-validation-python312`, `a0x-no-model`, `a0x-synthetic`, and
`documentation-audit`. The four hosted inputs are a manifest (32 KiB),
attestation bundle (1 MiB), trusted root (2 MiB), and transport record (16
KiB). Gate B creates the fifth verification receipt (32 KiB) only after the
offline verifier succeeds.

The first real post-merge hosted Gate A run is an acceptance test and has no
rerun or CCP Gate A fallback. CCP Gate C is retained as a distinct local
coordinator. Historical CCP receipts remain **Historical evidence** only.
Capture, publication, Gate B, and Gate C require separate authorization. The
trusted-root snapshot cannot discover revocations published after that snapshot.
The [Hosted Gate A operator runbook](A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md)
defines the frozen verifier inputs, refusal codes, retention, and restart rule.

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

One ignored local wheelhouse has now passed this boundary for Python 3.11. Its
canonical manifest SHA-256 is
`fe541aa83b5dbd9770da1f50d2cd88eb192586406398d9cffa5507f9f352ca72`;
it binds 39 wheels totalling 150,397,774 bytes. The repository does not embed
or publish those wheels, so this is local preparatory evidence rather than a
portable public runtime. It neither retroactively proves the copied
environment used by the historical recovery nor authorizes an installation.

## Boundary 3.5: reproducible offline prerequisite builder

`scripts/a0x_build_gate_b_runtime.py` and
`latent_triz.a0x_gate_b_builder` connect the already verified wheelhouse and
APFS primitives without merging their authorities. `--plan` is a no-write
surface. Build mode is a separately authorized material action.

The builder requires a clean exact source HEAD, the raw wheelhouse-manifest
hash, and a canonical `a0x-python-runtime-manifest-v1` that allowlists every
independent regular file in the selected base runtime. That manifest binds the
interpreter, standard library, `venv`, `ensurepip`, and bundled bootstrap
installer rather than treating the launcher hash as proof of the runtime. The
request also binds the exact Python 3.11 version, bootstrap `pip` version,
model-card hash, allowlisted source snapshot, and absent attempt and model
destinations. Before any child execution it APFS-clones the complete verified
base runtime and all 39 wheels into private, attempt-owned paths. No external
executable or wheel path is consumed after that binding. It then uses
shell-free commands to:

1. create a virtual environment with `venv --copies`;
2. verify the installer created inside the environment, then install only
   hash-locked wheelhouse distributions with `--no-index`, `--no-cache-dir`,
   `--only-binary :all:`, `--require-hashes`, and `--no-deps`;
3. remove bootstrap `pip` and prove the final environment contains exactly the
   39 locked distributions;
4. clone only the model-card files through Darwin `clonefile(2)`; and
5. revalidate source state, all input bytes, output path components,
   interpreter bytes, installed metadata, and materialized snapshot before an
   exclusive local receipt write.

The bootstrap installer is an explicit tool, not a retained runtime package.
Its bundled bytes, reported version, and environment-local version are bound
before use; it is then removed. Package content added to the final environment
comes only from the verified wheelhouse. An extra, duplicate, or missing
distribution is terminal. Read-only probes disable bytecode writes; all child
commands have a 3,600-second fail-closed timeout.

The builder never repairs or deletes an incomplete attempt. It refuses
symlink or hardlink swaps, noncanonical external paths, path escape, occupied
outputs, base-runtime or source drift, command failure, malformed metadata,
unexpected files, full-copy fallback, and receipt reuse. A failed material
attempt requires new absent destinations and a new exact authorization.

The CLI has no implicit material default. Operators must select exactly one of
`--plan` or `--build`; omission is refused before probing or writing. Planning
performs no external execution. Build mode executes only the owned APFS-bound
runtime and installs only from the owned APFS-bound wheelhouse.

Repository tests exercise this path only with tiny synthetic wheels, a fake
Python executable, injected shell-free child results, and tiny model files.
They do not install the real environment or access a real model snapshot.

## Boundary 4: immutable preparation

Only after Boundaries 1--3.5 and the pair-specific authorization are satisfied
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
