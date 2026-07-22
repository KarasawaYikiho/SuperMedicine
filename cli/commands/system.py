"""CLI commands for permission and self-evolution system flows."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cli.helpers import (
    _confirm_full_access_interactively,
    _permission_result,
    _self_evolution_cli_result,
)
from cli.logging_setup import _log_json
from core.services import ExperienceEvolutionService, PermissionLogSystemService

logger = logging.getLogger(__name__)


def permission_status(cli) -> dict[str, Any]:
    """Show current CLI file access mode and authorized external roots."""
    service = PermissionLogSystemService(Path.cwd())
    file_access = service.require_data(service.permission_status())
    result = _permission_result(file_access, changed=False)
    result["config_load_error"] = file_access.get("config_load_error", "")
    _log_json(result)
    return result


def permission_set_mode(
    cli,
    mode: str,
    *,
    confirm_full: bool = False,
    interactive: bool = True,
) -> dict[str, Any]:
    """Persistently switch CLI file access mode without privilege escalation."""
    from permission.access_mode import AccessMode, normalize_access_mode

    normalized = normalize_access_mode(mode)
    explicit_confirmation = confirm_full
    if normalized == AccessMode.FULL and not explicit_confirmation and interactive:
        explicit_confirmation = _confirm_full_access_interactively()
    service = PermissionLogSystemService(Path.cwd())
    file_access = service.require_data(
        service.set_permission_mode(
            normalized.value, explicit_confirmation=explicit_confirmation
        )
    )
    result = _permission_result(
        file_access,
        changed=True,
        message="权限模式已切换；后续策略读取会立即使用新的配置。",
    )
    _log_json(result)
    return result


def permission_authorize(cli, path: str | Path) -> dict[str, Any]:
    """Persistently authorize an external directory for conservative mode."""
    service = PermissionLogSystemService(Path.cwd())
    file_access = service.require_data(service.authorize_directory(path))
    result = _permission_result(
        file_access,
        changed=True,
        message="外部授权目录已添加；后续策略读取会立即使用新的配置。",
    )
    _log_json(result)
    return result


def permission_revoke(cli, path: str | Path) -> dict[str, Any]:
    """Persistently remove an external directory authorization."""
    service = PermissionLogSystemService(Path.cwd())
    file_access = service.require_data(service.revoke_directory(path))
    result = _permission_result(
        file_access,
        changed=True,
        message="外部授权目录已移除；后续策略读取会立即使用新的配置。",
    )
    _log_json(result)
    return result


def multi_agent_status(cli) -> dict[str, Any]:
    """Show whether the optional full four-role pipeline is enabled."""
    service = PermissionLogSystemService(Path.cwd())
    result = service.require_data(service.multi_agent_status())
    _log_json(result)
    return result


def self_evolve(
    cli,
    *,
    instruction: str,
    artifact_type: str,
    output: str | Path,
    access_mode: str = "sandbox",
    experience_source: str | None = None,
    workspace: str | None = None,
    preview: bool = True,
    confirm_write: bool = False,
    overwrite: bool = False,
    confirm_full_access: bool = False,
    acknowledge_risk: bool = False,
) -> dict[str, Any]:
    """Generate a self-evolution preview or confirmed artifact write."""
    project_dir = Path.cwd()
    confirmed = bool(confirm_write and not preview)
    audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"

    service = ExperienceEvolutionService(project_dir)
    result = service.require_data(service.generate_evolution(
        instruction=instruction,
        artifact_type=artifact_type,
        output=output,
        access_mode=access_mode,
        experience_source=experience_source,
        workspace_id=workspace,
        confirmed=confirmed,
        overwrite=overwrite,
        confirm_full_access=confirm_full_access,
        acknowledge_risk=acknowledge_risk,
        metadata={"cli_command": "self-evolve"},
    ))
    cli_result = _self_evolution_cli_result(
        result,
        requested_access_mode=access_mode,
        requested_output=output,
        audit_log=audit_log,
        preview=not confirmed,
        confirm_write=confirm_write,
        confirm_full_access=confirm_full_access,
        acknowledge_risk=acknowledge_risk,
    )
    _log_json(cli_result)
    return cli_result


def multi_agent_set(cli, enabled: bool) -> dict[str, Any]:
    """Persistently switch the optional full four-role pipeline."""
    service = PermissionLogSystemService(Path.cwd())
    result = service.require_data(service.set_multi_agent_enabled(enabled))
    result["message"] = (
        "Multi-Agent 完整四角色流程已启用。"
        if enabled
        else "Multi-Agent 已关闭；后续任务使用轻量单流程。"
    )
    _log_json(result)
    return result
