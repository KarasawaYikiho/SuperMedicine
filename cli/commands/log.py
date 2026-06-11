"""CLI commands: log report management."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from core.redaction import redact_sensitive
from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def log_write(cli, message: str, session_id: str | None = None) -> dict:
    """Write a redacted log report."""
    from core.log_report import LogReportStore

    result = LogReportStore(Path.cwd()).write(message, session_id=session_id)
    _log_json(result)
    return result


def log_list(cli) -> list[dict]:
    """List redacted log report summaries."""
    from core.log_report import LogReportStore

    result = LogReportStore(Path.cwd()).list()
    _log_json(result)
    return result


def log_show(cli, file_name: str) -> dict:
    """Show a redacted log report."""
    from core.log_report import LogReportStore

    result = LogReportStore(Path.cwd()).show(file_name)
    _log_json(result)
    return result


def log_location(
    cli, *, file_name: str | None = None, session_id: str | None = None
) -> dict:
    """Show redacted log/report/audit storage locations."""
    from core.log_report import LogReportStore

    result = LogReportStore(Path.cwd()).storage_info(
        file_name=file_name, session_id=session_id
    )
    _log_json(result)
    return result


def log_follow(
    cli,
    *,
    file_name: str | None = None,
    session_id: str | None = None,
    interval: float = 1.0,
    max_entries: int = 50,
    max_lines: int | None = None,
    iterations: int | None = None,
    once: bool = False,
    no_clear: bool = False,
) -> dict:
    """Show a realtime/tail-style redacted log view with test-safe exit controls."""
    from core.log_report import LogReportError, LogReportStore

    if file_name and session_id:
        raise ValueError(
            "log follow accepts either --file or --session-id, not both"
        )
    try:
        refresh_interval = float(interval)
    except (TypeError, ValueError) as exc:
        raise ValueError("--interval must be a non-negative number") from exc
    if refresh_interval < 0:
        raise ValueError("--interval must be a non-negative number")
    if once:
        iterations = 1
    if iterations is not None:
        try:
            iterations = int(iterations)
        except (TypeError, ValueError) as exc:
            raise ValueError("--iterations must be a positive integer") from exc
        if iterations <= 0:
            raise ValueError("--iterations must be a positive integer")

    store = LogReportStore(Path.cwd())
    rendered_snapshots = 0
    latest: dict[str, Any] | None = None
    while iterations is None or rendered_snapshots < iterations:
        try:
            latest = store.follow_snapshot(
                file_name=file_name,
                session_id=session_id,
                max_entries=max_entries,
                max_lines=max_lines,
            )
        except LogReportError:
            raise
        if rendered_snapshots and not no_clear:
            logger.info("-" * 40)
        logger.info(
            "Log storage: %s",
            latest.get("storage", {}).get("current_log_file")
            or latest.get("storage", {}).get("log_dir"),
        )
        logger.info(
            "Follow: interval=%ss max_entries=%s max_lines=%s exit=Ctrl+C",
            refresh_interval,
            latest.get("max_entries"),
            latest.get("max_lines") or "unlimited",
        )
        for line in latest.get("lines", []):
            logger.info("%s", redact_sensitive(str(line)))
        rendered_snapshots += 1
        if iterations is not None and rendered_snapshots >= iterations:
            break
        time.sleep(refresh_interval)
    result = dict(latest or {})
    result["refresh_interval"] = refresh_interval
    result["iterations"] = rendered_snapshots
    result["exit_mode"] = (
        "iterations" if iterations is not None else "keyboard_interrupt"
    )
    return result
