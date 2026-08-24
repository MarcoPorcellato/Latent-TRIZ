# A0X Six-Model Replication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and synthetically qualify the immutable A0X-A0 and A0X-R1 replication system for six exact non-Pythia models, then prepare twelve separately approvable one-shot material runs.

**Architecture:** A0X is an additive namespace with one shared immutable-contract and model-adapter layer, two leg-specific activation and statistical paths, and one capability-based execution boundary that prevents activation from opening sealed targets. The implementation reuses verified numeric ideas from A0 and A0-R1 by copying them into newly tested A0X modules; it does not mutate or import writable state from historical result packages. A single plan is appropriate because both legs depend on the same protected-tree, model-card, target-reader, terminal-envelope, and publication contracts and cannot be qualified independently of those shared fail-closed boundaries.

**Tech Stack:** Python 3.11/3.12, standard-library `unittest`, JSON Schema through `latent_triz.validator`, NumPy for frozen statistics, PyTorch/Transformers/Safetensors only behind the authorized material boundary, Make, commit-ci-preflight (CCP).

**Spec:** [`docs/superpowers/specs/2026-08-24-a0x-six-model-replication-design.md`](../specs/2026-08-24-a0x-six-model-replication-design.md)

**Spec binding:** Git commit `2b718c2f12d70ee5e4580130ac14769766238016`; document SHA-256 `4573931ed3ee5b08a5022c90a781d1f3c51f92d4f60678c41357cc5746f467ff`.

## Global Constraints

- Base every freeze on public `origin/main` exactly `188eb65b5e249923baddadeba52659f07fcd1609`; drift stops freeze or material work and requires review.
- Preserve every byte in the historical A0 and A0-R1 protected trees and their publication-manifest external assets.
- Use only the six exact model IDs, 40-character revisions, and runtime roots in the approved design; never resolve aliases or latest revisions.
- Treat each `(leg, exact-model-revision)` as one authorization, execution, analysis, terminal package, and publication unit: exactly twelve independent one-shot runs.
- Run only local CPU `float32` with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `local_files_only=True`, and `trust_remote_code=False`; generation, chat templates, network, fallback, quantisation, tuning, batching changes, and retry are forbidden.
- A0X-A0 primary endpoints are hidden-state tuple indices `0, 2, 4, 6`; A0X-R1 primary is tuple index `6`; tuple index zero is the embedding output.
- The final-transformer-block endpoint is descriptive only and may never change a primary statistic, status, threshold, or interpretation.
- A0X-A0 maximum new dense/index bytes are `33,554,432`; A0X-R1 maximum new dense/index bytes are `4,194,304`; both have `1,800` seconds and `8,589,934,592` bytes peak-RSS limits.
- Activation receives no target path or target-reader capability and must record `activation_target_content_reads: 0`.
- A valid analysis may read the exact frozen target once and must record `analysis_target_content_reads: 1`; pre-analysis terminal outcomes record `0` and contain no statistical result.
- Publish the first terminal outcome for every authorized pair: `positive`, `null`, `non_interpretable`, `incompatible`, or `failed`.
- Do not pool, rank, average, vote, meta-analyse, or combine p-values across legs or models; keep `expert_validated: false`, `evidence_eligible: false`, and `claim_ids: []`.
- No task before Task 11 may load a model, construct a material tokenizer, read sealed-target bytes, invoke CCP, use the network, or publish remotely.
- The preserved untracked R5 directories `experiments/exp002-auto-partial-recovery/`, `results/exp002-auto-partial-recovery/`, and `tmp/` are outside A0X and must never be staged by broad Git commands.
- Prefix every shell command with `rtk`; stage exact paths only.

## Model Routing and Review Ownership

- GPT-5.6 Terra owns Tasks 1-11 as primary implementer because they contain
  access-control, schema, statistics, architecture, and release-governance
  decisions. A Luna worker must not take an entire task and decide those
  contracts independently.
- GPT-5.6 Luna may perform only bounded deterministic substeps after Terra has
  frozen the exact inputs and expected outputs: run named synthetic tests,
  validate schemas, compare hashes, execute `git diff --check`, run
  `docs-audit`, and mechanically update tables or receipts from already
  verified data.
- After Task 11, Luna may invoke one fixed argument-free material Make target
  only after an exact operator authorization exists and a Terra/Sol reviewer
  has confirmed the dossier, CCP binary binding, live Admit observation,
  inactive admission, and empty queue. Luna does not interpret or publish the
  result independently.
- Architecture, statistics, security, any exception, dossier regeneration,
  scientific interpretation, CCP qualification, publication, and merge remain
  with Terra or Sol.

## File Map

| File | Single responsibility |
| --- | --- |
| `src/latent_triz/a0x_contract.py` | Immutable enums, dataclasses, fixed endpoint/cap constants, canonical hashing, and cross-model non-pooling checks |
| `src/latent_triz/a0x_freeze.py` | Protected-tree, public A0 selection, model-card, and freeze construction/verification |
| `src/latent_triz/a0x_preflight.py` | Static snapshot, output emptiness, offline environment, CCP observation, authorization, and dense-bound checks |
| `src/latent_triz/a0x_model_adapter.py` | Exact local multi-architecture tokenizer/model loading and hidden-state extraction |
| `src/latent_triz/a0x_a0_activations.py` | A0X-A0 view/site/endpoint extraction and bounded atomic dense/index writes |
| `src/latent_triz/a0x_r1_activations.py` | A0X-R1 primary/baseline/final-block extraction and bounded atomic dense/index writes |
| `src/latent_triz/a0x_execution.py` | State machine and one-shot target-reader capability |
| `src/latent_triz/a0x_a0_analysis.py` | Frozen A0 family-blocked max-statistic primary plus descriptive sensitivity |
| `src/latent_triz/a0x_r1_analysis.py` | Frozen R1 fixed-primary permutation/domain-direction analysis plus descriptive sensitivity |
| `src/latent_triz/a0x_report.py` | Terminal report and immutable package generation |
| `src/latent_triz/a0x_verify.py` | Independent package, external-asset, protected-tree, and non-pooling verification |
| `src/latent_triz/a0x_runner.py` | One-pair one-shot orchestration; no model selection or fallback |
| `scripts/a0x_contract_check.py` | Synthetic and frozen no-model verifier used by repository checks |
| `scripts/a0x_material.py` | Fixed-dossier material entrypoint used only behind per-pair Make targets |
| `schemas/a0x-*.schema.json` | Strict schemas for every frozen, authorization, receipt, result, and publication artifact |
| `experiments/a0x-six-model/` | Frozen protocols, model cards, protected trees, selection manifest, and twelve dossiers |
| `results/a0x/<leg>/<model-key>/<run-id>/` | One immutable terminal package per pair |
| `artifacts/a0x/<leg>/<model-key>/<run-id>/` | External dense asset and representation index for one pair |
| `tests/test_a0x_*.py` | Synthetic and fail-closed TDD coverage only until material approval |
| `tests/a0x_test_support.py` | Shared synthetic pair-binding and artifact builders; never production data |

## Test Fixture Helper Contracts

The following names are test-only helpers, not production interfaces. Each is
defined in the named test/support file so a worker never depends on an
undeclared fixture:

- `tests/test_a0x_model_adapter.py`: `gpt2_card() -> ModelCard`,
  `fake_config(calls) -> object`, `fake_tokenizer(calls) -> object`,
  `fake_model(calls) -> object`, `FakeTorch`, and
  `synthetic_adapter(*, num_hidden_layers: int, width: int) -> A0XHiddenStateAdapter`.
- `tests/test_a0x_activations.py`:
  `synthetic_hidden_adapter(*, layers: int, width: int) -> object`,
  `public_cases() -> list[dict[str, object]]`,
  `selection_manifest() -> dict[str, object]`, `oversized_adapter() -> object`,
  and `synthetic_occupied_tree(root: Path, *, total_bytes: int) -> Path`.
- `tests/test_a0x_preflight.py`:
  `valid_ccp_raw_observations() -> tuple[dict[str, object], dict[str, object]]`,
  `valid_ccp_binary_binding() -> dict[str, str]`, and
  `stable_json_bytes(value: object) -> bytes` provide exact synthetic CCP v4
  observations without reading host admission state.
- `tests/test_a0x_a0_analysis.py`:
  `synthetic_a0_inputs(*, primary_signal: float, final_signal: float = 0.0,
  root: Path | None = None) -> dict[str, object]` writes a complete 48-case,
  24-family, six-domain synthetic dense/index fixture and returns keyword
  arguments for `analyze_a0x_a0`.
- `tests/test_a0x_r1_analysis.py`:
  `synthetic_r1_inputs(*, primary_signal: float = 0.0,
  final_signal: float = 0.0, p: float | None = None,
  margin: float | None = None, successes: int | None = None,
  domains: int | None = None, root: Path | None = None) -> dict[str, object]`
  writes the corresponding fixed-primary fixture and supports explicit
  threshold-boundary injection.
