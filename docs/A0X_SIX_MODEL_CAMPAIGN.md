---
type: laboratory-runbook
title: A0X six-model A0 and A0-R1 replication campaign
status: frozen-no-model
date: 2026-08-25
---

# A0X six-model campaign

A0X is a controlled replication campaign for the six exact model snapshots
that were acquired after the original Pythia study. It does not create a new
TRIZ claim. It asks whether the already frozen A0 and A0-R1 automated-proxy
signals recur when the model family changes, while keeping each leg and model
strictly separate.

Task 11 is preparatory only. The repository contains twelve
`approval_requested` dossiers, not twelve authorizations. No dossier grants a
model load, tokenizer construction, target read, CCP invocation, retry, or
publication.

## Current vertical Gate-Chain Convergence checkpoint — 2026-09-05

The current target-free implementation anchor is
`bf49a48106b77e65f16aa6763035f9ab2fa9a67f`. It regenerated the two leg
implementation inventories, two freezes, twelve approval-request dossiers, and
the no-model receipt. Those regenerated batch artifacts remain current only
for deterministic no-model verification; they are **not** a new material route.

The sole future execution route is:

```text
Hosted Gate A -> capture -> P0 v2 -> Gate B v2 -> Gate C v2 -> verification
```

P0 v2 creates one ignored, atomic local envelope bound to a protected-main
`HEAD/tree`, one leg/model pair, and a separate package commitment. Gate B v2
and Gate C v2 consume that same typed binding and have no v1 or batch fallback.
The tracked v1 vertical package, historical CCP/Matrix Gate A evidence, and
pre-convergence batch material interpretations are historical evidence only.
Their protected hashes are recorded in
[`docs/qualification/a0x-vertical-chain-historical-protection.json`](qualification/a0x-vertical-chain-historical-protection.json).

The next stop is a separate authorization for one protected-main Hosted Gate A
run, followed by separately authorized capture and P0 v2. Gate B v2, Gate C,
model/tokenizer access, target reads, scoring, CCP, Docker, network use, and
publication remain unauthorized. A0-R1 remains blocked until the A0 terminal
report and its own authorization. Frozen scientific inputs do not change
between legs.

## Historical Hosted Gate A capture-wrapper recovery checkpoint — 2026-09-02

The recovered target-free capture library, shell-free adapter, request and
transport schemas, and both capture test modules are now trusted inputs in
both implementation inventory definitions. The synthetic aggregate includes
both capture test modules. Existing generated inventories, freezes, twelve
dossiers, and no-model receipt predate that source and are intentionally stale.

Do not regenerate from this checkpoint. A new explicit authorization must bind
the exact implementation head and allow exactly one target-free regeneration,
both leg inventories/freezes, twelve dossiers, no-model receipt, full
deterministic suite, independent review, and local closure. It does not permit
real GitHub/CLI capture, network, publication, Gate B/C, CCP, Docker, model,
tokenizer, target, or scientific execution.

## Current offline Gate B builder checkpoint — 2026-09-01

This document is the sole canonical A0X status ledger. Architecture authority is
[A0X architecture convergence](A0X_ARCHITECTURE_CONVERGENCE.md); operator
authority is [A0X Gate B hardening](A0X_GATE_B_OPERATOR_HARDENING.md). All later
A0X checkpoint blocks in this file are historical evidence only.

The reviewed implementation anchor is
`b7ab6513c759b4f0133b33c8a70c034d8a1f92ba`, tree
`480e96a94a8602a3ba1bb08741a3ecf0fb86cce1`. Target-free regeneration binds:

| Leg | Implementation SHA-256 | Freeze SHA-256 |
| --- | --- | --- |
| A0 | `beea84d11b8c3c5b7262991a3f5e951834b81432c2aea0ca71a521a78228c6c3` | `38bdbb99db20c471e9aeafeb7b961709ce373d2fd8f0801c56655ac550266677` |
| A0-R1 | `6f8f6adeccb067aec4473a3b46c632db400317bcee432e41186c368a419da021` | `2ec31870102a9219a36df24304748e31da4050514d9e59cfd0c9056adaba3ffa` |

The twelve-dossier ledger identity is
`c249f94e3d5124c8fb19ebdf873d4bf91eb2dc7eb6c75654e55d9dff58451df0`: SHA-256
of compact, key-sorted JSON containing the ordered `dossiers` rows below, each
with its repository-relative `path` and SHA-256.

