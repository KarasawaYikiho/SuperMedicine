"""Shared sensitive-value redaction utilities.

The redaction layer is intentionally conservative for anything that may be
written to logs, audit trails, CLI output, TUI sinks, or persisted diagnostic
documents.  Callers pass structured data or text through ``redact_sensitive``;
the returned copy replaces secret-looking material with a fixed placeholder and
never stores the original sensitive value in the redacted object.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTION_PLACEHOLDER = "[REDACTED]"

_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "api-key",
    "apikey",
    "x-api-key",
    "access_key",
    "access-key",
    "accesskey",
    "access_token",
    "access-token",
    "auth_token",
    "auth-token",
    "refresh_token",
    "refresh-token",
    "id_token",
    "id-token",
    "token",
    "secret",
    "client_secret",
    "client-secret",
    "password",
    "passwd",
    "pwd",
    "credential",
    "credentials",
    "auth",
    "authorization",
    "cookie",
    "set-cookie",
    "private_key",
    "private-key",
    "privatekey",
    "ssh_key",
    "ssh-key",
    "session_key",
    "session-key",
    "signature",
    "sas",
)

_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "key",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "auth_token",
        "auth",
        "authorization",
        "password",
        "passwd",
        "pwd",
        "secret",
        "client_secret",
        "credential",
        "credentials",
        "cookie",
        "signature",
        "sig",
        "x-amz-signature",
        "x-amz-credential",
        "x-amz-security-token",
        "x-goog-signature",
        "x-goog-credential",
        "code",
        "sas",
        "sp",
        "se",
        "sr",
    }
)

_SENSITIVE_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?i)([\"'](?:api[_-]?key|x-api-key|access[_-]?key|access[_-]?token|auth[_-]?token|auth|refresh[_-]?token|id[_-]?token|token|secret|client[_-]?secret|password|passwd|pwd|credential|credentials|authorization|cookie|set-cookie|private[_-]?key|ssh[_-]?key|session[_-]?key|signature|sig|sas)[\"']\s*:\s*[\"'])([^\"']*)([\"'])"
    ),
    re.compile(
        r"(?i)(api[_-]?key|x-api-key|access[_-]?key|access[_-]?token|auth[_-]?token|auth|refresh[_-]?token|id[_-]?token|token|secret|client[_-]?secret|password|passwd|pwd|credential|credentials|authorization|cookie|set-cookie|private[_-]?key|ssh[_-]?key|session[_-]?key|signature|sig|sas)\s*[:=]\s*([^\s,;&\"'{}\[\]]+)"
    ),
    re.compile(
        r"(?i)([?&](?:api[_-]?key|apikey|key|access[_-]?token|auth[_-]?token|auth|refresh[_-]?token|id[_-]?token|token|secret|client[_-]?secret|password|passwd|pwd|credential|credentials|authorization|cookie|signature|sig|x-amz-signature|x-amz-credential|x-amz-security-token|x-goog-signature|x-goog-credential|code|sas|sp|se|sr)=)([^\s&#\"']+)"
    ),
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~+\-/=]+)"),
    re.compile(r"(?i)(basic\s+)([A-Za-z0-9+/=]{8,})"),
    re.compile(r"\b(sk-[A-Za-z0-9][A-Za-z0-9._\-]{8,})\b"),
    re.compile(
        r"\b(ghp_[A-Za-z0-9_]{12,}|gho_[A-Za-z0-9_]{12,}|glpat-[A-Za-z0-9_\-]{12,}|xox[baprs]-[A-Za-z0-9\-]{12,})\b"
    ),
    re.compile(r"\b(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16})\b"),
    re.compile(r"\b(ya29\.[A-Za-z0-9_\-]+)\b"),
    re.compile(r"\b(SG\.[A-Za-z0-9_\-]{12,}\.[A-Za-z0-9_\-]{12,})\b"),
    re.compile(
        r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----.*?-----END (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
        re.IGNORECASE | re.DOTALL,
    ),
)


def _is_sensitive_key(key: Any) -> bool:
    key_text = str(key).lower().strip()
    if key_text.endswith("_env"):
        return False
    normalized = re.sub(r"[\s.-]+", "_", key_text)
    if normalized == "auth":
        return True
    return any(
        marker in key_text or marker in normalized
        for marker in _SENSITIVE_KEY_MARKERS
        if marker != "auth"
    )


def _redacted_or_empty(value: Any) -> Any:
    return value if value in (None, "") else REDACTION_PLACEHOLDER


def _redact_url_query(text: str) -> str:
    """Redact sensitive URL query parameters while preserving non-secret parts."""

    if re.search(r"\s", text):
        return text
    try:
        parts = urlsplit(text)
    except ValueError:
        return text
    if not parts.query:
        return text
    try:
        query_items = parse_qsl(parts.query, keep_blank_values=True)
    except ValueError:
        return text
    if not query_items:
        return text
    redacted_items = [
        (
            key,
            REDACTION_PLACEHOLDER
            if key.lower() in _SENSITIVE_QUERY_KEYS and value
            else value,
        )
        for key, value in query_items
    ]
    return urlunsplit(parts._replace(query=urlencode(redacted_items, doseq=True)))


def redact_sensitive(value: Any) -> Any:
    """Recursively redact sensitive values from dicts/lists/strings."""
    if isinstance(value, dict):
        safe: dict[Any, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(key):
                safe[key] = _redacted_or_empty(item)
            else:
                safe[key] = redact_sensitive(item)
        return safe
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    if isinstance(value, str):
        text = value
        text = _redact_url_query(text)
        text = _SENSITIVE_VALUE_PATTERNS[-1].sub(REDACTION_PLACEHOLDER, text)
        text = _SENSITIVE_VALUE_PATTERNS[3].sub(
            lambda match: f"{match.group(1)}{REDACTION_PLACEHOLDER}", text
        )
        text = _SENSITIVE_VALUE_PATTERNS[4].sub(
            lambda match: f"{match.group(1)}{REDACTION_PLACEHOLDER}", text
        )
        text = _SENSITIVE_VALUE_PATTERNS[0].sub(
            lambda match: f"{match.group(1)}{REDACTION_PLACEHOLDER}{match.group(3)}",
            text,
        )
        text = _SENSITIVE_VALUE_PATTERNS[1].sub(
            lambda match: f"{match.group(1)}={REDACTION_PLACEHOLDER}", text
        )
        text = _SENSITIVE_VALUE_PATTERNS[2].sub(
            lambda match: f"{match.group(1)}{REDACTION_PLACEHOLDER}", text
        )
        for pattern in _SENSITIVE_VALUE_PATTERNS[5:-1]:
            text = pattern.sub(REDACTION_PLACEHOLDER, text)
        return text
    return value
