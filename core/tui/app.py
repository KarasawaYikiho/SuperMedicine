"""Minimal Textual/Rich TUI entrypoint foundation."""

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
        from textual.widgets import Footer, Header, Static
    except ImportError:
        console.print("Textual 未安装，无法启动交互界面。")
        return TUIStatus(
            title=status.title,
            message="Textual 未安装，无法启动交互界面。",
            labels=status.labels,
            interactive=False,
        )

    class SuperMedicineTUI(App[Any]):
        TITLE = status.title

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static(t("welcome"))
            yield Static(t("sandbox_notice"))
            yield Footer()

    SuperMedicineTUI().run()
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
