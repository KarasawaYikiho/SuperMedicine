from __future__ import annotations

from permission.policy import PermissionPolicy, PermissionResult


def test_path_scope_matches_resolved_same_file_representation(tmp_path):
    target = tmp_path / "nested" / ".." / "nested" / "allowed.txt"
    resolved_target = target.resolve(strict=False)
    policy_data = {
        "agent_id": "test-agent",
        "role": "test",
        "permissions": {
            "allowed": [{"action": "tool_call", "scope": str(target)}],
            "denied": [],
        },
    }
    policy = PermissionPolicy.from_dict(policy_data)

    assert policy.check("tool_call", str(resolved_target)) == PermissionResult.ALLOWED


def test_resolved_path_scope_matches_raw_same_file_representation(tmp_path):
    target = tmp_path / "nested" / ".." / "nested" / "allowed.txt"
    resolved_target = target.resolve(strict=False)
    policy_data = {
        "agent_id": "test-agent",
        "role": "test",
        "permissions": {
            "allowed": [{"action": "tool_call", "scope": str(resolved_target)}],
            "denied": [],
        },
    }
    policy = PermissionPolicy.from_dict(policy_data)

    assert policy.check("tool_call", str(target)) == PermissionResult.ALLOWED


def test_path_scope_does_not_match_different_normalized_file(tmp_path):
    target = tmp_path / "nested" / "allowed.txt"
    different = tmp_path / "nested" / "allowed.txt.bak"
    policy_data = {
        "agent_id": "test-agent",
        "role": "test",
        "permissions": {
            "allowed": [{"action": "tool_call", "scope": str(target)}],
            "denied": [],
        },
    }
    policy = PermissionPolicy.from_dict(policy_data)

    assert policy.check("tool_call", str(different)) == PermissionResult.DENIED


class TestPermissionPolicy:
    def test_load_policy_from_dict(self):
        policy_data = {
            "agent_id": "test-agent",
            "role": "retrieval",
            "security_level": "restricted",
            "permissions": {
                "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                "denied": [{"action": "tool.execute", "scope": "*"}],
                "hard_limits": {
                    "max_file_size": "10MB",
                    "max_execution_time": "300s",
                    "network_access": False,
                },
            },
        }
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.agent_id == "test-agent"
        assert policy.role == "retrieval"

    def test_check_allowed_action(self):
        policy_data = {
            "agent_id": "test-agent",
            "role": "retrieval",
            "permissions": {
                "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                "denied": [],
            },
        }
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("rag.query", "projects/current") == PermissionResult.ALLOWED

    def test_check_denied_action(self):
        policy_data = {
            "agent_id": "test-agent",
            "role": "retrieval",
            "permissions": {
                "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                "denied": [{"action": "tool.execute", "scope": "*"}],
            },
        }
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("tool.execute", "python/stats") == PermissionResult.DENIED

    def test_check_undeclared_action_denied(self):
        policy_data = {
            "agent_id": "test-agent",
            "role": "retrieval",
            "permissions": {
                "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                "denied": [],
            },
        }
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("config.modify", "system") == PermissionResult.DENIED

    def test_denied_overrides_allowed(self):
        policy_data = {
            "agent_id": "test-agent",
            "role": "test",
            "permissions": {
                "allowed": [{"action": "tool.execute", "scope": "python/*"}],
                "denied": [{"action": "tool.execute", "scope": "*"}],
            },
        }
        policy = PermissionPolicy.from_dict(policy_data)
        assert policy.check("tool.execute", "python/stats") == PermissionResult.DENIED
