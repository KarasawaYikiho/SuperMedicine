# SuperMedicine API Reference

This document provides a concise API reference for SuperMedicine's core modules.
For full design context, see [ARCHITECTURE.md](../../ARCHITECTURE.md).

## Core Modules (`core/`)

### Kernel

The central microkernel that wires all components together.

```python
from core.kernel import Kernel

kernel = Kernel(
    config_path=Path(".supermedicine/config.yaml"),  # optional, SM_CONFIG overrides
    plugins_dir=Path("plugins"),                      # optional
    policies_dir=Path(".supermedicine/policies"),      # optional
)
```

**Key methods:**

| Method | Description |
|--------|-------------|
| `execute_task(message, progress_callback=None)` | Execute a task through the kernel |
| `config` | Access the `ConfigCenter` instance |
| `event_bus` | Access the `EventBus` instance |
| `plugin_registry` | Access the `PluginRegistry` instance |
| `permission_engine` | Access the `PermissionEngine` instance |

### ConfigCenter

Reads YAML configuration with `SM_*` environment variable overrides.

```python
from core.config_center import ConfigCenter

config = ConfigCenter(Path(".supermedicine/config.yaml"))
value = config.get("llm.provider")
redacted_snapshot = config.get_redacted_llm_config()
```

### EventBus

Topic-based publish/subscribe messaging.

```python
from core.event_bus import EventBus

bus = EventBus()

# Subscribe to a topic
bus.subscribe("task.completed", lambda data: print(data))

# Publish to a topic
bus.publish("task.completed", {"task_id": "wb-001"})
```

### PluginRegistry

Discovers `plugin.yaml` manifests and records plugin capabilities.

```python
from core.plugin_registry import PluginRegistry

registry = PluginRegistry(Path("plugins"))
plugins = registry.list_plugins()
```

### SessionManager

Creates UUID sessions and stores session-scoped state.

```python
from core.session_manager import SessionManager

manager = SessionManager()
session_id = manager.create_session()
```

## Effect System (`core/effect.py`)

Monadic container for functional error handling, inspired by Effect-TS.

```python
from core.effect import Effect

# Create success/failure
result = Effect.succeed(42)
error = Effect.fail("something went wrong")

# Wrap exceptions
result = Effect.from_callable(lambda: 1 / 0)

# Functional combinators
mapped = result.map(lambda x: x * 2)
chained = result.flat_map(lambda x: Effect.succeed(x + 1))
value = result.get_or_else(0)

# Status checks
result.is_success()  # bool
result.is_failure()  # bool
```

**Type signature:** `Effect[T, E]` where `T` is the success type and `E` is the error type.

## Agent System (`agents/`)

### Agent Roles

| Agent | Role | Description |
|-------|------|-------------|
| `AlphaAgent` | Analyst | Planning and requirements analysis |
| `BetaAgent` | Reviewer | Independent verification and review |
| `GammaAgent` | Writer | Drafting and content execution |
| `DeltaAgent` | Orchestrator | Routing and coordination |

### BaseAgent Interface

```python
from agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="custom-1", role="custom")

    def execute(self, task: dict) -> dict:
        # Implementation
        return {"status": "completed"}
```

### State Machine

Task states follow a strict lifecycle:

```
PLANNING -> DISPATCH -> RUNNING -> VERIFYING -> COMPLETED
                        |                      |
                        +-> FAILED             +-> RETRY (max 3) -> DISPATCH
```

```python
from agents.state_machine import StateMachine, TaskState

sm = StateMachine(task_id="task-001", max_retries=3)
sm.transition(TaskState.DISPATCH)
sm.state  # TaskState.DISPATCH
```

### Orchestrator

Coordinates multi-agent workflows with checkpoint persistence.

```python
from agents.orchestrator import Orchestrator

orchestrator = Orchestrator(kernel)
result = orchestrator.run(task)
```

## Database Layer (`core/database/`)

### Database

Thread-safe SQLite wrapper with context manager support.

