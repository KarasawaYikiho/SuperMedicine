"""CLI commands: workspace management."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.logging_setup import _log_json
from core.services import WorkspaceService

logger = logging.getLogger(__name__)


def workspace_init(cli, workspace_id: str, name: str | None = None) -> dict:
    """Initialize an explicitly named workspace."""
    service = WorkspaceService(Path.cwd())
    result = service.require_data(service.create(workspace_id, name=name))
    _log_json(result)
    return result


def workspace_list(cli) -> list[dict]:
    """List initialized workspaces without consulting recent TUI state."""
    service = WorkspaceService(Path.cwd())
    workspaces = service.require_data(service.list())
    _log_json(workspaces)
    return workspaces


def workspace_show(cli, workspace_id: str) -> dict:
    """Show one explicitly requested workspace."""
    service = WorkspaceService(Path.cwd())
    result = service.require_data(service.show(workspace_id))
    _log_json(result)
    return result


def workspace_delete(cli, workspace_id: str, confirm: str) -> dict:
    """Hard-delete an explicitly confirmed workspace after guard approval."""
    service = WorkspaceService(Path.cwd())
    result = service.require_data(service.delete(workspace_id, confirm=confirm))
    _log_json(result)
    return result
