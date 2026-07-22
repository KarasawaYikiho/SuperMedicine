"""Explicit import aliases for the retired Python TUI surface.

The production terminal renderer is OpenTUI.  These declarations preserve the
historical module paths promised to integrations without reintroducing the
retired Textual implementation.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from types import ModuleType
from typing import Iterator, TextIO

OPENTUI_REPLACEMENT = "core.tui.app.launch_tui"


class _OpenTUICompatibilityDeclaration:
    """Importable declaration pointing callers at the OpenTUI entry point."""

    runtime = "@opentui/core"
    replacement = OPENTUI_REPLACEMENT

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeError(
            f"{type(self).__name__} was retired; use {self.replacement} instead"
        )


class ChatView(_OpenTUICompatibilityDeclaration):
    """Compatibility declaration for the OpenTUI chat page."""


class WorkspaceView(_OpenTUICompatibilityDeclaration):
    """Compatibility declaration for the OpenTUI workspace page."""


class PaperView(_OpenTUICompatibilityDeclaration):
    """Compatibility declaration for the OpenTUI paper page."""


class PermissionView(_OpenTUICompatibilityDeclaration):
    """Compatibility declaration for the OpenTUI permission page."""


class PromptInput(_OpenTUICompatibilityDeclaration):
    """Compatibility declaration for OpenTUI-owned prompt input."""


def _retired_recent_workspace(*_args: object, **_kwargs: object) -> None:
    """Reject the retired TUI-local selection store with migration guidance."""

    raise RuntimeError(
        "TUI-local recent workspace state was retired; use WorkspaceService instead"
    )


@contextmanager
def _capture_current_thread_tui_streams() -> Iterator[tuple[TextIO, TextIO]]:
    """Preserve the former context-manager shape without taking terminal ownership."""

    yield sys.stdout, sys.stderr


_ALIASES: dict[str, dict[str, object]] = {
    "core.tui.prompt_input": {"PromptInput": PromptInput},
    "core.tui.state": {"load_recent_workspace": _retired_recent_workspace},
    "core.tui.stream_capture": {
        "_capture_current_thread_tui_streams": _capture_current_thread_tui_streams
    },
    "core.tui.screens.chat_view": {"ChatView": ChatView},
    "core.tui.screens.workspace_screen": {"WorkspaceView": WorkspaceView},
    "core.tui.screens.paper_screen": {"PaperView": PaperView},
    "core.tui.screens.permission_screen": {"PermissionView": PermissionView},
}


def install_legacy_tui_aliases(*, screens: bool = False) -> None:
    """Register the reviewed historical imports as lightweight alias modules."""

    prefix = "core.tui.screens." if screens else "core.tui."
    for module_name, exports in _ALIASES.items():
        is_screen = module_name.startswith("core.tui.screens.")
        if is_screen != screens or not module_name.startswith(prefix):
            continue
        module = sys.modules.get(module_name)
        if module is None:
            module = ModuleType(
                module_name,
                f"Compatibility alias; production replacement: {OPENTUI_REPLACEMENT}.",
            )
            module.__dict__.update(exports)
            module.__dict__["__all__"] = tuple(exports)
            module.__dict__["OPENTUI_REPLACEMENT"] = OPENTUI_REPLACEMENT
            sys.modules[module_name] = module
        parent_name, child_name = module_name.rsplit(".", maxsplit=1)
        parent = sys.modules.get(parent_name)
        if parent is not None:
            setattr(parent, child_name, module)


__all__ = ["OPENTUI_REPLACEMENT", "install_legacy_tui_aliases"]
