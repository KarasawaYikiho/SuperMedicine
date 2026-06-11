"""SQLite-based database class for persistent storage.

This module provides a thread-safe SQLite database wrapper with context manager
support and automatic table creation for sessions, agents, and plugins.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator


class Database:
    """SQLite database wrapper with thread-safe connection handling.
    
    Usage:
        # As context manager (recommended)
        with Database() as db:
            db.execute("INSERT INTO sessions ...")
        
        # Manual lifecycle
        db = Database()
        db.connect()
        try:
            db.execute("SELECT * FROM sessions")
        finally:
            db.disconnect()
    """
    
    # Schema for core tables
    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        data TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS agents (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS plugins (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        version TEXT,
        config TEXT NOT NULL DEFAULT '{}',
        enabled BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    def __init__(self, db_path: str | Path | None = None):
        """Initialize database with optional custom path.
        
        Args:
            db_path: Path to SQLite database file. Defaults to .supermedicine/data.db
        """
        if db_path is None:
            db_path = Path(".supermedicine") / "data.db"
        self._db_path = Path(db_path)
        self._local = threading.local()
        self._lock = threading.Lock()
    
    @property
    def path(self) -> Path:
        """Return the database file path."""
        return self._db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a thread-local connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent read performance
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection
    
    def connect(self) -> None:
        """Establish database connection and create tables."""
        conn = self._get_connection()
        self._init_schema(conn)
    
    def disconnect(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "connection") and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
    
    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initialize database schema."""
        conn.executescript(self.SCHEMA_SQL)
        conn.commit()
    
    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> sqlite3.Cursor:
        """Execute a SQL statement.
        
        Args:
            sql: SQL statement to execute
            params: Optional parameters for the SQL statement
            
        Returns:
            Cursor object with results
        """
        conn = self._get_connection()
        with self._lock:
            if params:
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute(sql)
            conn.commit()
            return cursor
    
    def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        """Execute a SQL statement with multiple parameter sets.
        
        Args:
            sql: SQL statement to execute
            params_list: List of parameter tuples
            
        Returns:
            Cursor object
        """
        conn = self._get_connection()
        with self._lock:
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            return cursor
    
    def fetchone(self, sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        """Execute SQL and return a single row as dict.
        
        Args:
            sql: SQL query
            params: Optional parameters
            
        Returns:
            Dictionary of column values or None if no results
        """
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)
    
    def fetchall(self, sql: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        """Execute SQL and return all rows as list of dicts.
        
        Args:
            sql: SQL query
            params: Optional parameters
            
        Returns:
            List of dictionaries with column values
        """
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database transactions.
        
        Commits on success, rolls back on exception.
        
        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT ...")
                conn.execute("UPDATE ...")
        """
        conn = self._get_connection()
        with self._lock:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def __enter__(self) -> Database:
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()
