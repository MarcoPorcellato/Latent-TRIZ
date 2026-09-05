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

## 0. Gate B builder rejected repository model-card newline convention

**Symptom.** The target-free Gate B `--plan` refused the exact SmolLM2 source
before writing because the tracked model card ended with one `LF`, while the
builder compared raw bytes only with canonical JSON without a final line feed.

**Correction.** The model-card boundary now accepts the versioned A0X field
order with compact UTF-8 bytes or those bytes plus one final `LF`, while
retaining the raw-byte SHA-256. Unknown/reordered fields, additional line
feeds, trailing spaces, invalid UTF-8, and hash drift remain refusals. Synthetic
tests cover the accepted order and single-LF form plus rejected variants.

**Evidence.** Builder tests: 25/25 pass. The exact real card remains byte
unchanged and is still bound by its original SHA-256. The fresh target-free
`--plan` now passes with the explicit field-order contract.

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
exact live `source_head`. The implementation anchor recorded at that checkpoint was
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
readiness, descriptor, authorization, and mapping in that order and refuses every
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

## 28. Synthetic executable fixtures depended on the container temp mount

**Symptom.** The one authorized exact-head qualification of `e340e142...`
completed both schema checks but both repository checks returned exit code 1.
The authorized Python 3.11 diagnostic reproduced the failure without timeout:
1,099 tests ran in 195.295 seconds, with 24 errors and one failure.

**Root cause.** `scripts/repository_check.py` selected `/dev/shm` after proving
only that it was writable. The A0X runtime-bundle fixture then created inert
synthetic CCP and Python files there, set mode `0700`, and passed them through
the production `os.access(..., os.X_OK)` validation. The verification
container's temporary mount did not grant executable access, so every test
that depended on the shared constructible fixture failed at the same boundary.
The final CLI assertion observed only the derived exit code. This was a test
fixture portability defect, not a timeout, schema, model, target, or scientific
protocol failure.

**Correction.** Keep the production executable check unchanged and fail-closed.
The synthetic fixture now scopes a test-only access seam to its two exact inert
files while delegating every other access decision to the real operating-system
probe. The fixture still writes private mutable copies, so tamper tests remain
independent and cannot alter a real interpreter or CCP executable.

**Regression evidence required.** A test must first force the operating-system
access probe to deny execution for the temporary mount, then prove that the
synthetic bundle is prepared. The complete runtime-bundle, CCP-executor,
material-child, and production-adapter surfaces must remain green. A new
exact-head CCP qualification is still required; the consumed receipt and its
failed checks are historical evidence and cannot be relabelled.

**Status.** Resolved locally with TDD at implementation anchor
`d4845f0a7b204ba65b9669c05a677fc0560ababd`. Canonical regeneration completed
with two frozen legs, twelve dossiers, and zero material or remote access. The
full repository check passed 1,100 tests with 11 documented skips. Commit the
regenerated package, then request a new exact-head Gate A qualification.

## 29. Gate A did not prove pair-specific Python and snapshot readiness

**Symptom.** Gate A passed at `68f8bfe...`, but the pre-Gate-B inventory showed
that the available Python path was a virtual-environment symlink which the
existing external-file normalizer resolved to the Homebrew base interpreter.
That base interpreter did not expose the five pinned packages. The isolated
clone also had no `artifacts/models/` snapshot for the selected pair.

**Root cause.** Repository qualification proved source and verification
images, while runtime-bundle preparation bound executable bytes but not
virtual-environment identity, package/API compatibility, or pair-specific
snapshot presence. These are separate evidence layers and Gate A cannot imply
Gate B readiness.

**Correction.** Add an immutable private `a0x-runtime-readiness-v1` receipt as
the first node in the runtime chain. It requires an independent regular Python
3.11 executable inside a non-base environment; exact versions of torch,
Transformers, tokenizers, NumPy, and safetensors; required API symbols; and the
exact pair's source/card/allowlist/file commitments. Symlinked or hardlinked
Python/model files, missing assets, package drift, API drift, and pair drift
fail before bundle creation. Descriptor, material child, production adapter,
and outer launcher all validate the binding before an attempt can start.

**Regression evidence.** Synthetic tests cover a valid binding and reject
symlink/base Python, missing or altered model files, hardlinks, package/API
drift, wrong pairs, receipt/hash drift, and overwrite attempts. The readiness
probe never constructs a tokenizer/model or reads a target.

