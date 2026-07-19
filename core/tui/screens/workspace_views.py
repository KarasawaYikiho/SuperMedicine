"""Converged TUI views for the workspace domain."""
# ruff: noqa: E402,F401,F811

from __future__ import annotations

# --- migrated from workspaces.py ---
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.services import ServiceResult, WorkspaceService


WORKSPACE_DELETE_ACTION = "workspace.delete"
TUI_AGENT_ID = "delta"


@dataclass(slots=True)
class WorkspaceScreenController:
    """Translate TUI inputs and messages around shared workspace use cases."""

    project_root: Path | str | None = None
    agent_id: str = TUI_AGENT_ID

    @property
    def service(self) -> WorkspaceService:
        return WorkspaceService(self.project_root)

    @property
    def root(self) -> Path:
        return self.service.project_root

    def list_workspaces(self) -> list[dict[str, Any]]:
        data = self.service.require_data(self.service.list())
        return [self._display_payload(item, selected=False) for item in data]

    def create_workspace(self, workspace_id: str) -> dict[str, Any]:
        service = self.service
        result = service.create(workspace_id, fail_if_exists=True)
        data = self._require_tui_data(result)
        service.require_data(service.save_selection(data["id"], data["id"]))
        return self._display_payload(
            data, selected=True, message="已创建并选择工作区"
        )

    def select_workspace(
        self, workspace_id: str, *, state_workspace_id: str | None = None
    ) -> dict[str, Any]:
        service = self.service
        data = self._require_tui_data(service.show(workspace_id))
        service.require_data(
            service.save_selection(state_workspace_id or data["id"], data["id"])
        )
        return self._display_payload(data, selected=True, message="已选择工作区")

    def recent_workspace(self, workspace_id: str) -> str | None:
        service = self.service
        return service.require_data(service.load_selection(workspace_id))

    def delete_workspace(self, workspace_id: str, *, confirm: str) -> dict[str, Any]:
        service = self.service
        data = self._require_tui_data(
            service.delete(workspace_id, confirm=confirm, agent_id=self.agent_id)
        )
        return {**data, "message": "工作区已硬删除"}

    @staticmethod
    def _require_tui_data(result: ServiceResult[Any]) -> Any:
        if result.ok:
            return result.data
        error = result.error
        code = error.code if error else "workspace_error"
        if code == "invalid_workspace_id":
            raise ValueError(
                "工作区 ID 只能使用小写字母、数字和连字符，且不能以连字符开头或结尾"
            )
        if code == "workspace_exists":
            workspace_id = error.details.get("workspace_id", "") if error else ""
            raise ValueError(f"工作区已存在：{workspace_id}")
        if code == "confirmation_mismatch":
            raise ValueError("删除工作区需要输入完全一致的工作区 ID 作为确认")
        return WorkspaceService.require_data(result)

    @staticmethod
    def _display_payload(
        data: dict[str, Any], *, selected: bool, message: str | None = None
    ) -> dict[str, Any]:
        payload = {
            **data,
            "label": f"工作区：{data['id']}",
            "selected": selected,
        }
        if message is not None:
            payload["message"] = message
        return payload


# --- migrated from workspace_screen.py ---
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


# --- migrated from tool_screen.py ---
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.redaction import redact_sensitive
from core.services import (
    ExperimentToolService,
    ExperienceEvolutionService,
    PermissionLogSystemService,
)
from core.tui.app import apply_status_style
from core.tui.i18n import t


