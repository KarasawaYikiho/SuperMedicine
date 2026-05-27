"""SuperMedicine TUI application with Textual framework."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from core.tui.i18n import LABELS, t


@dataclass(frozen=True, slots=True)
class TUIStatus:
    """Test-friendly TUI startup status."""

    title: str
    message: str
    labels: dict[str, str]
    interactive: bool


def launch_tui(*, dry_run: bool = False, project_root: Path | str | None = None) -> TUIStatus:
    """Launch or describe the Chinese TUI foundation.

    ``dry_run`` returns a status object and prints a minimal Chinese readiness
    message, which keeps command-line tests non-interactive.  The real screen
    composition is intentionally deferred to the next implementation step.
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
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import Container
        from textual.widgets import Footer, Header, Static
    except ImportError:
        console.print("Textual 未安装，无法启动交互界面。")
        return TUIStatus(
            title=status.title,
            message="Textual 未安装，无法启动交互界面。",
            labels=status.labels,
            interactive=False,
        )

    # Import screens
    from core.tui.screens.dashboard import DashboardScreen
    from core.tui.screens.dialog_screen import DialogScreen
    from core.tui.screens.experience_screen import ExperienceScreen
    from core.tui.screens.paper_screen import PaperScreen
    from core.tui.screens.tool_screen import ToolScreen
    from core.tui.screens.workspace_screen import WorkspaceScreen

    _CSS_PATH = Path(__file__).parent / "app.tcss"

    class NavItem(Static):
        """A clickable sidebar navigation item."""

        def __init__(self, label: str, screen_name: str, **kwargs: Any) -> None:
            super().__init__(label, **kwargs)
            self.screen_name = screen_name
            self.add_class("nav-item")

        def on_click(self) -> None:
            self.app.switch_screen(self.screen_name)  # type: ignore[union-attr]

    class Sidebar(Container):
        """Left sidebar with navigation items."""

        def compose(self) -> ComposeResult:
            yield Static(t("app_title"), classes="nav-label")
            yield NavItem(f"1. {t('nav_dashboard')}", "dashboard")
            yield NavItem(f"2. {t('nav_workspace')}", "workspace")
            yield NavItem(f"3. {t('nav_paper')}", "paper")
            yield NavItem(f"4. {t('nav_experience')}", "experience")
            yield NavItem(f"5. {t('nav_tool')}", "tool")
            yield NavItem(f"6. {t('nav_dialog')}", "dialog")
            yield Static("")
            yield NavItem(f"Q. {t('nav_quit')}", "__quit__")

    class SuperMedicineTUI(App[Any]):
        """Main SuperMedicine TUI application."""

        CSS_PATH = str(_CSS_PATH)
        TITLE = "SuperMedicine 终端工作台"
        BINDINGS = [
            Binding("q", "quit", t("nav_quit")),
            Binding("question_mark", "help", t("help_title")),
            Binding("1", "switch_screen('dashboard')", t("nav_dashboard"), show=False),
            Binding("2", "switch_screen('workspace')", t("nav_workspace"), show=False),
            Binding("3", "switch_screen('paper')", t("nav_paper"), show=False),
            Binding("4", "switch_screen('experience')", t("nav_experience"), show=False),
            Binding("5", "switch_screen('tool')", t("nav_tool"), show=False),
            Binding("6", "switch_screen('dialog')", t("nav_dialog"), show=False),
        ]

        def __init__(self, project_root: Path | str, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.project_root = Path(project_root)

        def compose(self) -> ComposeResult:
            yield Header()
            yield Sidebar(id="sidebar")
            yield Container(id="content")
            yield Static(t("status_bar_ready"), id="status-bar")
            yield Footer()

        def on_mount(self) -> None:
            # Register all screens
            self.install_screen(DashboardScreen(), name="dashboard")
            self.install_screen(WorkspaceScreen(), name="workspace")
            self.install_screen(PaperScreen(), name="paper")
            self.install_screen(ExperienceScreen(), name="experience")
            self.install_screen(ToolScreen(), name="tool")
            self.install_screen(DialogScreen(), name="dialog")
            # Push dashboard as default
            self.push_screen("dashboard")

        def action_help(self) -> None:
            """Show help notification."""
            help_text = f"{t('help_navigation')}\n{t('help_global')}"
            self.notify(help_text, title=t("help_title"), timeout=5)

    app = SuperMedicineTUI(project_root=project_root or Path.cwd())
    app.run()
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
