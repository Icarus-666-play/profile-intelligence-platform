"""Enrich profiles table for Milestone 1 fields."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from profile_intelligence.database.migrations.base import Migration


class EnrichProfilesMigration(Migration):
    """Add contact and metadata columns to profiles."""

    version = "002"
    name = "enrich_profiles"

    def up(self, connection: Connection) -> None:
        columns = {
            "email": "VARCHAR(320)",
            "phone": "VARCHAR(64)",
            "title": "VARCHAR(255)",
            "organization": "VARCHAR(255)",
            "location": "VARCHAR(255)",
            "tags": "TEXT",
            "raw_json": "TEXT",
        }
        existing = {
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(profiles)")
            ).fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name in existing:
                continue
            # Column names/types come from the controlled mapping above.
            connection.execute(
                text(
                    f"ALTER TABLE profiles ADD COLUMN {column_name} {column_type}"
                )
            )

        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_email
                ON profiles (email)
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_profiles_external_id
                ON profiles (external_id)
                """
            )
        )

    def down(self, connection: Connection) -> None:
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_external_id"))
        connection.execute(text("DROP INDEX IF EXISTS ix_profiles_email"))
        # SQLite cannot DROP COLUMN portably on older versions; leave columns.
