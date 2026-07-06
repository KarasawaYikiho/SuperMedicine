"""Canonical lowercase installer entrypoint for source and release archives."""

from __future__ import annotations

from installer import entrypoint as _entrypoint


if __name__ == "__main__":
    try:
        _entrypoint.main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
