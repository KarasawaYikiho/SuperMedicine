# Maintainer Guide

This index identifies the maintained repository contracts and the order in
which they should be reviewed. Temporary investigations, implementation plans,
debug transcripts, and historical rebuild notes belong in the ignored
`Temp/` archive rather than in the published documentation set.

## Read Order

1. [Repository map](repository-map.md)
2. [Entrypoints](entrypoints.md)
3. [Feature parity](feature-parity.md)
4. [Quality gates](quality-gates.md)
5. [CI workflows](ci-workflows.md)

## Sources of Truth

| Topic | Source |
| --- | --- |
| Package metadata | `pyproject.toml` |
| CLI parser | `cli/parser.py` |
| CLI facade | `cli/facade.py` |
| Kernel | `core/kernel/` |
| Permissions | `permission/` |
| Plugin contract | `plugins/base_plugin.py` and manifests |
| TUI launcher/runtime | `core/tui/` |
| Web server | `core/web/server.py` |
| Installer/release | `installer/`, `setup.py`, `scripts/ci/`, and release workflows |
| User install docs | `docs/guides/INSTALL.md` |
| CI structure | `docs/maintainers/ci-workflows.md` |

## Documentation Boundary

Publish only durable guidance and current contracts. Store generated reports,
plans, task ledgers, debug records, and historical implementation notes under
local-only `Temp/`. Never cite an archived pass result as evidence for the
current tree; rerun the applicable gate.

## Before Editing

```powershell
git status --short --branch
git diff --name-status
git diff --name-status --cached
```

Preserve unrelated work. Inspect files that contain both staged and unstaged
changes before editing, and keep each commit limited to its declared scope.
