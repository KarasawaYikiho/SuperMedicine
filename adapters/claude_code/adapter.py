"""Claude Code 适配器"""
from __future__ import annotations
from typing import Any
from adapters.base_adapter import BaseAdapter

class ClaudeCodeAdapter(BaseAdapter):
    @property
    def platform_name(self) -> str: return "claude-code"
    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]: raise NotImplementedError
    def skill_load(self, skill_name: str) -> str: raise NotImplementedError
    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]: raise NotImplementedError
