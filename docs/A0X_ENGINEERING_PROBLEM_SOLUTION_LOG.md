# A0X engineering problem and solution log

This log records engineering failures and corrections encountered while
preparing the A0X two-leg, six-model campaign. It is deliberately separate from
the scientific results: an engineering correction does not strengthen or
weaken the Latent TRIZ hypotheses unless a valid frozen analysis later produces
evidence.

The authoritative design is
[`docs/superpowers/specs/2026-08-28-a0x-material-composition-correction-design.md`](superpowers/specs/2026-08-28-a0x-material-composition-correction-design.md).
The executable plan is
[`docs/superpowers/plans/2026-08-28-a0x-material-composition-correction.md`](superpowers/plans/2026-08-28-a0x-material-composition-correction.md).

## Status vocabulary

- **Resolved:** correction and regression evidence are complete.
- **Implementation in progress:** design is approved; offline code/tests remain.
- **External gate pending:** local implementation is ready but a new exact
  authorization or external state is required.
- **Historical evidence:** preserved outcome; never silently relabelled.

## 1. Material entrypoint remained a refusal stub

**Symptom.** The twelve fixed Make targets existed, but
`scripts/a0x_material.py` always returned a non-zero status after validating the
dossier path.

**Root cause.** Task 10 intentionally provided a fail-closed synthetic
orchestration seam, and Task 11 froze dossiers without crossing the material
boundary. A production subprocess composition was never authorized or added.

**Consequence.** Green synthetic tests proved ordering and invariants but could
not execute an actual model pair.

**Correction.** Add a fixed outer launcher, one shell-free CCP child, and a
private production composition module. Keep the existing A0/A0-R1 activation
and statistical modules unchanged.

**Regression evidence required.** Fixed-dossier-only CLI tests, authentic argv
tests, stage-order tests, one-read tests, and proof that imports/help do not
construct a tokenizer or model.

**Status.** Resolved in the offline composition; material execution remains a
separate gate.

## 2. Authorization path collided with the immutable output path

**Symptom.** Every dossier declared its future authorization below
`results/a0x/<leg>/<model>/<run-id>/`, while the runner correctly rejected any
pre-existing pair output.

**Root cause.** Synthetic tests placed authorization files outside the pair
output and therefore did not exercise the dossier-declared production path.

**Consequence.** A correctly placed real authorization would make the output
non-empty and block the run before model access.

**Correction.** Derive a Git-ignored authorization inlet below
`.a0x-runtime/authorizations/`. Embed its exact bytes in the final package so a
published result does not depend on the ephemeral inlet.

**Regression evidence required.** Reject authorizations below `results/`,
reject arbitrary inlet paths, accept only the pair-derived inlet, and verify the
package after the inlet has been removed from a disposable copy.

**Status.** Resolved in the offline composition.

## 3. `guard exec` commitment lacked a canonical argv preimage

**Symptom.** `guard_exec_argv_commitment` was a SHA-256 value without a stored,
canonical launch object. Synthetic tests compared the same opaque digest on
both sides.

**Root cause.** The original callback-shaped executor was a test seam, not a
real subprocess contract.

**Consequence.** A material launcher could not prove that the exact executable,
timeouts, resource labels, child script, descriptor, cwd, and environment were
the values approved by the operator.

**Correction.** Store a public-safe `a0x-guard-launch-v2` object and hash
canonical JSON. It binds logical executable roles, exact file hashes,
`cwd_kind: repository_root`, a fixed shell-free argv template, and a sanitized
environment template without publishing host-local paths. The ignored runtime
descriptor maps the fixed tokens to local paths. Before the durable claim and
again before the one permitted `guard exec`, verify the resolved file hashes
and prove that normalizing the resolved argv reproduces the authorized
template.

**Regression evidence required.** Mutate every argv token, role, hash, local
mapping, and environment binding individually; each mutation must fail before
the child. Absolute paths must be rejected from the public authorization.
Shell strings, pipes, redirections, managed-cache flags, inherited sensitive
environment values, and user-selectable model/target arguments must be
impossible.

**Status.** Resolved in the offline composition.

