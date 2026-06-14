"""Merged tests: agent unit tests, orchestrator tests, and state machine tests."""

from __future__ import annotations

import pytest
from typing import Any

from agents.alpha_agent import AlphaAgent
from agents.beta_agent import BetaAgent
from agents.gamma_agent import GammaAgent
from agents.delta_agent import DeltaAgent
from agents.orchestrator import Orchestrator
from agents.base_agent import BaseAgent
from agents.checkpoint import CheckpointManager
from agents.state_machine import TaskState, StateMachine


# ═══ Agent Unit Tests ═══


class TestAlphaAgent:
    """Tests for AlphaAgent (Analyst — planning and requirements analysis)."""

    def test_agent_id_and_role(self):
        agent = AlphaAgent()
        assert agent.agent_id == "alpha"
        assert agent.role == "analyst"

    def test_execute_basic_task(self):
        agent = AlphaAgent()
        result = agent.execute({"task": "Build a REST API for user management"})
        assert "analysis" in result
        assert "requirements" in result
        assert "complexity" in result
        assert "recommendations" in result

    def test_execute_with_description_key(self):
        agent = AlphaAgent()
        result = agent.execute({"description": "Create a login form"})
        assert result["analysis"]["input_description"] == "Create a login form"

    def test_execute_with_action_key(self):
        agent = AlphaAgent()
        result = agent.execute({"action": "Analyze data pipeline"})
        assert "pipeline" in result["analysis"]["input_description"].lower()

    def test_execute_empty_task(self):
        agent = AlphaAgent()
        result = agent.execute({})
        assert result["analysis"]["input_description"] == ""
        assert result["complexity"] == "low"
        # Should still have recommendations (including the empty-description warning)
        assert len(result["recommendations"]) > 0
        assert any("empty" in r.lower() for r in result["recommendations"])

    def test_execute_extracts_requirements(self):
        agent = AlphaAgent()
        result = agent.execute({"task": "First requirement. Second requirement."})
        reqs = result["requirements"]
        assert len(reqs) >= 2
        assert reqs[0]["id"] == "REQ-001"
        assert reqs[1]["id"] == "REQ-002"

    def test_execute_with_context_requirements(self):
        agent = AlphaAgent()
        result = agent.execute(
            {
                "task": "Main task",
                "context": {"requirements": ["extra req 1", "extra req 2"]},
            }
        )
        sources = [r["source"] for r in result["requirements"]]
        assert "context" in sources

    def test_complexity_low_for_simple_task(self):
        agent = AlphaAgent()
        result = agent.execute({"task": "Say hello"})
        assert result["complexity"] == "low"

    def test_complexity_high_for_complex_keywords(self):
        agent = AlphaAgent()
        result = agent.execute(
            {
                "task": (
                    "Build a multi-agent integration pipeline with security "
                    "permission compliance for distributed systems"
                )
            }
        )
        assert result["complexity"] == "high"

    def test_execute_with_domain_and_priority(self):
        agent = AlphaAgent()
        result = agent.execute(
            {"task": "Analyze dataset", "domain": "bioinformatics", "priority": "high"}
        )
        assert result["analysis"]["domain"] == "bioinformatics"
        assert result["analysis"]["priority"] == "high"

    def test_extract_constraints(self):
        agent = AlphaAgent()
        result = agent.execute(
            {"task": "The system must handle errors. Users shall authenticate."}
        )
        constraints = result["analysis"]["constraint_keywords"]
        assert "must" in constraints
        assert "shall" in constraints

    def test_describe_state(self):
        agent = AlphaAgent()
        state = agent.describe_state()
        assert state["agent_id"] == "alpha"
        assert state["role"] == "analyst"


