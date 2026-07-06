"""Adapter tests — merged from claude_code, opencode, and standalone."""

from __future__ import annotations

import builtins
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TypeVar

import pytest
import yaml

from adapters.base_adapter import BaseAdapter
from adapters.claude_code import ClaudeCodeAdapter
from adapters.opencode.adapter import OpenCodeAdapter
from adapters.standalone.adapter import StandaloneAdapter
from agents.base_agent import BaseAgent
from agents.orchestrator import Orchestrator
from permission.engine import PermissionEngine


# ═══ Shared Constants and Helpers ═══

FORBIDDEN_PLATFORM_AGENT_NAMES = {"Brain", "Planner", "Coder", "Tester"}
AdapterWithPolicy = TypeVar("AdapterWithPolicy", OpenCodeAdapter, StandaloneAdapter)


def _write_policy(project_dir: Path) -> None:
    policy_dir = project_dir / ".supermedicine" / "policies"
    policy_dir.mkdir(parents=True)
    (policy_dir / "default.yaml").write_text(
        """
- agent_id: "alpha"
  role: "analyst"
  permissions:
    allowed:
      - action: "tool_call"
        scope: "claude.capabilities"
      - action: "tool_call"
        scope: "claude.runtime_status"
      - action: "skill_load"
        scope: "*"
      - action: "execute"
        scope: "*"
    denied: []
- agent_id: "beta"
  role: "reviewer"
  permissions:
    allowed:
      - action: "tool_call"
        scope: "claude.invoke"
    denied: []
- agent_id: "gamma"
  role: "writer"
  permissions:
    allowed:
      - action: "tool_call"
        scope: "claude.capabilities"
    denied:
      - action: "tool_call"
        scope: "claude.invoke"
""".strip(),
        encoding="utf-8",
    )


def _adapter_with_policy(
    adapter_type: type[AdapterWithPolicy],
    tmp_path: Path,
    *,
    role: str,
    allowed: list[dict[str, str]],
    denied: list[dict[str, str]] | None = None,
    agent_id: str = "alpha",
) -> AdapterWithPolicy:
    policy_dir = tmp_path / ".supermedicine" / "policies"
    policy_dir.mkdir(parents=True)
    (policy_dir / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
        yaml.dump(
            {
                "agent_id": agent_id,
                "role": role,
                "permissions": {"allowed": allowed, "denied": denied or []},
            }
        ),
        encoding="utf-8",
    )
    engine = PermissionEngine(policy_dir, policy_dir / "audit.jsonl")
    return adapter_type(
        permission_engine=engine, project_dir=tmp_path, default_agent_id=agent_id
    )


@pytest.fixture
def permissive_opencode_adapter(tmp_path: Path) -> OpenCodeAdapter:
    return _adapter_with_policy(
        OpenCodeAdapter,
        tmp_path,
        role="adapter-test",
        allowed=[{"action": "tool_call", "scope": "*"}],
    )


@pytest.fixture
def permissive_standalone_adapter(tmp_path: Path) -> StandaloneAdapter:
    return _adapter_with_policy(
        StandaloneAdapter,
        tmp_path,
        role="standalone-test",
        allowed=[{"action": "tool_call", "scope": "*"}],
    )


class DummyEchoAgent(BaseAgent):
    def __init__(self, agent_id, role="test"):
        super().__init__(agent_id, role)

    def execute(self, task):
        return {"agent": self.agent_id, "echo": task, "status": "ok"}


# ═══ Claude Code Adapter Tests ═══


