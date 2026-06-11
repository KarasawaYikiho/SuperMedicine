"""CLI logging infrastructure — secret-redacting formatter and configuration."""

from __future__ import annotations

import json
import logging
import sys

from core.redaction import redact_sensitive

logger = logging.getLogger(__name__)


def _configure_stdio_errors() -> None:
    """Keep argparse/help output writable on narrow Windows stdio encodings."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (AttributeError, TypeError, ValueError):
            continue


def _log_json(value: object) -> None:
    """Log JSON output after recursively redacting secret-looking values."""
    logger.info(json.dumps(redact_sensitive(value), ensure_ascii=False, indent=2))


class _RedactingFormatter(logging.Formatter):
    """Formatter that redacts secrets before text reaches CLI streams."""

    def format(self, record: logging.LogRecord) -> str:
        original_msg = record.msg
        original_args = record.args
        try:
            record.msg = redact_sensitive(record.getMessage())
            record.args = ()
            return str(redact_sensitive(super().format(record)))
        finally:
            record.msg = original_msg
            record.args = original_args

    def formatException(self, ei) -> str:  # noqa: N802 - logging API name
        return str(redact_sensitive(super().formatException(ei)))


def _configure_cli_logging() -> None:
    """Configure default CLI logging with a secret-redacting formatter."""

    handler = logging.StreamHandler()
    handler.setFormatter(_RedactingFormatter("%(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
