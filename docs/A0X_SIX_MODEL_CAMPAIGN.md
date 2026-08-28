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

The campaign remains `sealed_gate_pending`. The material composition is no
longer a refusal stub: it now has a fixed outer launcher, an exact child
descriptor, a pair-scoped private runtime inlet, a one-shot target reader,
terminal sealing, package verification, protected-tree postflight, and model
release. All of those paths have been exercised only with synthetic injected
dependencies.

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
hashes, the exact shell-free guard template, and the exact reconciled CCP
candidate:

- source commit `a73ebed945d9d9e9744c4aff987589f3478a7f3c`;
- source tree `b12ff9ac9daa67d52e28c6793e14f646c5e37225`;
- executable SHA-256
  `2f7fe3fce7d44cdd8350c0248f1c3b5b5c9fc4d023c05adcdb320d41785fa45f`;
- plan-output SHA-256
  `4f401a3c13d94c48c722137511515bdb70099b596bbdb9756ec2cb491282e9e`.

Repository qualification remains a separate configuration-backed `run` flow.
The scientific workload uses `guard exec`, so its fresh preflight does not call
`plan`, `doctor`, or `dry-run`. It records six bounded read-only roles instead:
CCP version, resource status, admission status, Git source state, runtime
context, and active-container count. Each probe has a 30-second timeout and a
64-KiB capture ceiling and fails closed on timeout, excess output, dirty or
wrong source, non-Admit resources, non-idle admission, unavailable runtime, or
an active container.

Implementation anchor: `3dc40aa104358a83855cd59a40df30319131ea1e`.
The two freezes and twelve dossiers were regenerated from that exact anchor.
The synthetic aggregate passed 245 tests with three documented skips; the
frozen package passed 10/10. The no-model receipt reports zero model loads,
tokenizer constructions, sealed-target reads, CCP invocations, and remote
mutations.

| Artifact | SHA-256 |
| --- | --- |
| Material execution contract | `e4ab21c24a491a26e43b07be4cbc0102a84c7482cc425883ca5bda38ba988e1a` |
| A0 protocol | `42e252b21dd9f1d6b793be304bfe708d2d9324e8e08ffe1d1915e7f01b75f586` |
| A0 implementation | `886a2ec13b64ed376b443e36426322d64b59b6b38293484dfd0e2ed4e688efd5` |
| A0 freeze | `8817b260737f558259ad5091858513e0f7a156ec751e6191d077a5bdde057aee` |
| A0-R1 protocol | `32d8bbfcbd76e38d51a2eff012c22e65bfe0c1eca4f6d0bf345f309777df4b52` |
| A0-R1 implementation | `4467bc8d07b18372b9467e613ad54323a498dcc121f62ba3da01493e46d4459c` |
| A0-R1 freeze | `c1f43cfc834b788c45c90c66ab4602ccd3836c6da0b97b1fc4272089e05b19df` |
| No-model verification receipt | `c761ae76d77b976ea83bc83aa139da9730858a387422aff501ffad1b87217e4c` |
| A0 / SmolLM2-360M dossier | `ca9baf450e7c6528b80a9ed9dd5ccd619f23477829c7a78ee28531c3bc55b59e` |
| A0 / Qwen3-0.6B-Base dossier | `9a8afb0bdefa7a2f84b50269c6d9df36269a6eeab7ba3819c3bb0a25e702b326` |
| A0 / GPT-2 dossier | `526e3f86dcf6a0749afb578ad18ecd3f728c49c044f2b2a01408adc9534acf26` |
| A0 / SmolLM2-135M dossier | `02d211e42396c9d7b007409853b1d97473281a72ff3320e9b7113b0a034179df` |
| A0 / GPT-Neo-125M dossier | `0332331604f1f20ea752f186d3d5eff99f5e067e3e06017ab5fa5a5478721830` |
| A0 / Qwen2.5-0.5B dossier | `c3ea7d33e28a88819d2b74dda2ed35d788312b4a4c17040b4b43caef25942916` |
| A0-R1 / SmolLM2-360M dossier | `d930d2eda9385f5d44d3e30e3f28d1003f58042f0273758818072a8852b2de2b` |
| A0-R1 / Qwen3-0.6B-Base dossier | `0cb374df8a7e877a4df06bd3dedbbda1d53a87eaff9eb2b311aa90a6db0145d4` |
| A0-R1 / GPT-2 dossier | `ca2519b5ed92f25a792ac4679a8a0df682c212b779dc7c21ea4810eb6fdc5edf` |
| A0-R1 / SmolLM2-135M dossier | `f3acc82247c614790d84cc66110c7436bdeb1daecb4ab8f50b862cf09f4b46f1` |
| A0-R1 / GPT-Neo-125M dossier | `5691cdadc19c14c17fe699c73c43433bb14e84299b49ed9512e7e0f49ef893d8` |
| A0-R1 / Qwen2.5-0.5B dossier | `af2ed0739dfc144d6629753efc26c8e29cab6edc9334f39f79463cf99daf348a` |

These are approval-request artifacts only. The reconciled CCP candidate still
requires its own terminal heavy qualification and deliberate installation or
an exact authorized candidate path. Each scientific pair then needs a new
execution authorization bound to its exact dossier, live source HEAD,
qualification receipt, authorization ID, and attempt ID. No CCP heavy run,
Docker action, model/tokenizer construction, target read, publication, or retry
occurred in this correction.
