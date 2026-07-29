# Repository Map

This is the canonical navigation map for maintainers. It records stable
ownership and public entrypoints without turning file counts, function counts,
or private module names into contracts.

## Top-Level Ownership

| Path | Responsibility |
|---|---|
| `core/` | Kernel, application services, workspaces, papers, LLM, Web, TUI, and Desktop backend |
| `permission/` | Canonical policy evaluation, authorization, audit, and operation guards |
| `plugins/` | Required Harness/RAG and optional research, statistics, standards, and figure capabilities |
| `agents/` | Optional Alpha/Beta/Gamma/Delta roles, orchestration, and checkpoints |
| `adapters/` | Optional Standalone, OpenCode, and Claude Code integration layers |
| `cli/` | Argument parsing and thin application-service delegation |
| `installer/` | Install plans, release payload extraction, and uninstall behavior |
| `scripts/ci/` | Build, verification, and release helpers called by workflows |
| `scripts/maintainers/` | Documentation and release-metadata maintenance tools |
| `tests/` | Stable behavior, security, architecture, packaging, and policy tests |
| `docs/` | User, architecture, maintainer, API, example, and reference documentation |
| `.github/workflows/` | CI, runtime smoke, package smoke, nightly, and release orchestration |

## Public Entrypoints

| Surface | Authority |
|---|---|
| Python console command | `pyproject.toml` `[project.scripts]` |
| Source installer | `install.py` delegating to `installer/` |
| Uninstaller | installed/source uninstall entry delegating to `installer/` |
| CLI | `cli/` parser and application facade |
| TUI | `core/tui/` with the OpenTUI bridge |
| Web and Desktop backend | `core/web/` |
| Plugin actions | plugin manifests discovered by `PluginRegistry` |
| Release files | `scripts/ci/` build and verification helpers |

## Ownership Boundaries

- Public surfaces call application services instead of constructing internal
  stores, permission engines, or plugin registries.
- `permission/` and `agents/` do not import `core/`; the Kernel composes them.
- Plugins declare actions in manifests and execute behind `PluginRegistry`.
- Adapter runtime Markdown is packaged content, not ordinary documentation.
- `pyproject.toml` owns the version; controlled mirrors are checked by
  `sync_release_metadata.py`.
- Runtime-generated state belongs in ignored data/workspace/build locations.

Use code search for symbol-level discovery. A static function inventory is not a
maintained contract.
