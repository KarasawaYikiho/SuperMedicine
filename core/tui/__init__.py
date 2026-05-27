"""Chinese TUI foundation for SuperMedicine."""
from __future__ import annotations

from core.tui.app import TUIStatus, launch_tui, main
from core.tui.i18n import LABELS, t
from core.tui.permissions import TUIToolActionRequest, prepare_tool_action
from core.tui.screens.dashboard import DashboardView
from core.tui.screens.dialog_screen import DialogView
from core.tui.screens.experience_screen import ExperienceView
from core.tui.screens.paper_screen import PaperView
from core.tui.screens.tool_screen import ToolView
from core.tui.screens.workspace_screen import WorkspaceView
from core.tui.state import TUIState, load_recent_workspace, save_recent_workspace

# Backward-compatible aliases for legacy Screen class names
DashboardScreen = DashboardView
DialogScreen = DialogView
ExperienceScreen = ExperienceView
PaperScreen = PaperView
ToolScreen = ToolView
WorkspaceScreen = WorkspaceView

__all__ = [
    "DashboardScreen",
    "DashboardView",
    "DialogScreen",
    "DialogView",
    "ExperienceScreen",
    "ExperienceView",
    "LABELS",
    "PaperScreen",
    "PaperView",
    "TUIState",
    "TUIStatus",
    "TUIToolActionRequest",
    "ToolScreen",
    "ToolView",
    "WorkspaceScreen",
    "WorkspaceView",
    "launch_tui",
    "load_recent_workspace",
    "main",
    "prepare_tool_action",
    "save_recent_workspace",
    "t",
]
