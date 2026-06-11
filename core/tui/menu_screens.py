"""Menu screen classes for the SuperMedicine TUI."""

from __future__ import annotations

from typing import cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import ListView, Static

from core.tui.i18n import t
from core.tui.nav_widgets import MenuOption


class ViewSelectMenuScreen(ModalScreen[str | None]):
    """Submenu that lists all available TUI views."""

    BINDINGS = [Binding("escape", "dismiss", t("menu_back"), show=False)]

    def compose(self) -> ComposeResult:
        # Lazy import to avoid circular dependency with SuperMedicineTUI
        from core.tui.app import SuperMedicineTUI

        with Vertical(id="tui-menu-panel"):
            yield Static(
                t("menu_select_view"), id="tui-menu-title", classes="shell-title"
            )
            yield ListView(
                *(
                    MenuOption(f"{item.icon} {item.label}", "view", item.view_id)
                    for item in SuperMedicineTUI.nav_items()
                ),
                MenuOption(f"← {t('menu_back')}", "back"),
                id="tui-view-menu-list",
                classes="tui-menu-list",
            )

    def on_mount(self) -> None:
        self.query_one("#tui-view-menu-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, MenuOption):
            return
        if event.item.option_id == "back":
            self.dismiss(None)
            return
        if event.item.view_id:
            self.dismiss(event.item.view_id)


class MainMenuScreen(ModalScreen[str | None]):
    """Main menu opened by a single key, matching Textual theme-menu access."""

    BINDINGS = [Binding("escape", "dismiss", t("menu_close"), show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="tui-menu-panel"):
            yield Static(t("menu_title"), id="tui-menu-title", classes="shell-title")
            yield ListView(
                MenuOption(f"▸ {t('menu_select_view')}", "select-view"),
                MenuOption(f"◐ {t('menu_change_theme')}", "change-theme"),
                MenuOption(f"□ {t('menu_toggle_maximize')}", "toggle-maximize"),
                MenuOption(f"🛡 {t('menu_permission_settings')}", "permission-settings"),
                MenuOption(f"🤖 {t('menu_llm_settings')}", "llm-settings"),
                MenuOption(f"📁 {t('menu_workspace_settings')}", "workspace-settings"),
                MenuOption(f"? {t('menu_show_help')}", "show-help"),
                MenuOption(f"← {t('menu_close')}", "close"),
                id="tui-main-menu-list",
                classes="tui-menu-list",
            )

    def on_mount(self) -> None:
        self.query_one("#tui-main-menu-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, MenuOption):
            return
        # Lazy import to avoid circular dependency with SuperMedicineTUI
        from core.tui.app import SuperMedicineTUI

        app = cast("SuperMedicineTUI", self.app)
        if event.item.option_id == "select-view":
            self.app.push_screen(ViewSelectMenuScreen(), self._handle_view_menu_result)
        elif event.item.option_id == "change-theme":
            self.dismiss(None)
            self.app.action_change_theme()
        elif event.item.option_id == "toggle-maximize":
            self.dismiss(None)
            app.action_toggle_maximize()
        elif event.item.option_id == "permission-settings":
            self.dismiss("permission")
        elif event.item.option_id == "llm-settings":
            self.dismiss("llm")
        elif event.item.option_id == "workspace-settings":
            self.dismiss("workspace")
        elif event.item.option_id == "show-help":
            self.dismiss(None)
            app.action_show_help()
        elif event.item.option_id == "close":
            self.dismiss(None)

    def _handle_view_menu_result(self, result: str | None) -> None:
        if result is None:
            return
        self.dismiss(result)
