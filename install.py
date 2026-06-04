#!/usr/bin/env python3
"""Lowercase compatibility entrypoint for the SuperMedicine installer.

This wrapper keeps the user-facing ``python install.py`` command available on
case-sensitive platforms while preserving the existing ``python Install.py``
entrypoint for older scripts and release automation.
"""
from __future__ import annotations

from Install import main


if __name__ == "__main__":
    main()
