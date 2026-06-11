# SuperMedicine Architecture Guide

This guide explains SuperMedicine's architectural design. For the full technical
reference, see [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Microkernel Design

SuperMedicine uses a **microkernel architecture** where the core provides minimal
essential services, and all domain logic is added through plugins and components.

```text
CLI / TUI / Web / Optional Adapters
              |
              v
           Kernel
             |
             +-- ConfigCenter      (YAML config + env overrides)
             +-- EventBus          (pub/sub messaging)
             +-- PluginRegistry    (manifest discovery)
             +-- SessionManager    (UUID session state)
             +-- PermissionEngine  (runtime enforcement)
             +-- LLMConfigManager  (provider management)
             +-- CheckpointManager (agent checkpoint persistence)
```

The Kernel (`core/kernel.py`) wires these components together. It does not
contain domain logic itself — that lives in plugins, agents, and workspace modules.

## Layer Structure

### Layer 1: Core (`core/`)

Foundation services that everything else depends on:

| Component | Purpose |
|-----------|---------|
| `ConfigCenter` | Reads YAML config, supports `SM_*` env overrides, redacts secrets |
| `EventBus` | Topic-based publish/subscribe for decoupled communication |
| `PluginRegistry` | Discovers `plugin.yaml` manifests, records capabilities |
| `SessionManager` | Creates UUID sessions, stores session-scoped state |
| `WorkspaceManager` | Anchors workspaces under `workspaces/<id>`, rejects path traversal |
| `LLMConfigManager` | Provider-neutral LLM routing (OpenAI, Anthropic, OpenRouter, custom) |
| `Effect[T, E]` | Monadic error handling container |

### Layer 2: Permission System (`permission/`)

Two-layer permission architecture:

```text
Action request
    |
    +--> Runtime layer: PermissionEngine -> PermissionPolicy -> AuditLogger
    |    (Deny-Overrides-Allow, hard limits, enforced decisions)
    |
    +--> Prompt layer: safety text and rejection templates
         (Advisory only, not a runtime veto)
```

**Modes:**

| Mode | Behavior |
|------|----------|
| `conservative` | Default. Project-local allowed; external writes/execution denied unless authorized |
| `full` | Relaxes SuperMedicine's restrictions after explicit confirmation |

Policies are defined in YAML with fnmatch patterns:

```yaml
rules:
  - pattern: "workspaces/*"
    actions: ["read", "write"]
    effect: allow
  - pattern: "*.exe"
    actions: ["execute"]
    effect: deny
```

### Layer 3: Agent Orchestration (`agents/`)

Multi-role agent system with state machine and checkpoints.

**State machine lifecycle:**

```text
IDLE -> PLANNING -> DISPATCH -> RUNNING -> VERIFYING
  ^                                           |
  +--------------- RETRY (max 3) ------------+
                       |
                 COMPLETED / FAILED
```

**Agent roles:**

| Agent | Role | Stage |
|-------|------|-------|
| Alpha | Analyst | Planning and requirements analysis |
| Beta | Reviewer | Independent verification |
| Gamma | Writer | Drafting and execution |
| Delta | Orchestrator | Routing and coordination |

The `Orchestrator` coordinates agents through tasks, with `CheckpointManager`
persisting state for crash recovery.

### Layer 4: Plugin Ecosystem (`plugins/`)

Plugins are discovered from `plugin.yaml` manifests and execute through the
Kernel's permission model.

```text
plugins/
  base_plugin.py       Base class and execution contract
  rag/                 RAG Provider Interface (local TF-IDF, mock external)
  harness/             Audit monitoring and quality assessment
  tools/               Python statistics and R survival interfaces
  standards/           Medical writing checklists and citation formatting
  experiments/         Config-driven experiment protocols
```

**Plugin execution contract:**
- Input: `action: str`, `params: dict`, optional read-only `context: dict`
- Permission: plugins are not permission entry points; Kernel/PermissionEngine gates execution
- Output: unified shape `{status, plugin, action, output, error, metadata}`
- Errors: structured `plugin_error` for load failures, unknown actions, runtime exceptions

### Layer 5: Database Layer (`core/database/`)

SQLite-based persistence with repository pattern:

```python
# Database: thread-safe wrapper
with Database(Path("data.db")) as db:
    db.execute("...")

# Repository: abstract CRUD interface
class SessionRepository(Repository[Session]):
    def create(self, entity): ...
    def get(self, id): ...
    def update(self, entity): ...
    def delete(self, id): ...
    def list_all(self): ...
```

Built-in tables: `sessions`, `agents`, `plugins`, `migrations`

### Layer 6: Web API (`core/web/`)

FastAPI-based REST and WebSocket interface:

```text
Browser <-> FastAPI <-> Kernel
              |
              +-- REST endpoints (/api/v1/*)
              +-- WebSocket chat (/ws/chat)
              +-- Static frontend
```

### Layer 7: Workspace Layer

Domain modules for research workflows:

| Module | Purpose |
|--------|---------|
| `workspace.py` | Workspace lifecycle and path safety |
| `paper_import/` | Copy-only paper import with SHA-256 dedup |
| `experience.py` | User-confirmed experience summaries |
| `experiment_guide.py` | Config-driven experiment protocols |
| `workspace_tools.py` | Tool scanning, import, and execution |

## Plugin System

### Creating a Plugin

1. Create a directory under `plugins/`
2. Add a `plugin.yaml` manifest:

```yaml
name: my-plugin
version: "1.0"
description: "My custom plugin"
actions:
  - name: analyze
    description: "Analyze data"
```

3. Implement the plugin class:

```python
from plugins.base_plugin import BasePlugin, plugin_result

class MyPlugin(BasePlugin):
    def execute(self, action: str, params: dict, context: dict = None) -> dict:
        if action == "analyze":
            # Implementation
            return plugin_result(
                status="success",
                plugin="my-plugin",
                action=action,
                output={"result": "..."},
            )
        return plugin_result(
            status="error",
            plugin="my-plugin",
            action=action,
            error=f"Unknown action: {action}",
        )
```

### Plugin Discovery

Plugins are auto-discovered from `plugin.yaml` manifests:

```bash
# List discovered plugins
supermedicine plugin list
```

## Permission System

### How It Works

1. An action request arrives (file write, tool execution, etc.)
2. `PermissionEngine.check()` evaluates against loaded policies
3. Policies use Deny-Overrides-Allow semantics
4. All decisions are logged to `audit.jsonl`
5. Advisory prompts provide additional safety context

### Policy Configuration

```yaml
# .supermedicine/policies/default.yaml
rules:
  - pattern: "workspaces/*/papers/*"
    actions: ["read"]
    effect: allow
  - pattern: "../*"
    actions: ["read", "write", "delete"]
    effect: deny
    reason: "Path traversal not allowed"
```

### CLI Management

```bash
supermedicine permission status
supermedicine permission mode conservative
supermedicine permission authorize /path/to/allowed-dir
supermedicine permission revoke /path/to/allowed-dir
```

## Design Principles

1. **Preserve behavior** — changes require explicit approval
2. **Runtime enforcement** — permissions are checked in code, not prompts
3. **Core independence** — platform adapters are optional add-ons
4. **Plugin extensibility** — capabilities added through manifests and interfaces
5. **Research boundaries** — outputs require qualified human review

## Further Reading

- [ARCHITECTURE.md](../../ARCHITECTURE.md) — full technical reference
- [SECURITY.md](../../SECURITY.md) — security model and boundaries
- [FUNCTION_MAP.md](../../FUNCTION_MAP.md) — callable inventory
- [API Reference](../api/README.md) — module and endpoint details
