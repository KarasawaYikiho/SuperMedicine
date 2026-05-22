"""Agent 行为监控"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class AgentMonitor:
    def __init__(self, audit_log_path: Path):
        self._audit_log = Path(audit_log_path)
    def get_permission_audit(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        if not self._audit_log.exists(): return []
        entries = []
        with open(self._audit_log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
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
        return [{"agent_id": aid, "count": c, "type": "high_frequency"} for aid, c in counts.items() if c > 100]
