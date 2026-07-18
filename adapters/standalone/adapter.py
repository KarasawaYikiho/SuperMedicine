"""Standalone 适配器 — 自包含实现，工具方法继承自 BaseAdapter"""

from __future__ import annotations

from typing import Any

from adapters.base_adapter import ADAPTER_HOST_CONFIGS, BaseAdapter


class StandaloneAdapter(BaseAdapter):
    """Standalone 平台适配器 — 无需外部 AI 平台即可运行"""

    DEFAULT_AGENT_ID = "beta"
    HOST_CONFIG = ADAPTER_HOST_CONFIGS["standalone"]

    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        """调用本地工具"""
        handlers = {
            "bash": self._tool_bash,
            "read": self._tool_read,
            "write": self._tool_write,
            "edit": self._tool_edit,
            "glob": self._tool_glob,
            "grep": self._tool_grep,
            "skill": lambda values: self._delegate_tool(values, "skill", "standalone"),
            "task": lambda values: self._delegate_tool(values, "task", "standalone"),
        }
        return self._execute_permissioned_tool_call(
            tool_id=tool_id,
            params=params,
            handlers=handlers,
            unsupported_message=f"Unsupported: {tool_id}",
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
        """进程内模拟子代理分发（非真正子代理）。

        Standalone 适配器没有外部 AI 平台支持，因此 ``subagent_dispatch``
        仅在当前进程内模拟分发行为。返回结果中 ``simulated`` 字段为 ``True``
        ，调用方可据此判断这是模拟而非真正的子代理调度。
        """
        return {
            "agent_id": agent_id,
            "status": "dispatched",
            "platform": "standalone",
            "task": task,
            "simulated": True,
            "message": f"Task dispatched to {agent_id} in standalone mode (simulated, in-process)",
        }
