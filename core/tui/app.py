"""SuperMedicine TUI Application."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from textual.app import App, ComposeResult
from textual.theme import Theme
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Input, ListView, Static
from textual.timer import Timer

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.tui.i18n import LABELS, t
from core.tui.opentui_runtime import (
    OpenTUIRuntimeError,
    launch_opentui_runtime,
    runtime_info,
)
from core.tui.resources import resolve_tcss
from core.tui.status_helpers import _console_safe_text, _describe_llm_status, apply_status_style  # noqa: F401
from core.tui.kernel_output import (
    _KERNEL_OUTPUT_ASSISTANT_KEYS,
    _redact_display_secrets,
    _strip_internal_kernel_output,
)
from core.tui.menu_screens import MainMenuScreen
from core.tui.nav_widgets import MenuButton, NavItem
from core.tui.prompt_input import PromptInput
from core.tui.stream_capture import _capture_current_thread_tui_streams
from core.tui.types import (
    DynamicRefreshSurface,
    NavMetadata,
    OpenTUINavigationRoute,
    OpenTUINavigationState,
    ShellStatusText,
    TUIStatus,
)


logger = logging.getLogger(__name__)

_CSS_PATH = resolve_tcss("app.tcss")


class SuperMedicineTUI(App[Any]):
    """Main TUI application with persistent sidebar and swappable content."""

    CSS_PATH = str(_CSS_PATH)
    TITLE = t("app_title")
    AUTO_FOCUS = "#prompt-input"

    BINDINGS = [
        Binding("Q", "quit", t("nav_quit"), show=False),
        Binding("M", "open_menu", t("menu_open"), show=True),
        Binding("P", "switch_view('permission')", "权限", show=True),
    ]

    NAV_ITEMS = (
        NavMetadata("1", "chat", t("nav_chat"), "💬"),
        NavMetadata("2", "dashboard", t("nav_dashboard"), "📊"),
        NavMetadata("3", "workspace", t("nav_workspace"), "📁"),
        NavMetadata("4", "paper", t("nav_paper"), "📄"),
        NavMetadata("5", "experience", t("nav_experience"), "💡"),
        NavMetadata("6", "tool", t("nav_tool"), "🔧"),
        NavMetadata("7", "dialog", t("nav_dialog"), "📋"),
        NavMetadata("8", "llm", t("nav_llm"), "🤖"),
        NavMetadata("9", "experiment", t("nav_experiment"), "🧪"),
        NavMetadata("0", "log", t("nav_log"), "📝"),
    )

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        custom_theme = Theme(
            name="supermedicine",
            primary="#6B7280",
            secondary="#9CA3AF",
            accent="#A7F3D0",
            foreground="#E5E7EB",
            background="#0B0F14",
            surface="#111827",
            panel="#0F172A",
            success="#86EFAC",
            warning="#FDE68A",
            error="#FCA5A5",
            variables={
                "border": "#374151",
                "text-muted": "#9CA3AF",
            },
        )
        self.register_theme(custom_theme)
        self.theme = "supermedicine"
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._config_path = self.project_root / ".supermedicine" / "config.yaml"
        self._current_view = "chat"
        self._views: dict[str, Any] = {}
        self._task_running = False
        self._chat_processing = False
        self._processing_frame = 0
        self._processing_timer: Timer | None = None
        self._status_cache: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="app-body"):
            with Vertical(id="sidebar"):
                yield MenuButton(
                    f"≡ {t('menu_open')} (M)",
                    id="menu-button",
                    classes="menu-affordance",
                )
                yield Static(
                    t("layout_sidebar_title"), id="sidebar-title", classes="shell-title"
                )
                yield Static(
                    t("layout_sidebar_subtitle"),
                    id="sidebar-subtitle",
                    classes="shell-subtitle",
                )
                yield ListView(
                    *(
                        NavItem(f"{item.key} {item.icon} {item.label}", item.view_id)
                        for item in self.nav_items()
                    ),
                    id="nav-list",
                )

            with Vertical(id="main-area"):
                yield Static(t("nav_chat"), id="view-title", classes="view-heading")
                yield ScrollableContainer(id="content-pane")
                yield Static("", id="processing-indicator")
                with Horizontal(id="input-bar"):
                    yield Static("> ", id="prompt-prefix")
                    yield PromptInput(
                        placeholder=t("input_placeholder"),
                        id="prompt-input",
                    )
        with Horizontal(id="status-bar"):
            yield Static("", id="status-left")
            yield Static("", id="status-center")
            yield Static("", id="status-right")

    def on_mount(self) -> None:
        """Initialize views and show chat by default."""
        from core.tui.screens.chat_view import ChatView
        from core.tui.screens.dashboard import DashboardView
        from core.tui.screens.dialog_screen import DialogView
        from core.tui.screens.diagnose_screen import DiagnoseView
        from core.tui.screens.experience_screen import ExperienceView
        from core.tui.screens.experiment_screen import ExperimentGuideView
        from core.tui.screens.llm_screen import LLMView
        from core.tui.screens.log_screen import LogReportView
        from core.tui.screens.paper_screen import PaperView
        from core.tui.screens.permission_screen import PermissionView
        from core.tui.screens.self_evolution_screen import SelfEvolutionView
        from core.tui.screens.tool_screen import ToolView
        from core.tui.screens.workspace_screen import WorkspaceView

        self._views = {
            "chat": ChatView(self.project_root),
            "dashboard": DashboardView(self.project_root),
            "workspace": WorkspaceView(self.project_root),
            "paper": PaperView(self.project_root),
            "experience": ExperienceView(self.project_root),
            "tool": ToolView(self.project_root),
            "dialog": DialogView(self.project_root),
            "llm": LLMView(self.project_root),
            "experiment": ExperimentGuideView(self.project_root),
            "log": LogReportView(self.project_root),
            "self-evolution": SelfEvolutionView(self.project_root),
            "diagnose": DiagnoseView(self.project_root),
            "permission": PermissionView(self.project_root),
        }
        if self._current_view not in self._views:
            self._current_view = "chat"

        # Add all views to content pane, hide all except the persisted current view
        content_pane = self.query_one("#content-pane")
        for name, view in self._views.items():
            content_pane.mount(view)
            if name != self._current_view:
                view.display = False

        self._update_status_bar()
        self._update_view_title(self._current_view)
        self._refresh_visible_dynamic_data(self._current_view)
        # Focus the input
        self.query_one("#prompt-input", Input).focus()

    def action_switch_view(self, view_id: str) -> None:
        """Switch the visible content view."""
        if view_id == self._current_view:
            self._refresh_visible_dynamic_data(view_id)
            self._focus_current_view_default()
            self._update_status_bar()
            return
        # Hide current, show new
        if self._current_view in self._views:
            self._views[self._current_view].display = False
        if view_id in self._views:
            self._views[view_id].display = True
            self._current_view = view_id
            self._persist_current_view(view_id)
            self._refresh_visible_dynamic_data(view_id)
            self._update_view_title(view_id)
            self._update_status_bar()
            # Update sidebar selection
            nav_list = self.query_one("#nav-list", ListView)
            for i, item in enumerate(nav_list.query(NavItem)):
                if item.view_id == view_id:
                    nav_list.index = i
                    break
            self._focus_current_view_default()

    def refresh_workspace_views(
        self, *, selected_workspace_id: str | None = None
    ) -> None:
        """Refresh mounted views that expose workspace-dependent selectors."""

        for name, view in self._views.items():
            load_workspaces = getattr(view, "_load_workspaces", None)
            if callable(load_workspaces):
                try:
                    if name == "workspace":
                        load_workspaces(preserve_status=True)
                    else:
                        load_workspaces()
                except TypeError:
                    try:
                        load_workspaces(preserve_status=True)
                    except Exception:
                        continue
                except Exception:
                    continue
            select_workspace = getattr(view, "_select_workspace_if_available", None)
            if selected_workspace_id is not None and callable(select_workspace):
                try:
                    select_workspace(selected_workspace_id)
                except Exception:
                    continue
        try:
            self._update_status_bar()
        except Exception:
            pass

    def _refresh_visible_dynamic_data(self, view_id: str) -> None:
        """Reload dynamic view data whenever a mounted page becomes visible."""

        view = self._views.get(view_id)
        refresh_view_data = getattr(view, "refresh_view_data", None)
        if callable(refresh_view_data):
            try:
                refresh_view_data()
            except Exception:
                pass
            return
        load_workspaces = getattr(view, "_load_workspaces", None)
        if not callable(load_workspaces):
            return
        try:
            load_workspaces()
        except TypeError:
            try:
                load_workspaces(preserve_status=True)
            except Exception:
                pass
        except Exception:
            pass

    @classmethod
    def nav_items(cls) -> tuple[NavMetadata, ...]:
        """Return navigation items for sidebar and menu view selection."""

        return cls.NAV_ITEMS

    @classmethod
    def opentui_routes(cls) -> tuple[OpenTUINavigationRoute, ...]:
        """Return the shared OpenTUI page inventory for bridge metadata checks."""

        page_specs = {
            "chat": (
                "OpenTUI scrollback + split-footer prompt; Python Kernel/service layer remains the execution boundary.",
                ("Conversation Scrollback", "Prompt Footer", "Processing / Thinking Status"),
                ("Enter 提交 prompt", "/ 聚焦页面过滤", "[ ] 滚动 scrollback"),
            ),
            "dashboard": (
                "TextTable-style runtime board for workspace/plugin/LLM/token status.",
                ("Runtime Health", "Workspace Metrics", "LLM / Token Summary"),
                ("r 刷新 metrics", "Enter 打开当前指标", "Tab 切换焦点"),
            ),
            "workspace": (
                "OpenTUI selectable workspace list with bordered create/select/delete forms.",
                ("Workspace Select", "Create Workspace", "Danger Zone"),
                ("j/k 选择工作区", "Enter 选择", "Ctrl+N 聚焦创建输入"),
            ),
            "paper": (
                "OpenTUI import/list/enrich panels with permission-aware online enrichment.",
                ("Import Form", "Paper List", "Online Enrichment"),
                ("Enter 导入/选择", "r 刷新论文", "/ 过滤标题"),
            ),
            "experience": (
                "OpenTUI experience capture, suggestion and export workflow.",
                ("Suggest", "Records", "Export"),
                ("Enter 确认写入", "e 导出", "/ 过滤标签"),
            ),
            "tool": (
                "OpenTUI multi-panel tool scan/add/run workflow; permissions stay in Python service layer.",
                ("Tool Registry", "Scan Candidates", "Sandbox Run"),
                ("s 扫描", "a 添加", "Enter 运行选中工具"),
            ),
            "dialog": (
                "OpenTUI audit timeline; raw conversation fields remain rejected by Python store.",
                ("Timeline", "Session Filter", "Privacy Guard"),
                ("/ 过滤 session", "Enter 查看摘要", "[ ] 滚动时间线"),
            ),
            "llm": (
                "OpenTUI settings panel for provider CRUD with hidden API Key display.",
                ("Provider List", "Provider Form", "Validation"),
                ("Enter 切换 Provider", "d 删除", "Ctrl+S 保存"),
            ),
            "experiment": (
                "OpenTUI protocol stepper with JSON/key=value data input and calculation boundary.",
                ("Protocol", "Step Data", "Reagent Calculation"),
                ("Enter 保存步骤", "c 计算", "l 保存日志"),
            ),
            "log": (
                "OpenTUI log viewer/writer with redacted report details and list filtering.",
                ("Report Writer", "Report List", "Detail Viewer"),
                ("Enter 保存/查看", "r 刷新", "/ 过滤报告"),
            ),
        }
        return tuple(
            OpenTUINavigationRoute(
                key=item.key,
                view_id=item.view_id,
                label=item.label,
                icon=item.icon,
                placeholder=page_specs[item.view_id][0],
                sections=page_specs[item.view_id][1],
                actions=page_specs[item.view_id][2],
            )
            for item in cls.nav_items()
        )

    @classmethod
    def opentui_initial_navigation_state(cls) -> OpenTUINavigationState:
        """Return the initial OpenTUI navigation state used by bridge metadata checks."""

        return OpenTUINavigationState(
            current_view="chat",
            stack=("chat",),
            focus_target="prompt-input",
            menu_open=False,
        )

    @classmethod
    def dynamic_refresh_surfaces(cls) -> tuple[DynamicRefreshSurface, ...]:
        """Return the targeted refresh inventory without broad polling/watchers."""

        targeted = "activation/manual targeted refresh; no broad polling or filesystem watcher"
        return (
            DynamicRefreshSurface("workspace", "refresh_view_data", "#workspace-refresh", targeted),
            DynamicRefreshSurface("log", "refresh_view_data", "#log-refresh", targeted),
            DynamicRefreshSurface("dashboard", "refresh_view_data", "view activation", targeted),
            DynamicRefreshSurface("tool", "refresh_view_data", "#tool-refresh", targeted),
            DynamicRefreshSurface("dialog", "refresh_view_data", "#dialog-refresh", targeted),
        )

    @classmethod
    def view_title_text(cls, view_id: str) -> str:
        """Return the human-readable title for a view."""

        title_map = {item.view_id: item.label for item in cls.nav_items()}
        title_map["permission"] = "权限"
        title_map["self-evolution"] = t("nav_self_evolution")
        title_map["diagnose"] = t("nav_diagnose")
        return title_map.get(view_id, view_id)

    @staticmethod
    def shortcut_hint_text() -> str:
        """Return the global shortcut hint shown in sidebar and dry-run output."""

        return t("status_shortcuts_hint")

    def status_text(self, view_id: str | None = None) -> ShellStatusText:
        """Build current status bar text without mutating widgets."""

        current_view = view_id or self._current_view
        task_state = (
            t("chat_processing_state")
            if self.is_chat_processing
            else (
                t("status_task_running")
                if self._task_running
                else t("status_task_idle")
            )
        )
        layout_state = self._layout_status_label()
        left = f"📁 {self._workspace_count()} {t('status_workspaces')}"
        from cli_entry import required_runtime_snapshot

        runtime = required_runtime_snapshot(self.project_root)
        harness_label = "Harness ✓" if runtime["harness"]["healthy"] else "Harness ✗"
        rag_label = "RAG ✓" if runtime["rag"]["healthy"] else "RAG ✗"
        agents_label = f"Agents {runtime['agents']['mode']}"
        center = f"🔌 {self._plugin_count()} {t('status_plugins')}  |  {harness_label}  |  {rag_label}  |  {agents_label}  |  {self._llm_status_label()}  |  {self._permission_status_label()}  |  {task_state}"
        right = f"{t('layout_current_view')}：{self.view_title_text(current_view)}  |  {t('layout_mode')}：{layout_state}  |  SuperMedicine {self._package_version()}"
        focus = f"{t('layout_focus')}：{t('status_focus_input')}"
        return ShellStatusText(
            left=left, center=center, right=right, focus=focus, layout=layout_state
        )

    def _layout_status_label(self) -> str:
        """Return maximize state text safely for mounted and dry-run contexts."""

        try:
            return (
                t("status_layout_maximized")
                if self.screen.maximized is not None
                else t("status_layout_normal")
            )
        except Exception:
            return t("status_layout_normal")

    def _focus_prompt_input(self) -> None:
        """Move focus back to the prompt input after navigation."""

        try:
            self.query_one("#prompt-input", Input).focus()
        except Exception:
            pass

    def _refresh_visible_workspace_state(self, view_id: str) -> None:
        """Backward-compatible alias for mounted-page refresh hooks."""

        self._refresh_visible_dynamic_data(view_id)

    @property
    def is_chat_processing(self) -> bool:
        """Return whether the main Chat submit flow is currently processing."""

        return self._chat_processing

    def _begin_chat_processing(self) -> bool:
        """Activate the central Chat processing guard if no request is active."""

        if self._chat_processing:
            return False
        self._set_chat_processing(True)
        return True

    def _set_chat_processing(self, active: bool) -> None:
        """Update central Chat processing state and main prompt input lock."""

        self._chat_processing = active
        self._task_running = active
        self._update_prompt_input_lock(active)
        try:
            self._update_status_bar()
        except Exception:
            pass

    def start_processing_animation(self) -> None:
        """Show the app-level Processing indicator outside the chat dialog."""

        self._processing_frame = 0
        try:
            indicator = self.query_one("#processing-indicator", Static)
        except Exception:
            return
        indicator.update(f"[bold yellow]⏳ {t('chat_processing_state')} ○○○○○[/]")
        indicator.visible = True
        if self._processing_timer is not None:
            self._processing_timer.stop()
        self._processing_timer = self.set_interval(0.4, self._advance_processing_frame)

    def _advance_processing_frame(self) -> None:
        """Advance the app-level Processing animation by one frame."""

        if not self._chat_processing:
            return
        self._processing_frame = (self._processing_frame + 1) % 6
        filled = "●" * self._processing_frame
        empty = "○" * (5 - self._processing_frame)
        try:
            indicator = self.query_one("#processing-indicator", Static)
        except Exception:
            return
        indicator.update(f"[bold yellow]⏳ {t('chat_processing_state')} {filled}{empty}[/]")

    def stop_processing_animation(self) -> None:
        """Hide the app-level Processing indicator and stop its timer."""

        if self._processing_timer is not None:
            self._processing_timer.stop()
            self._processing_timer = None
        try:
            indicator = self.query_one("#processing-indicator", Static)
        except Exception:
            return
        indicator.visible = False

    @staticmethod
    def _safe_stop_chat_indicator(chat_view: Any, method_name: str) -> None:
        """Stop a ChatView indicator without blocking request-state cleanup."""

        method = getattr(chat_view, method_name, None)
        if not callable(method):
            return
        try:
            method()
        except Exception:
            logger.debug("Ignoring chat indicator cleanup failure: %s", method_name, exc_info=True)

    def _update_prompt_input_lock(self, active: bool) -> None:
        """Lock only the main Chat prompt input while Chat is processing."""

        try:
            prompt = self.query_one("#prompt-input", Input)
        except Exception:
            return
        prompt.disabled = active
        prompt.placeholder = (
            t("input_placeholder_processing") if active else t("input_placeholder")
        )

    def _focus_current_view_default(self) -> None:
        """Focus the active view's default control, falling back to chat prompt."""

        view = self._views.get(self._current_view)
        focus_default = getattr(view, "focus_default", None)
        if callable(focus_default):
            try:
                focus_default()
                return
            except Exception:
                pass
        self._focus_prompt_input()

    def action_toggle_maximize(self) -> None:
        """Toggle maximize on the focused widget."""
        if self.screen.maximized is not None:
            self.screen.minimize()
            self.notify(
                t("status_restored"),
                title=t("layout_mode"),
                severity="information",
                timeout=3,
            )
            self._update_status_bar()
        else:
            focused = self.screen.focused
            if focused is not None and getattr(focused, "allow_maximize", False):
                self.screen.maximize(focused)
                self.notify(
                    t("status_maximized"),
                    title=t("layout_mode"),
                    severity="information",
                    timeout=3,
                )
                self._update_status_bar()
            else:
                self.notify(
                    t("status_maximize_unavailable"),
                    title=t("layout_mode"),
                    severity="warning",
                    timeout=4,
                )

    def action_show_help(self) -> None:
        """Show help information."""
        self.notify(
            f"{t('help_navigation')}\n{t('help_global')}\n{t('help_escape_hint')}",
            title=t("help_title"),
            timeout=10,
        )

    def action_open_menu(self) -> None:
        """Open the main TUI menu."""
        self.push_screen(MainMenuScreen(), self._handle_main_menu_result)

    def action_command_palette(self) -> None:
        """Disable Textual's built-in Command Palette; settings live in the M menu."""
        self.notify(
            t("menu_open"),
            title=t("menu_title"),
            severity="information",
            timeout=2,
        )

    def _handle_main_menu_result(self, result: str | None) -> None:
        """Apply a completed main-menu selection after modal dismissal."""

        if result is None:
            return
        self.action_switch_view(result)

    def _update_view_title(self, view_id: str) -> None:
        """Update the view title bar."""
        title_widget = self.query_one("#view-title", Static)
        title_widget.update(
            f"{t('layout_current_view')}：{self.view_title_text(view_id)}  ·  {self.shortcut_hint_text()}"
        )

    def _update_status_bar(self) -> None:
        """Update the bottom status bar with context info."""
        status_left = self.query_one("#status-left", Static)
        status_center = self.query_one("#status-center", Static)
        status_right = self.query_one("#status-right", Static)
        status = self.status_text()
        now = self._status_clock_text()

        self._update_static_if_changed(
            status_left, "status-left", f"  {status.left}  |  {status.focus}"
        )
        self._update_static_if_changed(
            status_center, "status-center", f"  {status.center}"
        )
        self._update_static_if_changed(
            status_right, "status-right", f"  🕐 {now}  |  {status.right}  "
        )

    def _update_static_if_changed(
        self, widget: Static, cache_key: str, value: str
    ) -> None:
        """Avoid redundant widget updates that force unnecessary repaints."""

        if self._status_cache.get(cache_key) != value:
            self._status_cache[cache_key] = value
            widget.update(value)

    def _status_clock_text(self) -> str:
        """Return status-bar clock text isolated for stable refresh throttling."""

        return datetime.now(timezone.utc).strftime("%H:%M UTC")

    def _workspace_count(self) -> int:
        try:
            from core.services import WorkspaceService

            service = WorkspaceService(self.project_root)
            return len(service.require_data(service.list()))
        except Exception:
            return 0

    def _plugin_count(self) -> int:
        plugins_dir = self.project_root / "plugins"
        return (
            sum(
                1
                for d in plugins_dir.iterdir()
                if d.is_dir()
                and not d.name.startswith("_")
                and (d / "plugin.yaml").exists()
            )
            if plugins_dir.is_dir()
            else 0
        )

    @staticmethod
    def _package_version() -> str:
        try:
            from importlib.metadata import version as pkg_version

            return pkg_version("supermedicine")
        except Exception:
            return "0.4.2b0"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle sidebar navigation item selection."""
        if isinstance(event.item, NavItem):
            self.action_switch_view(event.item.view_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        input_id = getattr(event.input, "id", None)
        if input_id == "prompt-input":
            # existing chat handling (keep unchanged)
            event.stop()
            if self.is_chat_processing:
                chat_view = self._views.get("chat")
                if chat_view and hasattr(chat_view, "add_status_message"):
                    chat_view.add_status_message(t("chat_processing_reject"))
                self._focus_prompt_input()
                return
            message = event.value.strip()
            if not message:
                event.input.value = ""
                self._focus_prompt_input()
                return
            # Clear input
            event.input.value = ""
            # Send to chat view
            chat_view = self._views.get("chat")
            turn_id: int | None = None
            if chat_view and hasattr(chat_view, "add_user_message"):
                added_turn = chat_view.add_user_message(message)
                if isinstance(added_turn, int):
                    turn_id = added_turn
            # Process the message
            self._process_message(message, turn_id=turn_id)
            self._focus_prompt_input()
            return
        # Route to current view's unified handler
        view = self._views.get(self._current_view)
        handler = getattr(view, "handle_input_submit", None)
        if callable(handler):
            try:
                handler(input_id, event.value)
            except Exception:
                pass

    def _process_message(self, message: str, *, turn_id: int | None = None) -> None:
        """Process a user message through the Kernel asynchronously."""
        chat_view = self._views.get("chat")
        if not chat_view:
            return
        if not self._begin_chat_processing():
            if hasattr(chat_view, "add_status_message"):
                chat_view.add_status_message(t("chat_processing_reject"))
            return
        # Run in background worker to avoid blocking UI
        worker_coro = self._run_kernel_task(message, chat_view, turn_id=turn_id)
        try:
            self.run_worker(worker_coro, exclusive=True)
        except Exception:
            worker_coro.close()
            self._set_chat_processing(False)
            raise

    async def _run_kernel_task(
        self, message: str, chat_view: Any, *, turn_id: int | None = None
    ) -> None:
        """Execute kernel task in background worker."""
        try:
            from core.kernel import Kernel

            chat_view.add_system_message(t("thinking"))

            # Build kernel with proper paths
            config_path = self.project_root / ".supermedicine" / "config.yaml"
            plugins_dir = self.project_root / "plugins"
            policies_dir = self.project_root / ".supermedicine" / "policies"

            kernel = Kernel(
                config_path=config_path,
                plugins_dir=plugins_dir,
                policies_dir=policies_dir,
            )
            self.start_processing_animation()
            legacy_start_processing = getattr(chat_view, "start_processing_animation", None)
            if callable(legacy_start_processing) and chat_view.__class__.__name__ != "ChatView":
                try:
                    legacy_start_processing()
                except Exception:
                    pass
            assistant_started = False

            def render_progress(event: dict[str, Any]) -> None:
                nonlocal assistant_started
                kind = str(event.get("kind") or "")
                text = str(event.get("message") or event.get("content") or "")
                if kind == "reasoning":
                    if hasattr(chat_view, "start_thinking_animation"):
                        chat_view.start_thinking_animation()
                elif kind == "thinking_content":
                    if hasattr(chat_view, "append_thinking_content"):
                        chat_view.append_thinking_content(text)
                elif kind == "thinking_done":
                    if hasattr(chat_view, "stop_thinking_animation"):
                        chat_view.stop_thinking_animation()
                elif kind == "status":
                    if hasattr(chat_view, "stop_thinking_animation"):
                        chat_view.stop_thinking_animation()
                    if hasattr(chat_view, "add_status_message"):
                        chat_view.add_status_message(text)
                elif kind == "assistant_start":
                    if hasattr(chat_view, "stop_thinking_animation"):
                        chat_view.stop_thinking_animation()
                    if hasattr(chat_view, "begin_assistant_message"):
                        chat_view.begin_assistant_message(turn_id)
                        assistant_started = True
                elif kind == "assistant_delta" and hasattr(
                    chat_view, "append_assistant_delta"
                ):
                    if not assistant_started and hasattr(
                        chat_view, "begin_assistant_message"
                    ):
                        chat_view.begin_assistant_message(turn_id)
                        assistant_started = True
                    chat_view.append_assistant_delta(text)

            def progress_callback(event: dict[str, Any]) -> None:
                try:
                    self.call_from_thread(render_progress, event)
                except RuntimeError:
                    render_progress(event)

            def execute_in_thread() -> Any:
                with _capture_current_thread_tui_streams(self.project_root):
                    return kernel.execute_task(
                        message, progress_callback=progress_callback
                    )

            result = await asyncio.to_thread(execute_in_thread)
            formatted = self._format_kernel_result(result)

            if formatted["kind"] == "error":
                chat_view.add_error_message(formatted["message"])
            elif not assistant_started:
                chat_view.add_assistant_message(formatted["message"], turn_id=turn_id)
            if hasattr(chat_view, "add_status_message"):
                chat_view.add_status_message(t("chat_completed"))
        except Exception as e:
            chat_view.add_error_message(f"{t('error')}: {e}")
        finally:
            try:
                self._safe_stop_chat_indicator(chat_view, "stop_thinking_animation")
                self._safe_stop_chat_indicator(chat_view, "stop_processing_animation")
                self.stop_processing_animation()
            finally:
                self._set_chat_processing(False)

    @staticmethod
    def _format_kernel_output(output: Any) -> str:
        """Format arbitrary Kernel output into stable display text."""

        if output is None or output == "":
            return t("chat_no_output")
        if isinstance(output, str):
            return _redact_display_secrets(output or t("chat_no_output"))
        if isinstance(output, (dict, list, tuple)):
            try:
                return _redact_display_secrets(
                    json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True)
                )
            except TypeError:
                return _redact_display_secrets(str(output))
        return _redact_display_secrets(str(output))

    @classmethod
    def _visible_kernel_output(cls, output: Any) -> tuple[Any, list[Any]]:
        """Return chat-visible output plus any backend telemetry stripped from it."""

        if isinstance(output, dict):
            for key in _KERNEL_OUTPUT_ASSISTANT_KEYS:
                if key in output and output.get(key) not in (None, ""):
                    assistant_value, assistant_removed = _strip_internal_kernel_output(
                        output.get(key)
                    )
                    _, payload_removed = _strip_internal_kernel_output(output)
                    return assistant_value, payload_removed + assistant_removed
        return _strip_internal_kernel_output(output)

    @classmethod
    def _format_kernel_result(cls, result: Any) -> dict[str, str]:
        """Format Kernel result dict/list/string/empty values for ChatView."""

        if not isinstance(result, dict):
            output = cls._format_kernel_output(result)
            return {
                "kind": "assistant",
                "message": f"{t('chat_result_status')}: unknown\n{t('chat_result_output')}:\n{output}",
            }

        status = str(result.get("status") or "unknown")
        error = result.get("error") or result.get("reason")
        output_payload = result.get("output", result.get("result", ""))
        output_payload, stripped_internal = cls._visible_kernel_output(output_payload)
        if stripped_internal:
            logger.debug(
                "TUI kernel backend telemetry routed away from chat: status=%s telemetry=%s",
                status,
                _redact_display_secrets(str(stripped_internal)),
            )
        output = cls._format_kernel_output(output_payload)
        header = f"{t('chat_result_status')}: {status}"

        if error:
            return {
                "kind": "error",
                "message": f"{header}\n{_redact_display_secrets(str(error))}",
            }
        return {
            "kind": "assistant",
            "message": f"{header}\n{t('chat_result_output')}:\n{output}",
        }

    def _llm_manager(self) -> LLMConfigManager:
        config_path = self.project_root / ".supermedicine" / "config.yaml"
        return LLMConfigManager(ConfigCenter(config_path))

    def _llm_status_label(self) -> str:
        try:
            manager = self._llm_manager()
            current = manager.get_current_provider(redacted=True)
            provider = str(current.get("provider") or "")
            if provider and manager.validate_provider(provider) is None:
                return f"🤖 {provider} {t('llm_ready')}"
            return f"🤖 {t('llm_not_ready')}"
        except Exception:
            return f"🤖 {t('llm_not_ready')}"

    def _permission_status_label(self) -> str:
        try:
            config = ConfigCenter(self.project_root / ".supermedicine" / "config.yaml")
            return f"🛡️ 权限：{config.get_permission_mode_label()}"
        except Exception:
            return "🛡️ 权限：保守"

    def _persist_current_view(self, view_id: str) -> None:
        try:
            ConfigCenter(self._config_path).set_current_view(view_id, save=True)
        except Exception:
            logger.warning(
                "TUI runtime state sync failed: stage=current_view view=%s",
                view_id,
            )

    def _save_llm_exit_state(self) -> None:
        try:
            self._llm_manager().save_exit_state()
        except Exception:
            pass

    def on_unmount(self) -> None:
        """Persist the last selected LLM provider when the app closes."""
        self._save_llm_exit_state()


def _resolve_frozen_project_root() -> Path:
    """Return a sensible project root when running as a frozen executable.

    In frozen mode the working directory may differ from the executable
    location.  Prefer the directory that contains the executable, falling
    back to the current working directory.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / ".supermedicine").is_dir() or (exe_dir / "core").is_dir():
            return exe_dir
    return Path.cwd()


