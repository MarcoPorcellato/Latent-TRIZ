# A0X Offline Gate B Runtime Builder Design

**Status:** Approved for target-free implementation only  
**Date:** 2026-09-01  
**Scope:** Synthetic fixtures, offline code, tests, documentation, frozen A0X bindings, and one local commit

## Purpose

Add a fail-closed builder that can later create the two prerequisites consumed by the existing A0X Gate B preparer:

1. an independent Python 3.11 virtual environment installed only from one exact verified wheelhouse; and
2. an independent APFS copy-on-write materialization of one exact model-card snapshot.

This implementation does not perform the real build. It does not create a material environment, install a real package, clone a real model file, prepare a Gate B bundle, load a model or tokenizer, or access a target.

## Boundaries

The builder is a prerequisite producer, not a new Gate B authority. Its success means only that runtime prerequisites were created and verified under the recorded inputs. The existing Hosted Gate A verifier and `a0x_prepare_runtime.py` remain responsible for the later Gate B verification receipt, readiness document, launch descriptor, execution authorization, and local mapping.

The builder must:

- consume one canonical `a0x-offline-wheelhouse-v1` manifest whose raw SHA-256 is supplied by the operator;
- require exactly 39 distributions for the A0X Python 3.11 environment;
- require a canonical `a0x-python-runtime-manifest-v1` that allowlists every
  regular independent file in the selected Python runtime, including the
  interpreter, `venv`, standard library, `ensurepip`, and bundled installer;
- bind the runtime-manifest bytes, complete allowlisted tree, interpreter
  bytes, Python version, and bootstrap installer version before and after each
  use of the base runtime;
- APFS-clone the complete verified base runtime and all 39 verified wheels into
  private, overwrite-refusing attempt paths before any child execution;
- execute and install only from those owned, reverified paths;
- invoke `venv --copies` without a shell;
- bind the bootstrap `pip` version, use it only as the offline installer, remove
  it, and reject the environment unless the final installed set is exactly the
  39 wheelhouse distributions;
- verify the actual virtual-environment bootstrap installer before package
  installation;
- install with `pip --isolated install --no-index --find-links ...
  --no-cache-dir --only-binary :all: --require-hashes --no-deps`;
- derive the hash-locked requirements from the already verified wheelhouse manifest rather than resolving dependencies;
- verify the complete installed distribution set and exact versions through an isolated metadata probe;
- materialize only the runtime files named by the exact model card through `clone_regular_file`, which has no full-copy fallback;
- verify source and destination size and SHA-256 for every model file;
- refuse symlinks, hardlinks, noncanonical external paths, occupied outputs,
  unexpected files, path escape, version drift, hash drift, base-runtime drift,
  subprocess failure, malformed probe output, or source drift;
- use explicit, absent destination paths. A failed attempt is not silently resumed or repaired.

The builder must not:

- use a package index, resolver, source distribution, editable install, user site, or global installation;
- invoke a shell;
- fall back from APFS clonefile to an ordinary copy;
- construct a tokenizer, load weights, import the model runtime APIs, read targets, score data, or start Gate C;
- emit readiness, authorization, mapping, scientific results, or public evidence;
- interpret an incomplete output directory as reusable evidence.

## Components

### Library

`src/latent_triz/a0x_gate_b_builder.py` provides:

- strict request and plan records;
- canonical manifest-to-requirements derivation;
- read-only planning and input validation;
- shell-free execution through an injected or subprocess runner;
- installed-distribution validation;
- model-card allowlist materialization through an injected or real APFS clone boundary;
- a canonical local build receipt.

All external execution is dependency-injected in tests. Production defaults
use `subprocess.run(..., shell=False)` with a 3,600-second child timeout and the
existing APFS boundary. Read-only Python probes use isolated, no-bytecode mode.

### CLI

`scripts/a0x_build_gate_b_runtime.py` accepts exact paths, expected hashes, and
destination paths. It disables repository bytecode writes before importing
local modules. The CLI requires exactly one explicit mode: `--plan` or
`--build`. `--plan` validates static inputs, executes no external code, writes
nothing, and prints canonical JSON. Build mode is deliberately available for a
later, separately authorized material action; it is not executed in this
implementation tranche.

### Receipt

The receipt records only local prerequisite facts: source HEAD, wheelhouse
manifest hash, base-runtime manifest hash and file count, base Python hash and
version, shell-free commands, exact installed distributions, model-card hash,
per-file clone evidence, output paths, and output Python hash. It carries no
scientific status and is not public evidence.

## Transaction and failure model

Environment and model destinations must not exist at entry. The environment command creates its destination with `venv --copies`; the model destination is created exclusively by the builder. The builder never overwrites an existing path.

If any validation fails, the attempt terminates. The builder does not delete or reinterpret incomplete outputs because doing so could erase evidence or attacker-controlled replacements. A new attempt requires new absent destinations and a new material authorization.

The local receipt is written last with exclusive creation after both outputs pass final revalidation. An existing receipt is a terminal refusal.

## Testing strategy

Tests use only temporary synthetic wheels, tiny model-card files, a fake independent Python executable, injected subprocess results, and an injected clone operation. They prove:

- manifest-hash and 39-distribution binding;
- deterministic hash-locked requirements;
- exact shell-free `venv --copies`, bootstrap-installer probe, and offline pip
  commands;
- APFS binding of the complete base runtime and wheelhouse into owned paths,
  with execution and installation restricted to those reverified paths;
- full base-runtime manifest binding and refusal of interpreter, standard
  library, `venv`, or `ensurepip` drift around execution;
- refusal of model-card byte/path disagreement and no external runner call
  before static validation succeeds;
- no Python bytecode writes during planning;
- no runner call in planning and no material runner call before owned input
  binding succeeds;
- exact installed distribution validation;
- runtime allowlist cloning and post-clone byte verification;
- refusal of source drift, unexpected installed distributions, occupied destinations, failed commands, malformed metadata, and clone failure;
- CLI planning without material execution;
- inclusion of the new trusted surface in both frozen A0X implementation inventories.

## Frozen-package impact

The new library, CLI, tests, specification, plan, and operator documentation become part of the trusted A0X implementation surface where appropriate. After implementation, both A0 and R1 implementation inventories, freezes, and all twelve approval dossiers are regenerated target-free against the exact implementation commit.
