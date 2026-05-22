"""配置中心 — YAML 配置管理，支持 SM_* 环境变量覆盖"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class ConfigCenter:
    """配置管理中心"""

    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._config: dict[str, Any] = {}
        if config_path.exists():
            import yaml
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

    def all(self) -> dict[str, Any]:
        """获取全部配置（合并环境变量覆盖）"""
        result = dict(self._config)
        for env_key, env_val in os.environ.items():
            if env_key.startswith("SM_"):
                config_key = env_key[3:].lower().replace("_", "-")
                result[config_key] = env_val
        return result
