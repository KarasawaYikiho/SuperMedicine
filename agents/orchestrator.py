"""Orchestrator"""
from __future__ import annotations
from typing import Any
from .base_agent import BaseAgent

class Orchestrator:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.agent_id] = agent
    def get_agent(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)
    def list_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())
    def dispatch(self, agent_id: str, task: dict[str, Any]) -> dict[str, Any]:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Unknown agent: {agent_id}")
        return agent.execute(task)
