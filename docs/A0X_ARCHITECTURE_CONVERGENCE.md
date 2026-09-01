---
type: architecture-convergence-specification
title: A0X contract convergence and prevention of alignment drift
status: approved-for-offline-implementation
version: 1.0.0
date: 2026-09-01
source_head: 2670dbd8008b7498c417b03a38d475cb5acd279b
source_tree: 63c9e015c30c2c4aef48730718db8129a2d630f0
scope: target-free
---

# A0X contract convergence and prevention of alignment drift

## Purpose and decision

This specification records the architecture audit of A0X at the exact source
identity above and defines the approved, bounded correction. Its purpose is to
remove a class of repeated late-stage failures: independently maintained
representations of the same scientific pair, path, and gate semantics drifting
until a material boundary discovers the conflict.

The decision is **contract convergence**, not a broad rewrite. The new design
will establish one executable domain representation for a pair/attempt, compile
consumer schema fragments from it, generate representative fixtures from real
dossier-shaped data, and prove compatibility before any material gate can be
requested. It preserves the existing scientific protocol, exact model cards,
historical evidence, A/B/C authorization separation, and fail-closed posture.

This document is a versioned future-facing specification. Historical receipts,
frozen packages, dossiers, and prior reports retain their existing bytes,
identities, and meanings. They are evidence, not mutable configuration.

## Authority, evidence, and limits

### Verified facts

The following facts were established by bounded, target-free, read-only review
of the exact source identity above.

1. The freeze generator derives each real pair output directory as
   `results/a0x/<leg>/<model_key>/<run_id>` in
   `src/latent_triz/a0x_freeze.py`.
2. All twelve tracked A0X approval dossiers use that run-specific, no-trailing-
   slash form: six model snapshots for each of `a0` and `r1`.
3. Both hosted consumer schemas independently define their own PairBinding
   shape and require a different model-root path:
   `results/a0x/<leg>/<model_key>/`.
4. Production-schema validation therefore rejected all 24 combinations of
   twelve real dossiers and two hosted consumer documents. This is a
   **24/24 failure**, not an inference from a single example.
5. The synthetic helper creates the model-root path accepted by those schemas;
   the positive hosted fixtures are loaded from that synthetic path. Existing
   positive fixture tests consequently exercise a different semantic object
   from production dossiers.
6. `PairBinding.from_mapping()` currently verifies shape, relative-path safety,
   and dense-leg consistency, but does not derive or enforce the run-specific
   output path.
7. The hosted verifier verifies schema shape at its boundary. It did not have a
   test proving that every frozen dossier can produce a semantically valid
   hosted authorization and verification receipt.
8. A repository search found approximately 20 PairBinding definitions in
   multiple forms. The audit classified five semantic variants and eight byte
   shapes across code, JSON schemas, helpers, and fixtures.
9. `AttemptState` is the formal lifecycle state enum, while runner and adapter
   paths also use independently interpreted stage strings. The adapter has a
   broad fan-in (17 direct A0X-module imports in the audit) and translates
   between these representations.
10. Contract and material-contract modules have a dependency cycle through a
    local import. Existing code controls the immediate cycle, but the boundary
    is difficult to audit and encourages semantic leakage.
11. Multiple current-status locations duplicate status and hash narratives.
    Earlier documentation audits identified stale status wording as an operator
    risk even where the underlying artifacts were intact.

### Proposals in this specification

The canonical pair-scope semantics, schema compiler, compatibility oracle, generated
fixture projection, lifecycle reducer, status ledger, and migration sequence
below are design proposals approved for target-free implementation. Their exact
file layout, API signatures, generated hashes, and freeze values are not facts
until implementation and deterministic verification produce them.

### Unknowns and deliberately excluded conclusions

- This audit does not establish that every historical problem has the same root
  cause. It identifies a repeated class: parallel contract representations.
- It does not prove a scientific result, a model capability, a TRIZ mechanism,
  a hosted-attestation trust claim, or future runtime reproducibility.
