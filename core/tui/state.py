"""Workspace-local TUI session state helpers.

Recent workspace selection is intentionally persisted only inside an explicitly
selected workspace's ``.supermedicine/sessions`` directory.  These helpers never
change CLI defaults and never provide implicit workspace selection for non-TUI
commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.workspace import WorkspaceInfo, WorkspaceManager


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

        return self.workspace_manager.save_recent_selection(
            workspace_id, selected_workspace_id
        )

    def load_recent_workspace(self, workspace_id: str) -> str | None:
        """Load TUI recent selection only from the requested workspace state."""

        return self.workspace_manager.load_recent_selection(workspace_id)

    def list_workspaces(self) -> list[WorkspaceInfo]:
        """List initialized workspaces from the shared persistent workspace store."""

        return self.workspace_manager.list_workspaces()

    def create_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """Create a workspace through the shared persistent workspace store."""

        return self.workspace_manager.initialize_workspace(workspace_id)

    def select_workspace(
        self,
        workspace_id: str,
        *,
        state_workspace_id: str | None = None,
    ) -> WorkspaceInfo:
        """Persist a TUI workspace selection without changing CLI workspace behavior."""

        info = self.workspace_manager.get_workspace(workspace_id)
        self.save_recent_workspace(state_workspace_id or info.id, info.id)
        return info

    def workspace_payloads(self) -> list[dict[str, Any]]:
        """Return display-ready workspace records from the shared persistent list."""

        return [
            self._workspace_payload(info, selected=False)
            for info in self.list_workspaces()
        ]

    @staticmethod
    def _workspace_payload(info: WorkspaceInfo, *, selected: bool) -> dict[str, Any]:
        return {
            "id": info.id,
            "label": f"工作区：{info.id}",
            "path": str(info.path),
            "selected": selected,
            "metadata": info.metadata.to_dict(),
        }


def save_recent_workspace(
    workspace_id: str,
    selected_workspace_id: str | None = None,
    project_root: Path | str | None = None,
) -> Path:
    """Convenience wrapper for workspace-local recent workspace state."""

    return TUIState(project_root).save_recent_workspace(
        workspace_id, selected_workspace_id
    )


def load_recent_workspace(
    workspace_id: str,
    project_root: Path | str | None = None,
) -> str | None:
    """Convenience wrapper that does not affect CLI workspace behavior."""

    return TUIState(project_root).load_recent_workspace(workspace_id)


def list_workspaces(project_root: Path | str | None = None) -> list[WorkspaceInfo]:
    """Convenience wrapper listing TUI-visible workspaces from persistent state."""

    return TUIState(project_root).list_workspaces()