class ToolView(Vertical):
    """View for managing tools."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._table_mode = "workspace"
        self._tool_run_empty_error_active = False
        self._tool_run_empty_error_workspace_id: str | None = None
        self._self_evolution_last_request: dict[str, Any] | None = None
        self._self_evolution_last_result: dict[str, Any] | None = None

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
            yield Static(
                "选择候选工具后点击添加；无需输入或知道工具 ID。", classes="hint"
            )
        with Horizontal(classes="form-row"):
            yield Button(t("tool_init"), id="tool-init", classes="btn btn-secondary")
            yield Button("扫描候选", id="tool-scan", classes="btn btn-secondary")
            yield Button(t("tool_add"), id="tool-add", classes="btn btn-primary")
            yield Button(t("tool_run"), id="tool-run", classes="btn btn-secondary")
            yield Button(t("refresh"), id="tool-refresh", classes="btn btn-secondary")
        yield Static("", id="tool-status")
        yield Static("自进化", classes="section-title")
        yield Static(
            "输入自进化指令，选择权限/产物类型，先预览生成内容；只有显式确认后才写入文件。",
            id="self-evolution-hint",
            classes="hint",
        )
        with Horizontal(classes="form-row"):
            yield Select(
                [
                    ("Markdown 计划", "markdown"),
                    ("Python 工具", "python_tool"),
                    ("R 工具", "r_tool"),
                ],
                value="markdown",
                id="self-evolution-artifact-select",
            )
            yield Select(
                [
                    ("沙箱生成根目录", "sandbox"),
                    ("保守/项目内", "conservative"),
                    ("完全访问（需 FULL WRITE）", "full"),
                ],
                value="sandbox",
                id="self-evolution-access-mode-select",
            )
            yield Button(
                "使用当前权限",
                id="self-evolution-use-current-permission",
                classes="btn btn-secondary",
            )
        with Horizontal(classes="form-row"):
            yield Input(
                placeholder="自进化指令，例如：生成数据清洗工具说明",
                id="self-evolution-instruction-input",
            )
            yield Input(
                placeholder="输出路径，例如 generated/self-evolution.md",
                value="generated/self-evolution.md",
                id="self-evolution-output-input",
            )
        with Horizontal(classes="form-row"):
            yield Input(
                placeholder="确认写入输入 WRITE；full 模式输入 FULL WRITE",
                id="self-evolution-confirm-input",
            )
            yield Button(
                "生成预览", id="self-evolution-preview", classes="btn btn-primary"
            )
            yield Button(
                "确认写入", id="self-evolution-confirm-write", classes="btn btn-danger"
            )
            yield Button(
                "取消", id="self-evolution-cancel", classes="btn btn-secondary"
            )
        yield DataTable(id="self-evolution-files-table", cursor_type="row")
        yield Static("预览内容将在这里显示。", id="self-evolution-preview-content")
        yield Static("审计结果将在确认写入后显示。", id="self-evolution-audit-result")
        yield Static("", id="self-evolution-status")

    def on_mount(self) -> None:
        self._load_workspaces()
        self._sync_self_evolution_permission_mode()

    def focus_default(self) -> None:
        try:
            self.query_one("#tool-workspace-select", Select).focus()
        except Exception:
            pass

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
        if self._table_mode == "candidates" and not refreshed:
            return
        self._table_mode = "workspace"
        workspace_id = self._get_selected_workspace()
        table = self.query_one("#tool-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("tool_language"), "ID", "名称", t("dashboard_status"))
        if not workspace_id:
            self._tool_run_empty_error_active = False
            self._tool_run_empty_error_workspace_id = None
            self._set_status(
                f"{t('tool_refreshed')}：{t('paper_select_workspace')}"
                if refreshed
                else t("paper_select_workspace")
            )
            return

        try:
            service = ExperimentToolService(self._project_root)
            grouped = service.require_data(service.list_tools(workspace_id))
        except Exception as e:
            self._set_error(e)
            return

        tool_count = 0
        for language, tools in grouped.items():
            for tool in tools:
                table.add_row(language, tool.get("id", ""), tool.get("name", ""), "OK")
                tool_count += 1

        if tool_count == 0:
            if refreshed:
                self._tool_run_empty_error_active = False
                self._tool_run_empty_error_workspace_id = None
                self._set_status(f"{t('tool_refreshed')}：{t('tool_no_tools')}")
                return
            if (
                self._tool_run_empty_error_active
                and self._tool_run_empty_error_workspace_id == workspace_id
            ):
                return
            self._tool_run_empty_error_active = False
            self._tool_run_empty_error_workspace_id = None
            self._set_status(t("tool_no_tools"))
            return
        self._tool_run_empty_error_active = False
        self._tool_run_empty_error_workspace_id = None
        self._set_status(
            f"{t('tool_refreshed')}: {tool_count}"
            if refreshed
            else f"{t('tool_list')}: {tool_count}"
        )

    def _scan_candidates(self) -> None:
        self._table_mode = "candidates"
        table = self.query_one("#tool-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "编号", t("tool_language"), "ID", "名称", t("dashboard_status")
        )

        language_select = self.query_one("#tool-language-select", Select)
        language = (
            str(language_select.value)
            if language_select.value != Select.BLANK
            else None
        )
        try:
            service = ExperimentToolService(self._project_root)
            grouped = service.require_data(service.scan_tools(language))
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
            self._set_status(
                f"扫描到 {count} 个候选工具，其中 {invalid} 个格式错误不可导入。"
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
            if self._table_mode == "candidates":
                return
            workspace_id = self._get_selected_workspace()
            if not (
                self._tool_run_empty_error_active
                and self._tool_run_empty_error_workspace_id == workspace_id
            ):
                self._tool_run_empty_error_active = False
                self._tool_run_empty_error_workspace_id = None
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
            self._tool_run_empty_error_active = False
            self._tool_run_empty_error_workspace_id = None
            self._load_tools(refreshed=True)
        elif event.button.id == "self-evolution-use-current-permission":
            self._sync_self_evolution_permission_mode(show_status=True)
        elif event.button.id == "self-evolution-preview":
            self._preview_self_evolution()
        elif event.button.id == "self-evolution-confirm-write":
            self._confirm_self_evolution_write()
        elif event.button.id == "self-evolution-cancel":
            self._cancel_self_evolution()

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "self-evolution-instruction-input":
            self._preview_self_evolution()
        elif input_id == "self-evolution-output-input":
            self._preview_self_evolution()
        elif input_id == "self-evolution-confirm-input":
            self._confirm_self_evolution_write()

    def _init_tools(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        try:
            service = ExperimentToolService(self._project_root)
            service.require_data(service.initialize_tools(workspace_id))
        except Exception as e:
            self._set_error(e)
            return
        self._tool_run_empty_error_active = False
        self._tool_run_empty_error_workspace_id = None
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
        if (
            table.cursor_row is None
            or table.cursor_row < 0
            or table.cursor_row >= table.row_count
        ):
            self._set_status(f"{t('error')}: 未选择候选工具。")
            return
        selection = str(table.get_row_at(table.cursor_row)[0])
        try:
            service = ExperimentToolService(self._project_root)
            result = service.require_data(
                service.import_tools(workspace_id, [selection])
            )
        except Exception as e:
            self._set_error(e)
            return
        if result.get("errors"):
            self._set_status(f"{t('error')}: {result['errors'][0].get('error')}")
            return
        self.app.notify(t("tool_added"))
        self._load_tools(refreshed=True)
        self._set_status(t("tool_added"))

    def _run_tool(self) -> None:
        table = self.query_one("#tool-table", DataTable)
        if self._table_mode != "workspace":
            self._set_status("请先刷新工作区工具列表，再选择已导入工具运行。")
            return
        if table.row_count == 0:
            self._tool_run_empty_error_active = True
            self._tool_run_empty_error_workspace_id = self._get_selected_workspace()
            self._set_status(f"{t('error')}: {t('tool_no_tools')}")
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

        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        try:
            service = ExperimentToolService(self._project_root)
            tool = service.require_data(
                service.show_tool(workspace_id, language, tool_id)
            )
        except Exception:
            self._set_status(f"{t('error')}: {t('tool_no_tools')}")
            return

        # Show tool path for user
        self._set_status(f"{t('tool_run')}: {tool['path']}")

    def _sync_self_evolution_permission_mode(
        self, *, show_status: bool = False
    ) -> None:
        """Reflect the persisted permission mode in the self-evolution selector."""

        try:
            from permission.access_mode import AccessMode

            service = PermissionLogSystemService(self._project_root)
            config = service.require_data(service.permission_status())
            mode = str(
                config.get("mode")
                or AccessMode.CONSERVATIVE.value
            )
            select = self.query_one("#self-evolution-access-mode-select", Select)
            if mode in {"conservative", "full"}:
                select.value = mode
            if show_status:
                self._set_self_evolution_status(
                    f"已读取当前权限模式：{'完全访问' if mode == 'full' else '保守'}。"
                )
        except Exception as exc:
            if show_status:
                self._set_self_evolution_status(f"错误：{redact_sensitive(str(exc))}")

    def _self_evolution_request_from_form(self) -> dict[str, Any] | None:
        """Collect a service request from TUI controls without writing files."""

        instruction = self.query_one(
            "#self-evolution-instruction-input", Input
        ).value.strip()
        output = self.query_one("#self-evolution-output-input", Input).value.strip()
        artifact_select = self.query_one("#self-evolution-artifact-select", Select)
        access_select = self.query_one("#self-evolution-access-mode-select", Select)
        artifact_type = str(artifact_select.value or "markdown")
        access_mode = str(access_select.value or "sandbox")
        if not instruction:
            self._set_self_evolution_status("错误：请输入自进化指令。")
            return None
        if not output:
            self._set_self_evolution_status("错误：请输入输出路径。")
            return None
        return {
            "user_intent": instruction,
            "artifact_type": artifact_type,
            "output_path": output,
            "access_mode": access_mode,
            "metadata": {"tui_entry": "tool_screen.self_evolution"},
        }

    def _preview_self_evolution(self) -> None:
        request = self._self_evolution_request_from_form()
        if request is None:
            return
        try:
            service = ExperienceEvolutionService(self._project_root)
            result = service.require_data(service.generate_evolution(
                instruction=str(request["user_intent"]),
                artifact_type=str(request["artifact_type"]),
                output=str(request["output_path"]),
                access_mode=str(request["access_mode"]),
                confirmed=False,
                metadata=dict(request.get("metadata") or {}),
            ))
        except Exception as exc:
            self._set_self_evolution_status(f"错误：{redact_sensitive(str(exc))}")
            return
        self._self_evolution_last_request = dict(request)
        self._self_evolution_last_result = result
        self._render_self_evolution_result(result, preview=True)

    def _confirm_self_evolution_write(self) -> None:
        request = (
            self._self_evolution_last_request
            or self._self_evolution_request_from_form()
        )
        if request is None:
            return
        confirmation = self.query_one(
            "#self-evolution-confirm-input", Input
        ).value.strip()
        access_mode = str(request.get("access_mode") or "sandbox")
        if access_mode == "full":
            if confirmation != "FULL WRITE":
                self._set_self_evolution_status(
                    "错误：完全访问模式写入前必须在确认框输入 FULL WRITE。"
                )
                return
            full_access_confirmed = True
            risk_notice_acknowledged = True
        else:
            if confirmation != "WRITE":
                self._set_self_evolution_status("错误：确认写入前必须输入 WRITE。")
                return
            full_access_confirmed = False
            risk_notice_acknowledged = False
        try:
            service = ExperienceEvolutionService(self._project_root)
            result = service.require_data(service.generate_evolution(
                instruction=str(request["user_intent"]),
                artifact_type=str(request["artifact_type"]),
                output=str(request["output_path"]),
                access_mode=str(request["access_mode"]),
                confirmed=True,
                confirm_full_access=full_access_confirmed,
                acknowledge_risk=risk_notice_acknowledged,
                metadata=dict(request.get("metadata") or {}),
            ))
        except Exception as exc:
            self._set_self_evolution_status(f"错误：{redact_sensitive(str(exc))}")
            return
        self._self_evolution_last_result = result
        self._render_self_evolution_result(result, preview=False)

    def _cancel_self_evolution(self) -> None:
        self._self_evolution_last_request = None
        self._self_evolution_last_result = None
        self.query_one("#self-evolution-confirm-input", Input).value = ""
        table = self.query_one("#self-evolution-files-table", DataTable)
        table.clear(columns=True)
        self.query_one("#self-evolution-preview-content", Static).update(
            "已取消；未写入任何自进化文件。"
        )
        self.query_one("#self-evolution-audit-result", Static).update(
            "取消结果：没有新增审计记录。"
        )
        self._set_self_evolution_status("已取消自进化写入流程。")

    def _render_self_evolution_result(
        self, result: dict[str, Any], *, preview: bool
    ) -> None:
        table = self.query_one("#self-evolution-files-table", DataTable)
        table.clear(columns=True)
        table.add_columns("操作", "路径", "说明")
        artifacts = result.get("artifacts") if isinstance(result, dict) else []
        preview_text = ""
        if isinstance(artifacts, list):
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                operation = "修改" if artifact.get("exists") else "创建"
                path = str(artifact.get("path") or "")
                description = str(artifact.get("description") or "")
                table.add_row(operation, path, description)
                if not preview_text:
                    content = str(artifact.get("content") or "")
                    preview_text = f"目标文件：{path}\n\n{content}"
        if not preview_text:
            errors = "; ".join(str(error) for error in result.get("errors", []))
            preview_text = errors or str(
                result.get("message") or "没有可显示的预览内容。"
            )
        self.query_one("#self-evolution-preview-content", Static).update(
            str(redact_sensitive(preview_text))
        )
        audit_records = result.get("audit_records", [])
        audit_log = self._project_root / ".supermedicine" / "policies" / "audit.jsonl"
        if audit_records:
            audit_text = (
                f"审计结果：已记录 {len(audit_records)} 条；日志路径：{audit_log}"
            )
        elif preview:
            audit_text = f"审计结果：预览模式未写入文件；确认写入后记录到 {audit_log}。"
        else:
            audit_text = f"审计结果：无审计记录返回；日志路径：{audit_log}。"
        self.query_one("#self-evolution-audit-result", Static).update(
            str(redact_sensitive(audit_text))
        )
        status = str(result.get("status") or "unknown")
        message = str(result.get("message") or "")
        if status == "success":
            written_files = (
                result.get("plan", {}).get("written_files", [])
                if isinstance(result.get("plan"), dict)
                else []
            )
            self._set_self_evolution_status(
                f"写入成功：{', '.join(str(path) for path in written_files) or '已生成文件'}"
            )
            self.app.notify("自进化产物已写入，请检查生成文件。")
        elif status == "failed":
            errors = "; ".join(str(error) for error in result.get("errors", []))
            self._set_self_evolution_status(f"错误：{errors or message}")
        else:
            self._set_self_evolution_status(
                "预览已生成；确认无误后输入 WRITE 并点击确认写入。"
            )

    def _set_self_evolution_status(self, message: str) -> None:
        status = self.query_one("#self-evolution-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)


# Backward-compatible alias
ToolScreen = ToolView

