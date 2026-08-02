"""SQLite persistence layer."""

from __future__ import annotations

from profile_intelligence.database.connection import Database, create_database
from profile_intelligence.database.models import Base, Profile, SchemaMigration
from profile_intelligence.database.repository import (
    ProfileRepository,
    Repository,
)

__all__ = [
    "Base",
    "Database",
    "Profile",
    "ProfileRepository",
    "Repository",
    "SchemaMigration",
    "create_database",
]
