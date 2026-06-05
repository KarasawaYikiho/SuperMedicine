from __future__ import annotations

import json

import pytest

from core.tui.dialog_history import DialogHistoryPrivacyError, DialogHistoryStore
from core.workspace import WorkspaceManager


def test_dialog_history_appends_and_loads_summary_events_only(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = DialogHistoryStore(tmp_path)

    event = store.append_event(
        "study-a",
        event="screen_opened",
        summary="用户打开工作区屏幕",
        metadata={"screen": "工作区"},
        session_id="session1",
    )
    loaded = store.load_events("study-a", session_id="session1")

    assert loaded[0].id == event.id
    assert loaded[0].summary == "用户打开工作区屏幕"
    assert (
        store.history_path("study-a", "session1").parent
        == tmp_path / "workspaces" / "study-a" / ".supermedicine" / "sessions"
    )


def test_dialog_history_rejects_raw_conversation_fields(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = DialogHistoryStore(tmp_path)

    with pytest.raises(DialogHistoryPrivacyError, match="原始对话"):
        store.append_event(
            "study-a",
            event="bad",
            summary="摘要",
            metadata={"messages": ["raw"]},
        )


def test_dialog_history_rejects_raw_conversation_on_reload(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = DialogHistoryStore(tmp_path)
    path = store.history_path("study-a")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"event": "bad", "summary": "contains raw_conversation marker"},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DialogHistoryPrivacyError):
        store.load_events("study-a")
