"""CLI commands: experiment guide management."""

from __future__ import annotations

import logging
from pathlib import Path

from cli.logging_setup import _log_json
from core.services import ExperimentToolService

logger = logging.getLogger(__name__)


def _service() -> ExperimentToolService:
    return ExperimentToolService(Path.cwd())


def experiment_start(cli, protocol: str, session_id: str | None = None) -> dict:
    """Start a standalone experiment guide session and persist it as JSON."""
    service = _service()
    result = service.require_data(
        service.start_experiment(protocol, session_id=session_id)
    )
    _log_json(result)
    return result


def experiment_list(cli) -> list[dict]:
    """List configured experiment protocols discovered from plugins/experiments."""
    service = _service()
    result = service.require_data(service.list_experiments())
    _log_json(result)
    return result


def experiment_context(cli, protocol: str | None = None) -> dict:
    """Show the experiment context and authoring rules injected into LLM chat."""
    service = _service()
    result = service.require_data(service.experiment_context(protocol))
    _log_json(result)
    return result


def experiment_add_config(
    cli,
    *,
    instruction: str | None = None,
    config_json: str | None = None,
    filename: str | None = None,
    overwrite: bool = False,
) -> dict:
    """Draft/validate and save a new experiment config in plugins/experiments."""
    if bool(instruction and instruction.strip()) == bool(
        config_json and config_json.strip()
    ):
        raise ValueError("provide exactly one of --instruction or --config-json")
    service = _service()
    config = service.parse_input(config_json) if config_json else None
    result = service.require_data(
        service.add_experiment_config(
            instruction=instruction,
            config=config,
            filename=filename,
            overwrite=overwrite,
        )
    )
    _log_json(result)
    return result


def experiment_show(cli, session_file: str | Path) -> dict:
    """Show a persisted experiment guide session."""
    service = _service()
    result = service.require_data(service.show_experiment(session_file))
    _log_json(result)
    return result


def experiment_submit(
    cli,
    session_file: str | Path,
    step_id: str,
    input_json: str,
    *,
    calculate: bool = False,
) -> dict:
    """Submit data for the current experiment step."""
    service = _service()
    result = service.require_data(
        service.submit_experiment(
            session_file, step_id, input_json, calculate=calculate
        )
    )
    _log_json(result)
    return result
