from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from cli_entry import CLI, main
from core.operation_guard import DangerousOperationDenied
from core.path_safety import PathOutsideProjectRootError
from core.workspace import (
    InvalidWorkspaceId,
    SESSION_STATE_FILE,
    WORKSPACE_DIRECTORIES,
    WorkspaceManager,
    validate_workspace_id,
)
from core.workspace_tools import (
    BUILTIN_TEMPLATES,
    MANIFEST_FILE,
    TOOL_AUTHORING_SPEC,
    InvalidToolId,
    ToolManifest,
    ToolCandidateError,
    ToolManifestError,
    WorkspaceToolError,
    WorkspaceToolService,
    build_tool_authoring_llm_context,
    validate_language,
    validate_tool_id,
)
from core.workspace_tool_models import InvalidToolLanguage
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from permission.policy import PermissionResult, ensure_default_policy


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_default_policy(project_dir: Path) -> None:
    ensure_default_policy(project_dir, source_root=REPO_ROOT)


def _make_python_scan_tool(
    source_root: Path,
    dir_name: str,
    plugin_meta: dict[str, Any] | None = None,
    entrypoint_name: str = "main.py",
) -> Path:
    tool_dir = source_root / dir_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    if plugin_meta is not None:
        (tool_dir / "plugin.yaml").write_text(
            yaml.safe_dump(plugin_meta, sort_keys=False), encoding="utf-8"
        )
    (tool_dir / entrypoint_name).write_text("print('ok')\n", encoding="utf-8")
    return tool_dir


def _make_r_scan_tool(
    source_root: Path,
    dir_name: str,
    plugin_meta: dict[str, Any] | None = None,
    entrypoint_name: str = "runner.R",
) -> Path:
    tool_dir = source_root / dir_name
    tool_dir.mkdir(parents=True, exist_ok=True)
    if plugin_meta is not None:
        (tool_dir / "plugin.yaml").write_text(
            yaml.safe_dump(plugin_meta, sort_keys=False), encoding="utf-8"
        )
    (tool_dir / entrypoint_name).write_text("cat('ok')\n", encoding="utf-8")
    return tool_dir


