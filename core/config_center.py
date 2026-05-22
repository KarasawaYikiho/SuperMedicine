"""配置中心"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

class ConfigCenter:
    def __init__(self, config_path: Path):
        self._config_path = Path(config_path)
        self._data: dict[str, Any] = {}
        self._load()
    def _load(self) -> None:
        if self._config_path.exists():
            with open(self._config_path, encoding="utf-8") as f: self._data = yaml.safe_load(f) or {}
    def get(self, key: str, default: Any = None) -> Any: return self._data.get(key, default)
    def set(self, key: str, value: Any) -> None: self._data[key] = value
    def save(self) -> None:
        with open(self._config_path, "w", encoding="utf-8") as f: yaml.dump(self._data, f, allow_unicode=True)
