"""Alpha Agent — Analyst: Planning and requirements analysis."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent


class AlphaAgent(BaseAgent):
    """Analyst agent responsible for planning and requirements analysis.

    Alpha analyzes incoming tasks to extract requirements, identify key
    entities and constraints, assess complexity, and produce actionable
    recommendations for downstream agents.
    """

    def __init__(self) -> None:
        super().__init__(agent_id="alpha", role="analyst")

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
            task.get("task")
            or task.get("description")
            or task.get("action")
            or ""
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
            s.strip()
            for s in description.replace("\n", ". ").split(".")
            if s.strip()
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
    def _assess_complexity(
        description: str, requirements: list[dict[str, Any]]
    ) -> str:
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
            recs.append(
                "Break the task into smaller sub-tasks before execution."
            )
        if len(requirements) > 10:
            recs.append(
                "Consider grouping related requirements for phased delivery."
            )
        if not description:
            recs.append(
                "Task description is empty; clarify objectives before proceeding."
            )

        recs.append("Route to beta agent for review before execution.")
        recs.append(
            "Route to gamma agent for content generation after approval."
        )

        return recs
