"""Human-readable, launch-scoped application logging."""

from __future__ import annotations

import builtins
import logging
import os
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from permission.redaction import redact_path_for_display, redact_sensitive


DEFAULT_MAX_TOTAL_BYTES = 1024 * 1024 * 1024
ACTIVE_LOG_ENV = "SM_ACTIVE_LOG"
ACTIVE_LOG_SURFACE_ENV = "SM_LOG_SURFACE"
_SAFE_LOG_FILE = re.compile(
    r"^supermedicine-\d{8}-\d{6}(?:-[a-z0-9][a-z0-9-]{0,95})?(?:-\d+)?\.log$"
)
_SAFE_SUFFIX = re.compile(r"[^a-z0-9]+")
_LOG_LINE = re.compile(
    r"^\[(?P<created_at>[^\]]+)\] "
    r"\[(?P<severity>DEBUG|INFO|WARNING|ERROR|CRITICAL)\] "
    r"\[(?P<surface>[A-Z0-9_-]+)\] "
    r"\[(?P<module>[^\]]+)\] (?P<message>.*)$"
)
_WRITE_LOCK = threading.RLock()


class ApplicationLogError(ValueError):
    """Raised when an application log operation is unsafe or invalid."""


def normalize_surface(surface: str | None) -> str:
    value = str(surface or "SERVICE").strip().upper()
    value = re.sub(r"[^A-Z0-9_-]+", "-", value).strip("-")
    return value[:32] or "SERVICE"


def normalize_suffix(value: str | None) -> str:
    safe = _SAFE_SUFFIX.sub("-", str(value or "").strip().lower()).strip("-")
    return safe[:96]


