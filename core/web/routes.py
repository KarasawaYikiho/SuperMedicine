"""Domain route registration for the SuperMedicine Web adapter."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

from core.web.runtime import (
    WebRuntime,
    experiment_session_path,
    llm_provider_list_response,
    service_data,
    web_error,
)


def application_data(result: Any) -> Any:
    """Map the application facade result without routing through the CLI."""
    if result.ok:
        return result.data
    error = result.error
    assert error is not None
    status_code = {
        "validation_error": 422,
        "not_found": 404,
        "permission_denied": 403,
        "conflict": 409,
        "dependency_unavailable": 503,
        "internal_error": 500,
    }.get(error.code, 500)
    return web_error(error.message, status_code, code=error.code)

logger = logging.getLogger(__name__)


def register_status_routes(app: Any, runtime: WebRuntime) -> None:
    # ---- REST endpoints --------------------------------------------------

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        """Return the minimal readiness signal used by the desktop launcher."""
        return {"status": "ok"}

    @app.get("/api/v1/status")
    async def get_status() -> Any:
        """Return project status information."""
        return service_data(
            runtime.service("permission_log_system").application_status()
        )

    @app.post("/api/v1/chat")
    async def chat(request: dict[str, Any]) -> dict[str, Any]:
        """Send a message to the Kernel and return the response."""
        message = request.get("message", "")
        workspace_id = request.get("workspace_id") or None
        agent_mode = request.get("agent_mode") or None
        if not message:
            return web_error("No message provided", 400)
        if agent_mode not in {None, "single", "multi"}:
            return web_error("agent_mode must be 'single' or 'multi'", 400)

        try:
            result = runtime.execute_chat_message(
                message, workspace_id=workspace_id, agent_mode=agent_mode
            )
            return result
        except Exception as exc:
            logger.exception("Chat error")
            return web_error(str(exc), 500)


def register_workspace_paper_routes(app: Any, runtime: WebRuntime) -> None:

    @app.get("/api/v1/workspaces")
    async def workspace_list() -> Any:
        """List all workspaces."""
        return application_data(runtime.application.list_workspaces())

    @app.post("/api/v1/workspaces")
    async def workspace_create(request: dict[str, Any]) -> dict[str, Any]:
        """Initialize a new workspace."""
        workspace_id = request.get("id", "")
        if not workspace_id:
            return web_error("No workspace id provided", 400)
        return application_data(
            runtime.application.create_workspace(workspace_id, name=request.get("name"))
        )

    @app.get("/api/v1/workspaces/{workspace_id}")
    async def workspace_get(workspace_id: str) -> dict[str, Any]:
        """Show one workspace by id."""
        return application_data(runtime.application.get_workspace(workspace_id))

    @app.delete("/api/v1/workspaces/{workspace_id}")
    async def workspace_remove(
        workspace_id: str, request: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Delete a workspace after confirmation."""
        return application_data(
            runtime.application.delete_workspace(
                workspace_id, confirm=(request or {}).get("confirm")
            )
        )

    # ---- Paper endpoints --------------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/papers")
    async def paper_list(workspace_id: str) -> Any:
        """List papers in a workspace."""
        return service_data(runtime.service("paper_rag").list_papers(workspace_id))

    @app.post("/api/v1/workspaces/{workspace_id}/papers")
    async def paper_create(
        workspace_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Import a paper into a workspace."""
        source_path = request.get("source_path", "")
        if not source_path:
            return web_error("No source_path provided", 400)
        return service_data(
            runtime.service("paper_rag").import_paper(
                workspace_id,
                source_path,
                metadata=request.get("metadata"),
                enrich=request.get("enrich", False),
                confirm_enrich=request.get("confirm_enrich", False),
            )
        )

    @app.get("/api/v1/workspaces/{workspace_id}/papers/{paper_id}")
    async def paper_get(workspace_id: str, paper_id: str) -> dict[str, Any]:
        """Show one paper by id."""
        return service_data(
            runtime.service("paper_rag").show_paper(workspace_id, paper_id)
        )

    @app.patch("/api/v1/workspaces/{workspace_id}/papers/{paper_id}")
    async def paper_update(
        workspace_id: str, paper_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Edit paper metadata."""
        metadata = request.get("metadata", {})
        return service_data(
            runtime.service("paper_rag").edit_metadata(workspace_id, paper_id, metadata)
        )

    @app.post("/api/v1/workspaces/{workspace_id}/papers/{paper_id}/enrich")
    async def paper_enrich(
        workspace_id: str, paper_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Enrich a paper with LLM-extracted metadata."""
        return service_data(
            runtime.service("paper_rag").enrich_metadata(
                workspace_id,
                paper_id,
                confirm=bool(request.get("confirm_enrich", False)),
            )
        )


def register_experience_tool_routes(app: Any, runtime: WebRuntime) -> None:
    # ---- Experience endpoints ---------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/experiences")
    async def experience_list(workspace_id: str) -> Any:
        """List experiences in a workspace."""
        return service_data(
            runtime.service("experience_evolution").list_experiences(workspace_id)
        )

    @app.post("/api/v1/workspaces/{workspace_id}/experiences")
    async def experience_create(
        workspace_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a new experience."""
        scope = request.get("scope", "")
        title = request.get("title", "")
        summary = request.get("summary", "")
        if not all([scope, title, summary]):
            return web_error("scope, title, and summary are required", 400)
        return service_data(
            runtime.service("experience_evolution").add_experience(
                workspace_id,
                scope,
                title,
                summary,
                tags=request.get("tags"),
                confirm=request.get("confirm", True),
            )
        )

    @app.get("/api/v1/workspaces/{workspace_id}/experiences/{experience_id}")
    async def experience_get(workspace_id: str, experience_id: str) -> dict[str, Any]:
        """View one experience by id."""
        return service_data(
            runtime.service("experience_evolution").view_experience(
                experience_id, workspace_id
            )
        )

    @app.delete("/api/v1/workspaces/{workspace_id}/experiences/{experience_id}")
    async def experience_remove(
        workspace_id: str, experience_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Delete one experience after confirmation."""
        scope = request.get("scope", "")
        if not scope:
            return web_error("scope is required", 400)
        return service_data(
            runtime.service("experience_evolution").delete_experience(
                experience_id, workspace_id, scope, confirm=experience_id
            )
        )

    # ---- Tool endpoints ---------------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/tools")
    async def tool_list(workspace_id: str, language: str | None = None) -> Any:
        """List tools in a workspace."""
        return service_data(
            runtime.service("experiment_tool").list_tools(
                workspace_id, language=language
            )
        )

    @app.post("/api/v1/workspaces/{workspace_id}/tools")
    async def tool_create(workspace_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Add tools to a workspace."""
        return service_data(
            runtime.service("experiment_tool").import_tools(
                workspace_id,
                request.get("selections"),
                language=request.get("language"),
                overwrite=request.get("overwrite", False),
            )
        )

    @app.get("/api/v1/tools/scan")
    async def tool_scan(language: str | None = None) -> Any:
        """Scan for available tools."""
        return service_data(runtime.service("experiment_tool").scan_tools(language))

    # ---- LLM endpoints ---------------------------------------------------


def register_llm_permission_routes(app: Any, runtime: WebRuntime) -> None:

    @app.get("/api/v1/llm/providers")
    async def llm_providers() -> Any:
        """List configured LLM providers."""
        return llm_provider_list_response(
            service_data(runtime.service("llm").list_providers())
        )

    @app.post("/api/v1/llm/providers")
    async def llm_provider_create(request: dict[str, Any]) -> dict[str, Any]:
        """Add or update one LLM provider."""
        provider = request.get("provider") or request.get("name") or ""
        if not provider:
            return web_error("No provider specified", 400)
        values = {
            key: request[key]
            for key in (
                "api_format",
                "base_url",
                "api_key",
                "api_key_env",
                "model",
                "timeout",
                "headers",
            )
            if request.get(key) is not None
        }
        return service_data(
            runtime.service("llm").add_provider(
                provider,
                values,
                set_current=bool(request.get("set_current", False)),
            )
        )

    @app.get("/api/v1/llm/providers/{name}")
    async def llm_provider_get(name: str) -> dict[str, Any]:
        """Show one LLM provider."""
        return service_data(runtime.service("llm").show_provider(name))

    @app.post("/api/v1/llm/switch")
    async def llm_switch(request: dict[str, Any]) -> dict[str, Any]:
        """Switch the active LLM provider."""
        provider = request.get("provider", "")
        if not provider:
            return web_error("No provider specified", 400)
        return service_data(runtime.service("llm").switch_provider(provider))

    # ---- Permission endpoints ---------------------------------------------

    @app.get("/api/v1/permissions")
    async def permission_status() -> dict[str, Any]:
        """Show current permission status."""
        return service_data(
            runtime.service("permission_log_system").permission_status()
        )

    @app.post("/api/v1/permissions/mode")
    async def permission_set_mode(request: dict[str, Any]) -> dict[str, Any]:
        """Set the permission mode."""
        mode = request.get("mode", "")
        if not mode:
            return web_error("No mode specified", 400)
        return service_data(
            runtime.service("permission_log_system").set_permission_mode(
                mode, explicit_confirmation=bool(request.get("confirm_full", False))
            )
        )

    @app.post("/api/v1/permissions/authorize")
    async def permission_authorize(request: dict[str, Any]) -> dict[str, Any]:
        """Authorize an external path."""
        path = request.get("path", "")
        if not path:
            return web_error("No path specified", 400)
        return service_data(
            runtime.service("permission_log_system").authorize_directory(path)
        )

    @app.post("/api/v1/permissions/revoke")
    async def permission_revoke(request: dict[str, Any]) -> dict[str, Any]:
        """Revoke an authorized external path."""
        path = request.get("path", "")
        if not path:
            return web_error("No path specified", 400)
        return service_data(
            runtime.service("permission_log_system").revoke_directory(path)
        )


def register_multi_agent_routes(app: Any, runtime: WebRuntime) -> None:
    @app.get("/api/v1/multi-agent")
    async def multi_agent_status() -> Any:
        return service_data(
            runtime.service("permission_log_system").multi_agent_status()
        )

    @app.post("/api/v1/multi-agent")
    async def multi_agent_set(request: dict[str, Any]) -> Any:
        enabled = request.get("enabled")
        if not isinstance(enabled, bool):
            return web_error("enabled must be a boolean", 400)
        return service_data(
            runtime.service("permission_log_system").set_multi_agent_enabled(enabled)
        )


def register_log_experiment_routes(app: Any, runtime: WebRuntime) -> None:
    # ---- Log endpoints ----------------------------------------------------

    @app.get("/api/v1/logs")
    async def log_list() -> Any:
        """List available logs."""
        return service_data(runtime.service("permission_log_system").list_logs())

    @app.get("/api/v1/logs/{name}")
    async def log_get(name: str) -> dict[str, Any]:
        """Show one log by name."""
        return service_data(runtime.service("permission_log_system").show_log(name))

    @app.post("/api/v1/logs")
    async def log_create(request: dict[str, Any]) -> dict[str, Any]:
        """Write a log entry."""
        message = request.get("message", "")
        if not message:
            return web_error("No message provided", 400)
        return service_data(
            runtime.service("permission_log_system").write_log(
                message, session_id=request.get("session_id")
            )
        )

    # ---- Experiment endpoints ---------------------------------------------

    @app.get("/api/v1/experiments")
    async def experiment_list(session_file: str | None = None) -> Any:
        """List protocols or show one persisted experiment session in full."""
        try:
            if session_file:
                path = experiment_session_path(session_file)
                return service_data(
                    runtime.service("experiment_tool").show_experiment(path)
                )
            return service_data(runtime.service("experiment_tool").list_experiments())
        except ValueError as exc:
            return web_error(str(exc), 400)

    @app.post("/api/v1/experiments")
    async def experiment_create(request: dict[str, Any]) -> dict[str, Any]:
        """Start a new experiment."""
        protocol = request.get("protocol", "")
        if not protocol:
            return web_error("No protocol specified", 400)
        return service_data(
            runtime.service("experiment_tool").start_experiment(
                protocol, session_id=request.get("session_id")
            )
        )

    @app.post("/api/v1/experiments/{session_file}/submit")
    async def experiment_submit(
        session_file: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Submit data for an experiment step."""
        step_id = request.get("step_id", "")
        input_json = request.get("input_json", "")
        if not all([step_id, input_json]):
            return web_error("step_id and input_json are required", 400)
        try:
            path = experiment_session_path(session_file)
        except ValueError as exc:
            return web_error(str(exc), 400)
        return service_data(
            runtime.service("experiment_tool").submit_experiment(
                path,
                step_id,
                input_json,
                calculate=bool(request.get("calculate", False)),
            )
        )


def register_agent_evolution_routes(app: Any, runtime: WebRuntime) -> None:
    # ---- Dialog history endpoints ----------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/dialog-history")
    async def dialog_history_list(workspace_id: str) -> Any:
        """List redacted dialog history summary events for a workspace."""
        return service_data(
            runtime.service("agent_harness").list_dialog_events(workspace_id)
        )

    # ---- Self Evolution endpoints ----------------------------------------

    @app.get("/api/v1/self-evolution")
    async def self_evolution_list() -> Any:
        """List self evolution artifacts."""
        return service_data(
            runtime.service("experience_evolution").list_evolution_artifacts()
        )

    @app.post("/api/v1/self-evolution/generate")
    async def self_evolution_generate(request: dict[str, Any]) -> dict[str, Any]:
        """Generate a self evolution artifact."""
        instruction = request.get("instruction", "")
        artifact_type = request.get("type", "code")
        output = request.get("output", "")
        if not all([instruction, output]):
            return web_error("instruction and output are required", 400)
        return service_data(
            runtime.service("experience_evolution").generate_evolution(
                instruction=instruction,
                artifact_type=artifact_type,
                output=output,
                confirmed=False,
                metadata={"web_endpoint": "self_evolution_generate"},
            )
        )

    @app.get("/api/v1/self-evolution/{artifact_id}")
    async def self_evolution_get(artifact_id: str) -> dict[str, Any]:
        """View one self evolution artifact."""
        return service_data(
            runtime.service("experience_evolution").get_evolution_artifact(artifact_id)
        )

    @app.delete("/api/v1/self-evolution/{artifact_id}")
    async def self_evolution_delete(artifact_id: str) -> dict[str, Any]:
        """Delete one self evolution artifact."""
        return service_data(
            runtime.service("experience_evolution").delete_evolution_artifact(
                artifact_id
            )
        )


def register_diagnostic_routes(app: Any, runtime: WebRuntime) -> None:
    # ---- Diagnose endpoints ----------------------------------------------

    @app.get("/api/v1/diagnose")
    async def diagnose_all() -> Any:
        """Get all diagnostics."""
        return service_data(
            runtime.service("permission_log_system").system_diagnostics()
        )

    @app.get("/api/v1/diagnose/all")
    async def diagnose_all_compat() -> Any:
        """Compatibility alias for full diagnostics."""
        return await diagnose_all()

    @app.get("/api/v1/diagnose/config")
    async def diagnose_config() -> Any:
        """Get config diagnostics."""
        result = runtime.service("permission_log_system").system_diagnostics()
        return result.data.get("config", {}) if result.ok else service_data(result)

    @app.get("/api/v1/diagnose/llm")
    async def diagnose_llm() -> Any:
        """Get LLM diagnostics."""
        result = runtime.service("permission_log_system").system_diagnostics()
        return result.data.get("llm", {}) if result.ok else service_data(result)

    @app.get("/api/v1/diagnose/install")
    async def diagnose_install() -> Any:
        """Get install diagnostics."""
        result = runtime.service("permission_log_system").system_diagnostics()
        if not result.ok:
            return service_data(result)
        return {
            "audit": result.data.get("audit", {}),
            "database": result.data.get("database", {}),
            "log_storage": result.data.get("log_storage", {}),
        }


    @app.post("/api/v1/shutdown")
    async def shutdown() -> Any:
        """Request shutdown only when the embedding server supplied a controller."""
        if runtime.shutdown_callback is None:
            return web_error(
                "Server shutdown is not available in this runtime",
                503,
                code="shutdown_unavailable",
            )
        runtime.shutdown_callback()
        return {"status": "closing", "message": "Server shutdown requested"}


def register_websocket_routes(app: Any, runtime: WebRuntime) -> None:
    # ---- WebSocket chat --------------------------------------------------

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket) -> None:
        """Streaming chat via WebSocket with thinking/reasoning support."""
        await websocket.accept()
        if runtime.auth_token is not None:
            raw_auth = await websocket.receive_text()
            try:
                auth_message = json.loads(raw_auth)
            except json.JSONDecodeError:
                auth_message = {}
            supplied_token = auth_message.get("token", "")
            if auth_message.get("type") != "auth" or not supplied_token:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "authentication_required",
                        "content": "WebSocket authentication is required",
                    }
                )
                await websocket.close(code=1008)
                return
            from core.web.security import verify_token

            if not verify_token(supplied_token, runtime.auth_token):
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "invalid_authentication",
                        "content": "WebSocket authentication failed",
                    }
                )
                await websocket.close(code=1008)
                return
            await websocket.send_json({"type": "auth_ok"})
        logger.info("WebSocket client connected")

        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"message": raw}

                message = data.get("message", "")
                workspace_id = data.get("workspace_id") or None
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
                            websocket.send_json({"type": "progress", "data": info}),
                            loop,
                        )

                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: runtime.execute_chat_message(
                                message,
                                workspace_id=workspace_id,
                                progress_callback=progress_callback,
                            ),
                        )
                        await websocket.send_json({"type": "result", "data": result})
                    except Exception as exc:
                        logger.exception("WebSocket chat error")
                        await websocket.send_json(
                            {"type": "error", "content": str(exc)}
                        )

                await _stream_result()

        except Exception as exc:
            logger.info("WebSocket disconnected: %s", exc)


def register_static_routes(app: Any, runtime: WebRuntime) -> None:
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from core.web.desktop import frontend_directory

    # ---- Static files & index --------------------------------------------

    frontend_dir = frontend_directory()
    if frontend_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/", response_class=HTMLResponse)
        async def index() -> str:
            """Serve the frontend index page."""
            index_file = frontend_dir / "index.html"
            if index_file.exists():
                return index_file.read_text(encoding="utf-8")
            return "<h1>SuperMedicine Web</h1><p>Frontend not found.</p>"
