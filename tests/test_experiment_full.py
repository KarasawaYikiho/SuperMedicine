from __future__ import annotations

import json
import shutil
from typing import Any

import pytest
import yaml

from cli_entry import CLI, main
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
from core.plugin_registry import PluginRegistry
from permission.engine import PermissionEngine


# ═══ Experiment CLI Tests ═══


def test_experiment_start_persists_session_and_show_returns_current_step(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    started = CLI().experiment_start("wb", session_id="wb-session")
    session_file = tmp_path / ".supermedicine" / "experiments" / "wb-session.json"
    shown = CLI().experiment_show(session_file)

    assert started["session_file"] == str(session_file)
    assert session_file.is_file()
    assert started["session"]["session_id"] == "wb-session"
    assert started["current_step"]["step_id"] == "sample_preparation"
    assert shown["current_step"]["step_id"] == "sample_preparation"
    assert shown["progress"]["completed_steps"] == 0


def test_experiment_submit_advances_step_and_records_submitted_data(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    session_file = tmp_path / ".supermedicine" / "experiments" / "wb-session.json"
    CLI().experiment_start("wb", session_id="wb-session")

    result = CLI().experiment_submit(
        session_file,
        "sample_preparation",
        json.dumps(
            {
                "user_input": {"sample_id": "S1", "target_protein": "ACTB"},
                "outputs": {"sample_record": "ready"},
            }
        ),
    )
    saved = json.loads(session_file.read_text(encoding="utf-8"))

    assert result["record"]["step_id"] == "sample_preparation"
    assert result["record"]["user_input"]["sample_id"] == "S1"
    assert result["record"]["outputs"]["sample_record"] == "ready"
    assert result["current_step"]["step_id"] == "gel_electrophoresis"
    assert (
        saved["records"]["sample_preparation"]["user_input"]["target_protein"] == "ACTB"
    )


def test_experiment_submit_with_calculate_returns_wb_calculation_output(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    session_file = tmp_path / ".supermedicine" / "experiments" / "calc-session.json"
    CLI().experiment_start("wb", session_id="calc-session")

    result = CLI().experiment_submit(
        session_file,
        "sample_preparation",
        json.dumps(
            {
                "user_input": {"sample_id": "S1", "target_protein": "ACTB"},
                "calculation_params": {
                    "protein_loading_normalization": {
                        "target_protein_amount": 20,
                        "final_well_volume": 20,
                        "samples": [{"name": "A", "concentration": 2.0}],
                    }
                },
            }
        ),
        calculate=True,
    )

    assert result["plugin_request"]["plugin_name"] == "experiment-wb"
    assert result["kernel_result"]["status"] == "success"
    assert result["kernel_result"]["output"]["samples"][0]["sample_volume"] == 10.0
    assert (
        result["record"]["calculation_results"][0]["value"]["samples"][0][
            "diluent_volume"
        ]
        == 10.0
    )


def test_experiment_submit_calculate_rejects_step_without_supported_calculation(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    session_file = tmp_path / ".supermedicine" / "experiments" / "no-calc-session.json"
    CLI().experiment_start("wb", session_id="no-calc-session")
    CLI().experiment_submit(
        session_file,
        "sample_preparation",
        json.dumps({"user_input": {"sample_id": "S1", "target_protein": "ACTB"}}),
    )

    with pytest.raises(ValueError, match="has no supported WB calculation request"):
        CLI().experiment_submit(
            session_file,
            "gel_electrophoresis",
            json.dumps(
                {"user_input": {"gel_percentage": "10%", "run_condition": "120V 60min"}}
            ),
            calculate=True,
        )

    saved = json.loads(session_file.read_text(encoding="utf-8"))
    assert saved["current_step_index"] == 1
    assert "gel_electrophoresis" not in saved["records"]


def test_log_write_list_show_create_redacted_reports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    written = CLI().log_write("token=secret-token and note", session_id="wb-session")
    listed = CLI().log_list()
    shown = CLI().log_show(written["file"])

    assert (tmp_path / ".supermedicine" / "logs" / written["file"]).is_file()
    assert written["session_id"] == "wb-session"
    assert "secret-token" not in written["message"]
    assert "[REDACTED]" in written["message"]
    assert [item["file"] for item in listed] == [written["file"]]
    assert shown["report_id"] == written["report_id"]
    assert "secret-token" not in json.dumps(shown, ensure_ascii=False)


def test_experiment_submit_invalid_json_exits_with_argparse_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    session_file = CLI().experiment_start("wb", session_id="bad-json")["session_file"]

    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "experiment",
                "submit",
                "--session-file",
                session_file,
                "--step",
                "sample_preparation",
                "--input-json",
                "{",
            ]
        )

    assert excinfo.value.code == 2
    assert "--input-json must be valid JSON" in capsys.readouterr().err


def test_log_write_empty_message_exits_with_argparse_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        main(["log", "write", "--message", "   "])

    assert excinfo.value.code == 2
    assert "--message cannot be empty" in capsys.readouterr().err


def test_experiment_submit_wrong_step_exits_with_argparse_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    session_file = CLI().experiment_start("wb", session_id="wrong-step")["session_file"]

    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "experiment",
                "submit",
                "--session-file",
                session_file,
                "--step",
                "gel_electrophoresis",
                "--input-json",
                json.dumps(
                    {"user_input": {"sample_id": "S1", "target_protein": "ACTB"}}
                ),
            ]
        )

    assert excinfo.value.code == 2
    assert "expected step sample_preparation" in capsys.readouterr().err


