---
type: approval-dossier
title: A0-R2.3 Sealed Execution Approval Dossier
description: Exact operator gate for the one permitted SmolLM2 sealed execution.
status: approval-requested
last_verified: 2026-08-16
---

# A0-R2.3 sealed-execution approval dossier

This document is the human-readable R2.3 gate. The separate machine-readable
request is identified as
`experiments/a0r2-independent-model/sealed-execution-approval-dossier.json`.
It remains excluded from N3 audit access under
`excluded_sensitive_role_unverified`; its contents and role have not been
verified in N3. The historical request status recorded here is
`approval_requested`; this page is not an authorization receipt.

## Exact proposed action

Authorize exactly one material run of the frozen
`a0r2-independent-model-v1.0.0` study with the already acquired
`HuggingFaceTB/SmolLM2-360M` snapshot at revision
`f8027fd0eaeea54caa13c31d31b9fdc459c38b49`.

The run is limited to:

- local-only CPU execution with `float32` tensors;
- the nine integrity-receipted runtime files, 727,058,433 bytes total;
- no network access and no text generation;
- at most 1,800 seconds wall time;
- at most 8,589,934,592 bytes peak RSS;
- at most 67,108,864 bytes of new dense output;
- one activation extraction followed by one analysis;
- zero sealed-target reads during activation and exactly one exact-hash target
  read at the analysis boundary;
- publication of the first terminal outcome, including `positive`, `null`,
  `failed`, `non_interpretable`, or `incompatible`.

Before the guarded command starts, the installed commit-ci-preflight contract
must report resource decision `Admit`, admission inactive, and an empty queue.
Any `Unknown`, `Deny`, active run, or queued ticket refuses execution.

## Bound scientific contract

The primary endpoint remains the final transformer-block output at SmolLM2
hidden-state tuple index 32, using
`problem_plus_transformation` / `mean_transformation_span` and the problem-only
sentinel baseline. The classifier, grouped leave-one-domain-out evaluation,
999 paired within-family permutations, positive thresholds, shortcut refusal,
four descriptive depths, views, sites, and all 14 controls remain frozen.
Sensitivities and cross-model concordance are descriptive and cannot rescue the
primary.

The approval request binds the already merged R2.1 protocol and R2.2
implementation, the acquisition and feasibility receipts, the
`cleanup_uncertain` guard observation, the R1 corpus/freeze declarations, and
the exact nine-file snapshot. The prior synthetic feasibility probe loaded the
model under its separate authorization but accessed no sealed target and
retained no output content.

## Explicit exclusions

Approval does not permit:

- a second material attempt after model output or sealed-target access;
- tuning, model substitution, generation, network access, or a protocol change;
- changing prompts, cases, targets, controls, thresholds, or interpretation;
- using the post-freeze expert TRIZ reference corpus in R2.3;
- human labels, expert adjudication, an LLM judge, or claim promotion;
- describing an automated target as expert-validated TRIZ.

If execution stops before any model output and target access, recovery still
requires a documented fail-closed decision. If model output or target content
may have been accessed, any retry requires a new explicit operator approval.

## Approval statement

The operator approval must identify the public commit containing the exact
dossier and use this scope:

> I authorize exactly one A0-R2.3 sealed execution under the public
> `a0r2-sealed-execution-approval-v1` dossier: the exact acquired
> `HuggingFaceTB/SmolLM2-360M` revision
> `f8027fd0eaeea54caa13c31d31b9fdc459c38b49`, local-only CPU float32, no
> network or generation, maximum 1,800 seconds, 8,589,934,592 bytes peak RSS,
> and 67,108,864 bytes of new dense output. I authorize exactly one sealed
> target read at the analysis boundary and publication of every terminal
> outcome. I do not authorize tuning, model substitution, protocol changes,
> or a retry after model or target access without a new explicit approval.

Until that statement is received and recorded against the merged dossier,
model load, material execution, and sealed-target access remain prohibited.

## Post-approval sequence

1. Record the exact operator authorization without changing the frozen study.
2. Reverify the model snapshot, implementation, receipts, approval binding,
   empty output destinations, and no-access preconditions without loading the
   model or opening target content.
3. Require CCP `Admit`, admission inactive, and queue count zero.
4. Execute one guarded `a0r2-run` attempt.
5. Preserve the first terminal package and perform only no-load/no-target
   verification afterwards.
6. Publish the external dense-asset locator and hash, representation index,
   receipts, result, report, limitations, recovery observation, and manifest.
7. Verify fail-closed from a fresh clone plus the declared external asset.
