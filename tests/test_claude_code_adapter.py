"""Claude Code 适配器测试 — 最小真实行为与权限边界。"""
from __future__ import annotations

import subprocess
from pathlib import Path

from adapters.base_adapter import BaseAdapter
from adapters.claude_code import ClaudeCodeAdapter


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

    def test_platform_name_and_registration(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        assert adapter.platform_name == "claude-code"
        assert adapter.registration["platform"] == "claude-code"
        assert adapter.registration["adapter_class"] == "ClaudeCodeAdapter"

    def test_capabilities_available_with_mock_runtime(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: "/usr/bin/claude")
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.capabilities", {})
        assert result["status"] == "ok"
        assert result["result"]["features"]["permission_checked_calls"] is True
        assert result["result"]["features"]["native_subagent_dispatch"] is False
        assert result["result"]["status"] == "available"

    def test_runtime_unavailable_returns_structured_state(self, tmp_path, monkeypatch):
        _write_policy(tmp_path)
        monkeypatch.setattr("adapters.claude_code.adapter.shutil.which", lambda command: None)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("claude.invoke", {"agent_id": "beta", "prompt": "hello"})
        assert result["status"] == "unavailable"
        assert result["runtime"]["available"] is False
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

    def test_unsupported_tool_returns_structured_error(self, tmp_path):
        _write_policy(tmp_path)
        adapter = ClaudeCodeAdapter(project_dir=tmp_path)
        result = adapter.tool_call("unknown", {})
        assert result["status"] == "error"
        assert "supported_tools" in result

    def test_skill_doc_stable_api_examples_and_boundary(self):
        content = (Path(__file__).parent.parent / "adapters" / "claude_code" / "SKILL.md").read_text(encoding="utf-8")

        assert "from plugins.rag.main import execute" in content
        assert "RAGProvider()" not in content
        assert "JournalArticle" in content
        assert "human expert review" in content
        assert "does not provide clinical advice" in content
