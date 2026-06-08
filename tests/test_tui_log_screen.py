from __future__ import annotations

import asyncio

from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.log_report import LogReportStore
from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t
from core.tui.screens.log_screen import LogReportView


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


def test_tui_explicit_switch_opens_log_screen_and_global_shortcuts_remain(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            assert app._current_view == "log"
            assert app._views["log"].display is True
            assert app.query_one("#prompt-input", Input).has_focus
            assert t("nav_log") in _static_text(app.query_one("#view-title", Static))
            assert t("log_redaction_hint") in _static_text(
                app.query_one("#log-redaction-hint", Static)
            )
            assert app.query_one("#log-message-input", TextArea) is not None
            assert app.query_one("#log-table", DataTable) is not None

            app.action_switch_view("experiment")
            await pilot.pause()

            assert app._current_view == "experiment"
            assert app.query_one("#prompt-input", Input).has_focus

    asyncio.run(scenario())


def test_log_screen_writes_lists_and_shows_redacted_report(tmp_path):
    secret = "sk-log-screen-secret"

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            app.query_one("#log-session-id-input", Input).value = "session-1"
            app.query_one("#log-message-input", TextArea).load_text(
                f"实验记录 api_key={secret}"
            )

            await pilot.click("#log-write")
            await pilot.pause()

            log_dir = tmp_path / ".supermedicine" / "logs"
            log_files = list(log_dir.glob("*.json"))
            assert len(log_files) == 1
            saved_text = log_files[0].read_text(encoding="utf-8")
            assert secret not in saved_text
            assert "[REDACTED]" in saved_text
            assert t("log_list") in _static_text(app.query_one("#log-status", Static))

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 1
            table.move_cursor(row=0, column=0)
            await pilot.click("#log-show")
            await pilot.pause()

            detail = _static_text(app.query_one("#log-detail", Static))
            assert t("log_loaded") in detail
            assert "session-1" in detail
            assert secret not in detail
            assert "[REDACTED]" in detail

    asyncio.run(scenario())


def test_log_screen_empty_message_sets_status_without_creating_report(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            app.query_one("#log-message-input", TextArea).load_text("")
            await pilot.click("#log-write")
            await pilot.pause()

            assert t("log_empty_message") in _static_text(
                app.query_one("#log-status", Static)
            )
            assert not (tmp_path / ".supermedicine" / "logs").exists()

    asyncio.run(scenario())


def test_log_screen_initial_empty_copy_and_safe_layout_are_visible(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            assert t("log_redaction_hint") in _static_text(
                app.query_one("#log-redaction-hint", Static)
            )
            assert t("log_no_reports") in _static_text(
                app.query_one("#log-status", Static)
            )
            assert app.query_one("#log-session-id-input", Input).value == ""
            assert app.query_one("#log-message-input", TextArea).text == ""
            assert app.query_one("#log-table", DataTable).row_count == 0
            assert t("log_write") in str(app.query_one("#log-write", Button).label)
            assert t("log_show") in str(app.query_one("#log-show", Button).label)

    asyncio.run(scenario())


def test_log_screen_severity_text_uses_distinct_styles():
    cases = {
        "【Error】 failed": "red",
        "【Warning】 check this": "yellow",
        "【Info】 started": "cyan",
        "【Debug】 details": "blue",
        "【Success】 saved": "green",
    }

    for message, style_token in cases.items():
        rendered = LogReportView._severity_text(message)

        assert str(rendered) == message
        assert style_token in str(rendered.style)


def test_log_screen_empty_and_refreshed_status_include_zero_statistics(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            initial_status = _static_text(app.query_one("#log-status", Static))
            assert t("log_no_reports") in initial_status
            assert "entries=0" in initial_status
            assert "Error=0" in initial_status
            assert "Warning=0" in initial_status
            assert "Info=0" in initial_status
            assert "Debug=0" in initial_status
            assert "Success=0" in initial_status

            await pilot.click("#log-refresh")
            await pilot.pause()

            refreshed_status = _static_text(app.query_one("#log-status", Static))
            assert t("log_refreshed") in refreshed_status
            assert t("log_no_reports") in refreshed_status
            assert "entries=0" in refreshed_status

    asyncio.run(scenario())


def test_log_screen_populated_table_and_detail_statistics_match_selected_entry(
    tmp_path,
):
    store = LogReportStore(tmp_path)
    store.write("alpha failed", session_id="alpha", severity="Error")
    store.write("alpha saved", session_id="alpha", severity="Success")
    store.write("beta warning", session_id="beta", severity="Warning")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 3
            status = _static_text(app.query_one("#log-status", Static))
            assert f"{t('log_refreshed')}: 3" in status
            assert "entries=3" in status
            assert "Error=1" in status
            assert "Warning=1" in status
            assert "Success=1" in status

            beta_row = next(
                index
                for index in range(table.row_count)
                if "beta" in str(table.get_row_at(index)[3])
            )
            table.move_cursor(row=beta_row, column=0)
            await pilot.click("#log-show")
            await pilot.pause()

            detail = _static_text(app.query_one("#log-detail", Static))
            assert t("log_loaded") in detail
            assert "beta" in detail
            assert "Severity: Warning" in detail
            assert "Statistics: entries=1" in detail
            assert "Warning=1" in detail
            assert "Error=0" in detail
            assert "Success=0" in detail
            assert "alpha failed" not in detail
            assert "alpha saved" not in detail

    asyncio.run(scenario())


def test_log_screen_refresh_button_reads_entries_created_after_enter(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 0

            LogReportStore(tmp_path).write("late log", session_id="late")
            await pilot.click("#log-refresh")
            await pilot.pause()

            assert table.row_count == 1
            assert "late" in str(table.get_row_at(0))
            assert t("log_refreshed") in _static_text(app.query_one("#log-status", Static))

    asyncio.run(scenario())


def test_log_screen_uses_targeted_refresh_hook_without_timer_polling():
    import inspect

    source = inspect.getsource(LogReportView)

    assert "refresh_view_data" in source
    assert "set_interval" not in source
    assert "Timer" not in source


def test_log_screen_severity_label_uses_explicit_mapping_for_each_level():
    cases = {
        "Error": "red",
        "Warning": "yellow",
        "Info": "cyan",
        "Debug": "blue",
        "Success": "green",
    }

    for severity, style_token in cases.items():
        rendered = LogReportView._severity_label(severity)

        assert str(rendered) == f"[{severity}]"
        assert style_token in str(rendered.style)
