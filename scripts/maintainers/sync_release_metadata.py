#!/usr/bin/env python3
"""Check or update the small set of release metadata mirrors."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
START = "<!-- BEGIN GENERATED: release-metadata -->"
END = "<!-- END GENERATED: release-metadata -->"
JSON_VERSION = re.compile(r'^(\s*"version"\s*:\s*)"[^"]*"', re.MULTILINE)
PEP_440_BETA = re.compile(r"^(\d+\.\d+\.\d+)b0$")


def project_version() -> str:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def release_versions(version: str) -> tuple[str, str]:
    match = PEP_440_BETA.fullmatch(version)
    if match is None:
        raise ValueError("project version must use the supported X.Y.Zb0 form")
    api_version = match.group(1)
    return f"Beta{api_version}", api_version


def _replace_block(text: str, body: str) -> str:
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < start:
        raise ValueError("missing or invalid generated release metadata markers")
    end += len(END)
    return text[:start] + f"{START}\n{body}\n{END}" + text[end:]


def _replace_json_version(text: str, version: str) -> str:
    """Update only the top-level version field and preserve reviewed formatting."""
    updated, count = JSON_VERSION.subn(rf'\g<1>"{version}"', text, count=1)
    if count != 1 or json.loads(updated).get("version") != version:
        raise ValueError("missing or invalid top-level JSON version field")
    return updated


def _replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"release metadata marker not found: {pattern}")
    return updated


def desired_files() -> dict[Path, str]:
    version = project_version()
    public_version, api_version = release_versions(version)
    desired: dict[Path, str] = {}
    readmes = {
        REPOSITORY_ROOT / "README.md": f"Current release: **{version}**",
        REPOSITORY_ROOT / "README.zh-CN.md": f"当前版本：**{version}**",
    }
    for path, body in readmes.items():
        updated = _replace_block(path.read_text(encoding="utf-8"), body)
        label = (
            f"Release series: **{public_version}**"
            if path.name == "README.md"
            else f"发布系列：**{public_version}**"
        )
        pattern = (
            r"^Release series: \*\*Beta[^*]+\*\*$"
            if path.name == "README.md"
            else r"^发布系列：\*\*Beta[^*]+\*\*$"
        )
        desired[path] = _replace_once(
            updated,
            pattern,
            label,
        )

    for relative in ("install.json", "adapters/opencode/plugin.json"):
        path = REPOSITORY_ROOT / relative
        current = path.read_text(encoding="utf-8")
        updated = _replace_json_version(current, version)
        if relative == "install.json":
            updated = re.sub(
                r"the Beta\d+\.\d+\.\d+ fixed layout",
                f"the {public_version} fixed layout",
                updated,
                count=1,
            )
        desired[path] = updated

    replacements = {
        "core/__init__.py": (
            (r'^__version__ = "[^"]+"$', f'__version__ = "{version}"'),
            (r'^PUBLIC_VERSION = "[^"]+"$', f'PUBLIC_VERSION = "{public_version}"'),
            (r'^API_VERSION = "[^"]+"$', f'API_VERSION = "{api_version}"'),
        ),
        "CHANGELOG.md": (
            (
                r"^(is not PEP 440-compatible\. Current public/release label: )"
                r"\*\*Beta[^*]+\*\*(\. Current)$",
                rf"\g<1>**{public_version}**\g<2>",
            ),
            (
                r"^(Python package fallback version: )\*\*[^*]+\*\*\.$",
                rf"\g<1>**{version}**.",
            ),
        ),
        "SECURITY.md": (
            (
                r"^This policy applies to \*\*Beta[^*]+\*\*\.$",
                f"This policy applies to **{public_version}**.",
            ),
        ),
        "docs/guides/INSTALL.md": (
            (
                r"^SuperMedicine \*\*Beta[^*]+\*\*\.$",
                f"SuperMedicine **{public_version}**.",
            ),
        ),
    }
    for relative, rules in replacements.items():
        path = REPOSITORY_ROOT / relative
        updated = path.read_text(encoding="utf-8")
        for pattern, replacement in rules:
            updated = _replace_once(updated, pattern, replacement)
        desired[path] = updated
    return desired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    stale: list[str] = []
    for path, desired in desired_files().items():
        current = path.read_text(encoding="utf-8")
        if current == desired:
            continue
        stale.append(path.relative_to(REPOSITORY_ROOT).as_posix())
        if args.write:
            path.write_text(desired, encoding="utf-8", newline="")

    if stale and args.check:
        for relative in stale:
            print(f"stale release metadata: {relative}")
        return 1
    if args.write:
        for relative in stale:
            print(f"updated release metadata: {relative}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
