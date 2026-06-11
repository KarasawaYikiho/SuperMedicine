# SuperMedicine Web Interface Plan

> Planning document for a localhost+port web visualization interface  
> Reuses the existing Kernel as the sole backend entry point

---

## 1. Architecture

### 1.1 Integration Model

The web interface sits alongside the existing CLI and TUI as a **third presentation layer**. It does **not** replace or modify the Kernel; it wraps it through a thin HTTP/WebSocket server.

```
Browser (localhost:PORT)
    |
    +-- HTTP REST API  ──┐
    |                     |
    +-- WebSocket  ───────┤
                          v
                   Web Server Layer (FastAPI)
                          |
                          v
                     Kernel (unchanged)
                   /    |    \    \
             Config  EventBus  Plugins  LLM
             Center            Registry  Manager
```

**Key principle**: The Kernel, PermissionEngine, EventBus, and all core modules remain untouched. The web server is a new optional entry point, like the TUI.

### 1.2 Process Model

- **Single process**: The FastAPI server runs in the same Python process as the Kernel.
- **Async-native**: FastAPI's async support handles concurrent HTTP requests and WebSocket connections without blocking the Kernel.
- **Background tasks**: Long-running operations (LLM chat, plugin execution) run via `asyncio` tasks, with progress reported through WebSocket.

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **HTTP Framework** | FastAPI | Async-native, auto OpenAPI docs, WebSocket support, minimal boilerplate |
| **ASGI Server** | Uvicorn | Production-grade, pairs with FastAPI |
| **WebSocket** | FastAPI built-in (`WebSocket`) | No extra dependency; SSE as fallback for streaming |
| **Frontend** | Vanilla HTML + CSS + JS (no build step) | Zero build tooling, served as static files from FastAPI, easy to maintain |
| **Markdown Rendering** | marked.js (CDN) | Client-side markdown for chat messages |
| **Syntax Highlighting** | highlight.js (CDN) | Code blocks in chat responses |
| **Icons** | Lucide (CDN) | Lightweight, consistent icon set |

**Why no React/Vue/Svelte**: The project's TUI is already lightweight. A no-build-step frontend keeps the dependency surface minimal and avoids introducing Node.js tooling into a Python-only project.

---

## 3. API Design

### 3.1 REST Endpoints

All endpoints are prefixed with `/api/v1`. Responses use the same structured dict format the CLI already returns.

#### System

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `GET` | `/api/v1/status` | Project status, version, init state | `CLI.status()` |
| `GET` | `/api/v1/diagnose` | Secret-safe diagnostics | `CLI.diagnose()` |

#### Chat / LLM

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `POST` | `/api/v1/chat` | Send a message, get streamed response via WebSocket | `Kernel.execute_task()` with LLM path |
| `GET` | `/api/v1/llm/providers` | List configured LLM providers (redacted) | `CLI.llm_list()` |
| `GET` | `/api/v1/llm/providers/{name}` | Show one provider (redacted) | `CLI.llm_show()` |
| `POST` | `/api/v1/llm/switch` | Switch current provider | `CLI.llm_switch()` |

#### Workspace

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `GET` | `/api/v1/workspaces` | List all workspaces | `CLI.workspace_list()` |
| `POST` | `/api/v1/workspaces` | Initialize a workspace | `CLI.workspace_init()` |
| `GET` | `/api/v1/workspaces/{id}` | Show workspace details | `CLI.workspace_show()` |
| `DELETE` | `/api/v1/workspaces/{id}` | Delete workspace (requires confirm) | `CLI.workspace_delete()` |

#### Papers

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `GET` | `/api/v1/workspaces/{id}/papers` | List papers in workspace | `CLI.paper_list()` |
| `POST` | `/api/v1/workspaces/{id}/papers` | Import a paper | `CLI.paper_import()` |
| `GET` | `/api/v1/workspaces/{id}/papers/{pid}` | Show paper details | `CLI.paper_show()` |
| `PATCH` | `/api/v1/workspaces/{id}/papers/{pid}` | Edit paper metadata | `CLI.paper_edit()` |
| `POST` | `/api/v1/workspaces/{id}/papers/{pid}/enrich` | Enrich paper | `CLI.paper_enrich()` |

#### Experience

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `GET` | `/api/v1/workspaces/{id}/experiences` | List experiences | `CLI.experience_list()` |
| `POST` | `/api/v1/workspaces/{id}/experiences` | Add experience | `CLI.experience_add()` |
| `GET` | `/api/v1/workspaces/{id}/experiences/{eid}` | View experience | `CLI.experience_view()` |
| `PATCH` | `/api/v1/workspaces/{id}/experiences/{eid}` | Edit experience | `CLI.experience_edit()` |
| `DELETE` | `/api/v1/workspaces/{id}/experiences/{eid}` | Delete experience | `CLI.experience_delete()` |
| `POST` | `/api/v1/workspaces/{id}/experiences/suggest` | Suggest classification | `CLI.experience_suggest()` |
| `GET` | `/api/v1/workspaces/{id}/experiences/export` | Export experiences | `CLI.experience_export()` |

