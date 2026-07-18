"""Paper and local-RAG application service shared by every interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.paper_import.enrichment import PaperEnricher, PaperEnrichmentResult
from core.paper_import.errors import (
    MissingPaperSourceError,
    PaperImportError,
    UnsupportedPaperFormatError,
)
from core.paper_import.importer import PaperImporter
from core.paper_import.models import PaperImportResult, PaperMetadata
from core.redaction import redact_sensitive
from core.services.result import ServiceResult
from core.workspace import InvalidWorkspaceId, WorkspaceError, WorkspaceNotFoundError
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from permission.policy import ensure_default_policy


class PaperRAGService:
    """Own paper import, metadata, and permission-gated enrichment use cases."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.importer = PaperImporter(project_root)
        self.project_root = self.importer.project_root

    def import_paper(
        self,
        workspace_id: str,
        source_path: str | Path,
        metadata: dict[str, Any] | None = None,
        *,
        enrich: bool = False,
        confirm_enrich: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        operation = "import_paper"

        def action() -> dict[str, Any]:
            imported = self.importer.import_file(
                workspace_id, source_path, metadata or {}
            )
            warnings = list(imported.warnings)
            if enrich:
                enrichment = self._enrich(imported.metadata, confirm_enrich)
                if enrichment.status == "enriched":
                    self.importer.save_paper_metadata(
                        workspace_id, enrichment.metadata
                    )
                if enrichment.warning:
                    warnings.append(enrichment.warning)
            return self.import_payload(imported, warnings=warnings)

        return self._call(operation, request_id, action, workspace_id=workspace_id)

    def list_papers(
        self, workspace_id: str, *, request_id: str | None = None
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._call(
            "list_papers",
            request_id,
            lambda: [
                self.metadata_payload(paper)
                for paper in self.importer.list_papers(workspace_id)
            ],
            workspace_id=workspace_id,
        )

    def show_paper(
        self,
        workspace_id: str,
        paper_id: str,
        *,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "show_paper",
            request_id,
            lambda: self.metadata_payload(
                self.importer.get_paper(workspace_id, paper_id)
            ),
            workspace_id=workspace_id,
            paper_id=paper_id,
        )

    def edit_metadata(
        self,
        workspace_id: str,
        paper_id: str,
        metadata: dict[str, Any],
        *,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "edit_metadata",
            request_id,
            lambda: self.metadata_payload(
                self.importer.update_paper_metadata(
                    workspace_id, paper_id, metadata
                )
            ),
            workspace_id=workspace_id,
            paper_id=paper_id,
        )

    def enrich_metadata(
        self,
        workspace_id: str,
        paper_id: str,
        *,
        confirm: bool,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        operation = "enrich_metadata"

        def action() -> dict[str, Any]:
            metadata = self.importer.get_paper(workspace_id, paper_id)
            enrichment = self._enrich(metadata, confirm)
            if enrichment.status == "enriched":
                self.importer.save_paper_metadata(
                    workspace_id, enrichment.metadata
                )
            return self.enrichment_payload(enrichment)

        return self._call(
            operation,
            request_id,
            action,
            workspace_id=workspace_id,
            paper_id=paper_id,
        )

    def _enrich(
        self, metadata: PaperMetadata, confirmed: bool
    ) -> PaperEnrichmentResult:
        ensure_default_policy(self.project_root)
        audit_log = (
            self.project_root / ".supermedicine" / "policies" / "audit.jsonl"
        )
        return PaperEnricher(
            PermissionEngine(
                self.project_root / ".supermedicine" / "policies", audit_log
            ),
            AuditLogger(audit_log),
        ).enrich(metadata, confirmed=confirmed)

    def _call(
        self,
        operation: str,
        request_id: str | None,
        action: Callable[[], Any],
        **details: str,
    ) -> ServiceResult[Any]:
        try:
            return ServiceResult.success(
                action(), request_id=request_id, meta=self._meta(operation)
            )
        except (
            PaperImportError,
            InvalidWorkspaceId,
            WorkspaceError,
            OSError,
        ) as exc:
            return self._expected_failure(
                exc, operation, request_id, details
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                str(redact_sensitive(str(exc))) or "Paper service failed",
                request_id=request_id,
                details=details,
                meta=self._meta(operation),
            )

    def _expected_failure(
        self,
        exc: Exception,
        operation: str,
        request_id: str | None,
        details: dict[str, str],
    ) -> ServiceResult[Any]:
        if isinstance(exc, WorkspaceNotFoundError):
            code = "workspace_not_found"
        elif isinstance(exc, UnsupportedPaperFormatError):
            code = "unsupported_paper_format"
        elif isinstance(exc, MissingPaperSourceError):
            code = (
                "paper_not_found"
                if operation in {"show_paper", "edit_metadata", "enrich_metadata"}
                else "paper_source_missing"
            )
        elif isinstance(exc, InvalidWorkspaceId):
            code = "invalid_workspace_id"
        else:
            code = "paper_error"
        return ServiceResult.failure(
            code,
            str(exc),
            request_id=request_id,
            details=details,
            meta=self._meta(operation),
        )

    @staticmethod
    def require_data(result: ServiceResult[Any]) -> Any:
        """Restore legacy exception behavior at compatibility interfaces."""
        if result.ok:
            return result.data
        error = result.error
        code = error.code if error else "paper_error"
        message = error.message if error else "Paper service failed"
        if code == "workspace_not_found":
            raise WorkspaceNotFoundError(message)
        if code == "unsupported_paper_format":
            raise UnsupportedPaperFormatError(message)
        if code in {"paper_source_missing", "paper_not_found"}:
            raise MissingPaperSourceError(message)
        raise ValueError(message)

    @staticmethod
    def import_payload(
        imported: PaperImportResult, *, warnings: list[str] | None = None
    ) -> dict[str, Any]:
        return {
            "metadata": PaperRAGService.metadata_payload(imported.metadata),
            "source_path": str(imported.source_path) if imported.source_path else None,
            "warnings": warnings if warnings is not None else list(imported.warnings),
            "duplicate": imported.duplicate,
            "duplicate_reason": imported.duplicate_reason,
        }

    @staticmethod
    def enrichment_payload(enrichment: PaperEnrichmentResult) -> dict[str, Any]:
        return {
            "status": enrichment.status,
            "warning": enrichment.warning,
            "applied_fields": list(enrichment.applied_fields),
            "metadata": PaperRAGService.metadata_payload(enrichment.metadata),
        }

    @staticmethod
    def metadata_payload(metadata: PaperMetadata) -> dict[str, Any]:
        return {
            "id": metadata.id,
            "sha256": metadata.sha256,
            "stored_path": str(metadata.stored_path) if metadata.stored_path else None,
            "format": metadata.format,
            "imported_at": metadata.imported_at.isoformat()
            if metadata.imported_at
            else None,
            "updated_at": metadata.updated_at.isoformat()
            if metadata.updated_at
            else None,
            "title": metadata.title,
            "authors": list(metadata.authors),
            "doi": metadata.doi,
            "pmid": metadata.pmid,
            "notes": metadata.notes,
            "tags": list(metadata.tags),
        }

    @staticmethod
    def _meta(operation: str) -> dict[str, str]:
        return {"service": "paper_rag", "operation": operation}
