"""Stable lowercase installer package for SuperMedicine."""

from installer.entrypoint import (
    DEFAULT_CONFIG,
    INSTALL_ENV_NAMES,
    PROVIDER_ENV_NAMES,
    detect_platform,
    init_config,
    main,
    write_llm_config,
    _normalize_provider,
    _resolve_api_key,
    _resolve_install_value,
)

__all__ = [
    "DEFAULT_CONFIG",
    "INSTALL_ENV_NAMES",
    "PROVIDER_ENV_NAMES",
    "detect_platform",
    "init_config",
    "main",
    "write_llm_config",
    "_normalize_provider",
    "_resolve_api_key",
    "_resolve_install_value",
]