**Status.** Corrected locally; both implementation inventories, freezes, and
twelve dossiers must be regenerated and a new Gate A qualification requested.

## 30. Padding and post-claim observation persistence were incomplete

**Symptom.** A non-null model-card padding direction was recorded but not
enforced, and a filesystem failure while writing the pre-run observation
occurred after the one-shot claim but outside the terminal recovery block.

**Root cause.** The adapter verified tokenizer type/offset behavior without
comparing `padding_side`, while the launcher assumed its first post-claim write
could not fail.

**Correction.** Refuse a declared padding-side mismatch before model factory
construction. Move the pre-run observation write into the post-claim guarded
section; if it fails, retain the claim, start no child, and persist the first
possible terminal `launcher_internal_error` recovery observation.

**Regression evidence.** The GPT-Neo synthetic card rejects left padding
before model construction. An injected observation-write `OSError` produces no
process call, preserves the claim, and records terminal recovery evidence.

**Status.** Corrected locally; no material attempt was consumed.

## 31. Independent-file readiness was not revalidated at launch

**Symptom.** The readiness builder rejected symlinked or hardlinked Python and
snapshot files, but later material boundaries compared paths and SHA-256 values
without rechecking regular-file type and link count. A file could therefore be
replaced after readiness with a same-byte hardlink and retain its hash.

**Root cause.** Independent-file identity was treated as a build-time property
rather than a live precondition at every boundary that could start material
work.

**Correction.** Add one shared live-readiness validator and call it from the
outer executor, material child, and production adapter. It reopens and validates
the readiness receipt, Python executable, card, source receipts, snapshot
allowlist, every runtime file, and the complete model binding. Python and model
files must be regular, non-symlink, single-link objects with unchanged bytes;
the executable must also retain execute mode bits.

**Regression evidence.** After creating a valid readiness receipt, synthetic
tests replace Python with a hardlink, one model file with a hardlink, and Python
with a symlink. Every mutation is rejected before any model, tokenizer, target,
CCP, Docker, or network action.

**Status.** Corrected with TDD at implementation anchor
`7e1afaba83def501a2641a036c10aae1b98be7b0`. The shared validation now also
runs immediately before model construction, and the general snapshot verifier
rejects hardlinks. Final target-free verification passed (frozen 11/11,
synthetic 278/278, schema 155/19, repository 1,110 with one documented skip).
Final independent security, freeze/package, and documentation reviews returned
`APPROVE`; no P0--P3 blocker remains before the regenerated package commit.

## 32. Gate B validation occurred only in the writing command

**Symptom.** The first runtime preparation refusal was discovered only when the
operator invoked the output-producing command. Its public refusal was
intentionally minimal, so the source-derived qualification-receipt path
mismatch was not distinguishable from other preparation failures.

**Root cause.** The preparer combined validation, in-memory document
construction and exclusive writes. It had no no-write rehearsal surface and
no opt-in stable diagnostic code. This made a predictable binding error consume
operator time even though no material resource had been accessed.

**Correction.** Extract one shared validation/construction phase and expose it
through `preflight_runtime_bundle` and `scripts/a0x_prepare_runtime.py
--preflight`. It constructs the exact readiness, descriptor, authorization and
mapping bytes in memory, reports their hashes and writes no runtime output.
Preflight refusals carry stable codes and safe messages; the existing writing
mode preserves its byte-compatible minimal refusal response.

**Regression evidence.** Synthetic tests prove deterministic repeated output,
absence of all four runtime documents, non-reachability of the writer and the
exact receipt-path diagnostic. Existing prepare success and legacy refusal
tests remain unchanged.

**Status.** Corrected with TDD in an isolated process-hardening clone. It does
not modify the completed Gate B bundle and requires new exact-head Gate A
qualification before future operational use.

## 33. Copy-on-write and offline rebuildability were assertions, not tools

**Symptom.** An earlier Gate B action used a copied environment and snapshot,
but copy-on-write could not be proven retroactively and local package caches did
not contain a demonstrably complete exact wheelhouse.

**Root cause.** The repository validated the final interpreter and runtime
files but had no narrow Darwin `clonefile(2)` boundary and no canonical
offline-wheelhouse verifier. Host copying behavior and package availability
were therefore external assumptions.

