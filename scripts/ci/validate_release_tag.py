#!/usr/bin/env python3
"""Validate release tag, commit identity, and no-overwrite policy."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def package_version() -> str:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _run(*command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def validate(tag: str, sha: str, *, dry_run: bool, allow_non_tag: bool) -> dict[str, str]:
    version = package_version()
    expected_tag = f"v{version}"
    effective_tag = expected_tag if allow_non_tag and dry_run else tag
    if effective_tag != expected_tag:
        raise ValueError(f"release tag {effective_tag!r} must equal {expected_tag!r}")

    if not (allow_non_tag and dry_run):
        tag_commit = _run("git", "rev-list", "-n", "1", effective_tag).stdout.strip()
        if tag_commit != sha:
            raise ValueError(
                f"tag commit {tag_commit!r} does not match build commit {sha!r}"
            )

    if not dry_run:
        existing = _run("gh", "release", "view", effective_tag, check=False)
        if existing.returncode == 0:
            raise ValueError(
                f"release {effective_tag!r} already exists; refusing to overwrite"
            )

    return {
        "release_label": expected_tag,
        "release_title": f"SuperMedicine {version}",
        "archive_name": f"SuperMedicine {expected_tag}.zip",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-non-tag", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate(
            args.tag,
            args.sha,
            dry_run=args.dry_run,
            allow_non_tag=args.allow_non_tag,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for key, value in result.items():
        print(f"{key}={value}")
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as stream:
            for key, value in result.items():
                stream.write(f"{key}={value}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
