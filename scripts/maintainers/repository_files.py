"""List release-source files with a Git-index fast path."""

from __future__ import annotations

import subprocess
from pathlib import Path


_IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".pytest-tmp",
    ".pytest_tmp",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "self_evolution",
    "workspaces",
}


def repository_files(root: str | Path) -> list[str]:
    """Return tracked files, or the equivalent bounded source-archive list."""
    repository_root = Path(root).resolve()
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        result = None
    if result is not None and result.returncode == 0:
        return [
            line.strip().replace("\\", "/")
            for line in result.stdout.splitlines()
            if line.strip()
        ]

    files: list[str] = []
    for path in repository_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repository_root)
        if (
            relative.parts
            and relative.parts[0] == ".supermedicine"
            and relative.as_posix() != ".supermedicine/policies/default.yaml"
        ):
            continue
        if any(part.casefold() in _IGNORED_PARTS for part in relative.parts):
            continue
        if relative.name.endswith((".egg-info", "~", ".pyc")):
            continue
        files.append(relative.as_posix())
    return sorted(files)


__all__ = ["repository_files"]
