"""Tests for SQLite connection and repository layer."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig
from profile_intelligence.database.connection import Database, create_database
from profile_intelligence.database.models import Profile
from profile_intelligence.database.repository import ProfileRepository


def test_create_and_connect(app_config: AppConfig) -> None:
    db = create_database(app_config)
    assert db.is_connected
    assert app_config.database_path.exists()
    db.disconnect()
    assert not db.is_connected


def test_session_commit_and_rollback(database: Database) -> None:
    with database.session() as session:
        session.add(Profile(display_name="Alice", source="test"))
    repo = ProfileRepository(database)
    profiles = repo.list_all()
    assert len(profiles) == 1
    assert profiles[0].display_name == "Alice"


def test_profile_repository_crud(database: Database) -> None:
    repo = ProfileRepository(database)
    created = repo.add(Profile(display_name="Bob", source="unit", score=10))
    assert created.id is not None

    loaded = repo.get_by_id(created.id)
    assert loaded is not None
    assert loaded.display_name == "Bob"

    found = repo.find_by_display_name("Bob")
    assert len(found) == 1

    assert repo.delete(created.id) is True
    assert repo.get_by_id(created.id) is None
    assert repo.delete(created.id) is False
