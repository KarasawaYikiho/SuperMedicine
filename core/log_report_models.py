"""Data models and storage location resolution for log reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from permission.redaction import redact_path_for_display


def new_application_log_session_id(prefix: str = "application") -> str:
    """Return a process/opening scoped safe session id for one log container."""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{prefix}-{timestamp}-{os.getpid()}-{uuid4().hex[:8]}"


TUI_LOG_SESSION_ID = new_application_log_session_id("tui-application")


@dataclass(frozen=True)
class LogReport:
    """One redacted log report record persisted as JSON."""

    report_id: str
    created_at: str
    message: str
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogReport":
        return cls(
            report_id=str(data["report_id"]),
            created_at=str(data["created_at"]),
            session_id=str(data["session_id"])
            if data.get("session_id") is not None
            else None,
            message=str(data.get("message", "")),
        )


@dataclass(frozen=True)
class LogStorageLocations:
    """Resolved storage locations for log/report/audit files."""

    project_dir: Path
    log_dir: Path
    report_dir: Path
    tui_log_file: Path
    audit_file: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "project_dir": redact_path_for_display(str(self.project_dir)),
            "log_dir": redact_path_for_display(str(self.log_dir)),
            "report_dir": redact_path_for_display(str(self.report_dir)),
            "tui_log_file": redact_path_for_display(str(self.tui_log_file)),
            "audit_file": redact_path_for_display(str(self.audit_file)),
        }


def resolve_log_storage_locations(project_dir: str | Path) -> LogStorageLocations:
    """Return canonical project-local storage paths for logs, reports, and audit."""

    root = Path(project_dir).resolve()
    log_dir = root / ".supermedicine" / "logs"
    return LogStorageLocations(
        project_dir=root,
        log_dir=log_dir,
        report_dir=log_dir,
        tui_log_file=log_dir / f"session-{TUI_LOG_SESSION_ID}.json",
        audit_file=root / ".supermedicine" / "policies" / "audit.jsonl",
    )


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
