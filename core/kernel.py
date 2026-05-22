"""微内核"""
from __future__ import annotations
from pathlib import Path
from .config_center import ConfigCenter
from .event_bus import EventBus
from .plugin_registry import PluginRegistry
from .session_manager import SessionManager

class Kernel:
    def __init__(self, config_path: Path, plugins_dir: Path, policies_dir: Path):
        self._config = ConfigCenter(config_path)
        self._event_bus = EventBus()
        self._plugin_registry = PluginRegistry(plugins_dir)
        self._session_manager = SessionManager()
        self._plugin_registry.discover()
    @property
    def config(self) -> ConfigCenter: return self._config
    @property
    def event_bus(self) -> EventBus: return self._event_bus
    @property
    def plugin_registry(self) -> PluginRegistry: return self._plugin_registry
    @property
    def session_manager(self) -> SessionManager: return self._session_manager
