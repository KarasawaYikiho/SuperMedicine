# Maintainer Guide

This directory is the starting point for repository maintenance.

## Read Order

1. [repository-map.md](repository-map.md)
2. [entrypoints.md](entrypoints.md)
3. [quality-gates.md](quality-gates.md)
4. [maintenance-backlog.md](maintenance-backlog.md)
5. [feature-parity.md](feature-parity.md)
6. [human-maintainer-rebuild.md](human-maintainer-rebuild.md)
7. [human-maintenance.md](human-maintenance.md)

## Sources of Truth

| Topic | Source |
| --- | --- |
| Package metadata | `pyproject.toml` |
| CLI parser | `cli/parser.py` |
| CLI facade | `cli_entry.py` |
| Kernel | `core/kernel.py` |
| Permissions | `permission/` |
| Plugin contract | `plugins/base_plugin.py` and manifests |
| TUI launcher/runtime | `core/tui/` |
| Web server | `core/web/server.py` |
| Installer/release | `installer/`, `setup.py`, `.github/workflows/ci.yml`, `scripts/ci/` |
| User install docs | `docs/guides/INSTALL.md` |
| Current maintenance snapshot | `docs/maintainers/human-maintenance-baseline.json` |

## Archive Rule

Historical or generated notes belong under local-only `Temp/`, not in tracked
`docs/archive/`. Do not use archive PASS claims as current release evidence
without rerunning tests.

## Before Editing

```powershell
git status --short --branch
git diff --name-status
git diff --name-status --cached
```

Do not overwrite unrelated user changes. If a file has both staged and unstaged
changes, inspect it before editing.
