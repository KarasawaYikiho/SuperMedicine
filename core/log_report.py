"""Safe log report storage for CLI-facing experiment/report commands."""

from __future__ import annotations

import json
import re
import builtins
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.log_severity import (
    _SEVERITY_ORDER,
    _display_message,
    detect_log_severity,
    normalize_log_severity,
)
from core.log_report_models import (
    TUI_LOG_SESSION_ID,
    resolve_log_storage_locations,
)
from core.redaction import redact_path_for_display, redact_sensitive


_SAFE_LOG_NAME = re.compile(r"^[A-Za-z0-9_.-]+\.json$")
_SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
_LOG_TYPE = "supermedicine.log_report"
_SCHEMA_VERSION = 2
DEFAULT_MAX_MESSAGE_LENGTH = 10000
DEFAULT_MAX_RECORDS_PER_SESSION = 1000
DEFAULT_MAX_FILE_BYTES = 1024 * 1024
_LOG_STORAGE_LOCK = threading.RLock()
_STAT_DIMENSIONS = ("session_id", "source", "module", "category")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        self._locations = resolve_log_storage_locations(self.project_dir)
        self.log_dir = self._locations.log_dir
        self.max_message_length = self._positive_int(
            max_message_length, "max_message_length"
        )
        self.max_records_per_session = self._positive_int(
            max_records_per_session, "max_records_per_session"
        )
        self.max_file_bytes = self._positive_int(max_file_bytes, "max_file_bytes")

    def write(
        self,
        message: str,
        *,
        session_id: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """Write a redacted JSON log report.

        Session-scoped writes append to one safe session file. Writes without a
        session route to the shared TUI session log file (session-tui-application.json),
        consolidating all application logs into a single file per launch.
        """

        message = self._require_message(message)
        safe_session_id = self._validate_session_id(session_id)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        if safe_session_id:
            return self.append(message, session_id=safe_session_id, severity=severity)
        return self._write_isolated(message, severity=severity)

    def append(
        self, message: str, *, session_id: str, severity: str | None = None
    ) -> dict[str, Any]:
        """Append a redacted message to a session log file."""

        message = self._require_message(message)
        safe_session_id = self._validate_session_id(session_id)
        if safe_session_id is None:
            raise LogReportError("session_id is required for append")
        with _LOG_STORAGE_LOCK:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            path = self._safe_log_path(f"session-{safe_session_id}.json")
            entry = self._new_record(
                message, session_id=safe_session_id, severity=severity
            )

            if path.exists():
                payload = self._read_log_file(path)
                if payload.get("session_id") != safe_session_id:
                    raise LogReportError(
                        "refusing to append to a different session log"
                    )
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
            payload["severity"] = entry["severity"]
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
                    "path": redact_path_for_display(str(path)),
                    "storage": self.storage_info(file_name=path.name),
                    "report_id": data.get("report_id"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at", data.get("created_at")),
                    "session_id": data.get("session_id"),
                    "message": _display_message(
                        data.get("message"), severity=data.get("severity")
                    ),
                    "severity": normalize_log_severity(
                        data.get("severity")
                        or detect_log_severity(str(data.get("message") or ""))
                    ),
                    "entry_count": data.get(
                        "entry_count", len(data.get("records", [])) or 1
                    ),
                }
            )
        return redact_sensitive(reports)

    def storage_info(
        self,
        *,
        file_name: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Return redacted, resolvable storage paths for display surfaces."""

        if file_name and session_id:
            raise LogReportError(
                "storage_info accepts either file_name or session_id, not both"
            )
        current_file: Path | None = None
        if file_name:
            current_file = self._safe_log_path(file_name)
        else:
            safe_session_id = self._validate_session_id(session_id)
            if safe_session_id:
                current_file = self._safe_log_path(f"session-{safe_session_id}.json")
        payload: dict[str, Any] = self._locations.to_dict()
        payload.update(
            {
                "current_file": str(current_file) if current_file else "",
                "current_log_file": str(current_file) if current_file else "",
                "current_report_file": str(current_file) if current_file else "",
            }
        )
        for key in ("current_file", "current_log_file", "current_report_file"):
            if payload.get(key):
                payload[key] = redact_path_for_display(str(payload[key]))
        return payload

    def list_entries(
        self,
        *,
        file_name: str | None = None,
        session_id: str | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """Return de-duplicated individual log entries from centralized Log storage."""

        reports = self._reports_for_query(file_name=file_name, session_id=session_id)
        entries: builtins.list[dict[str, Any]] = []
        for report in reports:
            for record in self._records_from_payload(report):
                entries.append(self._entry_from_record(record, report=report))
        return redact_sensitive(self._unique_entries(entries))

    def statistics_for_entries(
        self, entries: builtins.list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Return statistics for the exact entries supplied by a caller."""

        return redact_sensitive(
            self._statistics_from_entries(self._unique_entries(entries))
        )

    def show(self, file_name: str) -> dict[str, Any]:
        path = self._safe_log_path(file_name)
        if not path.is_file():
            raise LogReportError(f"log report not found: {file_name}")
        return self._public_payload(path, self._read_log_file(path))

    def summary(
        self, *, file_name: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Return a redacted summary for one log, one session, or all logs."""

        if file_name and session_id:
            raise LogReportError(
                "summary accepts either file_name or session_id, not both"
            )
        reports = self._reports_for_query(file_name=file_name, session_id=session_id)
        entries = self.list_entries(file_name=file_name, session_id=session_id)
        statistics = self._statistics_from_entries(entries)
        return redact_sensitive(
            {
                "generated_at": _utc_now(),
                "log_count": len(reports),
                "entry_count": len(entries),
                "session_id": session_id,
                "statistics": statistics,
                "entries": entries,
            }
        )

    def follow_snapshot(
        self,
        *,
        file_name: str | None = None,
        session_id: str | None = None,
        max_entries: int = 50,
        max_lines: int | None = None,
    ) -> dict[str, Any]:
        """Return a redacted tail-style snapshot for realtime CLI log views."""

        entry_limit = self._positive_int(max_entries, "max_entries")
        line_limit = (
            self._positive_int(max_lines, "max_lines")
            if max_lines is not None
            else None
        )
        entries = self.list_entries(file_name=file_name, session_id=session_id)
        tail_entries = entries[-entry_limit:]
        lines = self._tail_display_lines(tail_entries, max_lines=line_limit)
        return redact_sensitive(
            {
                "generated_at": _utc_now(),
                "mode": "follow_snapshot",
                "file": file_name,
                "session_id": session_id,
                "storage": self.storage_info(
                    file_name=file_name, session_id=session_id
                ),
                "entry_count": len(entries),
                "displayed_entry_count": len(tail_entries),
                "max_entries": entry_limit,
                "max_lines": line_limit,
                "entries": tail_entries,
                "lines": lines,
                "displayed_line_count": len(lines),
            }
        )

    def export_summary(
        self, *, file_name: str | None = None, session_id: str | None = None
    ) -> dict[str, Any]:
        """Compatibility-friendly API for exporting a redacted JSON summary."""

        return self.summary(file_name=file_name, session_id=session_id)

    def _write_isolated(
        self, message: str, *, severity: str | None = None
    ) -> dict[str, Any]:
        """Route all non-session writes to the TUI session log file."""
        return self.append(message, session_id=TUI_LOG_SESSION_ID, severity=severity)

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
            "severity": "Info",
            "entry_count": 0,
        }

    def _new_record(
        self, message: str, *, session_id: str | None, severity: str | None = None
    ) -> dict[str, Any]:
        return {
            "entry_id": f"entry-{uuid4().hex}",
            "created_at": _utc_now(),
            "session_id": session_id,
            "severity": normalize_log_severity(severity)
            if severity
            else detect_log_severity(message),
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

    def _write_payload(
        self, path: Path, payload: dict[str, Any], *, allow_existing: bool
    ) -> None:
        safe_payload = redact_sensitive(payload)
        if path.exists() and not allow_existing:
            raise LogReportError(
                f"refusing to overwrite existing log report: {path.name}"
            )
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
        safe_payload["path"] = redact_path_for_display(str(path))
        safe_payload["storage"] = self.storage_info(file_name=path.name)
        return redact_sensitive(safe_payload)

    def _reports_for_query(
        self,
        *,
        file_name: str | None = None,
        session_id: str | None = None,
    ) -> builtins.list[dict[str, Any]]:
        if file_name and session_id:
            raise LogReportError(
                "query accepts either file_name or session_id, not both"
            )
        if file_name:
            return [self.show(file_name)]
        safe_session_id = self._validate_session_id(session_id)
        if not self.log_dir.exists():
            return []
        reports: builtins.list[dict[str, Any]] = []
        for path in sorted(self.log_dir.glob("*.json")):
            report = self._public_payload(path, self._read_log_file(path))
            if safe_session_id and report.get("session_id") != safe_session_id:
                matching_records = [
                    record
                    for record in self._records_from_payload(report)
                    if (record.get("session_id") or report.get("session_id"))
                    == safe_session_id
                ]
                if not matching_records:
                    continue
                report = dict(report)
                report["records"] = matching_records
            reports.append(report)
        return reports

    def _entry_from_record(
        self, record: dict[str, Any], *, report: dict[str, Any]
    ) -> dict[str, Any]:
        severity = self._record_severity(record)
        dimensions = self._record_dimensions(record, report=report)
        raw_message = str(record.get("message") or "")
        return {
            "file": report.get("file"),
            "path": report.get("path"),
            "storage": report.get("storage"),
            "report_id": report.get("report_id"),
            "entry_id": record.get("entry_id"),
            "created_at": record.get("created_at"),
            "updated_at": record.get("created_at"),
            "session_id": dimensions.get("session_id"),
            "source": dimensions.get("source"),
            "module": dimensions.get("module"),
            "category": dimensions.get("category"),
            "raw_message": raw_message,
            "message": _display_message(raw_message, severity=severity),
            "severity": severity,
        }

    def _records_from_payload(
        self, payload: dict[str, Any]
    ) -> builtins.list[dict[str, Any]]:
        records = payload.get("records")
        if isinstance(records, list):
            coerced_records: builtins.list[dict[str, Any]] = []
            for index, record in enumerate(records):
                if isinstance(record, dict):
                    coerced_records.append(
                        self._coerce_record(record, payload=payload, index=index)
                    )
            return [redact_sensitive(record) for record in coerced_records]
        legacy = self._coerce_legacy_record(payload)
        return [
            {
                "entry_id": legacy["report_id"],
                "created_at": legacy["created_at"],
                "session_id": legacy["session_id"],
                "severity": detect_log_severity(legacy["message"]),
                "message": legacy["message"],
            }
        ]

    def _coerce_record(
        self, record: dict[str, Any], *, payload: dict[str, Any], index: int
    ) -> dict[str, Any]:
        safe_record = dict(record)
        if safe_record.get("entry_id") is None:
            safe_record["entry_id"] = f"{payload.get('report_id') or 'legacy'}-{index}"
        if safe_record.get("created_at") is None:
            safe_record["created_at"] = (
                payload.get("created_at") or payload.get("updated_at") or ""
            )
        if safe_record.get("session_id") is None:
            safe_record["session_id"] = payload.get("session_id")
        if safe_record.get("message") is None:
            safe_record["message"] = ""
        safe_record["severity"] = self._record_severity(safe_record)
        return safe_record

    @staticmethod
    def _coerce_legacy_record(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "report_id": str(payload.get("report_id") or "legacy-log"),
            "created_at": str(
                payload.get("created_at") or payload.get("updated_at") or ""
            ),
            "session_id": str(payload["session_id"])
            if payload.get("session_id") is not None
            else None,
            "message": str(payload.get("message", "")),
        }

    @staticmethod
    def _record_severity(record: dict[str, Any]) -> str:
        return normalize_log_severity(
            record.get("severity")
            or detect_log_severity(str(record.get("message") or ""))
        )

    @staticmethod
    def _record_dimensions(
        record: dict[str, Any], *, report: dict[str, Any]
    ) -> dict[str, str | None]:
        dimensions: dict[str, str | None] = {}
        for key in _STAT_DIMENSIONS:
            value = record.get(key, report.get(key))
            dimensions[key] = (
                str(value) if value is not None and str(value) != "" else None
            )
        return dimensions

    @staticmethod
    def _entry_identity(
        entry: dict[str, Any], *, fallback: int
    ) -> tuple[str, str, str, str]:
        return (
            str(entry.get("file") or ""),
            str(entry.get("report_id") or ""),
            str(entry.get("entry_id") or fallback),
            str(entry.get("created_at") or ""),
        )

    def _unique_entries(
        self, entries: builtins.list[dict[str, Any]]
    ) -> builtins.list[dict[str, Any]]:
        unique_entries: builtins.list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, str, str]] = set()
        for index, entry in enumerate(entries):
            identity = self._entry_identity(entry, fallback=index)
            if identity in seen_keys:
                continue
            seen_keys.add(identity)
            unique_entries.append(entry)
        return unique_entries

    def _statistics_from_entries(
        self, entries: builtins.list[dict[str, Any]]
    ) -> dict[str, Any]:
        severity_counts = {severity: 0 for severity in _SEVERITY_ORDER}
        dimension_counts: dict[str, dict[str, int]] = {
            key: {} for key in _STAT_DIMENSIONS
        }
        first_seen: str | None = None
        last_seen: str | None = None

        for entry in entries:
            severity = normalize_log_severity(str(entry.get("severity") or "Info"))
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            created_at = str(entry.get("created_at") or "")
            if created_at:
                first_seen = (
                    created_at
                    if first_seen is None or created_at < first_seen
                    else first_seen
                )
                last_seen = (
                    created_at
                    if last_seen is None or created_at > last_seen
                    else last_seen
                )
            for dimension in _STAT_DIMENSIONS:
                value = entry.get(dimension)
                if value is None or str(value) == "":
                    continue
                key = str(value)
                dimension_counts[dimension][key] = (
                    dimension_counts[dimension].get(key, 0) + 1
                )

        return {
            "entry_count": len(entries),
            "severity_counts": severity_counts,
            "by_severity": severity_counts,
            "dimensions": dimension_counts,
            "time_range": {"start": first_seen, "end": last_seen},
        }

    @staticmethod
    def _tail_display_lines(
        entries: builtins.list[dict[str, Any]], *, max_lines: int | None
    ) -> builtins.list[str]:
        lines: builtins.list[str] = []
        for entry in entries:
            created_at = str(entry.get("created_at") or "")
            severity = str(entry.get("severity") or "Info")
            message = str(entry.get("message") or entry.get("raw_message") or "")
            message_lines = message.splitlines() or [message]
            for index, line in enumerate(message_lines):
                prefix = f"{created_at} {severity} " if index == 0 else ""
                lines.append(f"{prefix}{line}".rstrip())
        if max_lines is not None:
            return lines[-max_lines:]
        return lines

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
            raise LogReportError(
                f"could not read log report {path.name}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise LogReportError(f"log report {path.name} is not a JSON object")
        return redact_sensitive(data)
