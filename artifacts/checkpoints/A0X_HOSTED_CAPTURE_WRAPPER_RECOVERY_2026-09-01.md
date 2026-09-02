---
type: restart-checkpoint
title: A0X Hosted Gate A capture wrapper reconstruction
status: recovery-in-progress-target-free
date: 2026-09-01
---

# A0X Hosted Gate A capture wrapper recovery

## Durable workspace

- workspace: `/Users/marco1/.codex/worktrees/latent-triz-a0x-hosted-capture-20260901`;
- branch: `agent/a0x-hosted-gate-a-capture-wrapper`;
- public base: `1bde09bb72ab5c4e938e1b9904f6b0a745ab3cc2`;
- base tree: `d07daf572f471b2be3973a464c44d3d826c73106`;
- current capture implementation commit: `48f75508cf706df53917d4b4448465cf6ca95282`;
- current capture implementation tree: `1e1206e8e9c6449f3eb2e95e0c4d53be8e3891cc`.

## Recovery fact

Previous implementation clone lived in `/private/tmp` and macOS restart removed it. No public remote or primary dirty checkout changed. This branch reconstructs approved target-free capture-wrapper scope from approved design and recorded review findings.

## Binding scope

One fail-closed capture boundary accepts only pinned regular independent GitHub CLI, exact source/run/attempt/artifact metadata, canonical archive members and byte limits, then atomically writes only four overwrite-refusing outputs. Synthetic archives and injected subprocesses only. No real GitHub, attestation verification, Gate B/C, model, tokenizer, target, CCP, Docker, push, PR, or merge.

## Prior defects to prevent

1. Every path/type/timestamp error becomes stable refusal before transport.
2. Archive requires proven Unix regular metadata; unknown/link-like, duplicate, extra, encrypted, traversal, or oversized members refuse.
3. Output transaction is absent-only, no-overwrite, inode-owned staging cleanup, and rechecks the expected child bytes/digests through the held stage descriptor both before and after exclusive publication. Any post-publication validation failure removes only the still-owned inode; lost ownership raises `A0X_HOSTED_CAPTURE_PUBLICATION_OWNERSHIP_LOST` without deletion.
4. Darwin `renameatx_np(..., RENAME_EXCL | RENAME_NOFOLLOW_ANY)` publishes exclusively; unsupported or failed primitive refuses, and hosted tests inject the private descriptor-relative seam.
5. CLI path is absolute, regular, independent, SHA/version-bound, revalidated before each subprocess.

## Current stop boundary

Aggregate and inventory source changes are complete at the implementation commit above. Tracked generated inventories, freezes, dossiers, and no-model receipt are intentionally stale. Regeneration requires separate exact-head authorization; do not regenerate. The remaining adapter stdout/output cap belongs to Task 2 unless the controller explicitly reassigns it. No real GitHub, attestation verification, Gate B/C, model, tokenizer, target, CCP, Docker, push, PR, or merge is authorized.
