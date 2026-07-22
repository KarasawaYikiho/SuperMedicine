"""Typing facade for the historical ``core.redaction`` module path."""

from typing import Any

REDACTION_PLACEHOLDER: str

def redact_path_for_display(path: str) -> str: ...
def redact_sensitive(value: Any) -> Any: ...
