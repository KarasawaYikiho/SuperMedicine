# Phase Implementation Baseline

## Purpose And Scope

This document is the verifiable repository artifact for the phase implementation baseline. It maps the current SuperMedicine repository structure and compatibility boundaries before follow-on phase work.

This baseline avoids repeating full user guidance. Use [../README.md](../README.md)
for quick-start commands, [../INSTALL.md](../INSTALL.md) for installation detail,
and [../ARCHITECTURE.md](../ARCHITECTURE.md) for the current design narrative.

Scope for this baseline:

- Document the actual current repository layout and implementation entry points.
- Preserve existing runtime behavior while future phases are planned and implemented.
- Do not tag, release, publish, upload, or otherwise distribute artifacts as part of this baseline.
- Do not describe hypothetical package paths; all paths below are current repository paths.

## Actual Repository Layout

The current repository is organized around top-level modules plus first-party packages:

- `Cli.py` — console CLI entrypoint used by the `supermedicine` script.
- `Install.py` — installer/config initialization helper.
- `pyproject.toml` — package metadata, console script, pytest conventions, optional extras.
- `core/` — kernel, plugin registry, event bus, config, sessions, LLM helpers.
- `core/workspace.py` — explicit `workspaces/<id>` slug workspace layout and
  workspace-local TUI session-state helpers.
- `core/paper_import/` — copy-only workspace paper import, editable metadata,
  dedupe, and permission-gated enrichment primitives.
- `core/experience.py` — user-confirmed experience summary storage with general
  method tempdir scope and workspace-local scope.
- `core/tui/` — Chinese TUI workbench entrypoint and screens.
- `permission/` — permission policy model, PermissionEngine, audit logging, default policy resource.
- `plugins/` — plugin manifests and executable plugin entrypoints.
- `adapters/` — platform adapters and shared adapter sandbox/tool implementation.
- `agents/` — base agent abstractions, orchestrator, checkpointing, task state machine.
- `tests/` — pytest test suite using `test_*.py` modules and shared fixtures.

## CLI Commands And Run Flags

CLI implementation is in `Cli.py`:

- `main()` builds the `argparse` command tree.
- `CLI.init(project_dir)` backs `supermedicine init`.
- `CLI.status()` backs `supermedicine status`.
- `CLI.test()` backs `supermedicine test`.
- `CLI.run(...)` backs `supermedicine run` and delegates execution to `core.kernel.Kernel`.

Current `run` command interface:

- Positional argument: `task`.
- Flags:
  - `--verbose`
  - `--plugin`
  - `--action`
  - `--params-json`
  - `--params-file`
  - `--workspace`

Structured parameter helpers are also in `Cli.py`:

- `_load_params_json(...)`
- `_load_params_file(...)`
- `_resolve_run_params(...)`

`--params-json` and `--params-file` are mutually exclusive.

Workspace-aware command baseline:

- `supermedicine tui` launches the Chinese TUI workbench.
- `supermedicine workspace init/list/show/delete` manages slug workspaces under
  `workspaces/<id>`.
- `workspace delete` is a hard delete and requires exact `--confirm <id>`,
  destructive-path validation, PermissionEngine approval, and audit logging.
- `supermedicine run --workspace <id>` injects explicit workspace context; it
  must not read TUI recent workspace state.
- `supermedicine paper ... --workspace <id>` imports/lists/shows/edits papers and
  enriches metadata only after explicit confirmation and permission approval.
- `supermedicine experience ... --workspace <id>` suggests, adds, lists, views,
  edits, deletes, and exports user-confirmed experience records.

## Kernel And Execution Baseline

Runtime task execution is centralized in `core/kernel.py`:

- `Kernel.__init__(...)` wires config, event bus, plugin registry, sessions, checkpoints, and permissions.
- `Kernel.execute_task(...)` is the production plugin execution path.
- `Kernel._select_plugin_action(...)` maps task text to a plugin/action when explicit `--plugin` and `--action` are not supplied.

