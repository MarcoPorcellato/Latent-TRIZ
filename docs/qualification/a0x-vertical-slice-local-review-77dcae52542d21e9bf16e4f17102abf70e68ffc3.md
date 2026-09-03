---
type: local-qualification-review
title: A0X vertical-slice local readiness review
status: authorization-bootstrap-corrected-re-review-pending
date: 2026-09-02
reviewed_head: 77dcae52542d21e9bf16e4f17102abf70e68ffc3
reviewed_tree: 79d9fd9c868cf367fdec28bbad8c0ac0d7f8b598
scope: target-free
---

# A0X vertical-slice local readiness review

## Decision

**NO-GO pending independent re-review of the corrected P0 bootstrap.** The
target-free implementation now addresses the four provenance findings from the
whole-branch review, but implementation is not authorization. P0 has not run
and no generated package is qualified.

P0 remains fail-closed unless the operator can exclude every untrusted process
running as the same user from repository and output-namespace mutation for the
complete transaction. The single exclusion window begins before pre-execution
Python/bootstrap verification and process launch through terminal receipt
emission and private-bootstrap cleanup. Darwin cannot atomically remove a name
conditioned on an expected inode. Detected ownership loss must preserve the
possible replacement and return
`A0X_VERTICAL_SLICE_PUBLICATION_OWNERSHIP_LOST`.

## Exact reviewed state

- Worktree: `/Users/marco1/.codex/worktrees/latent-triz-a0x-hosted-capture-20260901`
- Branch: `agent/a0x-hosted-gate-a-capture-wrapper`
- Reviewed implementation HEAD: `77dcae52542d21e9bf16e4f17102abf70e68ffc3`
- Reviewed implementation tree: `79d9fd9c868cf367fdec28bbad8c0ac0d7f8b598`
- Review base: `24b51718c89e6c2fe2a3f7530c724eee66279ee8`
- Initial and post-test status: clean; branch was 22 commits ahead of
  `origin/main`.
- Exact range: 19 files, 2,940 insertions, 14 deletions.
- `git diff --check 24b51718c89e6c2fe2a3f7530c724eee66279ee8..HEAD`:
  exit 0.
- AST parse of ten changed Python source/test files: `ast-valid 10`.

The checkpoint and this review are committed after the reviewed implementation
head. Therefore P0 authorization must bind the final clean checkpoint commit
and tree reported after that commit, not the pre-checkpoint head in this file
name. These two documentation files are not package inputs; the raw input
ledger below remains independently revalidated after the checkpoint commit.

## Source and security review

The reviewed range adds a separate `a0x-vertical-slice-v1` namespace and leaves
the historical batch generator and its output paths intact. The request
requires one canonical `Leg`, one registered model key, a 40-hex source commit,
and the exact derived absent output root. Generation checks exact clean
HEAD/tree before reading prerequisites and immediately before publication.

Every prerequisite is read once through a descriptor-relative reader that
requires a regular, single-link, bounded file with stable descriptor identity
and size. Parsed values and SHA-256 values derive from the same bytes. The
package has exactly five canonical JSON members; the manifest binds the four
non-manifest members and the exact source HEAD/tree.

Publication uses a private `0700` sibling staging directory, `0600` exclusive
members, per-file and directory `fsync`, held directory descriptors, and Darwin
`renameatx_np(RENAME_EXCL | RENAME_NOFOLLOW_ANY)`. There is no path-based rename,
overwrite, or copy fallback. Occupied output, selector drift, source drift,
prerequisite drift, path/link/type drift, partial writes, and ownership loss
fail closed.

The pair-scoped material consumer derives its dossier path from the head, leg,
and model key. It validates all five files and retains the package head across
delegation before any authorization lookup, preflight, claim, or guard call.
The historical launcher still accepts only the twelve historical dossier
paths.

The only proposed P0 action starts with the exact authorization-bound inline
pre-execution launcher in the command below. Under the already authenticated
absolute Python and `-I -S -B`, that launcher descriptor-opens
`scripts/a0x_vertical_p0_bootstrap.py`, requires regular single-link stable
bytes, compares them with the immutable authorized bootstrap SHA-256, and only
then compiles and executes those verified bytes. The bootstrap independently
requires the same expected hash before importing repository modules or creating
staging state. It then verifies the immutable authorized HEAD/tree, exact clean
checkout, Python identity, source-only isolation, and exact 137-entry
descriptor ledger. It rejects repository bytecode, native extension artifacts,
ambient repository imports, and any ledger cardinality, type, link-count,
byte-count, or digest mismatch.

