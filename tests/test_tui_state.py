from __future__ import annotations

from Cli import CLI
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
