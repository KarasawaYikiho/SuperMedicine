#!/usr/bin/env python3
"""SuperMedicine safe local uninstaller.

Ownership rule: this script deletes only paths that are inside the selected
project directory and are either (1) canonical SuperMedicine-owned paths such as
``.supermedicine`` and generated runtime artifact directories, or (2) explicit
installer-created binaries, shortcuts, config/cache/log/temp/user-data paths and
platform targets recorded in ``.supermedicine/install-record.json`` or passed
through ``--target``.  Paths outside the project root, repository source files,
unrecorded platform directories, and unrecorded user-created files are never
removed.  Recorded user-data paths are removed by default for clean uninstall;
use ``--preserve-user-data`` to retain them explicitly.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from core.redaction import redact_sensitive


logger = logging.getLogger(__name__)

PROJECT_MARKER = "supermedicine"
INSTALL_RECORD = ".supermedicine/install-record.json"
INSTALL_MANIFEST = "install.json"
OWNED_DEFAULT_PATHS: tuple[str, ...] = (
    ".supermedicine",
    ".pytest-tmp",
    "workspaces",
)
RUNTIME_ARTIFACT_PATHS: tuple[str, ...] = (
    ".supermedicine/checkpoints",
    ".supermedicine/policies/audit.jsonl",
    ".supermedicine/sessions",
    ".supermedicine/rag",
)
INSTALL_RECORD_PATH_KEYS: tuple[str, ...] = (
    "created_paths",
    "platform_target_paths",
    "installer_created_platform_target_paths",
    "binaries",
    "binary_paths",
    "shortcuts",
    "shortcut_paths",
    "config_dirs",
    "configuration_dirs",
    "cache_dirs",
    "log_dirs",
    "logs",
    "temp_dirs",
    "temporary_dirs",
)
USER_DATA_PATH_KEYS: tuple[str, ...] = (
    "user_data_paths",
    "preserve_paths",
    "data_dirs",
)
SENSITIVE_KEY_PARTS = ("api_key", "apikey", "token", "secret", "password", "authorization")


@dataclass(frozen=True)
class RemovalCandidate:
    path: Path
    reason: str
    recorded: bool = False
    user_data: bool = False


@dataclass(frozen=True)
class Residual:
    kind: str
    target: str
    reason: str
    suggestion: str


def _redact_text(value: str) -> str:
    return str(redact_sensitive(value))


def _redact_data(data: Any) -> Any:
    if isinstance(data, dict):
        result: dict[str, Any] = {}
        for key, value in data.items():
            if any(part in str(key).lower().replace("-", "_") for part in SENSITIVE_KEY_PARTS):
                result[key] = "<redacted>" if value else value
            else:
                result[key] = _redact_data(value)
        return result
    if isinstance(data, list):
        return [_redact_data(item) for item in data]
    if isinstance(data, str):
        return _redact_text(data)
    return data


def _safe_display(path: Path, project_dir: Path) -> str:
    try:
        return path.resolve().relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        return "<outside-project>"


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _load_install_record(project_dir: Path) -> dict[str, Any]:
    record_path = project_dir / INSTALL_RECORD
    if not record_path.is_file():
        return {}
    try:
        loaded = json.loads(record_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Ignoring invalid install record: %s", _safe_display(record_path, project_dir))
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _load_install_manifest(project_dir: Path) -> dict[str, Any]:
    manifest_path = project_dir / INSTALL_MANIFEST
    if not manifest_path.is_file():
        return {}
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Ignoring invalid install manifest: %s", _safe_display(manifest_path, project_dir))
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _iter_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str) and value.strip():
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_string_values(item)
    elif isinstance(value, dict):
        path_value = value.get("path") or value.get("target") or value.get("location")
        if isinstance(path_value, str) and path_value.strip():
            yield path_value


def _iter_recorded_paths(record: dict[str, Any], keys: Iterable[str] = INSTALL_RECORD_PATH_KEYS) -> Iterable[str]:
    key_tuple = tuple(keys)
    for key in keys:
        values = record.get(key, [])
        yield from _iter_string_values(values)
    platforms = record.get("platforms", {})
    if isinstance(platforms, dict):
        for platform in platforms.values():
            if isinstance(platform, dict):
                platform_keys = (*key_tuple, "target_paths") if key_tuple == INSTALL_RECORD_PATH_KEYS else key_tuple
                for key in platform_keys:
                    yield from _iter_string_values(platform.get(key, []))


def _iter_user_data_paths(record: dict[str, Any]) -> Iterable[str]:
    yield from _iter_recorded_paths(record, USER_DATA_PATH_KEYS)


def _iter_recorded_names(record: dict[str, Any], key: str) -> Iterable[str]:
    yield from _iter_string_values(record.get(key, []))
    platforms = record.get("platforms", {})
    if isinstance(platforms, dict):
        for platform in platforms.values():
            if isinstance(platform, dict):
                yield from _iter_string_values(platform.get(key, []))


def _resolve_candidate(project_dir: Path, path_value: str) -> Path:
    candidate = Path(os.path.expanduser(os.path.expandvars(path_value)))
    if not candidate.is_absolute():
        candidate = project_dir / candidate
    return candidate


def collect_removal_candidates(
    project_dir: Path,
    explicit_targets: Iterable[str] = (),
    *,
    preserve_user_data: bool = False,
) -> tuple[list[RemovalCandidate], list[str]]:
    project_dir = project_dir.resolve()
    record = _load_install_record(project_dir)
    manifest = _load_install_manifest(project_dir)
    candidates: list[RemovalCandidate] = []
    skipped: list[str] = []

    for relative in (*RUNTIME_ARTIFACT_PATHS, *OWNED_DEFAULT_PATHS):
        candidates.append(RemovalCandidate(project_dir / relative, "canonical-project-owned"))

    for raw_path in _iter_recorded_paths(record):
        candidates.append(RemovalCandidate(_resolve_candidate(project_dir, raw_path), "recorded-installer-created", recorded=True))

    for raw_path in _iter_user_data_paths(record):
        candidates.append(
            RemovalCandidate(
                _resolve_candidate(project_dir, raw_path),
                "recorded-user-data" if not preserve_user_data else "preserved-user-data",
                recorded=True,
                user_data=True,
            )
        )

    uninstall_manifest = manifest.get("uninstall", {}) if isinstance(manifest.get("uninstall"), dict) else {}
    for raw_path in _iter_recorded_paths(uninstall_manifest):
        candidates.append(RemovalCandidate(_resolve_candidate(project_dir, raw_path), "manifest-uninstall-artifact", recorded=True))

    for raw_path in explicit_targets:
        candidates.append(RemovalCandidate(_resolve_candidate(project_dir, raw_path), "explicit-installer-created-target", recorded=True))

    unique: dict[Path, RemovalCandidate] = {}
    for candidate in candidates:
        resolved = candidate.path.resolve()
        if not _is_within(resolved, project_dir):
            skipped.append(f"outside-project:{resolved}")
            continue
        if resolved == project_dir:
            skipped.append("project-root-not-removed")
            continue
        if preserve_user_data and candidate.user_data:
            skipped.append(f"preserved-user-data:{resolved}")
            continue
        existing = unique.get(resolved)
        if existing is None or candidate.recorded:
            unique[resolved] = RemovalCandidate(resolved, candidate.reason, candidate.recorded)
    return sorted(unique.values(), key=lambda item: len(item.path.parts), reverse=True), skipped


def _delete_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _repair_suggestion(kind: str, target: str) -> str:
    suggestions = {
        "path": f"Remove '{target}' from PATH manually or rerun uninstall with sufficient permissions.",
        "environment": f"Unset environment variable '{target}' manually from the user/system environment.",
        "service": f"Stop and delete service '{target}' manually with service manager permissions.",
        "registry": f"Remove registry key/value '{target}' manually after confirming it belongs to SuperMedicine.",
        "file": f"Delete '{target}' manually after closing programs that may be using it.",
    }
    return suggestions.get(kind, f"Review and remove '{target}' manually if it belongs to SuperMedicine.")


def _residual(kind: str, target: str, reason: str) -> Residual:
    return Residual(kind=kind, target=target, reason=reason, suggestion=_repair_suggestion(kind, target))


def _remove_path_from_env_value(path_value: str, entries: Iterable[str]) -> tuple[str, list[str]]:
    wanted = {os.path.normcase(os.path.normpath(os.path.expanduser(os.path.expandvars(entry)))) for entry in entries if entry}
    kept: list[str] = []
    removed: list[str] = []
    for item in path_value.split(os.pathsep):
        normalized = os.path.normcase(os.path.normpath(os.path.expanduser(os.path.expandvars(item))))
        if normalized in wanted:
            removed.append(item)
        else:
            kept.append(item)
    return os.pathsep.join(kept), removed


def _cleanup_process_environment(record: dict[str, Any], *, dry_run: bool) -> tuple[list[str], list[Residual]]:
    cleaned: list[str] = []
    residuals: list[Residual] = []
    path_entries = list(_iter_recorded_names(record, "path_entries"))
    if path_entries:
        current_path = os.environ.get("PATH", "")
        new_path, removed = _remove_path_from_env_value(current_path, path_entries)
        if removed:
            cleaned.extend(f"PATH:{entry}" for entry in removed)
            if not dry_run:
                os.environ["PATH"] = new_path

    for name in _iter_recorded_names(record, "environment_variables"):
        if name in os.environ:
            cleaned.append(f"env:{name}")
            if not dry_run:
                os.environ.pop(name, None)
    return cleaned, residuals


def _cleanup_windows_registry_environment(record: dict[str, Any], *, dry_run: bool) -> tuple[list[str], list[Residual]]:
    if sys.platform != "win32":
        return [], []
    env_vars = list(_iter_recorded_names(record, "environment_variables"))
    path_entries = list(_iter_recorded_names(record, "path_entries"))
    if not env_vars and not path_entries:
        return [], []
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return [], []
    cleaned: list[str] = []
    residuals: list[Residual] = []
    hives = [
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    for hive, subkey in hives:
        try:
            access = winreg.KEY_READ | (winreg.KEY_SET_VALUE if not dry_run else 0)
            with winreg.OpenKey(hive, subkey, 0, access) as key:
                if path_entries:
                    try:
                        path_value, value_type = winreg.QueryValueEx(key, "Path")
                    except OSError:
                        path_value = ""
                        value_type = winreg.REG_EXPAND_SZ
                    if isinstance(path_value, str):
                        new_path, removed = _remove_path_from_env_value(path_value, path_entries)
                        if removed:
                            cleaned.extend(f"registry-path:{entry}" for entry in removed)
                            if not dry_run:
                                winreg.SetValueEx(key, "Path", 0, value_type, new_path)
                for name in env_vars:
                    try:
                        winreg.QueryValueEx(key, name)
                    except OSError:
                        continue
                    cleaned.append(f"registry-env:{name}")
                    if not dry_run:
                        winreg.DeleteValue(key, name)
        except PermissionError as exc:
            residuals.append(_residual("registry", subkey, f"Permission denied: {exc}"))
        except OSError as exc:
            residuals.append(_residual("registry", subkey, str(exc)))
    return cleaned, residuals


def _cleanup_windows_services(record: dict[str, Any], *, dry_run: bool) -> tuple[list[str], list[Residual]]:
    if sys.platform != "win32":
        return [], []
    cleaned: list[str] = []
    residuals: list[Residual] = []
    for service_name in _iter_recorded_names(record, "services"):
        cleaned.append(f"service:{service_name}")
        if dry_run:
            continue
        for command in (("sc", "stop", service_name), ("sc", "delete", service_name)):
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            combined = f"{completed.stdout}\n{completed.stderr}"
            if completed.returncode != 0 and "does not exist" not in combined.lower() and "1060" not in combined:
                residuals.append(_residual("service", service_name, combined.strip() or f"command failed: {' '.join(command)}"))
                break
    return cleaned, residuals


def _cleanup_registry_keys(record: dict[str, Any], *, dry_run: bool) -> tuple[list[str], list[Residual]]:
    cleaned: list[str] = []
    residuals: list[Residual] = []
    for registry_key in _iter_recorded_names(record, "registry_keys"):
        residuals.append(_residual("registry", registry_key, "Automatic registry key deletion is not performed unless recorded as environment cleanup"))
        if dry_run:
            cleaned.append(f"registry-planned:{registry_key}")
    return cleaned, residuals


def uninstall(
    project_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
    explicit_targets: Iterable[str] = (),
    preserve_user_data: bool = False,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    logger.info("Uninstall stage=collect project_dir=%s dry_run=%s force=%s preserve_user_data=%s", project_dir, dry_run, force, preserve_user_data)
    record = _load_install_record(project_dir)
    candidates, skipped = collect_removal_candidates(project_dir, explicit_targets, preserve_user_data=preserve_user_data)
    existing = [candidate for candidate in candidates if candidate.path.exists() or candidate.path.is_symlink()]

    if not dry_run and not (force or yes):
        confirmation = input("Type 'supermedicine' to remove SuperMedicine-owned local files: ").strip().lower()
        if confirmation != PROJECT_MARKER:
            cancelled_result: dict[str, Any] = {"status": "cancelled", "planned": [], "removed": [], "skipped": skipped + ["confirmation-mismatch"]}
            logger.info(json.dumps(_redact_data(cancelled_result), ensure_ascii=False, indent=2))
            return cancelled_result

    removed: list[str] = []
    residuals: list[Residual] = []
    planned: list[dict[str, str]] = []
    for candidate in existing:
        relative = _safe_display(candidate.path, project_dir)
        planned.append({"path": relative, "reason": candidate.reason})
        if not dry_run:
            try:
                logger.info("Uninstall stage=remove path=%s reason=%s", relative, candidate.reason)
                _delete_path(candidate.path)
                removed.append(relative)
            except OSError as exc:
                logger.error("Uninstall stage=remove-failed path=%s error=%s", relative, redact_sensitive(str(exc)))
                residuals.append(_residual("file", relative, str(exc)))

    environment_cleaned, environment_residuals = _cleanup_process_environment(record, dry_run=dry_run)
    registry_environment_cleaned, registry_environment_residuals = _cleanup_windows_registry_environment(record, dry_run=dry_run)
    service_cleaned, service_residuals = _cleanup_windows_services(record, dry_run=dry_run)
    registry_cleaned, registry_residuals = _cleanup_registry_keys(record, dry_run=dry_run)
    residuals.extend(environment_residuals)
    residuals.extend(registry_environment_residuals)
    residuals.extend(service_residuals)
    residuals.extend(registry_residuals)

    result: dict[str, Any] = {
        "status": "dry-run" if dry_run else ("removed-with-residuals" if residuals else "removed"),
        "project_dir": _safe_display(project_dir, project_dir),
        "ownership_rule": "project-owned paths only: canonical .supermedicine/runtime artifacts plus recorded or explicit installer-created binaries, shortcuts, service/environment/PATH metadata, configuration/cache/log/temp directories, platform targets, and explicit targets inside the project root; user data is removed by default unless --preserve-user-data is set",
        "planned": planned,
        "removed": removed,
        "environment_cleaned": environment_cleaned + registry_environment_cleaned,
        "services_cleaned": service_cleaned,
        "registry_cleaned": registry_cleaned,
        "residuals": [residual.__dict__ for residual in residuals],
        "repair_suggestions": [residual.suggestion for residual in residuals],
        "skipped": skipped,
    }
    logger.info(json.dumps(_redact_data(result), ensure_ascii=False, indent=2))
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Safely remove SuperMedicine-owned local install artifacts")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(), help="Project directory to clean; defaults to cwd")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without deleting anything")
    parser.add_argument("--yes", action="store_true", help="Confirm interactive uninstall without typing the marker")
    parser.add_argument("--force", action="store_true", help="Non-interactive mode; implies confirmation")
    parser.add_argument("--target", action="append", default=[], help="Additional installer-created target path to remove if inside project")
    parser.add_argument("--preserve-user-data", action="store_true", help="Keep paths recorded as user data; default uninstall removes them for clean deletion")
    args = parser.parse_args()
    uninstall(
        args.project_dir,
        dry_run=args.dry_run,
        force=args.force,
        yes=args.yes,
        explicit_targets=args.target,
        preserve_user_data=args.preserve_user_data,
    )


if __name__ == "__main__":
    main()
