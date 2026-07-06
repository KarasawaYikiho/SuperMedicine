"""TUI log routing and Python logging handler for LogReportStore."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from core.log_report import LogReportStore, DEFAULT_MAX_MESSAGE_LENGTH
from core.log_report_models import TUI_LOG_SESSION_ID, new_application_log_session_id


class LogReportLoggingHandler(logging.Handler):
    """Logging handler that persists application records into Log storage."""

    def __init__(
        self, project_dir: str | Path, *, session_id: str = TUI_LOG_SESSION_ID
    ) -> None:
        super().__init__()
        self.store = LogReportStore(project_dir)
        self.session_id = session_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            if message.strip():
                for chunk in _log_chunks(message):
                    self.store.append(
                        chunk,
                        session_id=self.session_id,
                        severity=record.levelname,
                        source="logging",
                        module=record.name,
                        category=record.levelname,
                    )
        except Exception:
            pass


class LogReportStream:
    """File-like stream that appends stdout/stderr lines into one log session."""

    def __init__(
        self, project_dir: str | Path, stream_name: str, *, session_id: str
    ) -> None:
        self.project_dir = Path(project_dir)
        self.stream_name = stream_name
        self.session_id = session_id
        self.encoding = "utf-8"
        self.errors = "backslashreplace"
        self._buffer = ""

    def write(self, value: str) -> int:
        text = str(value)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            _append_stream_output(
                self.project_dir, self.stream_name, line, session_id=self.session_id
            )
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            _append_stream_output(
                self.project_dir,
                self.stream_name,
                self._buffer,
                session_id=self.session_id,
            )
            self._buffer = ""

    def isatty(self) -> bool:
        return False


def configure_tui_log_storage(project_dir: str | Path) -> None:
    """Route TUI-mode logs only to Log storage, never console streams.

    All log output is consolidated into a single launch-scoped session file
    so that every application launch writes to one fresh log file.  Different log categories are simply
    appended as separate entries in that one file.
    """

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    configure_application_log_storage(project_dir, session_id=TUI_LOG_SESSION_ID)


def configure_application_log_storage(
    project_dir: str | Path, *, session_id: str | None = None
) -> str:
    """Route process logging to one launch-scoped LogReportStore session file."""

    active_session_id = session_id or new_application_log_session_id()
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    handler = LogReportLoggingHandler(project_dir, session_id=active_session_id)
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)

    for logger_name in ("core", "plugins", "permission", "adapters", "installer"):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.propagate = True

    for existing_logger in list(logging.Logger.manager.loggerDict.values()):
        if not isinstance(existing_logger, logging.Logger):
            continue
        for handler in list(existing_logger.handlers):
            if _is_console_stream_handler(handler):
                existing_logger.removeHandler(handler)
                handler.close()
        existing_logger.propagate = True
    return active_session_id


def append_tui_stream_output(
    project_dir: str | Path, stream_name: str, text: str
) -> None:
    """Persist stdout/stderr text captured during TUI background execution."""

    _append_stream_output(
        project_dir, stream_name, text, session_id=TUI_LOG_SESSION_ID
    )


def install_log_report_streams(
    project_dir: str | Path, *, session_id: str | None = None
) -> str:
    """Replace missing GUI stdio streams with LogReport-backed streams."""

    active_session_id = session_id or new_application_log_session_id("gui-application")
    if sys.stdout is None:
        sys.stdout = LogReportStream(  # type: ignore[assignment]
            project_dir, "stdout", session_id=active_session_id
        )
    if sys.stderr is None:
        sys.stderr = LogReportStream(  # type: ignore[assignment]
            project_dir, "stderr", session_id=active_session_id
        )
    return active_session_id


def _append_stream_output(
    project_dir: str | Path, stream_name: str, text: str, *, session_id: str
) -> None:
    """Persist stdout/stderr text captured during application execution."""

    message = str(text).strip()
    if not message:
        return
    severity = "Error" if str(stream_name).lower() == "stderr" else "Info"
    try:
        store = LogReportStore(project_dir)
        for chunk in _log_chunks(message):
            categorized_chunk = _categorized_message(
                source="stream",
                module=str(stream_name),
                category=str(stream_name),
                message=chunk,
            )
            store.append(
                categorized_chunk,
                session_id=session_id,
                severity=severity,
                source="stream",
                module=str(stream_name),
                category=str(stream_name),
            )
    except Exception:
        pass


def _is_console_stream_handler(handler: logging.Handler) -> bool:
    stream = getattr(handler, "stream", None)
    return stream in {
        sys.stdout,
        sys.stderr,
        getattr(sys, "__stdout__", None),
        getattr(sys, "__stderr__", None),
    }


def _log_chunks(message: str) -> list[str]:
    safe_message = str(message).strip()
    if len(safe_message) <= DEFAULT_MAX_MESSAGE_LENGTH:
        return [safe_message]
    chunk_size = DEFAULT_MAX_MESSAGE_LENGTH - 32
    return [
        safe_message[index : index + chunk_size]
        for index in range(0, len(safe_message), chunk_size)
    ]


def _categorized_message(
    *, source: str, module: str, category: str, message: str
) -> str:
    return f"[{source}:{module}:{category}]\n{message}"