## 4. Qualification receipt was hash-bound but not independently recoverable

**Symptom.** The execution authorization named the raw qualification-receipt
hash, but the package lacked a public-safe locator and producer/source metadata
needed to obtain and validate the exact object from a fresh clone.

**Root cause.** Qualification and scientific execution were deliberately split,
but the publication linkage was not completed before Task 12.

**Consequence.** Package integrity could prove that all included documents
agreed on a hash, but not independently retrieve the qualifying receipt.

**Correction.** Add a strict qualification-evidence record binding receipt ID,
raw hash, qualified source HEAD/generation, CCP identity, evidence branch/path,
and evidence commit. Exclude raw logs and private host data.

**Regression evidence required.** Missing or mutated evidence, receipt,
producer, source, branch, path, or commit must fail closed in a disposable
fresh-clone verification.

**Status.** Resolved in the offline composition.

## 5. CCP producer and Matrix profile drift

**Symptom.** The installed CCP producer, public upstream, and the locally
reviewed `matrix-v2-legacy-v1` profile diverged across several checkpoints.

**Root cause.** CCP evolved while A0X was being frozen. A merged public
terminal-release finalizer and the legacy Matrix compatibility profile existed
on different source lines.

**Consequence.** A green plan or static test from one producer could not qualify
another producer. Old configuration/policy pairs produced mismatch or
non-terminal evidence.

**Corrections and evidence.**

- Preserve all historical producer identities and receipts without relabelling.
- Reconcile the public source and legacy profile in an isolated offline clone.
- The reconciled source is commit
  `a73ebed945d9d9e9744c4aff987589f3478a7f3c`, tree
  `b12ff9ac9daa67d52e28c6793e14f646c5e37225`.
- Its single release candidate is SHA-256
  `2f7fe3fce7d44cdd8350c0248f1c3b5b5c9fc4d023c05adcdb320d41785fa45f`.
- Offline formatting, strict Clippy, 413 tests with four documented ignores,
  doctests, independent review, and an exact plan-digest comparison passed.
- That candidate's single heavy qualification later exposed a container-only
  fixture-path defect. The failure is preserved and was not retried.
- The corrected successor is commit
  `faf587890e4f899803f027660bc66452623f405e`, tree
  `4615028176f3d594fbce0554f5e5edecfb802af1`, executable SHA-256
  `7cde4c2888721d72fbb8c86b4fdcc75f992050979c5175a5bf10b0cecfa7c6f8`.
  Its one authorized generation-1 qualification passed every required check.
  Receipt ID
  `sha256:65ff7b62fa949b549c87c1d599e76d67ebfa3edb3cc15d0cfae3972fdde236d9`
  and receipt-file SHA-256
  `12f6d8988be5dc119eaa469cd3617a0f74e3416f7f66b5155d6cf3e1c1219670`
  were independently verified by candidate and stable producers.

**Residual gate.** The corrected candidate is terminally qualified but exists
only on a local isolated branch. Durable source preservation, full branch
review, installation or exact-path selection, publication, and A0X artifact
rebinding remain separate gates.

**Status.** Qualification resolved; durable integration gate pending.

## 6. A CCP qualification ended under host resource pressure

**Symptom.** The earlier candidate qualification at commit `c91915a…` ended
`PENDING` with exit code 5 after formatting passed.

**Root cause.** The resource watchdog tripped before later checks completed.
This was not a repository-test failure.

**Consequence.** The qualification was not positive, and its one authorized run
was consumed.

**Evidence.** Preserved receipt file SHA-256
`dae63a016d6ddc2396ed1d27b01c6f6b447353f0f3b87d834b183d8720114ce8`;
receipt integrity passed while policy qualification failed as expected.

**Correction.** Do not retry or reinterpret the receipt. Reconcile the producer,
request a new exact authorization, perform fresh resource/admission/runtime
checks, and preserve every terminal outcome.

**Status.** Historical evidence.

## 7. The 1,800-second scientific timeout was too costly for a one-shot design

**Symptom.** The original material envelope allowed only 1,800 seconds. A
timeout consumes the one guard attempt even when a run is otherwise progressing.

