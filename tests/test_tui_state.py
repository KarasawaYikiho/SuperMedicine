from __future__ import annotations

import yaml

from Cli import CLI
from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.tui.app import SuperMedicineTUI
from core.tui.state import TUIState, load_recent_workspace, save_recent_workspace
from core.workspace import WorkspaceManager


def test_recent_workspace_selection_saved_and_loaded_from_workspace_session_state(tmp_path):
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("trial-1")
    manager.initialize_workspace("trial-2")

    state_path = save_recent_workspace("trial-1", "trial-2", project_root=tmp_path)

    assert state_path == tmp_path / "workspaces" / "trial-1" / ".supermedicine" / "sessions" / "tui_recent_selection.yaml"
    assert load_recent_workspace("trial-1", project_root=tmp_path) == "trial-2"
    assert load_recent_workspace("trial-2", project_root=tmp_path) is None
    assert not (tmp_path / ".supermedicine" / "sessions" / "tui_recent_selection.yaml").exists()


def test_tui_state_facade_uses_workspace_session_only(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    state = TUIState(tmp_path)

    state.save_recent_workspace("trial-1")

    assert state.load_recent_workspace("trial-1") == "trial-1"


def test_recent_workspace_state_is_scoped_per_workspace_and_not_global_cli_state(tmp_path):
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("trial-1")
    manager.initialize_workspace("trial-2")

    first_state_path = save_recent_workspace("trial-1", "trial-2", project_root=tmp_path)
    second_state_path = save_recent_workspace("trial-2", "trial-1", project_root=tmp_path)

    assert load_recent_workspace("trial-1", project_root=tmp_path) == "trial-2"
    assert load_recent_workspace("trial-2", project_root=tmp_path) == "trial-1"
    assert first_state_path.parent == tmp_path / "workspaces" / "trial-1" / ".supermedicine" / "sessions"
    assert second_state_path.parent == tmp_path / "workspaces" / "trial-2" / ".supermedicine" / "sessions"
    assert not (tmp_path / ".supermedicine" / "sessions" / "tui_recent_selection.yaml").exists()


def test_tui_state_does_not_affect_cli_workspace_requirement(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    save_recent_workspace("trial-1", project_root=tmp_path)
    captured = {}

    class FakeRegistry:
        def discover(self):
            return []

    class FakeCheckpointManager:
        base_dir = "checkpoints"

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["params"] = params
            return {"status": "success", "task": task, "output": {}}

    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True)
    (policies / "default.yaml").write_text(
        "agent_id: delta\nrole: test\npermissions:\n  allowed:\n    - action: '*'\n      scope: '*'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)

    CLI().run("task", params={"x": 1})

    assert captured["params"] == {"x": 1}
    assert "_workspace" not in captured["params"]


def test_llm_startup_restore_is_separate_from_tui_workspace_session_state(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    save_recent_workspace("trial-1", project_root=tmp_path)
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "last_provider": "anthropic",
                    "providers": {
                        "openai": {"api_format": "openai", "base_url": "https://openai.test/v1", "api_key": "sk-openai-state", "model": "gpt-test"},
                        "anthropic": {"api_format": "anthropic", "base_url": "https://anthropic.test/v1", "api_key": "sk-anthropic-state", "model": "claude-test"},
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    manager = LLMConfigManager(ConfigCenter(config_path))

    assert load_recent_workspace("trial-1", project_root=tmp_path) == "trial-1"
    assert manager.get_current_provider()["provider"] == "anthropic"
    assert ConfigCenter(config_path).get_llm_current_provider_name() == "anthropic"


def test_tui_shell_status_object_exposes_workspace_plugin_llm_version_and_task_state(tmp_path):
    plugins_dir = tmp_path / "plugins" / "demo_plugin"
    plugins_dir.mkdir(parents=True)
    (plugins_dir / "plugin.yaml").write_text("name: demo\n", encoding="utf-8")
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.test/v1",
                            "api_key": "sk-hidden-state",
                            "model": "gpt-test",
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    app = SuperMedicineTUI(project_root=tmp_path)
    status = app.status_text("llm")

    assert status.left == "📁 1 工作区"
    assert "🔌 1 插件" in status.center
    assert "openai LLM 已就绪" in status.center
    assert "任务空闲" in status.center
    assert "当前视图：LLM 管理" in status.right
    assert "SuperMedicine" in status.right
    assert "sk-hidden-state" not in status.center
    assert status.focus == "焦点：输入栏"


def test_tui_navigation_metadata_preserves_numeric_shortcuts_and_chinese_titles(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)

    assert [item.key for item in app.nav_items()] == ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert [item.view_id for item in app.nav_items()] == [
        "chat",
        "dashboard",
        "workspace",
        "paper",
        "experience",
        "tool",
        "dialog",
        "llm",
    ]
    assert app.nav_items()[0].label == "对话"
    assert app.nav_items()[-1].label == "LLM 管理"
