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
hashes, the exact shell-free guard template, and the exact terminally
qualified CCP producer:

- source commit `27adf8d0820b3cd96f9c5e149de9b580ae41f639`;
- source tree `d8e0364d1313fde0898a44517ae6d233d9e10763`;
- executable SHA-256
  `c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`;
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

Implementation anchor: `9aeb6ef664b0576cb8a1ed58f50791be3bb070cb`.
The two freezes and twelve dossiers were regenerated from that exact anchor.
The A0X aggregate passed 246 tests; the frozen package passed 10/10. The
repository-wide suite passed 1,073 tests with one documented skip. The
no-model receipt reports zero model loads,
tokenizer constructions, sealed-target reads, CCP invocations, and remote
mutations.

| Artifact | SHA-256 |
| --- | --- |
| Material execution contract | `626c373dfc231f1f0448772a4a0483f8573b533d12cbe816348a11c83b954ed1` |
| A0 protocol | `42e252b21dd9f1d6b793be304bfe708d2d9324e8e08ffe1d1915e7f01b75f586` |
| A0 implementation | `58fc058af9db862b90bec64c6891ec960806935c29eb3dda06b9629318db7e14` |
| A0 freeze | `e32b79866466fd960b4ecc8916bab1ac098a449dac434df8afe224a9b4c68cc9` |
| A0-R1 protocol | `32d8bbfcbd76e38d51a2eff012c22e65bfe0c1eca4f6d0bf345f309777df4b52` |
| A0-R1 implementation | `989ef95e6a2e77d06c0bb3d2670c9717e744d3ce4ca3c0c228aa37e0d947018e` |
| A0-R1 freeze | `0d72f58d96455b69268f11ddbf32016c3c06dc18cb3ddfe515c5c63e216d769a` |
| No-model verification receipt | `c761ae76d77b976ea83bc83aa139da9730858a387422aff501ffad1b87217e4c` |
| A0 / SmolLM2-360M dossier | `a8e564df562ecaedf20380febdfa52cdb55910b6c3207c70c92b5c59baa44941` |
| A0 / Qwen3-0.6B-Base dossier | `ad1b8028a238be01e58d8b3bf0d0bf5b2caf5aea4057676f05d499ed7f7e443d` |
| A0 / GPT-2 dossier | `6a0fecb5ec0d1d5a0e60eea16d6b42a7b5f8646353de348d6ea07360e59d143e` |
| A0 / SmolLM2-135M dossier | `694a9df6bb86076dc06771910dfa79628b64d74225ab2f64dd7daf3b5e982378` |
| A0 / GPT-Neo-125M dossier | `aa7443c656a3929df355a2f57edbc7946c82bfb18408e6e78fb65ae8ad8b9ad0` |
| A0 / Qwen2.5-0.5B dossier | `d7265ec1f0fb8369f59d768847d3f016a164af8601f87230c2198cc45be013e8` |
| A0-R1 / SmolLM2-360M dossier | `9b2b6f3d17577e181992347b9e3a347308741ec0171bb913c2b000039bb4f89c` |
| A0-R1 / Qwen3-0.6B-Base dossier | `0c751d638c47230a6914a41f839b5bcd395f0865394871ea814ec7e69200d694` |
| A0-R1 / GPT-2 dossier | `74a32fcdd32d46df1b570b0f3c3abe14470ac2ee7e053ca8c572bc0a5eb6d88a` |
| A0-R1 / SmolLM2-135M dossier | `57621fc314a5093c53cd8eb5658137191ed7654c074fbfa9c8971e6cae784547` |
| A0-R1 / GPT-Neo-125M dossier | `6ad25612f23892cc78f809207dad8149f0f55f1896c339000ce8783de182de7d` |
| A0-R1 / Qwen2.5-0.5B dossier | `348f7385f3c2a764406a559719d190d106ea9115d24de7323e63da14de671053` |

These are approval-request artifacts only. They now bind the TDD-corrected
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

Before any scientific attempt, complete one separate exact-head Latent-TRIZ
qualification using this selected producer. Each scientific pair then needs a new
execution authorization bound to its exact dossier, live source HEAD,
qualification receipt, authorization ID, and attempt ID. No CCP heavy run,
Docker action, model/tokenizer construction, target read, publication, or retry
occurred in this correction.
