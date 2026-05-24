import pytest
from typing import Any

from agents.orchestrator import Orchestrator
from agents.base_agent import BaseAgent
from agents.checkpoint import CheckpointManager

class DummyAgent(BaseAgent):
    def __init__(self, agent_id: str, role: str):
        super().__init__(agent_id, role)
        self.executed: list[dict[str, Any]] = []
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        self.executed.append(task)
        return {"status": "ok", "agent": self.agent_id}

class FailingAgent(BaseAgent):
    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("agent boom")

class TestOrchestrator:
    def test_register_and_list(self):
        orch = Orchestrator()
        orch.register_agent(DummyAgent("a", "r"))
        assert len(orch.list_agents()) == 1
    def test_dispatch(self):
        orch = Orchestrator()
        agent = DummyAgent("a", "r")
        orch.register_agent(agent)
        result = orch.dispatch("a", {"action": "test"})
        assert result["status"] == "ok" and len(agent.executed) == 1
    def test_dispatch_unknown_raises(self):
        orch = Orchestrator()
        with pytest.raises(KeyError):
            orch.dispatch("unknown", {})

    def test_dispatch_records_stage_checkpoints(self, tmp_path):
        orch = Orchestrator(checkpoint_manager=CheckpointManager(tmp_path))
        orch.register_agent(DummyAgent("a", "r"))
        result = orch.dispatch("a", {"task_id": "task-1", "action": "test"})
        assert result["state"] == "completed"
        latest = orch.checkpoint_manager.load_latest("task-1")
        assert latest["state"] == "completed"
        assert latest["agent_id"] == "a"
        assert len(latest["stage_history"]) >= 4

    def test_failure_checkpoint_is_not_recoverable(self, tmp_path):
        orch = Orchestrator(checkpoint_manager=CheckpointManager(tmp_path))
        orch.register_agent(FailingAgent("a", "r"))
        with pytest.raises(RuntimeError):
            orch.dispatch("a", {"task_id": "task-fail", "token": "secret"})
        report = orch.recovery_report("task-fail")
        assert report["recoverable"] is False
        assert "manual review" in report["reason"]
        assert report["checkpoint"]["input_summary"]["token"] == "[REDACTED]"
