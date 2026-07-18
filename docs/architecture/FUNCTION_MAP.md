# Function Map

This document is a maintainer-facing map of the current repository. It is not a
complete runtime trace. Dynamic dispatch, plugin discovery, decorators, Textual
callbacks, tests, and adapter bridges can introduce relationships that static
reading will not show.

## Entrypoints

| Entrypoint | Target |
| --- | --- |
| `supermedicine` | `cli_entry:main` from `pyproject.toml` |
| `python install.py` | Installer compatibility entry |
| `python install_entry.py` | Installer implementation entry |
| `python uninstall_entry.py` | Uninstaller entry |
| `supermedicine tui` | Python launcher for OpenTUI runtime |
| `supermedicine web` | Optional FastAPI surface |

## Core Runtime

| Module | Responsibility |
| --- | --- |
| `core/kernel.py` | Runtime wiring and task execution. |
| `core/config_center.py` | YAML config and environment overrides. |
| `core/event_bus.py` | Topic-based event publication. |
| `core/plugin_registry.py` | Plugin manifest discovery and registry. |
| `core/session_manager.py` | Session lifecycle. |
| `core/workspace.py` | Workspace path and lifecycle management. |
| `core/workspace_tools.py` | Workspace tool scan/import/run behavior. |
| `core/path_safety.py` | Path validation helpers. |
| `core/log_report*.py` | Local log report storage and rendering. |
| `core/operation_guard.py` | Guardrails for dangerous operations. |
| `core/runtime_capabilities.py` | Required Harness/RAG manifest, entry, action, storage, and disable-policy validation. |
| `core/runtime_pipeline.py` | UUID Harness runs, ordered checkpoints, performance recording, and unique finalization. |
| `core/rag_service.py` | Task classification, local-first retrieval, PubMed degradation, source budgeting, and workspace paper indexing. |

`core/kernel.py::Kernel.execute_task` is the sole formal execution envelope for
single/multi-agent, plugin, and LLM paths. CLI, TUI, and Web read the same
`RuntimeCapabilities` health snapshot.

## LLM and Paper Flow

| Module | Responsibility |
| --- | --- |
| `core/llm_manager.py` | Provider records and switching. |
| `core/llm_client.py` | Provider-neutral client behavior. |
| `core/llm_providers/` | OpenAI, Anthropic, OpenRouter, and compatible clients. |
| `core/paper_import/` | Copy-only paper import, models, enrichment boundaries. |
| `core/token_tracker.py` | Token accounting helpers. |

## UI Surfaces

| Module | Responsibility |
| --- | --- |
| `core/tui/` | TUI launcher, route metadata, screens, prompt input, OpenTUI bridge. |
| `core/web/server.py` | Optional FastAPI API and static frontend service. |
| `core/web/frontend/` | Browser frontend assets. |
| `gui_entry.py`, `gui_standalone.py` | GUI launch surfaces. |

## Permissions

| Module | Responsibility |
| --- | --- |
| `permission/policy.py` | Policy data and rule matching. |
| `permission/engine.py` | Runtime permission decisions. |
| `permission/audit.py` | JSONL audit records. |
| `permission/prompt_generator.py` | Advisory prompt/context text. |
| `permission/access_mode.py` | Conservative/full access mode representation. |

## Plugins

| Path | Responsibility |
| --- | --- |
| `plugins/base_plugin.py` | Base plugin contract. |
| `plugins/rag/` | Local and provider-interface RAG behavior. |
| `plugins/harness/` | Monitoring/checkpoint helpers. |
| `plugins/standards/medical_writing/` | CONSORT/STROBE/PRISMA/STARD helpers. |
| `plugins/standards/medical_citation/` | AMA and Vancouver formatting. |
| `plugins/tools/` | Python/R data-analysis, statistics, survival, heatmap, UMAP tools. |
| `plugins/figure/` | Figure profiling, layout, styling, export, and QA helpers. |
| `plugins/experiments/` | Config-driven experiment protocols. |

## Agents and Adapters

| Path | Responsibility |
| --- | --- |
| `agents/` | Internal alpha/beta/gamma/delta roles, state machine, checkpoints. |
| `adapters/base_adapter.py` | Adapter interface. |
| `adapters/opencode/` | Optional OpenCode metadata/adapter files. |
| `adapters/claude_code/` | Optional Claude Code skill/adapter files. |
| `adapters/standalone/` | Standalone adapter surface. |

## Installer and Release

| Path | Responsibility |
| --- | --- |
| `installer/` | Installer, release extraction, component installer, GUI installer. |
| `setup.py` | Custom packaging behavior. |
| `scripts/ci/` | Release zip, installer payload, PyInstaller helpers. |
| `.github/workflows/ci.yml` | CI and release smoke workflow. |

## Tests

Test files are intentionally feature-oriented where possible. Broad integration
tests remain for release, installer, TUI, workspace, permissions, and regression
baselines. Repository hygiene tests protect ignored artifacts, adapter metadata,
release labels, and documentation boundaries.

## Maintenance Note

Do not paste raw logs, secrets, private endpoints, or environment values into
this map. If exact call graphs are needed, regenerate them outside the tracked
docs and keep raw generated output in ignored `Temp/`.
