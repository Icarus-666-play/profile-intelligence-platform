"""Importer plugin interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from profile_intelligence.core.types import PathLike

RawRecord = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Outcome of an import operation.

    Successful file parsers populate :attr:`records` with raw row mappings.
    Persistence is handled by the import service, not the plugin.
    """

    success: bool
    records_read: int = 0
    records_imported: int = 0
    records_skipped: int = 0
    records: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def failure(cls, message: str, *, records_read: int = 0) -> ImportResult:
        """Convenience constructor for a failed import."""
        return cls(
            success=False,
            records_read=records_read,
            errors=(message,),
        )

    @classmethod
    def from_records(
        cls,
        records: Sequence[Mapping[str, Any]],
        *,
        skipped: int = 0,
        errors: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ImportResult:
        """Build a successful result from parsed raw records."""
        materialized = tuple(dict(record) for record in records)
        return cls(
            success=True,
            records_read=len(materialized) + skipped,
            records_imported=len(materialized),
            records_skipped=skipped,
            records=materialized,
            errors=errors,
            metadata=metadata or {},
        )


class ImporterPlugin(ABC):
    """Base class for all importer plugins.

    Prefer :class:`~profile_intelligence.importers.profile_importer.ProfileImporter`
    for profile row importers. Plugins are discovered by subclassing and either:
    - living under ``profile_intelligence.importers.plugins``, or
    - being loaded from the configured external ``plugins/`` packages.
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
