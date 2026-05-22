"""平台适配器基类"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BaseAdapter(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str: ...
    @abstractmethod
    def tool_call(self, tool_id: str, params: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def skill_load(self, skill_name: str) -> str: ...
    @abstractmethod
    def subagent_dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]: ...
