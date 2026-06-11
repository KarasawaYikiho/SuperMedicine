"""Beta Agent — Reviewer: Independent verification and review."""

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent


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
        super().__init__(agent_id="beta", role="reviewer")

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

        if not task.get("task") and not task.get("description") and not task.get("content"):
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