**Evidence.** Comparable EXP-001 and EXP-002 executions completed in
approximately 312--950 seconds. No inspected receipt proves that an A0X-shaped
run itself exceeded 1,800 seconds, but A0X includes activation extraction,
serialization, analysis, packaging, and cleanup under one one-shot boundary.

**Risk.** Host variability or the larger A0 activation grid could turn a valid
run into an avoidable non-interpretable terminal result.

**Correction.** Use one uniform 3,600-second outer timeout, a 3,300-second
internal scientific budget, and a 300-second terminal/cleanup margin. Keep
admission wait separate at 300 seconds. The change is operational, not a change
to endpoints or statistics, but it invalidates old material hashes and requires
regeneration.

**Regression evidence required.** Exact timeout schema checks, rejection of
per-model overrides, monotonic deadline checks at all stage/forward seams, and
an authoritative outer-timeout recovery test.

**Status.** Resolved in the offline composition.

## 8. A model-availability audit produced a false negative

**Symptom.** One delegated audit reported that all six `artifacts/models/`
directories were empty, contradicting another audit.

**Root cause.** The audit used `rg --files`, which excludes Git-ignored files by
default. Model snapshots are deliberately ignored.

**Correction and evidence.** Direct filesystem inspection from the repository
root found all six directories and weight files, totalling approximately
4.1 GiB. The expected declared aggregate runtime bytes are 4,283,111,958.

**Regression lesson.** Never infer absence of ignored runtime assets from Git-
aware file enumeration. Use exact declared paths, `stat`, byte counts, and
allowlisted SHA-256 verification without loading model content.

**Status.** Resolved.

## 9. Model-family documentation and adapter mismatches caused earlier failures

**Symptom.** Earlier SmolLM2 attempts failed first at tokenizer handling and
then at hidden-state shape assumptions.

**Root cause.** Generic Transformers assumptions were applied before the exact
model-family configuration, tokenizer mapping, tuple convention, and tensor
shape were fully bound and tested.

**Correction.** A0X model cards now bind exact architecture, model type,
tokenizer class, layer count, hidden width, context, final-block tuple index,
runtime file inventory, and official-source provenance. The common adapter
checks fast offsets, CPU float32 parameters, embedding-plus-block hidden-state
count, and finite shapes.

**Regression evidence required for A0X.** Production composition must call only
the common card-bound adapter and reject any revision, tokenizer, architecture,
device, dtype, tuple, or context mismatch before target access.

**Status.** Resolved with card-bound synthetic production-composition tests;
material construction remains unauthorized.

## 10. Receipt ID and receipt-file SHA-256 were conflated

**Symptom.** One commitment could be interpreted as either CCP's canonical
semantic receipt ID or the SHA-256 of the complete receipt file.

**Risk.** A verifier might accept a semantically similar envelope when the
operator authorization actually bound exact bytes, or reject valid exact bytes
because the two hashes serve different domains.

**Correction.** Qualification evidence now carries and verifies both values:
the semantic receipt ID is recomputed from the canonical receipt object, while
the raw-file SHA-256 is recomputed over the injected complete bytes. Neither
may substitute for the other.

**Status.** Resolved.

## 11. Public artifacts exposed host-local execution details

**Symptom.** Earlier CCP observations included absolute executable, repository,
and cache paths and could retain raw argv or status data.

**Correction.** Public contracts now use roles, repository-relative locators,
hashes, and redacted state. Private runtime resolution supplies local paths
only at the authorized boundary. The package verifier recursively rejects host
paths, file URIs, raw argv, environment, usernames, container IDs, and raw-log
fields.

**Status.** Resolved.

## 12. A dossier could not safely bind its own future source commit

**Symptom.** Embedding the final future commit in a dossier creates an
impossible self-reference: committing the dossier changes the commit.

**Correction.** Dossiers bind an `implementation_source_head` containing the
reviewed implementation. A later execution authorization separately binds the
exact live `source_head`. The current implementation anchor is
`9aeb6ef664b0576cb8a1ed58f50791be3bb070cb`.

**Status.** Resolved.

