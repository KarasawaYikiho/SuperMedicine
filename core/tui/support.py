"""Shared Textual primitives, state, resources, and compatibility helpers."""
# ruff: noqa: E402,F401,F811

from __future__ import annotations

# --- migrated from types.py ---
from dataclasses import dataclass  # noqa: E402


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
    runtime_name: str = "@opentui/core"
    runtime_version: str = "0.4.1"


@dataclass(frozen=True, slots=True)
class NavMetadata:
    """Test-friendly navigation metadata."""

    key: str
    view_id: str
    label: str
    icon: str


@dataclass(frozen=True, slots=True)
class OpenTUINavigationRoute:
    """Shared metadata for OpenTUI route-shell navigation."""

    key: str
    view_id: str
    label: str
    icon: str
    placeholder: str
    sections: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpenTUINavigationState:
    """Test-friendly snapshot of OpenTUI navigation state."""

    current_view: str
    stack: tuple[str, ...]
    focus_target: str
    menu_open: bool = False


@dataclass(frozen=True, slots=True)
class ShellStatusText:
    """Status bar text for the TUI shell."""

    left: str
    center: str
    right: str
    focus: str
    layout: str


@dataclass(frozen=True, slots=True)
class DynamicRefreshSurface:
    """Code-backed boundary for targeted TUI refresh behavior."""

    view_id: str
    refresh_hook: str
    manual_control: str
    policy: str


# --- migrated from resources.py ---
import logging  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

logger = logging.getLogger(__name__)


def _bundle_root() -> Path | None:
    """Return the PyInstaller bundle root when running in frozen mode."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return None


def _source_root() -> Path:
    """Return the project source root (three levels above this file).

    This resolves to the repository root in development mode:
    ``core/tui/resources.py`` → ``<project_root>``
    """
    return Path(__file__).resolve().parents[2]


def resolve_resource(relative: str | Path) -> Path:
    """Resolve an absolute path for a bundled or source-tree resource.

    Resolution order:
    1. If running in PyInstaller frozen mode, look under ``sys._MEIPASS``.
    2. Otherwise resolve relative to the project source root.

    Parameters
    ----------
    relative:
        Path relative to the project root, e.g. ``"core/tui/app.tcss"``.

    Returns
    -------
    Path
        Absolute path to the resource.  The path may not exist if the
        resource was not bundled — callers should handle that case.
    """
    relative = Path(relative)

    bundle = _bundle_root()
    if bundle is not None:
        bundled = bundle / relative
        if bundled.exists():
            return bundled
        logger.debug(
            "Bundled resource not found: %s (looked in %s)", relative, bundled
        )

    return _source_root() / relative


def resolve_tcss(filename: str = "app.tcss") -> Path:
    """Resolve a TUI stylesheet file from ``core/tui/``.

    Parameters
    ----------
    filename:
        Stylesheet filename, defaults to ``"app.tcss"``.

    Returns
    -------
    Path
        Absolute path to the ``.tcss`` file.
    """
    return resolve_resource(Path("core") / "tui" / filename)


def resolve_asset(filename: str) -> Path:
    """Resolve a file from the ``assets/`` directory.

    Parameters
    ----------
    filename:
        Asset filename, e.g. ``"logo.svg"``.

    Returns
    -------
    Path
        Absolute path to the asset file.
    """
    return resolve_resource(Path("assets") / filename)


def is_frozen() -> bool:
    """Return ``True`` when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


__all__ = [
    "is_frozen",
    "resolve_asset",
    "resolve_resource",
    "resolve_tcss",
]


# --- migrated from dialog_history.py ---
from core.dialog_history import (  # noqa: E402
    DIALOG_HISTORY_FILENAME,
    RAW_CONVERSATION_FIELDS,
    DialogHistoryEvent,
    DialogHistoryPrivacyError,
    DialogHistoryStore,
)

__all__ = [
    "DIALOG_HISTORY_FILENAME",
    "RAW_CONVERSATION_FIELDS",
    "DialogHistoryEvent",
    "DialogHistoryPrivacyError",
    "DialogHistoryStore",
]


# --- migrated from kernel_output.py ---
import re  # noqa: E402
from typing import Any  # noqa: E402

from core.redaction import redact_sensitive  # noqa: E402


_DISPLAY_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*([:=])\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),
)


def _redact_display_secrets(value: str) -> str:
    """Redact common secret shapes before handing text to chat rendering."""

    return str(redact_sensitive(value)).replace("[REDACTED]", "[已隐藏]")


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


