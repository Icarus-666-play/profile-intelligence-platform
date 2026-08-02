"""Eros directory export importer (scaffold).

Replace :meth:`parse_profiles` with parsing for your Eros export format.
Until then this plugin only claims files marked with ``eros``.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from profile_intelligence.core.logging import get_logger
from profile_intelligence.importers.base import ImportResult
from profile_intelligence.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger("importers.external.eros")


class ErosImporter(ProfileImporter):
    """Scaffold importer for Eros profile exports."""

    name: ClassVar[str] = "eros"
    description: ClassVar[str] = (
        "Eros directory export importer (scaffold — implement parsing)"
    )
    supported_extensions: ClassVar[tuple[str, ...]] = (
        ".csv",
        ".json",
        ".xlsx",
        ".html",
    )
    source_markers: ClassVar[tuple[str, ...]] = ("eros",)
    require_source_marker: ClassVar[bool] = True

    def parse_profiles(self, path: Path, **options: object) -> ProfileParseOutcome:
        logger.warning(
            "Eros importer is a scaffold; no parser implemented for %s",
            path,
        )
        return ImportResult.failure(
            "Eros importer scaffold: implement parse_profiles in "
            "plugins/eros/importer.py"
        )
