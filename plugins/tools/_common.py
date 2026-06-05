"""Shared helper utilities for tool plugins."""

from __future__ import annotations

import math
from typing import Any


def param_or_default(params: dict[str, Any], key: str, default: Any = None) -> Any:
    """Extract a parameter value from params, falling back to default.

    Args:
        params: Parameter dictionary to search.
        key: Key to look up in *params*.
        default: Value returned when *key* is absent.

    Returns:
        The value associated with *key*, or *default* if missing.
    """
    if key in params:
        return params[key]
    return default


def as_float_list(value: Any, name: str) -> list[float]:
    """Convert a value to a list of floats, raising ValueError on failure.

    Args:
        value: Expected to be a list of numeric values.
        name: Human-readable label used in the error message.

    Returns:
        A ``list[float]`` converted from *value*.

    Raises:
        ValueError: If *value* is not a list.
    """
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of numbers")
    return [float(item) for item in value]


def as_float_groups(value: Any, name: str) -> list[list[float]]:
    """Convert a value to a list of lists of floats, raising ValueError on failure.

    Args:
        value: Expected to be a list of lists of numeric values.
        name: Human-readable label used in the error message.

    Returns:
        A ``list[list[float]]`` converted from *value*.

    Raises:
        ValueError: If *value* or any nested element is not a list.
    """
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list of numeric lists")
    return [
        as_float_list(group, f"{name}[{index}]") for index, group in enumerate(value)
    ]


def normal_cdf(z: float) -> float:
    """Compute the cumulative distribution function of the standard normal distribution.

    Args:
        z: The z-score.

    Returns:
        The probability that a standard normal random variable is less than z.
    """
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def required_str(params: dict[str, Any], key: str) -> str:
    """Extract a required non-empty string parameter.

    Args:
        params: Parameter dictionary.
        key: The key to extract.

    Returns:
        The string value.

    Raises:
        ValueError: If the key is missing or empty.
    """
    value = params.get(key)
    if not value or not isinstance(value, str):
        raise ValueError(
            f"Parameter '{key}' is required and must be a non-empty string"
        )
    return value