The terminal receipt binds source, Python, bootstrap, and ledger identities.
It also records whether package publication completed and whether private
bootstrap cleanup completed. If cleanup is uncertain after publication, the
bootstrap emits the successful generation receipt with `published`,
`uncertain`, and `retry_permitted: false`, then exits with a terminal cleanup
error. That outcome is not qualification evidence, does not prove the trust
window closed, preserves the published package, and must never be retried.

The bootstrap and its tests intentionally remain outside the 137 package-input
inventory. The authorized clean HEAD/tree binds their committed bytes, and the
bootstrap records its own SHA-256 in the terminal receipt. The package-input
ledger continues to cover exactly the bytes consumed by the generator.

## Fresh deterministic evidence

The corrected target-free command completed with `Ran 85 tests ... OK`:

```text
rtk env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.test_a0x_vertical_slice tests.test_a0x_vertical_material tests.test_a0x_vertical_p0_bootstrap tests.test_a0x_freeze tests.test_a0x_schema_projection -v
```

It covered selector refusal, exact clean-checkout binding, descriptor-bound
prerequisites, Darwin flags and errno mapping, exclusive publication,
ownership-loss preservation, exact five-file validation, cross-leg/model/head
substitution, changed package bytes, zero claim/preflight/guard calls, trusted
inventory registration, schema projection parity, immutable bootstrap source
identity, isolated hash-bound Python, conflicting valid ignored bytecode, PATH
shadowing, pre-execution bootstrap replacement without marker execution,
ledger cardinality/type/link/digest refusal, exact inline-source parity across
authorization documents, full trust-window wording, and post-publication
cleanup uncertainty with the successful receipt preserved.

`rtk env PYTHONDONTWRITEBYTECODE=1 make a0x-vertical-slice-verify` independently
completed with `Ran 52 tests ... OK`. Five active package schemas passed Draft
2020-12 meta-validation: protocol, implementation, freeze manifest,
authorization dossier, and vertical-slice manifest.

The full target-free synthetic aggregate produced a zero-material receipt with
`model_loaded: false`, `tokenizer_constructed: false`,
`sealed_target_content_reads: 0`, and `ccp_invoked: false`. It then ran 500
tests and ended with the expected historical stale-package boundary: three
failures, one dependent error, and one skip. Both frozen legs report
implementation-path drift; byte-identical historical regeneration differs;
the strict frozen-phase superset refuses with `A0X frozen leg package drifted`.
No failure belongs to the vertical selector/package suites, and no stale check
was suppressed.

The documentation gate found all four operational documents link the canonical
vertical-slice authority, label the batch artifacts historical and stale,
separate P0, Gates A/B/C, result verification, and publication, and block A0-R1
until the A0 terminal report. The target-free Make target is isolated from the
material launcher. An initial literal phrase check was inconclusive because
Markdown wrapped `A0 terminal report` across lines; the corrected
whitespace-normalized check passed.

One initial `rtk test ! -e` path probe was filtered by RTK and therefore is not
used as evidence. A direct Python existence check passed:
`real-vertical-package-path-absent`.

## Historical batch byte identity

`git diff --quiet` over the two batch freezes and twelve dossier paths returned
exit 0 for the full implementation range. Current SHA-256 values are:

```text
38bdbb99db20c471e9aeafeb7b961709ce373d2fd8f0801c56655ac550266677  experiments/a0x-six-model/freeze/a0-freeze.json
2ec31870102a9219a36df24304748e31da4050514d9e59cfd0c9056adaba3ffa  experiments/a0x-six-model/freeze/r1-freeze.json
c1e48c06d1d4d10b741edff0d3e7c06d452848fb30e4a7bcd80e7485c3392d7f  experiments/a0x-six-model/approval-dossiers/a0/gpt2.json
167c45a926532c280683427df818c3668d9e86c83223bf916f6829e0c67563aa  experiments/a0x-six-model/approval-dossiers/a0/gpt_neo_125m.json
16a3f584121f533378a903aed22e6db37118af2839372fad56ed5f86c7d0c3fe  experiments/a0x-six-model/approval-dossiers/a0/qwen2_5_0_5b.json
876e04a9ee9f36f11ef662411967367838bba260240cec76f8befb18ac574a6b  experiments/a0x-six-model/approval-dossiers/a0/qwen3_0_6b_base.json
213d915b48705beaba1c5e4d77a08daaa999aaf0d64bc12c9b93ea396d0dae8b  experiments/a0x-six-model/approval-dossiers/a0/smollm2_135m.json
41e748437c620117fac22d7ce4df3de3ce068ad44673f1a1adbdde514c950a92  experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json
8f0e4bcfe18a71b9bea98515e1aa8be4856ca73e8de0ce5e685e4cbab6f0151b  experiments/a0x-six-model/approval-dossiers/r1/gpt2.json
090128e0b84d76ca0cac42ba4f00acd470b89603fedca52e8eecf54760351fb1  experiments/a0x-six-model/approval-dossiers/r1/gpt_neo_125m.json
425291b73d2d5a1e8702fcbf9f9bf3e62bf423225c6eb8d188018db317b3a5e1  experiments/a0x-six-model/approval-dossiers/r1/qwen2_5_0_5b.json
56f31e074f5d4d8d56266fcb74c71ca1b0fd8fbffee01be913995316e8e8f4eb  experiments/a0x-six-model/approval-dossiers/r1/qwen3_0_6b_base.json
445fc14935aac0007a3f287ab5f3e05856f9503c9c2797eda8e1545f1459a5a8  experiments/a0x-six-model/approval-dossiers/r1/smollm2_135m.json
7f77eb6fac9ce168dae42c030d7ede4f43035018f62529dccfd8289069bcfe47  experiments/a0x-six-model/approval-dossiers/r1/smollm2_360m.json
```

