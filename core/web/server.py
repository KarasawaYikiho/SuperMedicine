"""SuperMedicine Web API server with domain-based route registration."""

from __future__ import annotations

import logging
from typing import Any

from core.services import (
    AgentHarnessService,
    ExperimentToolService,
    ExperienceEvolutionService,
    LLMService,
    PaperRAGService,
    PermissionLogSystemService,
    WorkspaceService,
)

logger = logging.getLogger(__name__)


def _ensure_fastapi() -> None:
    """fastapi/uvicorn ???????????"""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "?? GUI ?? 'fastapi' ? 'uvicorn'???????????pip install supermedicine[web]"
        ) from exc


def create_app() -> Any:
    """Create the FastAPI application and register domain route adapters."""
    _ensure_fastapi()
    from fastapi import FastAPI

    from core.web.routes import (
        register_agent_evolution_routes,
        register_diagnostic_routes,
        register_experience_tool_routes,
        register_llm_permission_routes,
        register_log_experiment_routes,
        register_multi_agent_routes,
        register_static_routes,
        register_status_routes,
        register_websocket_routes,
        register_workspace_paper_routes,
    )
    from core.web.runtime import WebRuntime

    app = FastAPI(
        title="SuperMedicine Web API",
        version="0.4.2",
        description="SuperMedicine ???????????/?? GUI ??",
    )
    runtime = WebRuntime(
        {
            "agent_harness": AgentHarnessService,
            "experiment_tool": ExperimentToolService,
            "experience_evolution": ExperienceEvolutionService,
            "llm": LLMService,
            "paper_rag": PaperRAGService,
            "permission_log_system": PermissionLogSystemService,
            "workspace": WorkspaceService,
        }
    )
    registrars = (
        register_status_routes,
        register_workspace_paper_routes,
        register_experience_tool_routes,
        register_llm_permission_routes,
        register_log_experiment_routes,
        register_multi_agent_routes,
        register_agent_evolution_routes,
        register_diagnostic_routes,
        register_websocket_routes,
        register_static_routes,
    )
    for register in registrars:
        register(app, runtime)
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