**Correction.** Add two independent target-free modules. The APFS helper has
no full-copy fallback and verifies unchanged source plus exact independent
destination bytes after `clonefile(2)`. The wheelhouse verifier binds Python
3.11, accepted tags and every wheel's normalized name, version, filename,
size and SHA-256; it rejects aliases, missing/extra files and drift without
invoking `pip` or network APIs.

The APFS boundary requires explicit trusted source and destination roots,
rejects every caller-controlled symlink component below them, and cleans up
only the same regular inode it just created when post-clone verification
fails.

**Regression evidence.** Synthetic tests cover valid operation and reject
unsupported platforms, aliasing, collision, post-clone drift, noncanonical
manifests, missing/extra/changed wheels, duplicate distributions, tag/version
mismatch and the wrong Python contract.

**Status.** Corrected with TDD as preparatory infrastructure. No complete
offline wheelhouse is currently proven, so the verifier does not promote the
historical copied environment to reproducible-build evidence.

## 34. Hosted repository lanes omitted the pinned schema oracle

**Symptom.** The first hosted qualification of the reconstructed A0X branch
passed trusted classification and scientific audit but both repository lanes
failed during test discovery. Python 3.11 reported the failure after 6 minutes
12 seconds and Python 3.12 after 8 minutes 32 seconds. Every terminal import
error was `ModuleNotFoundError: No module named 'jsonschema'`.

**Root cause.** PR #108 restored the hosted Python lanes but invoked
`scripts/repository_check.py` in a pristine `setup-python` environment without
installing `requirements-schema.lock`. Local verification had that pinned
oracle already installed, hiding the clean-runner dependency. The canonical
schema reference already required protected CI to install the pinned set.

**Correction.** Both hosted repository lanes install exactly
`requirements-schema.lock` before invoking the unchanged repository check. A
workflow contract test requires two exact install steps, one per runtime.

**Regression evidence.** The new assertion failed 0-versus-2 against the
published workflow before the correction and passes after the two minimal
steps are added. The full local target-free suite is rerun before updating the
PR; GitHub must still prove both clean hosted environments on the new exact
head.

**Status.** The correction was merged to public `main`
`d2a475f58db668a2ce0a4ec48082189422b19eab` through PR #110. Because the
pre-fix hosted workflow could not qualify its own missing dependency, that PR
used one explicitly authorized CCP-backed administrative bootstrap bridge. It
was not a hosted PASS. PR #109 then integrated the new main without history
rewrite at ancestry commit `7ac5a6065d78974f52a86816b019184f8f147bd7`;
fresh hosted verification on the reconstructed exact head is still required.
No model, tokenizer, target, Gate B/C, or scientific execution was used.

## Current stop boundary

The current integration branch must pass both clean hosted Python environments,
the scientific audit, and `merge-policy/gate` on one unchanged exact head.
Merge remains a separate external gate; after merge, a fresh clone must repeat
the target-free verification.

That hosted qualification is repository publication evidence only. The A0X
campaign remains `sealed_gate_pending`; Gate B bundle preparation and Gate C
material execution each still require their own later exact authorization. No
model, tokenizer, protected target, scientific retry, or claim promotion is
authorized here.

## 35. Hosted-attestation adapter required a frozen result-shape boundary

**Problem.** Offline Gate B bound GitHub CLI bytes, version, flags, and
high-level result semantics, but lacked an exact parser contract for
`gh attestation verify --format json`. Permissive parsing would turn future CLI
or sigstore-go output drift into a silent authorization change.

**Correction.** Add a synthetic-only adapter schema and inert fixture for
GitHub CLI `2.97.0` with `sigstore-go 1.2.2`. The frozen result media type is
`application/vnd.dev.sigstore.verificationresult+json;version=0.1`; its
certificate summary carries flat lower-camel extension fields, while
`verifiedIdentity` carries the version-pinned nested matcher serialization:
the literal GitHub CLI SAN prefix matcher and fixed issuer matcher are compared
as data and are never evaluated as supplied regular expressions.
The pure verifier binds the GitHub Actions workflow build type, workflow object,
single source dependency, repository IDs, push/github-hosted internal
parameters, invocation URL, certificate SAN/issuer, timestamps, and separate
`job_workflow_sha`/`source_sha` fields. For the current non-reusable same-repo
contract both fields must independently equal `source_head`; their command-line
flags remain distinct. Predicate evidence is workflow-controlled consistency
evidence, not a trust anchor.

