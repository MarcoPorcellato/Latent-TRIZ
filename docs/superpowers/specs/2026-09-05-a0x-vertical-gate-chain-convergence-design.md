# A0X Vertical Gate-Chain Convergence Design

**Status:** approved in chat; implementation pending written-spec review  
**Date:** 2026-09-05  
**Scope:** target-free architecture correction for one A0X model/leg pair  
**Reviewed source:** `cfd6b49a8e0be84dec272cd57645b9faa53cf54c`  
**Reviewed tree:** `728b48e3096aa6b34632e26f3c791c217488edb2`

## Purpose

Make the A0X vertical sequence constructible for one protected-main source
without weakening source cleanliness, hosted provenance, one-shot execution,
or historical evidence.

The correction is operational only. It does not change the scientific corpus,
prompts, labels, controls, model revisions, statistical rules, endpoints,
resource limits, or claim envelope. It grants no Gate B, Gate C, model,
tokenizer, target, network, CCP, Docker, publication, or retry authority.

## Verified defect

The current `a0x-vertical-slice-v1` package is stored in a tracked path that
contains its `implementation_source_head`. P0 requires a clean checkout at that
head, but publishing the package changes the checkout head. Gate C later
requires the live checkout head to equal the pre-publication package head.
Gate B independently accepts only the historical twelve-dossier batch set.

The resulting identities cannot be made equal:

```text
P0 package head              f0f52d3...
historical batch Gate B      c074701...
current candidate source     cfd6b49...
future squash-merged main    a new, not-yet-known commit
```

This is an architecture defect, not a model, tokenizer, GitHub artifact, or
resource failure. A new package generated into the same tracked convention
would reproduce the cycle.

The current PR workflow is also not Hosted Gate A. It is the merge-policy
workflow and correctly emits no artifact. The real Hosted Gate A is a
push-to-protected-`main` workflow that uploads and attests its evidence.

## Decision

Introduce a future-only `a0x-vertical-slice-v2` execution package. Generate it
after Hosted Gate A under ignored, attempt-owned runtime storage. Bind it to the
exact protected-main `HEAD/tree` and to a separate external package commitment.
Gate B and Gate C must consume the same v2 dossier and package commitment.

Preserve every v1 package, batch dossier, freeze, receipt, report, and published
artifact byte-identically as historical evidence. No v1 or batch artifact may
be silently upgraded, reinterpreted, or accepted by the v2 material route.

## Rejected alternative

A tracked v2 package could distinguish a reviewed implementation head from a
later package-publication or squash-merge head. This is rejected for the
execution trust root because it adds two source identities, parent/diff proofs,
another Hosted Gate A cycle, and another opportunity for binding drift.

A tracked copy may later be published for inspection under a separate
publication envelope. It cannot retroactively authorize Gate B or Gate C.

## Canonical sequence

For protected-main source `H` and tree `T`:

```text
architecture correction merged to protected main H/T
  -> Hosted Gate A validates and attests H/T
  -> four hosted inputs captured under separate authorization
  -> P0 v2 generates one local package bound to H/T and one pair
  -> Gate B verifies hosted inputs and prepares the runtime from that package
  -> Gate C revalidates the same package and Gate B outputs
  -> one separately authorized material attempt
  -> target-free result verification and optional publication
```

Every arrow is a stop boundary. Completion of one stage never authorizes the
next stage.

## Source identity

`qualified_source` is the exact protected-main identity attested by Hosted
Gate A:

```json
{
  "head": "<40 lowercase hexadecimal characters>",
  "tree": "<40 lowercase hexadecimal characters>",
  "ref": "refs/heads/main"
}
```

P0, Gate B, and Gate C require the live checkout to remain clean at this exact
`HEAD/tree`. Ignored runtime files do not weaken the check: all tracked and
untracked non-ignored changes remain terminal refusals.

The source identity and package identity are different facts. Source identity
is provided by Git and Hosted Gate A. Package identity is provided by the
external commitment defined below.

## P0 v2 runtime package

P0 publishes one atomic envelope under:

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

The envelope, package, and commitment paths are derived together, not
caller-selected. P0 requires the final `<model-key>/` destination to be absent,
builds both children within one private sibling staging directory, and
publishes the complete envelope through one exclusive atomic rename. It fsyncs
the staged files, both staged directories, and the destination parent. It
never publishes the package and commitment separately and never overwrites,
repairs, resumes, or reuses a previous destination.

The envelope contains exactly `package/` and `p0-commitment.json`. `package/`
contains exactly the five canonical UTF-8 JSON members.
`slice-manifest.json` binds the source, pair, generator profile, member paths,
member sizes, and the hashes of the other four members. It does not hash
itself. Extra entries, partial staging, cleanup uncertainty, or ownership loss
are terminal refusals.

### External package commitment

