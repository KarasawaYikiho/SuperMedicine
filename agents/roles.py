"""Data-driven role specifications and preserved four-agent behavior."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RoleSpec:
    agent_id: str
    role: str
    prompt: str
    input_keys: tuple[str, ...]
    output_keys: tuple[str, ...]
    next_role: str | None


ROLE_SPECS: dict[str, RoleSpec] = {
    "alpha": RoleSpec(
        "alpha",
        "analyst",
        "Analyze requirements and constraints.",
        ("task", "context"),
        ("analysis", "requirements", "complexity", "recommendations"),
        "beta",
    ),
    "beta": RoleSpec(
        "beta",
        "reviewer",
        "Review completeness, correctness, safety, and medical boundaries.",
        ("analysis", "requirements", "content"),
        ("review", "issues", "approved", "feedback"),
        "gamma",
    ),
    "gamma": RoleSpec(
        "gamma",
        "writer",
        "Draft structured research-support content.",
        ("task", "requirements", "analysis", "context"),
        ("content", "format", "metadata"),
        None,
    ),
    "delta": RoleSpec(
        "delta",
        "orchestrator",
        "Route tasks across configured roles.",
        ("task", "target_agent", "context", "phase"),
        ("route", "target_agent", "context"),
        "alpha",
    ),
}


class BaseAgent(ABC):
    """Abstract base class for all agents in the orchestration system."""

    def __init__(self, agent_id: str | RoleSpec, role: str | None = None):
        self.spec = (
            agent_id
            if isinstance(agent_id, RoleSpec)
            else RoleSpec(agent_id, role or "", "", (), (), None)
        )
        self._agent_id = self.spec.agent_id
        self._role = self.spec.role

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def role(self) -> str:
        return self._role

    def describe_state(self) -> dict[str, Any]:
        return {"agent_id": self._agent_id, "role": self._role, "status": "registered"}

    @abstractmethod
    def execute(self, task: dict[str, Any]) -> dict[str, Any]: ...


class AlphaAgent(BaseAgent):
    """Analyst agent responsible for planning and requirements analysis.

    Alpha analyzes incoming tasks to extract requirements, identify key
    entities and constraints, assess complexity, and produce actionable
    recommendations for downstream agents.
    """

    def __init__(self) -> None:
        super().__init__(ROLE_SPECS["alpha"])

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Analyze a task and return structured requirements.

        Parameters
        ----------
        task:
            Raw task dictionary.  Expected keys include ``task`` (str) or
            ``description`` (str) describing the work to be done.  Optional
            keys: ``context``, ``domain``, ``priority``.

        Returns
        -------
        dict
            ``analysis`` – high-level analysis dict.\n
            ``requirements`` – extracted requirement items.\n
            ``complexity`` – ``"low"`` / ``"medium"`` / ``"high"``.\n
            ``recommendations`` – actionable next-step suggestions.
        """
        description = str(
            task.get("task") or task.get("description") or task.get("action") or ""
        ).strip()

        context = task.get("context", {})
        domain = task.get("domain", "general")
        priority = task.get("priority", "normal")

        # --- analyse ---
        analysis: dict[str, Any] = {
            "input_description": description,
            "domain": domain,
            "priority": priority,
            "has_context": bool(context),
            "entity_count": self._count_entities(description),
            "constraint_keywords": self._extract_constraints(description),
        }

        requirements = self._extract_requirements(description, context)
        complexity = self._assess_complexity(description, requirements)
        recommendations = self._build_recommendations(
            description, requirements, complexity
        )

        return {
            "analysis": analysis,
            "requirements": requirements,
            "complexity": complexity,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_entities(text: str) -> int:
        """Rough count of distinct entity-like tokens (capitalised words)."""
        return sum(1 for w in text.split() if w[:1].isupper() and len(w) > 1)

    @staticmethod
    def _extract_constraints(text: str) -> list[str]:
        """Return constraint-related keywords found in *text*."""
        constraint_markers = [
            "must",
            "shall",
            "required",
            "mandatory",
            "limit",
            "maximum",
            "minimum",
            "constraint",
            "forbidden",
            "禁止",
            "必须",
            "限制",
            "要求",
        ]
        lower = text.lower()
        return [kw for kw in constraint_markers if kw in lower]

    @staticmethod
    def _extract_requirements(
        description: str, context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Derive requirement items from the description and context."""
        requirements: list[dict[str, Any]] = []

        # Split on sentence-like boundaries
        sentences = [
            s.strip() for s in description.replace("\n", ". ").split(".") if s.strip()
        ]

        for idx, sentence in enumerate(sentences, start=1):
            requirements.append(
                {
                    "id": f"REQ-{idx:03d}",
                    "text": sentence,
                    "source": "description",
                    "priority": "normal",
                }
            )

        # Merge context-provided requirements
        for idx, ctx_item in enumerate(
            context.get("requirements", []), start=len(requirements) + 1
        ):
            requirements.append(
                {
                    "id": f"REQ-{idx:03d}",
                    "text": str(ctx_item),
                    "source": "context",
                    "priority": context.get("priority", "normal"),
                }
            )

        return requirements

    @staticmethod
    def _assess_complexity(description: str, requirements: list[dict[str, Any]]) -> str:
        """Return ``"low"`` / ``"medium"`` / ``"high"`` complexity."""
        score = 0
        score += len(description) // 200
        score += len(requirements)

        lower = description.lower()
        high_markers = [
            "integration",
            "multi-agent",
            "pipeline",
            "security",
            "permission",
            "compliance",
            "distributed",
        ]
        score += sum(2 for m in high_markers if m in lower)

        if score >= 8:
            return "high"
        if score >= 4:
            return "medium"
        return "low"

    @staticmethod
    def _build_recommendations(
        description: str,
        requirements: list[dict[str, Any]],
        complexity: str,
    ) -> list[str]:
        """Produce actionable recommendations."""
        recs: list[str] = []

        if complexity == "high":
            recs.append("Break the task into smaller sub-tasks before execution.")
        if len(requirements) > 10:
            recs.append("Consider grouping related requirements for phased delivery.")
        if not description:
            recs.append(
                "Task description is empty; clarify objectives before proceeding."
            )

        recs.append("Route to beta agent for review before execution.")
        recs.append("Route to gamma agent for content generation after approval.")

        return recs


class BetaAgent(BaseAgent):
    """Reviewer agent responsible for independent verification and review.

    Beta reviews inputs for completeness, correctness, and safety.  It
    checks for medical boundary violations and returns a structured
    assessment with an approval decision.
    """

    # Keywords that suggest medical advice beyond research support
    _MEDICAL_ADVICE_MARKERS: list[str] = [
        "diagnose",
        "prescribe",
        "treatment plan",
        "clinical decision",
        "patient care",
        "dosage",
        "医嘱",
        "处方",
        "诊断",
        "临床决策",
    ]

    def __init__(self) -> None:
        super().__init__(ROLE_SPECS["beta"])

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Review input for completeness, correctness, and safety.

        Parameters
        ----------
        task:
            Task dictionary to review.  May contain ``analysis``,
            ``requirements``, ``content``, or any freeform keys.

        Returns
        -------
        dict
            ``review`` – detailed review dict.\n
            ``issues`` – list of issue dicts.\n
            ``approved`` – ``True`` when no blocking issues found.\n
            ``feedback`` – human-readable summary string.
        """
        issues: list[dict[str, Any]] = []

        # --- completeness check ---
        completeness = self._check_completeness(task)
        issues.extend(completeness["issues"])

        # --- correctness check ---
        correctness = self._check_correctness(task)
        issues.extend(correctness["issues"])

        # --- medical boundary check ---
        medical = self._check_medical_boundary(task)
        issues.extend(medical["issues"])

        # --- safety check ---
        safety = self._check_safety(task)
        issues.extend(safety["issues"])

        approved = all(i.get("severity") != "blocking" for i in issues)

        feedback = (
            "All checks passed."
            if approved
            else f"{sum(1 for i in issues if i.get('severity') == 'blocking')} blocking issue(s) found."
        )

        return {
            "review": {
                "completeness": completeness,
                "correctness": correctness,
                "medical_boundary": medical,
                "safety": safety,
            },
            "issues": issues,
            "approved": approved,
            "feedback": feedback,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_completeness(self, task: dict[str, Any]) -> dict[str, Any]:
        """Verify required fields are present."""
        issues: list[dict[str, Any]] = []
        present_keys = list(task.keys())

        if (
            not task.get("task")
            and not task.get("description")
            and not task.get("content")
        ):
            issues.append(
                {
                    "check": "completeness",
                    "severity": "warning",
                    "message": "No task description or content provided.",
                }
            )

        return {"issues": issues, "present_keys": present_keys}

    def _check_correctness(self, task: dict[str, Any]) -> dict[str, Any]:
        """Basic structural correctness validation."""
        issues: list[dict[str, Any]] = []

        # Validate requirements list if present
        requirements = task.get("requirements")
        if requirements is not None:
            if not isinstance(requirements, list):
                issues.append(
                    {
                        "check": "correctness",
                        "severity": "blocking",
                        "message": "'requirements' must be a list.",
                    }
                )
            else:
                for idx, req in enumerate(requirements):
                    if not isinstance(req, dict):
                        issues.append(
                            {
                                "check": "correctness",
                                "severity": "warning",
                                "message": f"Requirement at index {idx} is not a dict.",
                            }
                        )

        return {"issues": issues}

    def _check_medical_boundary(self, task: dict[str, Any]) -> dict[str, Any]:
        """Flag content that crosses the medical advice boundary."""
        issues: list[dict[str, Any]] = []
        text = self._flatten_text(task).lower()

        for marker in self._MEDICAL_ADVICE_MARKERS:
            if marker in text:
                issues.append(
                    {
                        "check": "medical_boundary",
                        "severity": "blocking",
                        "message": (
                            f"Content contains medical advice marker '{marker}'. "
                            "SuperMedicine provides research support only and must "
                            "not produce clinical decisions."
                        ),
                    }
                )

        return {"issues": issues}

    def _check_safety(self, task: dict[str, Any]) -> dict[str, Any]:
        """Check for unsafe patterns (secrets, injection hints, etc.)."""
        issues: list[dict[str, Any]] = []
        text = self._flatten_text(task)

        # Detect embedded secrets
        secret_patterns = ["api_key", "password", "token", "secret"]
        lower = text.lower()
        for pattern in secret_patterns:
            if pattern in lower and "=" in text:
                issues.append(
                    {
                        "check": "safety",
                        "severity": "warning",
                        "message": f"Possible embedded secret detected ('{pattern}').",
                    }
                )

        return {"issues": issues}

    @staticmethod
    def _flatten_text(task: dict[str, Any]) -> str:
        """Recursively extract all string values into a single blob."""
        parts: list[str] = []

        def _walk(obj: Any) -> None:
            if isinstance(obj, str):
                parts.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    _walk(item)

        _walk(task)
        return " ".join(parts)


class GammaAgent(BaseAgent):
    """Writer agent responsible for drafting and content execution.

    Gamma generates structured content based on analysis and requirements
    provided by upstream agents (typically Alpha and Beta).
    """

    def __init__(self) -> None:
        super().__init__(ROLE_SPECS["gamma"])

    def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        """Generate content based on analysis and requirements.

        Parameters
        ----------
        task:
            Task dictionary.  Recognised keys: ``task`` / ``description``
            (str), ``requirements`` (list), ``analysis`` (dict),
            ``format`` (str, default ``"markdown"``), ``context`` (dict).

        Returns
        -------
        dict
            ``content`` – generated content string.\n
            ``format`` – output format identifier.\n
            ``metadata`` – generation metadata dict.
        """
        description = str(
            task.get("task") or task.get("description") or task.get("content") or ""
        ).strip()

        requirements: list[dict[str, Any]] = task.get("requirements", [])
        analysis: dict[str, Any] = task.get("analysis", {})
        context: dict[str, Any] = task.get("context", {})
        output_format = task.get("format", "markdown")

        # --- generate content ---
        content = self._generate_content(
            description=description,
            requirements=requirements,
            analysis=analysis,
            context=context,
            output_format=output_format,
        )

        metadata: dict[str, Any] = {
            "generator": self.agent_id,
            "input_requirements_count": len(requirements),
            "output_format": output_format,
            "complexity": analysis.get("complexity", "unknown"),
            "has_context": bool(context),
        }

        return {
            "content": content,
            "format": output_format,
            "metadata": metadata,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_content(
        self,
        *,
        description: str,
        requirements: list[dict[str, Any]],
        analysis: dict[str, Any],
        context: dict[str, Any],
        output_format: str,
    ) -> str:
        """Build structured output from available inputs."""
        sections: list[str] = []

        # Title / header
        if description:
            sections.append(f"# Task: {description}\n")

        # Analysis summary
        if analysis:
            sections.append("## Analysis Summary\n")
            complexity = analysis.get("complexity", "unknown")
            sections.append(f"- **Complexity**: {complexity}")
            domain = analysis.get("domain", "general")
            sections.append(f"- **Domain**: {domain}")
            sections.append("")

        # Requirements
        if requirements:
            sections.append("## Requirements\n")
            for req in requirements:
                req_id = req.get("id", "—")
                text = req.get("text", "")
                priority = req.get("priority", "normal")
                sections.append(f"- **{req_id}** [{priority}]: {text}")
            sections.append("")

        # Context notes
        if context:
            sections.append("## Context\n")
            for key, value in context.items():
                if key == "requirements":
                    continue
                sections.append(f"- **{key}**: {value}")
            sections.append("")

        # Recommendations from analysis
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            sections.append("## Recommendations\n")
            for rec in recommendations:
                sections.append(f"- {rec}")
            sections.append("")

        # Fallback
        if not sections:
            sections.append(
                "No structured content could be generated from the provided input."
            )

        return "\n".join(sections)


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
        super().__init__(ROLE_SPECS["delta"])

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
            task.get("task") or task.get("description") or task.get("action") or ""
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


__all__ = [
    "RoleSpec",
    "ROLE_SPECS",
    "BaseAgent",
    "AlphaAgent",
    "BetaAgent",
    "GammaAgent",
    "DeltaAgent",
]
