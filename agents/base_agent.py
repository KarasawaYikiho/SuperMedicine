"""Agent 基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class for all agents in the orchestration system."""

    def __init__(self, agent_id: str, role: str):
        self._agent_id = agent_id
        self._role = role

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> str:
        return self._role

    def describe_state(self) -> dict[str, Any]:
        return {"agent_id": self._agent_id, "role": self._role, "status": "registered"}

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]: ...
