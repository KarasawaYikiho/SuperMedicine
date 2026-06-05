"""Agent 行为监控"""

from __future__ import annotations
import json
from json import JSONDecodeError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _jsonl_warning(
    path: Path, line_number: int, code: str, message: str
) -> dict[str, Any]:
    return {"path": str(path), "line": line_number, "code": code, "message": message}


def _read_jsonl_objects(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not path.exists():
        return entries, warnings
    if path.is_dir():
        raise ValueError(f"{path} must be a file path, not a directory")

    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except JSONDecodeError as exc:
                warnings.append(
                    _jsonl_warning(path, line_number, "malformed_json", str(exc))
                )
                continue
            if not isinstance(entry, dict):
                warnings.append(
                    _jsonl_warning(
                        path,
                        line_number,
                        "non_object_json",
                        "JSONL entry must be an object",
                    )
                )
                continue
            entries.append(entry)
    return entries, warnings


class AgentMonitor:
    def __init__(self, audit_log_path: Path, anomaly_threshold: int = 100):
        self._audit_log = Path(audit_log_path)
        self.anomaly_threshold = anomaly_threshold
        self._warnings: list[dict[str, Any]] = []

    @property
    def warnings(self) -> list[dict[str, Any]]:
        return list(self._warnings)

    def get_permission_audit(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        entries = []
        raw_entries, self._warnings = _read_jsonl_objects(self._audit_log)
        for entry in raw_entries:
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
        return [
            {"agent_id": aid, "count": c, "type": "high_frequency"}
            for aid, c in counts.items()
            if c > self.anomaly_threshold
        ]


class AgentPerformanceMonitor:
    """Agent 性能监控 — 记录任务执行耗时、成功率、重试次数"""

    def __init__(self, log_path: Path, *, create_parent: bool = True):
        self._log_path = Path(log_path)
        if create_parent:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._warnings: list[dict[str, Any]] = []

    @property
    def warnings(self) -> list[dict[str, Any]]:
        return list(self._warnings)

    def record(
        self,
        agent_id: str,
        task_id: str,
        duration_ms: float,
        success: bool,
        retries: int = 0,
    ) -> None:
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
        stats: dict[str, dict[str, Any]] = {}
        entries, self._warnings = self._validated_performance_entries()
        for entry in entries:
            aid = entry["agent_id"]
            if agent_id and aid != agent_id:
                continue
            if aid not in stats:
                stats[aid] = {
                    "total": 0,
                    "success": 0,
                    "total_duration_ms": 0.0,
                    "total_retries": 0,
                }
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
                "success_rate": round(s["success"] / s["total"] * 100, 1)
                if s["total"] > 0
                else 0,
                "avg_duration_ms": round(s["total_duration_ms"] / s["total"], 1)
                if s["total"] > 0
                else 0,
                "total_retries": s["total_retries"],
            }
        return result

    def detect_failure_patterns(
        self, agent_id: str | None = None
    ) -> list[dict[str, Any]]:
        """检测失败模式 — 连续失败 3 次以上"""
        failures: list[dict[str, Any]] = []
        consecutive = 0
        last_agent = None

        entries, self._warnings = self._validated_performance_entries()
        for entry in entries:
            if agent_id and entry["agent_id"] != agent_id:
                continue

            if not entry["success"]:
                consecutive += 1
                last_agent = entry["agent_id"]
            else:
                if consecutive >= 3:
                    failures.append(
                        {"agent_id": last_agent, "consecutive_failures": consecutive}
                    )
                consecutive = 0

        if consecutive >= 3:
            failures.append(
                {"agent_id": last_agent, "consecutive_failures": consecutive}
            )

        return failures

    def _validated_performance_entries(
        self,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        entries, warnings = _read_jsonl_objects(self._log_path)
        valid: list[dict[str, Any]] = []
        required = {"agent_id", "success", "duration_ms", "retries"}
        for index, entry in enumerate(entries, start=1):
            missing = sorted(required - set(entry))
            if missing:
                warnings.append(
                    _jsonl_warning(
                        self._log_path,
                        index,
                        "missing_fields",
                        f"Missing fields: {', '.join(missing)}",
                    )
                )
                continue
            if not isinstance(entry["agent_id"], str) or not entry["agent_id"].strip():
                warnings.append(
                    _jsonl_warning(
                        self._log_path,
                        index,
                        "invalid_agent_id",
                        "agent_id must be a non-empty string",
                    )
                )
                continue
            if not isinstance(entry["success"], bool):
                warnings.append(
                    _jsonl_warning(
                        self._log_path,
                        index,
                        "invalid_success",
                        "success must be a boolean",
                    )
                )
                continue
            if not isinstance(entry["duration_ms"], (int, float)):
                warnings.append(
                    _jsonl_warning(
                        self._log_path,
                        index,
                        "invalid_duration",
                        "duration_ms must be numeric",
                    )
                )
                continue
            if not isinstance(entry["retries"], int):
                warnings.append(
                    _jsonl_warning(
                        self._log_path,
                        index,
                        "invalid_retries",
                        "retries must be an integer",
                    )
                )
                continue
            valid.append(entry)
        return valid, warnings
