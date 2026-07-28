#!/usr/bin/env python3
"""Generate concise release notes from Git history."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def release_notes(tag: str) -> str:
    tags = [
        item
        for item in _git("tag", "--list", "Beta*", "--sort=-v:refname").splitlines()
        if item and item != tag
    ]
    revision = f"{tags[0]}..{tag}" if tags else tag
    log = _git("log", "--no-merges", "--pretty=format:- %s (%h)", revision)
    if not log:
        log = "No commit summary was available for this release."
    return f"## Changes\n\n{log}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.write_text(release_notes(args.tag), encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
