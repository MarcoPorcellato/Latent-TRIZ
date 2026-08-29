---
type: chronology
title: Laboratory chronology
description: Event-by-event record of the Latent-TRIZ laboratory.
status: canonical
last_verified: 2026-08-29
---

## 2026-08-29 — A0X Matrix V2 policy bootstrap

- **Problem:** PR #105 was qualified locally with the explicit
  `matrix-v2-legacy-v1` plan, but public `main` still accepts the preceding
  legacy-plan digests. The hosted verifier correctly reads the policy from the
  pull request base, so the candidate policy cannot authorize its own updated
  legacy-profile receipt.
- **Solution:** prepare a separate policy-only prerequisite from exact public
  `main` `188eb65b5e249923baddadeba52659f07fcd1609`. It changes only the outer,
  Python 3.11, and Python 3.12 accepted configuration digests; checks, images,
  platforms, and the one-hour freshness limit remain unchanged.
- **Trust bootstrap:** qualify the prerequisite itself with
  `matrix-v2-legacy-v1`, using the preceding plan digests still accepted by its
  trusted base. Only after the prerequisite is public may A0X be rebased and
  qualified with the updated `matrix-v2-legacy-v1` plan.
- **Gate:** the exact qualification dossier is
  [`qualification/a0x-legacy-policy-migration-dossier.json`](qualification/a0x-legacy-policy-migration-dossier.json).
  It remains `approval_requested`; no CCP run, Docker workload, remote
  mutation, model access, target access, or scientific retry is authorized by
  this preparation.
- **Negative qualification evidence:** the first prerequisite candidate at
  `a281dc72e1dcd1c8a323a0d3fa172a1b6e2858fe` ended `FAIL`. Receipt integrity
  passed; both schema checks passed; both repository checks exited 1 without
  timeout or cancellation. Receipt ID
  `sha256:5577fdbd42aae9f490e01f5b6281810fd773633e0eef03556e3749f19d2c4794`;
  receipt-file SHA-256
  `ddc037e1c354b4acc333b2cdc782d9a21d4021c6ce2c8a8d5d20aeab1c1e0064`.
- **Profile root cause:** the selected `current-v2` plan produced
  `25b35b94… / b3d8beef… / d446c4ca…`, which the historical trusted base does
  not accept. CCP's official Matrix compatibility contract requires the
  explicit `matrix-v2-legacy-v1` profile; on the same source configuration it
  reproduces exactly `13f4cb39… / eff5b7d5… / 7afb3e6d…`, the three digests
  accepted by the base policy. The corrected dossier now requires direct
  equality between the selected-plan and trusted-base digest maps.
- **Source-snapshot root cause:** the repository suite called the full EXP-002
  publication verifier on seven intentionally Git-ignored dense assets. A CCP
  source snapshot contains only committed blobs, so the test was not
  self-contained. The full verifier remains fail-closed and continues to read
  and hash every external asset. A separate `bindings_only` API now validates
  the tracked schema, package bindings, and safe asset declarations without
  claiming that external assets were verified; synthetic tests retain missing
  and mutated asset rejection coverage for the full verifier.

---

## 2026-08-20 — EXP-002 no-model checkpoint

- Completed and published the EXP-002 no-model implementation on branch
  `exp002-qwen3-followup`. The direct-question path is now stage-aware and
  keeps bounded generation disabled by default; EXP-002C has a label-free
  candidate-description scorer that emits four candidate scores without
  label-token scores.
- Added stage-specific response-index validation and a separate EXP-002C
  transfer-target-key schema/template. The public template remains
  `not_ready`, with no sealed answers or target-content hash until the
  independently authored corpus and expert labels are frozen.
- Refreshed the canonical plan, status, roadmap, master plan, persistent goal,
  and restart handoff to implementation checkpoint `e47937c`; subsequent
  documentation-only commits preserve that code checkpoint. The branch is
  publicly synchronized at the preceding checkpoint
  `ef030107f31a6ab436c91409479424703f34599e`.
- Deterministic validation remains model-free: 50 EXP-002 tests, 146 schema
  pairs, the contract/question-bank audit, and the full repository suite pass.
  Fresh EXP-002B/C preflight returns `approval_required` without model or
  sealed-target access because independent expert packets and the EXP-002C
  corpus/target key are still absent.
- Added the `make exp002-stage-preflight` convenience target so both material
  dossiers can be checked together before any CCP or model capability is
  consulted.
