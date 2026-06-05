from __future__ import annotations

import asyncio

from textual.widgets import DataTable, Input, Select, Static

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


def test_tool_run_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.press("6")
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
            _assert_red_error_with_reason(
                view.query_one("#tool-status", Static), t("tool_no_tools")
            )

    asyncio.run(scenario())


def test_paper_enrich_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.press("4")
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
            await pilot.press("0")
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
            await pilot.press("5")
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
