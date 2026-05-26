from __future__ import annotations

import os

import pytest
import yaml

from core.path_safety import PathOutsideProjectRootError
from core.workspace import (
    InvalidWorkspaceId,
    SESSION_STATE_FILE,
    WORKSPACE_DIRECTORIES,
    WorkspaceManager,
    validate_workspace_id,
)


@pytest.mark.parametrize("slug", ["study", "study-1", "abc123", "a"])
def test_valid_workspace_slug_is_accepted(slug):
    assert validate_workspace_id(slug) == slug


@pytest.mark.parametrize(
    "slug",
    ["", "Study", "study_1", "study 1", "-study", "study-", "../study", "study/one"],
)
def test_invalid_workspace_slug_is_rejected(slug):
    with pytest.raises(InvalidWorkspaceId):
        validate_workspace_id(slug)


def test_initialize_workspace_creates_expected_layout_only_under_workspaces(tmp_path):
    manager = WorkspaceManager(tmp_path)

    info = manager.initialize_workspace("trial-1")

    assert info.path == (tmp_path / "workspaces" / "trial-1").resolve()
    assert (tmp_path / "workspaces" / "trial-1" / "workspace.yaml").is_file()
    for directory in WORKSPACE_DIRECTORIES:
        assert (tmp_path / "workspaces" / "trial-1" / directory).is_dir()
    assert not (tmp_path / ".supermedicine").exists()


def test_workspace_metadata_is_stored_and_reloaded(tmp_path):
    manager = WorkspaceManager(tmp_path)

    created = manager.initialize_workspace("meta-study")
    loaded = manager.get_workspace("meta-study")

    assert loaded.id == "meta-study"
    assert loaded.path == created.path
    assert loaded.metadata.id == "meta-study"
    assert loaded.metadata.created_at == created.metadata.created_at
    assert manager.list_workspaces() == [loaded]

    raw = yaml.safe_load((loaded.path / "workspace.yaml").read_text(encoding="utf-8"))
    assert raw["id"] == "meta-study"


def test_workspace_symlink_target_inside_project_is_accepted(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink not supported on this platform")

    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    internal_target = tmp_path / "internal-target"
    internal_target.mkdir()
    link = workspaces / "linked-study"
    try:
        link.symlink_to(internal_target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    manager = WorkspaceManager(tmp_path)
    info = manager.initialize_workspace("linked-study")

    assert info.path == internal_target.resolve()
    assert (internal_target / "workspace.yaml").is_file()


def test_workspace_symlink_target_outside_project_is_rejected(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink not supported on this platform")

    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    outside_target = tmp_path.parent / f"{tmp_path.name}-outside-workspace"
    outside_target.mkdir()
    link = workspaces / "escaped-study"
    try:
        link.symlink_to(outside_target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    manager = WorkspaceManager(tmp_path)
    with pytest.raises(PathOutsideProjectRootError):
        manager.initialize_workspace("escaped-study")


def test_recent_selection_state_is_stored_only_in_workspace_session_path(tmp_path):
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("session-study")

    state_path = manager.save_recent_selection("session-study")

    expected = (
        tmp_path
        / "workspaces"
        / "session-study"
        / ".supermedicine"
        / "sessions"
        / SESSION_STATE_FILE
    ).resolve()
    assert state_path == expected
    assert manager.load_recent_selection("session-study") == "session-study"
    assert not (tmp_path / ".supermedicine").exists()


def test_no_implicit_cli_or_global_state_is_created(tmp_path):
    manager = WorkspaceManager(tmp_path)

    manager.initialize_workspace("explicit-study")

    assert not (tmp_path / ".supermedicine").exists()
    assert not (tmp_path / "workspace.yaml").exists()
    assert (tmp_path / "workspaces" / "explicit-study" / "workspace.yaml").is_file()
