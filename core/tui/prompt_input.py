"""Prompt input widget that filters terminal controls while preserving normal text."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from textual import events
from textual.widgets import Input

if TYPE_CHECKING:
    from core.tui.app import SuperMedicineTUI


class PromptInput(Input):
    """Prompt input that filters terminal controls while preserving normal text.

    IME Composition Limitation (BUG-4):
        Textual does not expose native IME composition events or hooks.  When an
        Input-style widget (including PromptInput) receives focus in the TUI the
        OS-level IME candidate window positioning is controlled entirely by the
        terminal emulator, not by Textual CSS or Python code.

        A best-effort CSS workaround is applied in ``app.tcss`` (``overflow:
        visible`` and extra margin on focused ``Input``) to reduce the chance
        that the IME overlay is clipped.  However, on some terminals the
        candidate window may still appear at the previous cursor position or at
        screen origin.  There is no further programmatic fix available until
        Textual adds first-class IME support.
    """

    ANSI_CONTROL_SEQUENCE_PATTERN = re.compile(
        r"(?:\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_])"
        r"|(?:\[<\d+(?:;\d+){0,2}[mM]|\[\?\d+(?:;\d+)*[hl]|\[\d+(?:;\d+)*[~A-Za-z])"
    )
    RAW_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    INCOMPLETE_CONTROL_SEQUENCE_PATTERN = re.compile(
        r"(?:\x1b(?:\[[0-?;<>]*[ -/]*|\][^\x07\x1b]*|)$|(?:\[<\d*(?:;\d*){0,2}|\[\?\d*(?:;\d*)*|\[\d+(?:;\d*)*)$)"
    )
    CONTROL_SEQUENCE_FINAL_CHARS = frozenset(
        "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
    )
    BACKSPACE_KEYS = frozenset({"backspace", "ctrl+h", "ctrl+?"})
    BACKSPACE_CHARACTERS = frozenset({"\b", "\x7f"})

    def on_key(self, event: events.Key) -> None:
        """Filter terminal control bytes without consuming ordinary input."""
        # Only process keys when this widget has focus
        if not self.has_focus:
            return

        # Don't process keys when a modal screen is active
        from textual.screen import ModalScreen
        if isinstance(self.app.screen, ModalScreen):
            return

        if self._is_menu_key(event):
            self._consume_key_event(event)
            event.stop()
            app = cast("SuperMedicineTUI", self.app)
            app.action_open_menu()
            return

        if self._is_backspace_key(event):
            return

        if self._is_terminal_control_key(event):
            self._consume_key_event(event)
            event.stop()
            return

        if self._value_has_incomplete_terminal_sequence():
            self._consume_key_event(event)
            event.stop()
            self.value = self._clean_terminal_control_text(self.value)
        return

    def on_input_changed(self, event: Input.Changed) -> None:
        """Drop terminal/mouse control bytes if they reach the prompt value."""

        if event.input is not self:
            return
        clean_value = self._clean_terminal_control_text(event.value)
        if clean_value != event.value:
            self.value = clean_value

    def _is_terminal_control_key(self, event: events.Key) -> bool:
        """Return True when a key event is part of a terminal control sequence."""

        if self._is_backspace_key(event):
            return False
        key = event.key
        char = getattr(event, "character", None) or getattr(event, "char", "") or ""
        if key in {"escape", "ctrl+["} or char == "\x1b":
            return True
        if char and self.RAW_CONTROL_CHARS_PATTERN.search(char):
            return True
        if char and self.ANSI_CONTROL_SEQUENCE_PATTERN.search(char):
            return True
        return False

    def _is_menu_key(self, event: events.Key) -> bool:
        """Return True when the prompt should delegate to the TUI menu action."""

        key = str(getattr(event, "key", "") or "")
        char = getattr(event, "character", None) or getattr(event, "char", "") or ""
        return key in {"M", "shift+m"} or char == "M"

    def _is_backspace_key(self, event: events.Key) -> bool:
        """Return True for terminal/Textual backspace events that should edit text."""

        key = str(getattr(event, "key", "") or "").lower()
        char = getattr(event, "character", None) or getattr(event, "char", "") or ""
        return key in self.BACKSPACE_KEYS or char in self.BACKSPACE_CHARACTERS

    def _consume_key_event(self, event: events.Key) -> None:
        """Prevent Textual's Input default handler from inserting consumed keys."""

        prevent_default = getattr(event, "prevent_default", None)
        if callable(prevent_default):
            prevent_default()

    def _value_has_incomplete_terminal_sequence(self) -> bool:
        """Detect orphan CSI/mouse prefixes before digits become prompt text."""

        value = self.value
        if not value:
            return False
        escape_index = value.rfind("\x1b")
        if escape_index >= 0:
            tail = value[escape_index:]
            return not self.ANSI_CONTROL_SEQUENCE_PATTERN.fullmatch(tail)
        csi_index = value.rfind("[")
        if csi_index < 0:
            return False
        tail = value[csi_index:]
        if self.ANSI_CONTROL_SEQUENCE_PATTERN.fullmatch(tail):
            return False
        if len(tail) == 1:
            return True
        if tail.startswith(("[<", "[?")):
            return tail[-1] not in self.CONTROL_SEQUENCE_FINAL_CHARS
        return bool(re.fullmatch(r"\[\d*(?:;\d*)*", tail))

    @classmethod
    def _clean_terminal_control_text(cls, value: str) -> str:
        """Remove terminal control/mouse escape sequences while preserving normal text."""

        without_sequences = cls.ANSI_CONTROL_SEQUENCE_PATTERN.sub("", value)
        without_incomplete_sequences = cls.INCOMPLETE_CONTROL_SEQUENCE_PATTERN.sub(
            "", without_sequences
        )
        return cls.RAW_CONTROL_CHARS_PATTERN.sub("", without_incomplete_sequences)
