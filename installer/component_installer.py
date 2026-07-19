"""Component-based installation logic for SuperMedicine.

This module provides the core logic for componentized installation,
decoupled from any GUI or CLI presentation layer.  Both script-mode
and GUI-mode installers call into these functions.

Usage::

    from installer.component_installer import (
        load_components,
        get_default_selection,
        validate_selection,
        install_components,
        get_component_files,
    )

    components = load_components("install.json")
    default = get_default_selection(components)
    validate_selection(components, selected)
    install_components(components, selected, install_path, source_root)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentDef:
    """Immutable definition of a single installable component.

    Attributes:
        name: Unique component identifier (e.g. ``"cli"``, ``"web"``).
        description: Human-readable description shown in selection UIs.
        required: When ``True`` the component cannot be deselected.
        default: Whether the component is selected by default.
        files: List of relative paths (directories or files) that belong
            to this component.  Directories end with ``/``.
        dependencies: Names of other components that must be selected
            whenever this component is selected.
    """

    name: str
    description: str
    required: bool = False
    default: bool = False
    files: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()


class ComponentError(ValueError):
    """Raised when a component selection or installation request is invalid."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_components(config_path: str | os.PathLike[str]) -> dict[str, ComponentDef]:
    """Load component definitions from an ``install.json`` file.

    Parameters:
        config_path: Path to the JSON configuration file that contains a
            top-level ``"components"`` mapping.

    Returns:
        A dict mapping component name to :class:`ComponentDef`.

    Raises:
        FileNotFoundError: If *config_path* does not exist.
        KeyError: If the file has no ``"components"`` key.
        ComponentError: If a component entry is malformed.
    """

    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with open(path, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)

    raw_components = data.get("components")
    if not isinstance(raw_components, dict):
        raise KeyError(f"配置文件缺少 'components' 字段: {path}")

    components: dict[str, ComponentDef] = {}
    for name, entry in raw_components.items():
        if not isinstance(entry, dict):
            raise ComponentError(
                f"组件 '{name}' 的定义必须是字典，实际类型: {type(entry).__name__}"
            )

        comp_name = entry.get("name", name)
        if comp_name != name:
            raise ComponentError(
                f"组件键名 '{name}' 与内部 name '{comp_name}' 不一致"
            )

        description = str(entry.get("description", ""))
        required = bool(entry.get("required", False))
        default = bool(entry.get("default", False))

        raw_files = entry.get("files", [])
        if not isinstance(raw_files, list):
            raise ComponentError(
                f"组件 '{name}' 的 files 必须是列表，实际类型: {type(raw_files).__name__}"
            )
        files = tuple(str(f) for f in raw_files)

        raw_deps = entry.get("dependencies", [])
        if not isinstance(raw_deps, list):
            raise ComponentError(
                f"组件 '{name}' 的 dependencies 必须是列表，实际类型: {type(raw_deps).__name__}"
            )
        dependencies = tuple(str(d) for d in raw_deps)

        components[name] = ComponentDef(
            name=comp_name,
            description=description,
            required=required,
            default=default,
            files=files,
            dependencies=dependencies,
        )

    return components


# ---------------------------------------------------------------------------
# Default selection
# ---------------------------------------------------------------------------


