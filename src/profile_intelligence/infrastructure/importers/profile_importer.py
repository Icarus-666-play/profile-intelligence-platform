"""Compatibility re-exports for :class:`ProfileImporter`."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.importers import (
    ProfileImporter,
    ProfileParseOutcome,
)

__all__ = ["ProfileImporter", "ProfileParseOutcome"]
