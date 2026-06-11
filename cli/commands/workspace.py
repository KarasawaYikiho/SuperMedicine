"""CLI commands: workspace management."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import yaml

from cli.helpers import _workspace_info_to_dict
from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def workspace_init(cli, workspace_id: str, name: str | None = None) -> dict:
    """Initialize an explicitly named workspace."""
    from core.workspace import WorkspaceManager

    info = WorkspaceManager(Path.cwd()).initialize_workspace(workspace_id)
    if name is not None:
        metadata_path = info.path / "workspace.yaml"
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        metadata["display_name"] = name
        metadata_path.write_text(
            yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        info = WorkspaceManager(Path.cwd()).get_workspace(workspace_id)
    result = _workspace_info_to_dict(info, name=name)
    _log_json(result)
    return result


def workspace_list(cli) -> list[dict]:
    """List initialized workspaces without consulting recent TUI state."""
    from core.workspace import WorkspaceManager

    workspaces = [
        _workspace_info_to_dict(info)
        for info in WorkspaceManager(Path.cwd()).list_workspaces()
    ]
    _log_json(workspaces)
    return workspaces


def workspace_show(cli, workspace_id: str) -> dict:
    """Show one explicitly requested workspace."""
    from core.workspace import WorkspaceManager

    info = WorkspaceManager(Path.cwd()).get_workspace(workspace_id)
    result = _workspace_info_to_dict(info)
    _log_json(result)
    return result


def workspace_delete(cli, workspace_id: str, confirm: str) -> dict:
    """Hard-delete an explicitly confirmed workspace after guard approval."""
    from core.operation_guard import authorize_dangerous_operation
    from core.path_safety import validate_destructive_path
    from core.workspace import WorkspaceManager, validate_workspace_id
    from permission.audit import AuditLogger
    from permission.engine import PermissionEngine
    from permission.policy import ensure_default_policy

    project_dir = Path.cwd()
    manager = WorkspaceManager(project_dir)
    slug = validate_workspace_id(workspace_id)
    workspace_path = manager.workspace_path(slug)
    audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
    audit_logger = AuditLogger(audit_log)

    if confirm != slug:
        audit_logger.log(
            agent_id="delta",
            action="workspace.delete",
            resource=str(workspace_path),
            result="cancelled",
            reason="confirmation_mismatch",
        )
        raise ValueError("--confirm must exactly match --workspace for deletion")

    manager.get_workspace(slug)
    safe_path = validate_destructive_path(workspace_path, project_dir)

    policies_dir = project_dir / ".supermedicine" / "policies"
    try:
        ensure_default_policy(project_dir)
    except FileNotFoundError:
        audit_logger.log(
            agent_id="delta",
            action="workspace.delete",
            resource=str(safe_path),
            result="cancelled",
            reason="missing_default_policy",
        )
        raise

    permission_engine = PermissionEngine(policies_dir, audit_log)
    authorization = authorize_dangerous_operation(
        permission_engine=permission_engine,
        agent_id="delta",
        action="workspace.delete",
        path=safe_path,
        project_root=project_dir,
        context={"workspace_id": slug},
        destructive=True,
        audit_logger=audit_logger,
        operation="workspace_delete",
    )

    if authorization.path.is_dir():
        shutil.rmtree(authorization.path)
    else:
        authorization.path.unlink()

    result = {"status": "deleted", "id": slug, "path": str(authorization.path)}
    _log_json(result)
    return result
