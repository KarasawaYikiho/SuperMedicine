"""CLI commands: permission management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cli.helpers import (
    _confirm_full_access_interactively,
    _permission_result,
)
from cli.logging_setup import _log_json
from core.services import PermissionLogSystemService

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
