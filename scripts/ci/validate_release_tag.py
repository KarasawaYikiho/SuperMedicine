#!/usr/bin/env python3
"""Validate release version and source commit identity."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

from scripts.ci.release_version import release_names  # noqa: E402


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
    expected_tag, release_title, archive_name = release_names(version)
    effective_tag = expected_tag if allow_non_tag else tag
    if effective_tag != expected_tag:
        raise ValueError(f"release tag {effective_tag!r} must equal {expected_tag!r}")

    source_commit = _run("git", "rev-parse", "HEAD").stdout.strip()
    if source_commit != sha:
        raise ValueError(
            f"checked-out commit {source_commit!r} does not match source commit {sha!r}"
        )

    if not allow_non_tag:
        tag_commit = _run("git", "rev-list", "-n", "1", effective_tag).stdout.strip()
        if tag_commit != sha:
            raise ValueError(
                f"tag commit {tag_commit!r} does not match build commit {sha!r}"
            )

    return {
        "release_label": expected_tag,
        "release_title": release_title,
        "archive_name": archive_name,
        "source_sha": sha,
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
