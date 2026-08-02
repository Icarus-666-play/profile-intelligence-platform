"""Eros directory export importer (scaffold).

Replace :meth:`import_file` with parsing for your Eros export format.
Until then this plugin only claims files whose names contain ``eros``.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.importers.base import ImporterPlugin, ImportResult

logger = get_logger("importers.external.eros")


def _has_source_marker(path: Path, marker: str) -> bool:
    stem = path.stem.lower()
    name = path.name.lower()
    return (
        stem == marker
        or stem.startswith(f"{marker}_")
        or stem.endswith(f"_{marker}")
        or f".{marker}." in name
    )


class ErosImporter(ImporterPlugin):
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

    def can_handle(self, path: PathLike) -> bool:
        resolved = Path(path)
        return _has_source_marker(resolved, "eros") and self.matches_extension(
            resolved
        )

    def import_file(self, path: PathLike, **options: object) -> ImportResult:
        resolved = self.validate_path(path)
        logger.warning(
            "Eros importer is a scaffold; no parser implemented for %s",
            resolved,
        )
        return ImportResult.failure(
            "Eros importer scaffold: implement parsing in "
            "plugins/eros/importer.py",
            records_read=0,
        )
