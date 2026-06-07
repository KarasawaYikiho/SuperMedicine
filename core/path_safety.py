"""Project-root path safety helpers.

These utilities are intentionally additive foundation code.  They validate paths
against a caller supplied (or current working directory) project root without
changing any existing adapter, CLI, API, plugin, action, permission, or security
semantics.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from core.redaction import redact_sensitive


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


class UnsafePathValueError(PathSafetyError):
    """Raised when a path contains unsafe control characters."""


class SandboxWriteScopeError(PathSafetyError):
    """Raised when a sandbox write target is outside approved writable roots."""


class SandboxFileTypeError(PathSafetyError):
    """Raised when a sandbox write target uses a disallowed file extension."""


class DangerousOverwriteError(PathSafetyError):
    """Raised when a generated write would overwrite an existing file unsafely."""


class SensitiveContentError(PathSafetyError):
    """Raised when generated content appears to contain sensitive material."""


_BARE_TOKEN_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\btoken\s+sk-[A-Za-z0-9._\-]+\b"),
    re.compile(r"\bsk-[A-Za-z0-9._\-]{4,}\b"),
)


def _path_text(path: str | Path) -> str:
    return str(path)


def _contains_unsafe_path_character(value: str) -> bool:
    return any(ord(character) < 32 for character in value)


def validate_path_value(path: str | Path) -> None:
    """Reject path values that cannot safely cross filesystem boundaries.

    The helper is intentionally conservative and additive: it does not reinterpret
    valid paths, but it rejects NUL/control characters before resolution so error
    handling, logging, and downstream filesystem calls cannot observe truncated or
    ambiguous path values.
    """

    value = _path_text(path)
    if _contains_unsafe_path_character(value):
        raise UnsafePathValueError("Path contains unsafe control characters")


def resolve_project_root(project_root: str | Path | None = None) -> Path:
    """Return the canonical project root path.

    If *project_root* is omitted, the current working directory is used.  The
    returned path is resolved so later containment checks compare canonical
    paths, including platform-specific junction/symlink resolution where
    available.
    """

    if project_root is not None:
        validate_path_value(project_root)
    root = Path.cwd() if project_root is None else Path(project_root)
    return root.expanduser().resolve()


def _resolve_candidate(path: str | Path, project_root: Path) -> Path:
    validate_path_value(path)
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
        raise ProtectedPathError(
            f"Destructive operation targets protected path: {resolved_path}"
        )
    return resolved_path


def validate_sandbox_write_path(
    path: str | Path,
    project_root: str | Path | None = None,
    *,
    writable_roots: Iterable[str | Path] = (
        "self_evolution",
        "generated",
        "tools/generated",
    ),
    allowed_extensions: Iterable[str] = (".md", ".py", ".txt"),
    allow_overwrite: bool = False,
) -> Path:
    """Validate a sandbox/self-evolution write target.

    The target must remain inside the project root, live below an approved
    generated-output directory, use an approved file extension, and avoid silent
    overwrites unless the caller explicitly allows replacement.
    """

    root = resolve_project_root(project_root)
    resolved_path = validate_path_in_project_root(path, root)
    normalized_extensions = {
        ext.lower() if str(ext).startswith(".") else f".{str(ext).lower()}"
        for ext in allowed_extensions
    }
    if resolved_path.suffix.lower() not in normalized_extensions:
        raise SandboxFileTypeError(
            f"Sandbox write file type is not allowed: {resolved_path.suffix}"
        )
    candidate_roots = tuple(
        (root / writable_root).expanduser().resolve()
        if not Path(writable_root).expanduser().is_absolute()
        else Path(writable_root).expanduser().resolve()
        for writable_root in writable_roots
    )
    if not any(
        _is_relative_to(resolved_path, writable_root)
        for writable_root in candidate_roots
    ):
        raise SandboxWriteScopeError(
            f"Sandbox write target is outside approved writable roots: {resolved_path}"
        )
    if is_protected_path(resolved_path, root):
        raise ProtectedPathError(
            f"Sandbox write targets protected path: {resolved_path}"
        )
    if resolved_path.exists() and not allow_overwrite:
        raise DangerousOverwriteError(
            f"Sandbox write would overwrite an existing file: {resolved_path}"
        )
    return resolved_path


def reject_sensitive_content(content: str | bytes | None) -> None:
    """Reject generated content that would be redacted before auditing/logging."""

    if content is None:
        return
    text = (
        content.decode("utf-8", errors="replace")
        if isinstance(content, bytes)
        else content
    )
    if any(pattern.search(text) for pattern in _BARE_TOKEN_SECRET_PATTERNS):
        raise SensitiveContentError(
            "Generated content appears to contain sensitive material"
        )
    if redact_sensitive(text) != text:
        raise SensitiveContentError(
            "Generated content appears to contain sensitive material"
        )
