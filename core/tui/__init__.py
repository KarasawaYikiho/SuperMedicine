"""OpenTUI integration for SuperMedicine."""

from __future__ import annotations

from typing import Any

from core.tui.compat import install_legacy_tui_aliases

install_legacy_tui_aliases()

__all__ = ["LABELS", "TUIStatus", "launch_tui", "main", "t"]


def __getattr__(name: str) -> Any:
    if name in {"TUIStatus", "launch_tui", "main"}:
        from core.tui import app

        return getattr(app, name)
    if name in {"LABELS", "t"}:
        from core.tui import i18n

        return getattr(i18n, name)
    raise AttributeError(name)
