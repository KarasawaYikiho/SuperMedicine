"""Test-friendly Chinese TUI screen controller foundations."""

from __future__ import annotations

from core.tui.screens.experience import ExperienceScreenController
from core.tui.screens.diagnose_screen import DiagnoseView
from core.tui.screens.llm_screen import LLMScreenController, LLMView
from core.tui.screens.papers import PaperScreenController
from core.tui.screens.self_evolution_screen import SelfEvolutionView
from core.tui.screens.workspaces import WorkspaceScreenController

__all__ = [
    "ExperienceScreenController",
    "DiagnoseView",
    "LLMScreenController",
    "LLMView",
    "PaperScreenController",
    "SelfEvolutionView",
    "WorkspaceScreenController",
]
