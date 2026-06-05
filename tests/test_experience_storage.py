from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

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


def test_experience_learning_enabled_by_default_constant():
    assert EXPERIENCE_LEARNING_ENABLED_BY_DEFAULT is True


def test_raw_conversation_field_rejected_and_not_persisted(tmp_path):
    temp_path = tmp_path / "temp"
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        with pytest.raises(ExperiencePrivacyError):
            store.store_confirmed_experience(
                {
                    "scope": "general",
                    "title": "Unsafe",
                    "summary": "A confirmed summary",
                    "raw_conversation": "user said private details",
                }
            )

    assert not (temp_path / "supermedicine-rag-interface").exists()


def test_raw_conversation_stored_true_rejected(tmp_path):
    temp_path = tmp_path / "temp"
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        with pytest.raises(ExperiencePrivacyError):
            store.store_confirmed_experience(
                ExperienceRecord(
                    scope="general",
                    title="Unsafe",
                    summary="A confirmed summary",
                    raw_conversation_stored=True,
                )
            )

    assert store.list_general_experiences() == []


def test_unconfirmed_summary_is_not_persisted(tmp_path):
    temp_path = tmp_path / "temp"
    store = _store(tmp_path, temp_path)

    with patch("core.experience.tempfile.gettempdir", return_value=str(temp_path)):
        with pytest.raises(ExperienceValidationError):
            store.store_confirmed_experience(
                {
                    "scope": "general",
                    "title": "Draft",
                    "summary": "Suggested but not approved",
                    "confirmed": False,
                }
            )

    assert store.list_general_experiences() == []


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