- `tests/test_a0x_report.py`: `terminal_fixture(*, status: str, root: Path) -> dict[str, object]`.
- `tests/test_a0x_verify.py`: `published_fixture(root: Path) -> tuple[Path, Path]`.
- `tests/test_a0x_runner.py`: `synthetic_dossier(root: Path, *, leg: str,
  model_key: str) -> Path`, `failing_adapter`, and `working_adapter`.
- `tests/a0x_test_support.py`: `synthetic_pair_binding(*, leg: str = "a0",
  model_key: str = "gpt2") -> PairBinding` supplies one complete internally
  consistent binding and is imported by other A0X test modules.
  `A0XTempTestCase(unittest.TestCase)` creates a fresh
  `TemporaryDirectory` in `setUp`, exposes it as `self.tmp_path`, and removes
  it in `tearDown`; every snippet using `self.tmp_path` subclasses this class.

All helper-generated paths live under `tempfile.TemporaryDirectory`; helpers
must not reference repository target files, runtime model roots, CCP state, or
the network.

---

### Task 1: Immutable Contract Types and Strict Schemas

**Files:**
- Create: `src/latent_triz/a0x_contract.py`
- Create: `schemas/a0x-model-card.schema.json`
- Create: `schemas/a0x-protected-tree.schema.json`
- Create: `schemas/a0x-selection-manifest.schema.json`
- Create: `schemas/a0x-protocol.schema.json`
- Create: `schemas/a0x-implementation.schema.json`
- Create: `schemas/a0x-freeze-manifest.schema.json`
- Create: `schemas/a0x-authorization-dossier.schema.json`
- Create: `schemas/a0x-execution-authorization.schema.json`
- Create: `schemas/a0x-model-identity-receipt.schema.json`
- Create: `schemas/a0x-ccp-observation.schema.json`
- Create: `schemas/a0x-preflight-receipt.schema.json`
- Create: `schemas/a0x-activation-receipt.schema.json`
- Create: `schemas/a0x-target-read-receipt.schema.json`
- Create: `schemas/a0x-output-occupancy-receipt.schema.json`
- Create: `schemas/a0x-representation-record.schema.json`
- Create: `schemas/a0x-statistical-result.schema.json`
- Create: `schemas/a0x-terminal-result.schema.json`
- Create: `schemas/a0x-publication-manifest.schema.json`
- Create: `tests/a0x_test_support.py`
- Test: `tests/test_a0x_contract.py`
- Test: `tests/test_a0x_schemas.py`

**Interfaces:**
- Consumes: no A0X code; only standard-library types and `latent_triz.validator.validate` in tests.
- Produces: `A0XContractError`, `LegContractIdentity`, `LegFreezeBinding`, `PairBinding`, `Leg`, `TerminalStatus`, `ModelCard`, `DenseBound`, `canonical_json_sha256`, `sha256_file`, `endpoint_indices`, `compute_dense_bound`, `build_leg_freeze_binding`, `assert_leg_freeze_binding`, `assert_pair_binding`, `assert_single_pair`, and strict protocol/implementation/dossier/authorization/identity/CCP/terminal schemas used by every later task.

- [ ] **Step 1: Write failing constant, cap, and non-pooling tests**

```python
from latent_triz.a0x_contract import Leg, assert_single_pair, compute_dense_bound, endpoint_indices

def test_exact_endpoints_and_dense_bounds(self) -> None:
    self.assertEqual((0, 2, 4, 6), endpoint_indices(Leg.A0))
    self.assertEqual((6,), endpoint_indices(Leg.R1))
    self.assertEqual(28_049_408, compute_dense_bound(Leg.A0, cases=48, hidden_width=1024).total_bytes)
    self.assertEqual(3_145_728, compute_dense_bound(Leg.R1, cases=48, hidden_width=1024).total_bytes)

def test_cross_pair_collection_is_rejected(self) -> None:
    rows = [
        {"leg": "a0", "model_key": "gpt2"},
        {"leg": "a0", "model_key": "smollm2_135m"},
    ]
    with self.assertRaisesRegex(A0XContractError, "exactly one leg/model pair"):
        assert_single_pair(rows)
```

- [ ] **Step 2: Run the focused tests and confirm import failure**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_contract tests.test_a0x_schemas -v`

Expected: FAIL because `latent_triz.a0x_contract` and the A0X schemas do not exist.

- [ ] **Step 3: Implement the immutable public contract**

```python
class Leg(StrEnum):
    A0 = "a0"
    R1 = "r1"

@dataclass(frozen=True)
class DenseBound:
    leg: Leg
    cases: int
    view_site_count: int
    endpoint_count: int
    hidden_width: int
    scalar_bytes: int
    vector_count: int
    dense_bytes: int
    dense_copy_count: int
    atomic_dense_bytes: int
    index_copy_count: int
    index_reservation_bytes: int
    payload_allowance_bytes: int
    total_bytes: int
    cap_bytes: int

def endpoint_indices(leg: Leg) -> tuple[int, ...]:
    return (0, 2, 4, 6) if leg is Leg.A0 else (6,)

def compute_dense_bound(leg: Leg, *, cases: int, hidden_width: int) -> DenseBound:
    vectors = 48 * 10 * 5 if leg is Leg.A0 else 48 * 2 * 2
    dense = vectors * hidden_width * 4
    index_bytes = 6_291_456 if leg is Leg.A0 else 1_048_576
    payload_bytes = 2_097_152 if leg is Leg.A0 else 524_288
    cap = 33_554_432 if leg is Leg.A0 else 4_194_304
    total = dense * 2 + index_bytes + payload_bytes
    if cases != 48 or hidden_width <= 0 or total > cap:
        raise A0XContractError("dense output reservation exceeds frozen contract")
    return DenseBound(
        leg, cases, 10 if leg is Leg.A0 else 2,
        5 if leg is Leg.A0 else 2, hidden_width, 4, vectors,
        dense, 2, dense * 2, 2, index_bytes, payload_bytes, total, cap,
    )
```

The schemas must use `additionalProperties: false`, exact `const` values for the epistemic boundary, 64-character lowercase SHA-256 patterns, 40-character revision patterns, repository-relative paths without `..`, and status-specific `oneOf` branches that prohibit a statistical result for pre-analysis `failed` or `incompatible` outcomes.

Define a non-hash `LegContractIdentity` with `leg`, `protocol_id`,
protected-tree SHA-256, selection/corpus SHA-256, and exact source-base commit.
The protocol and implementation documents contain that identity and never
contain their own SHA-256, a model, run, dossier, authorization, or output
path. The freeze manifest contains the same identity plus the already computed
protocol and implementation SHA-256 values; it never contains its own hash.

`build_leg_freeze_binding(protocol_path, implementation_path, freeze_path)`
constructs `LegFreezeBinding` externally after all three files are immutable.
It contains `leg`, `protocol_id`, the protocol/implementation hashes recorded
inside the freeze, the freshly computed freeze SHA-256, protected-tree hash,
selection/corpus hash, and source-base commit. No shared artifact embeds this
derived binding, so there is no self-hash or fixed-point contract.

Define a per-run `PairBinding` under profile `a0x-pair-scope-v2` with `leg`,
`leg_freeze_sha256`, `model_key`, `model_id`, `revision`, `run_id`,
`output_path`, and the complete serialized `DenseBound`. It contains no
dossier or authorization self-hash. Every dossier, authorization, identity
receipt, CCP observation, activation receipt, target-read receipt, occupancy
receipt, statistical result, terminal result, report input, and publication
manifest must contain that stable binding.

Define a directional approval chain outside `PairBinding`. Canonically commit
the complete validated dossier with profile `a0x-approval-dossier-json-v1`
and a dossier-specific domain separator. The authorization contains that
dossier commitment but never its own commitment. Canonically commit the
complete validated authorization with profile
`a0x-execution-authorization-json-v1` and a distinct domain separator. Every
post-authorization artifact carries both commitments in an identical strict
`authorization_chain`; the publication manifest also binds the two source
files' raw byte hashes. Canonical parsing rejects BOMs, duplicate object keys,
floats, NaN/Infinity, and unsupported scalar types. The repository-defined
sorted-key encoding is versioned and must not be described as RFC 8785.
`assert_leg_freeze_binding` reconstructs the derived binding and proves that
every dossier names the correct shared leg and exact freeze hash.
`assert_pair_binding(root, referenced_artifacts)`
then walks every per-pair referenced JSON artifact and rejects any unequal
field; structural equality, not keyword scanning, is the primary no-pooling
enforcement. `assert_authorization_chain` independently recomputes the dossier
and authorization commitments, verifies the directional link, and recursively
rejects any downstream chain mismatch before interpretation.

- [ ] **Step 4: Add valid fixtures and one mutation rejection per schema**

Use helper builders in `tests/test_a0x_schemas.py`; for every schema, validate one complete artifact and then mutate one required invariant (`claim_ids`, hash length, read counter, leg, model key, revision, run ID, commitment profile/hash, authorization-chain link, output path, cap allocation, status/result compatibility, or absolute path) and assert at least one validator error. Pin exact dossier and authorization commitment vectors; prove whitespace/key-order equivalence, semantic-mutation drift, and rejection of duplicate keys, BOMs, floats, legacy self-hash fields, and cross-pair substitutions. Add a recursive fixture where a valid publication manifest references a receipt with one altered model key or authorization commitment and prove the corresponding binding verifier rejects it even though both individual documents pass their schemas. Serialize protocol and implementation, hash both, write the freeze manifest containing those two hashes, hash the freeze externally, reconstruct `LegFreezeBinding`, and reverify all three without any fixed-point exception. Add six valid dossiers that share the derived A0 binding, then mutate one dossier to reference the R1 leg or a different freeze hash and prove `assert_leg_freeze_binding` rejects it.

- [ ] **Step 5: Run focused tests and all existing schema tests**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_contract tests.test_a0x_schemas tests.test_a0r1_output_schemas tests.test_a0r1_freeze_schemas -v`

