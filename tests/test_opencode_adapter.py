"""OpenCode 适配器集成测试"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from adapters.opencode.adapter import OpenCodeAdapter
from adapters.base_adapter import BaseAdapter


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

    def test_platform_name(self, adapter):
        """验证 platform_name 返回 'opencode'"""
        assert adapter.platform_name == "opencode"


class TestToolCall:
    """测试 tool_call 方法"""

    def test_tool_call_bash(self, adapter):
        """验证 tool_call 能处理 bash 工具调用"""
        result = adapter.tool_call("bash", {"command": "echo hello"})
        assert result["status"] == "ok"
        assert result["tool"] == "bash"
        assert "hello" in result["result"]

    def test_tool_call_read_write(self, adapter):
        """验证 read/write 工具调用在临时目录中正确工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            # Write
            write_result = adapter.tool_call("write", {
                "filePath": str(file_path),
                "content": "Hello, SuperMedicine!",
            })
            assert write_result["status"] == "ok"
            assert file_path.exists()

            # Read
            read_result = adapter.tool_call("read", {
                "filePath": str(file_path),
            })
            assert read_result["status"] == "ok"
            assert "Hello, SuperMedicine!" in read_result["result"]

    def test_tool_call_unsupported(self, adapter):
        """验证不支持的工具返回错误"""
        result = adapter.tool_call("nonexistent", {})
        assert result["status"] == "error"
        assert "Unsupported" in result["result"]

    def test_tool_call_glob(self, adapter):
        """验证 glob 工具调用"""
        result = adapter.tool_call("glob", {
            "pattern": "*.py",
            "path": str(Path(__file__).parent.parent / "cli.py").rsplit("\\", 1)[0] if "\\" in str(Path(__file__).parent.parent) else str(Path(__file__).parent.parent),
        })
        assert result["status"] == "ok"
        # Should find at least cli.py
        assert len(result["result"]) > 0

    def test_tool_call_grep(self, adapter):
        """验证 grep 工具调用"""
        adapter_dir = Path(__file__).parent.parent
        result = adapter.tool_call("grep", {
            "pattern": "class OpenCodeAdapter",
            "path": str(adapter_dir / "adapters" / "opencode"),
            "include": "*.py",
        })
        assert result["status"] == "ok"
        assert "OpenCodeAdapter" in result["result"]


class TestSkillLoad:
    """测试 skill_load 方法"""

    def test_skill_load_valid(self, adapter):
        """验证 skill_load 能加载存在的技能文件"""
        content = adapter.skill_load("rag-query")
        assert content is not None
        assert len(content) > 0
        # Should contain markdown content
        assert "rag" in content.lower() or "RAG" in content or "rag-query" in content.lower()

    def test_skill_load_invalid(self, adapter):
        """验证 skill_load 对不存在的技能返回合理错误信息"""
        content = adapter.skill_load("nonexistent-skill-xyz")
        assert "not found" in content.lower() or "error" in content.lower()


class TestSubagentDispatch:
    """测试 subagent_dispatch 方法"""

    def test_subagent_dispatch(self, adapter):
        """验证 subagent_dispatch 返回有效响应"""
        result = adapter.subagent_dispatch("alpha", {"action": "test", "data": "sample"})
        assert result["agent_id"] == "alpha"
        assert result["status"] == "dispatched"
        assert "task" in result
        assert result["task"]["action"] == "test"


class TestPluginJson:
    """测试 plugin.json 完整性"""

    def test_plugin_json_valid(self):
        """验证 plugin.json 可被 json 解析且包含所有必填字段"""
        plugin_path = Path(__file__).parent.parent / "adapters" / "opencode" / "plugin.json"
        assert plugin_path.exists(), "plugin.json not found"

        with open(plugin_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["name", "version", "description", "type", "entry", "permissions"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check permissions
        assert "tools" in data["permissions"]
        assert len(data["permissions"]["tools"]) >= 8

        # Check skills
        assert "skills" in data
        assert len(data["skills"]) == 6

        # Check agents
        assert "agents" in data
        assert len(data["agents"]) == 4


class TestSkillsExist:
    """测试所有 SKILL.md 文件存在"""

    def test_all_skills_exist(self):
        """验证 6 个 SKILL.md 文件存在"""
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


class TestAgentsExist:
    """测试所有 Agent 定义文件存在"""

    def test_all_agents_exist(self):
        """验证 4 个 Agent 定义文件存在"""
        agents_dir = Path(__file__).parent.parent / "adapters" / "opencode" / "agents"
        expected_agents = [
            "alpha-analyst.md",
            "beta-reviewer.md",
            "gamma-writer.md",
            "delta-orchestrator.md",
        ]
        for agent_file in expected_agents:
            agent_path = agents_dir / agent_file
            assert agent_path.exists(), f"Missing agent file: {agent_file}"
            content = agent_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"Empty agent file: {agent_file}"
