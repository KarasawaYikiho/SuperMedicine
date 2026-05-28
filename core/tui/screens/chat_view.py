"""Chat view for SuperMedicine TUI - main interaction interface."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog

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
            text = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}[已隐藏]", text)
    return text


def safe_display_text(value: Any) -> str:
    """Return escaped, secret-redacted text suitable for RichLog markup."""

    return html.escape(escape(_redact_sensitive_text(value)), quote=False)


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
        self.add_system_message(t("chat_help"))

    def _write_separator(self, output: RichLog) -> None:
        output.write(f"[dim]{safe_display_text(t('chat_separator'))}[/dim]")

    def _write_block(self, label: str, icon: str, style: str, message: str, *, blank_after: bool = True) -> None:
        output = self.query_one("#chat-output", RichLog)
        self._write_separator(output)
        output.write(f"[{style}]{icon} {safe_display_text(label)}[/]")
        output.write(safe_display_text(message))
        if blank_after:
            output.write("")

    def add_user_message(self, message: str) -> None:
        """Add a user message to the chat display."""
        self._message_count += 1
        self._write_block(f"{t('chat_user_label')} #{self._message_count}", "🧑", "bold cyan", message)

    def add_system_message(self, message: str) -> None:
        """Add a system message to the chat display."""
        self._write_block(t("chat_system_label"), "⚙", "dim italic", message, blank_after=False)

    def add_assistant_message(self, message: str) -> None:
        """Add an assistant/AI message to the chat display."""
        self._message_count += 1
        self._write_block(f"{t('chat_assistant_label')} #{self._message_count}", "🤖", "bold green", message)

    def add_error_message(self, message: str) -> None:
        """Add an error message to the chat display."""
        self._write_block(t("chat_error_label"), "❌", "bold red", f"{message}\n{t('chat_error_action')}")

    def add_status_message(self, message: str) -> None:
        """Add a running/completion status message to the chat display."""
        self._write_block(t("chat_status_label"), "⏳", "bold yellow", message, blank_after=False)

    def clear_chat(self) -> None:
        """Clear the chat display."""
        output = self.query_one("#chat-output", RichLog)
        output.clear()
        self._message_count = 0
