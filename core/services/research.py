"""Workspace, paper/RAG, and experience research application services."""

from __future__ import annotations

import json
from hashlib import sha256
from functools import partial
from pathlib import Path
from typing import Any, Callable, cast

import yaml

from core.experience import (
    ExperienceError,
    ExperienceScope,
    ExperienceStore,
    ExportFormat,
)
from core.config_center import resolve_config_path
from core.operation_guard import authorize_dangerous_operation
from core.paper_import.contracts import (
    MissingPaperSourceError,
    PaperImportError,
    PaperImportResult,
    PaperMetadata,
    UnsupportedPaperFormatError,
)
from core.paper_import.enrichment import PaperEnricher, PaperEnrichmentResult
from core.paper_import.importer import PaperImporter
from core.paper_import.online import OnlinePaperClient, OnlinePaperError
from core.path_safety import validate_destructive_path
from core.self_evolution import ARTIFACT_TYPE_WHITELIST, SelfEvolutionService
from core.time_utils import utc_now
from core.workspace import (
    InvalidWorkspaceId,
    WorkspaceError,
    WorkspaceInfo,
    WorkspaceManager,
    WorkspaceNotFoundError,
    validate_workspace_id,
)
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from permission.policy import ensure_default_policy, ensure_default_policy_in

from . import result as _result
from .result import ServiceResult


