"""Dialog history view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Select, Static

from core.redaction import redact_sensitive
from core.services import AgentHarnessService
from core.tui.app import apply_status_style
from core.tui.i18n import t


class DialogView(Vertical):
    """View for viewing dialog history."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("dialog_title"), classes="section-title")
        yield Static(t("dialog_action_hint"), id="dialog-action-hint", classes="hint")
        yield Select(
            [],
            prompt=t("paper_select_workspace"),
            id="dialog-workspace-select",
        )
        yield DataTable(id="dialog-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Button(t("refresh"), id="dialog-refresh", classes="btn btn-secondary")
        yield Static("", id="dialog-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def _get_workspace_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        return WorkspaceScreenController(project_root=self._project_root)

    def _load_workspaces(self) -> None:
        select_widget = self.query_one("#dialog-workspace-select", Select)
        controller = self._get_workspace_controller()
        try:
            workspaces = controller.list_workspaces()
            options = [(ws["label"], ws["id"]) for ws in workspaces]
            select_widget.set_options(options)
            if not options:
                self._set_status(t("workspace_no_workspaces"))
        except Exception as e:
            self._set_error(e)

    def _get_selected_workspace(self) -> str | None:
        select_widget = self.query_one("#dialog-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _load_dialog_history(self, *, refreshed: bool = False) -> None:
        workspace_id = self._get_selected_workspace()
        table = self.query_one("#dialog-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("dialog_event"), t("dialog_summary"), t("dialog_time"))
        if not workspace_id:
            self._set_status(
                f"{t('dialog_refreshed')}：{t('paper_select_workspace')}"
                if refreshed
                else t("paper_select_workspace")
            )
            return

        try:
            service = AgentHarnessService(self._project_root)
            events = service.require_data(service.list_dialog_events(workspace_id))
            if not events:
                self._set_status(
                    f"{t('dialog_refreshed')}：{t('dialog_no_history')}"
                    if refreshed
                    else t("dialog_no_history")
                )
                return
            for event in events:
                table.add_row(
                    str(event.get("event", "")),
                    str(event.get("summary", ""))[:80],
                    str(event.get("created_at", "")),
                    key=str(event.get("id", "")),
                )
            self._set_status(
                f"{t('dialog_refreshed')}: {len(events)}"
                if refreshed
                else f"{t('dialog_title')}: {len(events)}"
            )
        except Exception as e:
            self._set_error(e)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#dialog-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        message = (
            f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}"
        )
        self._set_status(message)
        self.app.notify(message, severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "dialog-workspace-select":
            self._load_dialog_history()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dialog-refresh":
            self._load_workspaces()
            self._load_dialog_history(refreshed=True)


# Backward-compatible alias
DialogScreen = DialogView
