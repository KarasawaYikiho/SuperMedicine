"""CLI commands: experience management."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.logging_setup import _log_json
from core.redaction import redact_sensitive
from core.services import ExperienceEvolutionService

logger = logging.getLogger(__name__)


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
