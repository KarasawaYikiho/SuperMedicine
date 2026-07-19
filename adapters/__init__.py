"""Lazy platform adapter discovery for SuperMedicine.

Importing :mod:`adapters` exposes only the shared base adapter plus static
registry metadata. Concrete standalone, OpenCode, and Claude Code adapter
implementations are imported explicitly from their subpackages so core
startup/import paths never trigger optional assistant-platform imports,
initialization, or runtime probing.
"""

from __future__ import annotations

import importlib
from types import MappingProxyType
from typing import Any

from adapters.base_adapter import (
    ADAPTER_HOST_CONFIGS,
    AdapterHostConfig,
    AdapterProtocol,
    BaseAdapter,
)


AdapterRegistration = AdapterHostConfig
_ADAPTER_REGISTRY: MappingProxyType[str, AdapterHostConfig] = MappingProxyType(
    ADAPTER_HOST_CONFIGS
)

ADAPTER_REGISTRY = _ADAPTER_REGISTRY


def list_adapter_registrations(
    *, include_optional: bool = True
) -> list[dict[str, Any]]:
    """Return static adapter metadata without importing concrete adapters."""
    registrations = list(_ADAPTER_REGISTRY.values())
    if not include_optional:
        registrations = [
            registration for registration in registrations if not registration.optional
        ]
    return [registration.as_dict() for registration in registrations]


def get_adapter_registration(platform: str) -> dict[str, Any] | None:
    """Return one adapter registration by platform name, if known."""
    registration = _ADAPTER_REGISTRY.get(platform)
    return None if registration is None else registration.as_dict()


def default_adapter_registration() -> dict[str, Any]:
    """Return the standalone/core default adapter registration."""
    return _ADAPTER_REGISTRY["standalone"].as_dict()


def __getattr__(name: str) -> Any:
    """Lazily import adapter subpackages only when explicitly accessed."""
    if name in {"standalone", "opencode", "claude_code"}:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ADAPTER_REGISTRY",
    "AdapterHostConfig",
    "AdapterProtocol",
    "AdapterRegistration",
    "BaseAdapter",
    "default_adapter_registration",
    "get_adapter_registration",
    "list_adapter_registrations",
    "standalone",
    "opencode",
    "claude_code",
]