## 13. Target-read and clock evidence admitted ambiguous states

**Symptom.** Synthetic seams could provide non-finite, Boolean, or backward
clock samples, and target-read outcomes lacked one legitimate selection-
mismatch status.

**Correction.** Stage timing uses finite non-Boolean monotonic samples and
integer nanosecond evidence. The one-shot reader owns immutable read evidence,
and target outcomes distinguish zero-read, exact one-read, and
`selection_mismatch` without reopening the target.

**Status.** Resolved.

## 14. Repository `run` and scientific `guard exec` were mixed

**Symptom.** Documentation and fixtures risked requiring `plan`, `doctor`, and
`dry-run` immediately before a scientific guard.

**Correction.** Repository qualification remains a separate configuration-
backed Matrix `run`. Material science uses `guard exec`, whose fresh preflight
has six configuration-free roles: CCP version, resource status, admission
status, Git source state, runtime context, and active-container count.

**Status.** Resolved.

## 15. Pair runtime paths could collide

**Symptom.** Mutable authorization, launch, claim, and observation paths were
not all proven to be unique across twelve leg/model pairs and a live source
HEAD.

**Correction.** Every private path is derived from leg, model key, run ID and,
where needed, exact source HEAD. Twelve-way collision and cross-pair mutation
tests fail closed.

**Status.** Resolved.

## 16. Child and preflight output capture could grow without bound

**Symptom.** A subprocess could emit more output than the public evidence
surface should retain, or a preflight probe could hang.

**Correction.** Material output is drained continuously while retaining only a
64-KiB prefix plus full-stream hash and byte count. Each preflight probe has a
30-second timeout and 64-KiB ceiling; timeout, excess output, or drain failure
is terminally rejected.

**Status.** Resolved.

## 17. Preflight could become stale between observation and claim

**Symptom.** A status sample is not a reservation. Source, admission, resource,
or runtime state can change before the one-shot claim.

**Correction.** The pair-derived public preflight observation is written before
the claim and its raw SHA-256 is chained into the claim and private pre-run
record. Executable and child hashes are checked again immediately before the
single guard launch. Post-claim drift produces durable recovery evidence and
does not start the child.

**Status.** Resolved.

## 18. The external supervisor could race CCP cleanup

**Symptom.** If the private caller stopped waiting at exactly 3,600 seconds, it
could pre-empt CCP while CCP was sealing or releasing resources.

**Correction.** CCP's authoritative child timeout remains 3,600 seconds. The
private supervisor may wait 3,900 seconds only to observe CCP's terminal result
and final cleanup. This is not additional scientific runtime and cannot rescue
an internal 3,300-second deadline.

**Status.** Resolved.

## 19. Matrix tests wrote fixtures below a read-only container root

**Symptom.** The first exact qualification of the reconciled CCP candidate
passed formatting but failed two Matrix tests with filesystem errors. The same
suite had passed on the writable macOS host.

**Root cause.** Two tests derived their temporary fixture directory from the
process working-directory parent. Under the read-only `/workspace` repository
mount this resolved to `/`, so the tests attempted to create directories at the
container root. The production Matrix implementation was not the failing path.

**Consequence.** The authorized `a73ebed…` qualification ended FAIL and its
single attempt was consumed. Static host evidence could not qualify the
container execution contract.

**Correction.** Add a test-only root resolver that honors the fixed
`CCP_TEST_ROOT` runtime binding, use it only for the two affected fixtures, and
keep the repository source mount read-only. The Matrix plan now supplies
`CCP_TEST_ROOT=/workspace/.ccp-mounts/test-work`, backed by the dedicated
writable CCP cache binding.

**Regression evidence.** The new helper test failed before implementation and
passed after it. The corrected source completed all static gates and then one
exact Matrix qualification: formatting, all-target/all-feature tests, strict
Clippy, documentation, and release metadata all passed. Candidate and stable
verification accepted the same terminal receipt.

**Status.** Resolved in qualified commit `faf587890e4f899803f027660bc66452623f405e`.
The exact source and receipt are durably published on dedicated branches;
at this historical checkpoint CCP PR #70 remained a draft and the candidate
was not installed. Issue 21 records the later producer and merge state.

