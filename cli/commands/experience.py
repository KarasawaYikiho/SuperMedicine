"""CLI commands: experience management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from core.redaction import redact_sensitive
from cli.helpers import (
    _as_experience_scope,
    _as_export_format,
    _as_optional_experience_scope,
)
from cli.logging_setup import _log_json

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def experience_suggest(
    cli,
    workspace_id: str,
    summary: str,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Suggest an experience classification without persisting anything."""
    from core.experience import ExperienceStore

    result = (
        ExperienceStore(Path.cwd())
        .suggest_classification(
            workspace_id=workspace_id,
            title=title,
            summary=summary,
            tags=tags,
        )
        .to_dict()
    )
    result["workspace_id"] = workspace_id
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
    """Persist a user-confirmed experience in the chosen scope."""
    from core.experience import ExperienceStore

    if not confirm:
        raise ValueError("experience add requires explicit --confirm")
    experience_scope = _as_experience_scope(scope)
    record = ExperienceStore(Path.cwd()).confirm_classification(
        workspace_id=workspace_id,
        scope=experience_scope,
        title=title,
        summary=summary,
        tags=tags,
    )
    result = record.to_dict()
    _log_json(result)
    return result


def experience_list(
    cli, workspace_id: str, include_general: bool = False
) -> list[dict]:
    """List experiences visible from an explicit workspace context."""
    from core.experience import ExperienceStore

    records = [
        record.to_dict()
        for record in ExperienceStore(Path.cwd()).list_experiences(
            workspace_id,
            include_general=include_general,
        )
    ]
    _log_json(records)
    return records


def experience_view(
    cli, record_id: str, workspace_id: str, scope: str | None = None
) -> dict:
    """View one visible experience by id."""
    from core.experience import ExperienceStore

    experience_scope = _as_optional_experience_scope(scope)
    record = ExperienceStore(Path.cwd()).get_experience(
        record_id,
        workspace_id=workspace_id,
        scope=experience_scope,
    )
    result = record.to_dict()
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
    """Edit one experience in an explicit scope."""
    from core.experience import ExperienceStore

    experience_scope = _as_experience_scope(scope)
    record = ExperienceStore(Path.cwd()).edit_experience(
        record_id,
        workspace_id=workspace_id,
        scope=experience_scope,
        title=title,
        summary=summary,
        tags=tags,
    )
    result = record.to_dict()
    _log_json(result)
    return result


def experience_delete(
    cli, record_id: str, workspace_id: str, scope: str, confirm: str
) -> dict:
    """Delete one experience after exact id confirmation."""
    from core.experience import ExperienceStore

    if confirm != record_id:
        raise ValueError("--confirm must exactly match the experience id")
    experience_scope = _as_experience_scope(scope)
    deleted = ExperienceStore(Path.cwd()).delete_experience(
        record_id,
        workspace_id=workspace_id,
        scope=experience_scope,
    )
    result = {"status": "deleted", "id": deleted.id, "scope": deleted.scope}
    _log_json(result)
    return result


def experience_export(
    cli,
    workspace_id: str,
    format: str,
    include_general: bool = False,
    output: str | None = None,
) -> str:
    """Export visible experiences as JSON or Markdown."""
    from core.experience import ExperienceStore

    export_format = _as_export_format(format)
    rendered = ExperienceStore(Path.cwd()).export_experiences(
        workspace_id=workspace_id,
        format=export_format,
        include_general=include_general,
        path=output,
    )
    logger.info("%s", redact_sensitive(rendered))
    return rendered
