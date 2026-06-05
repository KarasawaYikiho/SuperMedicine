"""Tool management view for SuperMedicine TUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


class ToolView(Vertical):
    """View for managing tools."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("tool_title"), classes="section-title")
        yield Static(t("tool_action_hint"), id="tool-action-hint", classes="hint")
        yield Select(
            [],
            prompt=t("paper_select_workspace"),
            id="tool-workspace-select",
        )
        yield DataTable(id="tool-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Select(
                [
                    (t("tool_language_python"), "python"),
                    (t("tool_language_r"), "r"),
                ],
                value="python",
                id="tool-language-select",
            )
            yield Input(placeholder=t("tool_tool_id"), id="tool-id-input")
        with Horizontal(classes="form-row"):
            yield Button(t("tool_init"), id="tool-init", classes="btn btn-secondary")
            yield Button(t("tool_add"), id="tool-add", classes="btn btn-primary")
            yield Button(t("tool_run"), id="tool-run", classes="btn btn-secondary")
            yield Button(t("refresh"), id="tool-refresh", classes="btn btn-secondary")
        yield Static("", id="tool-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def _get_workspace_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        return WorkspaceScreenController(project_root=self._project_root)

    def _load_workspaces(self) -> None:
        select_widget = self.query_one("#tool-workspace-select", Select)
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
        select_widget = self.query_one("#tool-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _get_workspace_path(self) -> Path | None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            return None
        controller = self._get_workspace_controller()
        try:
            workspaces = controller.list_workspaces()
            for ws in workspaces:
                if ws["id"] == workspace_id:
                    return Path(ws["path"])
        except Exception:
            pass
        return None

    def _load_tools(self, *, refreshed: bool = False) -> None:
        workspace_path = self._get_workspace_path()
        table = self.query_one("#tool-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("tool_language"), "ID", t("dashboard_status"))
        if not workspace_path:
            self._set_status(
                f"{t('tool_refreshed')}：{t('paper_select_workspace')}"
                if refreshed
                else t("paper_select_workspace")
            )
            return

        tools_dir = workspace_path / "tools"
        if not tools_dir.is_dir():
            self._set_status(
                f"{t('tool_refreshed')}：{t('tool_no_tools')}"
                if refreshed
                else t("tool_no_tools")
            )
            return

        tool_count = 0
        for lang_dir in tools_dir.iterdir():
            if lang_dir.is_dir():
                lang = lang_dir.name
                for tool_dir in lang_dir.iterdir():
                    if tool_dir.is_dir():
                        tool_file = tool_dir / "tool.json"
                        if tool_file.is_file():
                            try:
                                data = json.loads(tool_file.read_text(encoding="utf-8"))
                                status = "OK" if data.get("executable") else "--"
                            except Exception:
                                status = "?"
                            table.add_row(lang, tool_dir.name, status)
                            tool_count += 1

        if tool_count == 0:
            self._set_status(
                f"{t('tool_refreshed')}：{t('tool_no_tools')}"
                if refreshed
                else t("tool_no_tools")
            )
        else:
            self._set_status(
                f"{t('tool_refreshed')}: {tool_count}"
                if refreshed
                else f"{t('tool_list')}: {tool_count}"
            )

    def _set_status(self, message: str) -> None:
        status = self.query_one("#tool-status", Static)
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
        if event.select.id == "tool-workspace-select":
            self._load_tools()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tool-init":
            self._init_tools()
        elif event.button.id == "tool-add":
            self._add_tool()
        elif event.button.id == "tool-run":
            self._run_tool()
        elif event.button.id == "tool-refresh":
            self._load_tools(refreshed=True)

    def _init_tools(self) -> None:
        workspace_path = self._get_workspace_path()
        if not workspace_path:
            self._set_status(t("paper_select_workspace"))
            return

        tools_dir = workspace_path / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "python").mkdir(exist_ok=True)
        (tools_dir / "r").mkdir(exist_ok=True)
        self._set_status(t("tool_initialized"))
        self.app.notify(t("tool_initialized"))
        self._load_tools()
        self._set_status(t("tool_initialized"))

    def _add_tool(self) -> None:
        workspace_path = self._get_workspace_path()
        if not workspace_path:
            self._set_status(t("paper_select_workspace"))
            return

        language_select = self.query_one("#tool-language-select", Select)
        tool_id_input = self.query_one("#tool-id-input", Input)

        language = (
            str(language_select.value)
            if language_select.value != Select.BLANK
            else "python"
        )
        tool_id = tool_id_input.value.strip()

        if not tool_id:
            self._set_status(f"{t('error')}: {t('tool_tool_id')}")
            return

        tool_dir = workspace_path / "tools" / language / tool_id
        tool_dir.mkdir(parents=True, exist_ok=True)

        tool_meta = {
            "id": tool_id,
            "language": language,
            "executable": False,
        }
        (tool_dir / "tool.json").write_text(
            json.dumps(tool_meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._set_status(t("tool_added"))
        self.app.notify(t("tool_added"))
        self._load_tools()
        self._set_status(t("tool_added"))

    def _run_tool(self) -> None:
        table = self.query_one("#tool-table", DataTable)
        if table.row_count == 0:
            self._set_status(f"{t('error')}: {t('tool_no_tools')}，无法执行该操作")
            return
        if (
            table.cursor_row is None
            or table.cursor_row < 0
            or table.cursor_row >= table.row_count
        ):
            self._set_status(f"{t('error')}: 未选择任何工具，无法执行该操作")
            return

        row_data = table.get_row_at(table.cursor_row)
        language = str(row_data[0])
        tool_id = str(row_data[1])

        workspace_path = self._get_workspace_path()
        if not workspace_path:
            self._set_status(t("paper_select_workspace"))
            return

        tool_dir = workspace_path / "tools" / language / tool_id
        if not tool_dir.is_dir():
            self._set_status(f"{t('error')}: {t('tool_no_tools')}")
            return

        # Show tool path for user
        self._set_status(f"{t('tool_run')}: {tool_dir}")


# Backward-compatible alias
ToolScreen = ToolView
