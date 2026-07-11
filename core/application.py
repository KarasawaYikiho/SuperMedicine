"""UI-independent application operations and result contracts."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any, Callable

import yaml

from core.redaction import redact_sensitive
from core.runtime_paths import RuntimePaths
from core.workspace import (
    InvalidWorkspaceId,
    WorkspaceError,
    WorkspaceInfo,
    WorkspaceManager,
    WorkspaceNotFoundError,
    validate_workspace_id,
)


@dataclass(frozen=True, slots=True)
class AppResult:
    ok: bool
    data: Any = None
    error: AppError | None = None


@dataclass(frozen=True, slots=True)
class AppError:
    code: str
    message: str
    details: dict[str, Any] | None = None
    retryable: bool = False


class ApplicationFacade:
    """Expose core operations against one explicit set of runtime paths."""

    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths

    def create_workspace(self, workspace_id: str, name: str | None = None) -> AppResult:
        def operation() -> dict[str, Any]:
            manager = WorkspaceManager(self.paths.project_root)
            info = manager.initialize_workspace(workspace_id)
            if name is not None:
                metadata_path = info.path / "workspace.yaml"
                metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
                metadata["display_name"] = name
                metadata_path.write_text(
                    yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True),
                    encoding="utf-8",
                )
                info = manager.get_workspace(workspace_id)
            return _workspace_data(info, name=name)

        return self._run(operation)

    def list_workspaces(self) -> AppResult:
        return self._run(
            lambda: [
                _workspace_data(info)
                for info in WorkspaceManager(self.paths.project_root).list_workspaces()
            ]
        )

    def get_workspace(self, workspace_id: str) -> AppResult:
        return self._run(
            lambda: _workspace_data(
                WorkspaceManager(self.paths.project_root).get_workspace(workspace_id)
            )
        )

    def delete_workspace(self, workspace_id: str, *, confirm: str) -> AppResult:
        def operation() -> dict[str, Any]:
            from core.operation_guard import authorize_dangerous_operation
            from core.path_safety import validate_destructive_path
            from permission.audit import AuditLogger
            from permission.engine import PermissionEngine
            from permission.policy import ensure_default_policy

            project_root = self.paths.project_root
            manager = WorkspaceManager(project_root)
            slug = validate_workspace_id(workspace_id)
            workspace_path = manager.workspace_path(slug)
            audit_log = self.paths.data_root / "policies" / "audit.jsonl"
            audit_logger = AuditLogger(audit_log)
            if confirm != slug:
                audit_logger.log(
                    agent_id="delta",
                    action="workspace.delete",
                    resource=str(workspace_path),
                    result="cancelled",
                    reason="confirmation_mismatch",
                )
                raise ValueError("confirm must exactly match workspace id for deletion")

            manager.get_workspace(slug)
            safe_path = validate_destructive_path(workspace_path, project_root)
            policies_dir = self.paths.data_root / "policies"
            try:
                ensure_default_policy(project_root)
            except FileNotFoundError:
                audit_logger.log(
                    agent_id="delta",
                    action="workspace.delete",
                    resource=str(safe_path),
                    result="cancelled",
                    reason="missing_default_policy",
                )
                raise
            permission_engine = PermissionEngine(policies_dir, audit_log)
            authorization = authorize_dangerous_operation(
                permission_engine=permission_engine,
                agent_id="delta",
                action="workspace.delete",
                path=safe_path,
                project_root=project_root,
                context={"workspace_id": slug},
                destructive=True,
                audit_logger=audit_logger,
                operation="workspace_delete",
            )
            if authorization.path.is_dir():
                shutil.rmtree(authorization.path)
            else:
                authorization.path.unlink()
            return {"status": "deleted", "id": slug, "path": str(authorization.path)}

        return self._run(operation)

    @staticmethod
    def _run(operation: Callable[[], Any]) -> AppResult:
        try:
            return AppResult(ok=True, data=redact_sensitive(operation()))
        except Exception as exc:  # adapters consume stable domain errors
            code, retryable = _error_code(exc)
            message = "Internal application error" if code == "internal_error" else str(exc)
            return AppResult(
                ok=False,
                error=AppError(
                    code=code,
                    message=str(redact_sensitive(message)),
                    details=redact_sensitive({"exception": type(exc).__name__}),
                    retryable=retryable,
                ),
            )


def _workspace_data(info: WorkspaceInfo, name: str | None = None) -> dict[str, Any]:
    metadata = info.metadata.to_dict()
    metadata_path = info.path / "workspace.yaml"
    if metadata_path.is_file():
        raw = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict) and raw.get("display_name") is not None:
            metadata["display_name"] = str(raw["display_name"])
    data: dict[str, Any] = {"id": info.id, "path": str(info.path), "metadata": metadata}
    display_name = name if name is not None else metadata.get("display_name")
    if display_name is not None:
        data["name"] = display_name
    return data


def _error_code(exc: Exception) -> tuple[str, bool]:
    if isinstance(exc, WorkspaceNotFoundError):
        return "not_found", False
    if isinstance(exc, PermissionError):
        return "permission_denied", False
    if isinstance(exc, FileExistsError):
        return "conflict", False
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return "dependency_unavailable", True
    if isinstance(exc, (InvalidWorkspaceId, WorkspaceError, ValueError, TypeError)):
        return "validation_error", False
    if isinstance(exc, FileNotFoundError):
        return "not_found", False
    return "internal_error", False


__all__ = ["AppError", "ApplicationFacade", "AppResult"]
