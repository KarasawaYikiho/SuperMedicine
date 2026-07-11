"""Resolve writable project data separately from bundled resources."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    project_root: Path
    data_root: Path
    resource_root: Path
    executable_root: Path

    @classmethod
    def resolve(
        cls,
        project_root: str | Path | None = None,
        *,
        source_root: str | Path | None = None,
        install_record: str | Path | None = None,
        config_path: str | Path | None = None,
        frozen: bool | None = None,
        bundle_root: str | Path | None = None,
        executable: str | Path | None = None,
        platform: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> RuntimePaths:
        env = os.environ if environ is None else environ
        is_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        source = _absolute(source_root or Path(__file__).parents[1])
        executable_path = _absolute(executable or sys.executable)
        executable_root = executable_path.parent if is_frozen else source
        resource_root = (
            _absolute(bundle_root or getattr(sys, "_MEIPASS", source))
            if is_frozen
            else source
        )

        record = Path(install_record) if install_record else executable_root / ".supermedicine" / "install-record.json"
        config = Path(config_path) if config_path else executable_root / ".supermedicine" / "config.yaml"
        selected = (
            project_root
            or env.get("SM_PROJECT_ROOT")
            or _project_from_record(record)
            or _project_from_config(config)
            or _default_project_root(is_frozen, platform or sys.platform, env, source)
        )
        project = _absolute(selected)
        return cls(
            project_root=project,
            data_root=project / ".supermedicine",
            resource_root=resource_root,
            executable_root=executable_root,
        )


def _absolute(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _project_from_record(record_path: Path) -> str | None:
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    install_dir = record.get("install_dir") if isinstance(record, dict) else None
    return install_dir if isinstance(install_dir, str) and install_dir.strip() else None


def _project_from_config(config_path: Path) -> Path | None:
    if not config_path.is_file():
        return None
    parent = config_path.parent
    return parent.parent if parent.name == ".supermedicine" else parent


def _default_project_root(
    frozen: bool,
    platform: str,
    environ: Mapping[str, str],
    source_root: Path,
) -> Path:
    if not frozen:
        return source_root
    if platform == "win32" and environ.get("LOCALAPPDATA"):
        return Path(environ["LOCALAPPDATA"]) / "SuperMedicine"
    return Path.home() / ".local" / "share" / "SuperMedicine"


__all__ = ["RuntimePaths"]
