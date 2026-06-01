from __future__ import annotations

import yaml
from pathlib import Path
from permission.engine import PermissionEngine
from permission.policy import PermissionResult


PROJECT_ROOT = Path(__file__).parent.parent

class TestPermissionEngine:
    def _make_engine(self, tmp_path, policy_data):
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(yaml.dump(policy_data), encoding="utf-8")
        return PermissionEngine(policy_dir=tmp_path, audit_log=tmp_path / "audit.log")
    def test_check_allowed(self, tmp_path):
        engine = self._make_engine(tmp_path, {"agent_id": "a", "role": "r", "permissions": {"allowed": [{"action": "read", "scope": "*"}], "denied": []}})
        assert engine.check("a", "read", "file") == PermissionResult.ALLOWED
    def test_check_denied(self, tmp_path):
        engine = self._make_engine(tmp_path, {"agent_id": "a", "role": "r", "permissions": {"allowed": [], "denied": [{"action": "delete", "scope": "*"}]}})
        assert engine.check("a", "delete", "file") == PermissionResult.DENIED
    def test_check_unknown_agent(self, tmp_path):
        engine = self._make_engine(tmp_path, [])
        assert engine.check("unknown", "read", "file") == PermissionResult.DENIED
    def test_audit_log_written(self, tmp_path):
        engine = self._make_engine(tmp_path, {"agent_id": "a", "role": "r", "permissions": {"allowed": [{"action": "read", "scope": "*"}], "denied": []}})
        engine.check("a", "read", "file")
        assert (tmp_path / "audit.log").exists()
        assert "a" in (tmp_path / "audit.log").read_text(encoding="utf-8")


