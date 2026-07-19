"""Chinese TUI foundation for SuperMedicine."""

from __future__ import annotations

import sys

from core.tui import support as _support

for _legacy_module in (
    "dialog_history",
    "kernel_output",
    "menu_screens",
    "nav_widgets",
    "permissions",
    "prompt_input",
    "resources",
    "state",
    "status_helpers",
    "stream_capture",
    "types",
):
    sys.modules.setdefault(f"core.tui.{_legacy_module}", _support)
    globals()[_legacy_module] = _support

from core.tui.app import TUIStatus, launch_tui, main  # noqa: E402
from core.tui.i18n import LABELS, t  # noqa: E402
from core.tui.support import (  # noqa: E402
    TUIToolActionRequest,
    TUIState,
    load_recent_workspace,
    prepare_tool_action,
    save_recent_workspace,
)

# Backward-compatible aliases for legacy Screen class names — resolved lazily
_SCREEN_ALIASES = {
    "DashboardScreen": ("core.tui.screens.dashboard", "DashboardView"),
    "DialogScreen": ("core.tui.screens.dialog_screen", "DialogView"),
    "ExperienceScreen": ("core.tui.screens.experience_screen", "ExperienceView"),
    "PaperScreen": ("core.tui.screens.paper_screen", "PaperView"),
    "ToolScreen": ("core.tui.screens.tool_screen", "ToolView"),
    "WorkspaceScreen": ("core.tui.screens.workspace_screen", "WorkspaceView"),
}


def __getattr__(name: str) -> object:
    """Lazy imports for View classes (require Textual)."""
    _lazy = {
        "DashboardView": ("core.tui.screens.dashboard", "DashboardView"),
        "WorkspaceView": ("core.tui.screens.workspace_screen", "WorkspaceView"),
        "PaperView": ("core.tui.screens.paper_screen", "PaperView"),
        "ExperienceView": ("core.tui.screens.experience_screen", "ExperienceView"),
        "ToolView": ("core.tui.screens.tool_screen", "ToolView"),
        "DialogView": ("core.tui.screens.dialog_screen", "DialogView"),
        "ChatView": ("core.tui.screens.chat_view", "ChatView"),
    }
    _lazy.update(_SCREEN_ALIASES)
    if name in _lazy:
        mod_path, attr = _lazy[name]
        import importlib

        mod = importlib.import_module(mod_path)
        return getattr(mod, attr)
    raise AttributeError(f"module 'core.tui' has no attribute {name!r}")


__all__ = [
    "ChatView",
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
