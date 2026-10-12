---
type: laboratory-specification
title: A0X pair-scoped vertical-slice execution
status: current-v2-route-engineering-qualification
date: 2026-09-02
---

# A0X pair-scoped vertical slice

## Current route and closure gate — 2026-09-25

This document's tracked `a0x-vertical-slice-v1` package is historical evidence
only. It is not a selector for new Gate B or Gate C work. The operational route
is:

```text
Hosted Gate A -> capture -> P0 v2 -> Gate B v2 -> Gate C v2 -> verification
```

The v2 P0 package is an ignored, attempt-owned atomic envelope bound to one
protected-`main` `HEAD/tree`, one pair, and an external package commitment.
Gate B v2 and Gate C v2 reload that same commitment and reject v1, batch, or
caller-selected dossier fallbacks. See the [Vertical Gate-Chain Convergence
design](superpowers/specs/2026-09-05-a0x-vertical-gate-chain-convergence-design.md)
for the normative boundary. Every arrow remains a separate exact authorization;
this documentation does not authorize Hosted capture, P0, Gate B, Gate C, or
any material access.

Production-bound regeneration requires behavioral parent/child coverage:
absent or mutated public closure evidence must be rejected before runner
invocation or child dispatch. The September 25 review recorded this as a
target-free blocker. Current coverage and phase authority must be checked
against the active operator handoff, not inferred from that historical review.
Regeneration is not Gate B readiness and does not itself authorize model,
tokenizer, target, network, CCP, Docker, or scientific Gate C access.

The public closure contract distinguishes pre-execution inputs from terminal
and postflight outputs and assigns public versus private artifact roles. Its
hashes establish integrity and cross-document consistency only; they cannot
establish human consent, runtime truth, or independent verification. The
synthetic experimental profile is not accepted by production entry points.

## Purpose

### Prospective first-result engineering route — 2026-10-12

The current A0-only dispatcher uses the versioned production D1–D7 mechanical
recipe in `a0_shortcuts.production_mechanics_recipe`. It derives the complete
96-case calibration schedule from public identities, not labels or historical
outcomes. All fourteen controls remain required. The primary scientific
protocol, 24-family selection, 199 permutations, endpoint indices and stopping
rules remain unchanged. Historical v1.0.3 outputs and R1 are not reinterpreted.

The material contract v3 separates its historical Matrix producer from the
active vertical guard. The latter uses the installed, operator-qualified
macos-v5 producer, not a historical Matrix receipt. Native resource telemetry
accepts finite decimal percentages; cryptographic commitment parsing remains
integer-only. Static swap occupancy alone is not a resource veto. The guard
and its fresh status probes share a minimal private coordination environment;
`HOME` is required for the persistent admission namespace, while credentials
are not forwarded.

The outer coordinator environment is not the model-process environment. The
vertical guard launches the child through an explicit `env -i` boundary with
the five frozen offline assignments and Python `-I -B`. The child rejects
unexpected variables before dispatch. It admits only validated CPython locale
coercion and macOS CoreFoundation startup metadata, then normalizes these away;
coordination paths and credentials cannot become model-process inputs. The
historical batch launcher is unchanged.

New P0 preparation can use `current-source-inventory-v1`. Prepare its ignored,
source-bound input ledger using the existing operator's
`--prepare-current-ledger` mode, then pin its raw hash and derived path in the
P0 authorization. The historical 137-entry ledger and replay inlet remain
unchanged. An updated ledger refuses a stale implementation inventory rather
than concealing it. Source/inventory regeneration precedes preparation.

Production dispatch requires the full reloaded P0 package, Gate B outputs,
private v4 authorization, Hosted Gate A input bytes and public pre-execution
closure. A pure context projection cannot authorize model or target access.
Parent and child pin the same input identities before execution and revalidate
them afterward. Exact generated public pre-execution files and terminal pair
outputs are accounted for explicitly; this is not an arbitrary dirty-source
exemption. Hashes prove integrity and consistency, not human consent or the
truth of an unobserved runtime assertion.