class WorkspaceService:
    """Own workspace use cases, including guarded destructive deletion."""

    require_data = staticmethod(
        partial(
            _result._require_data,
            "Workspace service failed",
            {
                "permission_denied": PermissionError,
                "required_file_missing": FileNotFoundError,
                "workspace_not_found": WorkspaceNotFoundError,
            },
        )
    )
    _meta = staticmethod(partial(_result._service_meta, "workspace"))

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        config_path: str | Path | None = None,
    ) -> None:
        self.manager = WorkspaceManager(project_root)
        self.project_root = self.manager.project_root
        self.config_path = (
            Path(config_path)
            if config_path
            else resolve_config_path(self.project_root)
        )
        self.state_root = self.config_path.parent

    def create(
        self,
        workspace_id: str,
        *,
        name: str | None = None,
        fail_if_exists: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        try:
            slug = validate_workspace_id(workspace_id)
            if fail_if_exists:
                try:
                    self.manager.get_workspace(slug)
                except WorkspaceNotFoundError:
                    pass
                else:
                    return ServiceResult.failure(
                        "workspace_exists",
                        f"Workspace already exists: {slug}",
                        request_id=request_id,
                        details={"workspace_id": slug},
                        meta=self._meta("create"),
                    )
            info = self.manager.initialize_workspace_atomic(slug, name=name)
            return ServiceResult.success(
                self._workspace_data(info, name=name),
                request_id=request_id,
                meta=self._meta("create"),
            )
        except (InvalidWorkspaceId, WorkspaceError, OSError, yaml.YAMLError) as exc:
            return self._exception_result(exc, "create", request_id)
        except Exception as exc:
            return self._unexpected_result(exc, "create", request_id)

    def list(
        self, *, request_id: str | None = None
    ) -> ServiceResult[list[dict[str, Any]]]:
        try:
            data = [
                self._workspace_data(info) for info in self.manager.list_workspaces()
            ]
            return ServiceResult.success(
                data, request_id=request_id, meta=self._meta("list")
            )
        except (WorkspaceError, OSError, yaml.YAMLError) as exc:
            return self._exception_result(exc, "list", request_id)
        except Exception as exc:
            return self._unexpected_result(exc, "list", request_id)

    def show(
        self, workspace_id: str, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        try:
            info = self.manager.get_workspace(workspace_id)
            return ServiceResult.success(
                self._workspace_data(info),
                request_id=request_id,
                meta=self._meta("show"),
            )
        except (InvalidWorkspaceId, WorkspaceError, OSError, yaml.YAMLError) as exc:
            return self._exception_result(exc, "show", request_id)
        except Exception as exc:
            return self._unexpected_result(exc, "show", request_id)

    def save_selection(
        self,
        workspace_id: str,
        selected_workspace_id: str | None = None,
        *,
        request_id: str | None = None,
    ) -> ServiceResult[str]:
        try:
            path = self.manager.save_recent_selection(
                workspace_id, selected_workspace_id
            )
            return ServiceResult.success(
                str(path), request_id=request_id, meta=self._meta("save_selection")
            )
        except (InvalidWorkspaceId, WorkspaceError, OSError, yaml.YAMLError) as exc:
            return self._exception_result(exc, "save_selection", request_id)
        except Exception as exc:
            return self._unexpected_result(exc, "save_selection", request_id)

    def load_selection(
        self, workspace_id: str, *, request_id: str | None = None
    ) -> ServiceResult[str | None]:
        try:
            selected = self.manager.load_recent_selection(workspace_id)
            return ServiceResult.success(
                selected, request_id=request_id, meta=self._meta("load_selection")
            )
        except (InvalidWorkspaceId, WorkspaceError, OSError, yaml.YAMLError) as exc:
            return self._exception_result(exc, "load_selection", request_id)
        except Exception as exc:
            return self._unexpected_result(exc, "load_selection", request_id)

    def delete(
        self,
        workspace_id: str,
        *,
        confirm: str,
        agent_id: str = "delta",
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        operation = "delete"
        try:
            slug = validate_workspace_id(workspace_id)
            workspace_path = self.manager.workspace_path(slug)
            policies_dir = self.state_root / "policies"
            audit_path = policies_dir / "audit.jsonl"
            audit_logger = AuditLogger(audit_path)
            if confirm != slug:
                audit_logger.log(
                    agent_id=agent_id,
                    action="workspace.delete",
                    resource=str(workspace_path),
                    result="cancelled",
                    reason="confirmation_mismatch",
                )
                return ServiceResult.failure(
                    "confirmation_mismatch",
                    "--confirm must exactly match --workspace for deletion",
                    request_id=request_id,
                    details={"workspace_id": slug},
                    meta=self._meta(operation),
                )

            self.manager.get_workspace(slug)
            safe_path = validate_destructive_path(workspace_path, self.project_root)
            ensure_default_policy_in(policies_dir)
            authorization = authorize_dangerous_operation(
                permission_engine=PermissionEngine(policies_dir, audit_path),
                agent_id=agent_id,
                action="workspace.delete",
                path=safe_path,
                project_root=self.project_root,
                context={"workspace_id": slug},
                destructive=True,
                audit_logger=audit_logger,
                operation="workspace_delete",
            )
            self.manager.delete_workspace_atomic(authorization.path)
            return ServiceResult.success(
                {
                    "status": "deleted",
                    "id": slug,
                    "path": str(authorization.path),
                },
                request_id=request_id,
                meta=self._meta(operation),
            )
        except PermissionError as exc:
            return ServiceResult.failure(
                "permission_denied",
                str(exc),
                request_id=request_id,
                meta=self._meta(operation),
            )
        except FileNotFoundError as exc:
            return ServiceResult.failure(
                "required_file_missing",
                str(exc),
                request_id=request_id,
                meta=self._meta(operation),
            )
        except (InvalidWorkspaceId, WorkspaceError, OSError, yaml.YAMLError) as exc:
            return self._exception_result(exc, operation, request_id)
        except Exception as exc:
            return self._unexpected_result(exc, operation, request_id)

    def _exception_result(
        self, exc: Exception, operation: str, request_id: str | None
    ) -> ServiceResult[Any]:
        if isinstance(exc, InvalidWorkspaceId):
            code = "invalid_workspace_id"
        elif isinstance(exc, WorkspaceNotFoundError):
            code = "workspace_not_found"
        else:
            code = "workspace_error"
        return ServiceResult.failure(
            code,
            str(exc),
            request_id=request_id,
            meta=self._meta(operation),
        )

    def _unexpected_result(
        self, exc: Exception, operation: str, request_id: str | None
    ) -> ServiceResult[Any]:
        return ServiceResult.failure(
            "internal_error",
            _result._safe_internal_message(exc, "Workspace service failed"),
            request_id=request_id,
            meta=self._meta(operation),
        )

    @staticmethod
    def _workspace_data(
        info: WorkspaceInfo, *, name: str | None = None
    ) -> dict[str, Any]:
        metadata = info.metadata.to_dict()
        metadata_path = info.path / "workspace.yaml"
        if metadata_path.is_file():
            raw = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict) and raw.get("display_name") is not None:
                metadata["display_name"] = str(raw["display_name"])
        data: dict[str, Any] = {
            "id": info.id,
            "path": str(info.path),
            "metadata": metadata,
        }
        display_name = name if name is not None else metadata.get("display_name")
        if display_name is not None:
            data["name"] = display_name
        return data


class PaperRAGService:
    """Own paper import, metadata, and permission-gated enrichment use cases."""

    require_data = staticmethod(
        partial(
            _result._require_data,
            "Paper service failed",
            {
                "workspace_not_found": WorkspaceNotFoundError,
                "unsupported_paper_format": UnsupportedPaperFormatError,
                "paper_source_missing": MissingPaperSourceError,
                "paper_not_found": MissingPaperSourceError,
            },
        )
    )
    _meta = staticmethod(partial(_result._service_meta, "paper_rag"))

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        online_client: OnlinePaperClient | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        self.importer = PaperImporter(project_root)
        self.project_root = self.importer.project_root
        self.config_path = (
            Path(config_path)
            if config_path
            else resolve_config_path(self.project_root)
        )
        self.online_client = online_client or OnlinePaperClient()

    def search_online(
        self,
        query: str,
        *,
        source: str = "pubmed",
        limit: int = 10,
        request_id: str | None = None,
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._call(
            "search_online",
            request_id,
            lambda: [
                record.to_dict()
                for record in self.online_client.search(
                    query, source=source, limit=limit
                )
            ],
            source=source,
        )

    def import_online(
        self,
        workspace_id: str,
        source: str,
        external_id: str,
        *,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            record = self.online_client.get(source, external_id)
            cache = self.config_path.parent / "paper-import-cache"
            cache.mkdir(parents=True, exist_ok=True)
            cache_key = sha256(
                f"{record.source}\0{record.external_id}".encode("utf-8")
            ).hexdigest()
            source_path = cache / f"{record.source}-{cache_key}.md"
            temporary_path = source_path.with_suffix(".tmp")
            content = "\n".join(
                    [
                        f"# {record.title}",
                        "",
                        f"- 来源：{record.source}",
                        f"- 标识：{record.external_id}",
                        f"- 作者：{', '.join(record.authors)}",
                        f"- 期刊：{record.journal}",
                        f"- 发表时间：{record.published}",
                        f"- DOI：{record.doi or ''}",
                        f"- PMID：{record.pmid or ''}",
                        f"- 链接：{record.url}",
                        "",
                        "## 摘要",
                        "",
                        record.abstract or "该数据源未提供摘要。",
                        "",
                    ]
                )
            try:
                temporary_path.write_text(content, encoding="utf-8")
                temporary_path.replace(source_path)
                imported = self.importer.import_file(
                    workspace_id,
                    source_path,
                    {
                        "title": record.title,
                        "authors": list(record.authors),
                        "doi": record.doi,
                        "pmid": record.pmid,
                        "notes": (
                            f"从 {record.source} 在线检索并导入；"
                            f"原始链接：{record.url}"
                        ),
                        "tags": ["online-import", record.source],
                    },
                )
            except Exception:
                temporary_path.unlink(missing_ok=True)
                source_path.unlink(missing_ok=True)
                raise
            return {
                **self.import_payload(imported),
                "online_source": record.to_dict(),
            }

        return self._call(
            "import_online",
            request_id,
            action,
            workspace_id=workspace_id,
            source=source,
        )

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

    def delete_paper(
        self,
        workspace_id: str,
        paper_id: str,
        *,
        confirm: str,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        if confirm != paper_id:
            return ServiceResult.failure(
                "confirmation_mismatch",
                "confirm must exactly match the paper id",
                request_id=request_id,
                meta=self._meta("delete_paper"),
            )
        return self._call(
            "delete_paper",
            request_id,
            lambda: self.importer.delete_paper(workspace_id, paper_id),
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
            OnlinePaperError,
            InvalidWorkspaceId,
            WorkspaceError,
            ValueError,
            OSError,
        ) as exc:
            return self._expected_failure(
                exc, operation, request_id, details
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                _result._safe_internal_message(exc, "Paper service failed"),
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
                if operation
                in {"show_paper", "edit_metadata", "enrich_metadata", "delete_paper"}
                else "paper_source_missing"
            )
        elif isinstance(exc, InvalidWorkspaceId):
            code = "invalid_workspace_id"
        elif isinstance(exc, OnlinePaperError):
            code = "online_paper_unavailable"
        elif isinstance(exc, ValueError):
            code = "invalid_paper_request"
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


class ExperienceEvolutionService:
    """Own confirmed experience CRUD and guarded self-evolution generation."""

    require_data = staticmethod(
        partial(_result._require_data, "Experience service failed", {})
    )
    _meta = staticmethod(partial(_result._service_meta, "experience_evolution"))

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        config_path: str | Path | None = None,
    ) -> None:
        self.store = ExperienceStore(project_root)
        self.project_root = self.store.project_root
        self.config_path = (
            Path(config_path)
            if config_path
            else resolve_config_path(self.project_root)
        )
        self.state_root = self.config_path.parent
        self.evolution = SelfEvolutionService(self.project_root)

    def suggest_experience(
        self,
        workspace_id: str,
        summary: str,
        *,
        title: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "suggest_experience",
            lambda: {
                **self.store.suggest_classification(
                    workspace_id=workspace_id,
                    title=title,
                    summary=summary,
                    tags=tags,
                    metadata=metadata,
                ).to_dict(),
                "workspace_id": workspace_id,
            },
        )

    def add_experience(
        self,
        workspace_id: str,
        scope: str,
        title: str,
        summary: str,
        *,
        tags: list[str] | None = None,
        confirm: bool,
        source: dict[str, Any] | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        if not confirm:
            return ServiceResult.failure(
                "confirmation_required",
                "experience add requires explicit confirmation",
                meta=self._meta("add_experience"),
            )
        return self._call(
            "add_experience",
            lambda: self.store.confirm_classification(
                workspace_id=workspace_id,
                scope=self._scope(scope),
                title=title,
                summary=summary,
                tags=tags,
                source=source,
            ).to_dict(),
        )

    def list_experiences(
        self, workspace_id: str, *, include_general: bool = False
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._call(
            "list_experiences",
            lambda: [
                record.to_dict()
                for record in self.store.list_experiences(
                    workspace_id, include_general=include_general
                )
            ],
        )

    def view_experience(
        self, record_id: str, workspace_id: str, scope: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "view_experience",
            lambda: self.store.get_experience(
                record_id,
                workspace_id=workspace_id,
                scope=self._scope(scope) if scope is not None else None,
            ).to_dict(),
        )

    def edit_experience(
        self,
        record_id: str,
        workspace_id: str,
        scope: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "edit_experience",
            lambda: self.store.edit_experience(
                record_id,
                workspace_id=workspace_id,
                scope=self._scope(scope),
                title=title,
                summary=summary,
                tags=tags,
            ).to_dict(),
        )

    def delete_experience(
        self,
        record_id: str,
        workspace_id: str,
        scope: str,
        *,
        confirm: str,
    ) -> ServiceResult[dict[str, Any]]:
        if confirm != record_id:
            return ServiceResult.failure(
                "confirmation_mismatch",
                "--confirm must exactly match the experience id",
                meta=self._meta("delete_experience"),
            )

        def action() -> dict[str, Any]:
            deleted = self.store.delete_experience(
                record_id,
                workspace_id=workspace_id,
                scope=self._scope(scope),
            )
            return {"status": "deleted", "id": deleted.id, "scope": deleted.scope}

        return self._call("delete_experience", action)

    def export_experiences(
        self,
        workspace_id: str,
        format: str,
        *,
        include_general: bool = False,
        path: str | Path | None = None,
    ) -> ServiceResult[str]:
        return self._call(
            "export_experiences",
            lambda: self.store.export_experiences(
                workspace_id=workspace_id,
                format=self._format(format),
                include_general=include_general,
                path=path,
            ),
        )

    def generate_evolution(
        self,
        *,
        instruction: str,
        artifact_type: str,
        output: str | Path,
        access_mode: str = "sandbox",
        experience_source: Any | None = None,
        workspace_id: str | None = None,
        confirmed: bool = False,
        overwrite: bool = False,
        confirm_full_access: bool = False,
        acknowledge_risk: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        audit_path = self.state_root / "policies" / "audit.jsonl"
        return self._call(
            "generate_evolution",
            lambda: self.evolution.generate(
                user_intent=instruction,
                artifact_type=artifact_type,
                output_path=output,
                access_mode=access_mode,
                experience_source=experience_source,
                workspace_id=workspace_id,
                confirmed=confirmed,
                overwrite=overwrite,
                audit_logger=AuditLogger(audit_path) if confirmed else None,
                full_access_confirmed=confirm_full_access,
                risk_notice_acknowledged=acknowledge_risk,
                metadata=metadata,
            ),
        )

    def recommend_evolution(
        self,
        instruction: str,
        *,
        artifact_type: str = "markdown",
        workspace_id: str | None = None,
        source: dict[str, Any] | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        """Queue a safe preview recommendation for explicit human confirmation."""

        def action() -> dict[str, Any]:
            normalized = instruction.strip()
            if not normalized:
                raise ValueError("self-evolution recommendation is empty")
            if artifact_type not in ARTIFACT_TYPE_WHITELIST:
                raise ValueError("unsupported self-evolution artifact type")
            digest = sha256(
                f"{workspace_id or 'global'}\0{normalized}".encode("utf-8")
            ).hexdigest()[:16]
            artifact_id = f"recommendation-{digest}"
            directory = self.state_root / "self-evolution" / "recommendations"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{artifact_id}.json"
            payload = {
                "id": artifact_id,
                "type": artifact_type,
                "instruction": normalized,
                "status": "pending",
                "workspace_id": workspace_id,
                "source": source or {"kind": "manual"},
                "created_at": utc_now(),
                "output": f"self_evolution/generated/{artifact_id}.md",
            }
            if path.is_file():
                existing = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    return existing
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return payload

        return self._call("recommend_evolution", action)

    def confirm_evolution(
        self, artifact_id: str
    ) -> ServiceResult[dict[str, Any]]:
        """Generate one queued recommendation only after a human confirms it."""

        def action() -> dict[str, Any]:
            path = self._artifact_path(artifact_id)
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("invalid self-evolution recommendation")
            if payload.get("status") == "success":
                return payload
            result = self.evolution.generate(
                user_intent=str(payload.get("instruction") or ""),
                artifact_type=str(payload.get("type") or "markdown"),
                output_path=str(payload.get("output") or ""),
                workspace_id=(
                    str(payload["workspace_id"])
                    if payload.get("workspace_id")
                    else None
                ),
                access_mode="sandbox",
                confirmed=True,
                audit_logger=AuditLogger(
                    self.state_root / "policies" / "audit.jsonl"
                ),
            )
            payload["status"] = result.get("status", "failed")
            payload["result"] = result
            payload["confirmed_at"] = utc_now()
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return payload

        return self._call("confirm_evolution", action)

    def list_evolution_artifacts(self) -> ServiceResult[list[dict[str, Any]]]:
        def action() -> list[dict[str, Any]]:
            directory = self.state_root / "self-evolution" / "recommendations"
            if not directory.is_dir():
                return []
            artifacts = []
            for path in sorted(directory.glob("*.json")):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                artifacts.append(
                    {
                        "id": path.stem,
                        "type": data.get("type", "unknown"),
                        "instruction": data.get("instruction", ""),
                        "status": data.get("status", "pending"),
                        "path": str(path),
                    }
                )
            return artifacts

        return self._call("list_evolution_artifacts", action)

    def get_evolution_artifact(
        self, artifact_id: str
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "get_evolution_artifact",
            lambda: json.loads(self._artifact_path(artifact_id).read_text(encoding="utf-8")),
        )

    def delete_evolution_artifact(
        self, artifact_id: str
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            self._artifact_path(artifact_id).unlink()
            return {"success": True, "message": f"Artifact {artifact_id} deleted"}

        return self._call("delete_evolution_artifact", action)

    def _artifact_path(self, artifact_id: str) -> Path:
        if not artifact_id or Path(artifact_id).name != artifact_id:
            raise ValueError("invalid self-evolution artifact id")
        path = (
            self.state_root
            / "self-evolution"
            / "recommendations"
            / f"{artifact_id}.json"
        )
        if not path.is_file():
            raise FileNotFoundError(f"Artifact not found: {artifact_id}")
        return path

    def _call(self, operation: str, action: Callable[[], Any]) -> ServiceResult[Any]:
        try:
            return ServiceResult.success(action(), meta=self._meta(operation))
        except (ExperienceError, WorkspaceError, OSError, ValueError) as exc:
            code = (
                "workspace_not_found"
                if isinstance(exc, WorkspaceNotFoundError)
                else "evolution_artifact_not_found"
                if isinstance(exc, FileNotFoundError)
                else "invalid_artifact_id"
                if isinstance(exc, ValueError)
                and "artifact id" in str(exc).lower()
                else "experience_error"
            )
            return ServiceResult.failure(
                code, str(exc), meta=self._meta(operation)
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                _result._safe_internal_message(exc, "Experience service failed"),
                meta=self._meta(operation),
            )

    @staticmethod
    def _scope(value: str) -> ExperienceScope:
        if value not in {"general", "workspace"}:
            raise ValueError("experience scope must be one of: general, workspace")
        return cast(ExperienceScope, value)

    @staticmethod
    def _format(value: str) -> ExportFormat:
        if value not in {"json", "md"}:
            raise ValueError("experience export format must be one of: json, md")
        return cast(ExportFormat, value)
