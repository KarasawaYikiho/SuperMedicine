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
from typing import Any, Iterable

from core.services import LLMService, PaperRAGService, ServiceResult, WorkspaceService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app factory – lazy imports so the rest of the project never
# hard-requires fastapi/uvicorn.
# ---------------------------------------------------------------------------


def _ensure_fastapi() -> None:
    """fastapi/uvicorn 未安装时抛出清晰错误。"""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "网页 GUI 需要 'fastapi' 和 'uvicorn'。"
            "请使用以下命令安装：pip install supermedicine[web]"
        ) from exc


def create_app() -> Any:
    """Create and return the FastAPI application."""
    _ensure_fastapi()

    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(
        title="SuperMedicine Web API",
        version="0.4.2",
        description="SuperMedicine 医学研究智能体的浏览器/桌面 GUI 接口",
    )

    # ---- state -----------------------------------------------------------
    _kernel_holder: dict[str, Any] = {}

    def _web_error(message: str, status_code: int) -> Any:
        """Preserve the public error payload while using HTTP error semantics."""
        return JSONResponse(
            status_code=status_code,
            content={"error": message, "status": "error"},
        )

    def _service_data(result: ServiceResult[Any]) -> Any:
        """Return legacy data on success and stable HTTP semantics on failure."""
        if result.ok:
            return result.data
        error = result.error
        code = error.code if error else "service_error"
        status_code = {
            "invalid_workspace_id": 400,
            "confirmation_mismatch": 400,
            "workspace_exists": 409,
            "workspace_not_found": 404,
            "permission_denied": 403,
            "required_file_missing": 500,
            "missing_provider": 400,
            "provider_not_found": 404,
            "missing_base_url": 422,
            "missing_api_key": 422,
            "missing_model": 422,
            "incomplete_provider_config": 422,
            "paper_source_missing": 404,
            "paper_not_found": 404,
            "unsupported_paper_format": 422,
        }.get(code, 500)
        return _web_error(error.message if error else "Service failed", status_code)

    def _llm_provider_list_response(result: Any) -> Any:
        """Expose the provider collection as the list consumed by the Web UI."""
        if not isinstance(result, dict):
            return result
        current = str(result.get("current_provider") or "")
        raw_providers = result.get("providers", {})
        provider_items: Iterable[tuple[str, Any]]
        if isinstance(raw_providers, dict):
            provider_items = raw_providers.items()
        elif isinstance(raw_providers, list):
            provider_items = (
                (str(item.get("provider") or item.get("name") or ""), item)
                for item in raw_providers
                if isinstance(item, dict)
            )
        else:
            provider_items = ()
        providers: list[dict[str, Any]] = []
        for name, values in provider_items:
            if not isinstance(values, dict):
                continue
            provider = dict(values)
            provider_name = str(provider.get("provider") or name)
            provider["provider"] = provider_name
            provider["current"] = provider_name == current
            providers.append(provider)
        return {**result, "providers": providers}

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

    def _workspace_context(workspace_id: str | None) -> dict[str, Any] | None:
        """Validate a selected workspace and build the shared execution context."""
        if not workspace_id:
            return None
        service = WorkspaceService(Path.cwd())
        workspace = service.require_data(service.show(workspace_id))
        return {
            "id": workspace["id"],
            "path": workspace["path"],
            "metadata": workspace["metadata"],
        }

    def _experiment_session_path(session_file: str) -> Path:
        """Resolve a Web-selected experiment only inside managed storage."""
        storage = (Path.cwd() / ".supermedicine" / "experiments").resolve()
        requested = Path(session_file)
        candidate = (
            requested.resolve()
            if requested.is_absolute()
            else (Path.cwd() / requested).resolve()
        )
        try:
            candidate.relative_to(storage)
        except ValueError as exc:
            raise ValueError("Experiment session file is outside managed storage") from exc
        if candidate.suffix.lower() != ".json":
            raise ValueError("Experiment session file must be JSON")
        return candidate

    def _execute_chat_message(
        message: str,
        *,
        workspace_id: str | None = None,
        agent_mode: str | None = None,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """Execute chat with the selected workspace synchronized into runtime state."""
        kernel = _get_kernel()
        workspace_context = _workspace_context(workspace_id)
        params: dict[str, Any] | None = None
        if workspace_context is not None:
            workspace_id = str(workspace_context["id"])
            params = {"_workspace": workspace_context}
            kernel._config.set_runtime_state_value(
                "last_workspace_id", workspace_id, save=True
            )
        else:
            kernel._config.set_runtime_state_value("last_workspace_id", "", save=True)
        result = kernel.execute_task(
            message,
            params=params,
            progress_callback=progress_callback,
            use_agent_chain=None if agent_mode is None else agent_mode == "multi",
        )
        if workspace_context is not None:
            metadata = result.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata.setdefault("workspace", workspace_context)
                metadata.setdefault("workspace_id", workspace_id)
        return result

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
            "required_runtime": _get_kernel().runtime_capabilities.to_dict(),
        }
        runtime = status["required_runtime"]
        status["ok"] = bool(runtime["harness"]["healthy"]) and bool(
            runtime["rag"]["healthy"]
        )

        # Include LLM provider info if config is available
        if config_dir.exists():
            try:
                provider_result = LLMService(project_dir).show_provider()
                provider = provider_result.data or {} if provider_result.ok else {}
                status["llm_provider"] = provider.get("provider", "未知") if provider else "未配置"
            except Exception:
                status["llm_provider"] = "读取配置失败"

        return status

    @app.post("/api/v1/chat")
    async def chat(request: dict[str, Any]) -> dict[str, Any]:
        """Send a message to the Kernel and return the response."""
        message = request.get("message", "")
        workspace_id = request.get("workspace_id") or None
        agent_mode = request.get("agent_mode") or None
        if not message:
            return _web_error("No message provided", 400)
        if agent_mode not in {None, "single", "multi"}:
            return _web_error("agent_mode must be 'single' or 'multi'", 400)

        try:
            result = _execute_chat_message(
                message, workspace_id=workspace_id, agent_mode=agent_mode
            )
            return result
        except Exception as exc:
            logger.exception("Chat error")
            return _web_error(str(exc), 500)

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
        return _service_data(WorkspaceService(Path.cwd()).list())

    @app.post("/api/v1/workspaces")
    async def workspace_create(request: dict[str, Any]) -> dict[str, Any]:
        """Initialize a new workspace."""
        workspace_id = request.get("id", "")
        if not workspace_id:
            return _web_error("No workspace id provided", 400)
        return _service_data(
            WorkspaceService(Path.cwd()).create(
                workspace_id, name=request.get("name"), fail_if_exists=True
            )
        )

    @app.get("/api/v1/workspaces/{workspace_id}")
    async def workspace_get(workspace_id: str) -> dict[str, Any]:
        """Show one workspace by id."""
        return _service_data(WorkspaceService(Path.cwd()).show(workspace_id))

    @app.delete("/api/v1/workspaces/{workspace_id}")
    async def workspace_remove(workspace_id: str) -> dict[str, Any]:
        """Delete a workspace after confirmation."""
        return _service_data(
            WorkspaceService(Path.cwd()).delete(workspace_id, confirm=workspace_id)
        )

    # ---- Paper endpoints --------------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/papers")
    async def paper_list(workspace_id: str) -> Any:
        """List papers in a workspace."""
        return _service_data(PaperRAGService(Path.cwd()).list_papers(workspace_id))

    @app.post("/api/v1/workspaces/{workspace_id}/papers")
    async def paper_create(workspace_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Import a paper into a workspace."""
        source_path = request.get("source_path", "")
        if not source_path:
            return _web_error("No source_path provided", 400)
        return _service_data(
            PaperRAGService(Path.cwd()).import_paper(
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
        return _service_data(
            PaperRAGService(Path.cwd()).show_paper(workspace_id, paper_id)
        )

    @app.patch("/api/v1/workspaces/{workspace_id}/papers/{paper_id}")
    async def paper_update(workspace_id: str, paper_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Edit paper metadata."""
        metadata = request.get("metadata", {})
        return _service_data(
            PaperRAGService(Path.cwd()).edit_metadata(
                workspace_id, paper_id, metadata
            )
        )

    @app.post("/api/v1/workspaces/{workspace_id}/papers/{paper_id}/enrich")
    async def paper_enrich(workspace_id: str, paper_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Enrich a paper with LLM-extracted metadata."""
        return _service_data(
            PaperRAGService(Path.cwd()).enrich_metadata(
                workspace_id,
                paper_id,
                confirm=bool(request.get("confirm_enrich", False)),
            )
        )

    # ---- Experience endpoints ---------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/experiences")
    async def experience_list(workspace_id: str) -> Any:
        """List experiences in a workspace."""
        try:
            return _get_cli().experience_list(workspace_id)
        except Exception as exc:
            logger.exception("experience_list error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/workspaces/{workspace_id}/experiences")
    async def experience_create(workspace_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Add a new experience."""
        scope = request.get("scope", "")
        title = request.get("title", "")
        summary = request.get("summary", "")
        if not all([scope, title, summary]):
            return _web_error("scope, title, and summary are required", 400)
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
            return _web_error(str(exc), 500)

    @app.get("/api/v1/workspaces/{workspace_id}/experiences/{experience_id}")
    async def experience_get(workspace_id: str, experience_id: str) -> dict[str, Any]:
        """View one experience by id."""
        try:
            return _get_cli().experience_view(experience_id, workspace_id)
        except Exception as exc:
            logger.exception("experience_get error")
            return _web_error(str(exc), 500)

    @app.delete("/api/v1/workspaces/{workspace_id}/experiences/{experience_id}")
    async def experience_remove(workspace_id: str, experience_id: str, request: dict[str, Any]) -> dict[str, Any]:
        """Delete one experience after confirmation."""
        scope = request.get("scope", "")
        if not scope:
            return _web_error("scope is required", 400)
        try:
            return _get_cli().experience_delete(
                experience_id, workspace_id, scope, confirm=experience_id
            )
        except Exception as exc:
            logger.exception("experience_remove error")
            return _web_error(str(exc), 500)

    # ---- Tool endpoints ---------------------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/tools")
    async def tool_list(workspace_id: str, language: str | None = None) -> Any:
        """List tools in a workspace."""
        try:
            return _get_cli().tool_list(workspace_id, language=language)
        except Exception as exc:
            logger.exception("tool_list error")
            return _web_error(str(exc), 500)

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
            return _web_error(str(exc), 500)

    @app.get("/api/v1/tools/scan")
    async def tool_scan(language: str | None = None) -> Any:
        """Scan for available tools."""
        try:
            return _get_cli().tool_scan(language=language)
        except Exception as exc:
            logger.exception("tool_scan error")
            return _web_error(str(exc), 500)

    # ---- LLM endpoints ---------------------------------------------------

    @app.get("/api/v1/llm/providers")
    async def llm_providers() -> Any:
        """List configured LLM providers."""
        return _llm_provider_list_response(
            _service_data(LLMService(Path.cwd()).list_providers())
        )

    @app.post("/api/v1/llm/providers")
    async def llm_provider_create(request: dict[str, Any]) -> dict[str, Any]:
        """Add or update one LLM provider."""
        provider = request.get("provider") or request.get("name") or ""
        if not provider:
            return _web_error("No provider specified", 400)
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
        return _service_data(
            LLMService(Path.cwd()).add_provider(
                provider,
                values,
                set_current=bool(request.get("set_current", False)),
            )
        )

    @app.get("/api/v1/llm/providers/{name}")
    async def llm_provider_get(name: str) -> dict[str, Any]:
        """Show one LLM provider."""
        return _service_data(LLMService(Path.cwd()).show_provider(name))

    @app.post("/api/v1/llm/switch")
    async def llm_switch(request: dict[str, Any]) -> dict[str, Any]:
        """Switch the active LLM provider."""
        provider = request.get("provider", "")
        if not provider:
            return _web_error("No provider specified", 400)
        return _service_data(LLMService(Path.cwd()).switch_provider(provider))

    # ---- Permission endpoints ---------------------------------------------

    @app.get("/api/v1/permissions")
    async def permission_status() -> dict[str, Any]:
        """Show current permission status."""
        try:
            return _get_cli().permission_status()
        except Exception as exc:
            logger.exception("permission_status error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/permissions/mode")
    async def permission_set_mode(request: dict[str, Any]) -> dict[str, Any]:
        """Set the permission mode."""
        mode = request.get("mode", "")
        if not mode:
            return _web_error("No mode specified", 400)
        try:
            return _get_cli().permission_set_mode(
                mode,
                confirm_full=request.get("confirm_full", False),
                interactive=False,
            )
        except Exception as exc:
            logger.exception("permission_set_mode error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/permissions/authorize")
    async def permission_authorize(request: dict[str, Any]) -> dict[str, Any]:
        """Authorize an external path."""
        path = request.get("path", "")
        if not path:
            return _web_error("No path specified", 400)
        try:
            return _get_cli().permission_authorize(path)
        except Exception as exc:
            logger.exception("permission_authorize error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/permissions/revoke")
    async def permission_revoke(request: dict[str, Any]) -> dict[str, Any]:
        """Revoke an authorized external path."""
        path = request.get("path", "")
        if not path:
            return _web_error("No path specified", 400)
        try:
            return _get_cli().permission_revoke(path)
        except Exception as exc:
            logger.exception("permission_revoke error")
            return _web_error(str(exc), 500)

    # ---- Log endpoints ----------------------------------------------------

    @app.get("/api/v1/logs")
    async def log_list() -> Any:
        """List available logs."""
        try:
            return _get_cli().log_list()
        except Exception as exc:
            logger.exception("log_list error")
            return _web_error(str(exc), 500)

    @app.get("/api/v1/logs/{name}")
    async def log_get(name: str) -> dict[str, Any]:
        """Show one log by name."""
        try:
            return _get_cli().log_show(name)
        except Exception as exc:
            logger.exception("log_get error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/logs")
    async def log_create(request: dict[str, Any]) -> dict[str, Any]:
        """Write a log entry."""
        message = request.get("message", "")
        if not message:
            return _web_error("No message provided", 400)
        try:
            return _get_cli().log_write(message, session_id=request.get("session_id"))
        except Exception as exc:
            logger.exception("log_create error")
            return _web_error(str(exc), 500)

    # ---- Experiment endpoints ---------------------------------------------

    @app.get("/api/v1/experiments")
    async def experiment_list(session_file: str | None = None) -> Any:
        """List protocols or show one persisted experiment session in full."""
        try:
            if session_file:
                path = _experiment_session_path(session_file)
                return _get_cli().experiment_show(path)
            return _get_cli().experiment_list()
        except ValueError as exc:
            return _web_error(str(exc), 400)
        except Exception as exc:
            logger.exception("experiment_list error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/experiments")
    async def experiment_create(request: dict[str, Any]) -> dict[str, Any]:
        """Start a new experiment."""
        protocol = request.get("protocol", "")
        if not protocol:
            return _web_error("No protocol specified", 400)
        try:
            return _get_cli().experiment_start(protocol, session_id=request.get("session_id"))
        except Exception as exc:
            logger.exception("experiment_create error")
            return _web_error(str(exc), 500)

    @app.post("/api/v1/experiments/{session_file}/submit")
    async def experiment_submit(session_file: str, request: dict[str, Any]) -> dict[str, Any]:
        """Submit data for an experiment step."""
        step_id = request.get("step_id", "")
        input_json = request.get("input_json", "")
        if not all([step_id, input_json]):
            return _web_error("step_id and input_json are required", 400)
        try:
            return _get_cli().experiment_submit(
                session_file, step_id, input_json, calculate=request.get("calculate", False)
            )
        except Exception as exc:
            logger.exception("experiment_submit error")
            return _web_error(str(exc), 500)

    # ---- Dialog history endpoints ----------------------------------------

    @app.get("/api/v1/workspaces/{workspace_id}/dialog-history")
    async def dialog_history_list(workspace_id: str) -> Any:
        """List redacted dialog history summary events for a workspace."""
        try:
            from core.tui.dialog_history import DialogHistoryStore

            events = DialogHistoryStore(project_root=Path.cwd()).load_events(workspace_id)
            return [event.to_dict() for event in events]
        except Exception as exc:
            logger.exception("dialog_history_list error")
            return _web_error(str(exc), 500)

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
            return _web_error(str(exc), 500)

    @app.post("/api/v1/self-evolution/generate")
    async def self_evolution_generate(request: dict[str, Any]) -> dict[str, Any]:
        """Generate a self evolution artifact."""
        instruction = request.get("instruction", "")
        artifact_type = request.get("type", "code")
        output = request.get("output", "")
        if not all([instruction, output]):
            return _web_error("instruction and output are required", 400)
        try:
            return _get_cli().self_evolve(
                instruction=instruction,
                artifact_type=artifact_type,
                output=output,
                preview=True,
            )
        except Exception as exc:
            logger.exception("self_evolution_generate error")
            return _web_error(str(exc), 500)

    @app.get("/api/v1/self-evolution/{artifact_id}")
    async def self_evolution_get(artifact_id: str) -> dict[str, Any]:
        """View one self evolution artifact."""
        try:
            from pathlib import Path as _P
            project_dir = _P.cwd()
            artifact_path = project_dir / "self_evolution" / f"{artifact_id}.json"
            if not artifact_path.exists():
                return _web_error("Artifact not found", 404)
            import json as _json
            return _json.loads(artifact_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.exception("self_evolution_get error")
            return _web_error(str(exc), 500)

    @app.delete("/api/v1/self-evolution/{artifact_id}")
    async def self_evolution_delete(artifact_id: str) -> dict[str, Any]:
        """Delete one self evolution artifact."""
        try:
            from pathlib import Path as _P
            project_dir = _P.cwd()
            artifact_path = project_dir / "self_evolution" / f"{artifact_id}.json"
            if not artifact_path.exists():
                return _web_error("Artifact not found", 404)
            artifact_path.unlink()
            return {"success": True, "message": f"Artifact {artifact_id} deleted"}
        except Exception as exc:
            logger.exception("self_evolution_delete error")
            return _web_error(str(exc), 500)

    # ---- Diagnose endpoints ----------------------------------------------

    @app.get("/api/v1/diagnose")
    async def diagnose_all() -> dict[str, Any]:
        """Get all diagnostics."""
        try:
            return _get_cli().diagnose()
        except Exception as exc:
            logger.exception("diagnose_all error")
            return _web_error(str(exc), 500)

    @app.get("/api/v1/diagnose/all")
    async def diagnose_all_compat() -> dict[str, Any]:
        """Compatibility alias for full diagnostics."""
        return await diagnose_all()

    @app.get("/api/v1/diagnose/config")
    async def diagnose_config() -> dict[str, Any]:
        """Get config diagnostics."""
        try:
            result = _get_cli().diagnose()
            return result.get("config", {})
        except Exception as exc:
            logger.exception("diagnose_config error")
            return _web_error(str(exc), 500)

    @app.get("/api/v1/diagnose/llm")
    async def diagnose_llm() -> dict[str, Any]:
        """Get LLM diagnostics."""
        try:
            result = _get_cli().diagnose()
            return result.get("llm", {})
        except Exception as exc:
            logger.exception("diagnose_llm error")
            return _web_error(str(exc), 500)

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
            return _web_error(str(exc), 500)

    @app.post("/api/v1/shutdown")
    async def shutdown() -> dict[str, Any]:
        """Acknowledge GUI close requests without forcing server termination."""
        return {"status": "closing", "message": "GUI close requested"}

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
                            websocket.send_json(
                                {"type": "progress", "data": info}
                            ),
                            loop,
                        )

                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: _execute_chat_message(
                                message,
                                workspace_id=workspace_id,
                                progress_callback=progress_callback,
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


def create_server_app():
    """Create and return the FastAPI application for embedded use."""
    return create_app()


def find_available_port(host: str = "127.0.0.1") -> int:
    """Find an available port for the web server."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]
