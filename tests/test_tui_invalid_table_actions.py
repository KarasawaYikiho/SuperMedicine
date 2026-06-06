from __future__ import annotations

import asyncio
import time

import yaml
from textual.widgets import Button, DataTable, Input, Select, Static

from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t
from core.workspace import WorkspaceManager


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


def _assert_red_error_with_reason(status: Static, reason: str) -> None:
    rendered = _static_text(status)
    has_class = getattr(status, "has_class", None)
    classes = {str(class_name) for class_name in getattr(status, "classes", set())}

    assert t("error") in rendered
    assert reason in rendered
    assert "status-error" in classes or (
        callable(has_class) and has_class("status-error")
    )


def _assert_tool_empty_run_error(status: Static) -> None:
    rendered = _static_text(status)
    has_class = getattr(status, "has_class", None)
    classes = {str(class_name) for class_name in getattr(status, "classes", set())}

    assert t("error") in rendered
    assert t("tool_no_tools") in rendered
    assert "status-error" in classes or (
        callable(has_class) and has_class("status-error")
    )


async def _wait_for_tui_condition(pilot, condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause()
        if condition():
            return
    await pilot.pause()
    assert condition()


def test_tool_run_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("tool")
            await pilot.pause()

            view = app._views["tool"]
            view.query_one("#tool-workspace-select", Select).value = "study-a"
            view._load_tools()
            table = view.query_one("#tool-table", DataTable)
            assert table.row_count == 0

            await pilot.click("#tool-run")
            await pilot.pause()

            assert app._current_view == "tool"
            assert app._views["tool"].display is True
            assert app.query_one("#prompt-input", Input) is not None
            _assert_tool_empty_run_error(view.query_one("#tool-status", Static))

            select = view.query_one("#tool-workspace-select", Select)
            stale_same_workspace_event = type(
                "StaleSelectChangedEvent",
                (),
                {"select": select},
            )()
            view.on_select_changed(stale_same_workspace_event)
            await pilot.pause()
            _assert_tool_empty_run_error(view.query_one("#tool-status", Static))

            view._load_tools()
            await pilot.pause()
            _assert_tool_empty_run_error(view.query_one("#tool-status", Static))

    asyncio.run(scenario())


def test_tool_screen_scans_candidates_without_tool_id_input(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "plugins" / "tools" / "python_stats"
    source.mkdir(parents=True)
    (source / "plugin.yaml").write_text(
        yaml.safe_dump(
            {"name": "python-stats", "language": "python", "entry": "main.py"},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "main.py").write_text("print('ok')\n", encoding="utf-8")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("tool")
            await pilot.pause()

            view = app._views["tool"]
            assert list(view.query("#tool-id-input")) == []
            view.query_one("#tool-workspace-select", Select).value = "study-a"
            await _wait_for_tui_condition(
                pilot,
                lambda: view.query_one("#tool-workspace-select", Select).value
                == "study-a",
            )
            view.query_one("#tool-scan", Button).focus()
            await pilot.click("#tool-scan")

            table = view.query_one("#tool-table", DataTable)
            await _wait_for_tui_condition(
                pilot,
                lambda: getattr(view, "_table_mode") == "candidates"
                and table.row_count == 1,
            )
            assert table.row_count == 1
            assert table.get_row_at(0)[2] == "python-stats"

    asyncio.run(scenario())


def test_paper_enrich_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("paper")
            await pilot.pause()

            view = app._views["paper"]
            view.query_one("#paper-workspace-select", Select).value = "study-a"
            view._load_papers()
            table = view.query_one("#paper-table", DataTable)
            assert table.row_count == 0

            await pilot.click("#paper-enrich")
            await pilot.pause()

            assert app._current_view == "paper"
            assert app._views["paper"].display is True
            assert app.query_one("#prompt-input", Input) is not None
            _assert_red_error_with_reason(
                view.query_one("#paper-status", Static), t("paper_no_papers")
            )

    asyncio.run(scenario())


def test_log_show_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 0

            await pilot.click("#log-show")
            await pilot.pause()

            assert app._current_view == "log"
            assert app._views["log"].display is True
            assert app.query_one("#prompt-input", Input) is not None
            _assert_red_error_with_reason(
                app.query_one("#log-status", Static), t("log_no_reports")
            )

    asyncio.run(scenario())


def test_experience_delete_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experience")
            await pilot.pause()

            view = app._views["experience"]
            view.query_one("#exp-workspace-select", Select).value = "study-a"
            view._load_experiences()
            table = view.query_one("#exp-table", DataTable)
            assert table.row_count == 0

            await pilot.click("#exp-delete")
            await pilot.pause()

            assert app._current_view == "experience"
            assert app._views["experience"].display is True
            assert app.query_one("#prompt-input", Input) is not None
            _assert_red_error_with_reason(
                view.query_one("#exp-status", Static), t("experience_no_records")
            )

    asyncio.run(scenario())
