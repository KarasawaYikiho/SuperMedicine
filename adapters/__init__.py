"""Lazy platform adapter discovery for SuperMedicine.

Importing :mod:`adapters` exposes only the shared base adapter plus static
registry metadata. Concrete standalone, OpenCode, and Claude Code adapter
implementations are imported explicitly from their subpackages so core
startup/import paths never trigger optional assistant-platform imports,
initialization, or runtime probing.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from adapters.base_adapter import BaseAdapter


@dataclass(frozen=True)
class AdapterRegistration:
    """Static adapter discovery contract that does not import adapter modules."""

    platform: str
    adapter_class: str
    module: str
    status: str
    optional: bool
    core: bool
    default: bool
    requires_core_runtime: bool
    capability_tool: str | None = None
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "adapter_class": self.adapter_class,
            "module": self.module,
            "status": self.status,
            "optional": self.optional,
            "core": self.core,
            "default": self.default,
            "requires_core_runtime": self.requires_core_runtime,
            "capability_tool": self.capability_tool,
            "limitations": list(self.limitations),
        }


_ADAPTER_REGISTRY: MappingProxyType[str, AdapterRegistration] = MappingProxyType(
    {
        "standalone": AdapterRegistration(
            platform="standalone",
            adapter_class="StandaloneAdapter",
            module="adapters.standalone.adapter",
            status="core_default",
            optional=False,
            core=True,
            default=True,
            requires_core_runtime=True,
            capability_tool=None,
            limitations=(
                "Self-contained core adapter; does not load OpenCode or Claude Code platform resources.",
                "Skill loading returns core-neutral metadata instead of platform skill files.",
            ),
        ),
        "opencode": AdapterRegistration(
            platform="opencode",
            adapter_class="OpenCodeAdapter",
            module="adapters.opencode.adapter",
            status="optional_add_on",
            optional=True,
            core=False,
            default=False,
            requires_core_runtime=False,
            capability_tool="opencode.capabilities",
            limitations=(
                "Optional add-on; not imported, initialized, or probed by default.",
                "Native OpenCode dispatch requires an explicit orchestrator/runtime bridge.",
            ),
        ),
        "claude-code": AdapterRegistration(
            platform="claude-code",
            adapter_class="ClaudeCodeAdapter",
            module="adapters.claude_code.adapter",
            status="optional_minimal",
            optional=True,
            core=False,
            default=False,
            requires_core_runtime=False,
            capability_tool="claude.capabilities",
            limitations=(
                "Optional minimal add-on; not imported, initialized, or probed by default.",
                "Invocation requires an explicitly selected adapter and local Claude Code CLI runtime.",
            ),
        ),
    }
)

ADAPTER_REGISTRY = _ADAPTER_REGISTRY


def list_adapter_registrations(*, include_optional: bool = True) -> list[dict[str, Any]]:
    """Return static adapter metadata without importing concrete adapters."""
    registrations = list(_ADAPTER_REGISTRY.values())
    if not include_optional:
        registrations = [registration for registration in registrations if not registration.optional]
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
    "AdapterRegistration",
    "BaseAdapter",
    "default_adapter_registration",
    "get_adapter_registration",
    "list_adapter_registrations",
    "standalone",
    "opencode",
    "claude_code",
]
