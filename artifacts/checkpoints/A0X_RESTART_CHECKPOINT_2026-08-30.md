---
type: restart-checkpoint
title: A0X Hosted Gate A Task 10 checkpoint
status: target-free-regeneration-pending
date: 2026-08-31
---

# A0X Hosted Gate A Task 10 restart checkpoint

This new checkpoint is authoritative for the Hosted Gate A continuation. The
older `docs/A0X_RESTART_HANDOFF.md` is preserved byte-identically as historical
handoff evidence. The duplicate pointer is deliberate: the canonical plan
binds this exact `artifacts/checkpoints/A0X_RESTART_CHECKPOINT_2026-08-30.md`
path although it was absent when Task 10 began.

Tasks 1–9 are local target-free implementation. Task 9's stale-freeze refusal
is **Historical evidence**. Task 10 must first commit its current documentation
and implementation anchor, then regenerate exactly two inventories, two
freezes, twelve dossiers, and one no-model receipt with that immutable
`implementation_source_head`. A generated-artifact commit must not replace the
anchor.

Hosted Gate A requires exactly seven lanes: `repository-python311`,
`schema-cross-validation-python311`, `repository-python312`,
`schema-cross-validation-python312`, `a0x-no-model`, `a0x-synthetic`, and
`documentation-audit`. It accepts four hosted inputs with caps of 32 KiB
(manifest), 1 MiB (bundle), 2 MiB (trusted root), and 16 KiB (transport). Gate
B creates the fifth verification receipt, capped at 32 KiB. There is no rerun
and no CCP Gate A fallback; CCP Gate C remains an independent local coordinator.

The first real post-merge hosted Gate A run is a non-material acceptance test.
Capture, public evidence publication, Gate B, and Gate C each require separate
authorization. The captured trusted-root snapshot cannot identify revocations
published after that snapshot. On restart, revalidate source head/tree, object
type, link count, raw hashes, authorization, stage, and retention status. Do
not overwrite receipts or relabel old CCP evidence as hosted evidence.

