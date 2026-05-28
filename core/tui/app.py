"""SuperMedicine TUI Application."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.tui.i18n import LABELS, t


_DISPLAY_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*([:=])\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),
)


def _redact_display_secrets(value: str) -> str:
    """Redact common secret shapes before handing text to chat rendering."""

    text = value
    for pattern in _DISPLAY_SECRET_PATTERNS:
        if "Bearer" in pattern.pattern:
            text = pattern.sub("Bearer [已隐藏]", text)
        elif "sk-" in pattern.pattern:
            text = pattern.sub("[已隐藏密钥]", text)
        else:
            text = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[已隐藏]", text)
    return text


_CSS_PATH = Path(__file__).parent / "app.tcss"

STATUS_STYLE_CLASSES = ("status-info", "status-success", "status-warning", "status-error")


def apply_status_style(widget: Static, message: str) -> None:
    """Apply a semantic style class to a status widget based on its message."""

    widget.remove_class(*STATUS_STYLE_CLASSES)
    text = message.lower()
    if t("error").lower() in text or "error" in text or "失败" in message:
        widget.add_class("status-error")
    elif "缺少" in message or "未" in message or "请选择" in message or "确认" in message:
        widget.add_class("status-warning")
    elif "成功" in message or "已" in message or "ready" in text or "ok" in text:
        widget.add_class("status-success")
    else:
        widget.add_class("status-info")


@dataclass(frozen=True, slots=True)
class TUIStatus:
    """Test-friendly TUI startup status."""

    title: str
    message: str
    labels: dict[str, str]
    interactive: bool
    llm_ready: bool = False
    llm_provider: str = ""
    current_view: str = "chat"
    view_title: str = ""
    shortcut_hint: str = ""
    status_left: str = ""
    status_center: str = ""
    status_right: str = ""
    focus_target: str = "prompt-input"


@dataclass(frozen=True, slots=True)
class NavMetadata:
    """Test-friendly navigation metadata."""

    key: str
    view_id: str
    label: str
    icon: str


@dataclass(frozen=True, slots=True)
class ShellStatusText:
    """Status bar text for the TUI shell."""

    left: str
    center: str
    right: str
    focus: str


class NavItem(ListItem):
    """A sidebar navigation item."""

    def __init__(self, label: str, view_id: str) -> None:
        super().__init__()
        self.view_id = view_id
        self._label = label

    def compose(self) -> ComposeResult:
        yield Static(self._label)


class SuperMedicineTUI(App[Any]):
    """Main TUI application with persistent sidebar and swappable content."""

    CSS_PATH = str(_CSS_PATH)
    TITLE = t("app_title")

    BINDINGS = [
        Binding("q", "quit", t("nav_quit")),
        Binding("f", "toggle_maximize", t("nav_maximize"), show=True),
        Binding("question_mark", "show_help", t("help_title"), show=True),
        Binding("1", "switch_view('chat')", t("nav_chat"), show=False),
        Binding("2", "switch_view('dashboard')", t("nav_dashboard"), show=False),
        Binding("3", "switch_view('workspace')", t("nav_workspace"), show=False),
        Binding("4", "switch_view('paper')", t("nav_paper"), show=False),
        Binding("5", "switch_view('experience')", t("nav_experience"), show=False),
        Binding("6", "switch_view('tool')", t("nav_tool"), show=False),
        Binding("7", "switch_view('dialog')", t("nav_dialog"), show=False),
        Binding("8", "switch_view('llm')", t("nav_llm"), show=False),
    ]

    NAV_ITEMS = (
        NavMetadata("1", "chat", t("nav_chat"), "💬"),
        NavMetadata("2", "dashboard", t("nav_dashboard"), "📊"),
        NavMetadata("3", "workspace", t("nav_workspace"), "📁"),
        NavMetadata("4", "paper", t("nav_paper"), "📄"),
        NavMetadata("5", "experience", t("nav_experience"), "💡"),
        NavMetadata("6", "tool", t("nav_tool"), "🔧"),
        NavMetadata("7", "dialog", t("nav_dialog"), "📋"),
        NavMetadata("8", "llm", t("nav_llm"), "🤖"),
    )

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._current_view = "chat"
        self._views: dict[str, Any] = {}
        self._task_running = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app-body"):
            with Vertical(id="sidebar"):
                yield Static(t("layout_sidebar_title"), id="sidebar-title")
                yield Static(t("layout_sidebar_subtitle"), id="sidebar-subtitle")
                yield ListView(
                    *(
                        NavItem(f"{item.key} {item.icon} {item.label}", item.view_id)
                        for item in self.nav_items()
                    ),
                    id="nav-list",
                )
                yield Static(f"{t('layout_shortcuts')}\n{self.shortcut_hint_text()}", id="sidebar-shortcuts")
            with Vertical(id="main-area"):
                yield Static(t("nav_chat"), id="view-title")
                yield Vertical(id="content-pane")
                with Horizontal(id="input-bar"):
                    yield Static("> ", id="prompt-prefix")
                    yield Input(
                        placeholder=t("input_placeholder"),
                        id="prompt-input",
                    )
        with Horizontal(id="status-bar"):
            yield Static("", id="status-left")
            yield Static("", id="status-center")
            yield Static("", id="status-right")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize views and show chat by default."""
        from core.tui.screens.chat_view import ChatView
        from core.tui.screens.dashboard import DashboardView
        from core.tui.screens.dialog_screen import DialogView
        from core.tui.screens.experience_screen import ExperienceView
        from core.tui.screens.llm_screen import LLMView
        from core.tui.screens.paper_screen import PaperView
        from core.tui.screens.tool_screen import ToolView
        from core.tui.screens.workspace_screen import WorkspaceView

        self._views = {
            "chat": ChatView(self.project_root),
            "dashboard": DashboardView(self.project_root),
            "workspace": WorkspaceView(self.project_root),
            "paper": PaperView(self.project_root),
            "experience": ExperienceView(self.project_root),
            "tool": ToolView(self.project_root),
            "dialog": DialogView(self.project_root),
            "llm": LLMView(self.project_root),
        }
        # Add all views to content pane, hide all except chat
        content_pane = self.query_one("#content-pane")
        for name, view in self._views.items():
            content_pane.mount(view)
            if name != "chat":
                view.display = False

        self._update_status_bar()
        self._update_view_title("chat")
        # Focus the input
        self.query_one("#prompt-input", Input).focus()

    def action_switch_view(self, view_id: str) -> None:
        """Switch the visible content view."""
        if view_id == self._current_view:
            self._focus_prompt_input()
            self._update_status_bar()
            return
        # Hide current, show new
        if self._current_view in self._views:
            self._views[self._current_view].display = False
        if view_id in self._views:
            self._views[view_id].display = True
            self._current_view = view_id
            self._update_view_title(view_id)
            self._update_status_bar()
            # Update sidebar selection
            nav_list = self.query_one("#nav-list", ListView)
            for i, item in enumerate(nav_list.query(NavItem)):
                if item.view_id == view_id:
                    nav_list.index = i
                    break
            self._focus_prompt_input()

    @classmethod
    def nav_items(cls) -> tuple[NavMetadata, ...]:
        """Return navigation items and numeric shortcuts."""

        return cls.NAV_ITEMS

    @classmethod
    def view_title_text(cls, view_id: str) -> str:
        """Return the human-readable title for a view."""

        title_map = {item.view_id: item.label for item in cls.nav_items()}
        return title_map.get(view_id, view_id)

    @staticmethod
    def shortcut_hint_text() -> str:
        """Return the global shortcut hint shown in sidebar and dry-run output."""

        return t("status_shortcuts_hint")

    def status_text(self, view_id: str | None = None) -> ShellStatusText:
        """Build current status bar text without mutating widgets."""

        current_view = view_id or self._current_view
        task_state = t("status_task_running") if self._task_running else t("status_task_idle")
        left = f"📁 {self._workspace_count()} {t('status_workspaces')}"
        center = f"🔌 {self._plugin_count()} {t('status_plugins')}  |  {self._llm_status_label()}  |  {task_state}"
        right = f"{t('layout_current_view')}：{self.view_title_text(current_view)}  |  SuperMedicine {self._package_version()}"
        focus = f"{t('layout_focus')}：{t('status_focus_input')}"
        return ShellStatusText(left=left, center=center, right=right, focus=focus)

    def _focus_prompt_input(self) -> None:
        """Move focus back to the prompt input after navigation."""

        try:
            self.query_one("#prompt-input", Input).focus()
        except Exception:
            pass

    def action_toggle_maximize(self) -> None:
        """Toggle maximize on the focused widget."""
        if self.screen.maximized is not None:
            self.screen.minimize()
        else:
            focused = self.screen.focused
            if focused is not None and getattr(focused, "allow_maximize", False):
                self.screen.maximize(focused)

    def action_show_help(self) -> None:
        """Show help information."""
        self.notify(
            f"{t('help_navigation')}\n{t('help_global')}\n{t('help_escape_hint')}",
            title=t("help_title"),
            timeout=10,
        )

    def _update_view_title(self, view_id: str) -> None:
        """Update the view title bar."""
        title_widget = self.query_one("#view-title", Static)
        title_widget.update(f"{self.view_title_text(view_id)}  ·  {self.shortcut_hint_text()}")

    def _update_status_bar(self) -> None:
        """Update the bottom status bar with context info."""
        status_left = self.query_one("#status-left", Static)
        status_center = self.query_one("#status-center", Static)
        status_right = self.query_one("#status-right", Static)
        status = self.status_text()
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")

        status_left.update(f"  {status.left}  |  {status.focus}")
        status_center.update(f"  {status.center}")
        status_right.update(f"  🕐 {now}  |  {status.right}  ")

    def _workspace_count(self) -> int:
        try:
            from core.workspace import WorkspaceManager

            manager = WorkspaceManager(self.project_root)
            return len(manager.list_workspaces())
        except Exception:
            return 0

    def _plugin_count(self) -> int:
        plugins_dir = self.project_root / "plugins"
        return sum(
            1 for d in plugins_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and (d / "plugin.yaml").exists()
        ) if plugins_dir.is_dir() else 0

    @staticmethod
    def _package_version() -> str:
        try:
            from importlib.metadata import version as pkg_version
            return pkg_version("supermedicine")
        except Exception:
            return "0.3.0b0"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle sidebar navigation item selection."""
        if isinstance(event.item, NavItem):
            self.action_switch_view(event.item.view_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        message = event.value.strip()
        if not message:
            return
        # Clear input
        event.input.value = ""
        # Send to chat view
        chat_view = self._views.get("chat")
        if chat_view and hasattr(chat_view, "add_user_message"):
            chat_view.add_user_message(message)
        # Process the message
        self._process_message(message)

    def _process_message(self, message: str) -> None:
        """Process a user message through the Kernel asynchronously."""
        chat_view = self._views.get("chat")
        if not chat_view:
            return
        # Run in background worker to avoid blocking UI
        self._task_running = True
        self._update_status_bar()
        self.run_worker(self._run_kernel_task(message, chat_view), exclusive=True)

    async def _run_kernel_task(self, message: str, chat_view: Any) -> None:
        """Execute kernel task in background worker."""
        try:
            from core.kernel import Kernel

            chat_view.add_system_message(t("thinking"))

            # Build kernel with proper paths
            config_path = self.project_root / ".supermedicine" / "config.yaml"
            plugins_dir = self.project_root / "plugins"
            policies_dir = self.project_root / ".supermedicine" / "policies"

            kernel = Kernel(
                config_path=config_path,
                plugins_dir=plugins_dir,
                policies_dir=policies_dir,
            )
            if hasattr(chat_view, "add_status_message"):
                chat_view.add_status_message(t("chat_running"))
            result = kernel.execute_task(message)
            formatted = self._format_kernel_result(result)

            if formatted["kind"] == "error":
                chat_view.add_error_message(formatted["message"])
            else:
                chat_view.add_assistant_message(formatted["message"])
            if hasattr(chat_view, "add_status_message"):
                chat_view.add_status_message(t("chat_completed"))
        except Exception as e:
            chat_view.add_error_message(f"{t('error')}: {e}")
        finally:
            self._task_running = False
            self._update_status_bar()

    @staticmethod
    def _format_kernel_output(output: Any) -> str:
        """Format arbitrary Kernel output into stable display text."""

        if output is None or output == "":
            return t("chat_no_output")
        if isinstance(output, str):
            return _redact_display_secrets(output or t("chat_no_output"))
        if isinstance(output, (dict, list, tuple)):
            try:
                return _redact_display_secrets(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
            except TypeError:
                return _redact_display_secrets(str(output))
        return _redact_display_secrets(str(output))

    @classmethod
    def _format_kernel_result(cls, result: Any) -> dict[str, str]:
        """Format Kernel result dict/list/string/empty values for ChatView."""

        if not isinstance(result, dict):
            output = cls._format_kernel_output(result)
            return {"kind": "assistant", "message": f"{t('chat_result_status')}: unknown\n{t('chat_result_output')}:\n{output}"}

        status = str(result.get("status") or "unknown")
        error = result.get("error") or result.get("reason")
        output = cls._format_kernel_output(result.get("output", result.get("result", "")))
        header = f"{t('chat_result_status')}: {status}"

        if error:
            return {"kind": "error", "message": f"{header}\n{_redact_display_secrets(str(error))}"}
        return {"kind": "assistant", "message": f"{header}\n{t('chat_result_output')}:\n{output}"}

    def _llm_manager(self) -> LLMConfigManager:
        config_path = self.project_root / ".supermedicine" / "config.yaml"
        return LLMConfigManager(ConfigCenter(config_path))

    def _llm_status_label(self) -> str:
        try:
            manager = self._llm_manager()
            current = manager.get_current_provider(redacted=True)
            provider = str(current.get("provider") or "")
            if provider and manager.validate_provider(provider) is None:
                return f"🤖 {provider} {t('llm_ready')}"
            return f"🤖 {t('llm_not_ready')}"
        except Exception:
            return f"🤖 {t('llm_not_ready')}"

    def _save_llm_exit_state(self) -> None:
        try:
            self._llm_manager().save_exit_state()
        except Exception:
            pass

    def on_unmount(self) -> None:
        """Persist the last selected LLM provider when the app closes."""
        self._save_llm_exit_state()


def launch_tui(*, dry_run: bool = False, project_root: Path | str | None = None) -> TUIStatus:
    """Launch or describe the Chinese TUI foundation.

    ``dry_run`` returns a status object and prints a minimal Chinese readiness
    message, which keeps command-line tests non-interactive.
    """

    root = Path(project_root) if project_root else Path.cwd()
    llm_ready, llm_provider = _describe_llm_status(root)
    shell = SuperMedicineTUI(project_root=root)
    shell_status = shell.status_text("chat")
    view_title = shell.view_title_text("chat")
    shortcut_hint = shell.shortcut_hint_text()
    status_message = t("dry_run_status") if dry_run else t("welcome")
    if dry_run:
        llm_text = f"{t('llm_ready')}: {llm_provider}" if llm_ready else t("llm_not_ready")
        status_message = f"{status_message}；{llm_text}"

    status = TUIStatus(
        title=t("app_title"),
        message=status_message,
        labels=dict(LABELS),
        interactive=not dry_run,
        llm_ready=llm_ready,
        llm_provider=llm_provider,
        current_view="chat",
        view_title=view_title,
        shortcut_hint=shortcut_hint,
        status_left=shell_status.left,
        status_center=shell_status.center,
        status_right=shell_status.right,
        focus_target="prompt-input",
    )
    console = Console()
    console.print(f"[bold]{status.title}[/bold]")
    console.print(status.message)
    console.print(t("sandbox_notice"))
    console.print(f"{t('layout_current_view')}：{status.view_title}")
    console.print(f"{t('layout_shortcuts')}：{status.shortcut_hint}")
    console.print(shell_status.focus)
    console.print(f"{status.status_left} | {status.status_center} | {status.status_right}")
    if dry_run:
        return status

    try:
        app = SuperMedicineTUI(project_root=project_root or Path.cwd())
        app.run()
    except ImportError:
        console.print("Textual 未安装，无法启动交互界面。")
        return TUIStatus(
            title=status.title,
            message="Textual 未安装，无法启动交互界面。",
            labels=status.labels,
            interactive=False,
        )
    return status


def _describe_llm_status(project_root: Path | str) -> tuple[bool, str]:
    try:
        root = Path(project_root)
        manager = LLMConfigManager(ConfigCenter(root / ".supermedicine" / "config.yaml"))
        current = manager.get_current_provider(redacted=True)
        provider = str(current.get("provider") or "")
        if not provider:
            return False, ""
        return manager.validate_provider(provider) is None, provider
    except Exception:
        return False, ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supermedicine tui",
        description=t("app_title"),
    )
    parser.add_argument("--dry-run", action="store_true", help="输出中文 TUI 就绪状态，不启动交互界面")
    return parser


def main(argv: list[str] | None = None) -> TUIStatus:
    parser = build_parser()
    args = parser.parse_args(argv)
    return launch_tui(dry_run=args.dry_run)
