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
import getpass
import logging
import os
import shutil
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import yaml

from core.llm_providers.config import LLMProviderConfig
from core.redaction import redact_sensitive
from installer.exe_release import release_exe_to_desktop
from permission.policy import ensure_default_policy

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "supermedicine",
    "version": "Beta0.4.0",
    "llm": {
        "provider": "",
        "providers": {},
    },
}

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


def _default_config_text() -> str:
    header = (
        "# SuperMedicine 配置\n"
        "# LLM provider template. 支持任意 provider 名称。\n"
        "# api_format 决定 HTTP 请求格式: openai (兼容 DeepSeek/智谱/Ollama 等) 或 anthropic\n"
        "# 根据 provider 名称自动推断 api_format，也可手动指定。\n"
    )
    return header + yaml.safe_dump(DEFAULT_CONFIG, sort_keys=False, allow_unicode=True)


def _deep_merge_missing(target: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
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
            "完整 LLM Provider 配置是首次初始化必需项；缺失字段: "
            + ", ".join(missing)
            + "；配置来源优先级: CLI 参数 > SM_LLM_* 环境变量/Provider API key env > --llm-config 文件。请通过 --provider/--base-url/--api-key/--model、"
            "--llm-config、SM_LLM_PROVIDER/SM_LLM_BASE_URL/SM_LLM_API_KEY/SM_LLM_MODEL 环境变量或 --interactive 提供: "
            + ", ".join(missing)
        )
    _validate_install_llm_config(
        provider=normalized_provider or "",
        base_url=base_url or "",
        api_key=api_key or "",
        model=model or "",
    )
    return normalized_provider or ""


def _validate_install_llm_config(*, provider: str, base_url: str, api_key: str, model: str) -> None:
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
        raise ValueError(f"LLM Provider base_url 必须是有效的 http(s) URL；provider={provider} base_url={base_url}")


def _redact(value: str | None) -> str:
    return "<redacted>" if value else ""


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


def _prompt_value(prompt: str, default: str | None = None, *, secret: bool = False) -> str | None:
    suffix = f" [{default}]" if default and not secret else ""
    if secret:
        value = getpass.getpass(f"{prompt}: ").strip()
    else:
        value = input(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    return default


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

    provider = _normalize_provider(_optional_string(llm.get("provider") or loaded.get("provider")))
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
    logger.info("Install stage=llm-config-write project_dir=%s provider=%s", project_dir, provider or "")
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
        write_llm_config(project_dir, provider=normalized_provider, base_url=base_url, api_key=api_key, model=model)
        (config_dir / "agents").mkdir(exist_ok=True)
        (config_dir / "plugins").mkdir(exist_ok=True)
        ensure_default_policy(project_dir, Path(__file__).parent)
    except Exception as exc:
        _restore_install_state(config_dir, backup_dir)
        logger.error("初始化失败，已回滚安装状态。stage=init error=%s", redact_sensitive(str(exc)))
        raise
    if backup_dir is not None and backup_dir.exists():
        shutil.rmtree(backup_dir)
    logger.info("初始化完成。")
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
        logger.info("桌面 Exe 释放结果: status=%s target=%s reason=%s", status, target, reason)


def _release_exe_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """Release the requested Exe and convert copy failures into CLI errors."""

    try:
        result = release_exe_to_desktop(
            exe_path=args.release_exe,
            desktop_dir=args.desktop_dir,
            target_filename=args.exe_target_name,
            overwrite=args.exe_overwrite,
            dry_run=args.exe_dry_run,
        )
    except Exception as exc:
        logger.error("桌面 Exe 释放失败: %s", redact_sensitive(str(exc)))
        raise SystemExit(f"error: 桌面 Exe 释放失败: {redact_sensitive(str(exc))}") from exc
    _log_exe_release_result(result)
    return result

def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(
        description="SuperMedicine standalone/unified installer",
        epilog=(
            "统一安装示例: python Install.py --unified-install --release-exe dist/SuperMedicine.exe "
            "--provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini. "
            "--init 默认不复制 Exe；只有显式 --release-exe 才释放桌面 Exe。"
            "测试/CI 请配合 --desktop-dir <tmp> 或 --exe-dry-run，避免写入真实桌面。"
        ),
    )
    parser.add_argument("--detect", action="store_true", help="Optionally detect OpenCode/Claude Code add-on presence")
    parser.add_argument("--init", action="store_true", help="Initialize core SuperMedicine config only; does not release Exe unless --release-exe is also provided")
    parser.add_argument(
        "--unified-install",
        action="store_true",
        help="Run initialization plus desktop Exe release; requires --release-exe and keeps --init semantics explicit",
    )
    parser.add_argument(
        "--provider",
        help="LLM provider to configure (e.g. openai, anthropic, deepseek, or any custom OpenAI-compatible provider)",
    )
    parser.add_argument("--base-url", help="LLM provider BaseURL; may also use SM_LLM_BASE_URL")
    parser.add_argument("--api-key", help="LLM provider API key; may also use SM_LLM_API_KEY or provider env var")
    parser.add_argument("--model", help="Default LLM model; may also use SM_LLM_MODEL")
    parser.add_argument("--llm-config", type=Path, help="YAML file containing llm.provider and llm.providers.<provider> settings")
    parser.add_argument("--interactive", action="store_true", help="Prompt for LLM provider settings during initialization")
    parser.add_argument("--release-exe", type=Path, help="Release this Exe to the desktop after installer work completes; can be used alone, with --init, or with --unified-install")
    parser.add_argument("--desktop-dir", type=Path, help="Desktop directory override for Exe release; use in tests/CI to avoid the real user Desktop")
    parser.add_argument("--exe-target-name", help="Desktop filename for released Exe; defaults to the source filename and is normalized to .exe")
    parser.add_argument("--exe-overwrite", action="store_true", help="Overwrite an existing desktop Exe target; default behavior skips existing target")
    parser.add_argument("--exe-dry-run", action="store_true", help="Report Exe release action without copying")
    args = parser.parse_args(argv)
    run_init = args.init or args.unified_install
    if args.unified_install and not args.release_exe:
        parser.error("--unified-install requires --release-exe <path-to-SuperMedicine.exe>")
    if args.detect:
        logger.info("Detected platform: %s", detect_platform())
        return
    if run_init:
        imported_config = _load_llm_config_file(args.llm_config) if args.llm_config else {}
        provider = _resolve_install_value("provider", args.provider) or cast(str | None, imported_config.get("provider"))
        base_url = _resolve_install_value("base_url", args.base_url) or cast(str | None, imported_config.get("base_url"))
        model = _resolve_install_value("model", args.model) or cast(str | None, imported_config.get("model"))
        normalized_provider = _normalize_provider(provider)
        api_key = _resolve_api_key(normalized_provider, args.api_key) or cast(str | None, imported_config.get("api_key"))
        if args.interactive:
            normalized_provider = _normalize_provider(
                _prompt_value("LLM provider", normalized_provider or "openai")
            )
            if normalized_provider is None:
                raise ValueError("provider is required")
            base_url = _prompt_value("BaseURL", base_url)
            model = _prompt_value("Default model", model)
            api_key = _prompt_value("API key", api_key, secret=True)
        init_config(
            Path.cwd(),
            provider=normalized_provider,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )
        logger.info("安装初始化结果: .supermedicine=%s", Path.cwd() / ".supermedicine")
        if args.release_exe:
            _release_exe_from_args(args)
        return
    if args.release_exe:
        _release_exe_from_args(args)
        return
    parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
