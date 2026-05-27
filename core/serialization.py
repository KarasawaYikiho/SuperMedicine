"""Shared serialization utilities."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


def json_ready(value: Any) -> Any:
    """Convert a value to a JSON-serializable representation.

    Handles Path, datetime, dataclass, dict, and list/tuple recursively.
    """
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return json_ready(asdict(value))
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value
