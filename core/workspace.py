"""Workspace identity and storage layout primitives.

This module is intentionally additive: it provides explicit workspace path,
metadata, and session-state helpers without changing CLI/API/plugin/action/
permission/security behavior or adding implicit workspace selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
from typing import Any
from uuid import uuid4

import yaml

from core.path_safety import (
    PathOutsideProjectRootError,
    resolve_project_root,
    validate_path_in_project_root,
)
from core.time_utils import utc_now


WORKSPACES_DIR = "workspaces"
WORKSPACE_METADATA_FILE = "workspace.yaml"
WORKSPACE_METADATA_VERSION = 1
SESSION_STATE_FILE = "tui_recent_selection.yaml"
_STAGING_PREFIX = ".sm-staging-"
_TOMBSTONE_PREFIX = ".sm-tombstone-"

WORKSPACE_DIRECTORIES: tuple[str, ...] = (
    ".supermedicine",
    ".supermedicine/checkpoints",
    ".supermedicine/sessions",
    ".supermedicine/rag/local",
    "papers/originals",
    "papers/extracted",
    "papers/metadata",
    "papers/imports",
    "notes",
    "outputs",
    "tools/python",
    "tools/r",
)

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class WorkspaceError(ValueError):
    """Base exception for workspace identity/storage failures."""


class InvalidWorkspaceId(WorkspaceError):
    """Raised when a workspace id is not a valid slug."""


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a requested workspace has not been initialized."""


