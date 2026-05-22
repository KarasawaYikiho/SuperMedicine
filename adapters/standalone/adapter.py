"""Standalone 适配器 — 自包含实现，工具方法继承自 BaseAdapter"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.base_adapter import BaseAdapter


class StandaloneAdapter(BaseAdapter):
    """Standalone 平台适配器 — 无需外部 AI 平台即可运行"""

    @property
    def platform_name(self) -> str:
        return "standalone"

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
        handler = handlers.get(tool_id)
        if handler is None:
            return {"status": "error", "tool": tool_id, "result": f"Unsupported: {tool_id}"}
        try:
            result = handler(params)
            return {"status": "ok", "tool": tool_id, "result": result}
        except Exception as e:
            return {"status": "error", "tool": tool_id, "result": str(e)}

    def _tool_skill(self, params: dict[str, Any]) -> str:
        return self.skill_load(params.get("name", ""))

    def _tool_task(self, params: dict[str, Any]) -> dict[str, Any]:
        agent_id = params.get("agent_id", "standalone")
        task = params.get("task", params.get("prompt", ""))
        return self.subagent_dispatch(agent_id, task if isinstance(task, dict) else {"description": task})

    def skill_load(self, skill_name: str) -> str:
        """从本地加载技能文件"""
        adapter_dir = Path(__file__).parent.parent
        skill_path = adapter_dir / "opencode" / "skills" / f"{skill_name}.md"
        if skill_path.exists():
            return skill_path.read_text(encoding="utf-8")
        return f"Skill not found: {skill_name}"

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        """进程内模拟 Dispatch"""
        return {
            "agent_id": agent_id,
            "status": "dispatched",
            "platform": "standalone",
            "task": task,
            "message": f"Task dispatched to {agent_id} in standalone mode",
        }
