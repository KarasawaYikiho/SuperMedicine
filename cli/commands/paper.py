"""CLI commands: paper import and management."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.logging_setup import _log_json
from core.services import PaperRAGService

logger = logging.getLogger(__name__)


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
