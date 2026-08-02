"""Domain layer: entities, value objects, and interfaces."""

from __future__ import annotations

from profile_intelligence.domain.entities.profile import ProfileDraft, ProfileExtractor
from profile_intelligence.domain.interfaces.importers import (
    ImporterPlugin,
    ProfileImporter,
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
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.domain.value_objects.importing import ImportResult, RawRecord

__all__ = [
    "IPhotoRepository",
    "IProfileRepository",
    "IRateRepository",
    "IReviewRepository",
    "IServiceRepository",
    "ImportResult",
    "ImporterPlugin",
    "ParsedDocument",
    "ProfileDraft",
    "ProfileEntity",
    "ProfileExtractor",
    "ProfileImporter",
    "ProfileRepositoryPort",
    "RawDocument",
    "RawRecord",
    "Repository",
]
