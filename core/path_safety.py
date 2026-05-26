"""Project-root path safety helpers.

These utilities are intentionally additive foundation code.  They validate paths
against a caller supplied (or current working directory) project root without
changing any existing adapter, CLI, API, plugin, action, permission, or security
semantics.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


DEFAULT_PROTECTED_DIRECTORIES: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    ".supermedicine",
)


class PathSafetyError(ValueError):
    """Base exception for project-root path safety failures."""


class PathOutsideProjectRootError(PathSafetyError):
    """Raised when a path resolves outside the project root."""


class ProtectedPathError(PathSafetyError):
    """Raised when a destructive operation targets a protected path."""


def resolve_project_root(project_root: str | Path | None = None) -> Path:
    """Return the canonical project root path.

    If *project_root* is omitted, the current working directory is used.  The
    returned path is resolved so later containment checks compare canonical
    paths, including platform-specific junction/symlink resolution where
    available.
    """

    root = Path.cwd() if project_root is None else Path(project_root)
    return root.expanduser().resolve()


def _resolve_candidate(path: str | Path, project_root: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_path_in_project_root(
    path: str | Path,
    project_root: str | Path | None = None,
) -> Path:
    """Resolve *path* and ensure it stays within the project root.

    Relative paths are interpreted from the project root.  ``..`` traversal,
    absolute paths outside the root, and existing symlink/junction targets that
    resolve outside the root are rejected.
    """

    root = resolve_project_root(project_root)
    resolved_path = _resolve_candidate(path, root)
    if not _is_relative_to(resolved_path, root):
        raise PathOutsideProjectRootError(
            f"Path resolves outside project root: {resolved_path} (root: {root})"
        )
    return resolved_path


def is_protected_path(
    path: str | Path,
    project_root: str | Path | None = None,
    protected_directories: Iterable[str] = DEFAULT_PROTECTED_DIRECTORIES,
) -> bool:
    """Return whether *path* targets the root or a protected directory tree."""

    root = resolve_project_root(project_root)
    resolved_path = validate_path_in_project_root(path, root)
    if resolved_path == root:
        return True

    relative_parts = resolved_path.relative_to(root).parts
    protected = set(protected_directories)
    return any(part in protected for part in relative_parts)


def validate_destructive_path(
    path: str | Path,
    project_root: str | Path | None = None,
    protected_directories: Iterable[str] = DEFAULT_PROTECTED_DIRECTORIES,
) -> Path:
    """Validate a path intended for a destructive operation.

    The path must remain within the project root and must not target the root
    itself or any configured protected directory tree.
    """

    root = resolve_project_root(project_root)
    resolved_path = validate_path_in_project_root(path, root)
    if is_protected_path(resolved_path, root, protected_directories):
        raise ProtectedPathError(f"Destructive operation targets protected path: {resolved_path}")
    return resolved_path
