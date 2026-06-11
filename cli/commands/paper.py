"""CLI commands: paper import and management."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.helpers import (
    _paper_import_result_to_dict,
    _paper_metadata_to_dict,
)
from cli.logging_setup import _log_json

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
    from core.paper_import.enrichment import PaperEnricher
    from core.paper_import.importer import PaperImporter
    from permission.audit import AuditLogger
    from permission.engine import PermissionEngine
    from permission.policy import ensure_default_policy

    project_dir = Path.cwd()
    importer = PaperImporter(project_dir)
    import_result = importer.import_file(workspace_id, source_path, metadata or {})
    warnings = list(import_result.warnings)

    if enrich:
        audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
        ensure_default_policy(project_dir)
        enricher = PaperEnricher(
            PermissionEngine(
                project_dir / ".supermedicine" / "policies", audit_log
            ),
            AuditLogger(audit_log),
        )
        enrichment_result = enricher.enrich(
            import_result.metadata, confirmed=confirm_enrich
        )
        if enrichment_result.status == "enriched":
            importer.save_paper_metadata(workspace_id, enrichment_result.metadata)
        if enrichment_result.warning:
            warnings.append(enrichment_result.warning)

    result = _paper_import_result_to_dict(import_result, warnings=warnings)
    _log_json(result)
    return result


def paper_list(cli, workspace_id: str) -> list[dict]:
    """List papers from an explicitly selected workspace."""
    from core.paper_import.importer import PaperImporter

    papers = [
        _paper_metadata_to_dict(paper)
        for paper in PaperImporter(Path.cwd()).list_papers(workspace_id)
    ]
    _log_json(papers)
    return papers


def paper_show(cli, workspace_id: str, paper_id: str) -> dict:
    """Show one imported paper from an explicitly selected workspace."""
    from core.paper_import.importer import PaperImporter

    result = _paper_metadata_to_dict(
        PaperImporter(Path.cwd()).get_paper(workspace_id, paper_id)
    )
    _log_json(result)
    return result


def paper_edit(cli, workspace_id: str, paper_id: str, metadata: dict) -> dict:
    """Edit metadata for one imported paper from an explicit workspace."""
    from core.paper_import.importer import PaperImporter

    result = _paper_metadata_to_dict(
        PaperImporter(Path.cwd()).update_paper_metadata(
            workspace_id, paper_id, metadata
        )
    )
    _log_json(result)
    return result


def paper_enrich(
    cli, workspace_id: str, paper_id: str, confirm_enrich: bool
) -> dict:
    """Enrich one imported paper after explicit confirmation and permission approval."""
    from core.paper_import.enrichment import PaperEnricher
    from core.paper_import.importer import PaperImporter
    from permission.audit import AuditLogger
    from permission.engine import PermissionEngine
    from permission.policy import ensure_default_policy

    project_dir = Path.cwd()
    importer = PaperImporter(project_dir)
    metadata = importer.get_paper(workspace_id, paper_id)
    audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
    ensure_default_policy(project_dir)
    enrichment_result = PaperEnricher(
        PermissionEngine(project_dir / ".supermedicine" / "policies", audit_log),
        AuditLogger(audit_log),
    ).enrich(metadata, confirmed=confirm_enrich)
    if enrichment_result.status == "enriched":
        importer.save_paper_metadata(workspace_id, enrichment_result.metadata)
    result = {
        "status": enrichment_result.status,
        "warning": enrichment_result.warning,
        "applied_fields": enrichment_result.applied_fields,
        "metadata": _paper_metadata_to_dict(enrichment_result.metadata),
    }
    _log_json(result)
    return result
