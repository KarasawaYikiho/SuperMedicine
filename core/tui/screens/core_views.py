"""Converged TUI views for the core domain."""
# ruff: noqa: E402,F401,F811

from __future__ import annotations

# --- migrated from chat_view.py ---
import html
import re
from pathlib import Path
from typing import Any

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.timer import Timer
from textual.widgets import RichLog, Static

from core.tui.i18n import t


_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*([:=])\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),
)


def _redact_sensitive_text(value: Any) -> str:
    """Return display-safe text with common secrets redacted."""

    text = "" if value is None else str(value)
    for pattern in _SECRET_PATTERNS:
        if "Bearer" in pattern.pattern:
            text = pattern.sub("Bearer [已隐藏]", text)
        elif "sk-" in pattern.pattern:
            text = pattern.sub("[已隐藏密钥]", text)
        else:
            text = pattern.sub(
                lambda match: f"{match.group(1)}{match.group(2)}[已隐藏]", text
            )
    return text


def safe_display_text(value: Any) -> str:
    """Return escaped, secret-redacted text suitable for RichLog markup."""

    return html.escape(escape(_redact_sensitive_text(value)), quote=False)


class ChatView(Vertical):
    """Chat interface with message input and conversation display."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._turn_count = 0
        self._last_user_turn = 0
        self._last_assistant_turn = 0
        self._thinking_active = False
        self._thinking_frame = 0
        self._thinking_timer: Timer | None = None
        self._processing_active = False
        self._processing_frame = 0
        self._processing_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Container(id="chat-dialog"):
            yield RichLog(id="chat-output", wrap=True, highlight=True, markup=True)
            yield Static("", id="thinking-indicator")

    def _write_chat_output(self, content: str) -> None:
        """Write content using the full available chat dialog width."""

        output = self.query_one("#chat-output", RichLog)
        output.write(content, expand=True, shrink=False)

    def on_mount(self) -> None:
        """Show welcome message."""
        self.add_system_message(t("welcome"))
        self.add_system_message(t("sandbox_notice"))
        self.add_system_message(t("chat_help"))
        self.add_status_message(t("chat_empty_hint"))

    def _write_separator(self, output: RichLog) -> None:
        output.write(
            f"[dim]{safe_display_text(t('chat_separator'))}[/dim]",
            expand=True,
            shrink=False,
        )

    def _write_block(
        self,
        label: str,
        icon: str,
        style: str,
        message: str,
        *,
        blank_after: bool = True,
    ) -> None:
        lines = [
            f"[dim]{safe_display_text(t('chat_separator'))}[/dim]",
            f"[{style}]{icon} {safe_display_text(label)}[/]",
            safe_display_text(message),
        ]
        if blank_after:
            lines.append("")
        block = "\n".join(lines)
        self._write_chat_output(block)

    def add_user_message(self, message: str) -> int:
        """Add a user message to the chat display."""
        self._turn_count += 1
        self._last_user_turn = self._turn_count
        self._write_block(
            f"{t('chat_user_label')} #{self._last_user_turn}",
            "🧑",
            "bold cyan",
            message,
        )
        return self._last_user_turn

    def add_system_message(self, message: str) -> None:
        """Add a system message to the chat display."""
        self._write_block(
            t("chat_system_label"), "⚙", "dim italic", message, blank_after=False
        )

    def _next_assistant_turn(self, turn_id: int | None = None) -> int:
        if turn_id is not None and turn_id > 0:
            self._last_assistant_turn = turn_id
            return turn_id
        if self._last_user_turn > self._last_assistant_turn:
            self._last_assistant_turn = self._last_user_turn
            return self._last_assistant_turn
        self._turn_count += 1
        self._last_assistant_turn = self._turn_count
        return self._last_assistant_turn

    def add_assistant_message(self, message: str, turn_id: int | None = None) -> int:
        """Add an assistant/AI message to the chat display."""
        assistant_turn = self._next_assistant_turn(turn_id)
        self._write_block(
            f"{t('chat_assistant_label')} #{assistant_turn}",
            "🤖",
            "bold green",
            message,
        )
        return assistant_turn

    def begin_assistant_message(self, turn_id: int | None = None) -> int:
        """Start an assistant message block before streaming deltas arrive."""
        assistant_turn = self._next_assistant_turn(turn_id)
        self._write_chat_output(
            "\n".join(
                [
                    f"[dim]{safe_display_text(t('chat_separator'))}[/dim]",
                    f"[bold green]🤖 {safe_display_text(t('chat_assistant_label') + f' #{assistant_turn}')}[/]",
                ]
            )
        )
        return assistant_turn

    def append_assistant_delta(self, message: str) -> None:
        """Append an assistant streaming delta without changing input focus/state."""
        if not message:
            return
        self._write_chat_output(safe_display_text(message))

    def add_error_message(self, message: str) -> None:
        """Add an error message to the chat display."""
        self._write_block(
            t("chat_error_label"),
            "❌",
            "bold red",
            f"{message}\n{t('chat_error_action')}",
        )

    def add_status_message(self, message: str) -> None:
        """Add a running/completion status message to the chat display."""
        self._write_block(
            t("chat_status_label"), "⏳", "bold yellow", message, blank_after=False
        )

    def add_reasoning_status(self, message: str) -> None:
        """Show provider-safe reasoning/progress status without exposing hidden thoughts."""
        self._write_block("推理状态", "🧠", "bold magenta", message, blank_after=False)

    def start_thinking_animation(self) -> None:
        """Start the lower-right in-dialog thinking animation."""
        self._thinking_active = True
        self._thinking_frame = 0
        indicator = self.query_one("#thinking-indicator", Static)
        indicator.update("[bold magenta]🧠 思考中 ○○○○○[/]")
        indicator.visible = True
        if self._thinking_timer is not None:
            self._thinking_timer.stop()
        self._thinking_timer = self.set_interval(0.3, self._advance_thinking_frame)

    def _advance_thinking_frame(self) -> None:
        """Advance the thinking animation by one frame."""
        if not getattr(self, "_thinking_active", False):
            return
        self._thinking_frame = (getattr(self, "_thinking_frame", 0) + 1) % 6
        filled = "●" * self._thinking_frame
        empty = "○" * (5 - self._thinking_frame)
        indicator = self.query_one("#thinking-indicator", Static)
        indicator.update(f"[bold magenta]🧠 思考中 {filled}{empty}[/]")

    def stop_thinking_animation(self) -> None:
        """Stop the thinking animation."""
        self._thinking_active = False
        if self._thinking_timer is not None:
            self._thinking_timer.stop()
            self._thinking_timer = None
        indicator = self.query_one("#thinking-indicator", Static)
        indicator.visible = False

    def start_processing_animation(self) -> None:
        """Start the processing animation with circle indicators."""
        self._processing_active = True
        self._processing_frame = 0
        indicator = self.query_one("#processing-indicator", Static)
        indicator.update(f"[bold yellow]⏳ {t('chat_processing_state')} ○○○○○[/]")
        indicator.visible = True
        if self._processing_timer is not None:
            self._processing_timer.stop()
        self._processing_timer = self.set_interval(0.4, self._advance_processing_frame)

    def _advance_processing_frame(self) -> None:
        """Advance the processing animation by one frame."""
        if not self._processing_active:
            return
        self._processing_frame = (self._processing_frame + 1) % 6
        filled = "●" * self._processing_frame
        empty = "○" * (5 - self._processing_frame)
        indicator = self.query_one("#processing-indicator", Static)
        indicator.update(f"[bold yellow]⏳ {t('chat_processing_state')} {filled}{empty}[/]")

    def stop_processing_animation(self) -> None:
        """Stop the processing animation."""
        self._processing_active = False
        if self._processing_timer is not None:
            self._processing_timer.stop()
            self._processing_timer = None
        indicator = self.query_one("#processing-indicator", Static)
        indicator.visible = False

    def append_thinking_content(self, content: str) -> None:
        """Append streaming thinking content without moving the fixed animation."""
        if not content:
            return
        self._write_chat_output(f"[dim magenta]{safe_display_text(content)}[/]")

    def clear_chat(self) -> None:
        """Clear the chat display."""
        output = self.query_one("#chat-output", RichLog)
        output.clear()
        self._turn_count = 0
        self._last_user_turn = 0
        self._last_assistant_turn = 0
        self.add_status_message(t("chat_empty_hint"))


# --- migrated from dashboard.py ---
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from core.services import LLMService, WorkspaceService
from core.tui.app import apply_status_style
from core.tui.i18n import t


def collect_dashboard_context(project_root: Path | str | None = None) -> dict[str, Any]:
    """Collect dashboard data without depending on Textual widgets."""

    root = Path(project_root) if project_root else Path.cwd()
    workspace_infos = _safe_workspace_infos(root)
    llm_status, llm_ready = _safe_llm_status(root)
    initialized = (root / ".supermedicine").is_dir()

    context = {
        "initialized": initialized,
        "init_status": t("dashboard_initialized")
        if initialized
        else t("dashboard_not_initialized"),
        "workspace_count": len(workspace_infos),
        "plugin_count": _count_plugins(root),
        "module_count": _count_core_modules(root),
        "llm_status": llm_status,
        "llm_ready": llm_ready,
        "token_stats": _safe_token_stats(root),
        "recent_hint": _recent_workspace_hint(root, workspace_infos),
        "version": _package_version(),
    }
    context["action_hint"] = _action_hint(context)
    return context


class DashboardOverviewController:
    """Controller that formats dashboard context for the TUI table."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def context(self) -> dict[str, Any]:
        return collect_dashboard_context(self.project_root)

    def overview_rows(self) -> list[tuple[str, str]]:
        context = self.context()
        token_stats = context.get("token_stats", {})
        total_tokens = token_stats.get("total_tokens", 0)
        request_count = token_stats.get("request_count", 0)
        token_display = (
            f"{total_tokens:,} ({request_count} 次请求)"
            if total_tokens > 0
            else t("dashboard_no_token_data")
        )
        return [
            (t("dashboard_init_status"), str(context["init_status"])),
            (t("dashboard_workspaces"), str(context["workspace_count"])),
            (t("dashboard_plugins"), str(context["plugin_count"])),
            (t("dashboard_modules"), str(context["module_count"])),
            (t("dashboard_llm_status"), str(context["llm_status"])),
            (t("dashboard_token_stats"), token_display),
            (t("dashboard_recent_hint"), str(context["recent_hint"])),
            (t("dashboard_version"), str(context["version"])),
        ]

    def advice_text(self) -> str:
        return str(self.context()["action_hint"])


