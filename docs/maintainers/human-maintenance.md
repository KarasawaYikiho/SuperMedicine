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
| Feature IDs | 195 | at least 195 |
| Production Python files | 159 | 138-145 |
| Effective production Python LOC | 33,526 | 32,500-34,000 |
| Functions/methods | 1,586 | 1,450-1,500 |
| Public top-level symbols | 520 | 410-430 |
| Functions over 60 lines | 88 | at most 55-58 |
| Functions over 100 lines | 19 | at most 10 |
| Top-level dependency edges | 12 | at most 12 |

Targets are structural budgets, not permission to hide functions, generate Web
routes dynamically, weaken runtime contracts, or combine unrelated domains in
large files. Feature and surface preservation remains the hard gate.

The non-regression ceiling is stored separately in
`human-maintenance-budget.json` and enforced by the current-tree contract test.
It freezes the achieved tree so later maintenance cannot spend the recovered
file, LOC, function, symbol, long-function, or dependency budget silently. The
lower values above remain stretch targets, not permission to conceal static
feature surfaces or exceed the reviewed file-size limits.

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
| Workspace service/facade authority | 3 | -104 | -96 | -4 |
| OpenTUI/desktop convergence and Textual retirement | -4 | -5,600 | -4,796 | -361 |
| Shared ServiceResult compatibility conversion | 8 | +3 | -5 | -10 |
| Redaction compatibility module registry | -1 | +3 | +4 | 0 |
| LLM and agent/harness execution service authority | -1 | -2 | 0 | 0 |
| Permission/log and adapter system service authority | -1 | -7 | -4 | 0 |
| Workspace, paper/RAG, and experience research authority | -2 | -21 | -13 | 0 |
| Four CLI command-group authorities | -5 | -30 | -15 | 0 |

The workspace change preserves `AppResult`, `AppError`, and
`ApplicationFacade`, moves atomic create/delete into `WorkspaceService`, and
removes the duplicate manager, payload, permission, audit, and destructive-path
implementation from the facade.

The TUI/desktop change keeps the OpenTUI renderer as the only production TUI,
retains reviewed historical TUI imports through an explicit alias registry,
and connects its authenticated bridge actions to real services. The result
compatibility change centralizes service/operation metadata, safe internal
error text, and legacy error-code-to-exception conversion. Existing
`Service.require_data(result)` call signatures remain intact as declarative
callables and are covered by direct runtime signature and exception tests.
The redaction compatibility change removes the star-import implementation file,
maps `core.redaction` directly to the security-owned `permission.redaction`
authority, and keeps static typing through `core/redaction.pyi`.
The execution service change co-locates the two small LLM and agent/harness
application services in `core/services/execution.py`; explicit module aliases
and `.pyi` facades preserve both historical import paths and every reviewed
method signature.
The system service change similarly co-locates adapter authorization with the
permission/log/diagnostics application boundary. `PermissionChecker`, both
service classes, and both historical module paths remain directly importable;
permission decisions and policy loading remain explicit code.
The research service change places its three related application services in a
799-line authority, preserving explicit RAG, enrichment, permission, audit,
confirmation, and evolution flows. That file is now at the merge-size limit;
additional domains must not be added to it.
The CLI change groups the existing static command functions into four files:
research, execution, tools, and system. `cli/parser.py` remains the static
43-command authority; the nine former module paths and every command signature
remain available through aliases and `.pyi` facades.

## Final verification

The completed maintenance tree passed the following release gates on
2026-07-22:

- isolated Python suite: 1,256 passed, 4 skipped;
- Ruff and mypy checks over all 163 production Python files;
- wheel and source-distribution build, followed by a clean wheel-install smoke
  that discovered all 15 manifests/plugins;
- OpenTUI suite: 26 passed, 516 assertions, including automated navigation and
  full-page interaction checks;
- rebuilt CLI, GUI, and installer executables with successful dry-run or
  self-test entrypoints;
- packaged `SuperMedicine v0.4.2b0.zip` extracted into a clean directory, where
  the CLI dry-run, GUI self-test report, and installer self-test all exited
  successfully.

The only Python warning was the known upstream `wheel.bdist_wheel` deprecation
warning exercised by the repository-hygiene packaging test.

## Change rule

Keep one domain or one duplicate pattern per change. Regenerate the snapshot
only after reviewing every signature, Feature ID, surface, and role delta. Do
not accept fewer surface entries, historical imports, permission checks, audit
events, RAG/Harness enforcement, Multi-Agent roles, or release entrypoints.
