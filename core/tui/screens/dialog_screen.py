"""Dialog history screen for SuperMedicine TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Select, Static

from core.tui.i18n import t


class DialogScreen(Screen):
    """Screen for viewing dialog history."""

    def compose(self) -> ComposeResult:
        yield Static(t("dialog_title"), id="content-header", classes="section-title")
        with Vertical(id="content-body"):
            yield Select(
                [],
                prompt=t("paper_select_workspace"),
                id="dialog-workspace-select",
            )
            yield DataTable(id="dialog-table", cursor_type="row")
            with Horizontal():
                yield Button(t("refresh"), id="dialog-refresh", classes="btn btn-secondary")
            yield Static("", id="dialog-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def _get_workspace_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        return WorkspaceScreenController(project_root=self.app.project_root)  # type: ignore[attr-defined]

    def _load_workspaces(self) -> None:
        select_widget = self.query_one("#dialog-workspace-select", Select)
        controller = self._get_workspace_controller()
        try:
            workspaces = controller.list_workspaces()
            options = [(ws["label"], ws["id"]) for ws in workspaces]
            select_widget.set_options(options)
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _get_selected_workspace(self) -> str | None:
        select_widget = self.query_one("#dialog-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _load_dialog_history(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        table = self.query_one("#dialog-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("dialog_event"), t("dialog_summary"), t("dialog_time"))

        from core.tui.dialog_history import DialogHistoryStore

        store = DialogHistoryStore(project_root=self.app.project_root)  # type: ignore[attr-defined]
        try:
            events = store.load_events(workspace_id)
            if not events:
                self._set_status(t("dialog_no_history"))
                return
            for event in events:
                table.add_row(
                    event.event,
                    event.summary[:80],
                    event.created_at,
                    key=event.id,
                )
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#dialog-status", Static)
        status.update(message)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "dialog-workspace-select":
            self._load_dialog_history()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dialog-refresh":
            self._load_dialog_history()
