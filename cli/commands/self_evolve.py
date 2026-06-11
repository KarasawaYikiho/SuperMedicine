"""CLI commands: self-evolution."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cli.helpers import _self_evolution_cli_result
from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def self_evolve(
    cli,
    *,
    instruction: str,
    artifact_type: str,
    output: str | Path,
    access_mode: str = "sandbox",
    experience_source: str | None = None,
    workspace: str | None = None,
    preview: bool = True,
    confirm_write: bool = False,
    overwrite: bool = False,
    confirm_full_access: bool = False,
    acknowledge_risk: bool = False,
) -> dict[str, Any]:
    """Generate a self-evolution preview or confirmed artifact write."""
    from core.self_evolution import SelfEvolutionService
    from permission.audit import AuditLogger

    project_dir = Path.cwd()
    confirmed = bool(confirm_write and not preview)
    audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
    audit_logger = AuditLogger(audit_log) if confirmed else None

    result = SelfEvolutionService(project_dir).generate(
        user_intent=instruction,
        artifact_type=artifact_type,
        output_path=output,
        access_mode=access_mode,
        experience_source=experience_source,
        workspace_id=workspace,
        confirmed=confirmed,
        overwrite=overwrite,
        audit_logger=audit_logger,
        full_access_confirmed=confirm_full_access,
        risk_notice_acknowledged=acknowledge_risk,
        metadata={"cli_command": "self-evolve"},
    )
    cli_result = _self_evolution_cli_result(
        result,
        requested_access_mode=access_mode,
        requested_output=output,
        audit_log=audit_log,
        preview=not confirmed,
        confirm_write=confirm_write,
        confirm_full_access=confirm_full_access,
        acknowledge_risk=acknowledge_risk,
    )
    _log_json(cli_result)
    return cli_result
