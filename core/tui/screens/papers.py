"""Chinese TUI paper import screen/controller foundations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.paper_import.enrichment import PaperEnricher
from core.paper_import.enrichment import PAPER_ENRICH_ACTION, PAPER_ENRICH_AGENT_ID
from core.paper_import.importer import PaperImporter
from core.paper_import.models import PaperImportResult, PaperMetadata
from permission.audit import AuditLogger
from permission.engine import PermissionEngine


@dataclass(slots=True)
class PaperScreenController:
    """Controller for paper import/list/show/edit/enrich TUI actions."""

    project_root: Path | str | None = None

    @property
    def importer(self) -> PaperImporter:
        if self.project_root is None:
            return PaperImporter()
        return PaperImporter(self.project_root)

    @property
    def root(self) -> Path:
        return self.importer.project_root

    def import_paper(
        self,
        workspace_id: str,
        source_path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Copy-only import into the explicit workspace."""

        result = self.importer.import_file(workspace_id, source_path, metadata or {})
        return self._import_payload(result, message="论文已复制导入工作区")

    def list_papers(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self._metadata_payload(paper) for paper in self.importer.list_papers(workspace_id)]

    def show_paper(self, workspace_id: str, paper_id: str) -> dict[str, Any]:
        return self._metadata_payload(self.importer.get_paper(workspace_id, paper_id), message="论文详情")

    def edit_metadata(self, workspace_id: str, paper_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Edit only importer-supported metadata fields."""

        updated = self.importer.update_paper_metadata(workspace_id, paper_id, metadata)
        return self._metadata_payload(updated, message="论文元数据已更新")

    def enrich_metadata(self, workspace_id: str, paper_id: str, *, confirm: bool) -> dict[str, Any]:
        """Run explicit enrichment confirmation flow; never performs silent online enrichment."""

        importer = self.importer
        metadata = importer.get_paper(workspace_id, paper_id)
        audit_log = self.root / ".supermedicine" / "policies" / "audit.jsonl"
        if not confirm:
            AuditLogger(audit_log).log(
                agent_id=PAPER_ENRICH_AGENT_ID,
                action=PAPER_ENRICH_ACTION,
                resource=f"tui://paper/{paper_id}",
                result="skipped",
                reason="missing_explicit_tui_confirmation",
            )
            return {
                "status": "skipped",
                "message": "论文在线补全未执行",
                "warning": "enrichment skipped: TUI confirmation is required",
                "applied_fields": [],
                "metadata": self._metadata_payload(metadata),
            }
        result = PaperEnricher(
            PermissionEngine(self.root / ".supermedicine" / "policies", audit_log),
            AuditLogger(audit_log),
        ).enrich(metadata, confirmed=confirm)
        if result.status == "enriched":
            importer.save_paper_metadata(workspace_id, result.metadata)
        return {
            "status": result.status,
            "message": "论文在线补全已完成" if result.status == "enriched" else "论文在线补全未执行",
            "warning": result.warning,
            "applied_fields": result.applied_fields,
            "metadata": self._metadata_payload(result.metadata),
        }

    def _import_payload(self, result: PaperImportResult, *, message: str) -> dict[str, Any]:
        return {
            "message": message,
            "metadata": self._metadata_payload(result.metadata),
            "source_path": str(result.source_path) if result.source_path else None,
            "duplicate": result.duplicate,
            "duplicate_reason": result.duplicate_reason,
            "warnings": list(result.warnings),
        }

    def _metadata_payload(self, metadata: PaperMetadata, message: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": metadata.id,
            "label": f"论文：{metadata.title or metadata.id or '未命名'}",
            "sha256": metadata.sha256,
            "stored_path": str(metadata.stored_path) if metadata.stored_path else None,
            "format": metadata.format,
            "imported_at": metadata.imported_at.isoformat() if metadata.imported_at else None,
            "updated_at": metadata.updated_at.isoformat() if metadata.updated_at else None,
            "title": metadata.title,
            "authors": list(metadata.authors),
            "doi": metadata.doi,
            "pmid": metadata.pmid,
            "notes": metadata.notes,
            "tags": list(metadata.tags),
        }
        if message is not None:
            payload["message"] = message
        return payload
