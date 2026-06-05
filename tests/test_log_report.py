from __future__ import annotations

import io
import json
import logging
import sys

import pytest

from core.log_report import (
    LogReportError,
    LogReportLoggingHandler,
    LogReportStore,
    append_tui_stream_output,
    configure_tui_log_storage,
    format_log_message,
)


def test_log_directory_is_created_and_isolated_log_is_redacted(tmp_path):
    store = LogReportStore(tmp_path)

    written = store.write("api_key=secret-value observation")

    log_path = tmp_path / ".supermedicine" / "logs" / written["file"]
    saved = log_path.read_text(encoding="utf-8")
    assert log_path.is_file()
    assert "secret-value" not in saved
    assert "[REDACTED]" in saved
    assert written["entry_count"] == 1


def test_session_writes_append_to_one_redacted_log(tmp_path):
    store = LogReportStore(tmp_path)

    first = store.write("token=first-token", session_id="wb-session")
    second = store.write("Bearer second-token", session_id="wb-session")
    shown = store.show(first["file"])

    assert first["file"] == second["file"] == "session-wb-session.json"
    assert second["entry_count"] == 2
    assert len(shown["records"]) == 2
    assert "first-token" not in json.dumps(shown, ensure_ascii=False)
    assert "second-token" not in json.dumps(shown, ensure_ascii=False)


def test_log_report_redacts_request_headers_body_url_query_and_private_key(tmp_path):
    store = LogReportStore(tmp_path)
    secret = "sk-log-report-request-secret"
    private_material = "MIIEvlogreportprivatekeymaterial"
    message = json.dumps(
        {
            "headers": {
                "Authorization": f"Bearer {secret}",
                "Cookie": "sid=log-report-cookie-secret",
            },
            "url": f"https://example.test/v1?api_key={secret}&ok=1",
            "body": {
                "password": "log-report-password-secret",
                "private_key": (
                    "-----BEGIN PRIVATE KEY-----\n"
                    f"{private_material}\n"
                    "-----END PRIVATE KEY-----"
                ),
            },
        }
    )

    written = store.write(message, session_id="request-redaction")
    log_path = tmp_path / ".supermedicine" / "logs" / written["file"]
    persisted = log_path.read_text(encoding="utf-8")
    returned = json.dumps(store.show(written["file"]), ensure_ascii=False)

    for text in (persisted, returned):
        assert secret not in text
        assert "log-report-cookie-secret" not in text
        assert "log-report-password-secret" not in text
        assert private_material not in text
        assert "[REDACTED]" in text


def test_log_report_keeps_business_fields_while_redacting_error_payload(tmp_path):
    store = LogReportStore(tmp_path)
    secret = "sk-business-error-secret"
    payload = {
        "event": "paper_import",
        "status": "failed",
        "workspace_id": "study-visible",
        "paper_count": 2,
        "error": {
            "message": f"provider rejected Authorization: Bearer {secret}",
            "request": {
                "headers": {
                    "Authorization": f"Bearer {secret}",
                    "X-Api-Key": secret,
                },
                "url": f"https://example.test/v1?api_key={secret}&page=1",
            },
        },
    }

    written = store.write(json.dumps(payload), session_id="business-regression")
    shown = store.show(written["file"])
    persisted = (
        tmp_path / ".supermedicine" / "logs" / written["file"]
    ).read_text(encoding="utf-8")
    combined = json.dumps({"shown": shown, "persisted": persisted}, ensure_ascii=False)

    assert secret not in combined
    assert "[REDACTED]" in combined
    assert "paper_import" in combined
    assert "study-visible" in combined
    assert "paper_count" in combined
    assert "page=1" in combined


def test_list_show_and_summary_return_redacted_records(tmp_path):
    store = LogReportStore(tmp_path)
    session_log = store.write("password=hunter2", session_id="session-a")
    isolated_log = store.write("plain note")

    listed = store.list()
    shown = store.show(session_log["file"])
    summary = store.export_summary(session_id="session-a")

    assert [item["file"] for item in listed] == [
        isolated_log["file"],
        session_log["file"],
    ]
    assert shown["file"] == session_log["file"]
    assert summary["log_count"] == 1
    assert summary["entry_count"] == 1
    assert "hunter2" not in json.dumps(
        {"listed": listed, "shown": shown, "summary": summary}, ensure_ascii=False
    )


@pytest.mark.parametrize(
    "file_name", ["../evil.json", "nested/evil.json", "evil.txt", "", "C:/evil.json"]
)
def test_show_rejects_unsafe_file_names(tmp_path, file_name):
    store = LogReportStore(tmp_path)

    with pytest.raises(LogReportError):
        store.show(file_name)