The plugin registry is in `core/plugin_registry.py`:

- `PluginRegistry.discover()` recursively discovers `plugin.yaml` manifests.
- `PluginRegistry.get(...)` returns `plugins.base_plugin.BasePlugin` wrappers.

The shared plugin execution contract is in `plugins/base_plugin.py`:

- `PluginMeta`
- `BasePlugin`
- `plugin_result(...)`
- `redact_sensitive(...)`

## PermissionEngine And Audit Logging Locations

Permission implementation:

- `permission/engine.py` — `PermissionEngine` and policy loading/checking.
- `permission/policy.py` — `PermissionPolicy`, `PermissionRule`, `HardLimits`, `PermissionResult`, default policy path helpers.
- `permission/default_policy.yaml` — packaged default policy resource.
- `.supermedicine/policies/default.yaml` — tracked project policy used by the current repository.

Audit implementation:

- `permission/audit.py` — `AuditLogger` writes JSON Lines audit entries.
- `core/kernel.py` uses `.supermedicine/policies/audit.jsonl` under the active policy directory.
- Adapter permission checks in `adapters/base_adapter.py` also initialize `PermissionEngine(..., audit.jsonl)`.
- Harness audit inspection actions are implemented in `plugins/harness/main.py` and helper logic under `plugins/harness/monitor.py`.

## Adapter Sandbox And Gated Tools

Shared adapter logic is in `adapters/base_adapter.py`:

- Abstract methods: `platform_name`, `tool_call`, `skill_load`, `subagent_dispatch`.
- Shared tool methods: `_tool_bash`, `_tool_read`, `_tool_write`, `_tool_edit`, `_tool_glob`, `_tool_grep`.
- Permission-gated tool ids: `bash`, `write`, `edit`.
- Project-root sandbox enforcement: `_resolve_sandbox_path(...)` rejects paths outside `self._project_dir`.
- Shared denial/error helpers: `_tool_permission_denied(...)`, `_permission_denied_result(...)`, `_sandbox_denied_result(...)`, `_resource_error(...)`.

Concrete adapters:

- `adapters/opencode/adapter.py` — `OpenCodeAdapter`; supports `bash`, `read`, `write`, `edit`, `glob`, `grep`, `skill`, `task`.
- `adapters/claude_code/adapter.py` — `ClaudeCodeAdapter`; supports `claude.capabilities`, `claude.runtime_status`, `claude.invoke`.
- `adapters/standalone/adapter.py` — `StandaloneAdapter`; local tool handling and simulated subagent dispatch.

## RAG Providers And Actions

RAG manifest and executable entrypoint:

- `plugins/rag/plugin.yaml`
- `plugins/rag/main.py`

RAG actions currently exposed:

- `rag.query`
- `rag.context.store`
- `rag.context.retrieve`

RAG provider contract and implementations:

- `plugins/rag/interface.py` — `RAGProviderConfig`, `RAGProvider`, `EmptyRAGProvider`, structured RAG errors, and `make_rag_result(...)`.
- `plugins/rag/local_provider.py` — `LocalRAGProvider` and `MockExternalVectorStoreProvider`.
- `plugins/rag/pubmed_provider.py` — `PubmedRAGProvider` with permission-gated external HTTP access.

## Workspace, Paper Import, And Experience Baseline

- Workspaces are stored at `workspaces/<id>` with slug ids only. CLI workspace
  use is explicit; workspace-scoped commands require or accept `--workspace` and
  do not silently use TUI recent selection.
- Paper import is copy-only into the selected workspace and supports common local
  paper formats: PDF, TeX, BibTeX/RIS, TXT, and Markdown. SHA-256 identifies the
  stored original, with DOI/PMID duplicate checks when metadata is available.
  Metadata remains editable after import.
- Paper metadata enrichment requires explicit confirmation, PermissionEngine,
  network and external API hard-limit context, and audit logging. No import path
  performs silent network access.
