"""配置中心 — YAML 配置管理，支持 SM_* 环境变量覆盖"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from core.redaction import redact_sensitive


class ConfigCenter:
    """配置管理中心"""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._config: dict[str, Any] = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

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

    def get_llm_provider_config(self, provider: str | None = None, *, redacted: bool = False) -> dict[str, Any]:
        """获取可注入 LLM Provider 配置。

        默认返回运行时注入所需原始值；日志、错误、测试快照和能力输出必须使用
        ``redacted=True`` 或 ``safe_all()``，避免 API Key 明文外泄。
        """
        llm_config = self._config.get("llm", {})
        if not isinstance(llm_config, dict):
            llm_config = {}
        providers = llm_config.get("providers", {})
        if not isinstance(providers, dict):
            providers = {}

        provider_name = provider or llm_config.get("provider") or "openai"
        provider_config = providers.get(provider_name, {})
        if not isinstance(provider_config, dict):
            provider_config = {}

        result = dict(provider_config)
        result["provider"] = provider_name
        return redact_sensitive(result) if redacted else result
