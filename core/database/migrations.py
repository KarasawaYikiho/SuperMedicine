"""Simple migration system for database schema evolution.

This module provides version tracking and schema migration support
for the SQLite database, allowing incremental schema updates.
"""

from __future__ import annotations

from typing import Any, Callable

from core.database.database import Database


class Migration:
    """Represents a single database migration.
    
    Attributes:
        version: Migration version number (must be unique and sequential)
        name: Human-readable migration name
        up: Function to apply the migration
        down: Function to rollback the migration (optional)
    """
    
    def __init__(
        self,
        version: int,
        name: str,
        up: Callable[[Database], None],
        down: Callable[[Database], None] | None = None
    ):
        """Initialize migration.
        
        Args:
            version: Unique version number
            name: Descriptive name
            up: Function to apply migration
            down: Optional function to rollback migration
        """
        self.version = version
        self.name = name
        self.up = up
        self.down = down


class MigrationManager:
    """Manages database migrations with version tracking.
    
    Usage:
        manager = MigrationManager(db)
        manager.register(migration_001)
        manager.register(migration_002)
        manager.run_pending()
    """
    
    def __init__(self, db: Database):
        """Initialize migration manager.
        
        Args:
            db: Database instance to manage migrations for
        """
        self._db = db
        self._migrations: dict[int, Migration] = {}
    
    def register(self, migration: Migration) -> None:
        """Register a migration.
        
        Args:
            migration: Migration to register
            
        Raises:
            ValueError: If migration version already exists
        """
        if migration.version in self._migrations:
            raise ValueError(
                f"Migration version {migration.version} already registered"
            )
        self._migrations[migration.version] = migration
    
    def get_current_version(self) -> int:
        """Get the current database schema version.
        
        Returns:
            Current version number, 0 if no migrations applied
        """
        result = self._db.fetchone(
            "SELECT MAX(version) as version FROM migrations"
        )
        if result is None or result["version"] is None:
            return 0
        return result["version"]
    
    def get_pending(self) -> list[Migration]:
        """Get list of pending migrations.
        
        Returns:
            List of migrations that haven't been applied yet
        """
        current = self.get_current_version()
        return sorted(
            [m for m in self._migrations.values() if m.version > current],
            key=lambda m: m.version
        )
    
    def get_applied(self) -> list[dict[str, Any]]:
        """Get list of applied migrations.
        
        Returns:
            List of applied migration records
        """
        return self._db.fetchall(
            "SELECT version, name, applied_at FROM migrations ORDER BY version"
        )
    
    def run_pending(self) -> list[Migration]:
        """Run all pending migrations in order.
        
        Returns:
            List of migrations that were applied
            
        Raises:
            Exception: If any migration fails
        """
        pending = self.get_pending()
        applied = []
        
        for migration in pending:
            try:
                # Apply the migration
                migration.up(self._db)
                
                # Record the migration
                self._db.execute(
                    "INSERT INTO migrations (version, name) VALUES (?, ?)",
                    (migration.version, migration.name)
                )
                
                applied.append(migration)
            except Exception as e:
                # Log the failure and re-raise
                print(f"Migration {migration.version} ({migration.name}) failed: {e}")
                raise
        
        return applied
    
    def rollback(self, target_version: int) -> list[Migration]:
        """Rollback migrations to target version.
        
        Args:
            target_version: Version to rollback to (exclusive)
            
        Returns:
            List of migrations that were rolled back
            
        Raises:
            ValueError: If migration doesn't have a down function
        """
        current = self.get_current_version()
        if target_version >= current:
            return []
        
        # Get migrations to rollback (in reverse order)
        to_rollback = sorted(
            [m for m in self._migrations.values() if m.version > target_version],
            key=lambda m: m.version,
            reverse=True
        )
        
        rolled_back = []
        for migration in to_rollback:
            if migration.down is None:
                raise ValueError(
                    f"Migration {migration.version} ({migration.name}) "
                    f"does not support rollback"
                )
            
            try:
                # Apply the rollback
                migration.down(self._db)
                
                # Remove the migration record
                self._db.execute(
                    "DELETE FROM migrations WHERE version = ?",
                    (migration.version,)
                )
                
                rolled_back.append(migration)
            except Exception as e:
                print(f"Rollback of migration {migration.version} failed: {e}")
                raise
        
        return rolled_back


# Example migrations that could be added in the future:
#
# def migration_001_add_user_table(db: Database) -> None:
#     """Add users table."""
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             id TEXT PRIMARY KEY,
#             username TEXT UNIQUE NOT NULL,
#             email TEXT,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)
#
# def migration_002_add_session_user_fk(db: Database) -> None:
#     """Add user_id foreign key to sessions."""
#     db.execute("""
#         ALTER TABLE sessions ADD COLUMN user_id TEXT REFERENCES users(id)
#     """)