The private terminal verifier retains and independently cross-checks the
calibration result, activation receipt, one-shot target-read receipt,
statistical result and analysis seal. It checks their schemas, pair and
authorization bindings, actual dense/index hashes, measured calibration
sentinels and the unchanged frozen statistical predicate. A syntactically valid
or self-consistently rehashed contradiction is not sufficient evidence. These
receipts remain private and do not require reopening the sealed targets.
Completion also requires an observed successful postflight and release: a
sealed outcome remains preserved if cleanup fails, but is not reported as a
completed material attempt.

The real-model rehearsal calls the same internal calibration, loader,
activation, one-shot reader, analysis, sealing, packager and verifier stages.
Its independent synthetic inputs and ignored output namespace remain
permanently evidence- and publication-ineligible. The internal deadline is
3,300 seconds with a 300-second cleanup margin; the material RSS limit is
8 GiB. A failed or unevaluable calibration blocks further material stages.
A measured adverse shortcut remains non-interpretable and is never replaced
by a literal PASS.

The authorized Gate C parent temporarily restores only the two needed A0
target permissions, then reapplies mode 000 on every exit. This requires an
activity-owned source with no concurrent mutator: metadata identity checks
detect drift but are not hostile same-user isolation. Mode-000 files cannot
be pinned with macOS O_EVTONLY before restoring permissions. The parent uses
directory-relative checks and pins the admitted inode immediately afterward;
it does not chmod an identified replacement during cleanup.

Production qualification and scientific execution remain separate gates.
Independent review must accept the frozen engineering candidate before remote
publication. A separate exact authorization is still required for the single
scientific Gate C attempt and another for any scientific-result publication.

Execute the A0X replication campaign one exact model at a time without
rewriting or implying freshness for every other model. The first model slice is
`HuggingFaceTB/SmolLM2-360M@f8027fd0eaeea54caa13c31d31b9fdc459c38b49`.
Within that model, A0 and A0-R1 remain separate one-shot legs and separate
approval boundaries.

This changes packaging and operational sequencing only. It does not change the
frozen corpus, prompts, labels, controls, scoring, thresholds, statistical
rules, endpoint semantics, model cards, or claim envelope.

## Scientific invariant

The six-model registry and both scientific leg protocols stay globally frozen.
No later model, leg, prompt, control, statistic, or stopping rule may be chosen
because of an earlier terminal result. A null, failure, or positive terminal
result for the first model neither promotes a general TRIZ claim nor changes the
remaining model schedule.

The execution order is operational only:

```text
SmolLM2-360M / A0
  -> terminal report
  -> SmolLM2-360M / A0-R1
  -> terminal model-slice report
  -> next model, under the unchanged frozen protocol
```

## Historical v1 package and current v2 envelope

The existing batch generator, its two leg freezes, and its twelve dossiers are
historical target-free derivatives. The tracked
`a0x-vertical-slice-v1` generator and package are also historical evidence.
Neither can be silently reinterpreted as a current pair-scoped authorization.

The current P0 v2 generator accepts one typed leg/model pair and the already
captured protected-main source identity. It writes one ignored, attempt-owned
envelope under an absent, derived namespace:

```text
.a0x-runtime/p0/v2/<head>/<tree>/<leg>/<model-key>/
  package/
    protocol.json
    implementation.json
    freeze.json
    approval-dossier.json
    slice-manifest.json
  p0-commitment.json
```

`slice-manifest.json` binds the exact source `HEAD/tree`, one typed pair, and
the other four member sizes and SHA-256 values. The external
`p0-commitment.json` binds all five package members and records P0
authorization/attempt identities without self-hashing. Gate B v2 and Gate C v2
recompute and reload this same commitment. These documents never grant model,
tokenizer, target, network, CCP, publication, retry, or claim promotion.

All construction occurs in a private staging directory. The package publishes
only through an exclusive atomic rename; occupied output, selector ambiguity,
missing or stale prerequisite, path escape, symlink, hardlink, non-regular
file, hash drift, partial write, or cross-binding mismatch is terminal refusal.
Historical batch freezes and dossiers are neither overwritten nor reused as
current pair-scoped evidence.

