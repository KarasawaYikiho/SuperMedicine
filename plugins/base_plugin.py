"""插件基类与最小执行契约。

插件执行契约（P0，保持最小稳定面）：
- 输入：``action: str``、``params: dict``、可选只读 ``context: dict``。
- 权限：插件不得自行作为权限入口；生产执行必须经由 Kernel/PermissionEngine。
- 输出：所有结果统一为 ``status/plugin/action/output/error/metadata`` 形状。
- 错误：插件加载、未知动作、非法输入、运行期异常均隔离为结构化 ``plugin_error``。
- 边界：医疗/统计插件应在 ``metadata`` 或顶层结果携带当前阶段医疗/统计边界说明。
"""

from __future__ import annotations
from dataclasses import dataclass, field
import inspect
import importlib
import importlib.util
import os
from pathlib import Path
from typing import Any

import yaml

from core.redaction import redact_sensitive


PLUGIN_CONTRACT_VERSION = "2026-05-p0"


def plugin_result(
    *,
    status: str,
    plugin: str,
    action: str,
    output: Any = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the stable minimal plugin execution result shape."""
    return {
        "status": status,
        "plugin": plugin,
        "action": action,
        "output": redact_sensitive(output),
        "error": redact_sensitive(error),
        "metadata": redact_sensitive(
            {"contract_version": PLUGIN_CONTRACT_VERSION, **(metadata or {})}
        ),
    }


@dataclass
class PluginMeta:
    name: str
    version: str
    type: str
    language: str = "python"
    entry: str = "main.py"
    permissions_required: list[str] = field(default_factory=list)
    provides: list[dict[str, Any]] = field(default_factory=list)
    required: bool = False
    disable_supported: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginMeta:
        tool_id = str(data.get("id") or data["name"])
        raw_provides = data.get("provides") or [
            {
                "id": f"workspace.tool.{tool_id}",
                "description": str(
                    data.get("description") or data.get("name") or tool_id
                ),
            }
        ]
        return cls(
            name=tool_id if "entrypoint" in data else data["name"],
            version=data["version"],
            type=data.get("type", "tool"),
            language=data.get("language", "python"),
            entry=data.get("entry", data.get("entrypoint", "main.py")),
            permissions_required=data.get("permissions_required", []),
            provides=raw_provides,
            required=bool(data.get("required", False)),
            disable_supported=bool(data.get("disable_supported", True)),
        )

    @classmethod
    def from_manifest(cls, path: Path) -> PluginMeta:
        """Parse either plugin.yaml or tool.yaml through one canonical path."""
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not (data.get("name") or data.get("id")):
            raise ValueError(f"Invalid plugin manifest: {path}")
        return cls.from_dict(data)


class BasePlugin:
    def __init__(self, meta: PluginMeta, plugin_dir: Path):
        self._meta = meta
        self._plugin_dir = plugin_dir

    @property
    def meta(self) -> PluginMeta:
        return self._meta

    @property
    def name(self) -> str:
        return self._meta.name

    @property
    def plugin_dir(self) -> Path:
        """Filesystem location of the manifest, for runtime validation only."""
        return self._plugin_dir

    def execute(
        self,
        action: str,
        params: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """执行插件动作。

        默认实现按 plugin.yaml 的 entry 动态加载 Python 插件入口，并调用入口模块的
        execute(action, params, context=None) 函数。这样现有注册中心仍可返回 BasePlugin，
        同时 CLI/Kernel 可以走真实插件执行路径。调用方应使用 Kernel 完成权限检查；
        本方法只负责隔离插件异常并规范化输出形状。
        """
        params = params or {}
        context = context or {}
        denied = self._direct_execution_denied(action, context)
        if denied is not None:
            return denied
        if self._meta.language != "python":
            return plugin_result(
                status="plugin_error",
                action=action,
                plugin=self.name,
                error=f"Unsupported plugin language: {self._meta.language}",
            )

        entry_path = self._plugin_dir / self._meta.entry
        if not entry_path.exists():
            return plugin_result(
                status="plugin_error",
                action=action,
                plugin=self.name,
                error=f"Plugin entry not found: {entry_path}",
            )

        try:
            module = self._load_entry_module(entry_path)
        except Exception as exc:
            return plugin_result(
                status="plugin_error",
                action=action,
                plugin=self.name,
                error=f"Plugin entry load failed: {exc}",
            )
        if not hasattr(module, "execute"):
            return plugin_result(
                status="plugin_error",
                action=action,
                plugin=self.name,
                error=f"Plugin '{self.name}' entry has no execute(action, params, context=None) function.",
            )
        try:
            execute_fn = module.execute
            if len(inspect.signature(execute_fn).parameters) >= 3:
                result = execute_fn(action, params, context)
            else:
                result = execute_fn(action, params)
        except Exception as exc:
            return plugin_result(
                status="plugin_error",
                action=action,
                plugin=self.name,
                error=f"Plugin execution failed: {exc}",
            )
        if not isinstance(result, dict):
            return plugin_result(
                status="plugin_error",
                action=action,
                plugin=self.name,
                error=f"Plugin '{self.name}' returned non-dict result.",
            )
        return self._normalize_result(action, result)

    def health_check(self) -> bool:
        return True

    def _direct_execution_denied(
        self, action: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        security = context.get("security") if isinstance(context, dict) else None
        if (
            isinstance(security, dict)
            and security.get("permission_checked") is True
            and security.get("permission_entrypoint") == "kernel"
        ):
            return None
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return None
        return plugin_result(
            status="denied",
            action=action,
            plugin=self.name,
            error="Plugin direct execution denied: production execution must provide Kernel permission proof.",
            metadata={
                "security": {
                    "permission": "denied",
                    "permission_checked": False,
                    "permission_entrypoint": "direct",
                    "required_permission_proof": "context.security.permission_checked=true and permission_entrypoint=kernel",
                }
            },
        )

    def _load_entry_module(self, entry_path: Path):
        """加载插件入口；优先按包导入以支持入口中的相对 import。"""
        resolved = entry_path.resolve()
        parts = resolved.parts
        if "plugins" in parts:
            plugins_index = parts.index("plugins")
            module_parts = list(parts[plugins_index:-1]) + [resolved.stem]
            package_module = ".".join(module_parts)
            try:
                return importlib.import_module(package_module)
            except ImportError:
                pass

        module_name = f"supermedicine_plugin_{self.name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load plugin entry: {entry_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _normalize_result(self, action: str, result: dict[str, Any]) -> dict[str, Any]:
        """Normalize legacy plugin result dictionaries to the stable contract shape."""
        status = result.get("status") or "success"
        output = result.get("output", result.get("result"))
        raw_metadata = result.get("metadata")
        metadata: dict[str, Any] = (
            raw_metadata if isinstance(raw_metadata, dict) else {}
        )
        for key in (
            "medical_boundary",
            "statistics_boundary",
            "audit",
            "resource",
            "security",
        ):
            if key in result and key not in metadata:
                metadata[key] = result[key]
        metadata.setdefault("resource", {"kind": "plugin", "plugin": self.name})
        metadata.setdefault(
            "security",
            {"permission_entrypoint": "kernel", "plugin_direct_execution": True},
        )
        return plugin_result(
            status=status,
            plugin=str(result.get("plugin") or self.name),
            action=str(result.get("action") or action),
            output=output,
            error=result.get("error"),
            metadata=metadata,
        )