class TestClaudeCodeAdapter:
    """测试 Claude Code 适配器最小真实行为。"""

    def test_is_base_adapter(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        assert isinstance(adapter, BaseAdapter)

    def test_explicit_optional_import_degrades_without_claude_runtime(
        self, tmp_path, monkeypatch
    ):
        _write_policy(tmp_path)
        sys.modules.pop("adapters.claude_code", None)
        sys.modules.pop("adapters.claude_code.adapter", None)
        module = importlib.import_module("adapters.claude_code.adapter")
        monkeypatch.setattr(module.shutil, "which", lambda command: None)

        adapter = module.ClaudeCodeAdapter(project_dir=tmp_path)
        capabilities = adapter.tool_call("claude.capabilities", {})
        invoke = adapter.tool_call(
            "claude.invoke", {"agent_id": "beta", "prompt": "hello"}
        )

        assert capabilities["status"] == "ok"
        assert capabilities["result"]["optional"] is True
        assert capabilities["result"]["status"] == "runtime_unavailable"
        assert capabilities["result"]["runtime"]["required_for_core"] is False
        assert invoke["status"] == "unavailable"
        assert invoke["runtime"]["unavailable_is_core_failure"] is False

    def test_platform_name_and_registration(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        assert adapter.platform_name == "claude-code"
        assert adapter.registration["platform"] == "claude-code"
        assert adapter.registration["adapter_class"] == "ClaudeCodeAdapter"
        assert adapter.registration["optional"] is True
        assert adapter.registration["core"] is False
        assert adapter.registration["default"] is False
        assert adapter.registration["requires_core_runtime"] is False
        assert set(
            adapter.registration["ai_provider_support"]["supported_api_formats"]
        ) == {"openai", "anthropic", "openrouter"}
        assert (
            adapter.registration["ai_provider_support"]["secret_redaction"]["required"]
            is True
        )
        assert "not imported" in adapter.registration["limitations"][0]

    def test_capabilities_available_with_mock_runtime(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which",
            lambda command: "/usr/bin/claude",
        )
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.capabilities", {})
        assert result["status"] == "ok"
        assert result["result"]["features"]["permission_checked_calls"] is True
        assert result["result"]["features"]["native_subagent_dispatch"] is False
        assert result["result"]["features"]["native_skill_load"] is False
        assert result["result"]["features"]["ai_provider_config_discovery"] is True
        assert result["result"]["features"]["ai_provider_secret_redaction"] is True
        assert result["result"]["features"]["custom_ai_provider_base_url"] is True
        assert set(result["result"]["ai_provider"]["supported_api_formats"]) == {
            "openai",
            "anthropic",
            "openrouter",
        }
        assert (
            result["result"]["ai_provider"]["secret_redaction"][
                "plain_text_keys_in_manifest_or_docs"
            ]
            is False
        )
        assert result["result"]["optional"] is True
        assert result["result"]["status"] == "available"
        user_facing_names = [
            agent["name"] for agent in result["result"]["user_facing_agents"]
        ]
        assert user_facing_names == ["SuperMedicine"]
        assert len(result["result"]["user_facing_agents"]) == 1
        assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(user_facing_names)
        assert result["result"]["internal_role_contexts"] == [
            "alpha",
            "beta",
            "gamma",
            "delta",
        ]

    def test_capabilities_do_not_expose_environment_api_keys(
        self, tmp_path, monkeypatch
    ):
        _write_policy(tmp_path)
        openai_secret = "sk-test-claude-env-secret"
        anthropic_secret = "anthropic-test-claude-env-secret"
        monkeypatch.setenv("OPENAI_API_KEY", openai_secret)
        monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic_secret)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which", lambda command: None
        )

        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.capabilities", {})

        serialized = str(result)
        assert openai_secret not in serialized
        assert anthropic_secret not in serialized
        assert "<redacted>" in serialized

    def test_runtime_unavailable_returns_structured_state(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which", lambda command: None
        )
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call(
            "claude.invoke", {"agent_id": "beta", "prompt": "hello"}
        )
        assert result["status"] == "unavailable"
        assert result["runtime"]["available"] is False
        assert result["runtime"]["required_for_core"] is False
        assert result["runtime"]["ai_provider_configured"]["supported_api_formats"] == [
            "anthropic",
            "openai",
            "openrouter",
        ]
        assert (
            result["runtime"]["ai_provider_configured"]["secret_redaction_required"]
            is True
        )
        assert (
            result["runtime"]["ai_provider_configured"][
                "plaintext_api_keys_in_manifest_or_docs"
            ]
            is False
        )
        assert result["metadata"]["adapter"]["core_failure"] is False
        assert "error" in result

    def test_invoke_available_mock_path(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which",
            lambda command: "/usr/bin/claude",
        )

        def fake_run(command, cwd, capture_output, text, encoding, errors, timeout):
            return subprocess.CompletedProcess(
                command, 0, stdout="mock claude output", stderr=""
            )

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fake_run)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call(
            "claude.invoke", {"agent_id": "beta", "prompt": "hello"}
        )
        assert result["status"] == "ok"
        assert result["result"] == "mock claude output"
        assert result["metadata"]["security"]["permission_checked"] is True

    def test_invoke_timeout_returns_structured_timeout(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which",
            lambda command: "/usr/bin/claude",
        )

        def fake_run(command, cwd, capture_output, text, encoding, errors, timeout):
            raise subprocess.TimeoutExpired(command, timeout)

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fake_run)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call(
            "claude.invoke", {"agent_id": "beta", "prompt": "hello", "timeout": 1}
        )

        assert result["status"] == "timeout"
        assert result["error_code"] == "timeout"
        assert result["retryable"] is True
        assert result["metadata"]["resource"]["timeout_seconds"] == 1

    def test_invoke_redacts_secret_like_prompt_and_runtime_error(
        self, tmp_path, monkeypatch
    ):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which",
            lambda command: "/usr/bin/claude",
        )
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        api_key_label = "api" + "_" + "key"
        token_label = "tok" + "en"
        prompt_payload = "redaction" + "-" + "payload"
        runtime_payload = "runtime" + "-" + "payload"

        dry_run = adapter.tool_call(
            "claude.invoke",
            {
                "agent_id": "beta",
                "prompt": f"use {api_key_label}={prompt_payload}",
                "dry_run": True,
            },
        )
        assert prompt_payload not in str(dry_run)
        assert "[REDACTED]" in str(dry_run)
        assert dry_run["metadata"]["security"]["permission_checked"] is True

        def fake_run(command, cwd, capture_output, text, encoding, errors, timeout):
            return subprocess.CompletedProcess(
                command, 1, stdout="", stderr=f"{token_label}={runtime_payload} failed"
            )

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fake_run)
        error = adapter.tool_call(
            "claude.invoke", {"agent_id": "beta", "prompt": "hello"}
        )
        assert error["status"] == "runtime_error"
        assert runtime_payload not in str(error)
        assert "[REDACTED]" in str(error)

    def test_permission_denied_before_invoke(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which",
            lambda command: "/usr/bin/claude",
        )
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call(
            "claude.invoke", {"agent_id": "gamma", "prompt": "hello"}
        )
        assert result["status"] == "denied"
        assert result["resource"] == "claude.invoke"

    def test_permission_denied_before_runtime_subprocess(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr(
            "adapters.claude_code.adapter.shutil.which",
            lambda command: "/usr/bin/claude",
        )

        def fail_if_invoked(*args, **kwargs):
            raise AssertionError("denied claude.invoke must not call subprocess")

        monkeypatch.setattr(
            "adapters.claude_code.adapter.subprocess.run", fail_if_invoked
        )
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)

        result = adapter.tool_call(
            "claude.invoke", {"agent_id": "gamma", "prompt": "hello"}
        )

        assert result["status"] == "denied"
        assert result["resource"] == "claude.invoke"
        assert result["metadata"]["security"]["permission_checked"] is True

    def test_skill_load_returns_contract_metadata(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.skill_load("test-skill")
        assert "not natively loaded" in result
        assert "claude.capabilities" in result

    def test_subagent_dispatch_explicit_unavailable(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.subagent_dispatch("alpha", {"action": "test"})
        assert result["status"] == "unavailable"
        assert result["agent_id"] == "alpha"
        assert "Native Claude Code sub-agent dispatch" in result["error"]
        assert result["user_facing"] is False
        assert result["internal_role_context"] is True

    def test_unsupported_tool_returns_structured_error(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("unknown", {})
        assert result["status"] == "error"
        assert result["error_code"] == "unsupported_tool"
        assert "supported_tools" in result

    def test_skill_doc_stable_api_examples_and_boundary(self):
        content = (
            Path(__file__).parent.parent / "adapters" / "claude_code" / "SKILL.md"
        ).read_text(encoding="utf-8")

        assert "from plugins.rag.main import execute" in content
        assert "RAGProvider()" not in content
        assert "JournalArticle" in content
        assert "human expert review" in content
        assert "does not provide clinical advice" in content
        assert "No native Claude Code subagent dispatch is implemented" in content
        assert "No native Claude Code skill loading is implemented" in content
        assert "only user-facing Agent/surface is" in content
        assert "not a Claude Code Agent" in content
        assert "not a SuperMedicine core failure" in content
        assert "OpenAI-compatible and Anthropic-compatible" in content
        assert "OPENAI_API_KEY" in content
        assert "ANTHROPIC_API_KEY" in content
        assert "plaintext API key examples" in content
        assert "Installation Manifest Entry" in content
        assert "entry file: `adapters/claude_code/SKILL.md`" in content
        assert "Supported adapter tool IDs are limited" in content


# ═══ OpenCode Adapter Tests ═══


@pytest.fixture
def adapter():
    """创建 OpenCodeAdapter 实例"""
    return OpenCodeAdapter()


class TestAdapterImport:
    """测试适配器导入和继承"""

    def test_adapter_import(self, adapter):
        """验证 OpenCodeAdapter 可正确导入且为 BaseAdapter 子类"""
        assert isinstance(adapter, BaseAdapter)
        assert isinstance(adapter, OpenCodeAdapter)

    def test_explicit_optional_import_degrades_without_orchestrator(self):
        sys.modules.pop("adapters.opencode", None)
        sys.modules.pop("adapters.opencode.adapter", None)

        module = importlib.import_module("adapters.opencode.adapter")
        explicit_adapter = module.OpenCodeAdapter()

        capabilities = explicit_adapter.tool_call("opencode.capabilities", {})
        dispatch = explicit_adapter.subagent_dispatch(
            "alpha", {"action": "standalone-check"}
        )

        assert capabilities["status"] == "ok"
        assert capabilities["result"]["optional_add_on"] is True
        assert capabilities["result"]["status"] == "degraded"
        assert (
            capabilities["result"]["features"]["orchestrator_backed_dispatch"] is False
        )
        assert dispatch["status"] == "degraded"
        assert dispatch["error_code"] == "orchestrator_unavailable"
        assert dispatch["context"]["native_dispatch_executed"] is False

    def test_platform_name(self, adapter):
        """验证 platform_name 返回 'opencode'"""
        assert adapter.platform_name == "opencode"

    def test_capabilities_report_optional_degraded_boundary(self, adapter):
        result = adapter.tool_call("opencode.capabilities", {})

        assert result["status"] == "ok"
        capabilities = result["result"]
        assert capabilities["optional_add_on"] is True
        assert capabilities["status"] == "degraded"
        assert capabilities["features"]["core_runtime_dependency"] is False
        assert capabilities["features"]["native_opencode_subagent_runtime"] is False
        assert capabilities["features"]["permission_checked_dangerous_tools"] is True
        assert capabilities["features"]["ai_provider_config_discovery"] is True
        assert capabilities["features"]["ai_provider_secret_redaction"] is True
        assert capabilities["features"]["custom_ai_provider_base_url"] is True
        assert set(capabilities["ai_provider"]["supported_api_formats"]) == {
            "openai",
            "anthropic",
            "openrouter",
        }
        assert (
            capabilities["ai_provider"]["supported_api_formats"]["openai"][
                "custom_base_url"
            ]
            is True
        )
        assert capabilities["ai_provider"]["secret_redaction"]["required"] is True
        assert (
            capabilities["ai_provider"]["secret_redaction"]["redacted_value"]
            == "<redacted>"
        )
        assert capabilities["ai_provider"]["degraded_without_orchestrator"] is True
        user_facing_names = [
            agent["name"] for agent in capabilities["user_facing_agents"]
        ]
        assert user_facing_names == ["SuperMedicine"]
        assert len(capabilities["user_facing_agents"]) == 1
        assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(user_facing_names)
        assert set(capabilities["internal_role_contexts"]) == {
            "alpha-analyst.md",
            "beta-reviewer.md",
            "gamma-writer.md",
            "delta-orchestrator.md",
        }

    def test_capabilities_do_not_expose_environment_api_keys(
        self, adapter, monkeypatch
    ):
        openai_secret = "sk-test-opencode-env-secret"
        anthropic_secret = "anthropic-test-opencode-env-secret"
        monkeypatch.setenv("OPENAI_API_KEY", openai_secret)
        monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic_secret)

        result = adapter.tool_call("opencode.capabilities", {})

        serialized = json.dumps(result, ensure_ascii=False)
        assert openai_secret not in serialized
        assert anthropic_secret not in serialized
        assert "<redacted>" in serialized

    def test_registration_marks_opencode_as_optional_add_on(self, adapter):
        registration = adapter.registration
        assert registration["platform"] == "opencode"
        assert registration["status"] == "optional_add_on"
        assert registration["optional"] is True
        assert registration["core"] is False
        assert registration["default"] is False
        assert registration["requires_core_runtime"] is False
        assert "not imported" in registration["limitations"][0]


class TestToolCall:
    """测试 tool_call 方法"""

    def test_tool_call_bash(self, adapter):
        """验证 Tool_Call 能处理 Bash 工具调用"""
        result = adapter.tool_call("bash", {"command": "echo hello"})
        assert result["status"] == "ok"
        assert result["tool"] == "bash"
        assert "hello" in result["result"]

    def test_tool_call_read_write(self, adapter):
        """验证 Read/Write 工具调用在临时目录中正确工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            file_path = Path(tmpdir) / "test.txt"
            adapter = _adapter_with_policy(
                OpenCodeAdapter,
                project_dir,
                role="adapter-test",
                allowed=[{"action": "tool_call", "scope": str(file_path)}],
            )
            # Write
            write_result = adapter.tool_call(
                "write",
                {
                    "filePath": str(file_path),
                    "content": "Hello, SuperMedicine!",
                },
            )
            assert write_result["status"] == "ok"
            assert file_path.exists()

            # Read
            read_result = adapter.tool_call(
                "read",
                {
                    "filePath": str(file_path),
                },
            )
            assert read_result["status"] == "ok"
            assert "Hello, SuperMedicine!" in read_result["result"]

    def test_tool_call_unsupported(self, adapter):
        """验证不支持的工具返回错误"""
        result = adapter.tool_call("nonexistent", {})
        assert result["status"] == "error"
        assert "Unsupported" in result["result"]

    def test_task_tool_without_orchestrator_returns_degraded_result(self, adapter):
        result = adapter.tool_call(
            "task", {"agent_id": "alpha", "task": {"action": "test"}}
        )

        assert result["status"] == "degraded"
        assert result["tool"] == "task"
        assert result["error_code"] == "orchestrator_unavailable"
        assert result["context"]["native_dispatch_executed"] is False

    def test_high_risk_tool_denied_before_write_mutation(self, tmp_path):
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            tmp_path,
            role="adapter-test",
            allowed=[],
            denied=[{"action": "tool_call", "scope": "*"}],
        )
        file_path = tmp_path / "blocked.txt"

        result = adapter.tool_call(
            "write", {"filePath": str(file_path), "content": "blocked"}
        )

        assert result["status"] == "denied"
        assert result["error_code"] == "permission_denied"
        assert not file_path.exists()

    def test_high_risk_tool_allowed_with_explicit_policy(self, tmp_path):
        target = tmp_path / "allowed.txt"
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            tmp_path,
            role="adapter-test",
            allowed=[{"action": "tool_call", "scope": str(target)}],
        )

        result = adapter.tool_call(
            "write", {"filePath": str(target), "content": "allowed"}
        )

        assert result["status"] == "ok"
        assert target.read_text(encoding="utf-8") == "allowed"

    def test_tool_call_read_write_allows_same_file_when_policy_scope_uses_unresolved_path(
        self, tmp_path
    ):
        """Same-file policy scopes must survive adapter path resolution.

        The adapter checks permissions against BaseAdapter._tool_permission_resource(),
        which resolves filePath before calling PermissionEngine.check(), while the
        policy scope may come from the caller's original path string.  On CI roots
        that expose tmp paths through alternate representations (for example
        symlinked/private temp roots or case-normalized paths), exact string
        matching can deny the same file before write/read executes.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        policy_scope = project_dir / "nested" / ".." / "nested" / "same-file.txt"
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            project_dir,
            role="adapter-test",
            allowed=[{"action": "tool_call", "scope": str(policy_scope)}],
        )

        write_result = adapter.tool_call(
            "write",
            {
                "filePath": str(policy_scope),
                "content": "same file through unresolved policy scope",
            },
        )

        assert write_result["status"] == "ok"
        read_result = adapter.tool_call("read", {"filePath": str(policy_scope)})
        assert read_result["status"] == "ok"
        assert "same file through unresolved policy scope" in read_result["result"]

    def test_tool_call_read_write_allows_resolved_policy_scope_with_raw_params(
        self, tmp_path
    ):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        raw_file_path = (
            project_dir / "nested" / ".." / "nested" / "same-file-reversed.txt"
        )
        resolved_policy_scope = raw_file_path.resolve(strict=False)
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            project_dir,
            role="adapter-test",
            allowed=[{"action": "tool_call", "scope": str(resolved_policy_scope)}],
        )

        write_result = adapter.tool_call(
            "write",
            {
                "filePath": str(raw_file_path),
                "content": "same file through resolved policy scope",
            },
        )

        assert write_result["status"] == "ok"
        read_result = adapter.tool_call("read", {"filePath": str(raw_file_path)})
        assert read_result["status"] == "ok"
        assert "same file through resolved policy scope" in read_result["result"]

    def test_tool_call_read_write_does_not_allow_different_normalized_file(
        self, tmp_path
    ):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        allowed_file = project_dir / "nested" / "allowed.txt"
        different_file = project_dir / "nested" / "allowed.txt.bak"
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            project_dir,
            role="adapter-test",
            allowed=[
                {
                    "action": "tool_call",
                    "scope": str(allowed_file.resolve(strict=False)),
                }
            ],
        )

        write_result = adapter.tool_call(
            "write",
            {
                "filePath": str(different_file),
                "content": "must not be written",
            },
        )

        assert write_result["status"] == "denied"
        assert not different_file.exists()

    def test_tool_call_glob(self, adapter):
        """验证 Glob 工具调用"""
        result = adapter.tool_call(
            "glob",
            {
                "pattern": "*.py",
                "path": str(Path(__file__).parent.parent / "Cli.py").rsplit("\\", 1)[0]
                if "\\" in str(Path(__file__).parent.parent)
                else str(Path(__file__).parent.parent),
            },
        )
        assert result["status"] == "ok"
        # Should Find at Least CLI.Py
        assert len(result["result"]) > 0

    def test_tool_call_grep(self, adapter):
        """验证 Grep 工具调用"""
        adapter_dir = Path(__file__).parent.parent
        result = adapter.tool_call(
            "grep",
            {
                "pattern": "class OpenCodeAdapter",
                "path": str(adapter_dir / "adapters" / "opencode"),
                "include": "*.py",
            },
        )
        assert result["status"] == "ok"
        assert "OpenCodeAdapter" in result["result"]

    def test_filesystem_tools_deny_paths_outside_project_root(
        self, permissive_opencode_adapter, tmp_path
    ):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
        outside_file = outside_dir / "blocked.txt"
        assert not outside_file.exists()

        write_result = permissive_opencode_adapter.tool_call(
            "write", {"filePath": str(outside_file), "content": "blocked"}
        )
        read_result = permissive_opencode_adapter.tool_call(
            "read", {"filePath": str(outside_file)}
        )
        glob_result = permissive_opencode_adapter.tool_call(
            "glob", {"path": str(outside_dir), "pattern": "*"}
        )
        grep_result = permissive_opencode_adapter.tool_call(
            "grep", {"path": str(outside_dir), "pattern": "blocked"}
        )

        assert write_result["status"] == "denied"
        assert write_result["error_code"] == "sandbox_denied"
        assert not outside_file.exists()
        assert read_result["status"] == "denied"
        assert glob_result["status"] == "denied"
        assert grep_result["status"] == "denied"

    def test_edit_does_not_mutate_outside_project_root(
        self, permissive_opencode_adapter, tmp_path
    ):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-edit"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "blocked.txt"
        outside_file.write_text("old", encoding="utf-8")

        result = permissive_opencode_adapter.tool_call(
            "edit",
            {"filePath": str(outside_file), "oldString": "old", "newString": "new"},
        )

        assert result["status"] == "denied"
        assert result["error_code"] == "sandbox_denied"
        assert outside_file.read_text(encoding="utf-8") == "old"

    def test_bash_permission_denied_before_execution(self, tmp_path):
        marker = tmp_path / "should_not_exist.txt"
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            tmp_path,
            role="adapter-test",
            allowed=[],
            denied=[{"action": "tool_call", "scope": "bash"}],
        )

        result = adapter.tool_call(
            "bash",
            {
                "command": f"python -c \"from pathlib import Path; Path(r'{marker}').write_text('ran')\"",
                "workdir": str(tmp_path),
            },
        )

        assert result["status"] == "denied"
        assert result["resource"] == "bash"

    def test_bash_uses_shell_free_argv_and_does_not_expand_metacharacters(
        self, tmp_path
    ):
        marker = tmp_path / "shell-injection-marker"
        adapter = _adapter_with_policy(
            OpenCodeAdapter,
            tmp_path,
            role="adapter-test",
            allowed=[{"action": "tool_call", "scope": "bash"}],
        )

        result = adapter.tool_call(
            "bash",
            {"command": ["python", "-c", "print('safe')"], "workdir": str(tmp_path)},
        )
        injected = adapter.tool_call(
            "bash",
            {
                "command": f"echo safe && python -c \"open(r'{marker}', 'w').write('bad')\"",
                "workdir": str(tmp_path),
            },
        )

        assert result["status"] == "ok"
        assert "safe" in result["result"]
        assert injected["status"] == "ok"
        assert not marker.exists()


