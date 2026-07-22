"""Workspace application service shared by all user interfaces."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

import yaml

from core.operation_guard import authorize_dangerous_operation
from core.path_safety import validate_destructive_path
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
from permission.policy import ensure_default_policy

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

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.manager = WorkspaceManager(project_root)
        self.project_root = self.manager.project_root

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
            audit_path = (
                self.project_root / ".supermedicine" / "policies" / "audit.jsonl"
            )
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
            ensure_default_policy(self.project_root)
            policies_dir = self.project_root / ".supermedicine" / "policies"
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
