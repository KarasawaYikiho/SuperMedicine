"""Unit tests for the database layer (Database, Repositories, Migrations)."""

from __future__ import annotations

import pytest

from core.database.database import Database
from core.database.repository import AgentRepository, SessionRepository
from core.database.migrations import Migration, MigrationManager


# ── Database ─────────────────────────────────────────────────────────────


class TestDatabaseContextManager:
    """Tests for Database context manager lifecycle."""

    def test_context_manager_connects_and_disconnects(self, tmp_path):
        db_path = tmp_path / "test.db"
        with Database(db_path=db_path) as db:
            assert db.path == db_path
            # Should be able to execute SQL after connect
            db.execute("SELECT 1")

    def test_context_manager_creates_tables(self, tmp_path):
        db_path = tmp_path / "test.db"
        with Database(db_path=db_path) as db:
            tables = db.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            table_names = [t["name"] for t in tables]
            assert "sessions" in table_names
            assert "agents" in table_names
            assert "plugins" in table_names
            assert "migrations" in table_names

    def test_manual_connect_disconnect(self, tmp_path):
        db = Database(db_path=tmp_path / "manual.db")
        db.connect()
        db.execute("SELECT 1")
        db.disconnect()

    def test_disconnect_is_idempotent(self, tmp_path):
        db = Database(db_path=tmp_path / "idempotent.db")
        db.connect()
        db.disconnect()
        db.disconnect()  # Should not raise


class TestDatabaseExecuteFetch:
    """Tests for Database.execute / fetchone / fetchall."""

    def test_execute_insert_and_select(self, database):
        database.execute(
            "INSERT INTO sessions (id, data) VALUES (?, ?)",
            ("s1", '{"key": "value"}'),
        )
        row = database.fetchone("SELECT * FROM sessions WHERE id = ?", ("s1",))
        assert row is not None
        assert row["id"] == "s1"

    def test_fetchone_returns_none_for_missing(self, database):
        row = database.fetchone("SELECT * FROM sessions WHERE id = ?", ("missing",))
        assert row is None

    def test_fetchall_returns_list(self, database):
        database.execute("INSERT INTO sessions (id, data) VALUES (?, ?)", ("a", "{}"))
        database.execute("INSERT INTO sessions (id, data) VALUES (?, ?)", ("b", "{}"))
        rows = database.fetchall("SELECT * FROM sessions ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["id"] == "a"
        assert rows[1]["id"] == "b"

    def test_fetchall_empty_result(self, database):
        rows = database.fetchall("SELECT * FROM sessions WHERE 1=0")
        assert rows == []

    def test_execute_without_params(self, database):
        cursor = database.execute("SELECT 1 as val")
        row = cursor.fetchone()
        assert row["val"] == 1

    def test_executemany(self, database):
        params = [(f"s{i}", "{}") for i in range(3)]
        database.executemany(
            "INSERT INTO sessions (id, data) VALUES (?, ?)", params
        )
        rows = database.fetchall("SELECT * FROM sessions")
        assert len(rows) == 3


class TestDatabaseTransaction:
    """Tests for Database.transaction context manager."""

    def test_transaction_commits_on_success(self, database):
        with database.transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (id, data) VALUES (?, ?)",
                ("tx1", "{}"),
            )
        row = database.fetchone("SELECT * FROM sessions WHERE id = ?", ("tx1",))
        assert row is not None

    def test_transaction_rolls_back_on_exception(self, database):
        with pytest.raises(ValueError):
            with database.transaction() as conn:
                conn.execute(
                    "INSERT INTO sessions (id, data) VALUES (?, ?)",
                    ("tx2", "{}"),
                )
                raise ValueError("boom")
        row = database.fetchone("SELECT * FROM sessions WHERE id = ?", ("tx2",))
        assert row is None


# ── SessionRepository ────────────────────────────────────────────────────


