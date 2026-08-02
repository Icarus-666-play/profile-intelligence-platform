"""Compatibility shim for importer base types."""

from __future__ import annotations

from profile_intelligence.infrastructure.importers.base import (
    ImporterPlugin,
    ImportResult,
    RawRecord,
)

__all__ = ["ImportResult", "ImporterPlugin", "RawRecord"]
