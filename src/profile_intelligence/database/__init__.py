"""SQLite persistence layer."""

from __future__ import annotations

from profile_intelligence.database.connection import Database, create_database
from profile_intelligence.database.migrate import (
    Migration,
    MigrationRunner,
    run_migrations,
)
from profile_intelligence.database.models import Base, Profile, SchemaMigration
from profile_intelligence.database.repository import (
    ProfileRepository,
    Repository,
)
from profile_intelligence.database.seed import (
    DEFAULT_SEED_PROFILES,
    DatabaseSeeder,
    SeedResult,
    seed_database,
)

__all__ = [
    "DEFAULT_SEED_PROFILES",
    "Base",
    "Database",
    "DatabaseSeeder",
    "Migration",
    "MigrationRunner",
    "Profile",
    "ProfileRepository",
    "Repository",
    "SchemaMigration",
    "SeedResult",
    "create_database",
    "run_migrations",
    "seed_database",
]