class TestSkillLoad:
    """测试 skill_load 方法"""

    def test_skill_load_valid(self, adapter):
        """验证 skill_load 能加载存在的技能文件"""
        content = adapter.skill_load("rag-query")
        assert content is not None
        assert len(content) > 0
        # Should Contain Markdown Content
        assert (
            "rag" in content.lower()
            or "RAG" in content
            or "rag-query" in content.lower()
        )

    def test_skill_load_invalid(self, adapter):
        """验证 skill_load 对不存在的技能返回合理错误信息"""
        content = adapter.skill_load("nonexistent-skill-xyz")
        assert "not found" in content.lower() or "error" in content.lower()


class TestSubagentDispatch:
    """测试 subagent_dispatch 方法"""

    def test_subagent_dispatch(self, adapter):
        """验证 subagent_dispatch 返回有效响应"""
        result = adapter.subagent_dispatch(
            "alpha", {"action": "test", "data": "sample"}
        )
        assert result["agent_id"] == "alpha"
        assert result["status"] == "degraded"
        assert result["error_code"] == "orchestrator_unavailable"
        assert result["context"]["native_dispatch_executed"] is False
        assert result["context"]["user_facing"] is False
        assert result["context"]["internal_role_context"] is True
        assert "task" in result
        assert result["task"]["action"] == "test"


