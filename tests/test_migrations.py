"""Tests for the migration framework."""

from __future__ import annotations

from sqlalchemy import text

from profile_intelligence.core.config import AppConfig
from profile_intelligence.database.connection import create_database
from profile_intelligence.database.migrate import MigrationRunner, run_migrations


def test_migrate_applies_initial_schema(app_config: AppConfig) -> None:
    db = create_database(app_config)
    runner = MigrationRunner(db)
    assert runner.pending()
    applied = run_migrations(db)
    assert "001" in applied
    assert "002" in applied
    assert runner.pending() == []
    # Idempotent
    assert run_migrations(db) == []

    with db.engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(profiles)"))
        }
    assert "profiles" in tables
    assert "schema_migrations" in tables
    assert "email" in columns
    assert "raw_json" in columns
    db.disconnect()


def test_applied_versions(database) -> None:
    runner = MigrationRunner(database)
    assert {"001", "002"} <= runner.applied_versions()
