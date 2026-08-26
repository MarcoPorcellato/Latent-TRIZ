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

1. a separate repository-qualification authorization owns one exact positive
   Matrix generation, and the repository has its terminal exact-head receipt;
2. the installed CCP path and full SHA-256 match the current operator
   contract;
3. live `resource status` is `Admit`, admission is inactive, and the queue is
   empty;
4. the operator supplies a new per-pair execution authorization bound to
   exactly one dossier SHA-256, one pair, the exact qualification receipt, and
   one attempt ID; this authorization contains no Matrix generation;
5. a primary reviewer confirms the authorization chain and fixed command.

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

## Current checkpoint

The local no-model package remains at `sealed_gate_pending`. It is now bound to
the reviewed CCP compatibility candidate at source commit
`c91915adcb8706898574c0c74d033b9ff991eefb`, tree
`687fcaaa3643d35a66ba748409e5621d13e25dd7`, and executable SHA-256
`72a3458987e18313ceacfc97d8e7902d2d5338eb8eb609320fd37ca58aedd4be`.
The exact `matrix-v2-legacy-v1` profile reproduces the historical trusted-base
outer and runtime digests from a disclosed, reconstructible digest basis. The
default CCP profile remains unchanged.

The fetched official CCP `origin/main` is
`2b4b55ce1a4be0a2b610656ae4a56a7641b29f26`. That public main includes the
current admission rules, full-lifecycle standard-run cache locks, and
spawn-boundary generation revalidation. The legacy Matrix profile is an
additional reviewed candidate change on top of that main; it is not yet an
official released capability. Its static suite passed 394 tests with four
documented ignores, and an independent review returned GO. No terminal CCP
qualification receipt exists for the candidate yet.

After regeneration, the A0X suite passed 197 tests with three expected skips;
the frozen-package suite passed 9/9; and schema cross-validation reported 155
tracked pairs in agreement with 19 mutations rejected by both validators. The
no-model receipt reports two frozen legs, twelve `approval_requested` dossiers,
and zero model loads, tokenizer constructions, sealed-target reads, CCP
invocations, or remote mutations. The next gate is an explicitly authorized
single exact-head CCP qualification of the candidate. A positive candidate
receipt would still not authorize installation, Latent-TRIZ exact-head
qualification, publication, or any scientific run.

| Artifact | SHA-256 |
| --- | --- |
| Material execution contract | `5b9754c5689b6f48476768c61a58afcac6b7c6e88ee289a5b16678ec26021ca4` |
| A0 freeze | `711d7df84baf2cceaea6f0567733feec24292e4ca872fc66da79ece7e7577569` |
| A0-R1 freeze | `d43a91f02089ce6a103d6afe6126076ea53e480bbe68e49abcf61f3dee0e240b` |
| A0 / SmolLM2-360M dossier | `26ed343b750ea396eddc5b7b413e900b4dcc1b28e63b4d013212b9689992a7a9` |
| A0 / Qwen3-0.6B-Base dossier | `64fe1cacbd1999fc7d539ff0ddc557a0ee7bcf7edd3c53a76102c97d2d99c64d` |
| A0 / GPT-2 dossier | `d7c72afa535a7d2f708f380981fce64fb03df4dcb2882f5a5021f1769afc8647` |
| A0 / SmolLM2-135M dossier | `41cc33d1e7d99d156e1f77d19ddde816d33f69de41c4f5e79309a623808a19e7` |
| A0 / GPT-Neo-125M dossier | `9429986eb13bac01772ac6812fc5577faf9f4c5cfac56c2fbafdf9af917f6802` |
| A0 / Qwen2.5-0.5B dossier | `e86b56373d7b1e4951212ae9397e96f0c1026fe19ef810da3be8a50c9cd7084c` |
| A0-R1 / SmolLM2-360M dossier | `ebeefd625ebfa482552110de361668229c746cd5edb6bcee358358254f5b6b53` |
| A0-R1 / Qwen3-0.6B-Base dossier | `2e88c6618450e0576333cb628c6dc95cad1f81a53fcb45e1f80127b2013286d1` |
| A0-R1 / GPT-2 dossier | `5abfb2f9c48b489aeb5ac9ac50f106514ef4517e66be9dc97cf7327eb38e1ced` |
| A0-R1 / SmolLM2-135M dossier | `fa9cedff182aa229b93f06c2955885de015bb02dd13d1b62309a00e8c7cdc630` |
| A0-R1 / GPT-Neo-125M dossier | `6f5b01d86a6ca3477d54321622a3954ba53312991ef39dd544e07422225a0f03` |
| A0-R1 / Qwen2.5-0.5B dossier | `5268f25e090023c33779e29ada93862695e8b1dc249c72470f73a7208ca97816` |

These hashes identify approval requests only. The consolidation commit that
contains this table is the next source anchor and must be resolved live rather
than self-recorded here. No CCP exact-head qualification, model/target access,
GitHub publication, or execution authorization has occurred.
