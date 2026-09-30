# A0X First Result Autonomous Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to execute this plan task by task. Use `a0x-qualified-llm-lab`, `orchestrate-long-running-work`, and `terra-cost-aware-orchestration` throughout. Do not treat this plan as authorization for a material action or a remote mutation.

**Status:** N2 target-free closure tests complete; N3 broad suite is not green because frozen source bindings are stale and two history replays are hosted-CI-only; N4 regeneration requires separate authorization  
**Plan version:** 1.3 — current-state addendum on 2026-09-27; the earlier v1.2 review does not approve this addendum  
**Primary orchestrator:** GPT-5.6 Terra High  
**Bounded workers:** GPT-5.6 Luna  
**Architecture, safety, and release reviewer:** GPT-5.6 Sol  
**Every-block technical decision owner:** GPT-6 Astra, independently of implementation  
**Scientific objective:** obtain the first defensible terminal A0 result for the exact SmolLM2-360M pair, then preserve a reusable vertical path for A0-R1 and the remaining models.  
**Canonical pair:** `A0 / HuggingFaceTB/SmolLM2-360M@f8027fd0eaeea54caa13c31d31b9fdc459c38b49`  
**Historical implementation anchor:** HEAD `4f801f03d85d36c6aabda36ffe7ed33dfe1db05e`, tree `d1fcef86cdaa56f1059f5b0b39ba911cd3ac6bda`; this is not a current public-main claim  
**Current ruling:** `NO-GO` for material execution until every applicable prerequisite through CR-5 is complete, the exact one-shot authorization is approved, and the immediately pre-execution checks remain green.

## Current-state addendum — 2026-09-27

This addendum supersedes the dated *status observations* in the 2026-09-19
section below. It does not replace the detailed acceptance criteria or grant an
authorization. Read the current [vertical-slice runbook](../../A0X_VERTICAL_SLICE.md),
the locally installed `a0x-qualified-llm-lab` skill when available, and the
latest checkpoint before acting. The skill is
an operator aid; repository specifications remain authoritative. The route is
**Hosted Gate A → four-input capture → pair-scoped P0 v2 → Gate B v2 → Gate C v2
→ terminal verification**. Pre-Gate-A source-bound inventory/freeze/dossier
reconciliation is a separate operation, not P0 v2. Older P0-before-A and
v1/batch artifacts are historical and must remain byte-identical.

### Verified local state and limits of that evidence

- A clean local public-main snapshot at
  `/private/tmp/latent-triz-pages-fresh-0fd314` resolves to HEAD
  `1b070e84f79a689beefdd89f53b5fcbbb29510d0`, tree
  `92534ed24da4401b8b3030b5fe1f3e6fb1a3d7f2`. This is a **local
  snapshot**, not a live 2026-09-27 verification of `origin/main`, PRs, the
  ruleset, or the required checks. Requery those before any remote action.
- The implementation clone is
  `.a0x-runtime/workspaces/a0x-first-result-4f801f03`, detached at
  `4f801f03d85d36c6aabda36ffe7ed33dfe1db05e`, with substantial dirty
  source, schema, test, and documentation work. Preserve it. Its
  `docs/A0X_PUBLIC_CLOSURE_RESTART_2026-09-25.md` is the latest local
  checkpoint, not production qualification. The primary checkout is also
  dirty and must not be reset, stashed, cleaned, or switched.
- The Sep 25 checkpoint's 186 focused and 706/1-skipped broad-suite results
  are **historical only**. The refusal-timing condition has since been covered
  by fresh parent/child production-context tests; the exact current results
  are recorded in `.a0x-runtime/workspaces/a0x-first-result-4f801f03/docs/A0X_PUBLIC_CLOSURE_RESTART_2026-09-25.md`.
- The current A0X skill route correction received independent Astra
  `PASS_WITH_NOTES` for planning, not for execution. The skills/Beads
  assessment is recorded in
  `docs/A0X_SKILLS_BEADS_SITUATION_ASSESSMENT_2026-09-27.md`; Beads is not a
  first-result prerequisite.
- No A0X model, tokenizer, sealed target, Gate B/C, CCP heavy command, or
  scientific scoring is authorized by this addendum. No new A0X result exists.

### Fastest bounded continuation

| Step | Work and acceptance evidence | Stop boundary |
| --- | --- | --- |
| N1 — source safety | Reverify both checkout identities, full dirty diffs, protected historical hashes, and the checkpoint. Keep one integration owner for overlapping files; use Luna only for independent bounded audits when delegation is authorized. | No commit, source replacement, private-data access, or remote mutation. |
| N2 — close refusal timing | Add target-free RED/GREEN tests against the real parent and child entrypoints for missing and mutated public-closure evidence. Assert zero runner invocations and zero child dispatches; cover production rejection of the synthetic experimental profile. Make only the minimal correction the tests prove necessary. | No production-bound regeneration, model, tokenizer, target, or material runner. |
| N3 — qualify candidate locally | Rerun focused closure and vertical-chain tests, the full target-free A0X suite, synthetic contract check, **A0X target-free schema profile v1** (the N3 substitute for the legacy full schema command that opens protected instances), documentation audit, and diff check. Record exact commands, counts, skips, failures, and SHA-256 of changed source/schema/test files. Sol reviews architecture, authorization, security, concurrency, recovery, and publication closure. Astra resolves only a newly critical ambiguity or the explicit checkpoint required by this legacy plan; reviewers cannot grant operator permission. | Any unresolved P0/P1, incomplete test, or changed protected scientific input is `NO-GO`. The profile does not qualify actual protected-target conformance. |
| N4 — request source-bound reconciliation | First request exact authorization for the local implementation-anchor commit; after that commit, prepare a separate exact regeneration packet binding its new HEAD/tree, protected-input comparison, expected outputs, and overwrite policy. | No inferred permission from green tests or reviewers; no derivative regeneration until its separate authorization. Do not mutate historical v1/batch artifacts. |
| N5 — publish corrected source | After separate exact commit/push/PR/merge permissions, qualify the candidate, verify current public-repository hosted CI and ruleset, and publish only the reviewed engineering correction. Treat any changed HEAD/base/ruleset as a new binding. Public standard hosted CI is the economic default; CCP heavy requires its own authorized non-economic exception. | No automatic GitHub mutation or rerun. |
| N6 — run the one-pair evidence chain | Obtain a fresh successful attempt-1 Hosted Gate A for the merged HEAD, separately authorize/capture its four inputs, then separately authorize one atomic six-member P0 v2 envelope for A0/SmolLM2-360M. Verify exact hashes, regular independent files, ownership, and empty output namespaces at each boundary. | Each gate ends before the next; a consumed attempt is never retried automatically. |
| N7 — obtain first terminal result | Separately authorize exact Gate B v2 runtime prerequisites and readiness, then one Gate C v2 material attempt under the current CCP/host policy if CCP is actually needed. Verify outer and inner terminal status, output and dense-asset hashes, target-read count, cleanup, and public-safe package from a fresh clone. Preserve positive, null, failed, and non-interpretable outcomes without selecting a replacement model or changing the protocol. | A failed engineering attempt is terminal evidence, not a scientific result or retry permission. Publication, PR, merge, release, and A0-R1 each require their own exact authorization. |

### N3 engineering acceptance amendment — A0X target-free schema profile v1

This section adopts the operator-approved proposal
`docs/qualification/A0X_N3_TARGET_FREE_SCHEMA_RECONCILIATION_PROPOSAL_2026-09-29.md`
(SHA-256 `687e716e7eac35c328553637bab034f67844689e7b99425813cab641710d7f2a`)
as versioned engineering acceptance for N3 only. It replaces the N3 requirement
to run `scripts/schema_cross_validate.py` over every declared instance, because
that command reads four protected target files before the authorized analysis
boundary. The operator's adoption recorded here supersedes the proposal file's
draft-status sentence; its approved bytes remain unchanged. The legacy command
and historical artifacts remain unchanged.

The profile must fail closed against a machine-readable, closed-world manifest
covering the complete read closure: all 211 schema-related JSON inputs (209
`*.schema.json` documents, one schema fragment, and one projection registry),
local schema-reference dependencies, the bound validator and implementation sources, every
declared schema/instance pair, direct literal instance reads, and source or
fixture inputs used to construct instances. A source/read-set or manifest hash
drift is a failure, not a request to infer a new allowlist.