class TestSessionRepository:
    """Tests for SessionRepository CRUD operations."""

    def test_create_session(self, database):
        repo = SessionRepository(database)
        session = repo.create({"user": "alice"})
        assert "id" in session
        assert session["data"] == {"user": "alice"}
        assert "created_at" in session
        assert "updated_at" in session

    def test_create_empty_session(self, database):
        repo = SessionRepository(database)
        session = repo.create()
        assert session["data"] == {}

    def test_get_session(self, database):
        repo = SessionRepository(database)
        created = repo.create({"key": "val"})
        fetched = repo.get(created["id"])
        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["data"] == {"key": "val"}

    def test_get_missing_session(self, database):
        repo = SessionRepository(database)
        assert repo.get("nonexistent") is None

    def test_update_session(self, database):
        repo = SessionRepository(database)
        session = repo.create({"version": 1})
        session["data"] = {"version": 2}
        updated = repo.update(session)
        assert updated["data"]["version"] == 2

    def test_update_without_id_raises(self, database):
        repo = SessionRepository(database)
        with pytest.raises(ValueError, match="id"):
            repo.update({"data": {}})

    def test_delete_session(self, database):
        repo = SessionRepository(database)
        session = repo.create({})
        assert repo.delete(session["id"]) is True
        assert repo.get(session["id"]) is None

    def test_delete_missing_returns_false(self, database):
        repo = SessionRepository(database)
        assert repo.delete("nonexistent") is False

    def test_list_all_sessions(self, database):
        repo = SessionRepository(database)
        repo.create({"n": 1})
        repo.create({"n": 2})
        repo.create({"n": 3})
        all_sessions = repo.list_all()
        assert len(all_sessions) == 3

    def test_list_all_empty(self, database):
        repo = SessionRepository(database)
        assert repo.list_all() == []


# ── AgentRepository ──────────────────────────────────────────────────────


class TestAgentRepository:
    """Tests for AgentRepository CRUD operations."""

    def test_create_agent(self, database):
        repo = AgentRepository(database)
        agent = repo.create({"name": "alpha", "state": {"active": True}})
        assert "id" in agent
        assert agent["name"] == "alpha"
        assert agent["state"] == {"active": True}

    def test_create_without_name_raises(self, database):
        repo = AgentRepository(database)
        with pytest.raises(ValueError, match="name"):
            repo.create({"state": {}})

    def test_create_with_custom_id(self, database):
        repo = AgentRepository(database)
        agent = repo.create({"id": "custom-id", "name": "beta"})
        assert agent["id"] == "custom-id"

    def test_get_agent(self, database):
        repo = AgentRepository(database)
        created = repo.create({"name": "gamma", "state": {}})
        fetched = repo.get(created["id"])
        assert fetched is not None
        assert fetched["name"] == "gamma"

    def test_get_missing_agent(self, database):
        repo = AgentRepository(database)
        assert repo.get("nonexistent") is None

    def test_get_by_name(self, database):
        repo = AgentRepository(database)
        repo.create({"name": "delta"})
        found = repo.get_by_name("delta")
        assert found is not None
        assert found["name"] == "delta"

    def test_get_by_name_missing(self, database):
        repo = AgentRepository(database)
        assert repo.get_by_name("nope") is None

    def test_update_agent(self, database):
        repo = AgentRepository(database)
        agent = repo.create({"name": "epsilon", "state": {"step": 1}})
        agent["state"] = {"step": 2}
        updated = repo.update(agent)
        assert updated["state"]["step"] == 2

    def test_update_without_id_raises(self, database):
        repo = AgentRepository(database)
        with pytest.raises(ValueError, match="id"):
            repo.update({"name": "bad"})

    def test_delete_agent(self, database):
        repo = AgentRepository(database)
        agent = repo.create({"name": "zeta"})
        assert repo.delete(agent["id"]) is True
        assert repo.get(agent["id"]) is None

    def test_delete_missing_returns_false(self, database):
        repo = AgentRepository(database)
        assert repo.delete("nonexistent") is False

    def test_list_all_agents(self, database):
        repo = AgentRepository(database)
        repo.create({"name": "a"})
        repo.create({"name": "b"})
        repo.create({"name": "c"})
        all_agents = repo.list_all()
        assert len(all_agents) == 3
        # Should be ordered by name
        names = [a["name"] for a in all_agents]
        assert names == sorted(names)

    def test_list_all_empty(self, database):
        repo = AgentRepository(database)
        assert repo.list_all() == []


# ── MigrationManager ─────────────────────────────────────────────────────


