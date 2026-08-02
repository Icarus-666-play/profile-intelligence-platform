"""Domain events."""

from __future__ import annotations

from profile_intelligence.domain.events.base import DomainEvent
from profile_intelligence.domain.events.workflow import (
    WORKFLOW_EVENT_CHAIN,
    DashboardUpdated,
    ExcelExported,
    ImagesExtracted,
    ProfileImported,
    ScoreCalculated,
)

__all__ = [
    "WORKFLOW_EVENT_CHAIN",
    "DashboardUpdated",
    "DomainEvent",
    "ExcelExported",
    "ImagesExtracted",
    "ProfileImported",
    "ScoreCalculated",
]
