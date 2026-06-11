"""CLI commands: experiment guide management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cli.helpers import (
    _dict_payload,
    _experiment_response,
    _load_experiment_session,
    _load_input_json,
    _save_experiment_session,
)
from cli.logging_setup import _log_json

logger = logging.getLogger(__name__)


def experiment_start(cli, protocol: str, session_id: str | None = None) -> dict:
    """Start a standalone experiment guide session and persist it as JSON."""
    from core.config_center import ConfigCenter
    from core.experiment_guide import (
        ExperimentGuide,
        MEDICAL_BOUNDARY,
        append_experiment_log_event,
    )
    from core.log_report import LogReportStore

    session = ExperimentGuide().create_session(protocol, session_id=session_id)
    ConfigCenter(
        Path.cwd() / ".supermedicine" / "config.yaml"
    ).set_selected_experiment_protocol(
        session.protocol.protocol_id,
        save=True,
    )
    session_file = (
        Path.cwd() / ".supermedicine" / "experiments" / f"{session.session_id}.json"
    )
    _save_experiment_session(session_file, session.to_dict())
    append_experiment_log_event(
        LogReportStore(Path.cwd()),
        "experiment_started",
        session,
        message="experiment guide session started",
    )
    result = _experiment_response(
        session, session_file=session_file, medical_boundary=MEDICAL_BOUNDARY
    )
    _log_json(result)
    return result


def experiment_list(cli) -> list[dict]:
    """List configured experiment protocols discovered from plugins/experiments."""
    from core.experiment_protocols import list_protocols

    result = [
        {
            "protocol_id": protocol.protocol_id,
            "title": protocol.title,
            "description": protocol.description,
            "version": protocol.version,
            "metadata": protocol.metadata,
            "step_count": len(protocol.steps),
        }
        for protocol in list_protocols()
    ]
    _log_json(result)
    return result


def experiment_context(cli, protocol: str | None = None) -> dict:
    """Show the experiment context and authoring rules injected into LLM chat."""
    from core.config_center import ConfigCenter
    from core.experiment_protocols import build_experiment_llm_context

    result = build_experiment_llm_context(protocol)
    selected = result.get("selected_protocol") if isinstance(result, dict) else None
    if protocol and isinstance(selected, dict) and selected.get("protocol_id"):
        ConfigCenter(
            Path.cwd() / ".supermedicine" / "config.yaml"
        ).set_selected_experiment_protocol(
            str(selected["protocol_id"]),
            save=True,
        )
        result["runtime_sync"] = {
            "selected_experiment_protocol": selected["protocol_id"],
            "message": "实验配置选择已同步到统一配置；后续 LLM 上下文会读取该协议。",
        }
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
    from core.experiment_protocols import (
        create_experiment_config_from_instruction,
        save_experiment_config,
    )

    if bool(instruction and instruction.strip()) == bool(
        config_json and config_json.strip()
    ):
        raise ValueError("provide exactly one of --instruction or --config-json")
    if config_json and config_json.strip():
        payload = _load_input_json(config_json)
        result = save_experiment_config(
            payload,
            filename=filename,
            overwrite=overwrite,
        )
    else:
        result = create_experiment_config_from_instruction(
            instruction or "",
            filename=filename,
            overwrite=overwrite,
        )
    protocol = result.get("protocol") if isinstance(result, dict) else None
    if isinstance(protocol, dict) and protocol.get("protocol_id"):
        from core.config_center import ConfigCenter

        ConfigCenter(
            Path.cwd() / ".supermedicine" / "config.yaml"
        ).set_selected_experiment_protocol(
            str(protocol["protocol_id"]),
            save=True,
        )
        result["runtime_sync"] = {
            "selected_experiment_protocol": protocol["protocol_id"],
            "message": "新增实验配置已同步为后续 LLM 上下文的当前实验。",
        }
    _log_json(result)
    return result


def experiment_show(cli, session_file: str | Path) -> dict:
    """Show a persisted experiment guide session."""
    from core.experiment_guide import ExperimentGuide, MEDICAL_BOUNDARY

    path = Path(session_file)
    session = ExperimentGuide().restore_session(_load_experiment_session(path))
    result = _experiment_response(
        session, session_file=path, medical_boundary=MEDICAL_BOUNDARY
    )
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
    """Submit data for the current experiment step, optionally running a configured calculation."""
    from core.experiment_guide import (
        CalculationResult,
        ExperimentGuide,
        MEDICAL_BOUNDARY,
        append_experiment_log_event,
    )
    from core.log_report import LogReportStore
    from plugins.tools.experiment_wb import main as wb_plugin

    path = Path(session_file)
    guide = ExperimentGuide()
    session = guide.restore_session(_load_experiment_session(path))
    payload = _load_input_json(input_json)
    user_input = _dict_payload(payload.get("user_input", payload), "user_input")
    outputs = _dict_payload(payload.get("outputs", {}), "outputs")
    calculation_params = _dict_payload(
        payload.get("calculation_params", {}), "calculation_params"
    )
    log_store = LogReportStore(Path.cwd())
    calculation_results: list[CalculationResult | dict[str, Any]] = []
    plugin_request: dict[str, Any] | None = None
    kernel_result: dict[str, Any] | None = None

    if calculate:
        requests = session.build_plugin_requests(
            step_id, calculation_params=calculation_params
        )
        if not requests:
            if session.protocol.protocol_id == "western_blot_basic":
                raise ValueError(
                    f"step {step_id} has no supported WB calculation request"
                )
            raise ValueError(
                f"step {step_id} has no supported experiment calculation request"
            )
        plugin_request = requests[0]
        if plugin_request.get("plugin_name") != "experiment-wb":
            raise ValueError(
                "CLI --calculate currently supports experiment-wb plugin requests only; "
                f"got {plugin_request.get('plugin_name')}"
            )
        kernel_result = wb_plugin.execute(
            plugin_request["action"],
            plugin_request["params"],
            plugin_request["metadata"],
        )
        if kernel_result.get("status") != "success":
            raise ValueError(
                str(kernel_result.get("error") or "WB calculation failed")
            )
        append_experiment_log_event(
            log_store,
            "plugin_result",
            session,
            step_id=step_id,
            plugin_request=plugin_request,
            kernel_result=kernel_result,
        )
        calculation_results.append(
            {
                "request_id": str(plugin_request["request_id"]),
                "status": "completed",
                "value": kernel_result.get("output"),
                "metadata": {
                    "plugin": kernel_result.get("plugin"),
                    "action": kernel_result.get("action"),
                    "metadata": kernel_result.get("metadata", {}),
                },
            }
        )

    record = session.submit_step(
        step_id,
        user_input,
        outputs=outputs,
        calculation_results=calculation_results,
    )
    _save_experiment_session(path, session.to_dict())
    append_experiment_log_event(
        log_store,
        "step_input_submitted",
        session,
        step_id=step_id,
        user_input=user_input,
        outputs=outputs,
        record=record.to_dict(),
    )
    append_experiment_log_event(
        log_store,
        "experiment_completed" if session.is_completed else "step_guidance",
        session,
        step_id=step_id,
        record=record.to_dict(),
    )
    result = _experiment_response(
        session,
        session_file=path,
        record=record.to_dict(),
        plugin_request=plugin_request,
        kernel_result=kernel_result,
        medical_boundary=MEDICAL_BOUNDARY,
    )
    _log_json(result)
    return result
