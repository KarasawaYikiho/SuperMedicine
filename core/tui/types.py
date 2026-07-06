"""TUI dataclass types extracted for reuse and testability."""

from __future__ import annotations

from dataclasses import dataclass


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
