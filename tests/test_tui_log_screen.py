from __future__ import annotations

import asyncio

from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


def test_tui_numeric_shortcut_0_opens_log_screen_and_global_shortcuts_remain(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.press("0")
            await pilot.pause()

            assert app._current_view == "log"
            assert app._views["log"].display is True
            assert app.query_one("#prompt-input", Input).has_focus
            assert t("nav_log") in _static_text(app.query_one("#view-title", Static))
            assert t("log_redaction_hint") in _static_text(app.query_one("#log-redaction-hint", Static))
            assert app.query_one("#log-message-input", TextArea) is not None
            assert app.query_one("#log-table", DataTable) is not None

            await pilot.press("9")
            await pilot.pause()

            assert app._current_view == "experiment"
            assert app.query_one("#prompt-input", Input).has_focus

    asyncio.run(scenario())


def test_log_screen_writes_lists_and_shows_redacted_report(tmp_path):
    secret = "sk-log-screen-secret"

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.press("0")
            await pilot.pause()

            app.query_one("#log-session-id-input", Input).value = "session-1"
            app.query_one("#log-message-input", TextArea).load_text(f"实验记录 api_key={secret}")

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
            await pilot.press("0")
            await pilot.pause()

            app.query_one("#log-message-input", TextArea).load_text("")
            await pilot.click("#log-write")
            await pilot.pause()

            assert t("log_empty_message") in _static_text(app.query_one("#log-status", Static))
            assert not (tmp_path / ".supermedicine" / "logs").exists()

    asyncio.run(scenario())


def test_log_screen_initial_empty_copy_and_safe_layout_are_visible(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.press("0")
            await pilot.pause()

            assert t("log_redaction_hint") in _static_text(app.query_one("#log-redaction-hint", Static))
            assert t("log_no_reports") in _static_text(app.query_one("#log-status", Static))
            assert app.query_one("#log-session-id-input", Input).value == ""
            assert app.query_one("#log-message-input", TextArea).text == ""
            assert app.query_one("#log-table", DataTable).row_count == 0
            assert t("log_write") in str(app.query_one("#log-write", Button).label)
            assert t("log_show") in str(app.query_one("#log-show", Button).label)

    asyncio.run(scenario())
