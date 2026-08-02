"""Compatibility re-exports for importer interfaces."""

from __future__ import annotations

from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.importing import ImportResult, RawRecord

__all__ = ["ImportResult", "ImporterPlugin", "RawRecord"]
