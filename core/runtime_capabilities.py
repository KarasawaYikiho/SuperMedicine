"""Mandatory Harness/RAG runtime capability validation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from core.plugin_registry import PluginRegistry


REQUIRED_RUNTIME_PLUGINS: dict[str, frozenset[str]] = {
    "harness-core": frozenset(
        {
            "harness.runtime.health",
            "harness.integration.checkpoint",
            "harness.integration.checkpoint_all",
            "harness.monitor.permission_audit",
            "harness.monitor.denied_actions",
            "harness.monitor.anomaly",
            "harness.monitor.performance",
            "harness.monitor.failure_patterns",
        }
    ),
    "rag-interface": frozenset(
        {"rag.query", "rag.context.store", "rag.context.retrieve"}
    ),
}


class RuntimeInvariantError(RuntimeError):
    """A stable, serializable failure for a mandatory runtime invariant."""

    def __init__(self, code: str, message: str, details: dict[str, Any]) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Immutable health snapshot shared by runtime entry points."""

    harness_required: bool = True
    rag_required: bool = True
    agent_mode: str = "single"
    rag_index: str = ""
    healthy: bool = True
    diagnostics: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "harness": {
                "required": self.harness_required,
                "healthy": self.healthy,
                "disable_supported": False,
            },
            "rag": {
                "required": self.rag_required,
                "healthy": self.healthy,
                "disable_supported": False,
                "index": self.rag_index,
            },
            "agents": {
                "mode": self.agent_mode,
                "multi_available": True,
            },
            "diagnostics": [dict(item) for item in self.diagnostics],
        }


def validate_required_plugins(
    registry: PluginRegistry, config_path: Path | None = None
) -> RuntimeCapabilities:
    """Ensure mandatory plugin manifests, entries, and actions are available."""
    diagnostics = list(registry.diagnostics())
    duplicate = next(
        (
            item
            for item in diagnostics
            if item.get("code") == "duplicate_plugin_name"
            and item.get("plugin") in REQUIRED_RUNTIME_PLUGINS
        ),
        None,
    )
    if duplicate is not None:
        raise RuntimeInvariantError(
            "duplicate_plugin_name",
            f"Required runtime plugin name is duplicated: {duplicate['plugin']}",
            {"plugin": duplicate["plugin"]},
        )
    for plugin_name, required_actions in REQUIRED_RUNTIME_PLUGINS.items():
        meta = registry.get_meta(plugin_name)
        plugin = registry.get(plugin_name)
        if meta is None or plugin is None:
            raise RuntimeInvariantError(
                "required_plugin_missing",
                f"Required runtime plugin is unavailable: {plugin_name}",
                {"plugin": plugin_name},
            )
        if not meta.required or meta.disable_supported:
            raise RuntimeInvariantError(
                "required_plugin_manifest_invalid",
                f"Required runtime plugin manifest is not mandatory: {plugin_name}",
                {
                    "plugin": plugin_name,
                    "required": meta.required,
                    "disable_supported": meta.disable_supported,
                },
            )
        entry_path = plugin.plugin_dir / meta.entry
        if not entry_path.is_file():
            raise RuntimeInvariantError(
                "required_plugin_entry_missing",
                f"Required runtime plugin entry is unavailable: {plugin_name}",
                {"plugin": plugin_name, "entry": meta.entry},
            )
        try:
            compile(entry_path.read_text(encoding="utf-8"), str(entry_path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise RuntimeInvariantError(
                "required_plugin_import_error",
                f"Required runtime plugin entry cannot be imported: {plugin_name}",
                {"plugin": plugin_name, "reason": type(exc).__name__},
            ) from exc
        provided_actions = {
            str(item.get("id"))
            for item in meta.provides
            if isinstance(item, dict) and item.get("id")
        }
        missing_actions = sorted(required_actions - provided_actions)
        if missing_actions:
            raise RuntimeInvariantError(
                "required_plugin_action_missing",
                f"Required runtime plugin actions are unavailable: {plugin_name}",
                {"plugin": plugin_name, "actions": missing_actions},
            )
    if config_path is not None and Path(config_path).is_file():
        try:
            config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        except (OSError, UnicodeError, yaml.YAMLError):
            config = {}
        if isinstance(config, dict):
            for section in ("harness", "rag"):
                values = config.get(section)
                if isinstance(values, dict) and values.get("enabled") is False:
                    diagnostics.append(
                        {
                            "code": "invalid_disable_request",
                            "plugin": section,
                            "message": f"{section}.enabled=false is ignored",
                        }
                    )
    return RuntimeCapabilities(diagnostics=tuple(diagnostics))


def required_runtime_snapshot(project_dir: Path) -> dict[str, Any]:
    """Build the shared mandatory runtime health snapshot for every interface."""
    from core.config_center import ConfigCenter

    root = Path(project_dir).resolve()
    config_path = root / ".supermedicine" / "config.yaml"
    config = ConfigCenter(config_path)
    registry = PluginRegistry(root / "plugins", allow_package_fallback=True)
    registry.discover()
    try:
        capabilities = validate_required_plugins(registry, config_path)
    except RuntimeInvariantError as exc:
        return {
            "harness": {
                "required": True,
                "healthy": False,
                "disable_supported": False,
            },
            "rag": {
                "required": True,
                "healthy": False,
                "disable_supported": False,
                "index": "",
            },
            "agents": {"mode": "single", "multi_available": True},
            "diagnostics": [exc.to_dict()],
        }
    capabilities = replace(
        capabilities,
        agent_mode=(
            "multi" if config.get_multi_agent_config()["enabled"] else "single"
        ),
        rag_index=str(root / ".supermedicine" / "rag" / "local"),
    )
    return capabilities.to_dict()
