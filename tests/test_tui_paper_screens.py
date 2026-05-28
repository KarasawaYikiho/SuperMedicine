from __future__ import annotations

import inspect

from core.tui.screens.papers import PaperScreenController
from core.tui.i18n import t
from core.tui.screens.paper_screen import PaperView
from core.workspace import WorkspaceManager


def _policy(tmp_path):
    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True, exist_ok=True)
    (policies / "default.yaml").write_text(
        "agent_id: delta\nrole: test\npermissions:\n  allowed:\n    - action: 'paper.enrich'\n      scope: '*'\n",
        encoding="utf-8",
    )


def test_paper_screen_import_is_copy_only_and_lists_metadata(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)

    imported = controller.import_paper("study-a", source, metadata={"title": "研究论文", "tags": ["肿瘤"]})

    assert source.exists()
    assert imported["message"] == "论文已复制导入工作区"
    assert imported["metadata"]["title"] == "研究论文"
    assert imported["metadata"]["stored_path"] != str(source)
    assert controller.list_papers("study-a")[0]["label"] == "论文：研究论文"


def test_paper_screen_empty_state_and_select_workspace_copy_are_chinese(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = PaperScreenController(tmp_path)

    assert controller.list_papers("study-a") == []
    assert t("paper_no_papers") == "暂无论文，请先导入"
    assert t("paper_select_workspace") == "请先选择工作区"


def test_paper_screen_edit_metadata(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)
    paper_id = controller.import_paper("study-a", source)["metadata"]["id"]

    updated = controller.edit_metadata("study-a", paper_id, {"title": "更新标题", "notes": "中文备注"})

    assert updated["message"] == "论文元数据已更新"
    assert controller.show_paper("study-a", paper_id)["title"] == "更新标题"


def test_paper_screen_enrichment_requires_explicit_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)
    paper_id = controller.import_paper("study-a", source)["metadata"]["id"]

    skipped = controller.enrich_metadata("study-a", paper_id, confirm=False)

    assert skipped["status"] == "skipped"
    assert skipped["message"] == "论文在线补全未执行"

    _policy(tmp_path)
    enriched = controller.enrich_metadata("study-a", paper_id, confirm=True)
    assert enriched["status"] == "enriched"
    assert "enriched" in enriched["metadata"]["tags"]


def test_paper_enrichment_copy_warns_about_network_and_confirmation():
    assert "网络请求" in t("paper_enrich_confirm")
    assert "选中论文 ID" in t("paper_enrich_confirm")


def test_paper_enrichment_confirmation_skips_without_network_policy_or_api(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)
    paper_id = controller.import_paper("study-a", source)["metadata"]["id"]

    skipped = controller.enrich_metadata("study-a", paper_id, confirm=False)

    assert skipped["status"] == "skipped"
    assert skipped["applied_fields"] == []
    assert skipped["message"] == "论文在线补全未执行"
    assert t("paper_enrich_confirm")
    assert (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").exists()


def test_paper_view_sets_deterministic_non_empty_reload_status():
    loader = inspect.getsource(PaperView._load_papers)

    assert "paper_list" in loader
    assert "len(papers)" in loader
