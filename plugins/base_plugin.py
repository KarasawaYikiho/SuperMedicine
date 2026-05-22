"""插件基类"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class PluginMeta:
    name: str
    version: str
    type: str
    language: str = "python"
    entry: str = "main.py"
    permissions_required: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginMeta:
        return cls(name=data["name"], version=data["version"], type=data["type"], language=data.get("language", "python"), entry=data.get("entry", "main.py"), permissions_required=data.get("permissions_required", []), provides=data.get("provides", []))

class BasePlugin:
    def __init__(self, meta: PluginMeta, plugin_dir: Path):
        self._meta = meta
        self._plugin_dir = plugin_dir
    @property
    def meta(self) -> PluginMeta: return self._meta
    @property
    def name(self) -> str: return self._meta.name
    def execute(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """执行插件动作（子类可重写）"""
        return {
            "status": "not_implemented",
            "action": action,
            "plugin": self.name,
            "message": f"Plugin '{self.name}' has no custom execute() implementation. Override in subclass.",
        }
    def health_check(self) -> bool: return True