- It does not authorize model load, tokenizer construction, protected-target
  access, dense output, network use, GitHub mutation, Docker, CCP heavy work,
  Gate B, or Gate C.
- A future material authorization remains separate and must bind the new exact
  frozen artifacts after this migration has completed.

## Root cause model

The immediate defect is a path-regex mismatch. The root cause is more general:
the system has several manually maintained projections of one domain fact.

```text
frozen dossier generator     synthetic helper / positive fixtures
           |                              |
           +--------- Pair semantics -----+
                         |
                         +--- hosted schema A
                         +--- hosted schema B
                         +--- runtime adapter
                         +--- lifecycle interpretation
```

Each projection can be internally valid while the overall system is invalid.
Schema-only tests and synthetic fixtures made that failure cheap to hide and
expensive to discover. Gate B would have been the first production consumer to
construct the incompatible envelope.

The correction therefore moves the acceptance test from a late boundary to a
deterministic, target-free compatibility oracle. It also makes derivation,
rather than manually repeated string literals, the authority for output paths.

## Architecture target

### Bounded Clean Architecture

This is a small application of Clean Architecture, functional-core/imperative-
shell design, and design by contract. It is intentionally bounded to A0X
contract convergence; it is not a repository-wide framework migration.

```text
Domain core (no filesystem, JSON Schema, GitHub, CCP, or model imports)
  PairBinding (canonical pair-scope semantics)
  pair derivations
  GateState / transition reducer
  domain invariants
       |
       v
Contract compiler
  PairBinding JSON projection
  embedded JSON Schema $defs
  real-shaped fixture projection
  compatibility matrix
       |
       v
Adapters and orchestration
  dossier freeze generator
  Hosted Gate A evidence / Gate B authorization
  runtime preparation
  Gate C execution adapter
  status reporting
```

The domain core is pure and deterministic. Adapters may parse or serialize the
core projection but must not introduce a second interpretation of pair identity,
output destination, or legal gate transition. All external inputs remain
fail-closed and are revalidated at existing material boundaries.

### Canonical pair scope implemented by `PairBinding`

Pair scope is the domain concept; the existing public `PairBinding` remains
its implementation and compatibility surface. This avoids a second type name
becoming another source of truth. `PairBinding` contains the present binding
fields: profile, leg, freeze hash, model key, model ID, revision, run ID, and
dense bound. `output_path` is no longer caller-selected data. It is derived
exactly once:

```text
results/a0x/<leg>/<model_key>/<run_id>
```

The core must expose at least these operations:

```python
PairBinding.from_mapping(mapping) -> PairBinding
PairBinding.from_dossier(dossier) -> PairBinding
derive_pair_output_path(leg, model_key, run_id) -> str
PairBinding.as_mapping() -> dict[str, object]
PairBinding.assert_equivalent(mapping) -> None
```

`from_mapping()` rejects an `output_path` not exactly equal to the derived
value. It also continues strict key, model, revision, dense-bound, and relative-
path validation. A historical artifact is never rewritten merely because a
future parser would reject its old shape; historical readers remain explicit,
versioned compatibility paths if needed.

### Contract compiler and schemas

Create one canonical PairBinding field specification in the pure pair core and
one local schema-fragment generator. The checked-in fragment is generated
output, not an independently edited source. Each consumer schema remains
self-contained and offline-verifiable, but receives the same compiled local
`$defs.pair_scope` content. No external `$ref` or network fetch is introduced.

The compiler is authoritative for:

- required pair fields and `additionalProperties: false`;
- profile, leg, revision, model-key, run-ID, and hash constraints;
- the exact run-specific `output_path` pattern;
- dense-bound structure;
- schema fragment version identifier.

Schema documents may keep consumer-specific fields, but cannot carry their own
hand-written PairBinding definition. A deterministic check must reject a schema
whose embedded compiled fragment differs from the core-generated bytes.

### Fixture policy