def launch_tui(
    *, dry_run: bool = False, project_root: Path | str | None = None
) -> TUIStatus:
    """Launch or describe the Chinese TUI foundation.

    ``dry_run`` returns a status object and prints a minimal Chinese readiness
    message, which keeps command-line tests non-interactive.
    """

    if project_root is not None:
        root = Path(project_root)
    else:
        root = _resolve_frozen_project_root()
    if not dry_run:
        from core.log_report_handler import configure_tui_log_storage

        configure_tui_log_storage(root)
    llm_ready, llm_provider = _describe_llm_status(root)
    shell = SuperMedicineTUI(project_root=root)
    valid_views = {item.view_id for item in shell.nav_items()} | {"permission"}
    restored_view = (
        shell._current_view if shell._current_view in valid_views else "chat"
    )
    shell_status = shell.status_text(restored_view)
    view_title = shell.view_title_text(restored_view)
    shortcut_hint = shell.shortcut_hint_text()
    status_message = t("dry_run_status") if dry_run else t("welcome")
    runtime = runtime_info()
    config_load_error = (
        ConfigCenter(root / ".supermedicine" / "config.yaml")
        .diagnostics()
        .get("load_error", "")
    )
    if dry_run:
        llm_text = (
            f"{t('llm_ready')}: {llm_provider}" if llm_ready else t("llm_not_ready")
        )
        status_message = f"{status_message}；{llm_text}"
        if config_load_error:
            status_message = (
                f"{status_message}；配置读取异常，已使用安全默认值：{config_load_error}"
            )
    logger.info(
        "TUI launch: stage=start dry_run=%s project_root=%s llm_ready=%s provider=%s",
        dry_run,
        root,
        llm_ready,
        llm_provider,
    )

    status = TUIStatus(
        title=t("app_title"),
        message=status_message,
        labels=dict(LABELS),
        interactive=not dry_run,
        llm_ready=llm_ready,
        llm_provider=llm_provider,
        current_view=restored_view,
        view_title=view_title,
        shortcut_hint=shortcut_hint,
        status_left=shell_status.left,
        status_center=shell_status.center,
        status_right=shell_status.right,
        focus_target="prompt-input",
        runtime_name=runtime.package,
        runtime_version=runtime.version,
    )
    if dry_run:
        console = Console()
        console_encoding = getattr(console.file, "encoding", None) or getattr(
            sys.stdout, "encoding", None
        )
        console.print(
            f"[bold]{_console_safe_text(status.title, console_encoding)}[/bold]"
        )
        console.print(_console_safe_text(status.message, console_encoding))
        console.print(_console_safe_text(t("sandbox_notice"), console_encoding))
        console.print(
            _console_safe_text(
                f"{t('layout_current_view')}：{status.view_title}（{t('layout_mode')}：{shell_status.layout}）",
                console_encoding,
            )
        )
        console.print(
            _console_safe_text(
                f"{t('layout_shortcuts')}：{status.shortcut_hint}", console_encoding
            )
        )
        console.print(_console_safe_text(shell_status.focus, console_encoding))
        console.print(
            _console_safe_text(
                f"{t('layout_status_bar')}：{status.status_left} | {status.status_center} | {status.status_right}",
                console_encoding,
            )
        )
        return status

    try:
        return_code = launch_opentui_runtime(project_root=root)
    except OpenTUIRuntimeError as exc:
        console = Console()
        logger.error(
            "TUI launch failed: stage=opentui_runtime_missing project_root=%s error=%s",
            root,
            exc,
        )
        console.print(str(exc))
        return TUIStatus(
            title=status.title,
            message=str(exc),
            labels=status.labels,
            interactive=False,
            runtime_name=runtime.package,
            runtime_version=runtime.version,
        )
    if return_code:
        logger.error(
            "TUI launch failed: stage=opentui_runtime_exit project_root=%s code=%s",
            root,
            return_code,
        )
    logger.info("TUI launch: stage=exit project_root=%s", project_root or Path.cwd())
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="supermedicine tui",
        description=t("app_title"),
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="输出中文 TUI 就绪状态，不启动交互界面"
    )
    return parser


def main(argv: list[str] | None = None) -> TUIStatus:
    parser = build_parser()
    args = parser.parse_args(argv)
    return launch_tui(dry_run=args.dry_run)
