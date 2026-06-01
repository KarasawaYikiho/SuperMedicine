from __future__ import annotations

import inspect

import pytest

from core.tui.screens.experience import ExperienceScreenController
from core.tui.i18n import t
from core.tui.screens.experience_screen import ExperienceView
from core.workspace import WorkspaceManager


def test_experience_screen_suggest_requires_later_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    suggestion = controller.suggest_classification("study-a", title="方法", summary="总结事件")

    assert suggestion["label"] == "经验分类建议"
    assert suggestion["confirmed"] is False
    assert controller.list_experiences("study-a") == []


def test_experience_screen_empty_state_and_confirmation_copy_are_chinese(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    assert controller.list_experiences("study-a") == []
    assert t("experience_no_records") == "暂无经验记录"
    with pytest.raises(ValueError, match="最终确认"):
        controller.confirm_suggestion(
            "study-a",
            scope="workspace",
            title="经验",
            summary="摘要",
            confirm=False,
        )


def test_experience_screen_confirm_then_list_edit_export(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    with pytest.raises(ValueError, match="最终确认"):
        controller.confirm_suggestion(
            "study-a",
            scope="workspace",
            title="经验",
            summary="摘要",
            confirm=False,
        )

    record = controller.confirm_suggestion(
        "study-a",
        scope="workspace",
        title="经验",
        summary="摘要",
        tags=["tui"],
        confirm=True,
    )
    edited = controller.edit_experience(record["id"], workspace_id="study-a", scope="workspace", title="新经验")
    exported = controller.export_experiences(workspace_id="study-a", format="md")

    assert record["message"] == "经验已确认写入"
    assert edited["title"] == "新经验"
    assert controller.list_experiences("study-a")[0]["label"] == "经验：新经验"
    assert "新经验" in exported["content"]


def test_experience_screen_delete_requires_exact_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)
    record = controller.confirm_suggestion(
        "study-a",
        scope="workspace",
        title="经验",
        summary="摘要",
        confirm=True,
    )

    with pytest.raises(ValueError, match="经验 ID"):
        controller.delete_experience(record["id"], workspace_id="study-a", scope="workspace", confirm="wrong")

    deleted = controller.delete_experience(record["id"], workspace_id="study-a", scope="workspace", confirm=record["id"])
    assert deleted["status"] == "deleted"
    assert controller.list_experiences("study-a") == []


def test_experience_delete_copy_describes_exact_irreversible_confirmation():
    assert "完全一致" in t("experience_delete_requires_confirm")
    assert "不可恢复" in t("experience_delete_requires_confirm")


def test_experience_view_sets_deterministic_non_empty_reload_status():
    loader = inspect.getsource(ExperienceView._load_experiences)

    assert "experience_list" in loader
    assert "len(records)" in loader


def test_experience_view_empty_success_error_copy_and_secret_redaction_are_explicit():
    compose_source = inspect.getsource(ExperienceView.compose)
    loader_source = inspect.getsource(ExperienceView._load_experiences)
    confirm_source = inspect.getsource(ExperienceView._confirm_experience)
    error_source = inspect.getsource(ExperienceView._set_error)
    status_source = inspect.getsource(ExperienceView._set_status)

    assert "experience_no_records" in loader_source
    assert "experience_list" in loader_source
    assert "experience_confirmed" in confirm_source
    assert "experience_delete_requires_confirm" in compose_source + inspect.getsource(ExperienceView._delete_experience)
    assert "redact_sensitive" in error_source
    assert "redact_sensitive" in status_source
    assert t("experience_no_records") == "暂无经验记录"
    assert "完全一致" in t("experience_delete_requires_confirm")
