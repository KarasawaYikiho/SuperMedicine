from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cli_entry import CLI, main
from core.experience import (
    EXPERIENCE_LEARNING_ENABLED_BY_DEFAULT,
    ExperiencePrivacyError,
    ExperienceRecord,
    ExperienceStore,
    ExperienceValidationError,
)
from core.workspace import WorkspaceManager


def _store(tmp_path: Path, temp_path: Path) -> ExperienceStore:
    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        return ExperienceStore(tmp_path)


def _prepare_workspace(tmp_path, monkeypatch, *workspace_ids: str) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "core.experience.tempfile.gettempdir", lambda: str(tmp_path / "temp")
    )
    manager = WorkspaceManager(tmp_path)
    for workspace_id in workspace_ids or ("study-a",):
        manager.initialize_workspace(workspace_id)


# ═══ Experience Storage Tests ═══


def test_experience_learning_enabled_by_default_constant():
    assert EXPERIENCE_LEARNING_ENABLED_BY_DEFAULT is True


@pytest.mark.parametrize(
    ("payload", "expected_exception"),
    [
        (
            {
                "scope": "general",
                "title": "Unsafe",
                "summary": "A confirmed summary",
                "raw_conversation": "user said private details",
            },
            ExperiencePrivacyError,
        ),
        (
            ExperienceRecord(
                scope="general",
                title="Unsafe",
                summary="A confirmed summary",
                raw_conversation_stored=True,
            ),
            ExperiencePrivacyError,
        ),
        (
            {
                "scope": "general",
                "title": "Draft",
                "summary": "Suggested but not approved",
                "confirmed": False,
            },
            ExperienceValidationError,
        ),
    ],
)
def test_unsafe_or_unconfirmed_experience_is_rejected_without_persisting(
    tmp_path, payload, expected_exception
):
    temp_path = tmp_path / "temp"
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        with pytest.raises(expected_exception):
            store.store_confirmed_experience(payload)

    assert store.list_general_experiences() == []
    if isinstance(payload, dict) and "raw_conversation" in payload:
        assert not (temp_path / "supermedicine-rag-interface").exists()


def test_general_method_experience_writes_to_tempdir_layer(tmp_path):
    temp_path = tmp_path / "temp"
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        record = store.store_confirmed_general_experience(
            title="Use explicit verification handoff",
            summary="Keep implementation and verification responsibilities separate.",
            tags=["workflow"],
        )
        records = store.list_general_experiences()

    expected = (
        temp_path
        / "supermedicine-rag-interface"
        / "general-experience"
        / "confirmed.jsonl"
    )
    assert expected.is_file()
    assert records == [record]
    assert records[0].workspace_id is None
    assert records[0].raw_conversation_stored is False


def test_project_details_write_to_workspace_local_experience_path(tmp_path):
    temp_path = tmp_path / "temp"
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = _store(tmp_path, temp_path)

    record = store.store_confirmed_workspace_experience(
        workspace_id="study-a",
        title="Project-specific import note",
        summary="For this workspace, imported papers should be normalized before extraction.",
        tags=["project"],
    )

    expected = (
        tmp_path
        / "workspaces"
        / "study-a"
        / ".supermedicine"
        / "rag"
        / "local"
        / "experience"
        / "confirmed.jsonl"
    ).resolve()
    assert expected.is_file()
    assert store.list_workspace_experiences("study-a") == [record]


def test_workspace_a_cannot_list_workspace_b_local_memory(tmp_path):
    temp_path = tmp_path / "temp"
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("study-a")
    manager.initialize_workspace("study-b")
    store = _store(tmp_path, temp_path)

    record_b = store.store_confirmed_workspace_experience(
        workspace_id="study-b",
        title="B only",
        summary="This local memory belongs to workspace B.",
    )

    assert store.list_workspace_experiences("study-a") == []
    assert store.list_workspace_experiences("study-b") == [record_b]