@dataclass(frozen=True)
class WorkspaceMetadata:
    """Metadata persisted in each workspace's ``workspace.yaml`` file."""

    id: str
    created_at: str
    updated_at: str
    metadata_version: int = WORKSPACE_METADATA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a YAML-serializable representation."""

        return {
            "id": self.id,
            "metadata_version": self.metadata_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceMetadata":
        """Build metadata from a loaded YAML mapping."""

        workspace_id = validate_workspace_id(str(data.get("id", "")))
        return cls(
            id=workspace_id,
            metadata_version=int(
                data.get("metadata_version", WORKSPACE_METADATA_VERSION)
            ),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


@dataclass(frozen=True)
class WorkspaceInfo:
    """Loaded workspace record."""

    id: str
    path: Path
    metadata: WorkspaceMetadata


def validate_workspace_id(workspace_id: str) -> str:
    """Validate and return a workspace slug.

    Workspace ids are lowercase ASCII slug values using letters, digits, and
    hyphens.  They cannot be empty, contain path separators, start/end with a
    hyphen, or contain traversal segments.
    """

    if not isinstance(workspace_id, str):
        raise InvalidWorkspaceId("Workspace id must be a string slug")

    if not _SLUG_RE.fullmatch(workspace_id):
        raise InvalidWorkspaceId(
            "Workspace id must be a lowercase slug using letters, digits, and hyphens"
        )

    return workspace_id


class WorkspaceManager:
    """Explicit manager for project-local workspace storage."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = resolve_project_root(project_root)
        self.workspaces_root = validate_path_in_project_root(
            WORKSPACES_DIR, self.project_root
        )

    def workspace_anchor(self, workspace_id: str) -> Path:
        """Return the project-relative anchor path ``workspaces/<id>``."""

        slug = validate_workspace_id(workspace_id)
        return self.project_root / WORKSPACES_DIR / slug

    def workspace_path(self, workspace_id: str) -> Path:
        """Resolve ``workspaces/<id>`` and ensure its target stays in-project."""

        anchor = self.workspace_anchor(workspace_id)
        return validate_path_in_project_root(anchor, self.project_root)

    def metadata_path(self, workspace_id: str) -> Path:
        """Return the guarded metadata file path for a workspace."""

        return validate_path_in_project_root(
            self.workspace_path(workspace_id) / WORKSPACE_METADATA_FILE,
            self.project_root,
        )

    def initialize_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """Create the expected workspace layout and UTF-8 metadata."""

        slug = validate_workspace_id(workspace_id)
        workspace = self.workspace_path(slug)
        workspace.mkdir(parents=True, exist_ok=True)

        for directory in WORKSPACE_DIRECTORIES:
            path = validate_path_in_project_root(
                workspace / directory, self.project_root
            )
            path.mkdir(parents=True, exist_ok=True)

        metadata_file = self.metadata_path(slug)
        now = utc_now()
        if metadata_file.exists():
            existing = self.load_metadata(slug)
            metadata = WorkspaceMetadata(
                id=slug,
                metadata_version=existing.metadata_version,
                created_at=existing.created_at or now,
                updated_at=now,
            )
        else:
            metadata = WorkspaceMetadata(id=slug, created_at=now, updated_at=now)

        metadata_file.write_text(
            yaml.safe_dump(metadata.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return WorkspaceInfo(id=slug, path=workspace, metadata=metadata)

    create_workspace = initialize_workspace

    def initialize_workspace_atomic(
        self, workspace_id: str, *, name: str | None = None
    ) -> WorkspaceInfo:
        """Publish a fully built new workspace with one same-volume rename."""

        slug = validate_workspace_id(workspace_id)
        target = self.workspace_path(slug)
        if target.exists():
            return self.get_workspace(slug)
        self.workspaces_root.mkdir(parents=True, exist_ok=True)
        staging = validate_path_in_project_root(
            self.workspaces_root / f"{_STAGING_PREFIX}{slug}-{uuid4().hex}",
            self.project_root,
        )
        staging.mkdir()
        for directory in WORKSPACE_DIRECTORIES:
            validate_path_in_project_root(
                staging / directory, self.project_root
            ).mkdir(parents=True)
        now = utc_now()
        metadata: dict[str, Any] = WorkspaceMetadata(
            id=slug, created_at=now, updated_at=now
        ).to_dict()
        if name is not None:
            metadata["display_name"] = name
        (staging / WORKSPACE_METADATA_FILE).write_text(
            yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        try:
            staging.replace(target)
        except OSError:
            if target.exists():
                shutil.rmtree(staging, ignore_errors=True)
                return self.get_workspace(slug)
            raise
        return self.get_workspace(slug)

    def delete_workspace_atomic(self, workspace: Path) -> None:
        """Hide a workspace atomically before best-effort physical cleanup."""

        target = validate_path_in_project_root(workspace, self.project_root)
        tombstone = validate_path_in_project_root(
            self.workspaces_root
            / f"{_TOMBSTONE_PREFIX}{target.name}-{uuid4().hex}",
            self.project_root,
        )
        target.replace(tombstone)
        if tombstone.is_dir() and not tombstone.is_symlink():
            shutil.rmtree(tombstone)
        else:
            tombstone.unlink()

    def recover_atomic_transactions(self) -> None:
        """Remove unpublished staging and already-hidden delete tombstones."""

        if not self.workspaces_root.is_dir():
            return
        for entry in self.workspaces_root.iterdir():
            if not entry.name.startswith((_STAGING_PREFIX, _TOMBSTONE_PREFIX)):
                continue
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink(missing_ok=True)

    def load_metadata(self, workspace_id: str) -> WorkspaceMetadata:
        """Load a workspace's UTF-8 YAML metadata."""

        metadata_file = self.metadata_path(workspace_id)
        if not metadata_file.is_file():
            raise WorkspaceNotFoundError(
                f"Workspace metadata not found: {metadata_file}"
            )

        data = yaml.safe_load(metadata_file.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise WorkspaceError(
                f"Workspace metadata must be a mapping: {metadata_file}"
            )
        metadata = WorkspaceMetadata.from_dict(data)
        expected_id = validate_workspace_id(workspace_id)
        if metadata.id != expected_id:
            raise WorkspaceError(
                f"Workspace metadata id mismatch: expected {expected_id}, found {metadata.id}"
            )
        return metadata

    def get_workspace(self, workspace_id: str) -> WorkspaceInfo:
        """Load a single initialized workspace."""

        slug = validate_workspace_id(workspace_id)
        workspace = self.workspace_path(slug)
        metadata = self.load_metadata(slug)
        return WorkspaceInfo(id=slug, path=workspace, metadata=metadata)

    show_workspace = get_workspace

    def list_workspaces(self) -> list[WorkspaceInfo]:
        """List initialized workspaces with valid slug directory/link names."""

        if not self.workspaces_root.exists():
            return []

        workspaces: list[WorkspaceInfo] = []
        for entry in sorted(self.workspaces_root.iterdir(), key=lambda item: item.name):
            try:
                validate_workspace_id(entry.name)
                workspaces.append(self.get_workspace(entry.name))
            except (
                InvalidWorkspaceId,
                WorkspaceNotFoundError,
                WorkspaceError,
                PathOutsideProjectRootError,
            ):
                continue
        return workspaces

    def session_state_path(self, workspace_id: str) -> Path:
        """Return the guarded TUI/session state path inside a workspace."""

        return validate_path_in_project_root(
            self.workspace_path(workspace_id)
            / ".supermedicine"
            / "sessions"
            / SESSION_STATE_FILE,
            self.project_root,
        )

    def save_recent_selection(
        self,
        workspace_id: str,
        selected_workspace_id: str | None = None,
    ) -> Path:
        """Persist recent TUI workspace selection only in workspace session state."""

        slug = validate_workspace_id(workspace_id)
        selected = validate_workspace_id(selected_workspace_id or slug)
        state_path = self.session_state_path(slug)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "recent_workspace_id": selected,
            "updated_at": utc_now(),
        }
        state_path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return state_path

    def load_recent_selection(self, workspace_id: str) -> str | None:
        """Load recent TUI workspace selection from workspace session state."""

        state_path = self.session_state_path(workspace_id)
        if not state_path.is_file():
            return None
        data = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise WorkspaceError(
                f"Workspace session state must be a mapping: {state_path}"
            )
        recent = data.get("recent_workspace_id")
        return validate_workspace_id(str(recent)) if recent is not None else None


def workspace_path(workspace_id: str, project_root: str | Path | None = None) -> Path:
    """Convenience wrapper returning a guarded workspace path."""

    return WorkspaceManager(project_root).workspace_path(workspace_id)


resolve_workspace_path = workspace_path


def initialize_workspace(
    workspace_id: str,
    project_root: str | Path | None = None,
) -> WorkspaceInfo:
    """Convenience wrapper creating a workspace layout."""

    return WorkspaceManager(project_root).initialize_workspace(workspace_id)


init_workspace = initialize_workspace


def list_workspaces(project_root: str | Path | None = None) -> list[WorkspaceInfo]:
    """Convenience wrapper listing initialized workspaces."""

    return WorkspaceManager(project_root).list_workspaces()


def get_workspace(
    workspace_id: str,
    project_root: str | Path | None = None,
) -> WorkspaceInfo:
    """Convenience wrapper loading a single workspace."""

    return WorkspaceManager(project_root).get_workspace(workspace_id)


show_workspace = get_workspace


def save_recent_selection(
    workspace_id: str,
    selected_workspace_id: str | None = None,
    project_root: str | Path | None = None,
) -> Path:
    """Convenience wrapper for workspace-local TUI recent selection state."""

    return WorkspaceManager(project_root).save_recent_selection(
        workspace_id,
        selected_workspace_id,
    )


def load_recent_selection(
    workspace_id: str,
    project_root: str | Path | None = None,
) -> str | None:
    """Convenience wrapper loading workspace-local TUI recent selection state."""

    return WorkspaceManager(project_root).load_recent_selection(workspace_id)
