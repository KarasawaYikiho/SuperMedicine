#!/usr/bin/env python3
"""SuperMedicine safe local uninstaller.

Ownership rule: this script deletes only paths that are inside the selected
project directory and are either (1) canonical SuperMedicine-owned paths such as
``.supermedicine`` and generated runtime artifact directories, or (2) explicit
installer-created target paths recorded in ``.supermedicine/install-record.json``
or passed through ``--target``.  Paths outside the project root, repository
source files, unrecorded platform directories, and user-created files are never
removed by default.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


logger = logging.getLogger(__name__)

PROJECT_MARKER = "supermedicine"
INSTALL_RECORD = ".supermedicine/install-record.json"
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
SENSITIVE_KEY_PARTS = ("api_key", "apikey", "token", "secret", "password", "authorization")


@dataclass(frozen=True)
class RemovalCandidate:
    path: Path
    reason: str
    recorded: bool = False


def _redact_text(value: str) -> str:
    redacted = value
    for prefix in ("sk-", "xox", "ghp_", "gho_", "glpat-"):
        if prefix in redacted:
            redacted = redacted.replace(prefix, "<redacted-prefix>")
    return redacted


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


def _iter_recorded_paths(record: dict[str, Any]) -> Iterable[str]:
    for key in ("created_paths", "platform_target_paths", "installer_created_platform_target_paths"):
        values = record.get(key, [])
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str) and value.strip():
                    yield value
    platforms = record.get("platforms", {})
    if isinstance(platforms, dict):
        for platform in platforms.values():
            if isinstance(platform, dict):
                values = platform.get("target_paths", [])
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, str) and value.strip():
                            yield value


def _resolve_candidate(project_dir: Path, path_value: str) -> Path:
    candidate = Path(os.path.expanduser(os.path.expandvars(path_value)))
    if not candidate.is_absolute():
        candidate = project_dir / candidate
    return candidate


def collect_removal_candidates(project_dir: Path, explicit_targets: Iterable[str] = ()) -> tuple[list[RemovalCandidate], list[str]]:
    project_dir = project_dir.resolve()
    record = _load_install_record(project_dir)
    candidates: list[RemovalCandidate] = []
    skipped: list[str] = []

    for relative in (*RUNTIME_ARTIFACT_PATHS, *OWNED_DEFAULT_PATHS):
        candidates.append(RemovalCandidate(project_dir / relative, "canonical-project-owned"))

    for raw_path in _iter_recorded_paths(record):
        candidates.append(RemovalCandidate(_resolve_candidate(project_dir, raw_path), "recorded-installer-created", recorded=True))

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
        existing = unique.get(resolved)
        if existing is None or candidate.recorded:
            unique[resolved] = RemovalCandidate(resolved, candidate.reason, candidate.recorded)
    return sorted(unique.values(), key=lambda item: len(item.path.parts), reverse=True), skipped


def _delete_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def uninstall(
    project_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
    explicit_targets: Iterable[str] = (),
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    candidates, skipped = collect_removal_candidates(project_dir, explicit_targets)
    existing = [candidate for candidate in candidates if candidate.path.exists() or candidate.path.is_symlink()]

    if not dry_run and not (force or yes):
        confirmation = input("Type 'supermedicine' to remove SuperMedicine-owned local files: ").strip().lower()
        if confirmation != PROJECT_MARKER:
            cancelled_result: dict[str, Any] = {"status": "cancelled", "planned": [], "removed": [], "skipped": skipped + ["confirmation-mismatch"]}
            logger.info(json.dumps(_redact_data(cancelled_result), ensure_ascii=False, indent=2))
            return cancelled_result

    removed: list[str] = []
    planned: list[dict[str, str]] = []
    for candidate in existing:
        relative = _safe_display(candidate.path, project_dir)
        planned.append({"path": relative, "reason": candidate.reason})
        if not dry_run:
            _delete_path(candidate.path)
            removed.append(relative)

    result: dict[str, Any] = {
        "status": "dry-run" if dry_run else "removed",
        "project_dir": _safe_display(project_dir, project_dir),
        "ownership_rule": "project-owned paths only: canonical .supermedicine/runtime artifacts plus recorded or explicit installer-created platform targets inside the project root",
        "planned": planned,
        "removed": removed,
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
    args = parser.parse_args()
    uninstall(args.project_dir, dry_run=args.dry_run, force=args.force, yes=args.yes, explicit_targets=args.target)


if __name__ == "__main__":
    main()
