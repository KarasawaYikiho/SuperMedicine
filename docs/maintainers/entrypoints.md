# Entrypoints

Use the canonical commands and ownership boundaries below in new
documentation, packaging logic, and tests. Compatibility wrappers remain only
where an existing public or release contract requires them.

## User Commands

| Task | Command |
| --- | --- |
| Help | `supermedicine --help` |
| Status | `supermedicine status` |
| Diagnostics | `supermedicine diagnose` |
| TUI dry run | `supermedicine tui --dry-run` |
| TUI launch | `supermedicine tui` |
| Web launch | `supermedicine web` |
| Tests | `python -m pytest tests/ -v` |

Console script:

```text
supermedicine = "cli.__main__:main"
```

## Python Entrypoint Files

| File | Role |
| --- | --- |
| `cli/__main__.py` | Console-script and `python -m cli` target. |
| `cli/facade.py` | CLI application facade. |
| `cli_entry.py` | Compatibility wrapper retained for packaged launchers. |
| `cli/parser.py` | Argument parser and dispatch. |
| `install.py` | Compatibility installer entry. |
| `install_entry.py` | Installer implementation entry. |
| `uninstall_entry.py` | Uninstaller entry. |
| `desktop/__main__.py` | Desktop package and `python -m desktop` target. |
| `gui_entry.py` | Compatibility wrapper retained for packaged launchers. |
| `gui_standalone.py` | Standalone GUI executable source. |

## Runtime Surfaces

| Surface | Primary files |
| --- | --- |
| CLI | `cli/__main__.py`, `cli/parser.py`, `cli/facade.py`, `cli/commands/` |
| Kernel | `core/kernel/` |
| TUI | `core/tui/app.py`, `core/tui/opentui_runtime.mjs` |
| Web | `core/web/server.py`, `core/web/frontend/` |
| Installer | `install_entry.py`, `installer/`, `setup.py`, `scripts/ci/` |

New entrypoint names need a reason, packaging coverage, and an owner file.
