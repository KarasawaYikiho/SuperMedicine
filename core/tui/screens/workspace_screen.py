"""Workspace management view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static

from core.tui.app import apply_status_style
from core.tui.i18n import t, tui_redact_sensitive


class WorkspaceView(Vertical):
    """View for managing workspaces."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("workspace_title"), classes="section-title")
        yield Static(
            t("workspace_manual_create_hint"),
            id="workspace-create-hint",
            classes="hint",
        )
        yield Static(
            t("workspace_action_hint"), id="workspace-action-hint", classes="hint"
        )
        yield DataTable(id="workspace-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Input(
                placeholder=t("workspace_create_placeholder"),
                id="workspace-id-input",
            )
            yield Button(
                t("workspace_create"), id="workspace-create", classes="btn btn-primary"
            )
        with Horizontal(classes="form-row"):
            yield Button(
                t("workspace_select"),
                id="workspace-select",
                classes="btn btn-secondary",
            )
            yield Button(
                t("refresh"), id="workspace-refresh", classes="btn btn-secondary"
            )
            yield Button(
                t("workspace_delete"), id="workspace-delete", classes="btn btn-danger"
            )
        yield Static("", id="workspace-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def refresh_view_data(self) -> None:
        """Refresh workspace file/list data when the view becomes active."""

        self._load_workspaces(refreshed=True)

    def focus_default(self) -> None:
        self.query_one("#workspace-id-input", Input).focus()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+n":
            event.stop()
            self.query_one("#workspace-id-input", Input).focus()

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "workspace-id-input":
            self._create_workspace(value.strip())

    def _get_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        return WorkspaceScreenController(project_root=self._project_root)

    def _load_workspaces(
        self, *, preserve_status: bool = False, refreshed: bool = False
    ) -> None:
        table = self.query_one("#workspace-table", DataTable)
        selected_key = self._selected_workspace_id()
        table.clear(columns=True)
        table.add_columns("ID", t("workspace_path"), t("workspace_created_at"))

        controller = self._get_controller()
        try:
            workspaces = controller.list_workspaces()
            if not workspaces:
                self._set_status(
                    f"{t('workspace_refreshed')}：{t('workspace_no_workspaces')}"
                    if refreshed
                    else t("workspace_no_workspaces")
                )
                return
            for ws in workspaces:
                metadata = ws.get("metadata", {})
                created_at = metadata.get("created_at", "")
                table.add_row(ws["id"], ws["path"], str(created_at), key=ws["id"])
            if selected_key is not None:
                self._select_table_row(selected_key)
            if not preserve_status:
                self._set_status(
                    f"{t('workspace_refreshed')}: {len(workspaces)}"
                    if refreshed
                    else f"{t('workspace_list')}: {len(workspaces)}"
                )
        except Exception as e:
            self._set_error(e)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#workspace-status", Static)
        safe_message = tui_redact_sensitive(message)
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        message = (
            f"{t('error')}: {tui_redact_sensitive(str(error)) or t('safe_error_hint')}"
        )
        self._set_status(message)
        self.app.notify(message, severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        input_widget = self.query_one("#workspace-id-input", Input)
        workspace_id = input_widget.value.strip()

        if event.button.id == "workspace-create":
            self._create_workspace(workspace_id)
        elif event.button.id == "workspace-select":
            self._select_workspace(workspace_id)
        elif event.button.id == "workspace-delete":
            self._delete_workspace(workspace_id)
        elif event.button.id == "workspace-refresh":
            self._load_workspaces(refreshed=True)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id != "workspace-table":
            return
        workspace_id = str(event.row_key.value)
        input_widget = self.query_one("#workspace-id-input", Input)
        input_widget.value = workspace_id
        self._select_workspace(workspace_id)

    def _create_workspace(self, workspace_id: str) -> None:
        if not workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_id_label')}")
            return
        controller = self._get_controller()
        try:
            result = controller.create_workspace(workspace_id)
            created_id = result.get("id", workspace_id)
            message = f"{result.get('message', t('workspace_created'))}：{created_id}"
            self._set_status(message)
            self.app.notify(message)
            self._load_workspaces(preserve_status=True)
            self._select_table_row(str(created_id))
            input_widget = self.query_one("#workspace-id-input", Input)
            input_widget.value = str(created_id)
            input_widget.focus()
            refresh_workspace_views = getattr(self.app, "refresh_workspace_views", None)
            if callable(refresh_workspace_views):
                refresh_workspace_views(selected_workspace_id=str(created_id))
                self._select_table_row(str(created_id))
                input_widget.focus()
            update_status_bar = getattr(self.app, "_update_status_bar", None)
            if callable(update_status_bar):
                update_status_bar()
        except Exception as e:
            self._set_error(e)

    def _selected_workspace_id(self) -> str | None:
        table = self.query_one("#workspace-table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except Exception:
            return None
        value = getattr(row_key, "value", None)
        return str(value) if value is not None else None

    def _select_table_row(self, workspace_id: str) -> None:
        table = self.query_one("#workspace-table", DataTable)
        try:
            row_index = table.get_row_index(workspace_id)
        except Exception:
            return
        table.move_cursor(row=row_index, column=0)

    def _select_workspace(self, workspace_id: str) -> None:
        if not workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_id_label')}")
            return
        controller = self._get_controller()
        try:
            result = controller.select_workspace(workspace_id)
            self._set_status(result.get("message", t("workspace_selected")))
            self.app.notify(result.get("message", t("workspace_selected")))
        except Exception as e:
            self._set_error(e)

    def _delete_workspace(self, workspace_id: str) -> None:
        confirm_prefix = "delete:"
        if not workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_delete_requires_confirm')}")
            return
        if not workspace_id.startswith(confirm_prefix):
            self._set_status(
                f"{t('error')}: {t('workspace_delete_requires_confirm')}；"
                f"请在输入框手动输入 {confirm_prefix}<workspace-id> 后再删除"
            )
            return
        confirmed_workspace_id = workspace_id[len(confirm_prefix) :].strip()
        if not confirmed_workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_delete_requires_confirm')}")
            return
        controller = self._get_controller()
        try:
            result = controller.delete_workspace(
                confirmed_workspace_id, confirm=confirmed_workspace_id
            )
            self._set_status(result.get("message", t("workspace_deleted")))
            self.app.notify(result.get("message", t("workspace_deleted")))
            self._load_workspaces()
            self._set_status(result.get("message", t("workspace_deleted")))
            refresh_workspace_views = getattr(self.app, "refresh_workspace_views", None)
            if callable(refresh_workspace_views):
                refresh_workspace_views()
            update_status_bar = getattr(self.app, "_update_status_bar", None)
            if callable(update_status_bar):
                update_status_bar()
        except Exception as e:
            self._set_error(e)


# Backward-compatible alias
WorkspaceScreen = WorkspaceView