def _setup_import_source_tools(source_root: Path) -> None:
    py_dir = source_root / "py_heatmap"
    py_dir.mkdir(parents=True)
    (py_dir / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "py-heatmap",
                "version": "1.0.0",
                "type": "tool",
                "language": "python",
                "description": "Heatmap generator",
                "entry": "main.py",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (py_dir / "main.py").write_text("print('heatmap')\n", encoding="utf-8")

    r_dir = source_root / "r_umap"
    r_dir.mkdir()
    (r_dir / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "r-umap",
                "version": "1.0.0",
                "type": "tool",
                "language": "r",
                "description": "UMAP in R",
                "entry": "runner.R",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (r_dir / "runner.R").write_text("cat('umap')\n", encoding="utf-8")


# ═══ Workspace Tests ═══


@pytest.mark.parametrize("slug", ["study", "study-1", "abc123", "a"])
def test_valid_workspace_slug_is_accepted(slug):
    assert validate_workspace_id(slug) == slug


@pytest.mark.parametrize(
    "slug",
    ["", "Study", "study_1", "study 1", "-study", "study-", "../study", "study/one"],
)
def test_invalid_workspace_slug_is_rejected(slug):
    with pytest.raises(InvalidWorkspaceId):
        validate_workspace_id(slug)


def test_initialize_workspace_creates_expected_layout_only_under_workspaces(tmp_path):
    manager = WorkspaceManager(tmp_path)

    info = manager.initialize_workspace("trial-1")

    assert info.path == (tmp_path / "workspaces" / "trial-1").resolve()
    assert (tmp_path / "workspaces" / "trial-1" / "workspace.yaml").is_file()
    for directory in WORKSPACE_DIRECTORIES:
        assert (tmp_path / "workspaces" / "trial-1" / directory).is_dir()
    assert not (tmp_path / ".supermedicine").exists()


def test_atomic_workspace_create_publishes_only_a_complete_layout(
    tmp_path, monkeypatch
) -> None:
    manager = WorkspaceManager(tmp_path)
    original_replace = Path.replace

    def interrupt_publish(source: Path, target: Path):
        if source.name.startswith(".sm-staging-"):
            assert (source / "workspace.yaml").is_file()
            assert all((source / directory).is_dir() for directory in WORKSPACE_DIRECTORIES)
            raise OSError("simulated terminate before publish")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", interrupt_publish)
    with pytest.raises(OSError, match="simulated terminate"):
        manager.initialize_workspace_atomic("atomic-create", name="Atomic")

    assert not (tmp_path / "workspaces" / "atomic-create").exists()
    assert list((tmp_path / "workspaces").glob(".sm-staging-*"))
    monkeypatch.setattr(Path, "replace", original_replace)
    manager.recover_atomic_transactions()
    assert not list((tmp_path / "workspaces").glob(".sm-staging-*"))


def test_atomic_workspace_delete_hides_before_cleanup_and_recovers(
    tmp_path, monkeypatch
) -> None:
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("atomic-delete").path

    def interrupted_cleanup(_path: Path) -> None:
        raise OSError("simulated terminate during cleanup")

    monkeypatch.setattr("core.workspace.shutil.rmtree", interrupted_cleanup)
    with pytest.raises(OSError, match="simulated terminate"):
        manager.delete_workspace_atomic(workspace)

    assert not workspace.exists()
    assert list((tmp_path / "workspaces").glob(".sm-tombstone-*"))
    monkeypatch.undo()
    manager.recover_atomic_transactions()
    assert not list((tmp_path / "workspaces").glob(".sm-tombstone-*"))


def test_workspace_transaction_recovery_removes_only_internal_artifacts(tmp_path) -> None:
    root = tmp_path / "workspaces"
    staging = root / ".sm-staging-stale"
    tombstone = root / ".sm-tombstone-stale"
    visible = root / "visible"
    for path in (staging, tombstone, visible):
        path.mkdir(parents=True)

    WorkspaceManager(tmp_path).recover_atomic_transactions()

    assert not staging.exists()
    assert not tombstone.exists()
    assert visible.exists()


def test_workspace_metadata_is_stored_and_reloaded(tmp_path):
    manager = WorkspaceManager(tmp_path)

    created = manager.initialize_workspace("meta-study")
    loaded = manager.get_workspace("meta-study")

    assert loaded.id == "meta-study"
    assert loaded.path == created.path
    assert loaded.metadata.id == "meta-study"
    assert loaded.metadata.created_at == created.metadata.created_at
    assert manager.list_workspaces() == [loaded]

    raw = yaml.safe_load((loaded.path / "workspace.yaml").read_text(encoding="utf-8"))
    assert raw["id"] == "meta-study"


def test_workspace_symlink_target_inside_project_is_accepted(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink not supported on this platform")

    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    internal_target = tmp_path / "internal-target"
    internal_target.mkdir()
    link = workspaces / "linked-study"
    try:
        link.symlink_to(internal_target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    manager = WorkspaceManager(tmp_path)
    info = manager.initialize_workspace("linked-study")

    assert info.path == internal_target.resolve()
    assert (internal_target / "workspace.yaml").is_file()


def test_workspace_symlink_target_outside_project_is_rejected(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink not supported on this platform")

    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    outside_target = tmp_path.parent / f"{tmp_path.name}-outside-workspace"
    outside_target.mkdir()
    link = workspaces / "escaped-study"
    try:
        link.symlink_to(outside_target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    manager = WorkspaceManager(tmp_path)
    with pytest.raises(PathOutsideProjectRootError):
        manager.initialize_workspace("escaped-study")


def test_recent_selection_state_is_stored_only_in_workspace_session_path(tmp_path):
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("session-study")

    state_path = manager.save_recent_selection("session-study")

    expected = (
        tmp_path
        / "workspaces"
        / "session-study"
        / ".supermedicine"
        / "sessions"
        / SESSION_STATE_FILE
    ).resolve()
    assert state_path == expected
    assert manager.load_recent_selection("session-study") == "session-study"
    assert not (tmp_path / ".supermedicine").exists()


def test_no_implicit_cli_or_global_state_is_created(tmp_path):
    manager = WorkspaceManager(tmp_path)

    manager.initialize_workspace("explicit-study")

    assert not (tmp_path / ".supermedicine").exists()
    assert not (tmp_path / "workspace.yaml").exists()
    assert (tmp_path / "workspaces" / "explicit-study" / "workspace.yaml").is_file()


def test_workspace_manager_create_is_direct_without_kernel_or_llm_import(
    tmp_path, monkeypatch
):
    imported: list[str] = []
    original_import = __import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("core.kernel", "core.llm_client", "core.llm_providers")):
            imported.append(name)
            raise AssertionError(
                f"workspace creation must not import Kernel/LLM module: {name}"
            )
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded_import)

    info = WorkspaceManager(tmp_path).create_workspace("direct-study")

    assert info.id == "direct-study"
    assert (tmp_path / "workspaces" / "direct-study" / "workspace.yaml").is_file()
    assert imported == []


# ═══ Workspace CLI Tests ═══


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


def test_workspace_init_does_not_enter_kernel_or_llm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    imported: list[str] = []
    original_import = __import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("core.kernel", "core.llm_client", "core.llm_providers")):
            imported.append(name)
            raise AssertionError(
                f"workspace init must not import Kernel/LLM module: {name}"
            )
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded_import)

    result = CLI().workspace_init("direct-cli", name="Direct CLI")

    assert result["id"] == "direct-cli"
    assert result["name"] == "Direct CLI"
    assert (tmp_path / "workspaces" / "direct-cli" / "workspace.yaml").is_file()
    assert imported == []


def test_workspace_subcommands_require_explicit_workspace(monkeypatch):
    monkeypatch.setattr("sys.argv", ["supermedicine", "workspace", "show"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2


def test_workspace_delete_rejects_confirmation_mismatch_and_audits(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")

    with pytest.raises(ValueError, match="confirm"):
        CLI().workspace_delete("trial-1", "wrong-id")

    assert (tmp_path / "workspaces" / "trial-1").is_dir()
    audit_entries = [
        json.loads(line)
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
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
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert any(
        entry["action"] == "workspace.delete" and entry["result"] == "allowed"
        for entry in audit_entries
    )


def test_workspace_delete_denied_by_policy_keeps_workspace_and_audits(
    tmp_path, monkeypatch
):
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
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert any(
        entry["action"] == "workspace.delete" and entry["result"] == "denied"
        for entry in audit_entries
    )


@pytest.mark.parametrize("workspace_id", [None, "trial-1"])
def test_run_preserves_legacy_params_or_adds_explicit_workspace_context(
    monkeypatch, tmp_path, workspace_id
):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    if workspace_id is not None:
        WorkspaceManager(tmp_path).initialize_workspace(workspace_id)
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
            return {
                "status": "success",
                "task": task,
                "plugin": plugin_name,
                "action": action,
                "output": {},
            }

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    params = {"source_id": "src-1"}

    CLI().run("task", params=params, workspace=workspace_id)

    if workspace_id is None:
        assert captured["params"] is params
        assert "_workspace" not in captured["params"]
    else:
        assert captured["params"] is not params
        assert captured["params"]["source_id"] == "src-1"
        assert captured["params"]["_workspace"]["id"] == workspace_id
        assert captured["params"]["_workspace"]["path"] == str(
            (tmp_path / "workspaces" / workspace_id).resolve()
        )


# ═══ Workspace Tools Tests ═══


class RecordingPermissionEngine:
    def __init__(self, result: PermissionResult):
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def check(self, agent_id, action, resource, context=None):
        self.calls.append(
            {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": context,
            }
        )
        return self.result


@pytest.mark.parametrize("language", ["python", "r"])
def test_language_validation_accepts_supported_languages(language):
    assert validate_language(language) == language


@pytest.mark.parametrize("language", ["", "Python", "R", "julia", "python/../r"])
def test_language_validation_rejects_invalid_languages(language):
    with pytest.raises(InvalidToolLanguage):
        validate_language(language)


@pytest.mark.parametrize("tool_id", ["heatmap", "umap-2", "a", "a1", "my-tool-1"])
def test_tool_id_validation_accepts_safe_slugs(tool_id):
    assert validate_tool_id(tool_id) == tool_id


@pytest.mark.parametrize(
    "tool_id",
    [
        "",
        "Heatmap",
        "UPPER",
        "heat_map",
        "heat map",
        "-heatmap",
        "heatmap-",
        "../heatmap",
        "heatmap/one",
        "..",
        ".",
    ],
)
def test_tool_id_validation_rejects_traversal_and_unsafe_ids(tool_id):
    with pytest.raises(InvalidToolId):
        validate_tool_id(tool_id)


class TestWorkspaceToolSourceRoot:
    def test_tool_source_root_points_to_plugins_tools(self, tmp_path: Path):
        service = WorkspaceToolService(tmp_path)
        expected = (tmp_path / "plugins" / "tools").resolve()
        assert service.tool_source_root() == expected

    def test_project_root_walks_up_from_selected_workspace_directory(
        self, tmp_path: Path
    ):
        source_root = tmp_path / "plugins" / "tools"
        source_root.mkdir(parents=True)
        workspace = tmp_path / "workspaces" / "trial-1"
        workspace.mkdir(parents=True)

        service = WorkspaceToolService(workspace)

        assert service.project_root == tmp_path.resolve()
        assert service.tool_source_root() == source_root.resolve()


class TestWorkspaceToolScanning:
    def test_scan_empty_source_root_returns_empty_groups(self, tmp_path: Path):
        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert grouped["python"] == []
        assert grouped["r"] == []

    def test_scan_discovers_python_tool_with_plugin_yaml(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _make_python_scan_tool(
            source_root,
            "py_stats",
            {
                "name": "py-stats",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "description": "Python stats tool",
                "entry": "main.py",
            },
        )

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["python"]) == 1
        candidate = grouped["python"][0]
        assert candidate["id"] == "py-stats"
        assert candidate["language"] == "python"
        assert candidate["importable"] is True

    def test_scan_discovers_r_tool_with_r_prefix_inference(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _make_r_scan_tool(
            source_root,
            "r_survival",
            {
                "name": "r-survival",
                "version": "0.1.0",
                "type": "tool",
                "description": "R survival analysis",
            },
        )

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["r"]) == 1
        candidate = grouped["r"][0]
        assert candidate["id"] == "r-survival"
        assert candidate["language"] == "r"
        assert candidate["importable"] is True

    def test_scan_infers_python_when_language_metadata_missing(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _make_python_scan_tool(
            source_root,
            "mystery_tool",
            {
                "name": "mystery-tool",
                "version": "0.1.0",
                "type": "tool",
                "entry": "main.py",
            },
        )

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["python"]) == 1
        assert grouped["python"][0]["language"] == "python"
        assert any("inferred" in warning for warning in grouped["python"][0]["warnings"])

    def test_scan_infers_r_from_directory_prefix_when_language_missing(
        self, tmp_path: Path
    ):
        source_root = tmp_path / "plugins" / "tools"
        _make_r_scan_tool(
            source_root,
            "r_kaplan",
            {
                "name": "r-kaplan",
                "version": "0.1.0",
                "type": "tool",
            },
        )

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["r"]) == 1
        assert grouped["r"][0]["language"] == "r"
        assert any("inferred" in warning for warning in grouped["r"][0]["warnings"])

    def test_scan_falls_back_to_directory_name_when_no_metadata(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _make_python_scan_tool(source_root, "plain_tool")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

        assert len(grouped["python"]) == 1
        candidate = grouped["python"][0]
        assert candidate["name"] == "plain_tool"
        assert any("metadata missing" in warning for warning in candidate["warnings"])

    def test_scan_skips_non_directories(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        source_root.mkdir(parents=True)
        (source_root / "readme.txt").write_text("not a tool", encoding="utf-8")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert grouped["python"] == []
        assert grouped["r"] == []

    def test_scan_skips_pycache(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        source_root.mkdir(parents=True)
        pycache = source_root / "__pycache__"
        pycache.mkdir()
        (pycache / "main.py").write_text("print('ok')\n", encoding="utf-8")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert grouped["python"] == []
        assert grouped["r"] == []

    def test_scan_filters_by_language(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _make_python_scan_tool(
            source_root,
            "py_tool",
            {
                "name": "py-tool",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "entry": "main.py",
            },
        )
        _make_r_scan_tool(
            source_root,
            "r_tool",
            {
                "name": "r-tool",
                "version": "0.1.0",
                "type": "tool",
                "language": "r",
            },
        )

        python_only = WorkspaceToolService(tmp_path).scan_import_candidates("python")
        assert len(python_only["python"]) == 1
        assert "r" not in python_only

    def test_scan_assigns_sequential_indices(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _make_python_scan_tool(
            source_root,
            "alpha",
            {
                "name": "alpha",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "entry": "main.py",
            },
        )
        _make_python_scan_tool(
            source_root,
            "beta",
            {
                "name": "beta",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "entry": "main.py",
            },
        )

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        indices = [candidate["index"] for candidate in grouped["python"]]
        assert indices == [1, 2]

    def test_scan_marks_missing_entrypoint_as_invalid(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        tool_dir = source_root / "bad_entry"
        tool_dir.mkdir(parents=True)
        (tool_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "bad-entry",
                    "version": "0.1.0",
                    "type": "tool",
                    "language": "python",
                    "entry": "nonexistent.py",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert len(grouped["python"]) == 1
        assert grouped["python"][0]["status"] == "invalid"
        assert grouped["python"][0]["importable"] is False

    def test_scan_accepts_tool_yaml_over_plugin_yaml(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        tool_dir = source_root / "dual_meta"
        tool_dir.mkdir(parents=True)
        (tool_dir / "tool.yaml").write_text(
            yaml.safe_dump(
                {
                    "id": "dual-meta",
                    "language": "python",
                    "name": "Dual Meta Tool",
                    "description": "Has tool.yaml",
                    "entrypoint": "main.py",
                    "dependencies": [],
                    "inputs": [],
                    "outputs": [],
                    "version": "1.0.0",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (tool_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "different-name",
                    "version": "9.9.9",
                    "type": "tool",
                    "language": "python",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (tool_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        grouped = WorkspaceToolService(tmp_path).scan_import_candidates()
        assert len(grouped["python"]) == 1
        candidate = grouped["python"][0]
        assert candidate["id"] == "dual-meta"
        assert candidate["name"] == "Dual Meta Tool"
        assert not any(
            "workspace tool.yaml missing" in warning for warning in candidate["warnings"]
        )

    def test_scan_discovers_heatmap_umap_from_workspace_directory_context(
        self, tmp_path: Path
    ):
        source_root = tmp_path / "plugins" / "tools"
        _make_python_scan_tool(
            source_root,
            "heatmap",
            {
                "id": "heatmap",
                "language": "python",
                "name": "Python heatmap",
                "description": "Python heatmap",
                "entrypoint": "main.py",
                "dependencies": [],
                "inputs": [],
                "outputs": [],
                "version": "1.0.0",
            },
        )
        _make_python_scan_tool(
            source_root,
            "umap",
            {
                "id": "umap",
                "language": "python",
                "name": "Python UMAP",
                "description": "Python UMAP",
                "entrypoint": "main.py",
                "dependencies": [],
                "inputs": [],
                "outputs": [],
                "version": "1.0.0",
            },
        )
        _make_r_scan_tool(
            source_root,
            "r_heatmap",
            {
                "id": "r-heatmap",
                "language": "r",
                "name": "R heatmap",
                "description": "R heatmap",
                "entrypoint": "runner.R",
                "dependencies": [],
                "inputs": [],
                "outputs": [],
                "version": "1.0.0",
            },
        )
        _make_r_scan_tool(
            source_root,
            "r_umap",
            {
                "id": "r-umap",
                "language": "r",
                "name": "R UMAP",
                "description": "R UMAP",
                "entrypoint": "runner.R",
                "dependencies": [],
                "inputs": [],
                "outputs": [],
                "version": "1.0.0",
            },
        )
        workspace_path = tmp_path / "workspaces" / "trial-1"
        workspace_path.mkdir(parents=True)

        grouped = WorkspaceToolService(workspace_path).scan_import_candidates()

        assert {item["id"] for item in grouped["python"]} == {"heatmap", "umap"}
        assert {item["id"] for item in grouped["r"]} == {"r-heatmap", "r-umap"}
        assert all(item["importable"] for item in grouped["python"] + grouped["r"])


def test_tool_init_creates_python_and_r_directories_under_workspace(tmp_path):
    result = WorkspaceToolService(tmp_path).initialize_tools("trial-1")

    workspace = tmp_path / "workspaces" / "trial-1"
    assert result["status"] == "initialized"
    assert (workspace / "tools" / "python").is_dir()
    assert (workspace / "tools" / "r").is_dir()
    assert not (tmp_path / "tools").exists()


@pytest.mark.parametrize(
    ("language", "tool_id", "entrypoint"),
    [
        ("python", "heatmap", "runner.py"),
        ("python", "umap", "runner.py"),
        ("r", "heatmap", "runner.R"),
        ("r", "umap", "runner.R"),
    ],
)
def test_builtin_templates_can_be_scaffolded_and_loaded(
    tmp_path, language, tool_id, entrypoint
):
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")

    result = service.add_builtin_tool("trial-1", language, tool_id)
    manifest = service.load_manifest("trial-1", language, tool_id)
    tool_path = tmp_path / "workspaces" / "trial-1" / "tools" / language / tool_id

    assert result["status"] == "added"
    assert (tool_path / "tool.yaml").is_file()
    assert (tool_path / "README.md").is_file()
    assert (tool_path / entrypoint).is_file()
    assert manifest.id == tool_id
    assert manifest.language == language
    assert manifest.entrypoint == entrypoint
    assert manifest.dependencies
    assert manifest.inputs
    assert manifest.outputs
    assert manifest.version


def test_manifest_schema_requires_expected_fields_and_validates_identity():
    data = {
        "id": "heatmap",
        "language": "python",
        "name": "Python heatmap",
        "description": "description",
        "entrypoint": "runner.py",
        "dependencies": ["pandas"],
        "inputs": [{"name": "input"}],
        "outputs": [{"name": "output"}],
        "version": "1.0.0",
    }

    manifest = ToolManifest.from_dict(
        data, expected_id="heatmap", expected_language="python"
    )

    assert manifest.to_dict()["id"] == "heatmap"
    with pytest.raises(ToolManifestError, match="missing required fields"):
        ToolManifest.from_dict({"id": "heatmap"})
    with pytest.raises(ToolManifestError, match="id mismatch"):
        ToolManifest.from_dict(data, expected_id="umap", expected_language="python")
    with pytest.raises(ToolManifestError, match="relative path"):
        ToolManifest.from_dict({**data, "entrypoint": "../runner.py"})


def test_workspace_tool_manifest_size_is_bounded(tmp_path):
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    service.add_builtin_tool("trial-1", "python", "heatmap")
    manifest_path = (
        tmp_path
        / "workspaces"
        / "trial-1"
        / "tools"
        / "python"
        / "heatmap"
        / "tool.yaml"
    )
    manifest_path.write_text("a" * (256 * 1024 + 1), encoding="utf-8")

    with pytest.raises(ToolManifestError, match="too large"):
        service.load_manifest("trial-1", "python", "heatmap")


def test_tool_authoring_context_matches_manifest_and_scanner_contract():
    context = build_tool_authoring_llm_context()
    fields = context["manifest_fields"]

    assert context["source_directory"] == "plugins/tools"
    assert (
        context["storage"]["python"]
        == "workspaces/<workspace-id>/tools/python/<tool-id>/"
    )
    assert context["storage"]["r"] == "workspaces/<workspace-id>/tools/r/<tool-id>/"
    assert context["tool_folder_format"]["required_manifest"] == MANIFEST_FILE
    assert set(fields) == {
        "id",
        "language",
        "name",
        "description",
        "entrypoint",
        "dependencies",
        "inputs",
        "outputs",
        "version",
    }
    assert "python" in fields["language"]
    assert "r" in fields["language"]
    assert "relative" in fields["entrypoint"]
    assert "plugins/tools/<tool-directory>/" in context["llm_authoring_rule"]
    assert (
        TOOL_AUTHORING_SPEC["scan_validate_import_flow"]
        == context["scan_validate_import_flow"]
    )


def test_list_discovers_tools_grouped_by_language(tmp_path):
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    service.add_builtin_tool("trial-1", "python", "heatmap")
    service.add_builtin_tool("trial-1", "r", "umap")

    grouped = service.list_tools("trial-1")
    python_only = service.list_tools("trial-1", language="python")

    assert [tool["id"] for tool in grouped["python"]] == ["heatmap"]
    assert [tool["id"] for tool in grouped["r"]] == ["umap"]
    assert set(python_only) == {"python"}
    assert python_only["python"][0]["language"] == "python"


def test_scan_import_candidates_lists_python_and_r_with_metadata_fallback(tmp_path):
    source_root = tmp_path / "plugins" / "tools"
    python_tool = source_root / "python_stats"
    python_tool.mkdir(parents=True)
    (python_tool / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "python-stats",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "description": "Python stats",
                "entry": "main.py",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (python_tool / "main.py").write_text("print('ok')\n", encoding="utf-8")
    r_tool = source_root / "r_survival"
    r_tool.mkdir()
    (r_tool / "runner.R").write_text("cat('ok')\n", encoding="utf-8")

    grouped = WorkspaceToolService(tmp_path).scan_import_candidates()

    assert [item["id"] for item in grouped["python"]] == ["python-stats"]
    assert grouped["python"][0]["importable"] is True
    assert grouped["python"][0]["warnings"]
    assert [item["id"] for item in grouped["r"]] == ["r-survival"]
    assert grouped["r"][0]["description"] == "No description metadata provided"


def test_import_scanned_tools_by_selection_rejects_invalid_candidate(tmp_path):
    source_root = tmp_path / "plugins" / "tools"
    valid = source_root / "python_stats"
    valid.mkdir(parents=True)
    (valid / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "python-stats",
                "version": "0.1.0",
                "language": "python",
                "description": "Python stats",
                "entry": "main.py",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (valid / "main.py").write_text("print('ok')\n", encoding="utf-8")
    invalid = source_root / "r_bad"
    invalid.mkdir()
    (invalid / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "r-bad",
                "language": "r",
                "description": "Bad R tool",
                "entry": "missing.R",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    service = WorkspaceToolService(tmp_path)
    result = service.import_scanned_tools("trial-1", ["1", "2"])

    assert result["status"] == "partial"
    assert result["imported"][0]["tool"]["id"] == "python-stats"
    assert result["errors"][0]["id"] == "r-bad"
    assert not (tmp_path / "workspaces" / "trial-1" / "tools" / "r" / "r-bad").exists()


class TestWorkspaceToolImportScanned:
    def test_import_by_index(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "imported"
        assert len(result["imported"]) == 1
        assert result["imported"][0]["tool"]["id"] == "py-heatmap"

    def test_import_by_slug(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["r-umap"])

        assert result["status"] == "imported"
        assert result["imported"][0]["tool"]["language"] == "r"

    def test_import_by_language_prefixed_slug(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["python/py-heatmap"])

        assert result["status"] == "imported"
        assert result["imported"][0]["tool"]["id"] == "py-heatmap"

    def test_import_both_languages(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1", "2"])

        assert result["status"] == "imported"
        assert len(result["imported"]) == 2
        imported_ids = {item["tool"]["id"] for item in result["imported"]}
        assert imported_ids == {"py-heatmap", "r-umap"}

    def test_import_no_candidates_returns_no_candidates(self, tmp_path: Path):
        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "no_candidates"
        assert result["imported"] == []
        assert result["errors"] == []

    def test_import_invalid_selection_raises(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        with pytest.raises(ToolCandidateError, match="Unknown scanned tool selection"):
            service.import_scanned_tools("trial-1", ["999"])

    def test_import_empty_selection_raises(self, tmp_path: Path):
        service = WorkspaceToolService(tmp_path)
        with pytest.raises(ToolCandidateError, match="Select one or more"):
            service.import_scanned_tools("trial-1", [])

    def test_import_creates_manifest_in_workspace(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "my_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "my-tool",
                    "version": "2.0.0",
                    "type": "tool",
                    "language": "python",
                    "description": "My tool",
                    "entry": "main.py",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "imported"
        workspace_tool_dir = (
            tmp_path / "workspaces" / "trial-1" / "tools" / "python" / "my-tool"
        )
        assert workspace_tool_dir.is_dir()
        assert (workspace_tool_dir / "tool.yaml").is_file()
        assert (workspace_tool_dir / "main.py").is_file()

    def test_import_writes_normalized_manifest(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "norm_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "norm-tool",
                    "version": "3.0.0",
                    "type": "tool",
                    "language": "python",
                    "description": "Normalization test",
                    "entry": "main.py",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1"])

        manifest_path = (
            tmp_path
            / "workspaces"
            / "trial-1"
            / "tools"
            / "python"
            / "norm-tool"
            / "tool.yaml"
        )
        manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data["id"] == "norm-tool"
        assert manifest_data["language"] == "python"
        assert manifest_data["version"] == "3.0.0"
        assert isinstance(manifest_data["dependencies"], list)
        assert isinstance(manifest_data["inputs"], list)
        assert isinstance(manifest_data["outputs"], list)

    def test_import_existing_tool_without_overwrite_returns_exists(
        self, tmp_path: Path
    ):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        first = service.import_scanned_tools("trial-1", ["1"])
        second = service.import_scanned_tools("trial-1", ["1"])

        assert first["status"] == "imported"
        assert second["status"] == "imported"
        assert second["imported"][0]["status"] == "exists"

    def test_import_overwrite_replaces_existing(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1"])
        result = service.import_scanned_tools("trial-1", ["1"], overwrite=True)

        assert result["status"] == "imported"
        assert result["imported"][0]["status"] == "imported"

    def test_import_partial_when_one_candidate_invalid(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "py_good"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "py-good",
                    "version": "0.1.0",
                    "type": "tool",
                    "language": "python",
                    "entry": "main.py",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
        r_dir = source_root / "r_bad"
        r_dir.mkdir()
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "r-bad",
                    "version": "0.1.0",
                    "type": "tool",
                    "language": "r",
                    "description": "Bad R tool",
                    "entry": "missing.R",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1", "2"])

        assert result["status"] == "partial"
        assert len(result["imported"]) == 1
        assert result["imported"][0]["tool"]["id"] == "py-good"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["language"] == "r"

    def test_import_deduplicates_selections(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1", "1", "1"])

        assert result["status"] == "imported"
        assert len(result["imported"]) == 1

    def test_import_r_tool_creates_correct_directory_structure(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        r_dir = source_root / "r_kaplan"
        r_dir.mkdir(parents=True)
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "r-kaplan",
                    "version": "0.1.0",
                    "type": "tool",
                    "language": "r",
                    "description": "Kaplan-Meier",
                    "entry": "runner.R",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (r_dir / "runner.R").write_text("cat('km')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        result = service.import_scanned_tools("trial-1", ["1"])

        assert result["status"] == "imported"
        r_tool_dir = tmp_path / "workspaces" / "trial-1" / "tools" / "r" / "r-kaplan"
        assert r_tool_dir.is_dir()
        assert (r_tool_dir / "runner.R").is_file()
        assert (r_tool_dir / "tool.yaml").is_file()
        manifest_data = yaml.safe_load((r_tool_dir / "tool.yaml").read_text(encoding="utf-8"))
        assert manifest_data["language"] == "r"

    def test_import_heatmap_umap_remain_available_from_workspace_context(
        self, tmp_path: Path
    ):
        source_root = tmp_path / "plugins" / "tools"
        _setup_import_source_tools(source_root)
        workspace_path = tmp_path / "workspaces" / "trial-1"
        service = WorkspaceToolService(workspace_path)

        result = service.import_scanned_tools(
            "trial-1", ["python/py-heatmap", "r/r-umap"]
        )
        listed = service.list_tools("trial-1")

        assert result["status"] == "imported"
        assert [tool["id"] for tool in listed["python"]] == ["py-heatmap"]
        assert [tool["id"] for tool in listed["r"]] == ["r-umap"]


def test_cli_tool_add_without_selection_returns_scanned_candidates(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "plugins" / "tools" / "python_stats"
    source.mkdir(parents=True)
    (source / "plugin.yaml").write_text(
        yaml.safe_dump(
            {"name": "python-stats", "language": "python", "entry": "main.py"},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "main.py").write_text("print('ok')\n", encoding="utf-8")

    result = CLI().tool_add("trial-1")

    assert result["status"] == "select_required"
    assert result["candidates"]["python"][0]["id"] == "python-stats"


def test_cli_tool_add_selection_imports_scanned_tool_and_records_runtime_state(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "plugins" / "tools" / "python_stats"
    source.mkdir(parents=True)
    (source / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "python-stats",
                "version": "0.1.0",
                "language": "python",
                "description": "Python stats",
                "entry": "main.py",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "main.py").write_text("print('ok')\n", encoding="utf-8")

    result = CLI().tool_add("trial-1", selections=["1"])

    assert result["status"] == "imported"
    assert result["imported"][0]["tool"]["id"] == "python-stats"
    assert (
        tmp_path / "workspaces" / "trial-1" / "tools" / "python" / "python-stats"
    ).is_dir()
    state = yaml.safe_load(
        (tmp_path / ".supermedicine" / "config.yaml").read_text(encoding="utf-8")
    )["runtime_state"]
    assert state["last_workspace_id"] == "trial-1"
    assert state["last_tool_import"] == {
        "workspace_id": "trial-1",
        "tools": [{"language": "python", "id": "python-stats", "name": "python-stats"}],
    }


def test_show_returns_manifest_details_and_entrypoint_path(tmp_path):
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    service.add_builtin_tool("trial-1", "python", "heatmap")

    shown = service.show_tool("trial-1", "python", "heatmap")

    assert shown["id"] == "heatmap"
    assert shown["language"] == "python"
    assert shown["entrypoint"] == "runner.py"
    assert shown["entrypoint_path"].endswith("runner.py")
    assert shown["path"].endswith(str(Path("tools") / "python" / "heatmap"))


class TestWorkspaceToolListShow:
    def test_list_returns_imported_tools_grouped_by_language(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "py_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "py-tool",
                    "version": "0.1.0",
                    "type": "tool",
                    "language": "python",
                    "entry": "main.py",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
        r_dir = source_root / "r_tool"
        r_dir.mkdir()
        (r_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "r-tool",
                    "version": "0.1.0",
                    "type": "tool",
                    "language": "r",
                    "entry": "runner.R",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (r_dir / "runner.R").write_text("cat('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1", "2"])

        grouped = service.list_tools("trial-1")
        assert [tool["id"] for tool in grouped["python"]] == ["py-tool"]
        assert [tool["id"] for tool in grouped["r"]] == ["r-tool"]

    def test_show_tool_returns_full_details(self, tmp_path: Path):
        source_root = tmp_path / "plugins" / "tools"
        py_dir = source_root / "detail_tool"
        py_dir.mkdir(parents=True)
        (py_dir / "plugin.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "detail-tool",
                    "version": "2.0.0",
                    "type": "tool",
                    "language": "python",
                    "description": "Detailed tool",
                    "entry": "main.py",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        (py_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")

        service = WorkspaceToolService(tmp_path)
        service.import_scanned_tools("trial-1", ["1"])

        shown = service.show_tool("trial-1", "python", "detail-tool")
        assert shown["id"] == "detail-tool"
        assert shown["language"] == "python"
        assert shown["version"] == "2.0.0"
        assert shown["description"] == "Detailed tool"
        assert shown["entrypoint"] == "main.py"
        assert "path" in shown
        assert "entrypoint_path" in shown


def test_runner_templates_report_missing_dependency_messages_without_heavy_imports():
    python_runner = BUILTIN_TEMPLATES[("python", "heatmap")]["runner.py"]
    r_runner = BUILTIN_TEMPLATES[("r", "umap")]["runner.R"]

    assert "Missing optional Python dependencies" in python_runner
    assert "importlib.util.find_spec" in python_runner
    assert "Missing optional R dependencies" in r_runner
    assert "requireNamespace" in r_runner


def test_prepare_invocation_is_permission_guarded_and_audited(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.workspace_tools.shutil.which", lambda executable: f"/bin/{executable}"
    )
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    service.add_builtin_tool("trial-1", "python", "heatmap")
    audit_log = tmp_path / "audit.jsonl"
    engine = RecordingPermissionEngine(PermissionResult.ALLOWED)

    plan = service.prepare_invocation(
        "trial-1",
        "python",
        "heatmap",
        dry_run=True,
        input_path="data/matrix.csv",
        output_path="outputs/heatmap.png",
        permission_engine=engine,
        audit_logger=AuditLogger(audit_log),
    )

    assert engine.calls[0]["action"] == "tool.run"
    assert engine.calls[0]["context"]["workspace_id"] == "trial-1"
    assert engine.calls[0]["context"]["language"] == "python"
    assert plan.to_dict()["status"] == "prepared"
    assert plan.command[0] == "python"
    assert "--input" in plan.command
    entry = json.loads(audit_log.read_text(encoding="utf-8").strip())
    assert entry["action"] == "tool.run"
    assert entry["result"] == "allowed"


def test_permission_deny_prevents_prepared_invocation_and_audits(tmp_path):
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    service.add_builtin_tool("trial-1", "r", "umap")
    audit_log = tmp_path / "audit.jsonl"
    engine = RecordingPermissionEngine(PermissionResult.DENIED)

    with pytest.raises(DangerousOperationDenied):
        service.prepare_invocation(
            "trial-1",
            "r",
            "umap",
            dry_run=True,
            permission_engine=engine,
            audit_logger=AuditLogger(audit_log),
        )

    assert len(engine.calls) == 1
    entry = json.loads(audit_log.read_text(encoding="utf-8").strip())
    assert entry["action"] == "tool.run"
    assert entry["result"] == "denied"


def test_unsafe_entrypoint_input_and_output_paths_are_rejected(tmp_path):
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    service.add_builtin_tool("trial-1", "python", "heatmap")
    manifest_path = (
        tmp_path
        / "workspaces"
        / "trial-1"
        / "tools"
        / "python"
        / "heatmap"
        / "tool.yaml"
    )

    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace("runner.py", "../runner.py"),
        encoding="utf-8",
    )
    with pytest.raises(ToolManifestError, match="relative path"):
        service.load_manifest("trial-1", "python", "heatmap")

    service.add_builtin_tool("trial-1", "python", "heatmap", overwrite=True)
    with pytest.raises(WorkspaceToolError, match="outside workspace"):
        service.prepare_invocation(
            "trial-1",
            "python",
            "heatmap",
            dry_run=True,
            input_path="../outside.csv",
            permission_engine=RecordingPermissionEngine(PermissionResult.ALLOWED),
            audit_logger=AuditLogger(tmp_path / "audit-input.jsonl"),
        )
    with pytest.raises(WorkspaceToolError, match="outside workspace"):
        service.prepare_invocation(
            "trial-1",
            "python",
            "heatmap",
            dry_run=True,
            output_path="../outside.png",
            permission_engine=RecordingPermissionEngine(PermissionResult.ALLOWED),
            audit_logger=AuditLogger(tmp_path / "audit-output.jsonl"),
        )


def test_cli_tool_commands_require_explicit_workspace(monkeypatch):
    monkeypatch.setattr("sys.argv", ["supermedicine", "tool", "init"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2


def test_cli_tool_commands_do_not_read_tui_recent_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = WorkspaceToolService(tmp_path)
    service.initialize_tools("trial-1")
    manager = WorkspaceManager(tmp_path)
    manager.save_recent_selection("trial-1")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("CLI tool commands must not read TUI recent state")

    monkeypatch.setattr(
        "core.workspace.WorkspaceManager.load_recent_selection", fail_if_called
    )

    result = CLI().tool_list("trial-1")

    assert result == {"python": [], "r": []}


def test_cli_tool_run_uses_default_policy_and_writes_audit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    cli = CLI()
    cli.tool_init("trial-1")
    WorkspaceToolService(tmp_path).add_builtin_tool("trial-1", "python", "heatmap")

    result = cli.tool_run("trial-1", "python", "heatmap", dry_run=True)

    assert result["status"] == "prepared"
    assert result["command"][0] == "python"
    audit_entries = [
        json.loads(line)
        for line in (tmp_path / ".supermedicine" / "policies" / "audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert any(
        entry["action"] == "tool.run" and entry["result"] == "allowed"
        for entry in audit_entries
    )


def test_legacy_cli_run_flags_still_work_without_workspace(monkeypatch, tmp_path):
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
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()
            self._config_path = kwargs["config_path"]
            self._plugins_dir = kwargs["plugins_dir"]
            self._policies_dir = kwargs["policies_dir"]

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["task"] = task
            captured["plugin_name"] = plugin_name
            captured["action"] = action
            captured["params"] = params
            return {"status": "success"}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)

    CLI().run(
        "legacy task", plugin="python_stats", action="describe", params={"alpha": 1}
    )

    assert captured == {
        "task": "legacy task",
        "plugin_name": "python_stats",
        "action": "describe",
        "params": {"alpha": 1},
    }
