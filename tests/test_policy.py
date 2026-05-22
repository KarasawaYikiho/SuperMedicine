import pytest
from permission.policy import PermissionPolicy, PermissionResult

class TestPermissionPolicy:
    def test_load_policy_from_dict(self):
        policy_data = {"agent_id": "test-agent", "role": "retrieval", "security_level": "restricted", "permissions": {"allowed": [{"action": "rag.query", "scope": "projects/*"}], "denied": [{"action": "tool.execute", "scope": "*"}], "hard_limits": {"max_file_size": "10MB", "max_execution_time": "300s", "network_access": False}}}
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.agent_id == "test-agent"
        assert policy.role == "retrieval"
    def test_check_allowed_action(self):
        policy_data = {"agent_id": "test-agent", "role": "retrieval", "permissions": {"allowed": [{"action": "rag.query", "scope": "projects/*"}], "denied": []}}
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("rag.query", "projects/current") == PermissionResult.ALLOWED
    def test_check_denied_action(self):
        policy_data = {"agent_id": "test-agent", "role": "retrieval", "permissions": {"allowed": [{"action": "rag.query", "scope": "projects/*"}], "denied": [{"action": "tool.execute", "scope": "*"}]}}
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("tool.execute", "python/stats") == PermissionResult.DENIED
    def test_check_undeclared_action_denied(self):
        policy_data = {"agent_id": "test-agent", "role": "retrieval", "permissions": {"allowed": [{"action": "rag.query", "scope": "projects/*"}], "denied": []}}
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("config.modify", "system") == PermissionResult.DENIED
    def test_denied_overrides_allowed(self):
        policy_data = {"agent_id": "test-agent", "role": "test", "permissions": {"allowed": [{"action": "tool.execute", "scope": "python/*"}], "denied": [{"action": "tool.execute", "scope": "*"}]}}
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("tool.execute", "python/stats") == PermissionResult.DENIED
