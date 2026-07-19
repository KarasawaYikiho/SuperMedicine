"""Experience learning and self-evolution application service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, cast

from core.experience import (
    ExperienceError,
    ExperienceScope,
    ExperienceStore,
    ExportFormat,
)
from core.redaction import redact_sensitive
from core.self_evolution import SelfEvolutionService
from core.services.result import ServiceResult
from core.workspace import WorkspaceError, WorkspaceNotFoundError
from permission.audit import AuditLogger


class ExperienceEvolutionService:
    """Own confirmed experience CRUD and guarded self-evolution generation."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.store = ExperienceStore(project_root)
        self.project_root = self.store.project_root
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
        audit_path = self.project_root / ".supermedicine" / "policies" / "audit.jsonl"
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

    def list_evolution_artifacts(self) -> ServiceResult[list[dict[str, Any]]]:
        def action() -> list[dict[str, Any]]:
            directory = self.project_root / "self_evolution"
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
        path = self.project_root / "self_evolution" / f"{artifact_id}.json"
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
                str(redact_sensitive(str(exc))) or "Experience service failed",
                meta=self._meta(operation),
            )

    @staticmethod
    def require_data(result: ServiceResult[Any]) -> Any:
        if result.ok:
            return result.data
        raise ValueError(result.error.message if result.error else "Experience service failed")

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

    @staticmethod
    def _meta(operation: str) -> dict[str, str]:
        return {"service": "experience_evolution", "operation": operation}
