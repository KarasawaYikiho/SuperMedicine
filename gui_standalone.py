#!/usr/bin/env python3
"""PyInstaller-compatible alias for the standard desktop package entrypoint."""

from __future__ import annotations

from desktop.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