- Added `make exp002-review-packet-verify PACKET=...`, a single-packet audit
  that checks all 351 IDs, rationale hashes, answer presence, and the
  no-model/no-target boundary before a reviewer submits their packet.
- Added the EXP-002C transfer-corpus author quickstart, documenting the
  eight-domain minimum, independent source/proximity audit, required controls,
  and the rule that the sealed target key stays `not_ready` until review.

---

## 2026-08-20

- Advanced the published EXP-002 no-model tranche through exact head `278dcf2`:
  added the three-pseudonymous-reviewer answer-key gate, direct-question
  abstention/precision/recall metrics, and a target-free EXP-002C corpus schema
  and validator. The validator rejects EXP-001 reuse, TRIZ/source leakage in
  the blinded primary, duplicate fingerprints, and shared expert/generator
  locators. All changes remain model-free and claim-free.
- Refreshed the CCP coordination reference to current `origin/main`
  `5f2ef665be4dc47fd354befcba53251a4e51744f`; the runbook forbids manual lock
  or lease quarantine and requires fresh host-wide admission checks.
- Added separate unapproved EXP-002B and EXP-002C dossiers and a stage gate
  that requires their frozen prerequisites plus a fresh Admit/inactive/queue-0
  snapshot before material execution.

- Completed the authorised EXP-002A baseline on all seven exact snapshots under
  CCP `origin/main` `104d48d`: Pythia, SmolLM2-360M, Qwen3, GPT-2,
  SmolLM2-135M, GPT-Neo, and Qwen2.5. All seven terminal outcomes are `null`,
  with one analysis-boundary target read per model and no promoted claim.
  Immutable packages and external response-score hashes are published in
  `results/exp002/preexecution/publication-manifest.json` on branch
  `exp002-qwen3-followup` through exact head `9cbe6f5`.

- Created and published branch `exp002-qwen3-followup` for the Qwen3 outlier
  follow-up research plan. The no-model implementation is current through
  exact head `7b06136` (implementation commits are preserved in the branch
  history).
- Added the frozen seven-model protocol, tokenizer-audit receipt in
  `not_started` state, response-surface permutations and label-prior
  diagnostics, source-familiarity and rights/proximity plans, transfer-corpus
  and exact sign-flip analysis contracts, fail-closed terminal and CCP guards,
  restart handoff, and preexecution publication manifest.
- Expanded the direct TRIZ bank to 351 target-free questions: eight balanced
  task types for each of the 40 principles plus self-report, foundational,
  Matrix-direction, Panitz-edge, and false-concept controls. Public records
  contain no answer keys; locators remain sealed.
- Contract audit and 16 focused synthetic tests passed. No model/tokenizer,
  network, generation, CCP material run, or sealed target was accessed. The
  next material step remains a fresh operator approval bound to the exact
  dossier; no result or TRIZ claim is promoted.

## 2026-08-19

- Merged the final two-model publication checkpoints: GPT-Neo PR #96 at
  `74926e15fe06a6e41ef1aa0d96e731b70636531a` and Qwen2.5 PR #97 at
  `a081e612feca348b28253ee0cc9e67c24b45ed3a`. Exact-head CCP receipts are
  public on `ccp-evidence/df6ed20c070884f516c02c73c6adcc2307981b9d` and
  `ccp-evidence/e7947e4380b6cef82bb34fa0b51e80f049217b88`. A fresh public
  clone passed both publication verifiers when the locally retained dense
  response assets matched their declared hashes, and rejected missing and
  one-byte-mutated assets fail-closed. The seven-model comparative record is
  now complete as independent exploratory terminal packages; no claim IDs are
  promoted and no model is rerun.

- Completed the two authorized complementary-model controls, one run each from
  merged `main`, with CCP `Admit`, inactive admission, and an empty queue.
  GPT-Neo (`EleutherAI/gpt-neo-125m@21def0189f5705e2521767faed922f1f15e7d7db`)
  terminated `null` at p=.6875 (mean domain delta +.01553), 323.899 s wall,
  1,858,076,672 B peak RSS, and 20,599 B dense output. Qwen2.5
  (`Qwen/Qwen2.5-0.5B@060db6499f32faf8b98477b0a26969ef7d8b9987`) terminated
  `null` at p=.96875 (mean domain delta - .00587), 935.267 s wall,
  4,876,828,672 B peak RSS, and 20,699 B dense output. Both used CPU float32,
  no network/generation, exactly one sealed-target read, and no retry; claim
  IDs remain empty and pooling remains forbidden. Packages are published only
  after verifier PASS, with dense response assets external/hash-bound.

