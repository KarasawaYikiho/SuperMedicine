"""Agent 基类"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class BaseAgent(ABC):
    def __init__(self, agent_id: str, role: str):
        self._agent_id = agent_id
        self._role = role
    @property
    def agent_id(self) -> str: return self._agent_id
    @property
    def role(self) -> str: return self._role
    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]: ...