def _safe_workspace_infos(root: Path) -> list[Any]:
    service = WorkspaceService(root)
    result = service.list()
    return result.data if result.ok and result.data is not None else []


def _count_plugins(root: Path) -> int:
    plugins_dir = root / "plugins"
    if not plugins_dir.is_dir():
        return 0
    return sum(
        1
        for item in plugins_dir.iterdir()
        if item.is_dir()
        and not item.name.startswith("_")
        and (item / "plugin.yaml").exists()
    )


def _count_core_modules(root: Path) -> int:
    core_dir = root / "core"
    if not core_dir.is_dir():
        return 0
    return sum(
        1
        for item in core_dir.iterdir()
        if item.is_dir() and not item.name.startswith("_")
    )


def _safe_token_stats(root: Path) -> dict[str, int]:
    try:
        from core.token_tracker import TokenTracker

        tracker = TokenTracker(root / ".supermedicine" / "tokens.jsonl")
        return tracker.summary()
    except Exception:
        return {"total_tokens": 0, "request_count": 0}


def _safe_llm_status(root: Path) -> tuple[str, bool]:
    try:
        service = LLMService(root, restore_on_startup=True)
        listed = service.list_providers()
        current_result = service.show_provider()
        providers = (listed.data or {}).get("providers", []) if listed.ok else []
        current = current_result.data or {} if current_result.ok else {}
        provider = str(current.get("provider") or "")
        if not providers or not provider:
            return f"{t('llm_not_ready')}：{t('dashboard_llm_no_provider')}", False
        validation = service.validate_provider(provider)
        if validation.ok:
            model = str(current.get("model") or "").strip()
            suffix = f"（{model}）" if model else ""
            return f"{t('llm_ready')}：{provider}{suffix}", True
        missing = validation.error.details.get("missing", []) if validation.error else []
        missing_text = (
            "、".join(str(item) for item in missing) if missing else t("llm_not_ready")
        )
        return (
            f"{t('llm_not_ready')}：{provider}（{t('dashboard_llm_missing')}：{missing_text}）",
            False,
        )
    except Exception:
        return f"{t('llm_not_ready')}：{t('dashboard_llm_no_provider')}", False


