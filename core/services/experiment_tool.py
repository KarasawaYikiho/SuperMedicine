"""Experiment and workspace-tool application service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence, cast

from core.config_center import ConfigCenter
from core.redaction import redact_sensitive
from core.services.result import ServiceResult
from core.workspace import InvalidWorkspaceId, WorkspaceError, WorkspaceNotFoundError
from core.workspace_tool_models import (
    InvalidToolId,
    InvalidToolLanguage,
    ToolCandidateError,
    ToolManifestError,
    ToolNotFoundError,
    WorkspaceToolError,
)
from core.workspace_tools import WorkspaceToolService


class ExperimentToolService:
    """Own experiment and workspace-tool use cases used by all interfaces."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.tools = WorkspaceToolService(project_root)
        self.project_root = self.tools.project_root

    def initialize_tools(
        self, workspace_id: str, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._tool_call(
            "initialize_tools",
            request_id,
            lambda: self.tools.initialize_tools(workspace_id),
            workspace_id=workspace_id,
        )

    def list_tools(
        self,
        workspace_id: str,
        *,
        language: str | None = None,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, list[dict[str, Any]]]]:
        return self._tool_call(
            "list_tools",
            request_id,
            lambda: self.tools.list_tools(workspace_id, language=language),
            workspace_id=workspace_id,
        )

    def scan_tools(
        self, language: str | None = None, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, list[dict[str, Any]]]]:
        return self._tool_call(
            "scan_tools",
            request_id,
            lambda: self.tools.scan_import_candidates(language),
        )

    def import_tools(
        self,
        workspace_id: str,
        selections: Sequence[str | int] | None,
        *,
        language: str | None = None,
        overwrite: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            if not selections:
                return {
                    "status": "select_required",
                    "message": "Select tools from this scanned list with --select; no tool ID knowledge is required.",
                    "candidates": self.tools.scan_import_candidates(language),
                }
            result = self.tools.import_scanned_tools(
                workspace_id,
                selections,
                language=language,
                overwrite=overwrite,
            )
            imported_raw = result.get("imported")
            imported = (
                [cast(dict[str, Any], item) for item in imported_raw if isinstance(item, dict)]
                if isinstance(imported_raw, list)
                else []
            )
            if imported:
                self._record_tool_import(workspace_id, imported)
            return result

        return self._tool_call(
            "import_tools",
            request_id,
            action,
            workspace_id=workspace_id,
        )

    def show_tool(
        self,
        workspace_id: str,
        language: str,
        tool_id: str,
        *,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._tool_call(
            "show_tool",
            request_id,
            lambda: self.tools.show_tool(workspace_id, language, tool_id),
            workspace_id=workspace_id,
            tool_id=tool_id,
        )

    def prepare_tool(
        self,
        workspace_id: str,
        language: str,
        tool_id: str,
        *,
        dry_run: bool = False,
        input_path: str | None = None,
        output_path: str | None = None,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._tool_call(
            "prepare_tool",
            request_id,
            lambda: self.tools.prepare_invocation(
                workspace_id,
                language,
                tool_id,
                dry_run=dry_run,
                input_path=input_path,
                output_path=output_path,
            ).to_dict(),
            workspace_id=workspace_id,
            tool_id=tool_id,
        )

    def _record_tool_import(
        self, workspace_id: str, imported: list[dict[str, Any]]
    ) -> None:
        config = ConfigCenter(self.project_root / ".supermedicine" / "config.yaml")
        config.set_runtime_state_value("last_workspace_id", workspace_id)
        config.record_tool_import_state(
            workspace_id=workspace_id, imported=imported, save=True
        )

    def _tool_call(
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
        except (WorkspaceToolError, WorkspaceError, OSError) as exc:
            return ServiceResult.failure(
                self._tool_error_code(exc),
                str(exc),
                request_id=request_id,
                details=details,
                meta=self._meta(operation),
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                str(redact_sensitive(str(exc))) or "Experiment/tool service failed",
                request_id=request_id,
                details=details,
                meta=self._meta(operation),
            )

    @staticmethod
    def _tool_error_code(exc: Exception) -> str:
        if isinstance(exc, InvalidToolLanguage):
            return "invalid_tool_language"
        if isinstance(exc, InvalidToolId):
            return "invalid_tool_id"
        if isinstance(exc, ToolNotFoundError):
            return "tool_not_found"
        if isinstance(exc, ToolManifestError):
            return "invalid_tool_manifest"
        if isinstance(exc, ToolCandidateError):
            return "invalid_tool_candidate"
        if isinstance(exc, WorkspaceNotFoundError):
            return "workspace_not_found"
        if isinstance(exc, InvalidWorkspaceId):
            return "invalid_workspace_id"
        return "tool_error"

    @staticmethod
    def require_data(result: ServiceResult[Any]) -> Any:
        if result.ok:
            return result.data
        error = result.error
        message = error.message if error else "Experiment/tool service failed"
        if error and error.code == "workspace_not_found":
            raise WorkspaceNotFoundError(message)
        raise ValueError(message)

    @staticmethod
    def _meta(operation: str) -> dict[str, str]:
        return {"service": "experiment_tool", "operation": operation}