Disposition and evidence rules:

- Validate all schema definitions without network, lazy fetch, subprocess, or
  external reference retrieval. References are restricted to the exact local,
  manifest-bound schema closure; remote or unapproved references fail before
  retrieval.
- An existing instance is read only when its exact path has an affirmative
  `validated_public` manifest disposition. Filename, repository tracking, or
  a prior schema pair does not establish that role. Zero existing public
  instances may be admitted; report `validated_public: 0` and public coverage
  of zero rather than overclaiming.
- Keep the four protected A0/A0-R1 target instances `deferred_protected` and
  `UNVERIFIED`. Do not resolve, stat, open, hash, copy, or materialize them in
  N3. Keep the 14 unresolved sensitive paths
  `excluded_sensitive_role_unverified`; classify the other 137 declared
  instance candidates as excluded/unverified unless individually admitted by
  affirmative evidence. No excluded path may be read or represented as public.
- Preserve the three existing A0X positional synthetic pairs and their 12
  mutations. Add separately labelled valid/invalid synthetic coverage for
  protected-target schemas where absent. Synthetic validation proves validator
  behavior only, never real-target conformance.
- Retain existing schema-only checks that do not read instance files. Report
  `validated_public`, `validated_synthetic`, `deferred_protected`,
  `excluded_sensitive_role_unverified`, and other excluded/unverified inputs
  separately. Never label this profile full repository schema validation.
- Tests must intercept prohibited filesystem access and prove rejection before
  opening protected or excluded instances. Reject unknown paths, unlisted
  instances, duplicate pairs, missing schema definitions, and manifest drift.
- Do not call an existing aggregate safe until every transitive test module and
  child process has been audited for protected reads, whole-root copies, lazy
  fetch, and network or remote fallback.
- Preserve the frozen scientific protocol, target order/hashes, selection,
  uniqueness rules, one-read analysis boundary, stopping rules, and historical
  artifacts byte-identically. Do not move A0-R1 target validation into A0 Gate
  C or change production Gate C behavior.

N3 may pass only when the approved target-free profile and safe test ladder,
documentation audit, and independent reviews pass. This amendment does not
authorize inventory/freeze/dossier/receipt regeneration, commit, model or
tokenizer access, target access, scoring, CCP/Docker, network, or remote
publication. Those remain separate exact gates.

**Current block status — 2026-09-27:** Implementation-clone HEAD/tree and dirty
state were rechecked; its status inventory contains no changed paths under
`data/`, `results/`, or versioned `experiments/` (the inherited source/schema/
test/doc diff is intentionally still dirty). N2 is complete under the focused
tests and Sol review. N3's synthetic
contract check, schema cross-validation, docs audit (rerun after checkpoint
update), and diff check passed, as did the 69-test focused suite. The
738-test `a0x-synthetic-verify` command is
not green: 31 failures and 2 errors, all in frozen-package tests. Twenty-eight
subcases detect stale A0/R1 source-size bindings, three failures/errors detect
stale frozen/no-model recomputation, and two historical replay tests correctly
refuse outside canonical hosted CI. Do not edit around or regenerate these
bindings without the N4 authorization. After review, N4 is the next operator
gate: request the already-prepared local implementation-anchor commit packet
referenced below. That commit approval will not authorize source-bound
regeneration; a distinct exact packet and approval follow after the new
implementation HEAD exists. A green local suite is still not material
qualification. At every block update the durable checkpoint with exact paths,
HEAD/tree, dirty state, raw hashes, test evidence, review verdicts, consumed
counts, and the single next permitted action. Do not claim a public-main or
hosted-gate state from a local snapshot. The first scientific conclusion, if
one is obtained, remains an automated-proxy observation at E0; it cannot
establish general TRIZ competence, training-data origin, or mechanism. The
local implementation-anchor commit packet is at
`.a0x-runtime/checkpoints/a0x-n4-implementation-anchor-commit-authorization-2026-09-27.md`;
it binds 47 candidate files by manifest SHA-256
`34fc3fef73c93edd1c3ef6b8c900ab3f96461bda2c3f6a13091a7db8da936da2` and
requests one local implementation-anchor commit only. The local checkpoint
is excluded from the commit; no regeneration or remote action is requested.

## Historical operational review and execution order — 2026-09-19

This revision implements the operator's request for Terra orchestration, Luna operations, Sol reviews, and Astra analysis and progression decisions after **every block**. It updates the existing plan rather than creating another competing execution plan. The previous v1.1 hash was `7ed4aad0ec5846bbb8615c1574e07e896ddd525b501c05219ec088e860540b09`; its reviews approve only that historical version, not v1.2 or future code.

Fresh observations:

- The goal API returns `goal: null`. The earlier budget-limited goal is no longer an active blocker. Do not ask the operator to recreate it as a prerequisite. Never impose a token budget unless explicitly requested.
- Remote `main` still points to `4f801f03d85d36c6aabda36ffe7ed33dfe1db05e`.
- `/private/tmp/latent-triz-pr117-fresh-4f801f03` no longer exists. Do not report its historical clean state as current evidence.
- The primary checkout remains dirty on `agent/a0x-six-model-design`, ahead 52 and behind 9 relative to its cached tracking reference. Those counts are local observations, not a refreshed remote comparison. Preserve all existing changes and stashes.
- A local `git cat-file` for the required source attempted lazy fetching from the promisor remote and failed under restricted networking. Do not equate this with repository corruption or perform an offline clone that implicitly needs the same objects again.
- No new material run, runtime preparation, target read, or scientific result has been demonstrated in this revision. The earlier Luna/Sol/Astra source findings remain historical leads pending verification in recovered source.

### Block map and deliverables

Each row is a decision block. Completion requires evidence, Sol review, and a separate Astra decision. The detailed Tasks 1–14 below provide the implementation requirements; this map provides the progression order.

| Block | Scope and task mapping | Luna operations | Terra integration | Required exit evidence for Sol and Astra |
|---|---|---|---|---|
| B00 | Recover source and checkpoint | Inventory surviving source archives and prerequisite metadata; verify hashes | Select durable isolated checkout, recover exact public source with no hardlinks, copy control plan | HEAD/tree, remote URL, dirty-primary baseline, no alternates/shared objects, control-plan hash, authorization ledger |
| B01 | Task 1: CR-0 correction design | Recheck six historical findings; map existing tests and contracts | Specify one vertical v2 path, immutable evidence graph and terminal behavior | Concrete design, file ownership, real-CLI test matrix, Sol review, Astra CR-0 GO |
| B02 | Task 2: P0 v2 CLI | Add bounded fixture/canonicalization tests under explicit ownership | Implement canonical CLI and atomic package plus external commitment | RED then GREEN regression, interruption/ownership tests, no legacy fallback, per-block Astra decision |
| B03 | Task 3: Gate B CLI and child | Reproduce actual CLI TypeError; test valid v2 path and mutations | Repair production dispatch and exact vertical descriptor validation | Valid graph reaches injected inert capability; invalid graph reaches none; Astra decision |
| B04 | Task 4: adapter and result verification | Build synthetic terminal fixtures and run focused suites | Propagate v4 bindings through adapter, package, verifier and public-safe closure | Real dispatcher/child/adapter chain, frontier-correct outputs, backend equivalence, Astra decision |
| B05 | Task 4: freeze candidate | Execute full ladder once; audit changed-file inventory and hashes | Integrate all fixes, use authorized implementation/packaging commits, regenerate derivatives once | Protected scientific inputs unchanged, reproducible inventories/freezes/dossiers, final candidate anchors, Astra CR-1 GO |
| B06 | Task 5: corrected source hosted | Observe checks and collect public metadata | Execute authorized push/PR/merge, verify fresh public source | All required checks green; fresh attempt-1 Hosted Gate A; Astra CR-2 GO |
| B07 | Task 6: evidence capture | Audit pinned tool and exact metadata | Execute authorized acquisition/capture once | Four immutable inputs, source/run/archive verification, Astra decision |
| B08 | Task 7: P0 production | Independent output namespace/hash audit | Execute authorized P0 once | Atomic six-member envelope, external commitment and exact identities, Astra CR-3 GO |
| B09 | Task 8: prerequisites | Inventory first; download only if explicitly authorized; validate manifest | Resolve exact Python/wheels/snapshot availability and prepare builder plan | Complete independent-file runtime manifests, bounded disk cost, no loading, Astra decision |
| B10 | Task 9: Gate B | Hash/schema/installed-version checks | Execute individually bounded build/preflight/preparation | Readiness graph and verifier receipt, sealed_gate_pending, Astra CR-4 GO |
| B11 | Task 10: run admission packet | Mechanical binding/namespace checks | Resolve existing authorization or prepare one exact missing permission packet | Source/runtime/target commitments, one-shot counts, publication-closure proof, Astra CR-5 GO |
| B12 | Task 11: one Gate C attempt | Passive log distillation only | Own guarded execution and complete terminal lifecycle | Outer and inner status, sealed result or preserved failure, cleanup/resource evidence, Astra decision |
| B13 | Task 12: interpretation | Verify hashes and existing result fields; draft tables | Verify immutable result and scientific limitations | Scientific outcome or explicitly engineering-only outcome, Sol scientific review, Astra CR-6 GO |
| B14 | Task 13: public result | Privacy/link/package audits, documentation preparation | Authorized publication and fresh-clone verification | Public-safe closed evidence graph, correct execution/publication identities, final Astra decision |
| B15 | Task 14: next pair | Gap inventory only | Prepare next A0-R1 pair using proven code | Next-pair proposal with separate unconsumed authorization; Astra decision |

