"""CLI commands: workspace tool management."""

from __future__ import annotations

import logging
from pathlib import Path
from cli.logging_setup import _log_json
from core.services import ExperimentToolService

logger = logging.getLogger(__name__)


def tool_init(cli, workspace_id: str) -> dict:
    """Initialize workspace-local Python/R tool directories."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(service.initialize_tools(workspace_id))
    _log_json(result)
    return result


def tool_list(cli, workspace_id: str, language: str | None = None) -> dict:
    """List workspace-local tools grouped by language."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.list_tools(workspace_id, language=language)
    )
    _log_json(result)
    return result


def tool_scan(cli, language: str | None = None) -> dict:
    """Scan Python/R source tool directories for selectable import candidates."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(service.scan_tools(language))
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
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.import_tools(
            workspace_id,
            selections,
            language=language,
            overwrite=overwrite,
        )
    )
    _log_json(result)
    return result


def tool_show(cli, workspace_id: str, language: str, tool_id: str) -> dict:
    """Show one workspace-local tool manifest."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.show_tool(workspace_id, language, tool_id)
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
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.prepare_tool(
            workspace_id,
            language,
            tool_id,
            dry_run=dry_run,
            input_path=input_path,
            output_path=output_path,
        )
    )
    _log_json(result)
    return result
