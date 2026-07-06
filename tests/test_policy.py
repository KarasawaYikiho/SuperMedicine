from __future__ import annotations

import pytest

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


def test_load_policy_from_dict_preserves_identity_and_role():
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


@pytest.mark.parametrize(
    ("policy_data", "action", "resource", "expected"),
    [
        (
            {
                "agent_id": "test-agent",
                "role": "retrieval",
                "permissions": {
                    "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                    "denied": [],
                },
            },
            "rag.query",
            "projects/current",
            PermissionResult.ALLOWED,
        ),
        (
            {
                "agent_id": "test-agent",
                "role": "retrieval",
                "permissions": {
                    "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                    "denied": [{"action": "tool.execute", "scope": "*"}],
                },
            },
            "tool.execute",
            "python/stats",
            PermissionResult.DENIED,
        ),
        (
            {
                "agent_id": "test-agent",
                "role": "retrieval",
                "permissions": {
                    "allowed": [{"action": "rag.query", "scope": "projects/*"}],
                    "denied": [],
                },
            },
            "config.modify",
            "system",
            PermissionResult.DENIED,
        ),
        (
            {
                "agent_id": "test-agent",
                "role": "test",
                "permissions": {
                    "allowed": [{"action": "tool.execute", "scope": "python/*"}],
                    "denied": [{"action": "tool.execute", "scope": "*"}],
                },
            },
            "tool.execute",
            "python/stats",
            PermissionResult.DENIED,
        ),
    ],
)
def test_permission_policy_check_decisions(policy_data, action, resource, expected):
    policy = PermissionPolicy.from_dict(policy_data)

    assert policy.check(action, resource) == expected
