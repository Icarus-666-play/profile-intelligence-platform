"""Workflow domain events for the post-import reaction chain.

```
ProfileImported
 ↓
ScoreCalculated
 ↓
ImagesExtracted
 ↓
ExcelExported
 ↓
DashboardUpdated
```
"""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class ProfileImported(DomainEvent):
    """Raised after profiles have been imported into persistence."""

    profile_ids: tuple[int, ...] = ()
    created: int = 0
    updated: int = 0
    source: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class ScoreCalculated(DomainEvent):
    """Raised after Confidence Scores (0-100) have been recalculated."""

    profile_ids: tuple[int, ...] = ()
    rescored: int = 0


@dataclass(frozen=True, slots=True)
class ImagesExtracted(DomainEvent):
    """Raised after profile images have been extracted / inventoried."""

    profile_ids: tuple[int, ...] = ()
    image_count: int = 0


@dataclass(frozen=True, slots=True)
class ExcelExported(DomainEvent):
    """Raised after an Excel report has been written."""

    path: str = ""
    profile_count: int = 0


@dataclass(frozen=True, slots=True)
class DashboardUpdated(DomainEvent):
    """Raised after the dashboard export has been refreshed."""

    path: str = ""
    profile_count: int = 0


# Canonical reaction order for the workflow.
WORKFLOW_EVENT_CHAIN: tuple[type[DomainEvent], ...] = (
    ProfileImported,
    ScoreCalculated,
    ImagesExtracted,
    ExcelExported,
    DashboardUpdated,
)
