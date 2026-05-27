"""Chinese TUI foundation for SuperMedicine."""

from core.tui.app import TUIStatus, launch_tui, main
from core.tui.i18n import LABELS, t
from core.tui.permissions import TUIToolActionRequest, prepare_tool_action
from core.tui.screens.dashboard import DashboardScreen
from core.tui.screens.dialog_screen import DialogScreen
from core.tui.screens.experience_screen import ExperienceScreen
from core.tui.screens.paper_screen import PaperScreen
from core.tui.screens.tool_screen import ToolScreen
from core.tui.screens.workspace_screen import WorkspaceScreen
from core.tui.state import TUIState, load_recent_workspace, save_recent_workspace

__all__ = [
    "DashboardScreen",
    "DialogScreen",
    "ExperienceScreen",
    "LABELS",
    "PaperScreen",
    "TUIState",
    "TUIStatus",
    "TUIToolActionRequest",
    "ToolScreen",
    "WorkspaceScreen",
    "launch_tui",
    "load_recent_workspace",
    "main",
    "prepare_tool_action",
    "save_recent_workspace",
    "t",
]
