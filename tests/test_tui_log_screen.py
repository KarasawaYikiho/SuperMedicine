"""Tests for TUI log screen refresh and session-level aggregation display."""

from __future__ import annotations

import asyncio
import inspect
import time

from textual.widgets import DataTable, Input, Static, TextArea

from core.log_report import LogReportStore
from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t
from core.tui.screens.log_screen import LogReportView


# ═══ Shared helpers ═══


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


async def _wait_for_condition(pilot, condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause()
        if condition():
            return
    await pilot.pause()
    assert condition()


# ═══ Log screen refresh tests ═══


def test_log_screen_refresh_view_data_populates_table_from_store(tmp_path):
    """refresh_view_data loads entries from store when view becomes active."""
    store = LogReportStore(tmp_path)
    store.write("pre-existing log", session_id="pre-session", severity="Info")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 1
            assert "pre-session" in str(table.get_row_at(0))
            assert t("log_list") in _static_text(app.query_one("#log-status", Static))

    asyncio.run(scenario())


def test_log_screen_refresh_after_external_write_updates_table(tmp_path):
    """External writes appear after refresh_view_data is called."""
    store = LogReportStore(tmp_path)

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 0

            store.write("external entry", session_id="ext-session", severity="Info")

            view = app._views["log"]
            view.refresh_view_data()
            await pilot.pause()

            assert table.row_count == 1
            assert "ext-session" in str(table.get_row_at(0))
            assert t("log_refreshed") in _static_text(app.query_one("#log-status", Static))

    asyncio.run(scenario())


def test_log_screen_auto_follow_toggle_announces_state_change(tmp_path):
    """Auto-follow button toggle updates status with announcement."""
    store = LogReportStore(tmp_path)
    for i in range(3):
        store.write(f"entry {i}", session_id="follow-test", severity="Info")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            view = app._views["log"]
            assert view._auto_follow is True

            await pilot.click("#log-auto-follow")
            await pilot.pause()

            assert view._auto_follow is False
            status = _static_text(app.query_one("#log-status", Static))
            assert "自动跟随：关" in status

    asyncio.run(scenario())


def test_log_screen_auto_follow_scrolls_to_last_entry(tmp_path):
    """With auto-follow on, cursor moves to the last entry after refresh."""
    store = LogReportStore(tmp_path)
    for i in range(5):
        store.write(f"entry {i}", session_id="scroll-test", severity="Info")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 5
            assert table.cursor_row == 4

    asyncio.run(scenario())


def test_log_screen_multi_session_aggregated_statistics_in_status(tmp_path):
    """Status bar shows aggregated statistics across all sessions."""
    store = LogReportStore(tmp_path)
    store.write("alpha error", session_id="stat-alpha", severity="Error")
    store.write("alpha info", session_id="stat-alpha", severity="Info")
    store.write("beta warning", session_id="stat-beta", severity="Warning")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            status = _static_text(app.query_one("#log-status", Static))
            assert "entries=3" in status
            assert "Error=1" in status
            assert "Warning=1" in status
            assert "Info=1" in status

    asyncio.run(scenario())


def test_log_screen_detail_statistics_match_selected_session_entry(tmp_path):
    """Detail view statistics count only the selected entry."""
    store = LogReportStore(tmp_path)
    store.write("alpha error", session_id="detail-alpha", severity="Error")
    store.write("alpha info", session_id="detail-alpha", severity="Info")
    store.write("beta success", session_id="detail-beta", severity="Success")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 3

            # Find the beta row and select it
            beta_row = next(
                i for i in range(table.row_count)
                if "detail-beta" in str(table.get_row_at(i))
            )
            table.move_cursor(row=beta_row, column=0)
            await pilot.click("#log-show")
            await pilot.pause()

            detail = _static_text(app.query_one("#log-detail", Static))
            assert t("log_loaded") in detail
            assert "detail-beta" in detail
            assert "Statistics: entries=1" in detail
            assert "Success=1" in detail
            assert "Error=0" in detail

    asyncio.run(scenario())


def test_log_screen_write_with_session_refreshes_and_displays_new_entry(tmp_path):
    """Writing from the UI refreshes the table with the new entry."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            app.query_one("#log-session-id-input", Input).value = "ui-write-session"
            app.query_one("#log-message-input", TextArea).load_text("UI log entry")

            await pilot.click("#log-write")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 1
            assert "ui-write-session" in str(table.get_row_at(0))
            status = _static_text(app.query_one("#log-status", Static))
            assert t("log_saved") in status

            # Verify persisted to disk
            log_dir = tmp_path / ".supermedicine" / "logs"
            log_files = list(log_dir.glob("*.json"))
            assert len(log_files) == 1

    asyncio.run(scenario())


def test_log_screen_write_without_session_routes_to_tui_application(tmp_path):
    """Write without session_id routes to tui-application session."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            app.query_one("#log-message-input", TextArea).load_text("no session entry")

            await pilot.click("#log-write")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 1
            assert "tui-application" in str(table.get_row_at(0))

    asyncio.run(scenario())


def test_log_screen_severity_text_redacts_secrets_in_displayed_detail(tmp_path):
    """Detail view redacts sensitive data in messages."""
    secret = "sk-log-detail-secret"
    store = LogReportStore(tmp_path)
    store.write(f"api failure api_key={secret}", session_id="redact-detail", severity="Error")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            table.move_cursor(row=0, column=0)
            await pilot.click("#log-show")
            await pilot.pause()

            detail = _static_text(app.query_one("#log-detail", Static))
            assert secret not in detail
            assert "[REDACTED]" in detail

    asyncio.run(scenario())


def test_log_screen_preview_text_truncates_long_messages():
    """_preview_text truncates messages exceeding the summary limit."""
    long_msg = "a" * 200
    preview = LogReportView._preview_text(long_msg, limit=50)

    assert len(preview) <= 51  # 50 + ellipsis
    assert preview.endswith("…")


def test_log_screen_wrapped_detail_text_line_wraps_long_lines():
    """_wrapped_detail_text splits long lines at line_limit."""
    long_line = "b" * 400
    wrapped = LogReportView._wrapped_detail_text(long_line, line_limit=100)

    for line in wrapped.splitlines():
        assert len(line) <= 100


def test_log_screen_statistics_text_format():
    """_statistics_text formats severity counts as expected."""
    stats = {
        "entry_count": 5,
        "severity_counts": {
            "Error": 2,
            "Warning": 1,
            "Info": 1,
            "Debug": 0,
            "Success": 1,
        },
    }
    text = LogReportView._statistics_text(stats)

    assert "entries=5" in text
    assert "Error=2" in text
    assert "Warning=1" in text
    assert "Info=1" in text
    assert "Debug=0" in text
    assert "Success=1" in text


def test_log_screen_statistics_text_handles_empty_statistics():
    """_statistics_text handles missing or empty statistics gracefully."""
    text = LogReportView._statistics_text({})

    assert "entries=0" in text
    assert "Error=0" in text


def test_log_screen_entry_severity_uses_explicit_over_detected():
    """_entry_severity prefers explicit severity field over message detection."""
    entry = {"severity": "Success", "raw_message": "operation failed"}

    assert LogReportView._entry_severity(entry) == "Success"


def test_log_screen_entry_severity_falls_back_to_detection():
    """_entry_severity detects severity from message when explicit is empty."""
    entry = {"severity": "", "raw_message": "operation failed"}

    assert LogReportView._entry_severity(entry) == "Error"


def test_log_screen_entry_message_formats_with_severity_label():
    """_entry_message wraps the message with a severity label."""
    entry = {"raw_message": "saved data", "severity": "Success"}
    message = LogReportView._entry_message(entry, severity="Success")

    assert message == "【Success】 saved data"


def test_log_screen_storage_location_displays_log_and_audit_paths(tmp_path):
    """Storage location display shows log and audit file paths."""
    store = LogReportStore(tmp_path)
    store.write("test", session_id="path-test")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            location = _static_text(app.query_one("#log-storage-location", Static))
            assert "存储位置" in location
            assert "Log/Report=" in location
            assert "Audit=" in location
            assert "audit.jsonl" in location
            assert "logs" in location

    asyncio.run(scenario())


def test_log_screen_show_on_no_selection_shows_error(tmp_path):
    """Clicking show with invalid cursor position shows error status."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            view = app._views["log"]
            table = view.query_one("#log-table", DataTable)
            assert table.row_count == 0

            view._show_selected_log()

            status = _static_text(app.query_one("#log-status", Static))
            assert t("error") in status
            assert t("log_no_reports") in status

    asyncio.run(scenario())


def test_log_screen_refresh_preserves_cursor_position_when_auto_follow_off(tmp_path):
    """With auto-follow off, cursor position is preserved across refreshes."""
    store = LogReportStore(tmp_path)
    for i in range(5):
        store.write(f"entry {i}", session_id="cursor-test", severity="Info")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            view = app._views["log"]
            table = app.query_one("#log-table", DataTable)

            # Disable auto-follow
            view._set_auto_follow(False)
            table.move_cursor(row=1, column=0)
            await pilot.pause()

            # Add a new entry and refresh
            store.write("new entry", session_id="cursor-test", severity="Info")
            view.refresh_logs(refreshed=True)
            await pilot.pause()

            # Cursor should stay near position 1, not jump to end
            assert table.cursor_row <= 2


    asyncio.run(scenario())


def test_log_screen_compose_declares_required_widgets():
    """LogReportView.compose yields all required widgets."""
    compose_source = inspect.getsource(LogReportView.compose)

    assert 'id="log-redaction-hint"' in compose_source
    assert 'id="log-action-hint"' in compose_source
    assert 'id="log-session-id-input"' in compose_source
    assert 'id="log-message-input"' in compose_source
    assert 'id="log-write"' in compose_source
    assert 'id="log-show"' in compose_source
    assert 'id="log-refresh"' in compose_source
    assert 'id="log-auto-follow"' in compose_source
    assert 'id="log-table"' in compose_source
    assert 'id="log-detail"' in compose_source
    assert 'id="log-status"' in compose_source


def test_log_screen_uses_targeted_refresh_without_polling():
    """LogReportView uses refresh_view_data hook, not polling timer."""
    source = inspect.getsource(LogReportView)

    assert "refresh_view_data" in source
    assert "set_interval" not in source
    assert "Timer" not in source


def test_log_screen_store_property_creates_fresh_store(tmp_path):
    """The store property creates a new LogReportStore each call."""
    view = LogReportView(project_root=tmp_path)

    store1 = view.store
    store2 = view.store

    assert store1 is not store2
    assert store1.project_dir == store2.project_dir
