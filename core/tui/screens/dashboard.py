"""Dashboard screen for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static

from core.tui.i18n import t


class DashboardScreen(Screen):
    """Main dashboard showing system status and quick actions."""

    def compose(self) -> ComposeResult:
        yield Static(t("dashboard_title"), id="content-header", classes="section-title")
        with Vertical(id="content-body"):
            yield Static("", id="dashboard-status")
            yield DataTable(id="dashboard-table", cursor_type="row")
            yield Static(t("dashboard_quick_actions"), classes="section-title")
            with Container(id="quick-actions"):
                yield Button(t("nav_workspace"), id="goto-workspace", classes="btn btn-primary")
                yield Button(t("nav_paper"), id="goto-paper", classes="btn btn-primary")
                yield Button(t("nav_experience"), id="goto-experience", classes="btn btn-primary")
                yield Button(t("nav_tool"), id="goto-tool", classes="btn btn-primary")
                yield Button(t("nav_dialog"), id="goto-dialog", classes="btn btn-primary")

    def on_mount(self) -> None:
        self._load_dashboard_data()

    def _load_dashboard_data(self) -> None:
        project_root = self.app.project_root  # type: ignore[attr-defined]
        status_widget = self.query_one("#dashboard-status", Static)
        table = self.query_one("#dashboard-table", DataTable)

        # Check init status
        supermedicine_dir = Path(project_root) / ".supermedicine"
        is_initialized = supermedicine_dir.is_dir()

        # Build status text
        lines = []
        lines.append(f"{t('dashboard_status')}: {t('dashboard_initialized') if is_initialized else t('dashboard_not_initialized')}")

        # Count workspaces
        try:
            from core.workspace import WorkspaceManager

            manager = WorkspaceManager(project_root)
            workspaces = manager.list_workspaces()
            lines.append(f"{t('dashboard_workspaces')}: {len(workspaces)}")
        except Exception:
            lines.append(f"{t('dashboard_workspaces')}: 0")

        # Count plugins
        plugins_dir = Path(project_root) / "plugins"
        plugin_count = 0
        if plugins_dir.is_dir():
            plugin_count = sum(1 for _ in plugins_dir.iterdir())
        lines.append(f"{t('dashboard_plugins')}: {plugin_count}")

        # Count modules
        core_dir = Path(project_root) / "core"
        module_count = 0
        if core_dir.is_dir():
            module_count = sum(1 for p in core_dir.iterdir() if p.is_dir() and not p.name.startswith("_"))
        lines.append(f"{t('dashboard_modules')}: {module_count}")

        # Version
        version = "0.2.1b0"
        try:
            from importlib.metadata import version as pkg_version

            version = pkg_version("supermedicine")
        except Exception:
            pass
        lines.insert(0, f"{t('dashboard_version')}: {version}")

        status_widget.update("\n".join(lines))

        # Build table
        table.add_columns(t("dashboard_version"), t("dashboard_status"), t("dashboard_workspaces"), t("dashboard_plugins"), t("dashboard_modules"))
        table.add_row(
            version,
            t("dashboard_initialized") if is_initialized else t("dashboard_not_initialized"),
            str(len(workspaces) if "workspaces" in dir() else 0),
            str(plugin_count),
            str(module_count),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id is None:
            return
        screen_map = {
            "goto-workspace": "workspace",
            "goto-paper": "paper",
            "goto-experience": "experience",
            "goto-tool": "tool",
            "goto-dialog": "dialog",
        }
        screen_name = screen_map.get(button_id)
        if screen_name:
            self.app.switch_screen(screen_name)  # type: ignore[union-attr]
