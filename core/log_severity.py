"""Severity-related pure functions and constants for log reports."""

from __future__ import annotations

import re
from typing import Any

_SEVERITY_LABELS = {
    "critical": "Error",
    "error": "Error",
    "warning": "Warning",
    "warn": "Warning",
    "info": "Info",
    "information": "Info",
    "debug": "Debug",
    "trace": "Debug",
    "success": "Success",
    "ok": "Success",
}
_SEVERITY_ORDER = ("Error", "Warning", "Info", "Debug", "Success")
_SEVERITY_PREFIX = re.compile(
    r"^\s*(?:【\s*(?P<cjk>critical|error|warning|warn|info|information|debug|trace|success|ok)\s*】|"
    r"\[\s*(?P<bracket>critical|error|warning|warn|info|information|debug|trace|success|ok)\s*\]|"
    r"(?P<plain>critical|error|warning|warn|info|information|debug|trace|success|ok)\s*[:：-])",
    re.IGNORECASE,
)


def normalize_log_severity(severity: str | None) -> str:
    """Return a supported display severity name."""

    key = str(severity or "info").strip().lower()
    return _SEVERITY_LABELS.get(key, "Info")


def detect_log_severity(message: str, *, default: str = "Info") -> str:
    """Infer a supported severity from an existing log message."""

    text = str(message or "").strip()
    prefix_match = _SEVERITY_PREFIX.match(text)
    if prefix_match:
        return normalize_log_severity(
            next(value for value in prefix_match.groupdict().values() if value)
        )

    lowered = text.lower()
    if "captured stderr" in lowered:
        return "Error"
    if (
        re.search(
            r"\b(critical|fatal|exception|traceback|error|failed|failure)\b", lowered
        )
        or "失败" in text
    ):
        return "Error"
    if re.search(r"\b(warning|warn)\b", lowered) or any(
        token in text for token in ("警告", "缺少", "请选择", "确认")
    ):
        return "Warning"
    if re.search(r"\b(debug|trace)\b", lowered):
        return "Debug"
    if re.search(r"\b(success|succeeded|ready|ok|saved|completed)\b", lowered) or any(
        token in text for token in ("成功", "已保存", "完成")
    ):
        return "Success"
    if re.search(r"\b(info|information)\b", lowered):
        return "Info"
    return normalize_log_severity(default)


def format_log_message(message: str, *, severity: str | None = None) -> str:
    """Ensure a log message has one leading severity marker without duplicating legacy labels."""

    safe_message = str(message or "").strip()
    if not safe_message:
        return safe_message
    if _SEVERITY_PREFIX.match(safe_message):
        return safe_message
    label = (
        normalize_log_severity(severity)
        if severity
        else detect_log_severity(safe_message)
    )
    return f"【{label}】 {safe_message}"


def _display_message(message: Any, *, severity: str | None = None) -> str:
    return format_log_message(str(message or ""), severity=severity)