Expected: PASS.

- [ ] **Step 6: Commit exact Task 1 paths**

```bash
rtk git add -- src/latent_triz/a0x_contract.py schemas/a0x-model-card.schema.json schemas/a0x-protected-tree.schema.json schemas/a0x-selection-manifest.schema.json schemas/a0x-protocol.schema.json schemas/a0x-implementation.schema.json schemas/a0x-freeze-manifest.schema.json schemas/a0x-authorization-dossier.schema.json schemas/a0x-execution-authorization.schema.json schemas/a0x-model-identity-receipt.schema.json schemas/a0x-ccp-observation.schema.json schemas/a0x-preflight-receipt.schema.json schemas/a0x-activation-receipt.schema.json schemas/a0x-target-read-receipt.schema.json schemas/a0x-output-occupancy-receipt.schema.json schemas/a0x-representation-record.schema.json schemas/a0x-statistical-result.schema.json schemas/a0x-terminal-result.schema.json schemas/a0x-publication-manifest.schema.json tests/a0x_test_support.py tests/test_a0x_contract.py tests/test_a0x_schemas.py
rtk git commit -m "feat: define immutable A0X contracts"
```

### Task 2: Protected Historical Trees and Target-Free A0 Selection

**Files:**
- Create: `src/latent_triz/a0x_freeze.py`
- Create: `tests/test_a0x_freeze.py`
- Create: `tests/fixtures/a0x/public-cases-mini.jsonl`
- Create: `tests/fixtures/a0x/public-manifest-mini.json`
- Create: `experiments/a0x-six-model/protected-a0-tree.json`
- Create: `experiments/a0x-six-model/protected-a0r1-tree.json`
- Create: `experiments/a0x-six-model/a0-selection-manifest.json`

**Interfaces:**
- Consumes: `sha256_file`, `canonical_json_sha256`, and schema invariants from Task 1.
- Produces: `build_protected_tree`, `verify_protected_tree`, `build_a0_selection_manifest`, `verify_a0_selection_manifest`, and a deterministic module `main` for the declared write operations.

- [ ] **Step 1: Write failing protected-tree and selection tests**

```python
def test_selection_uses_public_cases_only_and_is_deterministic(self) -> None:
    manifest = build_a0_selection_manifest(
        cases_path=FIXTURES / "public-cases-mini.jsonl",
        corpus_manifest_path=FIXTURES / "public-manifest-mini.json",
    )
    self.assertEqual(48, len(manifest["cases"]))
    self.assertEqual(
        ["agriculture_01_a", "agriculture_01_b"],
        [row["case_id"] for row in manifest["cases"][:2]],
    )
    assert all("operator_proxy_family" not in row for row in manifest["cases"])
    assert manifest["target_content_reads"] == 0

def test_protected_tree_detects_one_byte_drift(self) -> None:
    tree = build_protected_tree(self.tmp_path, roots=(Path("historical"),), external_assets=())
    (self.tmp_path / "historical/input.json").write_text("changed", encoding="utf-8")
    with self.assertRaisesRegex(A0XFreezeError, "protected input drift"):
        verify_protected_tree(self.tmp_path, tree, phase="postflight")

def test_protected_tree_never_opens_declared_target(self) -> None:
    target = self.tmp_path / "data/a0/sealed-targets/targets.jsonl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"must-not-be-opened")
    declarations = {
        "data/a0/sealed-targets/targets.jsonl": {
            "sha256": "8b820294103ce748f65b49aa46e2e85ce584add8c058bb2d4129aadf366e7162",
            "bytes": 18,
            "provenance_manifest": "data/a0/manifest.json",
        }
    }
    with patch.object(Path, "open", side_effect=AssertionError("target opened")) as opened:
        tree = build_protected_tree(
            self.tmp_path, roots=(), external_assets=(), sealed_target_declarations=declarations,
        )
    opened.assert_not_called()
    self.assertEqual("declaration_only", tree["entries"][0]["verification_phase"])
```

- [ ] **Step 2: Run tests and verify missing-function failures**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_freeze -v`

Expected: FAIL because the freeze functions do not exist.

- [ ] **Step 3: Implement exhaustive manifest construction and verification**

`build_protected_tree` must enumerate files in sorted repository-relative order, record `path`, `bytes`, `sha256`, `provenance_manifest`, and `verification_phase`, reject symlinks/path escape, and require explicit external-asset entries. It accepts sealed-target entries only through a `sealed_target_declarations` mapping whose `sha256`, `bytes`, and `provenance_manifest` values come from the already frozen manifests named in the design. It must never call `open`, `read_bytes`, `stat`, or `sha256_file` on a sealed-target path during construction or preflight. `verify_protected_tree` hashes all non-target files in both `preflight` and `postflight`; before authorized analysis, sealed-target entries compare declaration strings and provenance-manifest hashes only. Deny/spy tests patch every filesystem read primitive for those exact paths.

`build_a0_selection_manifest` has no family-count parameter. It must load only `data/a0/cases.jsonl` and `data/a0/manifest.json`, group by the six frozen domains and `problem_family_id`, choose exactly the first four family IDs lexicographically per domain, preserve both cases per family, bind all 48 case-content hashes, and expose no target field or target path. Any corpus that cannot produce exactly 24 families and 48 selected cases fails closed. The synthetic public fixture therefore contains six domains, four families per domain, and two cases per family.

- [ ] **Step 4: Generate the three canonical manifests without opening targets**

Run: `rtk env PYTHONPATH=src python3 -m latent_triz.a0x_freeze --root . --write-protected-trees --write-a0-selection`

Expected: exactly three new JSON artifacts; stdout states `sealed_target_content_reads=0`.

- [ ] **Step 5: Verify canonical paths and historical bytes**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_freeze tests.test_a0r1_independence -v`

Run: `rtk git diff --check`

Expected: PASS; no historical A0/A0-R1 file appears in `rtk git diff --name-only`.

- [ ] **Step 6: Commit exact Task 2 paths**

```bash
rtk git add -- src/latent_triz/a0x_freeze.py tests/test_a0x_freeze.py tests/fixtures/a0x/public-cases-mini.jsonl tests/fixtures/a0x/public-manifest-mini.json experiments/a0x-six-model/protected-a0-tree.json experiments/a0x-six-model/protected-a0r1-tree.json experiments/a0x-six-model/a0-selection-manifest.json
rtk git commit -m "feat: freeze A0X protected inputs"
```

### Task 3: Six Exact Model Cards and Static Preflight

**Files:**
- Create: `src/latent_triz/a0x_preflight.py`
- Create: `tests/test_a0x_preflight.py`
- Create: `experiments/a0x-six-model/model-registry.json`
- Create: `experiments/a0x-six-model/model-cards/smollm2_360m.json`
- Create: `experiments/a0x-six-model/model-cards/qwen3_0_6b_base.json`
- Create: `experiments/a0x-six-model/model-cards/gpt2.json`
- Create: `experiments/a0x-six-model/model-cards/smollm2_135m.json`
- Create: `experiments/a0x-six-model/model-cards/gpt_neo_125m.json`
- Create: `experiments/a0x-six-model/model-cards/qwen2_5_0_5b.json`

**Interfaces:**
- Consumes: Task 1 contract types and Task 2 protected-tree verifier.
- Produces: `load_registry`, `load_model_card`, `verify_snapshot_files`, `verify_static_preflight`, `parse_ccp_observation`, and six immutable identity cards.

