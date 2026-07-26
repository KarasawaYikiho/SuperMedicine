#!/usr/bin/env python3
"""Validate the repository's formal Markdown documentation contract."""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPOSITORY_ROOT / "docs" / "manifest.yaml"
LINK_RE = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
GENERATED_METADATA_START = "<!-- BEGIN GENERATED: release-metadata -->"
GENERATED_METADATA_END = "<!-- END GENERATED: release-metadata -->"
README_ANCHORS = ("product", "safety", "install", "quickstart", "documentation", "license")


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def _git_paths() -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = [line.strip().replace("\\", "/") for line in result.stdout.splitlines()]
    return {path.casefold(): path for path in paths}


def _slug(heading: str) -> str:
    text = re.sub(r"<[^>]+>", "", heading).strip().lower()
    text = re.sub(r"[^\w\-\s\u4e00-\u9fff]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-")


def _target_path(markdown: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>")
    lower = target.lower()
    if (
        not target
        or target.startswith("#")
        or "://" in target
        or lower.startswith(("mailto:", "tel:", "data:"))
    ):
        return None
    target = unquote(target.split("#", maxsplit=1)[0])
    if not target:
        return None
    return (markdown.parent / target).resolve()


def _formal_paths(manifest: dict) -> list[str]:
    return [str(record["path"]).replace("\\", "/") for record in manifest["documents"]]


def check_docs() -> list[str]:
    errors: list[str] = []
    manifest = _manifest()
    formal_paths = _formal_paths(manifest)
    git_paths = _git_paths()

    if len(formal_paths) != len(set(formal_paths)):
        errors.append("docs/manifest.yaml: duplicate document path")

    expected_docs = {
        path.replace("\\", "/")
        for path in git_paths.values()
        if path.endswith(".md")
        and (REPOSITORY_ROOT / path).is_file()
        and (
            path.startswith("docs/")
            or "/" not in path
        )
    }
    missing_from_manifest = sorted(expected_docs - set(formal_paths))
    if missing_from_manifest:
        errors.append(
            "docs/manifest.yaml: unindexed formal documents: "
            + ", ".join(missing_from_manifest)
        )

    records = {str(record["path"]).replace("\\", "/"): record for record in manifest["documents"]}
    for relative in formal_paths:
        path = REPOSITORY_ROOT / relative
        if not path.is_file():
            errors.append(f"{relative}: manifest path does not exist")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{relative}: invalid UTF-8 at byte {exc.start}")
            continue

        if records[relative].get("role") not in {"release-history", "immutable-history"}:
            anchors = [_slug(value) for value in HEADING_RE.findall(text)]
            duplicates = sorted(
                anchor
                for anchor, count in Counter(anchors).items()
                if anchor and count > 1
            )
            if duplicates:
                errors.append(
                    f"{relative}: duplicate heading anchors: {', '.join(duplicates)}"
                )

        for match in LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            normalized = raw_target.replace("\\", "/")
            if (
                normalized.startswith(("Temp/", "docs/archive/"))
                or re.match(r"^[A-Za-z]:[/\\]", raw_target)
                or normalized.startswith("/")
            ):
                errors.append(f"{relative}: forbidden local/archive link: {raw_target}")
                continue
            linked = _target_path(path, raw_target)
            if linked is None:
                continue
            try:
                linked_relative = linked.relative_to(REPOSITORY_ROOT).as_posix()
            except ValueError:
                errors.append(f"{relative}: link escapes repository: {raw_target}")
                continue
            canonical = git_paths.get(linked_relative.casefold())
            if canonical is None and not linked.is_file():
                errors.append(f"{relative}: missing relative link: {raw_target}")
            elif canonical is not None and canonical != linked_relative:
                errors.append(
                    f"{relative}: link path case mismatch: {raw_target} -> {canonical}"
                )

    for readme_name in ("README.md", "README.zh-CN.md"):
        text = (REPOSITORY_ROOT / readme_name).read_text(encoding="utf-8")
        for anchor in README_ANCHORS:
            if f'<a id="{anchor}"></a>' not in text:
                errors.append(f"{readme_name}: missing structure anchor: {anchor}")
        if text.count(GENERATED_METADATA_START) != 1 or text.count(
            GENERATED_METADATA_END
        ) != 1:
            errors.append(f"{readme_name}: invalid generated release metadata block")

    architecture = (
        REPOSITORY_ROOT / "docs" / "architecture" / "ARCHITECTURE.md"
    ).read_text(encoding="utf-8")
    version = _project_version()
    if version in architecture:
        errors.append(
            "docs/architecture/ARCHITECTURE.md: current release version is not architecture"
        )

    for path in sorted((REPOSITORY_ROOT / "adapters").rglob("*.md")):
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(
                f"{path.relative_to(REPOSITORY_ROOT).as_posix()}: invalid UTF-8 "
                f"at byte {exc.start}"
            )
    return errors


def _project_version() -> str:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10
        import tomli as tomllib  # type: ignore[no-redef]

    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def main() -> int:
    errors = check_docs()
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
