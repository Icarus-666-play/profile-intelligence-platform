"""Compatibility shim — prefer ``profile_intelligence.application.use_cases``."""

from __future__ import annotations

from profile_intelligence.application.use_cases import (
    ApplicationService,
    CompareService,
    ImportService,
    ImportSummary,
    ProfileComparison,
    ProfileService,
)

__all__ = [
    "ApplicationService",
    "CompareService",
    "ImportService",
    "ImportSummary",
    "ProfileComparison",
    "ProfileService",
]
