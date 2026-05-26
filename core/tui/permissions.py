"""Permission boundary foundation for future TUI tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from permission.engine import PermissionEngine
from permission.policy import PermissionResult


TUI_TOOL_AGENT_ID = "delta"
TUI_TOOL_ACTION = "tui.tool_action"
HIGH_RISK_TOOLS = frozenset({"bash", "write", "edit"})


@dataclass(frozen=True, slots=True)
class TUIToolActionRequest:
    """Prepared, non-executing description of a TUI tool action."""

    tool: str
    resource: str
    agent_id: str = TUI_TOOL_AGENT_ID
    action: str = TUI_TOOL_ACTION
    confirmed: bool = False
    permission: str = PermissionResult.DENIED.value
    allowed: bool = False
    context: dict[str, Any] = field(default_factory=dict)


def prepare_tool_action(
    permission_engine: PermissionEngine,
    *,
    tool: str,
    resource: str,
    confirmed: bool,
    agent_id: str = TUI_TOOL_AGENT_ID,
    context: dict[str, Any] | None = None,
) -> TUIToolActionRequest:
    """Prepare a high-risk TUI tool action without executing it.

    ``bash``, ``write`` and ``edit`` are treated as high-risk foundations for
    later screens.  They require explicit confirmation first, then a successful
    ``PermissionEngine.check`` decision.  This function only returns a request
    object and never invokes the underlying tool.
    """

    request_context = dict(context or {})
    request_context.update(
        {
            "tool": tool,
            "requires_confirmation": tool in HIGH_RISK_TOOLS,
            "tui_boundary": True,
            "sandbox_required": True,
            "audit_required": True,
        }
    )

    if tool in HIGH_RISK_TOOLS and not confirmed:
        return TUIToolActionRequest(
            tool=tool,
            resource=resource,
            agent_id=agent_id,
            confirmed=False,
            context=request_context,
        )

    decision = permission_engine.check(
        agent_id,
        TUI_TOOL_ACTION,
        resource,
        context=request_context,
    )
    allowed = decision == PermissionResult.ALLOWED
    return TUIToolActionRequest(
        tool=tool,
        resource=resource,
        agent_id=agent_id,
        confirmed=confirmed,
        permission=decision.value,
        allowed=allowed,
        context=request_context,
    )
