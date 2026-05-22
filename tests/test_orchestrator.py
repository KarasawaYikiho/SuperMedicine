import pytest
from agents.orchestrator import Orchestrator
from agents.base_agent import BaseAgent

class DummyAgent(BaseAgent):
    def __init__(self, agent_id: str, role: str):
        super().__init__(agent_id, role)
        self.executed = []
    def execute(self, task: dict) -> dict:
        self.executed.append(task)
        return {"status": "ok", "agent": self.agent_id}

class TestOrchestrator:
    def test_register_and_list(self):
        orch = Orchestrator(); orch.register_agent(DummyAgent("a", "r"))
        assert len(orch.list_agents()) == 1
    def test_dispatch(self):
        orch = Orchestrator(); agent = DummyAgent("a", "r"); orch.register_agent(agent)
        result = orch.dispatch("a", {"action": "test"})
        assert result["status"] == "ok" and len(agent.executed) == 1
    def test_dispatch_unknown_raises(self):
        orch = Orchestrator()
        with pytest.raises(KeyError): orch.dispatch("unknown", {})
