---
type: restart-checkpoint
title: A0X pair-scoped vertical-slice readiness checkpoint
status: p0-bootstrap-re-review-pending
date: 2026-09-02
branch: agent/a0x-hosted-gate-a-capture-wrapper
reviewed_head: 77dcae52542d21e9bf16e4f17102abf70e68ffc3
reviewed_tree: 79d9fd9c868cf367fdec28bbad8c0ac0d7f8b598
scope: target-free
---

# A0X pair-scoped vertical-slice readiness checkpoint

## Purpose and decision

This checkpoint preserves the local readiness boundary for the first
pair-scoped package. The decision is **NO-GO pending independent re-review of
the corrected P0 bootstrap**. P0 has not run, no real vertical package exists,
and no later gate is authorized.

Canonical specification: `docs/A0X_VERTICAL_SLICE.md`.

Full local evidence and the 137-file raw input ledger:
`docs/qualification/a0x-vertical-slice-local-review-77dcae52542d21e9bf16e4f17102abf70e68ffc3.md`.

The reviewed implementation state before this checkpoint commit was:

- HEAD: `77dcae52542d21e9bf16e4f17102abf70e68ffc3`
- tree: `79d9fd9c868cf367fdec28bbad8c0ac0d7f8b598`
- branch: `agent/a0x-hosted-gate-a-capture-wrapper`
- worktree: clean

Because a commit cannot contain its own commit identity, the exact P0 source
identity is the clean checkpoint commit and tree recorded by the Task 4
post-commit report. On restart, verify those values live before relying on this
checkpoint. Do not use the pre-checkpoint implementation HEAD as the P0 source
head.

## Completed target-free evidence

- Exact implementation diff reviewed: 19 files, 2,940 insertions, 14
  deletions; `git diff --check` passed.
- Focused generator, selector, bootstrap, inventory, and projection suite:
  85/85 PASS.
- Vertical Make verification: 52/52 PASS.
- External pre-execution replacement, inline-source parity, full trust-window,
  and post-publication cleanup-receipt regressions: PASS.
- Five active package schemas: Draft 2020-12 meta-validation PASS.
- Production descriptor-bound input reader: 137/137 files PASS; 2,149,445 raw
  bytes.
- Sorted input-ledger SHA-256:
  `37301ed7234e91d2b13336505444864fddd85a789d7bf3db7a8ab713889acbfa`.
- Historical batch artifact range diff: byte-identical for two freezes and
  twelve dossiers.
- Real `experiments/a0x-six-model/vertical-slices/` path: absent.
- Documentation gate: canonical link, historical/stale labels, separate
  P0/A/B/C/result/publication gates, and A0-before-A0-R1 boundary present.
- Full synthetic aggregate: zero-material receipt emitted; 500 tests ended
  with the expected stale historical-package boundary of three failures, one
  dependent error, and one skip. This is not a full-suite PASS and must not be
  relabelled as one.

No model, tokenizer, sealed target, scoring, CCP, Docker, network, GitHub,
Gate A/B/C, package generation, batch regeneration, no-model receipt write,
push, PR, merge, publication, or retry occurred.

## Residual security boundary

P0 is NO-GO unless the operator excludes every untrusted same-UID repository
or namespace mutator in one window beginning before pre-execution
Python/bootstrap verification and process launch through terminal receipt
emission and private-bootstrap cleanup. Private modes do not exclude another
process with the same user ID. Darwin has no conditional expected-inode unlink
or `rmdir`; ownership loss must fail closed and preserve possible replacement
data.

The proposed command first runs an exact authorization-bound inline launcher
under the already authenticated absolute Python and `-I -S -B`. The launcher
descriptor-reads the target-free bootstrap as regular single-link stable bytes,
compares the immutable expected SHA-256, and only then executes the verified
bytes. The bootstrap rechecks that hash, immutable HEAD/tree, cleanliness,
Python identity, repository-bytecode absence, and complete descriptor-read
137-entry ledger before import or staging. Its terminal receipt binds source,
Python, bootstrap, ledger, package-publication state, private-cleanup state, and
no-retry status. Editing the bootstrap, inline launcher, or command requires a
new review and authorization.

Cleanup uncertainty does not prove that the trust window closed. Its terminal
receipt must distinguish successful publication from uncertain cleanup,
preserve the published package, prohibit retry, and stop for separately
authorized recovery.

