from __future__ import annotations

import yaml

from core.tui.screens.dashboard import DashboardOverviewController, collect_dashboard_context
from core.workspace import WorkspaceManager


def test_dashboard_context_for_uninitialized_project_is_chinese_and_stable(tmp_path):
    context = collect_dashboard_context(tmp_path)

    assert context["initialized"] is False
    assert context["init_status"] == "未初始化"
    assert context["workspace_count"] == 0
    assert context["plugin_count"] == 0
    assert context["module_count"] == 0
    assert context["llm_status"] == "LLM 未就绪：暂无 LLM Provider"
    assert context["recent_hint"] == "暂无工作区，请先创建"
    assert "初始化" in context["action_hint"]


def test_dashboard_context_for_initialized_project_with_workspace_and_ready_llm_redacts_secret(tmp_path):
    secret = "sk-dashboard-secret"
    (tmp_path / ".supermedicine").mkdir()
    plugin_dir = tmp_path / "plugins" / "demo_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text("name: demo\n", encoding="utf-8")
    (tmp_path / "core" / "agents").mkdir(parents=True)

    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("study-a")
    manager.save_recent_selection("study-a")
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.local.test/v1",
                            "api_key": secret,
                            "model": "gpt-dashboard",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)
    rows = DashboardOverviewController(tmp_path).overview_rows()
    rendered = str(context) + str(rows)

    assert context["initialized"] is True
    assert context["init_status"] == "已初始化"
    assert context["workspace_count"] == 1
    assert context["plugin_count"] == 1
    assert context["module_count"] == 1
    assert context["llm_status"] == "LLM 已就绪：openai（gpt-dashboard）"
    assert context["recent_hint"] == "最近工作区：study-a"
    assert rows[0] == ("初始化状态", "已初始化")
    assert secret not in rendered


def test_dashboard_context_reports_initialized_project_without_workspace_or_provider(tmp_path):
    (tmp_path / ".supermedicine").mkdir()

    context = collect_dashboard_context(tmp_path)

    assert context["init_status"] == "已初始化"
    assert context["workspace_count"] == 0
    assert context["llm_status"] == "LLM 未就绪：暂无 LLM Provider"
    assert context["recent_hint"] == "暂无工作区，请先创建"
    assert "创建工作区" in context["action_hint"]


def test_dashboard_context_collects_counts_recent_hint_and_ready_advice_without_network(tmp_path):
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / "plugins" / "good_plugin").mkdir(parents=True)
    (tmp_path / "plugins" / "good_plugin" / "plugin.yaml").write_text("name: good\n", encoding="utf-8")
    (tmp_path / "plugins" / "_ignored").mkdir(parents=True)
    (tmp_path / "plugins" / "_ignored" / "plugin.yaml").write_text("name: ignored\n", encoding="utf-8")
    (tmp_path / "core" / "agents").mkdir(parents=True)
    (tmp_path / "core" / "_private").mkdir(parents=True)
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("study-a")
    manager.initialize_workspace("study-b")
    manager.save_recent_selection("study-b", "study-a")
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.local.test/v1",
                            "api_key": "sk-dashboard-counts-secret",
                            "model": "gpt-dashboard",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)

    assert context["workspace_count"] == 2
    assert context["plugin_count"] == 1
    assert context["module_count"] == 1
    assert context["llm_ready"] is True
    assert context["recent_hint"] == "最近工作区：study-a"
    assert context["action_hint"] == "运行上下文已就绪，可进入对话或工作区继续任务。"
    assert "sk-dashboard-counts-secret" not in str(context)


def test_dashboard_context_reports_incomplete_llm_without_api_key_leak(tmp_path):
    secret = "sk-incomplete-dashboard-secret"
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "broken",
                    "providers": {
                        "broken": {
                            "api_format": "openai",
                            "base_url": "https://broken.local.test/v1",
                            "api_key": secret,
                            "model": "",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)

    assert context["llm_status"] == "LLM 未就绪：broken（缺少：model）"
    assert secret not in str(context)
