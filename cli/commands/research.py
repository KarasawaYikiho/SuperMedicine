"""CLI commands for workspace, paper, and experience research flows."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.logging_setup import _log_json
from core.redaction import redact_sensitive
from core.services import ExperienceEvolutionService, PaperRAGService

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


def paper_import(
    cli,
    workspace_id: str,
    source_path: str | Path,
    metadata: dict | None = None,
    enrich: bool = False,
    confirm_enrich: bool = False,
) -> dict:
    """Import a local paper into an explicitly selected workspace."""
    service = PaperRAGService(Path.cwd())
    result = service.require_data(
        service.import_paper(
            workspace_id,
            source_path,
            metadata,
            enrich=enrich,
            confirm_enrich=confirm_enrich,
        )
    )
    _log_json(result)
    return result


def paper_list(cli, workspace_id: str) -> list[dict]:
    """List papers from an explicitly selected workspace."""
    service = PaperRAGService(Path.cwd())
    papers = service.require_data(service.list_papers(workspace_id))
    _log_json(papers)
    return papers


def paper_show(cli, workspace_id: str, paper_id: str) -> dict:
    """Show one imported paper from an explicitly selected workspace."""
    service = PaperRAGService(Path.cwd())
    result = service.require_data(service.show_paper(workspace_id, paper_id))
    _log_json(result)
    return result


def paper_edit(cli, workspace_id: str, paper_id: str, metadata: dict) -> dict:
    """Edit metadata for one imported paper from an explicit workspace."""
    service = PaperRAGService(Path.cwd())
    result = service.require_data(
        service.edit_metadata(workspace_id, paper_id, metadata)
    )
    _log_json(result)
    return result


def paper_enrich(
    cli, workspace_id: str, paper_id: str, confirm_enrich: bool
) -> dict:
    """Enrich one imported paper after explicit confirmation and permission approval."""
    service = PaperRAGService(Path.cwd())
    result = service.require_data(
        service.enrich_metadata(
            workspace_id, paper_id, confirm=confirm_enrich
        )
    )
    _log_json(result)
    return result


def _service() -> ExperienceEvolutionService:
    return ExperienceEvolutionService(Path.cwd())


def experience_suggest(
    cli,
    workspace_id: str,
    summary: str,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    service = _service()
    result = service.require_data(
        service.suggest_experience(
            workspace_id, summary, title=title, tags=tags
        )
    )
    _log_json(result)
    return result


def experience_add(
    cli,
    workspace_id: str,
    scope: str,
    title: str,
    summary: str,
    tags: list[str] | None = None,
    confirm: bool = False,
) -> dict:
    service = _service()
    result = service.require_data(
        service.add_experience(
            workspace_id, scope, title, summary, tags=tags, confirm=confirm
        )
    )
    _log_json(result)
    return result


def experience_list(
    cli, workspace_id: str, include_general: bool = False
) -> list[dict]:
    service = _service()
    result = service.require_data(
        service.list_experiences(workspace_id, include_general=include_general)
    )
    _log_json(result)
    return result


def experience_view(
    cli, record_id: str, workspace_id: str, scope: str | None = None
) -> dict:
    service = _service()
    result = service.require_data(
        service.view_experience(record_id, workspace_id, scope)
    )
    _log_json(result)
    return result


def experience_edit(
    cli,
    record_id: str,
    workspace_id: str,
    scope: str,
    title: str | None = None,
    summary: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    service = _service()
    result = service.require_data(
        service.edit_experience(
            record_id,
            workspace_id,
            scope,
            title=title,
            summary=summary,
            tags=tags,
        )
    )
    _log_json(result)
    return result


def experience_delete(
    cli, record_id: str, workspace_id: str, scope: str, confirm: str
) -> dict:
    service = _service()
    result = service.require_data(
        service.delete_experience(
            record_id, workspace_id, scope, confirm=confirm
        )
    )
    _log_json(result)
    return result


def experience_export(
    cli,
    workspace_id: str,
    format: str,
    include_general: bool = False,
    output: str | None = None,
) -> str:
    service = _service()
    rendered = service.require_data(
        service.export_experiences(
            workspace_id,
            format,
            include_general=include_general,
            path=output,
        )
    )
    logger.info("%s", redact_sensitive(rendered))
    return rendered