- Operator authorization was recorded for exactly one local-only CPU float32
  run per `EleutherAI/gpt-neo-125m@21def0189f5705e2521767faed922f1f15e7d7db`
  and `Qwen/Qwen2.5-0.5B@060db6499f32faf8b98477b0a26969ef7d8b9987`, with
  allowlisted downloads, 1,800-second/8-GiB/128-MiB ceilings, no network or
  generation, one sealed-target read at the analysis boundary, and publication
  of every terminal outcome. GPT-Neo acquisition completed at exactly
  529,444,041 bytes (model SHA-256
  `52738cbfb54e25a232598242f60ef19ee193d36090b98fe649b10c02724b3521`), and
  Qwen2.5 acquisition completed at exactly 999,586,188 bytes (model SHA-256
  `88c142557820ccad55bb59756bfcfcf891de9cc6202816bd346445188a0ed342`).
  Integrity receipts are recorded under
  `results/exp001-comparative/preexecution/`; both explicitly state that no
  model output or sealed target was accessed. Material runs remain pending
  CCP `Admit` with inactive, empty admission and the one-run boundary.

- Studied official Hugging Face cards, frozen configs, tokenizer metadata, and
  licenses for two further tiny complementary candidates. Frozen a separate
  no-download dossier for `EleutherAI/gpt-neo-125m@21def0189f5705e2521767faed922f1f15e7d7db`
  (MIT, GPTNeoForCausalLM, 12 layers, 768 hidden) and
  `Qwen/Qwen2.5-0.5B@060db6499f32faf8b98477b0a26969ef7d8b9987` (Apache-2.0,
  Qwen2ForCausalLM, 24 layers, 896 hidden). The former supplies an architecture
  control distinct from GPT-NeoX Pythia; the latter is a within-provider
  Qwen2/Qwen3 control. OpenELM-270M and Mamba2-130M remain rejected alternatives
  because of remote-code/AMLR or missing self-contained tokenizer contracts.
  No model, weights, or sealed target was accessed; acquisition and material
  execution remain explicit later gates.
type: chronology-log
title: Documentation Chronology
description: Time-ordered notes for maintained documentation and governance updates.
status: canonical
last_verified: 2026-08-19
---

# Documentation Chronology

## 2026-08-19

- Official-source runtime review completed for the two additional controls.
  GPT-2 is `GPT2LMHeadModel` with 12 layers/768 hidden units; SmolLM2-135M
  is `LlamaForCausalLM` with 30 layers/576 hidden units but its pinned
  tokenizer metadata explicitly declares `GPT2Tokenizer`. The contract and
  preventative preflight are documented in
  `docs/EXP001_ADDITIONAL_MODEL_RUNTIME.md`.
- GPT-2 and SmolLM2-135M integrity receipts were verified from the exact
  authorized snapshots. One local CPU float32 run per model then completed
  under CCP with no network or generation and one sealed-target read each.
  Both terminal outcomes are `null`: GPT-2 p=.3125 (316.68 s, peak RSS
  2,121,891,840 B) and SmolLM2-135M p=.5 (341.66 s, peak RSS 2,520,023,040 B).
  Dense response assets are hash-bound in the immutable package manifests but
  retained locally; their contents are not publicly disclosed. A fresh clone
  therefore rejects a missing external asset fail-closed; claim IDs remain
  empty and scores are not pooled.
- A pre-access authorization-digest stop occurred before GPT-2 model load;
  no model or target was touched. The digest binding was corrected, locally
  CCP-qualified, and merged at `86973b407e3e207f7ca22ecf91b4f9e5b8c7b154`.
- Official revision-tree metadata was then fetched without model bytes for the
  next two candidates. The exact authorization request binds GPT-Neo's
  eight-file 529,444,041-byte allowlist and Qwen2.5's seven-file 999,586,188-
  byte allowlist, including Hub blob/LFS identifiers and canonical metadata
  hashes. It remains `approval_requested` with every permission false; the
  previous GPT-2/SmolLM2-135M approval is not reused. No weights, model, or
  sealed target was accessed.
- The operator gave an explicit authorization for the two exact revisions,
  including allowlisted acquisition, integrity receipts, CPU-float32 loading,
  one run per model, and one sealed-target read at the analysis boundary. Its
  canonical text digest is
  `2f70403f386c1a573ae4cc133f25d4612af8b58f6c1c0fe285b30a4d7e5df5a1`. The
  request grants no tuning, substitution, protocol change, or retry after
  model/target access; no model or target has yet been accessed.
