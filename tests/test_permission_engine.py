import yaml
from pathlib import Path
from permission.engine import PermissionEngine
from permission.policy import PermissionResult

class TestPermissionEngine:
    def _make_engine(self, tmp_path, policy_data):
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml.dump(policy_data))
        return PermissionEngine(policy_dir=tmp_path, audit_log=tmp_path / "audit.log")
    def test_check_allowed(self, tmp_path):
        engine = self._make_engine(tmp_path, {"agent_id": "a", "role": "r", "permissions": {"allowed": [{"action": "read", "scope": "*"}], "denied": []}})
        assert engine.check("a", "read", "file") == PermissionResult.ALLOWED
    def test_check_denied(self, tmp_path):
        engine = self._make_engine(tmp_path, {"agent_id": "a", "role": "r", "permissions": {"allowed": [], "denied": [{"action": "delete", "scope": "*"}]}})
        assert engine.check("a", "delete", "file") == PermissionResult.DENIED
    def test_check_unknown_agent(self, tmp_path):
        engine = self._make_engine(tmp_path, {})
        assert engine.check("unknown", "read", "file") == PermissionResult.DENIED
    def test_audit_log_written(self, tmp_path):
        engine = self._make_engine(tmp_path, {"agent_id": "a", "role": "r", "permissions": {"allowed": [{"action": "read", "scope": "*"}], "denied": []}})
        engine.check("a", "read", "file")
        assert (tmp_path / "audit.log").exists()
        assert "a" in (tmp_path / "audit.log").read_text()


class TestPermissionEngineWithPolicies:
    """测试 PermissionEngine 加载策略文件"""

    def test_load_default_policy(self, tmp_path):
        """验证加载 default.yaml 策略文件"""
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()
        audit_log = tmp_path / "audit.jsonl"

        # 写入测试策略
        import yaml
        policy = {
            "agent_id": "test_agent",
            "role": "tester",
            "security_level": "standard",
            "permissions": {
                "allowed": [{"action": "read", "scope": "*"}],
                "denied": [{"action": "write", "scope": "*"}],
                "hard_limits": {"max_files_per_session": 10, "max_tool_calls_per_minute": 5},
            },
        }
        (policy_dir / "test.yaml").write_text(yaml.dump(policy), encoding="utf-8")

        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)
        # 已知 agent 应通过
        result = engine.check("test_agent", "read", "file.txt")
        assert result == PermissionResult.ALLOWED
        # 被拒绝的操作
        result = engine.check("test_agent", "write", "file.txt")
        assert result == PermissionResult.DENIED
        # 未知 agent 应拒绝
        result = engine.check("unknown", "read", "file.txt")
        assert result == PermissionResult.DENIED

    def test_default_policies_exist(self):
        """验证项目默认策略文件存在"""
        policy_dir = Path(__file__).parent.parent / ".supermedicine" / "policies"
        assert policy_dir.exists()
        assert (policy_dir / "default.yaml").exists()
