from __future__ import annotations

from typing import Any

import pytest

from core.tui.permissions import TUI_TOOL_ACTION, prepare_tool_action
from core.tui.screens.permission_screen import PermissionScreenController
from permission.access_mode import AccessDecisionStatus, FullAccessConfirmationRequired
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


def test_permission_screen_controller_requires_full_confirmation_and_updates_policy(
    tmp_path,
):
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    controller = PermissionScreenController(project_root)

    conservative_write = controller.access_decision(external_root / "out.csv", "write")

    assert conservative_write["status"] == AccessDecisionStatus.DENIED.value
    with pytest.raises(FullAccessConfirmationRequired):
        controller.set_mode("full", confirmation_text="")

    full_config = controller.set_mode("full", confirmation_text="FULL")
    full_write = controller.access_decision(external_root / "out.csv", "write")
    conservative_config = controller.set_mode("conservative")

    assert full_config["mode"] == "full"
    assert full_config["full_mode_confirmed"] is True
    assert full_write["status"] == AccessDecisionStatus.ALLOWED.value
    assert "will not silently" in full_write["helper"]
    assert conservative_config["mode"] == "conservative"
    assert conservative_config["full_mode_confirmed"] is False