- A target-free `exp001_next_model_contract` and dedicated runner were added
  for the two architectures. Synthetic tests verify exact tokenizer/context
  metadata, integrity-receipt prerequisites, offline/no-generation boundaries,
  and refusal before model or target access. Material execution remains behind
  the fresh CCP Admit gate.

## 2026-08-18

- EXP-001 comparative tranche completed at exact head `c3027216853aa66faca77d35f28d11551a67be02`: CCP generation 6 passed on Python 3.11 and 3.12 after one non-material queue-timeout attempt.
- Exactly one authorized local CPU-float32 run completed for each model: Pythia (`null`, p=.6875), SmolLM2 (`null`, p=.65625), and Qwen3 (`null`, p=.0625).
- Each receipt records network disabled, generation false, exactly one sealed-target read, and approved resource ceilings. Publication verifiers pass for all three packages; dense assets remain external and hash-bound.
- Qwen3 produced a strong exploratory near-signal (mean domain delta +.9323; bootstrap CI [+0.5353, +1.2063]) but failed the preregistered p<=.05 and all-domain-positive gates because agriculture was slightly negative. No TRIZ claim is promoted.

- The comparative execution runner is fully bound at exact head
  `80b1de1df9c86c09b839327b3e89538cecead616`, with CCP v2 PASS published on
  `ccp-evidence/80b1de1df9c86c09b839327b3e89538cecead616`. Before the first
  model run, the required fresh admission check reported `active=true`,
  `queue_count=0`; live process inspection identifies an independent Matryca
  CCP/OrbStack run `909548b6ce14-ready-20260818T082051Z-58918` (guard PID
  58918, container `matryca-local-ci-*`). No process was terminated and no
  model or sealed target was accessed. Resume only after admission returns
  inactive with an empty queue.

- Corrected comparative receipts to bind the actual serialized external-score
  asset size instead of reporting zero dense bytes. The correction is published
  at `481cc082f8559b76bac3fa193820c83e07a8348e`; it awaits a fresh exact-head
  CCP receipt once the independent admission holder releases the slot.

- Operator authorization was recorded for the exact Qwen3 seven-file runtime
  acquisition at `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`, capped at
  1,610,612,736 bytes and limited to streaming SHA-256 integrity receipts.
  Model load, feasibility, generation, and sealed-target access remain
  explicitly forbidden. A fail-closed downloader now binds the authorization
  before any request, permits only official Hugging Face CDN redirects, rejects
  symlink/path escapes, and removes interrupted partials. The transfer is in
  progress; no model or target has been accessed.

- Qwen3 acquisition completed at the exact pinned revision. Seven files are
  present under the ignored runtime root, total `1,203,625,970` bytes, and the
  immutable receipt `results/exp001-comparative/preexecution/qwen-integrity-receipt.json`
  records per-file SHA-256 plus official Git/LFS source OIDs. No model load,
  generation, feasibility test, or sealed-target access occurred. The next
  gate is exact-head CCP qualification before the three one-run material
  executions.

- The comparative target-free tranche is committed at `a4ee5c74f3e0436f969f2411eb5b03385cbeaa87`.
  Live resource status is `Admit`, but exact-head CCP admission remains
  fail-closed because the shared coordinator reports an incompatible
  `.../leases` layout. No CCP qualification, model load, download, or sealed
  target access was attempted past that gate; the stale-layout report is
  ready for the CCP maintainer.

- Froze the target-free EXP-001 comparative dossier for the first-model Pythia
  retest and a third Qwen3 model. The dossier reuses the 40-principle,
  Matrix-2003, and Panitz fixtures without pooling strata or model scores,
  binds Qwen3 at exact revision `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`,
  and records all unknown acquisition/feasibility fields. No model or sealed
  target was accessed; explicit approval remains required before download,
  model load, or material execution.

- Closed the R3 publication checkpoint after PR #75 merged at
  `4cc1c6d862bffc9558b47a5cadd838a2ee22c465`. The exact-head CCP receipt is
  public on `ccp-evidence/48a354eaa2f06e0e6eabf016c42a7387a1ab1b65`. Fresh-clone
  verification passed with the declared external response-score asset and
  failed closed for missing or mutated bytes. The asset remains external/local
  pending explicit authorization to publish its contents; its locator/hash and
  the terminal null result are public.

