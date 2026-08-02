"""Compatibility shim — prefer ``profile_intelligence.application.use_cases``."""

from __future__ import annotations

from profile_intelligence.application.use_cases import ImportPipeline, PipelineResult
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)

__all__ = ["ImportPipeline", "ParsedDocument", "PipelineResult", "RawDocument"]