Positive fixture bytes must be generated from a real-shaped PairBinding and the
same envelope factories used by the compatibility oracle. Negative fixtures are
created by a narrowly named mutation of a positive canonical projection. Tests
may still use synthetic hashes and temporary paths, but not an alternate pair
path grammar or an unregistered envelope shape.

### Gate lifecycle reducer

Define one domain-owned gate transition reducer. It maps Gate A, Gate B, and
Gate C prerequisites and outputs to explicit states, including terminal refusal
and completion states. Runner and production adapter may convert external stage
labels at one adapter boundary only; no other module decides transition legality
from free-form strings.

The reducer must refuse, at minimum:

- Gate B before a verified, pair-compatible Gate A evidence set;
- Gate C before one prepared and hash-bound Gate B authorization;
- a second material attempt after model or target access;
- output emission into a pair destination inconsistent with `PairBinding`;
- a transition after a terminal outcome except documented read-only inspection.

This migration does not change the scientific one-shot policy. It makes the
existing policy executable at one authority point.

### Status ledger

One canonical current-status section will name current source identity,
implementation/freeze/dossier binding set, active gate, and next authorization
boundary. Other narrative documents may link to it but must label prior values
as historical. Generated hashes never become current merely because they are
the newest text in a file.

## Invariants and fitness functions

The following are non-negotiable after migration.

| ID | Invariant | Required evidence |
| --- | --- | --- |
| I1 | Each pair has exactly one derived output path. | Core unit tests and mutation refusals. |
| I2 | A parsed pair cannot contain a path different from its derivation. | `PairBinding.from_mapping()` negative tests. |
| I3 | Every hosted consumer accepts every current real dossier pair projection. | 12 dossiers × 2 hosted schemas = 24 PASS. |
| I4 | Every positive hosted fixture is generated from the canonical projection. | Fixture provenance test and byte-stable regeneration. |
| I5 | Consumer schemas embed byte-identical compiled pair fragment. | Schema compiler audit. |
| I6 | Exactly one reducer decides A/B/C transition legality. | Static import/ownership audit plus transition matrix tests. |
| I7 | Core has no imports from filesystem, schema, GitHub, CCP, model, or runtime adapters. | Dependency audit. |
| I8 | Historical artifacts are not changed or reinterpreted. | Before/after manifest of protected historical paths. |
| I9 | Status has one declared current authority; older checkpoints are historical. | Documentation audit. |
| I10 | A stale freeze cannot authorize material work. | Existing and expanded no-model refusal test. |

`I3` is the compatibility oracle's minimum matrix. It must report failures by
leg, model key, run ID, consumer document, JSON pointer, and reason without
reading a model, target, or private mapping.

## TRIZ analysis

### Contradiction

A0X needs immutable, highly checked evidence to protect scientific validity.
It also needs maintainable representations that evolve with engineering. More
independent copies increase local apparent safety but increase global drift.

### Applied principles

| TRIZ principle | Architectural application |
| --- | --- |
| Segmentation | Separate pure pair/lifecycle domain, contract compiler, and operational adapters. |
| Intermediary | Insert a compatibility oracle between frozen dossiers and Gate B. |
| Prior action | Detect every dossier/consumer incompatibility before Gate A publication or Gate B preparation. |
| Feedback | Publish deterministic matrix results in target-free CI. |
| Copying | Generate fixture projections from canonical dossier-shaped inputs instead of copying handwritten examples. |
| Universality | One PairBinding supplies paths, JSON, validation, schema fragments, and fixture inputs. |
| Separation in time | Preserve historical evidence; apply the new contract only to newly regenerated future-facing artifacts. |
| Parameter changes | Make schema fragment version and compatibility-matrix cardinality explicit, audited parameters. |

The result is not "more controls everywhere." It is fewer independent controls,
with one stronger early feedback loop.

## Non-goals and guardrails

- Do not alter the A0/A0-R1 scientific protocol, corpus, targets, scoring,
  thresholds, model cards, model revisions, timeout envelope, or outcome rules.
- Do not weaken any security or fail-closed condition to preserve fixture bytes.
- Do not add a general dependency-injection framework, ORM, web service,
  external schema registry, external JSON references, or network dependency.