- Exact-head CCP qualification then passed on `8bd99a68c07f8c666ec77e0f7d009703ac4551cf`
  for Python 3.11/3.12 with a clean worktree. Under the separately recorded
  authorization, the single guarded SmolLM2 R3 run completed terminal `null`
  in 299.054 seconds with peak RSS 2,824,798,208 bytes, exactly one sealed
  target read, and no retry. The immutable package and external response-score
  locator/hash are ready for publication; all claims remain exploratory and
  non-pooled.

- The R3 exact-head CCP attempts at `8a4df44` and `db46782` failed before any
  model or target access. The dependency-light image correctly lacked the
  optional `torch` package needed only by model-adapter synthetic tests, and
  CCP mounts a writable `/tmp` tmpfs capped at 64 MiB. The repository check now
  prefers `/dev/shm`, skips only those optional model tests when the dependency
  is absent, and excludes local `.venv` symlinks from copied-repository
  fixtures. Direct Python 3.11/3.12 read-only diagnostics pass; a fresh
  exact-head CCP receipt is still required before material execution.

## 2026-08-16

- Published and merged the non-authorizing R2.3 approval dossier through PR 62
  at `b9260cd9743d2afd5eb7fc79339e0687fa22689c`, from exact source head
  `28f0b2596a273212dfc0712aaa00b5887ecce83a`. Evidence branch
  `ccp-evidence/28f0b2596a273212dfc0712aaa00b5887ecce83a` points to receipt
  commit `880700a31a3f3f2a3ca639d1ab7b12a02c69ba82`; run `31955588854`
  attempt 2 passed the trusted scientific, exact-head CCP, aggregate, and
  required status gates. The dossier still records
  `operator_approval_granted=false`; no model load, material execution, or
  sealed-target access was authorized or performed.
- Closed the CCP multi-runtime v2 prerequisite at PR 37 merge commit
  `044697dee9a0d678d30a4847d62ddf9b4970505b`. The contract supports exact-head
  Python 3.11/3.12 local coverage with independently bound runtime and image
  digests; historical v1 receipts remain preserved.
- Merged Latent-TRIZ PR 51 at `39ad1965e82f5aa2f4671e38708e401774f176ec`.
  Its exact source head `e249c4b42795b27d27d78a0b5c3526a38e7809de` was qualified by receipt branch
  `ccp-evidence/e249c4b42795b27d27d78a0b5c3526a38e7809de` (evidence commit `e4fb6c183483cedd12d9306c29938d1bdedae966`) and terminal run
  `31934684914`; Python 3.11 took 2m44 and CCP 42s.
- Merged PR 50 at `e6a634d52fcd153d6c78224fabb8df4713b18415`, publishing the
  immutable public GHCR Python 3.11 and 3.12 verification images by digest.
  Merged PR 53 at `64892dd227f7256fe0dae204e501b2867ef4f905`, bridging the
  trusted CCP verifier to v2.
- Closed PR 54 without merge at head
  `c6874fdaa11aeebee079579b0a323146818be8fa`: its v2 receipt could not yet be
  evaluated by the base's v1-only policy route. This was a routing dependency,
  not a runner or scientific result. PR 55 then merged the fail-closed v1/v2
  policy selector at `28b6c5d309eb5e640c34945e598b3a1e8425d979`. The rebased
  matrix migration was then qualified once at head
  `c913ea5b89bc6feb261560ebfd80bb5bc2d23080` and merged by PR 56 at
  `1457e2c4e5e6affba75266fc0b62e7375f8e16fa`.
- Merged post-migration PR 57 at
  `9ef86ec22a46422eb586fbe29085cc0b05672ea8`. Run `31949031711` created no
  Python 3.11/3.12 candidate jobs: classifier took 8 seconds, receipt verifier
  45 seconds, and aggregate 3 seconds. Run wall time was 71 seconds and summed
  successful-job intervals were 56 seconds, versus 237 and 473 seconds in
  pre-migration run `31948392224`. GitHub reported zero billable milliseconds
  for both runs; no monetary saving is inferred.

- Merged the trusted CCP timeout migration in two fail-closed steps. PR 48
  changed only the accepted configuration digest and merged at
  `afd4b56ae84a944dc4cd60486caabce9b9452f75` after a receipt produced by the
  existing 120-second plan passed the base policy. PR 49 then changed only the
  repository-check timeout to 180 seconds and merged at
  `85180041717f336de554300dda109731b48c6b95` after its new-plan receipt passed
  the already public policy. Both PRs passed Python 3.11, Python 3.12, exact-head
  CCP, aggregate, and review-thread gates. No candidate policy authorized its
  own receipt, and no model or sealed target was accessed.
