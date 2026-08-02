"""Domain ports / interfaces."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.importers import (
    ImporterPlugin,
    ProfileImporter,
    ProfileParseOutcome,
)
from profile_intelligence.domain.interfaces.repositories import (
    ProfileRepositoryPort,
    Repository,
)

__all__ = [
    "ImporterPlugin",
    "ProfileImporter",
    "ProfileParseOutcome",
    "ProfileRepositoryPort",
    "Repository",
]
