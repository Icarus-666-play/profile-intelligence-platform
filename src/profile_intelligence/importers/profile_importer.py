"""Compatibility shim for ProfileImporter."""

from __future__ import annotations

from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

__all__ = ["ProfileImporter", "ProfileParseOutcome"]