- Do not rewrite large historical packages, receipts, outcome records, or
  published evidence branches.
- Do not promote hosted acceptance to Gate B authorization or scientific
  evidence.
- Do not change CCP policy or use CCP, Docker, models, tokenizer material,
  targets, or remote services during this migration.

## Migration DAG

Each node is target-free. A later node may not start until its predecessor has
the stated exit evidence. No node creates a material authorization.

```text
M0 baseline and protection manifest
 |
 +-- M1 PairBinding derivation and parser enforcement
 |      |
 |      +-- M2 local schema-fragment compiler
 |      |      |
 |      |      +-- M3 real-shaped fixture factories
 |      |      |      |
 |      |      +-- M4 12x2 compatibility oracle
 |      |             |
 |      +--------------+-- M5 lifecycle reducer integration
 |                              |
 +------------------------------+-- M6 inventory, docs, freeze regeneration
                                         |
                                         +-- M7 independent review and
                                             exact-head publication dossier
```

### M0 — baseline and protection manifest

Record exact source identity, protected historical artifact paths and hashes,
the twelve dossier paths, current schema identities, and current oracle result
(`0/24 PASS`). Add no generated or material files. Exit only when the baseline
test proves it would notice a historical-byte change.

### M1 — canonical PairBinding semantics

Write failing tests for correct derivation, trailing-slash rejection, wrong-run
rejection, wrong-model rejection, dense-leg mismatch, and exact dossier parse.
Move the PairBinding domain logic and its derivation into the pure pair core,
while preserving explicit compatibility re-exports and historical-reader
behavior. Exit only when core tests prove one path authority and all existing
compatible consumers still pass.

### M2 — compiled local schema fragment

Write failing tests that compare generated fragment content with both hosted
schemas. Implement the local compiler and update only future-facing consumer
schemas to embed compiled bytes. Exit only when hand-written pair definitions
are absent from migrated consumers and schemas remain self-contained.

### M3 — real-shaped fixtures

Write failing tests showing old model-root fixtures are invalid under
`PairBinding`. Replace fixture construction with factories that accept a
canonical `PairBinding`.
Use synthetic values only where they do not change pair grammar. Exit only when
positive fixture regeneration is deterministic and each fixture validates
through both schema and semantic parser.

### M4 — compatibility oracle

Write a failing test that loads all twelve tracked dossiers and projects each
one into both hosted envelopes. Implement a target-free oracle with machine-
readable report and readable failure summary. Exit only when all 24 validations
pass and deliberately corrupted pair/path cases report a precise refusal.

### M5 — lifecycle convergence

Write transition-matrix tests before editing adapters. Implement the one
reducer and adapt runner/production stage conversion at the single boundary.
Remove duplicate legality checks only after tests show equivalent or stronger
refusal. Exit only when there is one transition authority and an adapter cannot
advance an illegal state by changing a string.

### M6 — inventory, documentation, and deterministic regeneration

Update frozen implementation inventory for every new or changed trusted source
and test. Update this specification, the problem/solution log, and canonical
current-status authority. First prove a stale-freeze refusal. Then, and only
then, regenerate the two implementation inventories, two freezes, twelve
dossiers, and no-model receipt with no material access. Record exact SHA-256
values and a manifest of changed future-facing files. Exit only when a second
regeneration is byte-identical and historical protection manifest still passes.

### M7 — independent review and future authorization package

Terra reviews integration and deterministic results. Luna independently audits
schema cardinality, historical byte preservation, fixture provenance, matrix
coverage, and documentation status. Sol reviews security, lifecycle ownership,
scientific boundaries, and publication dossier before any Task 12-like remote
action. Exit only when all concrete findings are resolved or explicitly
accepted by a new user authorization.

## Deletion and compatibility policy

Deletion is a late action, not a migration shortcut.

1. Preserve all historical files byte-identically and maintain a protected-path
   manifest before removing any duplicate implementation.
