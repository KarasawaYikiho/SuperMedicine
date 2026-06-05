from __future__ import annotations

import json
import pytest
import shutil
import yaml

from core.experiment_guide import (
    CalculationResult,
    ExperimentGuide,
    ExperimentGuideError,
    ExperimentSession,
    ExperimentStatus,
    build_experiment_log_event,
)
from core.experiment_protocols import (
    build_experiment_llm_context,
    get_protocol,
    list_protocols,
    load_protocols,
)
from core.kernel import Kernel
from permission.engine import PermissionEngine


def _kernel_with_real_plugins(tmp_path):
    (tmp_path / "config.yaml").write_text(
        yaml.dump({"project": "test"}), encoding="utf-8"
    )
    (tmp_path / "policies").mkdir()
    shutil.copyfile(
        PermissionEngine.default_policy_path(),
        tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
    )
    return Kernel(
        config_path=tmp_path / "config.yaml",
        plugins_dir="plugins",
        policies_dir=tmp_path / "policies",
    )


def test_builtin_wb_protocol_is_available():
    protocols = list_protocols()
    assert any(protocol.protocol_id == "western_blot_basic" for protocol in protocols)
    protocol = get_protocol("wb")
    assert protocol.steps[0].step_id == "sample_preparation"
    assert protocol.steps[0].calculation_requests[0].kind == "normalization"


