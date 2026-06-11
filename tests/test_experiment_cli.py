from __future__ import annotations

import json

import pytest

from cli_entry import CLI, main


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
