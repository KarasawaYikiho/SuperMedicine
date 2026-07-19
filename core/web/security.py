"""Security primitives shared by Web server entry points."""

from __future__ import annotations

import hmac
import ipaddress
import re
from pathlib import Path

from core.web.errors import APIError


_ARTIFACT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_MIN_TOKEN_BYTES = 32


def is_loopback_host(host: str) -> bool:
    """Return whether a bind host is explicitly confined to loopback."""
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def load_remote_auth_token(
    host: str, token_file: str | Path | None
) -> str | None:
    """Load startup authentication state, failing closed for remote binds."""
    if token_file is None:
        if is_loopback_host(host):
            return None
        raise ValueError("Non-loopback Web binding requires --auth-token-file")

    path = Path(token_file)
    try:
        token = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Unable to read Web authentication token file: {path}") from exc
    if len(token.encode("utf-8")) < _MIN_TOKEN_BYTES:
        raise ValueError("Web authentication token must contain at least 32 bytes")
    return token


def verify_bearer_header(header: str | None, expected_token: str) -> bool:
    """Validate one Authorization header using constant-time comparison."""
    if not header:
        return False
    scheme, separator, supplied = header.partition(" ")
    if not separator or scheme.lower() != "bearer" or not supplied:
        return False
    return hmac.compare_digest(
        supplied.encode("utf-8"), expected_token.encode("utf-8")
    )


def verify_token(supplied_token: str, expected_token: str) -> bool:
    """Compare a protocol-level token without leaking timing information."""
    return hmac.compare_digest(
        supplied_token.encode("utf-8"), expected_token.encode("utf-8")
    )


def resolve_artifact_path(root: Path, artifact_id: str) -> Path:
    """Return the JSON path for a safe artifact ID contained by *root*."""
    if (
        not _ARTIFACT_ID.fullmatch(artifact_id)
        or artifact_id in {".", ".."}
        or "/" in artifact_id
        or "\\" in artifact_id
    ):
        raise APIError(400, "invalid_artifact_id", "Invalid artifact ID")

    resolved_root = root.resolve()
    candidate = (resolved_root / f"{artifact_id}.json").resolve()
    if candidate.parent != resolved_root:
        raise APIError(400, "invalid_artifact_id", "Invalid artifact ID")
    return candidate
