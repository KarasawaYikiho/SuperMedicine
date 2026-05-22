"""Standalone 适配器测试"""
from __future__ import annotations

import tempfile
from pathlib import Path

from adapters.standalone.adapter import StandaloneAdapter
from adapters.base_adapter import BaseAdapter


class TestStandaloneAdapter:
    """测试 Standalone 适配器"""

    def test_is_base_adapter(self):
        adapter = StandaloneAdapter()
        assert isinstance(adapter, BaseAdapter)

    def test_platform_name(self):
        adapter = StandaloneAdapter()
        assert adapter.platform_name == "standalone"

    def test_tool_call_bash(self):
        adapter = StandaloneAdapter()
        result = adapter.tool_call("bash", {"command": "echo hello"})
        assert result["status"] == "ok"
        assert "hello" in result["result"]

    def test_tool_call_read_write(self):
        adapter = StandaloneAdapter()
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "test.txt"
            w = adapter.tool_call("write", {"filePath": str(fp), "content": "test content"})
            assert w["status"] == "ok"
            r = adapter.tool_call("read", {"filePath": str(fp)})
            assert "test content" in r["result"]

    def test_tool_call_glob(self):
        adapter = StandaloneAdapter()
        result = adapter.tool_call("glob", {"pattern": "*.py", "path": "."})
        assert result["status"] == "ok"
        assert len(result["result"]) > 0

    def test_tool_call_unsupported(self):
        adapter = StandaloneAdapter()
        result = adapter.tool_call("nonexistent", {})
        assert result["status"] == "error"

    def test_skill_load(self):
        adapter = StandaloneAdapter()
        result = adapter.skill_load("rag-query")
        assert "rag" in result.lower() or "RAG" in result or "not found" in result.lower()

    def test_subagent_dispatch(self):
        adapter = StandaloneAdapter()
        result = adapter.subagent_dispatch("test-agent", {"action": "test"})
        assert result["agent_id"] == "test-agent"
        assert result["status"] == "dispatched"
        assert result["platform"] == "standalone"