class TestBetaAgent:
    """Tests for BetaAgent (Reviewer — verification and review)."""

    def test_agent_id_and_role(self):
        agent = BetaAgent()
        assert agent.agent_id == "beta"
        assert agent.role == "reviewer"

    def test_execute_approves_clean_task(self):
        agent = BetaAgent()
        result = agent.execute(
            {"task": "Write a Python function", "requirements": []}
        )
        assert result["approved"] is True
        assert result["issues"] == []
        assert "passed" in result["feedback"].lower()

    def test_execute_with_analysis_and_requirements(self):
        agent = BetaAgent()
        result = agent.execute(
            {
                "task": "Implement authentication",
                "requirements": [
                    {"id": "REQ-001", "text": "Must support OAuth2"},
                ],
            }
        )
        assert "review" in result
        assert "completeness" in result["review"]
        assert "correctness" in result["review"]
        assert "medical_boundary" in result["review"]
        assert "safety" in result["review"]

    def test_completeness_warning_on_empty_task(self):
        agent = BetaAgent()
        result = agent.execute({})
        warning_issues = [
            i for i in result["issues"] if i.get("severity") == "warning"
        ]
        assert len(warning_issues) >= 1
        assert any("completeness" in i["check"] for i in warning_issues)

    def test_medical_boundary_blocks_diagnose(self):
        agent = BetaAgent()
        result = agent.execute({"task": "Diagnose the patient with flu"})
        assert result["approved"] is False
        blocking = [i for i in result["issues"] if i.get("severity") == "blocking"]
        assert any("medical_boundary" in i["check"] for i in blocking)

    def test_medical_boundary_blocks_prescribe(self):
        agent = BetaAgent()
        result = agent.execute({"task": "Prescribe medication for headache"})
        assert result["approved"] is False

    def test_medical_boundary_blocks_chinese_markers(self):
        agent = BetaAgent()
        result = agent.execute({"task": "给出医嘱和处方"})
        assert result["approved"] is False

    def test_safety_warning_on_embedded_secret(self):
        agent = BetaAgent()
        result = agent.execute(
            {"task": "Connect to api_key=sk-secret123 and fetch data"}
        )
        safety_issues = [
            i
            for i in result["issues"]
            if i["check"] == "safety" and i["severity"] == "warning"
        ]
        assert len(safety_issues) >= 1

    def test_correctness_blocks_non_list_requirements(self):
        agent = BetaAgent()
        result = agent.execute(
            {"task": "Test", "requirements": "not a list"}
        )
        blocking = [i for i in result["issues"] if i.get("severity") == "blocking"]
        assert any("correctness" in i["check"] for i in blocking)

    def test_correctness_warns_on_non_dict_requirement_items(self):
        agent = BetaAgent()
        result = agent.execute(
            {"task": "Test", "requirements": ["string_item", 42]}
        )
        warnings = [
            i for i in result["issues"] if i.get("severity") == "warning"
        ]
        assert any("correctness" in i["check"] for i in warnings)

    def test_flatten_text_recurses_nested(self):
        agent = BetaAgent()
        result = agent.execute(
            {
                "task": "Outer",
                "context": {"detail": "Inner detail"},
                "items": ["item1", "item2"],
            }
        )
        # The agent should process without error even with nested structures
        assert "review" in result

    def test_describe_state(self):
        agent = BetaAgent()
        state = agent.describe_state()
        assert state["agent_id"] == "beta"
        assert state["role"] == "reviewer"


class TestGammaAgent:
    """Tests for GammaAgent (Writer — drafting and content generation)."""

    def test_agent_id_and_role(self):
        agent = GammaAgent()
        assert agent.agent_id == "gamma"
        assert agent.role == "writer"

    def test_execute_generates_content(self):
        agent = GammaAgent()
        result = agent.execute({"task": "Write a summary of the project"})
        assert "content" in result
        assert "format" in result
        assert "metadata" in result
        assert len(result["content"]) > 0

    def test_execute_with_description_key(self):
        agent = GammaAgent()
        result = agent.execute({"description": "Create documentation"})
        assert "documentation" in result["content"].lower()

    def test_execute_with_content_key(self):
        agent = GammaAgent()
        result = agent.execute({"content": "Generate a report"})
        assert "report" in result["content"].lower()

    def test_execute_default_format_is_markdown(self):
        agent = GammaAgent()
        result = agent.execute({"task": "Write something"})
        assert result["format"] == "markdown"

    def test_execute_custom_format(self):
        agent = GammaAgent()
        result = agent.execute({"task": "Write something", "format": "html"})
        assert result["format"] == "html"

    def test_execute_with_requirements(self):
        agent = GammaAgent()
        result = agent.execute(
            {
                "task": "Build login page",
                "requirements": [
                    {"id": "REQ-001", "text": "Must have username field", "priority": "high"},
                    {"id": "REQ-002", "text": "Must have password field", "priority": "high"},
                ],
            }
        )
        assert "REQ-001" in result["content"]
        assert "REQ-002" in result["content"]
        assert result["metadata"]["input_requirements_count"] == 2

    def test_execute_with_analysis(self):
        agent = GammaAgent()
        result = agent.execute(
            {
                "task": "Implement feature",
                "analysis": {"complexity": "high", "domain": "backend"},
            }
        )
        assert "high" in result["content"]
        assert "backend" in result["content"]
        assert result["metadata"]["complexity"] == "high"

    def test_execute_with_context(self):
        agent = GammaAgent()
        result = agent.execute(
            {
                "task": "Write docs",
                "context": {"audience": "developers", "language": "Python"},
            }
        )
        assert "developers" in result["content"]
        assert "Python" in result["content"]
        assert result["metadata"]["has_context"] is True

    def test_execute_empty_input(self):
        agent = GammaAgent()
        result = agent.execute({})
        assert "content" in result
        # Fallback message
        assert "no structured content" in result["content"].lower()

    def test_metadata_generator_field(self):
        agent = GammaAgent()
        result = agent.execute({"task": "Test"})
        assert result["metadata"]["generator"] == "gamma"

    def test_describe_state(self):
        agent = GammaAgent()
        state = agent.describe_state()
        assert state["agent_id"] == "gamma"
        assert state["role"] == "writer"


