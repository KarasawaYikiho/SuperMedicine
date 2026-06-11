"""Database layer for persistent storage.

This package provides SQLite-based database functionality with:
- Database class for connection management
- Repository pattern for data access
- Migration system for schema evolution

Usage:
    from core.database import Database, SessionRepository, AgentRepository

    # Using context manager
    with Database() as db:
        sessions = SessionRepository(db)
        session = sessions.create({"key": "value"})

        agents = AgentRepository(db)
        agent = agents.create({"name": "my_agent", "state": {"active": True}})
"""

from core.database.database import Database
from core.database.repository import AgentRepository, Repository, SessionRepository
from core.database.migrations import Migration, MigrationManager

__all__ = [
    "Database",
    "Repository",
    "SessionRepository",
    "AgentRepository",
    "Migration",
    "MigrationManager",
]