| Dossier | SHA-256 |
| --- | --- |
| `a0/gpt2.json` | `c1e48c06d1d4d10b741edff0d3e7c06d452848fb30e4a7bcd80e7485c3392d7f` |
| `a0/gpt_neo_125m.json` | `167c45a926532c280683427df818c3668d9e86c83223bf916f6829e0c67563aa` |
| `a0/qwen2_5_0_5b.json` | `16a3f584121f533378a903aed22e6db37118af2839372fad56ed5f86c7d0c3fe` |
| `a0/qwen3_0_6b_base.json` | `876e04a9ee9f36f11ef662411967367838bba260240cec76f8befb18ac574a6b` |
| `a0/smollm2_135m.json` | `213d915b48705beaba1c5e4d77a08daaa999aaf0d64bc12c9b93ea396d0dae8b` |
| `a0/smollm2_360m.json` | `41e748437c620117fac22d7ce4df3de3ce068ad44673f1a1adbdde514c950a92` |
| `r1/gpt2.json` | `8f0e4bcfe18a71b9bea98515e1aa8be4856ca73e8de0ce5e685e4cbab6f0151b` |
| `r1/gpt_neo_125m.json` | `090128e0b84d76ca0cac42ba4f00acd470b89603fedca52e8eecf54760351fb1` |
| `r1/qwen2_5_0_5b.json` | `425291b73d2d5a1e8702fcbf9f9bf3e62bf423225c6eb8d188018db317b3a5e1` |
| `r1/qwen3_0_6b_base.json` | `56f31e074f5d4d8d56266fcb74c71ca1b0fd8fbffee01be913995316e8e8f4eb` |
| `r1/smollm2_135m.json` | `445fc14935aac0007a3f287ab5f3e05856f9503c9c2797eda8e1545f1459a5a8` |
| `r1/smollm2_360m.json` | `7f77eb6fac9ce168dae42c030d7ede4f43035018f62529dccfd8289069bcfe47` |

The builder now performs no external execution during planning. A separately
authorized material build must APFS-bind the complete manifest-qualified base
Python runtime and all 39 wheels into attempt-owned paths before executing or
installing from them. The CLI requires explicit `--plan` or `--build`; all
bound inputs are revalidated before receipt sealing.

Current boundary remains target-free and `sealed_gate_pending`. Regeneration
reported two freezes, twelve approval-request dossiers, and zero model loads,
tokenizer constructions, sealed-target reads, CCP invocations, or remote
mutations. Gate B/C, real environment creation, installation, model/tokenizer
access, target reads, network, push, publication, and scientific execution
remain unauthorized. Final verification and a packaging commit may follow this
anchor without rewriting its generated `implementation_source_head`.

## Historical Hosted Gate A migration checkpoint

Tasks 1–9 of
`docs/superpowers/plans/2026-08-31-a0x-hosted-gate-a-implementation.md` are
locally complete through provider separation, Gate B lifecycle hardening, the
shared five-file Gate C boundary, and the explicit stale-freeze `NO-GO`. Task
10 records a documentation/implementation anchor and performs the one
controlled, target-free regeneration. The resulting dossiers retain that
immutable `implementation_source_head`; a later packaging or merge commit must
not rewrite it. Earlier implementation commits, freeze hashes, PR #109 wording,
and CCP Gate A receipts are **Historical evidence**; none qualifies this
branch.

Hosted Gate A has exactly seven target-free lanes: `repository-python311`,
`schema-cross-validation-python311`, `repository-python312`,
`schema-cross-validation-python312`, `a0x-no-model`, `a0x-synthetic`, and
`documentation-audit`. It binds four hosted inputs (manifest, attestation
bundle, trusted root, and transport) before Gate B may create the fifth
verification receipt. The respective caps are 32 KiB, 1 MiB, 2 MiB, 16 KiB,
and 32 KiB. Hosted qualification is one-run/no rerun; a local CCP Gate A
fallback is prohibited. CCP Gate C remains separately required for local
execution and never shares a producer identity with Hosted Gate A.

External publication, capture, the first real hosted run as acceptance, Gate B,
and Gate C each require a new separate authorization. Gate B/C, model,
tokenizer, target, and scientific execution remain unauthorized; status is
`sealed_gate_pending`. See the [Hosted Gate A operator runbook](A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md)
for refusal, retention, trusted-root revocation, governance, and restart limits.

## Frozen scientific legs

| Leg | Inherited experiment | Frozen endpoint | Public selection source | Dense-output cap |
| --- | --- | --- | --- | ---: |
| A0 | `a0-automated-weak-proxy-v1.0.3` | hidden-state tuple indices 0, 2, 4, 6 | exact raw bytes of `a0-selection-manifest.json` | 32 MiB |
| A0-R1 | `a0-r1-tier-r1-v1.0` | primary tuple index 6 | exact raw bytes of `data/a0r1/manifest.json` | 4 MiB |

The A0X protocol files copy the inherited corpus, split, controls,
statistics, thresholds, endpoint semantics, and outcome rules by JSON value.
They deliberately do not reuse the historical Pythia identity as a new model
identity. Each A0X model remains bound by its own exact card and runtime-file
receipts.

### Official architecture basis for the descriptive endpoint

The primary endpoint grids above remain unchanged. A0X additionally records
one **descriptive sensitivity endpoint** at the final transformer block. This
endpoint cannot replace, rescue, or alter a primary result.

