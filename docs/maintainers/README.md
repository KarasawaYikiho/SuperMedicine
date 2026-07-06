# Maintainer Guide

This directory is the human-maintainer starting point for SuperMedicine. It
summarizes the current repository shape, names the authoritative entrypoints,
and separates stable project facts from archive notes and planned work.

## Start Here

1. Read [repository-map.md](repository-map.md) for the current module and
   ownership map.
2. Read [entrypoints.md](entrypoints.md) before changing command, installer,
   TUI, Web, or release behavior.
3. Read [quality-gates.md](quality-gates.md) before changing CI, packaging, or
   tests.
4. Read [maintenance-backlog.md](maintenance-backlog.md) for the current
   low-risk cleanup order.

## Current Sources Of Truth

| Topic | Source |
| --- | --- |
| Package metadata and console script | `pyproject.toml` |
| CLI parser and dispatch | `cli/parser.py` |
| CLI facade methods | `cli_entry.py` |
| Kernel architecture | `core/kernel.py` |
| Permission runtime | `permission/` |
| Plugin contract | `plugins/base_plugin.py` and plugin manifests |
| TUI launcher | `core/tui/app.py` |
| OpenTUI runtime | `core/tui/opentui_runtime.mjs` |
| Web server | `core/web/server.py` |
| Release workflow | `.github/workflows/ci.yml`, `setup.py`, `scripts/ci/` |
| User install guide | `docs/guides/INSTALL.md` |

## Archive Rules

Files under `docs/archive/` are historical or generated notes unless a current
document links to them as authoritative. Do not treat archive PASS claims,
roadmaps, or inventories as current behavior without checking code and tests.

## Working Tree Caution

Large changes are often developed in this repository at once. Before editing,
run:

```powershell
git status --short --branch
git diff --name-status
git diff --name-status --cached
```

If a file has both staged and unstaged changes, avoid editing it until its owner
has resolved the split index state.

