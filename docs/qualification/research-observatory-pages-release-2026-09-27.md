# Research Observatory GitHub Pages release and operation note

## Release identity

- Public site: <https://marcoporcellato.github.io/Latent-TRIZ/>
- Verification: HTTPS returned status `200`.
- Source commit: `0fd314215003357dedfb14d3ad1ab614efb8992a`.
- Source tree: `fb4d55e69033a3bded37ba0fa6fe66c58ac52a69`.
- Public `site-data.json` SHA-256: `916fde737652071da129351e2b65662aad066fe06868faf0b26ec2d87a74c20b`.
- GitHub Actions build/deploy workflow run: [36318471059](https://github.com/MarcoPorcellato/Latent-TRIZ/actions/runs/36318471059), successful.
- Export inventory: 66 admitted sources, 35 observations, and 3 registered E0 claims.

These values identify the reviewed deployment snapshot. They do not establish
scientific validity or imply that the public site tracks later commits.

## Browser quality checks

Chrome inspection covered all six views: Start here, Experiments × models,
What results mean, Scientific route, Decisions and lessons, and Explore
sources. At 375px and 320px viewport widths, no horizontal overflow was
observed. Keyboard navigation, visible focus, accessible names, roles, and
states were inspected. This was a browser/accessibility-tree check, not a full
accessibility certification or screen-reader evaluation.

## Operating boundary

GitHub Pages publishes a derived, static snapshot. Browser code does not poll
GitHub; newly admitted repository changes appear only after a later successful
build and deployment. The local optional Marimo app is a separate read-only
view and does not provide deployment freshness. Neither surface is canonical
research evidence: maintained repository records, schemas, result manifests,
receipts, and deterministic verifiers remain authoritative.

Issue [#119](https://github.com/MarcoPorcellato/Latent-TRIZ/issues/119) tracks
the separate future work for dynamic updates. Until that work is implemented
and independently verified, describe Pages as a curated snapshot, not a live
monitor.
