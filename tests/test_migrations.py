"""Tests for the migration framework."""

from __future__ import annotations

from sqlalchemy import text

from profile_intelligence.core.config import AppConfig
from profile_intelligence.database.connection import create_database
from profile_intelligence.database.migrations.runner import MigrationRunner


def test_migrate_applies_initial_schema(app_config: AppConfig) -> None:
    db = create_database(app_config)
    runner = MigrationRunner(db)
    assert runner.pending()
    applied = runner.migrate()
    assert "001" in applied
    assert runner.pending() == []
    # Idempotent
    assert runner.migrate() == []

    with db.engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    assert "profiles" in tables
    assert "schema_migrations" in tables
    db.disconnect()


def test_applied_versions(database) -> None:
    runner = MigrationRunner(database)
    assert "001" in runner.applied_versions()
