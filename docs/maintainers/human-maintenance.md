# Human Maintenance Phase 2

This guide is the execution record for the feature-preserving maintenance plan
that follows the first Human Maintainer Rebuild. The machine-readable source of
truth is [human-maintenance-baseline.json](human-maintenance-baseline.json).

## Phase 0 baseline

Regenerate the reviewed current-tree snapshot with:

```powershell
python -m scripts.maintainers.human_maintenance_snapshot
python -m pytest tests/feature_contract -q
```

The snapshot freezes every current Feature ID and discovered surface entry,
public Python function/method signatures, per-file and per-group structural
metrics, one maintenance role for each production Python file, and a
feature-to-authority/test map.

The measured current tree differs from the planning estimate because
RuntimePaths, ApplicationFacade, OpenTUI lifecycle work, and two previously
unrecorded Multi-Agent Web routes landed after the analyzed source tree. The
reviewed starting point is therefore:

| Metric | Reviewed current tree | Steady-state target |
| --- | ---: | ---: |
| Feature IDs | 189 | at least 189 |
| Production Python files | 172 | 138-145 |
| Functions/methods | 1,914 | 1,450-1,500 |
| Public top-level symbols | 556 | 410-430 |
| Functions over 60 lines | 90 | at most 55-58 |
| Functions over 100 lines | 19 | at most 10 |
| Top-level dependency edges | 12 | at most 12 |

Targets are structural budgets, not permission to hide functions, generate Web
routes dynamically, weaken runtime contracts, or combine unrelated domains in
large files. Feature and surface preservation remains the hard gate.

## File roles

Every production Python file has exactly one reviewed role in the snapshot:

- `authority`: the implementation source for domain or runtime behavior;
- `interface`: CLI, Web, TUI, or GUI entry code;
- `compat`: a historical import or API facade;
- `data`: static protocol or constant declarations;
- `generated/release`: installer, build, or release-critical code;
- `candidate`: a reviewed convergence candidate.

The initial review identified `core/application.py`, whose workspace operations
overlapped the established application services, and `core/time_utils.py`,
whose two aliases can be reviewed for direct reuse. Workspace behavior now has
one authority in `WorkspaceService`; `ApplicationFacade` remains a compatibility
contract for authenticated UI bridges and only adapts service results. The
remaining candidate label does not authorize deletion; its Feature IDs,
callers, signatures, and tests must first be traced to an authority
implementation.

## Completed convergence

| Change | Files | Raw LOC | Effective LOC | Functions/methods |
| --- | ---: | ---: | ---: | ---: |
| Workspace service/facade authority | 3 | -107 | -99 | -4 |

The workspace change preserves `AppResult`, `AppError`, and
`ApplicationFacade`, moves atomic create/delete into `WorkspaceService`, and
removes the duplicate manager, payload, permission, audit, and destructive-path
implementation from the facade.

## Change rule

Keep one domain or one duplicate pattern per change. Regenerate the snapshot
only after reviewing every signature, Feature ID, surface, and role delta. Do
not accept fewer surface entries, historical imports, permission checks, audit
events, RAG/Harness enforcement, Multi-Agent roles, or release entrypoints.
