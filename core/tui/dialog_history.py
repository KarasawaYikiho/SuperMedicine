"""Compatibility exports for workspace-local dialog history."""

from core.dialog_history import (
    DIALOG_HISTORY_FILENAME,
    RAW_CONVERSATION_FIELDS,
    DialogHistoryEvent,
    DialogHistoryPrivacyError,
    DialogHistoryStore,
)

__all__ = [
    "DIALOG_HISTORY_FILENAME",
    "RAW_CONVERSATION_FIELDS",
    "DialogHistoryEvent",
    "DialogHistoryPrivacyError",
    "DialogHistoryStore",
]