## 20. No-model import tests depended on repository-suite order

**Symptom.** The isolated A0X aggregate passed, but the repository-wide suite
reported failures in no-model import assertions after earlier tests had
legitimately imported `torch` into the shared Python process.

**Root cause.** The assertions inspected the global `sys.modules` state rather
than the import delta caused by the entry point under test. They therefore
tested suite history, not entry-point behavior.

**Consequence.** Repository qualification would fail even though the A0X
entry points did not import a model library. The frozen implementation hashes
also correctly detected each test-file correction and required regeneration.

**Correction.** Entry-point import/help probes now execute in clean
subprocesses. Adapter tests that require injected in-process fixtures compare
the model-library module state before and after the operation. The final
implementation anchor was regenerated twice in independent no-hardlink clones
and once in the active checkout; all three artifact trees were byte-identical.

**Regression evidence.** The targeted tests passed, the A0X aggregate passed
246 tests, the frozen package passed 10/10, and the repository-wide suite
passed 1,073 tests with one documented skip.

**Status.** Resolved at implementation anchor
`7983e4ab5587f3f2c241ddb88e81219ffcf2a6e9`.

## 21. CCP source snapshots rejected a required tracked blob above 1 MiB

**Symptom.** The later CCP candidate could not faithfully stage the complete
Latent-TRIZ source snapshot because a required tracked repository blob exceeded
the producer's 1 MiB per-blob ceiling.

**Root cause.** The ceiling was suitable as a defensive default for small
source trees but was too low for this repository's legitimate tracked fixture.
Bypassing the file, changing the A0X source set, or weakening snapshot integrity
would have changed the qualification subject.

**Consequence.** The earlier `faf587…` producer remained valid historical
evidence, but it could not be the final producer for an exact complete A0X
qualification. No Latent-TRIZ heavy retry was attempted.

**Correction.** CCP raised the bounded tracked-blob ceiling to 64 MiB with TDD
coverage while retaining total-snapshot bounds and fail-closed behavior. Exact
source `27adf8d0820b3cd96f9c5e149de9b580ae41f639`, tree
`d8e0364d1313fde0898a44517ae6d233d9e10763`, executable SHA-256
`c8021e2322e172686c0a0c07d2b0260eafb5812d085d2306dbbde3fe4e964bd4`
then passed one authorized generation-1 Matrix qualification. The receipt-file
SHA-256 is
`14df36450ce982b0c5233651baa4c5f5d0e0c462b1b5f119ec8f93a9ad7465ce`.

**Publication and selection evidence.** The candidate and receipt are preserved
byte-identically under hash-bound paths. CCP PR #70 passed its GitHub gates and
was squash-merged as `1a2e081cd3912b0fd63a7226a4564f1d85a51eb8`;
the merge tree is exactly the qualified tree. A0X binds the qualified source,
tree, executable, and receipt directly. The installed stable executable was not
replaced.

**A0X regression evidence.** Implementation anchor
`9aeb6ef664b0576cb8a1ed58f50791be3bb070cb`, tree
`5f11c2323b2657ed202ffa0bd1918037313568ce`, regenerated both freezes and all
twelve dossiers without material access. Frozen verification passed 10/10, the
A0X aggregate passed 246 tests with three documented optional-NumPy skips,
schema cross-validation reported 155 agreements and 19 rejected mutations, and
the repository suite passed 1,073 tests with one documented skip.

**Status.** Resolved for offline A0X preparation. A fresh exact-head
Latent-TRIZ CCP qualification remains a separate authorization gate.

## 22. Repository qualification timed out and used the wrong Matrix profile

**Symptom.** The single authorized exact-head qualification of
`32e03b5ef34bb1d8f778877514601994df9c3898` ended terminal `FAIL`. Both schema
checks passed in about two seconds, while the Python 3.11 and 3.12 repository
checks were each terminated at approximately 300 seconds. Receipt ID:
`sha256:bbe9173bfe489e34071f71ce6822df26126f1026d939e1693245fd47daa864d9`;
receipt-file SHA-256:
`63a920e8cd97310a857be8465924311389edeb61746945c9219f4c85e2500e01`.

