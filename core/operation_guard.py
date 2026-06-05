"""Foundation helpers for guarded dangerous operations.

The helpers in this module mediate future dangerous operations through the
existing :class:`permission.engine.PermissionEngine` contract.  They do not
change default policies or execute user-facing workspace/import/RAG/TUI
behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from permission.audit import AuditLogger
from permission.access_mode import AccessModePolicy, FileAccessOperation
from permission.engine import PermissionEngine
from permission.policy import PermissionResult

from core.path_safety import validate_destructive_path, validate_path_in_project_root


class DangerousOperationDenied(PermissionError):
    """Raised when PermissionEngine denies a guarded dangerous operation."""


@dataclass(frozen=True)
class OperationAuditRecord:
    """Consistent audit metadata for guarded dangerous-operation decisions."""

    agent_id: str
    action: str
    resource: str
    result: str
    reason: str
    operation: str = "dangerous_operation"
    trace_id: str | None = None

    def to_context(self) -> dict[str, str]:
        """Return stable context fields for PermissionEngine hard-limit checks."""

        return {
            "operation": self.operation,
            "guard_result": self.result,
            "guard_reason": self.reason,
        }


@dataclass(frozen=True)
class OperationAuthorization:
    """Successful guarded-operation authorization result."""

    path: Path
    audit_record: OperationAuditRecord


def authorize_dangerous_operation(
    *,
    permission_engine: PermissionEngine,
    agent_id: str,
    action: str,
    path: str | Path,
    project_root: str | Path | None = None,
    context: dict[str, Any] | None = None,
    destructive: bool = False,
    audit_logger: AuditLogger | None = None,
    access_policy: AccessModePolicy | None = None,
    file_operation: FileAccessOperation | str | None = None,
    operation: str = "dangerous_operation",
    trace_id: str | None = None,
) -> OperationAuthorization:
    """Validate and authorize a future dangerous operation.

    Path validation is performed first so invalid project-root targets are never
    presented as valid resources.  The existing PermissionEngine is then called
    with the resolved resource path; only its ``ALLOWED`` result authorizes the
    operation.  When an explicit ``audit_logger`` is provided, a consistent guard
    audit record is written for both allow and deny decisions in addition to any
    logging performed internally by PermissionEngine.
    """

    if access_policy is None:
        resolved_path = (
            validate_destructive_path(path, project_root)
            if destructive
            else validate_path_in_project_root(path, project_root)
        )
    else:
        access_decision = access_policy.require_allowed(
            path,
            file_operation
            or (FileAccessOperation.DELETE if destructive else FileAccessOperation.WRITE),
        )
        resolved_path = access_decision.path
        if destructive:
            try:
                resolved_path.relative_to(access_policy.project_root)
            except ValueError:
                pass
            else:
                validate_destructive_path(resolved_path, access_policy.project_root)
    resource = str(resolved_path)
    permission_context = dict(context or {})
    permission_context.setdefault("operation", operation)

    permission_result = permission_engine.check(
        agent_id,
        action,
        resource,
        context=permission_context,
    )

    allowed = permission_result == PermissionResult.ALLOWED
    audit_record = OperationAuditRecord(
        agent_id=agent_id,
        action=action,
        resource=resource,
        result=permission_result.value,
        reason="permission_allowed" if allowed else "permission_denied",
        operation=operation,
        trace_id=trace_id,
    )
    if audit_logger is not None:
        audit_logger.log(
            agent_id=audit_record.agent_id,
            action=audit_record.action,
            resource=audit_record.resource,
            result=audit_record.result,
            reason=audit_record.reason,
            trace_id=audit_record.trace_id,
        )

    if not allowed:
        raise DangerousOperationDenied(
            f"Dangerous operation denied: {action} {resource}"
        )

    return OperationAuthorization(path=resolved_path, audit_record=audit_record)