class TestPermissionEngineWithPolicies:
    """测试 PermissionEngine 加载策略文件"""

    def test_load_default_policy(self, tmp_path):
        """验证加载 Default.YAML 策略文件"""
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
        # 已知 Agent 应通过
        result = engine.check("test_agent", "read", "file.txt")
        assert result == PermissionResult.ALLOWED
        # 被拒绝的操作
        result = engine.check("test_agent", "write", "file.txt")
        assert result == PermissionResult.DENIED
        # 未知 Agent 应拒绝
        result = engine.check("unknown", "read", "file.txt")
        assert result == PermissionResult.DENIED

    def test_default_policies_exist(self):
        """验证项目默认策略文件存在"""
        policy_dir = Path(__file__).parent.parent / ".supermedicine" / "policies"
        assert policy_dir.exists()
        assert (policy_dir / "default.yaml").exists()

    def test_hard_limits_enforced(self, tmp_path):
        """验证 hard_limits 被强制执行"""
        import yaml
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()
        audit_log = tmp_path / "audit.jsonl"

        policy = {
            "agent_id": "limited_agent",
            "role": "tester",
            "security_level": "standard",
            "permissions": {
                "allowed": [{"action": "read", "scope": "*"}],
                "denied": [],
                "hard_limits": {"max_file_size": 100, "max_memory": 50},
            },
        }
        (policy_dir / "test.yaml").write_text(yaml.dump(policy), encoding="utf-8")

        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)

        # 在限制范围内 — 应允许
        result = engine.check("limited_agent", "read", "file.txt",
                             context={"max_file_size": 50, "max_memory": 30})
        assert result == PermissionResult.ALLOWED

        # 超出限制 — 应拒绝
        result = engine.check("limited_agent", "read", "file.txt",
                             context={"max_file_size": 200, "max_memory": 30})
        assert result == PermissionResult.DENIED

    def test_hard_limits_no_context(self, tmp_path):
        """无 Context 时 Hard_Limits 不影响"""
        import yaml
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()
        audit_log = tmp_path / "audit.jsonl"

        policy = {
            "agent_id": "limited_agent",
            "role": "tester",
            "security_level": "standard",
            "permissions": {
                "allowed": [{"action": "read", "scope": "*"}],
                "denied": [],
                "hard_limits": {"max_file_size": 100},
            },
        }
        (policy_dir / "test.yaml").write_text(yaml.dump(policy), encoding="utf-8")

        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)
        result = engine.check("limited_agent", "read", "file.txt")
        assert result == PermissionResult.ALLOWED

    def test_external_api_hard_limit_denies_before_allow_rule(self, tmp_path):
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()
        audit_log = tmp_path / "audit.jsonl"
        policy = {
            "agent_id": "no_external",
            "role": "tester",
            "permissions": {
                "allowed": [{"action": "rag.external.query", "scope": "https://eutils.ncbi.nlm.nih.gov/*"}],
                "denied": [],
                "hard_limits": {"network_access": False, "external_api": False},
            },
        }
        (policy_dir / "test.yaml").write_text(yaml.dump(policy), encoding="utf-8")
        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)

        result = engine.check(
            "no_external",
            "rag.external.query",
            "https://eutils.ncbi.nlm.nih.gov/*",
            context={"requires_network": True, "requires_external_api": True},
        )

        assert result == PermissionResult.DENIED

    def test_default_policy_allows_declared_experiment_wb_local_actions(self, tmp_path):
        audit_log = tmp_path / "audit.jsonl"
        policy_dir = PROJECT_ROOT / "permission"
        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)

        declared_actions = (
            "experiment.wb.normalize_loading",
            "experiment.wb.antibody_dilution",
        )

        for action in declared_actions:
            result = engine.check(
                "alpha",
                "execute",
                action,
                context={
                    "plugin": "experiment-wb",
                    "action": action,
                    "requires_network": False,
                    "requires_external_api": False,
                },
            )
            assert result == PermissionResult.ALLOWED

    def test_experiment_wb_policy_does_not_default_allow_unknown_or_external_actions(self, tmp_path):
        policy = {
            "agent_id": "experiment_local",
            "role": "experiment_tool",
            "permissions": {
                "allowed": [
                    {"action": "execute", "scope": "experiment.wb.normalize_loading"},
                    {"action": "execute", "scope": "experiment.wb.antibody_dilution"},
                ],
                "denied": [],
                "hard_limits": {"network_access": False, "external_api": False},
            },
        }
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()
        audit_log = tmp_path / "audit.jsonl"
        (policy_dir / "test.yaml").write_text(yaml.dump(policy), encoding="utf-8")
        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)

        unknown_result = engine.check(
            "experiment_local",
            "execute",
            "experiment.wb.unknown_action",
            context={"plugin": "experiment-wb", "action": "experiment.wb.unknown_action"},
        )
        network_result = engine.check(
            "experiment_local",
            "execute",
            "experiment.wb.normalize_loading",
            context={
                "plugin": "experiment-wb",
                "action": "experiment.wb.normalize_loading",
                "requires_network": True,
            },
        )
        external_result = engine.check(
            "experiment_local",
            "execute",
            "experiment.wb.antibody_dilution",
            context={
                "plugin": "experiment-wb",
                "action": "experiment.wb.antibody_dilution",
                "requires_external_api": True,
            },
        )

        assert unknown_result == PermissionResult.DENIED
        assert network_result == PermissionResult.DENIED
        assert external_result == PermissionResult.DENIED

    def test_experiment_wb_denial_is_audited_with_redacted_context(self, tmp_path):
        policy = {
            "agent_id": "experiment_local",
            "role": "experiment_tool",
            "permissions": {
                "allowed": [{"action": "execute", "scope": "experiment.wb.normalize_loading"}],
                "denied": [],
                "hard_limits": {"network_access": False, "external_api": False},
            },
        }
        policy_dir = tmp_path / "policies"
        policy_dir.mkdir()
        audit_log = tmp_path / "audit.jsonl"
        (policy_dir / "test.yaml").write_text(yaml.dump(policy), encoding="utf-8")
        engine = PermissionEngine(policy_dir=policy_dir, audit_log=audit_log)

        result = engine.check(
            "experiment_local",
            "execute",
            "experiment.wb.normalize_loading",
            context={
                "plugin": "experiment-wb",
                "action": "experiment.wb.normalize_loading",
                "requires_external_api": True,
                "api_key": "sk-permission-secret",
            },
        )

        audit_text = audit_log.read_text(encoding="utf-8")
        assert result == PermissionResult.DENIED
        assert "experiment_local" in audit_text
        assert "experiment.wb.normalize_loading" in audit_text
        assert "DENIED" in audit_text
        assert "hard_limit_exceeded:external_api:false" in audit_text
        assert "api_key" not in audit_text
        assert "sk-permission-secret" not in audit_text
