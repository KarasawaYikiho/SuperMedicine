"""SuperMedicine 微内核 — 集成所有核心组件"""
from __future__ import annotations

from pathlib import Path

from core.config_center import ConfigCenter
from core.event_bus import EventBus
from core.plugin_registry import PluginRegistry
from core.session_manager import SessionManager
from permission.engine import PermissionEngine


class Kernel:
    """SuperMedicine 微内核"""

    def __init__(
        self,
        config_path: Path | None = None,
        plugins_dir: Path | None = None,
        policies_dir: Path | None = None,
    ):
        import os
        # SM_CONFIG 环境变量覆盖配置路径
        if config_path is None:
            env_config = os.environ.get("SM_CONFIG")
            if env_config:
                config_path = Path(env_config)

        self._config_path = config_path or Path(".supermedicine/config.yaml")
        self._plugins_dir = plugins_dir or Path("plugins")
        self._policies_dir = policies_dir or Path(".supermedicine/policies")

        self._config = ConfigCenter(self._config_path)
        self._event_bus = EventBus()
        self._plugin_registry = PluginRegistry(self._plugins_dir)
        self._session_manager = SessionManager()

        # P0 权限引擎集成
        audit_log_path = self._policies_dir / "audit.jsonl"
        self._permission_engine = PermissionEngine(
            self._policies_dir,
            audit_log_path,
        )

    @property
    def config(self) -> ConfigCenter:
        return self._config

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def plugin_registry(self) -> PluginRegistry:
        return self._plugin_registry

    @property
    def session_manager(self) -> SessionManager:
        return self._session_manager

    @property
    def permission_engine(self) -> PermissionEngine:
        """P0 权限引擎 — 双重约束（代码层 + Prompt 层），一票否决制"""
        return self._permission_engine
