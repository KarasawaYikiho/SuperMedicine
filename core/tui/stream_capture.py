"""Stream capture utilities for routing background stdout/stderr into TUI Log storage."""

from __future__ import annotations

import contextlib
import sys
import threading
from pathlib import Path
from typing import Any


class _TUILogTextSink:
    """File-like sink that routes background stdout/stderr text into Log storage."""

    def __init__(self, project_root: Path, stream_name: str) -> None:
        self.project_root = project_root
        self.stream_name = stream_name
        self._buffer = ""

    def write(self, value: str) -> int:
        text = str(value)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._append(line)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self._append(self._buffer)
            self._buffer = ""

    def _append(self, text: str) -> None:
        if not text.strip():
            return
        from core.log_report_handler import append_tui_stream_output

        append_tui_stream_output(self.project_root, self.stream_name, text)


class _TUIThreadRoutedStream:
    """Route only the current worker thread stream writes to Log storage."""

    def __init__(
        self, original: Any, sink: _TUILogTextSink, owner_thread_id: int
    ) -> None:
        self._original = original
        self._sink = sink
        self._owner_thread_id = owner_thread_id
        self.encoding = getattr(original, "encoding", None)
        self.errors = getattr(original, "errors", None)

    def write(self, value: str) -> int:
        if threading.get_ident() == self._owner_thread_id:
            return self._sink.write(value)
        return self._original.write(value)

    def flush(self) -> None:
        if threading.get_ident() == self._owner_thread_id:
            self._sink.flush()
            return
        self._original.flush()

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        return self._original.fileno()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


@contextlib.contextmanager
def _capture_current_thread_tui_streams(project_root: Path):
    """Capture Kernel stdout/stderr without redirecting TUI renderer writes."""

    stdout_sink = _TUILogTextSink(project_root, "stdout")
    stderr_sink = _TUILogTextSink(project_root, "stderr")
    owner_thread_id = threading.get_ident()
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = _TUIThreadRoutedStream(original_stdout, stdout_sink, owner_thread_id)  # type: ignore[assignment]
    sys.stderr = _TUIThreadRoutedStream(original_stderr, stderr_sink, owner_thread_id)  # type: ignore[assignment]
    try:
        yield
    finally:
        stdout_sink.flush()
        stderr_sink.flush()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