These bytes remain historical and stale. Byte identity is preservation
evidence, not current qualification.

## Raw P0 package-input ledger

For `A0 / smollm2_360m`, generation reads 137 unique raw prerequisite files,
totalling 2,149,928 bytes. All 137 passed the production descriptor-relative,
regular, single-link reader. Each line is `SHA-256 bytes repository-relative-path`.
The SHA-256 of the sorted newline-terminated ledger is
`72a3b119e3a3629b7bcb7a84a867f9a32bdb4f95c6f7db7396a5184229ea7595`.

```text
f84777250a50082cd4f2390d949193c73d983475d32c08b02536fdf5ebd8a7fd 293 .github/a0x-hosted-gate-a-actions.json
06a3c748ae9491ed4cfbf53f5f8eecdd23ab4ac2a9f7ca465b57874b838aa236 672 .github/a0x-hosted-gate-a-lanes.json
5f74199107481c73adc2fa1efbd462c2a9d8b1d5009164892a2917d02ae595e4 11419 .github/workflows/a0x-hosted-gate-a.yml
7ae4f426a812e78ed857715c255ec753e09e2c1fe1eb52c34b2c6cac42e9e58d 37420 Makefile
2d08085d8cfc566f62b1b414c6ca09ad23af8df67de0fbd6876a896783721df9 1936 experiments/a0-automated-weak-proxy/implementation.json
36d52643d419fd4e8feada63d19a42429940f3559dda72adf342c484411fc244 4755 experiments/a0-automated-weak-proxy/protocol.json
cf762fdb8e19c5d047910f1f65b353df06f31096cea27adf504ae8e0bccbf295 13436 experiments/a0x-six-model/a0-selection-manifest.json
9d743d1913664290451be62dbd21fa27b7bb6b5285a4cdea75e43c576cac2156 3303 experiments/a0x-six-model/material-execution-contract.json
07a655f88617e126aee83339a4c90278d8ff29a65fce37b637cf8bcb21b6b15b 2715 experiments/a0x-six-model/model-cards/gpt2.json
56315f2274287d368353b20d6680dd3a11d7fcc80b2a93cd6894ef00559d5bdd 2900 experiments/a0x-six-model/model-cards/gpt_neo_125m.json
41df14dfa7f5af02127c10bff936077b44cd063c3d30ea45c98361159bbe0649 2759 experiments/a0x-six-model/model-cards/qwen2_5_0_5b.json
8cf118f3a70ba44d32c4fa97e35709c47036c6f58bea0e45f64bdc248daaec70 2715 experiments/a0x-six-model/model-cards/qwen3_0_6b_base.json
1189f3d77ad3bc2ceaf857ef3cc0bd298d1870e771f57b3b4925d981b4a753ed 2891 experiments/a0x-six-model/model-cards/smollm2_135m.json
df3522a37cbca114c72ea2342ccd90393ea329a5d5f48b7b3639ce5e6b385754 3082 experiments/a0x-six-model/model-cards/smollm2_360m.json
0a1cb36454a04da9cf8c105abf664df07e6c846125e9c74a7c930f92010650f9 398 experiments/a0x-six-model/model-registry.json
ee760ab26a1e8d07bca17ed3d90fa0476816ea5f78d11ed4a8975f6c365a8fde 8207 experiments/a0x-six-model/protected-a0-tree.json
37caf5bff910fbd7dda44433b92df25fbfd989aea829e9bc4ce37e70df1f1782 33 requirements-schema.in
0bbafebbe4fdb6028f5e8565eae397d18d6ace90e7e5e2c5b9472aa924162be7 17541 requirements-schema.lock
aa3ff92fa99b0b0751b3f593ee7508c95c8e303959ee2bf4bd60a8ea37fe021d 14209 schemas/a0x-activation-receipt.schema.json
9c28a3de10858334d4d6f6c24bad0a8b3dbf8eef24f69fa0649356500d52b0bb 11003 schemas/a0x-activation-stage-occupancy-receipt.schema.json
c1ab65c1741876a933d22afb34399f85ca7df43a3bcfbcdae9b2e6bab7cb2bd8 7263 schemas/a0x-attempt-claim.schema.json
1d72b6591ec406205edb988be223f7d2f17b8b0bd65445b9e57b555a93dc173c 7384 schemas/a0x-authorization-dossier.schema.json
44c01339703d4931dc7b9eb0f5d885bbe131def16ca2c934764418cc2f6198eb 10237 schemas/a0x-ccp-observation.schema.json
e9f5661b845871094bbb7350df3e86f061adcafc64d9e1a17877d2c87a588ee8 18663 schemas/a0x-execution-authorization-v3.schema.json
68b5bdf10f8e46abffcc368e458853016630e2c5924f09786ec8b5ae47a8ee5e 16482 schemas/a0x-execution-authorization.schema.json
f03d4384e26d02556190644311578eb2da4bd6886a93d12f91b290f1484eb473 9592 schemas/a0x-external-assets-locator.schema.json
287486bbdb620f4045cc01905d2012a04fc3198978c1c78afe0262c94d3cb930 1212 schemas/a0x-freeze-manifest.schema.json
bc0f52d81a0280a8a59423eb4ab54ed63b06e4753e72ea095e78616873554874 10363 schemas/a0x-gate-b-authorization.schema.json
ae6b10ae31d9667a6a9c76ee219384d3c9bcb640d2098b006adc4be60be6f0d2 6933 schemas/a0x-gh-2.97.0-verification-result.schema.json
89620d854d38311600f8a6c18a0211dfd5da3eea86c382eb083dc34eb97ee49f 3479 schemas/a0x-guard-launch.schema.json
0be1da1e1eef94c78ed0cb87a84fcd3fcaf5e1da217c1da00dbecafedc26eb28 1502 schemas/a0x-hosted-gate-a-capture-request.schema.json
69830d76c21ef6ce4e3ea2e8627c46e4ec35b3660f10cb90d6563fad0c2ed863 1468 schemas/a0x-hosted-gate-a-capture-transport.schema.json
6e62ec41ea33bbc3ccb36baa997d0a8e2220cfdd60c61114834dd27e7638e2c2 3056 schemas/a0x-hosted-gate-a-evidence.schema.json
bff0dbde1e167f1a78cc6aed60c7b2bade8e20123adb63472c4ed3795b379543 2333 schemas/a0x-hosted-gate-a-lane-receipt.schema.json
c9b9da5e2f66b5eda13d0a536438cc8d4cf071d400ec799c4795db4565dc6007 1427 schemas/a0x-hosted-gate-a-transport.schema.json
bd735639a9b34fb231f0118be9dab40599b407a40a29c17f63f29f0e7c7e680e 9987 schemas/a0x-hosted-gate-a-verification-receipt.schema.json
dc746e9c1985ac17dc918c7837891510b2c18a6c81e06aaeb8de2660bb0999d1 1044 schemas/a0x-hosted-gate-a-verifier-policy.schema.json
20922989b578cbd586e2493b01c4c410ef44199f6c9b937688f8d060534c260e 2226 schemas/a0x-implementation.schema.json
63149bb2f6fb36f7d70ec238f72a5c4827d8e651d2e366415d5db002d1e38e67 5230 schemas/a0x-material-execution-contract.schema.json
28d32493c4e57cae16d2883be7803be86642de60c23138507f7d3dc53a984b65 9923 schemas/a0x-model-identity-receipt.schema.json
c6982e3ec918d042c9c16168c610c55c066c7705e5369aa46104225abba5fd5e 12909 schemas/a0x-output-occupancy-receipt.schema.json
66acfe46458da4a7ccd4f1fa57e2c3e97d0610a5f497f0be6f42660c3d59cbea 3043 schemas/a0x-pair-binding.fragment.json
6a0169f307b66a5eea788316b216fbd9cb40761abd2ccb7b811fca223d85da66 4955 schemas/a0x-pair-projections.json
ddd4eec19e746beac7cf73b044404e854a66515c3a8baa09c608d2f06ff8b99e 10544 schemas/a0x-preflight-receipt.schema.json
f2d42f301e7e0f741bb798e74a5431563ad637bd17484fcfc29234a1b95d9ac0 2628 schemas/a0x-protocol.schema.json
5258fbf153961cc53caf72f68746984439b87b0d54e42eb9765a27dac1364eb5 14226 schemas/a0x-publication-manifest.schema.json
8953626e9008c7677acaeb09c1ca872bdcbcd099d48a2bcf343c4bb615e1be18 2610 schemas/a0x-qualification-authorization.schema.json
325036d2602f569c1d4dfc9731d82d5fe469f281f6109e6ea8796600b1ce84be 4691 schemas/a0x-qualification-evidence.schema.json
cd9f5d12bd23c71945d245c7843d58605ba41fec8f7a5ad58d1c64a401c749e4 9933 schemas/a0x-representation-record.schema.json
f0ba551507b6d13d2180033bef3b344e6ee9b9552fac70d26fc6e7d53e42ffb7 30524 schemas/a0x-statistical-result.schema.json
42da40c230d3fced6fde8085f391c7a19ea7df62027ad0cce420647df1f1e7a3 11936 schemas/a0x-target-read-receipt.schema.json
95ccdac5be8bf205f071642c46f6b4b089d0943f66f7596e0370961d9aa139a2 39271 schemas/a0x-terminal-result.schema.json
c9e9dd0c7ce24fbae0af6cf0157860e936b426adef4a14805fd6924d92fba13a 7596 schemas/a0x-vertical-slice-manifest.schema.json
b4dffcaf9c93e76e0f2d55577aa730d6828b2027a7ffa4ce0e3598f00f6bffca 4496 scripts/a0x_build_gate_b_runtime.py
67cef25f9770326303f1476cdc892dfdf6b499ff54d32dcb318fb4fe9dc37a50 6852 scripts/a0x_capture_hosted_gate_a.py
c89dc10de43b6b0a341963effa7e5eb854888a38be74b33f74c8aefed51e8b2e 1403 scripts/a0x_compatibility_check.py
95221748b5b16d01ba11b0f3dfc0ed023c8f30d01df06eb454ff0a6eb7793dae 8601 scripts/a0x_compile_pair_schemas.py
a5fb96db4607b52d38ff9feb017f0e37d5c325e6cf133bc2a2c52880ad911b2f 982 scripts/a0x_contract_check.py
5c6d8673f6e4a0d3314c682c2d1417f4c1c789e7ce83af256ac1ebd4b8cf624b 2928 scripts/a0x_hosted_gate_a.py
effbed080b734311c962a2940c00c01ab9a5721f7fe1a7d9da4e6fc64be6f000 1378 scripts/a0x_material.py
fe49ad2e281f89645dc9deb1695131756f6e54dbcd9c81bc78525861421e0d30 23802 scripts/a0x_material_child.py
e779d001f44e244cdb66c82013a03a30580d4e9ca3ea50841e6955a2a3d68389 8116 scripts/a0x_materialize_no_model_receipt.py
22d81ae8b47edc883374eb948d6637f4cf88f5a1f5eb2512489680b59198d816 6621 scripts/a0x_prepare_runtime.py
4d3d764a2224c3777aeb3ea5875aa03d151fa15742af93d1cee6058b92b9a49b 3348 scripts/a0x_verify_hosted_gate_a.py
488097363e95881d51d368fb28b5cfd093c4f0c1853c1167fea60fa8aa3caba1 1782 scripts/a0x_vertical_material.py
4c94ce76452c86499ab860e0cbbc4c576caee0294df73cbfe7c2c0513d6bb498 43032 scripts/repository_check.py
70e70b0a1ba12331e2242fcfcdf8e354972e1fd23a7b0b1f1bb3eb4e1cd93b5a 24871 src/latent_triz/a0x_a0_activations.py
2faf8552aabc14e2cf757bc54938c60cda9fa4368e9618c1907a03f9b20b7f93 22749 src/latent_triz/a0x_a0_analysis.py
6e862c4b0d88a1450c86551d1309726e55fd16f7ef4f073b30146125ca566158 7361 src/latent_triz/a0x_apfs.py
a13ee843413e866bf66607051b4cd9672023787be1371f9d9c1758298399f65e 64804 src/latent_triz/a0x_ccp_executor.py
1c239ad09cc3e1999fe7950659232b6da8521d67bb828d5a584b6f4d2b0e1549 7989 src/latent_triz/a0x_compatibility.py
f068cd8a311fb5d8a8eb81a5c42c5eeffc4c3b2117ff0592613456bec2357094 23953 src/latent_triz/a0x_contract.py
8c7f52a69a41e0f8a9e946b0d023c4caa620420fef9bb7e9daa28d4454205b6f 34486 src/latent_triz/a0x_execution.py
c744ba0a1bc1eda4245c7b15665b1e860c76e021ed714a4fa9ab4c992101b454 48812 src/latent_triz/a0x_freeze.py
260e43a767dbc2e3f6a458d72cce81f1fa2385e2c73640f069680bfced552142 47086 src/latent_triz/a0x_gate_b_builder.py
d75d0862413e56fc37bd778b0becad49bf869734eb01d8b727a000f69118432f 8549 src/latent_triz/a0x_gate_contract.py
32e40b01360f80c5c95076c3775ab441f298f81150cc50f4696b72b68fd82424 21620 src/latent_triz/a0x_hosted_capture.py
e18dc826f46145dfd122ea96611cc790833a823c84d1609f82004c6a231006ae 11866 src/latent_triz/a0x_hosted_gate_a.py
fbb23c631250e5003fb90abdc39d486ae3ea232b4266d1120321ff60f8d512e9 24685 src/latent_triz/a0x_hosted_verifier.py
687430c80dfce9abf27dceef45b7a8a399c1ab2b85e9c3d4aba26582d1066576 22227 src/latent_triz/a0x_material_contract.py
36c7c235302f2daf492ac68a620d3d5b70996ea91538021ec730cc4c5c91870b 22254 src/latent_triz/a0x_material_runtime.py
efb1f64fd983202eb368e970a44e233e3f208b2ad35b8f442b0193b05063cbd6 14137 src/latent_triz/a0x_model_adapter.py
82f1ecbfdf6f30cc5b19a311ab1cd67c1a0592ffaf27651d4bda5719f097fe19 11618 src/latent_triz/a0x_pair.py
5cc13df65d2ad6b77287dbf9b830dd555bac37b968971885cc98ca28fe7addf1 42358 src/latent_triz/a0x_preflight.py
6c34a2ad17d251986b039a51e8633cbedea4d23484c5acf50cd4bc328529a852 41772 src/latent_triz/a0x_production_adapter.py
27bb51d3a0a2fecdab3cb217a2d8bfd0021c6a6727173de2787b618b56dbfc7c 1120 src/latent_triz/a0x_r1_activations.py
51d7cd8d0ccdac02b58b4ce820ed2aacb687b14814dcc82fe79f6e536ab130cc 16035 src/latent_triz/a0x_r1_analysis.py
e4dd89e479a8f392e074b952756d7c9f570a041e40d16fcb6f534c2e489585d9 31038 src/latent_triz/a0x_report.py
fcd7ec2c2eb110ab45a886f1998f8cef3d45848e72c62c6b34c160ff7690b9b8 87093 src/latent_triz/a0x_runner.py
2b5bf38e81f172afe1114409ca31cef872a7ca30bf3a9ae87ab027b6d6871f00 37486 src/latent_triz/a0x_runtime_bundle.py
78b4be282e8b6199a573c2ebb8af76dbb92da3e8d3863841512cc70dacc4fb95 14151 src/latent_triz/a0x_runtime_readiness.py
28061231fb1e03ca9ffda16444cab6aa2ac9b799075f95736dcf0c275810f5f7 9099 src/latent_triz/a0x_schema_projection.py
1ef8149e7daae1fd5499c73e2f16cf2b4422c3f179471e7bb69d3d716bfe4ada 27821 src/latent_triz/a0x_verify.py
9ec5306774927b12d277ea6b3994e8f1e39156c4d5e13610b6cf0bd9ff272629 47593 src/latent_triz/a0x_vertical_slice.py
229bdf84adf280e71f5d6d4b20d39d7019aa45812319d9948801318eb083c9ee 6571 src/latent_triz/a0x_wheelhouse.py
683667cc11a0ec5d7fbec5b725d4533aed9da6de45947841a50bc19007bc670a 37837 tests/a0x_test_support.py
938ac032b873565a64eaa201cc3783989584efe2ad821fffd8e311af838587c9 5758 tests/fixtures/a0x/ccp-matrix-v2-legacy-plan-27adf8d.json
8a14fb8bca982778c8759bd5c534cb14c159b0e845fb26dfb250e4d9eafa9334 2454 tests/fixtures/a0x/hosted-gate-a/positive/gate-b-authorization.json
fb35f3e2d410bf2a764de786b0251212fd49c345c520ca31d6e60c753e606687 2829 tests/fixtures/a0x/hosted-gate-a/positive/gh-2.97.0-verification-result.json
f0e9b434362ed1acb549b5cc3a1b6c6d39e06567e7cfb94c417e9273461657ff 473 tests/fixtures/a0x/hosted-gate-a/positive/transport.json
48189bbbbbb3af80cdf13275d46086a934c0e5256416baf48afbf8654b5f8208 2223 tests/fixtures/a0x/hosted-gate-a/positive/verification-receipt.json
e2e11f6bec9740d7e2025eae80fe87fa29d79436faa3a2c5c1ca7d55ceb9e4b4 413 tests/fixtures/a0x/hosted-gate-a/positive/verifier-policy.json
422f19c46b864a2d088e9624011d421b1ac7c77435e302456417b85e256f043b 20663 tests/test_a0x_a0_analysis.py
8f531a8f1ac7006c9b42ce98ebe7d3c676f049b251c903fe508a4cdbd309bbea 19092 tests/test_a0x_activations.py
d86698fe26985ad79263a89d3297371525776e68a40ca58748a557c56717cb2e 6278 tests/test_a0x_apfs.py
013897727eca3a7533f38f70dec57277fdb0a6ad2547593809801926cee5a958 4159 tests/test_a0x_architecture.py
f9bd6b249bd86db66d6a5374b5ba448b80446226e9d7128d33600d39df8c689a 15961 tests/test_a0x_capture_hosted_gate_a.py
2d636dfaf1f8cc77752d2419d1a85901beb439b3ebc79c5c4a37e1dba7cd270f 43992 tests/test_a0x_ccp_executor.py
f22db62509a437395b37716b7cfdca86346fa785f8b856e7121fd3ff540a7236 24796 tests/test_a0x_contract.py
7fd9eace4a3871337ad98114ed54e692be3398132a813302bc2efec9ecc5f43d 1261 tests/test_a0x_contract_check.py
03283b28c73db1a946ffeb98ac9854a9c18b014ef0ae3733075131651ecbd344 32955 tests/test_a0x_execution.py
4eccc59caba77c00924871075e419c4f2f689da9a052614d4de1f789eb5435e6 25572 tests/test_a0x_freeze.py
be4d01f706e744d26beed3a1d2d6d37c63eb21b40f524554b2996e25ba5ba43e 14415 tests/test_a0x_frozen_package.py
e887510d7d60d4a4c85d539f8b5b7eca219195c78b0bf65783816fb80c347065 33787 tests/test_a0x_gate_b_builder.py
eb5da4382207b6c78d04754bd47169788c28cb38e5b51b07bee827f33e5a6788 45422 tests/test_a0x_hosted_capture.py
93415a3537a68d7ffd9ff1284f588d316451617034dae31675b50883bbe3b113 6666 tests/test_a0x_hosted_gate_a.py
b41e05a253b5c3587eb0718eedc78ee202fe906173a13628e85f249c4ebbeb62 14410 tests/test_a0x_hosted_gate_a_workflow.py
9faf02cc9a0a99bedf4d60ad4383f4859a54c1bf49438059ca39205bc56a8858 39587 tests/test_a0x_hosted_verifier.py
dc1409b0bf8ce926ada85994628bdbde6996bb19d3a978408335beb608a2e3cf 2434 tests/test_a0x_material.py
8c22cef7155ec02026d9cfcdfce2300e6020f93465c3f4dc8bd0d408824f5987 29629 tests/test_a0x_material_child.py
bf96d53cfa6dda7d7fa9e6252d07701e00865510b4b1337de00982f3f9da3e33 19454 tests/test_a0x_material_contract.py
0b911a3baf6911839b97285f3d84cc1de48551516f76c5e016f31ac53cbdb558 24771 tests/test_a0x_material_runtime.py
bd1dc1443ea83396715a9f7b06a61e9416481d8ab350a71552d75397a1308f7a 5355 tests/test_a0x_matrix_plan_binding.py
bc00dc74c96cb1a870e1fabb75006189ae50df0c826bcf72b2f7ce70323d98f3 8411 tests/test_a0x_pair_compatibility.py
01973d65a983424c74202b692bc14b2313f26211bdb6a228132b70d080e639f2 27150 tests/test_a0x_preflight.py
e99b0167a39b7b2c780e895c7befa5ccfe1bf80e9125945124cc2ff4d04a203e 15991 tests/test_a0x_production_adapter.py
ab1d4d1c642a7a7b8c7a1a1222937775e38fd4898601315c4fe5236d166bb0f4 9904 tests/test_a0x_r1_analysis.py
8b7e0385270489ef06d640072381d84940e03af1d2a674c1366b289df7ec3b58 20956 tests/test_a0x_report.py
c27f52b1fadcd222c41da596dc9afd0ef013647f8c261908f84617250f667e6b 49533 tests/test_a0x_runner.py
0b41ce3fcf92c724269f568a017d1fa4290d34f8bdfcd949b8a395433210aebb 77812 tests/test_a0x_runtime_bundle.py
977b18c3167786777d3b19862ec1055c52b38112f5a36442e0c6af74fe066cb1 8229 tests/test_a0x_runtime_readiness.py
3d288de26eb5b701a7cabf6210769bf29f32e47f82856e47c142f6ed4208f976 16734 tests/test_a0x_schema_projection.py
503b2d12dd842dc1a1f4043bb23fe44f5e3cad9bce8b37c2ebd8ff6debd03c36 29146 tests/test_a0x_schemas.py
3d5d17fa16e45127622632447f319db1bce06c0d0829b972b7dc25f910ba4988 28401 tests/test_a0x_verify.py
4f8ab7493f9cfe86f21f6f494e9aec41cb6384579169b7fc07b651afe280c108 16994 tests/test_a0x_vertical_material.py
c2abe6b522b2527034ee037f31ed619886c86a62385c86c6d6853329a2fca987 31129 tests/test_a0x_vertical_slice.py
d56aad8b90d56a3961123cce768a1fe80aaa380f8a0a0ff479b0932cbe707fd8 5990 tests/test_a0x_wheelhouse.py
```

