"""Claude Code 适配器 (Coming Soon)"""
from __future__ import annotations
from typing import Any
from adapters.base_adapter import BaseAdapter

class ClaudeCodeAdapter(BaseAdapter):
    """Claude Code 平台适配器 — 计划中，即将支持"""

    @property
    def platform_name(self) -> str:
        return "claude-code"

    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "coming_soon",
            "tool": tool_id,
            "message": "Claude Code adapter is not yet implemented. Coming in a future release.",
        }

    def skill_load(self, skill_name: str) -> str:
        return f"[Coming Soon] Claude Code skill '{skill_name}' — adapter not yet implemented."

    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent_id": agent_id,
            "status": "coming_soon",
            "message": "Claude Code subagent dispatch is not yet implemented. Coming in a future release.",
        }
