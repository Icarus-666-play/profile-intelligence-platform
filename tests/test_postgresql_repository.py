"""Tests for PostgreSQLProfileRepository and driver selection."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from profile_intelligence.core.config import DatabaseSection
from profile_intelligence.core.config_manager import load_config
from profile_intelligence.core.exceptions import ConfigurationError
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.domain.value_objects.profile_children import Rate, Service
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.repository import (
    PostgreSQLProfileRepository,
    SQLiteProfileRepository,
    create_profile_repository,
)


def test_postgresql_repository_implements_iprofile(database: Database) -> None:
    repo = PostgreSQLProfileRepository(database)
    assert isinstance(repo, IProfileRepository)
    assert repo.backend == "postgresql"


def test_create_profile_repository_selects_adapters(database: Database) -> None:
    sqlite_repo = create_profile_repository(database, driver="sqlite")
    postgres_repo = create_profile_repository(database, driver="postgresql")
    assert isinstance(sqlite_repo, SQLiteProfileRepository)
    assert isinstance(postgres_repo, PostgreSQLProfileRepository)


def test_create_profile_repository_rejects_unknown_driver(database: Database) -> None:
    with pytest.raises(ConfigurationError, match="Unsupported database driver"):
        create_profile_repository(database, driver="oracle")


def test_postgresql_repository_upsert_on_sqlalchemy_session(
    database: Database,
) -> None:
    """ORM operations are dialect-portable; exercise against test SQLite DB."""
    repo: IProfileRepository = PostgreSQLProfileRepository(database)
    profile, created = repo.upsert_draft(
        ProfileDraft(
            display_name="Postgres Ada",
            external_id="pg-1",
            source="unit",
            rates=(Rate(duration="1 hour", price="100"),),
            services=(Service(name="Consulting"),),
        )
    )
    assert created is True
    assert profile.id is not None
    loaded = repo.get_by_id(int(profile.id))
    assert loaded is not None
    assert loaded.display_name == "Postgres Ada"


def test_database_section_defaults_to_sqlite() -> None:
    section = DatabaseSection()
    assert section.driver == "sqlite"
    assert section.url is None


def test_config_loads_postgresql_driver(temp_root: Path) -> None:
    override = {
        "database": {
            "driver": "postgresql",
            "url": "postgresql+psycopg://pip:pip@localhost:5432/pip",
        }
    }
    (temp_root / "config" / "settings.local.yaml").write_text(
        yaml.safe_dump(override),
        encoding="utf-8",
    )
    config = load_config(root_dir=temp_root)
    assert config.database.driver == "postgresql"
    assert config.database.url == (
        "postgresql+psycopg://pip:pip@localhost:5432/pip"
    )


def test_postgres_connect_requires_url(tmp_path: Path) -> None:
    db = Database(
        tmp_path / "unused.sqlite3",
        settings=DatabaseSection(driver="postgresql", url=None),
    )
    with pytest.raises(ConfigurationError, match=r"database\.url"):
        db.connect()