## Exact one-shot P0 command and stop boundary

The command template below is the only proposed P0 action. An independent
review must replace both identity placeholders with the exact final clean
commit and tree before authorization. The bootstrap refuses a mismatch before
repository imports or staging, fixes `A0 / smollm2_360m`, validates the exact
ledger, invokes the reviewed generator once, and prints its receipt as
canonical JSON.

```bash
rtk env -i PATH=/usr/bin:/bin LC_ALL=C /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -I -S -B -c '
import hashlib
import hmac
import os
import stat
import sys

MAXIMUM = 64 * 1024 * 1024
CODE = "A0X_VERTICAL_P0_BOOTSTRAP_IDENTITY_MISMATCH"

def refuse():
    print(f"a0x-vertical-p0-preexec: {CODE}", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]
expected_sha256 = sys.argv[2]
if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
    refuse()
try:
    before = os.lstat(path)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= MAXIMUM:
        refuse()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        raw = b"".join(iter(lambda: os.read(descriptor, 1024 * 1024), b""))
        final = os.fstat(descriptor)
    finally:
        os.close(descriptor)
except (AttributeError, OSError):
    refuse()
identity = (before.st_dev, before.st_ino, before.st_size)
if identity != (opened.st_dev, opened.st_ino, opened.st_size) or identity != (final.st_dev, final.st_ino, final.st_size):
    refuse()
if len(raw) != before.st_size or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
    refuse()
sys.argv = [
    path,
    *sys.argv[3:],
    "--preexec-bootstrap-device", str(opened.st_dev),
    "--preexec-bootstrap-inode", str(opened.st_ino),
    "--preexec-bootstrap-bytes", str(opened.st_size),
]
globals_for_script = {
    "__name__": "__main__",
    "__file__": path,
    "__package__": None,
    "__cached__": None,
}
exec(compile(raw, path, "exec", dont_inherit=True, optimize=0), globals_for_script, globals_for_script)
' /Users/marco1/.codex/worktrees/latent-triz-a0x-hosted-capture-20260901/scripts/a0x_vertical_p0_bootstrap.py fde8ca234ed9287f478bcfe2ea90aaa58822d6677e146cc74a6e886d1e3073a0 --repository-root /Users/marco1/.codex/worktrees/latent-triz-a0x-hosted-capture-20260901 --expected-head EXACT_FINAL_40_HEX_HEAD --expected-tree EXACT_FINAL_40_HEX_TREE --expected-python /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 --expected-python-sha256 3a1f077a333905eaac57197c9f2060ed95e05208daf83da4827d92e0474574d8 --expected-ledger-sha256 37301ed7234e91d2b13336505444864fddd85a789d7bf3db7a8ab713889acbfa --expected-bootstrap-sha256 fde8ca234ed9287f478bcfe2ea90aaa58822d6677e146cc74a6e886d1e3073a0 --expected-preexec-sha256 a0cc17b6d256ff03abfcd58e158d31ab0bffc1db497a2c400ed04bb16fc7483b
```

Authorization must bind the final clean HEAD/tree, this exact inline launcher
source and command, inline-source SHA-256
`a0cc17b6d256ff03abfcd58e158d31ab0bffc1db497a2c400ed04bb16fc7483b`,
worktree, absolute Python path and SHA-256, bootstrap path and committed
SHA-256, bootstrap profile `a0x-vertical-p0-bootstrap-v1`, pair
`A0 / smollm2_360m`, generator profile `a0x-vertical-slice-v1`, output root,
137-entry input-ledger digest, one invocation maximum, and the full same-UID
exclusion window defined above. The operator must revalidate the absolute
Python path/hash after that window starts and before launching this command.

Stop after the first terminal return, whether success, refusal, interruption,
cleanup uncertainty, or opaque failure. Do not retry. Do not invoke the
vertical material target,
Gate A, Gate B, Gate C, model/tokenizer/target/scoring code, CCP, Docker,
network/GitHub, batch regeneration, no-model receipt regeneration, push, PR,
merge, publication, or A0-R1. A successful P0 only permits read-only inspection
and hash recording of its five files; it does not authorize the next gate.
