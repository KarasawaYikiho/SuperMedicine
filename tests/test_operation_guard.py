from __future__ import annotations

import json
from typing import Any

import pytest

from core.operation_guard import DangerousOperationDenied, authorize_dangerous_operation
from permission.audit import AuditLogger
from permission.policy import PermissionResult


class RecordingPermissionEngine:
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


def test_permission_engine_called_before_authorizing_dangerous_operation(tmp_path):
    target = tmp_path / "data.txt"
    target.write_text("content", encoding="utf-8")
    engine = RecordingPermissionEngine(PermissionResult.ALLOWED)

    authorization = authorize_dangerous_operation(
        permission_engine=engine,
        agent_id="agent",
        action="file.delete",
        path=target,
        project_root=tmp_path,
        destructive=True,
    )

    assert authorization.path == target.resolve()
    assert len(engine.calls) == 1
    assert engine.calls[0]["agent_id"] == "agent"
    assert engine.calls[0]["action"] == "file.delete"
    assert engine.calls[0]["resource"] == str(target.resolve())


@pytest.mark.parametrize(
    (
        "permission_result",
        "action",
        "destructive",
        "trace_id",
        "expected_result",
        "expected_reason",
    ),
    [
        (
            PermissionResult.ALLOWED,
            "file.write",
            False,
            "trace-allow",
            "allowed",
            "permission_allowed",
        ),
        (
            PermissionResult.DENIED,
            "file.delete",
            True,
            "trace-deny",
            "denied",
            "permission_denied",
        ),
    ],
)
def test_guard_decisions_write_audit_events_and_denials_raise(
    tmp_path,
    permission_result,
    action,
    destructive,
    trace_id,
    expected_result,
    expected_reason,
):
    target = tmp_path / "data.txt"
    target.write_text("content", encoding="utf-8")
    engine = RecordingPermissionEngine(permission_result)
    audit_log = tmp_path / "audit.jsonl"

    if permission_result == PermissionResult.DENIED:
        with pytest.raises(DangerousOperationDenied):
            authorize_dangerous_operation(
                permission_engine=engine,
                agent_id="agent",
                action=action,
                path=target,
                project_root=tmp_path,
                destructive=destructive,
                audit_logger=AuditLogger(audit_log),
                trace_id=trace_id,
            )
    else:
        authorize_dangerous_operation(
            permission_engine=engine,
            agent_id="agent",
            action=action,
            path=target,
            project_root=tmp_path,
            destructive=destructive,
            audit_logger=AuditLogger(audit_log),
            trace_id=trace_id,
        )

    assert len(engine.calls) == 1
    entry = json.loads(audit_log.read_text(encoding="utf-8").strip())
    assert entry["agent_id"] == "agent"
    assert entry["action"] == action
    assert entry["resource"] == str(target.resolve())
    assert entry["result"] == expected_result
    assert entry["reason"] == expected_reason
    assert entry["trace_id"] == trace_id
