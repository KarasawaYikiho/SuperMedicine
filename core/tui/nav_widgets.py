"""Navigation widget classes for the SuperMedicine TUI."""

from __future__ import annotations

from typing import cast

from textual import events
from textual.app import ComposeResult
from textual.widgets import ListItem, Static


class NavItem(ListItem):
    """A sidebar navigation item."""

    def __init__(self, label: str, view_id: str) -> None:
        super().__init__()
        self.view_id = view_id
        self._label = label

    def compose(self) -> ComposeResult:
        yield Static(self._label)


class MenuOption(ListItem):
    """A selectable entry in the TUI menu overlay."""

    def __init__(self, label: str, option_id: str, view_id: str | None = None) -> None:
        super().__init__()
        self.option_id = option_id
        self.view_id = view_id
        self._label = label

    def compose(self) -> ComposeResult:
        yield Static(self._label)


class MenuButton(Static):
    """Clickable upper-left menu affordance for mouse-capable terminals."""

    def on_click(self, event: events.Click) -> None:
        event.stop()
        from core.tui.app import SuperMedicineTUI

        app = cast("SuperMedicineTUI", self.app)
        app.action_open_menu()