## Exact next authorization request

After independent re-review, authorize at most one invocation in this exact
worktree, on the exact final clean HEAD/tree, for only
`A0 / smollm2_360m`, output under
`experiments/a0x-six-model/vertical-slices/<final-head>/a0/smollm2_360m/`, with
the absolute Python identity, inline pre-execution source and SHA-256
`a0cc17b6d256ff03abfcd58e158d31ab0bffc1db497a2c400ed04bb16fc7483b`,
committed bootstrap identity, input-ledger digest above, and full same-UID
exclusion window. Revalidate the absolute Python path/hash after that window
starts and before process launch.

```bash
rtk env -i PATH=/usr/bin:/bin LC_ALL=C /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -I -S -B -c '
import hashlib
import hmac
import os
import stat
import sys

MAXIMUM = 64 * 1024 * 1024
CODE = "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH"

def refuse():
    print(f"a0x-vertical-p0-preexec: {CODE}", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]
expected_sha256 = sys.argv[2]
if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
    refuse()
try:
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= MAXIMUM:
        refuse()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        raw = b"".join(iter(lambda: os.read(descriptor, 1024 * 1024), b""))
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)
except (AttributeError, OSError):
    refuse()
identity = (before.st_dev, before.st_ino, before.st_size)
if identity != (opened.st_dev, opened.st_ino, opened.st_size) or identity != (final.st_dev, final.st_ino, final.st_size):
    refuse()
if len(raw) != before.st_size or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
    refuse()
sys.argv = [
    path,
    *sys.argv[3:],
    "--preexec-bootstrap-device", str(opened.st_dev),
    "--preexec-bootstrap-inode", str(opened.st_ino),
    "--preexec-bootstrap-bytes", str(opened.st_size),
]
globals_for_script = {
    "__name__": "__main__",
    "__file__": path,
    "__package__": None,
    "__cached__": None,
}
exec(compile(raw, path, "exec", dont_inherit=True, optimize=0), globals_for_script, globals_for_script)
' /Users/marco1/.codex/worktrees/latent-triz-a0x-hosted-capture-20260901/scripts/a0x_vertical_p0_bootstrap.py fde8ca234ed9287f478bcfe2ea90aaa58822d6677e146cc74a6e886d1e3073a0 --repository-root /Users/marco1/.codex/worktrees/latent-triz-a0x-hosted-capture-20260901 --expected-head EXACT_FINAL_40_HEX_HEAD --expected-tree EXACT_FINAL_40_HEX_TREE --expected-python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 --expected-python-sha256 3a1f077a333905eaac57197c9f2060ed95e05208daf83da4827d92e0474574d8 --expected-ledger-sha256 37301ed7234e91d2b13336505444864fddd85a789d7bf3db7a8ab713889acbfa --expected-bootstrap-sha256 fde8ca234ed9287f478bcfe2ea90aaa58822d6677e146cc74a6e886d1e3073a0 --expected-preexec-sha256 a0cc17b6d256ff03abfcd58e158d31ab0bffc1db497a2c400ed04bb16fc7483b
```

Stop after the first terminal return. No retry after success, refusal,
interruption, timeout, cleanup uncertainty, or opaque failure. On success, only
read-only inspection
and hashing of the five package members is permitted. Gate A, Gate B, Gate C,
the vertical material target, model/tokenizer/target/scoring access, CCP,
Docker, network/GitHub, batch regeneration, no-model receipt regeneration,
push, PR, merge, publication, and A0-R1 remain prohibited.

## Restart procedure

1. Read this checkpoint, the canonical specification, and the local review.
2. Verify the durable branch, exact final checkpoint HEAD/tree, and clean
   status. Preserve any dirty or divergent work; do not reset, stash, or clean.
3. Recompute the 137-file input ledger and require the exact digest above.
4. Revalidate the absolute Python path/hash, bootstrap committed hash, and
   source-only isolation contract.
5. Require the real vertical output root to be absent.
6. Complete independent review of the corrected bootstrap and its regressions.
7. Establish the full same-UID namespace isolation. If unavailable, record
   P0 NO-GO and stop.
8. Obtain a new explicit authorization containing every binding above.
9. If authorized, run the command once and stop at its terminal result.
