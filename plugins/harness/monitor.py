"""Agent 行为监控"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class AgentMonitor:
    def __init__(self, audit_log_path: Path, anomaly_threshold: int = 100):
        self._audit_log = Path(audit_log_path)
        self.anomaly_threshold = anomaly_threshold
    def get_permission_audit(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        if not self._audit_log.exists():
            return []
        entries = []
        with open(self._audit_log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if agent_id is None or entry.get("agent_id") == agent_id:
                    entries.append(entry)
        return entries
    def get_denied_actions(self) -> list[dict[str, Any]]:
        return [e for e in self.get_permission_audit() if e.get("result") == "DENIED"]
    def detect_anomalies(self) -> list[dict[str, Any]]:
        entries = self.get_permission_audit()
        counts: dict[str, int] = {}
        for e in entries:
            aid = e.get("agent_id", "unknown")
            counts[aid] = counts.get(aid, 0) + 1
        return [{"agent_id": aid, "count": c, "type": "high_frequency"} for aid, c in counts.items() if c > self.anomaly_threshold]


class AgentPerformanceMonitor:
    """Agent 性能监控 — 记录任务执行耗时、成功率、重试次数"""

    def __init__(self, log_path: Path):
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, agent_id: str, task_id: str, duration_ms: float,
               success: bool, retries: int = 0) -> None:
        """记录一次任务执行的性能指标"""
        entry = {
            "agent_id": agent_id,
            "task_id": task_id,
            "duration_ms": duration_ms,
            "success": success,
            "retries": retries,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_stats(self, agent_id: str | None = None) -> dict[str, Any]:
        """获取性能统计

        Returns:
            {"agent_id": {"total": N, "success_rate": %, "avg_duration_ms": ms, "total_retries": N}}
        """
        if not self._log_path.exists():
            return {}

        stats: dict[str, dict[str, Any]] = {}
        with open(self._log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                aid = entry["agent_id"]
                if agent_id and aid != agent_id:
                    continue
                if aid not in stats:
                    stats[aid] = {"total": 0, "success": 0, "total_duration_ms": 0.0, "total_retries": 0}
                s = stats[aid]
                s["total"] += 1
                if entry["success"]:
                    s["success"] += 1
                s["total_duration_ms"] += entry["duration_ms"]
                s["total_retries"] += entry["retries"]

        result = {}
        for aid, s in stats.items():
            result[aid] = {
                "total": s["total"],
                "success_rate": round(s["success"] / s["total"] * 100, 1) if s["total"] > 0 else 0,
                "avg_duration_ms": round(s["total_duration_ms"] / s["total"], 1) if s["total"] > 0 else 0,
                "total_retries": s["total_retries"],
            }
        return result

    def detect_failure_patterns(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        """检测失败模式 — 连续失败 3 次以上"""
        if not self._log_path.exists():
            return []

        failures: list[dict[str, Any]] = []
        consecutive = 0
        last_agent = None

        with open(self._log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if agent_id and entry["agent_id"] != agent_id:
                    continue

                if not entry["success"]:
                    consecutive += 1
                    last_agent = entry["agent_id"]
                else:
                    if consecutive >= 3:
                        failures.append({"agent_id": last_agent, "consecutive_failures": consecutive})
                    consecutive = 0

        if consecutive >= 3:
            failures.append({"agent_id": last_agent, "consecutive_failures": consecutive})

        return failures
