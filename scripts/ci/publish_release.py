#!/usr/bin/env python3
"""Create or safely refresh a verified GitHub Release."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _gh(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def publish(
    tag: str,
    title: str,
    notes: Path,
    archive: Path,
    checksum: Path,
    *,
    dry_run: bool,
) -> None:
    for path in (notes, archive, checksum):
        if not path.is_file():
            raise ValueError(f"required release input does not exist: {path}")
    if dry_run:
        print(f"dry-run: would publish {tag} with {archive.name} and {checksum.name}")
        return
    existing = _gh("release", "view", tag, check=False).returncode == 0
    if existing:
        _gh(
            "release",
            "edit",
            tag,
            "--draft",
            "--title",
            title,
            "--notes-file",
            str(notes),
        )
    else:
        _gh(
            "release",
            "create",
            tag,
            "--draft",
            "--title",
            title,
            "--notes-file",
            str(notes),
        )
    _gh("release", "upload", tag, str(archive), str(checksum), "--clobber")
    view = json.loads(_gh("release", "view", tag, "--json", "isDraft,assets").stdout)
    asset_names = {asset["name"] for asset in view.get("assets", [])}
    if not view.get("isDraft") or {archive.name, checksum.name} - asset_names:
        raise ValueError("draft release asset verification failed")
    _gh("release", "edit", tag, "--draft=false")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--notes", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--checksum", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        publish(
            args.tag,
            args.title,
            args.notes,
            args.archive,
            args.checksum,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