- [ ] **Step 1: Write six-card and drift tests**

```python
def test_registry_contains_only_six_non_pythia_cards(self) -> None:
    cards = load_registry(ROOT / "experiments/a0x-six-model/model-registry.json")
    assert tuple(card.model_key for card in cards) == (
        "smollm2_360m", "qwen3_0_6b_base", "gpt2",
        "smollm2_135m", "gpt_neo_125m", "qwen2_5_0_5b",
    )

def test_gpt2_requires_fast_runtime_type_and_offsets(self) -> None:
    card = load_model_card(ROOT / "experiments/a0x-six-model/model-cards/gpt2.json")
    assert card.tokenizer_class == "GPT2TokenizerFast"
    assert card.fast_offsets_required is True

def test_unknown_or_busy_ccp_fails_closed(self) -> None:
    resource, admission = valid_ccp_raw_observations()
    for mutator in (
        lambda r, a: r.update(decision="unknown"),
        lambda r, a: a.update(active=True),
        lambda r, a: a.update(queue_count=1),
        lambda r, a: a["slot"].update(state="unknown"),
    ):
        changed_resource, changed_admission = copy.deepcopy(resource), copy.deepcopy(admission)
        mutator(changed_resource, changed_admission)
        with self.assertRaises(A0XPreflightError):
            parse_ccp_observation(
                resource_raw=stable_json_bytes(changed_resource),
                admission_raw=stable_json_bytes(changed_admission),
                binary=valid_ccp_binary_binding(),
                pair_binding=synthetic_pair_binding(),
                output_dir=self.tmp_path / "ccp-observation",
            )
```

- [ ] **Step 2: Run tests and confirm failure before implementation**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_preflight -v`

Expected: FAIL because `a0x_preflight` and cards do not exist.

- [ ] **Step 3: Implement static fail-closed checks**

```python
def require_empty_output(path: Path) -> None:
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise A0XPreflightError(f"output destination is not empty: {path}")
```

`verify_snapshot_files` must accept only allowlisted regular files, compare size/SHA-256, parse `config.json` without constructing a model, verify model type/architecture/block count/width/vocabulary/context, and reject an extra or missing runtime file. Static preflight must validate offline environment variables, exact origin anchor supplied by the freeze, protected trees, literal/final layer availability, dense bound, dossier hash, authorization hash, empty output paths, and the canonical CCP observation below.

`parse_ccp_observation` is the only CCP JSON parser. Its reviewed source
contract is local `commit-ci-preflight` `origin/main`
`866db18a571f55ed3d9b481d6c9c9c3bd5e98d55`; Task 11 must refresh and bind a
new exact source commit if that remote-tracking reference changes. It receives
the exact raw stdout bytes from the dossier-bound binary through this exact
interface:

```python
def parse_ccp_observation(
    *, resource_raw: bytes, admission_raw: bytes,
    binary: Mapping[str, str], pair_binding: PairBinding,
    output_dir: Path,
) -> dict[str, object]:
    """Persist and validate one exact privacy-minimized CCP observation."""
```

It requires:

- binary absolute path, source commit, SHA-256, and complete `--version` output
  equal the dossier binding;
- resource top-level fields exactly `schema_version`, `policy_version`,
  `platform`, `capability`, `decision`, `available_percent`,
  `reclaimable_uncompressed_bytes`, `compressor_occupied_bytes`,
  `total_memory_bytes`, `swap_used_bytes`, `swap_total_bytes`, and
  `consecutive_soft_samples`;
- resource values `schema_version="1.0"`, `policy_version="macos-v4"`,
  `platform="macos"`, `capability="supported_enforced"`,
  `decision="admit"`, all six memory fields as non-negative integers with
  `available_percent <= 100`, `swap_used_bytes <= swap_total_bytes`, and
  `consecutive_soft_samples=0`;
- admission top-level fields exactly `schema_version`, `active`, `queue_count`,
  `ticket_ids`, `slot`, `queue_lock`, and `process_visibility_note`;
- admission values `schema_version="2.0"`, `active=false`, `queue_count=0`,
  `ticket_ids=[]`; both lock objects have their exact `kind`, `state="free"`,
  null owner/acquired/heartbeat fields, and `lease_state="not_applicable"`;
  the visibility note equals the string bound from the reviewed binary source.

Missing, additional, mistyped, differently cased, stale-policy, unsupported,
unknown, deny, held, queued, or inconclusive fields fail closed. The parser
writes `resource-status.raw.json` and `admission-status.raw.json` with exclusive
create semantics, records their byte counts and SHA-256 values, and embeds the
parsed privacy-minimized objects in the `a0x-ccp-observation` receipt. These raw
observations are retained as bounded evidence; raw process logs are not.

- [ ] **Step 4: Populate model cards from already registered receipts and official-audit records**

Copy literal ID/revision/root/config/tokenizer facts and allowlisted file receipts from tracked acquisition records. Do not scan the network or load tokenizer/model objects. Bind the source receipt path and SHA-256 in every card.

- [ ] **Step 5: Run all card mutations and static preflight tests**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_preflight tests.test_exp001_comparative_adapter tests.test_exp002_tokenizer_audit -v`

Expected: PASS, including GPT-2 fast-tokenizer, SmolLM2-135M tokenizer-class,
CCP field/type/casing/binary-hash/version/policy, and raw-observation mutation
cases.

- [ ] **Step 6: Commit exact Task 3 paths**

```bash
rtk git add -- src/latent_triz/a0x_preflight.py tests/test_a0x_preflight.py experiments/a0x-six-model/model-registry.json experiments/a0x-six-model/model-cards/smollm2_360m.json experiments/a0x-six-model/model-cards/qwen3_0_6b_base.json experiments/a0x-six-model/model-cards/gpt2.json experiments/a0x-six-model/model-cards/smollm2_135m.json experiments/a0x-six-model/model-cards/gpt_neo_125m.json experiments/a0x-six-model/model-cards/qwen2_5_0_5b.json
rtk git commit -m "feat: bind A0X model identity cards"
```

### Task 4: Multi-Architecture Hidden-State Adapter

**Files:**
- Create: `src/latent_triz/a0x_model_adapter.py`
- Create: `tests/test_a0x_model_adapter.py`

**Interfaces:**
- Consumes: `ModelCard` from Task 1 and the six static cards from Task 3.
- Produces: `A0XHiddenStateAdapter.load`, `A0XHiddenStateAdapter.tokenize_with_offsets`, and `A0XHiddenStateAdapter.forward_hidden`.

- [ ] **Step 1: Write synthetic loader and tuple-shape tests**

```python
def test_tokenizer_is_constructed_and_validated_before_model(self) -> None:
    calls: list[str] = []
    adapter = A0XHiddenStateAdapter.load(
        "/synthetic/gpt2", card=gpt2_card(),
        config_factory=lambda *_a, **_k: fake_config(calls),
        tokenizer_factory=lambda *_a, **_k: fake_tokenizer(calls),
        model_factory=lambda *_a, **_k: fake_model(calls),
        torch_module=FakeTorch(),
    )
    assert calls == ["config", "tokenizer", "offset-probe", "model"]
    assert adapter.model_loaded is True

def test_hidden_tuple_includes_embedding_and_final_block(self) -> None:
    payload = synthetic_adapter(num_hidden_layers=12, width=768).forward_hidden("Analysis anchor: x")
    assert len(payload.hidden_states) == 13
    assert payload.final_block_tuple_index == 12
    assert payload.hidden_states[6].shape == (1, payload.token_count, 768)
```

- [ ] **Step 2: Run tests and verify the adapter is absent**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_model_adapter -v`

Expected: FAIL on missing adapter.

- [ ] **Step 3: Implement exact local-only loading**

`load` must resolve a local path, call config and tokenizer factories with `local_files_only=True` and `trust_remote_code=False`, require the exact runtime tokenizer type, `is_fast=True`, and non-empty offset mappings on a frozen probe, then construct `AutoModelForCausalLM` with `torch_dtype=torch.float32`, move to CPU, call `eval`, and verify every parameter is CPU float32. The model call must set `output_hidden_states=True`, `output_attentions=False`, `use_cache=False`, and `return_dict=True`; no method named `generate` is invoked.

```python
@dataclass(frozen=True)
class HiddenPayload:
    input_ids: tuple[int, ...]
    attention_mask: tuple[int, ...]
    offsets: tuple[tuple[int, int], ...]
    special_tokens_mask: tuple[int, ...]
    hidden_states: tuple[object, ...]
    final_block_tuple_index: int
```

- [ ] **Step 4: Add one synthetic contract case for every architecture**

Test `llama`, `qwen3`, `gpt2`, `gpt_neo`, and `qwen2`, including both Llama widths/block counts. Reject wrong architecture, width, block count, tokenizer type, slow tokenizer, absent offsets, rank other than three, batch size other than one, non-finite hidden vectors, and tuple length other than `num_hidden_layers + 1`.

- [ ] **Step 5: Run adapter and existing comparative-adapter tests**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_model_adapter tests.test_exp001_comparative_adapter -v`

