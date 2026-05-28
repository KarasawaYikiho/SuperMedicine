"""集中式 LLM 配置管理服务。"""
from __future__ import annotations

from typing import Any

from core.config_center import ConfigCenter
from core.llm_client import LLMClient, create_llm_client
from core.llm_providers.config import LLMProviderConfig
from core.redaction import redact_sensitive


class LLMConfigManager:
    """管理 LLM providers、当前默认 provider 与启动恢复状态。"""

    REQUIRED_FIELDS = LLMProviderConfig.REQUIRED_FIELDS
    SETUP_HINT = (
        "Configure LLM before running this task via Install.py --init, "
        ".supermedicine/config.yaml, supermedicine llm add/switch CLI, or the TUI LLM screen."
    )

    def __init__(self, config_center: ConfigCenter, *, restore_on_startup: bool = True):
        self._config = config_center
        if restore_on_startup:
            self.restore_startup_provider()

    def list_providers(self, *, redacted: bool = True) -> dict[str, Any]:
        """列出 provider 配置；默认脱敏。"""
        return self._config.get_llm_providers(redacted=redacted)

    def add_provider(
        self,
        provider: str,
        values: dict[str, Any],
        *,
        set_current: bool = False,
        save: bool = True,
    ) -> dict[str, Any]:
        """添加或更新 provider 配置，可选设为当前默认。"""
        provider_name = self._normalize_provider(provider)
        if not provider_name:
            return self._error("missing_provider", "LLM provider name is required")

        config_values = dict(values)
        config_values.setdefault("api_format", self._default_api_format(provider_name))
        config_values.setdefault("provider", provider_name)
        self._config.set_llm_provider_config(provider_name, config_values)
        if set_current:
            switch_result = self.switch_provider(provider_name, save=False)
            if not switch_result["ok"]:
                return switch_result
        if save:
            self._config.save()
        return {"ok": True, "provider": self.get_provider(provider_name, redacted=True)}

    def switch_provider(self, provider: str, *, save: bool = True) -> dict[str, Any]:
        """切换当前 provider；切换前校验配置完整性。"""
        provider_name = self._normalize_provider(provider)
        if not provider_name:
            return self._error("missing_provider", "LLM provider name is required")
        provider_config = self._config.get_llm_provider_config(provider_name)
        if not self._provider_exists(provider_name):
            return self._error("provider_not_found", f"LLM provider not found: {provider_name}", provider=provider_name)

        validation_error = self.validate_provider(provider_name, provider_config)
        if validation_error is not None:
            return validation_error

        self._config.set_llm_current_provider(provider_name)
        self._config.set_llm_last_provider(provider_name)
        if save:
            self._config.save()
        return {"ok": True, "provider": self.get_provider(provider_name, redacted=True)}

    def get_current_provider(self, *, redacted: bool = True) -> dict[str, Any]:
        """获取当前 provider 配置；默认脱敏。"""
        provider_name = self._config.get_llm_runtime_provider_name()
        return self.get_provider(provider_name, redacted=redacted)

    def get_provider(self, provider: str, *, redacted: bool = True) -> dict[str, Any]:
        """获取指定 provider 配置。"""
        provider_name = self._normalize_provider(provider)
        if not provider_name:
            return {}
        return self._config.get_llm_provider_config(provider_name, redacted=redacted)

    def save_exit_state(self, provider: str | None = None, *, save: bool = True) -> dict[str, Any]:
        """保存退出时使用的 provider。"""
        provider_name = self._normalize_provider(provider or self._config.get_llm_current_provider_name())
        if not provider_name:
            return self._error("missing_provider", "No current LLM provider to save")
        if not self._provider_exists(provider_name):
            return self._error("provider_not_found", f"LLM provider not found: {provider_name}", provider=provider_name)
        self._config.set_llm_last_provider(provider_name)
        if save:
            self._config.save()
        return {"ok": True, "provider": provider_name}

    def restore_startup_provider(self, *, save: bool = True) -> dict[str, Any]:
        """启动时优先恢复 last_provider，否则保留安装阶段写入的默认 provider。"""
        last_provider = self._normalize_provider(self._config.get_llm_last_provider_name())
        current_provider = self._normalize_provider(self._config.get_llm_current_provider_name())
        provider_name = last_provider if last_provider and self._provider_exists(last_provider) else current_provider
        if not provider_name:
            return self._error("missing_provider", f"No LLM provider configured. {self.SETUP_HINT}")
        if not self._provider_exists(provider_name):
            return self._error("provider_not_found", f"LLM provider not found: {provider_name}. {self.SETUP_HINT}", provider=provider_name)

        self._config.set_llm_current_provider(provider_name)
        restored_last_provider = bool(last_provider and provider_name == last_provider and current_provider != provider_name)
        if save or restored_last_provider:
            self._config.save()
        return {"ok": True, "provider": self.get_provider(provider_name, redacted=True)}

    def validate_provider(self, provider: str, values: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """校验 provider 是否具备 base_url/api_key/model。"""
        provider_name = self._normalize_provider(provider)
        raw_values = dict(values or self._config.get_llm_provider_config(provider_name))
        config = LLMProviderConfig.from_mapping(provider_name, raw_values)
        missing = config.missing_fields()
        if not missing:
            return None
        code_by_field = {
            "base_url": "missing_base_url",
            "api_key": "missing_api_key",
            "model": "missing_model",
        }
        error_code = code_by_field.get(missing[0], "incomplete_provider_config")
        return self._error(
            error_code,
            "LLM provider configuration is incomplete: " + ", ".join(missing) + f". {self.SETUP_HINT}",
            provider=provider_name,
            details={"missing": missing, "config": config.safe_dict()},
        )

    def create_client(self, provider: str | None = None) -> LLMClient | dict[str, Any]:
        """基于当前/恢复 provider 创建 LLMClient；配置异常时返回结构化错误。"""
        if provider is None:
            restore_result = self.restore_startup_provider(save=False)
            if not restore_result["ok"]:
                return restore_result
        provider_name = self._normalize_provider(provider or self._config.get_llm_runtime_provider_name())
        if not provider_name:
            return self._error("missing_provider", f"No LLM provider configured. {self.SETUP_HINT}")
        if not self._provider_exists(provider_name):
            return self._error(
                "provider_not_found",
                f"LLM provider not found: {provider_name}. {self.SETUP_HINT}",
                provider=provider_name,
            )
        provider_config = self._config.get_llm_provider_config(provider_name)
        validation_error = self.validate_provider(provider_name, provider_config)
        if validation_error is not None:
            return validation_error
        return create_llm_client(provider_name, config=provider_config)

    def _provider_exists(self, provider: str) -> bool:
        return provider in self._config.get_llm_providers()

    @staticmethod
    def _normalize_provider(provider: str | None) -> str:
        return str(provider or "").strip().lower()

    @staticmethod
    def _default_api_format(provider: str) -> str:
        if provider == "anthropic":
            return "anthropic"
        return "openai"

    @staticmethod
    def _error(
        code: str,
        message: str,
        *,
        provider: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": code,
            "message": redact_sensitive(message),
        }
        if provider:
            error["provider"] = provider
        if details:
            error["details"] = redact_sensitive(details)
        return {"ok": False, "error": error}
