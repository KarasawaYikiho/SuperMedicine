# Entrypoints

This page names the current entrypoints and compatibility surfaces. Prefer the
canonical commands in new documentation and tests.

## Canonical User Commands

| Task | Preferred command |
| --- | --- |
| Show CLI help | `supermedicine --help` |
| Project status | `supermedicine status` |
| Diagnostics | `supermedicine diagnose` |
| TUI dry run | `supermedicine tui --dry-run` |
| TUI launch | `supermedicine tui` |
| Web launch | `supermedicine web` |
| Run tests through Python | `python -m pytest tests/ -v` |

The package console script is declared in `pyproject.toml`:

```text
supermedicine = "cli_entry:main"
```

## Python Files

| File | Role | Notes |
| --- | --- | --- |
| `cli_entry.py` | CLI facade and console-script target | Imports `cli.parser.main` at the bottom. |
| `cli/parser.py` | Argument parser and command dispatch | Owns subcommand registration. |
| `install_entry.py` | Installer executable/source entry | Current root installer file. |
| `uninstall_entry.py` | Uninstall entry | Current root uninstall file. |
| `gui_entry.py` | GUI launcher | Thin launcher surface. |
| `gui_standalone.py` | Standalone GUI executable source | Used by PyInstaller workflow. |

Older docs may mention `Cli.py`, `Install.py`, `install.py`, or `Uninstall.py`.
Before preserving those names, verify whether they are generated release shims,
legacy compatibility names, or stale documentation.

## Runtime Surfaces

| Surface | Primary files | Boundary |
| --- | --- | --- |
| CLI | `cli/parser.py`, `cli_entry.py`, `cli/commands/` | User commands and orchestration facade. |
| Kernel | `core/kernel.py` | Runtime wiring, plugin execution, permission integration. |
| TUI | `core/tui/app.py`, `core/tui/opentui_runtime.mjs` | Python launches the TUI; OpenTUI JS owns the terminal runtime. |
| Web | `core/web/server.py`, `core/web/frontend/` | FastAPI app and browser UI. |
| Installer/release | `install_entry.py`, `installer/`, `setup.py`, `scripts/ci/` | Release packaging, installer payloads, executable smoke checks. |

## Maintenance Rule

Do not add a new entrypoint name unless it has all three:

1. A documented reason to exist.
2. A packaging or compatibility test.
3. A clear owner file where maintainers update it.