@pytest.mark.parametrize("message", ["", "   "])
def test_write_rejects_empty_messages(tmp_path, message):
    store = LogReportStore(tmp_path)

    with pytest.raises(LogReportError, match="--message cannot be empty"):
        store.write(message)


def test_append_rejects_empty_messages(tmp_path):
    store = LogReportStore(tmp_path)

    with pytest.raises(LogReportError, match="--message cannot be empty"):
        store.append("   ", session_id="empty-session")


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("operation failed", "【Error】 operation failed"),
        ("warning: low disk", "warning: low disk"),
        ("【Debug】 verbose details", "【Debug】 verbose details"),
        ("saved successfully", "【Success】 saved successfully"),
        ("plain update", "【Info】 plain update"),
    ],
)
def test_format_log_message_adds_representative_labels_without_duplicates(
    message, expected
):
    assert format_log_message(message) == expected


def test_list_and_summary_display_severity_labels_but_raw_records_stay_unprefixed(
    tmp_path,
):
    store = LogReportStore(tmp_path)

    written = store.write("operation failed", session_id="severity-session")
    shown = store.show(written["file"])
    listed = store.list()
    summary = store.summary(session_id="severity-session")

    assert shown["message"] == "operation failed"
    assert shown["records"][0]["message"] == "operation failed"
    assert shown["severity"] == "Error"
    assert listed[0]["message"] == "【Error】 operation failed"
    assert listed[0]["severity"] == "Error"
    assert summary["entries"][0]["message"] == "【Error】 operation failed"
    assert summary["entries"][0]["severity"] == "Error"


def test_structured_json_record_message_remains_json_decodable(tmp_path):
    store = LogReportStore(tmp_path)
    structured = {"event": "experiment_log", "status": "ok", "value": 3}

    written = store.write(json.dumps(structured), session_id="experiment-json")
    shown = store.show(written["file"])
    raw_payload = json.loads(
        (tmp_path / ".supermedicine" / "logs" / written["file"]).read_text(
            encoding="utf-8"
        )
    )

    assert json.loads(shown["records"][0]["message"]) == structured
    assert shown["message"].startswith("{")
    assert json.loads(raw_payload["records"][0]["message"]) == structured
    assert store.list()[0]["message"].startswith("【Success】 {")


def test_session_ids_are_isolated_and_path_safe(tmp_path):
    store = LogReportStore(tmp_path)

    one = store.write("note one", session_id="session-one")
    two = store.write("note two", session_id="session-two")

    assert one["file"] != two["file"]
    assert (
        store.summary(session_id="session-one")["entries"][0]["session_id"]
        == "session-one"
    )
    with pytest.raises(LogReportError):
        store.write("bad", session_id="../outside")


def test_write_rejects_messages_over_configured_limit(tmp_path):
    store = LogReportStore(tmp_path, max_message_length=5)

    with pytest.raises(LogReportError, match="maximum length"):
        store.write("123456")


def test_session_record_limit_is_enforced(tmp_path):
    store = LogReportStore(tmp_path, max_records_per_session=1)

    store.write("first", session_id="limited-session")

    with pytest.raises(LogReportError, match="record limit"):
        store.write("second", session_id="limited-session")


def test_file_size_limit_is_enforced_without_overwriting_existing_log(tmp_path):
    store = LogReportStore(tmp_path, max_file_bytes=220)

    with pytest.raises(LogReportError, match="file size limit"):
        store.write("message large enough for json envelope")

    log_dir = tmp_path / ".supermedicine" / "logs"
    assert not list(log_dir.glob("*.json"))


def test_file_size_limit_is_enforced_for_session_append_without_mutating_file(tmp_path):
    store = LogReportStore(tmp_path, max_file_bytes=700)
    first = store.write("first", session_id="size-session")
    log_path = tmp_path / ".supermedicine" / "logs" / first["file"]
    before = log_path.read_text(encoding="utf-8")

    with pytest.raises(LogReportError, match="file size limit"):
        store.write(
            "second message that makes the serialized session log too large",
            session_id="size-session",
        )

    assert log_path.read_text(encoding="utf-8") == before


def test_existing_non_log_json_is_not_overwritten_or_read(tmp_path):
    store = LogReportStore(tmp_path)
    log_dir = tmp_path / ".supermedicine" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "session-wb-session.json").write_text(
        '{"not": "a log"}', encoding="utf-8"
    )

    with pytest.raises(LogReportError, match="non-log JSON"):
        store.write("new note", session_id="wb-session")
    with pytest.raises(LogReportError, match="non-log JSON"):
        store.show("session-wb-session.json")


