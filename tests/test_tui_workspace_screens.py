from __future__ import annotations

import pytest

from core.tui.screens.workspaces import WorkspaceScreenController


def _allow_delete_policy(tmp_path):
    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True)
    (policies / "default.yaml").write_text(
        "agent_id: delta\nrole: test\npermissions:\n  allowed:\n    - action: 'workspace.delete'\n      scope: '*'\n",
        encoding="utf-8",
    )


def test_workspace_screen_create_select_and_recent_state(tmp_path):
    controller = WorkspaceScreenController(tmp_path)

    created = controller.create_workspace("study-a")
    selected = controller.select_workspace("study-a")

    assert created["label"] == "工作区：study-a"
    assert selected["message"] == "已选择工作区"
    assert controller.recent_workspace("study-a") == "study-a"
    assert controller.list_workspaces()[0]["id"] == "study-a"


def test_workspace_screen_delete_requires_exact_confirmation(tmp_path):
    _allow_delete_policy(tmp_path)
    controller = WorkspaceScreenController(tmp_path)
    controller.create_workspace("study-a")

    with pytest.raises(ValueError, match="工作区 ID"):
        controller.delete_workspace("study-a", confirm="wrong")

    assert (tmp_path / "workspaces" / "study-a").exists()


def test_workspace_screen_hard_delete_uses_policy_and_removes_workspace(tmp_path):
    _allow_delete_policy(tmp_path)
    controller = WorkspaceScreenController(tmp_path)
    controller.create_workspace("study-a")

    result = controller.delete_workspace("study-a", confirm="study-a")

    assert result["status"] == "deleted"
    assert result["message"] == "工作区已硬删除"
    assert not (tmp_path / "workspaces" / "study-a").exists()
    assert (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").exists()
