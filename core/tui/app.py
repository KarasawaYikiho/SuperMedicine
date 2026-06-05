"""SuperMedicine TUI Application."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import re
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from textual import events
from rich.console import Console
from textual.app import App, ComposeResult
from textual.theme import Theme
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static

from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.tui.i18n import LABELS, t


logger = logging.getLogger(__name__)


class _TUILogTextSink:
    """File-like sink that routes background stdout/stderr text into Log storage."""

    def __init__(self, project_root: Path, stream_name: str) -> None:
        self.project_root = project_root
        self.stream_name = stream_name
        self._buffer = ""

    def write(self, value: str) -> int:
        text = str(value)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._append(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self._append(self._buffer)
            self._buffer = ""

    def _append(self, text: str) -> None:
        if not text.strip():
            return
        from core.log_report import append_tui_stream_output

        append_tui_stream_output(self.project_root, self.stream_name, text)


class _TUIThreadRoutedStream:
    """Route only the current worker thread stream writes to Log storage."""

    def __init__(
        self, original: Any, sink: _TUILogTextSink, owner_thread_id: int
    ) -> None:
        self._original = original
        self._sink = sink
        self._owner_thread_id = owner_thread_id
        self.encoding = getattr(original, "encoding", None)
        self.errors = getattr(original, "errors", None)

    def write(self, value: str) -> int:
        if threading.get_ident() == self._owner_thread_id:
            return self._sink.write(value)
        return self._original.write(value)

    def flush(self) -> None:
        if threading.get_ident() == self._owner_thread_id:
            self._sink.flush()
            return
        self._original.flush()

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        return self._original.fileno()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


@contextlib.contextmanager
def _capture_current_thread_tui_streams(project_root: Path):
    """Capture Kernel stdout/stderr without redirecting TUI renderer writes."""

    stdout_sink = _TUILogTextSink(project_root, "stdout")
    stderr_sink = _TUILogTextSink(project_root, "stderr")
    owner_thread_id = threading.get_ident()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = _TUIThreadRoutedStream(original_stdout, stdout_sink, owner_thread_id)  # type: ignore[assignment]
    sys.stderr = _TUIThreadRoutedStream(original_stderr, stderr_sink, owner_thread_id)  # type: ignore[assignment]
    try:
        yield
    finally:
        stdout_sink.flush()
        stderr_sink.flush()
        sys.stdout = original_stdout
        sys.stderr = original_stderr


_DISPLAY_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*([:=])\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),
)


def _redact_display_secrets(value: str) -> str:
    """Redact common secret shapes before handing text to chat rendering."""

    text = value
    for pattern in _DISPLAY_SECRET_PATTERNS:
        if "Bearer" in pattern.pattern:
            text = pattern.sub("Bearer [已隐藏]", text)
        elif "sk-" in pattern.pattern:
            text = pattern.sub("[已隐藏密钥]", text)
        else:
            text = pattern.sub(
                lambda match: f"{match.group(1)}{match.group(2)}[已隐藏]", text
            )
    return text


_KERNEL_OUTPUT_ASSISTANT_KEYS = (
    "assistant",
    "answer",
    "response",
    "content",
    "message",
    "text",
)
_KERNEL_OUTPUT_INTERNAL_KEYS = {
    "backend_command",
    "debug",
    "debug_event",
    "diagnostic",
    "diagnostics",
    "event",
    "event_type",
    "internal",
    "internal_event",
    "llm_debug",
    "request",
    "request_id",
    "stage",
    "telemetry",
    "transport",
}
_KERNEL_OUTPUT_INTERNAL_COMMAND_KEYS = {"backend_command", "command"}
_KERNEL_OUTPUT_INTERNAL_MARKERS = (
    "LLM Request Sending",
    "backend command",
    "debug event",
)


def _looks_like_internal_kernel_text(value: Any) -> bool:
    """Return whether text is backend telemetry rather than chat content."""

    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(marker.lower() in lowered for marker in _KERNEL_OUTPUT_INTERNAL_MARKERS)


def _strip_internal_kernel_output(value: Any) -> tuple[Any, list[Any]]:
    """Remove backend-only telemetry from a Kernel output payload for chat display."""

    removed: list[Any] = []
    if isinstance(value, dict):
        visible: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            key_normalized = key_text.lower()
            if (
                key_normalized in _KERNEL_OUTPUT_INTERNAL_KEYS
                or (
                    key_normalized in _KERNEL_OUTPUT_INTERNAL_COMMAND_KEYS
                    and _looks_like_internal_kernel_text(item)
                )
                or _looks_like_internal_kernel_text(item)
            ):
                removed.append({key_text: item})
                continue
            cleaned, child_removed = _strip_internal_kernel_output(item)
            removed.extend(child_removed)
            if cleaned is not None and cleaned != {} and cleaned != []:
                visible[key] = cleaned
        return visible, removed
    if isinstance(value, list):
        visible_list: list[Any] = []
        for item in value:
            if _looks_like_internal_kernel_text(item):
                removed.append(item)
                continue
            cleaned, child_removed = _strip_internal_kernel_output(item)
            removed.extend(child_removed)
            if cleaned is not None and cleaned != {} and cleaned != []:
                visible_list.append(cleaned)
        return visible_list, removed
    if isinstance(value, tuple):
        visible_items: list[Any] = []
        for item in value:
            if _looks_like_internal_kernel_text(item):
                removed.append(item)
                continue
            cleaned, child_removed = _strip_internal_kernel_output(item)
            removed.extend(child_removed)
            if cleaned is not None and cleaned != {} and cleaned != []:
                visible_items.append(cleaned)
        return tuple(visible_items), removed
    if _looks_like_internal_kernel_text(value):
        return None, [value]
    return value, removed


_CSS_PATH = Path(__file__).parent / "app.tcss"

STATUS_STYLE_CLASSES = (
    "status-info",
    "status-success",
    "status-warning",
    "status-error",
)


def apply_status_style(widget: Static, message: str) -> None:
    """Apply a semantic style class to a status widget based on its message."""

    widget.remove_class(*STATUS_STYLE_CLASSES)
    text = message.lower()
    if t("error").lower() in text or "error" in text or "失败" in message:
        widget.add_class("status-error")
    elif (
        "缺少" in message or "未" in message or "请选择" in message or "确认" in message
    ):
        widget.add_class("status-warning")
    elif "成功" in message or "已" in message or "ready" in text or "ok" in text:
        widget.add_class("status-success")
    else:
        widget.add_class("status-info")


@dataclass(frozen=True, slots=True)
class TUIStatus:
    """Test-friendly TUI startup status."""

    title: str
    message: str
    labels: dict[str, str]
    interactive: bool
    llm_ready: bool = False
    llm_provider: str = ""
    current_view: str = "chat"
    view_title: str = ""
    shortcut_hint: str = ""
    status_left: str = ""
    status_center: str = ""
    status_right: str = ""
    focus_target: str = "prompt-input"


@dataclass(frozen=True, slots=True)
class NavMetadata:
    """Test-friendly navigation metadata."""

    key: str
    view_id: str
    label: str
    icon: str


@dataclass(frozen=True, slots=True)
class ShellStatusText:
    """Status bar text for the TUI shell."""

    left: str
    center: str
    right: str
    focus: str
    layout: str


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


class ViewSelectMenuScreen(ModalScreen[str | None]):
    """Submenu that lists all available TUI views."""

    BINDINGS = [Binding("escape", "dismiss", t("menu_back"), show=False)]


    def compose(self) -> ComposeResult:
        with Vertical(id="tui-menu-panel"):
            yield Static(t("menu_select_view"), id="tui-menu-title", classes="shell-title")
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


class MainMenuScreen(ModalScreen[None]):
    """Main menu opened by a single key, matching Textual theme-menu access."""

    BINDINGS = [Binding("escape", "dismiss", t("menu_close"), show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="tui-menu-panel"):
            yield Static(t("menu_title"), id="tui-menu-title", classes="shell-title")
            yield ListView(
                MenuOption(f"▸ {t('menu_select_view')}", "select-view"),
                MenuOption(f"◐ {t('menu_change_theme')}", "change-theme"),
                MenuOption(f"← {t('menu_close')}", "close"),
                id="tui-main-menu-list",
                classes="tui-menu-list",
            )

    def on_mount(self) -> None:
        self.query_one("#tui-main-menu-list", ListView).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, MenuOption):
            return
        if event.item.option_id == "select-view":
            self.app.push_screen(ViewSelectMenuScreen(), self._handle_view_menu_result)
        elif event.item.option_id == "change-theme":
            self.dismiss(None)
            self.app.action_change_theme()
        elif event.item.option_id == "close":
            self.dismiss(None)

    def _handle_view_menu_result(self, result: str | None) -> None:
        if result is None:
            return
        app = cast("SuperMedicineTUI", self.app)
        view_id = result
        self.dismiss(None)
        app.call_after_refresh(lambda: app.action_switch_view(view_id))


class PromptInput(Input):
    """Prompt input that filters terminal controls while preserving normal text."""

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

        key = str(getattr(event, "key", "") or "").lower()
        char = getattr(event, "character", None) or getattr(event, "char", "") or ""
        return key in {"m", "shift+m"} or char in {"m", "M"}

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


class SuperMedicineTUI(App[Any]):
    """Main TUI application with persistent sidebar and swappable content."""

    CSS_PATH = str(_CSS_PATH)
    TITLE = t("app_title")
    AUTO_FOCUS = "#prompt-input"

    BINDINGS = [
        Binding("q", "quit", t("nav_quit")),
        Binding("m", "open_menu", t("menu_open"), show=True),
        Binding("f", "toggle_maximize", t("nav_maximize"), show=True),
        Binding("p", "switch_view('permission')", "权限模式", show=True),
        Binding("question_mark", "show_help", t("help_title"), show=True),
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
            primary="#0078D4",
            secondary="#89B4FA",
            accent="#89B4FA",
            foreground="#CDD6F4",
            background="#11111B",
            surface="#1E1E2E",
            panel="#181825",
            success="#A6E3A1",
            warning="#F9E2AF",
            error="#F38BA8",
            variables={
                "border": "#313244",
                "text-muted": "#A6ADC8",
            },
        )
        self.register_theme(custom_theme)
        self.theme = "supermedicine"
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._config_path = self.project_root / ".supermedicine" / "config.yaml"
        self._current_view = ConfigCenter(self._config_path).get_current_view()
        self._views: dict[str, Any] = {}
        self._task_running = False
        self._status_cache: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="app-body"):
            with Vertical(id="sidebar"):
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
                yield Static(
                    f"{t('layout_shortcuts')}\n{self.shortcut_hint_text()}",
                    id="sidebar-shortcuts",
                    classes="shortcut-hint",
                )
                yield Static(
                    "P 🛡️ 权限模式：查看/切换访问模式与外部授权目录",
                    id="sidebar-permission-entry",
                    classes="shortcut-hint",
                )
            with Vertical(id="main-area"):
                yield Static(t("nav_chat"), id="view-title", classes="view-heading")
                yield Vertical(id="content-pane")
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
        yield Footer()

    def on_mount(self) -> None:
        """Initialize views and show chat by default."""
        from core.tui.screens.chat_view import ChatView
        from core.tui.screens.dashboard import DashboardView
        from core.tui.screens.dialog_screen import DialogView
        from core.tui.screens.experience_screen import ExperienceView
        from core.tui.screens.experiment_screen import ExperimentGuideView
        from core.tui.screens.llm_screen import LLMView
        from core.tui.screens.log_screen import LogReportView
        from core.tui.screens.paper_screen import PaperView
        from core.tui.screens.permission_screen import PermissionView
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
        # Focus the input
        self.query_one("#prompt-input", Input).focus()

    def action_switch_view(self, view_id: str) -> None:
        """Switch the visible content view."""
        if view_id == self._current_view:
            self._refresh_visible_workspace_state(view_id)
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
            self._refresh_visible_workspace_state(view_id)
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

    def _refresh_visible_workspace_state(self, view_id: str) -> None:
        """Reload workspace selectors whenever a mounted page becomes visible."""

        view = self._views.get(view_id)
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
        """Return navigation items and numeric shortcuts."""

        return cls.NAV_ITEMS

    @classmethod
    def view_title_text(cls, view_id: str) -> str:
        """Return the human-readable title for a view."""

        title_map = {item.view_id: item.label for item in cls.nav_items()}
        title_map["permission"] = "权限模式"
        return title_map.get(view_id, view_id)

    @staticmethod
    def shortcut_hint_text() -> str:
        """Return the global shortcut hint shown in sidebar and dry-run output."""

        return t("status_shortcuts_hint")

    def status_text(self, view_id: str | None = None) -> ShellStatusText:
        """Build current status bar text without mutating widgets."""

        current_view = view_id or self._current_view
        task_state = (
            t("status_task_running") if self._task_running else t("status_task_idle")
        )
        layout_state = self._layout_status_label()
        left = f"📁 {self._workspace_count()} {t('status_workspaces')}"
        center = f"🔌 {self._plugin_count()} {t('status_plugins')}  |  {self._llm_status_label()}  |  {self._permission_status_label()}  |  {task_state}"
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
        self.push_screen(MainMenuScreen())

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
            from core.workspace import WorkspaceManager

            manager = WorkspaceManager(self.project_root)
            return len(manager.list_workspaces())
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
            return "0.4.1b0"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle sidebar navigation item selection."""
        if isinstance(event.item, NavItem):
            self.action_switch_view(event.item.view_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        event.stop()
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

    def _process_message(self, message: str, *, turn_id: int | None = None) -> None:
        """Process a user message through the Kernel asynchronously."""
        chat_view = self._views.get("chat")
        if not chat_view:
            return
        # Run in background worker to avoid blocking UI
        self._task_running = True
        self._update_status_bar()
        self.run_worker(
            self._run_kernel_task(message, chat_view, turn_id=turn_id), exclusive=True
        )

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
            if hasattr(chat_view, "add_status_message"):
                chat_view.add_status_message(t("chat_running"))
            assistant_started = False

            def render_progress(event: dict[str, Any]) -> None:
                nonlocal assistant_started
                kind = str(event.get("kind") or "")
                text = str(event.get("message") or event.get("content") or "")
                if kind == "reasoning" and hasattr(chat_view, "add_reasoning_status"):
                    chat_view.add_reasoning_status(
                        text
                        or "模型正在处理请求；当前 Provider 未暴露完整思考内容，仅显示合规处理进度。"
                    )
                elif kind == "status" and hasattr(chat_view, "add_status_message"):
                    chat_view.add_status_message(text)
                elif kind == "assistant_start" and hasattr(
                    chat_view, "begin_assistant_message"
                ):
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
                    return kernel.execute_task(message, progress_callback=progress_callback)

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
            self._task_running = False
            self._update_status_bar()

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
            config = ConfigCenter(
                self.project_root / ".supermedicine" / "config.yaml"
            )
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


def launch_tui(
    *, dry_run: bool = False, project_root: Path | str | None = None
) -> TUIStatus:
    """Launch or describe the Chinese TUI foundation.

    ``dry_run`` returns a status object and prints a minimal Chinese readiness
    message, which keeps command-line tests non-interactive.
    """

    root = Path(project_root) if project_root else Path.cwd()
    if not dry_run:
        from core.log_report import configure_tui_log_storage

        configure_tui_log_storage(root)
    llm_ready, llm_provider = _describe_llm_status(root)
    shell = SuperMedicineTUI(project_root=root)
    valid_views = {item.view_id for item in shell.nav_items()} | {"permission"}
    restored_view = shell._current_view if shell._current_view in valid_views else "chat"
    shell_status = shell.status_text(restored_view)
    view_title = shell.view_title_text(restored_view)
    shortcut_hint = shell.shortcut_hint_text()
    status_message = t("dry_run_status") if dry_run else t("welcome")
    config_load_error = ConfigCenter(root / ".supermedicine" / "config.yaml").diagnostics().get(
        "load_error", ""
    )
    if dry_run:
        llm_text = (
            f"{t('llm_ready')}: {llm_provider}" if llm_ready else t("llm_not_ready")
        )
        status_message = f"{status_message}；{llm_text}"
        if config_load_error:
            status_message = f"{status_message}；配置读取异常，已使用安全默认值：{config_load_error}"
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

    console = Console()
    try:
        app = SuperMedicineTUI(project_root=project_root or Path.cwd())
        app.run(mouse=True)
    except ImportError:
        logger.error(
            "TUI launch failed: stage=import textual_missing project_root=%s",
            project_root or Path.cwd(),
        )
        console.print("Textual 未安装，无法启动交互界面。")
        return TUIStatus(
            title=status.title,
            message="Textual 未安装，无法启动交互界面。",
            labels=status.labels,
            interactive=False,
        )
    logger.info("TUI launch: stage=exit project_root=%s", project_root or Path.cwd())
    return status


def _console_safe_text(value: str, encoding: str | None = None) -> str:
    """Return text that can be encoded by the active console.

    Windows legacy consoles may use GBK or another non-UTF-8 code page that
    cannot encode emoji used in TUI status labels.  Keep Unicode output on
    capable terminals, but replace only unencodable characters for safe
    non-interactive status printing.
    """

    target_encoding = encoding or "utf-8"
    try:
        value.encode(target_encoding)
    except (LookupError, UnicodeEncodeError):
        try:
            return value.encode(target_encoding, errors="replace").decode(
                target_encoding, errors="replace"
            )
        except LookupError:
            return value.encode("utf-8", errors="replace").decode(
                "utf-8", errors="replace"
            )
    return value


def _describe_llm_status(project_root: Path | str) -> tuple[bool, str]:
    try:
        root = Path(project_root)
        manager = LLMConfigManager(
            ConfigCenter(root / ".supermedicine" / "config.yaml")
        )
        current = manager.get_current_provider(redacted=True)
        provider = str(current.get("provider") or "")
        if not provider:
            return False, ""
        return manager.validate_provider(provider) is None, provider
    except Exception as exc:
        logger.warning(
            "TUI LLM status diagnostic failed: stage=config project_root=%s error=%s",
            project_root,
            exc,
        )
        return False, ""


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
