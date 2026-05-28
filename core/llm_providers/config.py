"""Unified LLM provider configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, Mapping

from core.redaction import redact_sensitive


_SECRET_KEYS = ("api_key", "authorization", "x-api-key", "key", "token")


def redact_secret(value: Any) -> str:
    """Return a non-reversible placeholder for secret values."""
    if value is None or value == "":
        return ""
    return "<redacted>"


def sanitize_error_message(message: str, secrets: list[str] | tuple[str, ...]) -> str:
    """Remove known raw secret values from an error message."""
    sanitized = redact_sensitive(message)
    for secret in secrets:
        if secret:
            sanitized = sanitized.replace(secret, "<redacted>")
    return sanitized


def sanitized_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return headers with secret-looking values redacted."""
    result: dict[str, Any] = {}
    for key, value in (headers or {}).items():
        lowered = key.lower()
        if any(secret_key in lowered for secret_key in _SECRET_KEYS):
            result[key] = redact_secret(value)
        else:
            result[key] = redact_sensitive(value)
    return result


@dataclass(frozen=True)
class LLMProviderConfig:
    """Provider-neutral configuration for OpenAI and Anthropic API formats."""

    provider: str
    api_format: str
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        provider: str,
        values: Mapping[str, Any] | None = None,
        **overrides: Any,
    ) -> "LLMProviderConfig":
        """Build a normalized config from file/env-injected values and kwargs."""
        raw = dict(values or {})
        raw.update({key: value for key, value in overrides.items() if value is not None})

        normalized_provider = str(raw.get("provider") or provider).lower()
        api_format = str(raw.get("api_format") or raw.get("format") or _default_api_format(normalized_provider)).lower()
        raw_base_url = raw.get("base_url", raw.get("baseURL", None))
        if raw_base_url is None:
            raw_base_url = _default_base_url(normalized_provider)
        base_url = str(raw_base_url).strip()
        raw_model = raw.get("model", None)
        if raw_model is None:
            raw_model = _default_model(normalized_provider)
        model = str(raw_model).strip()

        api_key = raw.get("api_key")
        api_key_env = raw.get("api_key_env") or _default_api_key_env(normalized_provider)
        if not api_key and api_key_env:
            api_key = os.environ.get(str(api_key_env), "")

        timeout_value = raw.get("timeout", 60.0)
        try:
            timeout = float(timeout_value)
        except (TypeError, ValueError):
            timeout = 60.0

        headers = raw.get("headers") or {}
        if not isinstance(headers, Mapping):
            headers = {}

        return cls(
            provider=normalized_provider,
            api_format=api_format,
            base_url=base_url,
            api_key=str(api_key or ""),
            model=model,
            timeout=timeout,
            headers={str(key): str(value) for key, value in headers.items()},
        )

    def validation_error(self) -> dict[str, Any] | None:
        """Return a structured validation error if required fields are missing."""
        if not self.base_url:
            return self.error("missing_base_url", "LLM provider base_url is required")
        if not self.api_key:
            return self.error("missing_api_key", "LLM provider api_key is required")
        if not self.model:
            return self.error("missing_model", "LLM provider model is required")
        return None

    def error(self, code: str, message: str) -> dict[str, Any]:
        """Build a structured, secret-safe error response."""
        return {
            "content": "",
            "model": self.model,
            "usage": {},
            "error": {
                "code": code,
                "message": sanitize_error_message(message, [self.api_key]),
                "provider": self.provider,
            },
        }

    def safe_dict(self) -> dict[str, Any]:
        """Return config suitable for logs/docs/tests without exposing secrets."""
        return {
            "provider": self.provider,
            "api_format": self.api_format,
            "base_url": self.base_url,
            "api_key": redact_secret(self.api_key),
            "model": self.model,
            "timeout": self.timeout,
            "headers": sanitized_headers(self.headers),
        }


def _default_api_format(provider: str) -> str:
    if provider == "anthropic":
        return "anthropic"
    return "openai"


def _default_base_url(provider: str) -> str:
    defaults = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
    }
    return defaults.get(provider, "")


def _default_model(provider: str) -> str:
    defaults = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-latest",
        "openrouter": "anthropic/claude-3.5-sonnet",
    }
    return defaults.get(provider, "")


def _default_api_key_env(provider: str) -> str:
    defaults = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    return defaults.get(provider, "")
