# Repository Map

SuperMedicine is a Python package with optional Web, GUI, and OpenTUI runtime
surfaces. The default product boundary is the standalone Python core plus CLI.

## Top-Level Areas

| Path | Purpose | Maintainer notes |
| --- | --- | --- |
| `cli/` | Parser helpers and command modules | Keep command-specific behavior here when possible. |
| `cli_entry.py` | CLI facade | Should stay thin; avoid growing business logic here. |
| `core/` | Runtime services and feature modules | Shared behavior used by CLI, TUI, and Web. |
| `permission/` | Permission policy, engine, and audit logging | Runtime enforcement belongs here, not only in prompts or docs. |
| `plugins/` | Plugin base classes, manifests, and research tools | Dynamic loading makes static call maps incomplete. |
| `agents/` | Internal orchestration roles and state machine | Treat as core architecture, not external subagent runtime. |
| `adapters/` | Optional platform adapter metadata | Must not claim native runtime support unless implemented and tested. |
| `core/tui/` | Python TUI launcher and screen support | Currently shares ownership with the OpenTUI JS runtime. |
| `core/web/` | FastAPI server and frontend assets | Avoid hiding destructive CLI semantics behind auto-confirming routes. |
| `installer/` | Installer implementation | Release-critical code. |
| `scripts/ci/` | CI/release helper scripts | Keep output paths configurable for clean local and CI runs. |
| `tests/` | Pytest suite | Prefer focused test files over giant catch-all suites. |
| `docs/` | User, architecture, reference, and archive docs | Mark archive/generated docs clearly. |

## Ownership Boundaries

### CLI

`cli/parser.py` owns argument parsing and dispatch. `cli_entry.CLI` provides a
facade over command modules and shared runtime services. New command behavior
should generally live under `cli/commands/`, with `cli_entry.py` delegating.

### Kernel

`core/kernel.py` wires configuration, events, plugin discovery, session state,
checkpoint state, and permission enforcement. Shared runtime policy should go
through the kernel or the permission package rather than being duplicated in UI
layers.

### TUI

The TUI currently has two important surfaces:

- Python launcher/support code in `core/tui/app.py`.
- OpenTUI JavaScript runtime in `core/tui/opentui_runtime.mjs`.

This split should remain explicit. Route/page inventory needs one owner; if both
Python and JavaScript define it, add tests that catch drift.

### Web

`core/web/server.py` exposes API routes and currently delegates to the CLI
facade for many operations. This is convenient, but Web routes should not weaken
CLI confirmation, permission, or audit semantics.

### Release

`setup.py`, `installer/`, `.github/workflows/ci.yml`, and `scripts/ci/` are
release code. Treat packaging rewrites and payload assembly as product behavior,
not incidental build script glue.

## Large-File Watch List

Large files are not automatically wrong, but they are harder for humans to
review. Prioritize focused extraction only when behavior is already covered.

| Area | Risk |
| --- | --- |
| `tests/test_tui.py` | Can absorb unrelated screen tests and become hard to review. |
| `core/tui/app.py` | Launcher, metadata, and UI support can drift together. |
| `core/web/frontend/app.js` | Browser behavior may need feature-based modules. |
| `core/web/server.py` | API, service, and CLI delegation boundaries can blur. |
| `setup.py` | Custom packaging behavior needs narrow regression tests. |

