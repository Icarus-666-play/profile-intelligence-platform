"""Document models for the import pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from profile_intelligence.core.exceptions import ValidationError
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.value_objects.importing import RawRecord


@dataclass(frozen=True, slots=True)
class RawDocument:
    """File stage output: a resolved source document ready for parsing."""

    path: Path
    source: str | None = None
    plugin_name: str | None = None
    content_type: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(
        cls,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RawDocument:
        """Build a :class:`RawDocument` from an existing filesystem path."""
        resolved = Path(path).expanduser().resolve()
        if not resolved.exists():
            raise ValidationError(f"Import file does not exist: {resolved}")
        if not resolved.is_file():
            raise ValidationError(f"Import path is not a file: {resolved}")
        return cls.reference(
            resolved,
            source=source,
            plugin_name=plugin_name,
            metadata=metadata,
        )

    @classmethod
    def reference(
        cls,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RawDocument:
        """Build a document reference without requiring the file to exist."""
        resolved = Path(path).expanduser().resolve()
        suffix = resolved.suffix.lower()
        return cls(
            path=resolved,
            source=source,
            plugin_name=plugin_name,
            content_type=suffix.lstrip(".") or None,
            metadata={
                "suffix": suffix,
                "name": resolved.name,
                **dict(metadata or {}),
            },
        )


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Parser stage output: raw row records extracted from a document."""

    document: RawDocument
    plugin_name: str
    records: tuple[RawRecord, ...]
    records_read: int
    records_skipped: int = 0
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        """Source file path."""
        return self.document.path
