"""SuperMedicine 微内核"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import sys

from core import log_report_models as _log_report_models
from core import workspace_tool_spec as _workspace_tool_spec
from permission import redaction as _redaction

_COMPAT_MODULES = {
    "core.workspace_tool_templates": _workspace_tool_spec,
    "core.log_severity": _log_report_models,
    "core.redaction": _redaction,
}
for _module_name, _module in _COMPAT_MODULES.items():
    sys.modules.setdefault(_module_name, _module)

if TYPE_CHECKING:
    from core.config_center import ConfigCenter
    from core.database import Database, SessionRepository, AgentRepository
    from core.effect import Effect
    from core.event_bus import EventBus
    from core.kernel import Kernel
    from core.llm_client import LLMClient
    from core.plugin_registry import PluginRegistry
    from core.session_manager import SessionManager
    from core.workspace import WorkspaceManager

    def create_llm_client(*args: Any, **kwargs: Any) -> LLMClient: ...


_EXPORTS: dict[str, tuple[str, str]] = {
    "Kernel": ("core.kernel", "Kernel"),
    "ConfigCenter": ("core.config_center", "ConfigCenter"),
    "Database": ("core.database", "Database"),
    "SessionRepository": ("core.database", "SessionRepository"),
    "AgentRepository": ("core.database", "AgentRepository"),
    "Effect": ("core.effect", "Effect"),
    "EventBus": ("core.event_bus", "EventBus"),
    "PluginRegistry": ("core.plugin_registry", "PluginRegistry"),
    "SessionManager": ("core.session_manager", "SessionManager"),
    "LLMClient": ("core.llm_client", "LLMClient"),
    "create_llm_client": ("core.llm_client", "create_llm_client"),
    "WorkspaceManager": ("core.workspace", "WorkspaceManager"),
}


def __getattr__(name: str) -> Any:
    """Lazily expose public core symbols without eager permission imports."""

    if name not in _EXPORTS:
        raise AttributeError(f"module 'core' has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "Kernel",
    "ConfigCenter",
    "Database",
    "SessionRepository",
    "AgentRepository",
    "Effect",
    "EventBus",
    "PluginRegistry",
    "SessionManager",
    "LLMClient",
    "create_llm_client",
    "WorkspaceManager",
]
