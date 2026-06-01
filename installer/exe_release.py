"""Helpers for releasing a packaged Windows Exe to a user's desktop.

The functions in this module are deliberately small and dependency-injected so
installer tests can use temporary Desktop directories instead of touching a real
user profile.  They do not inspect external assistant-platform configuration and
do not read or log secrets.
"""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TARGET_FILENAME = "SuperMedicine.exe"
_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class ExeReleaseError(ValueError):
    """Raised when an Exe desktop release request is invalid or unsafe."""


def resolve_desktop_dir(desktop_dir: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the Desktop directory, allowing tests/callers to inject it."""

    if desktop_dir is not None:
        return Path(desktop_dir).expanduser()
    return Path.home() / "Desktop"


def resolve_exe_path(exe_path: str | os.PathLike[str]) -> Path:
    """Resolve and validate the source Exe path."""

    source = Path(exe_path).expanduser()
    if source.suffix.lower() != ".exe":
        raise ExeReleaseError(f"Exe source must use .exe suffix: {source.name}")
    if not source.exists():
        raise FileNotFoundError(f"Exe source does not exist: {source}")
    if not source.is_file():
        raise ExeReleaseError(f"Exe source must be a file: {source}")
    return source


def normalize_target_filename(target_filename: str | os.PathLike[str] | None, source: Path) -> str:
    """Return a safe desktop target filename for the released Exe."""

    raw_name = str(target_filename) if target_filename is not None else source.name or DEFAULT_TARGET_FILENAME
    name = raw_name.strip()
    if not name:
        name = DEFAULT_TARGET_FILENAME
    if name != Path(name).name:
        raise ExeReleaseError(f"Target filename must not include directories: {raw_name!r}")
    if name in {".", ".."} or any(char in _INVALID_FILENAME_CHARS for char in name):
        raise ExeReleaseError(f"Target filename contains invalid characters: {raw_name!r}")
    stem = Path(name).stem
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        raise ExeReleaseError(f"Target filename uses a reserved Windows name: {raw_name!r}")
    if Path(name).suffix.lower() != ".exe":
        name = f"{name}.exe"
    return name


def _safe_target_path(desktop: Path, filename: str) -> Path:
    desktop_resolved = desktop.resolve(strict=False)
    target = desktop / filename
    target_resolved = target.resolve(strict=False)
    try:
        target_resolved.relative_to(desktop_resolved)
    except ValueError as exc:
        raise ExeReleaseError(f"Target path escapes desktop directory: {target}") from exc
    return target


def release_exe_to_desktop(
    *,
    exe_path: str | os.PathLike[str],
    desktop_dir: str | os.PathLike[str] | None = None,
    target_filename: str | os.PathLike[str] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Release ``exe_path`` to ``desktop_dir`` using deterministic copy rules.

    Existing targets are skipped by default.  Set ``overwrite=True`` to replace
    an existing target.  ``dry_run=True`` reports the intended operation without
    creating directories or copying bytes.
    """

    desktop = resolve_desktop_dir(desktop_dir)
    source = resolve_exe_path(exe_path)
    filename = normalize_target_filename(target_filename, source)
    target = _safe_target_path(desktop, filename)
    result: dict[str, Any] = {
        "source_path": source,
        "desktop_dir": desktop,
        "target_path": target,
        "target_filename": filename,
        "overwrite": overwrite,
        "dry_run": dry_run,
    }

    target_exists = target.exists()
    if target_exists and not overwrite:
        result.update({"status": "skipped", "reason": "target-exists"})
        logger.info("Exe release skipped: target exists at %s", target)
        return result

    if dry_run:
        result.update({"status": "dry-run", "reason": "would-overwrite" if target_exists else "would-copy"})
        logger.info("Exe release dry-run: source=%s target=%s overwrite=%s", source, target, overwrite)
        return result

    try:
        desktop.mkdir(parents=True, exist_ok=True)
        if not desktop.is_dir():
            raise ExeReleaseError(f"Desktop path is not a directory: {desktop}")
        shutil.copy2(source, target)
    except Exception as exc:
        logger.error("Exe release failed: source=%s target=%s error=%s", source, target, exc)
        raise

    result.update({"status": "copied", "reason": "overwritten" if target_exists else "created"})
    logger.info("Exe release completed: target=%s", target)
    return result
