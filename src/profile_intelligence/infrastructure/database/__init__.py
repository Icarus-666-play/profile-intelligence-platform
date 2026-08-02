"""Database persistence layer (SQLite / PostgreSQL)."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.repositories import Repository
from profile_intelligence.infrastructure.database.child_repositories import (
    SQLitePhotoRepository,
    SQLiteRateRepository,
    SQLiteReviewRepository,
    SQLiteServiceRepository,
)
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
    PostgreSQLProfileRepository,
    ProfileRepository,
    SqlAlchemyProfileRepository,
    SQLiteProfileRepository,
    SQLiteRepository,
    create_profile_repository,
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
    "PostgreSQLProfileRepository",
    "Profile",
    "ProfileAvailability",
    "ProfilePhoto",
    "ProfileRate",
    "ProfileRepository",
    "ProfileReview",
    "ProfileService",
    "Repository",
    "SQLitePhotoRepository",
    "SQLiteProfileRepository",
    "SQLiteRateRepository",
    "SQLiteRepository",
    "SQLiteReviewRepository",
    "SQLiteServiceRepository",
    "SchemaMigration",
    "SeedResult",
    "SqlAlchemyProfileRepository",
    "create_database",
    "create_profile_repository",
    "run_migrations",
    "seed_database",
]