It independently binds raw workflow SHA-256 from the canonical manifest,
rehashes authorization, policy, workflow, executable, and all four inputs after
the one injected runner, and writes a single fsynced receipt through a checked
trusted-root directory descriptors with component `mkdirat`/`openat`, then
`O_EXCL` and `O_NOFOLLOW` on the receipt leaf. Control,
input, and output paths reject traversal and caller-controlled ancestors. The
operational wrapper supplies only a fixed locale/path environment to both the
verifier and absolute `/usr/bin/git`; it never passes inherited GitHub tokens,
authentication, or proxy variables. Verifier stdout/stderr are each capped at
1 MiB before parse or receipt handling; the wrapper bounds verification to 300
seconds and each local Git probe to 30 seconds.

**Regression evidence.** Synthetic tests reject malformed, unknown, duplicate,
extra, missing, and wrong signed fields; independently wrong signer/source
revisions; nonzero or malformed runner output; source drift; pre/post control,
workflow, and input hash drift; traversal; symlink; hardlink; nonregular;
oversize; output collision; and rerun. Each refusal writes no new receipt and
reaches no readiness, descriptor, authorization, or mapping stage.

**Status.** The pure verifier, schema, fixture, mutation suite, and shell-free
wrapper are local only. The wrapper has injected runner and source-state seams;
its focused test reaches neither seam on an invalid packet. No network, GitHub
API, GitHub CLI verification, Gate B preparation, Gate C action, model,
tokenizer, target, Docker, CCP, or scientific execution occurred.

## 36. Post-verification rehash initially omitted ancestor revalidation

**Problem.** The verifier rehashed each hosted input and the workflow after the
injected GitHub CLI child returned, but the second pass reused previously
constructed paths. A concurrent replacement of an input or workflow parent
directory with a symlink to byte-identical content could therefore preserve
every hash while changing the trusted path resolution.

**Correction.** The post-child pass now resolves all four authorization-bound
input paths again through the checked repository-root boundary. Workflow
validation checks every caller-controlled ancestor before inspecting the leaf.
This applies both before the child and during the final manifest revalidation.

**Regression evidence.** New synthetic cases replace the workflow parent before
the runner and replace either the evidence parent or workflow parent during the
runner. All three cases reached the runner or produced a receipt before the
correction. They now fail closed, and the post-run cases produce no receipt.

**Status.** Corrected locally with TDD. This remains synthetic, target-free
evidence; no real GitHub CLI verification or material boundary was crossed.

## 37. Hosted qualification and local execution had been conflated

**Problem.** Historical A0X packages used a local CCP qualification receipt for
the pre-material Gate A boundary. Public GitHub-hosted repository checks then
duplicated ordinary target-free work without producing a provider shape that
new dossiers could verify offline.

**Correction.** Hosted Gate A now has seven exact lanes:
`repository-python311`, `schema-cross-validation-python311`,
`repository-python312`, `schema-cross-validation-python312`, `a0x-no-model`,
`a0x-synthetic`, and `documentation-audit`. It carries four hosted inputs with
hard 32 KiB/1 MiB/2 MiB/16 KiB caps; Gate B creates the fifth 32 KiB verification
receipt only after hash-bound offline verification. There is no rerun or CCP
Gate A fallback. CCP Gate C remains an independent local coordinator and
execution envelope.

**Limitations.** The first real post-merge hosted Gate A run is acceptance, not
permission to adapt the verifier. A trusted-root snapshot cannot reveal
revocations published after that snapshot. Signed provenance does not prove
branch-protection non-bypass, review state, or a SLSA level. Capture,
publication, Gate B, and Gate C are separate authorization boundaries.

**Status.** Target-free local implementation and documentation only. Earlier
CCP receipts and pre-migration package hashes remain **Historical evidence**
with their original bytes and meanings. No hosted capture, GitHub CLI
verification, Gate B, Gate C, model, tokenizer, target, CCP heavy, Docker,
network, publication, or scientific execution occurred in this correction.

## 38. Hosted verifier tests assumed macOS-only paths

**Symptom.** GitHub Actions run `33459576482` failed three verifier tests on
both Python 3.11 and Python 3.12. The fixtures assumed `/private/tmp` and the
Homebrew path `/opt/homebrew/bin/gh`, neither of which is a portable contract
for Ubuntu hosted runners.

**Rejected correction.** Mocking the SHA-256 calculation would have made a
synthetic executable appear to be the pinned GitHub CLI. That would weaken the
security property the public verifier entry point is intended to prove, so the
approach was not used.