class TestPluginJson:
    """测试 Plugin.JSON 完整性"""

    def test_plugin_json_valid(self):
        """验证 Plugin.JSON 可被 JSON 解析且包含所有必填字段"""
        plugin_path = (
            Path(__file__).parent.parent / "adapters" / "opencode" / "plugin.json"
        )
        assert plugin_path.exists(), "plugin.json not found"

        with open(plugin_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = [
            "name",
            "version",
            "description",
            "type",
            "entry",
            "permissions",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check Permissions
        assert "tools" in data["permissions"]
        assert len(data["permissions"]["tools"]) >= 9
        assert set(data["permissions"]["tools"]) == OpenCodeAdapter.SUPPORTED_TOOLS
        assert "opencode.capabilities" in data["permissions"]["tools"]
        assert set(data["permissions"]["high_risk_checked_tools"]) == {
            "bash",
            "write",
            "edit",
            "task",
        }
        assert set(data["permissions"]["high_risk_checked_tools"]).issubset(
            OpenCodeAdapter.SUPPORTED_TOOLS
        )
        assert "read" in data["permissions"]["sandboxed_filesystem_tools"]
        assert data["optional_add_on"] is True
        assert data["native_opencode_subagent_runtime"] is False
        assert data["core_runtime_required"] is False
        assert data["install_entry_files"]["adapter_module"] == "adapter.py"
        assert (
            plugin_path.parent / data["install_entry_files"]["plugin_manifest"]
        ).is_file()
        assert (
            plugin_path.parent / data["install_entry_files"]["adapter_module"]
        ).is_file()
        assert (
            plugin_path.parent / data["install_entry_files"]["single_user_facing_agent"]
        ).is_file()
        assert (
            plugin_path.parent / data["install_entry_files"]["skill_documents_dir"]
        ).is_dir()
        assert (
            plugin_path.parent
            / data["install_entry_files"]["internal_role_context_dir"]
        ).is_dir()
        assert (
            data["install_completeness_model"]["degraded_without_orchestrator"] is True
        )
        assert set(data["ai_provider"]["supported_api_formats"]) == {
            "openai",
            "anthropic",
            "openrouter",
        }
        assert (
            data["ai_provider"]["supported_api_formats"]["anthropic"]["custom_base_url"]
            is True
        )
        assert data["ai_provider"]["secret_redaction_required"] is True
        assert data["ai_provider"]["redacted_value"] == "<redacted>"
        assert data["ai_provider"]["plaintext_api_keys_in_manifest"] is False
        assert data["ai_provider"]["degraded_without_orchestrator"] is True
        assert data["install"]["log_redaction_required"] is True
        assert data["uninstall"]["remove_recorded_opencode_artifacts_only"] is True

        # Check Skills
        assert "skills" in data
        assert len(data["skills"]) == 6
        for skill_path in data["skills"]:
            assert (plugin_path.parent / skill_path).is_file(), (
                f"Missing declared OpenCode skill: {skill_path}"
            )

        # Check Agents: exactly one user-facing OpenCode agent
        assert "agents" in data
        assert data["agents"] == ["agents/supermedicine.md"]
        user_facing_names = [agent["name"] for agent in data["user_facing_agents"]]
        assert user_facing_names == ["SuperMedicine"]
        assert len(data["user_facing_agents"]) == 1
        assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(user_facing_names)
        assert sorted(data["internal_role_contexts"]) == sorted(
            [
                "agents/alpha-analyst.md",
                "agents/beta-reviewer.md",
                "agents/gamma-writer.md",
                "agents/delta-orchestrator.md",
            ]
        )


class TestSkillsExist:
    """测试所有 SKILL.Md 文件存在"""

    def test_all_skills_exist(self):
        """验证 6 个 SKILL.Md 文件存在"""
        skills_dir = Path(__file__).parent.parent / "adapters" / "opencode" / "skills"
        expected_skills = [
            "rag-query.md",
            "harness-monitor.md",
            "medical-writing.md",
            "medical-citation.md",
            "python-stats.md",
            "r-survival.md",
        ]
        for skill_file in expected_skills:
            skill_path = skills_dir / skill_file
            assert skill_path.exists(), f"Missing skill file: {skill_file}"
            content = skill_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Empty skill file: {skill_file}"

    def test_skill_docs_use_stable_python_api_examples(self):
        """Protect public OpenCode skill examples from drifting from actual APIs."""
        skills_dir = Path(__file__).parent.parent / "adapters" / "opencode" / "skills"

        rag_doc = (skills_dir / "rag-query.md").read_text(encoding="utf-8")
        assert "from plugins.rag.main import execute" in rag_doc
        assert "RAGProvider()" not in rag_doc
        assert "MockExternalVectorStoreProvider" in rag_doc

        citation_doc = (skills_dir / "medical-citation.md").read_text(encoding="utf-8")
        assert "JournalArticle" in citation_doc
        assert 'volume="331"' in citation_doc
        assert "standard.citation.ama" in citation_doc

        python_stats_doc = (skills_dir / "python-stats.md").read_text(encoding="utf-8")
        assert "stats.descriptive" in python_stats_doc
        assert "descriptive_stats" not in python_stats_doc
        assert "ttest_independent" not in python_stats_doc

        survival_doc = (skills_dir / "r-survival.md").read_text(encoding="utf-8")
        assert "r.survival.km" in survival_doc
        assert "groups=" not in survival_doc

    def test_skill_docs_preserve_interface_and_human_review_boundaries(self):
        """OpenCode skill docs must not overclaim clinical/production readiness."""
        skills_dir = Path(__file__).parent.parent / "adapters" / "opencode" / "skills"
        for skill_file in [
            "rag-query.md",
            "medical-citation.md",
            "medical-writing.md",
            "python-stats.md",
            "r-survival.md",
            "harness-monitor.md",
        ]:
            content = (skills_dir / skill_file).read_text(encoding="utf-8").lower()
            assert "human" in content or "expert review" in content
            assert "openai-compatible" in content
            assert "anthropic-compatible" in content
            assert "<redacted>" in content
            if "clinical-grade" in content:
                assert "not production-grade" in content


class TestAgentsExist:
    """测试所有 Agent 定义文件存在"""

    def test_user_facing_agent_and_internal_role_contexts_exist(self):
        """验证唯一用户可见 Agent 和内部 role context 文件存在"""
        agents_dir = Path(__file__).parent.parent / "adapters" / "opencode" / "agents"
        user_facing_agent = agents_dir / "supermedicine.md"
        assert user_facing_agent.exists(), (
            "Missing SuperMedicine user-facing agent file"
        )
        user_facing_content = user_facing_agent.read_text(encoding="utf-8")
        assert "name: SuperMedicine" in user_facing_content
        assert "user_facing: true" in user_facing_content
        assert "AI Provider Configuration" in user_facing_content
        assert "## Identity" in user_facing_content
        assert "answer as SuperMedicine" in user_facing_content
        assert "do not expose internal adapter wiring" in user_facing_content
        assert "<redacted>" in user_facing_content

        expected_contexts = [
            "alpha-analyst.md",
            "beta-reviewer.md",
            "gamma-writer.md",
            "delta-orchestrator.md",
        ]
        for agent_file in expected_contexts:
            agent_path = agents_dir / agent_file
            assert agent_path.exists(), (
                f"Missing internal role context file: {agent_file}"
            )
            content = agent_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Empty internal role context file: {agent_file}"
            assert "user_facing: false" in content
            assert "internal_role_context: true" in content
            assert "OpenCode Provider Boundary" in content


class TestOpenCodeRealDispatch:
    """测试真实 Dispatch（有 Orchestrator）"""

    def test_dispatch_with_orchestrator(self):
        """有 Orchestrator 时执行真实 Dispatch"""
        orch = Orchestrator()
        orch.register_agent(DummyEchoAgent("alpha", "test"))
        adapter = OpenCodeAdapter(orch)

        result = adapter.subagent_dispatch("alpha", {"action": "test", "data": 42})
        assert result["status"] == "ok"
        assert result["echo"]["data"] == 42

    def test_dispatch_unknown_agent(self):
        """未知 Agent 返回 Error"""
        orch = Orchestrator()
        adapter = OpenCodeAdapter(orch)
        result = adapter.subagent_dispatch("unknown", {"action": "test"})
        assert result["status"] == "error"

    def test_dispatch_without_orchestrator(self):
        """无 Orchestrator 时降级但不 Crash"""
        adapter = OpenCodeAdapter()
        result = adapter.subagent_dispatch("alpha", {"action": "test"})
        assert result["agent_id"] == "alpha"
        assert result["status"] == "degraded"
        assert result["error_code"] == "orchestrator_unavailable"
        assert result["capabilities"]["native_opencode_subagent_runtime"] is False


# ═══ Standalone Adapter Tests ═══


class TestStandaloneAdapter:
    """测试 Standalone 适配器"""

    def test_is_base_adapter(self):
        adapter = StandaloneAdapter()
        assert isinstance(adapter, BaseAdapter)

    def test_platform_name(self):
        adapter = StandaloneAdapter()
        assert adapter.platform_name == "standalone"

    def test_registration_marks_standalone_as_core_default(self):
        adapter = StandaloneAdapter()
        registration = adapter.registration
        assert registration["platform"] == "standalone"
        assert registration["status"] == "core_default"
        assert registration["optional"] is False
        assert registration["core"] is True
        assert registration["default"] is True
        assert registration["requires_core_runtime"] is True

    def test_explicit_standalone_import_does_not_load_optional_platform_adapters(self):
        for module_name in (
            "adapters.opencode",
            "adapters.opencode.adapter",
            "adapters.claude_code",
            "adapters.claude_code.adapter",
        ):
            sys.modules.pop(module_name, None)

        module = importlib.import_module("adapters.standalone.adapter")

        assert module.StandaloneAdapter().platform_name == "standalone"
        assert "adapters.opencode" not in sys.modules
        assert "adapters.opencode.adapter" not in sys.modules
        assert "adapters.claude_code" not in sys.modules
        assert "adapters.claude_code.adapter" not in sys.modules

    def test_tool_call_bash(self):
        adapter = StandaloneAdapter()
        result = adapter.tool_call("bash", {"command": "echo hello"})
        assert result["status"] == "ok"
        assert "hello" in result["result"]

    def test_tool_call_read_write(self):
        with tempfile.TemporaryDirectory() as td:
            adapter = _adapter_with_policy(
                StandaloneAdapter,
                Path(td),
                role="standalone-test",
                allowed=[{"action": "tool_call", "scope": "*"}],
            )
            fp = Path(td) / "test.txt"
            w = adapter.tool_call(
                "write", {"filePath": str(fp), "content": "test content"}
            )
            assert w["status"] == "ok"
            r = adapter.tool_call("read", {"filePath": str(fp)})
            assert "test content" in r["result"]

    def test_write_and_edit_fail_closed_when_permission_engine_unavailable(
        self, tmp_path
    ):
        adapter = StandaloneAdapter(permission_engine=None, project_dir=tmp_path)
        target = tmp_path / "blocked.txt"
        target.write_text("old", encoding="utf-8")
        policy_dir = tmp_path / ".supermedicine" / "policies"
        policy_dir.mkdir(parents=True)
        (policy_dir / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
            "invalid: [\n", encoding="utf-8"
        )

        write_result = adapter.tool_call(
            "write", {"filePath": str(target), "content": "new"}
        )
        edit_result = adapter.tool_call(
            "edit", {"filePath": str(target), "oldString": "old", "newString": "new"}
        )

        assert write_result["status"] == "denied"
        assert write_result["error_code"] == "permission_engine_unavailable"
        assert edit_result["status"] == "denied"
        assert target.read_text(encoding="utf-8") == "old"

    def test_tool_call_glob(self):
        adapter = StandaloneAdapter()
        result = adapter.tool_call("glob", {"pattern": "*.py", "path": "."})
        assert result["status"] == "ok"
        assert len(result["result"]) > 0

    def test_tool_call_unsupported(self):
        adapter = StandaloneAdapter()
        result = adapter.tool_call("nonexistent", {})
        assert result["status"] == "error"

    def test_denied_edit_returns_before_file_mutation(self, tmp_path):
        target = tmp_path / "blocked.txt"
        target.write_text("old", encoding="utf-8")
        adapter = _adapter_with_policy(
            StandaloneAdapter,
            tmp_path,
            role="standalone-test",
            allowed=[],
            denied=[{"action": "tool_call", "scope": "*"}],
        )

        result = adapter.tool_call(
            "edit", {"filePath": str(target), "oldString": "old", "newString": "new"}
        )

        assert result["status"] == "denied"
        assert target.read_text(encoding="utf-8") == "old"

    def test_allowed_read_with_explicit_policy(self, tmp_path):
        target = tmp_path / "allowed.txt"
        target.write_text("readable", encoding="utf-8")
        adapter = _adapter_with_policy(
            StandaloneAdapter,
            tmp_path,
            role="standalone-test",
            allowed=[{"action": "tool_call", "scope": str(target)}],
        )

        result = adapter.tool_call("read", {"filePath": str(target)})

        assert result["status"] == "ok"
        assert "readable" in result["result"]

    def test_filesystem_tools_deny_paths_outside_project_root(
        self, permissive_standalone_adapter, tmp_path
    ):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
        outside_file = outside_dir / "blocked.txt"
        assert not outside_file.exists()

        write_result = permissive_standalone_adapter.tool_call(
            "write", {"filePath": str(outside_file), "content": "blocked"}
        )
        read_result = permissive_standalone_adapter.tool_call(
            "read", {"filePath": str(outside_file)}
        )
        glob_result = permissive_standalone_adapter.tool_call(
            "glob", {"path": str(outside_dir), "pattern": "*"}
        )
        grep_result = permissive_standalone_adapter.tool_call(
            "grep", {"path": str(outside_dir), "pattern": "blocked"}
        )

        assert write_result["status"] == "denied"
        assert write_result["error_code"] == "sandbox_denied"
        assert not outside_file.exists()
        assert read_result["status"] == "denied"
        assert glob_result["status"] == "denied"
        assert grep_result["status"] == "denied"

    def test_edit_does_not_mutate_outside_project_root(
        self, permissive_standalone_adapter, tmp_path
    ):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-edit"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "blocked.txt"
        outside_file.write_text("old", encoding="utf-8")

        result = permissive_standalone_adapter.tool_call(
            "edit",
            {"filePath": str(outside_file), "oldString": "old", "newString": "new"},
        )

        assert result["status"] == "denied"
        assert result["error_code"] == "sandbox_denied"
        assert outside_file.read_text(encoding="utf-8") == "old"

    def test_bash_permission_denied_before_execution(self, tmp_path):
        marker = tmp_path / "should_not_exist.txt"
        adapter = _adapter_with_policy(
            StandaloneAdapter,
            tmp_path,
            role="standalone-test",
            allowed=[],
            denied=[{"action": "tool_call", "scope": "bash"}],
        )

        result = adapter.tool_call(
            "bash",
            {
                "command": f"python -c \"from pathlib import Path; Path(r'{marker}').write_text('ran')\"",
                "workdir": str(tmp_path),
            },
        )

        assert result["status"] == "denied"
        assert result["resource"] == "bash"

    def test_bash_accepts_argv_without_shell_expansion(self, tmp_path):
        marker = tmp_path / "should_not_exist.txt"
        adapter = _adapter_with_policy(
            StandaloneAdapter,
            tmp_path,
            role="standalone-test",
            allowed=[{"action": "tool_call", "scope": "bash"}],
        )

        result = adapter.tool_call(
            "bash",
            {"command": ["python", "-c", "print('safe')"], "workdir": str(tmp_path)},
        )

        assert result["status"] == "ok"
        assert "safe" in result["result"]
        assert not marker.exists()

    @pytest.mark.adapter
    def test_skill_load_returns_core_neutral_metadata(self):
        adapter = StandaloneAdapter()
        result = adapter.skill_load("rag-query")
        assert "Standalone skill 'rag-query'" in result
        assert "OpenCode" in result

    @pytest.mark.adapter
    def test_skill_load_does_not_read_opencode_skill_files(self, monkeypatch):
        opened_paths: list[str] = []
        original_open = builtins.open

        def tracking_open(file, *args, **kwargs):
            opened_paths.append(str(file))
            return original_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", tracking_open)

        result = StandaloneAdapter().skill_load("rag-query")

        assert "optional OpenCode adapter" in result
        assert not any(
            "adapters" in path and "opencode" in path and "skills" in path
            for path in opened_paths
        )

    def test_subagent_dispatch(self):
        adapter = StandaloneAdapter()
        result = adapter.subagent_dispatch("test-agent", {"action": "test"})
        assert result["agent_id"] == "test-agent"
        assert result["status"] == "dispatched"
        assert result["platform"] == "standalone"
