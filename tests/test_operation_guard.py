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


def test_allowed_decision_writes_guard_audit_event(tmp_path):
    target = tmp_path / "data.txt"
    target.write_text("content", encoding="utf-8")
    engine = RecordingPermissionEngine(PermissionResult.ALLOWED)
    audit_log = tmp_path / "audit.jsonl"

    authorize_dangerous_operation(
        permission_engine=engine,
        agent_id="agent",
        action="file.write",
        path=target,
        project_root=tmp_path,
        audit_logger=AuditLogger(audit_log),
        trace_id="trace-allow",
    )

    entry = json.loads(audit_log.read_text(encoding="utf-8").strip())
    assert entry["agent_id"] == "agent"
    assert entry["action"] == "file.write"
    assert entry["resource"] == str(target.resolve())
    assert entry["result"] == "allowed"
    assert entry["reason"] == "permission_allowed"
    assert entry["trace_id"] == "trace-allow"


def test_denied_decision_writes_guard_audit_event_and_raises(tmp_path):
    target = tmp_path / "data.txt"
    target.write_text("content", encoding="utf-8")
    engine = RecordingPermissionEngine(PermissionResult.DENIED)
    audit_log = tmp_path / "audit.jsonl"

    with pytest.raises(DangerousOperationDenied):
        authorize_dangerous_operation(
            permission_engine=engine,
            agent_id="agent",
            action="file.delete",
            path=target,
            project_root=tmp_path,
            destructive=True,
            audit_logger=AuditLogger(audit_log),
            trace_id="trace-deny",
        )

    assert len(engine.calls) == 1
    entry = json.loads(audit_log.read_text(encoding="utf-8").strip())
    assert entry["result"] == "denied"
    assert entry["reason"] == "permission_denied"
    assert entry["trace_id"] == "trace-deny"
