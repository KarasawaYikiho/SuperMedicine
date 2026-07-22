"""Permission, log, and system application service."""

from __future__ import annotations

import os
from functools import partial
from pathlib import Path
from typing import Any, Callable

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.log_report import (
    LogReportError,
    LogReportStore,
    resolve_log_storage_locations,
)
from core.plugin_registry import PluginRegistry
from core.runtime_capabilities import required_runtime_snapshot
from permission.access_mode import (
    AccessMode,
    FileAccessOperation,
    FullAccessConfirmationRequired,
    normalize_access_mode,
)

from . import result as _result
from .result import ServiceResult


class PermissionLogSystemService:
    """Own runtime permission configuration and redacted log storage use cases."""

    require_data = staticmethod(
        partial(
            _result._require_data,
            "System service failed",
            {"full_access_confirmation_required": FullAccessConfirmationRequired},
        )
    )
    _meta = staticmethod(partial(_result._service_meta, "permission_log_system"))

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.config = ConfigCenter(self.project_root / ".supermedicine" / "config.yaml")
        self.logs = LogReportStore(self.project_root)

    def permission_status(self) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            data = self.config.get_file_access_config()
            data["config_load_error"] = self.config.diagnostics().get("load_error", "")
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

    def application_status(self) -> ServiceResult[dict[str, Any]]:
        """Return the shared lightweight status used by Web and desktop clients."""

        def action() -> dict[str, Any]:
            from core.services.llm import LLMService

            provider_result = LLMService(self.project_root).show_provider()
            provider = (
                provider_result.data
                if provider_result.ok and isinstance(provider_result.data, dict)
                else {}
            )
            runtime = required_runtime_snapshot(self.project_root)
            return {
                "version": "0.4.2",
                "project_dir": str(self.project_root),
                "config_initialized": (self.project_root / ".supermedicine").exists(),
                "plugin_count": len(
                    PluginRegistry(
                        self.project_root / "plugins", allow_package_fallback=True
                    ).discover()
                ),
                "llm_provider": provider.get("provider", "未配置") if provider else "未配置",
                "required_runtime": runtime,
                "ok": bool(runtime["harness"]["healthy"])
                and bool(runtime["rag"]["healthy"]),
            }

        return self._call("application_status", action)

    def system_diagnostics(self) -> ServiceResult[dict[str, Any]]:
        """Aggregate secret-safe config, LLM, audit, and log diagnostics."""

        def action() -> dict[str, Any]:
            manager = LLMConfigManager(self.config, restore_on_startup=False)
            storage = resolve_log_storage_locations(self.project_root)
            config_diag = self.config.diagnostics()
            llm_diag = manager.diagnostics()
            runtime = required_runtime_snapshot(self.project_root)
            database_path = self.config.config_path.parent / "data.db"
            result: dict[str, Any] = {
                "ok": bool(config_diag.get("exists"))
                and bool(llm_diag.get("ok"))
                and bool(runtime["harness"]["healthy"])
                and bool(runtime["rag"]["healthy"]),
                "stage": "diagnose",
                "project_dir": str(self.project_root),
                "config": config_diag,
                "llm": llm_diag,
                "audit": {
                    "path": str(storage.audit_file),
                    "exists": storage.audit_file.exists(),
                    "writable_parent": storage.audit_file.parent.exists(),
                },
                "log_storage": storage.to_dict(),
                "database": {
                    "path": str(database_path),
                    "exists": database_path.is_file(),
                    "writable_parent": database_path.parent.is_dir()
                    and os.access(database_path.parent, os.W_OK),
                    "persistence": "required",
                    "ephemeral_fallback": False,
                },
                "required_runtime": runtime,
                "commands": {
                    "init": "set provider API key env var first, then run: supermedicine init --provider <name> --base-url <url> --model <model>",
                    "llm_list": "supermedicine llm list",
                    "llm_switch": "supermedicine llm switch <provider>",
                    "tui_dry_run": "supermedicine tui --dry-run",
                    "uninstall_dry_run": "python uninstall_entry.py --dry-run",
                },
            }
            return result

        return self._call("system_diagnostics", action)

    def runtime_state(self) -> ServiceResult[dict[str, Any]]:
        return self._call("runtime_state", self.config.get_runtime_state)

    def set_runtime_state_value(
        self, key: str, value: Any
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "set_runtime_state_value",
            lambda: self.config.set_runtime_state_value(key, value, save=True),
        )

    def plugin_capabilities(self) -> ServiceResult[dict[str, dict[str, Any]]]:
        def action() -> dict[str, dict[str, Any]]:
            registry = PluginRegistry(
                self.project_root / "plugins", allow_package_fallback=True
            )
            return {
                meta.name: {
                    "enabled": True,
                    "provides": [
                        item.get("id") if isinstance(item, dict) else str(item)
                        for item in meta.provides
                    ],
                }
                for meta in registry.discover()
            }

        return self._call("plugin_capabilities", action)

    def multi_agent_status(self) -> ServiceResult[dict[str, bool]]:
        return self._call("multi_agent_status", self.config.get_multi_agent_config)

    def set_multi_agent_enabled(self, enabled: bool) -> ServiceResult[dict[str, bool]]:
        return self._call(
            "set_multi_agent_enabled",
            lambda: self.config.set_multi_agent_enabled(enabled, save=True),
        )

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
            lambda: self.logs.storage_info(file_name=file_name, session_id=session_id),
        )

    def list_log_entries(
        self, *, file_name: str | None = None, session_id: str | None = None
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._call(
            "list_log_entries",
            lambda: self.logs.list_entries(file_name=file_name, session_id=session_id),
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
                _result._safe_internal_message(exc, "System service failed"),
                meta=self._meta(operation),
            )
