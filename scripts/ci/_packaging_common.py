"""Shared packaging logic for CI build scripts."""

from __future__ import annotations

from pathlib import Path
import shutil

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest-tmp",
    ".pytest_tmp",
}
EXCLUDED_FILE_NAMES = {".env"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".token"}

INCLUDE_FILES = [
    "cli_entry.py",
    "install_entry.py",
    "uninstall_entry.py",
    "pyproject.toml",
    "requirements.txt",
    "install.json",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/guides/INSTALL.md",
]
INCLUDE_DIRS = ["core", "permission", "agents", "plugins", "adapters", "installer"]


def should_exclude(path: Path) -> bool:
    """Return True if this path should be excluded from packaging."""
    if set(path.parts) & EXCLUDED_DIR_NAMES:
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    if path.name.endswith("~") or path.name.endswith(".log"):
        return True
    return False


def copy_include_files(root: Path, target: Path) -> None:
    """Copy INCLUDE_FILES from root to target, respecting exclusions."""
    for relative in INCLUDE_FILES:
        source = root / relative
        if source.exists() and not should_exclude(Path(relative)):
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)


def copy_include_dirs(root: Path, target: Path) -> None:
    """Recursively copy INCLUDE_DIRS from root to target, respecting exclusions."""
    for relative_dir in INCLUDE_DIRS:
        source_dir = root / relative_dir
        if not source_dir.exists():
            continue
        for source in source_dir.rglob("*"):
            relative = source.relative_to(root)
            if should_exclude(relative):
                continue
            dest = target / relative
            if source.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
