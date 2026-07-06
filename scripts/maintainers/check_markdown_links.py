#!/usr/bin/env python3
"""Check relative Markdown links under a documentation root."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def _is_external_or_anchor(target: str) -> bool:
    lower = target.lower()
    return (
        target.startswith("#")
        or "://" in target
        or lower.startswith(("mailto:", "tel:"))
    )


def _strip_fragment(target: str) -> str:
    return target.split("#", maxsplit=1)[0]


def check_markdown_links(root: str | Path) -> list[str]:
    """Return missing relative Markdown links below root."""

    root_path = Path(root).resolve()
    errors: list[str] = []

    for markdown_file in sorted(root_path.rglob("*.md")):
        text = markdown_file.read_text(encoding="utf-8")
        relative_file = markdown_file.relative_to(root_path).as_posix()
        for match in MARKDOWN_LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            target = _strip_fragment(raw_target)
            if not target or _is_external_or_anchor(raw_target):
                continue
            if not target.lower().endswith(".md"):
                continue
            linked_path = (markdown_file.parent / target).resolve()
            try:
                linked_path.relative_to(root_path)
            except ValueError:
                # Parent-directory docs links are legitimate in this repository.
                pass
            if not linked_path.is_file():
                errors.append(
                    f"{relative_file}: missing relative Markdown link: {raw_target}"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default="docs", help="Documentation root")
    args = parser.parse_args(argv)

    errors = check_markdown_links(args.root)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

