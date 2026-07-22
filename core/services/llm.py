"""LLM Provider application service shared by CLI and graphical interfaces."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager

from . import result as _result
from .result import ServiceResult


class LLMService:
    _meta = staticmethod(partial(_result._service_meta, "llm"))

    def __init__(
        self,
        project_root: str | Path | None = None,
        *,
        restore_on_startup: bool = False,
    ) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config = ConfigCenter(
            self.project_root / ".supermedicine" / "config.yaml"
        )
        self.manager = LLMConfigManager(
            self.config, restore_on_startup=restore_on_startup
        )

    @staticmethod
    def provider_values(
        *,
        api_format: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the persisted values for an LLM provider."""
        values: dict[str, Any] = {
            key: value
            for key, value in {
                "api_format": api_format,
                "base_url": base_url,
                "api_key": api_key,
                "api_key_env": api_key_env,
                "model": model,
                "timeout": timeout,
            }.items()
            if value is not None
        }
        if headers:
            values["headers"] = headers
        return values

    def add_provider(
        self,
        provider: str,
        values: dict[str, Any],
        *,
        set_current: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "add_provider",
            request_id,
            lambda: self.manager.add_provider(
                provider, values, set_current=set_current
            ),
        )

    def list_providers(
        self, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "list_providers",
            request_id,
            lambda: {
                "current_provider": self.config.get_llm_current_provider_name(),
                "last_provider": self.config.get_llm_last_provider_name(),
                "providers": self.manager.list_providers(redacted=True),
            },
        )

    def show_provider(
        self, provider: str | None = None, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "show_provider",
            request_id,
            lambda: self.manager.get_provider(provider, redacted=True)
            if provider
            else self.manager.get_current_provider(redacted=True),
        )

    def switch_provider(
        self, provider: str, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "switch_provider",
            request_id,
            lambda: self.manager.switch_provider(provider, save=True),
        )

    def delete_provider(
        self, provider: str, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "delete_provider",
            request_id,
            lambda: self.manager.delete_provider(provider, save=True),
        )

    def save_exit_state(
        self, provider: str | None = None, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._call(
            "save_exit_state",
            request_id,
            lambda: self.manager.save_exit_state(provider, save=True),
        )

    def validate_provider(self, provider: str) -> ServiceResult[dict[str, Any]]:
        error = self.manager.validate_provider(provider)
        if error is None:
            return ServiceResult.success(
                {"provider": provider, "valid": True},
                meta=self._meta("validate_provider"),
            )
        return self._manager_result(error, "validate_provider", None)

    @staticmethod
    def legacy_result(result: ServiceResult[Any]) -> Any:
        """Return the pre-service CLI/TUI result shape during migration."""
        if result.ok:
            return result.data
        error = result.error
        if error is not None:
            details = dict(error.details)
            provider = details.pop("provider", None)
            legacy_error: dict[str, Any] = {
                "code": error.code,
                "message": error.message,
            }
            if provider:
                legacy_error["provider"] = provider
            if details:
                legacy_error["details"] = details
            return {"ok": False, "error": legacy_error}
        return {
            "ok": False,
            "error": {
                "code": "service_error",
                "message": "LLM service failed",
            },
        }

    def _call(
        self,
        operation: str,
        request_id: str | None,
        action: Any,
    ) -> ServiceResult[dict[str, Any]]:
        try:
            raw = action()
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                _result._safe_internal_message(exc, "LLM service failed"),
                request_id=request_id,
                meta=self._meta(operation),
            )
        return self._manager_result(raw, operation, request_id)

    def _manager_result(
        self,
        raw: dict[str, Any],
        operation: str,
        request_id: str | None,
    ) -> ServiceResult[dict[str, Any]]:
        if raw.get("ok") is not False:
            return ServiceResult.success(
                raw, request_id=request_id, meta=self._meta(operation)
            )
        error_value = raw.get("error")
        raw_error: dict[str, Any] = error_value if isinstance(error_value, dict) else {}
        details = dict(raw_error.get("details") or {})
        if raw_error.get("provider"):
            details.setdefault("provider", raw_error["provider"])
        return ServiceResult.failure(
            str(raw_error.get("code") or "llm_error"),
            str(raw_error.get("message") or "LLM operation failed"),
            request_id=request_id,
            details=details,
            meta=self._meta(operation),
        )
