"""Domain ports / interfaces."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.interfaces.cache import ICache
from profile_intelligence.domain.interfaces.events import (
    EventHandler,
    IEventBus,
    IEventPublisher,
)
from profile_intelligence.domain.interfaces.importers import (
    ImporterPlugin,
    ProfileImporter,
    ProfileParseOutcome,
)
from profile_intelligence.domain.interfaces.plugin_pipeline import (
    PLUGIN_PIPELINE_STAGES,
    DownloadArtifact,
    IDocumentDownloader,
    ISourceExtractor,
    ISourceNormalizer,
    ISourceParser,
    ISourceValidator,
    StageValidationResult,
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
    "PLUGIN_PIPELINE_STAGES",
    "DownloadArtifact",
    "EventHandler",
    "IAIProvider",
    "ICache",
    "IDocumentDownloader",
    "IEventBus",
    "IEventPublisher",
    "IPhotoRepository",
    "IProfileRepository",
    "IRateRepository",
    "IReviewRepository",
    "IServiceRepository",
    "ISourceExtractor",
    "ISourceNormalizer",
    "ISourceParser",
    "ISourceValidator",
    "ImporterPlugin",
    "ProfileEntity",
    "ProfileImporter",
    "ProfileParseOutcome",
    "ProfileRepositoryPort",
    "Repository",
    "StageValidationResult",
]