#### Tools

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `POST` | `/api/v1/workspaces/{id}/tools/init` | Initialize tools | `CLI.tool_init()` |
| `GET` | `/api/v1/workspaces/{id}/tools` | List tools | `CLI.tool_list()` |
| `GET` | `/api/v1/tools/scan` | Scan tool candidates | `CLI.tool_scan()` |
| `POST` | `/api/v1/workspaces/{id}/tools/import` | Import scanned tools | `CLI.tool_add()` |
| `GET` | `/api/v1/workspaces/{id}/tools/{lang}/{tid}` | Show tool | `CLI.tool_show()` |
| `POST` | `/api/v1/workspaces/{id}/tools/{lang}/{tid}/run` | Prepare tool invocation | `CLI.tool_run()` |

#### Experiment

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `GET` | `/api/v1/experiments/protocols` | List protocols | `CLI.experiment_list()` |
| `POST` | `/api/v1/experiments/start` | Start experiment session | `CLI.experiment_start()` |
| `GET` | `/api/v1/experiments/context` | Show experiment context | `CLI.experiment_context()` |
| `POST` | `/api/v1/experiments/config` | Add experiment config | `CLI.experiment_add_config()` |
| `GET` | `/api/v1/experiments/sessions/{file}` | Show session | `CLI.experiment_show()` |
| `POST` | `/api/v1/experiments/sessions/{file}/submit` | Submit step data | `CLI.experiment_submit()` |

#### Permissions

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `GET` | `/api/v1/permissions/status` | Current permission mode | `CLI.permission_status()` |
| `POST` | `/api/v1/permissions/mode` | Set access mode | `CLI.permission_set_mode()` |
| `POST` | `/api/v1/permissions/authorize` | Authorize external dir | `CLI.permission_authorize()` |
| `POST` | `/api/v1/permissions/revoke` | Revoke external dir | `CLI.permission_revoke()` |

#### Logs

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `POST` | `/api/v1/logs/write` | Write a log entry | `CLI.log_write()` |
| `GET` | `/api/v1/logs` | List log entries | `CLI.log_list()` |
| `GET` | `/api/v1/logs/{file}` | Show a log | `CLI.log_show()` |
| `GET` | `/api/v1/logs/location` | Show storage locations | `CLI.log_location()` |

#### Self-Evolution

| Method | Path | Description | Maps to |
|--------|------|-------------|---------|
| `POST` | `/api/v1/evolve` | Generate self-evolution artifact | `CLI.self_evolve()` |

### 3.2 WebSocket Endpoints

| Path | Purpose | Protocol |
|------|---------|----------|
| `/ws/chat` | Real-time chat with streaming LLM responses | Client sends `{"type": "message", "content": "..."}`, server streams back `{"type": "thinking_delta" \| "thinking_done" \| "assistant_delta" \| "assistant_done" \| "status" \| "error", "content": "..."}` |
| `/ws/events` | General Kernel event bus relay | Server pushes EventBus events as `{"topic": "...", "data": {...}}` |

#### Chat WebSocket Protocol Detail

```
Client -> Server:
  {"type": "message", "content": "用户消息", "session_id": "optional-uuid"}

Server -> Client (streaming):
  {"type": "status", "content": "Kernel 已接收任务，正在选择执行路径。"}
  {"type": "thinking_delta", "content": "思考片段..."}     // if LLM supports reasoning
  {"type": "thinking_done", "content": ""}
  {"type": "assistant_delta", "content": "回复片段..."}
  {"type": "assistant_delta", "content": "继续回复..."}
  {"type": "assistant_done", "content": "", "metadata": {...}}

Server -> Client (error):
  {"type": "error", "content": "错误描述", "code": "error_code"}
```

---

## 4. Frontend Structure

### 4.1 Pages/Views

The frontend mirrors the TUI screens as a single-page application with tab navigation:

| Tab | TUI Equivalent | Content |
|-----|----------------|---------|
| **Dashboard** | `dashboard.py` | System status, workspace count, LLM status, token stats |
| **Chat** | `chat_view.py` | Message input, conversation display, thinking animation, streaming |
| **Workspace** | `workspace_screen.py` | Workspace list, create/delete, details |
| **Papers** | `paper_screen.py` | Paper list, import, metadata, enrichment |
| **Experience** | `experience_screen.py` | Experience list, add/edit/delete, export |
| **Tools** | `tool_screen.py` | Tool scan, import, list, run |
| **Experiment** | `experiment_screen.py` | Protocol list, session management, step submission |
| **LLM** | `llm_screen.py` | Provider list, switch, configuration |
| **Permissions** | `permission_screen.py` | Mode status, authorize/revoke directories |
| **Logs** | `log_screen.py` | Log list, view, real-time follow |

### 4.2 Chat View Design

The chat view is the most complex component. It features:

- **Message input**: Textarea at bottom, Enter to send, Shift+Enter for newline
- **Conversation display**: Scrollable message list with user/assistant/system message styling
- **Thinking animation**: Animated "..." indicator during LLM reasoning phase, collapsible thinking content
- **Streaming display**: Text appears incrementally as tokens arrive via WebSocket
- **Markdown rendering**: Assistant responses rendered as markdown with syntax highlighting
- **Secret redaction**: Client-side display mirrors server-side `_redact_sensitive_text()`
- **Medical boundary notice**: Persistent disclaimer banner

### 4.3 File Structure

```
core/web/
  __init__.py
  server.py           # FastAPI app, startup/shutdown, CORS
  routes/
    __init__.py
    system.py          # /api/v1/status, /api/v1/diagnose
    chat.py            # /api/v1/chat, /ws/chat
    workspace.py       # /api/v1/workspaces/*
    paper.py           # /api/v1/workspaces/{id}/papers/*
    experience.py      # /api/v1/workspaces/{id}/experiences/*
    tools.py           # /api/v1/tools/*, /api/v1/workspaces/{id}/tools/*
    experiment.py      # /api/v1/experiments/*
    permissions.py     # /api/v1/permissions/*
    logs.py            # /api/v1/logs/*
    llm.py             # /api/v1/llm/*
    evolve.py          # /api/v1/evolve
    ws_events.py       # /ws/events
  static/
    index.html         # Main SPA shell
    css/
      style.css        # All styles
    js/
      app.js           # Router, tab management, API client
      chat.js          # Chat WebSocket, streaming, thinking animation
      components.js    # Reusable UI components (tables, forms, modals)
      utils.js         # Markdown rendering, secret redaction, formatting
```

---

## 5. Security Considerations

### 5.1 Binding

- Default: `127.0.0.1:8420` (localhost only, not exposed to network)
- Configurable via `SM_WEB_HOST` and `SM_WEB_PORT` environment variables
- CLI flag: `supermedicine web --host 0.0.0.0 --port 8080` (explicit opt-in for network access)

### 5.2 Permission Enforcement

- All API endpoints go through the same `PermissionEngine.check()` path as CLI/TUI
- No endpoint bypasses permission gates
- Destructive operations (workspace delete, experience delete) require explicit confirmation in the request body

### 5.3 Secret Protection

- All API responses pass through `redact_sensitive()` before serialization
- LLM provider configs returned with `redacted=True`
- WebSocket messages redacted server-side before sending
- No API keys, tokens, or secrets ever reach the browser

### 5.4 CORS

- Default: Allow only `http://127.0.0.1:PORT` and `http://localhost:PORT`
- Configurable for development scenarios

### 5.5 Rate Limiting

- Basic in-memory rate limiter for chat endpoint (prevent accidental LLM cost spikes)
- Configurable via `SM_WEB_RATE_LIMIT` (default: 30 requests/minute for chat)

---

## 6. Configuration

### 6.1 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SM_WEB_HOST` | `127.0.0.1` | Bind address |
| `SM_WEB_PORT` | `8420` | Bind port |
| `SM_WEB_CORS_ORIGINS` | `http://127.0.0.1:{port},http://localhost:{port}` | Allowed CORS origins |
| `SM_WEB_RATE_LIMIT` | `30` | Chat requests per minute |

### 6.2 CLI Entry Point

```python
# In Cli.py, add:
def web(self, host: str = "127.0.0.1", port: int = 8420, open_browser: bool = True):
    """启动 Web 可视化界面"""
    from core.web.server import create_app, run_server
    app = create_app(project_root=Path.cwd())
    run_server(app, host=host, port=port, open_browser=open_browser)
```

### 6.3 Dependencies

Add to `pyproject.toml` optional dependencies:

```toml
[project.optional-dependencies]
web = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
]
```

The web feature is **opt-in**: users install with `pip install supermedicine[web]` and run `supermedicine web`. The core package remains dependency-light.

---

## 7. Implementation Phases

### Phase 1: Foundation (Core + Chat)
**Priority: Highest — delivers the primary value (LLM chat via browser)**