`p0-commitment.json` is both the external commitment document and the durable
P0 terminal receipt. It contains the package commitment plus the P0
authorization ID, attempt ID, and generator/bootstrap identities. It does not
contain its own hash. Its raw SHA-256 is calculated after canonical
serialization. The package commitment is the SHA-256 of a domain-separated
canonical projection with this semantic content:

```json
{
  "profile": "a0x-vertical-package-commitment-v2",
  "qualified_source": {"head": "H", "tree": "T", "ref": "refs/heads/main"},
  "pair_binding": {"...": "the exact canonical PairBinding"},
  "members": [
    {"name": "protocol.json", "size": 0, "sha256": "..."},
    {"name": "implementation.json", "size": 0, "sha256": "..."},
    {"name": "freeze.json", "size": 0, "sha256": "..."},
    {"name": "approval-dossier.json", "size": 0, "sha256": "..."},
    {"name": "slice-manifest.json", "size": 0, "sha256": "..."}
  ]
}
```

Member order is fixed. The commitment is external to the five members, so no
self-hash cycle exists. The raw `p0-commitment.json` bytes, their SHA-256, and
the independently recomputed package commitment become inputs to Gate B and
Gate C. A crash cannot expose an accepted package without its matching
commitment because both are published in one envelope rename.

### Namespace threat model

Git does not attest ignored runtime bytes. The v2 runtime package therefore
uses the stronger local boundary already established for A0X runtime assets:

- trusted-root containment and descriptor-relative access;
- `O_NOFOLLOW`-equivalent refusal for every controlled path component;
- regular files only and `st_nlink == 1`;
- exact inode, size, canonical-byte, and SHA-256 checks;
- exclusive atomic publication into an absent destination;
- immediate package-commitment recalculation before Gate B and Gate C;
- refusal on missing, extra, reordered, replaced, symlinked, hardlinked, or
  non-regular members;
- explicit exclusion of untrusted same-user namespace mutators during each
  P0, Gate B, and Gate C validation window;
- ownership-loss refusal without deleting a possible replacement inode.

No broad clean-check exception is introduced.

## Versioned interfaces

Historical v1 interfaces remain read-only compatibility surfaces. New v2
interfaces are distinct and cannot fall back to v1 or batch behavior.

### Package APIs

The implementation provides equivalent typed interfaces to:

```python
@dataclass(frozen=True)
class VerticalRuntimePackageRequest:
    qualified_source_head: str
    qualified_source_tree: str
    leg: Leg
    model_key: str
    output_root: str

@dataclass(frozen=True)
class VerticalPackageBinding:
    envelope_path: str
    package_root: str
    commitment_path: str
    commitment_raw_sha256: str
    package_commitment_sha256: str
    dossier_path: str
    dossier_sha256: str
    qualified_source_head: str
    qualified_source_tree: str
    pair_binding: PairBinding

def generate_vertical_runtime_package(
    root: str | Path,
    request: VerticalRuntimePackageRequest,
) -> dict[str, object]: ...

def load_vertical_runtime_package(
    root: str | Path,
    binding: VerticalPackageBinding,
) -> dict[str, object]: ...
```

Names may be adjusted to existing local conventions, but the two versioned
roles and all fields above are mandatory. The three paths are derived from the
same source/pair selector and cannot be supplied independently.

### Gate B

Gate B receives one typed `VerticalPackageBinding`. It must not accept
`fixed_dossier`, a batch path, a v1 package, or a caller-selected dossier
without the external package commitment.

Before its verifier, readiness producer, child process, or first output, Gate B
must verify:

1. clean live `HEAD/tree == H/T`;
2. the four Hosted Gate A inputs and their authorization bind `H/T`;
3. the v2 package path, five members, commitment, dossier, pair, leg, model,
   revision, and material-contract hash;
4. all regular-file, link-count, canonical-byte, ownership, and hash rules;
5. the destination set is absent.

Its verification receipt, readiness receipt, descriptor, execution
authorization, and local mapping must all bind `H/T`, the package commitment,
and exact dossier SHA-256.

The historical batch preparer remains available only for historical read-only
verification or explicitly versioned compatibility tests. It is not a fallback
for new A0X vertical work.

### Gate C

Gate C receives the same `VerticalPackageBinding`, plus the separately approved
Gate B output hashes and material-attempt authorization. It no longer treats a
pre-publication package head as a selector.

Immediately before any model factory, tokenizer construction, target read,
claim creation, or guard invocation, Gate C must revalidate:

1. clean live `HEAD/tree == H/T`;
2. the complete P0 package and external commitment;
3. exact dossier and pair bindings;
4. Gate B authorization and every Gate B output hash;
5. one-shot attempt identity, time/RSS/output limits, and current authorization;
6. no v1 or batch substitution.

