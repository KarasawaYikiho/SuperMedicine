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
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TARGET_FILENAME = "SuperMedicine.exe"
DEFAULT_INSTALLER_FILENAME = "SuperMedicineInstaller.exe"
DEFAULT_RELEASE_PAYLOAD_DIRNAME = "release_payload"
DEFAULT_EXE_SEARCH_RELATIVE_PATHS = (
    Path("dist") / DEFAULT_TARGET_FILENAME,
    Path("Dist") / DEFAULT_TARGET_FILENAME,
    Path(DEFAULT_TARGET_FILENAME),
)
RELEASE_PAYLOAD_REQUIRED_PATHS = (
    Path("install.py"),
    Path("Install.py"),
    Path("installer") / "exe_release.py",
    Path("core"),
    Path("permission"),
    Path("dist") / DEFAULT_TARGET_FILENAME,
)
_PAYLOAD_EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
_PAYLOAD_EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".token"}
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
    """Resolve and validate the source Exe path.

    CI release archives are laid out with the application executable at
    ``dist/SuperMedicine.exe``.  Local builds have historically used either
    ``dist/`` or ``Dist/``, and some manually assembled release archives place
    ``SuperMedicine.exe`` next to ``Install.py``.  Accept the requested path when
    it exists; otherwise search those compatible locations from both the current
    working directory and the extracted release root.
    """

    source = Path(exe_path).expanduser()
    candidates = _exe_search_candidates(source)
    for candidate in candidates:
        if candidate.exists():
            if candidate.suffix.lower() != ".exe":
                raise ExeReleaseError(
                    f"Exe source must use .exe suffix: {candidate.name}"
                )
            if not candidate.is_file():
                raise ExeReleaseError(f"Exe source must be a file: {candidate}")
            return candidate
    raise FileNotFoundError(_missing_exe_message(source, candidates))


def _release_root() -> Path:
    """Return the source/release root that contains Install.py and installer/."""

    return Path(__file__).resolve().parents[1]


def bundled_release_payload_root() -> Path | None:
    """Return the PyInstaller-bundled release payload root when available."""

    bundle_root = getattr(sys, "_MEIPASS", None)
    if not bundle_root:
        return None
    payload_root = Path(bundle_root) / DEFAULT_RELEASE_PAYLOAD_DIRNAME
    return payload_root if payload_root.exists() else None


