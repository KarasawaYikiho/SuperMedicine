"""CLI commands: LLM provider management."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.helpers import _llm_provider_values
from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def llm_add(
    cli,
    provider: str,
    *,
    api_format: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    headers: dict | None = None,
    set_current: bool = False,
) -> dict:
    """Add or update an LLM provider through the shared manager."""
    from core.config_center import ConfigCenter
    from core.llm_manager import LLMConfigManager

    values = _llm_provider_values(
        api_format=api_format,
        base_url=base_url,
        api_key=api_key,
        api_key_env=api_key_env,
        model=model,
        timeout=timeout,
        headers=headers,
    )
    manager = LLMConfigManager(
        ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
        restore_on_startup=False,
    )
    result = manager.add_provider(provider, values, set_current=set_current)
    _log_json(result)
    return result


def llm_list(cli) -> dict:
    """List configured LLM providers with secret-safe output."""
    from core.config_center import ConfigCenter
    from core.llm_manager import LLMConfigManager

    manager = LLMConfigManager(
        ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
        restore_on_startup=False,
    )
    config = manager._config
    result = {
        "current_provider": config.get_llm_current_provider_name(),
        "last_provider": config.get_llm_last_provider_name(),
        "providers": manager.list_providers(redacted=True),
    }
    _log_json(result)
    return result


def llm_show(cli, provider: str | None = None) -> dict:
    """Show one LLM provider, defaulting to the current provider, redacted."""
    from core.config_center import ConfigCenter
    from core.llm_manager import LLMConfigManager

    manager = LLMConfigManager(
        ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
        restore_on_startup=True,
    )
    result = (
        manager.get_provider(provider, redacted=True)
        if provider
        else manager.get_current_provider(redacted=True)
    )
    _log_json(result)
    return result


def llm_switch(cli, provider: str) -> dict:
    """Persistently switch the current LLM provider."""
    from core.config_center import ConfigCenter
    from core.llm_manager import LLMConfigManager

    manager = LLMConfigManager(
        ConfigCenter(Path.cwd() / ".supermedicine" / "config.yaml"),
        restore_on_startup=False,
    )
    result = manager.switch_provider(provider, save=True)
    _log_json(result)
    return result
