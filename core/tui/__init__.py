"""Chinese TUI foundation for SuperMedicine."""

from core.tui.app import TUIStatus, launch_tui, main
from core.tui.i18n import LABELS, t
from core.tui.permissions import TUIToolActionRequest, prepare_tool_action
from core.tui.state import TUIState, load_recent_workspace, save_recent_workspace

__all__ = [
    "LABELS",
    "TUIState",
    "TUIStatus",
    "TUIToolActionRequest",
    "launch_tui",
    "load_recent_workspace",
    "main",
    "prepare_tool_action",
    "save_recent_workspace",
    "t",
]
