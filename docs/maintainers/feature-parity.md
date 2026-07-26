# Feature Parity

`feature_manifest.json` is the machine-readable inventory of stable product
capabilities. It is intentionally independent of test filenames, pytest node
names, private module paths, and historical structure metrics.

## Manifest fields

Every feature declares:

| Field | Meaning |
|---|---|
| `feature_id` | Stable identity for a user-observable capability |
| `category` | CLI, Web, plugin, adapter, TUI, configuration, database, agent, installer, or release surface |
| `entrypoint` | Reviewed route into the capability |
| `expected_result` | Behavior that must survive implementation changes |

RAG and Harness records additionally declare `required=true`,
`default_enabled=true`, and their fail-closed runtime contract. Alpha, Beta,
Gamma, and Delta declare `preserved=true` and `optional_enabled=true`.

## Preservation rule

`baseline_feature_ids` is immutable. New capabilities may add IDs, but a
refactor must not remove or repurpose a baseline ID. The current `features`
array must remain a unique superset of the baseline.

Behavior is protected in its business-domain tests. The manifest does not point
to those tests because file layout is not a product capability.

## Validation

```powershell
python -m pytest tests/test_feature_manifest.py tests/test_runtime.py tests/test_agents.py -q
```

For a broad rebuild, also run the complete quality gate from
[quality-gates.md](quality-gates.md). Historical implementation metrics and
past defect closures are frozen in
[rebuild-0.4.2.md](history/rebuild-0.4.2.md); they are not current constraints.
