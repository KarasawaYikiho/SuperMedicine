"""Kernel output filtering utilities for the TUI chat display."""

from __future__ import annotations

import re
from typing import Any

from core.redaction import redact_sensitive


_DISPLAY_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd)\s*([:=])\s*([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*\b", re.IGNORECASE),
)


def _redact_display_secrets(value: str) -> str:
    """Redact common secret shapes before handing text to chat rendering."""

    return str(redact_sensitive(value)).replace("[REDACTED]", "[已隐藏]")


_KERNEL_OUTPUT_ASSISTANT_KEYS = (
    "assistant",
    "answer",
    "response",
    "content",
    "message",
    "text",
)
_KERNEL_OUTPUT_INTERNAL_KEYS = {
    "backend_command",
    "debug",
    "debug_event",
    "diagnostic",
    "diagnostics",
    "event",
    "event_type",
    "internal",
    "internal_event",
    "llm_debug",
    "request",
    "request_id",
    "stage",
    "telemetry",
    "transport",
}
_KERNEL_OUTPUT_INTERNAL_COMMAND_KEYS = {"backend_command", "command"}
_KERNEL_OUTPUT_INTERNAL_MARKERS = (
    "LLM Request Sending",
    "backend command",
    "debug event",
)


def _looks_like_internal_kernel_text(value: Any) -> bool:
    """Return whether text is backend telemetry rather than chat content."""

    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(marker.lower() in lowered for marker in _KERNEL_OUTPUT_INTERNAL_MARKERS)


def _strip_internal_kernel_output(value: Any) -> tuple[Any, list[Any]]:
    """Remove backend-only telemetry from a Kernel output payload for chat display."""

    removed: list[Any] = []
    if isinstance(value, dict):
        visible: dict[Any, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            key_normalized = key_text.lower()
            if (
                key_normalized in _KERNEL_OUTPUT_INTERNAL_KEYS
                or (
                    key_normalized in _KERNEL_OUTPUT_INTERNAL_COMMAND_KEYS
                    and _looks_like_internal_kernel_text(item)
                )
                or _looks_like_internal_kernel_text(item)
            ):
                removed.append({key_text: item})
                continue
            cleaned, child_removed = _strip_internal_kernel_output(item)
            removed.extend(child_removed)
            if cleaned is not None and cleaned != {} and cleaned != []:
                visible[key] = cleaned
        return visible, removed
    if isinstance(value, list):
        visible_list: list[Any] = []
        for item in value:
            if _looks_like_internal_kernel_text(item):
                removed.append(item)
                continue
            cleaned, child_removed = _strip_internal_kernel_output(item)
            removed.extend(child_removed)
            if cleaned is not None and cleaned != {} and cleaned != []:
                visible_list.append(cleaned)
        return visible_list, removed
    if isinstance(value, tuple):
        visible_items: list[Any] = []
        for item in value:
            if _looks_like_internal_kernel_text(item):
                removed.append(item)
                continue
            cleaned, child_removed = _strip_internal_kernel_output(item)
            removed.extend(child_removed)
            if cleaned is not None and cleaned != {} and cleaned != []:
                visible_items.append(cleaned)
        return tuple(visible_items), removed
    if _looks_like_internal_kernel_text(value):
        return None, [value]
    return value, removed
