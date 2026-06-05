from __future__ import annotations

from typing import Any

from core.tui.permissions import TUI_TOOL_ACTION, prepare_tool_action
from permission.policy import PermissionResult


class FakePermissionEngine:
    def __init__(self, result: PermissionResult):
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def check(self, agent_id, action, resource, context=None):
        self.calls.append(
            {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": context,
            }
        )
        return self.result


def test_high_risk_action_refuses_unconfirmed_request_without_permission_call():
    engine = FakePermissionEngine(PermissionResult.ALLOWED)

    request = prepare_tool_action(engine, tool="bash", resource="bash", confirmed=False)

    assert request.allowed is False
    assert request.confirmed is False
    assert request.permission == "denied"
    assert engine.calls == []


def test_high_risk_action_requires_permission_engine_allow():
    denied_engine = FakePermissionEngine(PermissionResult.DENIED)

    denied = prepare_tool_action(
        denied_engine, tool="write", resource="notes/output.md", confirmed=True
    )

    assert denied.allowed is False
    assert denied.permission == "denied"
    assert denied_engine.calls[0]["action"] == TUI_TOOL_ACTION
    assert denied_engine.calls[0]["context"]["sandbox_required"] is True

    allowed_engine = FakePermissionEngine(PermissionResult.ALLOWED)
    allowed = prepare_tool_action(
        allowed_engine, tool="edit", resource="notes/output.md", confirmed=True
    )

    assert allowed.allowed is True
    assert allowed.permission == "allowed"


def test_low_risk_action_still_uses_permission_engine_but_not_confirmation_gate():
    engine = FakePermissionEngine(PermissionResult.ALLOWED)

    request = prepare_tool_action(
        engine,
        tool="read",
        resource="notes/summary.md",
        confirmed=False,
        context={"screen": "工具管理"},
    )

    assert request.allowed is True
    assert request.confirmed is False
    assert request.context["requires_confirmation"] is False
    assert request.context["sandbox_required"] is True
    assert request.context["audit_required"] is True
    assert engine.calls[0]["context"]["screen"] == "工具管理"
