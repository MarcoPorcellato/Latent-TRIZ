# A0X Hosted-CI Publication Plan

**Goal:** Publish the reviewed A0X Gate B hardening through standard
GitHub-hosted CI while preserving every material boundary.

**Specification:** `docs/A0X_SIX_MODEL_CAMPAIGN.md` and
`docs/A0X_GATE_B_OPERATOR_HARDENING.md`.

## Constraints

- Preserve `merge-policy/gate`, trusted-base classification, scientific
  artifact auditing, `contents: read`, and absence of repository secrets.
- Preserve public provenance commit
  `8e17aa5d08dd7f768014646725397bbb40d3d219` unchanged.
- Do not access Gate B/C, models, tokenizer material, sealed targets, or
  scientific execution paths.
- Keep the primary checkout untouched and use the isolated clone.

## Task 1 — Hosted-CI bootstrap: complete

- [x] Replace the automatic public CCP receipt gate with hosted repository
  checks on Python 3.11 and 3.12.
- [x] Preserve the scientific audit and aggregate `merge-policy/gate`.
- [x] Verify 1,080 repository tests with 11 expected skips.
- [x] Merge PR #108 at public `main`
  `78b40677d7cd8b58421a6a2a80cb6feb066f85b3`.

The unchanged ruleset had no bypass actor, so one explicitly authorized
transition-only CCP qualification and one failed-workflow rerun were required
to close the bootstrap. That historical exception does not restore an automatic
CCP gate and does not authorize further CCP work.

## Task 2 — Reconstruct A0X on hosted-CI main: complete

- [x] Apply the reviewed functional delta to the new public base.
- [x] Commit implementation anchor
  `74d6bc048e656f3ced2d4bc6db4b0492dfd16359`.
- [x] Prove stale generated bindings fail closed.
- [x] Regenerate two implementations, two freezes, and twelve dossiers without
  material access.
- [x] Commit bindings at
  `50cf959e7a9b50d68ee58a11ac063e6681761abe`.
- [x] Pass focused hardening 97/97, frozen 11/11, synthetic 293/293, schema 155
  agreements plus 19 rejected mutations, and repository 1,125 tests with 11
  documented skips.

## Task 3 — Hosted publication: in progress

- [ ] Commit the authoritative documentation checkpoint.
- [ ] Reverify public base, ruleset, branch head, and clean diff.
- [ ] Push non-forced and open a ready PR.
- [ ] Require hosted Python 3.11, Python 3.12, scientific audit, trusted
  classification, and aggregate gate to be terminally green.
- [ ] Squash merge the unchanged exact head with no unresolved conversations.
- [ ] Verify the new public `main` and target-free package from a fresh clone.

Publication does not authorize Gate B/C. Any changed head/base, skipped required
lane, or failed gate stops the merge.
