"""Log report view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.log_report import LogReportStore
from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


class LogReportView(Vertical):
    """Minimal standalone page for writing and reading redacted log reports."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("log_title"), classes="section-title")
        yield Static(t("log_redaction_hint"), id="log-redaction-hint")
        yield Input(placeholder=t("log_session_id"), id="log-session-id-input")
        yield TextArea.code_editor("", language="markdown", id="log-message-input")
        with Horizontal(classes="form-row"):
            yield Button(t("log_write"), id="log-write", classes="btn btn-primary")
            yield Button(t("log_show"), id="log-show", classes="btn btn-secondary")
            yield Button(t("refresh"), id="log-refresh", classes="btn btn-secondary")
        yield DataTable(id="log-table", cursor_type="row")
        yield Static("", id="log-detail")
        yield Static("", id="log-status")

    @property
    def store(self) -> LogReportStore:
        return LogReportStore(self._project_root)

    def on_mount(self) -> None:
        self.refresh_logs()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "log-write":
            self._write_log()
        elif event.button.id == "log-show":
            self._show_selected_log()
        elif event.button.id == "log-refresh":
            self.refresh_logs()

    def refresh_logs(self) -> None:
        table = self.query_one("#log-table", DataTable)
        table.clear(columns=True)
        table.add_columns("文件", "报告 ID", "会话", "时间", "摘要")
        try:
            reports = self.store.list()
            for report in reports:
                table.add_row(
                    str(report.get("file") or ""),
                    str(report.get("report_id") or ""),
                    str(report.get("session_id") or ""),
                    str(report.get("created_at") or ""),
                    str(report.get("message") or "")[:80],
                )
            self._set_status(f"{t('log_list')}: {len(reports)}" if reports else t("log_no_reports"))
        except Exception as exc:
            self._set_error(exc)

    def _write_log(self) -> None:
        message = self.query_one("#log-message-input", TextArea).text.strip()
        if not message:
            self._set_status(t("log_empty_message"))
            return
        session_id = self.query_one("#log-session-id-input", Input).value.strip() or None
        try:
            result = self.store.write(message, session_id=session_id)
            self._set_status(f"{t('log_saved')}: {result.get('file')}")
            self.refresh_logs()
        except Exception as exc:
            self._set_error(exc)

    def _show_selected_log(self) -> None:
        table = self.query_one("#log-table", DataTable)
        if table.cursor_row is None:
            self._set_status(t("no_selection"))
            return
        row = table.get_row_at(table.cursor_row)
        file_name = str(row[0])
        try:
            report = self.store.show(file_name)
            detail = (
                f"{t('log_loaded')}: {report.get('file')}\n"
                f"ID: {report.get('report_id')}\n"
                f"{t('log_session_id')}: {report.get('session_id') or ''}\n"
                f"{t('log_message')}:\n{report.get('message') or ''}"
            )
            self.query_one("#log-detail", Static).update(str(redact_sensitive(detail)))
            self._set_status(t("log_loaded"))
        except Exception as exc:
            self._set_error(exc)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#log-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        self._set_status(f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}")


LogScreen = LogReportView
