# Feature Parity Baseline

This guide defines the PR-00 preservation gate for the feature-preserving Human
Rebuild. Later phases may consolidate implementations, but they may not remove
an existing Feature ID or make its contract test unreachable.

## Fixed Audit Baseline

- Required baseline: `49ac6f88264fe4e06090af39154f2a089a18d8ef`.
- The original local checkout was `db74254255ef3815f05c4c130dfd95077db23225`.
- Git ancestry proves `db74254` is an ancestor of `49ac6f8`; the rebuild branch
  must therefore be based on `49ac6f8`, not treated as an unrelated fork.
- `feature_manifest.json` records the fixed implementation baseline after that
  ancestry correction.

## Manifest Contract

Every object in `feature_manifest.json.features` has:

| Field | Meaning |
| --- | --- |
| `feature_id` | Stable identity for user-observable behaviour. |
| `category` | CLI, Web, plugin, adapter, TUI, configuration, database, agent, installer, or release surface. |
| `entrypoint` | Statically or manually reviewed route into the capability. |
| `expected_result` | Behaviour that must survive implementation changes. |
| `contract_test` | Existing pytest node that protects the entry. |

RAG and Harness records additionally require `required=true` and
`default_enabled=true`. Alpha, Beta, Gamma, and Delta records require
`preserved=true` and `optional_enabled=true`.

`baseline_feature_ids` is the immutable PR-00 reviewed set. The current
`features` list may grow, but it must remain a superset of that baseline.

## Current Coverage

The immutable PR-00 inventory covers 158 Feature IDs. The current reviewed
manifest covers 186; the 28 additions classify preserved Multi-Agent,
OpenTUI-interaction/page, versioned-health and mandatory Harness-health surfaces
rather than unrelated new product features:

| Surface | IDs |
| --- | ---: |
| CLI commands | 43 |
| Web HTTP/WebSocket routes | 46 |
| Plugin manifests and `provides` | 37 |
| Adapters | 3 |
| TUI actions | 5 |
| OpenTUI pages and interactions | 23 |
| Configuration environment keys | 7 |
| Database tables | 5 |
| Multi-Agent roles | 4 |
| Installer and release entrypoints | 12 |

Static discovery lives in `tests/feature_contract/inventory.py`. Curated
records cover required policy semantics that cannot be inferred safely from
syntax alone.

## Structural Baseline

| Metric | PR-00 value |
| --- | ---: |
| Production Python files | 182 |
| Production Python raw LOC | 38,897 |
| Production Python effective LOC | 33,270 |
| Functions/methods | 1,608 |
| Public top-level symbols | 472 |
| Functions over 60 lines | 78 |
| Functions over 100 lines | 28 |
| Top-level dependency edges | 17 |
| Feature IDs | 158 |

Metrics are recalculated from the immutable `audit_reference` Git tree, not the
evolving working tree. Only production Python files tracked at that reference
are counted; tests, documentation, build output, caches, and local files are
excluded. This keeps the PR-00 baseline reproducible throughout later refactors.

## Review and Validation

Run the preservation gates from the repository root:

```powershell
python -m pytest tests/feature_contract tests/test_repo_hygiene.py::test_feature_manifest_keeps_all_baseline_feature_ids -q
python -m pytest tests/test_maintainer_markdown_links.py -q
```

When a declaration is added, first run the contract suite and confirm that the
unclassified entry fails. Add a reviewed Feature ID, expected result, and real
contract-test node. Never reduce `baseline_feature_ids`, and never offset a
removed ID with an unrelated new feature.

## PR-00 Report

### Scope

- Handles: feature inventory, static discovery, critical runtime contracts,
  structural metrics, and no-regression gates.
- Does not handle: production consolidation or deletion; those begin only
  after this baseline is green.

### Feature parity

All 158 baseline IDs retain an entrypoint, expected result, and existing test
node. The automated suite verifies that discovered entries are classified and
that baseline IDs do not disappear.

### Structural changes

- Added only test infrastructure, the machine-readable manifest, and maintainer
  documentation.
- Deleted no production files, functions, commands, routes, plugins, adapters,
  installers, or UI capabilities.

### Validation

The final PR-00 report must record fresh results for pytest, mypy, Ruff, build,
OpenTUI, Web/Desktop, and Wheel/plugin discovery. Unavailable platform checks
remain explicitly unverified; they are never reported as passing by inference.
