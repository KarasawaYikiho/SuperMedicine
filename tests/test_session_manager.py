"""SessionManager 测试"""

from __future__ import annotations

from core.session_manager import SessionManager, Session


class TestSession:
    """测试 Session 类"""

    def test_session_set_get(self):
        """验证 Session.Set() / Session.Get() 读写正确"""
        session = Session("test-session-id")
        session.set("key1", "value1")
        session.set("key2", 42)
        assert session.get("key1") == "value1"
        assert session.get("key2") == 42

    def test_session_default_value(self):
        """验证默认值生效"""
        session = Session("test-session-id")
        assert session.get("nonexistent") is None
        assert session.get("nonexistent", "default") == "default"


class TestSessionManager:
    """测试 SessionManager 类"""

    def test_create(self):
        """验证 Create() 返回 Session 对象且有唯一 Session_ID"""
        manager = SessionManager()
        session = manager.create()
        assert session is not None
        assert isinstance(session, Session)
        assert isinstance(session.session_id, str)
        assert len(session.session_id) > 0

    def test_get_existing(self):
        """验证 Get() 返回已创建的 Session"""
        manager = SessionManager()
        session = manager.create()
        found = manager.get(session.session_id)
        assert found is not None
        assert found is session
        assert found.session_id == session.session_id

    def test_get_nonexistent(self):
        """验证 Get() 对不存在的 Session_ID 返回 None"""
        manager = SessionManager()
        assert manager.get("nonexistent-id") is None

    def test_multiple_sessions_isolation(self):
        """验证创建多个 Session 互相隔离"""
        manager = SessionManager()
        s1 = manager.create()
        s2 = manager.create()

        assert s1.session_id != s2.session_id

        s1.set("data", "from-session-1")
        s2.set("data", "from-session-2")

        assert s1.get("data") == "from-session-1"
        assert s2.get("data") == "from-session-2"


class TestSessionTTL:
    """测试会话 TTL 超时"""

    def test_ttl_cleanup_expired(self, monkeypatch):
        """验证 TTL 过期清理"""
        from datetime import datetime, timezone, timedelta

        manager = SessionManager(ttl_seconds=60)

        # 创建 Session 并伪造创建时间为 2 分钟前
        s = manager.create()
        s.created_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        # 创建另一个 Session，时间为现在
        s2 = manager.create()

        cleaned = manager.cleanup_expired()
        assert cleaned == 1
        assert manager.get(s.session_id) is None
        assert manager.get(s2.session_id) is not None

    def test_ttl_list_active(self, monkeypatch):
        """验证 list_active 只返回未过期会话"""
        from datetime import datetime, timezone, timedelta

        manager = SessionManager(ttl_seconds=60)
        s1 = manager.create()
        s1.created_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        s2 = manager.create()

        active = manager.list_active()
        assert len(active) == 1
        assert active[0].session_id == s2.session_id

    def test_no_ttl_default(self):
        """验证默认无 TTL 不清理"""
        manager = SessionManager()
        s = manager.create()
        cleaned = manager.cleanup_expired()
        assert cleaned == 0
        assert manager.get(s.session_id) is not None
