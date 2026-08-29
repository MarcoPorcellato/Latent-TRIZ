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

4. a separate repository-qualification authorization owns one exact positive
   Matrix generation, and the repository has its terminal exact-head receipt;
5. the installed CCP path and full SHA-256 match the current operator
   contract;
6. live `resource status` is `Admit`, admission is inactive, and the queue is
   empty;
7. the operator supplies a new per-pair execution authorization bound to
   exactly one dossier SHA-256, one pair, the exact qualification receipt, and
   one attempt ID; this authorization contains no Matrix generation;
8. a primary reviewer confirms the authorization chain and fixed command.

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

## Runtime-binding correction checkpoint

The earlier private runtime descriptor had an unmaterializable reciprocal hash
dependency. Descriptor-v2 removes that cycle: the operator-rooted execution
authorization binds the exact raw descriptor bytes; the descriptor refers only
to its pair-derived authorization path and byte-bound material contract; and
the local role mapping repeats the descriptor path and hash. The offline
preparer writes descriptor, authorization, and mapping only in that dependency
order and refuses every existing output path.

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

## Current checkpoint

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

The current implementation anchor is
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

These are current approval-request artifacts only. They bind the final-review
implementation anchor and do not authorize A, B, or C.

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