- Experience learning is enabled by default but persists only user-confirmed
  summaries/experience. Raw conversations are rejected. General method records
  live in an OS tempdir method layer; project/workspace details remain
  workspace-local. User-facing commands support view/edit/delete/export.
- Safety/privacy/security documentation and medical non-clinical disclaimers are
  part of this baseline; no tag, release, publish, package upload, paper upload,
  or external artifact upload is performed.

## Checkpoints And Sessions

Checkpointing:

- `agents/checkpoint.py` — `CheckpointManager`, checkpoint sanitization, save/load/recovery helpers.
- `core/kernel.py` — creates `CheckpointManager(self._config_path.parent / "checkpoints")` and writes dispatch/running/completed/failed checkpoints during task execution.
- `agents/orchestrator.py` — orchestrator checkpoint flow around agent dispatch.
- `agents/state_machine.py` — task states and valid transitions: `planning`, `dispatch`, `running`, `verifying`, `retry`, `completed`, `failed`.
- `plugins/harness/checkpoint_verifier.py` — checkpoint structural verification.

Sessions:

- `core/session_manager.py` — in-memory UUID `Session` and `SessionManager`, optional TTL cleanup, active-session listing.

## Plugin Manifests And Actions Overview

Plugin discovery uses `plugin.yaml` manifests under `plugins/`.

- `plugins/tools/python_stats/plugin.yaml`
  - `stats.descriptive`
  - `stats.ttest`
  - `stats.anova`
  - `stats.regression`
- `plugins/tools/r_survival/plugin.yaml`
  - `r.survival.km`
  - `r.survival.logrank`
  - `r.survival.cox`
- `plugins/rag/plugin.yaml`
  - `rag.query`
  - `rag.context.store`
  - `rag.context.retrieve`
- `plugins/harness/plugin.yaml`
  - `harness.integration.checkpoint`
  - `harness.integration.checkpoint_all`
  - `harness.monitor.permission_audit`
  - `harness.monitor.denied_actions`
  - `harness.monitor.anomaly`
  - `harness.monitor.performance`
  - `harness.monitor.failure_patterns`
- `plugins/standards/medical_writing/plugin.yaml`
  - `standard.consort`
  - `standard.strobe`
  - `standard.prisma`
  - `standard.stard`
- `plugins/standards/medical_citation/plugin.yaml`
  - `standard.citation.ama`
  - `standard.citation.vancouver`

Executable plugin entrypoints are the corresponding `main.py` files under each plugin directory, loaded through `plugins/base_plugin.py`.

## Test Conventions from `pyproject.toml`

Current pytest settings:

- `testpaths = ["tests"]`
- `python_files = ["test_*.py"]`
- `addopts = "-p no:cacheprovider"`

The test suite lives under `tests/`, with shared fixtures in `tests/conftest.py`.

## Compatibility Invariants For Future Phases

Future phase work should preserve these compatibility boundaries unless a phase explicitly supersedes them:

- Keep the console script target `supermedicine = "Cli:main"` compatible.
- Keep current CLI command names and existing `run` flags backward-compatible.
- Keep production plugin execution flowing through `core.kernel.Kernel.execute_task(...)` and the canonical `PermissionEngine` policy check.
- Keep policy files and audit logs under the canonical `.supermedicine/policies/` path unless a migration is explicitly documented.
- Keep adapter filesystem access constrained by the project-root sandbox in `adapters/base_adapter.py`.
- Keep `bash`, `write`, and `edit` tool calls permission-gated in adapters.
- Keep plugin discovery based on `plugin.yaml` manifests and executable `main.py` entrypoints.
- Keep plugin result shapes compatible with `plugins.base_plugin.plugin_result(...)` normalization.
- Keep checkpoint records JSON-serializable and sensitive-value-sanitized.
- Keep RAG external provider access permission-gated before network/API calls.
- Keep pytest discovery compatible with `tests/` and `test_*.py`.
- Do not introduce generated artifacts, build outputs, tags, releases, publishes, or uploads as part of phase implementation unless explicitly requested.
