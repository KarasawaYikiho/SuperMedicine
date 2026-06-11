"""Gamma Agent — Writer: Drafting and content execution."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent


class GammaAgent(BaseAgent):
    """Writer agent responsible for drafting and content execution.

    Gamma generates structured content based on analysis and requirements
    provided by upstream agents (typically Alpha and Beta).
    """

    def __init__(self) -> None:
        super().__init__(agent_id="gamma", role="writer")

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
            task.get("task")
            or task.get("description")
            or task.get("content")
            or ""
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
