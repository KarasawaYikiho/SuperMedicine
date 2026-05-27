"""Workspace management screen for SuperMedicine TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Static

from core.tui.i18n import t


class WorkspaceScreen(Screen):
    """Screen for managing workspaces."""

    def compose(self) -> ComposeResult:
        yield Static(t("workspace_title"), id="content-header", classes="section-title")
        with Vertical(id="content-body"):
            yield DataTable(id="workspace-table", cursor_type="row")
            with Horizontal():
                yield Input(
                    placeholder=t("workspace_id_label"),
                    id="workspace-id-input",
                )
                yield Button(t("workspace_create"), id="workspace-create", classes="btn btn-primary")
                yield Button(t("workspace_select"), id="workspace-select", classes="btn btn-secondary")
                yield Button(t("workspace_delete"), id="workspace-delete", classes="btn btn-danger")
                yield Button(t("refresh"), id="workspace-refresh", classes="btn btn-secondary")
            yield Static("", id="workspace-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def _get_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        project_root = self.app.project_root  # type: ignore[attr-defined]
        return WorkspaceScreenController(project_root=project_root)

    def _load_workspaces(self) -> None:
        table = self.query_one("#workspace-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", t("workspace_path"), t("workspace_created_at"))

        controller = self._get_controller()
        try:
            workspaces = controller.list_workspaces()
            if not workspaces:
                self._set_status(t("workspace_no_workspaces"))
                return
            for ws in workspaces:
                metadata = ws.get("metadata", {})
                created_at = metadata.get("created_at", "")
                table.add_row(ws["id"], ws["path"], str(created_at), key=ws["id"])
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#workspace-status", Static)
        status.update(message)

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
            self._load_workspaces()

    def _create_workspace(self, workspace_id: str) -> None:
        if not workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_id_label')}")
            return
        controller = self._get_controller()
        try:
            result = controller.create_workspace(workspace_id)
            self._set_status(result.get("message", t("workspace_created")))
            self._load_workspaces()
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _select_workspace(self, workspace_id: str) -> None:
        if not workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_id_label')}")
            return
        controller = self._get_controller()
        try:
            result = controller.select_workspace(workspace_id)
            self._set_status(result.get("message", t("workspace_selected")))
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _delete_workspace(self, workspace_id: str) -> None:
        if not workspace_id:
            self._set_status(f"{t('error')}: {t('workspace_confirm_delete')}")
            return
        controller = self._get_controller()
        try:
            result = controller.delete_workspace(workspace_id, confirm=workspace_id)
            self._set_status(result.get("message", t("workspace_deleted")))
            self._load_workspaces()
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")
