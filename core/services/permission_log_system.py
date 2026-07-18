"""Permission, log, and system application service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from core.config_center import ConfigCenter
from core.log_report import LogReportError, LogReportStore
from core.redaction import redact_sensitive
from core.services.result import ServiceResult
from permission.access_mode import (
    AccessMode,
    FileAccessOperation,
    FullAccessConfirmationRequired,
    normalize_access_mode,
)


class PermissionLogSystemService:
    """Own runtime permission configuration and redacted log storage use cases."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.config = ConfigCenter(
            self.project_root / ".supermedicine" / "config.yaml"
        )
        self.logs = LogReportStore(self.project_root)

    def permission_status(self) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            data = self.config.get_file_access_config()
            data["config_load_error"] = self.config.diagnostics().get(
                "load_error", ""
            )
            return data

        return self._call("permission_status", action)

    def set_permission_mode(
        self, mode: str, *, explicit_confirmation: bool = False
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            normalized = normalize_access_mode(mode)
            data = self.config.set_file_access_mode(
                normalized,
                explicit_confirmation=(
                    explicit_confirmation or normalized != AccessMode.FULL
                ),
            )
            self.config.save()
            return data

        return self._call("set_permission_mode", action)

    def authorize_directory(self, path: str | Path) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            data = self.config.authorize_external_file_access_directory(path)
            self.config.save()
            return data

        return self._call("authorize_directory", action)

    def revoke_directory(self, path: str | Path) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            data = self.config.revoke_external_file_access_directory(path)
            self.config.save()
            return data

        return self._call("revoke_directory", action)

    def access_decision(
        self, path: str | Path, operation: str = "write"
    ) -> ServiceResult[dict[str, str]]:
        def action() -> dict[str, str]:
            decision = self.config.get_file_access_policy(self.project_root).decide(
                path, FileAccessOperation(operation)
            )
            return {
                "status": decision.status.value,
                "mode": decision.mode.value,
                "reason": decision.reason,
                "path": str(decision.path),
                "helper": decision.helper,
            }

        return self._call("access_decision", action)

    def set_current_view(self, view_id: str) -> ServiceResult[str]:
        def action() -> str:
            self.config.set_current_view(view_id, save=True)
            return view_id

        return self._call("set_current_view", action)

    def config_diagnostics(self) -> ServiceResult[dict[str, Any]]:
        return self._call("config_diagnostics", self.config.diagnostics)

    def write_log(
        self, message: str, *, session_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "write_log", lambda: self.logs.write(message, session_id=session_id)
        )

    def list_logs(self) -> ServiceResult[list[dict[str, Any]]]:
        return self._call("list_logs", self.logs.list)

    def show_log(self, file_name: str) -> ServiceResult[dict[str, Any]]:
        return self._call("show_log", lambda: self.logs.show(file_name))

    def log_storage(
        self, *, file_name: str | None = None, session_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "log_storage",
            lambda: self.logs.storage_info(
                file_name=file_name, session_id=session_id
            ),
        )

    def list_log_entries(
        self, *, file_name: str | None = None, session_id: str | None = None
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._call(
            "list_log_entries",
            lambda: self.logs.list_entries(
                file_name=file_name, session_id=session_id
            ),
        )

    def log_statistics(
        self, entries: list[dict[str, Any]]
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "log_statistics", lambda: self.logs.statistics_for_entries(entries)
        )

    def follow_log_snapshot(self, **kwargs: Any) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "follow_log_snapshot", lambda: self.logs.follow_snapshot(**kwargs)
        )

    def _call(self, operation: str, action: Callable[[], Any]) -> ServiceResult[Any]:
        try:
            return ServiceResult.success(action(), meta=self._meta(operation))
        except FullAccessConfirmationRequired as exc:
            return ServiceResult.failure(
                "full_access_confirmation_required",
                str(exc),
                meta=self._meta(operation),
            )
        except (ValueError, OSError, LogReportError) as exc:
            return ServiceResult.failure(
                "system_error", str(exc), meta=self._meta(operation)
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                str(redact_sensitive(str(exc))) or "System service failed",
                meta=self._meta(operation),
            )

    @staticmethod
    def require_data(result: ServiceResult[Any]) -> Any:
        if result.ok:
            return result.data
        if result.error and result.error.code == "full_access_confirmation_required":
            raise FullAccessConfirmationRequired(result.error.message)
        raise ValueError(result.error.message if result.error else "System service failed")

    @staticmethod
    def _meta(operation: str) -> dict[str, str]:
        return {"service": "permission_log_system", "operation": operation}
