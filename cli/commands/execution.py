"""CLI commands for LLM execution configuration."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.logging_setup import _log_json
from core.services import LLMService

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
    values = LLMService.provider_values(
        api_format=api_format,
        base_url=base_url,
        api_key=api_key,
        api_key_env=api_key_env,
        model=model,
        timeout=timeout,
        headers=headers,
    )
    service = LLMService(Path.cwd())
    result = service.legacy_result(
        service.add_provider(provider, values, set_current=set_current)
    )
    _log_json(result)
    return result


def llm_list(cli) -> dict:
    """List configured LLM providers with secret-safe output."""
    service = LLMService(Path.cwd())
    result = service.legacy_result(service.list_providers())
    _log_json(result)
    return result


def llm_show(cli, provider: str | None = None) -> dict:
    """Show one LLM provider, defaulting to the current provider, redacted."""
    service = LLMService(Path.cwd(), restore_on_startup=provider is None)
    result = service.legacy_result(service.show_provider(provider))
    _log_json(result)
    return result


def llm_switch(cli, provider: str) -> dict:
    """Persistently switch the current LLM provider."""
    service = LLMService(Path.cwd())
    result = service.legacy_result(service.switch_provider(provider))
    _log_json(result)
    return result
