"""审计日志"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

class AuditLogger:
    def __init__(self, log_path: Path):
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
    def log(self, agent_id: str, action: str, resource: str, result: str, reason: str, trace_id: str | None = None) -> None:
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "trace_id": trace_id or str(uuid4()), "agent_id": agent_id, "action": action, "resource": resource, "result": result, "reason": reason}
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
