from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from Cli import CLI, main
from core.operation_guard import DangerousOperationDenied
from core.workspace import WorkspaceManager
from core.workspace_tools import (
    BUILTIN_TEMPLATES,
    MANIFEST_FILE,
    TOOL_AUTHORING_SPEC,
    InvalidToolId,
    ToolManifest,
    ToolManifestError,
    WorkspaceToolError,
    WorkspaceToolService,
    build_tool_authoring_llm_context,
    validate_language,
    validate_tool_id,
)
from core.workspace_tool_models import InvalidToolLanguage
from permission.audit import AuditLogger
from permission.policy import PermissionResult, ensure_default_policy


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_default_policy(project_dir: Path) -> None:
    ensure_default_policy(project_dir, source_root=REPO_ROOT)


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


@pytest.mark.parametrize("tool_id", ["heatmap", "umap-2", "a1"])
def test_tool_id_validation_accepts_safe_slugs(tool_id):
    assert validate_tool_id(tool_id) == tool_id


@pytest.mark.parametrize(
    "tool_id",
    [
        "",
        "Heatmap",
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