The primary completion target is B14 for the first A0/SmolLM2 pair. B15 prepares reuse; it does not silently start another model or leg. A null finding can satisfy the scientific objective when its measurement is valid. Infrastructure failure cannot.

### Source recovery and durable working directory

Prefer an isolated durable checkout under `.a0x-runtime/workspaces/` in the primary repository's ignored runtime area. Verify that this area is ignored before writing. If unsuitable, select another explicitly writable durable directory; do not rely on `/private/tmp` as the sole copy across restarts. Do not change, stash, clean, reset, or switch the primary checkout.

Inventory existing archives by filename and metadata before reading contents. Exclude private targets and mappings. Reuse a complete local source copy if its exact identity and independence can be proven. If recovery needs a network fetch, distinguish this read-only source acquisition from a material download and match it to applicable authorization; never claim an offline clone succeeded when lazy network access was needed. Recover source before revalidating code findings. Do not acquire a model, wheelhouse, or Gate A artifact merely to review source.

### Autonomous block decision loop

1. Terra selects the next dependency-ready block and records scope, owner files, source, expected output, authorized capabilities, and acceptance tests.
2. Luna performs separable operational work. Terra implements security-sensitive integration and verifies decisive bytes. Workers receive only the current block packet, not the complete conversation.
3. Sol reviews the resulting artifact or delta. Terra supplies reproducible evidence and resolves findings within the approved scope.
4. Terra delegates a fresh analysis to GPT-6 Astra for **that block**, including Sol's review and residual disagreements. The author cannot supply their own independent Astra verdict.
5. Astra returns `GO`, `REWORK`, or `EXTERNAL_GATE`, with exact evidence anchors, required corrections, and permitted next action. GO requires acceptance criteria and no unresolved blocking review findings; it cannot override failed evidence.
6. On `GO`, Terra records the review receipt and immediately starts the next authorized block. Do not finish the turn with a routine request for human confirmation.
7. On `REWORK`, Terra implements the bounded correction or reallocates it to Luna, reruns only affected tests, and returns the changed packet to Sol/Astra. No human confirmation is needed for ordinary in-scope technical corrections.
8. After two unsuccessful correction cycles, escalate the causal diagnosis to Sol and Astra rather than repeating the same patch/test loop. Continue independent authorized work. Escalation is not an automatic user stop.
9. `EXTERNAL_GATE` is reserved for an actual missing permission, unavailable credential/service, resource denial, consumed one-shot attempt, or a required change to frozen scientific scope. It must name the exact unsatisfied condition. A reviewer must not use it for an ordinary implementation choice.

Reuse authorizations that still match their complete scope, hashes, counts and expiry. A request to avoid confirmation delegates technical decisions; it does not retroactively authorize a different model/target/run or erase earlier exact execution limits. Only ask the user when an action truly lacks authority. Prepare all safe independent work and one complete, bundled permission request first.

### Controls against repeated preparation

- Read checkpoint and receipt manifest first; revalidate anchors and changed facts only. Do not reread the entire chat or repeat completed research each turn.
- Keep one integration checkout and one active model/leg. Do not create one clone per test or gate unless isolation specifically requires it.
- Carry out B02–B04 before final B05 derivative regeneration. Do not regenerate twelve dossiers for every intermediate edit. Label intermediate frozen-package drift expected, and require final coherence before publication.
- Reuse the existing RED-test inventory. Reject a test that merely confirms the public two-argument function rejects injection: the regression must invoke the faulty real CLI and demonstrate valid production dispatch succeeds after correction.
- Capture fresh Hosted Gate A only after source correction is merged. Keep old successful artifacts historical.
- Preserve public evidence metadata and prerequisite manifests independently of temporary directories. Store no secrets or target contents in the checkpoint.
- Track outcome, changed hashes and next action per block; avoid verbose command transcripts in the canonical plan.
- Never set a goal token budget without an explicit user request. If the goal service says no active goal, continue the authorized task without inventing a budget blocker.

## Scientific outcome

Produce, verify, document, and—only after a separate publication authorization—publish one defensible A0 result for SmolLM2-360M. `SCIENTIFIC_OBJECTIVE_COMPLETE` requires a result class justified by the frozen scientific protocol, complete required measurements, and successful read-only verification. Positive and valid null results can meet that condition. Non-interpretable, incompatible, failed, admission-denied, timed-out, cancelled, partial, outer-failed or cleanup-uncertain attempts are `TERMINAL_ENGINEERING_STOP` unless the frozen protocol explicitly supports a narrower interpretable scientific finding. A verifier PASS proves integrity, not scientific success. No terminal class authorizes an automatic retry.

The canonical dependency order after the corrected source is public is:

`Hosted Gate A -> capture -> P0 v2 -> Gate B v2 -> Gate C v2 -> R verification`

Scientific completion requires the exact frozen path and a verified scientific result. A preserved terminal engineering outcome ends the authorized attempt while leaving the scientific objective incomplete; record the next missing authority without retrying.

The fastest safe route is vertical, not campaign-wide:

1. repair and prove the real target-free gate chain;
2. merge that exact source;
3. obtain fresh Hosted Gate A evidence for that source;
4. prepare only the A0 / SmolLM2-360M runtime;
5. execute exactly one authorized material attempt;
6. verify and publish its terminal outcome;
7. reuse the proven path for A0-R1 and later models.

## Why material execution is currently blocked

Historical Sol and Astra reviews inspected the clean source at `4f801f03...` and reported the following failures. Confirm them after B00 source recovery; the missing clone prevents treating those historical inspections as new source verification:

1. `scripts/a0x_vertical_p0_bootstrap.py` is a v1 operator and calls `generate_vertical_slice`; no canonical CLI invokes `generate_vertical_runtime_package` for P0 v2.
2. `scripts/a0x_prepare_runtime.py` passes injected keyword arguments to production `prepare_vertical_runtime_bundle(root, request)`, whose hardened public signature accepts only `root` and `request`. A real non-preflight Gate B v2 reaches `TypeError`.
3. Gate B emits `.a0x-runtime/gate-b/v2/.../launch-descriptor.json` with profile `a0x-vertical-launch-descriptor-v2`; `scripts/a0x_material_child.py` accepts only the legacy `.a0x-runtime/launches/...` namespace and profile `a0x-material-child-descriptor-v2`.
4. The production adapter, report, and verifier still select or recognize historical dossier and authorization shapes instead of the full vertical v4 evidence graph.
5. Existing tests prove components with inert guards but do not prove the real CLI-to-child-to-terminal package chain.

Therefore the successful Hosted Gate A run on the current anchor is historical evidence only. Required source fixes will create a new HEAD and require a fresh Hosted Gate A attempt 1. Do not spend operator time capturing artifact `10452455863` unless a later review proves that no source change is required.

## Evidence already available

