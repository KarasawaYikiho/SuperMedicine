from __future__ import annotations

import json

import pytest

from core.log_report import LogReportError, LogReportStore


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


def test_list_show_and_summary_return_redacted_records(tmp_path):
    store = LogReportStore(tmp_path)
    session_log = store.write("password=hunter2", session_id="session-a")
    isolated_log = store.write("plain note")

    listed = store.list()
    shown = store.show(session_log["file"])
    summary = store.export_summary(session_id="session-a")

    assert [item["file"] for item in listed] == [isolated_log["file"], session_log["file"]]
    assert shown["file"] == session_log["file"]
    assert summary["log_count"] == 1
    assert summary["entry_count"] == 1
    assert "hunter2" not in json.dumps({"listed": listed, "shown": shown, "summary": summary}, ensure_ascii=False)


@pytest.mark.parametrize("file_name", ["../evil.json", "nested/evil.json", "evil.txt", "", "C:/evil.json"])
def test_show_rejects_unsafe_file_names(tmp_path, file_name):
    store = LogReportStore(tmp_path)

    with pytest.raises(LogReportError):
        store.show(file_name)


@pytest.mark.parametrize("message", ["", "   "])
def test_write_rejects_empty_messages(tmp_path, message):
    store = LogReportStore(tmp_path)

    with pytest.raises(LogReportError, match="--message cannot be empty"):
        store.write(message)


def test_session_ids_are_isolated_and_path_safe(tmp_path):
    store = LogReportStore(tmp_path)

    one = store.write("note one", session_id="session-one")
    two = store.write("note two", session_id="session-two")

    assert one["file"] != two["file"]
    assert store.summary(session_id="session-one")["entries"][0]["session_id"] == "session-one"
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
        store.write("second message that makes the serialized session log too large", session_id="size-session")

    assert log_path.read_text(encoding="utf-8") == before


def test_existing_non_log_json_is_not_overwritten_or_read(tmp_path):
    store = LogReportStore(tmp_path)
    log_dir = tmp_path / ".supermedicine" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "session-wb-session.json").write_text('{"not": "a log"}', encoding="utf-8")

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
    assert {entry["session_id"] for entry in summary["entries"]} == {"session-alpha", "session-beta"}
    assert "alpha-secret" not in dumped
    assert "beta-secret" not in dumped
    assert dumped.count("[REDACTED]") >= 2