The endpoint is derived rather than hard-coded. The official Transformers
[`hidden_states` contract](https://huggingface.co/docs/transformers/main_classes/output)
defines an initial embedding output, when the model returns one, followed by
one output for each layer. For the A0X adapters, the returned tuple must include
that initial embedding entry, have exactly `num_hidden_layers + 1` entries,
and place the final block at the exact model card's `num_hidden_layers` index.
The adapter verifies this convention rather than silently assuming it; an
absent embedding entry, unexpected cardinality, or card where those fields
differ fails closed before analysis.

| Exact model snapshot | Official layer-count source | Derived final-block tuple index |
| --- | --- | ---: |
| SmolLM2-360M `f8027fd...` | [pinned `config.json`](https://huggingface.co/HuggingFaceTB/SmolLM2-360M/blob/f8027fd0eaeea54caa13c31d31b9fdc459c38b49/config.json), `num_hidden_layers` | 32 |
| Qwen3-0.6B-Base `da87bfb...` | [pinned `config.json`](https://huggingface.co/Qwen/Qwen3-0.6B-Base/blob/da87bfb608c14b7cf20ba1ce41287e8de496c0cd/config.json), `num_hidden_layers` | 28 |
| GPT-2 `607a30d...` | [official config](https://huggingface.co/openai-community/gpt2/blob/main/config.json) and [pinned revision](https://huggingface.co/openai-community/gpt2/commit/607a30d783dfa663caf39e06633721c8d4cfcd7e), architecture-equivalent `n_layer` | 12 |
| SmolLM2-135M `93efa2f...` | exact locally receipt-bound `config.json`, corroborated by the [current official config](https://huggingface.co/HuggingFaceTB/SmolLM2-135M/blob/main/config.json) | 30 |
| GPT-Neo-125M `21def018...` | [pinned `config.json`](https://huggingface.co/EleutherAI/gpt-neo-125m/blob/21def0189f5705e2521767faed922f1f15e7d7db/config.json), architecture-equivalent `num_layers` | 12 |
| Qwen2.5-0.5B `060db649...` | [pinned `config.json`](https://huggingface.co/Qwen/Qwen2.5-0.5B/blob/060db6499f32faf8b98477b0a26969ef7d8b9987/config.json), `num_hidden_layers` | 24 |

The SmolLM2-135M row deliberately distinguishes the exact local integrity
receipt from a mutable public configuration that corroborates the same
architecture and layer count: the former is the runtime authority for this
frozen campaign. The exact `93efa2f...` public configuration was not
independently opened in this documentation pass, and no external link may
silently change the frozen card.

The two frozen manifests form this acyclic chain:

```text
historical scientific rules + protected tree + public selection source
                              |
                              v
                 A0X protocol + implementation
                              |
                              v
                    per-leg freeze manifest
                              |
                              v
             six independent approval dossiers
```

Protocols and implementations do not contain their own hashes. Freeze
manifests hash the protocol and implementation but do not contain their own
hash. Dossiers bind the raw freeze hash and never hash themselves.

## Exact model set and fixed commands

The model choice is not left to the executor. Each pair has one fixed Make
target and one fixed dossier.

| Leg | Model | Fixed target | Dossier |
| --- | --- | --- | --- |
| A0 | SmolLM2-360M | `make a0x-material-a0-smollm2-360m` | `approval-dossiers/a0/smollm2_360m.json` |
| A0 | Qwen3-0.6B Base | `make a0x-material-a0-qwen3-0-6b-base` | `approval-dossiers/a0/qwen3_0_6b_base.json` |
| A0 | GPT-2 | `make a0x-material-a0-gpt2` | `approval-dossiers/a0/gpt2.json` |
| A0 | SmolLM2-135M | `make a0x-material-a0-smollm2-135m` | `approval-dossiers/a0/smollm2_135m.json` |
| A0 | GPT-Neo-125M | `make a0x-material-a0-gpt-neo-125m` | `approval-dossiers/a0/gpt_neo_125m.json` |
| A0 | Qwen2.5-0.5B | `make a0x-material-a0-qwen2-5-0-5b` | `approval-dossiers/a0/qwen2_5_0_5b.json` |
| A0-R1 | SmolLM2-360M | `make a0x-material-r1-smollm2-360m` | `approval-dossiers/r1/smollm2_360m.json` |
| A0-R1 | Qwen3-0.6B Base | `make a0x-material-r1-qwen3-0-6b-base` | `approval-dossiers/r1/qwen3_0_6b_base.json` |
| A0-R1 | GPT-2 | `make a0x-material-r1-gpt2` | `approval-dossiers/r1/gpt2.json` |
| A0-R1 | SmolLM2-135M | `make a0x-material-r1-smollm2-135m` | `approval-dossiers/r1/smollm2_135m.json` |
| A0-R1 | GPT-Neo-125M | `make a0x-material-r1-gpt-neo-125m` | `approval-dossiers/r1/gpt_neo_125m.json` |
| A0-R1 | Qwen2.5-0.5B | `make a0x-material-r1-qwen2-5-0-5b` | `approval-dossiers/r1/qwen2_5_0_5b.json` |

All dossier paths are relative to `experiments/a0x-six-model/` in this table.
The model keys inside the contracts use the canonical underscore form; the
human-facing Make targets use hyphenated slugs. The verifier proves this
mapping is complete and bijective.

## Safe no-model verification

The following commands are preparatory and must report zero material access:

```bash
rtk make a0x-no-model-verify
rtk env PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_a0x_*.py' -v
rtk make docs-audit
rtk git diff --check
```

`a0x-no-model-verify` is a strict superset of the earlier synthetic verifier.
It validates both frozen legs, every inherited-rule copy, all source/test
hashes, both protected-tree identities, both public-selection identities, the
twelve-dossier Cartesian product, per-model dense bounds, and the fixed
Make-target mapping. It must report:

- zero model loads;
- zero material tokenizer constructions;
- zero sealed-target content reads;
- zero CCP invocations;
- zero remote mutations.

## Material approval boundary

Material execution is outside Task 11. Before one pair may run, all of the
following must be true at the same exact source HEAD:

The following are three separate operator stops, not one reusable approval:

1. **A — repository qualification.** An exact-head authorization names one
   repository qualification only; it must reach its terminal positive receipt.
2. **B — runtime-bundle preparation.** A separate exact pair/attempt
   authorization may prepare descriptor, authorization, and local mapping for
   exactly one dossier/pair/attempt. It does not start material work.
3. **C — material attempt.** A later one-shot material authorization must name
   the prepared authorization raw SHA-256 as well as the pair and attempt. It
   is the only stop that may permit the material action.

The current campaign is `sealed_gate_pending` and stops before **A**. Neither
the preparer, synthetic tests, nor regenerated approval-request artifacts
open **A**, **B**, or **C**.

The following are conditions inside those three stops, not additional stops:

- **A** owns one exact positive Matrix generation and its terminal exact-head
  receipt; the installed CCP path and full SHA-256 must match the current
  operator contract, while live resources must be `Admit` with inactive
  admission and an empty queue.
- **B** owns preparation for exactly one dossier, pair, and attempt after the
  Gate A receipt has been bound.
- **C** owns one material execution authorization bound to exactly one dossier
  SHA-256, one prepared authorization raw SHA-256, one pair, and one attempt
  ID. A primary reviewer confirms the complete chain and fixed command.

One approval is not reusable for another model, another leg, another source
HEAD, or a retry. A null, positive, failed, incompatible, interrupted, or
non-interpretable first outcome consumes the attempt and must be preserved.

An operator authorization should name at least:

```text
repository and exact source HEAD
one dossier path and raw SHA-256
one leg and one exact model/revision
exact CCP path, source commit, tree, executable SHA-256, and version
exact repository-qualification authorization and its positive generation
exact terminal qualification receipt SHA-256
one authorization ID, one attempt ID, and maximum run count 1
CPU float32, offline, no generation
the dossier-specific dense-output cap
one sealed-target read at the analysis boundary
publication of every terminal outcome
no tuning, substitution, pooling, protocol change, or retry
```

Luna may invoke only the fixed argument-free Make target after these facts are
recorded and independently checked. Luna must not choose a model, edit a
dossier, interpret a CCP denial, alter an endpoint or cap, authorize a retry,
or decide publication and merge.

## Interpretation boundary

The twelve outcomes remain independent exploratory replications. They must not
be pooled into one significance claim and must not be ranked as a model
leaderboard. A repeated proxy signal would support only persistence of the
frozen automated proxy across the tested exact model families. A null or
failed outcome does not by itself falsify the construct-level Latent TRIZ
hypothesis. Human TRIZ construct validation, stronger controls,
generalization, compositionality, and causal intervention remain separate
gates.

## Historical runtime-binding correction checkpoint

The earlier private runtime descriptor had an unmaterializable reciprocal hash
dependency. Descriptor-v2 removes that cycle: the operator-rooted execution
authorization binds the exact raw descriptor bytes; the descriptor refers only
to its pair-derived authorization path and byte-bound material contract; and
the local role mapping repeats the descriptor path and hash. The offline
preparer writes readiness, descriptor, authorization, and mapping only in that
dependency order and refuses every existing output path.

This is a three-stop design. First, **A** explicitly authorizes and completes
one exact-head repository qualification. Second, **B** separately authorizes
one exact pair/attempt private runtime bundle, binding the resulting dossier,
qualification receipt, authorization ID, and attempt ID. Third, **C** is a
later one-shot material authorization bound to that prepared authorization raw
SHA-256. No earlier stop opens a later one; the preparer, its synthetic tests,
and regenerated approval-request artifacts open none of them.

The frozen-inventory defect discovered during this correction was
`scripts/a0x_material_child.py`: its live bytes are 21,582 and its SHA-256 is
`fda405fbe6a3000f7de9b597aeea23300b5ecb107394411bddd21c3d3ba93955`.
It was not `tests/test_a0x_runtime_bundle.py`. Both leg inventories now bind
the preparer CLI, preparer module, and its regression suite, and the canonical
package is regenerated only from the post-inventory implementation commit.

### Pre-material readiness gate

The successful Gate A qualification of public source
`68f8bfe75a883054118246101485f71a56a5e82e` is preserved by receipt-file
SHA-256 `3f75c665115c00fd18df1a5fb403f6dd5e410b5d5cdb12c78eada39effb1810e`
and receipt ID
`sha256:2c82dc5205ad0b0c788fc1e5837ea9a790dfe924c488878b7a73413867103093`.
Its public evidence branch is rooted at commit
`fc46c39421ae85713f473ef49a1270beab3aefe6`. This is valid historical Gate A
evidence for that exact source only; the readiness correction changes frozen
implementation inputs and therefore requires a new Gate A qualification after
regeneration.

A target-free audit before Gate B found two independent blockers that the
earlier bundle contract did not prove:

- the available virtual-environment launcher was a symlink; resolving it
  selected the Homebrew base interpreter and lost the required package set;
- the isolated execution clone intentionally contained no model snapshot, so
  its pair-specific runtime root could not pass the allowlist/hash checks.

Gate B must now create or select one independent regular Python 3.11
executable in an exact virtual environment and materialize only the selected
pair's already acquired snapshot inside the isolated execution clone as
independent regular files. Symlinks and hardlinks are refused. On APFS, a
copy-on-write copy may avoid duplicating physical blocks, but it remains an
explicit Gate B action and must be followed by byte/size/SHA-256 verification.
The preparer records one private readiness receipt binding exact interpreter
bytes, the five pinned packages, required APIs, card bytes, runtime-file
commitment, and pair identity. The descriptor binds that receipt before any
authorization or role mapping is produced.

The offline prerequisite builder now makes that process explicit and
reproducible. It binds the clean source HEAD, the exact 39-wheel manifest, the
base Python and bootstrap `pip`, the model card, and the allowlisted source
snapshot. It creates the environment with `venv --copies`, installs only
hash-locked wheels with no index or dependency resolution, removes bootstrap
`pip`, requires the final exact 39-distribution set, and materializes the card
files only through APFS `clonefile(2)`. It writes a local prerequisite receipt
last; it does not write the Hosted Gate A verification receipt, readiness,
descriptor, authorization, mapping, or scientific output.

The verified local wheelhouse manifest is
`fe541aa83b5dbd9770da1f50d2cd88eb192586406398d9cffa5507f9f352ca72`
(39 wheels; 150,397,774 bytes). The wheel bytes remain ignored and local.
Their verification is not a Gate B authorization and is not portable public
evidence. This implementation tranche uses only synthetic fixtures; no real
environment, package installation, model snapshot, tokenizer, target, or
scientific action is performed.

The same correction also enforces a model card's non-null `pad_side` before
model construction and makes a post-claim failure to persist the pre-run
observation terminal recovery evidence without starting the child. No bundle,
model, tokenizer, target, CCP, Docker, or remote action was used to discover
or test these corrections.

Future Gate B preparation follows the separate no-write, APFS clonefile,
offline-wheelhouse and immutable-preparation boundaries in
[A0X Gate B operator hardening](A0X_GATE_B_OPERATOR_HARDENING.md). This
hardening does not change the bytes or status of any already prepared bundle.
Because it changes frozen implementation inputs, it requires a new exact-head
Gate A qualification before it can govern a future material attempt.

The historical hosted-integration implementation anchor was
`74d6bc048e656f3ced2d4bc6db4b0492dfd16359`. Public `main` is now
`d2a475f58db668a2ce0a4ec48082189422b19eab`, tree
`4d2b1221dd63a89d6c6c4433061a7d8ed130b76e`, after PR #110 installed the
pinned schema oracle in both GitHub-hosted repository lanes. PR #110 required a
one-time CCP-backed administrative bootstrap bridge after its hosted run failed
on the missing dependency; the bridge is not a hosted PASS and is not reusable.
PR #109 integrated that main without history rewrite at ancestry commit
`7ac5a6065d78974f52a86816b019184f8f147bd7`; its tree remained byte-identical
to the pre-integration A0X head, so no protected implementation member changed
and regeneration was not triggered merely by ancestry. Canonical target-free
regeneration at the implementation anchor produced the following exact
approval-request dossier hashes:

| Leg/model | Dossier SHA-256 |
| --- | --- |
| A0 / GPT-2 | `86e9ae7dc951cab86ee0034939db21f76d423de2f7812a242d7a89af7273feef` |
| A0 / GPT-Neo-125M | `79f7524bbff0de66c2a5cea089f4a25abe75bd5a52d6ba050dc0a4424cf6bbfa` |
| A0 / Qwen2.5-0.5B | `bb5448a66a004e65adf1da67d1aba711761455bbd1355b7c0c3e9d2aaee62093` |
| A0 / Qwen3-0.6B Base | `f6d98408721d237eb768d0790d534b84fc6eb52930cfb57d464277a2ee3a40a2` |
| A0 / SmolLM2-135M | `c9e95325a66e06811ee8e535a7a6bdbb464384fe1e9b29522eb64a7f5d310314` |
| A0 / SmolLM2-360M | `9252f35a159c435af83c56acf4ed4192a79c9454d5ec2da5fd32ccdc0b26695f` |
| A0-R1 / GPT-2 | `f191ec0bafba2c8ff5cb0e6a9dbeaf234c52675f4c6fc0875dca99baba2e883f` |
| A0-R1 / GPT-Neo-125M | `dc6685fdb5ff753d9dc47d501a2c9e238835c31bf6853abff270861d52cbd644` |
| A0-R1 / Qwen2.5-0.5B | `0046d789b5bf070c9b75e9e6701d97d02b933c62979ee9978203dce615b2f955` |
| A0-R1 / Qwen3-0.6B Base | `668bb760e9269e20308ee12a3bf88e9983b55e5bc131387c5008485cefbd40d1` |
| A0-R1 / SmolLM2-135M | `5a37fd8023b3bf35a09c21abecf0fbdff330fe3c8cff999f49f2117b7bc795b3` |
| A0-R1 / SmolLM2-360M | `c58ceeb29f6dbd0a9dbbc8c71669e17aa971bf95261c798a1121bfbd6f0e81c7` |

The material contract remains byte-identical at
`b56b860a4f4673f675035e0c76aa1b79e75b37ace9c441b2d1e36076d35c3fc8`.
The builder implementation anchor is
`0eb13410591cce4ad48c5a1f77fee765d587aa48`, tree
`d36010a678339c70c1ee782a71990aa4f8b1cd07`. The regenerated bindings are A0
implementation/freeze
`e663513ec1b4175dae39982cb35a40f652e60e80fac6f9a3a83ea5e17463f316` /
`91b040c4700083b412769cc17b013c8271ea7a8217ccc9bdf21e67339294e7eb`
and A0-R1 implementation/freeze
`857ee11cae8919de9c242262634c14f83c84943a8c376a30e508d368d6bed4c3` /
`02c57238d1da8449636b330a7455a1be3b20cf7e3a8bfe3167a2add7ae693935`.
Final target-free verification after this regeneration passed: focused Gate B
hardening 97/97, frozen 11/11, synthetic A0X aggregate 293/293, schema
cross-validation 155 agreements plus 19 rejected mutations, and the complete
repository suite 1,125 tests with 11 documented skips. No model, tokenizer,
sealed target, CCP heavy command, or scientific execution occurred. The branch
remains `sealed_gate_pending`. Fresh local and GitHub-hosted verification is
required on the reconstructed PR #109 head; publication does not authorize
Gate B or C.

## Historical 2026-08-25 checkpoint

The campaign remains `sealed_gate_pending`. The material composition is no
longer a refusal stub: it now has a fixed outer launcher, an acyclic
descriptor-v2 chain, a deterministic overwrite-refusing private runtime inlet,
a one-shot target reader, terminal sealing, package verification,
protected-tree postflight, and model release. All of those paths have been
exercised only with synthetic injected dependencies.

Every pair uses the same execution envelope:

- CCP child timeout: exactly 3,600 seconds;
- internal monotonic scientific budget: exactly 3,300 seconds;
- reserved sealing and cleanup margin: 300 seconds;
- admission wait: 300 seconds.

The extra 300 seconds are not scientific compute time. Crossing the internal
deadline seals the first terminal result; the remaining time is reserved for
durable packaging and cleanup. The private supervisor may wait up to 3,900
seconds only so it does not race CCP's own 3,600-second timeout and final
cleanup. It does not extend the authorized material workload.

The public contract is host-path-free. It binds roles, relative locators,
hashes, the exact shell-free guard template, and the exact terminally
qualified CCP producer:

- source commit `27adf8d0820b3cd96f9c5e149de9b580ae41f639`;
- source tree `d8e0364d1313fde0898a44517ae6d233d9e10763`;
- executable SHA-256
  `c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`;
- plan-output SHA-256
  `0969a1eeb62b2a92593cda0b75c8814d7eca893bebc736ec968f02aa9f2a5fad`.

Repository qualification remains a separate configuration-backed `run` flow.
Its two repository checks each have a 3,600-second configured timeout; the two
schema checks remain at 300 seconds. These qualification limits are distinct
from the 3,300-second scientific budget above. Every operator target for
repository qualification passes
`--matrix-plan-profile matrix-v2-legacy-v1`, and receipt verification uses
`.commit-ci-policy-v2.toml`. The reviewed plan digests are outer
`sha256:8eb0172c30aac8f9b47f65cebd222ee6615b17e4053a5a16e2be5583f3a10331`,
Python 3.11
`sha256:aa69a8795e20733a516fac99b253cfc26a9f963825ff1fa9ca5638364f7fc943`,
and Python 3.12
`sha256:072e50972a02f2df710bf81620ca058d230f0637bcc16a47ba35562fe1358510`.
The scientific workload uses `guard exec`, so its fresh preflight does not call
`plan`, `doctor`, or `dry-run`. It records six bounded read-only roles instead:
CCP version, resource status, admission status, Git source state, runtime
context, and active-container count. Each probe has a 30-second timeout and a
64-KiB capture ceiling and fails closed on timeout, excess output, dirty or
wrong source, non-Admit resources, non-idle admission, unavailable runtime, or
an active container.

**Historical runtime-binding checkpoint.** The former implementation anchor was
`e2f557909c9f816eb40ae5aae7be54cb523c97cd`; its generated package is commit
`a52a621d67a379937475fa066639cedd215c4c27`. The package is still
`sealed_gate_pending`: stop before **A**, one new exact-head repository
qualification; then require distinct authorization **B** for one exact
pair/attempt private-bundle preparation; then require distinct one-shot
material authorization **C** bound to the prepared authorization raw SHA-256.
Neither the package nor this documentation grants any stop.

| Artifact | SHA-256 |
| --- | --- |
| Material execution contract | `b56b860a4f4673f675035e0c76aa1b79e75b37ace9c441b2d1e36076d35c3fc8` |
| A0 protocol | `42e252b21dd9f1d6b793be304bfe708d2d9324e8e08ffe1d1915e7f01b75f586` |
| A0 implementation | `f168ad9cec7cd757c12a711e5c138608bbaa86ec2fe826ed2d9af210a4942e8e` |
| A0 freeze | `a8ca1889f91cd965399eaa9f3ac066d1f5b7bc9beea26ee2ceca517ebb358353` |
| A0-R1 protocol | `32d8bbfcbd76e38d51a2eff012c22e65bfe0c1eca4f6d0bf345f309777df4b52` |
| A0-R1 implementation | `705de31ef6c8dd8d53cb34c611de49637fed6e51719077e7c63524a5391abfdd` |
| A0-R1 freeze | `b8c470d45b098233f3497cb75d7fc95a41edd9f7772539b55db71aa803355c64` |
| No-model verification receipt | `c761ae76d77b976ea83bc83aa139da9730858a387422aff501ffad1b87217e4c` |
| A0 / SmolLM2-360M dossier | `f71f57de77d99e7c5e4c3c90cf5975213b0d4cc11f135068ccefa89325cc4ca3` |
| A0 / Qwen3-0.6B-Base dossier | `873a87a4d5bace562df80b97c2b4138141064202172e94c39a731ba23822e3ec` |
| A0 / GPT-2 dossier | `26c37f8fc19f59c95cd0c02e071c5b758b6ad43d35cf3409263767f8a9744bae` |
| A0 / SmolLM2-135M dossier | `857df3060cc71493920a2e170ec3c36d8e37d02238ced879023650a8e24ed450` |
| A0 / GPT-Neo-125M dossier | `2dd6def8af02343b8ec33bdd553c3ec0f20af5948cfeea7f7f4bddd33cd9bbee` |
| A0 / Qwen2.5-0.5B dossier | `af475aacd4e947ea30b119e74cff31d15798d5ceefd782ea18b00bfc71d0cc96` |
| A0-R1 / SmolLM2-360M dossier | `942f73da7528d1c3ba2ae8569a0ab6cd24ba513c9b80068c6244e185d157de0f` |
| A0-R1 / Qwen3-0.6B-Base dossier | `2f9df9292477a3e967d237d839d5dcaa6c668fd0fb7c8280919c8923a9f23a0c` |
| A0-R1 / GPT-2 dossier | `9bb38d992bda0fdcc94d825e2e950be8d4ea1d8de75d0ff5d9da90f7f0b26aa3` |
| A0-R1 / SmolLM2-135M dossier | `c31538a72a253d78b25c0f38baf95c4ec76c3f3f3fdb107f4e39f60d01dbbcb2` |
| A0-R1 / GPT-Neo-125M dossier | `a94b49a9640977669af38969782095fcc69a8d36155e5b0d4cbd0a1598e4ed4d` |
| A0-R1 / Qwen2.5-0.5B dossier | `797cf4fd525daae3e5853c5216d5f82ad11e102b4666fcdc23f28e7ff71ec219` |

These are historical approval-request artifacts only. They bind the former
runtime-binding checkpoint and do not authorize A, B, or C. The current
approval-request hashes are listed in the pre-material readiness section above.

**Historical producer/receipt note.** The former package bound the TDD-corrected
producer that passed one exact generation-1 Matrix qualification. Its receipt ID is
`sha256:21d5cf99a9d142b879b37ef8bb2f50573e45fd569a2259fa863a50fe6be08e85`
and its receipt-file SHA-256 is
`14df36450ce982b0c5233651baa4c5f5d0e0c462b1b5f119ec8f93a9ad7465ce`.
The source is preserved on public branch
`agent/matrix-v2-legacy-terminal-release-qualified`; its receipt is published
only on `ccp-evidence/27adf8d0820b3cd96f9c5e149de9b580ae41f639`, and
[CCP PR #70](https://github.com/MarcoPorcellato/commit-ci-preflight/pull/70)
is merged as `1a2e081cd3912b0fd63a7226a4564f1d85a51eb8`; that merge has the exact
qualified tree. The producer is deliberately selected for A0X but is not the
installed stable executable.

The prior exact-head attempt at `32e03b5…` is preserved as terminal `FAIL`:
both schema checks passed and both repository checks reached their configured
approximately 300-second limits. The corrected package does not reinterpret or
retry that attempt. Before any scientific attempt, complete one newly
authorized exact-head Latent-TRIZ qualification using this selected producer,
the explicit legacy profile, and the exact reviewed V2 plan. Each scientific pair then needs a new
execution authorization bound to its exact dossier, live source HEAD,
qualification receipt, authorization ID, and attempt ID. No CCP heavy run,
Docker action, model/tokenizer construction, target read, publication, or retry
occurred in this correction.

The subsequent one authorized exact-head attempt at `fb9484a…` is also
preserved as terminal `FAIL`. Both schema checks passed, while both repository
checks returned exit 1 without timeout or cancellation. Receipt ID
`sha256:f5348d82568ba98c6003132534b3a202631f04c42972b965251adaa2ca367dde`;
receipt-file SHA-256
`5bb2e49da31381e4c22858556e4c54f373ee69dfcea8f578e050efb6268e4232`.
The exact failure was five attempts by the Matrix binding test to execute
`make -n` in lean verification images that remove build-only `make`. A clean
host suite passed, and the failure reproduced under a no-`make` `PATH`. The
dependency-free Python recipe verifier is the only behavioral correction; the
protocol, plan profile, timeouts, policies, and scientific rules are unchanged.
This attempt is consumed and does not authorize a retry.

The later one authorized Gate A qualification at
`e340e142fcd745d47dec1df386eb9fdb1b2e15f7` is likewise preserved as terminal
`FAIL`. Both schema checks passed; both repository checks returned exit code 1
without timeout. Receipt-file SHA-256:
`6e354744099921f240108698258a184b2bdfbe170e9b29975bb305a88cfb99ac`.
One separately authorized Python 3.11 diagnostic reproduced 24 errors and one
derived failure across 1,099 tests. The shared runtime-bundle fixture created
inert synthetic executables on writable `/dev/shm`, while that container temp
mount did not grant executable access. The production executable check remains
unchanged. A test-only seam now recognizes only the fixture's two exact inert
files and delegates all other access checks to the operating system. Because
that fixture is frozen implementation input, both implementations, both
freezes, and all twelve dossiers require deterministic regeneration from the
new corrective implementation anchor before another explicit Gate A
authorization can be requested. No scientific artifact or claim changes.

The corrective implementation anchor is
`d4845f0a7b204ba65b9669c05a677fc0560ababd`. Deterministic no-material
regeneration produced A0 implementation/freeze SHA-256
`2398f026dc352be8a11950e0cb0996437d87b4ca1f0db11558d40e16f31c7b57` /
`cc78b1baf158d0a0c3f9e77cd411d8fff5abd0b579947687c2f53d55aa027ac1`
and A0-R1 implementation/freeze SHA-256
`6246c84fc4c7fc48114598406c5fa6a8b457f2fdb973626142bad30e7c68e004` /
`c4564adcd1e767e339467db953540123017284461abbd8225ed95ab1bb49695a`.
Frozen verification passed 11/11, the synthetic aggregate passed 268/268, and
the repository check passed 1,100 tests with 11 documented skips. The next
action remains a separately authorized exact-head Gate A qualification after
the regenerated package is committed.

## Validator-isolation correction

The A0-R2/C3 validator remains the exact historical dependency-free subset and
therefore rejects `prefixItems`. A0X owns a copied dependency-free extension
for exactly three positional schemas: Hosted Gate A evidence, the v2 slice
manifest, and the v2 package commitment. A0X v2 runtime callers use that
extension only where needed; Hosted Gate A remains independently checked by
the pinned Draft 2020-12 validator. `schema_cross_validate.py` retains its
legacy matrix separately and reports the A0X positional matrix independently.

Before current A0X bindings are replaced, the immutable Git-object ledger
`docs/qualification/a0x-batch-pre-regeneration-ledger-ab047833.json` records
the exact `ab0478331c5bfa9d6b3cb983d5e4550e68f53aa9` parent/tree and all
seventeen superseded generated artifacts. It is historical audit evidence,
not an authorization or an active runtime input.
