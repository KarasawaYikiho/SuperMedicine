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

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-output", wrap=True, highlight=True, markup=True)

    def on_mount(self) -> None:
        """Show welcome message."""
        self.add_system_message(t("welcome"))
        self.add_system_message(t("sandbox_notice"))
        self.add_system_message(t("chat_help"))
        self.add_status_message(t("chat_empty_hint"))

    def _write_separator(self, output: RichLog) -> None:
        output.write(f"[dim]{safe_display_text(t('chat_separator'))}[/dim]")

    def _write_block(
        self,
        label: str,
        icon: str,
        style: str,
        message: str,
        *,
        blank_after: bool = True,
    ) -> None:
        output = self.query_one("#chat-output", RichLog)
        lines = [
            f"[dim]{safe_display_text(t('chat_separator'))}[/dim]",
            f"[{style}]{icon} {safe_display_text(label)}[/]",
            safe_display_text(message),
        ]
        if blank_after:
            lines.append("")
        block = "\n".join(lines)
        output.write(block)

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
        output = self.query_one("#chat-output", RichLog)
        output.write(
            "\n".join(
                [
                    f"[dim]{safe_display_text(t('chat_separator'))}[/dim]",
                    f"[bold green]🤖 {safe_display_text(t('chat_assistant_label') + f' #{assistant_turn}')}[/]",
                    safe_display_text("助手正在生成回复..."),
                ]
            )
        )
        return assistant_turn

    def append_assistant_delta(self, message: str) -> None:
        """Append an assistant streaming delta without changing input focus/state."""
        if not message:
            return
        output = self.query_one("#chat-output", RichLog)
        output.write(safe_display_text(message))

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
        self._write_block(
            "推理状态", "🧠", "bold magenta", message, blank_after=False
        )

    def clear_chat(self) -> None:
        """Clear the chat display."""
        output = self.query_one("#chat-output", RichLog)
        output.clear()
        self._turn_count = 0
        self._last_user_turn = 0
        self._last_assistant_turn = 0
        self.add_status_message(t("chat_empty_hint"))
