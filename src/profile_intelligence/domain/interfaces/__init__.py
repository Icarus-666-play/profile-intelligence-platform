"""Domain ports / interfaces."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.importers import (
    ImporterPlugin,
    ProfileImporter,
    ProfileParseOutcome,
)
from profile_intelligence.domain.interfaces.repositories import (
    IPhotoRepository,
    IProfileRepository,
    IRateRepository,
    IReviewRepository,
    IServiceRepository,
    ProfileEntity,
    ProfileRepositoryPort,
    Repository,
)

__all__ = [
    "IPhotoRepository",
    "IProfileRepository",
    "IRateRepository",
    "IReviewRepository",
    "IServiceRepository",
    "ImporterPlugin",
    "ProfileEntity",
    "ProfileImporter",
    "ProfileParseOutcome",
    "ProfileRepositoryPort",
    "Repository",
]
