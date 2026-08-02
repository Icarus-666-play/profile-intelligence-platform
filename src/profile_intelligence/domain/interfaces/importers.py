"""Importer ports (plugin interfaces)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.value_objects.importing import ImportResult, RawRecord

logger = get_logger(__name__)

ProfileParseOutcome = ImportResult | tuple[list[RawRecord], int]


class ImporterPlugin(ABC):
    """Port for importer plugins.

    Prefer :class:`ProfileImporter` for profile row importers. Plugins are
    discovered under ``infrastructure.importers.plugins`` or external
    ``plugins/`` packages.
    """

    name: ClassVar[str]
    description: ClassVar[str] = ""
    supported_extensions: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def can_handle(self, path: PathLike) -> bool:
        """Return True if this plugin can import the given path."""

    @abstractmethod
    def import_file(self, path: PathLike, **options: object) -> ImportResult:
        """Parse *path* and return raw records inside an :class:`ImportResult`."""

    def validate_path(self, path: PathLike) -> Path:
        """Resolve and validate that *path* exists and is a file."""
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Import path does not exist: {resolved}")
        if not resolved.is_file():
            raise IsADirectoryError(f"Import path is not a file: {resolved}")
        return resolved

    def matches_extension(self, path: PathLike) -> bool:
        """Return True if the path extension is in ``supported_extensions``."""
        if not self.supported_extensions:
            return False
        suffix = Path(path).suffix.lower()
        return suffix in {ext.lower() for ext in self.supported_extensions}


class ProfileImporter(ImporterPlugin):
    """Port/base for importers that produce profile row records."""

    source_markers: ClassVar[tuple[str, ...]] = ()
    require_source_marker: ClassVar[bool] = False

    def can_handle(self, path: PathLike) -> bool:
        """Return True when extension (and optional source marker) match."""
        if not self.matches_extension(path):
            return False
        if self.require_source_marker or self.source_markers:
            return self.matches_source_marker(path)
        return True

    def matches_source_marker(self, path: PathLike) -> bool:
        """Return True if the filename matches any configured source marker."""
        if not self.source_markers:
            return False
        resolved = Path(path)
        return any(
            self._has_source_marker(resolved, marker) for marker in self.source_markers
        )

    def import_file(self, path: PathLike, **options: object) -> ImportResult:
        """Validate *path*, parse profile rows, and wrap an :class:`ImportResult`."""
        resolved = self.validate_path(path)
        parsed = self.parse_profiles(resolved, **options)
        if isinstance(parsed, ImportResult):
            if not parsed.metadata:
                parsed = ImportResult(
                    success=parsed.success,
                    records_read=parsed.records_read,
                    records_imported=parsed.records_imported,
                    records_skipped=parsed.records_skipped,
                    records=parsed.records,
                    errors=parsed.errors,
                    metadata=self.build_metadata(resolved, **options),
                )
            logger.debug(
                "Importer '%s' finished %s success=%s",
                self.name,
                resolved,
                parsed.success,
            )
            return parsed

        records, skipped = parsed
        logger.debug(
            "Parsed profiles via '%s' from %s: records=%d skipped=%d",
            self.name,
            resolved,
            len(records),
            skipped,
        )
        return ImportResult.from_records(
            records,
            skipped=skipped,
            metadata=self.build_metadata(resolved, **options),
        )

    @abstractmethod
    def parse_profiles(
        self,
        path: Path,
        **options: object,
    ) -> ProfileParseOutcome:
        """Parse *path* into ``(records, skipped)`` or an :class:`ImportResult`."""

    def build_metadata(self, path: Path, **options: object) -> dict[str, Any]:
        """Return default import metadata; subclasses may extend."""
        metadata: dict[str, Any] = {
            "path": str(path),
            "plugin": self.name,
        }
        serializable = {
            key: value
            for key, value in options.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        }
        if serializable:
            metadata["options"] = serializable
        return metadata

    def is_empty_row(self, row: dict[str, Any]) -> bool:
        """Return True when every cell in *row* is empty/blank."""
        return all(
            value is None or str(value).strip() == "" for value in row.values()
        )

    @staticmethod
    def _has_source_marker(path: Path, marker: str) -> bool:
        stem = path.stem.lower()
        name = path.name.lower()
        marker = marker.lower()
        return (
            stem == marker
            or stem.startswith(f"{marker}_")
            or stem.endswith(f"_{marker}")
            or f".{marker}." in name
        )
