"""Chat view for SuperMedicine TUI - main interaction interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog

from core.tui.i18n import t


class ChatView(Vertical):
    """Chat interface with message input and conversation display."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._message_count = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-output", wrap=True, highlight=True, markup=True)

    def on_mount(self) -> None:
        """Show welcome message."""
        self.add_system_message(t("welcome"))
        self.add_system_message(t("sandbox_notice"))
        self.add_system_message("---")
        self.add_system_message(t("chat_help"))

    def add_user_message(self, message: str) -> None:
        """Add a user message to the chat display."""
        output = self.query_one("#chat-output", RichLog)
        self._message_count += 1
        output.write(f"[bold cyan]🧑 You:[/bold cyan] {escape(message)}")
        output.write("")

    def add_system_message(self, message: str) -> None:
        """Add a system message to the chat display."""
        output = self.query_one("#chat-output", RichLog)
        output.write(f"[dim italic]⚙ {escape(message)}[/dim italic]")

    def add_assistant_message(self, message: str) -> None:
        """Add an assistant/AI message to the chat display."""
        output = self.query_one("#chat-output", RichLog)
        self._message_count += 1
        output.write("[bold green]🤖 Assistant:[/bold green]")
        output.write(escape(message))
        output.write("")

    def add_error_message(self, message: str) -> None:
        """Add an error message to the chat display."""
        output = self.query_one("#chat-output", RichLog)
        output.write(f"[bold red]❌ {escape(message)}[/bold red]")
        output.write("")

    def clear_chat(self) -> None:
        """Clear the chat display."""
        output = self.query_one("#chat-output", RichLog)
        output.clear()
        self._message_count = 0
