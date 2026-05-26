from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from Cli import CLI, main
from core.workspace import WorkspaceManager
from permission.engine import PermissionEngine
from permission.policy import ensure_default_policy


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_default_policy(project_dir: Path) -> None:
    ensure_default_policy(project_dir, source_root=REPO_ROOT)


def test_workspace_init_list_show_use_explicit_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli = CLI()

    created = cli.workspace_init("trial-1", name="Trial One")
    listed = cli.workspace_list()
    shown = cli.workspace_show("trial-1")

    assert created["id"] == "trial-1"
    assert created["name"] == "Trial One"
    assert listed == [shown]
    assert shown["id"] == "trial-1"
    assert (tmp_path / "workspaces" / "trial-1" / "workspace.yaml").is_file()
    assert not (tmp_path / ".supermedicine" / "sessions").exists()


def test_workspace_subcommands_require_explicit_workspace(monkeypatch):
    monkeypatch.setattr("sys.argv", ["supermedicine", "workspace", "show"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2


def test_workspace_delete_rejects_confirmation_mismatch_and_audits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")

    with pytest.raises(ValueError, match="confirm"):
        CLI().workspace_delete("trial-1", "wrong-id")

    assert (tmp_path / "workspaces" / "trial-1").is_dir()
    audit_entries = [
        json.loads(line)
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert audit_entries[-1]["action"] == "workspace.delete"
    assert audit_entries[-1]["result"] == "cancelled"
    assert audit_entries[-1]["reason"] == "confirmation_mismatch"


def test_workspace_delete_hard_deletes_after_permission_approval(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    workspace = WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    (workspace.path / "notes" / "note.txt").write_text("content", encoding="utf-8")

    result = CLI().workspace_delete("trial-1", "trial-1")

    assert result["status"] == "deleted"
    assert result["id"] == "trial-1"
    assert not workspace.path.exists()
    audit_entries = [
        json.loads(line)
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(entry["action"] == "workspace.delete" and entry["result"] == "allowed" for entry in audit_entries)


def test_workspace_delete_denied_by_policy_keeps_workspace_and_audits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True)
    (policies / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
        yaml.safe_dump(
            {
                "agent_id": "delta",
                "role": "restricted",
                "permissions": {
                    "allowed": [],
                    "denied": [{"action": "workspace.delete", "scope": "*"}],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    workspace = WorkspaceManager(tmp_path).initialize_workspace("trial-1")

    with pytest.raises(PermissionError):
        CLI().workspace_delete("trial-1", "trial-1")

    assert workspace.path.is_dir()
    audit_entries = [
        json.loads(line)
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(entry["action"] == "workspace.delete" and entry["result"] == "denied" for entry in audit_entries)


def test_run_without_workspace_preserves_legacy_params(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    captured = {}

    class FakeRegistry:
        def discover(self):
            return []

    class FakeCheckpointManager:
        base_dir = "checkpoints"

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            self._config_path = kwargs["config_path"]
            self._plugins_dir = kwargs["plugins_dir"]
            self._policies_dir = kwargs["policies_dir"]
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["params"] = params
            return {"status": "success", "task": task, "plugin": plugin_name, "action": action, "output": {}}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    params = {"source_id": "src-1"}

    CLI().run("task", params=params)

    assert captured["params"] is params
    assert "_workspace" not in captured["params"]


def test_run_with_workspace_adds_explicit_workspace_context(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    captured = {}

    class FakeRegistry:
        def discover(self):
            return []

    class FakeCheckpointManager:
        base_dir = "checkpoints"

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            self._config_path = kwargs["config_path"]
            self._plugins_dir = kwargs["plugins_dir"]
            self._policies_dir = kwargs["policies_dir"]
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["params"] = params
            return {"status": "success", "task": task, "plugin": plugin_name, "action": action, "output": {}}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    params = {"source_id": "src-1"}

    CLI().run("task", params=params, workspace="trial-1")

    assert captured["params"] is not params
    assert captured["params"]["source_id"] == "src-1"
    assert captured["params"]["_workspace"]["id"] == "trial-1"
    assert captured["params"]["_workspace"]["path"] == str((tmp_path / "workspaces" / "trial-1").resolve())
