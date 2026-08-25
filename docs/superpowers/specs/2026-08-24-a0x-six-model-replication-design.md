---
type: architectural-design
title: A0X six-model immutable replication family
status: approved-design-awaiting-implementation-plan
base_anchor: 188eb65b5e249923baddadeba52659f07fcd1609
---

# A0X six-model immutable replication family

## Decision and scope

Create a new, namespaced **A0X** family with two separately frozen legs:

- **A0X-A0** reproduces the A0 automated weak-proxy contract on six exact
  non-Pythia models.
- **A0X-R1** independently reproduces the A0-R1 pre-output contract on the
  same six exact non-Pythia models.

The unit of authorization, execution, analysis, publication, and interpretation
is one `(leg, exact-model-revision)` pair. There are therefore exactly **12
independent one-shot material runs**. No authorization spans two pairs, no
result is pooled across pairs, and no run is a substitute, retry, recovery, or
amendment of A0, A0-R1, A0-R2/C1/C2/C3, EXP-001, or EXP-002-AUTO.

This document is a design only. It authorizes no model load, tokenizer
construction, sealed-target read, CCP invocation, model acquisition, or
scientific conclusion.

## Verified anchors and preservation rule

All implementation work starts by re-verifying that `origin/main` resolves to
`188eb65b5e249923baddadeba52659f07fcd1609`. That anchor was verified locally
while this design was written; it must be reverified immediately before a
freeze, approval, or material action. A changed anchor stops the action and
requires a newly reviewed A0X freeze rather than a repair after access.

At design time, the checkout also contains preserved untracked R5 recovery
directories and `tmp/`. They are outside A0X and outside this design commit.
No A0X exact-head or clean-checkout claim may be made until those paths are
preserved elsewhere or the A0X action runs from a separately verified clean
checkout; ignoring them in Git is not evidence of cleanliness.

The original A0 and A0-R1 tracked inputs and published packages are immutable
inputs, never writable outputs. The table below records bootstrap roots; it is
not the complete preservation manifest:

| protected input | verified file SHA-256 | immutable evidence retained |
| --- | --- | --- |
| `experiments/a0-automated-weak-proxy/protocol.json` | `36d52643d419fd4e8feada63d19a42429940f3559dda72adf342c484411fc244` | original A0 protocol bytes |
| `experiments/a0-automated-weak-proxy/implementation.json` | `2d08085d8cfc566f62b1b414c6ca09ad23af8df67de0fbd6876a896783721df9` | original A0 implementation bytes |
| `data/a0/manifest.json` | `68eda0c1082b36b17836cb79684c5696280486ae93596109562853160f25d58f` | original A0 corpus bindings |
| `results/a0/calibration/freeze-manifest.json` | `a15e83c65573f50153f8608c9536e3bc4c60a1505fd939ec98ec97013a9407e1` | original A0 analysis freeze |
| `results/a0/a0-v1.0.3-e93a9faa/activation-receipt.json` | `e539d3bcaa63f130c96f9cfebb4b5d02aedeec989212fa0708b7ccafa115615d` | original A0 activation identity |
| `results/a0/a0-v1.0.3-e93a9faa/statistical-result.json` | `f03a8de0533cce6a1a99cde647512da1d3bec2bde526518facb5bb9b52e938a3` | original A0 statistical result |
| `results/a0/a0-v1.0.3-e93a9faa/publication-manifest.json` | `b5e97b71ffc24e9e3eb23d86be3e5d75f38cd93ac5dc3f98c523f5e8320d21c2` | original A0 package bindings |
| `data/a0/cases.jsonl` | `4d667a5b8e7512ee19feeedc37e2562413ace27fdd1220654ef79edcb8616707` | original A0 public case bytes |
| `data/a0/procedural-targets/calibration-targets.jsonl` | `1607a329e83ee77d010a9e839c10a6c5f073b0550256d0305fb5d49af0c26acd` | original A0 calibration target bytes |
| `data/a0/sealed-targets/targets.jsonl` | `8b820294103ce748f65b49aa46e2e85ce584add8c058bb2d4129aadf366e7162` | original A0 sealed-target commitment; byte verification occurs only during authorized analysis |
| `results/a0/a0-v1.0.3-e93a9faa/representations-index.jsonl` | `cfc53198eda44738b3c468ffb5581c659c025e8c3ebdd7ba57fe27198a60c089` | original A0 representation index |
| `results/a0/a0-v1.0.3-e93a9faa/report.html` | `8705cc1844ad7b988d4e59108d8c03dbad9c541627090a7eeed734009802a804` | original A0 report |
| `experiments/a0r1-independent-proxy/protocol.json` | `ed113d1c0bfdb44b57c879e2995b610d0ecf528fccedb37fc9b89093be083fbf` | original A0-R1 protocol bytes |
| `experiments/a0r1-independent-proxy/implementation.json` | `9fa6a8192546073257670aecdc88ea3840cfbab9dc0c49368fcc131f184c563c` | original A0-R1 implementation bytes |
| `data/a0r1/manifest.json` | `46c5cdf796f2abad709deb3066cfadd5fc6e6a30f55a737b3408e0a15b065c06` | original A0-R1 corpus bindings |
| `results/a0r1/freeze/freeze-manifest.json` | `bedb9df1d6650ab0d4d7f9a255555e4dbe80b07b705b45534eeb290d76fe5fc9` | original A0-R1 analysis freeze |
| `results/a0r1/a0r1-v1.0.0-e93a9faa-r1/activation-receipt.json` | `8d46e42fcb97511f913e188e098a103e29c811bb3fca6c469be5de4a72899d5f` | original A0-R1 activation identity |
| `results/a0r1/a0r1-v1.0.0-e93a9faa-r1/statistical-result.json` | `a2ad1ed0148a332fe85cb42ee2f3295e042d277d772353ebd84ccd2e255a6738` | original A0-R1 statistical result |
| `results/a0r1/a0r1-v1.0.0-e93a9faa-r1/publication-manifest.json` | `dada7b79fe08cf58407bda80c5e48e02fd862f7d2573de9984d9736b14936c91` | original A0-R1 package bindings |
| `data/a0r1/cases.jsonl` | `479caee11dd62a978e8f01e9802db624b1714909264292b53067e97e10002541` | original A0-R1 public case bytes |
| `data/a0r1/targets/calibration.jsonl` | `b8cae1ba5355c6d72d74030e3c1487dcd43dbe50431d9ce071ca386b81df0f19` | original A0-R1 calibration target bytes |
| `data/a0r1/targets/sealed.jsonl` | `e911a70279f5b141c35064da29c020557f69ee17dfed5adad6172ed3fe2db0e0` | original A0-R1 sealed-target commitment; byte verification occurs only during authorized analysis |
| `results/a0r1/a0r1-v1.0.0-e93a9faa-r1/representations-index.jsonl` | `0f78f5ca680957be04f430ced0ca7da3267251c5e544a3cd301b53eb7161657f` | original A0-R1 representation index |
| `results/a0r1/a0r1-v1.0.0-e93a9faa-r1/report.md` | `1f5017cd7729715ff33b13271262346a74dcae2a2fb2b0c8bf0a590c3b3e8e08` | original A0-R1 report |
| external A0-R1 dense asset | `c49436ed505cbaea677a4f68e597714ef0dd75119a0640474ac1372fae1d2c20` | original 944,964-byte external dense locator binding |

Each A0X artifact path is new and namespaced beneath
`experiments/a0x-six-model/`, `results/a0x/`, `src/latent_triz/a0x_*.py`, and
`tests/test_a0x_*.py`. Two canonical exhaustive manifests,
`experiments/a0x-six-model/protected-a0-tree.json` and
`experiments/a0x-six-model/protected-a0r1-tree.json`, must enumerate every
tracked file under each source experiment, corpus, calibration/freeze, and
published result package plus every publication-manifest external asset. Each
entry binds path, byte count, SHA-256, provenance manifest, and verification
phase. Verifiers hash every non-target entry before and after material action.
For sealed-target entries, preflight compares only the already frozen digest
declaration; the authorized analysis hashes and parses the bytes in the same
single read. A0X may refer to hashes and frozen semantic fields, but must not
copy an old run directory, append to it, or rewrite its manifests.

## Exact model identity cards

The only allowed A0X models are the six non-Pythia entries in
[`experiments/exp002-auto/model-registry.json`](../../../experiments/exp002-auto/model-registry.json),
whose verified SHA-256 is
`31176187a9ebb14a80d19a0f99868f2bc91672174f3b1d7ee5ca260074965b58`.
The A0X freeze copies these literals, not an alias, latest tag, or inferred
revision.

