"""Database integration tests — Database → SessionManager → Kernel full pipeline.

Tests the complete integration flow:
  - Kernel auto-creates database on init
  - Sessions persist across kernel restarts
  - Dirty flag triggers automatic persistence
  - Agent state persists after chain execution
  - Graceful fallback when database is unavailable
  - Backward compatibility in no-database mode
"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from core.database.database import Database
from core.database.repository import AgentRepository, SessionRepository
from core.kernel import Kernel
from core.session_manager import SessionManager
from permission.engine import PermissionEngine


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_kernel(tmp_path: Path) -> Kernel:
    """Create a fully initialised Kernel in tmp_path."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"project": "test"}), encoding="utf-8")
    (tmp_path / "plugins").mkdir(exist_ok=True)
    (tmp_path / "policies").mkdir(exist_ok=True)
    shutil.copyfile(
        PermissionEngine.default_policy_path(),
        tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
    )
    return Kernel(
        config_path=config_path,
        plugins_dir=tmp_path / "plugins",
        policies_dir=tmp_path / "policies",
    )


# ── 1. Kernel auto-creates database on init ─────────────────────────────


class TestKernelCreatesDatabaseOnInit:
    """Kernel 初始化时自动创建数据库."""

    def test_kernel_creates_database_on_init(self, tmp_path):
        """Verify Kernel.__init__ creates a Database and populates schema tables."""
        kernel = _make_kernel(tmp_path)

        assert kernel.database is not None
        db_path = tmp_path / "data.db"
        assert kernel.database.path == db_path

        # Schema tables should exist
        tables = kernel.database.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = {t["name"] for t in tables}
        assert "sessions" in table_names
        assert "agents" in table_names
        assert "plugins" in table_names
        assert "migrations" in table_names

        kernel.close()


# ── 2. Session persists across kernel restart ────────────────────────────


class TestSessionPersistsAcrossKernelRestart:
    """会话在 Kernel 重启后可恢复."""

    def test_session_persists_across_kernel_restart(self, tmp_path):
        """Create a session, write data, close kernel, re-open, verify data survives."""
        db_path = tmp_path / "data.db"

        # --- First kernel lifecycle ---
        kernel1 = _make_kernel(tmp_path)
        session1 = kernel1.session_manager.create()
        sid = session1.session_id
        session1.set("experiment_id", "exp-001")
        session1.set("results", {"p_value": 0.03})

        # Force persistence so data reaches SQLite
        kernel1.session_manager.persist(session1)

        # Verify data is in the database directly
        repo = SessionRepository(kernel1.database)
        db_row = repo.get(sid)
        assert db_row is not None
        assert db_row["data"]["experiment_id"] == "exp-001"

        # --- Simulate restart: close and re-open ---
        kernel1.close()
        assert db_path.exists()

        kernel2 = _make_kernel(tmp_path)
        try:
            # Session should be retrievable from the database
            session2 = kernel2.session_manager.get(sid)
            assert session2 is not None
            assert session2.session_id == sid
            assert session2.get("experiment_id") == "exp-001"
            assert session2.get("results") == {"p_value": 0.03}
        finally:
            kernel2.close()


# ── 3. Session dirty flag triggers persistence ───────────────────────────


class TestSessionDirtyFlagTriggersPersistence:
    """Session dirty 标志触发自动持久化."""

    def test_session_dirty_flag_triggers_persistence(self, tmp_path):
        """Setting data on a session should mark it dirty and auto-persist via on_dirty callback."""
        kernel = _make_kernel(tmp_path)

        try:
            sm = kernel.session_manager
            session = sm.create()
            sid = session.session_id

            # Fresh session should be clean (just created in DB)
            assert session.is_dirty is False

            # Setting data should mark dirty and trigger on_dirty callback
            session.set("analysis_type", "ttest")
            assert session.is_dirty is False  # on_dirty -> persist -> mark_clean

            # Verify data was persisted to database
            repo = SessionRepository(kernel.database)
            db_row = repo.get(sid)
            assert db_row is not None
            assert db_row["data"]["analysis_type"] == "ttest"

            # Another set triggers another auto-persist
            session.set("alpha", 0.05)
            assert session.is_dirty is False

            db_row = repo.get(sid)
            assert db_row["data"]["alpha"] == 0.05
            assert db_row["data"]["analysis_type"] == "ttest"
        finally:
            kernel.close()


# ── 4. Agent state persists after chain ──────────────────────────────────


