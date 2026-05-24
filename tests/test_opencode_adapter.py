"""OpenCode 适配器集成测试"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from adapters.opencode.adapter import OpenCodeAdapter
from adapters.base_adapter import BaseAdapter
from agents.orchestrator import Orchestrator
from agents.base_agent import BaseAgent
from permission.engine import PermissionEngine


@pytest.fixture
def adapter():
    """创建 OpenCodeAdapter 实例"""
    return OpenCodeAdapter()


def _adapter_with_policy(tmp_path: Path, *, allowed: list[dict[str, str]], denied: list[dict[str, str]] | None = None, agent_id: str = "alpha") -> OpenCodeAdapter:
    policy_dir = tmp_path / ".supermedicine" / "policies"
    policy_dir.mkdir(parents=True)
    (policy_dir / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(yaml.dump({
        "agent_id": agent_id,
        "role": "adapter-test",
        "permissions": {"allowed": allowed, "denied": denied or []},
    }), encoding="utf-8")
    engine = PermissionEngine(policy_dir, policy_dir / "audit.jsonl")
    return OpenCodeAdapter(permission_engine=engine, project_dir=tmp_path, default_agent_id=agent_id)


@pytest.fixture
def permissive_adapter(tmp_path: Path) -> OpenCodeAdapter:
    return _adapter_with_policy(tmp_path, allowed=[{"action": "tool_call", "scope": "*"}])


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
        """验证 Tool_Call 能处理 Bash 工具调用"""
        result = adapter.tool_call("bash", {"command": "echo hello"})
        assert result["status"] == "ok"
        assert result["tool"] == "bash"
        assert "hello" in result["result"]

    def test_tool_call_read_write(self, adapter):
        """验证 Read/Write 工具调用在临时目录中正确工作"""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = OpenCodeAdapter(project_dir=Path(tmpdir))
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

    def test_high_risk_tool_denied_before_write_mutation(self, tmp_path):
        adapter = _adapter_with_policy(tmp_path, allowed=[], denied=[{"action": "tool_call", "scope": "*"}])
        file_path = tmp_path / "blocked.txt"

        result = adapter.tool_call("write", {"filePath": str(file_path), "content": "blocked"})

        assert result["status"] == "denied"
        assert result["error_code"] == "permission_denied"
        assert not file_path.exists()

    def test_high_risk_tool_allowed_with_explicit_policy(self, tmp_path):
        target = tmp_path / "allowed.txt"
        adapter = _adapter_with_policy(tmp_path, allowed=[{"action": "tool_call", "scope": str(target)}])

        result = adapter.tool_call("write", {"filePath": str(target), "content": "allowed"})

        assert result["status"] == "ok"
        assert target.read_text(encoding="utf-8") == "allowed"

    def test_tool_call_glob(self, adapter):
        """验证 Glob 工具调用"""
        result = adapter.tool_call("glob", {
            "pattern": "*.py",
            "path": str(Path(__file__).parent.parent / "Cli.py").rsplit("\\", 1)[0] if "\\" in str(Path(__file__).parent.parent) else str(Path(__file__).parent.parent),
        })
        assert result["status"] == "ok"
        # Should Find at Least CLI.Py
        assert len(result["result"]) > 0

    def test_tool_call_grep(self, adapter):
        """验证 Grep 工具调用"""
        adapter_dir = Path(__file__).parent.parent
        result = adapter.tool_call("grep", {
            "pattern": "class OpenCodeAdapter",
            "path": str(adapter_dir / "adapters" / "opencode"),
            "include": "*.py",
        })
        assert result["status"] == "ok"
        assert "OpenCodeAdapter" in result["result"]

    def test_filesystem_tools_deny_paths_outside_project_root(self, permissive_adapter, tmp_path):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside"
        outside_file = outside_dir / "blocked.txt"
        assert not outside_file.exists()

        write_result = permissive_adapter.tool_call("write", {"filePath": str(outside_file), "content": "blocked"})
        read_result = permissive_adapter.tool_call("read", {"filePath": str(outside_file)})
        glob_result = permissive_adapter.tool_call("glob", {"path": str(outside_dir), "pattern": "*"})
        grep_result = permissive_adapter.tool_call("grep", {"path": str(outside_dir), "pattern": "blocked"})

        assert write_result["status"] == "denied"
        assert write_result["error_code"] == "sandbox_denied"
        assert not outside_file.exists()
        assert read_result["status"] == "denied"
        assert glob_result["status"] == "denied"
        assert grep_result["status"] == "denied"

    def test_edit_does_not_mutate_outside_project_root(self, permissive_adapter, tmp_path):
        outside_dir = tmp_path.parent / f"{tmp_path.name}-outside-edit"
        outside_dir.mkdir(exist_ok=True)
        outside_file = outside_dir / "blocked.txt"
        outside_file.write_text("old", encoding="utf-8")

        result = permissive_adapter.tool_call("edit", {"filePath": str(outside_file), "oldString": "old", "newString": "new"})

        assert result["status"] == "denied"
        assert result["error_code"] == "sandbox_denied"
        assert outside_file.read_text(encoding="utf-8") == "old"

    def test_bash_permission_denied_before_execution(self, tmp_path):
        marker = tmp_path / "should_not_exist.txt"
        adapter = _adapter_with_policy(tmp_path, allowed=[], denied=[{"action": "tool_call", "scope": "bash"}])

        result = adapter.tool_call("bash", {"command": f"python -c \"from pathlib import Path; Path(r'{marker}').write_text('ran')\"", "workdir": str(tmp_path)})

        assert result["status"] == "denied"
        assert result["resource"] == "bash"
        assert not marker.exists()


class TestSkillLoad:
    """测试 skill_load 方法"""

    def test_skill_load_valid(self, adapter):
        """验证 skill_load 能加载存在的技能文件"""
        content = adapter.skill_load("rag-query")
        assert content is not None
        assert len(content) > 0
        # Should Contain Markdown Content
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
    """测试 Plugin.JSON 完整性"""

    def test_plugin_json_valid(self):
        """验证 Plugin.JSON 可被 JSON 解析且包含所有必填字段"""
        plugin_path = Path(__file__).parent.parent / "adapters" / "opencode" / "plugin.json"
        assert plugin_path.exists(), "plugin.json not found"

        with open(plugin_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["name", "version", "description", "type", "entry", "permissions"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Check Permissions
        assert "tools" in data["permissions"]
        assert len(data["permissions"]["tools"]) >= 8

        # Check Skills
        assert "skills" in data
        assert len(data["skills"]) == 6

        # Check Agents
        assert "agents" in data
        assert len(data["agents"]) == 4


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
        assert "volume=\"331\"" in citation_doc
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
        for skill_file in ["rag-query.md", "medical-citation.md", "medical-writing.md", "python-stats.md", "r-survival.md", "harness-monitor.md"]:
            content = (skills_dir / skill_file).read_text(encoding="utf-8").lower()
            assert "human" in content or "expert review" in content
            if "clinical-grade" in content:
                assert "not production-grade" in content


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


class DummyEchoAgent(BaseAgent):
    def __init__(self, agent_id, role="test"):
        super().__init__(agent_id, role)

    def execute(self, task):
        return {"agent": self.agent_id, "echo": task, "status": "ok"}


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
