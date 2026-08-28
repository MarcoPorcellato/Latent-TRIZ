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

## Current stop boundary

The large-blob-qualified producer regeneration may be committed locally after
all no-material gates, independent review, and exact hash records pass. It must
then stop for a new Latent-TRIZ exact-head qualification authorization.

It does **not** authorize CCP heavy execution, Docker, model/tokenizer
construction, protected-target access, installation, Latent-TRIZ publication,
merge, or scientific retry. The separately authorized CCP source/evidence
publication ended with merged PR #70 and grants no further CCP mutation.