class TestAgentStatePersistsAfterChain:
    """Agent 状态在 chain 执行后持久化."""

    def test_agent_state_persists_after_chain(self, tmp_path):
        """save_agent_state / load_agent_state round-trips through the database."""
        kernel = _make_kernel(tmp_path)

        try:
            alpha_state = {
                "last_task": "analyse hypertension cohort",
                "tokens_used": 1200,
                "status": "completed",
            }
            beta_state = {
                "last_task": "review alpha output",
                "approved": True,
                "feedback": "Looks good",
            }

            kernel.save_agent_state("alpha", alpha_state)
            kernel.save_agent_state("beta", beta_state)

            # Load should return the persisted state
            loaded_alpha = kernel.load_agent_state("alpha")
            assert loaded_alpha is not None
            assert loaded_alpha["last_task"] == "analyse hypertension cohort"
            assert loaded_alpha["tokens_used"] == 1200
            assert loaded_alpha["status"] == "completed"

            loaded_beta = kernel.load_agent_state("beta")
            assert loaded_beta is not None
            assert loaded_beta["approved"] is True

            # Direct repository access should also see the data
            repo = AgentRepository(kernel.database)
            alpha_row = repo.get_by_name("alpha")
            assert alpha_row is not None
            assert alpha_row["state"]["tokens_used"] == 1200

            # Update should overwrite
            kernel.save_agent_state("alpha", {"status": "idle", "tokens_used": 0})
            updated = kernel.load_agent_state("alpha")
            assert updated["status"] == "idle"
            assert updated["tokens_used"] == 0
        finally:
            kernel.close()


# ── 5. Kernel fallback when DB unavailable ───────────────────────────────


class TestKernelFallbackWhenDbUnavailable:
    """数据库不可用时回退到纯内存模式."""

    def test_kernel_fallback_when_db_unavailable(self, tmp_path):
        """When the database path's parent is unreadable, Kernel should
        fall back to in-memory mode (database=None, agent_repo=None)."""
        # Point config at a non-existent nested path that will fail to create
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({"project": "test"}), encoding="utf-8")

        policies = tmp_path / "policies"
        policies.mkdir(exist_ok=True)
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )

        # Use a read-only parent directory to force database creation failure
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()

        # Monkeypatch Database.connect to force failure
        original_connect = Database.connect

        def failing_connect(self_db):
            raise OSError("Permission denied: cannot create database")

        Database.connect = failing_connect
        try:
            kernel = Kernel(
                config_path=config_path,
                plugins_dir=tmp_path / "plugins",
                policies_dir=policies,
            )

            # Should fall back gracefully
            assert kernel.database is None

            # SessionManager should still work in-memory
            session = kernel.session_manager.create()
            session.set("key", "value")
            assert session.get("key") == "value"
            assert kernel.session_manager.get(session.session_id) is session

            # Agent repo should be unavailable
            assert kernel._agent_repo is None

            # save/load agent state should be no-ops
            kernel.save_agent_state("alpha", {"test": True})
            assert kernel.load_agent_state("alpha") is None
        finally:
            Database.connect = original_connect


# ── 6. Backward compatibility: no-database mode ──────────────────────────


class TestBackwardCompatibilityNoDb:
    """无数据库时行为与修改前一致."""

    def test_backward_compatibility_no_db(self):
        """SessionManager without a database should behave identically
        to the pre-database implementation."""
        sm = SessionManager()

        # Create / get round-trip
        s1 = sm.create()
        assert isinstance(s1.session_id, str)
        assert len(s1.session_id) > 0

        found = sm.get(s1.session_id)
        assert found is s1

        # Data isolation
        s2 = sm.create()
        s1.set("x", 1)
        s2.set("x", 2)
        assert s1.get("x") == 1
        assert s2.get("x") == 2

        # Missing session returns None
        assert sm.get("nonexistent") is None

        # TTL cleanup still works
        sm_ttl = SessionManager(ttl_seconds=60)
        s_ttl = sm_ttl.create()
        assert sm_ttl.cleanup_expired() == 0  # not expired yet
        assert sm_ttl.get(s_ttl.session_id) is not None

    def test_kernel_no_db_sessions_still_work(self, tmp_path):
        """When database is unavailable, Kernel session manager
        still creates and retrieves sessions in-memory."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({"project": "test"}), encoding="utf-8")
        policies = tmp_path / "policies"
        policies.mkdir(exist_ok=True)
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )

        original_connect = Database.connect
        Database.connect = lambda self_db: (_ for _ in ()).throw(
            OSError("no db")
        )
        try:
            kernel = Kernel(
                config_path=config_path,
                plugins_dir=tmp_path / "plugins",
                policies_dir=policies,
            )
            assert kernel.database is None

            session = kernel.session_manager.create()
            session.set("task", "analyze")
            assert session.get("task") == "analyze"

            retrieved = kernel.session_manager.get(session.session_id)
            assert retrieved is session
        finally:
            Database.connect = original_connect

    def test_kernel_no_db_agent_state_is_noop(self, tmp_path):
        """save_agent_state / load_agent_state are safe no-ops
        when database is unavailable."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({"project": "test"}), encoding="utf-8")
        policies = tmp_path / "policies"
        policies.mkdir(exist_ok=True)
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            policies / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )

        original_connect = Database.connect
        Database.connect = lambda self_db: (_ for _ in ()).throw(
            OSError("no db")
        )
        try:
            kernel = Kernel(
                config_path=config_path,
                plugins_dir=tmp_path / "plugins",
                policies_dir=policies,
            )

            # Should not raise
            kernel.save_agent_state("alpha", {"status": "running"})
            assert kernel.load_agent_state("alpha") is None
            kernel.save_agent_state("gamma", {"content": "done"})
            assert kernel.load_agent_state("gamma") is None
        finally:
            Database.connect = original_connect
