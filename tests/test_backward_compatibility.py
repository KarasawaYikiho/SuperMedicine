from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest
import yaml

from cli_entry import CLI, main
from adapters.base_adapter import BaseAdapter
from core.kernel import Kernel
from core.llm_client import create_llm_client
from core.workspace import WorkspaceManager
from permission.engine import PermissionEngine
from permission.policy import PermissionResult, ensure_default_policy
from plugins.rag import main as rag_main


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_default_policy(project_dir: Path) -> None:
    ensure_default_policy(project_dir, source_root=REPO_ROOT)


def _write_policy(project_dir: Path, policy: dict | list[dict]) -> Path:
    policies = project_dir / ".supermedicine" / "policies"
    policies.mkdir(parents=True, exist_ok=True)
    (policies / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
        yaml.safe_dump(policy, sort_keys=False),
        encoding="utf-8",
    )
    return policies


def _init_args(project_dir: Path) -> list[str]:
    return [
        "init",
        "--dir",
        str(project_dir),
        "--provider",
        "openai",
        "--base-url",
        "https://openai.compat.test/v1",
        "--api-key",
        "compat-test-secret",
        "--model",
        "gpt-compat",
    ]


def test_cli_help_preserves_legacy_commands_and_run_flags(capsys):
    with pytest.raises(SystemExit) as top_level:
        main(["--help"])
    assert top_level.value.code == 0
    top_help = capsys.readouterr().out
    for command in ("init", "status", "test", "run"):
        assert command in top_help

    with pytest.raises(SystemExit) as run_help:
        main(["run", "--help"])
    assert run_help.value.code == 0
    run_output = capsys.readouterr().out
    for flag in (
        "--verbose",
        "--plugin",
        "--action",
        "--params-json",
        "--params-file",
        "--workspace",
    ):
        assert flag in run_output


@pytest.mark.core
def test_core_cli_kernel_imports_do_not_load_platform_adapters():
    for module_name in (
        "cli_entry",
        "core.kernel",
        "adapters.opencode",
        "adapters.opencode.adapter",
        "adapters.claude_code",
        "adapters.claude_code.adapter",
    ):
        sys.modules.pop(module_name, None)

    importlib.import_module("cli_entry")
    importlib.import_module("core.kernel")

    assert "adapters.opencode" not in sys.modules
    assert "adapters.opencode.adapter" not in sys.modules
    assert "adapters.claude_code" not in sys.modules
    assert "adapters.claude_code.adapter" not in sys.modules


def test_cli_help_and_init_do_not_require_platform_runtime_or_config(
    monkeypatch, tmp_path, capsys
):
    for module_name in (
        "adapters.opencode",
        "adapters.opencode.adapter",
        "adapters.claude_code",
        "adapters.claude_code.adapter",
    ):
        sys.modules.pop(module_name, None)

    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    top_help = capsys.readouterr().out
    assert "supermedicine" in top_help

    project_dir = tmp_path / "standalone-project"
    main(_init_args(project_dir))

    assert (project_dir / ".supermedicine" / "config.yaml").is_file()
    assert (
        project_dir
        / ".supermedicine"
        / "policies"
        / PermissionEngine.DEFAULT_POLICY_FILENAME
    ).is_file()
    assert not (project_dir / ".opencode").exists()
    assert not (project_dir / ".claude").exists()
    assert "adapters.opencode" not in sys.modules
    assert "adapters.opencode.adapter" not in sys.modules
    assert "adapters.claude_code" not in sys.modules
    assert "adapters.claude_code.adapter" not in sys.modules


def test_cli_help_documents_workspace_tui_paper_and_experience_boundaries(capsys):
    with pytest.raises(SystemExit) as top_level:
        main(["--help"])
    assert top_level.value.code == 0
    top_help = capsys.readouterr().out
    assert "tui" in top_help
    assert "workspace" in top_help

    help_cases = [
        (["run", "--help"], ["workspaces/<id>", "TUI"]),
        (["workspace", "delete", "--help"], ["硬删除", "权限", "审计", "--confirm"]),
        (
            ["paper", "import", "--help"],
            ["复制", "PDF", "TeX", "BibTeX", "RIS", "默认不联网", "--confirm-enrich"],
        ),
        (["paper", "enrich", "--help"], ["网络/API", "审计", "--confirm-enrich"]),
        (["experience", "--help"], ["不存原始对话"]),
    ]
    for argv, expected_fragments in help_cases:
        with pytest.raises(SystemExit) as help_exit:
            main(argv)
        assert help_exit.value.code == 0
        output = capsys.readouterr().out
        for fragment in expected_fragments:
            assert fragment in output


