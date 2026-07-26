#!/usr/bin/env python3
"""Compatibility entrypoint for source archives and frozen application builds."""

from __future__ import annotations

from cli.facade import CLI, main, required_runtime_snapshot

__all__ = ["CLI", "main", "required_runtime_snapshot"]


if __name__ == "__main__":
    main()