def test_summary_all_logs_preserves_session_boundaries_and_redaction(tmp_path):
    store = LogReportStore(tmp_path)
    store.write("session alpha api_key=alpha-secret", session_id="session-alpha")
    store.write("session beta token=beta-secret", session_id="session-beta")

    summary = store.summary()
    dumped = json.dumps(summary, ensure_ascii=False)

    assert summary["log_count"] == 2
    assert summary["entry_count"] == 2
    assert {entry["session_id"] for entry in summary["entries"]} == {
        "session-alpha",
        "session-beta",
    }
    assert "alpha-secret" not in dumped
    assert "beta-secret" not in dumped
    assert dumped.count("[REDACTED]") >= 2


def test_statistics_count_exact_entries_without_cross_file_leakage(tmp_path):
    store = LogReportStore(tmp_path)
    alpha_first = store.write("alpha failed", session_id="alpha", severity="Error")
    store.write("alpha saved", session_id="alpha", severity="Success")
    store.write("beta warning", session_id="beta", severity="Warning")
    store.write("standalone debug", severity="Debug")

    alpha_entries = store.list_entries(session_id="alpha")
    alpha_file_entries = store.list_entries(file_name=alpha_first["file"])
    all_entries = store.list_entries()

    assert len(alpha_entries) == 2
    assert {entry["session_id"] for entry in alpha_entries} == {"alpha"}
    assert store.statistics_for_entries(alpha_entries)["severity_counts"] == {
        "Error": 1,
        "Warning": 0,
        "Info": 0,
        "Debug": 0,
        "Success": 1,
    }
    assert store.statistics_for_entries(alpha_file_entries)["entry_count"] == 2
    assert store.statistics_for_entries(all_entries)["severity_counts"] == {
        "Error": 1,
        "Warning": 1,
        "Info": 0,
        "Debug": 1,
        "Success": 1,
    }


def test_statistics_deduplicates_same_entry_identity(tmp_path):
    store = LogReportStore(tmp_path)
    store.write("warning: once", session_id="dedupe", severity="Warning")
    entry = store.list_entries(session_id="dedupe")[0]

    statistics = store.statistics_for_entries([entry, dict(entry)])

    assert statistics["entry_count"] == 1
    assert statistics["severity_counts"]["Warning"] == 1


def test_tui_stream_output_is_routed_by_stream_severity_and_session(tmp_path):
    append_tui_stream_output(tmp_path, "stdout", "normal output")
    append_tui_stream_output(tmp_path, "stderr", "problem output")

    entries = LogReportStore(tmp_path).list_entries(session_id="tui-application")

    assert [entry["severity"] for entry in entries] == ["Info", "Error"]
    assert all(entry["session_id"] == "tui-application" for entry in entries)
    assert entries[0]["raw_message"] == "captured stdout: normal output"
    assert entries[1]["raw_message"] == "captured stderr: problem output"


def test_tui_stream_output_redacts_sensitive_stdout_and_stderr_before_persisting(tmp_path):
    secret = "sk-tui-stream-secret"

    append_tui_stream_output(
        tmp_path,
        "stdout",
        f"Authorization: Bearer {secret} url=https://example.test?token={secret}",
    )
    append_tui_stream_output(tmp_path, "stderr", "password=tui-stream-password")

    log_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / ".supermedicine" / "logs").glob("*.json")
    )
    entries_text = json.dumps(
        LogReportStore(tmp_path).list_entries(session_id="tui-application"),
        ensure_ascii=False,
    )

    assert secret not in log_text
    assert secret not in entries_text
    assert "tui-stream-password" not in log_text
    assert "tui-stream-password" not in entries_text
    assert "[REDACTED]" in log_text


def test_configure_tui_log_storage_replaces_console_routing_with_log_handler(
    tmp_path, monkeypatch
):
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    named_logger = logging.getLogger("core.tui_log_storage_test")
    original_named_handlers = list(named_logger.handlers)
    original_named_propagate = named_logger.propagate
    console_capture = io.StringIO()

    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in list(named_logger.handlers):
        named_logger.removeHandler(handler)

    monkeypatch.setattr(sys, "stderr", console_capture)
    root.addHandler(logging.StreamHandler(sys.stderr))
    named_logger.addHandler(logging.StreamHandler(sys.stderr))
    named_logger.propagate = False

    try:
        configure_tui_log_storage(tmp_path)
        named_logger.error("console isolated failure")

        assert all(
            isinstance(handler, LogReportLoggingHandler) for handler in root.handlers
        )
        assert named_logger.handlers == []
        assert named_logger.propagate is True
        assert console_capture.getvalue() == ""
        entries = LogReportStore(tmp_path).list_entries(session_id="tui-application")
        assert len(entries) == 1
        assert entries[0]["severity"] == "Error"
        assert "console isolated failure" in entries[0]["raw_message"]
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)
        for handler in list(named_logger.handlers):
            named_logger.removeHandler(handler)
            handler.close()
        for handler in original_named_handlers:
            named_logger.addHandler(handler)
        named_logger.propagate = original_named_propagate