- Public main reverified on 2026-09-19: `4f801f03d85d36c6aabda36ffe7ed33dfe1db05e`.
- Historical expected public tree, pending source recovery: `d1fcef86cdaa56f1059f5b0b39ba911cd3ac6bda`.
- Hosted Gate A historical run: `35109399536`, attempt `1`, all seven lanes green.
- Historical artifact ID: `10452455863`.
- Historical artifact name: `a0x-hosted-gate-a-4f801f03d85d36c6aabda36ffe7ed33dfe1db05e`.
- Historical archive digest: `sha256:652f70ab13395a13afd54d7a19b8f6fbaba14d6aa4ede1536cba7e4253f9b994`.
- Historical artifact size: `1062` bytes.
- Historical expiry: `2026-12-15T14:34:01Z`.
- Historical target-free baseline: `make a0x-no-model-verify a0x-synthetic-verify` passed in the now-absent clone; no new suite was run for this planning revision.
- Lab lock SHA-256: `23ee537ed17fea0035f0d4e7e86a5a355bd2802adbfaa6b7d787b57c61253400`.
- Expected historical wheelhouse manifest SHA-256: `fe541aa83b5dbd9770da1f50d2cd88eb192586406398d9cffa5507f9f352ca72`, 39 wheels, 150,397,774 bytes. This value must be reverified, never assumed.
- Pinned GitHub CLI executable: version `2.97.0`, SHA-256 `6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c`.
- Exact SmolLM2 revision: `f8027fd0eaeea54caa13c31d31b9fdc459c38b49`.

The local wheelhouse, pinned GitHub CLI, and exact model snapshot are not currently proven present. Their acquisition is a separate prerequisite stage, not an assumption.

## Non-negotiable boundaries

1. Preserve the dirty primary checkout. Perform implementation in a clean isolated clone without hardlinks.
2. Deterministic tools and exact-source inspection outrank delegation summaries.
3. Luna may inspect, hash, run bounded tests, prepare fixtures, and distill logs. Luna does not decide architecture, scientific interpretation, authorization scope, qualification, publication, or merge.
4. Terra owns implementation, integration, exact-state verification, checkpointing, and authorization packets.
5. Sol reviews architecture, security boundaries, one-shot semantics, concurrency, recovery, terminal packaging, and publication.
6. GPT-6 Astra analyzes and decides progression after every B00–B15 block, including intermediate implementation blocks. A missing verdict prevents progression of that dependent block; unrelated authorized work may continue.
7. An LLM review is evidence, not operator authorization.
8. No model, tokenizer, sealed target, mapping, material Gate B, or Gate C access occurs before an exact user authorization for that gate.
9. Push, PR, merge, evidence capture, network acquisition, materialization, Gate C, and publication are separate mutation gates.
10. Any source change invalidates Hosted Gate A evidence and every source-bound downstream artifact.
11. An attempt is consumed when its durable attempt claim is created or its authorized heavy invocation starts, whichever occurs first. This includes failure before model or target access. Acquisition, capture, P0, Gate B, and Gate C use separate attempt accounting. No automatic repair or retry follows a claimed, failed, interrupted, timed-out, cancelled, or uncertain attempt.
12. Preserve every terminal outcome. Never delete, overwrite, reinterpret, or silently replace negative evidence.
13. Do not promote a general TRIZ, causal, training-data, or expert-validity claim.
14. Exclude untrusted same-user mutators for the entire transaction window of capture, P0, Gate B, and Gate C, including claim, publication, terminal write, sealing, and cleanup. Failure to prove this isolation is `NO-GO`.
15. Plan-level Astra unavailability is a plan stop, not a repository or runtime failure.

## Autonomy contract

Terra should continue without asking the operator when all of the following are true:

- the action is local, target-free, model-free, network-free, and non-destructive;
- the action is explicitly contained in this plan;
- the selected baseline matches and changes stay within the block's declared implementation scope; ordinary in-scope source edits are expected and must be reviewed before qualification;
- it does not commit, push, open a PR, merge, publish, acquire remote artifacts, run CCP heavy work, or cross a material gate.

First check the permission ledger. If no existing permission covers the exact action and its unconsumed count, Terra prepares one copy-paste-ready authorization request before an action would:

- change a remote repository or GitHub state;
- download or publish an artifact;
- materialize a runtime or model snapshot;
- access a tokenizer, model weights, sealed targets, or private mappings;
- start CCP `run`, `benchmark`, or `guard exec`;
- retry a consumed or failed attempt;
- change the frozen scientific scope or bypass an explicit permission boundary. Ordinary technical ambiguity goes to Sol and Astra for resolution within scope, not to the operator.

Do not ask the operator to calculate hashes or assemble authorization text. Terra calculates all exact values, records them in the checkpoint, and provides the complete authorization paragraph.

## Delegation matrix

| Work | Luna | Terra | Sol | Astra |
|---|---|---|---|---|
| File inventory, schema diff, fixture audit, hash audit | Primary | Verify | Review block evidence | Decide block progression |
| Red tests and bounded unit tests | Primary where independent | Integrate | Review risk | Decide block progression |
| Production implementation | Assist bounded modules | Primary | Review architecture/security | Review exact candidate |
| Full-suite execution and log distillation | Primary | Verify decisive output; repeat only for drift or gaps | Review block evidence | Decide block progression |
| Gate design and authorization semantics | No | Prepare | Primary reviewer | Independent critical reviewer |
| Scientific statistics and claim language | Mechanical audit only | Integrate | Primary reviewer | Independent critical reviewer |
| CCP, material execution, publication, merge | No | Primary operator | Review before action | Review before critical action |

Every delegated result must include: source HEAD/tree, files inspected, commands run, outputs, limitations, and explicit `no mutation/no material access` statements. Terra rechecks all decisive evidence locally.

## Critical review checkpoints

CR-0–CR-6 are additional named evidence milestones within B00–B15. They do not replace the Sol review and Astra decision required at every block boundary. Historical approval of a plan is not approval of a correction design or implementation.

| ID | Checkpoint | Required evidence | Required reviewers | Stop condition |
|---|---|---|---|---|
| CR-0 | Correction design frozen | Contract map, failure tests, no-material boundary | Sol + Astra | Any unresolved architecture or safety objection |
| CR-1 | Corrected local candidate | Clean HEAD/tree, real-Git chain tests, full target-free suite, regenerated hashes | Sol + Astra | Any fallback, untested real child, race, or hash drift |
| CR-2 | Fresh public source and Hosted Gate A | Merged HEAD/tree, attempt-1 run, seven lanes, artifact metadata | Sol read-only + Astra | Head/base/ruleset/run mismatch or rerun required |
| CR-3 | Captured evidence and P0 v2 | Four captured inputs, P0 package, commitment/dossier hashes | Sol + Astra | Source/evidence/commitment mismatch |
| CR-4 | Gate B ready | Exact prerequisites, verifier receipt, readiness graph, independent files | Sol + Astra | Missing provenance, material load, link/ownership ambiguity |
| CR-5 | Gate C authorization ready | Exact one-shot packet, CCP preflight evidence, output namespace empty | Sol + Astra | Any open race, missing hash, stale resource state, or ambiguous target boundary |
| CR-6 | Terminal result and publication candidate | Immutable package, verifier PASS or preserved refusal, statistical audit, limitations | Sol + Astra | Unverifiable package, overclaim, privacy/provenance issue |

At each checkpoint, Terra sends each reviewer a compact packet, not the entire conversation: exact anchors, changed files, relevant contract snippets, test commands/results, known limitations, and the proposed GO/NO-GO decision.

## Durable checkpoint protocol

After every task and every critical review, write or update an ignored runtime checkpoint under:

`.a0x-runtime/checkpoints/A0X_FIRST_RESULT_AUTONOMOUS_CHECKPOINT.md`

The checkpoint must contain:

- plan path and plan version;
- raw SHA-256 of this plan version;
- UTC timestamp;
- repository and clone path;
- exact HEAD and tree;
- branch and clean/dirty state;
- origin/main and ruleset observation;
- completed task and next task;
- block ID, input hashes, output hashes, named next action and consumed invocation counts; skip completed blocks when their evidence still matches, and invalidate only affected downstream packets after a change;
- exact generated files with size and SHA-256;
- tests and exact exit status;
- independently verifiable Sol and Astra review receipts for every applicable checkpoint: reviewer/model identity, checkpoint ID, reviewed packet SHA-256 including plan and candidate anchors, complete verdict text, UTC timestamp, and immutable response/thread/operation ID or raw-response SHA-256;
- all authorization IDs and whether consumed;
- all one-shot attempt IDs and whether consumed;
- protected user work and paths never to mutate;
- current stop boundary.

