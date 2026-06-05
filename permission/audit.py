"""审计日志"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from core.redaction import redact_sensitive


logger = logging.getLogger(__name__)


def restrict_file_permissions(path: Path, mode: int = 0o600) -> None:
    """Apply owner-only POSIX-style permissions through a patchable boundary."""

    Path(path).chmod(mode)


class AuditLogger:
    """Audit logger for permission decisions and security events."""

    def __init__(self, log_path: Path):
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _restrict_log_permissions(self) -> None:
        try:
            restrict_file_permissions(self._log_path, 0o600)
        except OSError as exc:
            logger.warning(
                "audit_log_permission_restriction_failed path=%s error=%s",
                redact_sensitive(str(self._log_path)),
                redact_sensitive(str(exc)),
            )

    def log(
        self,
        agent_id: str,
        action: str,
        resource: str,
        result: str,
        reason: str,
        trace_id: str | None = None,
    ) -> None:
        entry = redact_sensitive(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trace_id": trace_id or str(uuid4()),
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "result": result,
                "reason": reason,
                "diagnostic_stage": "audit.write",
                "log_path": str(self._log_path),
            }
        )

        def opener(path: str, flags: int) -> int:
            return os.open(path, flags, 0o600)

        with open(self._log_path, "a", encoding="utf-8", opener=opener) as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._restrict_log_permissions()
