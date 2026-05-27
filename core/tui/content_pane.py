"""Swappable content pane for the SuperMedicine TUI."""

from __future__ import annotations

from textual.containers import Vertical


class ContentPane(Vertical):
    """Container that holds swappable view widgets.

    Views are mounted as children and toggled via ``display = True/False``.
    This class exists as a semantic wrapper — the actual show/hide logic
    lives in the parent ``SuperMedicineTUI`` application.
    """

    DEFAULT_CSS = """
    ContentPane {
        height: 1fr;
        width: 100%;
        overflow-y: auto;
        padding: 0 1;
    }
    """