No checkpoint may be marked reviewed or approved without its complete review receipt. A missing, partial, ambiguous, or unverifiable Sol/Astra receipt is `STOP`.

Before capture or P0, select one durable isolated execution root whose path will remain stable through Gate C. Absolute mappings, inode ownership, and path bindings are part of the evidence. Before a reboot, archive byte-identical copies of non-reconstructible `/private/tmp` artifacts into `.a0x-runtime/`, verify hashes, and record both locations. Relocation preserves evidence bytes but does not prove runtime resumability or transfer path/inode ownership. Resume only after the relevant gate revalidates or explicitly rebinds the durable location under a new authorization. Never overwrite an owned output. A checkpoint is never authorization to resume a material action.

---

## Task 1: Freeze the corrected vertical v2 contract

**Purpose:** eliminate interpretation during implementation.

**Primary files:**

- `docs/A0X_VERTICAL_SLICE.md`
- `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- `docs/A0X_GATE_B_OPERATOR_HARDENING.md`
- `docs/A0X_HOSTED_GATE_A_OPERATOR_RUNBOOK.md`
- a new design note under `docs/superpowers/specs/`

**Steps:**

1. Create an isolated clone from exact public main. Do not use the dirty primary checkout.
2. Record the raw SHA-256 of this plan in the durable checkpoint. Copy its exact bytes into the isolated clone as an untracked control document through an explicit preserved-control-document procedure; verify byte identity. This does not authorize a commit.
3. Luna maps the current P0 v2, Gate A, Gate B v2, Gate C v2, adapter, report, and verifier data shapes.
4. Terra writes one explicit end-to-end contract covering:
   - canonical P0 v2 CLI inputs and one atomic envelope containing the five-file `package/` plus external `p0-commitment.json`;
   - exact source/commitment binding;
   - Gate B v2 authorization and verifier receipt;
   - wrapper and launch descriptor profiles;
   - descriptor namespace and path derivation;
   - v4 execution authorization propagation;
   - same-user mutation and ownership assumptions;
   - one-shot claim timing;
   - frontier-dependent result terminal classes and packaging;
   - target-free public verification closure without private runtime mappings or target bytes;
   - refusal and recovery behavior.
5. Define one canonical descriptor profile. Do not make the child accept two semantically overlapping profiles.
6. Define how the five Hosted Gate A hashes—the four captured inputs plus the verification receipt—survive unchanged through Gate B, execution authorization, adapter, result manifest, and verifier.
7. Define the real-Git target-free integration fixture. It must execute real operator CLIs and the real child parser with injected inert material capabilities.
8. Define source-changing and material stop boundaries.
9. Request Sol and Astra reviews as CR-0. Resolve every P0/P1 finding before implementation.

**Verification:**

```bash
rtk git status --short --branch
rtk git rev-parse HEAD
rtk git rev-parse HEAD^{tree}
rtk python3 -m unittest tests.test_a0x_architecture tests.test_a0x_vertical_gate_chain_v2 -v
```

First verify that the named test modules exist in recovered source. Run existing relevant tests only. A missing module is an inventory fact, not a useful RED test. Task 2 owns behavior-specific RED regressions; a missing import alone does not reproduce the defect.

**Completion:** approved CR-0 design, no model/target/network/CCP access.

## Task 2: Add a canonical P0 v2 operator entry point

**Primary files:**

- `scripts/a0x_vertical_p0_bootstrap.py` or a new uniquely named v2 script
- `src/latent_triz/a0x_vertical_slice.py`
- `schemas/` for P0 v2 outputs, only if the current schemas are insufficient
- `tests/test_a0x_vertical_p0_bootstrap.py`
- `tests/test_a0x_vertical_slice.py`
- `tests/test_a0x_vertical_gate_chain_v2.py`

**TDD sequence:**

1. Luna writes RED tests proving the operator calls `generate_vertical_runtime_package`, never the legacy generator.
2. Add mutation cases for wrong source HEAD/tree, model/revision, leg, generator profile, Python identity, ledger, occupied output, symlink, hardlink, and post-write source drift.
3. Terra implements the smallest canonical v2 CLI. Do not use `python -c` as an operator surface.
4. Enforce atomic overwrite-refusing publication of one complete P0 envelope: five members under `package/` plus external `p0-commitment.json`.
5. Bind the commitment raw SHA-256, recomputed package commitment, P0 authorization ID, P0 attempt ID, bootstrap identity, source HEAD/tree, pair, model, and revision.
6. Test interruption between construction and publication. No accepted package may become visible without its matching commitment, and no commitment may become visible without all five accepted members.
7. Re-read and hash every output; verify regular type and link count one.
8. Preserve v1 only as clearly historical compatibility code. The v2 path must never silently fall back to v1.

**Verification:**

```bash
rtk python3 -m unittest tests.test_a0x_vertical_p0_bootstrap tests.test_a0x_vertical_slice tests.test_a0x_vertical_gate_chain_v2 -v
```

**Completion:** canonical P0 v2 CLI works target-free in a disposable real Git repository.

## Task 3: Repair Gate B v2 dispatch and descriptor contract

**Primary files:**

- `scripts/a0x_prepare_runtime.py`
- `src/latent_triz/a0x_runtime_bundle.py`
- `scripts/a0x_material_child.py`
- `src/latent_triz/a0x_material_contract.py`
- `schemas/` for the canonical wrapper/descriptor if needed
- `tests/test_a0x_runtime_bundle.py`
- `tests/test_a0x_material_child.py`
- `tests/test_a0x_vertical_gate_chain_v2.py`

**TDD sequence:**

1. Reproduce the current production `TypeError` through the real CLI in a target-free fixture.
2. Refactor injection behind a private test seam. The public production function keeps its hardened signature.
3. Define and emit one canonical vertical wrapper and child descriptor.
4. Make the child accept only the exact derived Gate B v2 namespace and profile.
5. Validate wrapper hash, payload hash, source, tree, pair, revision, commitment, evidence graph, authorization ID, and attempt ID before any material capability is reachable.
6. Add mutation tests showing zero model-factory calls for every invalid graph.
7. Add one valid target-free test showing the fake model factory is reached exactly once.
8. Add a mutation-between-bind-and-factory test to preserve the live regular-independent-file revalidation boundary.

**Verification:**

```bash
rtk python3 -m unittest tests.test_a0x_runtime_bundle tests.test_a0x_material_child tests.test_a0x_vertical_gate_chain_v2 -v
```

**Completion:** the actual child accepts the exact v2 output and rejects all drift before capability use.

## Task 4: Complete the vertical adapter, terminal packager, and verifier

**Primary files:**

- `src/latent_triz/a0x_ccp_executor.py`
- `src/latent_triz/a0x_production_adapter.py`
- `src/latent_triz/a0x_report.py`
- `src/latent_triz/a0x_verify.py`
- `scripts/a0x_vertical_material.py`
- related schemas
- `tests/test_a0x_ccp_executor.py`
- `tests/test_a0x_production_adapter.py`
- `tests/test_a0x_report.py`
- `tests/test_a0x_verify.py`
- `tests/test_a0x_vertical_gate_chain_v2.py`

**TDD sequence:**

1. Remove vertical dependence on `planned_material_dossiers()` and legacy authorization paths.
2. Propagate the exact vertical commitment, Gate B evidence graph, and v4 execution authorization into the adapter.
3. Teach report and verifier to recognize the vertical v4 inlet explicitly. Do not broaden a generic legacy branch.
4. Build a real-Git, real-CLI, target-free end-to-end test that executes:
   - P0 v2 operator;
   - synthetic Hosted Gate A capture inputs;
   - Gate B v2 authorization and verifier receipt;
   - Gate B v2 bundle and descriptor;
   - actual child parser and production adapter with inert capabilities;
   - terminal packager and verifier.
   The fixture must follow the production dependency order and invoke the real dispatcher and child. Synthetic contexts, fabricated terminal stdout, synthetic receipts, and synthetic targets must remain permanently ineligible for production or publication.
5. Cover terminal classes: positive, null, non-interpretable, incompatible, failed, timed out, cleanup-uncertain.
6. Prove the dense asset locator and hash are present when required and rejected when missing or mutated.
7. Prove source, pair, evidence, authorization, and output drift fail closed.
8. Add counters proving: invalid graphs call zero model factories, tokenizers, and targets; valid target-free activation reaches the fake factory exactly once and reads zero targets; the sealed synthetic activation reads exactly one synthetic target; an inner positive cannot override an outer timeout, cancellation, cleanup failure, or other guard failure.
9. Pin the qualified statistics backend and prove its inherited numerical semantics. Do not silently fall back between NumPy and pure Python. Any scaling, quantization, or near-zero standard-deviation change requires Astra scientific review and protocol-equivalence evidence; otherwise it is a new protocol requiring new authorization.
10. Keep protected corpus, selection, and scientific-input bytes identical. Do not regenerate protected inputs merely to absorb implementation drift.
11. Prove target-free publication closure: a fresh verifier can consume the exact public-safe P0 commitment and dossier, vertical execution authorization, Hosted Gate A evidence, and allowed receipts without private runtime mappings, target bytes, or historical-batch fallback.

**Scientific assertions:**

- 24 paired families / 48 cases;
- 199 shared permutations;
- maximum over 12 primary combinations;
- positive threshold: `p <= 0.05`, F1 margin `>= 0.10`, successes `>= 19`;
- minimum attainable permutation p-value: `0.005`;
- F1 maximum and family-success maximum may come from different combinations and must be reported as a composite rule;
- final block remains descriptive;
- Wilson intervals are not simultaneous post-selection intervals;
- all result metadata retain `evidence_eligible=false`, `expert_validated=false`, and empty `claim_ids`.

**Verification:**

```bash
rtk python3 -m unittest tests.test_a0x_ccp_executor tests.test_a0x_production_adapter tests.test_a0x_report tests.test_a0x_verify tests.test_a0x_vertical_gate_chain_v2 -v
rtk make a0x-no-model-verify
rtk make a0x-synthetic-verify
rtk make test
rtk make schema-cross-validate
rtk make docs-audit
```

**Local commit and derivative-regeneration gates:**

Local commits are not covered by target-free implementation autonomy. Terra first prepares an exact implementation-anchor commit authorization. After that literal implementation commit is created, regenerate derivative inventories, freezes, and dossiers against the exact commit. Terra then requests a separate packaging-commit authorization for the derived files. Rerun the complete verification ladder at the clean final packaging HEAD. Record the implementation anchor and final packaging HEAD/tree as distinct identities.

Machine-consumed Git state uses `rtk proxy git` and literal recorded hashes. After the authorized implementation commit, and only then:

```bash
rtk python3 -m latent_triz.a0x_freeze --root . --write-protected-trees --write-a0-selection
rtk python3 -m unittest tests.test_a0x_frozen_package.A0XFrozenPackageTests.test_regeneration_is_byte_identical_for_same_implementation_head -v
```

Between the two displayed commands, Terra runs `latent_triz.a0x_freeze --freeze-all --prepare-dossiers --implementation-source-head` with the literal 40-character implementation commit recorded by `rtk proxy git rev-parse HEAD`. The exact fully expanded command is first written into the checkpoint and authorization packet; no shell substitution is used for machine-consumed evidence.

**Reviews:**

1. Luna performs independent hash/schema/fixture audit.
2. Sol reviews architecture, authorization, race windows, one-shot timing, recovery, and publication.
3. Astra reviews the exact candidate as CR-1.
4. Any P0/P1 finding returns to the failing task. No remote action follows a conditional review.

**Completion:** clean exact final packaging HEAD/tree; distinct implementation anchor recorded; target-free chain green; inventories, freezes, and twelve dossiers byte-stable; CR-1 approved.

## Task 5: Publish the corrected source and obtain fresh Hosted Gate A

This task requires separate exact authorization for commit, push, PR, and merge unless the current authorization explicitly includes each action.

**Steps:**

1. Reverify `origin/main`, ruleset, open PRs, local HEAD/tree, and clean state.
2. Terra produces the exact publication authorization block.
3. Push non-forced to a uniquely named branch.
4. Open a ready PR under the current ruleset.
5. Observe the GitHub-hosted checks. Do not rerun a failed workflow without new authorization.
6. Merge only after all required checks are terminally green, discussions resolved, and exact head/base/ruleset unchanged.
7. Verify new public main and a clean fresh clone.
8. Identify the automatic Hosted Gate A run by exact repository, workflow, event `push`, source HEAD and attempt 1; require all seven lanes green. If no run appears, record the missing gate. If multiple matching runs appear, inspect triggers and apply the documented contract rather than selecting the most favorable run. Do not dispatch or rerun a workflow without matching permission.
9. Record artifact ID, name, size, archive digest, expiry, run ID, attempt, source HEAD/tree, workflow identity, and ruleset.
10. Request Sol read-only review and Astra CR-2 review.

The current run `35109399536` and artifact `10452455863` are invalid for every changed source HEAD. Preserve their metadata as historical evidence only; never capture or reuse them after the correction merge.

**Stop:** a source, base, ruleset, workflow, attempt, or artifact mismatch is terminal for this task. Do not rerun or reinterpret.

Resolve publication permissions against actual anchors as they become known. Keep branch creation, local commit, push, PR creation and merge distinct in the ledger. Reuse an existing permission only when it covers the actual state; never claim that a future merge hash or base was already approved when unknown.

## Task 6: Capture fresh Hosted Gate A evidence

This task requires separate network authorization bound to the exact new main and artifact. If the pinned CLI is absent, its acquisition is a distinct network authorization and attempt from evidence capture.

**Prerequisite:** acquire or verify the pinned regular independent GitHub CLI executable:

- version `2.97.0`;
- executable SHA-256 `6a2ab5fa89553eac1f0df50a26a5eaeea9a665d8971f5a51b32487b72c708f5c`;
- no global Homebrew modification;
- link count one;
- durable location under `.a0x-runtime/tools/gh-2.97.0/gh`.

**Steps:**

1. Luna audits the authorization bindings and output-root emptiness.
2. Terra rechecks the exact executable immediately before capture.
3. Bind the capture authorization to repository, source HEAD/tree, run ID, attempt, artifact ID/name, archive size/digest, artifact `created_at`, expiry, chosen `captured_at`, canonical absolute output root, pinned CLI identity, and maximum capture count one.
4. Prove same-user mutator exclusion for the complete capture transaction.
5. Use the shell-free capture wrapper once.
6. Download the archive once and reuse the exact bytes.
7. Produce only:
   - `hosted-gate-a-evidence.json`;
   - `hosted-gate-a-attestation.bundle.jsonl`;
   - `github-trusted-root.jsonl`;
   - `hosted-gate-a-transport.json`.
8. Verify path, size, SHA-256, regular type, link count one, source binding, run/attempt, archive membership, attestation, and trusted root.
9. Preserve any terminal refusal. No second capture attempt without new authorization.

**Completion:** four immutable local inputs; no model, target, Gate B, or Gate C access.

## Task 7: Produce the exact P0 v2 vertical package

This task requires separate exact P0 authorization.

**Steps:**

1. Terra computes and records the exact P0 bootstrap, ledger, Python executable, inline pre-exec, HEAD, tree, pair, model, and revision hashes.
2. Luna independently verifies all hashes and the atomic namespace containing five package members plus external `p0-commitment.json`.
3. Terra provides one complete copy-paste authorization block.
4. Run the canonical P0 v2 operator exactly once.
5. Produce one atomic overwrite-refusing envelope:
   - `package/protocol.json`;
   - `package/implementation.json`;
   - `package/freeze.json`;
   - `package/approval-dossier.json`;
   - `package/slice-manifest.json`;
   - external `p0-commitment.json`.
6. Verify the commitment raw SHA-256, recomputed package commitment, P0 authorization and attempt IDs, bootstrap identity, source binding, schema, file type, link count, size, and SHA-256.
7. Verify no accepted five-member package was exposed without its commitment and no commitment was exposed without its complete package.
8. Sol reviews the authorization graph; Astra performs CR-3 review over captured evidence plus P0.

**Stop:** any mismatch invalidates progression. No manual edit or package regeneration under the consumed authorization.

## Task 8: Reacquire and verify only the missing prerequisites

Each network acquisition requires a separate exact authorization and a declared disk budget.
Every interrupted, mismatched, or uncertain acquisition is terminal for that authorization: preserve the received bytes and diagnostics, then stop. Do not resume, repair, or retry automatically.

### 8.1 Offline wheelhouse

1. Bind to `requirements-lab01.lock` SHA-256 `23ee537ed17fea0035f0d4e7e86a5a355bd2802adbfaa6b7d787b57c61253400` unless the corrected source intentionally changes it.
2. Acquire exactly versioned binary wheels for CPython 3.11 macOS ARM64, no dependency resolution beyond the lock.
3. Verify all 39 distributions, regular independent files, total size, and canonical manifest.
4. Compare with historical manifest SHA-256 `fe541aa83b5dbd9770da1f50d2cd88eb192586406398d9cffa5507f9f352ca72`. A mismatch is a stop for review, not permission to force the historical value.

### 8.2 Python 3.11 base runtime

1. Bind and verify the complete canonical runtime manifest: interpreter, standard library, `venv`, `ensurepip`, bundled installer, and every required independent regular file—not merely the interpreter hash or import API.
2. Keep acquisition separate from environment construction.

### 8.3 SmolLM2 snapshot

1. Under a dedicated exact acquisition authorization, acquire only the allowlisted target-free runtime files for revision `f8027fd0eaeea54caa13c31d31b9fdc459c38b49`.
2. Download into a distinct temporary directory.
3. Verify filenames, sizes, SHA-256, revision, regular type, and link count.
4. Atomically rename into the durable cache only after verification.
5. The acquisition authorization covers stored bytes and hashing only. Do not construct the tokenizer, load weights, import the model, execute model code, or access targets.

### 8.4 Target-free prerequisite plan

Run `scripts/a0x_build_gate_b_runtime.py --plan` against the exact verified prerequisites. It must remain target-free and model-load-free. Record its maximum invocation count. This is distinct from `scripts/a0x_prepare_runtime.py --preflight` in Task 9.

**Reviews:** Luna performs mechanical provenance audits; Terra integrates; Sol reviews the trust boundary; Astra issues the mandatory B09 decision in every case. Repeat CR-3 additionally if a prerequisite changes the frozen package binding.

## Task 9: Execute Gate B v2 only

This task requires a separate exact Gate B authorization bound to the fresh P0 package, captured Hosted Gate A inputs, prerequisite manifests, new HEAD/tree, and an empty output namespace.

The authorization must name and cap each operation independently:

- one `scripts/a0x_build_gate_b_runtime.py --build` invocation;
- one `scripts/a0x_prepare_runtime.py --preflight` invocation;
- one production Gate B v2 preparation invocation.

Any failed, interrupted, or uncertain operation stops Gate B. A broad “Gate B authorization” does not imply retries or unspecified extra invocations.

**Required behavior:**

1. Revalidate all source and prerequisite hashes immediately before use.
2. Prove same-user mutator exclusion for the complete Gate B transaction.
3. Run the pinned Hosted Gate A verifier and produce the fifth evidence receipt.
4. Build the Python 3.11 environment with `venv --copies` and `pip --no-index` from the verified wheelhouse. Use only pinned binary wheels and the exact distribution set; no resolver, source distribution, network, fallback copy, or global package is allowed.
5. Verify every locked distribution and required API.
6. Materialize the runtime and exact snapshot with APFS copy-on-write when the contract requires it. No hardlink or symlink is accepted.
7. Validate every live file again at the final pre-model boundary.
8. Produce the canonical Gate B v2 readiness receipt, readiness descriptor, authorization document, local mapping, wrapper, and launch descriptor under the derived `.a0x-runtime/gate-b/v2/...` namespace. Bind the exact canonical profiles and paths through `scripts/a0x_material_child.py`; no legacy `.a0x-runtime/launches/...` path is accepted.
9. Do not construct the tokenizer, load model weights, read targets, or run inference.
10. Finish with explicit state `sealed_gate_pending`.
11. Luna audits hashes and schemas; Terra rechecks decisive evidence; Sol and Astra perform CR-4 review.

**Stop:** any provenance, ownership, file-type, path, API, package, source, or evidence mismatch. No retry.

## Task 10: Prepare the exact Gate C authorization packet

Terra prepares, but does not execute, a single material authorization packet containing:

- this plan version and raw SHA-256;
- exact repository, clone, HEAD, and tree;
- exact pair, model, and revision;
- P0 commitment and dossier hashes;
- four Hosted Gate A input hashes and verifier receipt hash;
- Gate B readiness and authorization hashes;
- complete runtime manifest, readiness, wrapper, launch-descriptor, and local-mapping hashes;
- exact vertical execution authorization raw SHA-256;
- selection-corpus commitment and declared target-key commitment read only from already authorized metadata, never calculated by pre-reading target bytes;
- authorization ID and attempt ID;
- exact CCP executable path, source commit/tree, and SHA-256;
- exact shell-free launcher argv and working directory;
- workload family and resource labels;
- CPU float32, local-only, network none, no generation;
- CCP child timeout 3,600 seconds;
- outer supervision ceiling 3,900 seconds, allowing the declared final sealing and cleanup margin without extending child execution;
- internal budget 3,300 seconds;
- cleanup/sealing reserve 300 seconds;
- maximum RSS 8 GiB;
- maximum new dense output 33,554,432 bytes for this frozen A0 dossier;
- exactly one sealed-target read at the analysis boundary;
- one guard maximum and no retry;
- every terminal outcome preserved; publication eligibility is verified later and publication requires separate authorization;
- exact final output paths and proof that each is absent before durable claim;
- stop boundary after terminal package and post-run checks.

Immediately before CR-5, reread the live repository `AGENTS.md`, `/Users/marco1/.codex/CCP_USAGE.md`, and the active producer documentation. The current contract says `guard exec` does **not** use `plan`, `doctor`, or `dry-run`.

CR-5 resource and admission samples are planning evidence, not a reservation. Sol reviews authorization, concurrency, one-shot timing, target boundary, recovery, publication closure, and result ownership. Astra performs CR-5. Terra then gives the operator the exact authorization paragraph and stops.

## Task 11: Execute exactly one Gate C material attempt

Only after the exact operator authorization:

Reread the live repository `AGENTS.md`, `/Users/marco1/.codex/CCP_USAGE.md`, and the active producer's applicable command-family documentation immediately before the following preflight and guard. The earlier CR-5 reading is not sufficient after an approval delay. Contract drift is evaluated before execution and never silently overridden.

1. Verify CCP executable path, complete SHA-256, and version.
2. Verify exact repository state and selected clean clone.
3. Prove same-user mutator exclusion for the complete claim-through-terminal-write-and-cleanup window.
4. Run the complete fresh ordered preflight:

```bash
rtk /Users/marco1/.cargo/bin/commit-ci-preflight --version
rtk shasum -a 256 /Users/marco1/.cargo/bin/commit-ci-preflight
rtk git status --short --branch
rtk git rev-parse HEAD
rtk /Users/marco1/.cargo/bin/commit-ci-preflight resource status --json
rtk /Users/marco1/.cargo/bin/commit-ci-preflight admission status --json
rtk docker context show
rtk docker ps -q
```

5. Compare version, binary SHA-256, complete HEAD, and clean state with the exact authorization. Proceed only with resource `admit`, admission inactive, queue empty, runtime free, and no unaccounted container.
6. Reverify the CCP binary hash immediately before the single `guard exec`.
7. Create or confirm the durable attempt claim. From this point the attempt is consumed even if no model or target is reached.
8. Execute only the reviewed shell-free argv. Do not wrap a command that re-enters CCP admission.
9. Allow the child to read the sealed targets exactly once at the analysis boundary.
10. Preserve the terminal outcome. Classify child results separately from admission denial, timeout, cancellation, outer failure, partial package, and cleanup uncertainty.
11. Do not tune, substitute, modify the protocol, repair output, or retry.
12. Run fresh post-outcome admission, Docker, and resource checks after every terminal outcome.
13. Record outer guard status separately from inner scientific outcome.

**Stop:** any drift before start, resource denial, cancellation, timeout, ownership loss, partial terminal package, cleanup uncertainty, or outer failure.

## Task 12: Verify and interpret the terminal package

This task must not reopen sealed targets, rerun the model, append to the sealed package, manufacture missing outputs, or perform new scoring.

**Steps:**

1. Invoke the canonical verification path proven in Task 4. Its implementation uses `latent_triz.a0x_verify.verify_a0x_package`, `latent_triz.a0x_report.build_terminal_package`, and the vertical production integration in `latent_triz.a0x_production_adapter`; no historical fallback is accepted.
2. Bind inputs explicitly: immutable package root, repository root, leg freeze, exact dossier, execution authorization, expected root-receipt hash, A0 and R1 protected-tree manifests/verifier, and Hosted Gate A evidence loader.
3. Verify every existing artifact, schema, source binding, evidence hash, authorization, dense locator, and dense asset SHA-256 read-only.
4. Apply frontier-dependent inventory rules:
   - preflight or activation refusal: preserve only the faithful refusal and recovery record; do not create statistical, representation, target-read, or dense artifacts;
   - positive or null child result: require the complete linked statistical result, representation index, target-read receipt, dense locator, and dense asset produced and sealed by Gate C;
   - non-interpretable, incompatible, or failed child result: require only the artifacts mandated by that terminal schema; never backfill unavailable scientific outputs;
   - admission denial, timeout, cancellation, outer failure, partial package, or cleanup uncertainty: preserve an engineering outcome and outer/inner evidence; do not call it the first scientific A0 result.
5. Verify a missing or mutated required dense asset fails closed.
6. Prove publication closure from a fresh clone using the exact public-safe P0 commitment/dossier, execution authorization, Hosted Gate A inputs, allowed receipts, terminal package, and declared external dense asset. Private runtime mappings, target bytes, and historical-batch fallback must be unnecessary.
7. Render deterministic human-readable summaries only into a separately authorized publication-staging directory. Do not modify the sealed package.
8. State only what the evidence supports:
   - this is an automated-proxy A0 decodability result;
   - it is not expert validation;
   - it is not a general TRIZ, causal, mechanistic, or training-data claim;
   - a positive result shows only that the frozen proxy signal was observed for this exact model/protocol;
   - a null or failed result remains informative about this exact pipeline.
9. Sol reviews the scientific wording and publication boundary.
10. Astra performs CR-6 over the exact terminal package.

## Task 13: Publish the terminal outcome

This task tracks separate exact permissions for branch creation, local commit, push, PR creation, merge, and external asset publication. Prepare local report drafts without creating a branch or commit; resolve each mutation against current anchors and an applicable permission before performing it. Existing matching permissions remain valid and must not be requested again.

**Steps:**

1. Perform privacy and path-leak audit. Remove no evidence; instead block publication if evidence is unsafe.
2. Ensure public files contain no secrets, local usernames, absolute local paths, raw private targets, raw logs, tokens, container IDs, or environment values.
3. Preserve separate identities for the execution source HEAD and the later documentation/result-publication HEAD. Publication changes do not retroactively invalidate historical execution evidence, and they never authorize another material run.
4. Prepare one coherent local publication diff, then place it on the publication branch once branch creation is authorized:
   - `README.md` with a concise first-result summary and evidence boundary;
   - `docs/CURRENT_STATUS.md`;
   - `docs/PERSISTENT_GOAL.txt`;
   - `docs/A0X_SIX_MODEL_CAMPAIGN.md`;
   - the scientific report and result manifest;
   - the problem/solution registry;
   - download links only for authorized public artifacts.
5. Keep historical failed attempts labeled historical.
6. Run the full hosted test suite locally target-free.
7. Resolve the permission ledger for local commit, push and PR creation using the concrete candidate. Resolve merge permission when actual PR head/base, ruleset and terminal gates are known; request only missing permissions. External asset publication has its own exact artifact scope.
8. Push non-forced, open PR, observe required GitHub-hosted gates, and merge only when exact bindings remain unchanged and every required gate is green.
9. Verify new public main and a fresh clone.
10. Confirm public package verification and fail-closed mutated-asset behavior.

**Completion:** mark `SCIENTIFIC_OBJECTIVE_COMPLETE` only for a defensible scientific result that is verified and published within scope. Publication of an engineering outcome retains `TERMINAL_ENGINEERING_STOP`; the scientific objective remains incomplete and no retry is implied.

## Task 14: Reuse the proven path

After Task 13, Terra writes a short continuation checkpoint. The default next pair is A0-R1 / SmolLM2-360M, followed by missing A0 and A0-R1 pairs one model at a time. Do not reopen campaign-wide execution until the first vertical chain has been reviewed for operational cost and failure modes.

For each new pair:

1. reuse code, never evidence or authorization IDs;
2. generate a new P0 package;
3. use separate Gate B and Gate C authorizations;
4. preserve one-shot semantics;
5. require Astra at the pair’s material authorization and result checkpoints;
6. publish only after Sol and Astra reviews.

## Completion checklist

- [ ] Current plan raw SHA-256 recorded; no previous-version review reused as current approval.
- [ ] B00 source recovered into a durable isolated checkout; source tree reverified.
- [ ] Every completed block has a Sol review and an independent Astra decision receipt.
- [ ] CR-0 design approved by Sol and Astra.
- [ ] Canonical P0 v2 CLI exists and has no legacy fallback.
- [ ] P0 atomically publishes five package members plus matching external commitment.
- [ ] Gate B v2 production CLI reaches its hardened implementation without `TypeError`.
- [ ] Real child accepts the exact vertical descriptor and rejects mutations before capability access.
- [ ] Adapter/report/verifier consume the vertical v4 evidence graph.
- [ ] Real-Git, real-CLI, target-free chain passes through terminal verification.
- [ ] Full target-free suite, schemas, docs, and deterministic regeneration pass.
- [ ] CR-1 exact candidate approved by Sol and Astra.
- [ ] Corrected source merged under exact authorization.
- [ ] Fresh attempt-1 Hosted Gate A succeeds at the corrected main.
- [ ] CR-2 approved.
- [ ] Four Hosted Gate A inputs captured and verified.
- [ ] P0 v2 package produced and CR-3 approved.
- [ ] Wheelhouse, Python, and exact model snapshot provenance verified.
- [ ] Gate B ends `sealed_gate_pending` without model or target access.
- [ ] CR-4 approved.
- [ ] Exact Gate C authorization prepared and CR-5 approved.
- [ ] Operator explicitly authorizes the one material attempt.
- [ ] One Gate C attempt reaches a preserved terminal outcome.
- [ ] Post-run admission/runtime/resource checks are recorded.
- [ ] Outer engineering failures are not labeled scientific results.
- [ ] Terminal package verifies target-free and rejects missing/mutated assets.
- [ ] Scientific report respects the evidence boundary.
- [ ] CR-6 approved.
- [ ] Publication separately authorized, gated, merged, and fresh-clone verified.
- [ ] Continuation checkpoint identifies A0-R1 as the next vertical pair.

## Persistent goal for Terra

Use this text when starting the execution task:

> Execute version 1.2 of `docs/superpowers/plans/2026-09-16-a0x-first-result-autonomous-execution.md`. Terra High orchestrates; Luna owns bounded operations; Sol reviews each block; independently delegated GPT-6 Astra analyzes the evidence and decides GO, REWORK, or EXTERNAL_GATE after every B00–B15 block. Start with B00 because the former temporary clone is absent. Preserve the dirty primary checkout. Recover exact source and work in a durable isolated clone without hardlinks. Reuse completed audits after source verification. After Astra GO, proceed immediately to the next authorized block; after REWORK, correct within scope without routine human confirmation. Reuse still-valid permissions; ask only for genuinely missing authority and only after preparing concrete evidence and all independent safe work. Preserve frozen science, one-shot limits, target boundaries and every terminal outcome. Do not invent a goal token budget. Record hashes, review receipts and attempt counts durably. Complete the objective with a verified first A0/SmolLM2 scientific result and its authorized publication. An engineering terminal stop preserves the attempt but leaves the scientific objective incomplete; never retry without authority.

## Final decision rule

Speed means minimizing failed material attempts, not skipping evidence. The first result arrives fastest when the real target-free chain is made executable once, reviewed at exact checkpoints, and then used vertically for one model. Any proposal that bypasses the canonical P0 v2 operator, vertical Gate B descriptor, real child, v4 evidence graph, or terminal verifier is `NO-GO`.
