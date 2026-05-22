import yaml
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