Expected: PASS without importing real model weights.

- [ ] **Step 6: Commit exact Task 4 paths**

```bash
rtk git add -- src/latent_triz/a0x_model_adapter.py tests/test_a0x_model_adapter.py
rtk git commit -m "feat: add A0X hidden-state adapter"
```

### Task 5: Leg-Specific Activation Extraction and Byte Caps

**Files:**
- Create: `src/latent_triz/a0x_a0_activations.py`
- Create: `src/latent_triz/a0x_r1_activations.py`
- Create: `tests/test_a0x_activations.py`

**Interfaces:**
- Consumes: Task 2 selection manifest, Task 4 `HiddenPayload`, and `src/latent_triz/a0_activation_sites.py` token-site selection.
- Produces: `extract_a0x_a0`, `extract_a0x_r1`, `ActivationArtifacts`, and activation receipts with zero target reads.

- [ ] **Step 1: Write failing endpoint, applicability, and cap tests**

```python
def test_a0_extracts_literal_and_final_endpoints_without_targets(self) -> None:
    artifacts = extract_a0x_a0(
        adapter=synthetic_hidden_adapter(layers=13, width=8),
        cases=public_cases(), selection=selection_manifest(),
        output_dir=self.tmp_path / "a0", created_at="2026-08-24T00:00:00Z",
    )
    assert artifacts.receipt["activation_target_content_reads"] == 0
    assert set(artifacts.receipt["literal_tuple_indices"]) == {0, 2, 4, 6}
    assert artifacts.receipt["final_block_tuple_index"] == 12

def test_synthetic_overflow_is_rejected_before_write(self) -> None:
    with self.assertRaisesRegex(A0XActivationError, "dense output cap"):
        extract_a0x_r1(adapter=oversized_adapter(), cases=public_cases(), output_dir=self.tmp_path / "r1")
    assert not (self.tmp_path / "r1").exists()

def test_actual_occupied_bytes_accept_exact_cap_and_reject_one_over(self) -> None:
    exact = synthetic_occupied_tree(self.tmp_path / "exact", total_bytes=4_194_304)
    receipt = measure_output_occupancy(exact, leg=Leg.R1)
    self.assertEqual(4_194_304, receipt.actual_total_bytes)
    one_over = synthetic_occupied_tree(self.tmp_path / "over", total_bytes=4_194_305)
    with self.assertRaisesRegex(A0XActivationError, "dense output cap"):
        measure_output_occupancy(one_over, leg=Leg.R1)
```

- [ ] **Step 2: Run tests and confirm missing extractors**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_activations -v`

Expected: FAIL on missing modules.

- [ ] **Step 3: Implement A0X-A0 extraction**

Extract ten view/site combinations for each of the four literal endpoints and the final endpoint: `problem_only/sentinel`; three sites each for `transformation_only`, `problem_plus_transformation`, and `problem_plus_solution`. Use the public 48-case selection manifest only. Average selected token positions into contiguous float32 one-dimensional vectors, hash raw vector bytes, and atomically write one Safetensors dense file plus a JSONL index.

- [ ] **Step 4: Implement A0X-R1 extraction**

Extract `problem_plus_transformation/mean_transformation_span` and `problem_only/sentinel` at literal tuple index 6 and the final-block tuple index. Keep primary and descriptive records distinguishable with `endpoint_role: primary|descriptive` and never derive the literal index from model depth.

- [ ] **Step 5: Enforce atomic-output reservations**

Before model construction, static preflight serializes the complete `DenseBound` into the dossier, authorization, and preflight receipt. Immediately before each write and before final rename, the extractor emits an occupancy receipt with actual bytes for final dense asset, surviving dense staging/crash residue, final index, surviving index staging/crash residue, target-read receipt, identity/integrity/environment/CCP receipts, report, publication manifest, and external-locator metadata. It verifies actual total occupied bytes do not exceed the leg cap. A crash-stage directory is renamed atomically only after all hashes are computed. On overflow, no final output directory is created; the terminal failure package still records the planned bound and measured residue without creating fabricated dense or statistical artifacts.

Add `measure_output_occupancy(root, *, leg) -> OutputOccupancyReceipt` and
`verify_output_occupancy(planned: DenseBound, actual: OutputOccupancyReceipt)`.
Tests cover empty output, exact cap, one byte over, duplicate staging copies,
crash residue, and external dense locator/report payload. Every later receipt
must bind both the serialized planned allocation and the actual occupied-byte
receipt SHA-256.

- [ ] **Step 6: Run extraction and historical token-site tests**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_activations tests.test_a0_activation_sites tests.test_a0r1_activations -v`

Expected: PASS; synthetic adapter call counts prove no target path was supplied.

- [ ] **Step 7: Commit exact Task 5 paths**

```bash
rtk git add -- src/latent_triz/a0x_a0_activations.py src/latent_triz/a0x_r1_activations.py tests/test_a0x_activations.py
rtk git commit -m "feat: extract bounded A0X activations"
```

### Task 6: One-Shot Target Capability and Terminal State Machine

**Files:**
- Create: `src/latent_triz/a0x_execution.py`
- Create: `tests/test_a0x_execution.py`

**Interfaces:**
- Consumes: activation artifacts from Task 5.
- Produces: `OneShotTargetReader`, `TargetReadReceipt`, `AttemptState`, `advance_attempt`, and `seal_terminal_attempt`.

- [ ] **Step 1: Write failing zero/one/two-read tests**

```python
def test_analysis_reader_hashes_and_parses_in_one_open(self) -> None:
    path = self.tmp_path / "targets.jsonl"
    path.write_bytes(b'{"case_id":"x"}\n')
    receipt_path = self.tmp_path / "target-read-receipt.json"
    reader = OneShotTargetReader(
        path=path, expected_sha256=sha256_file(path),
        expected_case_ids=("x",), require_file_exact=True,
        receipt_path=receipt_path, pair_binding=synthetic_pair_binding(),
    )
    rows, receipt = reader.read_jsonl_once()
    assert rows == [{"case_id": "x"}]
    assert receipt.content_reads == 1
    assert json.loads(receipt_path.read_text())["content_reads"] == 1
    with self.assertRaisesRegex(A0XExecutionError, "already consumed"):
        reader.read_jsonl_once()

def test_post_open_hash_or_json_failure_still_persists_one_read(self) -> None:
    for payload, expected_hash in ((b"bad-json\n", hashlib.sha256(b"bad-json\n").hexdigest()), (b'{}\n', "0" * 64)):
        path = self.tmp_path / hashlib.sha256(payload).hexdigest()
        path.write_bytes(payload)
        receipt_path = path.with_suffix(".receipt.json")
        reader = OneShotTargetReader(
            path=path, expected_sha256=expected_hash,
            expected_case_ids=("x",), require_file_exact=True,
            receipt_path=receipt_path, pair_binding=synthetic_pair_binding(),
        )
        with self.assertRaises(A0XExecutionError):
            reader.read_jsonl_once()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(1, receipt["content_reads"])
        self.assertIn(receipt["status"], ("hash_mismatch", "parse_failed"))

def test_preanalysis_failure_has_zero_reads_and_no_statistic(self) -> None:
    terminal = seal_terminal_attempt(state=AttemptState.PREFLIGHT, status="incompatible", target_reads=0)
    assert terminal["analysis_target_content_reads"] == 0
    assert "statistical_result" not in terminal
```

- [ ] **Step 2: Run tests and verify missing execution boundary**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_execution -v`

Expected: FAIL on missing execution module.

- [ ] **Step 3: Implement the capability and state transitions**

```python
class AttemptState(StrEnum):
    PREFLIGHT = "preflight"
    ACTIVATION = "activation"
    ANALYSIS = "analysis"
    SEALED = "sealed"

class OneShotTargetReader:
    def read_jsonl_once(self) -> tuple[list[dict[str, object]], TargetReadReceipt]:
        if self._consumed:
            raise A0XExecutionError("target reader already consumed")
        self._consumed = True
        status = "read_failed"
        observed_sha256 = None
        content_reads = 0
        try:
            with self._path.open("rb") as stream:
                content_reads = 1
                payload = stream.read()
            observed_sha256 = hashlib.sha256(payload).hexdigest()
            if observed_sha256 != self._expected_sha256:
                status = "hash_mismatch"
                raise A0XExecutionError("sealed target hash mismatch")
            try:
                parsed = [json.loads(line) for line in payload.splitlines() if line]
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                status = "parse_failed"
                raise A0XExecutionError("sealed target parse failed") from exc
            try:
                rows = self._select_and_validate(parsed)
            except A0XExecutionError:
                status = "selection_mismatch"
                raise
            status = "pass"
            return rows, TargetReadReceipt(
                pair_binding=self._pair_binding, content_reads=1,
                status=status, observed_sha256=observed_sha256,
            )
        finally:
            self._write_receipt_once(
                content_reads=content_reads, status=status,
                observed_sha256=observed_sha256,
            )