def test_experiment_config_loader_scans_unified_directory_and_alias_switches(tmp_path):
    config_dir = tmp_path / "plugins" / "experiments"
    config_dir.mkdir(parents=True)
    (config_dir / "cell_assay.yaml").write_text(
        yaml.safe_dump(
            {
                "protocol_id": "cell_assay",
                "title": "Cell Assay",
                "description": "Custom cell assay protocol",
                "metadata": {"aliases": ["cell", "viability"]},
                "steps": [
                    {
                        "step_id": "seed_cells",
                        "title": "Seed cells",
                        "instructions": "Record density and plate layout.",
                        "input_fields": [
                            {"name": "density", "label": "Density", "required": True}
                        ],
                        "expected_outputs": ["plate_map"],
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "qpcr.json").write_text(
        json.dumps(
            {
                "protocol_id": "qpcr_basic",
                "title": "qPCR Basic",
                "description": "qPCR protocol",
                "metadata": {"aliases": ["qpcr"]},
                "steps": [
                    {
                        "step_id": "prepare_plate",
                        "title": "Prepare plate",
                        "instructions": "Record primers and template amount.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    protocols, sources = load_protocols(config_dir)

    assert sorted({protocol.protocol_id for protocol in protocols.values()}) == [
        "cell_assay",
        "qpcr_basic",
    ]
    assert protocols["cell"].protocol_id == "cell_assay"
    assert protocols["viability"].steps[0].input_fields[0].name == "density"
    assert protocols["qpcr"].protocol_id == "qpcr_basic"
    assert sources["cell"] == config_dir / "cell_assay.yaml"


def test_experiment_llm_context_reflects_selected_protocol_switch():
    available = {protocol.protocol_id: protocol for protocol in list_protocols()}
    assert "western_blot_basic" in available
    assert "cell_culture_basic" in available

    context = build_experiment_llm_context("cell_culture_basic")

    assert context["selected_protocol"]["protocol_id"] == "cell_culture_basic"
    assert context["selected_protocol"]["protocol_id"] != "western_blot_basic"
    assert any(
        item["protocol_id"] == "western_blot_basic"
        for item in context["available_protocols"]
    )
    assert any(
        item["protocol_id"] == "cell_culture_basic"
        for item in context["available_protocols"]
    )
    assert "plugins/experiments/" in context["authoring_rules"]


def test_create_experiment_session_and_read_current_step():
    session = ExperimentGuide().create_session("wb", session_id="exp-1")
    assert session.session_id == "exp-1"
    assert session.status == ExperimentStatus.IN_PROGRESS
    assert session.current_step.step_id == "sample_preparation"
    assert session.progress == {
        "current_step_index": 0,
        "completed_steps": 0,
        "total_steps": len(session.protocol.steps),
    }


def test_submit_user_data_records_input_output_and_advances():
    session = ExperimentGuide().create_session("wb")
    record = session.submit_step(
        "sample_preparation",
        {"sample_id": "S1", "target_protein": "ACTB"},
        outputs={"sample_record": "ready"},
        calculation_results=[
            CalculationResult(
                request_id="protein_loading_normalization",
                status="deferred",
                metadata={"plugin": "pending"},
            )
        ],
    )
    assert record.completed is True
    assert session.records["sample_preparation"].user_input["sample_id"] == "S1"
    assert session.records["sample_preparation"].outputs["sample_record"] == "ready"
    assert (
        session.records["sample_preparation"].calculation_results[0].status
        == "deferred"
    )
    assert session.current_step.step_id == "gel_electrophoresis"


def test_advance_requires_completed_current_step():
    session = ExperimentGuide().create_session("wb")
    with pytest.raises(ExperimentGuideError):
        session.advance()
    assert session.status == ExperimentStatus.ERROR
    assert "cannot advance" in session.error


def test_experiment_completes_after_last_step():
    session = ExperimentGuide().create_session("wb")
    for step in session.protocol.steps:
        user_input = {
            field.name: f"value-{field.name}"
            for field in step.input_fields
            if field.required
        }
        session.submit_step(step.step_id, user_input)
    assert session.is_completed is True
    assert session.status == ExperimentStatus.COMPLETED
    assert session.current_step is None
    assert session.progress["completed_steps"] == len(session.protocol.steps)


def test_illegal_step_input_sets_error_state():
    session = ExperimentGuide().create_session("wb")
    with pytest.raises(ExperimentGuideError):
        session.submit_step("gel_electrophoresis", {})
    assert session.status == ExperimentStatus.ERROR
    assert "expected step" in session.error


def test_missing_required_input_sets_error_state():
    session = ExperimentGuide().create_session("wb")
    with pytest.raises(ExperimentGuideError):
        session.submit_step("sample_preparation", {"sample_id": "S1"})
    assert session.status == ExperimentStatus.ERROR
    assert "target_protein" in session.error


def test_recover_from_error_and_continue():
    session = ExperimentGuide().create_session("wb")
    with pytest.raises(ExperimentGuideError):
        session.submit_step("wrong", {})
    session.recover()
    assert session.status == ExperimentStatus.IN_PROGRESS
    assert session.error is None
    session.submit_step(
        "sample_preparation",
        {"sample_id": "S1", "target_protein": "ACTB"},
    )
    assert session.current_step.step_id == "gel_electrophoresis"


def test_session_state_round_trip_restores_progress_and_records():
    session = ExperimentGuide().create_session("wb", metadata={"workspace": "demo"})
    session.submit_step(
        "sample_preparation",
        {"sample_id": "S1", "target_protein": "ACTB"},
        calculation_results=[
            {
                "request_id": "protein_loading_normalization",
                "status": "completed",
                "value": 20,
                "unit": "ug",
            }
        ],
    )
    restored = ExperimentSession.from_dict(session.to_dict())
    assert restored.metadata["workspace"] == "demo"
    assert restored.current_step.step_id == "gel_electrophoresis"
    assert restored.records["sample_preparation"].calculation_results[0].value == 20
    assert restored.records["sample_preparation"].calculation_results[0].unit == "ug"


def test_build_experiment_log_event_redacts_and_bounds_sensitive_payloads():
    session = ExperimentGuide().create_session("wb", session_id="exp-log-event")
    long_note = "x" * 600

    event = build_experiment_log_event(
        "step_input_submitted",
        session,
        step_id="sample_preparation",
        user_input={
            "sample_id": "S1",
            "notes": f"api_key=sk-experiment-secret {long_note}",
            "replicates": [{"token": f"secret-{index}"} for index in range(12)],
        },
        outputs={"sample_record": "ready"},
        message="captured from integration path",
    )

    dumped = yaml.safe_dump(event, allow_unicode=True)
    assert event["event_type"] == "step_input_submitted"
    assert event["session_id"] == "exp-log-event"
    assert event["next_step"]["step_id"] == "sample_preparation"
    assert "sk-experiment-secret" not in dumped
    assert "[REDACTED]" in dumped
    assert event["user_input"]["replicates"][-1] == {"truncated_items": 2}
    assert str(event["user_input"]["notes"]).endswith("...<truncated>")


def test_restored_error_state_can_recover():
    session = ExperimentGuide().create_session("wb")
    with pytest.raises(ExperimentGuideError):
        session.submit_step("wrong", {})
    restored = ExperimentGuide().restore_session(session.to_dict())
    assert restored.status == ExperimentStatus.ERROR
    restored.recover()
    assert restored.status == ExperimentStatus.IN_PROGRESS


def test_experiment_session_builds_serializable_plugin_request():
    session = ExperimentGuide().create_session("wb", session_id="exp-1")

    requests = session.build_plugin_requests(
        "sample_preparation",
        calculation_params={
            "protein_loading_normalization": {
                "target_protein_amount": 20,
                "samples": [{"name": "A", "concentration": 2.0}],
            }
        },
    )

    assert requests == [
        {
            "request_id": "protein_loading_normalization",
            "kind": "normalization",
            "description": "预留蛋白上样量归一化计算请求。",
            "plugin_name": "experiment-wb",
            "action": "experiment.wb.normalize_loading",
            "params": {
                "target_protein_amount": 20,
                "samples": [{"name": "A", "concentration": 2.0}],
            },
            "task": "experiment calculation exp-1 sample_preparation protein_loading_normalization",
            "metadata": {
                "session_id": "exp-1",
                "protocol_id": "western_blot_basic",
                "step_id": "sample_preparation",
            },
        }
    ]


def test_experiment_guide_calls_wb_plugin_through_kernel_permission_path(tmp_path):
    guide = ExperimentGuide()
    session = guide.create_session("wb", session_id="exp-allowed")
    kernel = _kernel_with_real_plugins(tmp_path)

    result = guide.execute_step_calculation(
        kernel,
        session,
        "sample_preparation",
        {"sample_id": "S1", "target_protein": "ACTB"},
        calculation_params={
            "protein_loading_normalization": {
                "target_protein_amount": 20,
                "final_well_volume": 20,
                "samples": [{"name": "A", "concentration": 2.0}],
            }
        },
        outputs={"sample_record": "ready"},
        agent_id="alpha",
    )

    assert result["status"] == "success"
    assert result["kernel_result"]["metadata"]["security"]["permission_checked"] is True
    assert (
        result["kernel_result"]["metadata"]["security"]["permission_entrypoint"]
        == "kernel"
    )
    assert result["plugin_request"]["plugin_name"] == "experiment-wb"
    assert (
        result["record"]["calculation_results"][0]["request_id"]
        == "protein_loading_normalization"
    )
    assert (
        result["record"]["calculation_results"][0]["value"]["samples"][0][
            "sample_volume"
        ]
        == 10.0
    )
    assert result["next_step"]["step_id"] == "gel_electrophoresis"


def test_experiment_guide_denies_unauthorized_kernel_plugin_call(tmp_path):
    guide = ExperimentGuide()
    session = guide.create_session("wb", session_id="exp-denied")
    kernel = _kernel_with_real_plugins(tmp_path)

    result = guide.execute_step_calculation(
        kernel,
        session,
        "sample_preparation",
        {"sample_id": "S1", "target_protein": "ACTB"},
        calculation_params={
            "protein_loading_normalization": {
                "target_protein_amount": 20,
                "samples": [{"name": "A", "concentration": 2.0}],
            }
        },
        agent_id="unknown-agent",
    )

    assert result["status"] == "denied"
    assert result["kernel_result"]["metadata"]["security"]["permission_checked"] is True
    assert result["kernel_result"]["metadata"]["security"]["permission"] == "denied"
    assert result["record"] is None
    assert session.current_step.step_id == "sample_preparation"
    assert "sample_preparation" not in session.records