## Transaction namespace trust boundary

P0 authorization is valid only while no untrusted process running as the same
user can mutate the repository or output namespace. This single exclusion
window begins before pre-execution Python/bootstrap verification and process
launch through terminal receipt emission and private-bootstrap cleanup. It
therefore covers every pre-generator verification, repository import, staging
and publication operation. Private `0700` staging excludes other users; it
does not exclude another process with the same user ID.

Darwin provides the required exclusive atomic publish rename, but it does not
provide an atomic unlink or directory removal conditioned on an expected inode
identity. Descriptor-relative identity checks therefore detect replacement;
they cannot make a later name-based cleanup operation race-free against an
untrusted same-user mutator. If the generator loses ownership of a staged or
published name, it must fail closed with
`A0X_VERTICAL_SLICE_PUBLICATION_OWNERSHIP_LOST`, preserve the possible
replacement, and refuse to accept the package as evidence. Cleanup is claimed
only for names whose ownership remains established.

The operator must isolate or stop untrusted same-user namespace mutators for
the complete transaction. If that condition cannot be established, P0 is
NO-GO; file modes and post hoc identity checks are not substitutes.
If private-bootstrap cleanup is uncertain, the trust window has no proven clean
close. The terminal receipt must preserve publication success separately from
cleanup uncertainty, mark retry prohibited, and require separately authorized
recovery without deleting or overwriting the published package.

## Ordered gates for one leg-model pair

| Gate | Purpose | Evidence | Stop boundary |
| --- | --- | --- | --- |
| P0 | target-free pair-package generation | exact head/tree, manifest, freeze, dossier hashes | no material access |
| A | hosted seven-lane qualification and exact capture | four verified hosted inputs | no runtime creation |
| B | pair-specific offline runtime preparation | fifth verification receipt, readiness/descriptor/authorization hashes | no model load |
| C | one local CCP-guarded material attempt | terminal receipt, report, dense locator/hash, cleanup state | no retry |
| R | target-free result verification and model-slice report | verifier output, limitations, terminal status | no next model authorization |

Gate A, Gate B, Gate C, publication, and each later leg require their own
explicit exact-head authorization. A successful gate never authorizes the next
gate. Missing or incompatible evidence is refusal, never fallback to another
model or a batch artifact.

## First slice: SmolLM2-360M

1. Run one separately authorized Hosted Gate A for protected main.
2. Capture its four verified inputs under a separate authorization.
3. Generate only `A0 / smollm2_360m` through separately authorized P0 v2.
4. Complete separately authorized Gate B, then separately the one Gate C
   attempt. Preserve any terminal outcome.
5. Verify and publish the A0 terminal report only under a separate publication
   authorization.
6. Repeat steps 2--5 for `A0-R1 / smollm2_360m`, without changing frozen
   scientific inputs because of A0.
7. Produce a model-slice synthesis that reports both legs separately and never
   pools them or generalizes beyond the frozen automated-proxy evidence.

## Cost and recovery policy

One model slice may be stopped after any terminal outcome. Its permanent
checkpoint records source HEAD/tree, selected pair, generated hashes, completed
gates, unproven gates, terminal results, and the next explicit authorization.
The next model reuses only source code and validated process, never another
model's runtime, output, receipt, authorization, or target access.

Use deterministic checks first; delegate bounded inventory, test execution, and
documentation work to low-cost workers. Keep security, scientific
interpretation, gate decisions, integration, publication, and merge with the
orchestrator.

## Completion checklist

- [ ] P0 v2 refuses ambiguity and cannot alter historical v1 or batch artifacts.
- [ ] Pair package is generated atomically from one exact current source head.
- [ ] Each leg has its own freeze, dossier, gate evidence, and terminal report.
- [ ] A0 and A0-R1 remain unpooled and independently interpreted.
- [ ] The model-slice report is verified target-free and limits claims to the
      frozen automated-proxy signal for the exact tested model.
- [ ] The next model begins only under the unchanged global protocol and a new
      exact authorization.
