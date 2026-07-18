# PR-00 Feature-Preserving Human Rebuild Design

## Purpose

Create the machine-readable, regression-tested feature baseline that every
later Human Rebuild phase must preserve. This phase does not remove, rename,
or refactor production behaviour. It records the currently reachable product
surface and makes an accidental reduction fail in CI.

## Baselines and Scope

- Audit reference requested by the execution directive:
  `49ac6f88264fe4e06090af39154f2a089a18d8ef`.
- Implementation baseline: `db74254255ef3815f05c4c130dfd95077db23225` on
  `refactor/feature-preserving-human-rebuild`.
- The requested audit reference is available from `origin`, but is not an
  ancestor of the implementation baseline. PR-00 therefore records a
  reproducible two-way diff and inventories the implementation baseline; it
  does not claim that a linear migration took place.
- The untracked file in the original checkout,
  `tests/test_runtime_capabilities.py`, is excluded from this worktree and
  from the PR-00 baseline unless its owner explicitly supplies it.

## Design Decisions

### 1. Declarative manifest is the source of parity truth

`feature_manifest.json` will contain one stable `feature_id` per externally
reachable capability, its category, entrypoint, expected result, enabled
policy, and contract-test location. IDs describe user-observable behaviour,
not implementation files, so moving implementation later does not require
deleting or re-creating an ID.

The manifest includes the required default-enabled RAG and Harness features
with `required` and `default_enabled` flags. Multi-Agent features include all
Alpha, Beta, Gamma, and Delta flows with `preserved` and
`optional_enabled` flags. It also inventories CLI commands/options, FastAPI
routes, TUI actions/keybindings, GUI launch/actions, adapters, plugin
`provides`, installer/release entrypoints, configuration/environment keys, and
database/schema surfaces.

### 2. Discovery snapshots are generated, then checked

A small test-only inventory module will parse source declarations and package
metadata without importing runtime services. It will produce sorted snapshots
for CLI parser declarations, Web routes, plugin manifests/tool manifests,
adapter registrations, agent roles, packaged entrypoints, and configuration
keys. The generated manifest is committed as the reviewed baseline; tests
fail if discovery finds an entry that lacks an ID or if a committed ID becomes
unreachable.

This keeps the manifest reviewable and avoids a permissive test that merely
regenerates its own expected output at test time.

### 3. Contract tests protect behaviour at the right boundary

`tests/feature_contract/` contains tests only. It will be organized by
surface: manifest integrity, CLI help and dispatch, plugin discovery, RAG and
Harness defaults, Multi-Agent enabled/disabled behaviour, adapters,
installation/release entrypoints, and repository-hygiene metrics. Existing
tests remain in place; contract tests add cross-cutting preservation checks
rather than duplicating every unit assertion.

Each manifest item points to exactly one primary contract-test node. A single
test may cover several related IDs only where the user-visible operation is
atomic; the manifest records the individual IDs so future deletion is still
detected.

### 4. Reproducible structural baseline, not artificial reduction targets

The baseline generator records production-file count, raw/effective Python
LOC, public symbols, callable count, functions longer than 60/100 lines, and
top-level dependency edges. `tests/test_repo_hygiene.py` will reject a
decrease in Feature ID count and report metric deltas. It will not reject a
necessary temporary metric increase during safe migration, and it will not
permit adding fake product features to offset a loss.

## Data Flow

```text
source declarations + package metadata
          |
          v
test-only discovery snapshot ----> reviewed feature_manifest.json
          |                                  |
          +--------------> contract tests <--+
                                             |
                                             v
                                   CI parity and hygiene gate
```

## Failure Handling

- A malformed or duplicate Feature ID is an immediate test failure.
- An undiscovered static entry is reported as an unclassified surface, not
  silently ignored.
- Dynamic entries that cannot be statically resolved are represented as an
  explicit manifest record with a runtime contract test and documented source.
- Missing optional dependencies skip only the runtime invocation that requires
  them; manifest discovery and the capability contract still run.
- RAG, Harness, and the four Multi-Agent roles never become optional merely
  because a local runtime dependency is absent.

## Acceptance Criteria for PR-00

1. Every existing surfaced capability has a stable Feature ID, entrypoint,
   expected result, and contract-test reference.
2. The manifest is reproducibly generated from the implementation baseline and
   detects both removal and unclassified additions.
3. RAG and Harness are recorded and tested as required/default-enabled.
4. Multi-Agent disabled and enabled modes, including Alpha/Beta/Gamma/Delta,
   are recorded and tested.
5. Repository-hygiene measurements and the baseline/reference divergence are
   recorded without modifying production behaviour.
6. The PR report uses the directive's required scope, parity, metrics,
   validation, and unverified-items format.

## Explicit Non-Goals

- No production-code consolidation, deletion, or public-entrypoint change.
- No attempt to satisfy later numeric reduction targets in PR-00.
- No assertion that the requested audit commit is a linear ancestor of the
  current implementation baseline.
