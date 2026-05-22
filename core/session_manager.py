"""会话管理"""
from __future__ import annotations
from typing import Any
from uuid import uuid4

class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context: dict[str, Any] = {}
    def set(self, key: str, value: Any) -> None: self.context[key] = value
    def get(self, key: str, default: Any = None) -> Any: return self.context.get(key, default)

class SessionManager:
    def __init__(self): self._sessions: dict[str, Session] = {}
    def create(self) -> Session:
        sid = str(uuid4()); s = Session(sid); self._sessions[sid] = s; return s
    def get(self, session_id: str) -> Session | None: return self._sessions.get(session_id)