def test_cli_run_without_workspace_preserves_params_identity_and_ignores_tui_recent_state(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    captured: dict[str, object] = {}

    def fail_if_tui_recent_state_is_read(*args, **kwargs):
        raise AssertionError("run must not read TUI recent workspace state")

    monkeypatch.setattr(
        "core.tui.state.load_recent_workspace", fail_if_tui_recent_state_is_read
    )

    class FakeRegistry:
        def discover(self):
            return []

    class FakeCheckpointManager:
        base_dir = "checkpoints"

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            self._config_path = kwargs.get("config_path")
            self._plugins_dir = kwargs.get("plugins_dir")
            self._policies_dir = kwargs.get("policies_dir")
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["task"] = task
            captured["plugin_name"] = plugin_name
            captured["action"] = action
            captured["params"] = params
            return {
                "status": "success",
                "task": task,
                "plugin": plugin_name,
                "action": action,
                "output": {},
            }

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    monkeypatch.setattr("cli_entry.Kernel", FakeKernel, raising=False)
    params = {"source_id": "legacy-source", "nested": {"unchanged": True}}

    CLI().run(
        "legacy task", plugin="python-stats", action="stats.descriptive", params=params
    )

    assert captured == {
        "task": "legacy task",
        "plugin_name": "python-stats",
        "action": "stats.descriptive",
        "params": params,
    }
    assert captured["params"] is params
    assert "_workspace" not in params


def test_plugin_manifest_names_and_action_ids_are_unchanged():
    expected_actions = {
        "python-stats": {
            "stats.descriptive",
            "stats.ttest",
            "stats.anova",
            "stats.regression",
        },
        "experiment-wb": {
            "experiment.wb.normalize_loading",
            "experiment.wb.antibody_dilution",
        },
        "r-survival": {"r.survival.km", "r.survival.logrank", "r.survival.cox"},
        "rag-interface": {"rag.query", "rag.context.store", "rag.context.retrieve"},
        "medical-writing": {
            "standard.consort",
            "standard.strobe",
            "standard.prisma",
            "standard.stard",
        },
        "medical-citation": {"standard.citation.vancouver", "standard.citation.ama"},
        "harness-core": {
            "harness.integration.checkpoint",
            "harness.integration.checkpoint_all",
            "harness.monitor.permission_audit",
            "harness.monitor.denied_actions",
            "harness.monitor.anomaly",
            "harness.monitor.performance",
            "harness.monitor.failure_patterns",
        },
        "figure": {
            "figure.workflow",
            "figure-profile.profile",
            "figure-style.setup",
            "figure-style.list-fonts",
            "figure-export.export",
            "figure-check.audit",
            "figure-layout.labels",
            "figure-layout.finalize",
            "figure-qa.audit",
            "figure-qa.preview",
        },
    }

    discovered: dict[str, set[str]] = {}
    for manifest_path in (REPO_ROOT / "plugins").rglob("plugin.yaml"):
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        discovered[data["name"]] = {entry["id"] for entry in data.get("provides", [])}

    assert set(discovered) == set(expected_actions)
    for plugin_name, actions in expected_actions.items():
        assert discovered[plugin_name] == actions


def test_permission_engine_denies_unknown_agents_and_preserves_hard_limits(tmp_path):
    policies = _write_policy(
        tmp_path,
        {
            "agent_id": "limited",
            "role": "legacy-limit-test",
            "permissions": {
                "allowed": [{"action": "read", "scope": "*"}],
                "denied": [],
                "hard_limits": {
                    "max_file_size": 100,
                    "network_access": False,
                    "external_api": False,
                },
            },
        },
    )
    engine = PermissionEngine(policies, policies / "audit.jsonl")

    assert engine.check("unknown", "read", "file.txt") == PermissionResult.DENIED
    assert (
        engine.check("limited", "read", "file.txt", context={"max_file_size": 101})
        == PermissionResult.DENIED
    )
    assert (
        engine.check("limited", "read", "file.txt", context={"requires_network": True})
        == PermissionResult.DENIED
    )
    assert (
        engine.check(
            "limited", "read", "file.txt", context={"requires_external_api": True}
        )
        == PermissionResult.DENIED
    )


def test_kernel_execute_task_result_shape_and_permission_gate_are_stable(tmp_path):
    plugins_dir = tmp_path / "plugins"
    plugin_dir = plugins_dir / "compat_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "compat-plugin",
                "version": "0.1.0",
                "type": "tool",
                "language": "python",
                "entry": "main.py",
                "provides": [
                    {"id": "compat.action", "description": "Compatibility action"}
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (plugin_dir / "main.py").write_text(
        "def execute(action, params, context=None):\n"
        "    return {'status': 'success', 'output': {'echo': params}, 'metadata': {'custom': 'ok'}}\n",
        encoding="utf-8",
    )
    (tmp_path / "config.yaml").write_text("project: compat\n", encoding="utf-8")
    policies = _write_policy(
        tmp_path,
        [
            {
                "agent_id": "alpha",
                "role": "allowed",
                "permissions": {
                    "allowed": [{"action": "execute", "scope": "*"}],
                    "denied": [],
                },
            },
            {
                "agent_id": "blocked",
                "role": "denied",
                "permissions": {
                    "allowed": [],
                    "denied": [{"action": "execute", "scope": "*"}],
                },
            },
        ],
    )
    kernel = Kernel(
        config_path=tmp_path / "config.yaml",
        plugins_dir=plugins_dir,
        policies_dir=policies,
    )

    allowed = kernel.execute_task(
        "compat", plugin_name="compat-plugin", action="compat.action", params={"x": 1}
    )
    assert {
        "status",
        "task",
        "agent",
        "plugin",
        "action",
        "output",
        "result",
        "error",
        "metadata",
    }.issubset(allowed)
    assert allowed["status"] == "success"
    assert allowed["agent"] == "alpha"
    assert allowed["plugin"] == "compat-plugin"
    assert allowed["action"] == "compat.action"
    assert allowed["output"] == {"echo": {"x": 1}}
    assert allowed["result"] == allowed["output"]
    assert allowed["metadata"]["security"]["permission_checked"] is True

    denied = kernel.execute_task(
        "compat",
        plugin_name="compat-plugin",
        action="compat.action",
        agent_id="blocked",
    )
    assert denied["status"] == "denied"
    assert denied["agent"] == "blocked"
    assert denied["plugin"] == "compat-plugin"
    assert denied["action"] == "compat.action"
    assert denied["output"] is None
    assert denied["metadata"]["security"]["permission_checked"] is True
    assert denied["metadata"]["security"]["permission"] == "denied"


def test_rag_actions_and_result_contract_are_unchanged(tmp_path):
    storage_dir = tmp_path / "rag-storage"
    query = rag_main.execute(
        "rag.query",
        {
            "query": "hypertension",
            "top_k": 1,
            "storage_dir": str(storage_dir),
            "documents": [
                {"id": "doc-1", "text": "hypertension diabetes", "source": "fixture"}
            ],
        },
        {"agent_id": "alpha", "permission_checked": True},
    )

    assert query["status"] == "success"
    assert query["plugin"] == "rag-interface"
    assert query["action"] == "rag.query"
    assert {
        "items",
        "results",
        "relevance_scores",
        "source_metadata",
        "errors",
        "metadata",
    }.issubset(query["output"])
    assert query["metadata"]["contract"]["actions"] == rag_main.ACTION_CONTRACTS

    stored = rag_main.execute(
        "rag.context.store",
        {"key": "legacy", "data": {"v": 1}, "storage_dir": str(storage_dir)},
    )
    retrieved = rag_main.execute(
        "rag.context.retrieve", {"key": "legacy", "storage_dir": str(storage_dir)}
    )

    assert stored["status"] == "success"
    assert stored["action"] == "rag.context.store"
    assert stored["output"] == {"key": "legacy", "stored": True, "provider": "local"}
    assert retrieved["status"] == "success"
    assert retrieved["action"] == "rag.context.retrieve"
    assert retrieved["output"] == {
        "key": "legacy",
        "data": {"v": 1},
        "found": True,
        "provider": "local",
    }


def test_adapter_gated_tools_remain_bash_write_edit():
    assert BaseAdapter.PERMISSION_GATED_TOOLS == {"bash", "write", "edit"}


def test_legacy_openrouter_factory_still_uses_openai_compatible_defaults():
    client = create_llm_client("openrouter", api_key="test-openrouter-key")

    assert client.model == "anthropic/claude-3.5-sonnet"
    assert client.config.provider == "openrouter"
    assert client.config.api_format == "openai"
    assert client.config.base_url == "https://openrouter.ai/api/v1"
    assert client.config.safe_dict()["api_key"] == "<redacted>"


def test_paper_and_experience_paths_do_not_read_tui_recent_workspace_state(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("explicit-workspace")
    source = tmp_path / "paper.md"
    source.write_text("# Explicit workspace paper\n", encoding="utf-8")

    def fail_if_tui_recent_state_is_read(*args, **kwargs):
        raise AssertionError(
            "paper/experience CLI paths must not read TUI recent workspace state"
        )

    monkeypatch.setattr(
        "core.tui.state.load_recent_workspace", fail_if_tui_recent_state_is_read
    )

    imported = CLI().paper_import(
        "explicit-workspace", source, metadata={"title": "Explicit"}
    )
    suggestion = CLI().experience_suggest(
        "explicit-workspace", "Use explicit workspace only.", title="Explicit"
    )

    assert imported["metadata"]["title"] == "Explicit"
    assert suggestion["workspace_id"] == "explicit-workspace"
    assert suggestion["confirmed"] is False