- Merged PR 47 at `fa1e254ec373092278b1ab63f05504545e295b67`. The R2.2
  implementation is public; R2.3 model execution and sealed-target access
  remain separately approval-gated.

## 2026-08-15

- Qualified the complete R2.2 implementation locally at exact head
  `e9df61830611cff2c3acf60ea1382cdf9968e1b8`. The full repository suite and
  exact-head CCP repository check pass, and the clean receipt matches that
  head. No model or sealed target was accessed. The branch and receipt remain
  unpublished, so this is a resumable local checkpoint rather than merged
  evidence; R2.3 remains approval-gated.
- Merged the R2.1 publication and receipt branch through PR 46 at
  `1f35ba353e792aa263db7449216e3172d0306798` after exact head
  `5f9c21db944f25fd1dac4a550911c85e86471e35` and public receipt publication.
  R2.1 is now verified complete. R2.2 is in delivery as the local/offline
  SmolLM2 tranche with 192 forwards, 1920 vectors, the final-block primary,
  descriptive layers, views, and sites, fixed primary thresholds, strict
  single target read, failure publication, and descriptive-only cross-model
  concordance and resource-envelope refusal. Fifty-five focused synthetic tests currently pass, the
  execution contract verifies 11 code files and 9 runtime files without model
  load, and no real model load or sealed-target access occurred. R2.3 remains
  explicitly approval-gated.
- Began the no-human-review A0-R2 study preregistration from public main
  `25c978d89a07fcd66194f8e0e333ebdae2f6bc08`. The planned study keeps one fixed
  cross-model primary, freezes broad descriptive sensitivities and negative
  controls before output, forbids sensitivity rescue and claim promotion, and
  retains a separate explicit gate for one sealed/material execution.
- Merged the A0-R2 feasibility contract through PR 44 at
  `da8f4bb0c07fe32ede438b13da80b89019cfb812`, then executed the one authorized
  CPU-only probe. The schema-valid receipt reports `compatible`, 33 hidden-state
  entries, repeatability difference 0.0, 2,540,519,424 bytes peak RSS, and
  3.813451875 seconds total time. The outer CCP guard exited 70 with cleanup
  uncertain at `completed descendant seal`; a separate post-run observation
  records an inactive admission gate, empty queue, no matching processes, and
  no retroactive guarded PASS. The model was not rerun, no output content was
  retained, and sealed targets remained untouched.
- Merged the A0-R2 acquisition checkpoint through PR 43 at
  `5d4d96c16b56715203aa8a077b13d3b6cc550fc9` after publishing the exact-head
  CCP receipt and obtaining a green trusted aggregate. The external nine-file
  snapshot remains integrity-verified and ignored by Git.
- Started the separately authorized A0-R2 bounded feasibility tranche by
  freezing a pre-load CPU float32 contract. The tranche allows only a fixed
  synthetic probe, two non-generative forward passes, compatibility, timing,
  repeatability, and memory measurements. It remains instrumentation-only;
  sealed targets, sealed R2 execution, and scientific inference stay blocked.
- Published the terminal A0-R R1 package through PR 41 at merge commit
  `05ba15a28442260c32951413c9128f0179573198`. The immutable package retains
  the raw output, deterministic 54-label clerical recovery, recovery receipt,
  activation receipt, 96-record representation index, report, manifest, and
  external dense-asset locator. The fixed primary remains positive exploratory
  E0 evidence: 23/24 family successes, macro-F1 0.624348 versus 0.499130,
  margin 0.125217, six domain-direction successes, and permutation p = 0.002.
  Exact-head repository qualification and all seven hosted checks passed; A0
  stayed byte-stable, claim IDs stayed empty, and H1/Wave 2 were untouched.
  At that closeout, R2 model acquisition and material execution remained
  explicitly approval-gated.
- Recorded the authorized SmolLM2 runtime acquisition: nine files at revision
  `f8027fd0eaeea54caa13c31d31b9fdc459c38b49`, 727,058,433 bytes total, receipt
  status `integrity_verified`, weights SHA-256
  `7aaff6661428bed033abba9522bec81938678642cca3181fe752b6ca9e1e540f`, all
  access flags false. This is instrumentation-only and evidence-ineligible.
  Model load, feasibility, output generation, sealed targets, and any sealed R2
  run were not authorized and were not performed.
