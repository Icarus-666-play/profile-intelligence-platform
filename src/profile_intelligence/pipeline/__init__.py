"""Compatibility shim — prefer ``profile_intelligence.application.pipeline``."""

from __future__ import annotations

from profile_intelligence.application.pipeline import (
    DocumentParser,
    ProcessingChain,
    ProcessingResult,
    ProfileNormalizer,
    ProfileValidator,
)
from profile_intelligence.application.use_cases import ImportPipeline, PipelineResult
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)

__all__ = [
    "DocumentParser",
    "ImportPipeline",
    "ParsedDocument",
    "PipelineResult",
    "ProcessingChain",
    "ProcessingResult",
    "ProfileNormalizer",
    "ProfileValidator",
    "RawDocument",
]
