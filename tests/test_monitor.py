"""Harness 监控器测试"""
from __future__ import annotations

import json
from pathlib import Path


from plugins.harness.monitor import AgentMonitor


class TestAgentMonitor:
    """测试 AgentMonitor 类"""

    def test_init(self):
        """验证实例化成功"""
        monitor = AgentMonitor(audit_log_path=Path("test_audit.jsonl"))
        assert monitor is not None
        assert isinstance(monitor, AgentMonitor)

    def test_get_permission_audit_empty(self, tmp_path):
        """审计日志文件不存在时返回空列表"""
        audit_path = tmp_path / "nonexistent.jsonl"
        monitor = AgentMonitor(audit_log_path=audit_path)
        result = monitor.get_permission_audit()
        assert result == []

    def test_get_permission_audit_with_entries(self, tmp_path):
        """按 agent_id 过滤正确"""
        audit_path = tmp_path / "audit.jsonl"
        entries = [
            {"agent_id": "alpha", "action": "read", "result": "ALLOWED", "timestamp": "2024-01-01T00:00:00Z"},
            {"agent_id": "alpha", "action": "write", "result": "DENIED", "timestamp": "2024-01-01T00:01:00Z"},
            {"agent_id": "beta", "action": "read", "result": "ALLOWED", "timestamp": "2024-01-01T00:02:00Z"},
        ]
        audit_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

        monitor = AgentMonitor(audit_log_path=audit_path)

        # 全部获取
        all_entries = monitor.get_permission_audit()
        assert len(all_entries) == 3

        # 按 agent_id 过滤
        alpha_entries = monitor.get_permission_audit(agent_id="alpha")
        assert len(alpha_entries) == 2

    def test_get_denied_actions(self, tmp_path):
        """过滤出 DENIED 条目"""
        audit_path = tmp_path / "audit.jsonl"
        entries = [
            {"agent_id": "alpha", "action": "read", "result": "ALLOWED", "timestamp": "2024-01-01T00:00:00Z"},
            {"agent_id": "alpha", "action": "write", "result": "DENIED", "timestamp": "2024-01-01T00:01:00Z"},
            {"agent_id": "beta", "action": "delete", "result": "DENIED", "timestamp": "2024-01-01T00:02:00Z"},
        ]
        audit_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

        monitor = AgentMonitor(audit_log_path=audit_path)
        denied = monitor.get_denied_actions()
        assert len(denied) == 2
        assert all(d["result"] == "DENIED" for d in denied)

    def test_detect_anomalies_high_frequency(self, tmp_path):
        """检测高频异常 — 超过 100 条同 agent 日志"""
        audit_path = tmp_path / "audit.jsonl"
        # 创建 150 条来自 alpha 的日志
        entries = [
            {"agent_id": "alpha", "action": "read", "result": "ALLOWED", "timestamp": f"2024-01-01T00:{i:02d}:00Z"}
            for i in range(150)
        ]
        audit_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")

        monitor = AgentMonitor(audit_log_path=audit_path)
        anomalies = monitor.detect_anomalies()
        # alpha 有 150 条 > 100 阈值，应被检测到
        assert len(anomalies) > 0
        assert any(a["agent_id"] == "alpha" for a in anomalies)


from plugins.harness.monitor import AgentPerformanceMonitor


class TestAgentPerformanceMonitor:
    """测试 AgentPerformanceMonitor"""

    def test_record_and_stats(self, tmp_path):
        """验证记录和统计"""
        log_path = tmp_path / "perf.jsonl"
        monitor = AgentPerformanceMonitor(log_path)
        monitor.record("alpha", "task-1", 150.0, True, 1)
        monitor.record("alpha", "task-2", 200.0, False, 2)
        monitor.record("beta", "task-3", 100.0, True, 0)

        stats = monitor.get_stats()
        assert "alpha" in stats
        assert stats["alpha"]["total"] == 2
        assert stats["alpha"]["success_rate"] == 50.0
        assert stats["alpha"]["total_retries"] == 3
        assert "beta" in stats
        assert stats["beta"]["success_rate"] == 100.0

    def test_detect_failure_patterns(self, tmp_path):
        """验证失败模式检测"""
        log_path = tmp_path / "perf.jsonl"
        monitor = AgentPerformanceMonitor(log_path)
        # 连续 3 次失败
        for i in range(3):
            monitor.record("alpha", f"task-{i}", 100.0, False, 0)
        # 1 次成功
        monitor.record("alpha", "task-ok", 100.0, True, 0)

        failures = monitor.detect_failure_patterns()
        assert len(failures) == 1
        assert failures[0]["agent_id"] == "alpha"
        assert failures[0]["consecutive_failures"] == 3