class TestDeltaAgent:
    """Tests for DeltaAgent (Orchestrator — routing and coordination)."""

    def test_agent_id_and_role(self):
        agent = DeltaAgent()
        assert agent.agent_id == "delta"
        assert agent.role == "orchestrator"

    def test_execute_returns_routing_decision(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Analyze the data"})
        assert "route" in result
        assert "target_agent" in result
        assert "context" in result

    def test_auto_route_analyze_to_alpha(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Analyze the requirements"})
        assert result["target_agent"] == "alpha"

    def test_auto_route_plan_to_alpha(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Plan the implementation"})
        assert result["target_agent"] == "alpha"

    def test_auto_route_review_to_beta(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Review the code changes"})
        assert result["target_agent"] == "beta"

    def test_auto_route_verify_to_beta(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Verify the output"})
        assert result["target_agent"] == "beta"

    def test_auto_route_write_to_gamma(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Write the documentation"})
        assert result["target_agent"] == "gamma"

    def test_auto_route_draft_to_gamma(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Draft a summary report"})
        assert result["target_agent"] == "gamma"

    def test_auto_route_generate_to_gamma(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Generate content for the page"})
        assert result["target_agent"] == "gamma"

    def test_auto_route_default_to_alpha(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Do something random"})
        assert result["target_agent"] == "alpha"
        assert "default" in result["route"].lower()

    def test_explicit_target_override(self):
        agent = DeltaAgent()
        result = agent.execute(
            {"task": "Write docs", "target_agent": "beta"}
        )
        assert result["target_agent"] == "beta"
        assert "override" in result["route"].lower()

    def test_explicit_target_invalid_falls_back_to_auto(self):
        agent = DeltaAgent()
        result = agent.execute(
            {"task": "Write docs", "target_agent": "omega"}
        )
        # "omega" is not a valid target, so auto-route should kick in
        assert result["target_agent"] == "gamma"  # "write" keyword

    def test_phase_based_routing_analysis(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Do stuff", "phase": "analysis"})
        assert result["target_agent"] == "alpha"
        assert "analysis" in result["route"].lower()

    def test_phase_based_routing_review(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Do stuff", "phase": "review"})
        assert result["target_agent"] == "beta"
        assert "review" in result["route"].lower()

    def test_phase_based_routing_writing(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Do stuff", "phase": "writing"})
        assert result["target_agent"] == "gamma"
        assert "writing" in result["route"].lower()

    def test_routing_history_is_tracked(self):
        agent = DeltaAgent()
        result = agent.execute({"task": "Analyze data"})
        history = result["context"]["routing_history"]
        assert len(history) == 1
        assert history[0]["from"] == "delta"
        assert history[0]["to"] == result["target_agent"]
        assert "reason" in history[0]

    def test_context_is_enriched_not_replaced(self):
        agent = DeltaAgent()
        result = agent.execute(
            {"task": "Analyze", "context": {"existing_key": "preserved"}}
        )
        assert result["context"]["existing_key"] == "preserved"
        assert "routing_history" in result["context"]

    def test_execute_with_action_key(self):
        agent = DeltaAgent()
        result = agent.execute({"action": "Review the code"})
        assert result["target_agent"] == "beta"

    def test_describe_state(self):
        agent = DeltaAgent()
        state = agent.describe_state()
        assert state["agent_id"] == "delta"
        assert state["role"] == "orchestrator"


# ═══ Orchestrator Tests ═══


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


# ═══ State Machine Tests ═══


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine(task_id="t")
        assert sm.state == TaskState.PLANNING

    def test_transition_planning_to_dispatch(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        assert sm.state == TaskState.DISPATCH

    def test_transition_dispatch_to_running(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        assert sm.state == TaskState.RUNNING

    def test_transition_running_to_verifying(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        assert sm.state == TaskState.VERIFYING

    def test_transition_verifying_to_completed(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.COMPLETED)
        assert sm.state == TaskState.COMPLETED

    def test_transition_verifying_to_retry(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.RETRY)
        assert sm.state == TaskState.RETRY

    def test_invalid_transition_raises(self):
        with pytest.raises(ValueError):
            StateMachine(task_id="t").transition(TaskState.COMPLETED)

    def test_retry_increments_counter(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.VERIFYING)
        sm.transition(TaskState.RETRY)
        assert sm.retry_count == 1

    def test_max_retries_exceeded(self):
        sm = StateMachine(task_id="t", max_retries=3)
        for _ in range(3):
            sm.transition(TaskState.DISPATCH)
            sm.transition(TaskState.RUNNING)
            sm.transition(TaskState.VERIFYING)
            sm.transition(TaskState.RETRY)
        with pytest.raises(RuntimeError):
            sm.transition(TaskState.DISPATCH)

    def test_history_has_explicit_status_and_timestamp(self):
        sm = StateMachine(task_id="t")
        sm.transition(TaskState.DISPATCH, status="selected")
        assert sm.history[-1]["status"] == "selected"
        assert sm.history[-1]["task_id"] == "t"
        assert "timestamp" in sm.history[-1]

    def test_snapshot_reports_recoverability(self):
        sm = StateMachine(task_id="t")
        assert sm.snapshot()["recoverable"] is True
        sm.transition(TaskState.DISPATCH)
        sm.transition(TaskState.RUNNING)
        sm.transition(TaskState.FAILED)
        assert sm.snapshot()["recoverable"] is False
