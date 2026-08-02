"""Built-in migration versions.

Import migration modules here so they are registered with the runner's
discovery mechanism.
"""

from __future__ import annotations

from profile_intelligence.database.migrations.versions import v001_initial_schema

ALL_MIGRATIONS = (
    v001_initial_schema.InitialSchemaMigration,
)

__all__ = ["ALL_MIGRATIONS"]
