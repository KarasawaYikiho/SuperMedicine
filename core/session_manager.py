"""会话管理器 — UUID 会话 + TTL 超时清理"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class Session:
    """单个会话"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._data: dict[str, Any] = {}
        self.created_at = datetime.now(timezone.utc)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def age_seconds(self) -> float:
        """会话已存在时间（秒）"""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


class SessionManager:
    """会话管理器 — 支持 TTL 超时"""

    def __init__(self, ttl_seconds: float | None = None):
        self._sessions: dict[str, Session] = {}
        self._ttl_seconds = ttl_seconds

    def create(self) -> Session:
        sid = str(uuid4())
        s = Session(sid)
        self._sessions[sid] = s
        return s

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def cleanup_expired(self) -> int:
        """清理过期会话，返回清理数量"""
        if self._ttl_seconds is None:
            return 0
        expired = [
            sid
            for sid, s in self._sessions.items()
            if s.age_seconds > self._ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def list_active(self) -> list[Session]:
        """列出所有未过期会话"""
        if self._ttl_seconds is None:
            return list(self._sessions.values())
        return [
            s for s in self._sessions.values() if s.age_seconds <= self._ttl_seconds
        ]
