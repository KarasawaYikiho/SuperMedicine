from __future__ import annotations

import json
from typing import Any

from Cli import CLI


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