**Correction.** The public entry point still accepts only the exact pinned
GitHub CLI as a regular independent file with the frozen version and SHA-256.
After that check succeeds, it passes a private immutable verifier capability to
the already validated orchestration. Tests may exercise only that private
post-validation orchestration with a real temporary regular file and its real
hash. A separate public-boundary regression proves the same synthetic file is
rejected before the runner is invoked. All affected fixtures now use portable
temporary files and directories.

The verifier revalidates the executable path and hash after the child returns,
before the exclusive receipt write. The operational wrapper continues to call
only the public entry point; production code does not import or construct the
private test capability.

**Regression evidence.** The new public rejection test observes zero runner
calls and no receipt. The private orchestration cases retain pre-run and
post-run drift, input, path, output-collision, and rerun refusals without
mocking the frozen version, frozen SHA-256, or hash function. Independent Luna
and Terra reviews found no blocking issue in the correction.

**Status.** Corrected locally with TDD. This is target-free portability and
security-boundary evidence only. GitHub-hosted requalification remains pending;
no network, evidence capture, Gate B/C, model, tokenizer, target, CCP, Docker,
push, rerun, merge, or scientific execution occurred.

## 39. Parallel pair contracts hid a production-hosted incompatibility

**Symptom.** The architecture review found a 24/24 failure: all twelve frozen
approval dossiers were rejected by both hosted consumer schemas. Schema-only
validation had passed because the schemas accepted a model-root path, while
real dossiers correctly used the run-specific pair destination. Positive hosted
fixtures were built from that semantically invalid synthetic path, so they did
not represent a real dossier projection.

**Root cause.** `PairBinding`, consumer schema definitions, fixture helpers,
and lifecycle stage strings were maintained as parallel truths. The runner and
material adapter independently interpreted lifecycle state. The contract and
material-contract modules also formed a domain-level import cycle, making the
boundary difficult to audit.

**Correction.** `PairBinding` and its pair derivations are the sole domain
authority. The schema compiler registers every PairBinding projection; hosted
positive fixtures are projected by the canonical envelope builders; the runner
and material adapter use the canonical reducer; and adapter-side checks no
longer import the contract module through the material contract. Repository
verification invokes the compatibility oracle, which reports every frozen
dossier/consumer combination before a material boundary.

**Proof required before a future Gate A/B action.** On the selected exact
`HEAD`, run the 12 dossier × 2 hosted-consumer compatibility oracle, the
architecture fitness tests, and the documentation audit. These checks are
target-free and do not authorize Gate C, model/tokenizer access, target reads,
CCP heavy work, network, publication, or scientific execution.

## 40. Verified wheels still did not define a reproducible Gate B environment

**Problem.** The wheelhouse verifier proved exact local wheel bytes, and the
APFS primitive proved exact copy-on-write files, but no single transaction
bound them to a clean source HEAD, an exact interpreter, a final installed
distribution set, a model card, and an overwrite-refusing local receipt.
Using `venv` naively would also retain bootstrap `pip`, producing an
environment larger than the frozen 39-distribution contract. A generic pip
install could resolve online or accept unbound package bytes.

**Correction.** Add a focused offline prerequisite builder. Planning verifies
the exact clean source, canonical wheelhouse manifest, 39 wheel files, a
canonical allowlist of the complete base Python runtime, Python hash/version,
bootstrap pip bytes/version, canonical model card, and exact source snapshot
without writing or executing external code. The material path first APFS-clones
the complete verified base runtime and all 39 wheels into private attempt-owned
paths. It executes and installs only from those reverified paths, uses
`venv --copies`, verifies the actual environment-local bootstrap installer,
then runs one shell-free
`pip --isolated install` with `--no-index`, `--no-cache-dir`,
`--only-binary :all:`, `--require-hashes`, `--no-deps`, and the verified
wheelhouse. It removes bootstrap pip and accepts
the environment only when an isolated metadata probe reports exactly the 39
locked distributions and no importable pip. Model files are cloned only by the
existing no-fallback APFS boundary. Inputs, source state, output ancestors,
interpreter bytes, complete base-runtime allowlist, distribution metadata, and
model bytes are checked again before an exclusive receipt write. Static
validation precedes all child execution, read-only probes disable bytecode
writes, and every child has a 3,600-second timeout. The CLI requires an explicit
`--plan` or `--build`; material execution is never an implicit default.

