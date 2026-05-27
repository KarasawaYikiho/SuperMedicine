"""Shared UTC timestamp utilities."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> str:
    """Return current UTC time as ISO 8601 string without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_now_datetime() -> datetime:
    """Return current UTC time as datetime object without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0)