| A0X key | exact model card and revision | local runtime root | architecture identity that preflight must verify |
| --- | --- | --- | --- |
| `smollm2_360m` | [`HuggingFaceTB/SmolLM2-360M`](https://huggingface.co/HuggingFaceTB/SmolLM2-360M) @ `f8027fd0eaeea54caa13c31d31b9fdc459c38b49` | `artifacts/models/smollm2-360m-f8027fd0` | `llama`, `LlamaForCausalLM`, 32 blocks, width 960; bind tokenizer independently |
| `qwen3_0_6b_base` | [`Qwen/Qwen3-0.6B-Base`](https://huggingface.co/Qwen/Qwen3-0.6B-Base) @ `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` | `artifacts/models/qwen3-0.6b-base-da87bfb` | `qwen3`, `Qwen3ForCausalLM`, 28 blocks, width 1024 |
| `gpt2` | [`openai-community/gpt2`](https://huggingface.co/openai-community/gpt2) @ `607a30d783dfa663caf39e06633721c8d4cfcd7e` | `artifacts/models/gpt2-607a30d7` | `gpt2`, `GPT2LMHeadModel`, 12 blocks, width 768; expected runtime tokenizer `GPT2TokenizerFast`, `is_fast=true`, offset mappings required |
| `smollm2_135m` | [`HuggingFaceTB/SmolLM2-135M`](https://huggingface.co/HuggingFaceTB/SmolLM2-135M) @ `93efa2f097d58c2a74874c7e644dbc9b0cee75a2` | `artifacts/models/smollm2-135m-93efa2f0` | `llama`, `LlamaForCausalLM`, 30 blocks, width 576; exact tokenizer metadata is `GPT2Tokenizer` |
| `gpt_neo_125m` | [`EleutherAI/gpt-neo-125m`](https://huggingface.co/EleutherAI/gpt-neo-125m) @ `21def0189f5705e2521767faed922f1f15e7d7db` | `artifacts/models/gpt-neo-125m-21def018` | `gpt_neo`, `GPTNeoForCausalLM`, 12 blocks, width 768 |
| `qwen2_5_0_5b` | [`Qwen/Qwen2.5-0.5B`](https://huggingface.co/Qwen/Qwen2.5-0.5B) @ `060db6499f32faf8b98477b0a26969ef7d8b9987` | `artifacts/models/qwen2.5-0.5b-060db649` | `qwen2`, `Qwen2ForCausalLM`, 24 blocks, width 896; effective context is 32,768, not the tokenizer advertisement |

For every card, its A0X identity receipt must bind the model ID, 40-character
revision, exact local root, allowlisted filenames, bytes, SHA-256 values,
license field, `model_type`, `architectures`, number of transformer blocks,
hidden width, vocabulary, tokenizer class, fast-offset support, effective
context, pad side if padding is used, and `trust_remote_code=false`. The
architecture cannot stand in for tokenizer identity; the SmolLM2-135M
exception is an explicit regression case. A missing, non-fast, mismatched, or
unallowlisted card is terminal `incompatible` before model construction.

GPT-2's expected `GPT2TokenizerFast` class is frozen from the pinned
Transformers AutoTokenizer mapping for `model_type=gpt2`, together with the
presence of the exact `tokenizer.json`; it is not inferred from the snapshot's
absent `tokenizer_class` field. Material preflight constructs the tokenizer
before weights, requires the exact runtime type, `is_fast=true`, and non-empty
offset mappings on the fixed synthetic probe, and stops `incompatible` before
model construction if any check differs.

The card rows are corroborated by
[`docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md`](../../EXP001_ADDITIONAL_MODEL_RUNTIME.md),
[`docs/EXP001_MODEL_OFFICIAL_DOC_AUDIT.md`](../../EXP001_MODEL_OFFICIAL_DOC_AUDIT.md),
and [`docs/EXP001_QWEN3_OUTLIER_ANALYSIS.md`](../../EXP001_QWEN3_OUTLIER_ANALYSIS.md).
Those historical records establish metadata safeguards; they do not authorize
reuse of their executions, outputs, approvals, or target reads.

## Frozen analysis contract

The primary endpoints retain literal frozen indices even when a model has more
than six blocks:

| leg | primary literal endpoint | primary decision rule | architecture-aware sensitivity |
| --- | --- | --- | --- |
| A0X-A0 | `problem_plus_transformation` at hidden-state tuple indices `0`, `2`, `4`, and `6`, with applicable sites `sentinel`, `final_transformation_token`, and `mean_transformation_span` | inherited family-blocked max-statistic analysis with multiplicity 12, 199 permutations, and A0 positive threshold `max_statistic_p <= 0.05` plus macro-F1 margin over surface `>= 0.10`; `problem_only/sentinel` is the surface baseline | `transformation_only`, `problem_plus_solution`, and one final-transformer-block output by applicable view/site are descriptive only |
| A0X-R1 | literal hidden-state tuple index `6`, `problem_plus_transformation`, `mean_transformation_span`, with `problem_only` surface baseline at `sentinel` | inherited single primary: 999 paired within-family permutations, `p <= 0.05`, macro-F1 margin `>= 0.10`, at least 17 family successes, and at least four positive domain directions | the same primary view/site and problem-only baseline at the validated exact-config final-transformer-block output; descriptive only |

Tuple indexing includes the embedding entry at index zero. The implementation
must expose and test that convention explicitly. The architecture-aware block
is `num_hidden_layers` under that convention, never `num_hidden_layers - 1`, a
fraction of depth, or a post-result selected layer. A missing literal index or
final-block identity is terminal `incompatible`; a descriptive sensitivity
never changes the primary p-value, thresholds, status, or interpretation and
cannot rescue a failed, null, or non-interpretable primary.

All inherited corpus, split, control, threshold, and outcome fields are copied
into separate A0X freeze documents by value. Each leg preserves the source
leg's exact frozen rules from
`experiments/a0-automated-weak-proxy/protocol.json` and
`experiments/a0r1-independent-proxy/protocol.json`, while using a new A0X
protocol ID, corpus manifest, implementation manifest, model identity receipt,
and run ID. Results are model-separated and leg-separated. No meta-analysis,
average, vote, combined p-value, ranking, or cross-model selection is emitted.

A0X-A0 intentionally strengthens the historical A0 access boundary. Before
freeze, `experiments/a0x-six-model/a0-selection-manifest.json` records the
ordered 48 selected sealed case IDs, partitions, domains, family IDs,
case-content hashes, the lexicographic frozen selection rule, and the source
case/corpus-manifest hashes. It contains no target label or target value and is
derived only from public case bytes. Activation consumes this exact selection
manifest and never opens the historical target file. Analysis opens the target
file once, verifies its frozen digest while parsing, and checks that its IDs
match the frozen selection. This access-boundary strengthening is why A0X-A0
is a new cross-model extension rather than a byte-identical rerun of A0.

## Execution, access, and resource boundary

Every material pair has a unique immutable dossier, domain-separated
authorization commitment chain, CCP receipt, run ID, output directory, and
publication manifest. A single
authorization grants exactly one selected A0X leg and one exact model revision;
it expires if any bound hash, card fact, resource observation, output-destination
emptiness check, or source anchor drifts.

`PairBinding` contains only the stable one-run scope under the exact profile
`a0x-pair-scope-v2`: leg and freeze, model identity and revision, run ID,
output path, and complete dense bound. It never contains a dossier or
authorization self-hash. Approval lineage is instead an acyclic chain. A
shared `a0x-material-execution-contract-v1` first binds the stable repository
identity and exact CCP producer identity; one Matrix-V2 repository
qualification config and policy with their raw hashes, expected outer/runtime
plan digests, and canonical receipt contract. That same Matrix configuration
owns `plan`, `doctor`, reviewed `dry-run`, and the separately authorized
qualification `run`; `doctor` and `dry-run` must return a complete two-runtime
Matrix envelope whose nested V1 runtime objects are validated individually. It
also binds the offline runtime prohibitions, command order,
qualification/run limits, and fixed stop-boundary vocabulary without binding a
mutable source HEAD or granting permission. A declared configuration digest is
never substituted for a live observed plan digest. Each Task-11 dossier
binds that contract by repository-relative path and raw SHA-256 and names the
future authorization path, while remaining `approval_requested`. The complete
validated dossier is canonically committed as `D` with the profile
`a0x-approval-dossier-json-v2`. Repository qualification is separately
authorized for one exact source HEAD and one positive operator-selected CCP
generation and produces one canonical Matrix-V2 receipt. A later per-pair
execution authorization contains `D`, the complete selected source HEAD, the
exact qualifying receipt raw SHA-256, authorization/attempt IDs, exact CCP
identity, exact `guard exec` argv commitment, one-guard limit, and stop
boundary. It contains no CCP generation because `guard exec` has no generation
argument. The complete validated per-pair authorization is canonically committed as `A` with the profile
`a0x-execution-authorization-json-v2`. Every post-authorization
artifact carries the identical pair binding and `(D, A)` authorization chain.
The two commitments use strict UTF-8 JSON with duplicate-key and floating-point
rejection, repository-defined sorted-key serialization, and distinct
domain-separation prefixes. Neither source document embeds its own commitment.
The publication manifest additionally binds their raw byte hashes so a
semantically equivalent byte rewrite is still detected.

The only permitted material runtime is offline CPU `float32` with
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `local_files_only=True`,
`trust_remote_code=False`, `model.eval()`, and teacher-forced forward calls.
Network use, generation, `generate`, chat templates, fallbacks, quantisation,
automatic device selection, batching changes, model substitution, tuning, and
retry are prohibited. The runner must never offer a fallback model or retry a
partially completed attempt.

Each leg has a separate dense-output cap per model run:

| leg | maximum wall time | maximum peak RSS | maximum new dense/index bytes |
| --- | ---: | ---: | ---: |
| A0X-A0 | 1,800 seconds | 8,589,934,592 bytes | 33,554,432 bytes (32 MiB) |
| A0X-R1 | 1,800 seconds | 8,589,934,592 bytes | 4,194,304 bytes (4 MiB) |

The cap includes every newly produced dense activation, representation index,
temporary output that survives a crash, and publication payload; crossing it
is terminal `incompatible`. A larger outer CCP or operator resource envelope
does not relax these internal caps. These are A0X caps, not amendments to the
original A0 or A0-R1 assets. Before freeze, the no-model verifier must compute
the worst-case byte bound across every persisted
`(case, view, site, layer-endpoint)` vector. At maximum hidden width 1024,
A0X-A0 binds `48 × 10 × 5 × 1024 × 4 = 9,830,400` dense bytes: four literal
endpoints plus the final-block descriptive endpoint. Its freeze reserves two
dense copies for atomic/crash-safe writing (`19,660,800` bytes), two index
copies totalling at most `6,291,456` bytes, and `2,097,152` bytes for headers,
receipts, report, manifest, and other publication payload: at most
`28,049,408` bytes under the 32-MiB cap. A0X-R1 binds
`48 × 2 × 2 × 1024 × 4 = 786,432` dense bytes: primary/baseline at the literal
and final-block endpoints. Its freeze reserves two dense copies (`1,572,864`
bytes), two index copies totalling at most `1,048,576` bytes, and `524,288`
payload bytes: at most `3,145,728` bytes under the 4-MiB cap. The verifier
rejects any component or aggregate bound that exceeds its reservation before
model construction.

Preflight is no-load and no-target. It verifies the origin anchor, all frozen
hashes, model-card allowlist and config, offline variables, empty new output
path, literal and final-block index availability, file permissions, and a CCP
observation of `resource.decision=admit`, `admission.active=false`, and
`admission.queue_count=0`. Unknown, stale binary, deny, active, queued,
unreadable, or inconclusive observations fail closed.

The exact CCP qualification trace is fail-closed and ordered:
`admission status --json`, `resource status --json`, Matrix-V2 `plan --json`,
V1 `doctor --json`, reviewed V1 `dry-run --json`, then at most one separately
authorized Matrix-V2 `run --generation <authorized-u64> --json`. The runner
hashes the exact executable immediately before every command and requires the
observed digest to equal the shared material contract and the applicable
qualification authorization. The run qualifies the exact repository HEAD; it
does not execute or qualify a scientific pair. Its immutable observation uses
the authentic Matrix plan and canonical receipt envelopes and binds the exact
numeric generation.

Each separately authorized scientific pair repeats the read-only preflight,
revalidates the dossier, per-pair authorization, source HEAD, both config
families, policy bytes, qualifying receipt, executable, and empty output, then
exclusively creates and fsyncs an `a0x-attempt-claim`. The claim is never
deleted or reused. Exactly one CCP `guard exec` owns exactly one frozen child
program and argv for that pair; no local model path is available outside that
guard and no public unguarded runner exists. The immutable pre-guard observation
is hashed into the child preflight receipt; the final pair observation binds
that hash, the exact guard argv commitment, child exit, and terminal package
links. It is not described as a CCP run receipt. Any concurrent claim, crash,
interruption, ambiguous output, live lease, binary or policy drift, failed
doctor, rejected dry-run, nonzero qualification command, guard failure, or
child failure consumes or refuses the applicable attempt without permitting a
retry. Matrix `run` and `guard exec` are never nested because admission is
non-reentrant.

Cooperative child exceptions that reach the lifecycle boundary are sealed into
the first terminal package. Abrupt outer timeout, cancellation, process kill,
or cleanup uncertainty cannot truthfully guarantee that Python completed a
package: in that case the already-fsynced immutable attempt claim plus the
terminal `guard exec` classification is the durable consumed-attempt and
recovery evidence. It must not be promoted to a scientific result or described
as a CCP receipt, and it never authorizes a retry. The pre-guard observation
accepted by the child has one strict shared schema/validator shape. The final
pair observation recursively binds that exact observation by SHA-256 and a
non-recursive closed schema, plus the guard argv commitment, child/guard exit
classification, and any terminal package links.

Activation receives only public inputs and an activation capability that cannot
open target bytes. Its receipt must record `activation_target_content_reads: 0`.
Only analysis receives a one-shot target-reader capability, created after the
activation receipt is sealed. A valid analysis opens the exact frozen target
once, records `analysis_target_content_reads: 1`, then irrevocably closes. A
terminal failure before analysis records `analysis_target_content_reads: 0`
and must not contain a statistical result. For a claimed valid analysis, the
verifier rejects `0`, `2+`, absent counter receipts, target access by
activation, and any target hash mismatch. A model or target possibly accessed
in any terminal attempt consumes that pair's authorization; a later attempt
needs a new, separately reviewed explicit approval.

The first terminal package is always published: `positive`, `null`,
`non_interpretable`, `incompatible`, or `failed`. A package includes its
pair binding, authorization commitment chain, access counters,
identity/integrity/environment/CCP
receipts, resource measurements, activation/index/dense hashes when created,
statistical result only when valid, report, limitations, and manifest. A
failure before activation publishes no fabricated activation or score asset;
a failure after possible access remains terminal and is not recoverable under
the same approval.

Each terminal package uses the acyclic integrity profile
`a0x-terminal-package-v1`. Exact artifact, external-output, source-input, and
retained-residue bytes flow into `publication-manifest.json`; that manifest
never hashes itself. The complete-attempt root receipt
`output-occupancy-receipt.json` binds the manifest's exact raw bytes under
`a0x-complete-attempt-root-v2`, records complete occupancy and peak checkpoint
arithmetic, and excludes only its own not-yet-known byte length. The verifier
adds the exact serialized root-receipt length when enforcing the cap. The root
receipt contains no self-hash and no self-dependent total.

Before remote publication, verification requires the expected raw SHA-256 of
that root receipt as an external local anchor. After publication, the exact Git
tree and commit bind the root bytes; the exact-head CCP receipt and merged
commit become the durable public anchor. Internal agreement alone is never
sufficient: an unanchored package fails closed. Every regular package file must
be declared, every external dense/index/source/residue file must be raw-hashed,
and symlinks, hardlinks, path escapes, devices, FIFOs, duplicate roles/paths,
unknown members, and empty undeclared directories are rejected.

The terminal result records `sealed_from_state` (`preflight`, `activation`, or
`analysis`) so the verifier can enforce the five-status artifact matrix without
inferring lifecycle from missing files. Completed dense and index outputs appear
together through a strict external-assets locator; partial outputs are residue,
never evidence. The package manifest declares the root-receipt path and profile
but does not ledger its bytes, preventing a manifest/root hash cycle.

Path namespaces are exact. `package_artifacts[*].path` is normalized POSIX and
relative to the terminal package root. `external_outputs`, `source_inputs`, and
`retained_residue` use normalized repository-root-relative paths. The
`authorization_record` package role is an exact byte-for-byte copy of the
execution authorization and validates against
`a0x-execution-authorization.schema.json`; its ledger digest must equal the
`execution_authorization` source-input digest. The root field
`activation_receipt_raw_sha256` means the exact raw hash of
`activation-receipt.json`, never the nested activation-stage occupancy object.

The semantic verifier, not schema omission inference, enforces this literal
role matrix (`R` required, `F` forbidden, `O` optional, `C` conditional as one
inseparable completed-activation set):

| manifest/output role | preflight `failed|incompatible` | activation `failed|incompatible` | analysis `positive|null` | analysis `non_interpretable` | analysis `failed|incompatible` |
| --- | --- | --- | --- | --- | --- |
| `authorization_record` | R | R | R | R | R |
| `model_identity_receipt` | F | R | R | R | R |
| `ccp_observation` | O | R | R | R | R |
| `preflight_receipt` | F | R | R | R | R |
| `activation_receipt` | F | C | R | R | R |
| `target_read_receipt` | F | F | R | R | R |
| `statistical_result` | F | F | R | F | F |
| `terminal_result` | R | R | R | R | R |
| `external_assets_locator` | F | C | R | R | R |
| `report` | R | R | R | R | R |
| external `activation_dense` + `representation_index` | F | C | R | R | R |
| `retained_residue` | O | O | F | F | O |

For the activation frontier, the three `C` entries are either all present or
all absent. An activation receipt always means completed activation; partial
activation produces residue only and never an incomplete activation receipt.
Every manifest has exactly the two required source inputs: approval dossier and
execution authorization. Manifest and root receipt are always present outside
the ordinary package ledger.

Complete-attempt arithmetic excludes pre-existing `source_inputs` and counts
each physical output/residue path once. `component_bytes.package_artifacts` is
the package ledger sum, `component_bytes.manifest` is the exact manifest length,
`external_outputs` is the dense/index sum, and `retained_residue` is its ledger
sum. Their sum equals `final_bytes_excluding_this_receipt`.
`cap_bytes` equals `PairBinding.dense_bound.cap_bytes`;
`peak_bytes_before_this_receipt` is the maximum runtime checkpoint total and is
at least the final value. The final verifier computes
`final_bytes_excluding_this_receipt + len(exact root receipt bytes)` and rejects
when that value or the recorded peak exceeds the cap. Runtime checkpoints must
include unique `pre_manifest_write` and `pre_root_receipt_write` phases.

`Incompatible` is an A0X pre-statistical terminal class for a card, tokenizer,
architecture, context, or resource contract that cannot execute the frozen
leg. It is neither a scientific `null` nor permission to substitute a model.

## Separation from EXP-002-AUTO R5

EXP-002-AUTO's `AUTO-5` permutation work is an R5 response-surface diagnostic,
not an A0X leg. A0X uses neither its schedule, model-output paths, target-key
template, approval dossier, execution modules, shards, statistics, result
packages, nor terminal statuses. Conversely, EXP-002-AUTO/R5 must not import
or publish an A0X result. The only shared reference permitted is the immutable
six-model identity list in `experiments/exp002-auto/model-registry.json`; A0X
copies that list and its registry hash into its own freeze manifest.

This separation prevents R5 response-surface work from becoming a hidden
sensitivity, target source, retry route, or statistical rescue for either A0X
leg. A0X remains exploratory, `expert_validated: false`,
`evidence_eligible: false`, with empty `claim_ids`. It makes no general TRIZ,
invention, emergence, training-data, or latent-rediscovery claim.

## Implementation shape and TDD gates

Implementation is intentionally narrow and additive:

| responsibility | planned namespace |
| --- | --- |
| freeze/card/authorization schemas and hash checks | `experiments/a0x-six-model/`, `schemas/a0x-*.schema.json` |
| immutable input and model-card verifier | `src/latent_triz/a0x_freeze.py`, `src/latent_triz/a0x_preflight.py` |
| leg-specific extraction and fixed-index mapping | `src/latent_triz/a0x_a0_activations.py`, `src/latent_triz/a0x_r1_activations.py` |
| one-shot activation/analysis capability boundary | `src/latent_triz/a0x_execution.py`, `src/latent_triz/a0x_runner.py` |
| fixed-primary plus descriptive final-block analysis | `src/latent_triz/a0x_a0_analysis.py`, `src/latent_triz/a0x_r1_analysis.py` |
| terminal package/report/verification | `src/latent_triz/a0x_report.py`, `src/latent_triz/a0x_verify.py` |
| shared CCP/runtime material contract | `schemas/a0x-material-execution-contract.schema.json` |
| durable exclusive attempt reservation | `schemas/a0x-attempt-claim.schema.json` |
| focused synthetic tests | `tests/test_a0x_*.py` |

Tests are written before each implementation unit and begin with synthetic
adapters and synthetic sealed readers only. Required failing-first coverage
includes all six exact cards; revision/root/allowlist/hash drift; tokenizer
versus architecture mismatch; literal tuple-index convention; final-block
mapping; primary immutability under a favourable sensitivity; activation zero
target reads; analysis exactly one read; second-read refusal; forbidden network,
generation, fallback, and retry; per-leg cap overflow; original A0/A0-R1 byte
mutation detection; empty-output enforcement; all terminal package shapes; and
cross-leg/cross-model pooling rejection. Material tests are never replaced by
mocked pass-through tests to conceal a product defect.

Synthetic and repository verification validates protected-tree schemas,
internal tree commitments and provenance declarations but must never open the
two calibration-target files or the two sealed-target files. Full byte-level
protected-tree verification is reserved for an explicitly authorized material
boundary. Tests instrument all four paths and require zero content opens.

Luna-safe preparatory work is limited to no-model, no-target, no-CCP commands
such as a focused `pytest tests/test_a0x_preflight.py -q`,
`pytest tests/test_a0x_execution.py -q`, schema validation, manifest hashing,
`make a0x-no-model-verify`, `make docs-audit`, and `git diff --check`.
After the exact repository HEAD has one authorized canonical Matrix-V2
qualification receipt, the operator explicitly authorizes one exact dossier,
and a primary reviewer confirms the live CCP gate, Luna may invoke only that
dossier's argument-free material command and capture its first terminal
receipt. Luna
must not choose or alter a model, leg, path, endpoint, limit, target, CCP
decision, retry policy, interpretation, publication state, or merge decision.
Authorization recording, exception handling, scientific interpretation,
publication, and merge remain with the operator and primary reviewer.

## Milestones and release checklist

### Current implementation checkpoint — 2026-08-24

- Tasks 1-9 are locally committed through
  `34bbb38728c841c86128a2967ae18df9aea177cc`; Task 9 has fresh 21-test package
  verification, 57-test compatibility verification with three expected NumPy
  skips, and an independent Sol approval.
- Task 10 has a saved but unqualified local implementation checkpoint. Resume
  from `docs/A0X_RESTART_HANDOFF.md`; run the configured schema and synthetic
  gates, then obtain independent review before integration.
- Task 11 has materialized two frozen no-model legs and all twelve separate
  `approval_requested` dossiers. The focused and complete A0X gates pass;
  independent architecture/science review and the final exact-hash ledger
  remain pending before the Task-12 stop boundary.
- Task 12 remains outside the current authorization. This checkpoint grants no
  model, tokenizer, target, CCP, material-run, network, or publication access.

1. **Freeze:** add A0X schemas and per-leg/model manifests; prove all six
   literal cards and the protected A0/A0-R1 hashes; pass no-model verifier.
2. **Synthetic qualification:** add failing-first tests and minimal namespaced
   code; verify all access counters, resource refusals, endpoint mapping,
   terminal shapes, and non-pooling guards without reading a model or target.
3. **Reviewable approval package:** produce 12 separate dossiers, each binding
   one leg/model, exact code/input/card hashes, the leg-specific 32-MiB or
   4-MiB cap, output path,
   no-retry rule, and target capability semantics; obtain no material approval
   merely by merging this design or the implementation.
4. **Per-pair execution:** immediately before each selected pair, reverify
   `origin/main`, frozen inputs, empty output destination, and CCP admission;
   obtain that pair's explicit approval; execute once; seal the first terminal
   outcome; run only no-load/no-target verification afterwards.
5. **Publication verification:** fresh-clone verification checks every package
   independently, rejects a missing or mutated external dense asset, rejects
   pooling, verifies original A0/A0-R1 hashes, and confirms no R5 artifact is
   an A0X dependency.

Completion means 12 independently verifiable terminal packages or their
separately published fail-closed terminal outcomes. It never means that a
favourable subset, descriptive final-block sensitivity, or R5 result can
replace an unexecuted or failed primary pair.