```

Allow only `PREFLIGHT -> ACTIVATION -> ANALYSIS -> SEALED`. Exceptions seal the first terminal outcome; no state can return to a previous stage. Construct the target reader only after the activation receipt and dense/index hashes are sealed. Its receipt is written in `finally` with exclusive-create semantics after any successful file open, including hash mismatch, malformed UTF-8/JSON, duplicate/missing case IDs, or selection mismatch. The terminal builder consumes that persisted receipt and emits no statistic on any such error.

For A0X-A0, the reader may parse unselected historical target rows but must
return exactly the 48 selected records in the exact order of
`a0-selection-manifest.json`; every selected ID must appear once and no
selected ID may be duplicated. For A0X-R1, the complete target file must equal
the exact ordered 48-case frozen corpus selection. Both checks occur from the
same in-memory payload obtained by the single file open; no later validation
may reopen the target.

- [ ] **Step 4: Add refusal tests for activation target access and retry**

Inspect the activation callable signature and assert it has no `targets_path`, `target_reader`, or generic filesystem capability. Simulate exceptions at every state and assert correct read counters and terminal status. Test A0 selected-ID reorder/missing/duplicate cases and R1 extra/missing/reordered cases. Invoke `advance_attempt` after `SEALED` and assert a retry refusal.

- [ ] **Step 5: Run execution tests**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_execution tests.test_a0x_activations -v`

Expected: PASS.

- [ ] **Step 6: Commit exact Task 6 paths**

```bash
rtk git add -- src/latent_triz/a0x_execution.py tests/test_a0x_execution.py
rtk git commit -m "feat: enforce one-shot A0X target access"
```

### Task 7: Frozen A0X-A0 Statistical Path

**Files:**
- Create: `src/latent_triz/a0x_a0_analysis.py`
- Create: `tests/test_a0x_a0_analysis.py`

**Interfaces:**
- Consumes: Task 5 A0X-A0 index/dense assets and Task 6 one-shot target rows.
- Produces: `analyze_a0x_a0` and an `a0x-statistical-result` for leg `a0`.

- [ ] **Step 1: Write failing primary/sensitivity separation tests**

```python
def test_favourable_final_block_cannot_rescue_null_primary(self) -> None:
    result = analyze_a0x_a0(**synthetic_a0_inputs(primary_signal=0.0, final_signal=10.0, root=self.tmp_path))
    assert result["status"] == "null"
    assert result["primary"]["max_statistic_p"] > 0.05
    assert result["descriptive_final_block"]["rescues_primary"] is False

def test_primary_has_exact_twelve_combinations(self) -> None:
    result = analyze_a0x_a0(**synthetic_a0_inputs(primary_signal=1.0))
    assert result["primary"]["multiplicity"] == 12
    assert len(result["primary"]["combinations"]) == 12
```

- [ ] **Step 2: Run tests and verify the analysis module is missing**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_a0_analysis -v`

Expected: FAIL on missing analysis module.

- [ ] **Step 3: Port and freeze the verified A0 statistics**

Copy the L2 linear least-squares/LODO helpers from `a0_analysis.py` into the A0X namespace with explicit typed tests. Use the twelve `problem_plus_transformation × {0,2,4,6} × {sentinel,final_transformation_token,mean_transformation_span}` primary combinations, 199 shared within-family label-swap permutations, and the `problem_only/sentinel` maximum surface baseline. Compute `p = (1 + count(null_maximum >= observed_maximum)) / 200`.

- [ ] **Step 4: Implement the frozen positive rule**

Set `positive` only when `max_statistic_p <= 0.05`, `macro_f1_margin_over_surface >= 0.10`, and `observed_max_family_successes >= 19`. Shortcut refusal yields `non_interpretable`; a valid but non-positive primary yields `null`. Final-block results for all applicable views/sites are stored under `descriptive_final_block` with `rescues_primary: false`.

- [ ] **Step 5: Compare numeric helpers against historical A0 fixtures**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_a0_analysis tests.test_a0_analysis -v`

Expected: PASS; shared synthetic matrices produce identical historical and A0X primary helper outputs.

- [ ] **Step 6: Commit exact Task 7 paths**

```bash
rtk git add -- src/latent_triz/a0x_a0_analysis.py tests/test_a0x_a0_analysis.py
rtk git commit -m "feat: add frozen A0X A0 analysis"
```

### Task 8: Frozen A0X-R1 Statistical Path

**Files:**
- Create: `src/latent_triz/a0x_r1_analysis.py`
- Create: `tests/test_a0x_r1_analysis.py`

**Interfaces:**
- Consumes: Task 5 A0X-R1 index/dense assets and Task 6 one-shot target rows.
- Produces: `analyze_a0x_r1` and an `a0x-statistical-result` for leg `r1`.

- [ ] **Step 1: Write failing fixed-primary and domain-direction tests**

```python
def test_final_block_never_replaces_literal_index_six(self) -> None:
    result = analyze_a0x_r1(**synthetic_r1_inputs(primary_signal=0.0, final_signal=10.0, root=self.tmp_path))
    assert result["status"] == "null"
    assert result["primary"]["tuple_index"] == 6
    assert result["descriptive_final_block"]["rescues_primary"] is False

def test_positive_requires_all_four_frozen_conditions(self) -> None:
    result = analyze_a0x_r1(**synthetic_r1_inputs(p=0.01, margin=0.2, successes=17, domains=3))
    assert result["status"] == "null"
```

- [ ] **Step 2: Run tests and confirm missing R1 module**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_r1_analysis -v`

Expected: FAIL on missing module.

- [ ] **Step 3: Port the fixed-primary R1 analysis**

Copy the verified fixed-primary LODO, paired family direction, per-domain direction, and 999 within-family permutation logic from `a0r1_analysis.py`. The only primary representation is `problem_plus_transformation/mean_transformation_span/tuple-index-6`; the only surface baseline is `problem_only/sentinel/tuple-index-6`.

- [ ] **Step 4: Implement the four-condition positive rule**

Set `positive` only when permutation `p <= 0.05`, macro-F1 margin `>= 0.10`, family successes `>= 17`, and strictly positive directions in at least four domains. Store final-block primary/baseline analogues under `descriptive_final_block`; set `rescues_primary: false` unconditionally.

- [ ] **Step 5: Compare synthetic outputs against historical R1 helpers**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_r1_analysis tests.test_a0r1_analysis -v`

Expected: PASS.

- [ ] **Step 6: Commit exact Task 8 paths**

```bash
rtk git add -- src/latent_triz/a0x_r1_analysis.py tests/test_a0x_r1_analysis.py
rtk git commit -m "feat: add frozen A0X R1 analysis"
```

### Task 9: Terminal Packages, Reports, and Fresh-Clone Verification

**Files:**
- Create: `src/latent_triz/a0x_report.py`
- Create: `src/latent_triz/a0x_verify.py`
- Create: `tests/test_a0x_report.py`
- Create: `tests/test_a0x_verify.py`

**Interfaces:**
- Consumes: Task 6 terminal attempt state and Task 7/8 statistical results.
- Produces: `build_terminal_package`, `render_a0x_report`, `verify_a0x_package`, and `verify_a0x_campaign_separation`.

- [ ] **Step 1: Write failing tests for all five terminal classes**

```python
def test_every_terminal_status_builds_a_schema_valid_package(self) -> None:
    for status in ("positive", "null", "non_interpretable", "incompatible", "failed"):
        package = build_terminal_package(**terminal_fixture(status=status, root=self.tmp_path / status))
        assert package["status"] == status
        assert package["claim_ids"] == []

def test_missing_or_mutated_external_dense_asset_fails(self) -> None:
    package_dir, dense = published_fixture(self.tmp_path)
    verify_a0x_package(package_dir=package_dir, external_dense_path=dense)
    dense.write_bytes(dense.read_bytes() + b"x")
    with self.assertRaisesRegex(A0XVerifyError, "external dense asset"):
        verify_a0x_package(package_dir=package_dir, external_dense_path=dense)
```

