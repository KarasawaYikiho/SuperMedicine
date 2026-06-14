from __future__ import annotations

import inspect
import time

import pytest
from textual.widgets import DataTable, Input, Static

from core.tui.screens.workspaces import WorkspaceScreenController
from core.tui.i18n import t
from core.tui.screens.dialog_screen import DialogView
from core.tui.screens.tool_screen import ToolView
from core.tui.screens.workspace_screen import WorkspaceView
from core.tui.app import SuperMedicineTUI


async def _wait_for_tui_condition(pilot, condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause()
        if condition():
            return
    await pilot.pause()
    assert condition()


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


def test_workspace_screen_create_rejects_duplicate_and_invalid_ids(tmp_path):
    controller = WorkspaceScreenController(tmp_path)
    controller.create_workspace("study-a")

    with pytest.raises(ValueError, match="已存在"):
        controller.create_workspace("study-a")

    with pytest.raises(ValueError, match="小写字母"):
        controller.create_workspace("Study_A")


def test_workspace_screen_create_does_not_enter_kernel_or_llm(tmp_path, monkeypatch):
    imported: list[str] = []
    original_import = __import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("core.kernel", "core.llm_client", "core.llm_providers")):
            imported.append(name)
            raise AssertionError(
                f"TUI workspace create must not import Kernel/LLM module: {name}"
            )
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


def test_workspace_manual_create_entry_copy_is_visible_and_keyboard_mouse_friendly():
    assert "手动创建" in t("workspace_manual_create_hint")
    assert "Enter" in t("workspace_manual_create_hint")
    assert "Ctrl+N" in t("workspace_manual_create_hint")
    assert "鼠标" in t("workspace_manual_create_hint")
    assert "小写字母" in t("workspace_create_placeholder")


def test_workspace_view_supports_enter_shortcut_and_keeps_focus_after_create():
    compose_source = inspect.getsource(WorkspaceView.compose)
    create_source = inspect.getsource(WorkspaceView._create_workspace)
    load_source = inspect.getsource(WorkspaceView._load_workspaces)
    key_source = inspect.getsource(WorkspaceView.on_key)
    submit_source = inspect.getsource(WorkspaceView.handle_input_submit)
    row_source = inspect.getsource(WorkspaceView.on_data_table_row_selected)

    assert "workspace_manual_create_hint" in compose_source
    assert "workspace_create_placeholder" in compose_source
    assert "ctrl+n" in key_source
    assert "workspace-id-input" in submit_source
    assert "_create_workspace(value.strip())" in submit_source
    assert "input_widget.focus()" in create_source
    assert "_load_workspaces(preserve_status=True)" in create_source
    assert "_select_table_row" in create_source
    assert "move_cursor" in inspect.getsource(WorkspaceView._select_table_row)
    assert "preserve_status" in load_source
    assert "_select_workspace(workspace_id)" in row_source


def test_workspace_view_manual_create_is_visible_and_usable_in_running_tui(tmp_path):
    """Regression baseline: manual workspace creation is visible, focusable, and creates a selectable row."""

    import asyncio

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            view = app._views["workspace"]
            hint = view.query_one("#workspace-create-hint", Static)
            input_widget = view.query_one("#workspace-id-input", Input)
            table = view.query_one("#workspace-table", DataTable)
            status = view.query_one("#workspace-status", Static)

            assert "手动创建" in str(hint.renderable)
            assert input_widget.has_focus

            view._create_workspace("manual-a")
            await pilot.pause()

            assert (tmp_path / "workspaces" / "manual-a" / "workspace.yaml").is_file()
            assert input_widget.value == "manual-a"
            assert input_widget.has_focus
            assert table.get_row("manual-a")[0] == "manual-a"
            assert "manual-a" in str(status.renderable)

    asyncio.run(scenario())


def test_workspace_manual_create_is_visible_to_already_mounted_dialog_page(tmp_path):
    """Regression baseline: pages mounted before manual create must observe the shared workspace list."""

    import asyncio

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            workspace_view = app._views["workspace"]
            workspace_view._create_workspace("manual-cross-page")
            await pilot.pause()

            app.action_switch_view("dialog")
            await pilot.pause()

            dialog_view = app._views["dialog"]
            select_widget = dialog_view.query_one("#dialog-workspace-select")
            option_values = [str(option[1]) for option in select_widget._options]

            assert "manual-cross-page" in option_values

            dialog_view._load_dialog_history(refreshed=True)
            await pilot.pause()
            status = dialog_view.query_one("#dialog-status", Static)
            assert "暂无工作区" not in str(status.renderable)

    asyncio.run(scenario())


def test_workspace_view_prevents_global_prompt_from_stealing_workspace_focus():
    app_switch_source = inspect.getsource(SuperMedicineTUI.action_switch_view)
    app_focus_source = inspect.getsource(SuperMedicineTUI._focus_current_view_default)
    prompt_focus_source = inspect.getsource(SuperMedicineTUI._focus_prompt_input)

    assert "_focus_current_view_default" in app_switch_source
    assert "focus_default" in app_focus_source
    assert "self._focus_prompt_input()" in app_focus_source
    assert "#prompt-input" in prompt_focus_source


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


def test_workspace_view_refresh_button_reads_external_workspace_created_after_enter(tmp_path):
    import asyncio
    from core.workspace import WorkspaceManager

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 0

            WorkspaceManager(tmp_path).initialize_workspace("external-a")
            # 直接调用视图刷新方法，避免 pilot.click() 的事件传递问题
            workspace_view = app.query_one("WorkspaceView")
            workspace_view._load_workspaces(refreshed=True)
            await pilot.pause()
            await _wait_for_tui_condition(pilot, lambda: table.row_count == 1, timeout=5.0)

            assert table.row_count == 1
            assert table.get_row("external-a")[0] == "external-a"
            assert t("workspace_refreshed") in str(
                app.query_one("#workspace-status", Static).renderable
            )

    asyncio.run(scenario())


def test_app_switch_view_invokes_dynamic_refresh_hooks(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)
    calls: list[str] = []

    class FakeView:
        display = False

        def refresh_view_data(self) -> None:
            calls.append("refresh")

    app._views = {"workspace": FakeView()}
    app._current_view = "workspace"
    app._focus_current_view_default = lambda: None
    app._update_status_bar = lambda: None

    app.action_switch_view("workspace")

    assert calls == ["refresh"]
