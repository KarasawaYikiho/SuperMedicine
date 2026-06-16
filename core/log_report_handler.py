"""TUI log routing and Python logging handler for LogReportStore."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from core.log_report import LogReportStore, DEFAULT_MAX_MESSAGE_LENGTH
from core.log_report_models import TUI_LOG_SESSION_ID


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
                        chunk, session_id=self.session_id, severity=record.levelname
                    )
        except Exception:
            pass


def configure_tui_log_storage(project_dir: str | Path) -> None:
    """Route TUI-mode logs only to Log storage, never console streams.

    All log output is consolidated into a single session file
    (session-tui-application.json) so that every application launch
    writes to the same log file.  Different log categories are simply
    appended as separate entries in that one file.
    """

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    handler = LogReportLoggingHandler(project_dir, session_id=TUI_LOG_SESSION_ID)
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


def append_tui_stream_output(
    project_dir: str | Path, stream_name: str, text: str
) -> None:
    """Persist stdout/stderr text captured during TUI background execution."""

    message = str(text).strip()
    if not message:
        return
    severity = "Error" if str(stream_name).lower() == "stderr" else "Info"
    try:
        store = LogReportStore(project_dir)
        for chunk in _log_chunks(f"captured {stream_name}: {message}"):
            store.append(chunk, session_id=TUI_LOG_SESSION_ID, severity=severity)
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
