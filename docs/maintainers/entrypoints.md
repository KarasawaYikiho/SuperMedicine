# Entrypoints

Prefer the canonical commands below in new documentation and tests.

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
supermedicine = "cli_entry:main"
```

## Python Entrypoint Files

| File | Role |
| --- | --- |
| `cli_entry.py` | Console-script target and CLI facade. |
| `cli/parser.py` | Argument parser and dispatch. |
| `install.py` | Compatibility installer entry. |
| `install_entry.py` | Installer implementation entry. |
| `uninstall_entry.py` | Uninstaller entry. |
| `gui_entry.py` | GUI launcher. |
| `gui_standalone.py` | Standalone GUI executable source. |

## Runtime Surfaces

| Surface | Primary files |
| --- | --- |
| CLI | `cli/parser.py`, `cli_entry.py`, `cli/commands/` |
| Kernel | `core/kernel.py` |
| TUI | `core/tui/app.py`, `core/tui/opentui_runtime.mjs` |
| Web | `core/web/server.py`, `core/web/frontend/` |
| Installer | `install_entry.py`, `installer/`, `setup.py`, `scripts/ci/` |

New entrypoint names need a reason, packaging coverage, and an owner file.
