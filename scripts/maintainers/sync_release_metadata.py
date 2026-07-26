#!/usr/bin/env python3
"""Check or update the small set of release metadata mirrors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
START = "<!-- BEGIN GENERATED: release-metadata -->"
END = "<!-- END GENERATED: release-metadata -->"


def project_version() -> str:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _replace_block(text: str, body: str) -> str:
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < start:
        raise ValueError("missing or invalid generated release metadata markers")
    end += len(END)
    return text[:start] + f"{START}\n{body}\n{END}" + text[end:]


def desired_files() -> dict[Path, str]:
    version = project_version()
    desired: dict[Path, str] = {}
    readmes = {
        REPOSITORY_ROOT / "README.md": f"Current release: **{version}**",
        REPOSITORY_ROOT / "README.zh-CN.md": f"当前版本：**{version}**",
    }
    for path, body in readmes.items():
        desired[path] = _replace_block(path.read_text(encoding="utf-8"), body)

    for relative in ("install.json", "adapters/opencode/plugin.json"):
        path = REPOSITORY_ROOT / relative
        current = path.read_text(encoding="utf-8")
        data = json.loads(current)
        if data.get("version") == version:
            desired[path] = current
            continue
        data["version"] = version
        desired[path] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
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