**Verification distinction.** The first verification command supplied the
legacy V1 policy and rejected the Matrix V2 receipt shape. That was an operator
invocation error, not a receipt-integrity defect. Repeating only the read-only
verification with `.commit-ci-policy-v2.toml` established
`integrity_status: PASS` and `policy_status: FAIL`.

**Root causes.** First, both repository checks inherited a 300-second timeout,
which was not enough for the complete suite in the one-CPU qualification
containers. Second, the authorization and Make targets did not explicitly
select `matrix-v2-legacy-v1`, so CCP used its default `current-v2` plan while
the frozen contract and policy expected the legacy plan. The resulting runtime
digests correctly failed policy qualification.

**Consequence.** The attempt is consumed and remains negative engineering
evidence. It does not qualify the source and does not authorize a retry or any
scientific execution. Passing schema checks do not override the outer terminal
failure.

**Correction.** TDD at anchor
`9ce4dc1e342d68bdef0dd5f63c198270a9d6d3cd`, tree
`23ea89e42bdb1dae71bfa9d23fb858a904f82beb`, sets the two repository checks to
3,600 seconds, keeps both schema checks at 300 seconds, adds the explicit
legacy-profile argument to all four repository-qualification operator targets,
and binds receipt verification to the V2 policy. The real qualified producer
then rendered outer digest
`sha256:8eb0172c30aac8f9b47f65cebd222ee6615b17e4053a5a16e2be5583f3a10331`,
Python 3.11
`sha256:aa69a8795e20733a516fac99b253cfc26a9f963825ff1fa9ca5638364f7fc943`,
and Python 3.12
`sha256:072e50972a02f2df710bf81620ca058d230f0637bcc16a47ba35562fe1358510`.
The exact plan stdout SHA-256 is
`0969a1eeb62b2a92593cda0b75c8814d7eca893bebc736ec968f02aa9f2a5fad`.

**Regression evidence.** The four focused requirements failed before the
implementation and passed afterward. Related runner, preflight, material-
contract, and schema tests passed 64/64. Contract, both freezes, and all twelve
dossiers were regenerated with zero model loads, material tokenizer
constructions, target reads, CCP invocations, or remote mutations.

**Status.** Offline correction implemented. Fresh no-material verification
passed, and independent review returned `APPROVE` with no P0--P3 findings. The
final local package commit remains pending. A new
exact-head qualification requires a new authorization; no retry is implied.

## 23. Matrix binding test depended on absent runtime `make`

**Symptom.** The one authorized exact-head qualification of
`fb9484a89549fbbbfc5395932954b2d9565d91d6`, tree
`f0585981d136659df4fec39e8b26aaaf2fab02a3`, ended terminal `FAIL`. Both
schema checks passed. Both repository checks returned exit 1 without timeout
or cancellation: Python 3.11 after 295,816 ms and Python 3.12 after 195,160 ms.
Receipt ID:
`sha256:f5348d82568ba98c6003132534b3a202631f04c42972b965251adaa2ca367dde`;
receipt-file SHA-256:
`5bb2e49da31381e4c22858556e4c54f373ee69dfcea8f578e050efb6268e4232`.

**Evidence distinction.** Correct V2 verification reported integrity `PASS`
and policy `FAIL`. The same clean source passed all 1,075 repository tests in
the host environment. Running only the Matrix binding module with a `PATH`
that excluded `make` reproduced five `FileNotFoundError: 'make'` errors. Image
history showed that both verification images install `make` while compiling
Python and remove it during final `apt-get purge --auto-remove` cleanup.

**Root cause.** The test used `subprocess.run(["make", "-n", target])` as a
Makefile parser. This added an undeclared test-runtime dependency even though
the repository check itself is Python-based and the production Matrix contract
does not require `make` inside the verification container.

