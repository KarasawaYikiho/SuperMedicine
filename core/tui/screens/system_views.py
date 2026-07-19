"""Converged TUI views for the system domain."""
# ruff: noqa: E402,F401,F811

from __future__ import annotations

# --- migrated from llm_screen.py ---
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.redaction import redact_sensitive
from core.services import LLMService
from core.tui.app import apply_status_style
from core.tui.i18n import t


class LLMScreenController:
    """Thin TUI facade over the shared LLM configuration manager."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.service = LLMService(self.project_root, restore_on_startup=True)

    def list_providers(self) -> dict[str, Any]:
        result = self.service.list_providers()
        data = self.service.legacy_result(result)
        return data.get("providers", {}) if isinstance(data, dict) else {}

    def current_provider(self) -> dict[str, Any]:
        result = self.service.show_provider()
        data = self.service.legacy_result(result)
        return data if isinstance(data, dict) else {}

    def readiness(self) -> dict[str, Any]:
        current = self.current_provider()
        provider = str(current.get("provider") or "")
        if not provider:
            return {"ok": False, "provider": "", "message": t("llm_not_ready")}
        validation = self.service.validate_provider(provider)
        if validation.ok:
            return {"ok": True, "provider": provider, "message": t("llm_ready")}
        return {
            "ok": False,
            "provider": provider,
            "message": str(
                redact_sensitive(
                    validation.error.message if validation.error else t("llm_not_ready")
                )
            ),
        }

    def add_provider(
        self,
        provider: str,
        *,
        base_url: str,
        api_key: str,
        model: str,
        api_format: str = "",
        set_current: bool = True,
    ) -> dict[str, Any]:
        values = {
            "base_url": base_url.strip(),
            "api_key": api_key.strip(),
            "model": model.strip(),
        }
        if api_format.strip():
            values["api_format"] = api_format.strip()
        return self.service.legacy_result(
            self.service.add_provider(provider, values, set_current=set_current)
        )

    def switch_provider(self, provider: str) -> dict[str, Any]:
        return self.service.legacy_result(self.service.switch_provider(provider))

    def delete_provider(self, provider: str) -> dict[str, Any]:
        return self.service.legacy_result(self.service.delete_provider(provider))

    def save_exit_state(self) -> dict[str, Any]:
        return self.service.legacy_result(self.service.save_exit_state())

    def provider_is_valid(self, provider: str) -> bool:
        return self.service.validate_provider(provider).ok

    def validate_provider(self, provider: str) -> dict[str, Any]:
        return self.service.legacy_result(self.service.validate_provider(provider))


class LLMView(Vertical):
    """View for adding, selecting, and switching LLM providers."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._controller: LLMScreenController | None = None

    def compose(self) -> ComposeResult:
        yield Static(t("llm_title"), classes="section-title")
        yield Static("", id="llm-current")
        yield Static(t("llm_secret_hidden"), id="llm-secret-hint")
        yield Static(t("llm_action_hint"), id="llm-action-hint", classes="hint")
        yield DataTable(id="llm-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Select(
                [], prompt=t("llm_missing_selection"), id="llm-provider-select"
            )
            yield Button(
                t("llm_switch_provider"), id="llm-switch", classes="btn btn-primary"
            )
            yield Button(
                t("llm_delete_provider"), id="llm-delete", classes="btn btn-danger"
            )
            yield Button(t("refresh"), id="llm-refresh", classes="btn btn-secondary")
        with Vertical(id="llm-form"):
            yield Input(placeholder=t("llm_provider_name"), id="llm-provider-input")
            yield Input(placeholder=t("llm_base_url"), id="llm-base-url-input")
            yield Input(placeholder=t("llm_model"), id="llm-model-input")
            yield Input(
                placeholder=t("llm_api_key"), password=True, id="llm-api-key-input"
            )
            yield Input(placeholder=t("llm_api_format_hint"), id="llm-api-format-input")
            yield Button(t("llm_add_provider"), id="llm-add", classes="btn btn-primary")
        yield Static("", id="llm-status")

    @property
    def controller(self) -> LLMScreenController:
        if self._controller is None:
            self._controller = LLMScreenController(self._project_root)
        return self._controller

    def on_mount(self) -> None:
        self.refresh_llm_state()

    def refresh_llm_state(self) -> None:
        table = self.query_one("#llm-table", DataTable)
        select = self.query_one("#llm-provider-select", Select)
        current_widget = self.query_one("#llm-current", Static)
        table.clear(columns=True)
        table.add_columns(
            t("llm_provider"), t("llm_base_url"), t("llm_model"), t("dashboard_status")
        )

        providers = self.controller.list_providers()
        readiness = self.controller.readiness()
        current_provider = str(readiness.get("provider") or "")
        options: list[tuple[str, str]] = []

        for name, config in providers.items():
            provider_name = str(name)
            if not isinstance(config, dict):
                config = {}
            options.append((provider_name, provider_name))
            status = (
                t("llm_ready")
                if self.controller.provider_is_valid(provider_name)
                else t("llm_not_ready")
            )
            table.add_row(
                provider_name,
                str(config.get("base_url") or ""),
                str(config.get("model") or ""),
                status,
            )

        select.set_options(options)
        if current_provider and any(value == current_provider for _, value in options):
            select.value = current_provider

        current_label = current_provider or t("no_selection")
        state_label = t("llm_ready") if readiness.get("ok") else t("llm_not_ready")
        current_widget.update(f"{t('llm_current')}: {current_label} · {state_label}")
        if not providers:
            self._set_status(t("llm_no_providers"))
        else:
            self._set_status(str(readiness.get("message") or state_label))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "llm-refresh":
            self.refresh_llm_state()
            self._set_status(t("llm_refreshed"))
        elif event.button.id == "llm-add":
            self._add_provider_from_form()
        elif event.button.id == "llm-switch":
            self._switch_selected_provider()
        elif event.button.id == "llm-delete":
            self._delete_selected_provider()

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "llm-api-key-input":
            self._add_provider_from_form()

    def _add_provider_from_form(self) -> None:
        provider = self.query_one("#llm-provider-input", Input).value.strip()
        if not provider:
            self._set_status(t("llm_missing_provider"))
            return

        result = self.controller.add_provider(
            provider,
            base_url=self.query_one("#llm-base-url-input", Input).value,
            api_key=self.query_one("#llm-api-key-input", Input).value,
            model=self.query_one("#llm-model-input", Input).value,
            api_format=self.query_one("#llm-api-format-input", Input).value,
            set_current=True,
        )
        self.query_one("#llm-api-key-input", Input).value = ""
        if result.get("ok"):
            self._set_status(f"{t('llm_provider_added')}: {provider.lower()}")
            self.app.notify(f"{t('llm_provider_added')}: {provider.lower()}")
            self.refresh_llm_state()
            self._set_status(f"{t('llm_provider_added')}: {provider.lower()}")
        else:
            self._set_status(self._safe_error_message(result))

    def _switch_selected_provider(self) -> None:
        select = self.query_one("#llm-provider-select", Select)
        if select.value is None or select.value == Select.BLANK:
            self._set_status(t("llm_missing_selection"))
            return
        provider = str(select.value)
        result = self.controller.switch_provider(provider)
        if result.get("ok"):
            self._set_status(f"{t('llm_provider_switched')}: {provider}")
            self.app.notify(f"{t('llm_provider_switched')}: {provider}")
            self.refresh_llm_state()
            self._set_status(f"{t('llm_provider_switched')}: {provider}")
        else:
            self._set_status(self._safe_error_message(result))

    def _delete_selected_provider(self) -> None:
        select = self.query_one("#llm-provider-select", Select)
        if select.value is None or select.value == Select.BLANK:
            self._set_status(t("llm_missing_selection"))
            return
        provider = str(select.value)
        result = self.controller.delete_provider(provider)
        if result.get("ok"):
            self._set_status(f"{t('llm_provider_deleted')}: {provider}")
            self.app.notify(f"{t('llm_provider_deleted')}: {provider}")
            self.refresh_llm_state()
        else:
            self._set_status(self._safe_error_message(result))

    def _safe_error_message(self, result: dict[str, Any]) -> str:
        error = result.get("error", {}) if isinstance(result, dict) else {}
        message = (
            str(error.get("message") or t("error"))
            if isinstance(error, dict)
            else t("error")
        )
        return f"{t('error')}: {redact_sensitive(message) or t('safe_error_hint')}"

    def _set_status(self, message: str) -> None:
        status = self.query_one("#llm-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def on_unmount(self) -> None:
        try:
            self.controller.save_exit_state()
        except Exception:
            pass


LLMScreen = LLMView


# --- migrated from log_screen.py ---
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.log_report import detect_log_severity
from core.log_report_models import format_log_message
from core.redaction import redact_sensitive
from core.services import PermissionLogSystemService
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
        self._auto_follow = True
        self._suppress_follow_detection = False

    def compose(self) -> ComposeResult:
        yield Static(t("log_title"), classes="section-title")
        yield Static(t("log_redaction_hint"), id="log-redaction-hint")
        yield Static(t("log_action_hint"), id="log-action-hint", classes="hint")
        yield Static("", id="log-storage-location", classes="hint")
        yield Input(placeholder=t("log_session_id"), id="log-session-id-input")
        yield TextArea.code_editor("", language="markdown", id="log-message-input")
        with Horizontal(classes="form-row"):
            yield Button(t("log_write"), id="log-write", classes="btn btn-primary")
            yield Button(t("log_show"), id="log-show", classes="btn btn-secondary")
            yield Button(t("refresh"), id="log-refresh", classes="btn btn-secondary")
            yield Button(
                "自动跟随：开", id="log-auto-follow", classes="btn btn-secondary"
            )
        yield DataTable(id="log-table", cursor_type="row")
        yield Static("", id="log-detail")
        yield Static("", id="log-status")

    @property
    def service(self) -> PermissionLogSystemService:
        return PermissionLogSystemService(self._project_root)

    def on_mount(self) -> None:
        self.refresh_logs()

    def refresh_view_data(self) -> None:
        """Refresh log list/output when the view becomes active."""

        self.refresh_logs(refreshed=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "log-write":
            self._write_log()
        elif event.button.id == "log-show":
            self._show_selected_log()
        elif event.button.id == "log-refresh":
            self.refresh_logs(refreshed=True)
        elif event.button.id == "log-auto-follow":
            self._toggle_auto_follow()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "log-table":
            return
        if self._suppress_follow_detection:
            return
        table = event.data_table
        if table.row_count and table.cursor_row < max(0, table.row_count - 1):
            self._set_auto_follow(False, announce=True)

    def refresh_logs(self, *, refreshed: bool = False) -> str:
        table = self.query_one("#log-table", DataTable)
        previous_cursor = table.cursor_row if table.row_count else None
        previous_row_count = table.row_count
        table.clear(columns=True)
        table.add_columns(
            "文件", "报告 ID", "条目 ID", "会话", "时间", "级别", "存储位置", "摘要"
        )
        try:
            storage = self.service.require_data(self.service.log_storage())
            self._set_storage_location(storage)
            entries = self.service.require_data(self.service.list_log_entries())
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
                    self._preview_text(str(entry.get("path") or ""), limit=72),
                    self._severity_text(self._preview_text(message), severity=severity),
                )
            self._restore_log_position(
                table,
                previous_cursor=previous_cursor,
                previous_row_count=previous_row_count,
                new_row_count=len(entries),
            )
            stats_text = self._statistics_text(
                self.service.require_data(self.service.log_statistics(entries))
            )
            label = t("log_refreshed") if refreshed else t("log_list")
            follow_text = "自动跟随：开" if self._auto_follow else "自动跟随：关"
            status_text = (
                f"{label}: {len(entries)}；{follow_text}；{stats_text}"
                if entries
                else (
                    f"{t('log_refreshed')}：{t('log_no_reports')}；{follow_text}；{stats_text}"
                    if refreshed
                    else f"{t('log_no_reports')}；{follow_text}；{stats_text}"
                )
            )
            self._set_status(status_text)
            return status_text
        except Exception as exc:
            self._set_error(exc)
            return f"{t('error')}: {t('safe_error_hint')}"

    def _restore_log_position(
        self,
        table: DataTable,
        *,
        previous_cursor: int | None,
        previous_row_count: int,
        new_row_count: int,
    ) -> None:
        if new_row_count <= 0:
            return
        if self._auto_follow:
            self._move_cursor_preserving_follow(table, new_row_count - 1)
            self._scroll_table_end(table)
            return
        if previous_cursor is not None:
            self._move_cursor_preserving_follow(
                table, min(previous_cursor, new_row_count - 1)
            )
            return
        if previous_row_count:
            self._move_cursor_preserving_follow(
                table, min(previous_row_count - 1, new_row_count - 1)
            )

    @staticmethod
    def _move_table_cursor(table: DataTable, row: int) -> None:
        try:
            table.move_cursor(row=row, column=0)
        except Exception:
            pass

    @staticmethod
    def _scroll_table_end(table: DataTable) -> None:
        scroll_end = getattr(table, "scroll_end", None)
        if callable(scroll_end):
            try:
                scroll_end(animate=False)
            except TypeError:
                scroll_end()

    def _toggle_auto_follow(self) -> None:
        self._set_auto_follow(not self._auto_follow, announce=True)
        if self._auto_follow:
            table = self.query_one("#log-table", DataTable)
            if table.row_count:
                self._move_cursor_preserving_follow(table, table.row_count - 1)
                self._scroll_table_end(table)

    def _move_cursor_preserving_follow(self, table: DataTable, row: int) -> None:
        self._suppress_follow_detection = True
        try:
            self._move_table_cursor(table, row)
        finally:
            self._suppress_follow_detection = False

    def _set_auto_follow(self, enabled: bool, *, announce: bool = False) -> None:
        if self._auto_follow == enabled and not announce:
            return
        self._auto_follow = enabled
        label = "自动跟随：开" if enabled else "自动跟随：关"
        try:
            self.query_one("#log-auto-follow", Button).label = label
        except Exception:
            pass
        if announce:
            self._set_status(
                f"{label}；{'新日志将自动滚动到底部' if enabled else '手动浏览历史时保持当前位置'}"
            )

    def _write_log(self) -> None:
        message = self.query_one("#log-message-input", TextArea).text.strip()
        if not message:
            self._set_status(t("log_empty_message"))
            return
        session_id = (
            self.query_one("#log-session-id-input", Input).value.strip() or None
        )
        try:
            self.service.require_data(
                self.service.write_log(message, session_id=session_id)
            )
            self._set_storage_location(
                self.service.require_data(
                    self.service.log_storage(session_id=session_id)
                )
            )
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
            entries = self.service.require_data(
                self.service.list_log_entries(file_name=file_name)
            )
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
            storage = self.service.require_data(
                self.service.log_storage(file_name=file_name)
            )
            self._set_storage_location(storage)
            stats_text = self._statistics_text(
                self.service.require_data(
                    self.service.log_statistics([selected_entry])
                )
            )
            detail = (
                f"{t('log_loaded')}: {selected_entry.get('file')}\n"
                f"Storage: {selected_entry.get('path') or storage.get('current_file') or ''}\n"
                f"Audit: {storage.get('audit_file') or ''}\n"
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

    def _set_storage_location(self, storage: dict[str, Any]) -> None:
        location = self.query_one("#log-storage-location", Static)
        safe_storage = redact_sensitive(storage)
        current = str(
            safe_storage.get("current_file") or safe_storage.get("log_dir") or ""
        )
        audit = str(safe_storage.get("audit_file") or "")
        message = f"存储位置: Log/Report={current}；Audit={audit}"
        location.update(str(redact_sensitive(message)))

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


# --- migrated from permission_screen.py ---
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.redaction import redact_sensitive
from core.services import PermissionLogSystemService
from core.tui.app import apply_status_style
PERMISSION_RISK_NOTICE = (
    "安全边界：默认使用保守模式。完全访问模式必须输入 FULL 显式确认；"
    "它只使用当前进程/用户已经拥有的系统权限，不会静默提权、不会绕过 OS 权限。"
    "如果系统权限不足，请通过管理员权限、UAC 或系统安全提示显式授权后重试。"
)


class PermissionScreenController:
    """TUI facade over the shared file-access configuration service."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.service = PermissionLogSystemService(self.project_root)

    def current_config(self) -> dict[str, Any]:
        return self.service.require_data(self.service.permission_status())

    def set_mode(self, mode: str, *, confirmation_text: str = "") -> dict[str, Any]:
        return self.service.require_data(
            self.service.set_permission_mode(
                mode,
                explicit_confirmation=confirmation_text.strip() == "FULL",
            )
        )

    def authorize_directory(self, path: str | Path) -> dict[str, Any]:
        return self.service.require_data(self.service.authorize_directory(path))

    def revoke_directory(self, path: str | Path) -> dict[str, Any]:
        return self.service.require_data(self.service.revoke_directory(path))

    def access_decision(
        self, path: str | Path, operation: str = "write"
    ) -> dict[str, str]:
        """Return a serializable decision from the unified permission policy."""

        return self.service.require_data(
            self.service.access_decision(path, operation)
        )


class PermissionView(Vertical):
    """View for runtime file-access mode and external-root authorization."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._controller: PermissionScreenController | None = None

    @property
    def controller(self) -> PermissionScreenController:
        if self._controller is None:
            self._controller = PermissionScreenController(self._project_root)
        return self._controller

    def compose(self) -> ComposeResult:
        yield Static("权限", classes="section-title")
        yield Static("", id="permission-current")
        yield Static(PERMISSION_RISK_NOTICE, id="permission-risk", classes="hint")
        with Horizontal(classes="form-row"):
            yield Select(
                [("保守/沙箱模式", "conservative"), ("完全访问模式", "full")],
                prompt="选择权限模式",
                id="permission-mode-select",
            )
            yield Input(
                placeholder="切换到完全访问模式需输入 FULL",
                id="permission-confirm-input",
            )
            yield Button(
                "切换模式", id="permission-set-mode", classes="btn btn-primary"
            )
        yield Static("外部授权目录（保守模式下允许访问这些目录）", classes="hint")
        permission_table: DataTable = DataTable(id="permission-roots-table", cursor_type="row")
        permission_table.styles.height = "auto"
        permission_table.styles.max_height = 8
        yield permission_table
        with Horizontal(classes="form-row"):
            yield Input(placeholder="外部目录路径", id="permission-root-input")
            yield Button(
                "添加授权目录", id="permission-add-root", classes="btn btn-primary"
            )
            yield Button(
                "移除选中目录", id="permission-remove-root", classes="btn btn-secondary"
            )
            yield Button("刷新", id="permission-refresh", classes="btn btn-secondary")
        yield Static("", id="permission-status")

    def on_mount(self) -> None:
        self.refresh_permission_state()

    def focus_default(self) -> None:
        try:
            self.query_one("#permission-mode-select", Select).focus()
        except Exception:
            pass

    def refresh_permission_state(self) -> None:
        config = self.controller.current_config()
        mode = str(config.get("mode") or "conservative")
        confirmed = bool(config.get("full_mode_confirmed"))
        roots = [str(root) for root in config.get("authorized_external_roots", [])]

        current = self.query_one("#permission-current", Static)
        mode_label = (
            "完全访问模式" if mode == "full" else "保守/沙箱模式"
        )
        current.update(
            f"当前模式：{mode_label} ({mode}) · 完全模式确认：{'是' if confirmed else '否'}"
        )

        select = self.query_one("#permission-mode-select", Select)
        select.value = mode if mode in {"conservative", "full"} else "conservative"

        table = self.query_one("#permission-roots-table", DataTable)
        table.clear(columns=True)
        table.add_columns("编号", "授权目录")
        for index, root in enumerate(roots, start=1):
            table.add_row(str(index), root)
        if not roots:
            self._set_status("当前没有外部授权目录；保守模式默认只允许项目内路径。")
        else:
            self._set_status(f"已加载 {len(roots)} 个外部授权目录。")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "permission-refresh":
            self.refresh_permission_state()
            self._set_status("权限配置已刷新。")
        elif button_id == "permission-set-mode":
            self._set_mode_from_form()
        elif button_id == "permission-add-root":
            self._add_root_from_form()
        elif button_id == "permission-remove-root":
            self._remove_selected_root()

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "permission-confirm-input":
            self._set_mode_from_form()
        elif input_id == "permission-root-input":
            self._add_root_from_form()

    def _set_mode_from_form(self) -> None:
        select = self.query_one("#permission-mode-select", Select)
        mode = str(select.value or "conservative")
        confirmation = self.query_one("#permission-confirm-input", Input).value
        try:
            self.controller.set_mode(mode, confirmation_text=confirmation)
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")
            self.app.notify("权限模式切换失败，请检查确认文本。", severity="warning")
            return
        self.query_one("#permission-confirm-input", Input).value = ""
        self.refresh_permission_state()
        self._set_status("权限模式已切换；统一权限服务会立即读取新状态。")
        self.app.notify("权限模式已切换；不会静默提权或绕过 OS 权限。")
        self._refresh_shell_status()

    def _add_root_from_form(self) -> None:
        root_input = self.query_one("#permission-root-input", Input)
        root = root_input.value.strip()
        if not root:
            self._set_status("请输入要授权的外部目录路径。")
            return
        try:
            self.controller.authorize_directory(root)
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")
            self.app.notify("添加外部授权目录失败。", severity="warning")
            return
        root_input.value = ""
        self.refresh_permission_state()
        self._set_status("外部授权目录已添加；后续文件访问策略即时生效。")
        self.app.notify("外部授权目录已添加。")

    def _remove_selected_root(self) -> None:
        table = self.query_one("#permission-roots-table", DataTable)
        if (
            table.cursor_row is None
            or table.cursor_row < 0
            or table.cursor_row >= table.row_count
        ):
            self._set_status("请先在表格中选择要移除的授权目录。")
            return
        row = table.get_row_at(table.cursor_row)
        root = str(row[1]) if len(row) > 1 else ""
        if not root:
            self._set_status("选中的授权目录无效。")
            return
        try:
            self.controller.revoke_directory(root)
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")
            self.app.notify("移除外部授权目录失败。", severity="warning")
            return
        self.refresh_permission_state()
        self._set_status("外部授权目录已移除；后续文件访问策略即时生效。")
        self.app.notify("外部授权目录已移除。")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#permission-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _refresh_shell_status(self) -> None:
        update_status = getattr(self.app, "_update_status_bar", None)
        if callable(update_status):
            update_status()


PermissionScreen = PermissionView
