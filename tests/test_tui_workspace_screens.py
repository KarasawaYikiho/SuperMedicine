"""Tests for WorkspaceView real-time refresh — DBG-BUG-005."""

from __future__ import annotations

import asyncio
import inspect
import time

from textual.widgets import DataTable, Input, Static

from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t
from core.tui.screens.workspace_screen import WorkspaceView
from core.tui.screens.workspaces import WorkspaceScreenController
from core.workspace import WorkspaceManager


# ═══ Shared helpers ═══


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


async def _wait_for_tui_condition(pilot, condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause()
        if condition():
            return
    await pilot.pause()
    assert condition()


# ═══ Workspace refresh tests ═══


def test_workspace_view_exposes_refresh_view_data_hook():
    """WorkspaceView declares refresh_view_data method for activation refresh."""
    assert hasattr(WorkspaceView, "refresh_view_data")
    source = inspect.getsource(WorkspaceView.refresh_view_data)
    assert "_load_workspaces" in source
    assert "refreshed=True" in source


def test_workspace_view_compose_declares_required_widgets():
    """WorkspaceView.compose yields all required widgets including refresh button."""
    source = inspect.getsource(WorkspaceView.compose)

    assert 'id="workspace-table"' in source
    assert 'id="workspace-id-input"' in source
    assert 'id="workspace-create"' in source
    assert 'id="workspace-select"' in source
    assert 'id="workspace-refresh"' in source
    assert 'id="workspace-delete"' in source
    assert 'id="workspace-status"' in source


def test_workspace_view_uses_targeted_refresh_without_polling():
    """WorkspaceView uses refresh_view_data hook, not polling timer."""
    source = inspect.getsource(WorkspaceView)

    assert "refresh_view_data" in source
    assert "set_interval" not in source


def test_workspace_screen_loads_data_on_mount(tmp_path):
    """WorkspaceView._load_workspaces populates table on mount."""
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("test-ws")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 1
            assert "test-ws" in str(table.get_row_at(0))
            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_list") in status

    asyncio.run(scenario())


def test_workspace_screen_shows_empty_state_when_no_workspaces(tmp_path):
    """Empty workspace list shows localized empty-state message."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 0
            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_no_workspaces") in status

    asyncio.run(scenario())


def test_workspace_screen_refresh_view_data_updates_table(tmp_path):
    """refresh_view_data reloads workspace list from disk."""
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("initial-ws")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 1

            # Create a new workspace externally
            manager.initialize_workspace("external-ws")

            # Call refresh_view_data on the view
            view = app._views["workspace"]
            view.refresh_view_data()
            await pilot.pause()

            assert table.row_count == 2
            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_refreshed") in status

    asyncio.run(scenario())


def test_workspace_screen_refresh_button_triggers_reload(tmp_path):
    """Clicking the refresh button reloads workspace data."""
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("btn-ws")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 1

            # Add a workspace externally
            manager.initialize_workspace("added-ws")

            # Click the refresh button
            await pilot.click("#workspace-refresh")
            await pilot.pause()

            assert table.row_count == 2
            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_refreshed") in status

    asyncio.run(scenario())


def test_workspace_screen_refresh_preserves_selected_row(tmp_path):
    """After refresh, the previously selected row is re-selected."""
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("alpha")
    manager.initialize_workspace("beta")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 2

            # Select "beta" row
            beta_index = next(
                i for i in range(table.row_count)
                if "beta" in str(table.get_row_at(i))
            )
            table.move_cursor(row=beta_index, column=0)
            await pilot.pause()

            # Add workspace and refresh
            manager.initialize_workspace("gamma")
            view = app._views["workspace"]
            view.refresh_view_data()
            await pilot.pause()

            assert table.row_count == 3
            # The selected row key should still be beta
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            assert str(row_key.value) == "beta"

    asyncio.run(scenario())


def test_workspace_screen_create_then_refresh_shows_new_workspace(tmp_path):
    """Creating a workspace via UI input refreshes the table automatically."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 0

            # Type workspace ID and press Enter to submit
            input_widget = app.query_one("#workspace-id-input", Input)
            input_widget.value = "new-ws"
            input_widget.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            assert table.row_count == 1
            assert "new-ws" in str(table.get_row_at(0))
            status = _static_text(app.query_one("#workspace-status", Static))
            assert "已创建并选择工作区" in status

    asyncio.run(scenario())


def test_workspace_screen_create_empty_id_shows_error(tmp_path):
    """Creating a workspace with empty ID shows error status."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            input_widget = app.query_one("#workspace-id-input", Input)
            input_widget.focus()
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("error") in status

    asyncio.run(scenario())


def test_workspace_screen_select_updates_status(tmp_path):
    """Selecting a workspace via UI updates status message."""
    WorkspaceManager(tmp_path).initialize_workspace("sel-ws")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            input_widget = app.query_one("#workspace-id-input", Input)
            input_widget.value = "sel-ws"
            await pilot.click("#workspace-select")
            await pilot.pause()

            status = _static_text(app.query_one("#workspace-status", Static))
            assert "已选择工作区" in status

    asyncio.run(scenario())


def test_workspace_screen_refresh_view_data_shows_refreshed_prefix(tmp_path):
    """Refreshed status message uses refreshed prefix, not list prefix."""
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("refresh-prefix-ws")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            # Initial mount shows list prefix
            status_initial = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_list") in status_initial

            # Manual refresh shows refreshed prefix
            view = app._views["workspace"]
            view.refresh_view_data()
            await pilot.pause()

            status_refreshed = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_refreshed") in status_refreshed
            assert status_refreshed.startswith(t("workspace_refreshed"))

    asyncio.run(scenario())


def test_workspace_screen_refresh_empty_shows_refreshed_empty_message(tmp_path):
    """Refreshing an empty workspace list shows refreshed + empty state."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            view = app._views["workspace"]
            view.refresh_view_data()
            await pilot.pause()

            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_refreshed") in status
            assert t("workspace_no_workspaces") in status

    asyncio.run(scenario())


def test_workspace_screen_controller_list_returns_expected_format(tmp_path):
    """WorkspaceScreenController.list_workspaces returns dicts with required keys."""
    WorkspaceManager(tmp_path).initialize_workspace("ctrl-ws")
    controller = WorkspaceScreenController(project_root=tmp_path)

    workspaces = controller.list_workspaces()

    assert len(workspaces) == 1
    ws = workspaces[0]
    assert "id" in ws
    assert "path" in ws
    assert "metadata" in ws
    assert ws["id"] == "ctrl-ws"


def test_workspace_screen_compose_declares_hint_and_title_widgets():
    """WorkspaceView.compose yields title and hint Static widgets."""
    source = inspect.getsource(WorkspaceView.compose)

    assert 'classes="section-title"' in source
    assert 'id="workspace-create-hint"' in source
    assert 'id="workspace-action-hint"' in source


def test_workspace_screen_ctrl_n_focuses_input(tmp_path):
    """Ctrl+N keyboard shortcut focuses the workspace ID input."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            # Press ctrl+n to focus input
            await pilot.press("ctrl+n")
            await pilot.pause()

            input_widget = app.query_one("#workspace-id-input", Input)
            assert input_widget.has_focus

    asyncio.run(scenario())


def test_workspace_view_refresh_reads_external_workspace_with_condition_wait(tmp_path):
    """CI-stable: refresh after external workspace creation uses condition-based wait."""
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(180, 80)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 0

            # Create workspace externally
            WorkspaceManager(tmp_path).initialize_workspace("external-a")

            # Call refresh method directly and use condition-based wait
            workspace_view = app.query_one("WorkspaceView", WorkspaceView)
            workspace_view._load_workspaces(refreshed=True)
            await pilot.pause()
            await _wait_for_tui_condition(pilot, lambda: table.row_count == 1, timeout=5.0)

            assert table.row_count == 1
            assert table.get_row("external-a")[0] == "external-a"
            status = _static_text(app.query_one("#workspace-status", Static))
            assert t("workspace_refreshed") in status

    asyncio.run(scenario())
