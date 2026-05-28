"""Shared sensitive-value redaction utilities."""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|credential)\s*[:=]\s*([^\s,;&]+)"),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+\-/=]+)"),
)


def redact_sensitive(value: Any) -> Any:
    """Recursively redact sensitive values from dicts/lists/strings."""
    if isinstance(value, dict):
        safe: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text.endswith("_env"):
                safe[key] = item
            elif any(
                marker in key_text
                for marker in (
                    "api_key",
                    "apikey",
                    "token",
                    "secret",
                    "password",
                    "credential",
                )
            ):
                safe[key] = "[REDACTED]" if item not in (None, "") else item
            else:
                safe[key] = redact_sensitive(item)
        return safe
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        text = value
        text = _SENSITIVE_VALUE_PATTERNS[0].sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
        text = _SENSITIVE_VALUE_PATTERNS[1].sub(lambda match: f"{match.group(1)}[REDACTED]", text)
        return text
    return value
