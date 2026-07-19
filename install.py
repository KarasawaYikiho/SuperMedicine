"""Canonical lowercase installer entrypoint for source and release archives."""

from __future__ import annotations

from install_entry import main


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
