"""Claude Code 适配器测试 — Coming Soon 状态验证"""
from __future__ import annotations

from adapters.claude_code.adapter import ClaudeCodeAdapter
from adapters.base_adapter import BaseAdapter


class TestClaudeCodeAdapter:
    """测试 Claude Code 适配器 Coming Soon 行为"""

    def test_is_base_adapter(self):
        """验证是 BaseAdapter 子类"""
        adapter = ClaudeCodeAdapter()
        assert isinstance(adapter, BaseAdapter)

    def test_platform_name(self):
        """验证平台名"""
        adapter = ClaudeCodeAdapter()
        assert adapter.platform_name == "claude-code"

    def test_tool_call_returns_coming_soon(self):
        """验证 tool_call 返回 coming_soon 状态"""
        adapter = ClaudeCodeAdapter()
        result = adapter.tool_call("bash", {"command": "test"})
        assert result["status"] == "coming_soon"
        assert "not yet implemented" in result["message"].lower()

    def test_skill_load_returns_coming_soon(self):
        """验证 skill_load 返回 Coming Soon 标识"""
        adapter = ClaudeCodeAdapter()
        result = adapter.skill_load("test-skill")
        assert "Coming Soon" in result

    def test_subagent_dispatch_returns_coming_soon(self):
        """验证 subagent_dispatch 返回 coming_soon"""
        adapter = ClaudeCodeAdapter()
        result = adapter.subagent_dispatch("alpha", {"action": "test"})
        assert result["status"] == "coming_soon"

    def test_no_exceptions(self):
        """验证所有方法不抛出异常"""
        adapter = ClaudeCodeAdapter()
        adapter.tool_call("bash", {})
        adapter.skill_load("any")
        adapter.subagent_dispatch("any", {})
