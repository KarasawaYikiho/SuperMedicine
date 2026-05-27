"""Shared helper utilities for tool plugins."""
from __future__ import annotations

from typing import Any


def param_or_default(params: dict[str, Any], key: str, default: Any = None) -> Any:
    """Extract a parameter value from params, falling back to default."""
    if key in params:
        return params[key]
    return default


def as_float_list(value: Any, name: str) -> list[float]:
    """Convert a value to a list of floats, raising ValueError on failure."""
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of numbers")
    return [float(item) for item in value]


def as_float_groups(value: Any, name: str) -> list[list[float]]:
    """Convert a value to a list of lists of floats, raising ValueError on failure."""
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of numeric lists")
    return [as_float_list(group, f"{name}[{index}]") for index, group in enumerate(value)]
