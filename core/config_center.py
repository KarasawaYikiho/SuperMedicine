"""配置中心 — YAML 配置管理，支持 SM_* 环境变量覆盖"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any

import yaml

from core.redaction import redact_sensitive
from core.llm_providers.config import LLMProviderConfig, sanitized_headers


logger = logging.getLogger(__name__)


DEFAULT_EXPERIMENT_GUIDE_CONFIG: dict[str, Any] = {
    "enabled": True,
    "allowed_plugins": ["experiment-wb"],
    "allowed_actions": [
        "experiment.wb.normalize_loading",
        "experiment.wb.antibody_dilution",
    ],
    "allowed_protocol_sources": ["builtin"],
    "log_dir": ".supermedicine/logs",
    "max_log_bytes": 1024 * 1024,
    "max_steps": 50,
    "max_prompt_length": 8000,
    "allow_network": False,
    "allow_external_api": False,
    "on_error": "record_and_stop",
}


DEFAULT_LOG_REPORT_CONFIG: dict[str, Any] = {
    "log_dir": ".supermedicine/logs",
    "max_message_length": 10000,
    "max_records_per_session": 1000,
    "max_file_bytes": 1024 * 1024,
    "redact": True,
}


class ConfigCenter:
    """配置管理中心"""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._config: dict[str, Any] = {}
        self._load_error: str = ""
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f) or {}
                if isinstance(loaded, dict):
                    self._config = loaded
                else:
                    self._load_error = f"config root must be a mapping: {config_path}"
                    logger.error(
                        "Config load failed: stage=parse path=%s error=%s",
                        config_path,
                        self._load_error,
                    )
            except yaml.YAMLError as exc:
                self._load_error = f"invalid YAML in config file {config_path}: {exc}"
                logger.error(
                    "Config load failed: stage=parse path=%s error=%s",
                    config_path,
                    redact_sensitive(str(exc)),
                )
            except OSError as exc:
                self._load_error = f"cannot read config file {config_path}: {exc}"
                logger.error(
                    "Config load failed: stage=read path=%s error=%s",
                    config_path,
                    redact_sensitive(str(exc)),
                )

    @property
    def config_path(self) -> Path:
        """配置文件路径。"""
        return self._config_path

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，SM_* 环境变量优先"""
        # 检查环境变量覆盖
        env_key = "SM_" + key.upper().replace("-", "_")
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值（仅修改内存，不自动持久化，需调用 save() 写入文件）"""
        self._config[key] = value

    def save(self) -> None:
        """将内存中的配置持久化到 YAML 文件（不包含 SM_* 环境变量覆盖值）"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

    def all(self) -> dict[str, Any]:
        """获取全部配置（合并环境变量覆盖）"""
        result = dict(self._config)
        for env_key, env_val in os.environ.items():
            if env_key.startswith("SM_"):
                config_key = env_key[3:].lower().replace("_", "-")
                result[config_key] = env_val
        return result

    def safe_all(self) -> dict[str, Any]:
        """获取可用于日志、错误、快照和能力输出的脱敏配置。"""
        return redact_sensitive(self.all())

    def diagnostics(self) -> dict[str, Any]:
        """Return a user-shareable diagnostic snapshot for config loading."""
        env_overrides = sorted(key for key in os.environ if key.startswith("SM_"))
        return redact_sensitive(
            {
                "config_path": str(self._config_path),
                "exists": self._config_path.exists(),
                "load_error": self._load_error,
                "env_override_keys": env_overrides,
                "precedence": [
                    "SM_* environment variables",
                    "config file",
                    "code defaults",
                ],
                "config": self.safe_all(),
            }
        )

    def diagnose_llm_config(self) -> dict[str, Any]:
        """Diagnose LLM provider selection and required fields without exposing secrets."""
        providers = self.get_llm_providers(redacted=True)
        raw_providers = self.get_llm_providers(redacted=False)
        current = self.get_llm_runtime_provider_name()
        missing: list[str] = []
        if not current:
            missing.append("provider")
        if current and current not in raw_providers:
            missing.append("providers." + current)
        if current and current in raw_providers:
            selected = raw_providers.get(current, {})
            missing.extend(
                LLMProviderConfig.from_mapping(current, selected).missing_fields()
            )
        return {
            "ok": not self._load_error and not missing,
            "stage": "config.llm",
            "config_path": str(self._config_path),
            "load_error": redact_sensitive(self._load_error),
            "provider": current,
            "missing": missing,
            "providers": providers,
            "hints": {
                "provider": "Set llm.provider or SM_LLM_PROVIDER / supermedicine llm switch <provider>.",
                "base_url": "Set providers.<provider>.base_url or pass --base-url during init/add.",
                "api_key": "Set providers.<provider>.api_key, api_key_env, or a provider API key environment variable.",
                "model": "Set providers.<provider>.model or pass --model during init/add.",
            },
        }

    def get_llm_config(self) -> dict[str, Any]:
        """获取 LLM 配置段；缺失或类型异常时返回空配置。"""
        llm_config = self._config.get("llm", {})
        if not isinstance(llm_config, dict):
            return {}
        return llm_config

    def get_experiment_guide_config(self) -> dict[str, Any]:
        """获取实验引导配置，缺失用户配置时返回安全默认值。"""
        return self._merged_default_section(
            "experiment_guide", DEFAULT_EXPERIMENT_GUIDE_CONFIG
        )

    def get_log_report_config(self) -> dict[str, Any]:
        """获取日志报告配置，缺失用户配置时返回安全默认值。"""
        return self._merged_default_section("log_report", DEFAULT_LOG_REPORT_CONFIG)

    def _merged_default_section(
        self, key: str, defaults: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a shallow, default-compatible config section merge."""
        value = self.get(key, {})
        result = dict(defaults)
        if isinstance(value, dict):
            result.update(value)
        return result

    def ensure_llm_config(self) -> dict[str, Any]:
        """确保 LLM 配置段存在并返回可变引用。"""
        llm_config = self._config.setdefault("llm", {})
        if not isinstance(llm_config, dict):
            llm_config = {}
            self._config["llm"] = llm_config
        providers = llm_config.setdefault("providers", {})
        if not isinstance(providers, dict):
            llm_config["providers"] = (
                self._normalized_llm_providers() if isinstance(providers, list) else {}
            )
        return llm_config

    def get_llm_providers(self, *, redacted: bool = False) -> dict[str, Any]:
        """列出所有 LLM provider 配置。

        稳定 YAML 格式使用 ``llm.providers`` 映射：
        ``providers.<name>`` 是 provider 名称，配置体内也可显式写
        ``provider`` 以便用户手工复制/调整。为兼容早期或手工编辑的
        YAML，也接受 ``providers`` 为列表，每项通过 ``provider`` 或
        ``name`` 字段声明 provider 名称。
        """
        result = self._normalized_llm_providers()
        return _redact_llm_providers(result) if redacted else result

    def set_llm_provider_config(self, provider: str, values: dict[str, Any]) -> None:
        """新增或覆盖单个 LLM provider 配置（仅修改内存）。"""
        llm_config = self.ensure_llm_config()
        providers = llm_config.setdefault("providers", {})
        if not isinstance(providers, dict):
            providers = {}
            llm_config["providers"] = providers
        providers[provider] = dict(values)

    def set_llm_current_provider(self, provider: str) -> None:
        """设置当前默认 LLM provider（仅修改内存）。"""
        self.ensure_llm_config()["provider"] = provider

    def get_llm_current_provider_name(self) -> str:
        """获取当前默认 LLM provider 名称。"""
        provider = self.get_llm_config().get("provider", "")
        return str(provider or "")

    def set_llm_last_provider(self, provider: str) -> None:
        """保存上次使用/退出时的 LLM provider（仅修改内存）。"""
        self.ensure_llm_config()["last_provider"] = provider

    def get_llm_last_provider_name(self) -> str:
        """获取上次使用/退出时保存的 LLM provider 名称。"""
        provider = self.get_llm_config().get("last_provider", "")
        return str(provider or "")

    def get_llm_runtime_provider_name(self) -> str:
        """获取运行时应使用的 LLM provider 名称。"""
        current_provider = (
            str(self.get_llm_current_provider_name() or "").strip().lower()
        )
        if current_provider:
            return current_provider
        return str(self.get_llm_last_provider_name() or "").strip().lower()

    def get_llm_provider_config(
        self, provider: str | None = None, *, redacted: bool = False
    ) -> dict[str, Any]:
        """获取可注入 LLM Provider 配置。

        默认返回运行时注入所需原始值；日志、错误、测试快照和能力输出必须使用
        ``redacted=True`` 或 ``safe_all()``，避免 API Key 明文外泄。
        """
        providers = self.get_llm_providers()

        provider_name = (
            str(provider or self.get_llm_runtime_provider_name() or "").strip().lower()
        )
        provider_config = providers.get(provider_name, {})
        if not isinstance(provider_config, dict):
            provider_config = {}

        result = dict(provider_config)
        result["provider"] = provider_name
        return _redact_llm_provider(result) if redacted else result

    def _normalized_llm_providers(self) -> dict[str, dict[str, Any]]:
        """Return provider configs normalized from supported YAML shapes."""
        providers = self.get_llm_config().get("providers", {})
        normalized: dict[str, dict[str, Any]] = {}

        items: list[tuple[Any, Any]] = []
        if isinstance(providers, dict):
            items = list(providers.items())
        elif isinstance(providers, list):
            for index, value in enumerate(providers):
                if isinstance(value, dict):
                    name = (
                        value.get("provider")
                        or value.get("name")
                        or value.get("id")
                        or f"provider_{index}"
                    )
                    items.append((name, value))

        for name, value in items:
            provider_name = str(name or "").strip().lower()
            if not provider_name:
                continue
            provider_config = dict(value) if isinstance(value, dict) else {}
            provider_config["provider"] = (
                str(provider_config.get("provider") or provider_name).strip().lower()
            )
            normalized[provider_name] = provider_config
        return normalized


def _redact_llm_providers(providers: dict[str, Any]) -> dict[str, Any]:
    """Redact LLM provider configs, including secret-looking header names."""
    return {
        str(name): _redact_llm_provider(config) for name, config in providers.items()
    }


def _redact_llm_provider(config: Any) -> Any:
    """Return a secret-safe provider config for CLI/log output."""
    if not isinstance(config, dict):
        return redact_sensitive(config)
    safe = redact_sensitive(dict(config))
    headers = config.get("headers")
    if isinstance(headers, dict):
        safe["headers"] = sanitized_headers(headers)
    return safe
