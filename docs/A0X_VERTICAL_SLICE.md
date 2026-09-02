---
type: laboratory-specification
title: A0X pair-scoped vertical-slice execution
status: approved-design-pending-implementation
date: 2026-09-02
---

# A0X pair-scoped vertical slice

## Purpose

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

## Pair-scoped generated package

The existing batch generator writes both leg freezes and twelve dossiers. It
must remain historical and must not be silently reinterpreted as current.

The new `a0x-vertical-slice-v1` generator accepts exactly one `--leg` and one
`--model-key`. It writes only this five-file package under an absent,
implementation-head-qualified namespace:

```text
experiments/a0x-six-model/vertical-slices/<implementation-head>/<leg>/<model-key>/
  protocol.json
  implementation.json
  freeze.json
  approval-dossier.json
  slice-manifest.json
```

`slice-manifest.json` is canonical JSON and binds the repository, exact source
HEAD/tree, selected leg/model/revision, the four member paths and SHA-256
values, generator profile `a0x-vertical-slice-v1`, and the explicit statement
that this is one pair, not a campaign-wide regeneration. It does not hash
itself. The dossier binds the raw freeze hash and never grants model, tokenizer,
target, Gate B, Gate C, CCP, network, publication, retry, or claim promotion.

All construction occurs in a private staging directory. The package publishes
only through an exclusive atomic rename; occupied output, selector ambiguity,
missing or stale prerequisite, path escape, symlink, hardlink, non-regular
file, hash drift, partial write, or cross-binding mismatch is terminal refusal.
Historical batch freezes and dossiers are neither overwritten nor reused as
current pair-scoped evidence.

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

1. Implement and qualify the target-free pair-scoped generator.
2. Generate only `A0 / smollm2_360m` from an exact clean implementation head.
3. Request an exact-hash authorization for that one package.
4. Complete Gate A, then separately Gate B, then separately the one Gate C
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

- [ ] Pair-scoped generator refuses ambiguity and cannot alter historical batch artifacts.
- [ ] Pair package is generated atomically from one exact current source head.
- [ ] Each leg has its own freeze, dossier, gate evidence, and terminal report.
- [ ] A0 and A0-R1 remain unpooled and independently interpreted.
- [ ] The model-slice report is verified target-free and limits claims to the
      frozen automated-proxy signal for the exact tested model.
- [ ] The next model begins only under the unchanged global protocol and a new
      exact authorization.