- Merged the A0-R R1.4b harness in PR 40 at
  `c5b28cd3ffca38a4bbdca076ba4bff306e653aa6`, then executed the frozen R1
  endpoint once. The exploratory result is positive: 23/24 family successes,
  macro-F1 0.624348 versus 0.499130 for the surface baseline, margin 0.125217,
  six domain-direction successes, and permutation p = 0.002. The raw output's
  clerical `r1_` prefix failed schema validation; R1.5 preserves it and records
  a deterministic 54-label recovery with no metric changes and no additional
  model or sealed-target access.
- Merged A0-R R1.4a at `73d5e1cad5422d24209252257b54a46c24f8ee16`
  after exact-head qualification and hosted gates. The checkpoint binds the
  runtime, inputs, code, classifier, permutation, baseline, and domain rule;
  it accessed neither model output nor sealed targets. R1.4b is now preparing
  a separately bound runner and remains pre-output until that harness is
  reviewed, qualified, and merged. The harness records operational exceptions
  in a separate immutable receipt with tri-state access evidence; it does not
  fabricate a statistical outcome or treat uncertain access as non-access.
- Froze the A0-R R1.3 calibration and protocol state: exact-binomial power
  receipt now records false-positive rate `0.03195732831954956`, power
  `0.9108287412264922` under family-success probability `0.8`, minimum
  detectable effect `0.2597184664182352`, `100000` deterministic simulations,
  and minimum permutation p-value resolution `.001`. R1.3 merged to `main` and
  the protocol is frozen before model output, with no model or sealed output
  accessed. R1.4a subsequently merged with fixed runtime/input/code hash binding,
  fixed classifier/permutation/baseline/domain-statistic specification, and
  synthetic-adapter / synthetic-vector tests only. Model activation and sealed
  inference remain blocked behind the R1.4b pre-run harness gate.
- Completed the pre-freeze A0-R R1.2 corpus substrate: 48 independent families,
  96 paired cases, physically separate 48-case calibration and sealed target
  files, zero independence-audit violations against the 192-case A0 source,
  and 14/14 passing shortcut controls. Added strict artifact schemas and
  `make a0r1-verify` for byte-for-byte regeneration. No model output was
  accessed and the protocol remains planned pending the R1.3 power freeze.
- Started A0-R R1.1 with a planned protocol and strict schema fixing the
  same-model primary endpoint, power thresholds, E0 envelope, and immutable A0
  source anchors. Added a fail-closed independence auditor whose API keeps
  calibration and sealed targets physically separate. This is implementation
  substrate, not a freeze or empirical result.
- Published the complete A0 sealed exploration through PR 34 at merge commit
  `fc80976d3a256ed88e2d59f1a6f893e15154e3a0`. The frozen automated-proxy
  result is positive with maximum-statistic p = 0.005, 24/24 paired-family
  successes, and macro-F1 margin 0.188234 over the problem-only baseline.
- Preserved the result boundary: exploratory, evidence-ineligible, not
  expert-validated, empty claim links, and no promotion from E0.
- Closed the stale A0 delivery notes, added the separate A0-R independent-corpus
  and cross-model replication contract, and added a concise persistent goal
  pointing to the canonical Laboratory Master Plan.
- A0 protocol checkpoint `v1.0.3` was frozen before any model-backed or sealed
  execution. The deterministic label-free corpus is 96 families / 192 cases.
- Calibration and sealed evaluation files were separated at manifest level, with
  `sealed_targets_accessed: false`.
- Initial v1.0.1 corpus setup was rejected for shortcut calibration and replaced
  pre-freeze with token-matched unique role-pair redesign.
- All 14 shortcut controls passed on the 96 calibration cases.
- Power-calibration parameters fixed as 4 problem families/domain, 24 problem
  families total (48 paired cases), 199 permutations, critical threshold 19,
  MDE 0.333212784429589.
- The later exact-model sealed run and publication are recorded above; no TRIZ
  validation claim is made.
- The next automated milestone is a separately frozen A0-R replication, not a
  mutation or rerun-in-place of the published A0 result.

## 2026-08-14

- Added the canonical Phase A0 specification for a fully automated,
  exact-revision, counterfactual proxy exploration of the Weak Latent TRIZ
  Hypothesis. A0 freezes its design before sealed evaluation, publishes null and
  failed outcomes, remains independent from H1 and Wave 2, and cannot promote an
  expert-validated TRIZ claim.
- Added the canonical Laboratory Master Plan: an evidence-bounded evolution
  ledger from the verified PR 1–29 foundation through annotation v1.2, the
  permanent Wave 1 negative control, paired label-free Wave 2, canonical human
  labels, empirical envelope v2, multi-view model artifacts, and the first
  authentic EXP-001-R path. The plan records exact exit evidence, claim impact,
  residual risk, deferred work, and the cost-aware delegation policy.

