"""Claude Code 适配器测试 — 最小真实行为与权限边界。"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

from adapters.base_adapter import BaseAdapter
from adapters.claude_code import ClaudeCodeAdapter


FORBIDDEN_PLATFORM_AGENT_NAMES = {"Brain", "Planner", "Coder", "Tester"}


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


class TestClaudeCodeAdapter:
    """测试 Claude Code 适配器最小真实行为。"""

    def test_is_base_adapter(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        assert isinstance(adapter, BaseAdapter)

    def test_explicit_optional_import_degrades_without_claude_runtime(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        sys.modules.pop("adapters.claude_code", None)
        sys.modules.pop("adapters.claude_code.adapter", None)
        module = importlib.import_module("adapters.claude_code.adapter")
        monkeypatch.setattr(module.shutil, "which", lambda command: None)

        adapter = module.ClaudeCodeAdapter(project_dir=tmp_path)
        capabilities = adapter.tool_call("claude.capabilities", {})
        invoke = adapter.tool_call("claude.invoke", {"agent_id": "beta", "prompt": "hello"})

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
        assert set(adapter.registration["ai_provider_support"]["supported_api_formats"]) == {"openai", "anthropic", "openrouter"}
        assert adapter.registration["ai_provider_support"]["secret_redaction"]["required"] is True
        assert "not imported" in adapter.registration["limitations"][0]

    def test_capabilities_available_with_mock_runtime(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.capabilities", {})
        assert result["status"] == "ok"
        assert result["result"]["features"]["permission_checked_calls"] is True
        assert result["result"]["features"]["native_subagent_dispatch"] is False
        assert result["result"]["features"]["native_skill_load"] is False
        assert result["result"]["features"]["ai_provider_config_discovery"] is True
        assert result["result"]["features"]["ai_provider_secret_redaction"] is True
        assert result["result"]["features"]["custom_ai_provider_base_url"] is True
        assert set(result["result"]["ai_provider"]["supported_api_formats"]) == {"openai", "anthropic", "openrouter"}
        assert result["result"]["ai_provider"]["secret_redaction"]["plain_text_keys_in_manifest_or_docs"] is False
        assert result["result"]["optional"] is True
        assert result["result"]["status"] == "available"
        user_facing_names = [agent["name"] for agent in result["result"]["user_facing_agents"]]
        assert user_facing_names == ["SuperMedicine"]
        assert len(result["result"]["user_facing_agents"]) == 1
        assert FORBIDDEN_PLATFORM_AGENT_NAMES.isdisjoint(user_facing_names)
        assert result["result"]["internal_role_contexts"] == ["alpha", "beta", "gamma", "delta"]

    def test_capabilities_do_not_expose_environment_api_keys(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        openai_secret = "sk-test-claude-env-secret"
        anthropic_secret = "anthropic-test-claude-env-secret"
        monkeypatch.setenv("OPENAI_API_KEY", openai_secret)
        monkeypatch.setenv("ANTHROPIC_API_KEY", anthropic_secret)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: None)

        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.capabilities", {})

        serialized = str(result)
        assert openai_secret not in serialized
        assert anthropic_secret not in serialized
        assert "<redacted>" in serialized

    def test_runtime_unavailable_returns_structured_state(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: None)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.invoke", {"agent_id": "beta", "prompt": "hello"})
        assert result["status"] == "unavailable"
        assert result["runtime"]["available"] is False
        assert result["runtime"]["required_for_core"] is False
        assert result["runtime"]["ai_provider_configured"]["supported_api_formats"] == ["anthropic", "openai", "openrouter"]
        assert result["runtime"]["ai_provider_configured"]["secret_redaction_required"] is True
        assert result["runtime"]["ai_provider_configured"]["plaintext_api_keys_in_manifest_or_docs"] is False
        assert result["metadata"]["adapter"]["core_failure"] is False
        assert "error" in result

    def test_invoke_available_mock_path(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")

        def fake_run(command, cwd, capture_output, text, encoding, errors, timeout):
            return subprocess.CompletedProcess(command, 0, stdout="mock claude output", stderr="")

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fake_run)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.invoke", {"agent_id": "beta", "prompt": "hello"})
        assert result["status"] == "ok"
        assert result["result"] == "mock claude output"
        assert result["metadata"]["security"]["permission_checked"] is True

    def test_invoke_timeout_returns_structured_timeout(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")

        def fake_run(command, cwd, capture_output, text, encoding, errors, timeout):
            raise subprocess.TimeoutExpired(command, timeout)

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fake_run)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.invoke", {"agent_id": "beta", "prompt": "hello", "timeout": 1})

        assert result["status"] == "timeout"
        assert result["error_code"] == "timeout"
        assert result["retryable"] is True
        assert result["metadata"]["resource"]["timeout_seconds"] == 1

    def test_invoke_redacts_secret_like_prompt_and_runtime_error(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        api_key_label = "api" + "_" + "key"
        token_label = "tok" + "en"
        prompt_payload = "redaction" + "-" + "payload"
        runtime_payload = "runtime" + "-" + "payload"

        dry_run = adapter.tool_call(
            "claude.invoke",
            {"agent_id": "beta", "prompt": f"use {api_key_label}={prompt_payload}", "dry_run": True},
        )
        assert prompt_payload not in str(dry_run)
        assert "[REDACTED]" in str(dry_run)
        assert dry_run["metadata"]["security"]["permission_checked"] is True

        def fake_run(command, cwd, capture_output, text, encoding, errors, timeout):
            return subprocess.CompletedProcess(command, 1, stdout="", stderr=f"{token_label}={runtime_payload} failed")

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fake_run)
        error = adapter.tool_call("claude.invoke", {"agent_id": "beta", "prompt": "hello"})
        assert error["status"] == "runtime_error"
        assert runtime_payload not in str(error)
        assert "[REDACTED]" in str(error)

    def test_permission_denied_before_invoke(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.invoke", {"agent_id": "gamma", "prompt": "hello"})
        assert result["status"] == "denied"
        assert result["resource"] == "claude.invoke"

    def test_permission_denied_before_runtime_subprocess(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")

        def fail_if_invoked(*args, **kwargs):
            raise AssertionError("denied claude.invoke must not call subprocess")

        monkeypatch.setattr("adapters.claude_code.adapter.subprocess.run", fail_if_invoked)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)

        result = adapter.tool_call("claude.invoke", {"agent_id": "gamma", "prompt": "hello"})

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
        content = (Path(__file__).parent.parent / "adapters" / "claude_code" / "SKILL.md").read_text(encoding="utf-8")

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
