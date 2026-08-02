"""Domain value objects."""

from __future__ import annotations

from profile_intelligence.domain.value_objects.ai import (
    AICompletionRequest,
    AICompletionResult,
)
from profile_intelligence.domain.value_objects.confidence import ConfidenceScore
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.domain.value_objects.importing import ImportResult, RawRecord
from profile_intelligence.domain.value_objects.profile_children import (
    Availability,
    Photo,
    Rate,
    Review,
    Service,
)

__all__ = [
    "AICompletionRequest",
    "AICompletionResult",
    "Availability",
    "ConfidenceScore",
    "ImportResult",
    "ParsedDocument",
    "Photo",
    "Rate",
    "RawDocument",
    "RawRecord",
    "Review",
    "Service",
]
