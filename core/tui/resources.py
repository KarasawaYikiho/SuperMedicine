"""Resource path resolution for frozen (PyInstaller) and development modes.

When running as a PyInstaller-frozen executable, data files live under
``sys._MEIPASS``.  In development mode they sit next to the source tree.
This module centralises the lookup so every caller gets the right path
regardless of runtime context.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

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