# --- migrated from permissions.py ---
from dataclasses import dataclass, field  # noqa: E402
from typing import Any, Protocol  # noqa: E402


TUI_TOOL_AGENT_ID = "delta"
TUI_TOOL_ACTION = "tui.tool_action"
HIGH_RISK_TOOLS = frozenset({"bash", "write", "edit"})


class _PermissionDecision(Protocol):
    value: str


class PermissionChecker(Protocol):
    def check(
        self,
        agent_id: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> _PermissionDecision: ...


@dataclass(frozen=True, slots=True)
class TUIToolActionRequest:
    """Prepared, non-executing description of a TUI tool action."""

    tool: str
    resource: str
    agent_id: str = TUI_TOOL_AGENT_ID
    action: str = TUI_TOOL_ACTION
    confirmed: bool = False
    permission: str = "denied"
    allowed: bool = False
    context: dict[str, Any] = field(default_factory=dict)


def prepare_tool_action(
    permission_engine: PermissionChecker,
    *,
    tool: str,
    resource: str,
    confirmed: bool,
    agent_id: str = TUI_TOOL_AGENT_ID,
    context: dict[str, Any] | None = None,
) -> TUIToolActionRequest:
    """Prepare a high-risk TUI tool action without executing it.

    ``bash``, ``write`` and ``edit`` are treated as high-risk foundations for
    later screens.  They require explicit confirmation first, then a successful
    ``PermissionEngine.check`` decision.  This function only returns a request
    object and never invokes the underlying tool.
    """

    request_context = dict(context or {})
    request_context.update(
        {
            "tool": tool,
            "requires_confirmation": tool in HIGH_RISK_TOOLS,
            "tui_boundary": True,
            "sandbox_required": True,
            "audit_required": True,
        }
    )

    if tool in HIGH_RISK_TOOLS and not confirmed:
        return TUIToolActionRequest(
            tool=tool,
            resource=resource,
            agent_id=agent_id,
            confirmed=False,
            context=request_context,
        )

    decision = permission_engine.check(
        agent_id,
        TUI_TOOL_ACTION,
        resource,
        context=request_context,
    )
    allowed = decision.value == "allowed"
    return TUIToolActionRequest(
        tool=tool,
        resource=resource,
        agent_id=agent_id,
        confirmed=confirmed,
        permission=decision.value,
        allowed=allowed,
        context=request_context,
    )


# --- migrated from nav_widgets.py ---
from typing import cast  # noqa: E402

from textual import events  # noqa: E402
from textual.app import ComposeResult  # noqa: E402
from textual.widgets import ListItem, Static  # noqa: E402


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


# --- migrated from prompt_input.py ---
import re  # noqa: E402
from typing import TYPE_CHECKING, cast  # noqa: E402

from textual import events  # noqa: E402
from textual.widgets import Input  # noqa: E402

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


# --- migrated from state.py ---
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

from core.services import WorkspaceService  # noqa: E402


@dataclass(frozen=True, slots=True)
class TUIState:
    """Small state facade scoped to a single project root."""

    project_root: Path | str | None = None

    @property
    def workspace_service(self) -> WorkspaceService:
        return WorkspaceService(self.project_root)

    def save_recent_workspace(
        self,
        workspace_id: str,
        selected_workspace_id: str | None = None,
    ) -> Path:
        """Save TUI recent selection in the source workspace session state."""

        return Path(
            self.workspace_service.require_data(
                self.workspace_service.save_selection(
                    workspace_id, selected_workspace_id
                )
            )
        )

    def load_recent_workspace(self, workspace_id: str) -> str | None:
        """Load TUI recent selection only from the requested workspace state."""

        return self.workspace_service.require_data(
            self.workspace_service.load_selection(workspace_id)
        )

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List initialized workspaces from the shared persistent workspace store."""

        return self.workspace_service.require_data(self.workspace_service.list())

    def create_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Create a workspace through the shared persistent workspace store."""

        return self.workspace_service.require_data(
            self.workspace_service.create(workspace_id)
        )

    def select_workspace(
        self,
        workspace_id: str,
        *,
        state_workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist a TUI workspace selection without changing CLI workspace behavior."""

        info = self.workspace_service.require_data(
            self.workspace_service.show(workspace_id)
        )
        self.save_recent_workspace(state_workspace_id or info["id"], info["id"])
        return info

    def workspace_payloads(self) -> list[dict[str, Any]]:
        """Return display-ready workspace records from the shared persistent list."""

        return [
            self._workspace_payload(info, selected=False) for info in self.list_workspaces()
        ]

    @staticmethod
    def _workspace_payload(
        info: dict[str, Any], *, selected: bool
    ) -> dict[str, Any]:
        return {
            **info,
            "label": f"工作区：{info['id']}",
            "selected": selected,
        }


def save_recent_workspace(
    workspace_id: str,
    selected_workspace_id: str | None = None,
    project_root: Path | str | None = None,
) -> Path:
    """Convenience wrapper for workspace-local recent workspace state."""

    return TUIState(project_root).save_recent_workspace(
        workspace_id, selected_workspace_id
    )


def load_recent_workspace(
    workspace_id: str,
    project_root: Path | str | None = None,
) -> str | None:
    """Convenience wrapper that does not affect CLI workspace behavior."""

    return TUIState(project_root).load_recent_workspace(workspace_id)


def list_workspaces(
    project_root: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Convenience wrapper listing TUI-visible workspaces from persistent state."""

    return TUIState(project_root).list_workspaces()


# --- migrated from status_helpers.py ---
import logging  # noqa: E402
from pathlib import Path  # noqa: E402

from textual.widgets import Static  # noqa: E402

from core.services import LLMService  # noqa: E402
from core.tui.i18n import t  # noqa: E402


logger = logging.getLogger(__name__)


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
        service = LLMService(Path(project_root), restore_on_startup=True)
        current_result = service.show_provider()
        current = current_result.data or {} if current_result.ok else {}
        provider = str(current.get("provider") or "")
        if not provider:
            return False, ""
        return service.validate_provider(provider).ok, provider
    except Exception as exc:
        logger.warning(
            "TUI LLM status diagnostic failed: stage=config project_root=%s error=%s",
            project_root,
            exc,
        )
        return False, ""


# --- migrated from stream_capture.py ---
import contextlib  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402


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
        from core.log_report_handler import append_tui_stream_output

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


# --- migrated from menu_screens.py ---
from typing import cast  # noqa: E402

from textual.app import ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Vertical  # noqa: E402
from textual.screen import ModalScreen  # noqa: E402
from textual.widgets import ListView, Static  # noqa: E402

from core.tui.i18n import t  # noqa: E402
from core.tui.support import MenuOption  # noqa: E402


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
                MenuOption(f"🧬 {t('nav_self_evolution')}", "view", "self-evolution"),
                MenuOption(f"🩺 {t('nav_diagnose')}", "view", "diagnose"),
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
                MenuOption(f"🛡 {t('menu_permission_settings')}", "permission-settings"),
                MenuOption(f"◐ {t('menu_change_theme')}", "change-theme"),
                MenuOption(f"□ {t('menu_toggle_maximize')}", "toggle-maximize"),
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
        elif event.item.option_id == "permission-settings":
            self.dismiss(None)
            app.action_switch_view("permission")
        elif event.item.option_id == "change-theme":
            self.dismiss(None)
            self.app.action_change_theme()
        elif event.item.option_id == "toggle-maximize":
            self.dismiss(None)
            app.action_toggle_maximize()
        elif event.item.option_id == "show-help":
            self.dismiss(None)
            app.action_show_help()
        elif event.item.option_id == "close":
            self.dismiss(None)

    def _handle_view_menu_result(self, result: str | None) -> None:
        if result is None:
            return
        self.dismiss(result)


# Public surface of the consolidated compatibility module.  The explicit list
# also lets static type checkers understand the legacy ``*.pyi`` facades.
__all__ = [
    "DIALOG_HISTORY_FILENAME",
    "RAW_CONVERSATION_FIELDS",
    "DialogHistoryEvent",
    "DialogHistoryPrivacyError",
    "DialogHistoryStore",
    "DynamicRefreshSurface",
    "MainMenuScreen",
    "MenuButton",
    "NavItem",
    "NavMetadata",
    "OpenTUINavigationRoute",
    "OpenTUINavigationState",
    "PermissionChecker",
    "PromptInput",
    "STATUS_STYLE_CLASSES",
    "ShellStatusText",
    "TUIState",
    "TUIStatus",
    "TUIToolActionRequest",
    "TUI_TOOL_ACTION",
    "apply_status_style",
    "is_frozen",
    "load_recent_workspace",
    "prepare_tool_action",
    "resolve_asset",
    "resolve_resource",
    "resolve_tcss",
    "save_recent_workspace",
    "_KERNEL_OUTPUT_ASSISTANT_KEYS",
    "_capture_current_thread_tui_streams",
    "_console_safe_text",
    "_describe_llm_status",
    "_redact_display_secrets",
    "_strip_internal_kernel_output",
]