class TestMigrationManager:
    """Tests for MigrationManager."""

    def _make_manager(self, database) -> MigrationManager:
        return MigrationManager(database)

    def test_initial_version_is_zero(self, database):
        mgr = self._make_manager(database)
        assert mgr.get_current_version() == 0

    def test_register_migration(self, database):
        mgr = self._make_manager(database)
        m = Migration(1, "init", lambda db: None)
        mgr.register(m)
        assert len(mgr.get_pending()) == 1

    def test_register_duplicate_version_raises(self, database):
        mgr = self._make_manager(database)
        mgr.register(Migration(1, "first", lambda db: None))
        with pytest.raises(ValueError, match="already registered"):
            mgr.register(Migration(1, "duplicate", lambda db: None))

    def test_run_pending_applies_migrations(self, database):
        mgr = self._make_manager(database)
        applied_versions = []

        def m1(db):
            applied_versions.append(1)
            db.execute("CREATE TABLE IF NOT EXISTS t1 (id INTEGER PRIMARY KEY)")

        def m2(db):
            applied_versions.append(2)
            db.execute("CREATE TABLE IF NOT EXISTS t2 (id INTEGER PRIMARY KEY)")

        mgr.register(Migration(1, "create_t1", m1))
        mgr.register(Migration(2, "create_t2", m2))

        result = mgr.run_pending()
        assert len(result) == 2
        assert applied_versions == [1, 2]
        assert mgr.get_current_version() == 2

    def test_run_pending_skips_applied(self, database):
        mgr = self._make_manager(database)
        count = {"n": 0}

        def m1(db):
            count["n"] += 1

        mgr.register(Migration(1, "once", m1))
        mgr.run_pending()
        mgr.run_pending()  # Should not re-apply
        assert count["n"] == 1

    def test_run_pending_failure_raises(self, database):
        mgr = self._make_manager(database)

        def bad_migration(db):
            raise RuntimeError("migration exploded")

        mgr.register(Migration(1, "bad", bad_migration))
        with pytest.raises(RuntimeError, match="exploded"):
            mgr.run_pending()

    def test_get_applied(self, database):
        mgr = self._make_manager(database)
        mgr.register(Migration(1, "step1", lambda db: None))
        mgr.run_pending()
        applied = mgr.get_applied()
        assert len(applied) == 1
        assert applied[0]["version"] == 1
        assert applied[0]["name"] == "step1"

    def test_get_pending(self, database):
        mgr = self._make_manager(database)
        mgr.register(Migration(1, "a", lambda db: None))
        mgr.register(Migration(2, "b", lambda db: None))
        mgr.register(Migration(3, "c", lambda db: None))

        pending = mgr.get_pending()
        assert len(pending) == 3
        assert [m.version for m in pending] == [1, 2, 3]

    def test_rollback(self, database):
        mgr = self._make_manager(database)
        rolled_back_versions = []

        def up1(db):
            db.execute("CREATE TABLE IF NOT EXISTS rb1 (id INTEGER PRIMARY KEY)")

        def down1(db):
            rolled_back_versions.append(1)
            db.execute("DROP TABLE IF EXISTS rb1")

        def up2(db):
            db.execute("CREATE TABLE IF NOT EXISTS rb2 (id INTEGER PRIMARY KEY)")

        def down2(db):
            rolled_back_versions.append(2)
            db.execute("DROP TABLE IF EXISTS rb2")

        mgr.register(Migration(1, "rb1", up1, down1))
        mgr.register(Migration(2, "rb2", up2, down2))
        mgr.run_pending()

        result = mgr.rollback(0)
        assert len(result) == 2
        assert rolled_back_versions == [2, 1]  # Reverse order
        assert mgr.get_current_version() == 0

    def test_rollback_no_down_raises(self, database):
        mgr = self._make_manager(database)
        mgr.register(Migration(1, "no_down", lambda db: None))
        mgr.run_pending()

        with pytest.raises(ValueError, match="does not support rollback"):
            mgr.rollback(0)

    def test_rollback_to_target_version(self, database):
        mgr = self._make_manager(database)
        mgr.register(Migration(1, "v1", lambda db: None, lambda db: None))
        mgr.register(Migration(2, "v2", lambda db: None, lambda db: None))
        mgr.register(Migration(3, "v3", lambda db: None, lambda db: None))
        mgr.run_pending()

        result = mgr.rollback(1)
        assert len(result) == 2  # Rolled back v3 and v2
        assert mgr.get_current_version() == 1

    def test_rollback_noop_if_at_or_below_target(self, database):
        mgr = self._make_manager(database)
        mgr.register(Migration(1, "v1", lambda db: None))
        mgr.run_pending()

        result = mgr.rollback(1)
        assert result == []