```python
from core.database.database import Database

# Context manager (recommended)
with Database(Path("data.db")) as db:
    db.execute("INSERT INTO sessions ...")

# Manual lifecycle
db = Database(Path("data.db"))
db.connect()
try:
    db.execute("SELECT * FROM sessions")
finally:
    db.disconnect()
```

**Built-in tables:** `sessions`, `agents`, `plugins`, `migrations`

### Repository

Abstract repository pattern for clean data access.

```python
from core.database.repository import Repository

class SessionRepository(Repository[Session]):
    def create(self, entity: Session) -> Session: ...
    def get(self, id: str) -> Session | None: ...
    def update(self, entity: Session) -> Session: ...
    def delete(self, id: str) -> bool: ...
    def list_all(self) -> list[Session]: ...
```

## Permission System (`permission/`)

### PermissionEngine

Runtime enforcement of permission policies.

```python
from permission.engine import PermissionEngine

engine = PermissionEngine(
    policy_dir=Path(".supermedicine/policies"),
    audit_log=Path(".supermedicine/policies/audit.jsonl"),
)

# Check permission
result = engine.check(
    action="file.write",
    resource="/path/to/file",
    context={"user": "researcher"},
)
# result.allowed: bool
# result.reason: str
```

### PermissionPolicy

Policy data and fnmatch rule matching. Policies are defined in YAML files:

```yaml
# .supermedicine/policies/default.yaml
rules:
  - pattern: "workspaces/*"
    actions: ["read", "write"]
    effect: allow
  - pattern: "*.exe"
    actions: ["execute"]
    effect: deny
```

## Web API (`core/web/`)

REST and WebSocket endpoints for browser-based interaction.

**Installation:** `pip install supermedicine[web]`

### REST Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/status` | Project status and version |
| `POST` | `/api/v1/chat` | Send a message to the kernel |
| `GET` | `/api/v1/workspaces` | List all workspaces |
| `POST` | `/api/v1/workspaces` | Create a new workspace |
| `GET` | `/api/v1/workspaces/{id}` | Get workspace details |
| `DELETE` | `/api/v1/workspaces/{id}` | Delete a workspace |
| `GET` | `/api/v1/workspaces/{id}/papers` | List papers |
| `POST` | `/api/v1/workspaces/{id}/papers` | Import a paper |
| `GET` | `/api/v1/workspaces/{id}/papers/{pid}` | Get paper details |
| `PATCH` | `/api/v1/workspaces/{id}/papers/{pid}` | Update paper metadata |
| `POST` | `/api/v1/workspaces/{id}/papers/{pid}/enrich` | Enrich paper with LLM |
| `GET` | `/api/v1/workspaces/{id}/experiences` | List experiences |
| `POST` | `/api/v1/workspaces/{id}/experiences` | Add experience |
| `GET` | `/api/v1/workspaces/{id}/tools` | List workspace tools |
| `POST` | `/api/v1/workspaces/{id}/tools` | Add tools to workspace |
| `GET` | `/api/v1/tools/scan` | Scan for available tools |
| `GET` | `/api/v1/llm/providers` | List LLM providers |
| `GET` | `/api/v1/llm/providers/{name}` | Get provider details |
| `POST` | `/api/v1/llm/switch` | Switch active provider |
| `GET` | `/api/v1/permissions` | Permission status |
| `POST` | `/api/v1/permissions/mode` | Set permission mode |
| `POST` | `/api/v1/permissions/authorize` | Authorize external path |
| `GET` | `/api/v1/logs` | List logs |
| `GET` | `/api/v1/logs/{name}` | Get log details |
| `GET` | `/api/v1/experiments` | List experiments |
| `POST` | `/api/v1/experiments` | Start experiment |
| `POST` | `/api/v1/experiments/{id}/submit` | Submit experiment data |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://host:port/ws/chat` | Streaming chat with thinking/reasoning support |

**Message format (client -> server):**
```json
{"message": "Your query here"}
```

**Event format (server -> client):**
```json
{"type": "progress", "data": {...}}
{"type": "result", "data": {...}}
{"type": "error", "content": "Error message"}
```

### Starting the Server

```python
from core.web.server import start_server

start_server(host="127.0.0.1", port=8000)
```

Or via CLI:
```bash
supermedicine web
```