## 2026-08-13

- Added the stable path- and risk-aware merge policy contract: lightweight docs qualification, dual-version Python checks for code, exact-head CCP plus artifact auditing for scientific changes, and scheduled live ruleset drift detection.
- Reordered the research program after the retained Wave 1 negative surface result: integrity hotfixes and stable governance now precede annotation v1.2, immutable calibration-only Wave 1, label-free counterfactual Wave 2, canonical human labels, and the first empirical recognition run. Empirical direction and causal work remain deferred until held-out-domain generalization is demonstrated.
- Replaced Lab 04 all-layer Holm gating with shared, domain-blocked max-statistic control, nested alpha reselection within every permutation, explicit p-resolution refusal, typed public receipts, and regenerated fail-closed Lab 04–05 fixture artifacts.
- Updated the v1.1 annotation ontology workflow: four primary ontology labels plus
  abstain, canonical case and batch hashes in annotation records, v1.1.0 display
  version, nominal Krippendorff alpha in blinded-audit output, and explicit
  frozen agreement policy in the stage-1 guide and audit schema.
- Added deterministic, case-clustered 95% bootstrap intervals for raw agreement
  and nominal alpha as descriptive calibration metadata under a frozen seed and
  resample count.
- Added the Wave 1 retained audit command for per-rater files, including
  exact guide digest checks, full coverage, pairwise agreement and abstention
  thresholds, consensus and disagreement retention, and a non-evidence
  boundary for `artifacts/annotations/wave1-audit.json`.
- Documented the Wave 1 candidate batch as discovery-only: 24 model-generated Segmentation/Inversion cases across four domains, reciprocal opposite-label pairs, lexical-cue exclusions, non-frozen status, and evidence ineligibility.
- Added the acceptance path for Wave 1 to the protocol: two independent raters, abstentions, agreement checks, provenance expansion, split freeze, and leakage audit before confirmatory use.
- Added the blinded localhost annotation workbench documentation path, with
  sanitized case views, Segmentation/Inversion-only labeling, local append-only
  outputs, and an explicit non-evidence boundary.
- Promoted the commit-bound CCP receipt to the primary pull-request gate after repeated exact-head end-to-end trials; retained the Python matrix on `main` and manual dispatch to reduce duplicate GitHub Actions execution.
- Added Lab 05 candidate-direction instrumentation with D1-D8 gates, seeded and unrelated-label controls, sparse public artifacts, and an explicit no-steering/no-causality boundary.
- Added the one-command local visual laboratory suite for navigating the maintained Lab 00 through Lab 05 artifacts with explicit readiness, provenance, and no-claim boundaries.
- Added Lab 03 behavioral-baseline contracts, deterministic local diagnostics, leave-one-domain-out and random-label gates, and an explicit no-claim visual report.
- Added Lab 02 dataset anatomy with immutable split membership, provenance/license checks, source/template leakage fingerprints, balance gates, annotation reliability, and a one-command visual readiness report.
- Added Lab 01 as the first exact-revision, real-model instrumentation laboratory with receipt-derived readiness, residual-stream capture, final-logit parity, repeatability, sparse public artifacts, and an explicit no-TRIZ-claim boundary.
- Added fail-closed evidence-profile obligations to claim-level promotion and target-specific readiness for the foundation, Lab 01, and EXP-001.
- Added offline model-preflight and dataset-audit gates for EXP-001 readiness, with deterministic JSON reports and no-download enforcement.
- Renamed the public laboratory to Latent TRIZ and updated repository identity references.
- Added the canonical E0-E6 Evidence Ladder, strict claim schema, and three explicit E0 hypotheses.
- Reframed the public entrance around the runnable Stage 1 process smoke and its non-empirical boundary.
- Added four contribution lanes and a staged visual/mechanistic-interpretability roadmap.
- Added the one-command, dependency-free Lab 00 visual smoke, explicitly infrastructure-only and not claim-attached.
- Recorded the provisional EXP-001 model roles and synthetic-first dataset strategy in ADR 0003 without promoting claims or freezing a preregistration.

- Initialized the Matryca Knowledge OKF maintained-bundle documentation structure.
- Added documentation portal pages and ADR 0001 for the dependency-free official-lab foundation.
- Wired root README, CONTRIBUTING, and PR template to require documentation checks and timestamp updates.
- Added a deterministic zero-LLM OKF gate for metadata, lifecycle, safe entry points, links, anchors, and unique canonical roles.
