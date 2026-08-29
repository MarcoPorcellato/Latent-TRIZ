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

Correction anchor: `9ce4dc1e342d68bdef0dd5f63c198270a9d6d3cd`
(tree `23ea89e42bdb1dae71bfa9d23fb858a904f82beb`).
The two freezes and twelve dossiers were regenerated from that exact anchor.
Fresh verification passed: frozen package 10/10, A0X aggregate 248 tests,
schema cross-validation 155 agreements with 19 rejected mutations, and the
repository suite 1,075 tests with one documented skip. Independent review
returned `APPROVE` with no P0--P3 findings. The package commit is the remaining
local gate. The no-model receipt reports zero model loads,
tokenizer constructions, sealed-target reads, CCP invocations, and remote
mutations.

| Artifact | SHA-256 |
| --- | --- |
| Material execution contract | `b56b860a4f4673f675035e0c76aa1b79e75b37ace9c441b2d1e36076d35c3fc8` |
| A0 protocol | `42e252b21dd9f1d6b793be304bfe708d2d9324e8e08ffe1d1915e7f01b75f586` |
| A0 implementation | `f97212eed5601caedef7979cb4d7dff2a3acdb10b05276eabd7a54891b736b88` |
| A0 freeze | `961b273074ecc0338b36c9da4643c97abd73ed62de01887b5e7f7e4c1c97a95e` |
| A0-R1 protocol | `32d8bbfcbd76e38d51a2eff012c22e65bfe0c1eca4f6d0bf345f309777df4b52` |
| A0-R1 implementation | `a86a377d24f8ccb01523fc92e9d10eaac47c10e05d3a290ae76c33bdec6e34ae` |
| A0-R1 freeze | `a028564ffd0bb39015e2e6e1fe3cecc71a04f65c99dc0b79a85f1e01d8b2cda8` |
| No-model verification receipt | `c761ae76d77b976ea83bc83aa139da9730858a387422aff501ffad1b87217e4c` |
| A0 / SmolLM2-360M dossier | `1e7a734b956b026601568412f8cff7f7c4c138b345eb0145c21754b111c0ae52` |
| A0 / Qwen3-0.6B-Base dossier | `c4cddc8e5427dab50f84e7b8570f4aef107492e288f7640961f794c7c8030cf3` |
| A0 / GPT-2 dossier | `f95dad26c6be226b92ab4144ce789576f83c7b7555b16e5914a0356e01efc000` |
| A0 / SmolLM2-135M dossier | `e21d8c6bc799d79c46bd03b77741663b6da426e8295e1a6d8eab21482f535309` |
| A0 / GPT-Neo-125M dossier | `a87955120d467e6444415d4a2b0dbb7c58ad474c093cb19c8cc0b272da559ded` |
| A0 / Qwen2.5-0.5B dossier | `5c3ad79bce2ed12e2028ee65e093e78d2082edcf3373569f9fa4b54f43ec7a04` |
| A0-R1 / SmolLM2-360M dossier | `53008523132382722af2d15c4d195c21abff6679fe0c1a302c0aa62537fd0739` |
| A0-R1 / Qwen3-0.6B-Base dossier | `b0d5a258f84236d34bdcfe531f3286bc5a030c2548d902744db1538ac1f5a5fb` |
| A0-R1 / GPT-2 dossier | `a53687473bfcfccef648d221ee3644f6eea146c48ab8ed1b1cc1d2b04e1d6c0f` |
| A0-R1 / SmolLM2-135M dossier | `a33ac97ac782acdbda18cd0aa9b97ca891dde1297524f84b2cdfd5a6696d8d71` |
| A0-R1 / GPT-Neo-125M dossier | `ca6775ff486c7e12f65b79425dec53779beeee0eb3ed05992dc8bfdd60bf733f` |
| A0-R1 / Qwen2.5-0.5B dossier | `bb623b0d987aa8f563819c34e0503e0b5d79502269c4dacfde8465f2e5c3c40e` |

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
