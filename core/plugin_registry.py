"""插件注册中心"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from plugins.base_plugin import BasePlugin, PluginMeta


class PluginRegistry:
    """Discovers plugin metadata and returns BasePlugin contract adapters.

    Registry only discovers and instantiates plugins. It does not execute plugins
    or check permissions; production execution must flow through Kernel so the
    canonical PermissionEngine path cannot be bypassed accidentally by CLI code.
    """

    def __init__(self, plugins_dir: Path):
        self._plugins_dir = Path(plugins_dir)
        self._metas: dict[str, PluginMeta] = {}
        self._plugins: dict[str, BasePlugin] = {}
        self._diagnostics: list[dict[str, Any]] = []

    def discover(self) -> list[PluginMeta]:
        found = []
        self._metas = {}
        self._plugins = {}
        self._diagnostics = []
        plugins_dir = self._discovery_root()
        if plugins_dir is None:
            return []
        for yml in plugins_dir.rglob("plugin.yaml"):
            try:
                with open(yml, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or "name" not in data:
                    continue
                meta = PluginMeta.from_dict(data)
            except Exception as exc:
                self._diagnostics.append(
                    {"status": "skipped", "manifest": str(yml), "error": str(exc)}
                )
                continue
            if meta.name in self._metas:
                self._diagnostics.append(
                    {
                        "status": "failed",
                        "code": "duplicate_plugin_name",
                        "manifest": str(yml),
                        "plugin": meta.name,
                    }
                )
                continue
            self._metas[meta.name] = meta
            self._plugins[meta.name] = BasePlugin(meta, yml.parent)
            found.append(meta)
        return found

    def _discovery_root(self) -> Path | None:
        """Prefer an explicit source tree, then fall back to Wheel resources."""
        if self._plugins_dir.is_dir():
            return self._plugins_dir
        try:
            package_root = Path(str(resources.files("plugins")))
        except (ModuleNotFoundError, TypeError):
            return None
        return package_root if package_root.is_dir() else None

    def diagnostics(self) -> list[dict[str, Any]]:
        return list(self._diagnostics)

    def get_meta(self, name: str) -> PluginMeta | None:
        return self._metas.get(name)

    def get(self, name: str) -> BasePlugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginMeta]:
        return list(self._metas.values())