def _recent_workspace_hint(root: Path, workspace_infos: list[Any]) -> str:
    if not workspace_infos:
        return t("dashboard_no_workspace_hint")
    service = WorkspaceService(root)
    for workspace in workspace_infos:
        workspace_id = str(workspace.get("id", ""))
        if not workspace_id:
            continue
        result = service.load_selection(workspace_id)
        recent = result.data if result.ok else None
        if recent:
            return f"{t('dashboard_recent_workspace_hint')}：{recent}"
    return f"{t('dashboard_recent_workspace_hint')}：{workspace_infos[0].get('id', '')}"


def _package_version() -> str:
    try:
        return pkg_version("supermedicine")
    except Exception:
        return "0.4.2b0"


def _action_hint(context: dict[str, Any]) -> str:
    if not context.get("initialized"):
        return t("dashboard_action_init")
    if int(context.get("workspace_count") or 0) == 0:
        return t("dashboard_action_create_workspace")
    if not context.get("llm_ready"):
        return t("dashboard_action_configure_llm")
    return t("dashboard_action_ready")


class DashboardView(Vertical):
    """Dashboard showing system status and quick actions."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._controller = DashboardOverviewController(self._project_root)

    def compose(self) -> ComposeResult:
        yield Static(t("dashboard_title"), classes="section-title")
        yield Static(t("sandbox_notice"), id="dashboard-summary")
        yield DataTable(
            id="dashboard-table", cursor_type="row", classes="dashboard-stat"
        )
        yield Static("", id="dashboard-advice")
        yield Static(
            t("status_shortcuts_hint"), id="dashboard-shortcuts", classes="hint"
        )

    def on_mount(self) -> None:
        self._load_data()

    def refresh_view_data(self) -> None:
        """Refresh dynamic dashboard metrics when the view becomes active."""

        self._load_data()

    def _load_data(self) -> None:
        table = self.query_one("#dashboard-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("dashboard_metric"), t("dashboard_value"))
        for metric, value in self._controller.overview_rows():
            table.add_row(metric, value)
        self.query_one("#dashboard-advice", Static).update(
            f"{t('dashboard_action_hint')}：{self._controller.advice_text()}"
        )
        apply_status_style(
            self.query_one("#dashboard-advice", Static), self._controller.advice_text()
        )


# Backward-compatible alias
DashboardScreen = DashboardView


# --- migrated from diagnose_screen.py ---
import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style


class DiagnoseView(Vertical):
    """TUI surface aligned with the GUI/CLI diagnose feature."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static("诊断", classes="section-title")
        yield Static("输出可安全分享的配置、LLM、审计和日志诊断摘要。", classes="hint")
        with Horizontal(classes="form-row"):
            yield Button("运行全部", id="diagnose-refresh", classes="btn btn-primary")
            yield Button("配置", id="diagnose-config", classes="btn btn-secondary")
            yield Button("LLM", id="diagnose-llm", classes="btn btn-secondary")
            yield Button("安装", id="diagnose-install", classes="btn btn-secondary")
        yield Static("", id="diagnose-status")
        yield Static("点击诊断按钮以运行诊断。", id="diagnose-output")

    def on_mount(self) -> None:
        self.refresh_view_data()

    def refresh_view_data(self) -> None:
        self._run_diagnose("all")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diagnose-refresh":
            self._run_diagnose("all")
        elif event.button.id == "diagnose-config":
            self._run_diagnose("config")
        elif event.button.id == "diagnose-llm":
            self._run_diagnose("llm")
        elif event.button.id == "diagnose-install":
            self._run_diagnose("install")

    def _run_diagnose(self, section: str) -> None:
        try:
            from cli_entry import CLI

            result = CLI().diagnose()
            if section == "config":
                result = result.get("config", {})
            elif section == "llm":
                result = result.get("llm", {})
            elif section == "install":
                result = {
                    "audit": result.get("audit", {}),
                    "log_storage": result.get("log_storage", {}),
                }
            text = json.dumps(result, ensure_ascii=False, indent=2)
            self.query_one("#diagnose-output", Static).update(str(redact_sensitive(text)))
            self._set_status("诊断完成")
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#diagnose-status", Static)
        status.update(str(redact_sensitive(message)))
        apply_status_style(status, str(message))


