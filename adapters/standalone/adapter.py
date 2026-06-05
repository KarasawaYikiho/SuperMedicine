"""Standalone 适配器 — 自包含实现，工具方法继承自 BaseAdapter"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.base_adapter import BaseAdapter
from permission.engine import PermissionEngine


class StandaloneAdapter(BaseAdapter):
    """Standalone 平台适配器 — 无需外部 AI 平台即可运行"""

    def __init__(
        self,
        permission_engine: PermissionEngine | None = None,
        project_dir: Path | None = None,
        default_agent_id: str = "beta",
    ):
        super().__init__(
            permission_engine=permission_engine,
            project_dir=project_dir,
            default_agent_id=default_agent_id,
        )

    @property
    def platform_name(self) -> str:
        return "standalone"

    @property
    def registration(self) -> dict[str, Any]:
        """Return adapter discovery metadata for registries and callers."""
        return {
            "platform": self.platform_name,
            "adapter_class": self.__class__.__name__,
            "status": "core_default",
            "optional": False,
            "core": True,
            "default": True,
            "module": "adapters.standalone.adapter",
            "capability_tool": None,
            "requires_core_runtime": True,
            "limitations": [
                "Self-contained core adapter; does not load OpenCode or Claude Code platform resources.",
                "Skill loading returns core-neutral metadata instead of platform skill files.",
            ],
        }

    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """调用本地工具"""
        handlers = {
            "bash": self._tool_bash,
            "read": self._tool_read,
            "write": self._tool_write,
            "edit": self._tool_edit,
            "glob": self._tool_glob,
            "grep": self._tool_grep,
            "skill": self._tool_skill,
            "task": self._tool_task,
        }
        return self._execute_permissioned_tool_call(
            tool_id=tool_id,
            params=params,
            handlers=handlers,
            unsupported_message=f"Unsupported: {tool_id}",
        )

    def _tool_skill(self, params: dict[str, Any]) -> str:
        return self.skill_load(params.get("name", ""))

    def _tool_task(self, params: dict[str, Any]) -> dict[str, Any]:
        agent_id = params.get("agent_id", "standalone")
        task = params.get("task", params.get("prompt", ""))
        return self.subagent_dispatch(
            agent_id, task if isinstance(task, dict) else {"description": task}
        )

    def skill_load(self, skill_name: str) -> str:
        """Return standalone skill metadata without depending on OpenCode files."""
        if not skill_name:
            return "Standalone skill name is required."
        return (
            f"Standalone skill '{skill_name}' is not backed by a platform skill file. "
            "Use Kernel/plugin actions directly for core SuperMedicine workflows; "
            "OpenCode skill documents are available only through the optional OpenCode adapter."
        )

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """进程内模拟 Dispatch"""
        return {
            "agent_id": agent_id,
            "status": "dispatched",
            "platform": "standalone",
            "task": task,
            "message": f"Task dispatched to {agent_id} in standalone mode",
        }