# ═══ Experiment Guide Tests ═══


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


# ═══ Experiment Log Integration Tests ═══


def _message(record: dict[str, Any]) -> dict[str, Any]:
    return json.loads(record["message"])


def _submit_payload(step_id: str) -> dict[str, Any]:
    payloads: dict[str, dict[str, Any]] = {
        "sample_preparation": {
            "user_input": {
                "sample_id": "S1",
                "target_protein": "ACTB",
                "notes": "token=secret-token",
            },
            "outputs": {"sample_record": "ready"},
            "calculation_params": {
                "protein_loading_normalization": {
                    "target_protein_amount": 20,
                    "final_well_volume": 20,
                    "samples": [{"name": "A", "concentration": 2.0}],
                }
            },
        },
        "gel_electrophoresis": {
            "user_input": {"gel_percentage": "10%", "run_condition": "120V 60min"},
            "outputs": {"electrophoresis_record": "bands separated"},
        },
        "transfer": {
            "user_input": {
                "membrane_type": "PVDF",
                "transfer_condition": "wet transfer",
            },
            "outputs": {"transfer_record": "transfer complete"},
        },
        "blocking_and_antibody": {
            "user_input": {
                "blocking_buffer": "5% milk",
                "primary_antibody": "anti-ACTB",
                "secondary_antibody": "HRP",
            },
            "outputs": {"antibody_incubation_record": "overnight 4C"},
            "calculation_params": {
                "antibody_dilution": {
                    "total_volume": 1000,
                    "dilution_ratio": "1:1000",
                    "antibody_name": "anti-ACTB",
                }
            },
        },
        "detection_and_analysis": {
            "user_input": {
                "detection_method": "ECL",
                "image_reference": "image-1",
                "analysis_notes": "complete",
            },
            "outputs": {"analysis_record": "quantified"},
        },
    }
    return payloads[step_id]


def test_complete_wb_cli_flow_writes_structured_session_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session_id = "wb-complete-log"
    cli = CLI()

    started = cli.experiment_start("wb", session_id=session_id)
    session_file = started["session_file"]
    step_ids = [step["step_id"] for step in started["session"]["protocol"]["steps"]]

    for step_id in step_ids:
        payload = _submit_payload(step_id)
        cli.experiment_submit(
            session_file,
            step_id,
            json.dumps(payload),
            calculate=bool(payload.get("calculation_params")),
        )

    log_files = list((tmp_path / ".supermedicine" / "logs").glob("session-*.json"))
    assert [path.name for path in log_files] == [f"session-{session_id}.json"]

    report = json.loads(log_files[0].read_text(encoding="utf-8"))
    messages = [_message(record) for record in report["records"]]
    event_types = [message["event_type"] for message in messages]

    assert report["session_id"] == session_id
    assert event_types.count("experiment_started") == 1
    assert event_types.count("step_input_submitted") == len(step_ids)
    assert event_types.count("plugin_result") == 2
    assert event_types.count("step_guidance") == len(step_ids) - 1
    assert event_types[-1] == "experiment_completed"

    submitted_steps = [
        message["step_id"]
        for message in messages
        if message["event_type"] == "step_input_submitted"
    ]
    assert submitted_steps == step_ids
    assert all(
        "user_input" in message and "outputs" in message
        for message in messages
        if message["event_type"] == "step_input_submitted"
    )
    assert "secret-token" not in json.dumps(report, ensure_ascii=False)
    assert "[REDACTED]" in json.dumps(report, ensure_ascii=False)

    plugin_events = [
        message for message in messages if message["event_type"] == "plugin_result"
    ]
    assert {event["request_id"] for event in plugin_events} == {
        "protein_loading_normalization",
        "antibody_dilution",
    }
    assert all(event["plugin"] == "experiment-wb" for event in plugin_events)
    plugin_events_by_request = {event["request_id"]: event for event in plugin_events}
    assert (
        plugin_events_by_request["protein_loading_normalization"][
            "plugin_result_summary"
        ]["output"]["samples"][0]["sample_volume"]
        == 10.0
    )
    assert (
        plugin_events_by_request["antibody_dilution"]["plugin_result_summary"][
            "output"
        ]["antibody_volume"]
        == 1.0
    )

    guidance_events = [
        message for message in messages if message["event_type"] == "step_guidance"
    ]
    assert [event["next_step"]["step_id"] for event in guidance_events] == step_ids[1:]

    completion = messages[-1]
    assert completion["event_type"] == "experiment_completed"
    assert completion["status"] == "completed"
    assert completion["progress"]["completed_steps"] == len(step_ids)
    assert completion["completion"]["completed"] is True


