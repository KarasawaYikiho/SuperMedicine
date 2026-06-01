"""Standalone 适配器测试"""
from __future__ import annotations

import builtins
import importlib
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from adapters.standalone.adapter import StandaloneAdapter
from adapters.base_adapter import BaseAdapter
from permission.engine import PermissionEngine


def _adapter_with_policy(tmp_path: Path, *, allowed: list[dict[str, str]], denied: list[dict[str, str]] | None = None, agent_id: str = "alpha") -> StandaloneAdapter:
    policy_dir = tmp_path / ".supermedicine" / "policies"
    policy_dir.mkdir(parents=True)
    (policy_dir / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(yaml.dump({
        "agent_id": agent_id,
        "role": "standalone-test",
        "permissions": {"allowed": allowed, "denied": denied or []},
    }), encoding="utf-8")
    engine = PermissionEngine(policy_dir, policy_dir / "audit.jsonl")
    return StandaloneAdapter(permission_engine=engine, project_dir=tmp_path, default_agent_id=agent_id)


@pytest.fixture
def permissive_adapter(tmp_path: Path) -> StandaloneAdapter:
    return _adapter_with_policy(tmp_path, allowed=[{"action": "tool_call", "scope": "*"}])


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
            adapter = _adapter_with_policy(Path(td), allowed=[{"action": "tool_call", "scope": "*"}])
            fp = Path(td) / "test.txt"
            w = adapter.tool_call("write", {"filePath": str(fp), "content": "test content"})
            assert w["status"] == "ok"
            r = adapter.tool_call("read", {"filePath": str(fp)})
            assert "test content" in r["result"]

    def test_write_and_edit_fail_closed_when_permission_engine_unavailable(self, tmp_path):
        adapter = StandaloneAdapter(permission_engine=None, project_dir=tmp_path)
        target = tmp_path / "blocked.txt"
        target.write_text("old", encoding="utf-8")
        policy_dir = tmp_path / ".supermedicine" / "policies"
        policy_dir.mkdir(parents=True)
        (policy_dir / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text("invalid: [\n", encoding="utf-8")

        write_result = adapter.tool_call("write", {"filePath": str(target), "content": "new"})
        edit_result = adapter.tool_call("edit", {"filePath": str(target), "oldString": "old", "newString": "new"})

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
        adapter = _adapter_with_policy(tmp_path, allowed=[], denied=[{"action": "tool_call", "scope": "*"}])

        result = adapter.tool_call("edit", {"filePath": str(target), "oldString": "old", "newString": "new"})

        assert result["status"] == "denied"
        assert target.read_text(encoding="utf-8") == "old"

    def test_allowed_read_with_explicit_policy(self, tmp_path):
        target = tmp_path / "allowed.txt"
        target.write_text("readable", encoding="utf-8")
        adapter = _adapter_with_policy(tmp_path, allowed=[{"action": "tool_call", "scope": str(target)}])

        result = adapter.tool_call("read", {"filePath": str(target)})

        assert result["status"] == "ok"
        assert "readable" in result["result"]

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

    def test_bash_accepts_argv_without_shell_expansion(self, tmp_path):
        marker = tmp_path / "should_not_exist.txt"
        adapter = _adapter_with_policy(tmp_path, allowed=[{"action": "tool_call", "scope": "bash"}])

        result = adapter.tool_call("bash", {"command": ["python", "-c", "print('safe')"], "workdir": str(tmp_path)})

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
        assert not any("adapters" in path and "opencode" in path and "skills" in path for path in opened_paths)

    def test_subagent_dispatch(self):
        adapter = StandaloneAdapter()
        result = adapter.subagent_dispatch("test-agent", {"action": "test"})
        assert result["agent_id"] == "test-agent"
        assert result["status"] == "dispatched"
        assert result["platform"] == "standalone"