1. Create `core/web/server.py` — FastAPI app factory, static file serving, startup/shutdown hooks
2. Create `core/web/routes/system.py` — `/api/v1/status` endpoint
3. Create `core/web/routes/chat.py` — `/api/v1/chat` (non-streaming fallback) + `/ws/chat` (streaming WebSocket)
4. Create `core/web/static/index.html` — SPA shell with tab navigation
5. Create `core/web/static/css/style.css` — Base styles, dark theme matching TUI aesthetic
6. Create `core/web/static/js/app.js` — Tab router, API client utility
7. Create `core/web/static/js/chat.js` — WebSocket connection, streaming display, thinking animation
8. Create `core/web/static/js/utils.js` — Markdown rendering, secret redaction
9. Add `web` CLI command to `Cli.py`
10. Add `web` optional dependency group to `pyproject.toml`

**Deliverable**: User can run `supermedicine web`, open browser, and have a streaming chat with the LLM.

### Phase 2: Dashboard + System Views
**Priority: High — provides system overview**

1. Create `core/web/routes/llm.py` — LLM provider endpoints
2. Implement Dashboard tab — system status, workspace count, LLM status, token stats
3. Implement LLM tab — provider list, switch
4. Implement Permissions tab — mode status, authorize/revoke

**Deliverable**: Full system visibility and LLM management from browser.

### Phase 3: Workspace + Paper + Experience Management
**Priority: Medium — data management views**

1. Create `core/web/routes/workspace.py` — Workspace CRUD
2. Create `core/web/routes/paper.py` — Paper CRUD + enrichment
3. Create `core/web/routes/experience.py` — Experience CRUD + export
4. Implement Workspace, Papers, Experience tabs with tables, forms, modals
5. Create `core/web/static/js/components.js` — Reusable table/form/modal components

**Deliverable**: Full workspace data management from browser.

### Phase 4: Tools + Experiment + Logs
**Priority: Lower — specialized views**

1. Create `core/web/routes/tools.py` — Tool scan/import/run
2. Create `core/web/routes/experiment.py` — Experiment protocol/session management
3. Create `core/web/routes/logs.py` — Log viewing + real-time follow
4. Create `core/web/routes/evolve.py` — Self-evolution
5. Implement Tools, Experiment, Logs tabs

**Deliverable**: Complete feature parity with TUI.

### Phase 5: Polish + Events
**Priority: Nice-to-have**

1. Create `core/web/routes/ws_events.py` — General EventBus relay via WebSocket
2. Add real-time notifications for background events
3. Add responsive design for mobile/tablet
4. Add keyboard shortcuts (matching TUI bindings)
5. Add search/filter across views

---

## 8. Key Design Decisions

### 8.1 Why FastAPI over Flask?

- **Async support**: LLM streaming requires non-blocking I/O; Flask's sync model would require threading hacks
- **WebSocket**: FastAPI has native WebSocket support; Flask requires Flask-SocketIO (additional dependency)
- **Auto docs**: FastAPI generates OpenAPI docs at `/docs` — useful for API consumers
- **Type hints**: FastAPI's Pydantic integration matches the project's type annotation style

### 8.2 Why No Frontend Framework?

- **Zero build step**: No Node.js, no webpack, no npm — keeps the project Python-only
- **Simplicity**: The TUI has ~10 screens; vanilla JS with a simple tab router is sufficient
- **CDN dependencies**: marked.js and highlight.js loaded from CDN, no local node_modules
- **Maintainability**: Any Python developer can maintain the frontend without JS toolchain knowledge

### 8.3 Why WebSocket over SSE?

- **Bidirectional**: Chat requires sending messages from client to server
- **Lower overhead**: Single persistent connection vs. repeated SSE connections
- **Event relay**: The `/ws/events` endpoint benefits from bidirectional capability (future: client can filter events)

### 8.4 Conversation State

- **Server-side**: Chat history stored in `SessionManager` (existing), keyed by session UUID
- **Client-side**: Browser stores conversation in memory; page refresh clears display but server retains history
- **Session continuity**: Client can reconnect with `session_id` parameter to resume a conversation

---

## 9. Verification Standard

After implementation, the following must hold:

1. `supermedicine web` starts the server on `127.0.0.1:8420` and opens the browser
2. All REST endpoints return the same structured dicts as the CLI equivalents
3. Chat WebSocket streams LLM responses incrementally with thinking animation
4. All responses are secret-redacted (no API keys in browser)
5. Permission enforcement is identical to CLI/TUI paths
6. `pip install supermedicine` without `[web]` does not pull in FastAPI/uvicorn
7. Existing tests continue to pass (no core module modifications)
