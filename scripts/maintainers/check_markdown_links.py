#!/usr/bin/env python3
"""Compatibility entrypoint for the repository documentation checker."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.maintainers.check_docs import check_docs


def check_markdown_links(root: str | Path) -> list[str]:
    """Retain the old callable while delegating repository checks."""

    del root
    return check_docs()


def main(argv: list[str] | None = None) -> int:
    del argv
    errors = check_docs()
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