def local_log_timestamp(now: datetime | None = None) -> str:
    return (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")


def readable_log_timestamp(now: datetime | None = None) -> str:
    selected = now or datetime.now().astimezone()
    return selected.strftime("%Y-%m-%d %H:%M:%S.") + f"{selected.microsecond // 1000:03d}"


def _severity_name(value: str | int | None) -> str:
    if isinstance(value, int):
        normalized = str(logging.getLevelName(value)).upper()
        return normalized if normalized in {
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        } else "INFO"
    normalized = str(value or "INFO").strip().upper()
    if normalized == "WARN":
        normalized = "WARNING"
    return normalized if normalized in {
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    } else "INFO"


def format_readable_log_line(
    message: Any,
    *,
    severity: str | int = "INFO",
    surface: str = "SERVICE",
    module: str = "application",
    now: datetime | None = None,
) -> str:
    """Format every physical line with readable level and surface markers."""

    safe_message = str(redact_sensitive(str(message or ""))).replace("\r\n", "\n")
    safe_message = safe_message.replace("\r", "\n")
    lines = safe_message.splitlines() or [""]
    timestamp = readable_log_timestamp(now)
    prefix = (
        f"[{timestamp}] [{_severity_name(severity)}] "
        f"[{normalize_surface(surface)}] [{str(module or 'application')[:96]}] "
    )
    return "\n".join(prefix + line for line in lines)


@dataclass(slots=True)
class ApplicationLogSession:
    path: Path
    surface: str
    max_total_bytes: int
    owner: bool = True
    stopped: bool = False

    def write(
        self,
        severity: str | int,
        module: str,
        message: Any,
        *,
        surface: str | None = None,
    ) -> None:
        line = format_readable_log_line(
            message,
            severity=severity,
            surface=surface or self.surface,
            module=module,
        )
        with _WRITE_LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(line + "\n")

    def stop(self, *, reason: str = "normal") -> None:
        if self.stopped:
            return
        self.write(
            "INFO",
            "application",
            (
                f"Application stopped reason={reason}"
                if self.owner
                else f"Interface detached reason={reason}"
            ),
        )
        self.stopped = True
        if self.owner and os.environ.get(ACTIVE_LOG_ENV) == str(self.path):
            os.environ.pop(ACTIVE_LOG_ENV, None)
            os.environ.pop(ACTIVE_LOG_SURFACE_ENV, None)


class ApplicationLogManager:
    """Create, append, inspect, and prune readable launch logs."""

    def __init__(
        self,
        project_dir: str | Path,
        *,
        data_root: str | Path | None = None,
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    ) -> None:
        project = Path(project_dir).expanduser().resolve()
        state = (
            Path(data_root).expanduser().resolve()
            if data_root is not None
            else project / ".supermedicine"
        )
        self.project_dir = project
        self.log_dir = state / "logs"
        self.max_total_bytes = self._positive_int(max_total_bytes, "max_total_bytes")

    def start(
        self,
        *,
        surface: str,
        command: str | None = None,
        continuous: bool = True,
        attach_existing: bool = True,
    ) -> ApplicationLogSession:
        """Start one launch log or attach to a parent service log."""

        normalized_surface = normalize_surface(surface)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        existing = self._active_path() if attach_existing else None
        if existing is not None:
            session = ApplicationLogSession(
                existing,
                normalized_surface,
                self.max_total_bytes,
                owner=False,
            )
            session.write(
                "INFO",
                "application",
                "Interface attached to active service log",
            )
            return session

        suffix = ""
        if not continuous:
            suffix_value = "-".join(
                value
                for value in (
                    normalize_suffix(normalized_surface),
                    normalize_suffix(command),
                )
                if value
            )
            suffix = f"-{suffix_value}" if suffix_value else ""
        base_name = f"supermedicine-{local_log_timestamp()}{suffix}"
        path = self._unique_path(base_name)
        path.touch(exist_ok=False)
        os.environ[ACTIVE_LOG_ENV] = str(path)
        os.environ[ACTIVE_LOG_SURFACE_ENV] = normalized_surface
        session = ApplicationLogSession(
            path,
            normalized_surface,
            self.max_total_bytes,
            owner=True,
        )
        session.write(
            "INFO",
            "application",
            (
                "Application started "
                f"mode={'continuous' if continuous else 'one-shot'}"
                + (f" command={normalize_suffix(command)}" if command else "")
            ),
        )
        self.prune(exclude=path)
        return session

    def append(
        self,
        message: str,
        *,
        severity: str = "INFO",
        surface: str | None = None,
        module: str = "manual",
    ) -> dict[str, Any]:
        active = self._active_path()
        created_session = False
        if active is None:
            session = self.start(
                surface=surface or "CLI",
                command="log-write",
                continuous=False,
                attach_existing=False,
            )
            active = session.path
            created_session = True
        else:
            session = ApplicationLogSession(
                active,
                normalize_surface(
                    surface or os.environ.get(ACTIVE_LOG_SURFACE_ENV) or "SERVICE"
                ),
                self.max_total_bytes,
                owner=False,
            )
        session.write(severity, module, message, surface=surface)
        if created_session:
            session.stop(reason="normal")
        return self.show(active.name)

    def list(self) -> builtins.list[dict[str, Any]]:
        if not self.log_dir.is_dir():
            return []
        reports: builtins.list[dict[str, Any]] = []
        for path in sorted(
            self.log_dir.glob("supermedicine-*.log"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            if not _SAFE_LOG_FILE.fullmatch(path.name):
                continue
            entries = self._entries(path)
            stat = path.stat()
            latest = entries[-1] if entries else {}
            reports.append(
                {
                    "file": path.name,
                    "path": redact_path_for_display(str(path)),
                    "created_at": datetime.fromtimestamp(
                        stat.st_ctime
                    ).astimezone().isoformat(timespec="seconds"),
                    "updated_at": datetime.fromtimestamp(
                        stat.st_mtime
                    ).astimezone().isoformat(timespec="seconds"),
                    "message": latest.get("message", ""),
                    "severity": latest.get("severity", "INFO"),
                    "surface": latest.get("surface", ""),
                    "entry_count": len(entries),
                    "size_bytes": stat.st_size,
                    "active": path == self._active_path(),
                }
            )
        return reports

    def show(self, file_name: str) -> dict[str, Any]:
        path = self._safe_path(file_name)
        if not path.is_file():
            raise ApplicationLogError(f"log not found: {file_name}")
        content = path.read_text(encoding="utf-8", errors="replace")
        entries = self._entries(path)
        return {
            "file": path.name,
            "path": redact_path_for_display(str(path)),
            "content": str(redact_sensitive(content)),
            "entries": entries,
            "entry_count": len(entries),
            "size_bytes": path.stat().st_size,
        }

    def storage_info(self, *, file_name: str | None = None) -> dict[str, Any]:
        current = self._safe_path(file_name) if file_name else self._active_path()
        return {
            "log_dir": redact_path_for_display(str(self.log_dir)),
            "current_file": (
                redact_path_for_display(str(current)) if current is not None else ""
            ),
            "current_log_file": (
                redact_path_for_display(str(current)) if current is not None else ""
            ),
            "max_total_bytes": self.max_total_bytes,
            "total_bytes": self.total_bytes(),
        }

    def list_entries(
        self, *, file_name: str | None = None
    ) -> builtins.list[dict[str, Any]]:
        if file_name:
            return self._entries(self._safe_path(file_name))
        entries: builtins.list[dict[str, Any]] = []
        for item in reversed(self.list()):
            entries.extend(self._entries(self._safe_path(str(item["file"]))))
        return entries

    def statistics_for_entries(
        self, entries: builtins.list[dict[str, Any]]
    ) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        by_surface: dict[str, int] = {}
        for entry in entries:
            severity = str(entry.get("severity") or "INFO")
            surface = str(entry.get("surface") or "SERVICE")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_surface[surface] = by_surface.get(surface, 0) + 1
        return {
            "entry_count": len(entries),
            "by_severity": by_severity,
            "by_surface": by_surface,
        }

    def follow_snapshot(
        self,
        *,
        file_name: str | None = None,
        max_entries: int = 50,
        max_lines: int | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        selected = file_name
        if selected is None:
            active = self._active_path()
            if active is not None:
                selected = active.name
            else:
                logs = self.list()
                selected = str(logs[0]["file"]) if logs else None
        entries = self.list_entries(file_name=selected) if selected else []
        tail = entries[-self._positive_int(max_entries, "max_entries") :]
        lines = [str(entry.get("display", "")) for entry in tail]
        if max_lines is not None:
            lines = lines[-self._positive_int(max_lines, "max_lines") :]
        return {
            "mode": "follow_snapshot",
            "file": selected,
            "entry_count": len(entries),
            "displayed_entry_count": len(tail),
            "max_entries": max_entries,
            "max_lines": max_lines,
            "entries": tail,
            "lines": lines,
            "displayed_line_count": len(lines),
            "storage": self.storage_info(file_name=selected) if selected else self.storage_info(),
        }

    def total_bytes(self) -> int:
        if not self.log_dir.is_dir():
            return 0
        return sum(
            path.stat().st_size
            for path in self.log_dir.glob("supermedicine-*.log")
            if path.is_file() and _SAFE_LOG_FILE.fullmatch(path.name)
        )

    def prune(self, *, exclude: Path | None = None) -> builtins.list[str]:
        """Delete oldest completed logs until the configured total limit is met."""

        if not self.log_dir.is_dir():
            return []
        active = self._active_path()
        protected = {
            path.resolve()
            for path in (exclude, active)
            if path is not None
        }
        paths = sorted(
            (
                path
                for path in self.log_dir.glob("supermedicine-*.log")
                if path.is_file() and _SAFE_LOG_FILE.fullmatch(path.name)
            ),
            key=lambda item: item.stat().st_mtime,
        )
        total = sum(path.stat().st_size for path in paths)
        removed: builtins.list[str] = []
        for path in paths:
            if total <= self.max_total_bytes:
                break
            if path.resolve() in protected:
                continue
            size = path.stat().st_size
            path.unlink()
            total -= size
            removed.append(path.name)
        return removed

    def _active_path(self) -> Path | None:
        raw = os.environ.get(ACTIVE_LOG_ENV, "").strip()
        if not raw:
            return None
        candidate = Path(raw).expanduser().resolve()
        if candidate.parent != self.log_dir.resolve():
            return None
        if not _SAFE_LOG_FILE.fullmatch(candidate.name):
            return None
        return candidate if candidate.is_file() else None

    def _unique_path(self, base_name: str) -> Path:
        candidate = self.log_dir / f"{base_name}.log"
        index = 2
        while candidate.exists():
            candidate = self.log_dir / f"{base_name}-{index}.log"
            index += 1
        return candidate

    def _safe_path(self, file_name: str) -> Path:
        if not _SAFE_LOG_FILE.fullmatch(str(file_name)):
            raise ApplicationLogError("file must be a safe SuperMedicine .log name")
        path = (self.log_dir / str(file_name)).resolve()
        if path.parent != self.log_dir.resolve():
            raise ApplicationLogError("unsafe application log path")
        return path

    def _entries(self, path: Path) -> builtins.list[dict[str, Any]]:
        if not path.is_file():
            return []
        entries: builtins.list[dict[str, Any]] = []
        for index, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            match = _LOG_LINE.fullmatch(line)
            if match is None:
                continue
            entry = match.groupdict()
            entry["line"] = index
            entry["display"] = line
            entries.append(entry)
        return entries

    @staticmethod
    def _positive_int(value: Any, name: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ApplicationLogError(f"{name} must be a positive integer") from exc
        if parsed <= 0:
            raise ApplicationLogError(f"{name} must be a positive integer")
        return parsed


class ReadableApplicationLogHandler(logging.Handler):
    """Logging handler that writes into the current readable launch log."""

    def __init__(self, session: ApplicationLogSession) -> None:
        super().__init__()
        self.session = session

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            self.session.write(
                record.levelno,
                record.name,
                message,
                surface=getattr(record, "surface", None),
            )
        except Exception:
            self.handleError(record)


class ApplicationEventLogAdapter:
    """Compatibility adapter that routes structured service events to one log."""

    def __init__(
        self,
        project_dir: str | Path,
        *,
        data_root: str | Path | None = None,
        surface: str = "SERVICE",
        max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    ) -> None:
        self.manager = ApplicationLogManager(
            project_dir,
            data_root=data_root,
            max_total_bytes=max_total_bytes,
        )
        self.surface = normalize_surface(surface)

    def append(
        self,
        message: str,
        *,
        session_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        module: str | None = None,
        category: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        selected_module = (
            module
            or category
            or source
            or (f"session.{normalize_suffix(session_id)}" if session_id else "event")
        )
        return self.manager.append(
            message,
            severity=_severity_name(severity),
            surface=self.surface,
            module=selected_module,
        )


__all__ = [
    "ACTIVE_LOG_ENV",
    "ACTIVE_LOG_SURFACE_ENV",
    "ApplicationLogError",
    "ApplicationLogManager",
    "ApplicationLogSession",
    "ApplicationEventLogAdapter",
    "DEFAULT_MAX_TOTAL_BYTES",
    "ReadableApplicationLogHandler",
    "format_readable_log_line",
    "local_log_timestamp",
    "normalize_suffix",
    "normalize_surface",
]
