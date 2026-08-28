# A0X material composition correction final review

## Verdict

**APPROVE for the completed offline tranche.** This verdict does not qualify
the selected CCP producer and does not authorize or report a material run.

## Reviewed identity

- Implementation anchor: `3dc40aa104358a83855cd59a40df30319131ea1e`
- Implementation tree: `4de3f2f704935d388d0b806dbf9a71cfa7d398e3`
- Selected CCP source: `a73ebed945d9d9e9744c4aff987589f3478a7f3c`
- Selected CCP tree: `b12ff9ac9daa67d52e28c6793e14f646c5e37225`
- Selected CCP binary SHA-256:
  `2f7fe3fce7d44cdd8350c0248f1c3b5b5c9fc4d023c05adcdb320d41785fa45f`
- Selected CCP plan-output SHA-256:
  `4f401a3c13d94c48c722137511515bdb70099b596bbdb9756ec2cb491282e9e`

## Independent findings

- Timeout bindings are uniform: 3,600 seconds outer, 3,300 seconds internal,
  300 seconds reserved for sealing and cleanup, and 300 seconds admission.
- Guard preflight has exactly six configuration-free roles and does not use
  repository `plan`, `doctor`, or `dry-run` as guard prerequisites.
- Public commitments contain hashes and stable roles; local paths and runtime
  authority remain private.
- The source binding is acyclic: regenerated dossiers bind the implementation
  anchor, while later execution authorization must bind the then-current exact
  execution HEAD.
- CCP receipt semantic identity and raw file SHA-256 are distinct bindings.
- No previous `c91915ad...` or `72a34589...` CCP identity remains in active
  source or material experiment artifacts.
- Hard-coded CCP identity is intentional fail-closed behavior for this exact
  campaign candidate.

## Verification evidence

- Synthetic aggregate: 245 PASS; three documented dependency skips.
- Frozen package: 10/10 PASS.
- Documentation audit: PASS.
- `git diff --check`: PASS.
- Offline-tranche counters: zero CCP heavy commands, Docker/OrbStack actions,
  model loads, material tokenizer constructions, protected-target reads,
  network actions, or remote mutations.

## Canonical artifact hashes

- Material contract:
  `e4ab21c24a491a26e43b07be4cbc0102a84c7482cc425883ca5bda38ba988e1a`
- A0 protocol:
  `42e252b21dd9f1d6b793be304bfe708d2d9324e8e08ffe1d1915e7f01b75f586`
- A0 implementation:
  `886a2ec13b64ed376b443e36426322d64b59b6b38293484dfd0e2ed4e688efd5`
- A0 freeze:
  `8817b260737f558259ad5091858513e0f7a156ec751e6191d077a5bdde057aee`
- A0-R1 protocol:
  `32d8bbfcbd76e38d51a2eff012c22e65bfe0c1eca4f6d0bf345f309777df4b52`
- A0-R1 implementation:
  `4467bc8d07b18372b9467e613ad54323a498dcc121f62ba3da01493e46d4459c`
- A0-R1 freeze:
  `c1f43cfc834b788c45c90c66ab4602ccd3836c6da0b97b1fc4272089e05b19df`
- No-model verification receipt:
  `c761ae76d77b976ea83bc83aa139da9730858a387422aff501ffad1b87217e4c`

### A0 approval dossiers

- GPT-2: `526e3f86dcf6a0749afb578ad18ecd3f728c49c044f2b2a01408adc9534acf26`
- GPT-Neo 125M: `0332331604f1f20ea752f186d3d5eff99f5e067e3e06017ab5fa5a5478721830`
- Qwen2.5 0.5B: `c3ea7d33e28a88819d2b74dda2ed35d788312b4a4c17040b4b43caef25942916`
- Qwen3 0.6B Base: `9a8afb0bdefa7a2f84b50269c6d9df36269a6eeab7ba3819c3bb0a25e702b326`
- SmolLM2 135M: `02d211e42396c9d7b007409853b1d97473281a72ff3320e9b7113b0a034179df`
- SmolLM2 360M: `ca9baf450e7c6528b80a9ed9dd5ccd619f23477829c7a78ee28531c3bc55b59e`

### A0-R1 approval dossiers

- GPT-2: `ca2519b5ed92f25a792ac4679a8a0df682c212b779dc7c21ea4810eb6fdc5edf`
- GPT-Neo 125M: `5691cdadc19c14c17fe699c73c43433bb14e84299b49ed9512e7e0f49ef893d8`
- Qwen2.5 0.5B: `af2ed0739dfc144d6629753efc26c8e29cab6edc9334f39f79463cf99daf348a`
- Qwen3 0.6B Base: `0cb374df8a7e877a4df06bd3dedbbda1d53a87eaff9eb2b311aa90a6db0145d4`
- SmolLM2 135M: `f3acc82247c614790d84cc66110c7436bdeb1daecb4ab8f50b862cf09f4b46f1`
- SmolLM2 360M: `d930d2eda9385f5d44d3e30e3f28d1003f58042f0273758818072a8852b2de2b`

## Stop boundary

The next allowed step requires a new exact authorization for qualification of
the selected CCP candidate. No material model or target action is authorized
by this review.