**Correction.** TDD anchor
`6b8c8e3491b24fa4717b2f4faa8700b007c48892`, tree
`18b8fdaf9ba00a81e3c90686a2563a23f2436824`, replaces all five subprocesses
with dependency-free Python inspection. The verifier requires exactly one
target definition and an exact non-empty recipe for `preflight-plan`,
`preflight-doctor`, `preflight-dry-run`, `preflight-run`, and
`preflight-verify`. Exact legacy-profile, V2-policy, generation, receipt, and
expected-commit arguments remain bound.

**TDD evidence.** The module first failed with five missing-`make` errors under
the lean `PATH`; after correction, the same no-`make` invocation passed all
three tests. Regeneration produced two freezes and twelve
`approval_requested` dossiers with zero CCP invocations, model loads, material
tokenizer constructions, target reads, or remote mutations.

**Status.** The qualification attempt is consumed and remains historical
negative engineering evidence. Fresh verification passed the no-`make`
regression 3/3, frozen package 10/10, A0X aggregate 248/248, schema
cross-validation 155 agreements with 19 rejected mutations, repository suite
1,075 tests with one documented skip, documentation audit, and diff check.
Independent Luna review returned `APPROVE` with no P0--P3 findings. The later
exact-head qualification of `4aee4698f5c59101b1f3292519f10ae802629bf7` passed;
its receipt is historical after the final base integration described below.

## 24. Source-snapshot CI confused tracked bindings with external dense assets

**Symptom.** A prior exact-head qualification mounted only the committed source
snapshot, while a positive EXP-002 publication test called the full verifier
and required seven intentionally ignored dense assets.

**Root cause.** The test conflated two valid but distinct claims: that tracked
package bindings and declared locators are internally consistent, and that the
external dense bytes exist and match their hashes.

**Consequence.** The source-snapshot repository check failed before it could
test the A0X candidate, even though the production verifier correctly rejected
missing or mutated dense assets.

**Correction.** Retain the full fail-closed verifier for publication evidence.
Add a separate `bindings_only` verification surface for committed schemas,
package bindings, and safe asset declarations. The positive full-verification
test materializes deterministic synthetic assets; negative tests retain both
missing-asset and one-byte-mutation rejection.

**Regression evidence.** The integrated test module must pass all four cases:
tracked bindings only, complete synthetic assets, missing or mutated assets,
and a mutated package binding.

**Status.** Resolved in the final integration candidate; final no-material
repository verification remains pending.

## 25. A candidate policy cannot authorize its own legacy-profile receipt

**Symptom.** PR #105's local receipt was integrity-valid but the hosted gate
rejected it when the trusted public base still accepted the preceding Matrix
plan digests.

**Root cause.** The GitHub verifier intentionally reads the policy from the PR
base, not from untrusted candidate code. The `matrix-v2-legacy-v1` profile
changes the receipt's outer and per-runtime digest commitments, so the new
candidate policy cannot authorize that new receipt before it is merged.

**Consequence.** A local PASS on `4aee4698f5c59101b1f3292519f10ae802629bf7`
could not satisfy the old hosted trusted-base policy. Treating that policy
rejection as a repository-test failure would be incorrect.

**Correction.** Merge the policy-only prerequisite PR #106 first. Public
`main@4ba3c36a0f6b7a50d34bc87bb34bafc79687eb08` now accepts the exact legacy
profile digests while preserving checks, images, platforms, and freshness.

**Regression evidence.** The policy-migration tests prove that the trusted
base reads only its policy, the candidate does not self-authorize, and the
selected legacy plan equals the preceding trusted digest map.

**Status.** Resolved on public main. A source-head change still requires a new
receipt; historical receipts are never relabelled.

## 26. Final base integration invalidates an old receipt without changing science

**Symptom.** Integrating public main into PR #105 creates a new source commit,
even when the policy blob already matches and only non-A0X conflicts require
resolution.

**Root cause.** CCP receipts attest one exact commit. The receipt for
`4aee4698f5c59101b1f3292519f10ae802629bf7` cannot be reused for the integrated
commit. Conversely, an arbitrary A0X freeze regeneration would alter frozen
scientific commitments without a corresponding scientific change.

**Consequence.** The integration needs one fresh exact-head qualification, but
does not justify a model retry, sealed-target read, protocol change, or dossier
regeneration.

