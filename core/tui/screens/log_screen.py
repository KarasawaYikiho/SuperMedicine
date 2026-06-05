"""Log report view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.log_report import LogReportStore, detect_log_severity, format_log_message
from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


_SUMMARY_LIMIT = 96
_DETAIL_LINE_LIMIT = 160


_SEVERITY_STYLES = {
    "Error": "bold red",
    "Warning": "yellow",
    "Info": "cyan",
    "Debug": "dim blue",
    "Success": "green",
}


class LogReportView(Vertical):
    """Minimal standalone page for writing and reading redacted log reports."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("log_title"), classes="section-title")
        yield Static(t("log_redaction_hint"), id="log-redaction-hint")
        yield Static(t("log_action_hint"), id="log-action-hint", classes="hint")
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
            self.refresh_logs(refreshed=True)

    def refresh_logs(self, *, refreshed: bool = False) -> str:
        table = self.query_one("#log-table", DataTable)
        table.clear(columns=True)
        table.add_columns("文件", "报告 ID", "条目 ID", "会话", "时间", "级别", "摘要")
        try:
            entries = self.store.list_entries()
            for entry in entries:
                severity = self._entry_severity(entry)
                message = self._entry_message(entry, severity=severity)
                table.add_row(
                    str(entry.get("file") or ""),
                    str(entry.get("report_id") or ""),
                    str(entry.get("entry_id") or ""),
                    str(entry.get("session_id") or ""),
                    str(entry.get("created_at") or ""),
                    self._severity_label(severity),
                    self._severity_text(self._preview_text(message), severity=severity),
                )
            stats_text = self._statistics_text(
                self.store.statistics_for_entries(entries)
            )
            label = t("log_refreshed") if refreshed else t("log_list")
            status_text = (
                f"{label}: {len(entries)}；{stats_text}"
                if entries
                else (
                    f"{t('log_refreshed')}：{t('log_no_reports')}；{stats_text}"
                    if refreshed
                    else f"{t('log_no_reports')}；{stats_text}"
                )
            )
            self._set_status(status_text)
            return status_text
        except Exception as exc:
            self._set_error(exc)
            return f"{t('error')}: {t('safe_error_hint')}"

    def _write_log(self) -> None:
        message = self.query_one("#log-message-input", TextArea).text.strip()
        if not message:
            self._set_status(t("log_empty_message"))
            return
        session_id = (
            self.query_one("#log-session-id-input", Input).value.strip() or None
        )
        try:
            self.store.write(message, session_id=session_id)
            self.app.notify(t("log_saved"))
            list_status = self.refresh_logs()
            self._set_status(f"{t('log_saved')}；{list_status}")
        except Exception as exc:
            self._set_error(exc)

    def _show_selected_log(self) -> None:
        table = self.query_one("#log-table", DataTable)
        if table.row_count == 0:
            self._set_status(f"{t('error')}: {t('log_no_reports')}，无法执行该操作")
            return
        if (
            table.cursor_row is None
            or table.cursor_row < 0
            or table.cursor_row >= table.row_count
        ):
            self._set_status(f"{t('error')}: {t('no_selection')}，无法执行该操作")
            return
        try:
            row = table.get_row_at(table.cursor_row)
        except Exception:
            self._set_status(f"{t('error')}: {t('no_selection')}，无法执行该操作")
            return
        if len(row) < 3:
            self._set_status(f"{t('error')}: {t('no_selection')}，无法执行该操作")
            return
        file_name = str(row[0])
        entry_id = str(row[2])
        try:
            entries = self.store.list_entries(file_name=file_name)
            selected_entry = next(
                (
                    entry
                    for entry in entries
                    if str(entry.get("entry_id") or "") == entry_id
                ),
                None,
            )
            if selected_entry is None:
                self._set_status(f"{t('error')}: {t('no_selection')}，无法执行该操作")
                return
            severity = self._entry_severity(selected_entry)
            message = self._wrapped_detail_text(
                self._entry_message(selected_entry, severity=severity)
            )
            stats_text = self._statistics_text(
                self.store.statistics_for_entries([selected_entry])
            )
            detail = (
                f"{t('log_loaded')}: {selected_entry.get('file')}\n"
                f"ID: {selected_entry.get('report_id')}\n"
                f"Entry ID: {selected_entry.get('entry_id') or ''}\n"
                f"{t('log_session_id')}: {selected_entry.get('session_id') or ''}\n"
                f"Severity: {severity}\n"
                f"Statistics: {stats_text}\n"
                f"{t('log_message')}:\n{message}"
            )
            self.query_one("#log-detail", Static).update(
                self._severity_text(str(redact_sensitive(detail)), severity=severity)
            )
            self._set_status(t("log_loaded"))
        except Exception as exc:
            self._set_error(exc)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#log-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        message = (
            f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}"
        )
        self._set_status(message)
        self.app.notify(message, severity="error")

    @staticmethod
    def _entry_severity(entry: dict[str, Any]) -> str:
        explicit_severity = str(entry.get("severity") or "").strip()
        if explicit_severity in _SEVERITY_STYLES:
            return explicit_severity
        raw_message = str(entry.get("raw_message") or entry.get("message") or "")
        return detect_log_severity(raw_message)

    @staticmethod
    def _entry_message(entry: dict[str, Any], *, severity: str | None = None) -> str:
        return format_log_message(
            str(entry.get("raw_message") or entry.get("message") or ""),
            severity=severity or entry.get("severity"),
        )

    @staticmethod
    def _severity_label(severity: str) -> Text:
        safe_severity = severity if severity in _SEVERITY_STYLES else "Info"
        return Text(
            f"[{safe_severity}]",
            style=_SEVERITY_STYLES.get(safe_severity, _SEVERITY_STYLES["Info"]),
        )

    @staticmethod
    def _severity_text(message: str, *, severity: str | None = None) -> Text:
        safe_message = str(redact_sensitive(message))
        detected_severity = (
            severity
            if severity in _SEVERITY_STYLES
            else detect_log_severity(safe_message)
        )
        return Text(
            safe_message,
            style=_SEVERITY_STYLES.get(detected_severity, _SEVERITY_STYLES["Info"]),
        )

    @staticmethod
    def _preview_text(message: str, *, limit: int = _SUMMARY_LIMIT) -> str:
        compact = " ".join(str(redact_sensitive(message)).split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: max(0, limit - 1)].rstrip()}…"

    @staticmethod
    def _wrapped_detail_text(
        message: str, *, line_limit: int = _DETAIL_LINE_LIMIT
    ) -> str:
        safe_message = str(redact_sensitive(message))
        wrapped_lines: list[str] = []
        for line in safe_message.splitlines() or [""]:
            if len(line) <= line_limit:
                wrapped_lines.append(line)
                continue
            for index in range(0, len(line), line_limit):
                wrapped_lines.append(line[index : index + line_limit])
        return "\n".join(wrapped_lines)

    @staticmethod
    def _statistics_text(statistics: dict[str, Any]) -> str:
        severity_counts = (
            statistics.get("severity_counts") if isinstance(statistics, dict) else {}
        )
        if not isinstance(severity_counts, dict):
            severity_counts = {}
        entry_count = (
            statistics.get("entry_count", 0) if isinstance(statistics, dict) else 0
        )
        parts = [f"entries={int(entry_count or 0)}"]
        for severity in ("Error", "Warning", "Info", "Debug", "Success"):
            parts.append(f"{severity}={int(severity_counts.get(severity, 0) or 0)}")
        return ", ".join(parts)


LogScreen = LogReportView