def resolve_release_payload_root(
    source_root: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve the release payload root shared by Python and Exe installers."""

    if source_root is not None:
        return Path(source_root).expanduser()
    bundled_root = bundled_release_payload_root()
    if bundled_root is not None:
        return bundled_root
    return _release_root()


def validate_release_payload_root(
    source_root: str | os.PathLike[str] | None = None,
) -> Path:
    """Validate that a payload root follows the unified release layout."""

    root = resolve_release_payload_root(source_root)
    missing = [
        relative.as_posix()
        for relative in RELEASE_PAYLOAD_REQUIRED_PATHS
        if not (root / relative).exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Release payload is incomplete; missing required path(s): "
            + ", ".join(missing)
            + f". Expected unified release layout rooted at: {root}"
        )
    return root


def _is_payload_excluded(relative: Path) -> bool:
    if any(part in _PAYLOAD_EXCLUDED_DIR_NAMES for part in relative.parts):
        return True
    if relative.suffix in _PAYLOAD_EXCLUDED_SUFFIXES:
        return True
    if relative.name in {
        DEFAULT_INSTALLER_FILENAME,
        f"{DEFAULT_INSTALLER_FILENAME}.manifest",
    }:
        return True
    if relative.name.endswith("~") or relative.name.endswith(".log"):
        return True
    return False


def iter_release_payload_files(
    source_root: str | os.PathLike[str] | None = None,
) -> list[tuple[Path, Path]]:
    """Return ``(source, relative)`` pairs for files in the unified payload."""

    root = validate_release_payload_root(source_root)
    files: list[tuple[Path, Path]] = []
    for source in sorted(root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(root)
        if _is_payload_excluded(relative):
            continue
        files.append((source, relative))
    return files


def _safe_directory_target(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ExeReleaseError(f"Release payload relative path is unsafe: {relative}")
    target = root / relative
    root_resolved = root.resolve(strict=False)
    target_resolved = target.resolve(strict=False)
    try:
        target_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ExeReleaseError(
            f"Release payload target escapes install directory: {target}"
        ) from exc
    return target


def release_payload_to_directory(
    *,
    target_dir: str | os.PathLike[str],
    source_root: str | os.PathLike[str] | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Extract/copy the unified release payload into a user-selected directory."""

    payload_root = validate_release_payload_root(source_root)
    install_dir = Path(target_dir).expanduser()
    files = iter_release_payload_files(payload_root)
    planned_targets = [
        _safe_directory_target(install_dir, relative) for _, relative in files
    ]
    existing = [target for target in planned_targets if target.exists()]
    result: dict[str, Any] = {
        "source_root": payload_root,
        "target_dir": install_dir,
        "file_count": len(files),
        "existing_count": len(existing),
        "overwrite": overwrite,
        "dry_run": dry_run,
    }

    if existing and not overwrite:
        result.update(
            {"status": "skipped", "reason": "target-exists", "target_path": existing[0]}
        )
        logger.info(
            "Release payload extraction skipped: target exists at %s", existing[0]
        )
        return result

    if dry_run:
        result.update({"status": "dry-run", "reason": "would-extract"})
        logger.info(
            "Release payload extraction dry-run: source=%s target=%s files=%s overwrite=%s",
            payload_root,
            install_dir,
            len(files),
            overwrite,
        )
        return result

    try:
        for source, relative in files:
            target = _safe_directory_target(install_dir, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    except Exception as exc:
        logger.error(
            "Release payload extraction failed: source=%s target=%s error=%s",
            payload_root,
            install_dir,
            exc,
        )
        raise

    result.update(
        {"status": "copied", "reason": "overwritten" if existing else "created"}
    )
    logger.info(
        "Release payload extraction completed: target=%s files=%s",
        install_dir,
        len(files),
    )
    return result


def _append_unique_path(paths: list[Path], path: Path) -> None:
    comparable = path.resolve(strict=False)
    if all(existing.resolve(strict=False) != comparable for existing in paths):
        paths.append(path)


def _exe_search_candidates(requested: Path) -> list[Path]:
    """Return deterministic executable candidates for release and local layouts."""

    roots = [Path.cwd(), _release_root()]
    candidates: list[Path] = []

    if requested.is_absolute():
        _append_unique_path(candidates, requested)
    else:
        for root in roots:
            _append_unique_path(candidates, root / requested)

    for relative in DEFAULT_EXE_SEARCH_RELATIVE_PATHS:
        for root in roots:
            _append_unique_path(candidates, root / relative)

    return candidates


def _missing_exe_message(requested: Path, candidates: list[Path]) -> str:
    searched = "; ".join(str(path) for path in candidates)
    expected = ", ".join(path.as_posix() for path in DEFAULT_EXE_SEARCH_RELATIVE_PATHS)
    return (
        f"Exe source does not exist: {requested}. "
        f"Missing required file: {DEFAULT_TARGET_FILENAME}. "
        f"Searched paths: {searched}. "
        f"Expected release executable layout: {expected}. "
        "Regenerate the release package from CI or run the packaging workflow so "
        "dist/SuperMedicine.exe is produced and included next to Install.py; for "
        "local builds, rebuild the executable into dist/ or Dist/ before rerunning "
        "Install.py --release-exe."
    )


def normalize_target_filename(
    target_filename: str | os.PathLike[str] | None, source: Path
) -> str:
    """Return a safe desktop target filename for the released Exe."""

    raw_name = (
        str(target_filename)
        if target_filename is not None
        else source.name or DEFAULT_TARGET_FILENAME
    )
    name = raw_name.strip()
    if not name:
        name = DEFAULT_TARGET_FILENAME
    if name != Path(name).name:
        raise ExeReleaseError(
            f"Target filename must not include directories: {raw_name!r}"
        )
    if name in {".", ".."} or any(char in _INVALID_FILENAME_CHARS for char in name):
        raise ExeReleaseError(
            f"Target filename contains invalid characters: {raw_name!r}"
        )
    stem = Path(name).stem
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        raise ExeReleaseError(
            f"Target filename uses a reserved Windows name: {raw_name!r}"
        )
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
        raise ExeReleaseError(
            f"Target path escapes desktop directory: {target}"
        ) from exc
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
        result.update(
            {
                "status": "dry-run",
                "reason": "would-overwrite" if target_exists else "would-copy",
            }
        )
        logger.info(
            "Exe release dry-run: source=%s target=%s overwrite=%s",
            source,
            target,
            overwrite,
        )
        return result

    try:
        desktop.mkdir(parents=True, exist_ok=True)
        if not desktop.is_dir():
            raise ExeReleaseError(f"Desktop path is not a directory: {desktop}")
        shutil.copy2(source, target)
    except Exception as exc:
        logger.error(
            "Exe release failed: source=%s target=%s error=%s", source, target, exc
        )
        raise

    result.update(
        {"status": "copied", "reason": "overwritten" if target_exists else "created"}
    )
    logger.info("Exe release completed: target=%s", target)
    return result
