"""Safe log report storage for CLI-facing experiment/report commands."""
from __future__ import annotations

import json
import re
import builtins
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.redaction import redact_sensitive


_SAFE_LOG_NAME = re.compile(r"^[A-Za-z0-9_.-]+\.json$")
_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_LOG_TYPE = "supermedicine.log_report"
_SCHEMA_VERSION = 2
DEFAULT_MAX_MESSAGE_LENGTH = 10000
DEFAULT_MAX_RECORDS_PER_SESSION = 1000
DEFAULT_MAX_FILE_BYTES = 1024 * 1024


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            session_id=str(data["session_id"]) if data.get("session_id") is not None else None,
            message=str(data.get("message", "")),
        )


class LogReportError(ValueError):
    """Raised when a log report operation cannot be completed safely."""


class LogReportStore:
    """JSON-file backed log report store with redaction and path safety."""

    def __init__(
        self,
        project_dir: str | Path,
        *,
        max_message_length: int = DEFAULT_MAX_MESSAGE_LENGTH,
        max_records_per_session: int = DEFAULT_MAX_RECORDS_PER_SESSION,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.log_dir = self.project_dir / ".supermedicine" / "logs"
        self.max_message_length = self._positive_int(max_message_length, "max_message_length")
        self.max_records_per_session = self._positive_int(max_records_per_session, "max_records_per_session")
        self.max_file_bytes = self._positive_int(max_file_bytes, "max_file_bytes")

    def write(self, message: str, *, session_id: str | None = None) -> dict[str, Any]:
        """Write a redacted JSON log report.

        Session-scoped writes append to one safe session file. Writes without a
        session remain isolated in unique files, preserving existing CLI/TUI
        behavior while adding multi-record storage for experiment sessions.
        """

        message = self._require_message(message)
        safe_session_id = self._validate_session_id(session_id)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if safe_session_id:
            return self.append(message, session_id=safe_session_id)
        return self._write_isolated(message)

    def append(self, message: str, *, session_id: str) -> dict[str, Any]:
        """Append a redacted message to a session log file."""

        message = self._require_message(message)
        safe_session_id = self._validate_session_id(session_id)
        if safe_session_id is None:
            raise LogReportError("session_id is required for append")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self._safe_log_path(f"session-{safe_session_id}.json")
        entry = self._new_record(message, session_id=safe_session_id)

        if path.exists():
            payload = self._read_log_file(path)
            if payload.get("session_id") != safe_session_id:
                raise LogReportError("refusing to append to a different session log")
            records = self._records_from_payload(payload)
        else:
            payload = self._new_payload(session_id=safe_session_id)
            records = []

        if len(records) >= self.max_records_per_session:
            raise LogReportError("session log record limit exceeded")
        records.append(entry)
        payload["records"] = records
        payload["updated_at"] = entry["created_at"]
        payload["message"] = entry["message"]
        payload["entry_count"] = len(records)
        self._write_payload(path, payload, allow_existing=True)
        return self._public_payload(path, payload)

    def list(self) -> builtins.list[dict[str, Any]]:
        if not self.log_dir.exists():
            return []
        reports: builtins.list[dict[str, Any]] = []
        for path in sorted(self.log_dir.glob("*.json")):
            data = self._read_log_file(path)
            reports.append(
                {
                    "file": path.name,
                    "report_id": data.get("report_id"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at", data.get("created_at")),
                    "session_id": data.get("session_id"),
                    "message": data.get("message"),
                    "entry_count": data.get("entry_count", len(data.get("records", [])) or 1),
                }
            )
        return redact_sensitive(reports)

    def show(self, file_name: str) -> dict[str, Any]:
        path = self._safe_log_path(file_name)
        if not path.is_file():
            raise LogReportError(f"log report not found: {file_name}")
        return self._public_payload(path, self._read_log_file(path))

    def summary(self, *, file_name: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Return a redacted summary for one log, one session, or all logs."""

        if file_name and session_id:
            raise LogReportError("summary accepts either file_name or session_id, not both")
        if file_name:
            reports = [self.show(file_name)]
        else:
            safe_session_id = self._validate_session_id(session_id)
            reports = [self.show(item["file"]) for item in self.list()]
            if safe_session_id:
                reports = [item for item in reports if item.get("session_id") == safe_session_id]

        entries: builtins.list[dict[str, Any]] = []
        for report in reports:
            for record in self._records_from_payload(report):
                entries.append(
                    {
                        "file": report.get("file"),
                        "report_id": report.get("report_id"),
                        "entry_id": record.get("entry_id"),
                        "created_at": record.get("created_at"),
                        "session_id": record.get("session_id", report.get("session_id")),
                        "message": record.get("message"),
                    }
                )
        return redact_sensitive(
            {
                "generated_at": _utc_now(),
                "log_count": len(reports),
                "entry_count": len(entries),
                "session_id": session_id,
                "entries": entries,
            }
        )

    def export_summary(self, *, file_name: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        """Compatibility-friendly API for exporting a redacted JSON summary."""

        return self.summary(file_name=file_name, session_id=session_id)

    def _write_isolated(self, message: str) -> dict[str, Any]:
        payload = self._new_payload(session_id=None)
        entry = self._new_record(message, session_id=None)
        payload["records"] = [entry]
        payload["updated_at"] = entry["created_at"]
        payload["message"] = entry["message"]
        payload["entry_count"] = 1
        filename = f"{payload['created_at'].replace(':', '').replace('+', 'Z')}-{payload['report_id']}.json"
        path = self._safe_log_path(filename)
        self._write_payload(path, payload, allow_existing=False)
        return self._public_payload(path, payload)

    def _new_payload(self, *, session_id: str | None) -> dict[str, Any]:
        created_at = _utc_now()
        return {
            "log_type": _LOG_TYPE,
            "schema_version": _SCHEMA_VERSION,
            "report_id": f"log-{uuid4().hex}",
            "created_at": created_at,
            "updated_at": created_at,
            "session_id": session_id,
            "records": [],
            "message": "",
            "entry_count": 0,
        }

    def _new_record(self, message: str, *, session_id: str | None) -> dict[str, Any]:
        return {
            "entry_id": f"entry-{uuid4().hex}",
            "created_at": _utc_now(),
            "session_id": session_id,
            "message": str(redact_sensitive(message)),
        }

    def _require_message(self, message: str) -> str:
        if not isinstance(message, str) or not message.strip():
            raise LogReportError("--message cannot be empty")
        safe_message = message.strip()
        if len(safe_message) > self.max_message_length:
            raise LogReportError("--message exceeds maximum length")
        return safe_message

    @staticmethod
    def _positive_int(value: int, name: str) -> int:
        try:
            limit = int(value)
        except (TypeError, ValueError) as exc:
            raise LogReportError(f"{name} must be a positive integer") from exc
        if limit <= 0:
            raise LogReportError(f"{name} must be a positive integer")
        return limit

    def _validate_session_id(self, session_id: str | None) -> str | None:
        if session_id is None:
            return None
        safe_session_id = str(session_id).strip()
        if not safe_session_id:
            return None
        if not _SAFE_SESSION_ID.match(safe_session_id):
            raise LogReportError("session_id must be a safe name")
        return safe_session_id

    def _safe_log_path(self, file_name: str) -> Path:
        if not _SAFE_LOG_NAME.match(file_name):
            raise LogReportError("--file must be a safe log JSON file name")
        path = (self.log_dir / file_name).resolve()
        project_root = self.project_dir.resolve()
        log_root = self.log_dir.resolve()
        if path.parent != log_root or not self._is_relative_to(path, project_root):
            raise LogReportError("unsafe log report path")
        return path

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True

    def _write_payload(self, path: Path, payload: dict[str, Any], *, allow_existing: bool) -> None:
        safe_payload = redact_sensitive(payload)
        if path.exists() and not allow_existing:
            raise LogReportError(f"refusing to overwrite existing log report: {path.name}")
        if path.exists():
            self._read_log_file(path)
        text = json.dumps(safe_payload, ensure_ascii=False, indent=2)
        if len(text.encode("utf-8")) > self.max_file_bytes:
            raise LogReportError("log report file size limit exceeded")
        if allow_existing:
            path.write_text(text, encoding="utf-8")
        else:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(text)

    def _public_payload(self, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        safe_payload = dict(redact_sensitive(payload))
        safe_payload["file"] = path.name
        safe_payload["path"] = str(path)
        return redact_sensitive(safe_payload)

    def _records_from_payload(self, payload: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        records = payload.get("records")
        if isinstance(records, list):
            return [redact_sensitive(record) for record in records if isinstance(record, dict)]
        legacy = LogReport.from_dict(payload).to_dict()
        return [
            {
                "entry_id": legacy["report_id"],
                "created_at": legacy["created_at"],
                "session_id": legacy["session_id"],
                "message": legacy["message"],
            }
        ]

    def _read_log_file(self, path: Path) -> dict[str, Any]:
        data = self._read_path(path)
        if data.get("log_type") == _LOG_TYPE:
            return data
        required_legacy_keys = {"report_id", "created_at", "message"}
        if required_legacy_keys.issubset(data):
            data = dict(data)
            data.setdefault("log_type", _LOG_TYPE)
            data.setdefault("schema_version", 1)
            data.setdefault("updated_at", data.get("created_at"))
            data.setdefault("entry_count", 1)
            data.setdefault("records", self._records_from_payload(data))
            return redact_sensitive(data)
        raise LogReportError(f"refusing to read non-log JSON file: {path.name}")

    def _read_path(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LogReportError(f"could not read log report {path.name}: {exc}") from exc
        if not isinstance(data, dict):
            raise LogReportError(f"log report {path.name} is not a JSON object")
        return redact_sensitive(data)