**Regression evidence.** Synthetic tests cover exact command construction,
manifest/card/Python/base-runtime hashes, model-card double-read refusal,
owned input binding, no-runner planning, explicit mode selection,
dot-identifier refusal, 39-package cardinality, deterministic
requirements, dirty or wrong source, child failure, malformed or extra and
duplicate distributions, model-source drift, source-root and attempt-root
symlink swaps, occupied outputs, exact allowlist cloning, and canonical CLI
planning. Adjacent APFS and wheelhouse tests remain green.

**Status.** Implementation is target-free and uses only temporary synthetic
fixtures. The local wheelhouse manifest
`fe541aa83b5dbd9770da1f50d2cd88eb192586406398d9cffa5507f9f352ca72`
binds 39 wheels totalling 150,397,774 bytes, but no real environment has been
created and no real snapshot has been cloned. Gate B/C, model, tokenizer,
target, network, CCP, push, and publication remain unauthorized.

## 41. Lost capture-wrapper paths were outside frozen A0X trust surface

**Problem.** macOS restart removed the volatile recovery clone containing the
target-free Hosted Gate A capture boundary. Reconstructing its source, schemas,
adapter, and tests without adding them to both A0X implementation inventories
would allow a later frozen package to omit capture-critical behavior. Omitting
either capture test module from the synthetic aggregate would also leave a
trusted input unexercised by the required target-free lane.

**Correction.** Both capture schemas, the capture library, shell-free adapter,
and both capture test modules are now required by both inventory definitions.
The synthetic aggregate runs both capture test modules. The production adapter
remains fail-closed with no real subprocess runner; no live GitHub or CLI
contract was enabled by the recovery.

**Status.** The existing inventories, freezes, twelve dossiers, and no-model
receipt are intentionally stale because they predate this trusted surface. No
regeneration occurred. A new explicit authorization is required for one
target-free regeneration, all twelve dossiers, full deterministic suite,
independent review, and local closure. No capture, network, GitHub CLI, Gate
B/C, CCP, Docker, model, tokenizer, target, publication, or scientific work is
authorized.

## 42. Batch-wide artifacts could not represent a one-pair execution boundary

**Problem.** The two historical batch freezes, twelve approval dossiers, and
no-model receipt cover a broad campaign state. After the trusted vertical
generator and selector-only launcher were added, those bytes could not attest a
current, exact-head package for one leg/model pair.

**Correction.** Register the vertical library, CLI, tests, and manifest schema
in both implementation inventories and the target-free aggregate. Register its
PairBinding projection and require the schema inventory count to match the
actual A0X schema set. The target-free Make verification covers only the
vertical tests; the selector-derived material target is a future launcher and
is not an authorization to run it. The governing sequence is
[A0X pair-scoped vertical slice](A0X_VERTICAL_SLICE.md): P0, Gate A, Gate B,
Gate C, result verification, and publication are distinct gates.

**Status.** The batch artifacts remain historical and stale. No package,
freeze, dossier, receipt, model, tokenizer, target, CCP, network, or
publication action occurred. A0-R1 remains blocked until the A0 terminal
report and a separate authorization; scientific rules remain frozen between
legs.

## 43. Hosted repository checks exposed non-portable target-free fixtures

**Problem.** The first Hosted Gate A workflow for the vertical branch failed
on both Python 3.11 and 3.12. The test suite used macOS-only `/private/tmp`
paths, the bootstrap hard-coded that path for its private bytecode directory,
and injected capture tests did not explicitly enable their synthetic host
boundary. The same run also exposed implementation/freeze byte drift because
the latest trusted source changes had not yet been regenerated into the
committed A0X package.

**Correction.** Synthetic tests now use the repository root or platform
temporary directories rather than a fixed macOS namespace, while preserving
the real source and path-safety assertions. The P0 bootstrap creates its
private bytecode directory with the platform-managed temporary root, retaining
mode, regular-directory, emptiness, and cleanup checks. Capture tests pass an
explicit injected supported-host predicate; production still refuses
unsupported hosts. After this correction, the affected local suites pass
target-free; the A0X implementation inventories, freezes, and dossiers must
be regenerated from the correction commit before hosted requalification.

**Status.** Corrected offline with TDD. No models, tokenizers, targets, CCP,
Docker, network, or scientific execution were used. The failed workflow is
preserved as negative hosted evidence; a new push and workflow are required.

