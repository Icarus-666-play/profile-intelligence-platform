"""SQLite persistence layer."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.repositories import Repository
from profile_intelligence.infrastructure.database.connection import (
    Database,
    create_database,
)
from profile_intelligence.infrastructure.database.migrate import (
    Migration,
    MigrationRunner,
    run_migrations,
)
from profile_intelligence.infrastructure.database.models import (
    Base,
    MediaAsset,
    Profile,
    SchemaMigration,
)
from profile_intelligence.infrastructure.database.models_profile_children import (
    ProfileAvailability,
    ProfilePhoto,
    ProfileRate,
    ProfileReview,
    ProfileService,
)
from profile_intelligence.infrastructure.database.repository import (
    DatabaseRepository,
    ProfileRepository,
    SQLiteRepository,
)
from profile_intelligence.infrastructure.database.seed import (
    DEFAULT_SEED_PROFILES,
    DatabaseSeeder,
    SeedResult,
    seed_database,
)

__all__ = [
    "DEFAULT_SEED_PROFILES",
    "Base",
    "Database",
    "DatabaseRepository",
    "DatabaseSeeder",
    "MediaAsset",
    "Migration",
    "MigrationRunner",
    "Profile",
    "ProfileAvailability",
    "ProfilePhoto",
    "ProfileRate",
    "ProfileRepository",
    "ProfileReview",
    "ProfileService",
    "Repository",
    "SQLiteRepository",
    "SchemaMigration",
    "SeedResult",
    "create_database",
    "run_migrations",
    "seed_database",
]
