"""Data models and storage location resolution for log reports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.redaction import redact_path_for_display

TUI_LOG_SESSION_ID = "tui-application"


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
