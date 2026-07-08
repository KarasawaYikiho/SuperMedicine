# API Reference

This is a compact map of the stable internal APIs most likely to matter to
contributors. Treat direct imports as code contracts only when tests cover them.

## Core

| Module | Purpose |
| --- | --- |
| `core.kernel.Kernel` | Coordinates config, events, plugins, permissions, sessions, and task execution. |
| `core.config_center.ConfigCenter` | Reads YAML config and environment overrides. |
| `core.event_bus.EventBus` | Topic-based publish/subscribe. |
| `core.plugin_registry.PluginRegistry` | Discovers plugin manifests and capabilities. |
| `core.session_manager.SessionManager` | Creates and stores session state. |
| `core.workspace.WorkspaceManager` | Creates, lists, resolves, and deletes workspaces safely. |
| `core.workspace_tools.WorkspaceToolService` | Scans, imports, lists, and runs workspace tools. |

## Permissions

| Module | Purpose |
| --- | --- |
| `permission.engine.PermissionEngine` | Runtime allow/deny decisions. |
| `permission.policy.PermissionPolicy` | Policy data and rule evaluation. |
| `permission.audit.AuditLogger` | JSONL audit records. |

Permission checks are runtime enforcement. Prompt helpers are advisory.

## LLM Providers

| Module | Purpose |
| --- | --- |
| `core.llm_manager.LLMConfigManager` | Provider records, switching, validation. |
| `core.llm_client` | Provider-neutral client helpers. |
| `core.llm_providers.*` | OpenAI, Anthropic, OpenRouter, and compatible provider clients. |

Provider records require API format, Base URL, model, and key source.

## Plugins

Plugins use manifests under `plugins/` and implement action-based execution.
Common result payloads use structured `status`, `output`, `error`, and metadata
fields.

## Web API

The optional Web surface is implemented in `core/web/server.py` and requires the
`web` extra:

```bash
python -m pip install -e ".[web]"
supermedicine web
```

Default address:

```text
http://127.0.0.1:8000
```

Primary route groups cover status, chat, workspaces, papers, experiences, tools,
LLM providers, permissions, logs, and experiments.

## Examples

See [examples](../examples/README.md) for CLI workflows and small API usage
snippets.
