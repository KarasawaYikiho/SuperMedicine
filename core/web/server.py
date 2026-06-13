"""SuperMedicine Web API server.

Provides HTTP and WebSocket endpoints for interacting with the SuperMedicine
kernel from a browser-based interface.

Dependencies (optional):
    pip install supermedicine[web]
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app factory – lazy imports so the rest of the project never
# hard-requires fastapi/uvicorn.
# ---------------------------------------------------------------------------


def _ensure_fastapi() -> None:
    """Raise a clear error when fastapi/uvicorn are not installed."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Web interface requires 'fastapi' and 'uvicorn'. "
            "Install them with:  pip install supermedicine[web]"
        ) from exc


def create_app() -> Any:
    """Create and return the FastAPI application."""
    _ensure_fastapi()

    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(
        title="SuperMedicine Web API",
        version="0.4.2",
        description="Browser-based interface for SuperMedicine medical research agent",
    )

    # ---- state -----------------------------------------------------------
    _kernel_holder: dict[str, Any] = {}

    def _get_kernel() -> Any:
        """Lazily initialise a Kernel instance (cached)."""
        if "kernel" not in _kernel_holder:
            from pathlib import Path as _P

            project_dir = _P.cwd()
            from core.kernel import Kernel
            from permission.policy import ensure_default_policy

            policies_dir = project_dir / ".supermedicine" / "policies"
            ensure_default_policy(project_dir)

            _kernel_holder["kernel"] = Kernel(
                config_path=project_dir / ".supermedicine" / "config.yaml",
                plugins_dir=project_dir / "plugins",
                policies_dir=policies_dir,
            )
        return _kernel_holder["kernel"]

    # ---- REST endpoints --------------------------------------------------

    @app.get("/api/v1/status")
    async def get_status() -> dict[str, Any]:
        """Return project status information."""
        from pathlib import Path as _P

        project_dir = _P.cwd()
        config_dir = project_dir / ".supermedicine"
        plugins_dir = project_dir / "plugins"

        status: dict[str, Any] = {
            "version": "0.4.2",
            "project_dir": str(project_dir),
            "config_initialized": config_dir.exists(),
            "plugin_count": (
                len(list(plugins_dir.rglob("plugin.yaml")))
                if plugins_dir.exists()
                else 0
            ),
        }

        # Include LLM provider info if config is available
        if config_dir.exists():
            try:
                from core.config_center import ConfigCenter
                from core.llm_manager import LLMConfigManager

                config = ConfigCenter(config_dir / "config.yaml")
                manager = LLMConfigManager(config, restore_on_startup=False)
                provider = manager.get_current_provider(redacted=True)
                status["llm_provider"] = provider.get("provider", "unknown") if provider else "not configured"
            except Exception:
                status["llm_provider"] = "error reading config"

        return status

    @app.post("/api/v1/chat")
    async def chat(request: dict[str, Any]) -> dict[str, Any]:
        """Send a message to the Kernel and return the response."""
        message = request.get("message", "")
        if not message:
            return {"error": "No message provided", "status": "error"}

        try:
            kernel = _get_kernel()
            result = kernel.execute_task(message)
            return result
        except Exception as exc:
            logger.exception("Chat error")
            return {"error": str(exc), "status": "error"}

    # ---- CLI helper (lazy) ------------------------------------------------

    def _get_cli() -> Any:
        """Lazily initialise a CLI instance (cached)."""
        if "cli" not in _kernel_holder:
            from cli_entry import CLI
            _kernel_holder["cli"] = CLI()
        return _kernel_holder["cli"]

    # ---- Workspace endpoints ----------------------------------------------

    @app.get("/api/v1/workspaces")
    async def workspace_list() -> Any:
        """List all workspaces."""
        try:
            return _get_cli().workspace_list()
        except Exception as exc:
            logger.exception("workspace_list error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/workspaces")
    async def workspace_create(request: dict[str, Any]) -> dict[str, Any]:
        """Initialize a new workspace."""
        workspace_id = request.get("id", "")
        if not workspace_id:
            return {"error": "No workspace id provided", "status": "error"}
        try:
            return _get_cli().workspace_init(workspace_id, name=request.get("name"))
        except Exception as exc:
            logger.exception("workspace_create error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/workspaces/{workspace_id}")
    async def workspace_get(workspace_id: str) -> dict[str, Any]:
        """Show one workspace by id."""
        try:
            return _get_cli().workspace_show(workspace_id)
        except Exception as exc:
            logger.exception("workspace_get error")
            return {"error": str(exc), "status": "error"}

    @app.delete("/api/v1/workspaces/{workspace_id}")
    async def workspace_remove(workspace_id: str) -> dict[str, Any]:
        """Delete a workspace after confirmation."""
        try:
            return _get_cli().workspace_delete(workspace_id, confirm=workspace_id)
        except Exception as exc:
            logger.exception("workspace_remove error")
            return {"error": str(exc), "status": "error"}

    # ---- Paper endpoints --------------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/papers")
    async def paper_list(workspace_id: str) -> Any:
        """List papers in a workspace."""
        try:
            return _get_cli().paper_list(workspace_id)
        except Exception as exc:
            logger.exception("paper_list error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/workspaces/{workspace_id}/papers")
    async def paper_create(workspace_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Import a paper into a workspace."""
        source_path = request.get("source_path", "")
        if not source_path:
            return {"error": "No source_path provided", "status": "error"}
        try:
            return _get_cli().paper_import(
                workspace_id,
                source_path,
                metadata=request.get("metadata"),
                enrich=request.get("enrich", False),
                confirm_enrich=request.get("confirm_enrich", False),
            )
        except Exception as exc:
            logger.exception("paper_create error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/workspaces/{workspace_id}/papers/{paper_id}")
    async def paper_get(workspace_id: str, paper_id: str) -> dict[str, Any]:
        """Show one paper by id."""
        try:
            return _get_cli().paper_show(workspace_id, paper_id)
        except Exception as exc:
            logger.exception("paper_get error")
            return {"error": str(exc), "status": "error"}

    @app.patch("/api/v1/workspaces/{workspace_id}/papers/{paper_id}")
    async def paper_update(workspace_id: str, paper_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Edit paper metadata."""
        metadata = request.get("metadata", {})
        try:
            return _get_cli().paper_edit(workspace_id, paper_id, metadata)
        except Exception as exc:
            logger.exception("paper_update error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/workspaces/{workspace_id}/papers/{paper_id}/enrich")
    async def paper_enrich(workspace_id: str, paper_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Enrich a paper with LLM-extracted metadata."""
        try:
            return _get_cli().paper_enrich(
                workspace_id, paper_id, confirm_enrich=request.get("confirm_enrich", True)
            )
        except Exception as exc:
            logger.exception("paper_enrich error")
            return {"error": str(exc), "status": "error"}

    # ---- Experience endpoints ---------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/experiences")
    async def experience_list(workspace_id: str) -> Any:
        """List experiences in a workspace."""
        try:
            return _get_cli().experience_list(workspace_id)
        except Exception as exc:
            logger.exception("experience_list error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/workspaces/{workspace_id}/experiences")
    async def experience_create(workspace_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Add a new experience."""
        scope = request.get("scope", "")
        title = request.get("title", "")
        summary = request.get("summary", "")
        if not all([scope, title, summary]):
            return {"error": "scope, title, and summary are required", "status": "error"}
        try:
            return _get_cli().experience_add(
                workspace_id,
                scope,
                title,
                summary,
                tags=request.get("tags"),
                confirm=request.get("confirm", True),
            )
        except Exception as exc:
            logger.exception("experience_create error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/workspaces/{workspace_id}/experiences/{experience_id}")
    async def experience_get(workspace_id: str, experience_id: str) -> dict[str, Any]:
        """View one experience by id."""
        try:
            return _get_cli().experience_view(experience_id, workspace_id)
        except Exception as exc:
            logger.exception("experience_get error")
            return {"error": str(exc), "status": "error"}

    @app.delete("/api/v1/workspaces/{workspace_id}/experiences/{experience_id}")
    async def experience_remove(workspace_id: str, experience_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Delete one experience after confirmation."""
        scope = request.get("scope", "")
        if not scope:
            return {"error": "scope is required", "status": "error"}
        try:
            return _get_cli().experience_delete(
                experience_id, workspace_id, scope, confirm=experience_id
            )
        except Exception as exc:
            logger.exception("experience_remove error")
            return {"error": str(exc), "status": "error"}

    # ---- Tool endpoints ---------------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/tools")
    async def tool_list(workspace_id: str, language: str | None = None) -> Any:
        """List tools in a workspace."""
        try:
            return _get_cli().tool_list(workspace_id, language=language)
        except Exception as exc:
            logger.exception("tool_list error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/workspaces/{workspace_id}/tools")
    async def tool_create(workspace_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Add tools to a workspace."""
        try:
            return _get_cli().tool_add(
                workspace_id,
                selections=request.get("selections"),
                language=request.get("language"),
                overwrite=request.get("overwrite", False),
            )
        except Exception as exc:
            logger.exception("tool_create error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/tools/scan")
    async def tool_scan(language: str | None = None) -> Any:
        """Scan for available tools."""
        try:
            return _get_cli().tool_scan(language=language)
        except Exception as exc:
            logger.exception("tool_scan error")
            return {"error": str(exc), "status": "error"}

    # ---- LLM endpoints ---------------------------------------------------

    @app.get("/api/v1/llm/providers")
    async def llm_providers() -> Any:
        """List configured LLM providers."""
        try:
            return _get_cli().llm_list()
        except Exception as exc:
            logger.exception("llm_providers error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/llm/providers/{name}")
    async def llm_provider_get(name: str) -> dict[str, Any]:
        """Show one LLM provider."""
        try:
            return _get_cli().llm_show(name)
        except Exception as exc:
            logger.exception("llm_provider_get error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/llm/switch")
    async def llm_switch(request: dict[str, Any]) -> dict[str, Any]:
        """Switch the active LLM provider."""
        provider = request.get("provider", "")
        if not provider:
            return {"error": "No provider specified", "status": "error"}
        try:
            return _get_cli().llm_switch(provider)
        except Exception as exc:
            logger.exception("llm_switch error")
            return {"error": str(exc), "status": "error"}

    # ---- Permission endpoints ---------------------------------------------

    @app.get("/api/v1/permissions")
    async def permission_status() -> dict[str, Any]:
        """Show current permission status."""
        try:
            return _get_cli().permission_status()
        except Exception as exc:
            logger.exception("permission_status error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/permissions/mode")
    async def permission_set_mode(request: dict[str, Any]) -> dict[str, Any]:
        """Set the permission mode."""
        mode = request.get("mode", "")
        if not mode:
            return {"error": "No mode specified", "status": "error"}
        try:
            return _get_cli().permission_set_mode(
                mode,
                confirm_full=request.get("confirm_full", False),
                interactive=False,
            )
        except Exception as exc:
            logger.exception("permission_set_mode error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/permissions/authorize")
    async def permission_authorize(request: dict[str, Any]) -> dict[str, Any]:
        """Authorize an external path."""
        path = request.get("path", "")
        if not path:
            return {"error": "No path specified", "status": "error"}
        try:
            return _get_cli().permission_authorize(path)
        except Exception as exc:
            logger.exception("permission_authorize error")
            return {"error": str(exc), "status": "error"}

    # ---- Log endpoints ----------------------------------------------------

    @app.get("/api/v1/logs")
    async def log_list() -> Any:
        """List available logs."""
        try:
            return _get_cli().log_list()
        except Exception as exc:
            logger.exception("log_list error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/logs/{name}")
    async def log_get(name: str) -> dict[str, Any]:
        """Show one log by name."""
        try:
            return _get_cli().log_show(name)
        except Exception as exc:
            logger.exception("log_get error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/logs")
    async def log_create(request: dict[str, Any]) -> dict[str, Any]:
        """Write a log entry."""
        message = request.get("message", "")
        if not message:
            return {"error": "No message provided", "status": "error"}
        try:
            return _get_cli().log_write(message, session_id=request.get("session_id"))
        except Exception as exc:
            logger.exception("log_create error")
            return {"error": str(exc), "status": "error"}

    # ---- Experiment endpoints ---------------------------------------------

    @app.get("/api/v1/experiments")
    async def experiment_list() -> Any:
        """List available experiments."""
        try:
            return _get_cli().experiment_list()
        except Exception as exc:
            logger.exception("experiment_list error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/experiments")
    async def experiment_create(request: dict[str, Any]) -> dict[str, Any]:
        """Start a new experiment."""
        protocol = request.get("protocol", "")
        if not protocol:
            return {"error": "No protocol specified", "status": "error"}
        try:
            return _get_cli().experiment_start(protocol, session_id=request.get("session_id"))
        except Exception as exc:
            logger.exception("experiment_create error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/experiments/{session_file}/submit")
    async def experiment_submit(session_file: str, request: dict[str, Any]) -> dict[str, Any]:
        """Submit data for an experiment step."""
        step_id = request.get("step_id", "")
        input_json = request.get("input_json", "")
        if not all([step_id, input_json]):
            return {"error": "step_id and input_json are required", "status": "error"}
        try:
            return _get_cli().experiment_submit(
                session_file, step_id, input_json, calculate=request.get("calculate", False)
            )
        except Exception as exc:
            logger.exception("experiment_submit error")
            return {"error": str(exc), "status": "error"}

    # ---- Self Evolution endpoints ----------------------------------------

    @app.get("/api/v1/self-evolution")
    async def self_evolution_list() -> Any:
        """List self evolution artifacts."""
        try:
            from pathlib import Path as _P
            project_dir = _P.cwd()
            artifacts_dir = project_dir / "self_evolution"
            if not artifacts_dir.exists():
                return []
            artifacts = []
            for f in artifacts_dir.glob("*.json"):
                try:
                    import json as _json
                    data = _json.loads(f.read_text(encoding="utf-8"))
                    artifacts.append({
                        "id": f.stem,
                        "type": data.get("type", "unknown"),
                        "instruction": data.get("instruction", ""),
                        "status": data.get("status", "pending"),
                        "path": str(f),
                    })
                except Exception:
                    continue
            return artifacts
        except Exception as exc:
            logger.exception("self_evolution_list error")
            return {"error": str(exc), "status": "error"}

    @app.post("/api/v1/self-evolution/generate")
    async def self_evolution_generate(request: dict[str, Any]) -> dict[str, Any]:
        """Generate a self evolution artifact."""
        instruction = request.get("instruction", "")
        artifact_type = request.get("type", "code")
        output = request.get("output", "")
        if not all([instruction, output]):
            return {"error": "instruction and output are required", "status": "error"}
        try:
            return _get_cli().self_evolve(
                instruction=instruction,
                artifact_type=artifact_type,
                output=output,
                preview=True,
            )
        except Exception as exc:
            logger.exception("self_evolution_generate error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/self-evolution/{artifact_id}")
    async def self_evolution_get(artifact_id: str) -> dict[str, Any]:
        """View one self evolution artifact."""
        try:
            from pathlib import Path as _P
            project_dir = _P.cwd()
            artifact_path = project_dir / "self_evolution" / f"{artifact_id}.json"
            if not artifact_path.exists():
                return {"error": "Artifact not found", "status": "error"}
            import json as _json
            return _json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.exception("self_evolution_get error")
            return {"error": str(exc), "status": "error"}

    @app.delete("/api/v1/self-evolution/{artifact_id}")
    async def self_evolution_delete(artifact_id: str) -> dict[str, Any]:
        """Delete one self evolution artifact."""
        try:
            from pathlib import Path as _P
            project_dir = _P.cwd()
            artifact_path = project_dir / "self_evolution" / f"{artifact_id}.json"
            if not artifact_path.exists():
                return {"error": "Artifact not found", "status": "error"}
            artifact_path.unlink()
            return {"success": True, "message": f"Artifact {artifact_id} deleted"}
        except Exception as exc:
            logger.exception("self_evolution_delete error")
            return {"error": str(exc), "status": "error"}

    # ---- Diagnose endpoints ----------------------------------------------

    @app.get("/api/v1/diagnose")
    async def diagnose_all() -> dict[str, Any]:
        """Get all diagnostics."""
        try:
            return _get_cli().diagnose()
        except Exception as exc:
            logger.exception("diagnose_all error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/diagnose/config")
    async def diagnose_config() -> dict[str, Any]:
        """Get config diagnostics."""
        try:
            result = _get_cli().diagnose()
            return result.get("config", {})
        except Exception as exc:
            logger.exception("diagnose_config error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/diagnose/llm")
    async def diagnose_llm() -> dict[str, Any]:
        """Get LLM diagnostics."""
        try:
            result = _get_cli().diagnose()
            return result.get("llm", {})
        except Exception as exc:
            logger.exception("diagnose_llm error")
            return {"error": str(exc), "status": "error"}

    @app.get("/api/v1/diagnose/install")
    async def diagnose_install() -> dict[str, Any]:
        """Get install diagnostics."""
        try:
            result = _get_cli().diagnose()
            return {
                "audit": result.get("audit", {}),
                "log_storage": result.get("log_storage", {}),
            }
        except Exception as exc:
            logger.exception("diagnose_install error")
            return {"error": str(exc), "status": "error"}

    # ---- WebSocket chat --------------------------------------------------

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: Any) -> None:
        """Streaming chat via WebSocket with thinking/reasoning support."""
        await websocket.accept()
        logger.info("WebSocket client connected")

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"message": raw}

                message = data.get("message", "")
                if not message:
                    await websocket.send_json(
                        {"type": "error", "content": "No message provided"}
                    )
                    continue

                # Stream progress updates via progress_callback
                async def _stream_result() -> None:
                    loop = asyncio.get_running_loop()

                    def progress_callback(info: dict[str, Any]) -> None:
                        # Thread-safe: submit coroutine to the main event loop
                        # from the worker thread spawned by run_in_executor.
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json(
                                {"type": "progress", "data": info}
                            ),
                            loop,
                        )

                    try:
                        kernel = _get_kernel()
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: kernel.execute_task(
                                message, progress_callback=progress_callback
                            ),
                        )
                        await websocket.send_json(
                            {"type": "result", "data": result}
                        )
                    except Exception as exc:
                        logger.exception("WebSocket chat error")
                        await websocket.send_json(
                            {"type": "error", "content": str(exc)}
                        )

                await _stream_result()

        except Exception as exc:
            logger.info("WebSocket disconnected: %s", exc)

    # ---- Static files & index --------------------------------------------

    frontend_dir = Path(__file__).parent / "frontend"
    if frontend_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def index() -> str:
            """Serve the frontend index page."""
            index_file = frontend_dir / "index.html"
            if index_file.exists():
                return index_file.read_text(encoding="utf-8")
            return "<h1>SuperMedicine Web</h1><p>Frontend not found.</p>"

    return app


def start_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    reload: bool = False,
) -> None:
    """Start the SuperMedicine web server.

    Parameters
    ----------
    host:
        Bind address.  Defaults to ``127.0.0.1`` (localhost only).
    port:
        Port number.  Defaults to ``8000``.
    reload:
        Enable auto-reload for development.
    """
    _ensure_fastapi()

    import uvicorn

    logger.info("Starting SuperMedicine Web server on %s:%s", host, port)
    uvicorn.run(
        "core.web.server:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