def test_general_layer_can_be_listed_from_different_workspaces(tmp_path):
    temp_path = tmp_path / "temp"
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    project_a.mkdir()
    project_b.mkdir()
    store_a = _store(project_a, temp_path)
    store_b = _store(project_b, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        record = store_a.store_confirmed_general_experience(
            title="General method",
            summary="A reusable process detail without project identifiers.",
        )
        assert store_b.list_general_experiences() == [record]


def test_external_method_suggestion_stays_non_persisted_until_confirmed(tmp_path):
    temp_path = tmp_path / "temp"
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        suggestion = store.suggest_classification(
            workspace_id="study-a",
            title="External review cadence",
            summary=(
                "Borrow a general external project idea: separate implementation "
                "and verification handoff."
            ),
            tags=["external-method"],
        )

        assert suggestion.suggested_scope == "general"
        assert suggestion.confirmed is False
        assert store.list_general_experiences() == []
        assert store.list_workspace_experiences("study-a") == []

        confirmed = store.confirm_classification(
            workspace_id="study-a",
            scope=suggestion.suggested_scope,
            title=suggestion.title,
            summary=suggestion.summary,
            tags=suggestion.tags,
        )

        assert confirmed.scope == "general"
        assert confirmed.raw_conversation_stored is False
        assert store.list_general_experiences() == [confirmed]
        assert store.list_workspace_experiences("study-a") == []


def test_external_project_detail_suggestion_remains_workspace_local(tmp_path):
    temp_path = tmp_path / "temp"
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        suggestion = store.suggest_classification(
            workspace_id="study-a",
            title="External workflow adapted for study A",
            summary="Use the imported-paper normalization sequence for this project.",
            metadata={"paper_ids": ["pmid-123"], "contains_project_details": True},
        )
        confirmed = store.confirm_classification(
            workspace_id="study-a",
            scope=suggestion.suggested_scope,
            title=suggestion.title,
            summary=suggestion.summary,
            source={"paper_ids": ["pmid-123"]},
        )

        assert suggestion.suggested_scope == "workspace"
        assert confirmed.scope == "workspace"
        assert confirmed.workspace_id == "study-a"
        assert store.list_general_experiences() == []
        assert store.list_workspace_experiences("study-a") == [confirmed]


@pytest.mark.parametrize(
    "payload",
    [
        {"workspace_id": "study-a"},
        {"project_details": {"name": "secret"}},
        {"paper_ids": ["pmid-1"]},
        {"paper_paths": ["papers/originals/a.pdf"]},
        {"contains_project_details": True},
    ],
)
def test_project_detail_markers_rejected_from_general_layer(tmp_path, payload):
    temp_path = tmp_path / "temp"
    store = _store(tmp_path, temp_path)
    data = {
        "scope": "general",
        "title": "General",
        "summary": "Reusable method note.",
        **payload,
    }

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        with pytest.raises(ExperiencePrivacyError):
            store.store_confirmed_experience(data)

    assert store.list_general_experiences() == []


# ═══ Experience CLI Tests ═══


def test_suggested_classification_does_not_persist(tmp_path, monkeypatch):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")

    suggestion = CLI().experience_suggest(
        "study-a",
        "Use a repeatable review checklist.",
        title="Checklist",
    )

    assert suggestion["suggested_scope"] == "general"
    assert suggestion["confirmed"] is False
    store = ExperienceStore(tmp_path)
    assert store.list_general_experiences() == []
    assert store.list_workspace_experiences("study-a") == []


def test_confirm_writes_to_user_chosen_scope_overriding_suggestion(
    tmp_path, monkeypatch
):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")
    store = ExperienceStore(tmp_path)

    suggestion = store.suggest_classification(
        workspace_id="study-a",
        title="Suggested local",
        summary="This note mentions project_details and should be suggested local.",
    )
    created = CLI().experience_add(
        "study-a",
        "general",
        "Reusable method",
        "Use a generic extraction checklist without project identifiers.",
        tags=["method"],
        confirm=True,
    )

    assert suggestion.suggested_scope == "workspace"
    assert created["scope"] == "general"
    assert created["workspace_id"] is None
    assert [record.id for record in store.list_general_experiences()] == [created["id"]]
    assert store.list_workspace_experiences("study-a") == []


def test_cli_view_list_and_get_workspace_record(tmp_path, monkeypatch):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")
    cli = CLI()

    created = cli.experience_add(
        "study-a",
        "workspace",
        "Local import rule",
        "For this workspace, normalize imported files before extraction.",
        confirm=True,
    )
    listed = cli.experience_list("study-a")
    viewed = cli.experience_view(created["id"], "study-a", scope="workspace")
    fetched = ExperienceStore(tmp_path).get_experience(
        created["id"],
        workspace_id="study-a",
        scope="workspace",
    )

    assert [record["id"] for record in listed] == [created["id"]]
    assert viewed["id"] == created["id"]
    assert fetched.title == "Local import rule"
    assert fetched.workspace_id == "study-a"


def test_cli_edit_workspace_record(tmp_path, monkeypatch):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")
    cli = CLI()
    created = cli.experience_add(
        "study-a",
        "workspace",
        "Draft local rule",
        "Initial workspace note.",
        tags=["draft"],
        confirm=True,
    )

    edited = cli.experience_edit(
        created["id"],
        "study-a",
        "workspace",
        title="Edited local rule",
        summary="Edited workspace note.",
        tags=["edited"],
    )

    assert edited["id"] == created["id"]
    assert edited["title"] == "Edited local rule"
    assert edited["summary"] == "Edited workspace note."
    assert edited["tags"] == ["edited"]
    assert edited["created_at"] == created["created_at"]


def test_cli_delete_workspace_record_requires_matching_confirmation(
    tmp_path, monkeypatch
):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")
    cli = CLI()
    created = cli.experience_add(
        "study-a",
        "workspace",
        "Delete me",
        "Temporary workspace note.",
        confirm=True,
    )

    with pytest.raises(ValueError, match="confirm"):
        cli.experience_delete(created["id"], "study-a", "workspace", "wrong-id")

    deleted = cli.experience_delete(
        created["id"], "study-a", "workspace", created["id"]
    )

    assert deleted == {"status": "deleted", "id": created["id"], "scope": "workspace"}
    assert CLI().experience_list("study-a") == []


def test_export_workspace_records_as_json_and_markdown(tmp_path, monkeypatch):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")
    cli = CLI()
    created = cli.experience_add(
        "study-a",
        "workspace",
        "Exportable local rule",
        "Workspace export content.",
        tags=["export"],
        confirm=True,
    )

    exported_json = cli.experience_export("study-a", "json")
    exported_md = cli.experience_export("study-a", "md")

    parsed = json.loads(exported_json)
    assert [record["id"] for record in parsed] == [created["id"]]
    assert parsed[0]["scope"] == "workspace"
    assert "Exportable local rule" in exported_md
    assert created["id"] in exported_md
    assert "Workspace export content." in exported_md


def test_general_export_is_cross_workspace_and_rejects_project_details(
    tmp_path, monkeypatch
):
    _prepare_workspace(tmp_path, monkeypatch, "study-a", "study-b")
    cli = CLI()
    general = cli.experience_add(
        "study-a",
        "general",
        "Reusable review method",
        "Apply the same abstract checklist across projects.",
        confirm=True,
    )

    with pytest.raises(ExperiencePrivacyError):
        ExperienceStore(tmp_path).confirm_classification(
            workspace_id="study-a",
            scope="general",
            title="Unsafe general",
            summary="Reusable summary.",
            source={"project_details": {"secret": "study-a"}},
        )

    exported = json.loads(
        cli.experience_export("study-b", "json", include_general=True)
    )

    assert [record["id"] for record in exported] == [general["id"]]
    assert exported[0]["workspace_id"] is None
    assert "project_details" not in json.dumps(exported, ensure_ascii=False)
    assert "study-a" not in json.dumps(exported, ensure_ascii=False)


def test_workspace_export_excludes_other_workspace_records(tmp_path, monkeypatch):
    _prepare_workspace(tmp_path, monkeypatch, "study-a", "study-b")
    cli = CLI()
    record_a = cli.experience_add(
        "study-a",
        "workspace",
        "A only",
        "Only workspace A should see this.",
        confirm=True,
    )
    record_b = cli.experience_add(
        "study-b",
        "workspace",
        "B only",
        "Only workspace B should see this.",
        confirm=True,
    )

    exported_a = json.loads(cli.experience_export("study-a", "json"))

    assert [record["id"] for record in exported_a] == [record_a["id"]]
    assert record_b["id"] not in json.dumps(exported_a)


@pytest.mark.parametrize(
    "payload",
    [
        {"raw_conversation": "private transcript"},
        {"summary": "This contains a raw_conversation marker."},
        {"project_details": {"workspace": "secret"}},
        {"paper_paths": ["papers/originals/secret.pdf"]},
        {"summary": "This mentions workspace_id and cannot be general."},
    ],
)
def test_raw_conversation_and_project_markers_rejected(tmp_path, monkeypatch, payload):
    _prepare_workspace(tmp_path, monkeypatch, "study-a")
    data = {
        "workspace_id": "study-a",
        "scope": "general",
        "title": "Unsafe",
        "summary": "Reusable summary.",
        **payload,
    }

    with pytest.raises(ExperiencePrivacyError):
        ExperienceStore(tmp_path).store_confirmed_experience(data)


@pytest.mark.parametrize(
    "argv",
    [
        ["supermedicine", "experience", "suggest", "--summary", "Need workspace"],
        [
            "supermedicine",
            "experience",
            "add",
            "--scope",
            "workspace",
            "--title",
            "T",
            "--summary",
            "S",
            "--confirm",
        ],
        ["supermedicine", "experience", "list"],
        ["supermedicine", "experience", "view", "record-1"],
        [
            "supermedicine",
            "experience",
            "edit",
            "record-1",
            "--scope",
            "workspace",
            "--title",
            "T",
        ],
        [
            "supermedicine",
            "experience",
            "delete",
            "record-1",
            "--scope",
            "workspace",
            "--confirm",
            "record-1",
        ],
        ["supermedicine", "experience", "export", "--format", "json"],
    ],
)
def test_cli_experience_commands_require_explicit_workspace(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", argv)

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2


def test_cli_experience_does_not_read_tui_recent_state(tmp_path, monkeypatch):
    _prepare_workspace(tmp_path, monkeypatch, "study-a", "study-b")
    manager = WorkspaceManager(tmp_path)
    manager.save_recent_selection("study-a", "study-b")
    cli = CLI()
    record_a = cli.experience_add(
        "study-a",
        "workspace",
        "A explicit",
        "Explicit workspace A note.",
        confirm=True,
    )
    record_b = cli.experience_add(
        "study-b",
        "workspace",
        "B recent",
        "Recent selection should not be used.",
        confirm=True,
    )

    listed = cli.experience_list("study-a")

    assert [record["id"] for record in listed] == [record_a["id"]]
    assert record_b["id"] not in json.dumps(listed)