Any package mutation between Gate B and Gate C is terminal refusal. No retry is
implied or authorized.

## Schemas and profiles

Create future-only profiles and schemas for:

- `a0x-vertical-slice-manifest-v2`;
- `a0x-vertical-package-commitment-v2`;
- `a0x-gate-b-verification-authorization-v2`;
- the execution-authorization revision required to bind the package commitment.

If the existing execution-authorization profile cannot gain these bindings
without changing its meaning, introduce a new version. Do not mutate the
meaning of an existing public profile in place.

## Mandatory target-free integration proof

Add a test using a real disposable Git repository, not a worktree and not a
mocked Git identity:

1. create and commit exact protected source `H/T`;
2. generate P0 v2 below ignored runtime storage;
3. prove `HEAD/tree` unchanged and `git status` clean;
4. load and verify the real package and external commitment;
5. construct synthetic Hosted Gate A inputs bound to `H/T`;
6. pass the package through real Gate B static/preparation boundaries, injecting
   only external capabilities that would otherwise contact GitHub or create a
   material runtime;
7. pass the resulting real documents through Gate C pre-material validation;
8. use an inert injected guard and prove at most one invocation;
9. prove zero model loads, tokenizer constructions, target reads, network
   operations, CCP invocations, and Docker operations.

The integration test must fail before verifier, readiness, or guard execution
for each mutation:

- any member byte, size, name, or order;
- external commitment drift;
- dossier or pair mismatch;
- wrong leg, model, or revision;
- source `HEAD` or tree drift;
- dirty source checkout;
- symlink, hardlink, non-regular, missing, or extra member;
- Hosted Gate A source mismatch;
- v1 package or batch-dossier substitution;
- occupied output;
- package mutation between Gate B and Gate C.

Component mocks may remain for component behavior, but they cannot satisfy the
full-chain acceptance criterion.

## Expected implementation surface

The correction is expected to touch only:

- `src/latent_triz/a0x_vertical_slice.py`;
- `src/latent_triz/a0x_runtime_bundle.py`;
- `src/latent_triz/a0x_ccp_executor.py`;
- `src/latent_triz/a0x_runner.py` where path derivation is shared;
- `scripts/a0x_prepare_runtime.py`;
- `scripts/a0x_vertical_material.py`;
- versioned A0X schemas and focused tests;
- A0X implementation inventories and generated artifacts after code is stable;
- canonical A0X runbooks, current status, persistent goal, engineering log,
  and the local `a0x-qualified-llm-lab` skill after repository behavior is
  proven.

Unrelated refactors are excluded.

## TDD order

1. Add the real-Git test that demonstrates the current chain is impossible.
2. Add package-path and external-commitment unit tests; observe RED.
3. Implement v2 package generation/loading; reach GREEN.
4. Add Gate B vertical-only selection and mutation tests; observe RED.
5. Implement typed v2 Gate B consumption; reach GREEN.
6. Add Gate C same-package and pre-material mutation tests; observe RED.
7. Implement v2 Gate C validation; reach GREEN.
8. Complete the real-Git chain without material capabilities.
9. Run focused, synthetic, schema, documentation, and full target-free suites.
10. Regenerate only implementation-bound inventories, freezes, dossiers, and
    receipts required by the existing hash graph.
11. Verify historical protected paths remain byte-identical.
12. Obtain independent Luna and Sol reviews before any push or material gate.

## Documentation reconciliation

After implementation, make one canonical current route:

```text
Hosted Gate A -> capture -> P0 v2 -> Gate B -> Gate C -> result verification
```

Mark the CCP/Matrix Gate A route, batch dossiers, and v1 tracked vertical
packages as historical. Update the current-status authority and problem/solution
log. Older checkpoints retain their historical values and labels.

## Acceptance criteria

The architecture correction is ready for publication only when:

- the real-Git target-free chain passes at one exact clean `H/T`;
- P0 leaves Git `HEAD/tree/status` unchanged;
- Gate B and Gate C consume one byte-identical v2 dossier and commitment;
- every mutation case refuses before an external or material capability;
- no v1 or batch fallback exists;
- existing historical artifacts are byte-identical;
- implementation inventories and derived A0X artifacts are regenerated only
  after the implementation commit;
- focused, synthetic, schema, documentation, and complete target-free suites
  pass;
- independent review finds no weakened binding or unrecorded capability;
- the exact local HEAD/tree and all regenerated hashes are recorded;
- no model, tokenizer, target, scoring, CCP heavy command, Docker, or scientific
  execution has occurred.

## Post-merge stop boundaries

After the correction merges, wait for the push-only Hosted Gate A on the new
protected-main commit. Capture requires a new exact authorization. P0 v2 then
requires its own authorization. Gate B and Gate C remain separate later
authorizations. No current artifact or earlier authorization carries forward.
