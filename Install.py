#!/usr/bin/env python3
"""SuperMedicine standalone installer.

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
from pathlib import Path
from typing import Any, cast

import yaml

from permission.policy import ensure_default_policy

logger = logging.getLogger(__name__)

SUPPORTED_LLM_PROVIDERS = {"openai", "anthropic"}

DEFAULT_CONFIG: dict[str, Any] = {
    "project_name": "supermedicine",
    "version": "Beta0.3.0",
    "llm": {
        "provider": "openai",
        "providers": {
            "openai": {
                "api_format": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key_env": "OPENAI_API_KEY",
                "model": "gpt-4o-mini",
                "timeout": 60,
                "headers": {},
            },
            "anthropic": {
                "api_format": "anthropic",
                "base_url": "https://api.anthropic.com/v1",
                "api_key_env": "ANTHROPIC_API_KEY",
                "model": "claude-3-5-sonnet-latest",
                "timeout": 60,
                "headers": {},
            },
        },
    },
}

PROVIDER_ENV_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

INSTALL_ENV_NAMES = {
    "provider": "SM_LLM_PROVIDER",
    "base_url": "SM_LLM_BASE_URL",
    "api_key": "SM_LLM_API_KEY",
    "model": "SM_LLM_MODEL",
}


def _default_config_text() -> str:
    header = (
        "# SuperMedicine 配置\n"
        "# LLM provider defaults. API keys may be injected into this local project\n"
        "# file by Install.py or loaded from environment variables. Do not commit\n"
        "# real secrets from local workspaces.\n"
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
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError("provider must be one of: openai, anthropic")
    return normalized


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
        return os.environ.get(PROVIDER_ENV_NAMES[provider])
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

    provider_config.setdefault("api_format", provider)
    provider_config.setdefault("api_key_env", PROVIDER_ENV_NAMES[provider])
    if base_url:
        provider_config["base_url"] = base_url
    if model:
        provider_config["model"] = model
    if api_key:
        provider_config["api_key"] = api_key
        provider_config["api_key_env"] = PROVIDER_ENV_NAMES[provider]
    llm["provider"] = provider


def write_llm_config(
    project_dir: Path,
    *,
    provider: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    normalized_provider = _normalize_provider(provider)
    if normalized_provider is None:
        return
    config_file = project_dir / ".supermedicine" / "config.yaml"
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
    normalized_provider = _normalize_provider(provider)
    config_dir = project_dir / ".supermedicine"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"
    if not config_file.exists():
        config_file.write_text(_default_config_text(), encoding="utf-8")
    if normalized_provider is not None:
        write_llm_config(project_dir, provider=normalized_provider, base_url=base_url, api_key=api_key, model=model)
    (config_dir / "agents").mkdir(exist_ok=True)
    (config_dir / "plugins").mkdir(exist_ok=True)
    ensure_default_policy(project_dir, Path(__file__).parent)
    logger.info("初始化完成。")
    logger.info("")
    logger.info("如果 'supermedicine' 命令不可用，请将以下目录添加到系统 PATH：")
    logger.info("  Windows:  %APPDATA%\\Python\\Python<版本>\\Scripts")
    logger.info("  Linux/macOS: ~/.local/bin")
    logger.info("或者使用 'python Cli.py' 代替 'supermedicine' 命令。")

def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description="SuperMedicine standalone installer")
    parser.add_argument("--detect", action="store_true", help="Optionally detect OpenCode/Claude Code add-on presence")
    parser.add_argument("--init", action="store_true", help="Initialize core SuperMedicine config only")
    parser.add_argument(
        "--provider",
        choices=sorted(SUPPORTED_LLM_PROVIDERS),
        help="LLM provider to configure: openai or anthropic",
    )
    parser.add_argument("--base-url", help="LLM provider BaseURL; may also use SM_LLM_BASE_URL")
    parser.add_argument("--api-key", help="LLM provider API key; may also use SM_LLM_API_KEY or provider env var")
    parser.add_argument("--model", help="Default LLM model; may also use SM_LLM_MODEL")
    parser.add_argument("--interactive", action="store_true", help="Prompt for LLM provider settings during initialization")
    args = parser.parse_args()
    if args.detect:
        logger.info("Detected platform: %s", detect_platform())
        return
    if args.init:
        provider = _resolve_install_value("provider", args.provider)
        base_url = _resolve_install_value("base_url", args.base_url)
        model = _resolve_install_value("model", args.model)
        normalized_provider = _normalize_provider(provider)
        api_key = _resolve_api_key(normalized_provider, args.api_key)
        if args.interactive:
            normalized_provider = _normalize_provider(
                _prompt_value("LLM provider (openai/anthropic)", normalized_provider or "openai")
            )
            if normalized_provider is None:
                raise ValueError("provider must be one of: openai, anthropic")
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
        return
    parser.print_help()

if __name__ == "__main__":
    main()
