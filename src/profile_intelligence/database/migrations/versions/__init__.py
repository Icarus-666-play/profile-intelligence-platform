"""Built-in migration versions.

Import migration modules here so they are registered with the runner's
discovery mechanism.
"""

from __future__ import annotations

from profile_intelligence.database.migrations.versions import (
    v001_initial_schema,
    v002_enrich_profiles,
)

ALL_MIGRATIONS = (
    v001_initial_schema.InitialSchemaMigration,
    v002_enrich_profiles.EnrichProfilesMigration,
)

__all__ = ["ALL_MIGRATIONS"]
