#!/usr/bin/env python3
"""Compatibility launcher for source and release archives."""

from __future__ import annotations

from desktop.__main__ import main

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
