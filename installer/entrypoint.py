#!/usr/bin/env python3
"""SuperMedicine standalone/unified installer.

The default ``--init`` path is intentionally core-only: it creates the
``.supermedicine`` project configuration and canonical permission policy
without inspecting OpenCode, Claude Code, or any other assistant-platform
runtime/config directories. Platform discovery remains available only through
the explicit optional ``--detect`` command.
"""

from __future__ import annotations

import argparse
import json
import getpass
import importlib.util
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import yaml

from core.llm_providers.config import LLMProviderConfig
from core.redaction import redact_sensitive
from core.secure_files import secure_config_permissions
from permission.policy import ensure_default_policy
from installer.component_installer import (
    ComponentDef,
    ComponentError,
    InstallService,
    get_default_selection,
    validate_selection,
)

logger = logging.getLogger("Install")

INSTALLER_TITLE = "SuperMedicine 安装向导"
INSTALLER_RULE = "=" * 52


def _configure_stdio_errors() -> None:
    """Keep argparse/help output writable on narrow Windows stdio encodings."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (AttributeError, TypeError, ValueError):
            continue


DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "supermedicine",
    "version": "Beta0.4.2",
    "llm": {
        "provider": "",
        "providers": {},
    },
}

INSTALL_RECORD_RELATIVE = Path(".supermedicine") / "install-record.json"
CONFIG_RELATIVE = Path(".supermedicine") / "config.yaml"
INSTALL_RECORD_SCHEMA_VERSION = 1
INSTALL_RECORD_NAME = "supermedicine"
PAYLOAD_COLLISION_PATHS: tuple[Path, ...] = (
    Path("cli_entry.py"),
    Path("install_entry.py"),
    Path("installer") / "entrypoint.py",
    Path("installer") / "exe_release.py",
    Path("core"),
    Path("permission"),
    Path("dist") / "SuperMedicine.exe",
    Path("SuperMedicine.exe"),
)


@dataclass(frozen=True)
class ExistingInstallEvidence:
    kind: str
    path: Path
    priority: int
    detail: str = ""


@dataclass(frozen=True)
class ExistingInstallDetection:
    installed: bool
    project_dir: Path
    primary: ExistingInstallEvidence | None = None
    evidence: tuple[ExistingInstallEvidence, ...] = field(default_factory=tuple)

    @property
    def reason(self) -> str:
        return self.primary.kind if self.primary is not None else "none"


_PROVIDER_ENV_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_PROVIDER_FORMAT_HINTS: dict[str, str] = {
    "anthropic": "anthropic",
    "claude": "anthropic",
}

PROVIDER_ENV_NAMES = _PROVIDER_ENV_MAP

INSTALL_ENV_NAMES = {
    "provider": "SM_LLM_PROVIDER",
    "base_url": "SM_LLM_BASE_URL",
    "api_key": "SM_LLM_API_KEY",
    "model": "SM_LLM_MODEL",
}

_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-sonnet-latest",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-3.5-sonnet",
    },
}


def _default_config_text() -> str:
    header = (
        "# SuperMedicine 配置\n"
        "# LLM provider template. 支持任意 provider 名称。\n"
        "# api_format 决定 HTTP 请求格式: openai (兼容 DeepSeek/智谱/Ollama 等) 或 anthropic\n"
        "# 根据 provider 名称自动推断 api_format，也可手动指定。\n"
    )
    return header + yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False, allow_unicode=True)


def _deep_merge_missing(
    target: dict[str, Any], defaults: dict[str, Any]
) -> dict[str, Any]:
    for key, value in defaults.items():
        if key not in target:
            target[key] = value
        elif isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge_missing(target[key], value)
    return target


def _load_config(config_file: Path) -> dict[str, Any]:
    if not config_file.exists():
        return cast(dict[str, Any], yaml.safe_load(_default_config_text()) or {})
    loaded = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        loaded = {}
    defaults = cast(dict[str, Any], yaml.safe_load(_default_config_text()) or {})
    return _deep_merge_missing(loaded, defaults)


def _write_config(config_file: Path, config: dict[str, Any]) -> None:
    header = (
        "# SuperMedicine 配置\n"
        "# Local project configuration. Keep API keys private and do not commit\n"
        "# real secrets from a user workspace.\n"
    )
    config_file.write_text(
        header + yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    secure_config_permissions(config_file)


def _normalize_provider(provider: str | None) -> str | None:
    if provider is None or not provider.strip():
        return None
    normalized = provider.strip().lower()
    return normalized


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _provider_api_format(provider: str) -> str:
    normalized = provider.strip().lower()
    for hint, fmt in _PROVIDER_FORMAT_HINTS.items():
        if hint in normalized:
            return fmt
    return "openai"


def _provider_api_key_env(provider: str) -> str:
    return _PROVIDER_ENV_MAP.get(provider, f"{provider.upper()}_API_KEY")


def _require_complete_llm_config(
    *,
    provider: str | None,
    base_url: str | None,
    api_key: str | None,
    model: str | None,
) -> str:
    normalized_provider = _normalize_provider(provider)
    missing: list[str] = []
    if normalized_provider is None:
        missing.append("provider")
    if not base_url or not base_url.strip():
        missing.append("base_url")
    if not api_key or not api_key.strip():
        missing.append("api_key")
    if not model or not model.strip():
        missing.append("model")
    if missing:
        raise ValueError(
            "初始化需要完整 LLM Provider 配置；缺失: "
            + ", ".join(missing)
            + "。请使用 --interactive，或提供 --provider/--base-url/--api-key/--model、--llm-config、SM_LLM_* 环境变量。"
            " 配置优先级: CLI 参数 > 环境变量 > --llm-config。待补充字段: "
            + ", ".join(missing)
        )
    _validate_install_llm_config(
        provider=normalized_provider or "",
        base_url=base_url or "",
        api_key=api_key or "",
        model=model or "",
    )
    return normalized_provider or ""


def _validate_install_llm_config(
    *, provider: str, base_url: str, api_key: str, model: str
) -> None:
    config = LLMProviderConfig.from_mapping(
        provider,
        {
            "provider": provider,
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
        },
    )
    missing = config.missing_fields()
    if missing:
        raise ValueError("LLM Provider 配置不完整，缺少: " + ", ".join(missing))
    parsed = urlparse(config.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            f"LLM Provider base_url 必须是有效的 http(s) URL；provider={provider} base_url={base_url}"
        )


def _redact(value: str | None) -> str:
    return "<redacted>" if value else ""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_relative_string(path: Path, root: Path) -> str:
    try:
        return (
            path.resolve(strict=False)
            .relative_to(root.resolve(strict=False))
            .as_posix()
        )
    except ValueError:
        return str(path)


def _read_package_version() -> str:
    return str(DEFAULT_CONFIG.get("version", ""))


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        tmp_name = handle.name
        handle.write(text)
    os.replace(tmp_name, path)


def detect_existing_install(
    project_dir: Path,
    *,
    desktop_dir: Path | None = None,
    exe_target_name: str | None = None,
    include_project: bool = True,
    include_payload: bool = True,
) -> ExistingInstallDetection:
    """Detect an existing SuperMedicine install without modifying files.

    Priority is deterministic: install record, config file, payload collision,
    then desktop executable collision.
    """

    project_dir = Path(project_dir).expanduser().resolve()
    evidence: list[ExistingInstallEvidence] = []
    record_path = project_dir / INSTALL_RECORD_RELATIVE
    config_path = project_dir / CONFIG_RELATIVE
    if include_project and record_path.is_file():
        evidence.append(
            ExistingInstallEvidence("install-record", record_path, 10, "record exists")
        )
    if include_project and config_path.is_file():
        evidence.append(
            ExistingInstallEvidence("config", config_path, 20, "config exists")
        )
    if include_project and include_payload:
        for relative in PAYLOAD_COLLISION_PATHS:
            candidate = project_dir / relative
            if candidate.exists():
                evidence.append(
                    ExistingInstallEvidence(
                        "payload-collision", candidate, 30, relative.as_posix()
                    )
                )
                break
    if desktop_dir is not None:
        desktop_candidate = Path(desktop_dir).expanduser() / (
            exe_target_name or "SuperMedicine.exe"
        )
        if desktop_candidate.exists():
            evidence.append(
                ExistingInstallEvidence(
                    "desktop-exe-collision", desktop_candidate, 40, "desktop exe exists"
                )
            )
    ordered = tuple(sorted(evidence, key=lambda item: item.priority))
    return ExistingInstallDetection(
        bool(ordered), project_dir, ordered[0] if ordered else None, ordered
    )


def _record_artifact_value(value: Any, project_dir: Path) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        return path.as_posix()
    return _safe_relative_string(path, project_dir)


def write_install_record(
    project_dir: Path,
    *,
    artifacts: dict[str, Any] | None = None,
    mode: str = "init",
) -> dict[str, Any]:
    """Write or refresh secret-free installer ownership metadata."""

    project_dir = Path(project_dir).expanduser().resolve()
    record_path = project_dir / INSTALL_RECORD_RELATIVE
    previous: dict[str, Any] = {}
    if record_path.is_file():
        try:
            loaded = json.loads(record_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                previous = loaded
        except json.JSONDecodeError:
            previous = {}
    now = _utc_now_iso()
    record: dict[str, Any] = {
        "schema_version": INSTALL_RECORD_SCHEMA_VERSION,
        "name": INSTALL_RECORD_NAME,
        "version": str(DEFAULT_CONFIG.get("version", "")),
        "package_version": _read_package_version(),
        "install_dir": str(project_dir),
        "created_at": previous.get("created_at") or now,
        "updated_at": now,
        "mode": mode,
        "artifacts": previous.get("artifacts", {}),
    }
    if artifacts:
        merged = dict(
            record["artifacts"] if isinstance(record["artifacts"], dict) else {}
        )
        for key, value in artifacts.items():
            if value is None:
                continue
            if isinstance(value, list):
                normalized_values = [
                    item
                    for item in (_record_artifact_value(v, project_dir) for v in value)
                    if item
                ]
                merged[key] = normalized_values
                record[key] = normalized_values
            else:
                normalized_value = _record_artifact_value(value, project_dir)
                merged[key] = normalized_value
                record[key] = normalized_value
        record["artifacts"] = merged
    _atomic_write_json(record_path, record)
    return record


def _resolve_install_value(name: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    return os.environ.get(INSTALL_ENV_NAMES[name])


def _resolve_api_key(provider: str | None, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    generic = os.environ.get(INSTALL_ENV_NAMES["api_key"])
    if generic:
        return generic
    if provider:
        return os.environ.get(_provider_api_key_env(provider))
    return None


def _prompt_value(
    prompt: str, default: str | None = None, *, secret: bool = False
) -> str | None:
    suffix = f" [{default}]" if default and not secret else ""
    if secret:
        if sys.stdin.isatty():
            value = getpass.getpass(f"{prompt}: ").strip()
        else:
            value = input(f"{prompt}: ").strip()
    else:
        value = input(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    return default


def _prompt_required_value(
    prompt: str, default: str | None = None, *, secret: bool = False
) -> str:
    while True:
        value = _prompt_value(prompt, default, secret=secret)
        if value and value.strip():
            return value.strip()
        logger.info("提示: %s 不能为空。", prompt)


def _prompt_base_url(default: str | None = None) -> str:
    while True:
        value = _prompt_required_value("Base URL", default)
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return value
        logger.info(
            "提示: Base URL 需为 http(s) 地址，例如 https://api.openai.com/v1。"
        )


def _prompt_yes_no(prompt: str, default: bool = False) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_text}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes", "1", "true", "是", "好"}:
            return True
        if value in {"n", "no", "0", "false", "否", "不"}:
            return False
        logger.info("提示: 请输入 y 或 n。")


def _prompt_existing_install_action(detection: ExistingInstallDetection) -> str:
    logger.info("")
    logger.info("检测到已有 SuperMedicine 安装: %s", detection.project_dir)
    logger.info(
        "检测依据: %s (%s)",
        detection.reason,
        detection.primary.path if detection.primary else "",
    )
    logger.info("请选择处理方式:")
    logger.info("  1) 卸载旧版本后继续安装")
    logger.info("  2) 更新版本（保留 .supermedicine/config.yaml 和用户数据）")
    logger.info("  3) 取消安装")
    while True:
        value = input("已有安装处理 [1/2/3]: ").strip().lower()
        if value in {"1", "uninstall", "u", "卸载"}:
            return "uninstall"
        if value in {"2", "update", "更新"}:
            return "update"
        if value in {"3", "cancel", "c", "取消"}:
            return "cancel"
        logger.info("提示: 请输入 1、2 或 3。")


def _prompt_preserve_user_data() -> bool:
    logger.info("")
    logger.info("卸载旧版本时是否保留用户数据？")
    logger.info("  1) 保留用户数据（推荐）")
    logger.info("  2) 删除用户数据（干净卸载）")
    logger.info("  3) 返回上一步")
    while True:
        value = input("用户数据处理 [1/2/3]: ").strip().lower()
        if value in {"1", "preserve", "keep", "保留"}:
            return True
        if value in {"2", "remove", "delete", "删除"}:
            return False
        if value in {"3", "back", "返回"}:
            raise KeyboardInterrupt("back")
        logger.info("提示: 请输入 1、2 或 3。")


def _prompt_component_selection(
    components: dict[str, ComponentDef],
) -> list[str]:
    """Interactive component selection with toggle support.

    Required components cannot be deselected.  Dependencies are automatically
    pulled in when a component is selected.
    """
    selected = set(get_default_selection(components))

    while True:
        logger.info("")
        for name in sorted(components):
            comp = components[name]
            is_selected = name in selected
            marker = "✓" if is_selected else " "
            parts: list[str] = []
            if comp.required:
                parts.append("必选")
            if comp.default and not comp.required:
                parts.append("默认选中")
            tag = f" ({', '.join(parts)})" if parts else ""
            logger.info("  [%s] %s - %s%s", marker, name, comp.description, tag)

        logger.info("")
        logger.info("输入组件名切换选中状态，直接回车确认当前选择。")
        value = input("组件选择: ").strip().lower()

        if not value:
            selected_list = sorted(selected)
            try:
                validate_selection(components, selected_list)
                return selected_list
            except ComponentError as exc:
                logger.info("选择无效: %s", exc)
                continue

        if value not in components:
            logger.info(
                "未知组件: %s。可用: %s", value, ", ".join(sorted(components))
            )
            continue

        if components[value].required:
            logger.info("组件 '%s' 为必选组件，不可取消。", value)
            continue

        if value in selected:
            selected.discard(value)
            dependents = [
                n for n in selected if value in components[n].dependencies
            ]
            if dependents:
                logger.info(
                    "无法取消 '%s'：以下组件依赖它: %s",
                    value,
                    ", ".join(dependents),
                )
                selected.add(value)
                continue
        else:
            selected.add(value)
            for dep in components[value].dependencies:
                if dep not in selected:
                    selected.add(dep)
                    logger.info("自动选中依赖组件: %s", dep)


def _prompt_path(prompt: str, default: Path) -> Path:
    value = _prompt_value(prompt, str(default))
    return Path(value or str(default)).expanduser().resolve()


def _provider_defaults(provider: str | None) -> dict[str, str]:
    if provider is None:
        return {}
    return _PROVIDER_DEFAULTS.get(provider, {})


def _collect_interactive_llm_config(
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, str | None]:
    normalized_provider = _normalize_provider(
        _prompt_required_value("Provider", _normalize_provider(provider) or "openai")
    )
    if normalized_provider is None:
        raise ValueError("provider is required")
    defaults = _provider_defaults(normalized_provider)
    base_url = _prompt_base_url(base_url or defaults.get("base_url"))
    model = _prompt_required_value("Model", model or defaults.get("model"))
    api_key = _prompt_required_value("API key", api_key, secret=True)
    return {
        "provider": normalized_provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
    }


def _log_interactive_summary(
    *,
    install_path: Path,
    init_config_enabled: bool,
    provider: str | None,
    base_url: str | None,
    model: str | None,
    create_shortcut: bool,
    add_to_path: bool,
    release_exe: Path | None,
    extract_release: bool,
    selected_components: list[str] | None = None,
) -> None:
    logger.info("")
    logger.info("%s", INSTALLER_RULE)
    logger.info("安装摘要")
    logger.info("%s", INSTALLER_RULE)
    logger.info("目标目录      %s", install_path)
    if selected_components is not None:
        logger.info("已选组件      %s", ", ".join(selected_components))
    logger.info("初始化配置    %s", "是" if init_config_enabled else "否")
    if init_config_enabled:
        logger.info("Provider      %s", provider or "")
        logger.info("Base URL      %s", base_url or "")
        logger.info("Model         %s", model or "")
        logger.info("API key       %s", _redact("provided"))
    logger.info("释放程序文件  %s", "是" if extract_release else "否")
    logger.info("桌面 Exe      %s", release_exe if release_exe else "跳过")
    logger.info("快捷方式      %s", "记录选择" if create_shortcut else "跳过")
    logger.info("PATH          %s", "显示手动配置提示" if add_to_path else "跳过")
    logger.info("%s", INSTALLER_RULE)


def _run_interactive_installer(args: argparse.Namespace) -> None:
    logger.info("%s", INSTALLER_RULE)
    logger.info("%s", INSTALLER_TITLE)
    logger.info("%s", INSTALLER_RULE)
    logger.info("回车使用默认值；API key 不会显示在屏幕上。")
    logger.info("准备: 建议先执行 pip install -e .；命令不可用时可用 python Cli.py。")

    source_root = _release_entrypoint_dir()
    install_json_path = source_root / "install.json"
    install_service: InstallService | None = None
    components: dict[str, ComponentDef] | None = None
    try:
        install_service = InstallService.from_manifest(
            install_json_path, source_root=source_root
        )
        components = install_service.components
    except (FileNotFoundError, KeyError, ComponentError):
        components = None
    has_components = components is not None and bool(components)
    step_total = 5 if has_components else 4

    while True:
        step = 0

        step += 1
        logger.info("")
        logger.info("[%d/%d] 选择安装位置", step, step_total)
        install_path = _prompt_path("安装/项目路径", Path.cwd())
        detection = detect_existing_install(install_path, include_payload=False)
        existing_action = "ignore"
        preserve_user_data = True
        if detection.installed:
            existing_action = _prompt_existing_install_action(detection)
            if existing_action == "cancel":
                logger.info("安装已取消。")
                return
            if existing_action == "uninstall":
                try:
                    preserve_user_data = _prompt_preserve_user_data()
                except KeyboardInterrupt:
                    continue
        extract_release = _prompt_yes_no(
            "释放完整程序文件到该目录", bool(getattr(sys, "frozen", False))
        )

        selected_components: list[str] | None = None
        if has_components and components is not None:
            step += 1
            logger.info("")
            logger.info("[%d/%d] 选择安装组件", step, step_total)
            selected_components = _prompt_component_selection(components)

        step += 1
        logger.info("")
        logger.info("[%d/%d] 初始化项目配置", step, step_total)
        init_config_enabled = _prompt_yes_no("初始化 .supermedicine 配置", True)
        llm_config: dict[str, str | None] = {
            "provider": None,
            "base_url": None,
            "api_key": None,
            "model": None,
        }
        if (
            init_config_enabled
            and existing_action == "update"
            and (install_path / CONFIG_RELATIVE).is_file()
        ):
            logger.info("更新模式: 跳过 LLM 重新填写，保留现有 config.yaml。")
        elif init_config_enabled:
            imported_config = (
                _load_llm_config_file(args.llm_config) if args.llm_config else {}
            )
            provider = _resolve_install_value("provider", args.provider) or cast(
                str | None, imported_config.get("provider")
            )
            base_url = _resolve_install_value("base_url", args.base_url) or cast(
                str | None, imported_config.get("base_url")
            )
            model = _resolve_install_value("model", args.model) or cast(
                str | None, imported_config.get("model")
            )
            normalized_provider = _normalize_provider(provider)
            api_key = _resolve_api_key(normalized_provider, args.api_key) or cast(
                str | None, imported_config.get("api_key")
            )
            llm_config = _collect_interactive_llm_config(
                provider=normalized_provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )

        step += 1
        logger.info("")
        logger.info("[%d/%d] 可选快捷入口", step, step_total)
        create_shortcut = _prompt_yes_no("记录创建快捷方式意向", False)
        add_to_path = _prompt_yes_no("显示 PATH 手动配置提示", False)

        release_exe: Path | None = None
        if _prompt_yes_no("复制 SuperMedicine.exe 到桌面", bool(args.release_exe)):
            default_exe = args.release_exe or Path("dist") / "SuperMedicine.exe"
            release_exe = _prompt_path("Exe 路径", default_exe)

        step += 1
        logger.info("")
        logger.info("[%d/%d] 确认安装", step, step_total)
        _log_interactive_summary(
            install_path=install_path,
            init_config_enabled=init_config_enabled,
            provider=llm_config.get("provider"),
            base_url=llm_config.get("base_url"),
            model=llm_config.get("model"),
            create_shortcut=create_shortcut,
            add_to_path=add_to_path,
            release_exe=release_exe,
            extract_release=extract_release,
            selected_components=selected_components,
        )
        if not _prompt_yes_no("开始安装", True):
            if _prompt_yes_no("返回重新填写", True):
                continue
            logger.info("安装已取消。")
            return

        try:
            logger.info("")
            logger.info("正在安装...")
            if existing_action == "uninstall":
                _uninstall_existing_install(
                    install_path, preserve_user_data=preserve_user_data
                )
            elif existing_action == "update":
                args.extract_overwrite = True
                args.exe_overwrite = True
                logger.info("更新模式: 将保留 .supermedicine/config.yaml 和用户数据。")
            payload_result: dict[str, Any] | None = None
            exe_result: dict[str, Any] | None = None
            if init_config_enabled:
                if (
                    existing_action == "update"
                    and (install_path / CONFIG_RELATIVE).is_file()
                ):
                    _refresh_existing_project_config(install_path)
                else:
                    init_config(
                        install_path,
                        provider=llm_config.get("provider"),
                        base_url=llm_config.get("base_url"),
                        api_key=llm_config.get("api_key"),
                        model=llm_config.get("model"),
                    )
                logger.info("配置完成: %s", install_path / ".supermedicine")
            if extract_release:
                args.extract_release_to = install_path
                payload_result = _extract_release_from_args(args)
            if selected_components and install_service is not None:
                component_result = install_service.install(
                    selected_components,
                    install_path,
                    overwrite=existing_action == "update",
                )
                logger.info(
                    "组件安装完成: status=%s files=%d",
                    component_result.get("status"),
                    component_result.get("file_count", 0),
                )
            if release_exe:
                args.release_exe = release_exe
                if extract_release:
                    _align_release_exe_with_extracted_payload(args)
                exe_result = _release_exe_from_args(args)
            has_install_actions = (
                init_config_enabled
                or extract_release
                or release_exe
                or bool(selected_components)
            )
            if has_install_actions:
                artifacts = _install_record_artifacts_from_results(
                    payload_result=payload_result,
                    exe_result=exe_result,
                    selected_components=selected_components,
                )
                write_install_record(
                    install_path,
                    artifacts=artifacts,
                    mode="update" if existing_action == "update" else "init",
                )
            if add_to_path:
                logger.info(
                    "PATH 提示: 可将 Python Scripts 目录加入系统 PATH，或使用 python Cli.py。"
                )
            if create_shortcut:
                logger.info(
                    "快捷方式提示: 当前版本请手动创建指向 supermedicine 或 python Cli.py 的快捷方式。"
                )
            logger.info("安装完成。可运行 python Cli.py status 检查状态。")
            return
        except (ValueError, OSError, SystemExit) as exc:
            logger.error("安装失败: %s", redact_sensitive(str(exc)))
            if not _prompt_yes_no("重试安装向导", True):
                raise


def _apply_llm_config(
    config: dict[str, Any],
    *,
    provider: str,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    llm = config.setdefault("llm", {})
    if not isinstance(llm, dict):
        llm = {}
        config["llm"] = llm
    providers = llm.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        llm["providers"] = providers
    provider_config = providers.setdefault(provider, {})
    if not isinstance(provider_config, dict):
        provider_config = {}
        providers[provider] = provider_config

    provider_config.setdefault("api_format", _provider_api_format(provider))
    provider_config.setdefault("api_key_env", _provider_api_key_env(provider))
    if base_url:
        provider_config["base_url"] = base_url
    if model:
        provider_config["model"] = model
    if api_key:
        provider_config["api_key"] = api_key
        provider_config["api_key_env"] = _provider_api_key_env(provider)
    llm["provider"] = provider


def _load_llm_config_file(config_path: Path) -> dict[str, str | None]:
    if not config_path.exists():
        raise ValueError(f"LLM 配置文件不存在: {config_path}")
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError("LLM 配置文件必须是 YAML mapping")

    llm = loaded.get("llm") if isinstance(loaded.get("llm"), dict) else loaded
    if not isinstance(llm, dict):
        raise ValueError("LLM 配置文件缺少 llm 配置段")

    provider = _normalize_provider(
        _optional_string(llm.get("provider") or loaded.get("provider"))
    )
    provider_config: dict[str, Any] = {}
    providers = llm.get("providers")
    if provider and isinstance(providers, dict):
        raw_provider_config = providers.get(provider, {})
        if isinstance(raw_provider_config, dict):
            provider_config = dict(raw_provider_config)
    elif provider is None and isinstance(providers, dict) and len(providers) == 1:
        provider, raw_provider_config = next(iter(providers.items()))
        provider = _normalize_provider(str(provider))
        if isinstance(raw_provider_config, dict):
            provider_config = dict(raw_provider_config)

    merged = dict(llm)
    merged.update(provider_config)
    return {
        "provider": provider,
        "base_url": _optional_string(merged.get("base_url") or merged.get("baseURL")),
        "api_key": _optional_string(merged.get("api_key")),
        "model": _optional_string(merged.get("model")),
    }


def _snapshot_install_state(config_dir: Path) -> Path | None:
    if not config_dir.exists():
        return None
    backup_dir = config_dir.parent / f".{config_dir.name}.install-backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(config_dir, backup_dir)
    return backup_dir


def _restore_install_state(config_dir: Path, backup_dir: Path | None) -> None:
    if config_dir.exists():
        shutil.rmtree(config_dir)
    if backup_dir is not None and backup_dir.exists():
        shutil.move(str(backup_dir), str(config_dir))


def write_llm_config(
    project_dir: Path,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    logger.info(
        "Install stage=llm-config-write project_dir=%s provider=%s",
        project_dir,
        provider or "",
    )
    normalized_provider = _require_complete_llm_config(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    config_file = project_dir / ".supermedicine" / "config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config = _load_config(config_file)
    _apply_llm_config(
        config,
        provider=normalized_provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    _write_config(config_file, config)
    logger.info(
        "LLM 配置已写入: provider=%s base_url=%s model=%s api_key=%s",
        normalized_provider,
        base_url or config["llm"]["providers"][normalized_provider].get("base_url", ""),
        model or config["llm"]["providers"][normalized_provider].get("model", ""),
        _redact(api_key),
    )


def detect_platform() -> str:
    """Optionally detect installed assistant-platform add-ons.

    This function is not called by ``init_config`` or by module import. Keeping
    it behind the explicit CLI flag preserves standalone initialization on
    hosts with no OpenCode/Claude Code assumptions.
    """
    if Path.home().joinpath(".claude").exists():
        return "claude-code"
    if Path.home().joinpath(".config", "opencode").exists():
        return "opencode"
    return "standalone"


def init_config(
    project_dir: Path,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    """Initialize standalone SuperMedicine project configuration only."""
    logger.info(
        "Install stage=init-start project_dir=%s provider=%s base_url=%s model=%s api_key=%s",
        project_dir,
        provider or "",
        base_url or "",
        model or "",
        _redact(api_key),
    )
    normalized_provider = _require_complete_llm_config(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    config_dir = project_dir / ".supermedicine"
    backup_dir = _snapshot_install_state(config_dir)
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"
        if not config_file.exists():
            config_file.write_text(_default_config_text(), encoding="utf-8")
        write_llm_config(
            project_dir,
            provider=normalized_provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        (config_dir / "agents").mkdir(exist_ok=True)
        (config_dir / "plugins").mkdir(exist_ok=True)
        ensure_default_policy(project_dir, Path(__file__).resolve().parents[1])
    except Exception as exc:
        _restore_install_state(config_dir, backup_dir)
        logger.error("初始化失败，已回滚更改: %s", redact_sensitive(str(exc)))
        raise
    if backup_dir is not None and backup_dir.exists():
        shutil.rmtree(backup_dir)
    write_install_record(project_dir, mode="init")
    logger.info("初始化完成: %s", config_dir)
    logger.info("")
    logger.info("如果 'supermedicine' 命令不可用，请将以下目录添加到系统 PATH：")
    logger.info("  Windows:  %APPDATA%\\Python\\Python<版本>\\Scripts")
    logger.info("  Linux/macOS: ~/.local/bin")
    logger.info("或者使用 'python Cli.py' 代替 'supermedicine' 命令。")


def _log_exe_release_result(result: dict[str, Any]) -> None:
    """Log user-facing Exe release status with deterministic wording."""

    status = result.get("status", "unknown")
    target = result.get("target_path", "")
    reason = result.get("reason", "")
    if status == "copied":
        logger.info("桌面 Exe 释放完成: target=%s reason=%s", target, reason)
    elif status == "skipped":
        logger.info("桌面 Exe 释放跳过: target=%s reason=%s", target, reason)
    elif status == "dry-run":
        logger.info("桌面 Exe 释放 dry-run: target=%s reason=%s", target, reason)
    else:
        logger.info(
            "桌面 Exe 释放结果: status=%s target=%s reason=%s", status, target, reason
        )


def _log_payload_release_result(result: dict[str, Any]) -> None:
    """Log user-facing full release extraction status with deterministic wording."""

    status = result.get("status", "unknown")
    target = result.get("target_dir", "")
    reason = result.get("reason", "")
    files = result.get("file_count", "")
    if status == "copied":
        logger.info(
            "安装 Exe 程序文件释放完成: target=%s files=%s reason=%s",
            target,
            files,
            reason,
        )
    elif status == "skipped":
        logger.info("安装 Exe 程序文件释放跳过: target=%s reason=%s", target, reason)
    elif status == "dry-run":
        logger.info(
            "安装 Exe 程序文件释放 dry-run: target=%s files=%s reason=%s",
            target,
            files,
            reason,
        )
    else:
        logger.info(
            "安装 Exe 程序文件释放结果: status=%s target=%s files=%s reason=%s",
            status,
            target,
            files,
            reason,
        )


def _load_release_exe_to_desktop() -> Any:
    """Lazily load Exe release support only when explicitly requested."""

    entrypoint_dir = _release_entrypoint_dir()
    installer_dir = entrypoint_dir / "installer"
    release_module = installer_dir / "exe_release.py"
    if not installer_dir.is_dir() or not release_module.is_file():
        # Dry-run mode: return a stub function when exe_release.py is missing
        def _dry_run_release_stub(
            exe_path: Any,
            desktop_dir: Any = None,
            target_filename: Any = None,
            overwrite: bool = False,
            dry_run: bool = False,
        ) -> dict[str, Any]:
            return {
                "status": "dry-run",
                "exe_path": str(exe_path),
                "desktop_dir": str(desktop_dir) if desktop_dir else None,
                "target_filename": target_filename,
                "message": "dry-run: installer/exe_release.py 不可用，仅模拟释放",
            }

        return _dry_run_release_stub

    try:
        return _load_release_function_from_path(
            release_module, "release_exe_to_desktop"
        )
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "installer.exe_release"
        raise SystemExit(
            "error: 桌面 Exe 释放功能不可用: release package is incomplete "
            f"(missing Python module: {missing_module}). "
            "请重新下载完整发布包，或从包含 installer/ 目录的完整源码/发布目录运行。"
        ) from None


def _load_release_payload_to_directory() -> Any:
    """Lazily load shared release payload extraction support."""

    entrypoint_dir = _release_entrypoint_dir()
    bundled = getattr(sys, "_MEIPASS", None)
    bundled_payload = Path(bundled) / "release_payload" if bundled else None
    release_module = entrypoint_dir / "installer" / "exe_release.py"
    if not bundled and not release_module.is_file():
        raise SystemExit(
            "error: 安装 Exe 释放功能不可用: requires installer/exe_release.py or a bundled release payload. "
            "请重新下载完整发布包，或运行 CI 生成的 SuperMedicineInstaller.exe。"
        ) from None

    try:
        if bundled_payload is not None:
            bundled_module = bundled_payload / "installer" / "exe_release.py"
            if bundled_module.is_file():
                return _load_release_function_from_path(
                    bundled_module, "release_payload_to_directory"
                )
        return _load_release_function_from_path(
            release_module, "release_payload_to_directory"
        )
    except ModuleNotFoundError as exc:
        missing_module = exc.name or "installer.exe_release"
        raise SystemExit(
            "error: 安装 Exe 释放功能不可用: release package is incomplete "
            f"(missing Python module: {missing_module}). "
            "请重新下载完整发布包，或运行 CI 生成的 SuperMedicineInstaller.exe。"
        ) from None


def _release_entrypoint_dir() -> Path:
    """Return the release root for optional Exe helpers without falling through to unrelated packages."""

    script_path = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else None
    if script_path is not None and script_path.name.lower() in {
        "install_entry.py",
        "install.py",
        "supermedicineinstaller.exe",
    }:
        return script_path.parent
    return Path(__file__).resolve().parents[1]


def _load_release_function_from_path(release_module: Path, function_name: str) -> Any:
    """Load an optional release helper from an exact local file path."""

    spec = importlib.util.spec_from_file_location(
        "_supermedicine_installer_exe_release", release_module
    )
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError("installer.exe_release")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, function_name)


def _release_exe_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Release the requested Exe and convert copy failures into CLI errors."""

    try:
        release_exe_to_desktop = _load_release_exe_to_desktop()
        result = release_exe_to_desktop(
            exe_path=args.release_exe,
            desktop_dir=args.desktop_dir,
            target_filename=args.exe_target_name,
            overwrite=args.exe_overwrite,
            dry_run=args.exe_dry_run,
        )
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("桌面 Exe 释放失败: %s", redact_sensitive(str(exc)))
        raise SystemExit(
            f"error: 桌面 Exe 释放失败: {redact_sensitive(str(exc))}"
        ) from exc
    _log_exe_release_result(result)
    return result


