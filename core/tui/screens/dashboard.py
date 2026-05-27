"""Dashboard view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from core.tui.i18n import t


class DashboardView(Vertical):
    """Dashboard showing system status and quick actions."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("dashboard_title"), classes="section-title")
        yield DataTable(id="dashboard-table", cursor_type="row", classes="dashboard-stat")

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        table = self.query_one("#dashboard-table", DataTable)
        table.add_columns(t("dashboard_metric"), t("dashboard_value"))

        # Init status
        is_initialized = (self._project_root / ".supermedicine").is_dir()
        table.add_row(
            t("dashboard_status"),
            t("dashboard_initialized") if is_initialized else t("dashboard_not_initialized"),
        )

        # Workspaces
        try:
            from core.workspace import WorkspaceManager

            ws_count = len(WorkspaceManager(self._project_root).list_workspaces())
        except Exception:
            ws_count = 0
        table.add_row(t("dashboard_workspaces"), str(ws_count))

        # Plugins
        plugins_dir = self._project_root / "plugins"
        plugin_count = sum(
            1 for d in plugins_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and (d / "plugin.yaml").exists()
        ) if plugins_dir.is_dir() else 0
        table.add_row(t("dashboard_plugins"), str(plugin_count))

        # Modules
        core_dir = self._project_root / "core"
        module_count = (
            sum(1 for p in core_dir.iterdir() if p.is_dir() and not p.name.startswith("_"))
            if core_dir.is_dir()
            else 0
        )
        table.add_row(t("dashboard_modules"), str(module_count))

        # Version
        version = "0.3.0b0"
        try:
            from importlib.metadata import version as pkg_version

            version = pkg_version("supermedicine")
        except Exception:
            pass
        table.add_row(t("dashboard_version"), version)


# Backward-compatible alias
DashboardScreen = DashboardView

