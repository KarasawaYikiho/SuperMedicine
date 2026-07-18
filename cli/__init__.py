"""SuperMedicine CLI package — re-exports for backward compatibility."""

from cli.helpers import (
    PERMISSION_RISK_NOTICE,
    _confirm_full_access_interactively,
    _load_params_file,
    _load_params_json,
    _paper_metadata_options,
    _parse_llm_headers,
    _permission_result,
    _resolve_run_params,
    _self_evolution_cli_result,
)
from cli.logging_setup import (
    _configure_cli_logging,
    _configure_stdio_errors,
    _log_json,
    _RedactingFormatter,
)

__all__ = [
    "PERMISSION_RISK_NOTICE",
    "_RedactingFormatter",
    "_configure_cli_logging",
    "_configure_stdio_errors",
    "_confirm_full_access_interactively",
    "_load_params_file",
    "_load_params_json",
    "_log_json",
    "_paper_metadata_options",
    "_parse_llm_headers",
    "_permission_result",
    "_resolve_run_params",
    "_self_evolution_cli_result",
]
