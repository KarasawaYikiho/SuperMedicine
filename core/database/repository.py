"""Repository pattern implementation for database access.

This module provides abstract base repository and concrete implementations
for sessions and agents, following the repository pattern for clean data access.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

from core.database.database import Database

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Abstract base repository for CRUD operations.

    Subclasses must implement the abstract methods to provide
    entity-specific database operations.
    """

    def __init__(self, db: Database):
        """Initialize repository with database instance.

        Args:
            db: Database instance for persistence
        """
        self._db = db

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity in the database."""
        ...

    @abstractmethod
    def get(self, id: str) -> T | None:
        """Retrieve an entity by ID."""
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        ...

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete an entity by ID. Returns True if deleted."""
        ...

    @abstractmethod
    def list_all(self) -> list[T]:
        """List all entities."""
        ...


class SessionRepository(Repository[dict[str, Any]]):
    """Repository for session CRUD operations.

    Sessions are stored as JSON data with automatic timestamp management.
    """

    def create(self, entity: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a new session.

        Args:
            entity: Optional initial session data. If None, creates empty session.

        Returns:
            Created session with generated ID and timestamps
        """
        session_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = json.dumps(entity or {})

        self._db.execute(
            "INSERT INTO sessions (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, data, now, now)
        )

        return {
            "id": session_id,
            "data": entity or {},
            "created_at": now,
            "updated_at": now
        }

    def get(self, id: str) -> dict[str, Any] | None:
        """Retrieve a session by ID.

        Args:
            id: Session ID

        Returns:
            Session data or None if not found
        """
        row = self._db.fetchone(
            "SELECT id, data, created_at, updated_at FROM sessions WHERE id = ?",
            (id,)
        )
        if row is None:
            return None

        return {
            "id": row["id"],
            "data": json.loads(row["data"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    def update(self, entity: dict[str, Any]) -> dict[str, Any]:
        """Update session data.

        Args:
            entity: Session data with 'id' field

        Returns:
            Updated session data

        Raises:
            ValueError: If session ID is missing
        """
        if "id" not in entity:
            raise ValueError("Session entity must have an 'id' field")

        now = datetime.now(timezone.utc).isoformat()
        data = json.dumps(entity.get("data", {}))

        self._db.execute(
            "UPDATE sessions SET data = ?, updated_at = ? WHERE id = ?",
            (data, now, entity["id"])
        )

        entity["updated_at"] = now
        return entity

    def delete(self, id: str) -> bool:
        """Delete a session by ID.

        Args:
            id: Session ID

        Returns:
            True if session was deleted, False if not found
        """
        cursor = self._db.execute(
            "DELETE FROM sessions WHERE id = ?",
            (id,)
        )
        return cursor.rowcount > 0

    def list_all(self) -> list[dict[str, Any]]:
        """List all sessions.

        Returns:
            List of all sessions
        """
        rows = self._db.fetchall(
            "SELECT id, data, created_at, updated_at FROM sessions ORDER BY created_at DESC"
        )
        return [
            {
                "id": row["id"],
                "data": json.loads(row["data"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]

    def get_by_age(self, max_age_seconds: float) -> list[dict[str, Any]]:
        """Get sessions younger than max_age_seconds.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            List of sessions within age limit
        """
        cutoff = datetime.now(timezone.utc).timestamp() - max_age_seconds
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

        rows = self._db.fetchall(
            "SELECT id, data, created_at, updated_at FROM sessions WHERE created_at > ?",
            (cutoff_iso,)
        )
        return [
            {
                "id": row["id"],
                "data": json.loads(row["data"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]


class AgentRepository(Repository[dict[str, Any]]):
    """Repository for agent state CRUD operations.

    Agents are stored with their configuration and runtime state.
    """

    def create(self, entity: dict[str, Any]) -> dict[str, Any]:
        """Create a new agent.

        Args:
            entity: Agent data with 'name' field required

        Returns:
            Created agent with generated ID and timestamps

        Raises:
            ValueError: If agent name is missing
        """
        if "name" not in entity:
            raise ValueError("Agent entity must have a 'name' field")

        agent_id = entity.get("id", str(uuid4()))
        now = datetime.now(timezone.utc).isoformat()
        state = json.dumps(entity.get("state", {}))

        self._db.execute(
            "INSERT INTO agents (id, name, state, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (agent_id, entity["name"], state, now, now)
        )

        return {
            "id": agent_id,
            "name": entity["name"],
            "state": entity.get("state", {}),
            "created_at": now,
            "updated_at": now
        }

    def get(self, id: str) -> dict[str, Any] | None:
        """Retrieve an agent by ID.

        Args:
            id: Agent ID

        Returns:
            Agent data or None if not found
        """
        row = self._db.fetchone(
            "SELECT id, name, state, created_at, updated_at FROM agents WHERE id = ?",
            (id,)
        )
        if row is None:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "state": json.loads(row["state"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Retrieve an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent data or None if not found
        """
        row = self._db.fetchone(
            "SELECT id, name, state, created_at, updated_at FROM agents WHERE name = ?",
            (name,)
        )
        if row is None:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "state": json.loads(row["state"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }

    def update(self, entity: dict[str, Any]) -> dict[str, Any]:
        """Update agent state.

        Args:
            entity: Agent data with 'id' field

        Returns:
            Updated agent data

        Raises:
            ValueError: If agent ID is missing
        """
        if "id" not in entity:
            raise ValueError("Agent entity must have an 'id' field")

        now = datetime.now(timezone.utc).isoformat()
        state = json.dumps(entity.get("state", {}))

        self._db.execute(
            "UPDATE agents SET state = ?, updated_at = ? WHERE id = ?",
            (state, now, entity["id"])
        )

        entity["updated_at"] = now
        return entity

    def delete(self, id: str) -> bool:
        """Delete an agent by ID.

        Args:
            id: Agent ID

        Returns:
            True if agent was deleted, False if not found
        """
        cursor = self._db.execute(
            "DELETE FROM agents WHERE id = ?",
            (id,)
        )
        return cursor.rowcount > 0

    def list_all(self) -> list[dict[str, Any]]:
        """List all agents.

        Returns:
            List of all agents
        """
        rows = self._db.fetchall(
            "SELECT id, name, state, created_at, updated_at FROM agents ORDER BY name"
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "state": json.loads(row["state"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]

    def list_enabled(self) -> list[dict[str, Any]]:
        """List agents that are currently enabled.

        Returns:
            List of enabled agents
        """
        rows = self._db.fetchall(
            "SELECT id, name, state, created_at, updated_at FROM agents "
            "WHERE json_extract(state, '$.enabled') = 1 OR json_extract(state, '$.enabled') IS NULL"
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "state": json.loads(row["state"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]
