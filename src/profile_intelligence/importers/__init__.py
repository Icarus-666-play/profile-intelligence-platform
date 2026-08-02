"""Compatibility shim — prefer ``profile_intelligence.infrastructure.importers``."""

from __future__ import annotations

from profile_intelligence.infrastructure.importers import (
    ImporterPlugin,
    ImporterRegistry,
    ImportResult,
    ProfileImporter,
    RawRecord,
)

__all__ = [
    "ImportResult",
    "ImporterPlugin",
    "ImporterRegistry",
    "ProfileImporter",
    "RawRecord",
]
