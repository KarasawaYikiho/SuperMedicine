from __future__ import annotations

import pytest

from core.tui.screens.experience import ExperienceScreenController
from core.workspace import WorkspaceManager


def test_experience_screen_suggest_requires_later_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    suggestion = controller.suggest_classification("study-a", title="方法", summary="总结事件")

    assert suggestion["label"] == "经验分类建议"
    assert suggestion["confirmed"] is False
    assert controller.list_experiences("study-a") == []


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
