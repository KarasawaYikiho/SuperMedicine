"""Launch-scoped readable application logging for every interface."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from core.config_center import ConfigCenter, resolve_config_path
from core.logs.session import (
    ApplicationLogManager,
    ApplicationLogSession,
    ReadableApplicationLogHandler,
)


_ACTIVE_SESSION: ApplicationLogSession | None = None
_PREVIOUS_ROOT_HANDLERS: list[logging.Handler] | None = None
_PREVIOUS_ROOT_LEVEL: int | None = None


class LogReportLoggingHandler(ReadableApplicationLogHandler):
    """Backward-compatible name for the readable application-log handler."""

    def __init__(
        self,
        project_dir: str | Path,
        *,
        session_id: str | None = None,
        surface: str = "SERVICE",
    ) -> None:
        del session_id
        manager = _log_manager(project_dir)
        session = manager.start(
            surface=surface,
            command="logging-handler",
            continuous=False,
            attach_existing=False,
        )
        super().__init__(session)


class LogReportStream:
    """File-like stdout/stderr bridge into the active readable launch log."""

    def __init__(
        self,
        project_dir: str | Path,
        stream_name: str,
        *,
        session: ApplicationLogSession | None = None,
        session_id: Any = None,
        surface: str = "GUI",
    ) -> None:
        self.project_dir = Path(project_dir)
        self.stream_name = stream_name
        self.session = session or _coerce_session(
            project_dir, session_id, surface=surface
        )
        self.surface = surface
        self.encoding = "utf-8"
        self.errors = "backslashreplace"
        self._buffer = ""

    def write(self, value: str) -> int:
        text = str(value)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            _append_stream_output(
                self.session,
                self.stream_name,
                line,
                surface=self.surface,
            )
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            _append_stream_output(
                self.session,
                self.stream_name,
                self._buffer,
                surface=self.surface,
            )
            self._buffer = ""

    def isatty(self) -> bool:
        return False


def configure_tui_log_storage(project_dir: str | Path) -> ApplicationLogSession:
    """Start one continuous TUI cycle and route logs only to its shared file."""

    return configure_application_log_storage(
        project_dir,
        surface="TUI",
        continuous=True,
        keep_console=False,
    )


def configure_application_log_storage(
    project_dir: str | Path,
    *,
    surface: str = "GUI",
    command: str | None = None,
    continuous: bool = True,
    keep_console: bool = False,
    data_root: str | Path | None = None,
    max_total_bytes: int | None = None,
    session_id: str | None = None,
) -> ApplicationLogSession:
    """Configure Python logging for one launch cycle.

    ``session_id`` remains accepted for old callers but no longer controls file
    names; readable logs use the required local launch timestamp.
    """

    del session_id
    global _ACTIVE_SESSION, _PREVIOUS_ROOT_HANDLERS, _PREVIOUS_ROOT_LEVEL
    manager = _log_manager(
        project_dir,
        data_root=data_root,
        max_total_bytes=max_total_bytes,
    )
    session = manager.start(
        surface=surface,
        command=command,
        continuous=continuous,
    )
    _ACTIVE_SESSION = session

    root = logging.getLogger()
    if _PREVIOUS_ROOT_HANDLERS is None:
        _PREVIOUS_ROOT_HANDLERS = [
            handler
            for handler in root.handlers
            if not getattr(handler, "_supermedicine_cli_console", False)
        ]
        _PREVIOUS_ROOT_LEVEL = root.level
    root.setLevel(logging.INFO)
    console_handlers = [
        handler
        for handler in root.handlers
        if keep_console and getattr(handler, "_supermedicine_cli_console", False)
    ]
    for handler in list(root.handlers):
        if handler in console_handlers:
            continue
        root.removeHandler(handler)

    readable_handler = ReadableApplicationLogHandler(session)
    readable_handler.setLevel(logging.INFO)
    readable_handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(readable_handler)

    for logger_name in ("core", "plugins", "permission", "adapters", "installer"):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.propagate = True

    for existing_logger in list(logging.Logger.manager.loggerDict.values()):
        if not isinstance(existing_logger, logging.Logger):
            continue
        for handler in list(existing_logger.handlers):
            if not keep_console and _is_console_stream_handler(handler):
                existing_logger.removeHandler(handler)
        existing_logger.propagate = True
    return session


def stop_application_log_storage(*, reason: str = "normal") -> None:
    """Close the owned launch cycle and detach its logging handler."""

    global _ACTIVE_SESSION, _PREVIOUS_ROOT_HANDLERS, _PREVIOUS_ROOT_LEVEL
    session = _ACTIVE_SESSION
    if session is None:
        return
    session.stop(reason=reason)
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_supermedicine_cli_console", False):
            root.removeHandler(handler)
            handler.close()
        elif (
            isinstance(handler, ReadableApplicationLogHandler)
            and handler.session is session
        ):
            root.removeHandler(handler)
            handler.close()
    for handler in _PREVIOUS_ROOT_HANDLERS or []:
        if handler not in root.handlers:
            root.addHandler(handler)
    if _PREVIOUS_ROOT_LEVEL is not None:
        root.setLevel(_PREVIOUS_ROOT_LEVEL)
    _PREVIOUS_ROOT_HANDLERS = None
    _PREVIOUS_ROOT_LEVEL = None
    _ACTIVE_SESSION = None


def append_tui_stream_output(
    project_dir: str | Path, stream_name: str, text: str
) -> None:
    """Persist TUI background stdout/stderr into the current launch log."""

    session = _ACTIVE_SESSION or _coerce_session(
        project_dir, None, surface="TUI"
    )
    _append_stream_output(session, stream_name, text, surface="TUI")


def install_log_report_streams(
    project_dir: str | Path,
    *,
    session: ApplicationLogSession | None = None,
    session_id: Any = None,
    surface: str = "GUI",
) -> ApplicationLogSession:
    """Replace missing GUI stdio streams with readable-log-backed streams."""

    selected = session or _coerce_session(
        project_dir,
        session_id,
        surface=surface,
    )
    if sys.stdout is None:
        sys.stdout = LogReportStream(  # type: ignore[assignment]
            project_dir,
            "stdout",
            session=selected,
            surface=surface,
        )
    if sys.stderr is None:
        sys.stderr = LogReportStream(  # type: ignore[assignment]
            project_dir,
            "stderr",
            session=selected,
            surface=surface,
        )
    return selected


def _log_manager(
    project_dir: str | Path,
    *,
    data_root: str | Path | None = None,
    max_total_bytes: int | None = None,
) -> ApplicationLogManager:
    project = Path(project_dir).expanduser().resolve()
    selected_data_root = (
        Path(data_root).expanduser().resolve()
        if data_root is not None
        else resolve_config_path(project).expanduser().resolve().parent
    )
    configured_limit = max_total_bytes
    if configured_limit is None:
        config = ConfigCenter(selected_data_root / "config.yaml")
        configured_limit = config.get_application_log_config()["max_total_bytes"]
    return ApplicationLogManager(
        project,
        data_root=selected_data_root,
        max_total_bytes=configured_limit,
    )


def _coerce_session(
    project_dir: str | Path,
    value: Any,
    *,
    surface: str,
) -> ApplicationLogSession:
    if isinstance(value, ApplicationLogSession):
        return value
    if _ACTIVE_SESSION is not None:
        return _ACTIVE_SESSION
    return _log_manager(project_dir).start(
        surface=surface,
        command="stream",
        continuous=False,
    )


def _append_stream_output(
    session: ApplicationLogSession,
    stream_name: str,
    text: str,
    *,
    surface: str,
) -> None:
    message = str(text).strip()
    if not message:
        return
    severity = "ERROR" if str(stream_name).lower() == "stderr" else "INFO"
    try:
        session.write(
            severity,
            str(stream_name),
            message,
            surface=surface,
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


__all__ = [
    "LogReportLoggingHandler",
    "LogReportStream",
    "append_tui_stream_output",
    "configure_application_log_storage",
    "configure_tui_log_storage",
    "install_log_report_streams",
    "stop_application_log_storage",
]