## 44. Model-card byte correction required freeze regeneration

**Problem.** The six tracked model cards intentionally use a versioned insertion
order, compact UTF-8, and one final LF. A generic sorted-key canonicalizer
therefore rejected valid cards. After correcting the builder to enforce the
explicit A0X field order, the implementation and test bytes changed while the
tracked freezes and dossiers still referenced their previous sizes and hashes.

**Correction.** The builder now validates the explicit model-card field order
and whitespace contract while preserving raw bytes. The two implementation
inventories, two freezes, and twelve dossiers were regenerated target-free from
the correction commit and committed together. Frozen-package and no-model
verification passed; synthetic verification passed 505 tests with one skip.

**Status.** Hosted run `33709259544`, attempt `1`, correctly failed on both
Python lanes before any material access because the pre-regeneration package
was stale (`50136` current bytes versus `47086` bound bytes). No artifact was
created and no rerun is authorized. The regenerated package is now at
`62dd5cd9c747f986fc41c364ea86306f0d7164ac`; a fresh Hosted Gate A is required
for that exact head.

## 45. Tracked vertical packages created a source-identity cycle

**Problem.** The tracked `a0x-vertical-slice-v1` package bound its own
`implementation_source_head`. Publishing it necessarily changed the checkout
identity required by P0 and later Gate C, while the batch Gate B route accepted
only the unrelated twelve-dossier set. The sequence could not produce one
stable source/package identity; repeated preparation would only move the
mismatch.

**Correction.** The future-only v2 route separates protected-main source
identity from local package identity: `Hosted Gate A -> capture -> P0 v2 ->
Gate B v2 -> Gate C v2 -> verification`. P0 v2 writes an ignored atomic
envelope containing the canonical five-member package and a non-self-hashing
external commitment. Gate B v2 and Gate C v2 reload the same typed binding,
source `HEAD/tree`, raw commitment, dossier, and pair; v1 and batch routes are
rejected for new work. The implementation inventory now binds every v2
schema/source/script/test path, including the schema cardinality baseline.

**Historical protection.** The tracked v1 package and historical review bytes
are recorded in
`docs/qualification/a0x-vertical-chain-historical-protection.json`. Generated
batch inventories/freezes/dossiers and the no-model receipt are explicitly
distinguished as current target-free derivatives and were regenerated from
implementation anchor `2bed9da6cd51877162f7efa39d2b1906219b1101`; they do
not authorize material work.

**Residual limitation.** Ignored runtime storage is not Git-attested. Every
P0/Gate B/Gate C validation window therefore assumes no untrusted same-user
namespace mutator; it enforces trusted-root containment, no-follow traversal,
regular-file/link-count/inode/size/hash checks, atomic absent-destination
publication, and ownership-loss refusal. This reduces but cannot eliminate a
same-user concurrent-mutator threat without operator isolation.

**Next boundary.** Stop at `sealed_gate_pending`. A new exact authorization is
required first for one Hosted Gate A run on protected main, then separately for
capture, P0 v2, Gate B v2, Gate C, and any publication. No model, tokenizer,
target, scoring, CCP, Docker, network, or scientific claim is opened here.

## 46. Historical batch derivatives required an independent Git-object ledger

**Problem.** The original seven-file historical protection manifest preserves
tracked v1 and review evidence, but intentionally excludes the seventeen
batch-derived implementation, freeze, dossier, and no-model receipt files that
were regenerated while Task 5 established the v2 route. A local working-tree
comparison would not prove their pre-regeneration bytes, and a shallow hosted
checkout would not retain their exact parent objects.

**Correction.** `docs/qualification/a0x-batch-pre-regeneration-ledger-d7a8b5f.json`
records exactly the seventeen generated paths from parent
`d7a8b5f475480dd0a1f9adcf67df12fd2ae81c1d`, its tree, mode, blob object ID,
byte count, SHA-256, and a domain-separated non-self commitment. The explicit
historical verifier replays only `git ls-tree` and `git cat-file` objects,
requires the complete exact path set, and refuses a missing parent. It is not
an active P0, Gate B, Gate C, or no-model input. Hosted checkout depth is zero
so the target-free test can prove the same historical object availability.

**Status.** The original seven-file protection manifest remains byte-identical.
The new ledger is historical audit evidence, not a qualification, authorization,
or scientific result. Regeneration remains target-free and is followed by exact
canonical recomputation of the tracked no-model receipt.