**Correction.** Use a normal feature-branch merge, preserve the migrated policy
blob byte-for-byte, combine the two independent EXP-002 verification surfaces,
and compare the complete A0X protected path set against `4aee4698...` before
requesting the new qualification.

**Regression evidence.** The final no-material verification must show zero
protected-path differences, a clean checkout, passing A0X and repository
suites, schema cross-validation, documentation audit, and the expected policy,
plan, and producer bindings.

**Integration namespace correction.** Public `main` also introduced an
operational CCP-policy test named `test_a0x_policy_migration.py`. The A0X
no-model verifier reserves the `test_a0x_*.py` namespace for its frozen
synthetic aggregate, so the operational test was discovered after the merge
but was correctly absent from the frozen implementation inventory. Sol review
classified this as a cross-branch namespace collision, not scientific drift.
The test is therefore byte-preservingly renamed
`test_ccp_a0x_policy_migration.py`; the Makefile aggregate, A0X runner,
implementation manifests, freezes, dossiers, and all protected artifacts stay
unchanged.

**Status.** Implementation in progress. Stop before CCP until the final
integrated commit, tree, and verification ledger are recorded.

## 27. Private runtime binding was cyclic and a frozen mismatch was misattributed

**Symptom.** The original private descriptor required a future authorization
binding while the authorization required the descriptor's raw SHA-256. No
single descriptor/authorization pair could satisfy both commitments. The
initial Task-3 narrative also attributed the resulting stale frozen inventory
to `tests/test_a0x_runtime_bundle.py`.

**Root cause.** The private descriptor was treated as an equal hash peer of the
operator authorization rather than as a dependent document. The stale-inventory
diagnosis relied on an outdated report instead of the live implementation
bindings.

**Correction.** Descriptor-v2 has a path-only pair-derived authorization
reference and a byte-bound material-contract reference. The authorization is
the operator-rooted document that binds exact descriptor bytes; the local role
mapping repeats that descriptor path/hash. The target-free preparer constructs
the descriptor, authorization, and mapping in that order and refuses every
overwrite. Live evidence identifies the stale file as
`scripts/a0x_material_child.py` (21,582 bytes, SHA-256
`fda405fbe6a3000f7de9b597aeea23300b5ecb107394411bddd21c3d3ba93955`), not
`tests/test_a0x_runtime_bundle.py`.

**Regression evidence.** Both leg implementation inventories bind the preparer
CLI, module, and test. A deterministic test regenerates every protocol,
implementation, freeze, and dossier from the committed implementation anchor
and byte-compares them with the tracked package. No test loads a model or
tokenizer, reads a target, invokes CCP/Docker, or uses the network.

**Status.** Resolved locally only after the two frozen legs and twelve
approval-request dossiers are regenerated from the exact post-inventory HEAD.
That new source HEAD invalidates every earlier exact-head qualification for
future material action; the campaign remains `sealed_gate_pending` and stops
before **A**, the first of three explicit operator stops: **A** exact-head
repository qualification authorization, **B** separate exact pair/attempt
runtime-bundle-preparation authorization, and **C** later one-shot material
authorization bound to the prepared authorization raw SHA-256.

## Current stop boundary

The final integration candidate must first complete all no-material gates and
the protected-path comparison against `4aee4698f5c59101b1f3292519f10ae802629bf7`.
It must then stop for a new Latent-TRIZ exact-head qualification authorization
bound to the final commit, selected producer, `matrix-v2-legacy-v1`, and the
three reviewed plan digests.

That stop is **A** only. A completed **A** still requires **B**, a separate
exact pair/attempt authorization to prepare one private runtime bundle. A
prepared bundle still requires **C**, a later one-shot material authorization
bound to its prepared authorization raw SHA-256. Current work remains before
**A** and `sealed_gate_pending`; none of these documents authorizes a later
stop.

It does **not** authorize CCP heavy execution, Docker, model/tokenizer
construction, protected-target access, installation, Latent-TRIZ publication,
merge, or scientific retry. The separately authorized CCP source/evidence
publication ended with merged PR #70 and grants no further CCP mutation.
