"""会话管理器 — UUID 会话 + TTL 超时清理 + 可选数据库持久化"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

if TYPE_CHECKING:
    from core.database.database import Database
    from core.database.repository import SessionRepository


class Session:
    """单个会话"""

    def __init__(
        self,
        session_id: str,
        on_dirty: Callable[[Session], None] | None = None,
    ):
        self.session_id = session_id
        self._data: dict[str, Any] = {}
        self.created_at = datetime.now(timezone.utc)
        self._dirty: bool = False
        self._on_dirty = on_dirty

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.mark_dirty()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def mark_dirty(self) -> None:
        """标记会话数据已变更"""
        self._dirty = True
        if self._on_dirty is not None:
            self._on_dirty(self)

    def mark_clean(self) -> None:
        """标记会话数据已持久化（清除脏标志）"""
        self._dirty = False

    @property
    def is_dirty(self) -> bool:
        """会话数据是否已变更（只读）"""
        return self._dirty

    @property
    def age_seconds(self) -> float:
        """会话已存在时间（秒）"""
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()


class SessionManager:
    """会话管理器 — 支持 TTL 超时 + 可选数据库持久化"""

    def __init__(
        self,
        ttl_seconds: float | None = None,
        db: Database | None = None,
    ):
        self._sessions: dict[str, Session] = {}
        self._ttl_seconds = ttl_seconds
        self._db = db
        self._session_repo: SessionRepository | None = None
        if db is not None:
            from core.database.repository import SessionRepository

            self._session_repo = SessionRepository(db)

    def create(self) -> Session:
        on_dirty = self.persist if self._session_repo is not None else None

        if self._session_repo is not None:
            # Create in DB first — use the generated UUID
            db_session = self._session_repo.create()
            sid = db_session["id"]
        else:
            sid = str(uuid4())

        s = Session(sid, on_dirty=on_dirty)
        self._sessions[sid] = s

        if self._session_repo is not None:
            s.mark_clean()  # already persisted by SessionRepository.create()

        return s

    def get(self, session_id: str) -> Session | None:
        # 1) Check in-memory cache first
        session = self._sessions.get(session_id)
        if session is not None:
            return session

        # 2) Fall back to database
        if self._session_repo is not None:
            db_session = self._session_repo.get(session_id)
            if db_session is not None:
                on_dirty = self.persist
                session = Session(db_session["id"], on_dirty=on_dirty)
                session._data = db_session.get("data", {})
                if "created_at" in db_session:
                    session.created_at = datetime.fromisoformat(db_session["created_at"])
                session.mark_clean()
                self._sessions[session.session_id] = session
                return session

        return None

    def persist(self, session: Session) -> None:
        """Persist a dirty session to the database (no-op when db=None)."""
        if self._session_repo is not None and session.is_dirty:
            self._session_repo.update(
                {
                    "id": session.session_id,
                    "data": session._data,
                }
            )
            session.mark_clean()

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
