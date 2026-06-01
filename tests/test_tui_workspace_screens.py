from __future__ import annotations

import inspect

import pytest

from core.tui.screens.workspaces import WorkspaceScreenController
from core.tui.i18n import t
from core.tui.screens.dialog_screen import DialogView
from core.tui.screens.tool_screen import ToolView
from core.tui.screens.workspace_screen import WorkspaceView


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


def test_workspace_screen_create_does_not_enter_kernel_or_llm(tmp_path, monkeypatch):
    imported: list[str] = []
    original_import = __import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("core.kernel", "core.llm_client", "core.llm_providers")):
            imported.append(name)
            raise AssertionError(f"TUI workspace create must not import Kernel/LLM module: {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded_import)

    result = WorkspaceScreenController(tmp_path).create_workspace("direct-tui")

    assert result["id"] == "direct-tui"
    assert result["selected"] is True
    assert (tmp_path / "workspaces" / "direct-tui" / "workspace.yaml").is_file()
    assert imported == []


def test_workspace_screen_empty_state_is_chinese_and_non_destructive(tmp_path):
    controller = WorkspaceScreenController(tmp_path)

    assert controller.list_workspaces() == []
    assert t("workspace_no_workspaces") == "暂无工作区，请先创建"
    assert not (tmp_path / "workspaces").exists()


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


def test_workspace_view_delete_does_not_auto_confirm_source():
    delete_source = inspect.getsource(WorkspaceView._delete_workspace)

    assert "confirm=workspace_id" not in delete_source
    assert "delete:" in delete_source
    assert "confirmed_workspace_id" in delete_source


def test_workspace_delete_copy_describes_exact_irreversible_confirmation():
    assert "完全一致" in t("workspace_delete_requires_confirm")
    assert "不可恢复" in t("workspace_delete_requires_confirm")


def test_workspace_view_error_path_redacts_secret_and_notifies(monkeypatch, tmp_path):
    secret = "sk-workspace-error-secret"
    messages: list[str] = []

    class FakeStatus:
        def update(self, message):
            messages.append(str(message))

        def remove_class(self, *classes):
            pass

        def add_class(self, class_name):
            pass

    class FakeApp:
        def notify(self, message, severity=None):
            messages.append(str(message))

    class TestWorkspaceView(WorkspaceView):
        @property
        def app(self):
            return FakeApp()

        def query_one(self, *args, **kwargs):
            return FakeStatus()

    view = TestWorkspaceView(tmp_path)

    view._set_error(RuntimeError(f"failed api_key={secret}"))

    rendered = "\n".join(messages)
    assert t("error") in rendered
    assert secret not in rendered
    assert "[已隐藏]" in rendered


def test_business_views_set_deterministic_non_empty_reload_statuses():
    workspace_loader = inspect.getsource(WorkspaceView._load_workspaces)
    tool_loader = inspect.getsource(ToolView._load_tools)
    dialog_loader = inspect.getsource(DialogView._load_dialog_history)

    assert "workspace_list" in workspace_loader
    assert "len(workspaces)" in workspace_loader
    assert "tool_list" in tool_loader
    assert "tool_count" in tool_loader
    assert "dialog_refreshed" in dialog_loader
    assert "len(events)" in dialog_loader