2. Keep old parsers/readers only where a named historical profile needs them;
   reject them as producers for new future-facing artifacts.
3. Delete a duplicate schema fragment, fixture builder, or transition check
   only after the core replacement, compatibility oracle, and regression tests
   prove coverage. Each deletion must be explicit in a reviewable diff.
4. Do not delete checked-in receipts, historical dossiers, reports, evidence
   branches, or sealed outcome artifacts under this specification.
5. Do not retain an unused compatibility shim merely to keep an invalid
   synthetic fixture green.

## Approval and material boundaries

This approved scope permits only offline code, schema, test, documentation,
inventory, freeze, dossier, and no-model-receipt work. It does not grant an
authorization to any material operation.

| Boundary | Requires a new exact authorization after M7 |
| --- | --- |
| Hosted Gate A publication or capture | Yes |
| Gate B runtime materialization | Yes |
| Model or tokenizer material construction/load | Yes |
| Sealed target access | Yes |
| Gate C guarded execution | Yes |
| CCP heavy run or Docker | Yes |
| Push, pull request, merge, evidence publication | Yes |

If any migration change alters a hash-bound future artifact after a later
authorization is granted, stop, regenerate only under a new authorization, and
never reuse the prior authorization.

## Delegation and review model

Use deterministic tools before language-model analysis. Delegate bounded,
independent work to lower-cost workers:

- **Luna:** schema inventory, fixture provenance audit, compatibility-matrix
  cardinality checks, historical-path hash comparison, documentation-link and
  stale-status audit, log distillation.
- **Terra:** implement M1–M6 with TDD, integrate reviewed changes, run target-
  free suites, and create checkpoints.
- **Sol:** approve domain boundaries, security properties, lifecycle ownership,
  scientific interpretation, freeze/publication decisions, and any gate
  transition beyond M7.

No delegated finding is terminal evidence until the owning integrator verifies
the exact source bytes and relevant test output.

## Recovery and checkpoints

After each milestone record: exact HEAD/tree, clean/dirty status, changed-path
manifest, focused and complete test counts, oracle cardinality/result, and all
future-facing artifact hashes. Keep a restart checkpoint in the repository
under `artifacts/checkpoints/` before any restart or handoff.

On failure:

1. preserve the failing report and no-model artifacts;
2. do not retry a material boundary, because none is authorized here;
3. classify the failure as core, compiler, fixture, oracle, lifecycle, freeze,
   or documentation authority;
4. return to the nearest target-free DAG node with a new failing test;
5. do not overwrite historical evidence or use a broad reset/cleanup to make a
   result appear green.

## Completion checklist

This specification is implemented only when all items below have direct
evidence on one exact future source head.

- [ ] PairBinding is the sole future-facing path derivation and semantic parser.
- [ ] Migrated consumer schemas embed the same compiled local pair fragment.
- [ ] Positive hosted fixtures are generated from canonical real-shaped inputs.
- [ ] Compatibility oracle reports 24/24 PASS for the twelve tracked dossiers.
- [ ] Negative matrix cases fail closed with actionable, non-secret diagnostics.
- [ ] One lifecycle reducer owns A/B/C legality; adapter string handling is
      translation only.
- [ ] Core dependency audit shows no forbidden adapter imports or new cycle.
- [ ] Protected historical-path manifest proves historical bytes unchanged.
- [ ] Stale-freeze NO-GO, deterministic double regeneration, target-free suite,
      schema cross-validation, and documentation audit pass.
- [ ] Canonical status authority identifies current artifacts; older values are
      visibly historical.
- [ ] Terra and Luna independent reviews are recorded; Sol architecture/security
      review approves or records residual risk.
- [ ] Exact-head publication dossier is ready, but no remote or material action
      has occurred without its own authorization.

## Change log

### 1.0.0 — 2026-09-01

Initial canonical specification. Captures the exact-main audit, 24/24 hosted
compatibility failure, architecture decision, TRIZ rationale, migration DAG,
and target-free approval boundary.
