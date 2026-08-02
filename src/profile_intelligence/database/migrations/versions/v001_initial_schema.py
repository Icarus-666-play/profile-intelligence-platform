"""Initial schema migration — profiles and schema_migrations tables."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from profile_intelligence.database.migrations.base import Migration


class InitialSchemaMigration(Migration):
    """Create core tables for PIP."""

    version = "001"
    name = "initial_schema"

    def up(self, connection: Connection) -> None:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(64) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    external_id VARCHAR(255),
                    display_name VARCHAR(512) NOT NULL,
                    source VARCHAR(128),
                    notes TEXT,
                    score INTEGER,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_display_name
                ON profiles (display_name)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_source
                ON profiles (source)
                """
            )
        )

    def down(self, connection: Connection) -> None:
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_source"))
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_display_name"))
        connection.execute(text("DROP TABLE IF EXISTS profiles"))
        # schema_migrations retained so history is not destroyed accidentally