- [ ] **Step 2: Run tests and confirm report/verifier imports fail**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_report tests.test_a0x_verify -v`

Expected: FAIL on missing modules.

- [ ] **Step 3: Implement immutable package construction**

Write into a sibling staging directory, validate every JSON artifact, hash report/receipts/index/dense locator, use hard-link or exclusive-create semantics for first terminal publication, then atomically rename. Never overwrite an existing terminal directory. A pre-analysis terminal package omits `statistical-result.json`; a valid analysis package requires it and requires one target read.

- [ ] **Step 4: Implement human-readable reports without claim promotion**

Reports must identify one exact leg/model/revision, state the terminal status, primary endpoint and thresholds, descriptive final-block status, read counters, runtime limits, limitations, and the exact sentence: `This exploratory automated-proxy result is not a general TRIZ, causal, mechanism, emergence, or training-data claim.`

- [ ] **Step 5: Implement independent verifier and non-pooling guards**

Verify all schemas and hashes, protected historical trees, authorization/dossier binding, exact pair identity, external dense locator, read counters, output caps, status/statistical-result compatibility, and absence of EXP-002/R5 paths. First use `assert_leg_freeze_binding` to prove the dossier's leg and `leg_freeze_sha256` match the immutable shared leg artifacts. Starting from the publication manifest's root `PairBinding`, recursively load every per-pair referenced JSON receipt/result/report-input artifact, require byte/hash agreement, and pass the complete set to `assert_pair_binding`; any leg/freeze/model/revision/run/dossier/authorization/output/cap mismatch fails before interpretation. Also reject forbidden aggregate fields (`aggregate`, `ranking`, `combined_p`) as defence in depth; keyword rejection is never a substitute for structural binding.

- [ ] **Step 6: Run terminal, mutation, and publication tests**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_report tests.test_a0x_verify tests.test_a0r1_report -v`

Expected: PASS.

- [ ] **Step 7: Commit exact Task 9 paths**

```bash
rtk git add -- src/latent_triz/a0x_report.py src/latent_triz/a0x_verify.py tests/test_a0x_report.py tests/test_a0x_verify.py
rtk git commit -m "feat: verify immutable A0X packages"
```

### Task 10: One-Pair Runner, Fixed Material Targets, and Repository Integration

**Files:**
- Create: `src/latent_triz/a0x_runner.py`
- Create: `scripts/a0x_contract_check.py`
- Create: `scripts/a0x_material.py`
- Create: `tests/test_a0x_runner.py`
- Create: `tests/test_a0x_contract_check.py`
- Create: `tests/test_a0x_material.py`
- Modify: `src/latent_triz/cli.py`
- Modify: `scripts/repository_check.py`
- Modify: `scripts/schema_cross_validate.py`
- Modify: `Makefile`

**Interfaces:**
- Consumes: Tasks 2-9.
- Produces: `run_a0x_pair`, `verify_a0x_implementation`, `main` for fixed dossier execution, `make a0x-synthetic-verify`, and twelve argument-free material targets that remain blocked until Task 11 creates exact dossiers.

- [ ] **Step 1: Write failing runner state and fixed-target tests**

```python
def test_runner_seals_first_failure_and_refuses_second_attempt(self) -> None:
    dossier = synthetic_dossier(self.tmp_path, leg="a0", model_key="gpt2")
    first = run_a0x_pair(root=self.tmp_path, dossier_path=dossier, adapter_factory=failing_adapter)
    assert first["status"] == "failed"
    with self.assertRaisesRegex(A0XRunnerError, "terminal attempt already exists"):
        run_a0x_pair(root=self.tmp_path, dossier_path=dossier, adapter_factory=working_adapter)

def test_material_entrypoint_rejects_cli_model_or_leg_override(self) -> None:
    with self.assertRaises(SystemExit):
        material_main(["--model", "gpt2"])
```

- [ ] **Step 2: Run tests and confirm missing integration**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_runner tests.test_a0x_contract_check tests.test_a0x_material -v`

Expected: FAIL on missing runner/scripts.

- [ ] **Step 3: Implement one-pair orchestration**

`run_a0x_pair` must verify the exact dossier and approval object, run static preflight, construct tokenizer then model, run the selected leg activation, seal activation hashes, construct the one-shot target capability, run the selected leg analysis, seal the first terminal package, verify protected inputs postflight, and release model references. It must never loop over models or legs and must refuse a non-empty output or existing terminal receipt.

- [ ] **Step 4: Implement no-model aggregate verification**

`verify_a0x_implementation(root)` validates all schemas, six cards, protected trees, selection manifest, cap calculations, fixed Make target mapping, and source/test interfaces. It deliberately does not claim that frozen protocols or dossiers exist. It must record `phase: synthetic_implementation`, `model_loaded: false`, `tokenizer_constructed: false`, `sealed_target_content_reads: 0`, and `ccp_invoked: false`. `scripts/a0x_contract_check.py --phase synthetic` invokes this function.

- [ ] **Step 5: Add twelve fixed Make targets**

Add these exact argument-free targets, each mapped to one immutable dossier path:

```text
a0x-material-a0-smollm2-360m
a0x-material-a0-qwen3-0-6b-base
a0x-material-a0-gpt2
a0x-material-a0-smollm2-135m
a0x-material-a0-gpt-neo-125m
a0x-material-a0-qwen2-5-0-5b
a0x-material-r1-smollm2-360m
a0x-material-r1-qwen3-0-6b-base
a0x-material-r1-gpt2
a0x-material-r1-smollm2-135m
a0x-material-r1-gpt-neo-125m
a0x-material-r1-qwen2-5-0-5b
```

Each target invokes `scripts/a0x_material.py` with a single hard-coded dossier path and no user-selectable model, leg, target, output, cap, or retry argument. The script verifies live CCP `resource status --json` and `admission status --json` through the exact binary bound in the dossier, proceeds only on Admit/inactive/empty queue, and enters one CCP guard for the one fixed runner. Unknown output or binary/hash drift seals a pre-model `incompatible` outcome.

- [ ] **Step 6: Integrate repository checks**

Add `a0x-synthetic-verify` to `.PHONY`, make it call `scripts/a0x_contract_check.py --phase synthetic` and all focused A0X tests, and call only that synthetic phase from `scripts/repository_check.py`. Add A0X schemas to schema cross-validation. Do not add any material target to `make test`, `make check`, GitHub Actions, or repository check.

- [ ] **Step 7: Run focused and full no-model verification**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_runner tests.test_a0x_contract_check tests.test_a0x_material -v`

Run: `rtk make a0x-synthetic-verify`

Expected: PASS and an explicit receipt proving no model/tokenizer/target/CCP access.

- [ ] **Step 8: Commit exact Task 10 paths**

```bash
rtk git add -- src/latent_triz/a0x_runner.py scripts/a0x_contract_check.py scripts/a0x_material.py tests/test_a0x_runner.py tests/test_a0x_contract_check.py tests/test_a0x_material.py src/latent_triz/cli.py scripts/repository_check.py scripts/schema_cross_validate.py Makefile
rtk git commit -m "feat: integrate one-shot A0X runner"
```

### Task 11: Freeze Both Legs and Prepare Twelve Approval Dossiers

**Files:**
- Create: `experiments/a0x-six-model/a0/protocol.json`
- Create: `experiments/a0x-six-model/a0/implementation.json`
- Create: `experiments/a0x-six-model/r1/protocol.json`
- Create: `experiments/a0x-six-model/r1/implementation.json`
- Create: `experiments/a0x-six-model/freeze/a0-freeze.json`
- Create: `experiments/a0x-six-model/freeze/r1-freeze.json`
- Create: `experiments/a0x-six-model/approval-dossiers/a0/*.json`
- Create: `experiments/a0x-six-model/approval-dossiers/r1/*.json`
- Create: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Create: `tests/test_a0x_frozen_package.py`
- Modify: `docs/LABORATORY_MASTER_PLAN.md`
- Modify: `docs/PERSISTENT_GOAL.txt`
- Modify: `Makefile`

**Interfaces:**
- Consumes: complete no-model system from Tasks 1-10 and exact source/model receipts.
- Produces: two hash-bound frozen legs, twelve unapproved dossier objects, `verify_a0x_no_model`, `make a0x-no-model-verify`, campaign runbook, and the exact hashes needed for later operator approval.

- [ ] **Step 1: Write failing frozen-package tests**

Assert that both protocols copy every inherited corpus/split/control/statistic/threshold field by value, use new A0X IDs, bind the exact protected trees and selection manifest, and preserve the literal endpoints. Assert neither protocol nor implementation contains its own hash, and neither freeze manifest contains its own hash. Serialize and hash the two components, write and hash each freeze, then reconstruct the two derived `LegFreezeBinding` objects. Assert twelve dossiers equal the Cartesian product of two legs and six cards, with no multi-pair dossier and `authorization_status: approval_required`. Prove the six A0 dossiers share the one derived A0 binding and the six R1 dossiers share the one derived R1 binding; mutate one dossier to the wrong leg and one to the wrong freeze hash and require fail-closed rejection.

- [ ] **Step 2: Run tests before generating freezes**

Run: `rtk env PYTHONPATH=src python3 -m unittest tests.test_a0x_frozen_package -v`

