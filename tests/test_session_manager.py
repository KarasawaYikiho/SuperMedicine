"""SessionManager 测试"""
import pytest
from core.session_manager import SessionManager, Session


class TestSession:
    """测试 Session 类"""

    def test_session_set_get(self):
        """验证 Session.set() / Session.get() 读写正确"""
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
        """验证 create() 返回 Session 对象且有唯一 session_id"""
        manager = SessionManager()
        session = manager.create()
        assert session is not None
        assert isinstance(session, Session)
        assert isinstance(session.session_id, str)
        assert len(session.session_id) > 0

    def test_get_existing(self):
        """验证 get() 返回已创建的 session"""
        manager = SessionManager()
        session = manager.create()
        found = manager.get(session.session_id)
        assert found is not None
        assert found is session
        assert found.session_id == session.session_id

    def test_get_nonexistent(self):
        """验证 get() 对不存在的 session_id 返回 None"""
        manager = SessionManager()
        assert manager.get("nonexistent-id") is None

    def test_multiple_sessions_isolation(self):
        """验证创建多个 session 互相隔离"""
        manager = SessionManager()
        s1 = manager.create()
        s2 = manager.create()

        assert s1.session_id != s2.session_id

        s1.set("data", "from-session-1")
        s2.set("data", "from-session-2")

        assert s1.get("data") == "from-session-1"
        assert s2.get("data") == "from-session-2"