DiagnoseScreen = DiagnoseView


# --- migrated from dialog_screen.py ---
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


# --- migrated from self_evolution_screen.py ---
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static, TextArea

from core.redaction import redact_sensitive
from core.services import ExperienceEvolutionService
from core.tui.app import apply_status_style


class SelfEvolutionView(Vertical):
    """TUI surface aligned with the GUI self-evolution feature."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static("自进化", classes="section-title")
        yield Static("生成代码、配置、文档或测试制品预览；写入仍受权限策略保护。", classes="hint")
        yield TextArea("", id="self-evolution-instruction")
        yield Select(
            [("代码", "code"), ("配置", "config"), ("文档", "documentation"), ("测试", "test")],
            value="code",
            id="self-evolution-type",
        )
        yield Input(placeholder="输出路径", id="self-evolution-output")
        with Horizontal(classes="form-row"):
            yield Button("生成制品", id="self-evolution-generate", classes="btn btn-primary")
            yield Button("刷新", id="self-evolution-refresh", classes="btn btn-secondary")
        yield DataTable(id="self-evolution-table", cursor_type="row")
        yield Static("", id="self-evolution-status")

    def on_mount(self) -> None:
        self.refresh_view_data()

    def refresh_view_data(self) -> None:
        table = self.query_one("#self-evolution-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "类型", "指令", "状态")
        service = ExperienceEvolutionService(self._project_root)
        artifacts = service.require_data(service.list_evolution_artifacts())
        for data in artifacts:
            table.add_row(
                str(data.get("id", "")),
                str(data.get("type", "-")),
                str(data.get("instruction", "-"))[:80],
                str(data.get("status", "pending")),
                key=str(data.get("id", "")),
            )
        count = len(artifacts)
        self._set_status(f"自进化制品：{count}" if count else "暂无自进化制品")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "self-evolution-refresh":
            self.refresh_view_data()
        elif event.button.id == "self-evolution-generate":
            self._generate_artifact()

    def _generate_artifact(self) -> None:
        instruction = self.query_one("#self-evolution-instruction", TextArea).text.strip()
        output = self.query_one("#self-evolution-output", Input).value.strip()
        artifact_type = self.query_one("#self-evolution-type", Select).value
        if not instruction or not output:
            self._set_status("请填写指令和输出路径")
            return
        try:
            service = ExperienceEvolutionService(self._project_root)
            result = service.require_data(service.generate_evolution(
                instruction=instruction,
                artifact_type=str(artifact_type or "code"),
                output=output,
                confirmed=False,
                metadata={"tui_entry": "self_evolution_screen"},
            ))
            self._set_status(str(redact_sensitive(result.get("message") or result.get("status") or "制品已生成")))
            self.refresh_view_data()
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#self-evolution-status", Static)
        status.update(str(redact_sensitive(message)))
        apply_status_style(status, str(message))


SelfEvolutionScreen = SelfEvolutionView
