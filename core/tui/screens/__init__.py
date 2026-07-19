"""Converged Textual views with historical module-path compatibility."""

from __future__ import annotations

import sys

from core.tui.screens import (
    core_views,
    research_views,
    system_views,
    workspace_views,
)

_ALIASES = {
    "chat_view": core_views,
    "dashboard": core_views,
    "diagnose_screen": core_views,
    "dialog_screen": core_views,
    "self_evolution_screen": core_views,
    "workspaces": workspace_views,
    "workspace_screen": workspace_views,
    "tool_screen": workspace_views,
    "papers": research_views,
    "paper_screen": research_views,
    "experience": research_views,
    "experience_screen": research_views,
    "experiment_screen": research_views,
    "llm_screen": system_views,
    "log_screen": system_views,
    "permission_screen": system_views,
}
for _name, _module in _ALIASES.items():
    sys.modules.setdefault(f"core.tui.screens.{_name}", _module)

ExperienceScreenController = research_views.ExperienceScreenController
PaperScreenController = research_views.PaperScreenController
DiagnoseView = core_views.DiagnoseView
SelfEvolutionView = core_views.SelfEvolutionView
LLMScreenController = system_views.LLMScreenController
LLMView = system_views.LLMView
WorkspaceScreenController = workspace_views.WorkspaceScreenController

__all__ = [
    "ExperienceScreenController",
    "DiagnoseView",
    "LLMScreenController",
    "LLMView",
    "PaperScreenController",
    "SelfEvolutionView",
    "WorkspaceScreenController",
]
