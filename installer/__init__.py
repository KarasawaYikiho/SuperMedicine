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

from installer.component_installer import (
    load_components,
    install_components,
    validate_selection,
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
    "load_components",
    "install_components",
    "validate_selection",
]
