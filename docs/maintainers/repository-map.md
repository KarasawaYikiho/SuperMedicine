# Repository Map

SuperMedicine is a Python package with optional Web, GUI, OpenTUI, OpenCode, and
Claude Code surfaces. The supported default product remains the standalone
Python core plus CLI.

## Top-Level Areas

| Path | Purpose | Maintainer note |
| --- | --- | --- |
| `cli/` | Parser helpers and command modules | Keep command behavior here when possible. |
| `cli_entry.py` | Console-script facade | Keep thin; delegate feature logic. |
| `core/` | Shared runtime services | Used by CLI, TUI, Web, plugins, and tests. |
| `permission/` | Runtime permission policy and audit | Enforcement belongs here. |
| `plugins/` | Plugin manifests and research tools | Dynamic discovery makes static maps incomplete. |
| `agents/` | Internal orchestration components | Not an external platform subagent runtime by itself. |
| `adapters/` | Optional platform metadata and bridges | Do not claim native runtime support without tests. |
| `installer/` | Installer and release extraction | Release-critical code. |
| `scripts/ci/` | Packaging and release helpers | Keep temp output outside the repo. |
| `tests/` | Pytest suite | Prefer focused regression tests. |
| `docs/` | User and maintainer documentation | `docs/archive/` is ignored; use `Temp/` for local archives. |

## Ownership Boundaries

- CLI parsing lives in `cli/parser.py`.
- CLI facade methods live in `cli_entry.py`.
- Runtime wiring lives in `core/kernel.py`.
- Permission checks live in `permission/`.
- Release behavior lives in `installer/`, `setup.py`, `.github/workflows/ci.yml`,
  and `scripts/ci/`.
- OpenTUI behavior spans `core/tui/app.py`, `core/tui/opentui_runtime.py`, and
  `core/tui/opentui_runtime.mjs`.

## Large-File Watch List

| Area | Risk |
| --- | --- |
| `tests/test_tui.py` | Can become a catch-all for unrelated screen behavior. |
| `core/tui/app.py` | Launcher, metadata, and UI support can drift together. |
| `core/web/frontend/app.js` | Browser behavior may need feature-based modules. |
| `core/web/server.py` | API and CLI delegation boundaries can blur. |
| `setup.py` | Packaging behavior is release-critical and needs narrow tests. |
