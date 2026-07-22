"""CLI commands for workspace tools, experiments, and logs."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from cli.logging_setup import _log_json
from core.redaction import redact_sensitive
from core.services import ExperimentToolService, PermissionLogSystemService

logger = logging.getLogger(__name__)


def tool_init(cli, workspace_id: str) -> dict:
    """Initialize workspace-local Python/R tool directories."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(service.initialize_tools(workspace_id))
    _log_json(result)
    return result


def tool_list(cli, workspace_id: str, language: str | None = None) -> dict:
    """List workspace-local tools grouped by language."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.list_tools(workspace_id, language=language)
    )
    _log_json(result)
    return result


def tool_scan(cli, language: str | None = None) -> dict:
    """Scan Python/R source tool directories for selectable import candidates."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(service.scan_tools(language))
    _log_json(result)
    return result


def tool_add(
    cli,
    workspace_id: str,
    selections: list[str] | None = None,
    *,
    language: str | None = None,
    overwrite: bool = False,
) -> dict:
    """Import scanned Python/R tools selected from the candidate list."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.import_tools(
            workspace_id,
            selections,
            language=language,
            overwrite=overwrite,
        )
    )
    _log_json(result)
    return result


def tool_show(cli, workspace_id: str, language: str, tool_id: str) -> dict:
    """Show one workspace-local tool manifest."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.show_tool(workspace_id, language, tool_id)
    )
    _log_json(result)
    return result


def tool_run(
    cli,
    workspace_id: str,
    language: str,
    tool_id: str,
    *,
    dry_run: bool = False,
    input_path: str | None = None,
    output_path: str | None = None,
) -> dict:
    """Prepare a guarded workspace-local tool invocation without unsafe execution."""
    service = ExperimentToolService(Path.cwd())
    result = service.require_data(
        service.prepare_tool(
            workspace_id,
            language,
            tool_id,
            dry_run=dry_run,
            input_path=input_path,
            output_path=output_path,
        )
    )
    _log_json(result)
    return result


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


def log_write(cli, message: str, session_id: str | None = None) -> dict:
    """Write a redacted log report."""
    service = PermissionLogSystemService(Path.cwd())
    result = service.require_data(service.write_log(message, session_id=session_id))
    _log_json(result)
    return result


def log_list(cli) -> list[dict]:
    """List redacted log report summaries."""
    service = PermissionLogSystemService(Path.cwd())
    result = service.require_data(service.list_logs())
    _log_json(result)
    return result


def log_show(cli, file_name: str) -> dict:
    """Show a redacted log report."""
    service = PermissionLogSystemService(Path.cwd())
    result = service.require_data(service.show_log(file_name))
    _log_json(result)
    return result


def log_location(
    cli, *, file_name: str | None = None, session_id: str | None = None
) -> dict:
    """Show redacted log/report/audit storage locations."""
    service = PermissionLogSystemService(Path.cwd())
    result = service.require_data(
        service.log_storage(file_name=file_name, session_id=session_id)
    )
    _log_json(result)
    return result


def log_follow(
    cli,
    *,
    file_name: str | None = None,
    session_id: str | None = None,
    interval: float = 1.0,
    max_entries: int = 50,
    max_lines: int | None = None,
    iterations: int | None = None,
    once: bool = False,
    no_clear: bool = False,
) -> dict:
    """Show a realtime/tail-style redacted log view with test-safe exit controls."""
    if file_name and session_id:
        raise ValueError(
            "log follow accepts either --file or --session-id, not both"
        )
    try:
        refresh_interval = float(interval)
    except (TypeError, ValueError) as exc:
        raise ValueError("--interval must be a non-negative number") from exc
    if refresh_interval < 0:
        raise ValueError("--interval must be a non-negative number")
    if once:
        iterations = 1
    if iterations is not None:
        try:
            iterations = int(iterations)
        except (TypeError, ValueError) as exc:
            raise ValueError("--iterations must be a positive integer") from exc
        if iterations <= 0:
            raise ValueError("--iterations must be a positive integer")

    service = PermissionLogSystemService(Path.cwd())
    rendered_snapshots = 0
    latest: dict[str, Any] | None = None
    while iterations is None or rendered_snapshots < iterations:
        latest = service.require_data(
            service.follow_log_snapshot(
                file_name=file_name,
                session_id=session_id,
                max_entries=max_entries,
                max_lines=max_lines,
            )
        )
        if rendered_snapshots and not no_clear:
            logger.info("-" * 40)
        logger.info(
            "Log storage: %s",
            latest.get("storage", {}).get("current_log_file")
            or latest.get("storage", {}).get("log_dir"),
        )
        logger.info(
            "Follow: interval=%ss max_entries=%s max_lines=%s exit=Ctrl+C",
            refresh_interval,
            latest.get("max_entries"),
            latest.get("max_lines") or "unlimited",
        )
        for line in latest.get("lines", []):
            logger.info("%s", redact_sensitive(str(line)))
        rendered_snapshots += 1
        if iterations is not None and rendered_snapshots >= iterations:
            break
        time.sleep(refresh_interval)
    result = dict(latest or {})
    result["refresh_interval"] = refresh_interval
    result["iterations"] = rendered_snapshots
    result["exit_mode"] = (
        "iterations" if iterations is not None else "keyboard_interrupt"
    )
    return result
