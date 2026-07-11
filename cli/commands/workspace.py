"""CLI commands: workspace management."""

from __future__ import annotations

import logging
from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def workspace_init(cli, workspace_id: str, name: str | None = None) -> dict:
    """Initialize an explicitly named workspace."""
    result = _unwrap(cli.application.create_workspace(workspace_id, name=name))
    _log_json(result)
    return result


def workspace_list(cli) -> list[dict]:
    """List initialized workspaces without consulting recent TUI state."""
    workspaces = _unwrap(cli.application.list_workspaces())
    _log_json(workspaces)
    return workspaces


def workspace_show(cli, workspace_id: str) -> dict:
    """Show one explicitly requested workspace."""
    result = _unwrap(cli.application.get_workspace(workspace_id))
    _log_json(result)
    return result


def workspace_delete(cli, workspace_id: str, confirm: str) -> dict:
    """Hard-delete an explicitly confirmed workspace after guard approval."""
    result = _unwrap(cli.application.delete_workspace(workspace_id, confirm=confirm))
    _log_json(result)
    return result


def _unwrap(result):
    if result.ok:
        return result.data
    error = result.error
    assert error is not None
    if error.code == "permission_denied":
        raise PermissionError(error.message)
    if error.code in {"validation_error", "not_found"}:
        raise ValueError(error.message)
    raise RuntimeError(error.message)
