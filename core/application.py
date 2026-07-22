"""UI-independent application operations and result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.redaction import redact_sensitive
from core.runtime_paths import RuntimePaths

if TYPE_CHECKING:
    from core.services.result import ServiceResult
    from core.services.workspace import WorkspaceService


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
        self._workspaces: WorkspaceService | None = None

    def _workspace_service(self) -> WorkspaceService:
        if self._workspaces is None:
            from core.services.workspace import WorkspaceService

            self._workspaces = WorkspaceService(self.paths.project_root)
        return self._workspaces

    def create_workspace(self, workspace_id: str, name: str | None = None) -> AppResult:
        return _app_result(self._workspace_service().create(workspace_id, name=name))

    def list_workspaces(self) -> AppResult:
        return _app_result(self._workspace_service().list())

    def get_workspace(self, workspace_id: str) -> AppResult:
        return _app_result(self._workspace_service().show(workspace_id))

    def delete_workspace(self, workspace_id: str, *, confirm: str) -> AppResult:
        return _app_result(
            self._workspace_service().delete(workspace_id, confirm=confirm)
        )


def _app_result(result: ServiceResult[Any]) -> AppResult:
    if result.ok:
        return AppResult(ok=True, data=redact_sensitive(result.data))
    error = result.error
    code = error.code if error else "internal_error"
    public_codes = {
        "confirmation_mismatch": "validation_error",
        "invalid_workspace_id": "validation_error",
        "required_file_missing": "not_found",
        "workspace_error": "validation_error",
        "workspace_exists": "conflict",
        "workspace_not_found": "not_found",
    }
    code = public_codes.get(code, code)
    message = error.message if error else "Internal application error"
    if code == "internal_error":
        message = "Internal application error"
    return AppResult(
        ok=False,
        error=AppError(
            code=code,
            message=str(redact_sensitive(message)),
            details=redact_sensitive(error.details if error else {}),
        ),
    )


__all__ = ["AppError", "ApplicationFacade", "AppResult"]
