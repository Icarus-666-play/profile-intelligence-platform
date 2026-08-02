"""Console dashboard adapter and snapshot metrics.

Milestone 2 ships the multi-page local UI under ``profile_intelligence.ui``.
"""

from __future__ import annotations

from profile_intelligence.infrastructure.dashboard.service import (
    DashboardDuplicateItem,
    DashboardService,
    DashboardSnapshot,
    ImportQueueItem,
    LatestImportItem,
)

__all__ = [
    "DashboardDuplicateItem",
    "DashboardService",
    "DashboardSnapshot",
    "ImportQueueItem",
    "LatestImportItem",
]
