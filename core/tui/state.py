"""Workspace-local TUI session state helpers.

Recent workspace selection is intentionally persisted only inside an explicitly
selected workspace's ``.supermedicine/sessions`` directory.  These helpers never
change CLI defaults and never provide implicit workspace selection for non-TUI
commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.workspace import WorkspaceManager


@dataclass(frozen=True, slots=True)
class TUIState:
    """Small state facade scoped to a single project root."""

    project_root: Path | str | None = None

    @property
    def workspace_manager(self) -> WorkspaceManager:
        return WorkspaceManager(self.project_root)

    def save_recent_workspace(
        self,
        workspace_id: str,
        selected_workspace_id: str | None = None,
    ) -> Path:
        """Save TUI recent selection in the source workspace session state."""

        return self.workspace_manager.save_recent_selection(workspace_id, selected_workspace_id)

    def load_recent_workspace(self, workspace_id: str) -> str | None:
        """Load TUI recent selection only from the requested workspace state."""

        return self.workspace_manager.load_recent_selection(workspace_id)


def save_recent_workspace(
    workspace_id: str,
    selected_workspace_id: str | None = None,
    project_root: Path | str | None = None,
) -> Path:
    """Convenience wrapper for workspace-local recent workspace state."""

    return TUIState(project_root).save_recent_workspace(workspace_id, selected_workspace_id)


def load_recent_workspace(
    workspace_id: str,
    project_root: Path | str | None = None,
) -> str | None:
    """Convenience wrapper that does not affect CLI workspace behavior."""

    return TUIState(project_root).load_recent_workspace(workspace_id)
