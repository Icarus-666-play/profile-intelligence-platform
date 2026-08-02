"""Compatibility shim — prefer ``profile_intelligence.infrastructure.dashboard``."""

from __future__ import annotations

from profile_intelligence.infrastructure.dashboard import (
    DashboardService,
    DashboardSnapshot,
)

__all__ = ["DashboardService", "DashboardSnapshot"]
