"""Test-friendly Chinese TUI screen controller foundations."""

from __future__ import annotations

from core.tui.screens.experience import ExperienceScreenController
from core.tui.screens.llm_screen import LLMScreenController, LLMView
from core.tui.screens.papers import PaperScreenController
from core.tui.screens.workspaces import WorkspaceScreenController

__all__ = [
    "ExperienceScreenController",
    "LLMScreenController",
    "LLMView",
    "PaperScreenController",
    "WorkspaceScreenController",
]
