"""Dashboard view for SuperMedicine TUI."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.tui.app import apply_status_style
from core.tui.i18n import t
from core.workspace import WorkspaceManager


def collect_dashboard_context(project_root: Path | str | None = None) -> dict[str, Any]:
    """Collect dashboard data without depending on Textual widgets."""

    root = Path(project_root) if project_root else Path.cwd()
    workspace_infos = _safe_workspace_infos(root)
    llm_status, llm_ready = _safe_llm_status(root)
    initialized = (root / ".supermedicine").is_dir()

    context = {
        "initialized": initialized,
        "init_status": t("dashboard_initialized")
        if initialized
        else t("dashboard_not_initialized"),
        "workspace_count": len(workspace_infos),
        "plugin_count": _count_plugins(root),
        "module_count": _count_core_modules(root),
        "llm_status": llm_status,
        "llm_ready": llm_ready,
        "token_stats": _safe_token_stats(root),
        "recent_hint": _recent_workspace_hint(root, workspace_infos),
        "version": _package_version(),
    }
    context["action_hint"] = _action_hint(context)
    return context


class DashboardOverviewController:
    """Controller that formats dashboard context for the TUI table."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root) if project_root else Path.cwd()

    def context(self) -> dict[str, Any]:
        return collect_dashboard_context(self.project_root)

    def overview_rows(self) -> list[tuple[str, str]]:
        context = self.context()
        token_stats = context.get("token_stats", {})
        total_tokens = token_stats.get("total_tokens", 0)
        request_count = token_stats.get("request_count", 0)
        token_display = (
            f"{total_tokens:,} ({request_count} 次请求)"
            if total_tokens > 0
            else t("dashboard_no_token_data")
        )
        return [
            (t("dashboard_init_status"), str(context["init_status"])),
            (t("dashboard_workspaces"), str(context["workspace_count"])),
            (t("dashboard_plugins"), str(context["plugin_count"])),
            (t("dashboard_modules"), str(context["module_count"])),
            (t("dashboard_llm_status"), str(context["llm_status"])),
            (t("dashboard_token_stats"), token_display),
            (t("dashboard_recent_hint"), str(context["recent_hint"])),
            (t("dashboard_version"), str(context["version"])),
        ]

    def advice_text(self) -> str:
        return str(self.context()["action_hint"])


def _safe_workspace_infos(root: Path) -> list[Any]:
    try:
        return WorkspaceManager(root).list_workspaces()
    except Exception:
        return []


def _count_plugins(root: Path) -> int:
    plugins_dir = root / "plugins"
    if not plugins_dir.is_dir():
        return 0
    return sum(
        1
        for item in plugins_dir.iterdir()
        if item.is_dir()
        and not item.name.startswith("_")
        and (item / "plugin.yaml").exists()
    )


def _count_core_modules(root: Path) -> int:
    core_dir = root / "core"
    if not core_dir.is_dir():
        return 0
    return sum(
        1
        for item in core_dir.iterdir()
        if item.is_dir() and not item.name.startswith("_")
    )


def _safe_token_stats(root: Path) -> dict[str, int]:
    try:
        from core.token_tracker import TokenTracker

        tracker = TokenTracker(root / ".supermedicine" / "tokens.jsonl")
        return tracker.summary()
    except Exception:
        return {"total_tokens": 0, "request_count": 0}


def _safe_llm_status(root: Path) -> tuple[str, bool]:
    try:
        manager = LLMConfigManager(
            ConfigCenter(root / ".supermedicine" / "config.yaml")
        )
        providers = manager.list_providers(redacted=True)
        current = manager.get_current_provider(redacted=True)
        provider = str(current.get("provider") or "")
        if not providers or not provider:
            return f"{t('llm_not_ready')}：{t('dashboard_llm_no_provider')}", False
        validation = manager.validate_provider(provider)
        if validation is None:
            model = str(current.get("model") or "").strip()
            suffix = f"（{model}）" if model else ""
            return f"{t('llm_ready')}：{provider}{suffix}", True
        missing = validation.get("error", {}).get("details", {}).get("missing", [])
        missing_text = (
            "、".join(str(item) for item in missing) if missing else t("llm_not_ready")
        )
        return (
            f"{t('llm_not_ready')}：{provider}（{t('dashboard_llm_missing')}：{missing_text}）",
            False,
        )
    except Exception:
        return f"{t('llm_not_ready')}：{t('dashboard_llm_no_provider')}", False


def _recent_workspace_hint(root: Path, workspace_infos: list[Any]) -> str:
    if not workspace_infos:
        return t("dashboard_no_workspace_hint")
    manager = WorkspaceManager(root)
    for workspace in workspace_infos:
        workspace_id = str(getattr(workspace, "id", ""))
        if not workspace_id:
            continue
        try:
            recent = manager.load_recent_selection(workspace_id)
        except Exception:
            recent = None
        if recent:
            return f"{t('dashboard_recent_workspace_hint')}：{recent}"
    return f"{t('dashboard_recent_workspace_hint')}：{getattr(workspace_infos[0], 'id', '')}"


def _package_version() -> str:
    try:
        return pkg_version("supermedicine")
    except Exception:
        return "0.4.2b0"


def _action_hint(context: dict[str, Any]) -> str:
    if not context.get("initialized"):
        return t("dashboard_action_init")
    if int(context.get("workspace_count") or 0) == 0:
        return t("dashboard_action_create_workspace")
    if not context.get("llm_ready"):
        return t("dashboard_action_configure_llm")
    return t("dashboard_action_ready")


class DashboardView(Vertical):
    """Dashboard showing system status and quick actions."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._controller = DashboardOverviewController(self._project_root)

    def compose(self) -> ComposeResult:
        yield Static(t("dashboard_title"), classes="section-title")
        yield Static(t("sandbox_notice"), id="dashboard-summary")
        yield DataTable(
            id="dashboard-table", cursor_type="row", classes="dashboard-stat"
        )
        yield Static("", id="dashboard-advice")
        yield Static(
            t("status_shortcuts_hint"), id="dashboard-shortcuts", classes="hint"
        )

    def on_mount(self) -> None:
        self._load_data()

    def refresh_view_data(self) -> None:
        """Refresh dynamic dashboard metrics when the view becomes active."""

        self._load_data()

    def _load_data(self) -> None:
        table = self.query_one("#dashboard-table", DataTable)
        table.clear(columns=True)
        table.add_columns(t("dashboard_metric"), t("dashboard_value"))
        for metric, value in self._controller.overview_rows():
            table.add_row(metric, value)
        self.query_one("#dashboard-advice", Static).update(
            f"{t('dashboard_action_hint')}：{self._controller.advice_text()}"
        )
        apply_status_style(
            self.query_one("#dashboard-advice", Static), self._controller.advice_text()
        )


# Backward-compatible alias
DashboardScreen = DashboardView
