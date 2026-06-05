"""Tool management view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Select, Static

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


class ToolView(Vertical):
    """View for managing tools."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._table_mode = "workspace"

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
            yield Static("选择候选工具后点击添加；无需输入或知道工具 ID。", classes="hint")
        with Horizontal(classes="form-row"):
            yield Button(t("tool_init"), id="tool-init", classes="btn btn-secondary")
            yield Button("扫描候选", id="tool-scan", classes="btn btn-secondary")
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
        self._table_mode = "workspace"
        workspace_id = self._get_selected_workspace()
        table = self.query_one("#tool-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("tool_language"), "ID", "名称", t("dashboard_status"))
        if not workspace_id:
            self._set_status(
                f"{t('tool_refreshed')}：{t('paper_select_workspace')}"
                if refreshed
                else t("paper_select_workspace")
            )
            return

        from core.workspace_tools import WorkspaceToolService

        try:
            grouped = WorkspaceToolService(self._project_root).list_tools(workspace_id)
        except Exception as e:
            self._set_error(e)
            return

        tool_count = 0
        for language, tools in grouped.items():
            for tool in tools:
                table.add_row(language, tool.get("id", ""), tool.get("name", ""), "OK")
                tool_count += 1

        if tool_count == 0:
            self._set_status(
                f"{t('tool_refreshed')}：{t('tool_no_tools')}"
                if refreshed
                else t("tool_no_tools")
            )
            return
        self._set_status(
            f"{t('tool_refreshed')}: {tool_count}"
            if refreshed
            else f"{t('tool_list')}: {tool_count}"
        )

    def _scan_candidates(self) -> None:
        self._table_mode = "candidates"
        table = self.query_one("#tool-table", DataTable)
        table.clear(columns=True)
        table.add_columns("编号", t("tool_language"), "ID", "名称", t("dashboard_status"))

        language_select = self.query_one("#tool-language-select", Select)
        language = (
            str(language_select.value)
            if language_select.value != Select.BLANK
            else None
        )
        from core.workspace_tools import WorkspaceToolService

        try:
            grouped = WorkspaceToolService(self._project_root).scan_import_candidates(language)
        except Exception as e:
            self._set_error(e)
            return
        count = 0
        invalid = 0
        for candidates in grouped.values():
            for item in candidates:
                warnings = "; ".join(item.get("warnings") or [])
                status = item.get("status", "?")
                if not item.get("importable"):
                    invalid += 1
                table.add_row(
                    str(item.get("index", "")),
                    str(item.get("language", "")),
                    str(item.get("id", "")),
                    str(item.get("name", "")),
                    f"{status}: {warnings}" if warnings else str(status),
                )
                count += 1
        if count == 0:
            self._set_status("未扫描到 Python/R 工具目录或目录为空。")
        else:
            self._set_status(f"扫描到 {count} 个候选工具，其中 {invalid} 个格式错误不可导入。")

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
        elif event.button.id == "tool-scan":
            self._scan_candidates()
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
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return
        table = self.query_one("#tool-table", DataTable)
        if self._table_mode != "candidates":
            self._scan_candidates()
            self._set_status("请从扫描候选列表中选择工具后再次点击添加。")
            return
        if table.row_count == 0:
            self._set_status(f"{t('error')}: 未扫描到可导入工具。")
            return
        if table.cursor_row is None or table.cursor_row < 0 or table.cursor_row >= table.row_count:
            self._set_status(f"{t('error')}: 未选择候选工具。")
            return
        selection = str(table.get_row_at(table.cursor_row)[0])
        from core.workspace_tools import WorkspaceToolService

        try:
            result = WorkspaceToolService(self._project_root).import_scanned_tools(
                workspace_id, [selection]
            )
        except Exception as e:
            self._set_error(e)
            return
        if result.get("errors"):
            self._set_status(f"{t('error')}: {result['errors'][0].get('error')}")
            return
        if result.get("imported"):
            self._sync_tool_import_state(
                workspace_id,
                list(result.get("imported") or []),
            )
        self.app.notify(t("tool_added"))
        self._load_tools(refreshed=True)
        self._set_status(t("tool_added"))

    def _sync_tool_import_state(
        self, workspace_id: str, imported: list[dict[str, Any]]
    ) -> None:
        """Persist latest import so Kernel LLM tool context sees refreshed tools."""

        try:
            from core.config_center import ConfigCenter

            config = ConfigCenter(self._project_root / ".supermedicine" / "config.yaml")
            config.set_runtime_state_value("last_workspace_id", workspace_id)
            config.record_tool_import_state(
                workspace_id=workspace_id,
                imported=imported,
                save=True,
            )
        except Exception as exc:
            self._set_status(f"工具导入状态同步失败：{redact_sensitive(str(exc))}")

    def _run_tool(self) -> None:
        table = self.query_one("#tool-table", DataTable)
        if self._table_mode != "workspace":
            self._set_status("请先刷新工作区工具列表，再选择已导入工具运行。")
            return
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
