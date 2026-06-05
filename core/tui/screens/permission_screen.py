"""Permission mode management view for the SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.config_center import ConfigCenter
from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from permission.access_mode import AccessMode, FileAccessOperation, normalize_access_mode


PERMISSION_RISK_NOTICE = (
    "安全边界：默认使用保守模式。完全访问模式必须输入 FULL 显式确认；"
    "它只使用当前进程/用户已经拥有的系统权限，不会静默提权、不会绕过 OS 权限。"
    "如果系统权限不足，请通过管理员权限、UAC 或系统安全提示显式授权后重试。"
)


class PermissionScreenController:
    """TUI facade over the shared file-access configuration service."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config_path = self.project_root / ".supermedicine" / "config.yaml"
        self.config = ConfigCenter(self.config_path)

    def current_config(self) -> dict[str, Any]:
        return self.config.get_file_access_config()

    def set_mode(self, mode: str, *, confirmation_text: str = "") -> dict[str, Any]:
        normalized = normalize_access_mode(mode)
        explicit_confirmation = (
            normalized != AccessMode.FULL or confirmation_text.strip() == "FULL"
        )
        file_access = self.config.set_file_access_mode(
            normalized,
            explicit_confirmation=explicit_confirmation,
        )
        self.config.save()
        return file_access

    def authorize_directory(self, path: str | Path) -> dict[str, Any]:
        file_access = self.config.authorize_external_file_access_directory(path)
        self.config.save()
        return file_access

    def revoke_directory(self, path: str | Path) -> dict[str, Any]:
        file_access = self.config.revoke_external_file_access_directory(path)
        self.config.save()
        return file_access

    def access_decision(self, path: str | Path, operation: str = "write") -> dict[str, str]:
        """Return a serializable decision from the unified permission policy."""

        decision = self.config.get_file_access_policy(self.project_root).decide(
            path,
            FileAccessOperation(operation),
        )
        return {
            "status": decision.status.value,
            "mode": decision.mode.value,
            "reason": decision.reason,
            "path": str(decision.path),
            "helper": decision.helper,
        }


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
        yield Static("权限模式", classes="section-title")
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
            yield Button("切换模式", id="permission-set-mode", classes="btn btn-primary")
        yield Static("外部授权目录（保守模式下允许访问这些目录）", classes="hint")
        yield DataTable(id="permission-roots-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Input(placeholder="外部目录路径", id="permission-root-input")
            yield Button("添加授权目录", id="permission-add-root", classes="btn btn-primary")
            yield Button("移除选中目录", id="permission-remove-root", classes="btn btn-secondary")
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
        mode = str(config.get("mode") or AccessMode.CONSERVATIVE.value)
        confirmed = bool(config.get("full_mode_confirmed"))
        roots = [str(root) for root in config.get("authorized_external_roots", [])]

        current = self.query_one("#permission-current", Static)
        mode_label = "完全访问模式" if mode == AccessMode.FULL.value else "保守/沙箱模式"
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

    def _set_mode_from_form(self) -> None:
        select = self.query_one("#permission-mode-select", Select)
        mode = str(select.value or AccessMode.CONSERVATIVE.value)
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
        if table.cursor_row is None or table.cursor_row < 0 or table.cursor_row >= table.row_count:
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
