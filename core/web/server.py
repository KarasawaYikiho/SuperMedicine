"""SuperMedicine Web API server with domain-based route registration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

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


def _install_web_security(app: Any, auth_token: str | None) -> None:
    """Install shared errors, request IDs, path validation, and remote auth."""
    from urllib.parse import unquote

    from core.web.errors import APIError, api_error_response, install_api_error_handlers

    install_api_error_handlers(app)

    @app.middleware("http")
    async def authenticate_remote_api(request: Any, call_next: Any) -> Any:
        request_id = str(uuid4())
        request.state.request_id = request_id
        raw_path = request.scope.get("raw_path", b"")
        encoded_path = (
            raw_path.decode("ascii", errors="ignore")
            if isinstance(raw_path, bytes)
            else str(raw_path)
        )
        artifact_prefix = "/api/v1/self-evolution/"
        if encoded_path.startswith(artifact_prefix):
            from core.web.security import validate_artifact_id

            artifact_id = unquote(encoded_path[len(artifact_prefix) :])
            try:
                validate_artifact_id(artifact_id)
            except APIError as exc:
                return api_error_response(exc, request_id=request_id)
        api_path = request.url.path == "/api/v1" or request.url.path.startswith(
            "/api/v1/"
        )
        if auth_token is not None and api_path:
            from core.web.security import verify_bearer_header

            authorization = request.headers.get("authorization")
            if not authorization:
                return api_error_response(
                    APIError(
                        401,
                        "authentication_required",
                        "Bearer authentication is required",
                        headers={"WWW-Authenticate": "Bearer"},
                    ),
                    request_id=request_id,
                )
            if not verify_bearer_header(authorization, auth_token):
                return api_error_response(
                    APIError(
                        403,
                        "invalid_authentication",
                        "Bearer authentication failed",
                    ),
                    request_id=request_id,
                )
        response = await call_next(request)
        response.headers.setdefault("X-Request-ID", request_id)
        return response


def create_app(*, auth_token: str | None = None) -> Any:
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
    _install_web_security(app, auth_token)

    runtime = WebRuntime(
        {
            "agent_harness": AgentHarnessService,
            "experiment_tool": ExperimentToolService,
            "experience_evolution": ExperienceEvolutionService,
            "llm": LLMService,
            "paper_rag": PaperRAGService,
            "permission_log_system": PermissionLogSystemService,
            "workspace": WorkspaceService,
        },
        auth_token=auth_token,
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
    auth_token_file: str | Path | None = None,
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

    from core.web.security import load_remote_auth_token

    auth_token = load_remote_auth_token(host, auth_token_file)
    if auth_token is not None and reload:
        raise ValueError("--reload cannot be combined with authenticated Web startup")

    logger.info("Starting SuperMedicine Web server on %s:%s", host, port)
    if auth_token is None:
        uvicorn.run(
            "core.web.server:create_app",
            host=host,
            port=port,
            reload=reload,
            factory=True,
        )
    else:
        uvicorn.run(create_app(auth_token=auth_token), host=host, port=port)


def create_server_app():
    """Create and return the FastAPI application for embedded use."""
    return create_app()


def find_available_port(host: str = "127.0.0.1") -> int:
    """Find an available port for the web server."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]
