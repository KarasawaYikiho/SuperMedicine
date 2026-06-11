"""CLI commands: workspace tool management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def tool_init(cli, workspace_id: str) -> dict:
    """Initialize workspace-local Python/R tool directories."""
    from core.workspace_tools import WorkspaceToolService

    result = WorkspaceToolService(Path.cwd()).initialize_tools(workspace_id)
    _log_json(result)
    return result


def tool_list(cli, workspace_id: str, language: str | None = None) -> dict:
    """List workspace-local tools grouped by language."""
    from core.workspace_tools import WorkspaceToolService

    result = WorkspaceToolService(Path.cwd()).list_tools(
        workspace_id, language=language
    )
    _log_json(result)
    return result


def tool_scan(cli, language: str | None = None) -> dict:
    """Scan Python/R source tool directories for selectable import candidates."""
    from core.workspace_tools import WorkspaceToolService

    result = WorkspaceToolService(Path.cwd()).scan_import_candidates(language)
    _log_json(result)
    return result


def tool_add(
    cli,
    workspace_id: str,
    selections: list[str] | None = None,
    *,
    language: str | None = None,
    overwrite: bool = False,
) -> dict:
    """Import scanned Python/R tools selected from the candidate list."""
    from core.workspace_tools import WorkspaceToolService

    service = WorkspaceToolService(Path.cwd())
    if not selections:
        result = {
            "status": "select_required",
            "message": "Select tools from this scanned list with --select; no tool ID knowledge is required.",
            "candidates": service.scan_import_candidates(language),
        }
    else:
        result = service.import_scanned_tools(
            workspace_id, selections, language=language, overwrite=overwrite
        )
        imported_raw: object = result.get("imported")
        imported_items: list[dict[str, Any]] = (
            [
                cast(dict[str, Any], item)
                for item in imported_raw
                if isinstance(item, dict)
            ]
            if isinstance(imported_raw, list)
            else []
        )
        if imported_items:
            from core.config_center import ConfigCenter

            config = ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml")
            config.set_runtime_state_value("last_workspace_id", workspace_id)
            config.record_tool_import_state(
                workspace_id=workspace_id,
                imported=imported_items,
                save=True,
            )
    _log_json(result)
    return result


def tool_show(cli, workspace_id: str, language: str, tool_id: str) -> dict:
    """Show one workspace-local tool manifest."""
    from core.workspace_tools import WorkspaceToolService

    result = WorkspaceToolService(Path.cwd()).show_tool(
        workspace_id, language, tool_id
    )
    _log_json(result)
    return result


def tool_run(
    cli,
    workspace_id: str,
    language: str,
    tool_id: str,
    *,
    dry_run: bool = False,
    input_path: str | None = None,
    output_path: str | None = None,
) -> dict:
    """Prepare a guarded workspace-local tool invocation without unsafe execution."""
    from core.workspace_tools import WorkspaceToolService

    result = (
        WorkspaceToolService(Path.cwd())
        .prepare_invocation(
            workspace_id,
            language,
            tool_id,
            dry_run=dry_run,
            input_path=input_path,
            output_path=output_path,
        )
        .to_dict()
    )
    _log_json(result)
    return result