def _extract_release_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Extract bundled/unified release payload and convert failures into CLI errors."""

    try:
        release_payload_to_directory = _load_release_payload_to_directory()
        result = release_payload_to_directory(
            target_dir=args.extract_release_to,
            source_root=args.release_payload_root,
            overwrite=args.extract_overwrite,
            dry_run=args.exe_dry_run,
        )
    except SystemExit:
        raise
    except Exception as exc:
        logger.error("安装 Exe 程序文件释放失败: %s", redact_sensitive(str(exc)))
        raise SystemExit(
            f"error: 安装 Exe 程序文件释放失败: {redact_sensitive(str(exc))}"
        ) from exc
    _log_payload_release_result(result)
    return result


def _resolve_project_dir(args: argparse.Namespace) -> Path:
    """Return where installer configuration should be written."""

    project_dir = getattr(args, "project_dir", None)
    if project_dir:
        return Path(project_dir).expanduser().resolve()
    extract_release_to = getattr(args, "extract_release_to", None)
    if extract_release_to:
        return Path(extract_release_to).expanduser().resolve()
    return Path.cwd()


def _align_release_exe_with_extracted_payload(args: argparse.Namespace) -> None:
    """Prefer the freshly extracted application Exe for combined installs."""

    if not getattr(args, "release_exe", None) or not getattr(
        args, "extract_release_to", None
    ):
        return
    release_exe = Path(args.release_exe)
    if release_exe.is_absolute() or release_exe.exists():
        return
    extracted_candidate = Path(args.extract_release_to).expanduser() / release_exe
    if extracted_candidate.exists():
        args.release_exe = extracted_candidate


def _resolve_desktop_collision_args(
    args: argparse.Namespace,
) -> tuple[Path | None, str | None]:
    if not getattr(args, "release_exe", None):
        return None, None
    desktop_dir = getattr(args, "desktop_dir", None)
    if desktop_dir is None:
        return Path.home() / "Desktop", getattr(args, "exe_target_name", None)
    return Path(desktop_dir).expanduser(), getattr(args, "exe_target_name", None)


def _uninstall_existing_install(
    project_dir: Path, *, preserve_user_data: bool
) -> dict[str, Any]:
    project_dir = Path(project_dir).expanduser().resolve()
    preserved_config_backup: Path | None = None
    preserved_tempdir: tempfile.TemporaryDirectory[str] | None = None
    config_dir = project_dir / ".supermedicine"
    if preserve_user_data and config_dir.exists():
        preserved_tempdir = tempfile.TemporaryDirectory(
            prefix="supermedicine-preserve-"
        )
        preserved_config_backup = Path(preserved_tempdir.name) / ".supermedicine"
        shutil.copytree(config_dir, preserved_config_backup)
    try:
        from uninstall_entry import uninstall
    except ImportError as exc:
        raise SystemExit(f"error: 卸载旧版本失败: uninstall_entry.py 不可用 ({exc})") from exc
    try:
        result = uninstall(
            project_dir, force=True, preserve_user_data=preserve_user_data
        )
        if (
            preserved_config_backup is not None
            and preserved_config_backup.exists()
            and not config_dir.exists()
        ):
            shutil.copytree(preserved_config_backup, config_dir)
        if str(result.get("status", "")).startswith("removed-with-residuals"):
            logger.warning("旧版本卸载存在残留，请查看上方 repair_suggestions。")
        elif result.get("status") not in {"removed", "dry-run"}:
            raise SystemExit(f"error: 卸载旧版本未完成: {result.get('status')}")
        return result
    finally:
        if preserved_tempdir is not None:
            preserved_tempdir.cleanup()


def _refresh_existing_project_config(project_dir: Path) -> None:
    """Refresh installer-owned metadata around an existing config without rewriting secrets."""

    project_dir = Path(project_dir).expanduser().resolve()
    config_dir = project_dir / ".supermedicine"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "agents").mkdir(exist_ok=True)
    (config_dir / "plugins").mkdir(exist_ok=True)
    ensure_default_policy(project_dir, Path(__file__).resolve().parents[1])


def _enforce_existing_install_policy(
    args: argparse.Namespace, detection: ExistingInstallDetection
) -> str:
    if not detection.installed:
        return "ignore"
    action = getattr(args, "if_installed", None)
    if action is None:
        raise SystemExit(
            "error: 检测到已有 SuperMedicine 安装；脚本模式请显式传入 "
            "--if-installed update|uninstall|fail|ignore"
        )
    if action == "fail":
        raise SystemExit(
            "error: 检测到已有 SuperMedicine 安装，按 --if-installed fail 退出"
        )
    if action == "ignore":
        return action
    if action == "uninstall":
        if getattr(args, "preserve_user_data", False) == getattr(
            args, "remove_user_data", False
        ):
            raise SystemExit(
                "error: --if-installed uninstall 需要显式选择 --preserve-user-data 或 --remove-user-data"
            )
        _uninstall_existing_install(
            detection.project_dir, preserve_user_data=bool(args.preserve_user_data)
        )
        return action
    if action == "update":
        args.extract_overwrite = True
        args.exe_overwrite = True
        return action
    raise SystemExit(f"error: unknown --if-installed action: {action}")


def _install_record_artifacts_from_results(
    *,
    payload_result: dict[str, Any] | None = None,
    exe_result: dict[str, Any] | None = None,
    selected_components: list[str] | None = None,
) -> dict[str, Any]:
    artifacts: dict[str, Any] = {
        "created_paths": [".supermedicine"],
        "config_dirs": [".supermedicine"],
        "user_data_paths": [".supermedicine"],
    }
    if payload_result and payload_result.get("status") in {"copied", "dry-run"}:
        artifacts["payload_dir"] = payload_result.get("target_dir")
    if exe_result and exe_result.get("target_path"):
        artifacts["binaries"] = [exe_result.get("target_path")]
    if selected_components:
        artifacts["installed_components"] = list(selected_components)
    return artifacts


def main(argv: list[str] | None = None) -> None:
    _configure_stdio_errors()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="SuperMedicine 安装器：初始化配置、释放程序文件、复制桌面 Exe。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "常用示例:\n"
            "  python install_entry.py\n"
            "  python install_entry.py --init --interactive\n"
            "  统一安装示例:\n"
            "  python install_entry.py --unified-install --release-exe dist/SuperMedicine.exe --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini\n"
            "  SuperMedicineInstaller.exe --extract-release-to C:\\SuperMedicine --init --project-dir C:\\SuperMedicine ...\n\n"
            "说明:\n"
            "  --init 默认只初始化配置；只有显式 --release-exe 才复制桌面 Exe。\n"
            "  --release-exe 默认查找 dist/SuperMedicine.exe，并兼容 Dist/SuperMedicine.exe 或根目录 SuperMedicine.exe。\n"
            "  测试/CI 请使用 --desktop-dir <tmp> 或 --exe-dry-run，避免写入真实桌面。"
        ),
    )
    parser.add_argument(
        "--detect", action="store_true", help="检测可选 OpenCode/Claude Code 适配器"
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="初始化 .supermedicine 配置；脚本模式需提供完整 LLM 配置",
    )
    parser.add_argument(
        "--unified-install",
        action="store_true",
        help="初始化配置并复制桌面 Exe；必须同时提供 --release-exe",
    )
    parser.add_argument(
        "--provider",
        help="LLM provider 名称，如 openai、anthropic、deepseek 或自定义兼容网关",
    )
    parser.add_argument("--base-url", help="LLM Base URL；也可用 SM_LLM_BASE_URL")
    parser.add_argument(
        "--api-key", help="LLM API key；也可用 SM_LLM_API_KEY 或 provider 专用环境变量"
    )
    parser.add_argument("--model", help="默认 LLM model；也可用 SM_LLM_MODEL")
    parser.add_argument(
        "--llm-config",
        type=Path,
        help="读取包含 llm.provider / llm.providers 的 YAML 配置",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="在初始化时交互填写 LLM 配置"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        help=".supermedicine 初始化目录；默认使用 --extract-release-to 或当前目录",
    )
    parser.add_argument(
        "--release-exe",
        type=Path,
        nargs="?",
        const=Path("dist") / "SuperMedicine.exe",
        help="复制指定 Exe 到桌面；不带值时默认 dist/SuperMedicine.exe，并兼容 Dist/ 或根目录 Exe",
    )
    parser.add_argument(
        "--desktop-dir", type=Path, help="指定桌面目录；测试/CI 用于避免真实桌面"
    )
    parser.add_argument(
        "--exe-target-name", help="桌面 Exe 文件名；默认使用源文件名并规范为 .exe"
    )
    parser.add_argument(
        "--exe-overwrite", action="store_true", help="覆盖已存在的桌面 Exe；默认跳过"
    )
    parser.add_argument(
        "--exe-dry-run",
        action="store_true",
        help="仅显示将执行的 Exe 释放动作，不复制文件",
    )
    parser.add_argument(
        "--extract-release-to",
        type=Path,
        help="释放完整发布 payload 到目录；供独立安装 Exe 使用",
    )
    parser.add_argument(
        "--release-payload-root",
        type=Path,
        help="指定发布 payload 来源；默认使用 PyInstaller 内置 payload 或当前发布根目录",
    )
    parser.add_argument(
        "--extract-overwrite", action="store_true", help="释放 payload 时覆盖已有文件"
    )
    parser.add_argument(
        "--if-installed",
        choices=("update", "uninstall", "fail", "ignore"),
        help="脚本模式检测到已有安装时的处理: update 覆盖安装器拥有的产物并保留用户数据；uninstall 先卸载；fail 安全退出；ignore 跳过检测保护",
    )
    parser.add_argument(
        "--preserve-user-data",
        action="store_true",
        help="配合 --if-installed uninstall 使用：卸载旧版本时保留用户数据",
    )
    parser.add_argument(
        "--remove-user-data",
        action="store_true",
        help="配合 --if-installed uninstall 使用：卸载旧版本时删除记录的用户数据",
    )
    args = parser.parse_args(argv)
    if args.preserve_user_data and args.remove_user_data:
        parser.error(
            "--preserve-user-data and --remove-user-data are mutually exclusive"
        )
    if not (argv if argv is not None else sys.argv[1:]):
        _run_interactive_installer(args)
        return
    run_init = args.init or args.unified_install
    if args.unified_install and not args.release_exe:
        parser.error(
            "--unified-install requires --release-exe <path-to-SuperMedicine.exe>"
        )
    if args.detect:
        logger.info("Detected platform: %s", detect_platform())
        return
    scripted_project_dir = _resolve_project_dir(args)
    desktop_dir, exe_target_name = _resolve_desktop_collision_args(args)
    detection = detect_existing_install(
        scripted_project_dir,
        desktop_dir=desktop_dir,
        exe_target_name=exe_target_name,
        include_project=bool(run_init or args.extract_release_to),
        include_payload=bool(args.extract_release_to),
    )
    install_policy_action = "ignore"
    if run_init or args.extract_release_to or args.release_exe:
        install_policy_action = _enforce_existing_install_policy(args, detection)
    payload_result: dict[str, Any] | None = None
    exe_result: dict[str, Any] | None = None
    if args.extract_release_to:
        payload_result = _extract_release_from_args(args)
        _align_release_exe_with_extracted_payload(args)
        if not run_init and not args.release_exe:
            if payload_result.get("status") != "dry-run":
                write_install_record(
                    scripted_project_dir,
                    artifacts=_install_record_artifacts_from_results(
                        payload_result=payload_result
                    ),
                    mode="update" if install_policy_action == "update" else "init",
                )
            return
    if run_init:
        imported_config = (
            _load_llm_config_file(args.llm_config) if args.llm_config else {}
        )
        provider = _resolve_install_value("provider", args.provider) or cast(
            str | None, imported_config.get("provider")
        )
        base_url = _resolve_install_value("base_url", args.base_url) or cast(
            str | None, imported_config.get("base_url")
        )
        model = _resolve_install_value("model", args.model) or cast(
            str | None, imported_config.get("model")
        )
        normalized_provider = _normalize_provider(provider)
        api_key = _resolve_api_key(normalized_provider, args.api_key) or cast(
            str | None, imported_config.get("api_key")
        )
        if args.interactive:
            prompted_config = _collect_interactive_llm_config(
                provider=normalized_provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )
            normalized_provider = cast(str | None, prompted_config.get("provider"))
            base_url = cast(str | None, prompted_config.get("base_url"))
            model = cast(str | None, prompted_config.get("model"))
            api_key = cast(str | None, prompted_config.get("api_key"))
        if (
            install_policy_action == "update"
            and (scripted_project_dir / CONFIG_RELATIVE).is_file()
        ):
            _refresh_existing_project_config(scripted_project_dir)
        else:
            init_config(
                scripted_project_dir,
                provider=normalized_provider,
                base_url=base_url,
                api_key=api_key,
                model=model,
            )
        logger.info(
            "安装初始化结果: .supermedicine=%s",
            scripted_project_dir / ".supermedicine",
        )
        if args.release_exe:
            exe_result = _release_exe_from_args(args)
        write_install_record(
            scripted_project_dir,
            artifacts=_install_record_artifacts_from_results(
                payload_result=payload_result, exe_result=exe_result
            ),
            mode="update" if install_policy_action == "update" else "init",
        )
        return
    if args.release_exe:
        exe_result = _release_exe_from_args(args)
        if exe_result.get("status") != "dry-run":
            write_install_record(
                scripted_project_dir,
                artifacts=_install_record_artifacts_from_results(exe_result=exe_result),
                mode="update" if install_policy_action == "update" else "init",
            )
        return
    parser.print_help()


__all__ = [
    "DEFAULT_CONFIG",
    "INSTALL_ENV_NAMES",
    "PROVIDER_ENV_NAMES",
    "ExistingInstallDetection",
    "ExistingInstallEvidence",
    "detect_platform",
    "detect_existing_install",
    "init_config",
    "main",
    "write_install_record",
    "write_llm_config",
    "_normalize_provider",
    "_resolve_api_key",
    "_resolve_install_value",
]

if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
