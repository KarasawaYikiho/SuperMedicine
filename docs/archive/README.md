# Archive

This directory contains historical plans, audits, generated inventories, and
debug-review notes. These files are useful context, but they are not current
source-of-truth documents unless a current guide links to them explicitly.

## How To Use This Directory

- Check current code and tests before relying on an archive claim.
- Treat PASS/complete language as historical evidence, not current verification.
- Treat generated inventories as navigation aids, not runtime traces.
- Prefer current docs under `docs/maintainers/`, `docs/architecture/`, and
  `docs/guides/` for onboarding and release work.

## Common Archive Types

| Type | Examples | Maintainer rule |
| --- | --- | --- |
| Generated inventory | `FunctionMapASTInventory.md` | Regenerate or verify before using for impact analysis. |
| Historical plan | `ExecutionRoadmap.md`, `PhaseImplementationPlan.md` | Use for background only. |
| Debug/review ledger | `DebugReviewTaskLedger.md`, `DebugReviewManualValidation.md` | Re-run checks before making release claims. |
| Audit note | `PlatformIntegrationAudit.md`, `RepositoryOptimizationAudit.md` | Convert useful findings into current docs or issues. |

## Promotion Rule

If an archive item becomes current guidance, move or summarize it in a current
document and link back here for historical detail. Do not make maintainers infer
current policy from old planning files.