Expected: FAIL because frozen A0X artifacts do not exist.

- [ ] **Step 3: Generate protocols, implementations, freezes, and dossiers deterministically**

Run: `rtk env PYTHONPATH=src python3 -m latent_triz.a0x_freeze --root . --freeze-all --prepare-dossiers`

Expected: two protocols, two implementation manifests, two freezes, and twelve dossiers; no model/tokenizer/target/CCP access.

- [ ] **Step 4: Write the operator/Luna runbook**

Document the exact per-pair approval template, the corresponding fixed Make target, CCP prerequisites, read counters, caps, first-terminal publication rule, no-retry rule, cleanup evidence, and post-run verifier. State that Luna may invoke a fixed target only after the operator supplies authorization bound to the exact dossier SHA-256 and a primary reviewer confirms the exact CCP binary/hash and live gate.

- [ ] **Step 5: Promote the no-model verifier to the frozen phase**

Implement `verify_a0x_no_model(root)` as a strict superset of the synthetic verifier: require both frozen protocols/implementations, both freeze manifests, all twelve dossier shapes, exact source/test hash bindings, and the fixed Make-target-to-dossier bijection. Add `a0x-no-model-verify` to `.PHONY`; it must invoke `scripts/a0x_contract_check.py --phase frozen` and the focused test suite. Keep `a0x-synthetic-verify` for earlier implementation checkpoints.

- [ ] **Step 6: Run complete synthetic qualification**

Run: `rtk make a0x-no-model-verify`

Run: `rtk env PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_a0x_*.py' -v`

Run: `rtk make docs-audit`

Run: `rtk git diff --check`

Expected: all PASS; output explicitly reports zero model loads, zero material tokenizer constructions, zero sealed-target reads, zero CCP invocations, and zero remote mutations.

- [ ] **Step 7: Perform fresh architecture/science review before committing**

Reviewer checks exact endpoint semantics, cap math, target capability, six identity cards, twelve dossier isolation, no-pooling guards, and absence of imports from EXP-002/R5. Any correction changes bound hashes and requires dossier regeneration before commit.

- [ ] **Step 8: Commit exact Task 11 paths**

```bash
rtk git add -- experiments/a0x-six-model/a0/protocol.json experiments/a0x-six-model/a0/implementation.json experiments/a0x-six-model/r1/protocol.json experiments/a0x-six-model/r1/implementation.json experiments/a0x-six-model/freeze/a0-freeze.json experiments/a0x-six-model/freeze/r1-freeze.json experiments/a0x-six-model/approval-dossiers/a0/smollm2_360m.json experiments/a0x-six-model/approval-dossiers/a0/qwen3_0_6b_base.json experiments/a0x-six-model/approval-dossiers/a0/gpt2.json experiments/a0x-six-model/approval-dossiers/a0/smollm2_135m.json experiments/a0x-six-model/approval-dossiers/a0/gpt_neo_125m.json experiments/a0x-six-model/approval-dossiers/a0/qwen2_5_0_5b.json experiments/a0x-six-model/approval-dossiers/r1/smollm2_360m.json experiments/a0x-six-model/approval-dossiers/r1/qwen3_0_6b_base.json experiments/a0x-six-model/approval-dossiers/r1/gpt2.json experiments/a0x-six-model/approval-dossiers/r1/smollm2_135m.json experiments/a0x-six-model/approval-dossiers/r1/gpt_neo_125m.json experiments/a0x-six-model/approval-dossiers/r1/qwen2_5_0_5b.json docs/A0X_SIX_MODEL_CAMPAIGN.md tests/test_a0x_frozen_package.py docs/LABORATORY_MASTER_PLAN.md docs/PERSISTENT_GOAL.txt Makefile
rtk git commit -m "docs: freeze A0X six-model campaign"
```

- [ ] **Step 9: Stop at the material approval boundary**

Report exact repository HEAD, origin/main, two freeze hashes, twelve dossier SHA-256 values, test receipt, and CCP binary requirement. Do not load a model, construct a material tokenizer, read target bytes, invoke CCP, push, or publish. Request a separate explicit operator authorization for each intended `(leg, model)` pair.

### Task 12: Execute and Publish Each Separately Authorized Pair

**Files:**
- Create per authorized pair: `results/a0x/<leg>/<model-key>/<run-id>/authorization.json`
- Create per authorized pair: `results/a0x/<leg>/<model-key>/<run-id>/preflight-receipt.json`
- Create per authorized pair: `results/a0x/<leg>/<model-key>/<run-id>/terminal-result.json`
- Create when analysis is valid: `results/a0x/<leg>/<model-key>/<run-id>/statistical-result.json`
- Create per authorized pair: `results/a0x/<leg>/<model-key>/<run-id>/report.md`
- Create per authorized pair: `results/a0x/<leg>/<model-key>/<run-id>/publication-manifest.json`
- Create when activation occurs: `artifacts/a0x/<leg>/<model-key>/<run-id>/activations.safetensors`
- Create when activation occurs: `artifacts/a0x/<leg>/<model-key>/<run-id>/representations-index.jsonl`
- Modify after each published terminal pair: `docs/A0X_SIX_MODEL_CAMPAIGN.md`
- Modify after each published terminal pair: `docs/LABORATORY_MASTER_PLAN.md`
- Modify after each published terminal pair: `docs/PERSISTENT_GOAL.txt`

**Interfaces:**
- Consumes: one exact approved dossier, one exact approval object, one fixed Make target, and a live verified CCP gate.
- Produces: one immutable terminal package; repeated independently until twelve packages or twelve fail-closed outcomes exist.

- [ ] **Step 1: Verify one pair's approval without material access**

Run the no-model authorization verifier for exactly one dossier/authorization pair. It must bind exact repository HEAD, origin/main, dossier hash, model card, runtime receipts, protected trees, target declaration, output path, CCP binary hash, `1,800` seconds, `8,589,934,592` RSS bytes, the leg-specific dense cap, one target read, and no retry.

- [ ] **Step 2: Verify the live CCP gate**

Run the exact dossier-bound CCP binary's `resource status --json` and `admission status --json`. Proceed only when resource decision is `admit`, admission is inactive, queue count is zero, and no active/queued run exists. Preserve the JSON observation in the pair's preflight receipt.

- [ ] **Step 3: Invoke the one fixed argument-free target once**

Run the exact `rtk make a0x-material-<leg>-<model-key>` target named in the approved dossier. Do not add arguments, environment overrides, parallel processes, or a second invocation. The first terminal package consumes the authorization whether it is positive, null, non-interpretable, incompatible, or failed.

- [ ] **Step 4: Run no-load/no-target post-verification**

Run `verify_a0x_package` for the exact package and external dense locator. Confirm protected trees are unchanged, hashes and read counters match, output cap and runtime receipts pass, the package has one model and one leg, and no EXP-002/R5 path is referenced. Do not rerun analysis.

- [ ] **Step 5: Commit and qualify only the one terminal package**

Stage exact pair paths and the three canonical status documents. Run repository tests and one CCP exact-head qualification only under a separate publication authorization. Publish `.ccp/receipt.json` only on `ccp-evidence/<exact-head>`, then push the feature branch, open the PR, wait for terminal GitHub gates, merge, and verify from a fresh clone.

- [ ] **Step 6: Repeat Steps 1-5 only for a newly and separately authorized pair**

Never reuse an approval, output directory, CCP receipt, target-reader capability, run ID, or terminal package. A failed or consumed pair remains terminal until the operator issues a new explicitly reviewed authorization for a distinct attempt.

- [ ] **Step 7: Close the campaign without pooling**

When all twelve pair slots have terminal packages, publish a model-by-leg availability matrix containing only links, exact statuses, and limitations. Do not compute aggregate accuracy, combined p-values, rankings, votes, or a general TRIZ claim. The campaign completion statement is limited to independently reproducible outcomes for the frozen automated proxies.

## Final Verification Checklist

- [ ] `rtk git diff --check` exits 0.
- [ ] `rtk make a0x-no-model-verify` exits 0 before any material approval.
- [ ] `rtk env PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_a0x_*.py' -v` passes.
- [ ] `rtk make check` and `rtk make docs-audit` pass without invoking material targets.
- [ ] Protected A0/A0-R1 tree hashes match before and after every material pair.
- [ ] The six model cards and twelve dossiers are exact and pair-separated.
- [ ] Every valid analysis records exactly one target content read; every pre-analysis terminal package records zero.
- [ ] Every activation records zero target content reads.
- [ ] Missing or mutated external dense assets fail closed from a fresh clone.
- [ ] No result contains more than one leg or model key.
- [ ] No R5/EXP-002 artifact is an A0X dependency.
- [ ] Every material or publication action has its own explicit hash-bound authorization and terminal receipt.
