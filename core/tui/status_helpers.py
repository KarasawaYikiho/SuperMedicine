"""TUI status helper utilities extracted from app.py."""

from __future__ import annotations

import logging
from pathlib import Path

from textual.widgets import Static

from core.services import LLMService
from core.tui.i18n import t


logger = logging.getLogger(__name__)


STATUS_STYLE_CLASSES = (
    "status-info",
    "status-success",
    "status-warning",
    "status-error",
)


def apply_status_style(widget: Static, message: str) -> None:
    """Apply a semantic style class to a status widget based on its message."""

    widget.remove_class(*STATUS_STYLE_CLASSES)
    text = message.lower()
    if t("error").lower() in text or "error" in text or "失败" in message:
        widget.add_class("status-error")
    elif (
        "缺少" in message or "未" in message or "请选择" in message or "确认" in message
    ):
        widget.add_class("status-warning")
    elif "成功" in message or "已" in message or "ready" in text or "ok" in text:
        widget.add_class("status-success")
    else:
        widget.add_class("status-info")


def _console_safe_text(value: str, encoding: str | None = None) -> str:
    """Return text that can be encoded by the active console.

    Windows legacy consoles may use GBK or another non-UTF-8 code page that
    cannot encode emoji used in TUI status labels.  Keep Unicode output on
    capable terminals, but replace only unencodable characters for safe
    non-interactive status printing.
    """

    target_encoding = encoding or "utf-8"
    try:
        value.encode(target_encoding)
    except (LookupError, UnicodeEncodeError):
        try:
            return value.encode(target_encoding, errors="replace").decode(
                target_encoding, errors="replace"
            )
        except LookupError:
            return value.encode("utf-8", errors="replace").decode(
                "utf-8", errors="replace"
            )
    return value


def _describe_llm_status(project_root: Path | str) -> tuple[bool, str]:
    try:
        service = LLMService(Path(project_root), restore_on_startup=True)
        current_result = service.show_provider()
        current = current_result.data or {} if current_result.ok else {}
        provider = str(current.get("provider") or "")
        if not provider:
            return False, ""
        return service.validate_provider(provider).ok, provider
    except Exception as exc:
        logger.warning(
            "TUI LLM status diagnostic failed: stage=config project_root=%s error=%s",
            project_root,
            exc,
        )
        return False, ""
