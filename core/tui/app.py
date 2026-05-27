"""SuperMedicine TUI Application."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static

from core.tui.i18n import LABELS, t


_CSS_PATH = Path(__file__).parent / "app.tcss"


@dataclass(frozen=True, slots=True)
class TUIStatus:
    """Test-friendly TUI startup status."""

    title: str
    message: str
    labels: dict[str, str]
    interactive: bool


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
        Binding("1", "switch_view('chat')", t("nav_chat"), show=False),
        Binding("2", "switch_view('dashboard')", t("nav_dashboard"), show=False),
        Binding("3", "switch_view('workspace')", t("nav_workspace"), show=False),
        Binding("4", "switch_view('paper')", t("nav_paper"), show=False),
        Binding("5", "switch_view('experience')", t("nav_experience"), show=False),
        Binding("6", "switch_view('tool')", t("nav_tool"), show=False),
        Binding("7", "switch_view('dialog')", t("nav_dialog"), show=False),
    ]

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._current_view = "chat"
        self._views: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app-body"):
            with Vertical(id="sidebar"):
                yield ListView(
                    NavItem(f"💬 {t('nav_chat')}", "chat"),
                    NavItem(f"📊 {t('nav_dashboard')}", "dashboard"),
                    NavItem(f"📁 {t('nav_workspace')}", "workspace"),
                    NavItem(f"📄 {t('nav_paper')}", "paper"),
                    NavItem(f"💡 {t('nav_experience')}", "experience"),
                    NavItem(f"🔧 {t('nav_tool')}", "tool"),
                    NavItem(f"📋 {t('nav_dialog')}", "dialog"),
                    id="nav-list",
                )
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
            return
        # Hide current, show new
        if self._current_view in self._views:
            self._views[self._current_view].display = False
        if view_id in self._views:
            self._views[view_id].display = True
            self._current_view = view_id
            self._update_view_title(view_id)
            # Update sidebar selection
            nav_list = self.query_one("#nav-list", ListView)
            for i, item in enumerate(nav_list.query(NavItem)):
                if item.view_id == view_id:
                    nav_list.index = i
                    break

    def _update_view_title(self, view_id: str) -> None:
        """Update the view title bar."""
        title_map = {
            "chat": t("nav_chat"),
            "dashboard": t("nav_dashboard"),
            "workspace": t("nav_workspace"),
            "paper": t("nav_paper"),
            "experience": t("nav_experience"),
            "tool": t("nav_tool"),
            "dialog": t("nav_dialog"),
        }
        title_widget = self.query_one("#view-title", Static)
        title_widget.update(title_map.get(view_id, view_id))

    def _update_status_bar(self) -> None:
        """Update the bottom status bar with context info."""
        try:
            from core.workspace import WorkspaceManager

            manager = WorkspaceManager(self.project_root)
            workspaces = manager.list_workspaces()
            ws_count = len(workspaces)
        except Exception:
            ws_count = 0

        plugins_dir = self.project_root / "plugins"
        plugin_count = sum(
            1 for d in plugins_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and (d / "plugin.yaml").exists()
        ) if plugins_dir.is_dir() else 0

        now = datetime.now(timezone.utc).strftime("%H:%M UTC")

        status_left = self.query_one("#status-left", Static)
        status_center = self.query_one("#status-center", Static)
        status_right = self.query_one("#status-right", Static)

        status_left.update(f"  📁 {ws_count} {t('status_workspaces')}")
        status_center.update(f"  🔌 {plugin_count} {t('status_plugins')}")
        try:
            from importlib.metadata import version as pkg_version
            ver = pkg_version("supermedicine")
        except Exception:
            ver = "0.3.0b0"
        status_right.update(f"  🕐 {now}  |  {ver}  ")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle sidebar navigation item selection."""
        if isinstance(event.item, NavItem):
            if event.item.view_id == "__quit__":
                self.exit()
            else:
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
            result = kernel.execute_task(message)

            # Format the result nicely
            status = result.get("status", "unknown")
            output = result.get("output", "")
            error = result.get("error")

            if status == "success" and output:
                chat_view.add_assistant_message(f"{output}")
            elif error:
                chat_view.add_error_message(f"{error}")
            else:
                chat_view.add_assistant_message(f"Status: {status}\n{output or 'No output'}")
        except Exception as e:
            chat_view.add_error_message(f"{t('error')}: {e}")


def launch_tui(*, dry_run: bool = False, project_root: Path | str | None = None) -> TUIStatus:
    """Launch or describe the Chinese TUI foundation.

    ``dry_run`` returns a status object and prints a minimal Chinese readiness
    message, which keeps command-line tests non-interactive.
    """

    status = TUIStatus(
        title=t("app_title"),
        message=t("dry_run_status") if dry_run else t("welcome"),
        labels=dict(LABELS),
        interactive=not dry_run,
    )
    console = Console()
    console.print(f"[bold]{status.title}[/bold]")
    console.print(status.message)
    console.print(t("sandbox_notice"))
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