# ═══ Experiment WB Plugin Tests ═══


def _plugin():
    registry = PluginRegistry("plugins")
    metas = registry.discover()
    meta = registry.get_meta("experiment-wb")
    assert meta is not None
    assert meta.name in [item.name for item in metas]
    return registry.get("experiment-wb")


def test_experiment_wb_plugin_is_discovered_with_actions():
    registry = PluginRegistry("plugins")
    registry.discover()
    meta = registry.get_meta("experiment-wb")

    assert meta is not None
    assert {item["id"] for item in meta.provides} == {
        "experiment.wb.normalize_loading",
        "experiment.wb.antibody_dilution",
    }


def test_normalize_loading_returns_deterministic_wb_volumes():
    result = _plugin().execute(
        "experiment.wb.normalize_loading",
        {
            "target_protein_amount": 20,
            "final_well_volume": 20,
            "max_sample_volume": 15,
            "samples": [
                {"name": "A", "concentration": 2.0},
                {"name": "B", "concentration": 1.0},
            ],
        },
    )

    assert result["status"] == "success"
    assert result["plugin"] == "experiment-wb"
    assert result["action"] == "experiment.wb.normalize_loading"
    output = result["output"]
    assert output["target_protein_amount"] == 20.0
    assert output["volume_unit"] == "ul"
    assert output["samples"][0]["sample_volume"] == 10.0
    assert output["samples"][0]["diluent_volume"] == 10.0
    assert output["samples"][0]["within_limits"] is True
    assert output["samples"][1]["sample_volume"] == 20.0
    assert output["samples"][1]["diluent_volume"] == 0.0
    assert output["samples"][1]["within_limits"] is False
    assert output["samples"][1]["warnings"][0]["code"] == "sample_volume_exceeds_max"
    assert (
        result["metadata"]["contract"]["calculation_scope"]
        == "deterministic_arithmetic"
    )


def test_antibody_dilution_returns_deterministic_reagent_volumes():
    result = _plugin().execute(
        "experiment.wb.antibody_dilution",
        {
            "total_volume": 10000,
            "dilution_ratio": "1:5000",
            "antibody_name": "anti-ACTB",
        },
    )

    assert result["status"] == "success"
    assert result["output"] == {
        "antibody_name": "anti-ACTB",
        "total_volume": 10000.0,
        "dilution_ratio": "1:5000",
        "antibody_volume": 2.0,
        "diluent_volume": 9998.0,
        "volume_unit": "ul",
    }


@pytest.mark.parametrize(
    ("action", "params", "expected_error_parts"),
    [
        (
            "experiment.wb.normalize_loading",
            {
                "target_protein_amount": 20,
                "samples": [{"name": "A", "concentration": 0}],
            },
            ("Invalid experiment-wb input", "concentration"),
        ),
        (
            "experiment.wb.antibody_dilution",
            {"total_volume": 1000},
            ("dilution_ratio is required",),
        ),
        (
            "experiment.wb.external_lookup",
            {"query": "should-not-run"},
            ("Unsupported experiment-wb action",),
        ),
    ],
)
def test_experiment_wb_plugin_errors_are_structured(
    action, params, expected_error_parts
):
    result = _plugin().execute(action, params)

    assert result["status"] == "plugin_error"
    assert result["plugin"] == "experiment-wb"
    assert result["action"] == action
    assert result["output"] is None
    assert all(part in result["error"] for part in expected_error_parts)
    assert (
        result["metadata"]["contract"]["calculation_scope"]
        == "deterministic_arithmetic"
    )
