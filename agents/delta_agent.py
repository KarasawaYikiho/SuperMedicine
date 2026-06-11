"""Delta Agent — Orchestrator: Routing and coordination."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent


class DeltaAgent(BaseAgent):
    """Orchestrator agent responsible for routing and coordination.

    Delta inspects an incoming task and decides which downstream agent
    should handle it next, carrying forward accumulated context.
    """

    # Default routing table: task keyword → target agent id
    _ROUTE_TABLE: dict[str, str] = {
        "analyse": "alpha",
        "analyze": "alpha",
        "plan": "alpha",
        "requirements": "alpha",
        "review": "beta",
        "verify": "beta",
        "check": "beta",
        "validate": "beta",
        "write": "gamma",
        "draft": "gamma",
        "generate": "gamma",
        "content": "gamma",
    }

    def __init__(self) -> None:
        super().__init__(agent_id="delta", role="orchestrator")

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Route the task to the appropriate agent.

        Parameters
        ----------
        task:
            Task dictionary.  Recognised keys: ``task`` / ``description``
            (str), ``target_agent`` (str, explicit override), ``context``
            (dict), ``phase`` (str).

        Returns
        -------
        dict
            ``route`` – routing decision reason string.\n
            ``target_agent`` – chosen agent id.\n
            ``context`` – enriched context to forward.
        """
        description = str(
            task.get("task")
            or task.get("description")
            or task.get("action")
            or ""
        ).strip()

        # Allow explicit override
        explicit_target = task.get("target_agent")
        context: dict[str, Any] = dict(task.get("context", {}))
        phase = task.get("phase", "auto")

        if explicit_target and explicit_target in ("alpha", "beta", "gamma"):
            target = explicit_target
            route_reason = f"Explicit target_agent override: {target}"
        else:
            target, route_reason = self._auto_route(description, phase)

        # Enrich context with routing metadata
        context.setdefault("routing_history", [])
        context["routing_history"].append(
            {
                "from": self.agent_id,
                "to": target,
                "reason": route_reason,
            }
        )

        return {
            "route": route_reason,
            "target_agent": target,
            "context": context,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _auto_route(self, description: str, phase: str) -> tuple[str, str]:
        """Determine target agent from description keywords and phase."""
        lower = description.lower()

        # Phase-based routing takes priority
        if phase == "analysis":
            return "alpha", "Phase 'analysis' → alpha"
        if phase == "review":
            return "beta", "Phase 'review' → beta"
        if phase == "writing":
            return "gamma", "Phase 'writing' → gamma"

        # Keyword-based routing
        for keyword, target in self._ROUTE_TABLE.items():
            if keyword in lower:
                return target, f"Keyword '{keyword}' matched → {target}"

        # Default: start with analysis
        return "alpha", "Default route → alpha for initial analysis"
