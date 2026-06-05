#!/usr/bin/env python3
"""Compatibility wrapper for the stable lowercase installer entrypoint."""

from __future__ import annotations

from installer import entrypoint as _entrypoint

globals().update(
    {
        name: getattr(_entrypoint, name)
        for name in dir(_entrypoint)
        if not (name.startswith("__") and name.endswith("__"))
    }
)

__all__ = [
    name for name in globals() if not (name.startswith("__") and name.endswith("__"))
]

if __name__ == "__main__":
    try:
        _entrypoint.main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