def get_default_selection(components: dict[str, ComponentDef]) -> list[str]:
    """Return the list of component names that are selected by default.

    A component is included when its ``default`` flag is ``True`` **or**
    when it is ``required`` (required components are always selected).

    The returned list is sorted alphabetically for determinism.
    """

    return sorted(
        name
        for name, comp in components.items()
        if comp.default or comp.required
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_selection(
    components: dict[str, ComponentDef],
    selected: list[str],
) -> None:
    """Validate that *selected* is a legal subset of *components*.

    Rules:
    1. Every name in *selected* must exist in *components*.
    2. All ``required`` components must appear in *selected*.
    3. For every selected component, its ``dependencies`` must also
       appear in *selected*.

    Raises:
        ComponentError: If any rule is violated.
    """

    known = set(components.keys())
    selected_set = set(selected)

    # Rule 1: unknown names
    unknown = selected_set - known
    if unknown:
        raise ComponentError(
            f"选择了未知组件: {', '.join(sorted(unknown))}。"
            f" 可用组件: {', '.join(sorted(known))}"
        )

    # Rule 2: required components must be selected
    missing_required = sorted(
        name for name, comp in components.items()
        if comp.required and name not in selected_set
    )
    if missing_required:
        raise ComponentError(
            f"以下必选组件不可取消: {', '.join(missing_required)}"
        )

    # Rule 3: dependency satisfaction
    for name in sorted(selected_set):
        comp = components[name]
        for dep in comp.dependencies:
            if dep not in selected_set:
                raise ComponentError(
                    f"组件 '{name}' 依赖 '{dep}'，但 '{dep}' 未被选中"
                )


# ---------------------------------------------------------------------------
# File enumeration
# ---------------------------------------------------------------------------


def _iter_source_files(
    source_root: Path,
    relative_entry: str,
) -> list[tuple[Path, Path]]:
    """Expand a component file entry into ``(source, relative)`` pairs.

    * If *relative_entry* ends with ``/`` it is treated as a directory and
      all files beneath it are included.
    * Otherwise it is treated as a single file.
    """

    source = source_root / relative_entry

    if relative_entry.endswith("/"):
        # Directory entry — enumerate all files recursively
        if not source.is_dir():
            logger.warning(
                "组件目录不存在，跳过: %s", source,
            )
            return []
        pairs: list[tuple[Path, Path]] = []
        for file in sorted(source.rglob("*")):
            if file.is_file():
                pairs.append((file, file.relative_to(source_root)))
        return pairs
    else:
        # Single file entry
        if not source.is_file():
            logger.warning(
                "组件文件不存在，跳过: %s", source,
            )
            return []
        return [(source, source.relative_to(source_root))]


def get_component_files(
    components: dict[str, ComponentDef],
    selected: list[str],
    source_root: str | os.PathLike[str] | None = None,
) -> list[tuple[Path, Path]]:
    """Return the ``(source, relative)`` file pairs for *selected* components.

    Parameters:
        components: Component definitions (from :func:`load_components`).
        selected: Names of components to include.
        source_root: Root directory that component ``files`` paths are
            relative to.  Defaults to the current working directory.

    Returns:
        A list of ``(source_absolute, relative)`` pairs, deduplicated and
        sorted by relative path.
    """

    root = Path(source_root) if source_root else Path.cwd()
    seen: dict[Path, Path] = {}

    for name in selected:
        comp = components.get(name)
        if comp is None:
            logger.warning("未知组件 '%s'，跳过", name)
            continue
        for entry in comp.files:
            for source, relative in _iter_source_files(root, entry):
                # Last-write-wins deduplication (deterministic due to sorted iteration)
                seen[relative] = source

    return sorted(((src, rel) for rel, src in seen.items()), key=lambda pair: pair[1])


# ---------------------------------------------------------------------------
# Installation (file copy)
# ---------------------------------------------------------------------------


def install_components(
    components: dict[str, ComponentDef],
    selected: list[str],
    install_path: str | os.PathLike[str],
    source_root: str | os.PathLike[str] | None = None,
    *,
    overwrite: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Copy files for *selected* components into *install_path*.

    Parameters:
        components: Component definitions (from :func:`load_components`).
        selected: Names of components to install.
        install_path: Destination directory.
        source_root: Root directory that component ``files`` paths are
            relative to.  Defaults to the current working directory.
        overwrite: When ``True``, overwrite existing files.
        dry_run: When ``True``, report what *would* happen without
            copying any files.

    Returns:
        A result dict with keys ``status``, ``target_dir``, ``file_count``,
        ``overwrite``, ``dry_run``, and optionally ``reason``.
    """

    validate_selection(components, selected)

    target_dir = Path(install_path).expanduser().resolve()
    files = get_component_files(components, selected, source_root)

    result: dict[str, Any] = {
        "source_root": str(source_root) if source_root else str(Path.cwd()),
        "target_dir": str(target_dir),
        "components": sorted(selected),
        "file_count": len(files),
        "overwrite": overwrite,
        "dry_run": dry_run,
    }

    if not files:
        result.update({"status": "skipped", "reason": "no-files"})
        logger.info("组件安装跳过: 没有需要释放的文件")
        return result

    # Check for existing files when overwrite is False
    if not overwrite:
        existing = [
            target_dir / relative for _, relative in files
            if (target_dir / relative).exists()
        ]
        if existing:
            result.update({
                "status": "skipped",
                "reason": "target-exists",
                "existing_count": len(existing),
                "first_existing": str(existing[0]),
            })
            logger.info(
                "组件安装跳过: 目标文件已存在 (%d 个冲突)，首个: %s",
                len(existing),
                existing[0],
            )
            return result

    if dry_run:
        result.update({"status": "dry-run", "reason": "would-copy"})
        logger.info(
            "组件安装 dry-run: target=%s files=%s components=%s",
            target_dir,
            len(files),
            sorted(selected),
        )
        return result

    # Perform actual copy
    copied = 0
    created: list[Path] = []
    overwritten: dict[Path, bytes] = {}
    try:
        for source, relative in files:
            target = target_dir / relative
            if target.is_file():
                overwritten[target] = target.read_bytes()
            else:
                created.append(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
    except Exception as exc:
        for target in reversed(created):
            target.unlink(missing_ok=True)
        for target, payload in overwritten.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        logger.error(
            "组件安装失败: target=%s copied=%d/%d error=%s",
            target_dir,
            copied,
            len(files),
            exc,
        )
        raise

    result.update({"status": "copied", "reason": "overwritten" if overwrite else "created"})
    logger.info(
        "组件安装完成: target=%s files=%d components=%s",
        target_dir,
        copied,
        sorted(selected),
    )
    return result


def load_install_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read an installation manifest, returning an empty mapping if unavailable."""

    manifest_path = Path(path)
    if not manifest_path.is_file():
        return {}
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class InstallService:
    """Resolve and install manifest components without presentation logic."""

    manifest_path: Path
    source_root: Path
    components: dict[str, ComponentDef]

    @classmethod
    def from_manifest(
        cls,
        manifest_path: str | os.PathLike[str],
        *,
        source_root: str | os.PathLike[str] | None = None,
    ) -> InstallService:
        path = Path(manifest_path).expanduser().resolve()
        return cls(
            manifest_path=path,
            source_root=(Path(source_root) if source_root else path.parent).resolve(),
            components=load_components(path),
        )

    def default_selection(self) -> list[str]:
        return get_default_selection(self.components)

    def validate(self, selected: list[str]) -> None:
        validate_selection(self.components, selected)

    def diagnostics(self, selected: list[str]) -> dict[str, Any]:
        self.validate(selected)
        files = get_component_files(self.components, selected, self.source_root)
        return {
            "manifest": str(self.manifest_path),
            "source_root": str(self.source_root),
            "components": sorted(selected),
            "file_count": len(files),
            "missing_components": sorted(set(selected) - self.components.keys()),
        }

    def install(
        self,
        selected: list[str],
        install_path: str | os.PathLike[str],
        *,
        overwrite: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        return install_components(
            self.components,
            selected,
            install_path,
            self.source_root,
            overwrite=overwrite,
            dry_run=dry_run,
        )
