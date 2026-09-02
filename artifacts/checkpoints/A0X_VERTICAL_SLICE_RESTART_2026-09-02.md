---
type: restart-checkpoint
title: A0X pair-scoped vertical-slice readiness checkpoint
status: p0-authorization-pending
date: 2026-09-02
branch: agent/a0x-hosted-gate-a-capture-wrapper
reviewed_head: 77dcae52542d21e9bf16e4f17102abf70e68ffc3
reviewed_tree: 79d9fd9c868cf367fdec28bbad8c0ac0d7f8b598
scope: target-free
---

# A0X pair-scoped vertical-slice readiness checkpoint

## Purpose and decision

This checkpoint preserves the independently reviewed local readiness boundary
for the first pair-scoped package. The decision is **GO to request one exact P0
authorization only**. P0 has not run, no real vertical package exists, and no
later gate is authorized.

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
- Focused generator, selector, inventory, and projection suite: 75/75 PASS.
- Vertical Make verification: 42/42 PASS.
- Five active package schemas: Draft 2020-12 meta-validation PASS.
- Production descriptor-bound input reader: 137/137 files PASS; 2,149,289 raw
  bytes.
- Sorted input-ledger SHA-256:
  `d3f4724dc9873a9fcb2235ebabab9aead9a25ba9e72772648f28a5b5b6615956`.
- Historical batch artifact range diff: byte-identical for two freezes and
  twelve dossiers.
- Real `experiments/a0x-six-model/vertical-slices/` path: absent.
- Documentation gate: canonical link, historical/stale labels, separate
  P0/A/B/C/result/publication gates, and A0-before-A0-R1 boundary present.
- Full synthetic aggregate: zero-material receipt emitted; 490 tests ended
  with the expected stale historical-package boundary of three failures, one
  dependent error, and one skip. This is not a full-suite PASS and must not be
  relabelled as one.

No model, tokenizer, sealed target, scoring, CCP, Docker, network, GitHub,
Gate A/B/C, package generation, batch regeneration, no-model receipt write,
push, PR, merge, publication, or retry occurred.

## Residual security boundary

P0 is NO-GO unless the operator excludes every untrusted same-UID repository
or namespace mutator from the generator's first source-state check through
terminal success or cleanup. Private modes do not exclude another process with
the same user ID. Darwin has no conditional expected-inode unlink or `rmdir`;
ownership loss must fail closed and preserve possible replacement data.

The package generator has no dedicated CLI. The proposed command invokes the
reviewed Python API with fixed selectors and no material-consumer call. This is
acceptable only as the exact one-shot command below; editing it requires a new
review and authorization.

## Exact next authorization request

Authorize at most one invocation in this exact worktree, on the final clean
checkpoint HEAD/tree reported by Task 4, for only `A0 / smollm2_360m`, output
under
`experiments/a0x-six-model/vertical-slices/<final-checkpoint-head>/a0/smollm2_360m/`,
with the input-ledger digest above and the complete same-UID exclusion.

```bash
rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -c 'import json,subprocess; from pathlib import Path; from latent_triz.a0x_contract import Leg; from latent_triz.a0x_vertical_slice import VerticalSliceRequest,generate_vertical_slice; completed=subprocess.run(("/usr/bin/git","rev-parse","--verify","HEAD^{commit}"),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10,env={"PATH":"/usr/bin:/bin","LC_ALL":"C","GIT_CONFIG_NOSYSTEM":"1","GIT_NO_REPLACE_OBJECTS":"1"}); head=completed.stdout.decode("ascii","strict").strip(); output=f"experiments/a0x-six-model/vertical-slices/{head}/a0/smollm2_360m"; print(json.dumps(generate_vertical_slice(Path("."),VerticalSliceRequest(leg=Leg.A0,model_key="smollm2_360m",implementation_source_head=head,output_root=output)),sort_keys=True,separators=(",",":")))'
```

Stop after the first terminal return. No retry after success, refusal,
interruption, timeout, or opaque failure. On success, only read-only inspection
and hashing of the five package members is permitted. Gate A, Gate B, Gate C,
the vertical material target, model/tokenizer/target/scoring access, CCP,
Docker, network/GitHub, batch regeneration, no-model receipt regeneration,
push, PR, merge, publication, and A0-R1 remain prohibited.

## Restart procedure

1. Read this checkpoint, the canonical specification, and the local review.
2. Verify the durable branch, exact final checkpoint HEAD/tree, and clean
   status. Preserve any dirty or divergent work; do not reset, stash, or clean.
3. Recompute the 137-file input ledger and require the exact digest above.
4. Require the real vertical output root to be absent.
5. Establish the full same-UID namespace isolation. If unavailable, record
   P0 NO-GO and stop.
6. Obtain a new explicit authorization containing every binding above.
7. If authorized, run the command once and stop at its terminal result.
